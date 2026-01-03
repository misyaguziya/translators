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
import asyncio
import os
import re
import sys
from typing import Optional, Union, Tuple
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
    'translate_text', 'translate_html', 'translators_pool',
]  # 37


class TranslatorsServer:
    def __init__(self):
        self.cpu_cnt = os.cpu_count()
        self._region = Region()
        # TODO: use async
        self.get_region_of_server = self._region.get_region_of_server_async
        self.server_region = self._region.get_region_of_server(if_print_region=False)
        self._alibaba = AlibabaV2()
        self._apertium = Apertium()
        self._argos = Argos()
        self._baidu = BaiduV1()  # V2
        self._bing = Bing(server_region=self.server_region)
        self._caiyun = Caiyun()
        self._cloudTranslation = cloudTranslationV2()
        self._deepl = Deepl()
        self._elia = Elia()
        self._google = GoogleV2(server_region=self.server_region)
        self._hujiang = Hujiang()
        self._iciba = Iciba()
        self._iflytek = IflytekV2()
        self._iflyrec = Iflyrec()
        self._itranslate = Itranslate()
        self._judic = Judic()
        self._languageWire = LanguageWire()
        self._lingvanex = LingvanexV2()
        self._niutrans = NiutransV2()
        self._mglip = Mglip()
        self._mirai = Mirai()
        self._modernMt = ModernMt()
        self._myMemory = MyMemory()
        self._papago = Papago()
        self._qqFanyi = QQFanyi()
        self._qqTranSmart = QQTranSmart()
        self._reverso = Reverso()
        self._sogou = Sogou()
        self._sysTran = SysTran()
        self._tilde = Tilde()
        self._translateCom = TranslateCom()
        self._translateMe = TranslateMe()
        self._utibet = Utibet()
        self._volcEngine = VolcEngine()
        self._yandex = YandexV2()
        self._yeekit = Yeekit()
        self._youdao = YoudaoV3()
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
        self.translators_list = ['alibaba', 'apertium', 'argos', 'baidu', 'bing', 'caiyun', 'cloudTranslation', 'deepl',
                                 'elia', 'google',
                                 'hujiang', 'iciba', 'iflytek', 'iflyrec', 'itranslate', 'judic', 'languageWire',
                                 'lingvanex', 'niutrans',
                                 'mglip', 'mirai', 'modernMt', 'myMemory', 'papago', 'qqFanyi', 'qqTranSmart',
                                 'reverso', 'sogou', 'sysTran',
                                 'tilde', 'translateCom', 'translateMe', 'utibet', 'volcEngine', 'yandex', 'yeekit',
                                 'youdao']
        self.translators_dict = {
            tran: getattr(self, f"_{tran}").trans_api_async
            for tran in self.translators_list
        }
        for key, value in self.translators_dict.items():
            setattr(self, key, value)

        self.translators_pool = list(self.translators_dict.keys())
        self.not_en_langs = {'utibet': 'ti', 'mglip': 'mon'}
        self.not_zh_langs = {'languageWire': 'fr', 'tilde': 'fr', 'elia': 'fr', 'apertium': 'spa', 'judic': 'de'}
        self.pre_acceleration_label = 0
        self.example_query_text = '你好。\n欢迎你！'
        self.success_translators_pool = []
        self.failure_translators_pool = []

    async def translate_text(self,
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
            _ = await self.preaccelerate()

        return await self.translators_dict[translator](query_text=query_text, from_language=from_language,
                                                             to_language=to_language, **kwargs)

    async def translate_html(self,
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
            _ = await self.preaccelerate()



        pattern = re.compile('>([\\s\\S]*?)<')  # not perfect
        sentence_list = list(set(pattern.findall(html_text)))
        if not sentence_list:
            return html_text

        n_jobs = self.cpu_cnt if n_jobs <= 0 else n_jobs
        semaphore = asyncio.Semaphore(n_jobs)

        async def _translate_text(sentence: str) -> Tuple[str, str]:
            async with semaphore:
                translated = await self.translators_dict[translator](
                    query_text=sentence,
                    from_language=from_language,
                    to_language=to_language,
                    **kwargs
                )
                return sentence, translated

        result_list = await asyncio.gather(
            *(_translate_text(sentence) for sentence in sentence_list)
        )
        result_dict = {src: f'>{dst}<' for src, dst in result_list}

        def _repl(match: re.Match):
            return result_dict.get(match.group(1), match.group(0))

        return pattern.sub(_repl, html_text)

    async def _test_translate(self, _ts: str, timeout: Optional[float] = None,
                                    if_show_time_stat: bool = False) -> str:
        from_language = self.not_zh_langs[_ts] if _ts in self.not_zh_langs else 'auto'
        to_language = "ar"# self.not_en_langs[_ts] if _ts in self.not_en_langs else 'en'
        result = await self.translators_dict[_ts](
            query_text=self.example_query_text,
            translator=_ts,
            from_language=from_language,
            to_language=to_language,
            if_print_warning=False,
            timeout=timeout,
            if_show_time_stat=if_show_time_stat
        )
        return result

    async def get_languages(self, translator: str = 'bing'):
        language_map = self._translators_dict[translator].language_map
        if language_map:
            return language_map

        _ = await self._test_translate(_ts=translator)
        return self._translators_dict[translator].language_map

    async def preaccelerate(self, timeout: Optional[float] = None, if_show_time_stat: bool = True,
                                  **kwargs: str) -> dict:
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
                _ = await self._test_translate(_ts, timeout, if_show_time_stat)
                self.success_translators_pool.append(_ts)
            except:
                self.failure_translators_pool.append(_ts)

            self.pre_acceleration_label += 1
        return {'success': self.success_translators_pool, 'failure': self.failure_translators_pool}

    async def speedtest(self, **kwargs: dict[str, str]) -> None:
        if self.pre_acceleration_label < 1:
            raise TranslatorError('Preacceleration first.')

        test_translators_pool = kwargs.get('test_translators_pool', self.success_translators_pool)

        sys.stderr.write('SpeedTest-Process will take a few seconds.\n\n')
        for i in tqdm.tqdm(range(len(test_translators_pool)), desc='SpeedTest Process', ncols=80):
            _ts = test_translators_pool[i]
            try:
                _ = await self._test_translate(_ts, timeout=None, if_show_time_stat=True)
            except:
                pass
        return

    async def preaccelerate_and_speedtest(self, timeout: Optional[float] = None, **kwargs: str) -> dict:
        result = await self.preaccelerate(timeout=timeout, **kwargs)
        sys.stderr.write('\n\n')
        await self.speedtest()
        return result


async_tss = TranslatorsServer()
translate_text = async_tss.translate_text
translate_html = async_tss.translate_html
translators_pool = async_tss.translators_pool
get_languages = async_tss.get_languages
get_region_of_server = async_tss.get_region_of_server

preaccelerate = async_tss.preaccelerate
speedtest = async_tss.speedtest
preaccelerate_and_speedtest = async_tss.preaccelerate_and_speedtest
# sys.stderr.write(f'Support translators {translators_pool} only.\n')
