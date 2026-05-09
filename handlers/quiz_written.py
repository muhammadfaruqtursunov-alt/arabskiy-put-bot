from aiogram import Router
from aiogram.types import Message
import database as db
from words import get_lesson_words, normalize
from locales import t, get_fail_text

router = Router()
MAX_FAILURES = 3


async def send_written_question(message: Message, user_id: int):
    user = db.get_user(user_id)
    session = db.get_session(user_id)
    ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"
    words = get_lesson_words(user["current_volume"], session["lesson"])
    idx = session["word_index"]
    if idx >= len(words):
        await finish_lesson(message, user_id, user, session)
        return
    word = words[idx]
    await message.answer(t(ui, "written_question", ar=word["ar"]))


async def finish_lesson(message: Message, user_id: int, user, session):
    ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"
    lesson = session["lesson"]
    volume = user["current_volume"]
    words = get_lesson_words(volume, lesson)
    week = _current_week(user_id)
    for w in words:
        db.mark_word(user_id, w["id"], "learned", week)
    learned = len(db.get_learned_words(user_id, week))
    await message.answer(t(ui, "lesson_passed", lesson=lesson))
    if learned >= 70:
        from handlers.weekly_test import start_weekly_test
        await start_weekly_test(message, user_id)
    else:
        db.update_user(user_id, current_lesson=lesson + 1, state="idle")
        db.clear_session(user_id)


def _current_week(user_id: int) -> int:
    user = db.get_user(user_id)
    return user["current_volume"] * 100 + user["current_lesson"] // 7


def check_answer(answer: str, word: dict) -> bool:
    ru_variants = [normalize(v.strip()) for v in word["ru"].split(",")]
    tj_variants = [normalize(v.strip()) for v in word["tj"].split(",")]
    return answer in ru_variants or answer in tj_variants


def correct_display(word: dict, lang: str) -> str:
    if lang == "both":
        return f"{word['tj']} / {word['ru']}"
    elif lang == "ru":
        return word["ru"]
    else:
        return word["tj"]


async def handle_written_answer(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user or user["state"] not in ("quiz_written", "weekly"):
        return
    session = db.get_s
