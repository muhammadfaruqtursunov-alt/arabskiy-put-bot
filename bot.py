import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
import database as db
from locales import t
import scheduler as sched

from handlers import study, quiz_visual, quiz_written, weekly_test, settings

logging.basicConfig(level=logging.INFO)


async def main():
    db.init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # /start — register BEFORE routers
    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        user_id = message.from_user.id
        db.create_user(user_id)
        user = db.get_user(user_id)
        ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"
        await message.answer(t(ui, "welcome"))

    # Routers
    dp.include_router(settings.router)
    dp.include_router(study.router)
    dp.include_router(quiz_visual.router)
    dp.include_router(quiz_written.router)
    dp.include_router(weekly_test.router)

    # Weekly written answers — LAST, only for weekly_written phase
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

    sched.setup(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
