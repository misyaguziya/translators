import asyncio
import time
from typing import Optional, Union

import lxml.etree as lxml_etree

from translators.base import Tse, LangMapKwargsType, ApiKwargsType, AsyncSessionType, SessionType


class MyMemory(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://mymemory.translated.net'
        self.api_web_url = 'https://mymemory.translated.net/api/ajaxfetch'
        self.api_api_url = 'https://api.mymemory.translated.net/get'
        self.get_matecat_language_url = 'https://www.matecat.com/api/v2/languages'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.session = None
        self.language_map = None
        self.myMemory_language_list = None
        self.mateCat_language_list = None
        self.query_count = 0
        self.output_zh = 'zh-CN'
        self.input_limit = int(5e2)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, myMemory_host_html: str, matecat_lang_url: str, ss: SessionType, headers: dict,
                         timeout: Optional[float], **kwargs: LangMapKwargsType) -> dict:
        et = lxml_etree.HTML(myMemory_host_html)
        lang_list = et.xpath('//*[@id="select_source_mm"]/option/@value')[2:]
        self.myMemory_language_list = sorted(list(set(lang_list)))

        lang_d_list = ss.get(matecat_lang_url, headers=headers, timeout=timeout).json()
        self.mateCat_language_list = sorted(list(set([item['code'] for item in lang_d_list])))

        lang_list = sorted(list(set(self.myMemory_language_list + self.mateCat_language_list)))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, myMemory_host_html: str, matecat_lang_url: str, ss: AsyncSessionType,
                                     headers: dict,
                                     timeout: Optional[float], **kwargs: LangMapKwargsType) -> dict:
        et = lxml_etree.HTML(myMemory_host_html)
        lang_list = et.xpath('//*[@id="select_source_mm"]/option/@value')[2:]
        self.myMemory_language_list = sorted(list(set(lang_list)))

        lang_d_list = await (await ss.get(matecat_lang_url, headers=headers, timeout=timeout)).json()
        self.mateCat_language_list = sorted(list(set([item['code'] for item in lang_d_list])))

        lang_list = sorted(list(set(self.myMemory_language_list + self.mateCat_language_list)))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.time_stat
    @Tse.check_query
    def myMemory_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                     **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://mymemory.translated.net
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
                :param myMemory_mode: str, default "web", choose from ("web", "api").
        :return: str or dict
        """

        mode = kwargs.get('myMemory_mode', 'web')
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
            self.language_map = self.get_language_map(host_html, self.get_matecat_language_url, self.session,
                                                      self.host_headers, timeout, **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('myMemory', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='myMemory', output_en='en-GB')

        params = {
            'q': query_text,
            'langpair': f'{from_language}|{to_language}'
        }
        params = params if mode == 'api' else {**params, **{'mtonly': 1}}
        api_url = self.api_api_url if mode == 'api' else self.api_web_url

        r = self.session.get(api_url, params=params, headers=self.host_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['responseData']['translatedText']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://mymemory.translated.net
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
                :param myMemory_mode: str, default "web", choose from ("web", "api").
        :return: str or dict
        """

        mode = kwargs.get('myMemory_mode', 'web')
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
            self.language_map = await self.get_language_map_async(host_html, self.get_matecat_language_url,
                                                                  self.async_session,
                                                                  self.host_headers, timeout, **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('myMemory', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='myMemory', output_en='en-GB')

        params = {
            'q': query_text,
            'langpair': f'{from_language}|{to_language}'
        }
        params = params if mode == 'api' else {**params, **{'mtonly': 1}}
        api_url = self.api_api_url if mode == 'api' else self.api_web_url

        r = await self.async_session.get(api_url, params=params, headers=self.host_headers, timeout=timeout)
        r.raise_for_status()
        data = await r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['responseData']['translatedText']
