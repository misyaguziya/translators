import asyncio
import json
import random
import re
import time
import urllib.parse
from typing import Optional, Union

from yarl import URL

from translators.base import Tse, LangMapKwargsType, TranslatorError, ApiKwargsType, AsyncSessionType, SessionType


class YandexV1(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.home_url = 'https://yandex.com'
        self.host_url = 'https://translate.yandex.com'
        self.api_url = 'https://translate.yandex.net/api/v1/tr.json/translate'
        self.api_host = 'https://translate.yandex.net'
        self.detect_language_url = 'https://translate.yandex.net/api/v1/tr.json/detect'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True)
        self.api_headers.update({'Referer': self.api_host, 'x-retpath-y': self.host_url})
        self.language_map = None
        self.session = None
        self.sid = None
        self.yu = None
        self.yum = None
        self.sprvk = None
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(1e4)  # ten thousand.
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, host_html: str, **kwargs: LangMapKwargsType) -> dict:
        lang_str = re.compile('TRANSLATOR_LANGS: {(.*?)},').search(host_html).group(0)[18:-1]
        lang_dict = json.loads(lang_str)
        lang_list = sorted(list(lang_dict.keys()))
        return {}.fromkeys(lang_list, lang_list)

    def get_yum(self) -> str:
        return str(int(time.time() * 1e10))

    # def get_csrf_token(self, host_html: str) -> str:
    #     return re.compile(pattern="CSRF_TOKEN: '(.*?)',").findall(host_html)[0]
    #
    # def get_key(self, host_html: str) -> str:
    #     return re.compile(pattern="SPEECHKIT_KEY: '(.*?)',").findall(host_html)[0]

    def get_sid(self, host_html: str) -> str:
        try:
            sid_find = re.compile("SID: '(.*?)',").findall(host_html)[0]
            return '.'.join([w[::-1] for w in sid_find.split('.')])
        except Exception as e:
            captcha_info = 'SmartCaptcha needs verification'
            if captcha_info in host_html:
                raise TranslatorError(captcha_info)
            raise TranslatorError(str(e))

    def detect_language(self, ss: SessionType, query_text: str, sid: str, yu: str, headers: dict,
                        timeout: Optional[float]) -> str:
        params = {
            'sid': sid,
            'yu': yu,
            'text': query_text,
            'srv': 'tr-text',
            'hint': 'en,ru',
            'options': 1
        }
        r = ss.get(self.detect_language_url, params=params, headers=headers, timeout=timeout)
        lang = r.json().get('lang')
        return lang if lang else 'en'

    async def detect_language_async(self, ss: AsyncSessionType, query_text: str, sid: str, yu: str, headers: dict,
                                    timeout: Optional[float]) -> str:
        params = {
            'sid': sid,
            'yu': yu,
            'text': query_text,
            'srv': 'tr-text',
            'hint': 'en,ru',
            'options': 1
        }
        r = await ss.get(self.detect_language_url, params=params, headers=headers, timeout=timeout)
        lang = (await r.json()).get('lang')
        return lang if lang else 'en'

    @Tse.uncertified
    @Tse.time_stat
    @Tse.check_query
    def yandex_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                   **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translate.yandex.com
        :param query_text: str, must.
        :param from_language: str, default 'auto'.
        :param to_language: str, default 'en'.
        :param **kwargs:
                :param timeout: Optional[float], default None.
                :param proxies: Optional[dict], default None.
                :param sleep_seconds: float, default 0.
                :param is_detail_result: bool, default False.
                :param http_client: str, default 'requests'. Union['requests', 'niquests', 'httpx', 'cloudscraper']
                :param if_ignore_limit_of_length: bool, default False.
                :param limit_of_length: int, default 20000.
                :param if_ignore_empty_query: bool, default False.
                :param update_session_after_freq: int, default 1000.
                :param update_session_after_seconds: float, default 1500.
                :param if_show_time_stat: bool, default False.
                :param show_time_stat_precision: int, default 2.
                :param if_print_warning: bool, default True.
                :param reset_host_url: str, default None. eg: 'https://translate.yandex.fr'
                :param if_check_reset_host_url: bool, default True.
        :return: str or dict
        """

        reset_host_url = kwargs.get('reset_host_url', None)
        if reset_host_url and reset_host_url != self.host_url:
            if kwargs.get('if_check_reset_host_url', True) and not reset_host_url[:25] == 'https://translate.yandex.':
                raise TranslatorError
            self.host_url = reset_host_url.strip('/')

        timeout = kwargs.get('timeout', None)
        proxies = kwargs.get('proxies', None)
        sleep_seconds = kwargs.get('sleep_seconds', 0)
        http_client = kwargs.get('http_client', 'requests')
        if_print_warning = kwargs.get('if_print_warning', True)
        is_detail_result = kwargs.get('is_detail_result', False)
        update_session_after_freq = kwargs.get('update_session_after_freq', self.default_session_freq)
        update_session_after_seconds = kwargs.get('update_session_after_seconds', self.default_session_seconds)
        self.check_input_limit(query_text, self.input_limit)

        not_update_cond_freq = 1 if self.query_count % update_session_after_freq != 0 else 0
        not_update_cond_time = 1 if time.time() - self.begin_time < update_session_after_seconds else 0
        if not (
                self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.sid and self.yu):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            _ = self.session.get(self.home_url, headers=self.host_headers, timeout=timeout)
            _ = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text

            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, **debug_lang_kwargs)

            self.sid = self.get_sid(host_html)
            self.yum = self.get_yum()
            self.yu = dict(self.session.cookies).get(
                'yuidss') or f'{random.randint(int(1e8), int(9e8))}{int(time.time())}'
            self.sprvk = dict(self.session.cookies).get('spravka')

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)
        if from_language == 'auto':
            from_language = self.detect_language(self.session, query_text, self.sid, self.yu, self.api_headers, timeout)

        params = {
            'id': f'{self.sid}-{self.query_count}-0',
            'source_lang': from_language,
            'target_lang': to_language,
            'srv': 'tr-text',
            'reason': 'paste',  # 'auto'
            'format': 'text',
            'ajax': 1,
            'yu': self.yu,
        }
        if self.sprvk:
            params.update({'sprvk': self.sprvk, 'yum': self.yum})

        payload = urllib.parse.urlencode({'text': query_text, 'options': 4})
        r = self.session.post(self.api_url, params=params, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join(data['text'])

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translate.yandex.com
        :param query_text: str, must.
        :param from_language: str, default 'auto'.
        :param to_language: str, default 'en'.
        :param **kwargs:
                :param timeout: Optional[float], default None.
                :param proxies: Optional[dict], default None.
                :param sleep_seconds: float, default 0.
                :param is_detail_result: bool, default False.
                :param http_client: str, default 'requests'. Union['requests', 'niquests', 'httpx', 'cloudscraper']
                :param if_ignore_limit_of_length: bool, default False.
                :param limit_of_length: int, default 20000.
                :param if_ignore_empty_query: bool, default False.
                :param update_session_after_freq: int, default 1000.
                :param update_session_after_seconds: float, default 1500.
                :param if_show_time_stat: bool, default False.
                :param show_time_stat_precision: int, default 2.
                :param if_print_warning: bool, default True.
                :param reset_host_url: str, default None. eg: 'https://translate.yandex.fr'
                :param if_check_reset_host_url: bool, default True.
        :return: str or dict
        """

        reset_host_url = kwargs.get('reset_host_url', None)
        if reset_host_url and reset_host_url != self.host_url:
            if kwargs.get('if_check_reset_host_url', True) and not reset_host_url[:25] == 'https://translate.yandex.':
                raise TranslatorError
            self.host_url = reset_host_url.strip('/')

        timeout = kwargs.get('timeout', None)
        proxies = kwargs.get('proxies', None)
        sleep_seconds = kwargs.get('sleep_seconds', 0)
        if_print_warning = kwargs.get('if_print_warning', True)
        is_detail_result = kwargs.get('is_detail_result', False)
        update_session_after_freq = kwargs.get('update_session_after_freq', self.default_session_freq)
        update_session_after_seconds = kwargs.get('update_session_after_seconds', self.default_session_seconds)
        self.check_input_limit(query_text, self.input_limit)

        not_update_cond_freq = 1 if self.query_count % update_session_after_freq != 0 else 0
        not_update_cond_time = 1 if time.time() - self.begin_time < update_session_after_seconds else 0
        if not (
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.sid and self.yu):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(proxies)
            _ = await self.async_session.get(self.home_url, headers=self.host_headers, timeout=timeout)
            _ = await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            host_html = await (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text()

            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, **debug_lang_kwargs)

            self.sid = self.get_sid(host_html)
            self.yum = self.get_yum()
            self.yu = self.async_session.cookie_jar.filter_cookies(URL(self.api_url)).get('yuidss').value or f'{random.randint(int(1e8), int(9e8))}{int(time.time())}'
            self.sprvk = self.async_session.cookie_jar.filter_cookies(URL(self.api_url)).get('spravka').value

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)
        if from_language == 'auto':
            from_language = await self.detect_language_async(self.async_session, query_text, self.sid, self.yu,
                                                             self.api_headers, timeout)

        params = {
            'id': f'{self.sid}-{self.query_count}-0',
            'source_lang': from_language,
            'target_lang': to_language,
            'srv': 'tr-text',
            'reason': 'paste',  # 'auto'
            'format': 'text',
            'ajax': 1,
            'yu': self.yu,
        }
        if self.sprvk:
            params.update({'sprvk': self.sprvk, 'yum': self.yum})

        payload = urllib.parse.urlencode({'text': query_text, 'options': 4})
        r = await self.async_session.post(self.api_url, params=params, data=payload, headers=self.api_headers,
                                          timeout=timeout)
        r.raise_for_status()
        data = await r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join(data['text'])


