import time
import urllib.parse
import uuid
from typing import Union, Optional, Tuple

import lxml.etree as lxml_etree

from translators.base import Tse, LangMapKwargsType, ApiKwargsType


class Hujiang(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://dict.hjenglish.com/app/trans'
        self.api_url = 'https://dict.hjenglish.com/v10/dict/translation'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True)
        self.language_map = None
        self.session = None
        self.hj_uid = str(uuid.uuid4())
        self.query_count = 0
        self.output_zh = 'cn'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, host_html: str, **kwargs: LangMapKwargsType) -> dict:
        et = lxml_etree.HTML(host_html)
        lang_list = sorted(list(set(et.xpath('//*/select[@class="translate-fromLang"]/option/@value'))))
        return {}.fromkeys(lang_list, lang_list)

    def check_language(self,
                       from_language: str,
                       to_language: str,
                       language_map: dict,
                       output_auto: str = 'auto',
                       output_zh: str = 'zh',
                       output_en_translator: Optional[str] = None,
                       output_en: str = 'en-US',
                       if_check_lang_reverse: bool = True,
                       ) -> Tuple[str, str]:
        _lang = {"ar":'ar-EG'}
        from_language = _lang.get(from_language, from_language)
        to_language = _lang.get(to_language, to_language)
        return super().check_language(
            from_language, to_language, self.language_map,
            output_auto, output_zh, output_en_translator, output_en, if_check_lang_reverse)


    @Tse.time_stat
    @Tse.check_query
    def hujiang_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                    **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://dict.hjenglish.com/app/trans
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
            self.session.cookies.update({'HJ_UID': self.hj_uid, 'HJC_USRC': 'uzhi', 'HJC_NUID': '1'})
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('hujiang', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = urllib.parse.urlencode({'content': query_text})
        api_url = f'{self.api_url}/{from_language}/{to_language}'
        r = self.session.post(api_url, headers=self.api_headers, data=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['data']['content']  # supported by baidu.

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://dict.hjenglish.com/app/trans
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
            self.async_session.cookie_jar.update_cookies({
                'HJ_UID': self.hj_uid,
                'HJC_USRC': 'uzhi',
                'HJC_NUID': '1'
            })
            host_html = await (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text()
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('hujiang', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = urllib.parse.urlencode({'content': query_text})
        api_url = f'{self.api_url}/{from_language}/{to_language}'
        r = await self.async_session.post(api_url, headers=self.api_headers, data=payload, timeout=timeout)
        r.raise_for_status()
        data = await r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['data']['content']  # supported by baidu.
