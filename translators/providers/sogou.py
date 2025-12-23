import asyncio
import hashlib
import json
import re
import time
import uuid
from typing import Optional, Union

from translators.base import Tse, LangMapKwargsType, ApiKwargsType, AsyncSessionType, SessionType


class Sogou(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://fanyi.sogou.com/text'
        self.api_url = 'https://fanyi.sogou.com/api/transpc/text/result'
        self.get_language_old_url = 'https://search.sogoucdn.com/translate/pc/static/js/app.7016e0df.js'
        self.get_language_pattern = '//search.sogoucdn.com/translate/pc/static/js/vendors.(.*?).js'
        self.get_language_url = None
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True)
        self.language_map = None
        self.uuid = None
        self.session = None
        self.query_count = 0
        self.output_zh = 'zh-CHS'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, host_html: str, lang_old_url: str, ss: SessionType, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        try:
            if not self.get_language_url:
                lang_url_path = re.compile(self.get_language_pattern).search(host_html).group()
                self.get_language_url = ''.join(['https:', lang_url_path])
            lang_html = ss.get(self.get_language_url, headers=self.host_headers, timeout=timeout).text
        except:
            lang_html = ss.get(lang_old_url, headers=self.host_headers, timeout=timeout).text

        lang_list_str = re.compile('"ALL":\\[(.*?)]').search(lang_html).group().replace('!0', '1').replace('!1', '0')[
            6:]
        lang_item_list = json.loads(lang_list_str)
        lang_list = [item['lang'] for item in lang_item_list if item['play'] == 1]
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, host_html: str, lang_old_url: str, ss: AsyncSessionType,
                                     timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        try:
            if not self.get_language_url:
                lang_url_path = re.compile(self.get_language_pattern).search(host_html).group()
                self.get_language_url = ''.join(['https:', lang_url_path])
            lang_html = (await ss.get(self.get_language_url, headers=self.host_headers, timeout=timeout)).text
        except:
            lang_html = (await ss.get(lang_old_url, headers=self.host_headers, timeout=timeout)).text

        lang_list_str = re.compile('"ALL":\\[(.*?)]').search(lang_html).group().replace('!0', '1').replace('!1', '0')[
            6:]
        lang_item_list = json.loads(lang_list_str)
        lang_list = [item['lang'] for item in lang_item_list if item['play'] == 1]
        return {}.fromkeys(lang_list, lang_list)

    def get_form(self, query_text: str, from_language: str, to_language: str, uid: str) -> dict:
        sign_text = "" + from_language + to_language + query_text + '109984457'  # window.__INITIAL_STATE__.common.CONFIG.secretCode
        sign = hashlib.md5(sign_text.encode()).hexdigest()
        form = {
            "from": from_language,
            "to": to_language,
            "text": query_text,
            "uuid": uid,
            "s": sign,
            "client": "pc",  # wap
            "fr": "browser_pc",  # browser_wap
            "needQc": "1",
        }
        return form

    @Tse.time_stat
    @Tse.check_query
    def sogou_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                  **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.sogou.com/text
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
        if not (self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.uuid):
            self.uuid = str(uuid.uuid4())
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, self.get_language_old_url, self.session, timeout,
                                                      **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = self.get_form(query_text, from_language, to_language, self.uuid)
        r = self.session.post(self.api_url, headers=self.api_headers, data=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['data']['translate']['dit']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.sogou.com/text
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
        if not (
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.uuid):
            self.uuid = str(uuid.uuid4())
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(http_client, proxies)
            host_html = (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(host_html, self.get_language_old_url,
                                                                  self.async_session, timeout,
                                                                  **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = self.get_form(query_text, from_language, to_language, self.uuid)
        r = await self.async_session.post(self.api_url, headers=self.api_headers, data=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['data']['translate']['dit']
