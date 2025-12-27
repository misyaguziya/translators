import asyncio
import base64
import hashlib
import json
import time
from typing import Optional, Union

import cryptography.hazmat.primitives.ciphers as cry_ciphers
import cryptography.hazmat.primitives.padding as cry_padding

from translators.base import Tse, LangMapKwargsType, ApiKwargsType, AsyncSessionType, SessionType


class Iciba(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://www.iciba.com/fy'
        self.api_url = 'https://ifanyi.iciba.com/index.php'
        self.host_headers = self.get_headers(self.host_url, if_api=False, if_ajax_for_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_ajax_for_api=True, if_json_for_api=False)
        self.language_headers = self.get_headers(self.host_url, if_api=False, if_json_for_api=True)
        self.language_map = None
        self.session = None
        self.sign_key = '6dVjYLFyzfkFkk'  # 'ifanyiweb8hc9s98e'
        self.encrypt_key = 'L4fBtD5fLC9FQw22'
        self.decrypt_key = 'aahc3TfyfCEmER33'
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(3e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, api_url: str, ss: SessionType, headers: dict, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        params = {'c': 'trans', 'm': 'getLanguage', 'q': 0, 'type': 'en', 'str': ''}
        dd = ss.get(api_url, params=params, headers=headers, timeout=timeout).json()
        lang_list = sorted(list(set([lang for d in dd for lang in dd[d]])))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, api_url: str, ss: AsyncSessionType, headers: dict, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        params = {'c': 'trans', 'm': 'getLanguage', 'q': 0, 'type': 'en', 'str': ''}
        dd = await (await ss.get(api_url, params=params, headers=headers, timeout=timeout)).json()
        lang_list = sorted(list(set([lang for d in dd for lang in dd[d]])))
        return {}.fromkeys(lang_list, lang_list)

    def encrypt_by_aes_ecb_pkcs7(self, data: str, key: str, if_padding: bool = True) -> bytes:
        algorithm = cry_ciphers.base.modes.algorithms.AES(key=key.encode())
        mode = cry_ciphers.base.modes.ECB()
        block_size = cry_ciphers.base.modes.algorithms.AES.block_size

        cipher = cry_ciphers.Cipher(algorithm=algorithm, mode=mode)
        encryptor = cipher.encryptor()

        if if_padding:
            padder = cry_padding.PKCS7(block_size=block_size).padder()
            data = padder.update(data.encode()) + padder.finalize()  #

        data = data if if_padding else data.encode()
        encrypted_data = encryptor.update(data=data)
        return encrypted_data

    def decrypt_by_aes_ecb_pkcs7(self, data: bytes, key: str, if_padding: bool = True) -> str:
        algorithm = cry_ciphers.base.modes.algorithms.AES(key=key.encode())
        mode = cry_ciphers.base.modes.ECB()
        block_size = cry_ciphers.base.modes.algorithms.AES.block_size

        cipher = cry_ciphers.Cipher(algorithm=algorithm, mode=mode)
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(data=data)

        if if_padding:
            un_padder = cry_padding.PKCS7(block_size=block_size).unpadder()
            decrypted_data = un_padder.update(decrypted_data) + un_padder.finalize()  #
        return decrypted_data.decode()

    def get_sign(self, query_text: str) -> str:
        cry_text = f"6key_web_new_fanyi{self.sign_key}{query_text}"
        sign = hashlib.md5(cry_text.encode()).hexdigest()[:16]
        sign = self.encrypt_by_aes_ecb_pkcs7(data=sign, key=self.encrypt_key, if_padding=True)
        sign = base64.b64encode(sign).decode()
        return sign

    def get_result(self, data: dict) -> dict:
        data = base64.b64decode(data['content'])
        data_str = self.decrypt_by_aes_ecb_pkcs7(data=data, key=self.decrypt_key, if_padding=True)
        data = json.loads(data_str)
        return data

    @Tse.time_stat
    @Tse.check_query
    def iciba_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                  **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.iciba.com/fy
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
            _ = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.api_url, self.session, self.language_headers, timeout,
                                                      **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        params = {
            'c': 'trans',
            'm': 'fy',
            'client': 6,
            'auth_user': 'key_web_new_fanyi',
            'sign': self.get_sign(query_text),
        }
        payload = {
            'from': from_language,
            'to': 'auto' if from_language == 'auto' else to_language,
            'q': query_text,
        }
        r = self.session.post(self.api_url, headers=self.api_headers, params=params, data=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        data = self.get_result(data)
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['out']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://www.iciba.com/fy
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
            _ = await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(self.api_url, self.async_session,
                                                                  self.language_headers, timeout,
                                                                  **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        params = {
            'c': 'trans',
            'm': 'fy',
            'client': 6,
            'auth_user': 'key_web_new_fanyi',
            'sign': self.get_sign(query_text),
        }
        payload = {
            'from': from_language,
            'to': 'auto' if from_language == 'auto' else to_language,
            'q': query_text,
        }
        r = await self.async_session.post(self.api_url, headers=self.api_headers, params=params, data=payload,
                                          timeout=timeout)
        r.raise_for_status()
        data = await r.json(content_type=None)
        data = self.get_result(data)
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['out']
