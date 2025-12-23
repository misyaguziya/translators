import translators as tss
from translators.server import tss as serv
import asyncio

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
            continue
        ar_text = await serv._test_translate_async(tans)
        print("async: ",ar_text)

asyncio.run(test())
# baidu, deepl, iciba, judic