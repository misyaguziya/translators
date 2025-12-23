import asyncio
import datetime
import re
import time
import uuid
from typing import Optional, Union

from translators.base import Tse, LangMapKwargsType, ApiKwargsType, AsyncSessionType, SessionType


class Mirai(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.home_url = 'https://miraitranslate.com'
        self.host_url = 'https://miraitranslate.com/trial/'
        self.api_url = 'https://trial.miraitranslate.com/trial/api/translate.php'
        self.lang_url = None
        self.lang_url_pattern = 'main-es2015.(.*?).js'
        self.detect_lang_url = 'https://trial.miraitranslate.com/trial/api/detect_lang.php'
        self.trace_url = 'https://trial.miraitranslate.com/trial/api/trace.php'
        self.host_headers = self.get_headers(self.home_url, if_api=False)
        self.api_json_headers = self.get_headers(self.home_url, if_api=True, if_json_for_api=True)
        self.api_text_headers = self.get_headers(self.home_url, if_api=True, if_ajax_for_api=False)
        self.session = None
        self.language_map = None
        self.tran_key = None
        self.trans_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())
        self.lang_zh_map = {'zh-CN': 'zh', 'zh-TW': 'zt'}
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(2e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, lang_url: str, ss: SessionType, headers: dict, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        js_html = ss.get(lang_url, headers=headers, timeout=timeout).text
        lang_pairs = re.compile('"/trial/(\\w{2})/(\\w{2})"').findall(js_html)
        return {f_lang: [v for k, v in lang_pairs if k == f_lang] for f_lang, t_lang in lang_pairs}

    @Tse.debug_language_map_async
    async def get_language_map_async(self, lang_url: str, ss: AsyncSessionType, headers: dict, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        js_html = (await ss.get(lang_url, headers=headers, timeout=timeout)).text
        lang_pairs = re.compile('"/trial/(\\w{2})/(\\w{2})"').findall(js_html)
        return {f_lang: [v for k, v in lang_pairs if k == f_lang] for f_lang, t_lang in lang_pairs}

    @Tse.uncertified
    @Tse.time_stat
    @Tse.check_query
    def mirai_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'ja',
                  **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://miraitranslate.com/en/trial/
        :param query_text: str, must.
        :param from_language: str, default 'auto'.
        :param to_language: str, default 'ja'.
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
        if not (self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.tran_key):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            # _ = self.session.get(self.home_url, headers=self.host_headers, timeout=timeout)
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            self.tran_key = re.compile('var tran = "(.*?)";').search(host_html).group(1)
            lang_url_part = re.compile(self.lang_url_pattern).search(host_html).group()
            self.lang_url = f'https://miraitranslate.com/trial/inmt/{lang_url_part}'
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.lang_url, self.session, self.api_json_headers, timeout,
                                                      **debug_lang_kwargs)

        if from_language == 'auto':
            r = self.session.post(self.detect_lang_url, headers=self.api_json_headers, json={'text': query_text},
                                  timeout=timeout)
            from_language = r.json()['language']
            from_language = self.lang_zh_map[from_language] if 'zh' in from_language else from_language
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        trace_data = {
            'operationType': 'SLA',
            'lang': from_language,
            'source': query_text,
            'userId': self.user_id,
            'transId': self.trans_id,
            'uniqueId': self.tran_key,
            'date': f'{datetime.datetime.now(datetime.UTC).isoformat()[:-3]}Z',
        }
        _ = self.session.post(self.trace_url, json=trace_data, headers=self.api_text_headers, timeout=timeout)

        payload = {
            'input': query_text,
            'source': from_language,
            'target': to_language,
            'tran': self.tran_key,
            'adaptPhrases': [],
            'filter_profile': 'nmt',
            'profile': 'inmt',
            'usePrefix': 'false',
            'zt': 'true' if 'zt' in (from_language, to_language) else 'false',
            'InmtTarget': '',
            'InmtTranslateType': 'gisting',
        }
        r = self.session.post(self.api_url, data=payload, headers=self.api_text_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['ouputs'][0]['output'][0]['translation']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'ja',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://miraitranslate.com/en/trial/
        :param query_text: str, must.
        :param from_language: str, default 'auto'.
        :param to_language: str, default 'ja'.
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
        if not (
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.tran_key):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(http_client, proxies)
            # _ = await self.async_session.get(self.home_url, headers=self.host_headers, timeout=timeout)
            host_html = (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text
            self.tran_key = re.compile('var tran = "(.*?)";').search(host_html).group(1)
            lang_url_part = re.compile(self.lang_url_pattern).search(host_html).group()
            self.lang_url = f'https://miraitranslate.com/trial/inmt/{lang_url_part}'
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(self.lang_url, self.async_session,
                                                                  self.api_json_headers, timeout,
                                                                  **debug_lang_kwargs)

        if from_language == 'auto':
            r = await self.async_session.post(self.detect_lang_url, headers=self.api_json_headers,
                                              json={'text': query_text},
                                              timeout=timeout)
            from_language = r.json()['language']
            from_language = self.lang_zh_map[from_language] if 'zh' in from_language else from_language
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        trace_data = {
            'operationType': 'SLA',
            'lang': from_language,
            'source': query_text,
            'userId': self.user_id,
            'transId': self.trans_id,
            'uniqueId': self.tran_key,
            'date': f'{datetime.datetime.now(datetime.UTC).isoformat()[:-3]}Z',
        }
        _ = await self.async_session.post(self.trace_url, json=trace_data, headers=self.api_text_headers,
                                          timeout=timeout)

        payload = {
            'input': query_text,
            'source': from_language,
            'target': to_language,
            'tran': self.tran_key,
            'adaptPhrases': [],
            'filter_profile': 'nmt',
            'profile': 'inmt',
            'usePrefix': 'false',
            'zt': 'true' if 'zt' in (from_language, to_language) else 'false',
            'InmtTarget': '',
            'InmtTranslateType': 'gisting',
        }
        r = await self.async_session.post(self.api_url, data=payload, headers=self.api_text_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['ouputs'][0]['output'][0]['translation']
