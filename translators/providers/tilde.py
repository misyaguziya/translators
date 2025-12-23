import asyncio
import time
from typing import Union

from translators.base import Tse, LangMapKwargsType, ApiKwargsType


class Tilde(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://translate.tilde.com/'
        self.api_url = 'https://letsmt.eu/ws/service.svc/json/TranslateEx'
        self.get_config_url = 'https://translate.tilde.com/assets/config.local.json'  # ?version=46852
        self.subscribe_url = 'https://translate.tilde.com/assets/subscriptions-config.local.json'
        self.plausible_url = 'https://plausible.io/api/event'
        self.auth_url = 'https://auth.tilde.com/auth/realms/Tilde/protocol/openid-connect/login-status-iframe.html/init'
        self.speech_url = 'https://va.tilde.com/dl/directline/aHR0cDovL3Byb2RrOHNib3R0aWxkZTQ=/tokens/speech'
        self.host_headers = self.get_headers(self.host_url, if_api=False, if_referer_for_host=True)
        self.api_headers = self.get_headers(self.host_url, if_api=True, if_json_for_api=True)
        self.session = None
        self.language_map = None
        self.langpair_ids = None
        self.config_data = None
        self.sys_data = None
        self.query_count = 0
        self.output_zh = None  # unsupported
        self.output_en = 'eng'
        self.input_limit = int(5e3)  # unknown
        self.default_from_language = 'lv'  # 'fr'

    @Tse.debug_language_map
    def get_language_map(self, sys_data: dict, **kwargs: LangMapKwargsType) -> dict:
        lang_pairs = [[item['SourceLanguage']['Code'], item['TargetLanguage']['Code']] for item in sys_data['System'] if
                      'General' in item['Domain']]
        return {f_lang: [v for k, v in lang_pairs if k == f_lang] for f_lang, t_lang in lang_pairs}

    def get_langpair_ids(self, sys_data: dict) -> dict:
        return {f"{item['SourceLanguage']['Code']}-{item['TargetLanguage']['Code']}": item['ID'] for item in
                sys_data['System'] if 'General' in item['Domain']}

    @Tse.uncertified
    @Tse.time_stat
    @Tse.check_query
    def tilde_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                  **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translate.tilde.com/
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
            self.config_data = self.session.get(self.get_config_url, headers=self.host_headers, timeout=timeout).json()
            self.api_headers.update({'client-id': self.config_data['mt']['api']['clientId']})  # must lower keyword

            sys_url = self.config_data['mt']['api']['systemListUrl']
            params = {'appID': self.config_data['mt']['api']['appID'],
                      'uiLanguageID': self.config_data['mt']['api']['uiLanguageID']}
            self.sys_data = self.session.get(sys_url, params=params, headers=self.api_headers,
                                             timeout=timeout).json()  # test
            self.langpair_ids = self.get_langpair_ids(self.sys_data)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.sys_data, **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('tilde', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map)

        payload = {
            'text': query_text,
            'appID': self.config_data['mt']['api']['appID'],
            'systemID': self.langpair_ids[f'{from_language}-{to_language}'],
            'options': 'widget=text,alignment,markSentences',
        }
        r = self.session.post(self.api_url, json=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['translation']

    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://translate.tilde.com/
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
            _ = await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)
            self.config_data = (
                await self.async_session.get(self.get_config_url, headers=self.host_headers, timeout=timeout)).json()
            self.api_headers.update({'client-id': self.config_data['mt']['api']['clientId']})  # must lower keyword

            sys_url = self.config_data['mt']['api']['systemListUrl']
            params = {'appID': self.config_data['mt']['api']['appID'],
                      'uiLanguageID': self.config_data['mt']['api']['uiLanguageID']}
            self.sys_data = (await self.async_session.get(sys_url, params=params, headers=self.api_headers,
                                                          timeout=timeout)).json()  # test
            self.langpair_ids = self.get_langpair_ids(self.sys_data)
            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.sys_data, **debug_lang_kwargs)

        if from_language == 'auto':
            from_language = self.warning_auto_lang('tilde', self.default_from_language, if_print_warning)
        from_language, to_language = self.check_language(from_language, to_language, self.language_map)

        payload = {
            'text': query_text,
            'appID': self.config_data['mt']['api']['appID'],
            'systemID': self.langpair_ids[f'{from_language}-{to_language}'],
            'options': 'widget=text,alignment,markSentences',
        }
        r = await self.async_session.post(self.api_url, json=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data['translation']
