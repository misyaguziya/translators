import asyncio
import re
import time
import urllib.parse
from typing import Union

from translators.base import Tse, LangMapKwargsType, TranslatorError, ApiKwargsType


class TranslateMe(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://translateme.network/'
        self.api_url = 'https://translateme.network/wp-admin/admin-ajax.php'
        self.host_headers = self.get_headers(self.host_url, if_api=False, if_referer_for_host=True)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_ajax_for_api=True)
        self.session = None
        self.language_map = None
        self.query_count = 0
        self.output_zh = 'Chinese'
        self.output_en = 'English'
        self.input_limit = int(1e2)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, host_html: str, **kwargs: LangMapKwargsType) -> dict:
        lang_list = re.compile('data-lang="(.*?)"').findall(host_html)
        if not lang_list:
            raise TranslatorError

        lang_list = sorted(list(set(lang_list)))
        return {}.fromkeys(lang_list, lang_list)

    # @Tse.uncertified
    # @Tse.time_stat
    # @Tse.check_query
    def _translateMe_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                         **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translateme.network/
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

        if from_language == 'auto':
            from_language = self.warning_auto_lang('translateMe', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='translateMe', output_en=self.output_en)
        if self.output_en not in (from_language, to_language):
            raise TranslatorError('Must use English as an intermediate translation.')

        data_list = []
        paragraphs = [paragraph for paragraph in query_text.split('\n') if paragraph.strip()]
        for paragraph in paragraphs:
            payload = {
                'text': paragraph,
                'lang_from': from_language,
                'lang_to': to_language,
                'action': 'tm_my_action',
                'type': 'convert'
            }
            payload = urllib.parse.urlencode(payload)
            r = self.session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            data_list.append(data)
        time.sleep(sleep_seconds)
        self.query_count += 1
        return {'data': data_list} if is_detail_result else '\n'.join([item['to'] for item in data_list])

    @Tse.uncertified_async
    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translateme.network/
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
        if not (self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(http_client, proxies)
            host_html = (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('translateMe', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='translateMe', output_en=self.output_en)
        if self.output_en not in (from_language, to_language):
            raise TranslatorError('Must use English as an intermediate translation.')

        data_list = []
        paragraphs = [paragraph for paragraph in query_text.split('\n') if paragraph.strip()]
        for paragraph in paragraphs:
            payload = {
                'text': paragraph,
                'lang_from': from_language,
                'lang_to': to_language,
                'action': 'tm_my_action',
                'type': 'convert'
            }
            payload = urllib.parse.urlencode(payload)
            r = await self.async_session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            data_list.append(data)
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return {'data': data_list} if is_detail_result else '\n'.join([item['to'] for item in data_list])

    @Tse.uncertified
    @Tse.time_stat
    @Tse.check_query
    def translateMe_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                        **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translateme.network/
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

        if from_language == 'auto':
            from_language = self.warning_auto_lang('translateMe', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='translateMe', output_en=self.output_en)

        if self.output_en in (from_language, to_language):
            return self._translateMe_api(query_text, from_language, to_language, **kwargs)

        tmp_kwargs = kwargs.copy()
        tmp_kwargs.update({'is_detail_result': False, 'if_show_time_stat': False})
        next_query_text = self._translateMe_api(query_text, from_language, self.output_en, **tmp_kwargs)
        return self._translateMe_api(next_query_text, self.output_en, to_language, **kwargs)

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translateme.network/
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
        if not (self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(http_client, proxies)
            host_html = (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('translateMe', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh,
                                                         output_en_translator='translateMe', output_en=self.output_en)

        if self.output_en in (from_language, to_language):
            return await self._translateMe_api_async(query_text, from_language, to_language, **kwargs)

        tmp_kwargs = kwargs.copy()
        tmp_kwargs.update({'is_detail_result': False, 'if_show_time_stat': False})
        next_query_text = await self._translateMe_api_async(query_text, from_language, self.output_en, **tmp_kwargs)
        return await self._translateMe_api_async(next_query_text, self.output_en, to_language, **kwargs)
