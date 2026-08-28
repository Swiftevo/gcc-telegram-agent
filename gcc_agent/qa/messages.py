"""QA response messages and Telegram markup."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

MEETING_REMINDER = {
    "zh-TW": "\n\n_如希望深入交流，歡迎參與 GCC 定期例會。_",
    "zh-CN": "\n\n_如希望深入交流，欢迎参与 GCC 定期例会。_",
    "en": "\n\n_For deeper discussion, you're welcome to join GCC's regular community calls._",
}
APPLY_BUTTON_LABEL = {
    "zh-TW": "🚀 開始申請資助",
    "zh-CN": "🚀 开始申请资助",
    "en": "🚀 Apply for Funding",
}
AI_ERROR = {
    "zh-TW": "⚠️ 暫時無法回應，請稍後再試。",
    "zh-CN": "⚠️ 暂时无法回应，请稍后再试。",
    "en": "⚠️ Unable to respond right now. Please try again later.",
}


def append_reminder(text: str, lang: str) -> str:
    if "例會" in text or "例会" in text or "community calls" in text:
        return text
    return text + MEETING_REMINDER.get(lang, MEETING_REMINDER["zh-TW"])


def make_apply_markup(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            APPLY_BUTTON_LABEL.get(lang, APPLY_BUTTON_LABEL["zh-TW"]),
            callback_data="intent_apply",
        )
    ]])
