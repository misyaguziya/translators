# coding=utf-8
# author=UlionTse

"""
Copyright (C) 2017  UlionTse

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Email: uliontse@outlook.com

translators  Copyright (C) 2017  UlionTse
This program comes with ABSOLUTELY NO WARRANTY; for details type `show w'.
This is free software, and you are welcome to redistribute it
under certain conditions; type `show c' for details.
"""
import os
import re
import sys
from typing import Optional, Union, Tuple, List

import pathos.multiprocessing as pathos_multiprocessing
import tqdm

from translators.base import TranslatorError, ApiKwargsType
from translators.providers import (
    AlibabaV2, Apertium, Argos, BaiduV1, Bing, Caiyun, cloudTranslationV2, Deepl, Elia,
    QQFanyi, GoogleV2, Hujiang, Iciba, IflytekV2, Iflyrec, Itranslate, Judic,
    LanguageWire, LingvanexV2, Mglip, Mirai, ModernMt, MyMemory, NiutransV2, Papago,
    Reverso, Sogou, SysTran, Tilde, TranslateCom, TranslateMe, QQTranSmart, Utibet,
    VolcEngine, YandexV2, Yeekit, YoudaoV3)
from translators.utils import Region

__all__ = [
    'translate_text', 'translate_html', 'translators_pool', 'translate_text_async',

    'alibaba', 'apertium', 'argos', 'baidu', 'bing',
    'caiyun', 'cloudTranslation', 'deepl', 'elia', 'google',
    'hujiang', 'iciba', 'iflytek', 'iflyrec', 'itranslate',
    'judic', 'languageWire', 'lingvanex', 'mglip', 'mirai',
    'modernMt', 'myMemory', 'niutrans', 'papago', 'qqFanyi',
    'qqTranSmart', 'reverso', 'sogou', 'sysTran', 'tilde',
    'translateCom', 'translateMe', 'utibet', 'volcEngine', 'yandex',
    'yeekit', 'youdao',

    '_alibaba', '_apertium', '_argos', '_baidu', '_bing',
    '_caiyun', '_cloudTranslation', '_deepl', '_elia', '_google',
    '_hujiang', '_iciba', '_iflytek', '_iflyrec', '_itranslate',
    '_judic', '_languageWire', '_lingvanex', '_mglip', '_mirai',
    '_modernMt', '_myMemory', '_niutrans', '_papago', '_qqFanyi',
    '_qqTranSmart', '_reverso', '_sogou', '_sysTran', '_tilde',
    '_translateCom', '_translateMe', '_utibet', '_volcEngine', '_yandex',
    '_yeekit', '_youdao',
]  # 37


