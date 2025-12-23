import asyncio
import json
import re
import time
import urllib.parse
from typing import Union, List

import exejs
import lxml.etree as lxml_etree

from translators.base import Tse, LangMapKwargsType, TranslatorError, ApiKwargsType


class GoogleV1(Tse):
    def __init__(self, server_region='EN'):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = None
        self.cn_host_url = 'https://translate.google.cn'
        self.en_host_url = 'https://translate.google.com'
        self.api_url = None
        self.server_region = server_region
        self.host_headers = None
        self.language_map = None
        self.session = None
        self.query_count = 0
        self.output_zh = 'zh-CN'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    @staticmethod
    def _xr(a: int, b: str) -> int:
        size_b = len(b)
        c = 0
        while c < size_b - 2:
            d = b[c + 2]
            d = ord(d[0]) - 87 if 'a' <= d else int(d)
            d = (a % 2 ** 32) >> d if '+' == b[c + 1] else a << d
            a = a + d & (2 ** 32 - 1) if '+' == b[c] else a ^ d
            c += 3
        return a

    @staticmethod
    def _ints(text: str) -> List[int]:
        ints = []
        for v in text:
            int_v = ord(v)
            if int_v < 2 ** 16:
                ints.append(int_v)
            else:
                # unicode, emoji
                ints.append(int((int_v - 2 ** 16) / 2 ** 10 + 55296))
                ints.append(int((int_v - 2 ** 16) % 2 ** 10 + 56320))
        return ints

    def acquire(self, text: str, tkk: str) -> str:
        ints = self._ints(text)
        size = len(ints)
        e = []
        g = 0

        while g < size:
            l = ints[g]
            if l < 2 ** 7:  # 128(ascii)
                e.append(l)
            else:
                if l < 2 ** 11:  # 2048
                    e.append(l >> 6 | 192)
                else:
                    if (l & 64512) == 55296 and g + 1 < size and ints[g + 1] & 64512 == 56320:
                        g += 1
                        l = 65536 + ((l & 1023) << 10) + (ints[g] & 1023)
                        e.append(l >> 18 | 240)
                        e.append(l >> 12 & 63 | 128)
                    else:
                        e.append(l >> 12 | 224)
                    e.append(l >> 6 & 63 | 128)
                e.append(l & 63 | 128)
            g += 1

        b = tkk if tkk != '0' else ''
        d = b.split('.')
        b = int(d[0]) if len(d) > 1 else 0

        a = b
        for value in e:
            a += value
            a = self._xr(a, '+-a^+6')
        a = self._xr(a, '+-3^+b+-f')
        a ^= int(d[1]) if len(d) > 1 else 0
        if a < 0:
            a = (a & (2 ** 31 - 1)) + 2 ** 31
        a %= int(1E6)
        return '{}.{}'.format(a, a ^ b)

    @Tse.debug_language_map
    def get_language_map(self, host_html: str, **kwargs: LangMapKwargsType) -> dict:
        et = lxml_etree.HTML(host_html)
        lang_list = sorted(list(set(et.xpath('//*/@data-language-code'))))
        return {}.fromkeys(lang_list, lang_list)

    def get_tkk(self, host_html: str) -> str:
        return re.compile("tkk:'(.*?)'").findall(host_html)[0]

    @Tse.time_stat
    @Tse.check_query
    def google_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                   **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translate.google.com, https://translate.google.cn.
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
                :param if_use_cn_host: bool, default None.
                :param reset_host_url: str, default None.
                :param if_check_reset_host_url: bool, default True.
        :return: str or dict
        """

        reset_host_url = kwargs.get('reset_host_url', None)
        if reset_host_url and reset_host_url != self.host_url:
            if kwargs.get('if_check_reset_host_url', True) and not reset_host_url[:25] == 'https://translate.google.':
                raise TranslatorError
            self.host_url = reset_host_url.strip('/')
        else:
            use_cn_condition = kwargs.get('if_use_cn_host', None) or self.server_region == 'CN'
            self.host_url = self.cn_host_url if use_cn_condition else self.en_host_url

        if self.host_url[-2:] == 'cn':
            raise TranslatorError('Google service was offline in inland of China on Oct 2022.')

        self.host_headers = self.host_headers or self.get_headers(self.host_url, if_api=False)

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
        if not (self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.api_url):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text

            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, self.session, timeout, **debug_lang_kwargs)
            from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                             output_zh=self.output_zh)

            tkk = self.get_tkk(host_html)
            tk = self.acquire(query_text, tkk)

            api_url_part_1 = '/translate_a/single?client={0}&sl={1}&tl={2}&hl=zh-CN&dt=at&dt=bd&dt=ex'.format('webapp',
                                                                                                              from_language,
                                                                                                              to_language)
            api_url_part_2 = '&dt=ld&dt=md&dt=qca&dt=rw&dt=rm&dt=ss&dt=t&ie=UTF-8&oe=UTF-8&source=bh&ssel=0&tsel=0&kc=1'
            api_url_part_3 = '&tk={0}&q={1}'.format(tk, urllib.parse.quote(query_text))
            self.api_url = ''.join([self.host_url, api_url_part_1, api_url_part_2, api_url_part_3])  # [t,webapp]

        r = self.session.get(self.api_url, headers=self.host_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else ''.join([item[0] for item in data[0] if isinstance(item[0], str)])

    @Tse.time_stat
    @Tse.check_query
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translate.google.com, https://translate.google.cn.
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
                :param if_use_cn_host: bool, default None.
                :param reset_host_url: str, default None.
                :param if_check_reset_host_url: bool, default True.
        :return: str or dict
        """

        reset_host_url = kwargs.get('reset_host_url', None)
        if reset_host_url and reset_host_url != self.host_url:
            if kwargs.get('if_check_reset_host_url', True) and not reset_host_url[:25] == 'https://translate.google.':
                raise TranslatorError
            self.host_url = reset_host_url.strip('/')
        else:
            use_cn_condition = kwargs.get('if_use_cn_host', None) or self.server_region == 'CN'
            self.host_url = self.cn_host_url if use_cn_condition else self.en_host_url

        if self.host_url[-2:] == 'cn':
            raise TranslatorError('Google service was offline in inland of China on Oct 2022.')

        self.host_headers = self.host_headers or self.get_headers(self.host_url, if_api=False)

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
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.api_url):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(http_client, proxies)
            host_html = (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text

            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, **debug_lang_kwargs)
            from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                             output_zh=self.output_zh)

            tkk = self.get_tkk(host_html)
            tk = self.acquire(query_text, tkk)

            api_url_part_1 = '/translate_a/single?client={0}&sl={1}&tl={2}&hl=zh-CN&dt=at&dt=bd&dt=ex'.format('webapp',
                                                                                                              from_language,
                                                                                                              to_language)
            api_url_part_2 = '&dt=ld&dt=md&dt=qca&dt=rw&dt=rm&dt=ss&dt=t&ie=UTF-8&oe=UTF-8&source=bh&ssel=0&tsel=0&kc=1'
            api_url_part_3 = '&tk={0}&q={1}'.format(tk, urllib.parse.quote(query_text))
            self.api_url = ''.join([self.host_url, api_url_part_1, api_url_part_2, api_url_part_3])  # [t,webapp]

        r = await self.async_session.get(self.api_url, headers=self.host_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else ''.join([item[0] for item in data[0] if isinstance(item[0], str)])


class GoogleV2(Tse):
    def __init__(self, server_region='EN'):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = None
        self.cn_host_url = 'https://translate.google.cn'
        self.en_host_url = 'https://translate.google.com'
        self.api_url = None
        self.api_url_path = '/_/TranslateWebserverUi/data/batchexecute'
        self.consent_url = 'https://consent.google.com/save'
        self.server_region = server_region
        self.host_headers = None
        self.api_headers = None
        self.language_map = None
        self.session = None
        self.rpcid = 'MkEWBc'
        self.query_count = 0
        self.output_zh = 'zh-CN'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, host_html: str, **kwargs: LangMapKwargsType) -> dict:
        et = lxml_etree.HTML(host_html)
        lang_list = sorted(list(set(et.xpath('//*/@data-language-code'))))
        return {}.fromkeys(lang_list, lang_list)

    def get_rpc(self, query_text: str, from_language: str, to_language: str) -> dict:
        param = json.dumps([[query_text, from_language, to_language, True], [1]])
        rpc = json.dumps([[[self.rpcid, param, None, "generic"]]])
        return {'f.req': rpc}

    def get_info(self, host_html: str) -> dict:
        data_str = re.compile(r'window.WIZ_global_data = (.*?);</script>').findall(host_html)[0]
        data = exejs.evaluate(data_str)
        return {'bl': data['cfb2h'], 'f.sid': data['FdrFJe']}

    def get_consent_data(self, consent_html: str) -> dict:  # 142 merged but not verify.
        et = lxml_etree.HTML(consent_html)
        form_element = et.xpath('.//form[1]')
        self.consent_url = form_element[0].attrib.get('action') if form_element else self.consent_url

        input_elements = form_element[0].xpath('.//input[@type="hidden"]')
        data = {e.attrib.get('name'): e.attrib.get('value') for e in input_elements}
        return data

    @Tse.time_stat
    @Tse.check_query
    def google_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                   **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translate.google.com, https://translate.google.cn.
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
                :param reset_host_url: str, default None.
                :param if_check_reset_host_url: bool, default True.
        :return: str or dict
        """

        reset_host_url = kwargs.get('reset_host_url', None)
        if reset_host_url and reset_host_url != self.host_url:
            if kwargs.get('if_check_reset_host_url', True) and not reset_host_url[:25] == 'https://translate.google.':
                raise TranslatorError
            self.host_url = reset_host_url.strip('/')
        else:
            use_cn_condition = kwargs.get('if_use_cn_host', None) or self.server_region == 'CN'
            self.host_url = self.cn_host_url if use_cn_condition else self.en_host_url

        if self.host_url[-2:] == 'cn':
            raise TranslatorError('Google service was offline in inland of China on Oct 2022.')

        self.api_url = f'{self.host_url}{self.api_url_path}'
        self.host_headers = self.host_headers or self.get_headers(self.host_url, if_api=False)  # reuse cookie header
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_referer_for_host=True, if_ajax_for_api=True)

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
            r = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            if urllib.parse.urlparse(self.consent_url).hostname == urllib.parse.urlparse(str(r.url)).hostname:
                form_data = self.get_consent_data(r.text)
                host_html = self.session.post(self.consent_url, data=form_data, headers=self.host_headers,
                                              timeout=timeout).text
            else:
                host_html = r.text
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        rpc_data = self.get_rpc(query_text, from_language, to_language)
        rpc_data = urllib.parse.urlencode(rpc_data)
        r = self.session.post(self.api_url, headers=self.api_headers, data=rpc_data, timeout=timeout)
        r.raise_for_status()
        json_data = json.loads(r.text[6:])
        data = json.loads(json_data[0][2])
        time.sleep(sleep_seconds)
        self.query_count += 1
        return {'data': data} if is_detail_result else ' '.join(
            [x[0] for x in (data[1][0][0][5] or data[1][0]) if x[0]])

    @Tse.time_stat
    @Tse.check_query
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translate.google.com, https://translate.google.cn.
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
                :param reset_host_url: str, default None.
                :param if_check_reset_host_url: bool, default True.
        :return: str or dict
        """

        reset_host_url = kwargs.get('reset_host_url', None)
        if reset_host_url and reset_host_url != self.host_url:
            if kwargs.get('if_check_reset_host_url', True) and not reset_host_url[:25] == 'https://translate.google.':
                raise TranslatorError
            self.host_url = reset_host_url.strip('/')
        else:
            use_cn_condition = kwargs.get('if_use_cn_host', None) or self.server_region == 'CN'
            self.host_url = self.cn_host_url if use_cn_condition else self.en_host_url

        if self.host_url[-2:] == 'cn':
            raise TranslatorError('Google service was offline in inland of China on Oct 2022.')

        self.api_url = f'{self.host_url}{self.api_url_path}'
        self.host_headers = self.host_headers or self.get_headers(self.host_url, if_api=False)  # reuse cookie header
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_referer_for_host=True, if_ajax_for_api=True)

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
            r = await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            if urllib.parse.urlparse(self.consent_url).hostname == urllib.parse.urlparse(str(r.url)).hostname:
                form_data = self.get_consent_data(r.text)
                host_html = (await self.async_session.post(self.consent_url, data=form_data, headers=self.host_headers,
                                                           timeout=timeout)).text
            else:
                host_html = r.text
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        rpc_data = self.get_rpc(query_text, from_language, to_language)
        rpc_data = urllib.parse.urlencode(rpc_data)
        r = await self.async_session.post(self.api_url, headers=self.api_headers, data=rpc_data, timeout=timeout)
        r.raise_for_status()
        json_data = json.loads(r.text[6:])
        data = json.loads(json_data[0][2])
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return {'data': data} if is_detail_result else ' '.join(
            [x[0] for x in (data[1][0][0][5] or data[1][0]) if x[0]])
