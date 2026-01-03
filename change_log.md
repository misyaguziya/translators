# Translators Library - Changelog

## Version 1.0.1 (Oct 10, 2017)

- Initial build of `translate_api`
- ...(history)

## Version 2.2.2

- Added proxy support

## Version 2.4.0

- Added Youdao translator

## Version 2.4.2

- Added `translate.google()` function

## Version 2.4.4

- Simplified `README.rst`
- Added GitHub homepage link

## Version 3.0.0

- **Breaking Change:** Due to incompatible changes introduced in v2.4.2, incremented major version

## Version 4.0.0

- **Renamed:** Module renamed from `translate_api` to `translators`
- Enhanced warning system

## Version 4.0.1

- Fixed issue with "translators.google.cn"

## Version 4.0.2

- Changed documentation format from RST to MD on PyPI

## Version 4.0.4

- Replaced `print` with `raise`/`warn`
- Added 'zh-cn' language code
- Removed `client=t` parameter

## Version 4.0.6

- Fixed exception raising
- Added license to code

## Version 4.0.8

- Restored `youdao()` function

## Version 4.1.0

- Added Tencent translator

## Version 4.2.0

- Added Alibaba translator
- Added support for `**kwargs`
- Renamed parameter: `proxy` → `proxies`
- Formalized license

## Version 4.2.2

- Set default `from_language` to 'auto'

## Version 4.3.0

- Added Baidu translator

## Version 4.3.2

- Introduced `apis.py` (framework restructuring)

## Version 4.4.0

- Added Bing translator
- Added Sogou translator

## Version 4.4.2

- Improved robustness of Alibaba's `get_language_url`
- Improved robustness of Bing's XPath patterns

## Version 4.4.3

- Fixed Youdao issue when `from_language='auto'` and language detection fails

## Version 4.5.0

- Added DeepL translator
- Added `TranslatorError` exception
- Implemented dynamic `sleep_seconds`
- Updated README

## Version 4.5.4

- Updated README and License

## Version 4.5.8

- Added service backend identification messages
- Updated README with common issues
- Enhanced debug logging

## Version 4.5.14

- Updated README

## Version 4.6.0

- Updated README
- Synchronized version numbering scheme

## Version 4.6.10

- Improved Google translator's handling of emojis
- Enhanced server region request logic

## Version 4.6.18

- Improved Youdao translator's handling of long sentences (>50 chars, errCode40)

## Version 4.6.20

- Enhanced Tencent & DeepL with `language_map`
- Improved Youdao with `action` and `lts` parameters
- Added `use_cache` parameter for speed
- Added function type hints
- Renamed: `use_domain` → `professional_field`

## Version 4.7.0

- Added Yandex translator
- Fixed `use_cache` logic
- Updated README

## Version 4.7.1

- Updated README

## Version 4.7.2

- Enhanced DeepL request headers (`content-type`)

## Version 4.7.3

- Improved output formatting for newlines
- Added `translate_html()` function

## Version 4.7.5

- Upgraded `translate_html()`
- Enhanced Baidu translator (thanks @mozbugbox)
- Implemented request session reuse (thanks @mozbugbox)

## Version 4.7.6

- Removed `use_cache` parameter (language maps cached by default)
- Cached `tkk` in Google translator
- Fixed Yandex `api_url`

## Version 4.7.7

- Improved Google's `get_language_map`

## Version 4.7.8

- Updated README

## Version 4.7.9

- Improved Google's `get_tkk`

## Version 4.7.11

- Enhanced DeepL translator

## Version 4.7.12

- Added `google_v2()`
- Switched to absolute imports

## Version 4.7.13

- Fixed bug in `google_v2` by replacing `execjs` with `json.loads`

## Version 4.7.14

- Updated Baidu, Sogou, Youdao to follow provider changes

## Version 4.7.16

- Enhanced Baidu with `js_txt`

## Version 4.7.20

