import asyncio
import re
import time
import uuid
from typing import Optional, Union, List

import exejs

from translators.base import Tse, LangMapKwargsType, ApiKwargsType, AsyncSessionType, SessionType


class QQTranSmart(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://transmart.qq.com'
        self.api_url = 'https://transmart.qq.com/api/imt'
        self.get_lang_url = None
        self.get_lang_url_pattern = '/assets/vendor.(.*?).js'  # e4c6831c
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_json_for_api=True)
        self.language_map = None
        self.session = None
        self.uuid = str(uuid.uuid4())
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, lang_url: str, ss: SessionType, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        js_html = ss.get(lang_url, headers=self.host_headers, timeout=timeout).text
        lang_str_list = re.compile('lngs:\\[(.*?)]').findall(js_html)  # 'lngs:\\[(.*?)\\]'
        lang_list = [exejs.evaluate(f'[{x}]') for x in lang_str_list]
        lang_list = sorted(list(set([lang for langs in lang_list for lang in langs])))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, lang_url: str, ss: AsyncSessionType, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        js_html = await (await ss.get(lang_url, headers=self.host_headers, timeout=timeout)).text()
        lang_str_list = re.compile('lngs:\\[(.*?)]').findall(js_html)
        lang_list = [await exejs.evaluate_async(f'[{x}]') for x in lang_str_list]
        lang_list = sorted(list(set([lang for langs in lang_list for lang in langs])))
        return {}.fromkeys(lang_list, lang_list)

    def get_clientKey(self) -> str:
        return f'browser-firefox-110.0.0-Windows 10-{self.uuid}-{self.get_timestamp()}'

    def split_sentence(self, data: dict) -> List[str]:
        index_pair_list = [[item['start'], item['start'] + item['len']] for item in data['sentence_list']]
        index_list = [i for ii in index_pair_list for i in ii]
        return [data['text'][index_list[i]: index_list[i + 1]] for i in range(len(index_list) - 1)]

    @Tse.time_stat
    @Tse.check_query
    def qqTranSmart_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                        **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://transmart.qq.com
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

            if not self.get_lang_url:
                self.get_lang_url = f'{self.host_url}{re.compile(self.get_lang_url_pattern).search(host_html).group()}'
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.get_lang_url, self.session, timeout, **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('qqTranSmart', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        client_key = self.get_clientKey()
        self.api_headers.update({'Cookie': f'client_key={client_key}'})

        split_payload = {
            'header': {
                'fn': 'text_analysis',
                'client_key': client_key,
            },
            'type': 'plain',
            'text': query_text,
            'normalize': {'merge_broken_line': 'false'}
        }
        split_data = self.session.post(self.api_url, json=split_payload, headers=self.api_headers,
                                       timeout=timeout).json()
        text_list = self.split_sentence(split_data)

        api_payload = {
            'header': {
                'fn': 'auto_translation',
                'client_key': client_key,
            },
            'type': 'plain',
            'model_category': 'normal',
            'source': {
                'lang': from_language,
                'text_list': [''] + text_list + [''],
            },
            'target': {'lang': to_language}
        }
        r = self.session.post(self.api_url, json=api_payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else ''.join(data['auto_translation'])

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://transmart.qq.com
        :param query_text: str, must.
        :param from_language: str, default 'auto'.
        :param to_language: str, default 'en'.
        :param **kwargs:
                :param timeout: Optional[float], default None.
                :param proxies: Optional[dict], default None.
                :param sleep_seconds: float, default 0.
                :param is_detail_result: bool, default False.
                :param http_client: str, default 'niquests'. Union['niquests', 'httpx']
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

            if not self.get_lang_url:
                self.get_lang_url = f'{self.host_url}{re.compile(self.get_lang_url_pattern).search(host_html).group()}'
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(self.get_lang_url, self.async_session, timeout,
                                                                  **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('qqTranSmart', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        client_key = self.get_clientKey()
        self.api_headers.update({'Cookie': f'client_key={client_key}'})

        split_payload = {
            'header': {
                'fn': 'text_analysis',
                'client_key': client_key,
            },
            'type': 'plain',
            'text': query_text,
            'normalize': {'merge_broken_line': 'false'}
        }
        split_data = await (await self.async_session.post(self.api_url, json=split_payload, headers=self.api_headers,
                                                    timeout=timeout)).json()
        text_list = self.split_sentence(split_data)

        api_payload = {
            'header': {
                'fn': 'auto_translation',
                'client_key': client_key,
            },
            'type': 'plain',
            'model_category': 'normal',
            'source': {
                'lang': from_language,
                'text_list': [''] + text_list + [''],
            },
            'target': {'lang': to_language}
        }
        r = await self.async_session.post(self.api_url, json=api_payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = await r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else ''.join(data['auto_translation'])
