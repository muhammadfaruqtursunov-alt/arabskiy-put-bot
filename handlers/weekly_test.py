import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import database as db
from words import get_words_by_ids, make_visual_choices, normalize
from locales import t, get_fail_text
from config import WEEKLY_TEST_COUNT

router = Router()
MAX_FAILURES = 3

# Store weekly test state in session extras via DB session table
# phase = 'weekly_visual' or 'weekly_written'
# We reuse session.lesson field as packed word_ids (json string)


async def start_weekly_test(message: Message, user_id: int):
    user = db.get_user(user_id)
    ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"

    week = _week_key(user)
    learned_ids = db.get_learned_words(user_id, week)

    if len(learned_ids) < WEEKLY_TEST_COUNT:
        test_ids = learned_ids
    else:
        test_ids = random.sample(learned_ids, WEEKLY_TEST_COUNT)

    import json
    db.set_session(user_id,
                   lesson=0,
                   word_index=0,
                   failures=0,
                   phase="weekly_visual",
                   fail_texts_index=0)
    # Store test_ids as JSON in a temp file keyed by user_id (simple approach)
    _save_test_ids(user_id, test_ids)

    db.update_user(user_id, state="weekly")
    await message.answer(t(ui, "weekly_start"), parse_mode="Markdown")
    await send_weekly_visual(message, user_id)


def _week_key(user) -> int:
    return user["current_volume"] * 100 + (user["current_lesson"] // 7)


def _save_test_ids(user_id: int, ids: list):
    import json, os
    os.makedirs("data/sessions", exist_ok=True)
    with open(f"data/sessions/{user_id}_weekly.json", "w") as f:
        json.dump(ids, f)


def _load_test_ids(user_id: int) -> list:
    import json
    try:
        with open(f"data/sessions/{user_id}_weekly.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


async def send_weekly_visual(message: Message, user_id: int):
    user = db.get_user(user_id)
    session = db.get_session(user_id)
    ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"

    test_ids = _load_test_ids(user_id)
    idx = session["word_index"]

    if idx >= len(test_ids):
        # Visual done → written
        db.set_session(user_id, phase="weekly_written", word_index=0, failures=0)
        await message.answer(t(ui, "start_written"), parse_mode="Markdown")
        await send_weekly_written(message, user_id)
        return

    word_id = test_ids[idx]
    words = get_words_by_ids(test_ids)
    word = next((w for w in words if w["id"] == word_id), None)
    if not word:
        return

    choices, correct_label = make_visual_choices(word, words, user["lang"])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=c, callback_data=f"wvis_{i}_{word['id']}")]
        for i, c in enumerate(choices)
    ])
    await message.answer(t(ui, "visual_question", ar=word["ar"]), reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("wvis_"))
async def cb_weekly_visual(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    session = db.get_session(user_id)
    ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"

    parts = callback.data.split("_")
    chosen_idx = int(parts[1])
    word_id = int(parts[2])

    test_ids = _load_test_ids(user_id)
    words = get_words_by_ids(test_ids)
    word = next((w for w in words if w["id"] == word_id), None)
    if not word:
        return

    choices, correct_label = make_visual_choices(word, words, user["lang"])
    chosen_label = choices[chosen_idx] if chosen_idx < len(choices) else ""

    if chosen_label == correct_label:
        await callback.message.answer(t(ui, "visual_correct"), parse_mode="Markdown")
        db.set_session(user_id, word_index=session["word_index"] + 1)
        await send_weekly_visual(callback.message, user_id)
    else:
        failures = session["failures"] + 1
        db.set_session(user_id, failures=failures)
        await callback.message.answer(t(ui, "visual_wrong", correct=correct_label), parse_mode="Markdown")

        if failures >= MAX_FAILURES:
            await _weekly_fail(callback.message, user_id, ui, session)
        else:
            await send_weekly_visual(callback.message, user_id)


async def send_weekly_written(message: Message, user_id: int):
    user = db.get_user(user_id)
    session = db.get_session(user_id)
    ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"

    test_ids = _load_test_ids(user_id)
    idx = session["word_index"]

    if idx >= len(test_ids):
        # Weekly test passed!
        await message.answer(t(ui, "weekly_passed"), parse_mode="Markdown")
        # Advance to next week (volume/lesson stays, just reset)
        next_lesson = user["current_lesson"] + 1
        db.update_user(user_id, current_lesson=next_lesson, state="idle")
        db.clear_session(user_id)
        return

    words = get_words_by_ids(test_ids)
    word = words[idx] if idx < len(words) else None
    if not word:
        return

    await message.answer(t(ui, "written_question", ar=word["ar"]), parse_mode="Markdown")


# Written answers for weekly test are handled in quiz_written.py handler
# but we need to route weekly_written phase here
async def handle_weekly_written_answer(message: Message, user_id: int):
    user = db.get_user(user_id)
    session = db.get_session(user_id)
    ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"

    test_ids = _load_test_ids(user_id)
    idx = session["word_index"]
    words = get_words_by_ids(test_ids)

    if idx >= len(words):
        return

    word = words[idx]
    answer = normalize(message.text)
    correct_ru = normalize(word["ru"])
    correct_tj = normalize(word["tj"])
    is_correct = answer in (correct_ru, correct_tj)

    if is_correct:
        await message.answer(t(ui, "written_correct"), parse_mode="Markdown")
        db.set_session(user_id, word_index=idx + 1, failures=0)
        await send_weekly_written(message, user_id)
    else:
        failures = session["failures"] + 1
        db.set_session(user_id, failures=failures)
        correct_display = f"{word['tj']} / {word['ru']}"
        await message.answer(t(ui, "written_wrong", correct=correct_display), parse_mode="Markdown")

        if failures >= MAX_FAILURES:
            await _weekly_fail(message, user_id, ui, session)
        else:
            await send_weekly_written(message, user_id)


async def _weekly_fail(message: Message, user_id: int, ui: str, session):
    fail_idx = session.get("fail_texts_index", 0)
    await message.answer(get_fail_text(ui, fail_idx), parse_mode="Markdown")
    db.set_session(user_id, fail_texts_index=fail_idx + 1)
    await message.answer(t(ui, "weekly_failed"), parse_mode="Markdown")

    # Reset all 70 words and restart full week study
    user = db.get_user(user_id)
    week = _week_key(user)
    db.reset_week_progress(user_id, week)

    # Go back to lesson 1 of the week
    week_start_lesson = ((user["current_lesson"] - 1) // 7) * 7 + 1
    db.update_user(user_id, current_lesson=week_start_lesson, state="idle")
    db.clear_session(user_id)
    await message.answer("📚 /start_lesson", parse_mode="Markdown")
