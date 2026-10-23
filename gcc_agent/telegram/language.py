"""User-selectable Telegram response language."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

from gcc_agent.common.persistence import users

SUPPORTED_LANGUAGES = ("zh-CN", "zh-TW", "en")
LANGUAGE_LABELS = {
    "zh-CN": "简体中文",
    "zh-TW": "繁體中文",
    "en": "English",
}
LANGUAGE_ALIASES = {
    "zh-cn": "zh-CN",
    "zh-hans": "zh-CN",
    "cn": "zh-CN",
    "简体": "zh-CN",
    "简体中文": "zh-CN",
    "zh-tw": "zh-TW",
    "zh-hant": "zh-TW",
    "tw": "zh-TW",
    "繁體": "zh-TW",
    "繁體中文": "zh-TW",
    "繁体": "zh-TW",
    "繁体中文": "zh-TW",
    "en": "en",
    "english": "en",
}

LANGUAGE_PROMPTS = {
    "zh-CN": "请选择回复语言：",
    "zh-TW": "請選擇回覆語言：",
    "en": "Choose a response language:",
}
LANGUAGE_SAVED = {
    "zh-CN": "✅ 已切换为简体中文。之后的回复将使用简体中文。",
    "zh-TW": "✅ 已切換為繁體中文。之後的回覆將使用繁體中文。",
    "en": "✅ Switched to English. Future replies will use English.",
}
LANGUAGE_USAGE = {
    "zh-CN": "不支持该语言。请使用 `/language` 重新选择。",
    "zh-TW": "不支援該語言。請使用 `/language` 重新選擇。",
    "en": "That language is not supported. Use `/language` to choose again.",
}


def normalize_language(value: str) -> str | None:
    cleaned = (value or "").strip()
    if cleaned in SUPPORTED_LANGUAGES:
        return cleaned
    return LANGUAGE_ALIASES.get(cleaned.lower())


def language_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(label, callback_data=f"language:{lang}")
                for lang, label in LANGUAGE_LABELS.items()
            ]
        ]
    )


async def stored_language(update: Update, fallback: str) -> str:
    """Read an existing preference without creating a user record."""
    tg_user = update.effective_user
    user_id = getattr(tg_user, "id", None)
    if user_id is None:
        return fallback
    user = await users.get_user(user_id)
    return (getattr(user, "preferred_lang", "") if user else "") or fallback


async def ensure_user(update: Update, detected_lang: str):
    tg_user = update.effective_user
    if tg_user is None:
        return None
    user, _ = await users.get_or_create_user(
        tg_user.id,
        getattr(tg_user, "username", "") or "",
        getattr(tg_user, "first_name", "") or "",
        detected_lang,
    )
    return user

