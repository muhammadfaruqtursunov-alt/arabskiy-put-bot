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


async def handle_written_answer(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user or user["state"] not in ("quiz_written", "weekly"):
        return
    session = db.get_session(user_id)
    if not session or session["phase"] not in ("written",):
        return
    ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"
    words = get_lesson_words(user["current_volume"], session["lesson"])
    idx = session["word_index"]
    if idx >= len(words):
        return
    word = words[idx]
    answer = normalize(message.text)
    is_correct = check_answer(answer, word)
    if is_correct:
        await message.answer(t(ui, "written_correct"))
        db.set_session(user_id, word_index=idx + 1, failures=0)
        await send_written_question(message, user_id)
    else:
        failures = session["failures"] + 1
        db.set_session(user_id, failures=failures)
       if user["lang"] == "both":
            correct_display = f"{word['tj']} / {word['ru']}"
        elif user["lang"] == "ru":
            correct_display = word["ru"]
        else:
            correct_display = word["tj"])
        await message.answer(t(ui, "written_wrong", correct=correct_display))
        if failures >= MAX_FAILURES:
            fail_idx = session.get("fail_texts_index", 0)
            await message.answer(get_fail_text(ui, fail_idx))
            db.set_session(user_id, fail_texts_index=fail_idx + 1)
            await message.answer(t(ui, "failures_written"))
            db.set_session(user_id, phase="visual", word_index=0, failures=0)
            db.update_user(user_id, state="quiz_visual")
            from handlers.quiz_visual import send_visual_question
            await send_visual_question(message, user_id)
        else:
            await send_written_question(message, user_id)
