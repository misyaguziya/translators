import translators as tss
import asyncio

async def test():
    ar_text = await tss.translate_text_async("Hello World!",to_language="ar")
    print(ar_text)

asyncio.run(test())