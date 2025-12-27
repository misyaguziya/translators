import asyncio
import re
import time
import urllib.parse
from typing import Optional, Union

from translators.base import Tse, LangMapKwargsType, TranslatorError, ApiKwargsType, AsyncSessionType, SessionType


class LingvanexV1(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://lingvanex.com/translate/'
        self.api_url = None
        self.language_url = None
        self.auth_url = 'https://lingvanex.com/translate/js/api-base.js'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_json_for_api=False)
        self.session = None
        self.language_map = None
        self.detail_language_map = None
        self.auth_info = None
        self.mode = None
        self.model_pool = ('B2B', 'B2C',)
        self.query_count = 0
        self.output_zh = 'zh-Hans_CN'
        self.input_limit = int(1e4)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, lang_url: str, ss: SessionType, headers: dict, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        params = {'all': 'true', 'code': 'en_GB', 'platform': 'dp', '_': self.get_timestamp()}
        detail_lang_map = ss.get(lang_url, params=params, headers=headers, timeout=timeout).json()
        for _ in range(3):
            _ = ss.get(lang_url, params={'platform': 'dp'}, headers=headers, timeout=timeout)
        lang_list = sorted(set([item['full_code'] for item in detail_lang_map['result']]))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, lang_url: str, ss: AsyncSessionType, headers: dict, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        params = {'all': 'true', 'code': 'en_GB', 'platform': 'dp', '_': self.get_timestamp()}
        detail_lang_map = await (await ss.get(lang_url, params=params, headers=headers, timeout=timeout)).json()
        for _ in range(3):
            _ = ss.get(lang_url, params={'platform': 'dp'}, headers=headers, timeout=timeout)
        lang_list = sorted(set([item['full_code'] for item in detail_lang_map['result']]))
        return {}.fromkeys(lang_list, lang_list)

    def get_d_lang_map(self, lang_url: str, ss: SessionType, headers: dict, timeout: Optional[float]) -> dict:
        params = {'all': 'true', 'code': 'en_GB', 'platform': 'dp', '_': self.get_timestamp()}
        return ss.get(lang_url, params=params, headers=headers, timeout=timeout).json()

    async def get_d_lang_map_async(self, lang_url: str, ss: AsyncSessionType, headers: dict,
                                   timeout: Optional[float]) -> dict:
        params = {'all': 'true', 'code': 'en_GB', 'platform': 'dp', '_': self.get_timestamp()}
        return await (await ss.get(lang_url, params=params, headers=headers, timeout=timeout)).json()

    def get_auth(self, auth_url: str, ss: SessionType, headers: dict, timeout: Optional[float]) -> dict:
        js_html = ss.get(auth_url, headers=headers, timeout=timeout).text
        return {k: v for k, v in re.compile(',(.*?)="(.*?)"').findall(js_html)}

    async def get_auth_async(self, auth_url: str, ss: AsyncSessionType, headers: dict,
                             timeout: Optional[float]) -> dict:
        js_html = await(await ss.get(auth_url, headers=headers, timeout=timeout)).text()
        return {k: v for k, v in re.compile(',(.*?)="(.*?)"').findall(js_html)}

    @Tse.time_stat
    @Tse.check_query
    def lingvanex_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                      **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://lingvanex.com/translate/
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
                :param lingvanex_mode: str, default "B2C", choose from ("B2B", "B2C").
        :return: str or dict
        """

        mode = kwargs.get('lingvanex_mode', 'B2C')
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
                self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.auth_info and self.mode == mode):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            _ = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            self.auth_info = self.get_auth(self.auth_url, self.session, self.host_headers, timeout)

            if mode not in self.model_pool:
                raise TranslatorError

            if mode != self.mode:
                self.mode = mode
                self.api_url = ''.join([self.auth_info[f'{mode}_BASE_URL'], self.auth_info['TRANSLATE_URL']])
                self.language_url = ''.join([self.auth_info[f'{mode}_BASE_URL'], self.auth_info['GET_LANGUAGES_URL']])
                self.host_headers.update({'authorization': self.auth_info[f'{mode}_AUTH_TOKEN']})
                self.api_headers.update({'authorization': self.auth_info[f'{mode}_AUTH_TOKEN']})
                self.api_headers.update({'referer': urllib.parse.urlparse(self.auth_info[f'{mode}_BASE_URL']).netloc})

            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.language_url, self.session, self.host_headers, timeout,
                                                      **debug_lang_kwargs)
            self.detail_language_map = self.get_d_lang_map(self.language_url, self.session, self.host_headers, timeout)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('lingvanex', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='lingvanex', output_en='en_GB')

        payload = {
            'from': from_language,
            'to': to_language,
            'text': query_text,
            'platform': 'dp',
            # 'is_return_text_split_ranges': 'true'
        }
        payload = urllib.parse.urlencode(payload)
        r = self.session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['result']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://lingvanex.com/translate/
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
                :param lingvanex_mode: str, default "B2C", choose from ("B2B", "B2C").
        :return: str or dict
        """

        mode = kwargs.get('lingvanex_mode', 'B2C')
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
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.auth_info and self.mode == mode):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(proxies)
            _ = await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            self.auth_info = await self.get_auth_async(self.auth_url, self.async_session, self.host_headers, timeout)

            if mode not in self.model_pool:
                raise TranslatorError

            if mode != self.mode:
                self.mode = mode
                self.api_url = ''.join([self.auth_info[f'{mode}_BASE_URL'], self.auth_info['TRANSLATE_URL']])
                self.language_url = ''.join([self.auth_info[f'{mode}_BASE_URL'], self.auth_info['GET_LANGUAGES_URL']])
                self.host_headers.update({'authorization': self.auth_info[f'{mode}_AUTH_TOKEN']})
                self.api_headers.update({'authorization': self.auth_info[f'{mode}_AUTH_TOKEN']})
                self.api_headers.update({'referer': urllib.parse.urlparse(self.auth_info[f'{mode}_BASE_URL']).netloc})

            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(self.language_url, self.async_session,
                                                                  self.host_headers, timeout,
                                                                  **debug_lang_kwargs)
            self.detail_language_map = await self.get_d_lang_map_async(self.language_url, self.async_session,
                                                                       self.host_headers, timeout)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('lingvanex', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='lingvanex', output_en='en_GB')

        payload = {
            'from': from_language,
            'to': to_language,
            'text': query_text,
            'platform': 'dp',
            # 'is_return_text_split_ranges': 'true'
        }
        payload = urllib.parse.urlencode(payload)
        r = await self.async_session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = await  r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['result']


