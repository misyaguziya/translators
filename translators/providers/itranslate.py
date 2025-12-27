import asyncio
import re
import time
from typing import Union

import exejs

from translators.base import Tse, LangMapKwargsType, ApiKwargsType


class Itranslate(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://itranslate.com/translate'
        self.api_url = 'https://web-api.itranslateapp.com/v3/texts/translate'
        self.manifest_url = 'https://itranslate-webapp-production.web.app/manifest.json'
        self.language_url = None
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_json_for_api=True)
        self.session = None
        self.language_map = None
        self.api_key = None
        self.query_count = 0
        self.output_zh = 'zh-CN'
        self.input_limit = int(1e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, lang_html: str, **kwargs: LangMapKwargsType) -> dict:
        lang_str = re.compile('\\[{dialect:"auto",(.*?)}]').search(lang_html).group()
        lang_origin_list = exejs.evaluate(lang_str)
        lang_list = sorted(list(set([dd['dialect'] for dd in lang_origin_list])))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map
    async def get_language_map_async(self, lang_html: str, **kwargs: LangMapKwargsType) -> dict:
        lang_str = re.compile('\\[{dialect:"auto",(.*?)}]').search(lang_html).group()
        lang_origin_list = await exejs.evaluate_async(lang_str)
        lang_list = sorted(list(set([dd['dialect'] for dd in lang_origin_list])))
        return {}.fromkeys(lang_list, lang_list)

    def get_apikey(self, lang_html: str) -> str:
        return re.compile('"API-KEY":"(.*?)"').findall(lang_html)[0]

    @Tse.time_stat
    @Tse.check_query
    def itranslate_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                       **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://itranslate.com/translate
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

            if not self.language_url:
                manifest_data = self.session.get(self.manifest_url, headers=self.host_headers, timeout=timeout).json()
                self.language_url = manifest_data.get('main.js')

            lang_html = self.session.get(self.language_url, headers=self.host_headers, timeout=timeout).text
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(lang_html, **debug_lang_kwargs)

            self.api_key = self.get_apikey(lang_html)
            self.api_headers.update({'API-KEY': self.api_key})

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='itranslate', output_en='en-US')

        payload = {
            'source': {'dialect': from_language, 'text': query_text, 'with': ['synonyms']},
            'target': {'dialect': to_language},
        }
        r = self.session.post(self.api_url, headers=self.api_headers, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['target']['text']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://itranslate.com/translate
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
            _ = await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)

            if not self.language_url:
                manifest_data = await (
                    await self.async_session.get(self.manifest_url, headers=self.host_headers, timeout=timeout)).json()
                self.language_url = manifest_data.get('main.js')

            lang_html = await (
                await self.async_session.get(self.language_url, headers=self.host_headers, timeout=timeout)).text()
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(lang_html, **debug_lang_kwargs)

            self.api_key = self.get_apikey(lang_html)
            self.api_headers.update({'API-KEY': self.api_key})

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='itranslate', output_en='en-US')

        payload = {
            'source': {'dialect': from_language, 'text': query_text, 'with': ['synonyms']},
            'target': {'dialect': to_language},
        }
        r = await self.async_session.post(self.api_url, headers=self.api_headers, json=payload, timeout=timeout)
        r.raise_for_status()
        data = await r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['target']['text']
