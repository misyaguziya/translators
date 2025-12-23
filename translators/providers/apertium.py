import asyncio
import re
import time
import urllib.parse
from typing import Optional, Union

from translators.base import Tse, LangMapKwargsType, ApiKwargsType, AsyncSessionType, SessionType


class Apertium(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://www.apertium.org/'
        self.api_url = 'https://apertium.org/apy/translate'
        self.get_lang_url = 'https://www.apertium.org/index.js'
        self.detect_lang_url = 'https://apertium.org/apy/identifyLang'
        self.host_headers = self.get_headers(self.host_url, if_api=False, if_referer_for_host=True)
        self.api_headers = self.get_headers(self.host_url, if_api=True)
        self.session = None
        self.language_map = None
        self.query_count = 0
        self.output_zh = None  # unsupported
        self.output_en = 'eng'
        self.input_limit = int(1e4)  # almost no limit.
        self.default_from_language = 'spa'

    @Tse.debug_language_map
    def get_language_map(self, lang_url: str, ss: SessionType, headers: dict, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        js_html = ss.get(lang_url, headers=headers, timeout=timeout).text
        lang_pairs = re.compile('{sourceLanguage:"(.*?)",targetLanguage:"(.*?)"}').findall(js_html)
        return {f_lang: [v for k, v in lang_pairs if k == f_lang] for f_lang, t_lang in lang_pairs}

    @Tse.debug_language_map_async
    async def get_language_map_async(self, lang_url: str, ss: AsyncSessionType, headers: dict, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        js_html = (await ss.get(lang_url, headers=headers, timeout=timeout)).text
        lang_pairs = re.compile('{sourceLanguage:"(.*?)",targetLanguage:"(.*?)"}').findall(js_html)
        return {f_lang: [v for k, v in lang_pairs if k == f_lang] for f_lang, t_lang in lang_pairs}

    @Tse.time_stat
    @Tse.check_query
    def apertium_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                     **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.apertium.org/
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
            self.language_map = self.get_language_map(self.get_lang_url, self.session, self.host_headers, timeout,
                                                      **debug_lang_kwargs)

        if from_language == 'auto':
            payload = urllib.parse.urlencode({'q': query_text})
            langs = self.session.post(self.detect_lang_url, data=payload, headers=self.api_headers,
                                      timeout=timeout).json()
            from_language = sorted(langs, key=lambda k: langs[k], reverse=True)[0]
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_en_translator='apertium', output_en=self.output_en)

        payload = {
            'q': query_text,
            'langpair': f'{from_language}|{to_language}',
            'prefs': '',
            'markUnknown': 'no',
        }
        payload = urllib.parse.urlencode(payload)
        r = self.session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['responseData']['translatedText']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.apertium.org/
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
            self.language_map = await self.get_language_map_async(self.get_lang_url, self.async_session,
                                                                  self.host_headers, timeout,
                                                                  **debug_lang_kwargs)

        if from_language == 'auto':
            payload = urllib.parse.urlencode({'q': query_text})
            langs = (await self.async_session.post(self.detect_lang_url, data=payload, headers=self.api_headers,
                                                   timeout=timeout)).json()
            from_language = sorted(langs, key=lambda k: langs[k], reverse=True)[0]
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_en_translator='apertium', output_en=self.output_en)

        payload = {
            'q': query_text,
            'langpair': f'{from_language}|{to_language}',
            'prefs': '',
            'markUnknown': 'no',
        }
        payload = urllib.parse.urlencode(payload)
        r = await self.async_session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['responseData']['translatedText']
