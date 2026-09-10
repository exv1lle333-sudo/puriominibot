"""
Раздел "Инструкция": как скачать приложение Happ и подключиться —
отдельно для телефона и для компьютера.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery

import keyboards as kb
from config import HAPP_DOWNLOAD_URL

router = Router()

INTRO_TEXT = (
    "📖 <b>Инструкция по подключению</b>\n\n"
    "Мы рекомендуем приложение <b>Happ</b> — оно работает и на телефоне, "
    "и на компьютере, и обеспечивает стабильное подключение.\n\n"
    "Выбери своё устройство:"
)

PHONE_TEXT = (
    "📱 <b>Инструкция для телефона (iOS / Android)</b>\n\n"
    f"1️⃣ Скачай приложение Happ: {HAPP_DOWNLOAD_URL}\n"
    "2️⃣ Открой раздел «🔑 Подписка» в этом боте и перейди по своей ссылке "
    "подключения — Happ добавит её автоматически (либо добавь вручную "
    "через «+» в приложении).\n"
    "3️⃣ Зайди в настройки подключения и поставь предпочитаемый тип IP: "
    "<b>IPv4</b>.\n\n"
    "4️⃣ Сохрани настройки и подключайся.\n\n"
    "💡 Если соединение нестабильно — напиши в поддержку."
)

PC_TEXT = (
    "💻 <b>Инструкция для компьютера (Windows / macOS / Linux)</b>\n\n"
    f"1️⃣ Скачай приложение Happ: {HAPP_DOWNLOAD_URL}\n"
    "2️⃣ Открой раздел «🔑 Подписка» в этом боте, скопируй свою ссылку "
    "подключения и добавь её в приложении (кнопка добавления подписки).\n"
    "3️⃣ Поставь предпочитаемый тип IP: <b>IPv4</b>.\n\n"
    "4️⃣ Сохрани настройки и подключайся.\n\n"
    "💡 Если соединение нестабильно — напиши в поддержку."
)


@router.callback_query(F.data == "menu_instructions")
async def cb_instructions_menu(callback: CallbackQuery):
    await callback.message.edit_text(INTRO_TEXT, reply_markup=kb.instructions_platform_kb())
    await callback.answer()


@router.callback_query(F.data == "instructions_phone")
async def cb_instructions_phone(callback: CallbackQuery):
    await callback.message.edit_text(PHONE_TEXT, reply_markup=kb.instructions_back_kb())
    await callback.answer()


@router.callback_query(F.data == "instructions_pc")
async def cb_instructions_pc(callback: CallbackQuery):
    await callback.message.edit_text(PC_TEXT, reply_markup=kb.instructions_back_kb())
    await callback.answer()