- Fixed incomplete language map in Google (#37, #42)
- Fixed Bing translator
- Fixed DeepL translator (expanded supported languages from 11 to 24)
- Fixed default `sleep_seconds` (#39)
- Fixed 5000-character query limit (#40)
- Added `check_query_text()`
- Enhanced `get_headers()`
- Optimized `translate_html()` from O(n) to O(1) using multiprocessing

## Version 4.8.0

- Fixed Tencent translator
- Fixed Bing translator
- Fixed Google's incomplete language map
- Removed `temp_language_map`
- Enhanced `request_server_region_info` to accept user input

## Version 4.8.1

- Fixed `request_server_region_info` (HTTPS → HTTP). Merged from @dadas190

## Version 4.9.1

- Added Caiyun translator

## Version 4.9.4

- Fixed changes in `app().js`
- Added configurable timeout (#47)

## Version 4.9.5

- Fixed DeepL. Language map fix merged from @BingLingGroup

## Version 4.10.0

- Added Argos translator
- Fixed Caiyun translator (resolved network address change causing parsing errors)
- Fixed whitespace handling in output

## Version 4.11.0

- Added Iciba translator
- Added Iflytek translator
- Fixed Caiyun translator's auto-language detection error

## Version 4.11.1

- Updated README
- Updated DeepL translator

## Version 4.11.3

- Enhanced Google translator for `consent.google.com` (merged from @mercuree, #57)
- Added `reset_host_url` parameter to Google translator

## Version 4.11.4

- Enhanced Iciba translator for sensitive words
- Enhanced Baidu and Iflytek translators

## Version 5.0.0

- **Changed versioning scheme** to avoid ambiguity (e.g., 4.11.4 < 4.9.4)
- Fixed Yandex translator
- Fixed Google request headers
- Fixed Iflytek language map regex and auto-language detection warnings

## Version 5.0.1

- Enhanced DeepL's `language_map`
- Updated README

## Version 5.0.2

- Updated Baidu, DeepL, Iflytek per service changes
- Specified compatible Python versions

## Version 5.1.0

- Added Reverso translator
- Added Itranslate translator
- Added `translateCom` (Microsoft/Bing-like)
- Replaced `assert` with explicit checks
- Prepared fix for Iflytek's geetest challenge

## Version 5.1.1

- Updated README

## Version 5.2.1

- Added Papago translator
- Added Utibet translator
- Temporarily disabled Iflytek pending fix

## Version 5.2.2

- Fixed `multiprocessing.pool.close()` in `translate_html()` (#67)
- Fixed handling of empty `query_text` (returns '')
- Added and fixed input length limits

## Version 5.3.0

- Rebuilt Baidu translator (added v1/v2)
- Rebuilt Iflytek translator (v2)
- Fixed Youdao `get_sign()` (#74)
- Enhanced Google's data parsing for single words with multiple results (#69)
- Improved multiprocessing (merged from @llabbasmkhll, #71, #72)

## Version 5.3.1

- Updated and restored Iciba translator
- Enhanced Papago translator

## Version 5.4.0

- Added Lingvanex translator
- Added Mglip translator
- Added Niutrans translator
- Set Baidu's default `version` to `v1` and fixed regex bug (#78)

## Version 5.4.1

- Updated README

## Version 5.4.2

- Fixed `request_server_region_info()`

## Version 5.4.3

- Fixed `en_tran()` function
- Fixed Iflytek's `language_map` fetching
- Added `self.default_country` via `os.environ` (merged from @kevindragon, #79)
- Enhanced Papago translator

## Version 5.4.6

- Improved project packaging
- Published package to Anaconda (#90)

## Version 5.4.8

- Enhanced Baidu, Caiyun, DeepL (#83) translators
- Rebuilt Niutrans translator
- Improved paragraph splitting in data parsing

## Version 5.5.0

- Restructured codebase
- Added `translate_text()` function
- Enhanced Yandex translator

## Version 5.5.1

- Added `alibaba_v2()`
- Updated and improved session reuse
- Restructured function index tree
- Added decorators: `get_language_map`, `check_query`, `time_stat`

## Version 5.5.3

- Fixed Tuple type hint for Python <3.9 (#99)
- Updated README with new parameters
- Enhanced `time_stat()` and `translate_html()`

## Version 5.5.4

- Enhanced `check_query()`
- Added `youdao_v2()`, `youdao_v3()`
- Improved Google's data parsing (#100)
- Updated README

## Version 5.5.5

- Enhanced `time_stat()`
- Further improved Google's data parsing (#101)

## Version 5.5.6

- Updated and restored Bing (#104) and Lingvanex translators

## Version 5.6.0

- Renamed: `tencent()` → `qqFanyi()`
- Added `qqTranSmart()`, `modernMT()`, `myMemory()`, `iflyrec()`
- Added incomplete `volcEngine()` (#106)
- Updated Baidu, Itranslate, Lingvanex
- Added `update_session_after_freq` parameter/functionality
- Enhanced `get_server_region()`
- Changed default `sleep_seconds` from random to 0
- Updated README

## Version 5.6.1

- Added `preaccelerate()` function
- Enhanced Caiyun and YoudaoV1
- Updated README

## Version 5.6.2

- Enhanced `preaccelerate()`
- Updated README structure

## Version 5.6.3

- Further enhanced `preaccelerate()` and integrated it into `translate_text()`

## Version 5.7.0

- Added multiple translators: `sysTran()`, `apertium()`, `cloudYi()`, `tilde()`, `translateMe()`, `marai()` (#119)
- Added multiple translators: `yeekit()`, `languageWire()`, `elia()`, `judic()`
- Enhanced `preaccelerate()`

## Version 5.7.1

- Set `python_requires='>=3.8'`
- Added parameter `if_check_reset_host_url=True` (#124)
- Clarified `input_limit` vs `limit_of_length`
- Added `professional_field` info
- Enhanced regex patterns and `preaccelerate()`

## Version 5.7.2

- Enhanced `languageWire()` (#127)
- Added `uncertified()` function (#128)
- Noted Yeekit server issues (#129)
- Updated `setup.py` keywords and README

## Version 5.7.5

- Enhanced `uncertified()` and `debug_language_map()`
- Improved parameter type handling
- Removed all `eval()` usage

## Version 5.7.6

- Enhanced `translateMe()` and `preaccelerate()`
- Added `preaccelerate_and_speedtest()`
- Fixed `debug_language_map()` for translators not supporting 'auto'

## Version 5.7.7

- Updated license and email
- Enhanced parameter types and `sysTran()`
- Noted `translateMe()` server issues

## Version 5.7.8

- Enhanced `myMemory()` with more languages (#132)
- Updated README

## Version 5.7.9

- No functional changes (Conda metadata update)

## Version 5.8.0

- Added `get_languages()` function
- Enhanced `update_session_after_freq` logic (#134) and `update_session_after_seconds`
- Updated README

## Version 5.8.2

- Enhanced `reverso()` (#135)
- Renamed `cloudYi()` to `cloudTranslation()` (added v2)
- Fixed `alibaba_v1`
- Updated README

## Version 5.8.3

- Enhanced Caiyun (#138), DeepL, `debug_language_map()`
- Updated `niutransV2()`
- Updated README

## Version 5.8.4

- Enhanced and fixed `translate_html()` (#145)
- Set default `if_ignore_empty_query=True`
- Set default `n_jobs=1`

## Version 5.8.5

- Enhanced `debug_language_map()` (#144)
- Removed `get_consent_cookie()` (#142)
- Updated license

## Version 5.8.7

- Enhanced DeepL, Bing (#122), Google (#142, #144)
- Enhanced `get_server_region()` (#110)

## Version 5.8.8

- Enhanced Argos, DeepL, Lingvanex

## Version 5.8.9

- Enhanced `get_server_region()` (#147)

## Version 5.9.0

- Added Hujiang translator
- Enhanced Iciba (#151)
- Added `bias_of_length` to `check_query_text()` (#154)

## Version 5.9.1

- Enhanced Baidu (#155)

## Version 5.9.2

- Fixed Yandex (#94)

## Version 5.9.3

- Enhanced Papago (#161), Yandex (#162), Argos, Caiyun, Lingvanex

## Version 5.9.4

- Added multiple HTTP client support (`requests`, `niquests`, `httpx`)
- Added CLI tool `fanyi` (#166)
- Enhanced Papago, Reverso, Utibet

## Version 5.9.6

- Switched from `pyexecjs` to `exejs`

## Version 5.9.8

- Enhanced `Region` class (#167)

## Version 5.9.9

- Requires `exejs>=0.0.4` (#169)

## Version 6.0.0

- Enhanced Papago and Reverso (Cloudflare fixes, #161)
- Added `cloudscraper` HTTP client support
- Enhanced `fanyi` CLI

## Version 6.0.1

- Updated dependency versions
- Updated Conda package version

## Version 6.0.2

- Added multiple translators: `lara()`, `xunjie()`
- Enhanced multiple translators: `argos()`, `iciba()`, `lingvanex()`, `youdao()`
- Enhanced `cli` about input_file
- Enhanced `translate_html` about parallel
