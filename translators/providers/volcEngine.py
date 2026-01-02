import asyncio
import re
import time
from typing import Union

from translators.base import Tse, LangMapKwargsType, TranslatorError, ApiKwargsType


class VolcEngine(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://translate.volcengine.com'
        self.api_url = 'https://translate.volcengine.com/web/translate/v1'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_json_for_api=True)
        self.session = None
        self.language_map = None
        self.ms_token = ''
        self.x_bogus = 'DFS#todo'
        self.signature = '_02B#todo'
        self.query_count = 0
        self.output_auto = 'detect'
        self.output_zh = 'zh'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, host_html: str, **kwargs: LangMapKwargsType) -> dict:
        lang_list = re.compile('"language_(.*?)":').findall(host_html)
        lang_list = sorted(list(set(lang_list)))
        return {}.fromkeys(lang_list, lang_list)

    @property
    def professional_field_map(self) -> dict:
        data = {
            '': {'category': '', 'glossary_list': []},
            'clean': {'category': 'clean', 'glossary_list': []},
            'novel': {'category': 'novel', 'glossary_list': []},
            'finance': {'category': 'finance', 'glossary_list': []},
            'biomedical': {'category': 'biomedical', 'glossary_list': []},

            'ai': {'category': '', 'glossary_list': ['ailab/ai']},
            'menu': {'category': '', 'glossary_list': ['ailab/menu']},
            'techfirm': {'category': '', 'glossary_list': ['ailab/techfirm']},

            'ecommerce': {'category': 'ecommerce', 'glossary_list': ['ailab/ecommerce']},
            'technique': {'category': 'technique', 'glossary_list': ['ailab/technique']},
        }
        return data

    @Tse.uncertified
    @Tse.time_stat
    @Tse.check_query
    def volcEngine_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                       **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translate.volcengine.com
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
                :param professional_field: str, default '', choose from ('', 'clean')
        :return: str or dict
        """

        use_domain = kwargs.get('professional_field', '')
        if use_domain not in self.professional_field_map:
            raise TranslatorError

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
            self.language_map = self.get_language_map(host_html, **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_auto=self.output_auto, output_zh=self.output_zh)
        params = {
            'msToken': self.ms_token,
            'X-Bogus': self.x_bogus,
            '_signature': self.signature,
        }
        payload = {
            'text': query_text,
            'source_language': from_language,
            'target_language': to_language,
            'home_language': 'zh',
            'enable_user_glossary': 'false',
        }
        payload.update(self.professional_field_map[use_domain])
        r = self.session.post(self.api_url, params=params, json=payload, headers=self.api_headers, timeout=timeout)
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
        https://translate.volcengine.com
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
                :param professional_field: str, default '', choose from ('', 'clean')
        :return: str or dict
        """

        use_domain = kwargs.get('professional_field', '')
        if use_domain not in self.professional_field_map:
            raise TranslatorError

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
            host_html = await (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text()
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_auto=self.output_auto, output_zh=self.output_zh)
        params = {
            'msToken': self.ms_token,
            'X-Bogus': self.x_bogus,
            '_signature': self.signature,
        }
        payload = {
            'text': query_text,
            'source_language': from_language,
            'target_language': to_language,
            'home_language': 'zh',
            'enable_user_glossary': 'false',
        }
        payload.update(self.professional_field_map[use_domain])
        r = await self.async_session.post(self.api_url, params=params, json=payload, headers=self.api_headers,
                                          timeout=timeout)
        r.raise_for_status()
        data = await r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['translation']
