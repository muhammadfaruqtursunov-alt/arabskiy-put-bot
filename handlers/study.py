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
        await message.answer(f"⚠️ Слова не найдены.\nvol={volume} lesson={lesson}")
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
