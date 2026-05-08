import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO, stream=sys.stdout)


async def main():
    print(f"BOT_TOKEN length={len(BOT_TOKEN)} starts={BOT_TOKEN[:12]}", flush=True)
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    @dp.message()
    async def echo_all(message: Message):
        print(f"GOT: {message.text!r} from {message.from_user.id}", flush=True)
        await message.answer(f"ECHO: {message.text}")

    me = await bot.get_me()
    print(f"BOT IS: @{me.username} id={me.id}", flush=True)

    # Удаляет webhook и все ожидающие апдейты — чистый старт
    await bot.delete_webhook(drop_pending_updates=True)
    print("Webhook deleted, pending dropped. Starting polling...", flush=True)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
