import asyncio
import re
import time
import urllib.parse
from typing import Optional, Union

from translators.base import Tse, LangMapKwargsType, TranslatorError, ApiKwargsType, AsyncSessionType, SessionType


class SysTran(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.home_url = 'https://www.systran.net'
        self.host_url = 'https://www.systran.net/translate/'
        self.api_url = 'https://api-translate.systran.net/translation/text/translate'
        self.get_lang_url = 'https://api-translate.systran.net/translation/supportedLanguages'
        self.get_token_url = 'https://translate.systran.net/oidc/token'
        self.get_client_url = 'https://www.systransoft.com/wp-content/themes/systran/dist/translatebox/translateBox.bundle.js'
        self.host_headers = self.get_headers(self.home_url, if_api=False, if_referer_for_host=True)
        self.api_ajax_headers = self.get_headers(self.home_url, if_api=True, if_ajax_for_api=True)
        self.api_json_headers = self.get_headers(self.home_url, if_api=True, if_json_for_api=True)
        self.session = None
        self.language_map = None
        self.professional_field = None
        self.langpair_domain = None
        self.client_data = None
        self.token_data = None
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, d_lang_map: dict, **kwargs: LangMapKwargsType) -> dict:
        return {ii['source']: [jj['target'] for jj in d_lang_map['languagePairs'] if jj['source'] == ii['source']] for
                ii in d_lang_map['languagePairs']}

    def get_professional_field_list(self, d_lang_map: dict) -> set:
        return {it['selectors']['domain'] for item in d_lang_map['languagePairs'] for it in item['profiles']}

    def get_langpair_domain(self, d_lang_map: dict) -> dict:
        data = {
            f'{item["source"]}__{item["target"]}__{it["selectors"]["domain"]}': {
                'domain': it["selectors"]["domain"],
                'owner': it['selectors']['owner'],
                'size': it['selectors']['size'],
            } for item in d_lang_map['languagePairs'] for it in item['profiles']
        }
        return data

    def get_client_data(self, client_url: str, ss: SessionType, headers: dict, timeout: Optional[float]) -> dict:
        js_html = ss.get(client_url, headers=headers, timeout=timeout).text
        search_groups = re.compile('"https://translate.systran.net/oidc",\\w="(.*?)",\\w="(.*?)";').search(
            js_html)  # \\w{1} == \\w
        client_data = {
            'grant_type': 'client_credentials',
            'client_id': search_groups.group(1),
            'client_secret': search_groups.group(2),
        }
        return client_data

    async def get_client_data_async(self, client_url: str, ss: AsyncSessionType, headers: dict,
                                    timeout: Optional[float]) -> dict:
        js_html = await (await ss.get(client_url, headers=headers, timeout=timeout)).text()
        search_groups = re.compile('"https://translate.systran.net/oidc",\\w="(.*?)",\\w="(.*?)";').search(
            js_html)  # \\w{1} == \\w
        client_data = {
            'grant_type': 'client_credentials',
            'client_id': search_groups.group(1),
            'client_secret': search_groups.group(2),
        }
        return client_data

    @Tse.time_stat
    @Tse.check_query
    def sysTran_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                    **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.systran.net/translate/, https://www.systransoft.com/translate/
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
                :param professional_field: str, default None.
        :return: str or dict
        """

        use_domain = kwargs.get('professional_field', 'Generic')
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
            self.client_data = self.get_client_data(self.get_client_url, self.session, self.host_headers, timeout)
            payload = urllib.parse.urlencode(self.client_data)
            self.token_data = self.session.post(self.get_token_url, data=payload, headers=self.api_ajax_headers,
                                                timeout=timeout).json()

            header_params = {
                'authorization': f'{self.token_data["token_type"]} {self.token_data["access_token"]}',
                'x-user-agent': 'File Translate Box Portable',
            }
            self.api_json_headers.update(header_params)

            d_lang_map = self.session.get(self.get_lang_url, headers=self.api_json_headers, timeout=timeout).json()
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(d_lang_map, **debug_lang_kwargs)
            self.professional_field = self.get_professional_field_list(d_lang_map)
            self.langpair_domain = self.get_langpair_domain(d_lang_map)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)
        if from_language == 'auto':
            from_language = self.warning_auto_lang('sysTran', self.default_from_language, if_print_warning)

        payload = {
            'target': to_language,
            'source': from_language if from_language != 'auto' else None,
            'inputs': [paragraph for paragraph in query_text.split('\n') if paragraph.strip()],
            'format': 'text/plain',
            'autodetectionMode': 'single',
            'withInfo': 'true',
            'withAnnotations': 'true',
            'profileId': None,
            'domain': None,
            'owner': None,
            'size': None,
        }
        if use_domain and from_language != 'auto':
            domain_payload = self.langpair_domain.get(f'{from_language}__{to_language}__{use_domain}')
            if not domain_payload:
                raise TranslatorError
            else:
                payload.update(domain_payload)

        r = self.session.post(self.api_url, json=payload, headers=self.api_json_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join(' '.join(it['alt_transes'][0]['target']['text'] for it in
                                                                item['output']['documents'][0]['trans_units'][0][
                                                                    'sentences']) for item in data['outputs'])

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.systran.net/translate/, https://www.systransoft.com/translate/
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
                :param professional_field: str, default None.
        :return: str or dict
        """

        use_domain = kwargs.get('professional_field', 'Generic')
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
            self.client_data = await self.get_client_data_async(self.get_client_url, self.async_session,
                                                                self.host_headers, timeout)
            payload = urllib.parse.urlencode(self.client_data)
            self.token_data = await (
                await self.async_session.post(self.get_token_url, data=payload, headers=self.api_ajax_headers,
                                              timeout=timeout)).json()

            header_params = {
                'authorization': f'{self.token_data["token_type"]} {self.token_data["access_token"]}',
                'x-user-agent': 'File Translate Box Portable',
            }
            self.api_json_headers.update(header_params)

            d_lang_map = await (
                await self.async_session.get(self.get_lang_url, headers=self.api_json_headers, timeout=timeout)).json()
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(d_lang_map, **debug_lang_kwargs)
            self.professional_field = self.get_professional_field_list(d_lang_map)
            self.langpair_domain = self.get_langpair_domain(d_lang_map)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)
        if from_language == 'auto':
            from_language = self.warning_auto_lang('sysTran', self.default_from_language, if_print_warning)

        payload = {
            'target': to_language,
            'source': from_language if from_language != 'auto' else None,
            'inputs': [paragraph for paragraph in query_text.split('\n') if paragraph.strip()],
            'format': 'text/plain',
            'autodetectionMode': 'single',
            'withInfo': 'true',
            'withAnnotations': 'true',
            'profileId': None,
            'domain': None,
            'owner': None,
            'size': None,
        }
        if use_domain and from_language != 'auto':
            domain_payload = self.langpair_domain.get(f'{from_language}__{to_language}__{use_domain}')
            if not domain_payload:
                raise TranslatorError
            else:
                payload.update(domain_payload)

        r = await self.async_session.post(self.api_url, json=payload, headers=self.api_json_headers, timeout=timeout)
        r.raise_for_status()
        data =await  r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join(' '.join(it['alt_transes'][0]['target']['text'] for it in
                                                                item['output']['documents'][0]['trans_units'][0][
                                                                    'sentences']) for item in data['outputs'])
