from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

import database as db
from words import get_lesson_words, get_lesson_meta
from locales import t

router = Router()


def word_text(word: dict, lang: str, loc_key_both: str, loc_key_ru: str, loc_key_tj: str) -> str:
    if lang == "ru":
        return t("ru", loc_key_ru, ar=word["ar"], ru=word["ru"])
    elif lang == "tj":
        return t("tj", loc_key_tj, ar=word["ar"], tj=word["tj"])
    else:
        return t("ru", loc_key_both, ar=word["ar"], tj=word["tj"], ru=word["ru"])


def get_ui_lang(user) -> str:
    return getattr(user, "ui_lang", "ru") if hasattr(user, "ui_lang") else "ru"


@router.message(Command("start_lesson"))
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
        await message.answer("⚠️ Слова не найдены.")
        return

    meta = get_lesson_meta(volume, lesson)
    theme = meta.get("theme_tj" if ui == "tj" else "theme_ru", "")

    db.set_session(user_id, lesson=lesson, word_index=0, failures=0, phase="study")
    db.update_user(user_id, state="study")

    header = t(ui, "lesson_header", lesson=lesson, theme=theme)
    lines = []
    for w in words:
        lines.append(word_text(w, user["lang"], "word_line_both", "word_line_ru", "word_line_tj"))

    text = header + "\n".join(lines)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(ui, "btn_learned"), callback_data="lesson_learned"),
        InlineKeyboardButton(text=t(ui, "btn_repeat"),  callback_data="lesson_repeat"),
    ]])
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "lesson_repeat")
async def cb_repeat(callback: CallbackQuery):
    await callback.answer()
    await cmd_start_lesson(callback.message)


@router.callback_query(F.data == "lesson_learned")
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
