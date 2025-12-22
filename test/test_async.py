import translators as tss
from translators.server import tss as serv
import asyncio

async def test():
    for tans in serv.translators_list:
        print(tans)
        ar_text = serv._test_translate(tans)
        print("sync: ",ar_text)
        ar_text = await serv._test_translate_async(tans)
        print("async: ",ar_text)

asyncio.run(test())
# baidu