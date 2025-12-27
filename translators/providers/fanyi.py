import asyncio
import re
import time
from typing import Optional, Union

import exejs

from translators.base import Tse, LangMapKwargsType, ApiKwargsType, AsyncSessionType, SessionType


class QQFanyi(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://fanyi.qq.com'
        self.api_url = 'https://fanyi.qq.com/api/translate'
        self.get_language_url = 'https://fanyi.qq.com/js/index.js'
        self.get_qt_url = 'https://fanyi.qq.com/api/reauth12f'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True)
        self.qt_headers = self.get_headers(self.host_url, if_api=True, if_json_for_api=True)
        self.language_map = None
        self.session = None
        self.qtv_qtk = None
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(2e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, ss: SessionType, language_url: str, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        r = ss.get(language_url, headers=self.host_headers, timeout=timeout)
        r.raise_for_status()
        lang_map_str = re.compile('C={(.*?)}|languagePair = {(.*?)}', flags=re.S).search(r.text).group()  # C=
        return exejs.evaluate(lang_map_str)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, ss: AsyncSessionType, language_url: str, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        r = await ss.get(language_url, headers=self.host_headers, timeout=timeout)
        r.raise_for_status()
        lang_map_str = re.compile('C={(.*?)}|languagePair = {(.*?)}', flags=re.S).search(await r.text()).group()  # C=
        return await exejs.evaluate_async(lang_map_str)

    def get_qt(self, ss: SessionType, timeout: Optional[float]) -> dict:
        return ss.post(self.get_qt_url, headers=self.qt_headers, json=self.qtv_qtk, timeout=timeout).json()

    async def get_qt_async(self, ss: AsyncSessionType, timeout: Optional[float]) -> dict:
        return await (await ss.post(self.get_qt_url, headers=self.qt_headers, json=self.qtv_qtk, timeout=timeout)).json()

    @Tse.uncertified  # todo: need ticket and randstr of TCaptcha.
    @Tse.time_stat
    @Tse.check_query
    def qqFanyi_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                    **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.qq.com
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
        if not (self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.qtv_qtk):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            _ = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            self.qtv_qtk = self.get_qt(self.session, timeout)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.session, self.get_language_url, timeout, **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = {
            'source': from_language,
            'target': to_language,
            'sourceText': query_text,
            'qtv': self.qtv_qtk.get('qtv', ''),
            'qtk': self.qtv_qtk.get('qtk', ''),
            'ticket': '',
            'randstr': '',
            'sessionUuid': f'translate_uuid{self.get_timestamp()}',
        }
        r = self.session.post(self.api_url, headers=self.api_headers, data=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else ''.join(
            item['targetText'] for item in data['translate']['records'])  # auto whitespace

    @Tse.uncertified_async  # todo: need ticket and randstr of TCaptcha.
    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.qq.com
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
        if not (
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.qtv_qtk):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(proxies)
            _ = await (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text()
            self.qtv_qtk = await self.get_qt_async(self.async_session, timeout)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(self.async_session, self.get_language_url, timeout,
                                                                  **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = {
            'source': from_language,
            'target': to_language,
            'sourceText': query_text,
            'qtv': self.qtv_qtk.get('qtv', ''),
            'qtk': self.qtv_qtk.get('qtk', ''),
            'ticket': '',
            'randstr': '',
            'sessionUuid': f'translate_uuid{self.get_timestamp()}',
        }
        r = await self.async_session.post(self.api_url, headers=self.api_headers, data=payload, timeout=timeout)
        r.raise_for_status()
        data = await r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else ''.join(item['targetText'] for item in data['translate']['records'])
