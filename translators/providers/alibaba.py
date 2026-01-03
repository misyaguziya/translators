import asyncio
import random
import re
import time
from typing import Optional, Union

import aiohttp

from translators.base import Tse, LangMapKwargsType, TranslatorError, ApiKwargsType, AsyncSessionType, SessionType, \
    ResponseType, AsyncResponseType


class AlibabaV1(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://translate.alibaba.com'
        self.api_url = 'https://translate.alibaba.com/translationopenseviceapp/trans/TranslateTextAddAlignment.do'
        self.get_language_url = 'https://translate.alibaba.com/translationopenseviceapp/trans/acquire_supportLanguage.do'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True)
        self.language_map = None
        self.professional_field = ("general", "message", "offer")
        self.dmtrack_pageid = None
        self.session = None
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    def get_dmtrack_pageid(self, host_response: ResponseType) -> str:
        try:
            e = re.compile("dmtrack_pageid='(\\w+)';").findall(host_response.text)[0]
        except:
            e = ''
        if not e:
            e = dict(host_response.cookies).get("cna", "001")
            e = re.compile('[^a-z\\d]').sub(repl='', string=e.lower())[:16]
        else:
            n, r = e[0:16], e[16:26]
            i = hex(int(r, 10))[2:] if re.compile('^[\\-+]?[0-9]+$').match(r) else r
            e = n + i

        s = self.get_timestamp()
        o = ''.join([e, hex(s)[2:]])
        for _ in range(1, 10):
            a = hex(int(random.random() * 1e10))[2:]  # int->str: 16, '0x'
            o += a
        return o[:42]

    async def get_dmtrack_pageid_async(self, host_response: AsyncResponseType) -> str:
        try:
            e = re.compile("dmtrack_pageid='(\\w+)';").findall(await host_response.text())[0]
        except:
            e = ''
        if not e:
            e = dict(host_response.cookies).get("cna", "001")
            e = re.compile('[^a-z\\d]').sub(repl='', string=e.lower())[:16]
        else:
            n, r = e[0:16], e[16:26]
            i = hex(int(r, 10))[2:] if re.compile('^[\\-+]?[0-9]+$').match(r) else r
            e = n + i

        s = self.get_timestamp()
        o = ''.join([e, hex(s)[2:]])
        for _ in range(1, 10):
            a = hex(int(random.random() * 1e10))[2:]  # int->str: 16, '0x'
            o += a
        return o[:42]

    @Tse.debug_language_map
    def get_language_map(self, ss: SessionType, lang_url: str, use_domain: str, dmtrack_pageid: str,
                         timeout: Optional[float], **kwargs: LangMapKwargsType) -> dict:
        params = {'dmtrack_pageid': dmtrack_pageid, 'biz_type': use_domain}
        language_dict = ss.get(lang_url, params=params, headers=self.host_headers, timeout=timeout).json()
        return dict(map(lambda x: x, [(x['sourceLuange'], x['targetLanguages']) for x in language_dict['languageMap']]))

    @Tse.debug_language_map_async
    async def get_language_map_async(self, ss: AsyncSessionType, lang_url: str, use_domain: str, dmtrack_pageid: str,
                                     timeout: Optional[float], **kwargs: LangMapKwargsType) -> dict:
        params = {'dmtrack_pageid': dmtrack_pageid, 'biz_type': use_domain}
        language_dict = await (await ss.get(lang_url, params=params, headers=self.host_headers, timeout=timeout)).json()
        return dict(map(lambda x: x, [(x['sourceLuange'], x['targetLanguages']) for x in language_dict['languageMap']]))

    @Tse.time_stat
    @Tse.check_query
    def alibaba_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                    **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translate.alibaba.com
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
                :param professional_field: str, default 'message', choose from ("general","message","offer")
        :return: str or dict
        """

        use_domain = kwargs.get('professional_field', 'message')
        if use_domain not in self.professional_field:
            raise TranslatorError

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
        if not (
                self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.dmtrack_pageid):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            host_response = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            self.dmtrack_pageid = self.get_dmtrack_pageid(host_response)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.session, self.get_language_url, use_domain,
                                                      self.dmtrack_pageid, timeout, **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)
        payload = {
            "srcLanguage": from_language,
            "tgtLanguage": to_language,
            "srcText": query_text,
            "bizType": use_domain,
            "viewType": "",
            "source": "",
        }
        params = {"dmtrack_pageid": self.dmtrack_pageid}
        r = self.session.post(self.api_url, headers=self.api_headers, params=params, data=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['listTargetText'][0]

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translate.alibaba.com
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
                :param professional_field: str, default 'message', choose from ("general","message","offer")
        :return: str or dict
        """

        use_domain = kwargs.get('professional_field', 'message')
        if use_domain not in self.professional_field:
            raise TranslatorError

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
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.dmtrack_pageid):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(proxies)
            host_response = await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            # Need to access cookies from response or session. niquests/httpx handles cookies in session usually.
            # get_dmtrack_pageid might need adaptation if it reads cookies from response object structure difference.
            # Assuming basic structure compatibility or cookies in session.
            # For simplicity, we assume get_dmtrack_pageid works with the async response object or we extract cookies manually if needed.
            # niquests response has .cookies similar to requests.
            self.dmtrack_pageid = await self.get_dmtrack_pageid_async(host_response)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(self.async_session, self.get_language_url, use_domain,
                                                                  self.dmtrack_pageid, timeout, **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)
        payload = {
            "srcLanguage": from_language,
            "tgtLanguage": to_language,
            "srcText": query_text,
            "bizType": use_domain,
            "viewType": "",
            "source": "",
        }
        params = {"dmtrack_pageid": self.dmtrack_pageid}
        r = await self.async_session.post(self.api_url, headers=self.api_headers, params=params, data=payload,
                                          timeout=timeout)
        r.raise_for_status()
        data = await r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['listTargetText'][0]


