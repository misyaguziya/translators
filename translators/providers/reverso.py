import asyncio
import re
import time
from typing import Union

import exejs

from translators.base import Tse, LangMapKwargsType, ApiKwargsType


class Reverso(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://www.reverso.net/text-translation'
        self.api_url = 'https://api.reverso.net/translate/v1/translation'
        self.language_url = 'https://cdn.reverso.net/trans/v2.22.8/main.js'
        # self.language_pattern = 'https://cdn.reverso.net/trans/v(\\d+).(\\d+).(\\d+)/main.js'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_json_for_api=True)
        self.session = None
        self.language_map = None
        self.decrypt_language_map = None
        self.query_count = 0
        self.output_zh = 'zh'  # 'chi', because there are self.language_tran
        self.input_limit = int(2e3)
        self.default_from_language = self.output_zh
        self.scraper = None

    @Tse.debug_language_map
    def get_language_map(self, lang_html: str, **kwargs: LangMapKwargsType) -> dict:
        lang_dict_str = re.compile('={eng:(.*?)}').search(lang_html).group()[1:]
        lang_dict = exejs.evaluate(lang_dict_str)
        lang_list = sorted(list(lang_dict.values()))
        return {}.fromkeys(lang_list, lang_list)

    def decrypt_lang_map(self, lang_html: str) -> dict:
        lang_dict_str = re.compile('={eng:(.*?)}').search(lang_html).group()[1:]
        lang_dict = exejs.evaluate(lang_dict_str)
        return {k: v for v, k in lang_dict.items()}

    @Tse.time_stat
    @Tse.check_query
    def reverso_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                    **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.reverso.net/text-translation
        :param query_text: str, must.
        :param from_language: str, default 'zh', unsupported 'auto'.
        :param to_language: str, default 'en'.
        :param **kwargs:
                :param timeout: Optional[float], default None.
                :param proxies: Optional[dict], default None.
                :param sleep_seconds: float, default 0.
                :param is_detail_result: bool, default False.
                :param http_client: str, default 'cloudscraper'. Union['requests', 'niquests', 'httpx', 'cloudscraper']
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
        http_client = kwargs.get('http_client', 'cloudscraper')  #
        if_print_warning = kwargs.get('if_print_warning', True)
        is_detail_result = kwargs.get('is_detail_result', False)
        update_session_after_freq = kwargs.get('update_session_after_freq', self.default_session_freq)
        update_session_after_seconds = kwargs.get('update_session_after_seconds', self.default_session_seconds)
        self.check_input_limit(query_text, self.input_limit)

        not_update_cond_freq = 1 if self.query_count % update_session_after_freq != 0 else 0
        not_update_cond_time = 1 if time.time() - self.begin_time < update_session_after_seconds else 0
        if not (
                self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.decrypt_language_map):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            _ = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout)

            # self.language_url = re.compile(self.language_pattern).search(host_html).group()
            lang_html = self.session.get(self.language_url, headers=self.host_headers, timeout=timeout).text
            self.decrypt_language_map = self.decrypt_lang_map(lang_html)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(lang_html, **debug_lang_kwargs)
            self.api_headers.update({'X-Reverso-Origin': 'translation.web'})

        if from_language == 'auto':
            from_language = self.warning_auto_lang('reverso', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)
        from_language, to_language = self.decrypt_language_map[from_language], self.decrypt_language_map[to_language]

        payload = {
            'format': 'text',
            'from': from_language,
            'to': to_language,
            'input': query_text,
            'options': {
                'contextResults': 'true',
                'languageDetection': 'true',
                'sentenceSplitter': 'true',
                'origin': 'translation.web',
            }
        }
        r = self.session.post(self.api_url, json=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else ''.join(data['translation'])

    @Tse.time_stat
    @Tse.check_query
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.reverso.net/text-translation
        :param query_text: str, must.
        :param from_language: str, default 'zh', unsupported 'auto'.
        :param to_language: str, default 'en'.
        :param **kwargs:
                :param timeout: Optional[float], default None.
                :param proxies: Optional[dict], default None.
                :param sleep_seconds: float, default 0.
                :param is_detail_result: bool, default False.
                :param http_client: str, default 'cloudscraper'. Union['requests', 'niquests', 'httpx', 'cloudscraper']
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
        http_client = kwargs.get('http_client', 'httpx')  #
        if_print_warning = kwargs.get('if_print_warning', True)
        is_detail_result = kwargs.get('is_detail_result', False)
        update_session_after_freq = kwargs.get('update_session_after_freq', self.default_session_freq)
        update_session_after_seconds = kwargs.get('update_session_after_seconds', self.default_session_seconds)
        self.check_input_limit(query_text, self.input_limit)

        not_update_cond_freq = 1 if self.query_count % update_session_after_freq != 0 else 0
        not_update_cond_time = 1 if time.time() - self.begin_time < update_session_after_seconds else 0
        if not (
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.decrypt_language_map):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(http_client, proxies)
            _ = await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)

            # self.language_url = re.compile(self.language_pattern).search(host_html).group()
            lang_html = (
                await self.async_session.get(self.language_url, headers=self.host_headers, timeout=timeout)).text
            self.decrypt_language_map = self.decrypt_lang_map(lang_html)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(lang_html, **debug_lang_kwargs)
            self.api_headers.update({'X-Reverso-Origin': 'translation.web'})

        if from_language == 'auto':
            from_language = self.warning_auto_lang('reverso', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)
        from_language, to_language = self.decrypt_language_map[from_language], self.decrypt_language_map[to_language]

        payload = {
            'format': 'text',
            'from': from_language,
            'to': to_language,
            'input': query_text,
            'options': {
                'contextResults': 'true',
                'languageDetection': 'true',
                'sentenceSplitter': 'true',
                'origin': 'translation.web',
            }
        }
        r = await self.async_session.post(self.api_url, json=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else ''.join(data['translation'])
