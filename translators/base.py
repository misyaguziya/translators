import sys
import time
import random
import warnings
import functools
import urllib.parse
from typing import Optional, Union, Tuple
import httpx
import requests
import niquests
import cloudscraper
import aiohttp

LangMapKwargsType = Union[str, bool]
ApiKwargsType = Union[str, int, float, bool, dict]
SessionType = Union[requests.sessions.Session, niquests.sessions.Session, httpx.Client]
ResponseType = Union[requests.models.Response, niquests.models.Response, httpx.Response]
AsyncSessionType = aiohttp.ClientSession
AsyncResponseType = aiohttp.ClientResponse


class TranslatorError(Exception):
    pass


class Tse:
    working = True

    def __init__(self):
        self.author = 'UlionTse'
        self.all_begin_time = time.time()
        self.default_session_freq = int(1e3)
        self.default_session_seconds = 1.5e3
        self.transform_en_translator_pool = ('itranslate', 'lingvanex', 'myMemory', 'apertium', 'cloudTranslation',
                                             'translateMe')
        self.auto_pool = ('auto', 'detect', 'auto-detect', 'all')
        self.zh_pool = ('zh', 'zh-CN', 'zh-cn', 'zh-CHS', 'zh-Hans', 'zh-Hans_CN', 'cn', 'chi', 'Chinese')
        self.session: Optional[SessionType] = None
        self.async_session: Optional[AsyncSessionType] = None

    @staticmethod
    def time_stat(func):
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            if_show_time_stat = kwargs.get('if_show_time_stat', False)
            show_time_stat_precision = kwargs.get('show_time_stat_precision', 2)
            sleep_seconds = kwargs.get('sleep_seconds', 0)

            if if_show_time_stat and sleep_seconds >= 0:
                t1 = time.time()
                result = func(*args, **kwargs)
                t2 = time.time()
                cost_time = round((t2 - t1 - sleep_seconds), show_time_stat_precision)
                name = func.__name__.removesuffix('_api').removesuffix('_async')
                sys.stderr.write(f'TimeSpent(function: {name}): {cost_time}s\n')
                return result
            return func(*args, **kwargs)

        return _wrapper

    @staticmethod
    def time_stat_async(func):
        @functools.wraps(func)
        async def _wrapper(*args, **kwargs):
            if_show_time_stat = kwargs.get('if_show_time_stat', False)
            show_time_stat_precision = kwargs.get('show_time_stat_precision', 2)
            sleep_seconds = kwargs.get('sleep_seconds', 0)

            if if_show_time_stat and sleep_seconds >= 0:
                t1 = time.time()
                result = await func(*args, **kwargs)
                t2 = time.time()
                cost_time = round((t2 - t1 - sleep_seconds), show_time_stat_precision)
                name = func.__name__.removesuffix('_api').removesuffix('_async')
                sys.stderr.write(f'TimeSpent(function: {name}): {cost_time}s\n')
                return result
            return await func(*args, **kwargs)

        return _wrapper

    @staticmethod
    def get_timestamp() -> int:
        return int(time.time() * 1e3)

    @staticmethod
    def get_uuid() -> str:
        _uuid = ''
        for i in range(8):
            _uuid += hex(int(65536 * (1 + random.random())))[2:][1:]
            if 1 <= i <= 4:
                _uuid += '-'
        return _uuid

    @staticmethod
    def get_headers(host_url: str,
                    if_api: bool = False,
                    if_referer_for_host: bool = True,
                    if_ajax_for_api: bool = True,
                    if_json_for_api: bool = False,
                    if_multipart_for_api: bool = False,
                    if_http_override_for_api: bool = False
                    ) -> dict:

        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
        host_headers = {
            'Referer' if if_referer_for_host else 'Host': host_url,
            "User-Agent": user_agent,
        }
        api_headers = {
            'Origin': f'https://{urllib.parse.urlparse(host_url.strip("/")).netloc}',
            'Referer': host_url,
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            "User-Agent": user_agent,
        }
        if if_api and not if_ajax_for_api:
            api_headers.pop('X-Requested-With')
            api_headers.update({'Content-Type': 'text/plain'})
        if if_api and if_json_for_api:
            api_headers.update({'Content-Type': 'application/json'})
        if if_api and if_multipart_for_api:
            api_headers.pop('Content-Type')
        if if_api and if_http_override_for_api:
            api_headers.update({'X-HTTP-Method-Override': 'GET'})
        return host_headers if not if_api else api_headers

    def check_en_lang(self, from_lang: str, to_lang: str, default_translator: Optional[str] = None,
                      default_lang: str = 'en-US') -> Tuple[str, str]:
        if default_translator and default_translator in self.transform_en_translator_pool:
            from_lang = default_lang if from_lang == 'en' else from_lang
            to_lang = default_lang if to_lang == 'en' else to_lang
            from_lang = default_lang.replace('-', '_') if default_translator == 'lingvanex' and from_lang[
                :3] == 'en-' else from_lang
            to_lang = default_lang.replace('-', '_') if default_translator == 'lingvanex' and to_lang[
                :3] == 'en-' else to_lang
        return from_lang, to_lang

    def check_language(self,
                       from_language: str,
                       to_language: str,
                       language_map: dict,
                       output_auto: str = 'auto',
                       output_zh: str = 'zh',
                       output_en_translator: Optional[str] = None,
                       output_en: str = 'en-US',
                       if_check_lang_reverse: bool = True,
                       ) -> Tuple[str, str]:

        if output_en_translator:
            from_language, to_language = self.check_en_lang(from_language, to_language, output_en_translator, output_en)

        from_language = output_auto if from_language in self.auto_pool else from_language
        from_language = output_zh if from_language in self.zh_pool else from_language
        to_language = output_zh if to_language in self.zh_pool else to_language

        if from_language != output_auto and from_language not in language_map:
            raise TranslatorError(
                'Unsupported from_language[{}] in {}.'.format(from_language, sorted(language_map.keys())))
        elif to_language not in language_map and if_check_lang_reverse:
            raise TranslatorError('Unsupported to_language[{}] in {}.'.format(to_language, sorted(language_map.keys())))
        elif from_language != output_auto and to_language not in language_map[from_language]:
            raise TranslatorError('Unsupported translation: from [{0}] to [{1}]!'.format(from_language, to_language))
        elif from_language == to_language:
            raise TranslatorError(f'from_language[{from_language}] and to_language[{to_language}] should not be same.')
        return from_language, to_language

    @staticmethod
    def warning_auto_lang(translator: str, default_from_language: str, if_print_warning: bool = True) -> str:
        if if_print_warning:
            warn_tips = f'Unsupported [from_language=auto({default_from_language} instead)] with [{translator}]!'
            warnings.warn(f'{warn_tips} Please specify it.')
        return default_from_language

    @staticmethod
    def debug_lang_kwargs(from_language: str, to_language: str, default_from_language: str,
                          if_print_warning: bool = True) -> dict:
        kwargs = {
            'from_language': from_language,
            'to_language': to_language,
            'default_from_language': default_from_language,
            'if_print_warning': if_print_warning,
        }
        return kwargs

    @staticmethod
    def debug_language_map(func):
        def make_temp_language_map(from_language: str, to_language: str, default_from_language: str) -> dict:
            if from_language == to_language or to_language == 'auto':
                raise TranslatorError

            temp_language_map = {from_language: to_language}
            if from_language != 'auto':
                temp_language_map.update({to_language: from_language})
            elif default_from_language != to_language:
                temp_language_map.update({default_from_language: to_language, to_language: default_from_language})

            return temp_language_map

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            try:
                language_map = func(*args, **kwargs)
                if not language_map:
                    raise TranslatorError
                return language_map
            except Exception as e:
                if kwargs.get('if_print_warning', True):
                    warnings.warn(f'GetLanguageMapError: {str(e)}.\nThe function make_temp_language_map() works.')
                return make_temp_language_map(kwargs.get('from_language'), kwargs.get('to_language'),
                                              kwargs.get('default_from_language'))

        return _wrapper

    @staticmethod
    def debug_language_map_async(func):
        def make_temp_language_map(from_language: str, to_language: str, default_from_language: str) -> dict:
            if from_language == to_language or to_language == 'auto':
                raise TranslatorError

            temp_language_map = {from_language: to_language}
            if from_language != 'auto':
                temp_language_map.update({to_language: from_language})
            elif default_from_language != to_language:
                temp_language_map.update({default_from_language: to_language, to_language: default_from_language})

            return temp_language_map

        @functools.wraps(func)
        async def _wrapper(*args, **kwargs):
            try:
                language_map = await func(*args, **kwargs)
                if not language_map:
                    raise TranslatorError
                return language_map
            except Exception as e:
                if kwargs.get('if_print_warning', True):
                    warnings.warn(f'GetLanguageMapError: {str(e)}.\nThe function make_temp_language_map() works.')
                return make_temp_language_map(kwargs.get('from_language'), kwargs.get('to_language'),
                                              kwargs.get('default_from_language'))
        return _wrapper

    @staticmethod
    def check_input_limit(query_text: str, input_limit: int) -> None:
        if len(query_text) > input_limit:
            raise TranslatorError

    @staticmethod
    def check_query(func):
        def check_query_text(query_text: str, if_ignore_empty_query: bool, if_ignore_limit_of_length: bool,
                             limit_of_length: int, bias_of_length: int = 10) -> str:
            if not isinstance(query_text, str):
                raise TranslatorError

            query_text = query_text.strip()
            qt_length = len(query_text)
            limit_of_length -= bias_of_length  # #154

            if qt_length == 0 and not if_ignore_empty_query:
                raise TranslatorError("The `query_text` can't be empty!")
            if qt_length >= limit_of_length and not if_ignore_limit_of_length:
                raise TranslatorError('The length of `query_text` exceeds the limit.')
            else:
                if qt_length >= limit_of_length:
                    warnings.warn(f'The length of `query_text` is {qt_length}, above {limit_of_length}.')
                    return query_text[:limit_of_length]
            return query_text

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            if_ignore_empty_query = kwargs.get('if_ignore_empty_query', True)
            if_ignore_limit_of_length = kwargs.get('if_ignore_limit_of_length', False)
            limit_of_length = kwargs.get('limit_of_length', 20000)
            is_detail_result = kwargs.get('is_detail_result', False)

            query_text = list(args)[1] if len(args) >= 2 else kwargs.get('query_text')
            query_text = check_query_text(query_text, if_ignore_empty_query, if_ignore_limit_of_length, limit_of_length)
            if not query_text and if_ignore_empty_query:
                return {'data': query_text} if is_detail_result else query_text

            if len(args) >= 2:
                new_args = list(args)
                new_args[1] = query_text
                return func(*tuple(new_args), **kwargs)
            return func(*args, **{**kwargs, **{'query_text': query_text}})

        return _wrapper

    @staticmethod
    def check_query_async(func):
        def check_query_text(query_text: str, if_ignore_empty_query: bool, if_ignore_limit_of_length: bool,
                             limit_of_length: int, bias_of_length: int = 10) -> str:
            if not isinstance(query_text, str):
                raise TranslatorError

            query_text = query_text.strip()
            qt_length = len(query_text)
            limit_of_length -= bias_of_length  # #154

            if qt_length == 0 and not if_ignore_empty_query:
                raise TranslatorError("The `query_text` can't be empty!")
            if qt_length >= limit_of_length and not if_ignore_limit_of_length:
                raise TranslatorError('The length of `query_text` exceeds the limit.')
            else:
                if qt_length >= limit_of_length:
                    warnings.warn(f'The length of `query_text` is {qt_length}, above {limit_of_length}.')
                    return query_text[:limit_of_length]
            return query_text


        @functools.wraps(func)
        async def _wrapper(*args, **kwargs):
            if_ignore_empty_query = kwargs.get('if_ignore_empty_query', True)
            if_ignore_limit_of_length = kwargs.get('if_ignore_limit_of_length', False)
            limit_of_length = kwargs.get('limit_of_length', 20000)
            is_detail_result = kwargs.get('is_detail_result', False)

            query_text = list(args)[1] if len(args) >= 2 else kwargs.get('query_text')
            query_text = check_query_text(query_text, if_ignore_empty_query, if_ignore_limit_of_length, limit_of_length)
            if not query_text and if_ignore_empty_query:
                return {'data': query_text} if is_detail_result else query_text

            if len(args) >= 2:
                new_args = list(args)
                new_args[1] = query_text
                return await func(*tuple(new_args), **kwargs)
            return await func(*args, **{**kwargs, **{'query_text': query_text}})

        return _wrapper

    @staticmethod
    def uncertified(func):
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except:
                raise_tips1 = f'The function {func.__name__[:-4]}() has been not certified yet.'
                raise_tips2_url = 'https://github.com/UlionTse/translators#supported-translation-services'
                raise_tips2 = f'Please read for details: Status of Translator on this webpage({raise_tips2_url}).'
                raise TranslatorError(f'{raise_tips1} {raise_tips2}')

        return _wrapper

    @staticmethod
    def uncertified_async(func):
        @functools.wraps(func)
        async def _wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except:
                raise_tips1 = f'The function {func.__name__[:-4]}() has been not certified yet.'
                raise_tips2_url = 'https://github.com/UlionTse/translators#supported-translation-services'
                raise_tips2 = f'Please read for details: Status of Translator on this webpage({raise_tips2_url}).'
                raise TranslatorError(f'{raise_tips1} {raise_tips2}')

        return _wrapper

    # @staticmethod
    # def certified(func):
    #     @functools.wraps(func)
    #     def _wrapper(*args, **kwargs):
    #         try:
    #             return func(*args, **kwargs)
    #         except Exception as e:
    #             raise TranslatorError(e)
    #     return _wrapper

    @staticmethod
    def get_client_session(http_client: str = 'requests', proxies: Optional[dict] = None) -> SessionType:
        if http_client not in ('requests', 'niquests', 'httpx', 'cloudscraper'):
            raise TranslatorError

        if proxies is None:
            proxies = {}

        if http_client == 'requests':
            session = requests.Session()
            session.proxies = proxies
        elif http_client == 'niquests':
            session = niquests.Session(happy_eyeballs=True)
            session.proxies = proxies
        elif http_client == 'httpx':
            proxy_url = proxies.get('http') or proxies.get('https')
            session = httpx.Client(follow_redirects=True, proxy=proxy_url)
        else:
            session = cloudscraper.create_scraper()
            session.proxies = proxies
        return session

    @staticmethod
    def get_async_client_session(proxies: Optional[dict] = None) -> AsyncSessionType:
        if proxies is None:
            proxies = {}
        # TODO: Add proxies
        session = aiohttp.ClientSession()
        return session

