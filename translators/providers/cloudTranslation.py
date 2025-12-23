import asyncio
import json
import time
from typing import Union

from translators.base import Tse, LangMapKwargsType, TranslatorError, ApiKwargsType


class cloudTranslationV1(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.home_url = 'https://www.cloudtranslation.com'
        self.host_url = 'https://www.cloudtranslation.com/#/translate'
        self.api_url = 'https://www.cloudtranslation.com/official-website/v1/transOneSrcText'
        self.get_lang_url = 'https://online.cloudtranslation.com/api/v1.0/site/get_all_language_and_domain'
        self.detect_lang_url = 'https://online.cloudtranslation.com/api/v1.0/request_translate/langid'
        self.get_cookie_url = 'https://online.cloudtranslation.com/api/v1.0/site/sites_language_list'
        self.host_headers = self.get_headers(self.home_url, if_api=False, if_referer_for_host=True)
        self.api_headers = self.get_headers(self.home_url, if_api=True, if_json_for_api=True)
        self.session = None
        self.language_map = None
        self.langpair_domain = None
        self.professional_field = None
        self.query_count = 0
        self.output_zh = 'zh-cn'
        self.output_en = 'en-us'
        self.output_auto = 'all'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, d_lang_map: dict, **kwargs: LangMapKwargsType) -> dict:
        return {k: [it['language_code'] for it in item] for k, item in d_lang_map['data']['src_to_tgt'].items()}

    def get_langpair_domain(self, d_lang_map: dict) -> dict:
        return {k: [it['domain_code'] for it in item] for k, item in
                d_lang_map['data']['language_pair_to_domain'].items()}

    def get_professional_field_list(self, d_lang_map: dict) -> set:
        return {it['domain_code'] for _, item in d_lang_map['data']['language_pair_to_domain'].items() for it in item}

    @Tse.time_stat
    @Tse.check_query
    def cloudTranslation_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                             **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.cloudtranslation.com/#/translate
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
                :param professional_field: str, default 'general'.
        :return: str or dict
        """

        use_domain = kwargs.get('professional_field', 'general')
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
            _ = self.session.get(self.get_cookie_url, headers=self.api_headers, timeout=timeout)
            d_lang_map = self.session.get(self.get_lang_url, headers=self.api_headers, timeout=timeout).json()
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(d_lang_map, **debug_lang_kwargs)
            self.langpair_domain = self.get_langpair_domain(d_lang_map)
            self.professional_field = self.get_professional_field_list(d_lang_map)

        if from_language == 'auto':
            payload = {'text': query_text}
            r = self.session.post(self.detect_lang_url, json=payload, headers=self.api_headers, timeout=timeout)
            from_language = r.json()['data']['language']
        from_language, to_language = from_language.lower(), to_language.lower()  # must lower
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='cloudTranslation',
                                                         output_en=self.output_en)

        domains = self.langpair_domain.get(f'{from_language}_{to_language}')
        if not domains:
            raise TranslatorError

        if use_domain not in domains:
            use_domain = domains[0]

        payload = {
            'text': query_text,
            'domain': use_domain,
            'srcLangCode': from_language,
            'tgtLangCode': to_language,
        }
        r = self.session.post(self.api_url, json=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['data']['translation']

    @Tse.time_stat
    @Tse.check_query
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.cloudtranslation.com/#/translate
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
                :param professional_field: str, default 'general'.
        :return: str or dict
        """

        use_domain = kwargs.get('professional_field', 'general')
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
            _ = await self.async_session.get(self.get_cookie_url, headers=self.api_headers, timeout=timeout)
            d_lang_map = (
                await self.async_session.get(self.get_lang_url, headers=self.api_headers, timeout=timeout)).json()
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(d_lang_map, **debug_lang_kwargs)
            self.langpair_domain = self.get_langpair_domain(d_lang_map)
            self.professional_field = self.get_professional_field_list(d_lang_map)

        if from_language == 'auto':
            payload = {'text': query_text}
            r = await self.async_session.post(self.detect_lang_url, json=payload, headers=self.api_headers,
                                              timeout=timeout)
            from_language = r.json()['data']['language']
        from_language, to_language = from_language.lower(), to_language.lower()  # must lower
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='cloudTranslation',
                                                         output_en=self.output_en)

        domains = self.langpair_domain.get(f'{from_language}_{to_language}')
        if not domains:
            raise TranslatorError

        if use_domain not in domains:
            use_domain = domains[0]

        payload = {
            'text': query_text,
            'domain': use_domain,
            'srcLangCode': from_language,
            'tgtLangCode': to_language,
        }
        r = await self.async_session.post(self.api_url, json=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['data']['translation']


class cloudTranslationV2(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://online.cloudtranslation.com'
        self.api_url = 'https://online.cloudtranslation.com/api/v1.0/request_translate/try_translate'
        self.get_lang_url = 'https://online.cloudtranslation.com/api/v1.0/site/get_all_language_and_domain'
        self.detect_lang_url = 'https://online.cloudtranslation.com/api/v1.0/request_translate/langid'
        self.get_cookie_url = 'https://online.cloudtranslation.com/api/v1.0/site/sites_language_list'
        self.host_headers = self.get_headers(self.host_url, if_api=False, if_referer_for_host=True)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_json_for_api=True)
        self.session = None
        self.language_map = None
        self.langpair_domain = None
        self.professional_field = None
        self.query_count = 0
        self.output_zh = 'zh-cn'
        self.output_en = 'en-us'
        self.output_auto = 'all'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, d_lang_map: dict, **kwargs: LangMapKwargsType) -> dict:
        return {k: [it['language_code'] for it in item] for k, item in d_lang_map['data']['src_to_tgt'].items()}

    def get_langpair_domain(self, d_lang_map: dict) -> dict:
        return {k: [it['domain_code'] for it in item] for k, item in
                d_lang_map['data']['language_pair_to_domain'].items()}

    def get_professional_field_list(self, d_lang_map: dict) -> set:
        return {it['domain_code'] for _, item in d_lang_map['data']['language_pair_to_domain'].items() for it in item}

    @Tse.time_stat
    @Tse.check_query
    def cloudTranslation_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                             **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://online.cloudtranslation.com
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
                :param professional_field: str, default 'general'.
        :return: str or dict
        """

        use_domain = kwargs.get('professional_field', 'general')
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
            _ = self.session.get(self.get_cookie_url, headers=self.api_headers, timeout=timeout)
            d_lang_map = self.session.get(self.get_lang_url, headers=self.api_headers, timeout=timeout).json()
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(d_lang_map, **debug_lang_kwargs)
            self.langpair_domain = self.get_langpair_domain(d_lang_map)
            self.professional_field = self.get_professional_field_list(d_lang_map)

        if from_language == 'auto':
            payload = {'text': query_text}
            r = self.session.post(self.detect_lang_url, json=payload, headers=self.api_headers, timeout=timeout)
            from_language = r.json()['data']['language']
        from_language, to_language = from_language.lower(), to_language.lower()  # must lower
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='cloudTranslation',
                                                         output_en=self.output_en)

        domains = self.langpair_domain.get(f'{from_language}_{to_language}')
        if not domains:
            raise TranslatorError

        if use_domain not in domains:
            use_domain = domains[0]

        payload = {
            'type': 'text',
            'text': query_text,
            'domain': use_domain,
            'src_lang': from_language,
            'tgt_lang': to_language,
        }
        r = self.session.post(self.api_url, json=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else json.loads(data['data']['data'])['translation']

    @Tse.time_stat
    @Tse.check_query
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://online.cloudtranslation.com
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
                :param professional_field: str, default 'general'.
        :return: str or dict
        """

        use_domain = kwargs.get('professional_field', 'general')
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
            _ = await self.async_session.get(self.get_cookie_url, headers=self.api_headers, timeout=timeout)
            d_lang_map = (
                await self.async_session.get(self.get_lang_url, headers=self.api_headers, timeout=timeout)).json()
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(d_lang_map, **debug_lang_kwargs)
            self.langpair_domain = self.get_langpair_domain(d_lang_map)
            self.professional_field = self.get_professional_field_list(d_lang_map)

        if from_language == 'auto':
            payload = {'text': query_text}
            r = await self.async_session.post(self.detect_lang_url, json=payload, headers=self.api_headers,
                                              timeout=timeout)
            from_language = r.json()['data']['language']
        from_language, to_language = from_language.lower(), to_language.lower()  # must lower
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='cloudTranslation',
                                                         output_en=self.output_en)

        domains = self.langpair_domain.get(f'{from_language}_{to_language}')
        if not domains:
            raise TranslatorError

        if use_domain not in domains:
            use_domain = domains[0]

        payload = {
            'type': 'text',
            'text': query_text,
            'domain': use_domain,
            'src_lang': from_language,
            'tgt_lang': to_language,
        }
        r = await self.async_session.post(self.api_url, json=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else json.loads(data['data']['data'])['translation']
