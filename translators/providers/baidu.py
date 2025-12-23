import asyncio
import re
import time
import urllib.parse
from typing import Optional, Union

import exejs

from translators.base import Tse, LangMapKwargsType, TranslatorError, ApiKwargsType, AsyncSessionType, SessionType


class BaiduV1(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://fanyi.baidu.com'
        self.api_url = 'https://fanyi.baidu.com/transapi'
        self.get_lang_url = None
        self.get_lang_url_pattern = 'https://fanyi-cdn.cdn.bcebos.com/static/cat/js/index.(.*?).js'
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True)
        self.language_map = None
        self.session = None
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    # @Tse.debug_language_map
    # def get_language_map(self, host_html: str, **kwargs: LangMapKwargsType) -> dict:
    #     lang_str = re.compile('langMap: {(.*?)}').search(host_html.replace('\n', '').replace('  ', '')).group()[8:]
    #     return exejs.evaluate(lang_str)

    @Tse.debug_language_map
    def get_language_map(self, lang_url: str, ss: SessionType, headers: dict, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        js_html = ss.get(lang_url, headers=headers, timeout=timeout).text
        lang_str = re.compile('exports={auto:(.*?)}}}},').search(js_html).group()[8:-3]
        lang_list = re.compile('(\\w+):{zhName:').findall(lang_str)
        lang_list = sorted(list(set(lang_list)))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, lang_url: str, ss: AsyncSessionType, headers: dict, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        js_html = (await ss.get(lang_url, headers=headers, timeout=timeout)).text
        lang_str = re.compile('exports={auto:(.*?)}}}},').search(js_html).group()[8:-3]
        lang_list = re.compile('(\\w+):{zhName:').findall(lang_str)
        lang_list = sorted(list(set(lang_list)))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.uncertified
    @Tse.time_stat
    @Tse.check_query
    def baidu_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                  **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.baidu.com
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
            _ = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout)  # must twice, send cookies.
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text

            if not self.get_lang_url:
                self.get_lang_url = re.compile(self.get_lang_url_pattern).search(host_html).group()

            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.get_lang_url, self.session, self.host_headers, timeout,
                                                      **debug_lang_kwargs)

            # self.session.cookies.update({'ab_sr': f'1.0.1_{self.absr_v}=='})
            # self.session.cookies.update({k: '1' for k in ['REALTIME_TRANS_SWITCH', 'FANYI_WORD_SWITCH', 'HISTORY_SWITCH', 'SOUND_SPD_SWITCH', 'SOUND_PREFER_SWITCH']})

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = {
            'from': from_language,
            'to': to_language,
            'query': query_text,
            'source': 'txt',
        }
        r = self.session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join([item['dst'] for item in data['data']])

    @Tse.uncertified_async
    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.baidu.com
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
            _ = await self.async_session.get(self.host_url, headers=self.host_headers,
                                             timeout=timeout)  # must twice, send cookies.
            host_html = (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text

            if not self.get_lang_url:
                self.get_lang_url = re.compile(self.get_lang_url_pattern).search(host_html).group()

            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(self.get_lang_url, self.async_session,
                                                                  self.host_headers, timeout, **debug_lang_kwargs)

            # self.session.cookies.update({'ab_sr': f'1.0.1_{self.absr_v}=='})
            # self.session.cookies.update({k: '1' for k in ['REALTIME_TRANS_SWITCH', 'FANYI_WORD_SWITCH', 'HISTORY_SWITCH', 'SOUND_SPD_SWITCH', 'SOUND_PREFER_SWITCH']})

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = {
            'from': from_language,
            'to': to_language,
            'query': query_text,
            'source': 'txt',
        }
        r = await self.async_session.post(self.api_url, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join([item['dst'] for item in data['data']])


class BaiduV2(Tse):
    def __init__(self):
        super().__init__()
        self.begin_time = time.time()
        self.host_url = 'https://fanyi.baidu.com'
        self.api_url = 'https://fanyi.baidu.com/v2transapi'
        self.langdetect_url = 'https://fanyi.baidu.com/langdetect'
        self.get_sign_url = 'https://fanyi-cdn.cdn.bcebos.com/static/translation/pkg/index_bd36cef.js'
        self.get_lang_url = None
        self.get_lang_url_pattern = 'https://fanyi-cdn.cdn.bcebos.com/static/cat/js/index.(.*?).js'
        self.acs_url = 'https://dlswbr.baidu.com/heicha/mm/{i}/acs-{i}.js'.format(i=2060)
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True)
        self.language_map = None
        self.session = None
        self.professional_field = ('common', 'medicine', 'electronics', 'mechanics', 'novel')
        self.token = None
        self.sign = None
        self.acs_token = None
        self.query_count = 0
        self.output_zh = 'zh'
        self.input_limit = int(5e3)
        self.default_from_language = self.output_zh

    @Tse.debug_language_map
    def get_language_map(self, lang_url: str, ss: SessionType, headers: dict, timeout: Optional[float],
                         **kwargs: LangMapKwargsType) -> dict:
        js_html = ss.get(lang_url, headers=headers, timeout=timeout).text
        lang_str = re.compile('exports={auto:(.*?)}}}},').search(js_html).group()[8:-3]
        lang_list = re.compile('(\\w+):{zhName:').findall(lang_str)
        lang_list = sorted(list(set(lang_list)))
        return {}.fromkeys(lang_list, lang_list)

    @Tse.debug_language_map_async
    async def get_language_map_async(self, lang_url: str, ss: AsyncSessionType, headers: dict, timeout: Optional[float],
                                     **kwargs: LangMapKwargsType) -> dict:
        js_html = (await ss.get(lang_url, headers=headers, timeout=timeout)).text
        lang_str = re.compile('exports={auto:(.*?)}}}},').search(js_html).group()[8:-3]
        lang_list = re.compile('(\\w+):{zhName:').findall(lang_str)
        lang_list = sorted(list(set(lang_list)))
        return {}.fromkeys(lang_list, lang_list)

    def get_sign(self, query_text: str, host_html: str, ss: SessionType, headers: dict,
                 timeout: Optional[float]) -> str:
        gtk_list = re.compile("""window.gtk = '(.*?)';|window.gtk = "(.*?)";""").findall(host_html)[0]
        gtk = gtk_list[0] or gtk_list[1]

        sign_html = ss.get(self.get_sign_url, headers=headers, timeout=timeout).text
        begin_label = 'define("translation:widget/translate/input/pGrab",function(r,o,t){'
        end_label = 'var i=null;t.exports=e});'
        sign_js = sign_html[sign_html.find(begin_label) + len(begin_label):sign_html.find(end_label)]
        sign_js = sign_js.replace('function e(r)', 'function e(r,i)')
        return exejs.compile(sign_js).call('e', query_text, gtk)

    async def get_sign_async(self, query_text: str, host_html: str, ss: AsyncSessionType, headers: dict,
                             timeout: Optional[float]) -> str:
        gtk_list = re.compile("""window.gtk = '(.*?)';|window.gtk = "(.*?)";""").findall(host_html)[0]
        gtk = gtk_list[0] or gtk_list[1]

        sign_html = (await ss.get(self.get_sign_url, headers=headers, timeout=timeout)).text
        begin_label = 'define("translation:widget/translate/input/pGrab",function(r,o,t){'
        end_label = 'var i=null;t.exports=e});'
        sign_js = sign_html[sign_html.find(begin_label) + len(begin_label):sign_html.find(end_label)]
        sign_js = sign_js.replace('function e(r)', 'function e(r,i)')
        return await exejs.compile(sign_js).call_async('e', query_text, gtk)

    def get_tk(self, host_html: str) -> str:
        tk_list = re.compile("""token: '(.*?)',|token: "(.*?)",""").findall(host_html)[0]
        return tk_list[0] or tk_list[1]

    # def get_new_absr(self, absr):
    #     absr = base64.b64decode(absr+'==').decode()
    #     absr = absr[:-32] + hashlib.md5(str(int(time.time())).encode()).hexdigest()
    #     absr = base64.b64encode(absr.encode()).decode()
    #     return absr

    # def get_acs_token(self):
    #     pass

    @Tse.uncertified
    @Tse.time_stat
    @Tse.check_query
    def baidu_api(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                  **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.baidu.com
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
                :param professional_field: str, default 'common'. Choose from ('common', 'medicine', 'electronics', 'mechanics', 'novel')
        :return: str or dict
        """

        use_domain = kwargs.get('professional_field', 'common')
        if use_domain not in self.professional_field:  # only support zh-en, en-zh.
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
                self.session and self.language_map and not_update_cond_freq and not_update_cond_time and self.token and self.sign):
            self.begin_time = time.time()
            self.session = Tse.get_client_session(http_client, proxies)
            _ = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout)  # must twice, reload token.
            host_html = self.session.get(self.host_url, headers=self.host_headers, timeout=timeout).text
            self.token = self.get_tk(host_html)
            self.sign = self.get_sign(query_text, host_html, self.session, self.host_headers, timeout)

            if not self.get_lang_url:
                self.get_lang_url = re.compile(self.get_lang_url_pattern).search(host_html).group()

            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = self.get_language_map(self.get_lang_url, self.session, self.host_headers, timeout,
                                                      **debug_lang_kwargs)

            # self.session.cookies.update({'ab_sr': f'1.0.1_{self.absr_v}=='})
            # self.session.cookies.update({k: '1' for k in ['REALTIME_TRANS_SWITCH', 'FANYI_WORD_SWITCH', 'HISTORY_SWITCH', 'SOUND_SPD_SWITCH', 'SOUND_PREFER_SWITCH']})

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = urllib.parse.urlencode({"query": query_text})
        res = self.session.post(self.langdetect_url, headers=self.api_headers, data=payload, timeout=timeout)
        if from_language == 'auto':
            from_language = res.json()['lan']

        params = {"from": from_language, "to": to_language}
        payload = {
            "from": from_language,
            "to": to_language,
            "query": query_text,  # from urllib.parse import quote_plus
            "transtype": "realtime",  # ["translang","realtime"]
            "simple_means_flag": "3",
            "sign": self.sign,
            "token": self.token,
            "domain": use_domain,
            "ts": self.get_timestamp(),
        }
        payload = urllib.parse.urlencode(payload)
        # self.api_headers.update({'Acs-Token': self.acs_token})
        r = self.session.post(self.api_url, params=params, data=payload, headers=self.api_headers, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join([x['dst'] for x in data['trans_result']['data']])

    @Tse.uncertified_async
    @Tse.time_stat_async
    @Tse.check_query_async
    async def trans_api_async(self, query_text: str, from_language: str = 'auto', to_language: str = 'en',
                              **kwargs: ApiKwargsType) -> Union[str, dict]:
        """
        https://fanyi.baidu.com
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
                :param professional_field: str, default 'common'. Choose from ('common', 'medicine', 'electronics', 'mechanics', 'novel')
        :return: str or dict
        """

        use_domain = kwargs.get('professional_field', 'common')
        if use_domain not in self.professional_field:  # only support zh-en, en-zh.
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
                self.async_session and self.language_map and not_update_cond_freq and not_update_cond_time and self.token and self.sign):
            self.begin_time = time.time()
            self.async_session = Tse.get_async_client_session(http_client, proxies)
            _ = await self.async_session.get(self.host_url, headers=self.host_headers,
                                             timeout=timeout)  # must twice, reload token.
            host_html = (await self.async_session.get(self.host_url, headers=self.host_headers, timeout=timeout)).text
            self.token = self.get_tk(host_html)
            self.sign = await self.get_sign_async(query_text, host_html, self.async_session, self.host_headers, timeout)

            if not self.get_lang_url:
                self.get_lang_url = re.compile(self.get_lang_url_pattern).search(host_html).group()

            debug_lang_kwargs = self.debug_lang_kwargs(from_language, to_language, self.default_from_language,
                                                       if_print_warning)
            self.language_map = await self.get_language_map_async(self.get_lang_url, self.async_session,
                                                                  self.host_headers, timeout, **debug_lang_kwargs)

            # self.async_session.cookies.update({'ab_sr': f'1.0.1_{self.absr_v}=='})
            # self.async_session.cookies.update({k: '1' for k in ['REALTIME_TRANS_SWITCH', 'FANYI_WORD_SWITCH', 'HISTORY_SWITCH', 'SOUND_SPD_SWITCH', 'SOUND_PREFER_SWITCH']})

        from_language, to_language = self.check_language(from_language, to_language, self.language_map,
                                                         output_zh=self.output_zh)

        payload = urllib.parse.urlencode({"query": query_text})
        res = await self.async_session.post(self.langdetect_url, headers=self.api_headers, data=payload,
                                            timeout=timeout)
        if from_language == 'auto':
            from_language = res.json()['lan']

        params = {"from": from_language, "to": to_language}
        payload = {
            "from": from_language,
            "to": to_language,
            "query": query_text,  # from urllib.parse import quote_plus
            "transtype": "realtime",  # ["translang","realtime"]
            "simple_means_flag": "3",
            "sign": self.sign,
            "token": self.token,
            "domain": use_domain,
            "ts": self.get_timestamp(),
        }
        payload = urllib.parse.urlencode(payload)
        # self.api_headers.update({'Acs-Token': self.acs_token})
        r = await self.async_session.post(self.api_url, params=params, data=payload, headers=self.api_headers,
                                          timeout=timeout)
        r.raise_for_status()
        data = r.json()
        await asyncio.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else '\n'.join([x['dst'] for x in data['trans_result']['data']])
