import asyncio
import random
import re
import time
from typing import Union, List

from translators.base import Tse, LangMapKwargsType, ApiKwargsType


class Deepl(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://www.deepl.com/translator'
        self.api_url = 'https://www2.deepl.com/jsonrpc'
        self.login_url = 'https://login-wall.deepl.com'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_ajax_for_api=False, if_json_for_api=True)
        self.params = {'split': {'method': 'LMT_split_text'}, 'handle': {'method': 'LMT_handle_jobs'}}
        self.request_id = int(random.randrange(100, 10000) * 10000 + 4)
        self.language_map = None
        self.session = None
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, host_html: str, **kwargs: LangMapKwargsType) -> dict:
        lang_list = sorted(list(set(re.compile("\\['selectLang_source_(\\w+)']").findall(host_html))))
        return {}.fromkeys(lang_list, lang_list)

    def split_sentences_param(self, query_text: str, from_language: str) -> dict:
        data = {
            'id': self.request_id,
            'jsonrpc': '2.0',
            'params': {
                'texts': query_text.split('\n'),
                'commonJobParams': {'mode': 'translate'},
                'lang': {
                    'lang_user_selected': from_language,
                    'preference': {
                        'weight': {},
                        'default': 'default',
                    },
                },
            },
        }
        if from_language != 'auto':
            data['params']['lang'].update({'lang_computed': from_language})
        return {**self.params['split'], **data}

    def context_sentences_param(self, sentences: List[str], from_language: str, to_language: str) -> dict:
        sentences = [''] + sentences + ['']
        data = {
            'id': self.request_id + 1,
            'jsonrpc': ' 2.0',
            'params': {
                'priority': 1,  # -1 if 'quality': 'fast'
                'timestamp': self.get_timestamp(),
                'commonJobParams': {
                    # 'regionalVariant': 'en-US',
                    'browserType': 1,
                    'mode': 'translate',
                    'textType': 'plaintext',
                },
                'jobs': [
                    {
                        'kind': 'default',
                        # 'quality': 'fast', # -1
                        'sentences': [{'id': i - 1, 'prefix': '', 'text': sentences[i]}],
                        'raw_en_context_before': sentences[1:i] if sentences[i - 1] else [],
                        'raw_en_context_after': [sentences[i + 1]] if sentences[i + 1] else [],
                        'preferred_num_beams': 1 if len(sentences) >= 4 else 4,  # 1 if two sentences else 4, len>=2+2
                    }
                    for i in range(1, len(sentences) - 1)
                ],
                'lang': {
                    'preference': {
                        'weight': {},
                        'default': 'default',
                    },
                    'source_lang_computed': from_language,  # 'source_lang_user_selected'
                    'target_lang': to_language,
                },
            },
        }
        return {**self.params['handle'], **data}

    @Tse.time_stat
    @Tse.check_query
    def deepl_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                  **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.deepl.com
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
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, **debug_lang_kwargs)
            _ = self.session.get(self.login_url, headers=self.host_headers, timeout=timeout)

        from_language, to_language = self.check_language(from_language, to_language, language_map=self.language_map,
                                                         output_zh=self.output_zh, output_auto='auto')
        from_language = from_language.upper() if from_language != 'auto' else from_language
        to_language = to_language.upper() if to_language != 'auto' else to_language

        ssp_data = self.split_sentences_param(query_text, from_language)
        r_s = self.session.post(self.api_url, params=self.params['split'], json=ssp_data, headers=self.api_headers,
                                timeout=timeout)
        r_s.raise_for_status()
        s_data = r_s.json()
        from_language = s_data['result']['lang']['detected']
        s_sentences = [it['sentences'][0]['text'] for item in s_data['result']['texts'] for it in item['chunks']]

        h_data = self.context_sentences_param(s_sentences, from_language, to_language)
        r_cs = self.session.post(self.api_url, params=self.params['handle'], json=h_data, headers=self.api_headers,
                                 timeout=timeout)
        r_cs.raise_for_status()
        data = r_cs.json()
        time.sleep(sleep_seconds)
        self.request_id += 3
        self.query_count += 1
        return data if is_detail_result else ' '.join(
            item['beams'][0]['sentences'][0]["text"] for item in data['result']['translations'])  # either ' ' or '\n'.

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.deepl.com
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
            host_html = await (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text()
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, **debug_lang_kwargs)
            _ = await self.async_session.get(self.login_url, headers=self.host_headers, timeout=timeout)

        from_language, to_language = self.check_language(from_language, to_language, language_map=self.language_map,
                                                         output_zh=self.output_zh, output_auto='auto')
        from_language = from_language.upper() if from_language != 'auto' else from_language
        to_language = to_language.upper() if to_language != 'auto' else to_language

        ssp_data = self.split_sentences_param(query_text, from_language)
        r_s = await self.async_session.post(self.api_url, params=self.params['split'], json=ssp_data,
                                            headers=self.api_headers,
                                            timeout=timeout)
        r_s.raise_for_status()
        s_data = await r_s.json()
        from_language = s_data['result']['lang']['detected']
        s_sentences = [it['sentences'][0]['text'] for item in s_data['result']['texts'] for it in item['chunks']]

        h_data = self.context_sentences_param(s_sentences, from_language, to_language)
        r_cs = await self.async_session.post(self.api_url, params=self.params['handle'], json=h_data,
                                             headers=self.api_headers,
                                             timeout=timeout)
        r_cs.raise_for_status()
        data = await r_cs.json()
        await asyncio.sleep(sleep_seconds)
        self.request_id += 3
        self.query_count += 1
        return data if is_detail_result else ' '.join(
            item['beams'][0]['sentences'][0]["text"] for item in data['result']['translations'])  # either ' ' or '\n'.
