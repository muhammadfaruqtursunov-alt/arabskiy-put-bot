from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from locales import t

router = Router()


class SettingsState(StatesGroup):
    waiting_reminder = State()


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        db.create_user(user_id)
        user = db.get_user(user_id)
    ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(ui, "btn_lang_both"), callback_data="lang_both"),
            InlineKeyboardButton(text=t(ui, "btn_lang_ru"),   callback_data="lang_ru"),
            InlineKeyboardButton(text=t(ui, "btn_lang_tj"),   callback_data="lang_tj"),
        ],
        [InlineKeyboardButton(text="⏰ Напоминание / Ёдоваркунӣ", callback_data="set_reminder")],
    ])
    await message.answer(t(ui, "settings_lang"), reply_markup=kb)


@router.callback_query(F.data.startswith("lang_"))
async def cb_set_lang(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    lang_map = {"lang_both": "both", "lang_ru": "ru", "lang_tj": "tj"}
    lang = lang_map.get(callback.data, "both")
    db.update_user(user_id, lang=lang)

    ui = lang if lang in ("ru", "tj") else "ru"
    await callback.message.answer(t(ui, "lang_set"))


@router.callback_query(F.data == "set_reminder")
async def cb_set_reminder(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    user = db.get_user(user_id)
    ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"
    await state.set_state(SettingsState.waiting_reminder)
    await callback.message.answer(t(ui, "settings_reminder"))


@router.message(SettingsState.waiting_reminder)
async def handle_reminder_time(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"
    text = message.text.strip()

    try:
        h, m = text.split(":")
        assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
        time_str = f"{int(h):02d}:{int(m):02d}"
    except Exception:
        await message.answer("⚠️ Неверный формат. Пример: 08:00")
        return

    db.update_user(user_id, reminder_time=time_str)
    await state.clear()
    await message.answer(t(ui, "reminder_set", time=time_str))


@router.message(Command("progress"))
async def cmd_progress(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        db.create_user(user_id)
        user = db.get_user(user_id)
    ui = user["lang"] if user["lang"] in ("ru", "tj") else "ru"

    week = user["current_volume"] * 100 + user["current_lesson"] // 7
    learned = len(db.get_learned_words(user_id, week))
    await message.answer(
        t(ui, "progress",
          vol=user["current_volume"],
          lesson=user["current_lesson"],
          learned=learned),
    )
