import asyncio
import time
import urllib.parse
from typing import Union

from translators.base import Tse, ApiKwargsType


class Mglip(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'http://fy.mglip.com/pc'  # must http  # new host: https://ai.nmgoyun.com/#/AI/translate
        self.api_url = 'http://fy.mglip.com/t2t'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_json_for_api=False)
        self.language_map = {}.fromkeys(['zh', 'mon', 'xle'], ['zh', 'mon', 'xle'])
        self.session = None
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(5e2)
        self.default_from_language = self.output_zh

    @Tse.uncertified
    @Tse.time_stat
    @Tse.check_query
    def mglip_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'mon',
                  **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        http://fy.mglip.com/pc
        :param query_text: str, must.
        :param from_language: str, default 'auto', equals 'zh'.
        :param to_language: str, default 'mon'.
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

        if from_language == 'auto':
            from_language = self.warning_auto_lang('mglip', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = {'userInput': query_text, 'from': from_language, 'to': to_language}
        payload = urllib.parse.urlencode(payload)
        r = self.session.post(self.api_url, headers=self.api_headers, data=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['datas'][0]['paragraph'] if data['datas'][0]['type'] == 'trans' else \
            data['datas'][0]['data']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'mon',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        http://fy.mglip.com/pc
        :param query_text: str, must.
        :param from_language: str, default 'auto', equals 'zh'.
        :param to_language: str, default 'mon'.
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
            _ = await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('mglip', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = {'userInput': query_text, 'from': from_language, 'to': to_language}
        payload = urllib.parse.urlencode(payload)
        r = await self.async_session.post(self.api_url, headers=self.api_headers, data=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['datas'][0]['paragraph'] if data['datas'][0]['type'] == 'trans' else \
            data['datas'][0]['data']
