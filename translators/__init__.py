__version__ = "6.0.2"
__author__ = "UlionTse"

from translators.server import (
    translate_text,
    translate_html,
    translators_pool,
    get_languages,
    get_region_of_server,
    preaccelerate_and_speedtest,
)

import translators.server_async as server_async

__all__ = (
    "__version__",
    "__author__",
    "translate_text",
    "translate_html",
    "translators_pool",
    "get_languages",
    "get_region_of_server",
    "preaccelerate_and_speedtest",
)
