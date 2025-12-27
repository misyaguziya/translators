import asyncio
import base64
import json
import random
import re
import time
import uuid
from typing import Optional, Union

import cryptography.hazmat.primitives.asymmetric.padding as cry_asym_padding
import cryptography.hazmat.primitives.hashes as cry_hashes
import cryptography.hazmat.primitives.serialization as cry_serialization

from translators.base import Tse, LangMapKwargsType, ApiKwargsType, AsyncSessionType, SessionType


class NiutransV1(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'http://display.niutrans.com'  # must http
        self.api_url = 'http://display.niutrans.com/niutrans/textTranslation'
        self.cookie_url = 'http://display.niutrans.com/niutrans/user/getAccountAdmin?locale=zh-CN'
        self.user_url = 'http://display.niutrans.com/niutrans/user/getGuestUser'
        self.key_url = 'http://display.niutrans.com/niutrans/user/getOnePublicKey'
        self.token_url = 'http://display.niutrans.com/niutrans/login'
        self.info_url = 'http://display.niutrans.com/niutrans/user/getUserInfoByToken'
        self.get_language_url = 'http://display.niutrans.com/niutrans/translServiceInfo/getAllLanguage'
        self.detect_language_url = 'http://display.niutrans.com/niutrans/textLanguageDetect'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = None
        self.session = None
        self.language_map = None
        # self.detail_language_map = None
        self.account_info = None
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, lang_url: str, ss: SessionType, headers: dict, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        detail_lang_map = ss.get(lang_url, headers=headers, timeout=timeout).json()
        lang_list = sorted(set([item['languageAbbreviation'] for item in detail_lang_map['data']]))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, lang_url: str, ss: AsyncSessionType, headers: dict, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        detail_lang_map = await (await ss.get(lang_url, headers=headers, timeout=timeout)).json()
        lang_list = sorted(set([item['languageAbbreviation'] for item in detail_lang_map['data']]))
        return {}.fromkeys(lang_list, lang_list)

    def encrypt_rsa(self, message_text: str, public_key_text: str) -> str:
        public_key_pem = ''.join(['-----BEGIN PUBLIC KEY-----\n', public_key_text, '\n-----END PUBLIC KEY-----'])
        public_key_object = cry_serialization.load_pem_public_key(public_key_pem.encode())
        cipher_text = base64.b64encode(public_key_object.encrypt(
            plaintext=message_text.encode(),
            # padding=cry_asym_padding.PKCS1v15()
            padding=cry_asym_padding.OAEP(
                mgf=cry_asym_padding.MGF1(algorithm=cry_hashes.SHA256()),
                algorithm=cry_hashes.SHA256(),
                label=None
            )
        )).decode()
        return cipher_text  # TODO

    @Tse.uncertified
    @Tse.time_stat
    @Tse.check_query
    def niutrans_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                     **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        http://display.niutrans.com
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
        if not (
                self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.account_info and self.api_headers):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            _ = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            _ = self.session.options(self.cookie_url, headers=self.host_headers, timeout=timeout)

            user_data = self.session.get(self.user_url, headers=self.host_headers, timeout=timeout).json()
            key_data = self.session.get(self.key_url, headers=self.host_headers, timeout=timeout).json()
            guest_info = {
                'username': user_data['data']['username'].strip(),
                'password': self.encrypt_rsa(message_text=user_data['data']['password'],
                                             public_key_text=key_data['data']),
                'publicKey': key_data['data'],
                'symbol': '',
            }
            r_tk = self.session.post(self.token_url, json=guest_info, headers=self.host_headers, timeout=timeout)
            token_data = r_tk.json()

            self.account_info = {**guest_info, **token_data['data']}
            self.api_headers = {**self.host_headers, **{'Jwt': self.account_info['token']}}
            self.session.cookies.update({'Admin-Token': self.account_info['token']})
            # info_data = ss.get(self.info_url, headers=self.host_headers, timeout=timeout).json()

            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.get_language_url, self.session, self.api_headers, timeout,
                                                      **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)
        if from_language == 'auto':
            res = self.session.post(self.detect_language_url, json={'src_text': query_text}, headers=self.api_headers,
                                    timeout=timeout)
            from_language = res.json()['data']['language']

        payload = {
            'src_text': query_text, 'from': from_language, 'to': to_language,
            'contrastFlag': 'true', 'termDictionaryLibraryId': '', 'translationMemoryLibraryId': '',
        }
        r = self.session.post(self.api_url, json=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join(
            [' '.join([it['data'] for it in item['sentences']]) for item in data['data']])

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        http://display.niutrans.com
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
        if not (
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.account_info and self.api_headers):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(proxies)
            _ = await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            _ = await self.async_session.options(self.cookie_url, headers=self.host_headers, timeout=timeout)

            user_data = await (await self.async_session.get(self.user_url, headers=self.host_headers, timeout=timeout)).json()
            key_data = await (await self.async_session.get(self.key_url, headers=self.host_headers, timeout=timeout)).json()
            guest_info = {
                'username': user_data['data']['username'].strip(),
                'password': self.encrypt_rsa(message_text=user_data['data']['password'],
                                             public_key_text=key_data['data']),
                'publicKey': key_data['data'],
                'symbol': '',
            }
            r_tk = await self.async_session.post(self.token_url, json=guest_info, headers=self.host_headers,
                                                 timeout=timeout)
            token_data = await r_tk.json()

            self.account_info = {**guest_info, **token_data['data']}
            self.api_headers = {**self.host_headers, **{'Jwt': self.account_info['token']}}
            self.async_session.cookie_jar.update_cookies({'Admin-Token': self.account_info['token']})
            # info_data = ss.get(self.info_url, headers=self.host_headers, timeout=timeout).json()

            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(self.get_language_url, self.async_session,
                                                                  self.api_headers, timeout,
                                                                  **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)
        if from_language == 'auto':
            res = await self.async_session.post(self.detect_language_url, json={'src_text': query_text},
                                                headers=self.api_headers,
                                                timeout=timeout)
            from_language = (await res.json())['data']['language']

        payload = {
            'src_text': query_text, 'from': from_language, 'to': to_language,
            'contrastFlag': 'true', 'termDictionaryLibraryId': '', 'translationMemoryLibraryId': '',
        }
        r = await self.async_session.post(self.api_url, json=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = await  r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join(
            [' '.join([it['data'] for it in item['sentences']]) for item in data['data']])


class NiutransV2(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.home_url = 'https://niutrans.com'
        self.host_url = 'https://niutrans.com/trans?type=text'
        self.api_url = 'https://test.niutrans.com/NiuTransServer/testaligntrans'
        self.get_language_url = 'https://niutrans.com/NiuTransFrontPage/language/getAllLanguage'
        self.detect_language_url = 'https://test.niutrans.com/NiuTransServer/language'
        self.login_url = 'https://niutrans.com/NiuTransConsole/user/isLogin'
        self.geetest_host_url = 'https://www.geetest.com'
        self.geetest_captcaha_url = 'https://www.geetest.com/adaptive-captcha-demo'
        self.geetest_load_url = 'https://gcaptcha4.geetest.com/load'
        self.geetest_verify_url = 'https://gcaptcha4.geetest.com/verify'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_json_for_api=True)
        self.session = None
        self.language_map = None
        self.captcha_id = None  # '24f56dc13c40dc4a02fd0318567caef5'
        self.geetest_load_data = None
        self.geetest_verify_data = {
            "pass_token":"dd2b77a1be40d1158cd7141501b6d843",
        }
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, lang_url: str, ss: SessionType, headers: dict, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        d_lang_map = ss.get(lang_url, headers=headers, timeout=timeout).json()
        lang_list = sorted(set([it['code'] for item in d_lang_map['languageList'] for it in item['result']]))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, lang_url: str, ss: AsyncSessionType, headers: dict, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        d_lang_map = await (await ss.get(lang_url, headers=headers, timeout=timeout)).json()
        lang_list = sorted(set([it['code'] for item in d_lang_map['languageList'] for it in item['result']]))
        return {}.fromkeys(lang_list, lang_list)

    def get_captcha_id(self, captcha_url: str, ss: SessionType, headers: dict, timeout: Optional[float]):
        captcha_host_html = ss.get(captcha_url, headers=headers, timeout=timeout).text
        captcha_js_url_path = re.compile('/_next/static/(.*?)/pages/adaptive-captcha-demo.js').search(
            captcha_host_html).group(0)
        captcha_js_url = f'{self.geetest_host_url}{captcha_js_url_path}'
        captcha_js_html = ss.get(captcha_js_url, headers=headers, timeout=timeout).text
        captcha_id = re.compile('captchaId:"(.*?)",').search(captcha_js_html).group(1)
        return captcha_id

    async def get_captcha_id_async(self, captcha_url: str, ss: AsyncSessionType, headers: dict,
                                   timeout: Optional[float]):
        res = await ss.get(captcha_url, headers=headers, timeout=timeout)
        captcha_host_html = await res.text()
        captcha_js_url_path = re.compile('/_next/static/(.*?)/pages/adaptive-captcha-demo.js').search(
            captcha_host_html).group(0)
        captcha_js_url = f'{self.geetest_host_url}{captcha_js_url_path}'
        captcha_js_html = await (await ss.get(captcha_js_url, headers=headers, timeout=timeout)).text()
        captcha_id = re.compile('captchaId:"(.*?)",').search(captcha_js_html).group(1)
        return captcha_id

    def get_geetest_callback(self):
        return f'geetest_{int(self.get_timestamp() + int(random.random() * 1e4))}'

    def get_geetest_w(self, k=1088):
        pool = list('abcdef' + '0123456789')
        return ''.join(random.choices(pool, k=k))  # TODO

    def get_geetest_data(self, timeout):
        gl_params = {
            'callback': self.get_geetest_callback(),
            'captcha_id': self.captcha_id,
            'challenge': str(uuid.uuid4()),
            'client_type': 'web',  # 'h5'
            'lang': 'zh-cn',
        }
        r_gl = self.session.get(self.geetest_load_url, params=gl_params, headers=self.host_headers, timeout=timeout)
        self.geetest_load_data = json.loads(r_gl.text[22:-1])['data']

        gv_params = {
            'callback': self.get_geetest_callback(),
            'captcha_id': self.captcha_id,
            'client_type': 'web',  # 'h5'
            'lot_number': self.geetest_load_data['lot_number'],
            'payload': self.geetest_load_data['payload'],
            'process_token': self.geetest_load_data['process_token'],
            'payload_protocol': self.geetest_load_data['payload_protocol'],
            'pt': self.geetest_load_data['pt'],
            'w': self.get_geetest_w(),  # TODO
        }
        r_gv = self.session.get(self.geetest_verify_url, params=gv_params, headers=self.host_headers, timeout=timeout)
        self.geetest_verify_data = json.loads(r_gv.text[22:-1])['data']['seccode']
        return

    async def get_geetest_data_async(self, ss: AsyncSessionType, timeout):
        gl_params = {
            'callback': self.get_geetest_callback(),
            # 'captcha_id': self.captcha_id,
            'challenge': str(uuid.uuid4()),
            'client_type': 'web',  # 'h5'
            'lang': 'zh-cn',
        }
        r_gl = await ss.get(self.geetest_load_url, params=gl_params, headers=self.host_headers, timeout=timeout)
        self.geetest_load_data = json.loads((await r_gl.text())[22:-1])['data']

        gv_params = {
            'callback': self.get_geetest_callback(),
            # 'captcha_id': self.captcha_id,
            'client_type': 'web',  # 'h5'
            'lot_number': self.geetest_load_data['lot_number'],
            'payload': self.geetest_load_data['payload'],
            'process_token': self.geetest_load_data['process_token'],
            'payload_protocol': self.geetest_load_data['payload_protocol'],
            'pt': self.geetest_load_data['pt'],
            'w': self.get_geetest_w(),  # TODO
        }
        r_gv = await ss.get(self.geetest_verify_url, params=gv_params, headers=self.host_headers, timeout=timeout)
        self.geetest_verify_data = json.loads((await r_gv.text())[22:-1])['data']['seccode']
        return

    @Tse.uncertified
    @Tse.time_stat
    @Tse.check_query
    def niutrans_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                     **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://niutrans.com/trans?type=text
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
        if not (
                self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.captcha_id):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            _ = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            _ = self.session.get(self.login_url, headers=self.host_headers, timeout=timeout)
            self.captcha_id = self.get_captcha_id(self.geetest_captcaha_url, self.session, self.host_headers, timeout)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.get_language_url, self.session, self.api_headers, timeout,
                                                      **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)
        if from_language == 'auto':
            params = {
                'src_text': query_text,
                'time': self.get_timestamp(),
                'source': 'text',
            }
            res = self.session.get(self.detect_language_url, params=params, headers=self.host_headers, timeout=timeout)
            from_language = res.json()['language']

        # self.get_geetest_data(timeout)
        trans_params = {
            'src_text': query_text,
            'from': from_language,
            'to': to_language,
            'source': 'text',
            'dictNo': '',
            'memoryNo': '',
            'pass_token': self.geetest_verify_data['pass_token'],
            'time': self.get_timestamp(),
            'isUseDict': 0,
            'isUseMemory': 0,
        }
        r = self.session.get(self.api_url, params=trans_params, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['tgt_text']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://niutrans.com/trans?type=text
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
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(proxies)
            _ = await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            _ = await self.async_session.get(self.login_url, headers=self.host_headers, timeout=timeout)
            # self.captcha_id = await self.get_captcha_id_async(self.geetest_captcaha_url, self.async_session,
            #                                                   self.host_headers, timeout)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(self.get_language_url, self.async_session,
                                                                  self.api_headers, timeout,
                                                                  **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)
        if from_language == 'auto':
            params = {
                'src_text': query_text,
                'time': self.get_timestamp(),
                'source': 'text',
            }
            res = await self.async_session.get(self.detect_language_url, params=params, headers=self.host_headers,
                                               timeout=timeout)
            from_language = (await res.json(content_type=None))['language']
        # await self.get_geetest_data_async(self.async_session, timeout)
        trans_params = {
            'src_text': query_text,
            'from': from_language,
            'to': to_language,
            'source': 'text',
            'dictNo': '',
            'memoryNo': '',
            'pass_token': self.geetest_verify_data['pass_token'],
            'time': self.get_timestamp(),
            'isUseDict': 0,
            'isUseMemory': 0,
        }
        r = await self.async_session.get(self.api_url, params=trans_params, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = await r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['tgt_text']