class TranslatorsServer:
    def __init__(self):
        self.cpu_cnt = os.cpu_count()
        self._region = Region()
        self.get_region_of_server = self._region.get_region_of_server
        self.server_region = self.get_region_of_server(if_print_region=False)
        self._alibaba = AlibabaV2()
        self.alibaba = self._alibaba.alibaba_api
        self._apertium = Apertium()
        self.apertium = self._apertium.apertium_api
        self._argos = Argos()
        self.argos = self._argos.argos_api
        self._baidu = BaiduV1()  # V2
        self.baidu = self._baidu.baidu_api
        self._bing = Bing(server_region=self.server_region)
        self.bing = self._bing.bing_api
        self._caiyun = Caiyun()
        self.caiyun = self._caiyun.caiyun_api
        self._cloudTranslation = cloudTranslationV2()
        self.cloudTranslation = self._cloudTranslation.cloudTranslation_api
        self._deepl = Deepl()
        self.deepl = self._deepl.deepl_api
        self._elia = Elia()
        self.elia = self._elia.elia_api
        self._google = GoogleV2(server_region=self.server_region)
        self.google = self._google.google_api
        self.async_google = self._google.trans_api_async
        self._hujiang = Hujiang()
        self.hujiang = self._hujiang.hujiang_api
        self._iciba = Iciba()
        self.iciba = self._iciba.iciba_api
        self._iflytek = IflytekV2()
        self.iflytek = self._iflytek.iflytek_api
        self._iflyrec = Iflyrec()
        self.iflyrec = self._iflyrec.iflyrec_api
        self._itranslate = Itranslate()
        self.itranslate = self._itranslate.itranslate_api
        self._judic = Judic()
        self.judic = self._judic.judic_api
        self._languageWire = LanguageWire()
        self.languageWire = self._languageWire.languageWire_api
        self._lingvanex = LingvanexV2()
        self.lingvanex = self._lingvanex.lingvanex_api
        self._niutrans = NiutransV2()
        self.niutrans = self._niutrans.niutrans_api
        self._mglip = Mglip()
        self.mglip = self._mglip.mglip_api
        self._mirai = Mirai()
        self.mirai = self._mirai.mirai_api
        self._modernMt = ModernMt()
        self.modernMt = self._modernMt.modernMt_api
        self._myMemory = MyMemory()
        self.myMemory = self._myMemory.myMemory_api
        self._papago = Papago()
        self.papago = self._papago.papago_api
        self._qqFanyi = QQFanyi()
        self.qqFanyi = self._qqFanyi.qqFanyi_api
        self._qqTranSmart = QQTranSmart()
        self.qqTranSmart = self._qqTranSmart.qqTranSmart_api
        self._reverso = Reverso()
        self.reverso = self._reverso.reverso_api
        self._sogou = Sogou()
        self.sogou = self._sogou.sogou_api
        self._sysTran = SysTran()
        self.sysTran = self._sysTran.sysTran_api
        self._tilde = Tilde()
        self.tilde = self._tilde.tilde_api
        self._translateCom = TranslateCom()
        self.translateCom = self._translateCom.translateCom_api
        self._translateMe = TranslateMe()
        self.translateMe = self._translateMe.translateMe_api
        self._utibet = Utibet()
        self.utibet = self._utibet.utibet_api
        self._volcEngine = VolcEngine()
        self.volcEngine = self._volcEngine.volcEngine_api
        self._yandex = YandexV2()
        self.yandex = self._yandex.yandex_api
        self._yeekit = Yeekit()
        self.yeekit = self._yeekit.yeekit_api
        self._youdao = YoudaoV3()
        self.youdao = self._youdao.youdao_api
        self._translators_dict = {
            'alibaba': self._alibaba, 'apertium': self._apertium, 'argos': self._argos, 'baidu': self._baidu,
            'bing': self._bing,
            'caiyun': self._caiyun, 'cloudTranslation': self._cloudTranslation, 'deepl': self._deepl,
            'elia': self._elia, 'google': self._google,
            'hujiang': self._hujiang, 'iciba': self._iciba, 'iflytek': self._iflytek, 'iflyrec': self._iflyrec,
            'itranslate': self._itranslate,
            'judic': self._judic, 'languageWire': self._languageWire, 'lingvanex': self._lingvanex,
            'niutrans': self._niutrans, 'mglip': self._mglip,
            'mirai': self._mirai, 'modernMt': self._modernMt, 'myMemory': self._myMemory, 'papago': self._papago,
            'qqFanyi': self._qqFanyi,
            'qqTranSmart': self._qqTranSmart, 'reverso': self._reverso, 'sogou': self._sogou, 'sysTran': self._sysTran,
            'tilde': self._tilde,
            'translateCom': self._translateCom, 'translateMe': self._translateMe, 'utibet': self._utibet,
            'volcEngine': self._volcEngine, 'yandex': self._yandex,
            'yeekit': self._yeekit, 'youdao': self._youdao,
        }
        self.translators_dict = {
            'alibaba': self.alibaba, 'apertium': self.apertium, 'argos': self.argos, 'baidu': self.baidu,
            'bing': self.bing,
            'caiyun': self.caiyun, 'cloudTranslation': self.cloudTranslation, 'deepl': self.deepl, 'elia': self.elia,
            'google': self.google,
            'hujiang': self.hujiang, 'iciba': self.iciba, 'iflytek': self.iflytek, 'iflyrec': self.iflyrec,
            'itranslate': self.itranslate,
            'judic': self.judic, 'languageWire': self.languageWire, 'lingvanex': self.lingvanex,
            'niutrans': self.niutrans, 'mglip': self.mglip,
            'mirai': self.mirai, 'modernMt': self.modernMt, 'myMemory': self.myMemory, 'papago': self.papago,
            'qqFanyi': self.qqFanyi,
            'qqTranSmart': self.qqTranSmart, 'reverso': self.reverso, 'sogou': self.sogou, 'sysTran': self.sysTran,
            'tilde': self.tilde,
            'translateCom': self.translateCom, 'translateMe': self.translateMe, 'utibet': self.utibet,
            'volcEngine': self.volcEngine, 'yandex': self.yandex,
            'yeekit': self.yeekit, 'youdao': self.youdao,
        }

        self.translators_list = ['alibaba', 'apertium', 'argos', 'baidu', 'bing', 'caiyun', 'cloudTranslation', 'deepl',
                                 'elia', 'google',
                                 'hujiang', 'iciba', 'iflytek', 'iflyrec', 'itranslate', 'judic', 'languageWire',
                                 'lingvanex', 'niutrans',
                                 'mglip', 'mirai', 'modernMt', 'myMemory', 'papago', 'qqFanyi', 'qqTranSmart',
                                 'reverso', 'sogou', 'sysTran',
                                 'tilde', 'translateCom', 'translateMe', 'utibet', 'volcEngine', 'yandex', 'yeekit',
                                 'youdao']

        self.translators_dict_async = {
            tran: getattr(self, f"_{tran}").trans_api_async
            for tran in self.translators_list
        }
        self.translators_pool = list(self.translators_dict.keys())
        self.translators_pool_async = list(self.translators_dict_async.keys())
        self.not_en_langs = {'utibet': 'ti', 'mglip': 'mon'}
        self.not_zh_langs = {'languageWire': 'fr', 'tilde': 'fr', 'elia': 'fr', 'apertium': 'spa', 'judic': 'de'}
        self.pre_acceleration_label = 0
        self.example_query_text = '你好。\n欢迎你！'
        self.success_translators_pool = []
        self.failure_translators_pool = []

    def translate_text(self,
                       query_text: str,
                       translator: str = 'alibaba',
                       from_language: str = 'auto',
                       to_language: str = 'en',
                       if_use_preacceleration: bool = False,
                       **kwargs: ApiKwargsType,
                       ) -> Union[str, dict]:
        """
        :param query_text: str, must.
        :param translator: str, default 'alibaba'.
        :param from_language: str, default 'auto'.
        :param to_language: str, default 'en'.
        :param if_use_preacceleration: bool, default False.
        :param **kwargs:
                :param is_detail_result: bool, default False.
                :param http_client: str, default 'requests' (except reverso). Union['requests', 'niquests', 'httpx', 'cloudscraper']
                :param professional_field: str, support alibaba(), baidu(), caiyun(), cloudTranslation(), elia(), sysTran(), youdao(), volcEngine() only.
                :param timeout: Optional[float], default None.
                :param proxies: Optional[dict], default None.
                :param sleep_seconds: float, default 0.
                :param update_session_after_freq: int, default 1000.
                :param update_session_after_seconds: float, default 1500.
                :param if_use_cn_host: bool, default False. Support google(), bing() only.
                :param reset_host_url: str, default None. Support google(), yandex() only.
                :param if_check_reset_host_url: bool, default True. Support google(), yandex() only.
                :param if_ignore_empty_query: bool, default True.
                :param if_ignore_limit_of_length: bool, default False.
                :param limit_of_length: int, default 20000.
                :param if_show_time_stat: bool, default False.
                :param show_time_stat_precision: int, default 2.
                :param if_print_warning: bool, default True.
                :param lingvanex_model: str, default 'B2C', choose from ("B2C", "B2B").
                :param myMemory_mode: str, default "web", choose from ("web", "api").
        :return: str or dict
        """

        if translator not in self.translators_pool:
            raise TranslatorError

        if not self.pre_acceleration_label and if_use_preacceleration:
            _ = self.preaccelerate()

        return self.translators_dict[translator](query_text=query_text, from_language=from_language,
                                                 to_language=to_language, **kwargs)

    async def translate_text_async(self,
                                   query_text: str,
                                   translator: str = 'google',
                                   from_language: str = 'auto',
                                   to_language: str = 'en',
                                   if_use_preacceleration: bool = False,
                                   **kwargs: ApiKwargsType,
                                   ) -> Union[str, dict]:
        """
        :param query_text: str, must.
        :param translator: str, default 'alibaba'.
        :param from_language: str, default 'auto'.
        :param to_language: str, default 'en'.
        :param if_use_preacceleration: bool, default False.
        :param **kwargs:
                :param is_detail_result: bool, default False.
                :param http_client: str, default 'requests' (except reverso). Union['requests', 'niquests', 'httpx', 'cloudscraper']
                :param professional_field: str, support alibaba(), baidu(), caiyun(), cloudTranslation(), elia(), sysTran(), youdao(), volcEngine() only.
                :param timeout: Optional[float], default None.
                :param proxies: Optional[dict], default None.
                :param sleep_seconds: float, default 0.
                :param update_session_after_freq: int, default 1000.
                :param update_session_after_seconds: float, default 1500.
                :param if_use_cn_host: bool, default False. Support google(), bing() only.
                :param reset_host_url: str, default None. Support google(), yandex() only.
                :param if_check_reset_host_url: bool, default True. Support google(), yandex() only.
                :param if_ignore_empty_query: bool, default True.
                :param if_ignore_limit_of_length: bool, default False.
                :param limit_of_length: int, default 20000.
                :param if_show_time_stat: bool, default False.
                :param show_time_stat_precision: int, default 2.
                :param if_print_warning: bool, default True.
                :param lingvanex_model: str, default 'B2C', choose from ("B2C", "B2B").
                :param myMemory_mode: str, default "web", choose from ("web", "api").
        :return: str or dict
        """

        if translator not in self.translators_pool_async:
            raise TranslatorError

        if not self.pre_acceleration_label and if_use_preacceleration:
            _ = await self.preaccelerate_async()

        return await self.translators_dict_async[translator](query_text=query_text, from_language=from_language,
                                                             to_language=to_language, **kwargs)

    def translate_html(self,
                       html_text: str,
                       translator: str = 'alibaba',
                       from_language: str = 'auto',
                       to_language: str = 'en',
                       n_jobs: int = 1,
                       if_use_preacceleration: bool = False,
                       **kwargs: ApiKwargsType,
                       ) -> str:
        """
        Translate the displayed content of html without changing the html structure.
        :param html_text: str, must.
        :param translator: str, default 'alibaba'.
        :param from_language: str, default 'auto'.
        :param to_language: str, default 'en'.
        :param n_jobs: int, default 1. -1 means os.cpu_cnt().
        :param if_use_preacceleration: bool, default False.
        :param **kwargs:
                :param is_detail_result: bool, default False, must False.
                :param http_client: str, default 'requests' (except reverso). Union['requests', 'niquests', 'httpx', 'cloudscraper']
                :param professional_field: str, support alibaba(), baidu(), caiyun(), cloudTranslation(), elia(), sysTran(), youdao(), volcEngine() only.
                :param timeout: Optional[float], default None.
                :param proxies: Optional[dict], default None.
                :param sleep_seconds: float, default 0.
                :param update_session_after_freq: int, default 1000.
                :param update_session_after_seconds: float, default 1500.
                :param if_use_cn_host: bool, default False. Support google(), bing() only.
                :param reset_host_url: str, default None. Support google(), argos(), yandex() only.
                :param if_check_reset_host_url: bool, default True. Support google(), yandex() only.
                :param if_ignore_empty_query: bool, default True.
                :param if_ignore_limit_of_length: bool, default False.
                :param limit_of_length: int, default 20000.
                :param if_show_time_stat: bool, default False.
                :param show_time_stat_precision: int, default 2.
                :param if_print_warning: bool, default True.
                :param lingvanex_model: str, default 'B2C', choose from ("B2C", "B2B").
                :param myMemory_mode: str, default "web", choose from ("web", "api").
        :return: str
        """

        if translator not in self.translators_pool or kwargs.get('is_detail_result', False) or n_jobs > self.cpu_cnt:
            raise TranslatorError

        if not self.pre_acceleration_label and if_use_preacceleration:
            _ = self.preaccelerate()

        def _translate_text(sentence: str) -> Tuple[str, str]:
            return sentence, self.translators_dict[translator](query_text=sentence, from_language=from_language,
                                                               to_language=to_language, **kwargs)

        pattern = re.compile('>([\\s\\S]*?)<')  # not perfect
        sentence_list = list(set(pattern.findall(html_text)))

        n_jobs = self.cpu_cnt if n_jobs <= 0 else n_jobs
        with pathos_multiprocessing.ProcessPool(n_jobs) as pool:
            result_list = pool.map(_translate_text, sentence_list)

        result_dict = {text: f'>{ts_text}<' for text, ts_text in result_list}
        _get_result_func = lambda k: result_dict.get(k.group(1), '')
        return pattern.sub(repl=_get_result_func, string=html_text)

    def _test_translate(self, _ts: str, timeout: Optional[float] = None, if_show_time_stat: bool = False) -> str:
        from_language = self.not_zh_langs[_ts] if _ts in self.not_zh_langs else 'auto'
        to_language = self.not_en_langs[_ts] if _ts in self.not_en_langs else 'en'
        result = self.translators_dict[_ts](
            query_text=self.example_query_text,
            translator=_ts,
            from_language=from_language,
            to_language=to_language,
            if_print_warning=False,
            timeout=timeout,
            if_show_time_stat=if_show_time_stat
        )
        return result

    async def _test_translate_async(self, _ts: str, timeout: Optional[float] = None,
                                    if_show_time_stat: bool = False) -> str:
        from_language = self.not_zh_langs[_ts] if _ts in self.not_zh_langs else 'auto'
        to_language = self.not_en_langs[_ts] if _ts in self.not_en_langs else 'en'
        result = await self.translators_dict_async[_ts](
            query_text=self.example_query_text,
            translator=_ts,
            from_language=from_language,
            to_language=to_language,
            if_print_warning=False,
            timeout=timeout,
            if_show_time_stat=if_show_time_stat
        )
        return result

    def get_languages(self, translator: str = 'bing'):
        language_map = self._translators_dict[translator].language_map
        if language_map:
            return language_map

        _ = self._test_translate(_ts=translator)
        return self._translators_dict[translator].language_map

    def preaccelerate(self, timeout: Optional[float] = None, if_show_time_stat: bool = True, **kwargs: str) -> dict:
        if self.pre_acceleration_label > 0:
            raise TranslatorError('Preacceleration can only be performed once.')

        self.example_query_text = kwargs.get('example_query_text', self.example_query_text)

        sys.stderr.write('Preacceleration-Process will take a few minutes.\n')
        sys.stderr.write('Tips: The smaller `timeout` value, the fewer translators pass the test '
                         'and the less time it takes to preaccelerate. However, the slow speed of '
                         'preacceleration does not mean the slow speed of later translation.\n\n')

        for i in tqdm.tqdm(range(len(self.translators_pool)), desc='Preacceleration Process', ncols=80):
            _ts = self.translators_pool[i]
            try:
                _ = self._test_translate(_ts, timeout, if_show_time_stat)
                self.success_translators_pool.append(_ts)
            except:
                self.failure_translators_pool.append(_ts)

            self.pre_acceleration_label += 1
        return {'success': self.success_translators_pool, 'failure': self.failure_translators_pool}

    async def preaccelerate_async(self, timeout: Optional[float] = None, if_show_time_stat: bool = True,
                                  **kwargs: str) -> dict:
        if self.pre_acceleration_label > 0:
            raise TranslatorError('Preacceleration can only be performed once.')

        self.example_query_text = kwargs.get('example_query_text', self.example_query_text)

        sys.stderr.write('Preacceleration-Process will take a few minutes.\n')
        sys.stderr.write('Tips: The smaller `timeout` value, the fewer translators pass the test '
                         'and the less time it takes to preaccelerate. However, the slow speed of '
                         'preacceleration does not mean the slow speed of later translation.\n\n')

        for i in tqdm.tqdm(range(len(self.translators_pool_async)), desc='Preacceleration Process', ncols=80):
            _ts = self.translators_pool_async[i]
            try:
                _ = await self._test_translate_async(_ts, timeout, if_show_time_stat)
                self.success_translators_pool.append(_ts)
            except:
                self.failure_translators_pool.append(_ts)

            self.pre_acceleration_label += 1
        return {'success': self.success_translators_pool, 'failure': self.failure_translators_pool}

    def speedtest(self, **kwargs: List[str]) -> None:
        if self.pre_acceleration_label < 1:
            raise TranslatorError('Preacceleration first.')

        test_translators_pool = kwargs.get('test_translators_pool', self.success_translators_pool)

        sys.stderr.write('SpeedTest-Process will take a few seconds.\n\n')
        for i in tqdm.tqdm(range(len(test_translators_pool)), desc='SpeedTest Process', ncols=80):
            _ts = test_translators_pool[i]
            try:
                _ = self._test_translate(_ts, timeout=None, if_show_time_stat=True)
            except:
                pass
        return

    def preaccelerate_and_speedtest(self, timeout: Optional[float] = None, **kwargs: str) -> dict:
        result = self.preaccelerate(timeout=timeout, **kwargs)
        sys.stderr.write('\n\n')
        self.speedtest()
        return result