class YandexV2(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.home_url = 'https://www.youtube.com'
        self.api_url = 'https://browser.translate.yandex.net/api/v1/tr.json'
        self.ua_yandex = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 YaBrowser/24.1.5.825 Yowser/2.5 Safari/537.36'
        self.api_headers = self.get_headers(self.home_url, if_api=True)
        self.api_headers.update({'User-Agent': self.ua_yandex})
        self.language_map = None
        self.session = None
        self.srv = 'browser_video_translation'
        self.api_payload = {'maxRetryCount': 2, 'fetchAbortTimeout': 500}
        self.add_zh_lang_map = {'zh': ['az', 'en', 'es', 'fr', 'it', 'ru']}
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(1e4)  # ten thousand.
        self.default_from_language = self.output_zh

    def get_request_data(self, ss: SessionType, method: str, params: dict, timeout: Optional[float]) -> dict:
        url = f'{self.api_url}/{method}'
        params = {**{'srv': self.srv}, **params}
        r = ss.post(url=url, params=params, data=self.api_payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data

    async def get_request_data_async(self, ss: AsyncSessionType, method: str, params: dict,
                                     timeout: Optional[float]) -> dict:
        url = f'{self.api_url}/{method}'
        params = {**{'srv': self.srv}, **params}
        r = await ss.post(url=url, params=params, data=self.api_payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = await r.json()
        return data

    @Tse.debug_language_map
    def get_language_map(self, ss: SessionType, timeout: Optional[float], **kwargs: LangMapKwargsType) -> dict:
        lang_map = {}
        lang_data = self.get_request_data(ss=ss, method='getLangs', params={}, timeout=timeout)
        for k, v in [lang_pair.split('-') for lang_pair in lang_data['dirs']]:
            lang_map.setdefault(k, []).append(v)
        return lang_map

    @Tse.debug_language_map_async
    async def get_language_map_async(self, ss: AsyncSessionType, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        lang_map = {}
        lang_data = await self.get_request_data_async(ss=ss, method='getLangs', params={}, timeout=timeout)
        for k, v in [lang_pair.split('-') for lang_pair in lang_data['dirs']]:
            lang_map.setdefault(k, []).append(v)
        return lang_map

    @Tse.time_stat
    @Tse.check_query
    def yandex_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                   **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://browser.translate.yandex.net
        :param query_text: str, must.
        :param from_language: str, default 'auto'.
        :param to_language: str, default 'en'.
        :param **kwargs:
                :param timeout: Optional[float], default None.
                :param proxies: Optional[dict], default None.
                :param sleep_seconds: float, default 0.
                :param is_detail_result: bool, default False.
                :param http_client: str, default 'requests'. Union['requests', 'niquests', 'httpx', 'cloudscraper']
                :param if_ignore_limit_of_length: bool, default False.
                :param limit_of_length: int, default 20000.
                :param if_ignore_empty_query: bool, default False.
                :param update_session_after_freq: int, default 1000.
                :param update_session_after_seconds: float, default 1500.
                :param if_show_time_stat: bool, default False.
                :param show_time_stat_precision: int, default 2.
                :param if_print_warning: bool, default True.
        :return: str or dict
        """

        timeout = kwargs.get('timeout', None)
        proxies = kwargs.get('proxies', None)
        sleep_seconds = kwargs.get('sleep_seconds', 0)
        http_client = kwargs.get('http_client', 'requests')
        if_print_warning = kwargs.get('if_print_warning', True)
        is_detail_result = kwargs.get('is_detail_result', False)
        update_session_after_freq = kwargs.get('update_session_after_freq', self.default_session_freq)
        update_session_after_seconds = kwargs.get('update_session_after_seconds', self.default_session_seconds)
        self.check_input_limit(query_text, self.input_limit)

        not_update_cond_freq = 1 if self.query_count % update_session_after_freq != 0 else 0
        not_update_cond_time = 1 if time.time() - self.begin_time < update_session_after_seconds else 0
        if not (self.session and self.language_map and not_update_cond_freq and not_update_cond_time):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(ss=self.session, timeout=timeout, **debug_lang_kwargs)
            if not self.language_map.get('zh'):
                self.language_map.update(self.add_zh_lang_map)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)
        if from_language == 'auto':
            from_language = \
                self.get_request_data(ss=self.session, method='detect', params={'text': query_text}, timeout=timeout)[
                    'lang']
            if not from_language:
                from_language = self.warning_auto_lang('yandex', self.default_from_language, if_print_warning)

        params = {'text': query_text, 'lang': f'{from_language}-{to_language}'}
        data = self.get_request_data(ss=self.session, method='translate', params=params, timeout=timeout)
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['text'][0]

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://browser.translate.yandex.net
        :param query_text: str, must.
        :param from_language: str, default 'auto'.
        :param to_language: str, default 'en'.
        :param **kwargs:
                :param timeout: Optional[float], default None.
                :param proxies: Optional[dict], default None.
                :param sleep_seconds: float, default 0.
                :param is_detail_result: bool, default False.
                :param http_client: str, default 'requests'. Union['requests', 'niquests', 'httpx', 'cloudscraper']
                :param if_ignore_limit_of_length: bool, default False.
                :param limit_of_length: int, default 20000.
                :param if_ignore_empty_query: bool, default False.
                :param update_session_after_freq: int, default 1000.
                :param update_session_after_seconds: float, default 1500.
                :param if_show_time_stat: bool, default False.
                :param show_time_stat_precision: int, default 2.
                :param if_print_warning: bool, default True.
        :return: str or dict
        """
        timeout = kwargs.get('timeout', None)
        proxies = kwargs.get('proxies', None)
        sleep_seconds = kwargs.get('sleep_seconds', 0)
        http_client = kwargs.get('http_client', 'niquests')
        if_print_warning = kwargs.get('if_print_warning', True)
        is_detail_result = kwargs.get('is_detail_result', False)
        update_session_after_freq = kwargs.get('update_session_after_freq', self.default_session_freq)
        update_session_after_seconds = kwargs.get('update_session_after_seconds', self.default_session_seconds)
        self.check_input_limit(query_text, self.input_limit)

        not_update_cond_freq = 1 if self.query_count % update_session_after_freq != 0 else 0
        not_update_cond_time = 1 if time.time() - self.begin_time < update_session_after_seconds else 0
        if not (self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(proxies)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(ss=self.async_session, timeout=timeout,
                                                                  **debug_lang_kwargs)
            if not self.language_map.get('zh'):
                self.language_map.update(self.add_zh_lang_map)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        if from_language == 'auto':
            from_language = (
                await self.get_request_data_async(ss=self.async_session, method='detect', params={'text': query_text},
                                                  timeout=timeout))[
                'lang']
            if not from_language:
                from_language = self.warning_auto_lang('yandex', self.default_from_language, if_print_warning)

        params = {'text': query_text, 'lang': f'{from_language}-{to_language}'}
        data = await self.get_request_data_async(ss=self.async_session, method='translate', params=params,
                                                 timeout=timeout)
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['text'][0]
