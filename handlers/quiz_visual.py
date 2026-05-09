from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import database as db
from words import get_lesson_words, make_visual_choices
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
        db.set_session(user_id, phase="written", word_index=0, failures=0)
        db.update_user(user_id, state="quiz_written")
        await message.answer(t(ui, "start_written"))
        from handlers.quiz_written import send_written_question
        await send_written_question(message, user_id)
        return

    word = words[idx]
    choices, correct_label = make_visual_choices(word, words, user["lang"])

    # Храним word_id правильного и word_id выбранного — без текста в callback
    # choices — список слов в том же порядке что и кнопки
    # Получаем id каждого слова из choices через обратный поиск
    def get_word_id_by_label(label, all_words, lang):
        for w in all_words:
            if lang == "ru" and w["ru"] == label:
                return w["id"]
            elif lang == "tj" and w["tj"] == label:
                return w["id"]
            elif lang not in ("ru", "tj") and f"{w['tj']} / {w['ru']}" == label:
                return w["id"]
        return 0

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=c,
            callback_data=f"vis_{word['id']}_{get_word_id_by_label(c, words, user['lang'])}"
        )]
        for c in choices
    ])
    await message.answer(
        t(ui, "visual_question", ar=word["ar"]),
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("vis_"))
async def cb_visual_answer(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    session = db.get_session(user_id)
    ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"

    parts = callback.data.split("_")
    correct_word_id = int(parts[1])
    chosen_word_id = int(parts[2])

    words = get_lesson_words(user["current_volume"], session["lesson"])
    correct_word = next((w for w in words if w["id"] == correct_word_id), None)
    if not correct_word:
        return

    def label(w):
        if user["lang"] == "ru":
            return w["ru"]
        elif user["lang"] == "tj":
            return w["tj"]
        else:
            return f"{w['tj']} / {w['ru']}"

    if chosen_word_id == correct_word_id:
        await callback.message.answer(t(ui, "visual_correct"))
        db.set_session(user_id, word_index=session["word_index"] + 1, failures=0)
        await send_visual_question(callback.message, user_id)
    else:
        failures = session["failures"] + 1
        db.set_session(user_id, failures=failures)
        await callback.message.answer(t(ui, "visual_wrong", correct=label(correct_word)))

        if failures >= MAX_FAILURES:
            fail_idx = session.get("fail_texts_index", 0)
            await callback.message.answer(get_fail_text(ui, fail_idx))
            db.set_session(user_id, fail_texts_index=fail_idx + 1)
            await callback.message.answer(t(ui, "failures_visual"))
            db.set_session(user_id, phase="study", word_index=0, failures=0)
            db.update_user(user_id, state="study")
            from handlers.study import cmd_start_lesson
            await cmd_start_lesson(callback.message)
        else:
            await send_visual_question(callback.message, user_id)
