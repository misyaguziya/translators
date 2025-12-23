import os
import sys
import json
import requests
import niquests
from translators.base import Tse, TranslatorError


class Region(Tse):
    def __init__(self, default_region=None):
        super().__init__()
        self.get_addr_url = 'https://geolocation.onetrust.com/cookieconsentpub/v1/geo/location'
        self.get_ip_url = 'https://httpbin.org/ip'  # 'https://get.geojs.io/v1/ip/country'
        self.ip_api_addr_url = 'http://ip-api.com/json'  # must http.
        self.ip_tb_add_url = 'https://ip.taobao.com/outGetIpInfo'
        self.default_region = os.environ.get('translators_default_region', None) or default_region

    def get_region_of_server(self, if_judge_cn: bool = True, if_print_region: bool = True) -> str:
        if self.default_region:
            if if_print_region:
                sys.stderr.write(f'Using customized region {self.default_region} server backend.\n\n')
            return ('CN' if self.default_region in ('China', 'CN') else 'EN') if if_judge_cn else self.default_region

        find_info = 'Unable to find server backend.'
        connect_info = 'Unable to connect the Internet.'
        try_info = 'Try `os.environ["translators_default_region"] = "EN" or "CN"` before `import translators`'

        _headers_fn = lambda url: self.get_headers(url, if_api=False, if_referer_for_host=True)
        try:
            try:
                data = json.loads(requests.get(self.get_addr_url, headers=_headers_fn(self.get_addr_url)).text[9:-2])
                if if_print_region:
                    sys.stderr.write(f'Using region {data.get("stateName")} server backend.\n\n')
                return data.get('country') if if_judge_cn else data.get("stateName")
            except:
                ip_address = requests.get(self.get_ip_url, headers=_headers_fn(self.get_ip_url)).json()['origin']
                payload = {'ip': ip_address, 'accessKey': 'alibaba-inc'}
                data = requests.post(url=self.ip_tb_add_url, data=payload,
                                     headers=_headers_fn(self.ip_tb_add_url)).json().get('data')
                return data.get('country_id')  # region_id

        except requests.exceptions.ConnectionError as e:
            raise TranslatorError('\n'.join([connect_info, try_info, str(e)]))
        except Exception as e:
            raise TranslatorError('\n'.join([find_info, try_info, str(e)]))

    async def get_region_of_server_async(self, if_judge_cn: bool = True, if_print_region: bool = True) -> str:
        if self.default_region:
            if if_print_region:
                sys.stderr.write(f'Using customized region {self.default_region} server backend.\n\n')
            return ('CN' if self.default_region in ('China', 'CN') else 'EN') if if_judge_cn else self.default_region

        find_info = 'Unable to find server backend.'
        connect_info = 'Unable to connect the Internet.'
        try_info = 'Try `os.environ["translators_default_region"] = "EN" or "CN"` before `import translators`'

        _headers_fn = lambda url: self.get_headers(url, if_api=False, if_referer_for_host=True)
        try:
            try:
                data = json.loads(
                    (await niquests.aget(self.get_addr_url, headers=_headers_fn(self.get_addr_url))).text[9:-2])
                if if_print_region:
                    sys.stderr.write(f'Using region {data.get("stateName")} server backend.\n\n')
                return data.get('country') if if_judge_cn else data.get("stateName")
            except:
                ip_address = (await niquests.aget(self.get_ip_url, headers=_headers_fn(self.get_ip_url))).json()[
                    'origin']
                payload = {'ip': ip_address, 'accessKey': 'alibaba-inc'}
                data = (await niquests.apost(url=self.ip_tb_add_url, data=payload,
                                             headers=_headers_fn(self.ip_tb_add_url))).json().get('data')
                return data.get('country_id')  # region_id

        except niquests.exceptions.ConnectionError as e:
            raise TranslatorError('\n'.join([connect_info, try_info, str(e)]))
        except Exception as e:
            raise TranslatorError('\n'.join([find_info, try_info, str(e)]))