import asyncio
import time
from typing import Union

from translators.base import Tse, LangMapKwargsType, ApiKwargsType


class TranslateCom(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://www.translate.com/machine-translation'
        self.api_url = 'https://www.translate.com/translator/translate_mt'
        self.lang_detect_url = 'https://www.translate.com/translator/ajax_lang_auto_detect'
        self.language_url = 'https://www.translate.com/ajax/language/ht/all'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_json_for_api=False)
        self.session = None
        self.language_map = None
        self.language_description = None
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(1.5e4)  # fifteen thousand letters left today.
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, lang_desc: dict, **kwargs: LangMapKwargsType) -> dict:
        return {item['code']: [it['code'] for it in item['availableTranslationLanguages']] for item in lang_desc}

    @Tse.time_stat
    @Tse.check_query
    def translateCom_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                         **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.translate.com/machine-translation
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
            lang_r = self.session.get(self.language_url, headers=self.host_headers, timeout=timeout)
            self.language_description = lang_r.json()
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.language_description, **debug_lang_kwargs)

        if from_language == 'auto':
            detect_form = {'text_to_translate': query_text}
            r_detect = self.session.post(self.lang_detect_url, data=detect_form, headers=self.api_headers,
                                         timeout=timeout)
            from_language = r_detect.json()['language']

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = {
            'text_to_translate': query_text,
            'source_lang': from_language,
            'translated_lang': to_language,
            'use_cache_only': 'false',
        }
        r = self.session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['translated_text']  # translation_source is microsoft, wtf!

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.translate.com/machine-translation
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
            _ = (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout))
            lang_r = await self.async_session.get(self.language_url, headers=self.host_headers, timeout=timeout)
            self.language_description = lang_r.json()
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.language_description, **debug_lang_kwargs)

        if from_language == 'auto':
            detect_form = {'text_to_translate': query_text}
            r_detect = await self.async_session.post(self.lang_detect_url, data=detect_form, headers=self.api_headers,
                                                     timeout=timeout)
            from_language = (r_detect.json())['language']

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = {
            'text_to_translate': query_text,
            'source_lang': from_language,
            'translated_lang': to_language,
            'use_cache_only': 'false',
        }
        r = await self.async_session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['translated_text']
