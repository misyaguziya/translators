import asyncio
import base64
import hmac
import re
import time
import urllib.parse
import uuid
from typing import Union

from translators.base import Tse, LangMapKwargsType, ApiKwargsType


class Papago(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://papago.naver.com'
        self.api_url = 'https://papago.naver.com/apis/n2mt/translate'  # nsmt
        self.web_api_url = 'https://papago.naver.net/website'
        self.lang_detect_url = 'https://papago.naver.com/apis/langs/dect'
        self.language_url = None
        self.language_url_pattern = '/home.(.*?).chunk.js'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_json_for_api=False)
        self.language_map = None
        self.session = None
        self.device_id = None
        self.auth_key = 'v1.8.10_9e022f68fb'  # 'v1.8.8_3ab8f7c2df'  #'v1.8.4_bbf86e0446'  # 'v1.7.1_12f919c9b5'  #'v1.6.7_cc60b67557'
        self.query_count = 0
        self.output_zh = 'zh-CN'
        self.input_limit = int(1e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, lang_html: str, **kwargs: LangMapKwargsType) -> dict:
        lang_str = re.compile('={ALL:(.*?)}').search(lang_html).group()[1:]
        lang_str = lang_str.lower().replace('zh-cn', 'zh-CN').replace('zh-tw', 'zh-TW')
        lang_list = re.compile(',"(.*?)":|,(.*?):').findall(lang_str)
        lang_list = [j if j else k for j, k in lang_list]
        lang_list = sorted(list(filter(lambda x: x not in ('all', 'auto'), lang_list)))
        return {}.fromkeys(lang_list, lang_list)

    # def get_auth_key(self, lang_html: str) -> str:
    #     return re.compile('AUTH_KEY:"(.*?)"').findall(lang_html)[0]

    def get_authorization(self, url: str, auth_key: str, device_id: str, timestamp: int) -> str:
        auth = hmac.new(key=auth_key.encode(), msg=f'{device_id}\n{url}\n{timestamp}'.encode(),
                        digestmod='md5').digest()
        return f'PPG {device_id}:{base64.b64encode(auth).decode()}'

    @Tse.time_stat
    @Tse.check_query
    def papago_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                   **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://papago.naver.com
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
        if not (self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.auth_key):
            self.device_id = str(uuid.uuid4())
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            url_path = re.compile(self.language_url_pattern).search(host_html).group()
            self.language_url = ''.join([self.host_url, url_path])
            lang_html = self.session.get(self.language_url, headers=self.host_headers, timeout=timeout).text
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(lang_html, **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        detect_time = self.get_timestamp()
        detect_auth = self.get_authorization(self.lang_detect_url, self.auth_key, self.device_id, detect_time)
        detect_add_headers = {'device-type': 'pc', 'timestamp': str(detect_time), 'authorization': detect_auth}
        detect_headers = {**self.api_headers, **detect_add_headers}

        if from_language == 'auto':
            detect_form = urllib.parse.urlencode({'query': query_text})
            r_detect = self.session.post(self.lang_detect_url, headers=detect_headers, data=detect_form,
                                         timeout=timeout)
            from_language = r_detect.json()['langCode']

        trans_time = self.get_timestamp()
        trans_auth = self.get_authorization(self.api_url, self.auth_key, self.device_id, trans_time)
        trans_update_headers = {'x-apigw-partnerid': 'papago', 'timestamp': str(trans_time),
                                'authorization': trans_auth}
        detect_headers.update(trans_update_headers)
        trans_headers = detect_headers

        payload = {
            'deviceId': self.device_id,
            'text': query_text, 'source': from_language, 'target': to_language, 'locale': 'en',
            'dict': 'true', 'dictDisplay': 30, 'honorific': 'false', 'instant': 'false', 'paging': 'false',
        }
        payload = urllib.parse.urlencode(payload)
        r = self.session.post(self.api_url, headers=trans_headers, data=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['translatedText']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://papago.naver.com
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
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.auth_key):
            self.device_id = str(uuid.uuid4())
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(http_client, proxies)
            host_html = (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text
            url_path = re.compile(self.language_url_pattern).search(host_html).group()
            self.language_url = ''.join([self.host_url, url_path])
            lang_html = (
                await self.async_session.get(self.language_url, headers=self.host_headers, timeout=timeout)).text
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(lang_html, **debug_lang_kwargs)

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        detect_time = self.get_timestamp()
        detect_auth = self.get_authorization(self.lang_detect_url, self.auth_key, self.device_id, detect_time)
        detect_add_headers = {'device-type': 'pc', 'timestamp': str(detect_time), 'authorization': detect_auth}
        detect_headers = {**self.api_headers, **detect_add_headers}

        if from_language == 'auto':
            detect_form = urllib.parse.urlencode({'query': query_text})
            r_detect = await self.async_session.post(self.lang_detect_url, headers=detect_headers, data=detect_form,
                                                     timeout=timeout)
            from_language = (r_detect.json())['langCode']

        trans_time = self.get_timestamp()
        trans_auth = self.get_authorization(self.api_url, self.auth_key, self.device_id, trans_time)
        trans_update_headers = {'x-apigw-partnerid': 'papago', 'timestamp': str(trans_time),
                                'authorization': trans_auth}
        detect_headers.update(trans_update_headers)
        trans_headers = detect_headers

        payload = {
            'deviceId': self.device_id,
            'text': query_text, 'source': from_language, 'target': to_language, 'locale': 'en',
            'dict': 'true', 'dictDisplay': 30, 'honorific': 'false', 'instant': 'false', 'paging': 'false',
        }
        payload = urllib.parse.urlencode(payload)
        r = await self.async_session.post(self.api_url, headers=trans_headers, data=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['translatedText']
