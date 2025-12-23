import asyncio
import json
import re
import time
import urllib.parse
from typing import Optional, Union

import exejs
import lxml.etree as lxml_etree

from translators.base import Tse, LangMapKwargsType, ApiKwargsType, AsyncSessionType, SessionType


class IflytekV1(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://saas.xfyun.cn/translate?tabKey=text'
        self.api_url = 'https://saas.xfyun.cn/ai-application/trans/its'
        self.language_old_url = 'https://saas.xfyun.cn/_next/static/4bzLSGCWUNl67Xal-AfIl/pages/translate.js'
        self.language_url_pattern = r'/_next/static/(\w+([-]?\w+))/pages/translate.js'
        self.language_url = None
        self.cookies_url = 'https://sso.xfyun.cn//SSOService/login/getcookies'
        self.info_url = 'https://saas.xfyun.cn/ai-application/user/info'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True)
        self.language_map = None
        self.session = None
        self.query_count = 0
        self.output_zh = 'cn'
        self.input_limit = int(2e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, host_html: str, ss: SessionType, headers: dict, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        try:
            if not self.language_url:
                url_path = re.compile(self.language_url_pattern).search(host_html).group()
                self.language_url = f'{self.host_url[:21]}{url_path}'
            r = ss.get(self.language_url, headers=headers, timeout=timeout)
        except:
            r = ss.get(self.language_old_url, headers=headers, timeout=timeout)

        js_html = r.text
        lang_str = re.compile('languageList:\\(e={(.*?)}').search(js_html).group()[16:]
        lang_list = sorted(list(exejs.evaluate(lang_str).keys()))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, host_html: str, ss: AsyncSessionType, headers: dict,
                                     timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        try:
            if not self.language_url:
                url_path = re.compile(self.language_url_pattern).search(host_html).group()
                self.language_url = f'{self.host_url[:21]}{url_path}'
            r = await ss.get(self.language_url, headers=headers, timeout=timeout)
        except:
            r = await ss.get(self.language_old_url, headers=headers, timeout=timeout)

        js_html = r.text
        lang_str = re.compile('languageList:\\(e={(.*?)}').search(js_html).group()[16:]
        lang_list = sorted(list(exejs.evaluate(lang_str).keys()))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.uncertified
    @Tse.time_stat
    @Tse.check_query
    def iflytek_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                    **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://saas.xfyun.cn/translate?tabKey=text
        :param query_text: str, must.
        :param from_language: str, default 'zh', unsupported 'auto'.
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
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            _ = self.session.get(self.cookies_url, headers=self.host_headers, timeout=timeout)
            _ = self.session.get(self.info_url, headers=self.host_headers, timeout=timeout)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, self.session, self.host_headers, timeout,
                                                      **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('iflytek', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        # cipher_query_text = base64.b64encode(query_text.encode()).decode()
        cipher_query_text = query_text
        payload = {'from': from_language, 'to': to_language, 'text': cipher_query_text}
        r = self.session.post(self.api_url, headers=self.api_headers, data=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else json.loads(data['data'])['trans_result']['dst']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://saas.xfyun.cn/translate?tabKey=text
        :param query_text: str, must.
        :param from_language: str, default 'zh', unsupported 'auto'.
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
            self.async_session = Tse.get_async_client_session(http_client, proxies)
            host_html = (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text
            _ = await self.async_session.get(self.cookies_url, headers=self.host_headers, timeout=timeout)
            _ = await self.async_session.get(self.info_url, headers=self.host_headers, timeout=timeout)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(host_html, self.async_session, self.host_headers,
                                                                  timeout,
                                                                  **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('iflytek', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        # cipher_query_text = base64.b64encode(query_text.encode()).decode()
        cipher_query_text = query_text
        payload = {'from': from_language, 'to': to_language, 'text': cipher_query_text}
        r = await self.async_session.post(self.api_url, headers=self.api_headers, data=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else json.loads(data['data'])['trans_result']['dst']


class IflytekV2(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://fanyi.xfyun.cn/console/trans/text'  # https://www.iflyrec.com/html/translate.html
        self.api_url = 'https://fanyi.xfyun.cn/api-tran/trans/its'
        self.detect_language_url = 'https://fanyi.xfyun.cn/api-tran/trans/detection'
        self.language_url_pattern = '/js/trans-text/index.(.*?).js'
        self.language_url = None
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True)
        self.language_map = None
        self.session = None
        self.query_count = 0
        self.output_zh = 'cn'
        self.input_limit = int(2e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, host_html: str, ss: SessionType, headers: dict, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        host_true_url = f'https://{urllib.parse.urlparse(self.host_url).hostname}'

        et = lxml_etree.HTML(host_html)
        host_js_url = f"""{host_true_url}{et.xpath('//script[@type="module"]/@src')[0]}"""
        host_js_html = ss.get(host_js_url, headers=headers, timeout=timeout).text
        self.language_url = f"""{host_true_url}{re.compile(self.language_url_pattern).search(host_js_html).group()}"""

        lang_js_html = ss.get(self.language_url, headers=headers, timeout=timeout).text
        lang_list = re.compile('languageCode:"(.*?)",').findall(lang_js_html)
        lang_list = sorted(list(set(lang_list)))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, host_html: str, ss: AsyncSessionType, headers: dict,
                                     timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        host_true_url = f'https://{urllib.parse.urlparse(self.host_url).hostname}'

        et = lxml_etree.HTML(host_html)
        host_js_url = f"""{host_true_url}{et.xpath('//script[@type="module"]/@src')[0]}"""
        host_js_html = (await ss.get(host_js_url, headers=headers, timeout=timeout)).text
        self.language_url = f"""{host_true_url}{re.compile(self.language_url_pattern).search(host_js_html).group()}"""

        lang_js_html = (await ss.get(self.language_url, headers=headers, timeout=timeout)).text
        lang_list = re.compile('languageCode:"(.*?)",').findall(lang_js_html)
        lang_list = sorted(list(set(lang_list)))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.uncertified
    @Tse.time_stat
    @Tse.check_query
    def iflytek_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                    **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.xfyun.cn/console/trans/text
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
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, self.session, self.host_headers, timeout,
                                                      **debug_lang_kwargs)

        if from_language == 'auto':
            params = {'text': query_text}
            detect_r = self.session.get(self.detect_language_url, params=params, headers=self.host_headers,
                                        timeout=timeout)
            from_language = detect_r.json()[
                'data'] if detect_r.status_code == 200 and detect_r.text.strip() != '' else self.output_zh
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = {'from': from_language, 'to': to_language, 'text': query_text}
        r = self.session.post(self.api_url, headers=self.api_headers, data=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else json.loads(data['data'])['trans_result']['dst']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.xfyun.cn/console/trans/text
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
            self.async_session = Tse.get_async_client_session(http_client, proxies)
            host_html = (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(host_html, self.async_session, self.host_headers,
                                                                  timeout,
                                                                  **debug_lang_kwargs)

        if from_language == 'auto':
            params = {'text': query_text}
            detect_r = await self.async_session.get(self.detect_language_url, params=params, headers=self.host_headers,
                                                    timeout=timeout)
            from_language = detect_r.json()[
                'data'] if detect_r.status_code == 200 and detect_r.text.strip() != '' else self.output_zh
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = {'from': from_language, 'to': to_language, 'text': query_text}
        r = await self.async_session.post(self.api_url, headers=self.api_headers, data=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else json.loads(data['data'])['trans_result']['dst']


class Iflyrec(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://fanyi.iflyrec.com'
        self.api_url = 'https://fanyi.iflyrec.com/TranslationService/v1/textAutoTranslation'
        self.detect_lang_url = 'https://fanyi.iflyrec.com/TranslationService/v1/languageDetection'
        self.language_url = 'https://fanyi.iflyrec.com/TranslationService/v1/textTranslation/languages'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_json_for_api=True)
        self.lang_index = {'zh': 1, 'en': 2, 'ja': 3, 'ko': 4, 'ru': 5, 'fr': 6, 'es': 7, 'vi': 8, 'yue': 9, 'ar': 12,
                           'de': 13, 'it': 14}
        self.lang_index_mirror = {v: k for k, v in self.lang_index.items()}
        self.language_map = None
        self.session = None
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(2e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, lang_index: dict, **kwargs: LangMapKwargsType) -> dict:
        lang_list = sorted(list(lang_index.keys()))
        lang_map = {lang: ['zh'] for lang in lang_list if lang != 'zh'}
        return {**lang_map, **{'zh': lang_list}}

    @Tse.time_stat
    @Tse.check_query
    def iflyrec_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                    **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.iflyrec.com
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
            _ = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.lang_index, **debug_lang_kwargs)

        if from_language == 'auto':
            params = {'t': self.get_timestamp()}
            form = {'originalText': query_text}
            detect_r = self.session.post(self.detect_lang_url, params=params, json=form, headers=self.api_headers,
                                         timeout=timeout)
            from_language_id = detect_r.json()['biz'][0]['detectionLanguage']
            from_language = self.lang_index_mirror[from_language_id]
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        api_params = {'t': self.get_timestamp()}
        api_form = {
            'from': self.lang_index[from_language],
            'to': self.lang_index[to_language],
            'openTerminology': 'false',
            'contents': [{'text': t.strip(), 'frontBlankLine': 0} for t in query_text.split('\n') if t.strip() != ''],
        }
        r = self.session.post(self.api_url, params=api_params, json=api_form, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join([item['translateResult'] for item in data['biz']])

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.iflyrec.com
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
            self.async_session = Tse.get_async_client_session(http_client, proxies)
            _ = await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.lang_index, **debug_lang_kwargs)

        if from_language == 'auto':
            params = {'t': self.get_timestamp()}
            form = {'originalText': query_text}
            detect_r = await self.async_session.post(self.detect_lang_url, params=params, json=form,
                                                     headers=self.api_headers,
                                                     timeout=timeout)
            from_language_id = detect_r.json()['biz'][0]['detectionLanguage']
            from_language = self.lang_index_mirror[from_language_id]
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        api_params = {'t': self.get_timestamp()}
        api_form = {
            'from': self.lang_index[from_language],
            'to': self.lang_index[to_language],
            'openTerminology': 'false',
            'contents': [{'text': t.strip(), 'frontBlankLine': 0} for t in query_text.split('\n') if t.strip() != ''],
        }
        r = await self.async_session.post(self.api_url, params=api_params, json=api_form, headers=self.api_headers,
                                          timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join([item['translateResult'] for item in data['biz']])
