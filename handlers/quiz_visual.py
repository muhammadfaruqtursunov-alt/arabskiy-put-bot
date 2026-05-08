from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import database as db
from words import get_lesson_words, get_lesson_meta, make_visual_choices
from locales import t, get_fail_text

router = Router()
MAX_FAILURES = 3


async def send_visual_question(message: Message, user_id: int):
    user = db.get_user(user_id)
    session = db.get_session(user_id)
    ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"

    words = get_lesson_words(user["current_volume"], session["lesson"])
    idx = session["word_index"]

    if idx >= len(words):
        # Visual quiz passed — go to written
        db.set_session(user_id, phase="written", word_index=0, failures=0)
        db.update_user(user_id, state="quiz_written")
        await message.answer(t(ui, "start_written"), parse_mode="Markdown")
        from handlers.quiz_written import send_written_question
        await send_written_question(message, user_id)
        return

    word = words[idx]
    choices, correct_label = make_visual_choices(word, words, user["lang"])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=c, callback_data=f"vis_{i}_{correct_label}_{word['id']}")]
        for i, c in enumerate(choices)
    ])
    await message.answer(
        t(ui, "visual_question", ar=word["ar"]),
        reply_markup=kb,
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("vis_"))
async def cb_visual_answer(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    session = db.get_session(user_id)
    ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"

    parts = callback.data.split("_", 3)
    chosen_idx = int(parts[1])
    correct_label = parts[2]
    word_id = int(parts[3])

    # Rebuild choices to find chosen label
    words = get_lesson_words(user["current_volume"], session["lesson"])
    word = next((w for w in words if w["id"] == word_id), None)
    if not word:
        return

    choices, _ = make_visual_choices(word, words, user["lang"])
    chosen_label = choices[chosen_idx] if chosen_idx < len(choices) else ""

    if chosen_label == correct_label:
        await callback.message.answer(t(ui, "visual_correct"), parse_mode="Markdown")
        db.set_session(user_id, word_index=session["word_index"] + 1)
        await send_visual_question(callback.message, user_id)
    else:
        failures = session["failures"] + 1
        db.set_session(user_id, failures=failures)

        await callback.message.answer(
            t(ui, "visual_wrong", correct=correct_label),
            parse_mode="Markdown"
        )

        if failures >= MAX_FAILURES:
            # Fail — back to study
            fail_idx = session.get("fail_texts_index", 0)
            await callback.message.answer(get_fail_text(ui, fail_idx), parse_mode="Markdown")
            db.set_session(user_id, fail_texts_index=fail_idx + 1)
            await callback.message.answer(t(ui, "failures_visual"), parse_mode="Markdown")

            db.set_session(user_id, phase="study", word_index=0, failures=0)
            db.update_user(user_id, state="study")

            from handlers.study import cmd_start_lesson
            await cmd_start_lesson(callback.message)
        else:
            # Continue same word
            await send_visual_question(callback.message, user_id)
