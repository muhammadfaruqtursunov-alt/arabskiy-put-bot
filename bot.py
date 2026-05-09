import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
import database as db
from locales import t
from words import get_lesson_words, get_lesson_meta
import scheduler as sched

from handlers import quiz_visual, quiz_written, weekly_test, settings

logging.basicConfig(level=logging.INFO)


def word_text(word, lang):
    if lang == "ru":
        return t("ru", "word_line_ru", ar=word["ar"], ru=word["ru"])
    elif lang == "tj":
        return t("tj", "word_line_tj", ar=word["ar"], tj=word["tj"])
    else:
        return t("ru", "word_line_both", ar=word["ar"], tj=word["tj"], ru=word["ru"])


async def main():
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

    @dp.message(Command("start_lesson"))
    async def cmd_start_lesson(message: Message):
        user_id = message.from_user.id
        user = db.get_user(user_id)
        if not user:
            db.create_user(user_id)
            user = db.get_user(user_id)
        ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"
        volume = user["current_volume"]
        lesson = user["current_lesson"]
        words = get_lesson_words(volume, lesson)
        if not words:
            await message.answer(f"Слова не найдены. vol={volume} lesson={lesson}")
            return
        meta = get_lesson_meta(volume, lesson)
        theme = meta.get("theme_tj" if ui == "tj" else "theme_ru", "")
        db.set_session(user_id, lesson=lesson, word_index=0, failures=0, phase="study")
        db.update_user(user_id, state="study")
        header = t(ui, "lesson_header", lesson=lesson, theme=theme)
        lines = [word_text(w, user["lang"]) for w in words]
        text = header + "\n".join(lines)
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=t(ui, "btn_learned"), callback_data="lesson_learned"),
            InlineKeyboardButton(text=t(ui, "btn_repeat"), callback_data="lesson_repeat"),
        ]])
        await message.answer(text, reply_markup=kb)

    @dp.callback_query(lambda c: c.data == "lesson_repeat")
    async def cb_repeat(callback: CallbackQuery):
        await callback.answer()
        await cmd_start_lesson(callback.message)

    @dp.callback_query(lambda c: c.data == "lesson_learned")
    async def cb_learned(callback: CallbackQuery):
        await callback.answer()
        user_id = callback.from_user.id
        user = db.get_user(user_id)
        ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"
        db.set_session(user_id, phase="visual", word_index=0, failures=0)
        db.update_user(user_id, state="quiz_visual")
        await callback.message.answer(t(ui, "start_visual"))
        from handlers.quiz_visual import send_visual_question
        await send_visual_question(callback.message, user_id)

    dp.include_router(settings.router)
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
        if not session:
            return
        print(f"TEXT: state={user['state']} phase={session['phase']} text={message.text!r}", flush=True)
        if user["state"] == "quiz_written" and session["phase"] == "written":
            await quiz_written.handle_written_answer(message)
            return
        if session["phase"] == "weekly_written":
            await weekly_test.handle_weekly_written_answer(message, user_id)

    await bot.delete_webhook(drop_pending_updates=True)
    sched.setup(bot)
    await dp.start_polling(bot)


asyncio.run(main())
