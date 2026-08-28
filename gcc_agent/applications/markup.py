"""Telegram markup for the application workflow."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

EXIT_BUTTON_LABEL = {
    "zh-TW": "❌ 退出申請",
    "zh-CN": "❌ 退出申请",
    "en": "❌ Exit Application",
}
APPLY_FORM_BUTTON_LABEL = {
    "zh-TW": "📋 前往申請表",
    "zh-CN": "📋 前往申请表",
    "en": "📋 Go to Application Form",
}


def make_exit_markup(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            EXIT_BUTTON_LABEL.get(lang, EXIT_BUTTON_LABEL["zh-TW"]),
            callback_data="intent_exit",
        )
    ]])


def make_completion_markup(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            APPLY_FORM_BUTTON_LABEL.get(lang, APPLY_FORM_BUTTON_LABEL["zh-TW"]),
            url="https://www.gccofficial.org/application",
        )
    ]])
