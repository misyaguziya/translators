import asyncio
import base64
import hashlib
import random
import re
import time
import urllib.parse
from typing import Optional, Union

import lxml.etree as lxml_etree

from translators.base import Tse, LangMapKwargsType, TranslatorError, ApiKwargsType, AsyncSessionType, SessionType


class YoudaoV1(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://fanyi.youdao.com'
        self.api_url = 'https://fanyi.youdao.com/translate_o?smartresult=dict&smartresult=rule'
        self.language_url = 'https://api-overmind.youdao.com/openapi/get/luna/dict/luna-front/prod/langType'
        self.get_sign_old_url = 'https://shared.ydstatic.com/fanyi/newweb/v1.0.29/scripts/newweb/fanyi.min.js'
        self.get_sign_url = None
        self.get_sign_pattern = 'https://shared.ydstatic.com/fanyi/newweb/(.*?)/scripts/newweb/fanyi.min.js'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True)
        self.language_map = None
        self.session = None
        self.sign_key = None
        self.query_count = 0
        self.output_zh = 'zh-CHS'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    # @Tse.debug_language_map
    # def get_language_map(self, host_html: str, **kwargs: LangMapKwargsType) -> dict:
    #     et = lxml_etree.HTML(host_html)
    #     lang_list = et.xpath('//*[@id="languageSelect"]/li/@data-value')
    #     lang_list = [(x.split('2')[0], [x.split('2')[1]]) for x in lang_list if '2' in x]
    #     lang_map = dict(map(lambda x: x, lang_list))
    #     lang_map.pop('zh-CHS')
    #     lang_map.update({'zh-CHS': list(lang_map.keys())})
    #     return lang_map

    @Tse.debug_language_map
    def get_language_map(self, lang_url: str, ss: SessionType, headers: dict, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        data = ss.get(lang_url, headers=headers, timeout=timeout).json()
        lang_list = sorted([it['code'] for it in data['data']['value']['textTranslate']['specify']])
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, lang_url: str, ss: AsyncSessionType, headers: dict, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        data = await(await ss.get(lang_url, headers=headers, timeout=timeout)).json()
        lang_list = sorted([it['code'] for it in data['data']['value']['textTranslate']['specify']])
        return {}.fromkeys(lang_list, lang_list)

    def get_sign_key(self, host_html: str, ss: SessionType, timeout: Optional[float]) -> str:
        try:
            if not self.get_sign_url:
                self.get_sign_url = re.compile(self.get_sign_pattern).search(host_html).group()
            r = ss.get(self.get_sign_url, headers=self.host_headers, timeout=timeout)
            r.raise_for_status()
        except:
            r = ss.get(self.get_sign_old_url, headers=self.host_headers, timeout=timeout)
            r.raise_for_status()
        sign = re.compile('md5\\("fanyideskweb" \\+ e \\+ i \\+ "(.*?)"\\)').findall(r.text)
        return sign[0] if sign and sign != [''] else "Ygy_4c=r#e#4EX^NUGUc5"  # v1.1.10

    async def get_sign_key_async(self, host_html: str, ss: AsyncSessionType, timeout: Optional[float]) -> str:
        try:
            if not self.get_sign_url:
                self.get_sign_url = re.compile(self.get_sign_pattern).search(host_html).group()
            r = await ss.get(self.get_sign_url, headers=self.host_headers, timeout=timeout)
            r.raise_for_status()
        except:
            r = await ss.get(self.get_sign_old_url, headers=self.host_headers, timeout=timeout)
            r.raise_for_status()
        sign = re.compile('md5\\("fanyideskweb" \\+ e \\+ i \\+ "(.*?)"\\)').findall(await r.text())
        return sign[0] if sign and sign != [''] else "Ygy_4c=r#e#4EX^NUGUc5"

    def get_form(self, query_text: str, from_language: str, to_language: str, sign_key: str) -> dict:
        ts = str(self.get_timestamp())
        salt = str(ts) + str(random.randrange(0, 10))
        sign_text = ''.join(['fanyideskweb', query_text, salt, sign_key])
        sign = hashlib.md5(sign_text.encode()).hexdigest()
        bv = hashlib.md5(self.api_headers['User-Agent'][8:].encode()).hexdigest()
        form = {
            'i': query_text,
            'from': from_language,
            'to': to_language,
            'lts': ts,  # r = "" + (new Date).getTime()
            'salt': salt,  # i = r + parseInt(10 * Math.random(), 10)
            'sign': sign,  # n.md5("fanyideskweb" + e + i + "n%A-rKaT5fb[Gy?;N5@Tj"),e=text
            'bv': bv,  # n.md5(navigator.appVersion)
            'smartresult': 'dict',
            'client': 'fanyideskweb',
            'doctype': 'json',
            'version': '2.1',
            'keyfrom': 'fanyi.web',
            'action': 'FY_BY_REALTlME',
            # not time.["FY_BY_REALTlME", "FY_BY_DEFAULT", "FY_BY_CLICKBUTTION", "lan-select"]
            # 'typoResult': 'false'
        }
        return form

    @Tse.time_stat
    @Tse.check_query
    def youdao_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                   **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.youdao.com
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
        if not (self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.sign_key):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            self.sign_key = self.get_sign_key(host_html, self.session, timeout)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.language_url, self.session, self.host_headers, timeout,
                                                      **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        form = self.get_form(query_text, from_language, to_language, self.sign_key)
        r = self.session.post(self.api_url, data=form, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join(
            [' '.join([it['tgt'] for it in item]) for item in data['translateResult']])

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.youdao.com
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
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.sign_key):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(proxies)
            host_html = await (
                await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text()
            self.sign_key = await self.get_sign_key_async(host_html, self.async_session, timeout)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(self.language_url, self.async_session,
                                                                  self.host_headers, timeout, **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        form = self.get_form(query_text, from_language, to_language, self.sign_key)
        r = await self.async_session.post(self.api_url, data=form, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = await  r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join(
            [' '.join([it['tgt'] for it in item]) for item in data['translateResult']])


class YoudaoV2(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://fanyi.youdao.com'
        self.api_url = 'https://dict.youdao.com/webtranslate'
        self.api_host = 'https://dict.youdao.com'
        self.get_js_url = None
        self.get_js_pattern = 'js/app.(.*?).js'
        self.get_sign_url = None
        self.get_sign_pattern = ''
        self.login_url = 'https://dict.youdao.com/login/acc/query/accountinfo'
        self.language_url = 'https://api-overmind.youdao.com/openapi/get/luna/dict/luna-front/prod/langType'
        self.domain_url = 'https://doctrans-service.youdao.com/common/enums/list?key=domain'
        self.get_key_url = 'https://dict.youdao.com/webtranslate/key'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True)
        self.api_headers.update({'Host': self.api_host})
        self.language_map = None
        self.session = None
        self.professional_field = ('0', '1', '2', '3')
        self.professional_field_map = None
        self.default_key = None
        self.secret_key = None
        self.decode_key = None
        self.decode_iv = None
        self.query_count = 0
        self.output_zh = 'zh-CHS'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, lang_url: str, ss: SessionType, headers: dict, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        data = ss.get(lang_url, headers=headers, timeout=timeout).json()
        lang_list = sorted([it['code'] for it in data['data']['value']['textTranslate']['specify']])
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, lang_url: str, ss: AsyncSessionType, headers: dict, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        data = await (await ss.get(lang_url, headers=headers, timeout=timeout)).json()
        lang_list = sorted([it['code'] for it in data['data']['value']['textTranslate']['specify']])
        return {}.fromkeys(lang_list, lang_list)

    def get_default_key(self, js_html: str) -> str:
        return re.compile('="webfanyi-key-getter",(\\w+)="(\\w+)";').search(js_html).group(2)

    def get_sign(self, key: str, timestmp: int) -> str:
        value = f'client=fanyideskweb&mysticTime={timestmp}&product=webfanyi&key={key}'
        return hashlib.md5(value.encode()).hexdigest()

    def get_payload(self, keyid: str, key: str, timestamp: int, **kwargs: str) -> dict:
        if keyid not in ('webfanyi-key-getter', 'webfanyi'):
            raise TranslatorError

        payload = {
            'keyid': keyid,
            'mysticTime': str(timestamp),
            'sign': self.get_sign(key, timestamp),
            'client': 'fanyideskweb',
            'product': 'webfanyi',
            'appVersion': '1.0.0',
            'vendor': 'web',
            'keyfrom': 'fanyi.web',
            'pointParam': 'client,mysticTime,product',
        }
        return {**kwargs, **payload} if keyid == 'webfanyi' else payload

    def decrypt(self, cipher_text: str, decrypt_dictionary: dict) -> str:
        _ciphertext = ''.join(list(map(lambda k: decrypt_dictionary[k], cipher_text)))
        return base64.b64decode(_ciphertext).decode()

    @Tse.uncertified
    @Tse.time_stat
    @Tse.check_query
    def youdao_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                   **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.youdao.com
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
                :param professional_field: str, default '0'. Choose from ('0','1','2','3')
        :return: str or dict
        """

        domain = kwargs.get('professional_field', '0')
        if domain not in self.professional_field:
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
                self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.secret_key):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            _ = self.session.get(self.login_url, headers=self.host_headers, timeout=timeout)
            self.professional_field_map = \
                self.session.get(self.domain_url, headers=self.host_headers, timeout=timeout).json()['data']
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.language_url, self.session, self.host_headers, timeout,
                                                      **debug_lang_kwargs)

            self.get_js_url = ''.join([self.host_url, '/', re.compile(self.get_js_pattern).search(host_html).group()])
            js_html = self.session.get(self.get_js_url, headers=self.host_headers, timeout=timeout).text

            self.decode_key = re.compile('decodeKey:"(.*?)",').search(js_html).group(1)
            self.decode_iv = re.compile('decodeIv:"(.*?)",').search(js_html).group(1)
            self.default_key = self.get_default_key(js_html)

            params = self.get_payload(keyid='webfanyi-key-getter', key=self.default_key, timestamp=self.get_timestamp())
            key_r = self.session.get(self.get_key_url, params=params, headers=self.api_headers, timeout=timeout)
            self.secret_key = key_r.json()['data']['secretKey']

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        translate_form = {
            'i': query_text,
            'from': from_language,
            'to': to_language if from_language != 'auto' else '',
            'domain': domain,
            'dictResult': 'true',
        }
        payload = self.get_payload(keyid='webfanyi', key=self.default_key, timestamp=self.get_timestamp(),
                                   **translate_form)
        payload = urllib.parse.urlencode(payload)
        r = self.session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()  # raise TranslatorError('YoudaoV2 has not been completed.')  # TODO
        data = self.decrypt(r.text, decrypt_dictionary={})
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else str(data)  # TODO

    @Tse.uncertified_async
    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.youdao.com
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
                :param professional_field: str, default '0'. Choose from ('0','1','2','3')
        :return: str or dict
        """

        domain = kwargs.get('professional_field', '0')
        if domain not in self.professional_field:
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
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.secret_key):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(proxies)
            host_html = await (
                await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text()
            _ = await self.async_session.get(self.login_url, headers=self.host_headers, timeout=timeout)
            self.professional_field_map =  await (await  (
                await self.async_session.get(self.domain_url, headers=self.host_headers, timeout=timeout)).json())[
                'data']
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(self.language_url, self.async_session,
                                                                  self.host_headers, timeout, **debug_lang_kwargs)

            self.get_js_url = ''.join([self.host_url, '/', re.compile(self.get_js_pattern).search(host_html).group()])
            js_html = await (
                await self.async_session.get(self.get_js_url, headers=self.host_headers, timeout=timeout)).text()

            self.decode_key = re.compile('decodeKey:"(.*?)",').search(js_html).group(1)
            self.decode_iv = re.compile('decodeIv:"(.*?)",').search(js_html).group(1)
            self.default_key = self.get_default_key(js_html)

            params = self.get_payload(keyid='webfanyi-key-getter', key=self.default_key, timestamp=self.get_timestamp())
            key_r = await self.async_session.get(self.get_key_url, params=params, headers=self.api_headers,
                                                 timeout=timeout)
            self.secret_key = (await key_r.json())['data']['secretKey']

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        translate_form = {
            'i': query_text,
            'from': from_language,
            'to': to_language if from_language != 'auto' else '',
            'domain': domain,
            'dictResult': 'true',
        }
        payload = self.get_payload(keyid='webfanyi', key=self.default_key, timestamp=self.get_timestamp(),
                                   **translate_form)
        payload = urllib.parse.urlencode(payload)
        r = await self.async_session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = self.decrypt(await r.text(), decrypt_dictionary={})
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else str(data)


class YoudaoV3(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://ai.youdao.com/product-fanyi-text.s'
        self.api_url = 'https://aidemo.youdao.com/trans'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True)
        self.language_map = None
        self.session = None
        self.query_count = 0
        self.output_zh = 'zh-CHS'
        self.input_limit = int(1e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, host_html: str, **kwargs: LangMapKwargsType) -> dict:
        et = lxml_etree.HTML(host_html)
        lang_list = et.xpath('//*[@id="customSelectOption"]/li/a/@val')
        lang_list = sorted([it.split('2')[1] for it in lang_list if f'{self.output_zh}2' in it])
        return {**{lang: [self.output_zh] for lang in lang_list}, **{self.output_zh: lang_list}}

    @Tse.time_stat
    @Tse.check_query
    def youdao_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                   **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://ai.youdao.com/product-fanyi-text.s
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

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)
        if from_language == 'auto':
            from_language = to_language = 'Auto'

        payload = {'q': query_text, 'from': from_language, 'to': to_language}
        payload = urllib.parse.urlencode(payload)
        r = self.session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['translation'][0]

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://ai.youdao.com/product-fanyi-text.s
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
            self.async_session = Tse.get_async_client_session(proxies)
            host_html = await (
                await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text()
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(host_html, **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)
        if from_language == 'auto':
            from_language = to_language = 'Auto'

        payload = {'q': query_text, 'from': from_language, 'to': to_language}
        payload = urllib.parse.urlencode(payload)
        r = await self.async_session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = await r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['translation'][0]