tss = TranslatorsServer()

_alibaba = tss._alibaba
alibaba = tss.alibaba
_apertium = tss._apertium
apertium = tss.apertium
_argos = tss._argos
argos = tss.argos
_baidu = tss._baidu
baidu = tss.baidu
_bing = tss._bing
bing = tss.bing
_caiyun = tss._caiyun
caiyun = tss.caiyun
_cloudTranslation = tss._cloudTranslation
cloudTranslation = tss.cloudTranslation
_deepl = tss._deepl
deepl = tss.deepl
_elia = tss._elia
elia = tss.elia
_google = tss._google
google = tss.google
_hujiang = tss._hujiang
hujiang = tss.hujiang
_iciba = tss._iciba
iciba = tss.iciba
_iflytek = tss._iflytek
iflytek = tss.iflytek
_iflyrec = tss._iflyrec
iflyrec = tss.iflyrec
_itranslate = tss._itranslate
itranslate = tss.itranslate
_judic = tss._judic
judic = tss.judic
_languageWire = tss._languageWire
languageWire = tss.languageWire
_lingvanex = tss._lingvanex
lingvanex = tss.lingvanex
_niutrans = tss._niutrans
niutrans = tss.niutrans
_mglip = tss._mglip
mglip = tss.mglip
_mirai = tss._mirai
mirai = tss.mirai
_modernMt = tss._modernMt
modernMt = tss.modernMt
_myMemory = tss._myMemory
myMemory = tss.myMemory
_papago = tss._papago
papago = tss.papago
_qqFanyi = tss._qqFanyi
qqFanyi = tss.qqFanyi
_qqTranSmart = tss._qqTranSmart
qqTranSmart = tss.qqTranSmart
_reverso = tss._reverso
reverso = tss.reverso
_sogou = tss._sogou
sogou = tss.sogou
_sysTran = tss._sysTran
sysTran = tss.sysTran
_tilde = tss._tilde
tilde = tss.tilde
_translateCom = tss._translateCom
translateCom = tss.translateCom
_translateMe = tss._translateMe
translateMe = tss.translateMe
_utibet = tss._utibet
utibet = tss.utibet
_volcEngine = tss._volcEngine
volcEngine = tss.volcEngine
_yandex = tss._yandex
yandex = tss.yandex
_yeekit = tss._yeekit
yeekit = tss.yeekit
_youdao = tss._youdao
youdao = tss.youdao

translate_text = tss.translate_text
translate_text_async = tss.translate_text_async
translate_html = tss.translate_html
translators_pool = tss.translators_pool
get_languages = tss.get_languages
get_region_of_server = tss.get_region_of_server

preaccelerate = tss.preaccelerate
speedtest = tss.speedtest
preaccelerate_and_speedtest = tss.preaccelerate_and_speedtest
# sys.stderr.write(f'Support translators {translators_pool} only.\n')
