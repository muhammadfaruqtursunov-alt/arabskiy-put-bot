import sys
print(f"Python: {sys.version}", flush=True)
print(f"Starting imports...", flush=True)

import asyncio
import logging

print("asyncio ok", flush=True)

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

print("aiogram ok", flush=True)

from config import BOT_TOKEN
import database as db
from locales import t
import scheduler as sched

print("local imports ok", flush=True)

from handlers import study, quiz_visual, quiz_written, weekly_test, settings

print("handlers ok", flush=True)

logging.basicConfig(level=logging.INFO)


async def main():
    print("main() started", flush=True)
    db.init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        user_id = message.from_user.id
        db.create_user(user_id)
        user = db.get_user(user_id)
        ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"
        await message.answer(t(ui, "welcome"))

    dp.include_router(settings.router)
    dp.include_router(study.router)
    dp.include_router(quiz_visual.router)
    dp.include_router(quiz_written.router)
    dp.include_router(weekly_test.router)

    @dp.message()
    async def global_text_handler(message: Message):
        if not message.text or message.text.startswith("/"):
            return
        user_id = message.from_user.id
        user = db.get_user(user_id)
        if not user:
            return
        session = db.get_session(user_id)
        if session and session["phase"] == "weekly_written":
            await weekly_test.handle_weekly_written_answer(message, user_id)

    await bot.delete_webhook(drop_pending_updates=True)
    sched.setup(bot)
    print("Starting polling...", flush=True)
    await dp.start_polling(bot)


print("Calling asyncio.run...", flush=True)
asyncio.run(main())
