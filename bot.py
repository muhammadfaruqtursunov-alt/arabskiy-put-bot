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
from words import get_lesson_words, get_lesson_meta, normalize
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
            await message.answer(f"⚠️ Слова не найдены. vol={volume} lesson={lesson}")
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
    async def cb