class AlibabaV2(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://translate.alibaba.com'
        self.api_url = 'https://translate.alibaba.com/api/translate/text'
        self.csrf_url = 'https://translate.alibaba.com/api/translate/csrftoken'
        self.get_language_pattern = '//lang.alicdn.com/mcms/translation-open-portal/(.*?)/translation-open-portal_interface.json'
        self.get_language_url = None
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_ajax_for_api=False,
                                            if_multipart_for_api=True)
        self.language_map = None
        self.detail_language_map = None
        self.professional_field = ('general',)
        self.csrf_token = None
        self.session = None
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, lang_html: str, **kwargs: LangMapKwargsType) -> dict:
        lang_paragraph = re.compile('"en_US":{(.*?)},"zh_CN":{').search(lang_html).group().replace('",', '",\n')
        lang_items = re.compile('interface.(.*?)":"(.*?)"').findall(lang_paragraph)
        _fn_filter = lambda k, v: 1 if (len(k) <= 3 or (len(k) == 5 and '-' in k)) and len(v.split(' ')) <= 2 else 0
        lang_items = sorted([(k, v) for k, v in lang_items if _fn_filter(k, v)])
        d_lang_map = {k: v for k, v in lang_items}
        lang_list = list(d_lang_map.keys())
        return {}.fromkeys(lang_list, lang_list)

    def get_d_lang_map(self, lang_html: str) -> dict:
        lang_paragraph = re.compile('"en_US":{(.*?)},"zh_CN":{').search(lang_html).group().replace('",', '",\n')
        lang_items = re.compile('interface.(.*?)":"(.*?)"').findall(lang_paragraph)
        _fn_filter = lambda k, v: 1 if (len(k) <= 3 or (len(k) == 5 and '-' in k)) and len(v.split(' ')) <= 2 else 0
        lang_items = sorted([(k, v) for k, v in lang_items if _fn_filter(k, v)])
        return {k: v for k, v in lang_items}

    @Tse.time_stat
    @Tse.check_query
    def alibaba_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                    **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translate.alibaba.com
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
                :param professional_field: str, default 'message', choose from ("general",)
        :return: str or dict
        """

        use_domain = kwargs.get('professional_field', 'general')
        if use_domain not in self.professional_field:
            raise TranslatorError

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
        if not (
                self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.csrf_token):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            self.get_language_url = f'https:{re.compile(self.get_language_pattern).search(host_html).group()}'
            lang_html = self.session.get(self.get_language_url, headers=self.host_headers, timeout=timeout).text
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(lang_html, **debug_lang_kwargs)
            self.detail_language_map = self.get_d_lang_map(lang_html)

            _ = self.session.get(self.csrf_url, headers=self.host_headers, timeout=timeout)
            self.csrf_token = self.session.get(self.csrf_url, headers=self.host_headers, timeout=timeout).json()
            self.api_headers.update({self.csrf_token['headerName']: self.csrf_token['token']})

        from_language, to_language = self.check_language(from_language, to_language, self.language_map, self.output_zh)
        files_data = {
            'query': (None, query_text),
            'srcLang': (None, from_language),
            'tgtLang': (None, to_language),
            '_csrf': (None, self.csrf_token['token']),
            'domain': (None, self.professional_field[0]),
        }  # Content-Type: multipart/form-data
        r = self.session.post(self.api_url, files=files_data, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['data']['translateText']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translate.alibaba.com
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
        use_domain = kwargs.get('professional_field', 'general')
        if use_domain not in self.professional_field:
            raise TranslatorError
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
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.csrf_token):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(proxies)
            host_html = await (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text()
            self.get_language_url = f'https:{re.compile(self.get_language_pattern).search(host_html).group()}'
            lang_html = await (
                await self.async_session.get(self.get_language_url, headers=self.host_headers, timeout=timeout)).text()
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(lang_html, **debug_lang_kwargs)
            self.detail_language_map = self.get_d_lang_map(lang_html)

            _ = await self.async_session.get(self.csrf_url, headers=self.host_headers, timeout=timeout)
            self.csrf_token =  await (
                await self.async_session.get(self.csrf_url, headers=self.host_headers, timeout=timeout)).json()
            self.api_headers.update({self.csrf_token['headerName']: self.csrf_token['token']})

        from_language, to_language = self.check_language(from_language, to_language, self.language_map, self.output_zh)
        # Content-Type: multipart/form-data
        form = aiohttp.FormData()
        form.add_field('query', query_text)
        form.add_field('srcLang', from_language)
        form.add_field('tgtLang', to_language)
        form.add_field('_csrf', self.csrf_token['token'])
        form.add_field('domain', self.professional_field[0])
        r = await self.async_session.post(self.api_url, data=form, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data =  await r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['data']['translateText']
