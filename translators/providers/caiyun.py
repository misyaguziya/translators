import asyncio
import base64
import re
import time
import uuid
from typing import Optional, Union

from translators.base import Tse, LangMapKwargsType, ApiKwargsType, AsyncSessionType, SessionType


class Caiyun(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://fanyi.caiyunapp.com'
        self.api_url = 'https://api.interpreter.caiyunai.com/v1/translator'
        self.get_language_url = 'https://fanyi.caiyunapp.com/get_config/xiaoyi_translation_languages.json'
        self.get_js_pattern = '/dist/assets/index.(.*?).js'
        self.get_js_url = None
        self.get_jwt_url = 'https://api.interpreter.caiyunai.com/v1/user/jwt/generate'
        self.host_headers = self.get_headers(self.host_url, if_api=False, if_referer_for_host=True)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_ajax_for_api=False, if_json_for_api=True)
        self.language_map = None
        self.session = None
        self.browser_id = str(uuid.uuid4()).replace('-', '')
        self.normal_key = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz' + '0123456789' + '=.+-_/'
        self.cipher_key = 'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm' + '0123456789' + '=.+-_/'
        self.decrypt_dictionary = self.crypt(if_de=True)
        self.tk = 'token:qgemv4jr1y38jyq6vhvi'  # 'token gh0nd9ybc4a7mvb2unqi'
        self.jwt = None
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    # @Tse.debug_language_map
    # def get_language_map(self, js_html: str, **kwargs: LangMapKwargsType) -> dict:
    #     lang_text = re.compile('lang:{(.*?)},').search(js_html).group()[5:-1]
    #     lang_pair_list = re.compile('(\\w+):(.*?),').findall(lang_text)
    #     lang_list = sorted([lang for lang, _ in lang_pair_list])
    #     return {}.fromkeys(lang_list, lang_list)

    # def get_tk(self, js_html: str) -> str:
    #     return re.compile('headers\\["X-Authorization"]="(.*?)",').findall(js_html)[0]

    @Tse.debug_language_map
    def get_language_map(self, lang_url: str, ss: SessionType, headers: dict, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        lang_dict = ss.get(lang_url, headers=headers, timeout=timeout).json()
        lang_list = sorted([item['code'] for item in lang_dict['supported_translation_languages']])
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, lang_url: str, ss: AsyncSessionType, headers: dict, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        lang_dict = (await ss.get(lang_url, headers=headers, timeout=timeout)).json()
        lang_list = sorted([item['code'] for item in lang_dict['supported_translation_languages']])
        return {}.fromkeys(lang_list, lang_list)

    def get_tk(self, js_html: str) -> str:
        tk = re.compile('"X-Authorization":"(.*?)"').findall(js_html)[0]
        tk = tk.replace(' ', ':')
        return tk

    def crypt(self, if_de: bool = True) -> dict:
        if if_de:
            return {k: v for k, v in zip(self.cipher_key, self.normal_key)}
        return {v: k for k, v in zip(self.cipher_key, self.normal_key)}

    def encrypt(self, plain_text: str) -> str:
        encrypt_dictionary = self.crypt(if_de=False)
        _cipher_text = base64.b64encode(plain_text.encode()).decode()
        return ''.join(list(map(lambda k: encrypt_dictionary[k], _cipher_text)))

    def decrypt(self, cipher_text: str) -> str:
        _ciphertext = ''.join(list(map(lambda k: self.decrypt_dictionary[k], cipher_text)))
        return base64.b64decode(_ciphertext).decode()

    @Tse.time_stat
    @Tse.check_query
    def caiyun_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                   **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.caiyunapp.com
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
                :param professional_field: str, default None, choose from (None, "medicine","law","machinery")
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
                self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.tk and self.jwt):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            js_url_path = re.compile(self.get_js_pattern).search(host_html).group()
            self.get_js_url = ''.join([self.host_url, js_url_path])
            js_html = self.session.get(self.get_js_url, headers=self.host_headers, timeout=timeout).text
            # self.tk = self.get_tk(js_html)

            self.api_headers.update({
                "app-name": "xiaoyi",
                "device-id": self.browser_id,
                "os-type": "web",
                "os-version": "",
                "version": "4.6.0",
                "Authorization": "bearer",
                "X-Authorization": self.tk,
            })
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.get_language_url, self.session, self.api_headers, timeout,
                                                      **debug_lang_kwargs)

            jwt_payload = {'browser_id': self.browser_id}
            jwt_r = self.session.post(self.get_jwt_url, json=jwt_payload, headers=self.api_headers, timeout=timeout)
            self.jwt = jwt_r.json()['jwt']
            self.api_headers.update({"T-Authorization": self.jwt})

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = {
            "browser_id": self.browser_id,
            "source": query_text.split('\n'),
            "trans_type": f"{from_language}2{to_language}",
            "dict": "true",
            "cached": "true",
            "replaced": "true",
            "media": "text",
            "os_type": "web",
            "request_id": "web_fanyi",
            "model": "",
            "style": "formal",
        }
        if from_language == 'auto':
            payload.update({'detect': 'true'})

        # _ = self.session.options(self.api_url, headers=self.host_headers, timeout=timeout)
        r = self.session.post(self.api_url, headers=self.api_headers, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join([self.decrypt(item) for item in data['target']])

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.caiyunapp.com
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
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.tk and self.jwt):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(http_client, proxies)
            host_html = (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text
            js_url_path = re.compile(self.get_js_pattern).search(host_html).group()
            self.get_js_url = ''.join([self.host_url, js_url_path])
            js_html = (await self.async_session.get(self.get_js_url, headers=self.host_headers, timeout=timeout)).text
            # self.tk = self.get_tk(js_html)
            self.api_headers.update({
                "app-name": "xiaoyi",
                "device-id": self.browser_id,
                "os-type": "web",
                "os-version": "",
                "version": "4.6.0",
                "Authorization": "bearer",
                "X-Authorization": self.tk,
            })
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(self.get_language_url, self.async_session,
                                                                  self.api_headers, timeout,
                                                                  **debug_lang_kwargs)

            jwt_payload = {'browser_id': self.browser_id}
            jwt_r = await self.async_session.post(self.get_jwt_url, json=jwt_payload, headers=self.api_headers,
                                                  timeout=timeout)
            self.jwt = jwt_r.json()['jwt']
            self.api_headers.update({"T-Authorization": self.jwt})

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = {
            "browser_id": self.browser_id,
            "source": query_text.split('\n'),
            "trans_type": f"{from_language}2{to_language}",
            "dict": "true",
            "cached": "true",
            "replaced": "true",
            "media": "text",
            "os_type": "web",
            "request_id": "web_fanyi",
            "model": "",
            "style": "formal",
        }
        if from_language == 'auto':
            payload.update({'detect': 'true'})

        # _ = await self.async_session.options(self.api_url, headers=self.host_headers, timeout=timeout)
        r = await self.async_session.post(self.api_url, headers=self.api_headers, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join([self.decrypt(item) for item in data['target']])
