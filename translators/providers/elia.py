import asyncio
import json
import re
import time
import urllib.parse
from typing import Union

from translators.base import Tse, LangMapKwargsType, TranslatorError, ApiKwargsType


class Elia(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://elia.eus/translator'
        self.api_url = 'https://elia.eus/ajax/translate_string'
        self.detect_lang_url = 'https://elia.eus/ajax/language_detection'
        self.host_headers = self.get_headers(self.host_url, if_api=False, if_referer_for_host=True)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_ajax_for_api=True)
        self.session = None
        self.language_map = None
        self.professional_field = None
        self.langpair_domain = None
        self.token = None
        self.query_count = 0
        self.output_zh = None  # unsupported
        self.input_limit = int(1e2)
        self.default_from_language = 'fr'

    @Tse.debug_language_map
    def get_language_map(self, dd: dict, **kwargs: LangMapKwargsType) -> dict:
        return {ii['source_language']['code']: [jj['target_language']['code'] for jj in dd['language_pairs'] if
                                                jj['source_language']['code'] == ii['source_language']['code']] for ii
                in dd['language_pairs']}

    def get_professional_field_list(self, dd: dict) -> set:
        return {it['translation_model']['code'] for it in dd['language_pairs']}

    def get_langpair_domain(self, dd: dict) -> dict:
        data = {
            f'{item["source_language"]["code"]}__{item["target_language"]["code"]}__{item["translation_model"]["code"]}': {
                'translation_engine': item["engine"]["pk"],
            } for item in dd['language_pairs']
        }
        return data

    @Tse.time_stat
    @Tse.check_query
    def elia_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                 **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://elia.eus/translator
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
                :param professional_field: str, default 'general'. Choose from ('general', 'admin').
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
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            self.token = re.compile('"csrfmiddlewaretoken": "(.*?)"').search(host_html).group(1)
            d_lang_str = re.compile('var languagePairs = JSON.parse\\((.*?)\\);').search(host_html).group()
            d_lang_map = json.loads(d_lang_str[43:-4].replace('&quot;', '"'))
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(d_lang_map, **debug_lang_kwargs)
            self.professional_field = self.get_professional_field_list(d_lang_map)
            self.langpair_domain = self.get_langpair_domain(d_lang_map)

        if from_language == 'auto':
            payload = {
                'text': query_text,
                'csrfmiddlewaretoken': self.token,
            }
            payload = urllib.parse.urlencode(payload)
            r = self.session.post(self.detect_lang_url, data=payload, headers=self.api_headers, timeout=timeout)
            from_language = r.json()['lang_id']
        from_language, to_language = self.check_language(from_language, to_language, self.language_map)

        payload = {
            'input_text': query_text,
            'source_language': from_language,
            'target_language': to_language,
            'translation_model': use_domain,
            'translation_engine': 1,
            'csrfmiddlewaretoken': self.token,
        }

        domain_payload = self.langpair_domain.get(f'{from_language}__{to_language}__{use_domain}')
        if not domain_payload:
            raise TranslatorError
        else:
            payload.update(domain_payload)

        payload = urllib.parse.urlencode(payload)
        r = self.session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['translated_text'].replace('</div>', '\n').replace('<div>',
                                                                                                     '').replace(
            '<span>', '').replace('</span>', '')

    @Tse.time_stat
    @Tse.check_query
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://elia.eus/translator
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
                :param professional_field: str, default 'general'. Choose from ('general', 'admin').
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
            host_html = (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text
            self.token = re.compile('"csrfmiddlewaretoken": "(.*?)"').search(host_html).group(1)
            d_lang_str = re.compile('var languagePairs = JSON.parse\\((.*?)\\);').search(host_html).group()
            d_lang_map = json.loads(d_lang_str[43:-4].replace('&quot;', '"'))
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(d_lang_map, **debug_lang_kwargs)
            self.professional_field = self.get_professional_field_list(d_lang_map)
            self.langpair_domain = self.get_langpair_domain(d_lang_map)

        if from_language == 'auto':
            payload = {
                'text': query_text,
                'csrfmiddlewaretoken': self.token,
            }
            payload = urllib.parse.urlencode(payload)
            r = await self.async_session.post(self.detect_lang_url, data=payload, headers=self.api_headers,
                                              timeout=timeout)
            from_language = r.json()['lang_id']
        from_language, to_language = self.check_language(from_language, to_language, self.language_map)

        payload = {
            'input_text': query_text,
            'source_language': from_language,
            'target_language': to_language,
            'translation_model': use_domain,
            'translation_engine': 1,
            'csrfmiddlewaretoken': self.token,
        }

        domain_payload = self.langpair_domain.get(f'{from_language}__{to_language}__{use_domain}')
        if not domain_payload:
            raise TranslatorError
        else:
            payload.update(domain_payload)

        payload = urllib.parse.urlencode(payload)
        r = await self.async_session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['translated_text'].replace('</div>', '\n').replace('<div>',
                                                                                                     '').replace(
            '<span>', '').replace('</span>', '')