class LingvanexV2(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://lingvanex.com/en/translate/'
        self.api_url = 'https://api-b2b.backenster.com/b1/api/v3/translate/?client=site&feature=seo_text&lang_pair=en_te'
        self.language_url = 'https://api-b2b.backenster.com/b1/api/v3/getLanguages?platform=dp'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_json_for_api=False)
        self.session = None
        self.language_map = None
        self.detail_language_map = None
        self.auth = None
        self.query_count = 0
        self.output_zh = 'zh-Hans_CN'
        self.input_limit = int(1e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, lang_url: str, ss: SessionType, headers: dict, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        self.detail_language_map = ss.get(lang_url, headers=headers, timeout=timeout).json()
        lang_list = sorted(set([item['full_code'] for item in self.detail_language_map['result']]))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, lang_url: str, ss: AsyncSessionType, headers: dict, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        self.detail_language_map = await (await ss.get(lang_url, headers=headers, timeout=timeout)).json()
        lang_list = sorted(set([item['full_code'] for item in self.detail_language_map['result']]))
        return {}.fromkeys(lang_list, lang_list)

    def get_auth(self, host_html: str) -> str:
        return re.compile('const API_BEARER_TOKEN = "(.*?)"').findall(host_html)[0]

    @Tse.time_stat
    @Tse.check_query
    def lingvanex_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                      **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://lingvanex.com/en/translate/
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
        if not (self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.auth):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            self.auth = self.get_auth(host_html)
            self.host_headers.update({'authorization': self.auth})
            self.api_headers.update({'authorization': self.auth})
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.language_url, self.session, self.host_headers, timeout,
                                                      **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('lingvanex', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='lingvanex', output_en='en_GB')

        payload = {
            'from': from_language,
            'to': to_language,
            'text': query_text,
            'platform': 'dp',
        }
        payload = urllib.parse.urlencode(payload)
        r = self.session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['result']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://lingvanex.com/en/translate/
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
        if not (
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.auth):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(proxies)
            host_html = await(await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text()
            self.auth = self.get_auth(host_html)
            self.host_headers.update({'authorization': self.auth})
            self.api_headers.update({'authorization': self.auth})
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(self.language_url, self.async_session,
                                                                  self.host_headers, timeout,
                                                                  **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('lingvanex', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='lingvanex', output_en='en_GB')

        payload = {
            'from': from_language,
            'to': to_language,
            'text': query_text,
            'platform': 'dp',
        }
        payload = urllib.parse.urlencode(payload)
        r = await self.async_session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = await r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['result']
