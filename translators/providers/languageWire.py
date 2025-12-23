import asyncio
import time
from typing import Optional, Union

from translators.base import Tse, LangMapKwargsType, ApiKwargsType, AsyncSessionType, SessionType


class LanguageWire(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.home_url = 'https://jwt.languagewire.com'
        self.host_url = 'https://www.languagewire.com/en/technology/languagewire-translate'
        self.api_url = 'https://lwt.languagewire.com/f/api/v1/translations/text'
        self.lang_url = 'https://lwt.languagewire.com/f/api/v1/language-pairs?includeVariants=true'
        self.cookie_url = 'https://lwt.languagewire.com/f/api/v1/auth/cookie'
        self.lwt_js_url = 'https://lwt.languagewire.com/en/main.6f20295b104bc52a.js'
        self.host_headers = self.get_headers(self.home_url, if_api=False, if_referer_for_host=True)
        self.api_headers = self.get_headers(self.home_url, if_api=True, if_json_for_api=True)
        self.session = None
        self.language_map = None
        self.lwt_data = None
        self.query_count = 0
        self.output_zh = None  # unsupported
        self.input_limit = int(5e3)
        self.default_from_language = 'fr'
        self.default_en_to_language = 'en-US'

    @Tse.debug_language_map
    def get_language_map(self, lang_url: str, ss: SessionType, headers: dict, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        d_lang_map = ss.get(lang_url, headers=headers, timeout=timeout).json()
        return {ii['sourceLanguage']['mmtCode']: [jj['targetLanguage']['mmtCode'] for jj in d_lang_map if
                                                  jj['sourceLanguage']['mmtCode'] == ii['sourceLanguage']['mmtCode']]
                for ii in d_lang_map}

    @Tse.debug_language_map_async
    async def get_language_map_async(self, lang_url: str, ss: AsyncSessionType, headers: dict, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        d_lang_map = (await ss.get(lang_url, headers=headers, timeout=timeout)).json()
        return {ii['sourceLanguage']['mmtCode']: [jj['targetLanguage']['mmtCode'] for jj in d_lang_map if
                                                  jj['sourceLanguage']['mmtCode'] == ii['sourceLanguage']['mmtCode']]
                for ii in d_lang_map}

    # def get_lwt_data(self, lwt_js_url: str, ss: SessionType, headers: dict, timeout: Optional[float]) -> dict:
    #     js_html = ss.get(lwt_js_url, headers=headers, timeout=timeout).text
    #     lwt_data = {
    #         'x-lwt-application-id': re.compile('"X-LWT-Application-ID":"(.*?)"').search(js_html).group(1),
    #         'x-lwt-build-id': re.compile('"X-LWT-Build-ID":"(.*?)"').search(js_html).group(1),
    #     }
    #     return lwt_data

    def get_lwt_data(self) -> dict:
        lwt_data = {
            'x-lwt-application-id': 'LWT_WEB',
            'x-lwt-build-id': '346775',
        }
        return lwt_data

    @Tse.time_stat
    @Tse.check_query
    def languageWire_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                         **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.languagewire.com/en/technology/languagewire-translate
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
            self.lwt_data = self.get_lwt_data()
            self.api_headers.update(self.lwt_data)

            _ = self.session.post(self.cookie_url, headers=self.api_headers, timeout=timeout)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.lang_url, self.session, self.api_headers, timeout,
                                                      **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('languageWire', self.default_from_language, if_print_warning)
        to_language = self.default_en_to_language if to_language == 'en' else to_language
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         if_check_lang_reverse=False)

        payload = {
            'sourceText': query_text,
            'sourceLanguage': from_language,
            'targetLanguage': to_language,
        }
        r = self.session.post(self.api_url, json=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['translation']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.languagewire.com/en/technology/languagewire-translate
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
            self.lwt_data = self.get_lwt_data()
            self.api_headers.update(self.lwt_data)

            _ = await self.async_session.post(self.cookie_url, headers=self.api_headers, timeout=timeout)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(self.lang_url, self.async_session, self.api_headers,
                                                                  timeout,
                                                                  **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('languageWire', self.default_from_language, if_print_warning)
        to_language = self.default_en_to_language if to_language == 'en' else to_language
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         if_check_lang_reverse=False)

        payload = {
            'sourceText': query_text,
            'sourceLanguage': from_language,
            'targetLanguage': to_language,
        }
        r = await self.async_session.post(self.api_url, json=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['translation']
