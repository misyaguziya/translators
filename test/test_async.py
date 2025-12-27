from translators.base import TranslatorError
from translators.server import tss as serv
from translators import server_async
import asyncio
import traceback

async def test():
    for i, tans in enumerate(serv.translators_list):
        # if i < 27:
        #     continue
        print(i, tans)
        try:
            ar_text = serv._test_translate(tans)
            print("sync: ",ar_text)
        except Exception as e:
            print(e)
        try:
            ar_text = await server_async.async_tss._test_translate(tans)
            print("async: ",ar_text)
        except Exception as e:
            traceback.print_exc()

# asyncio.run(test())

async def test2(tans):
    # text = serv._test_translate(tans)
    # async_text = await server_async.async_tss._test_translate(tans)
    async_text = await server_async.translate_text("hellow",tans, to_language="ar", from_language="en")
    # print(text)
    print(async_text)


asyncio.run(test2("lingvanex"))
# baidu, deepl, iciba, judic, reverso
# deepl work fine with aiohttp, not sync

# judic ??
# qqFanyi
# tilde
# translateMe
# yeekit