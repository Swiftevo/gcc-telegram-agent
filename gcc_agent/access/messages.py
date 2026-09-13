"""User-facing access messages."""

WELCOME = {
    "zh-TW": (
        "👋 你好！我是 *GCC AI 助手*。\n\n"
        "我可以幫你了解 GCC 的資助方向、已資助項目，以及如何申請資助。\n\n"
        "🔗 官方網站：https://www.gccofficial.org\n\n"
        "私訊成員啟用目前暫停。你仍可在指定 GCC 群組明確 mention Bot 提問。\n\n"
        "資料告知：`/privacy`"
    ),
    "zh-CN": (
        "👋 你好！我是 *GCC AI 助手*。\n\n"
        "我可以帮你了解 GCC 的资助方向、已资助项目，以及如何申请资助。\n\n"
        "🔗 官方网站：https://www.gccofficial.org\n\n"
        "私聊成员启用目前暂停。你仍可在指定 GCC 群组明确 mention Bot 提问。\n\n"
        "数据告知：`/privacy`"
    ),
    "en": (
        "👋 Hello! I'm the *GCC AI Assistant*.\n\n"
        "I can help with GCC funding, funded projects, and applications.\n\n"
        "🔗 Website: https://www.gccofficial.org\n\n"
        "Private member onboarding is currently paused. You can still ask questions "
        "by explicitly mentioning the Bot in the configured GCC group.\n\n"
        "Data notice: `/privacy`"
    ),
}

NEED_VERIFICATION = {
    "zh-TW": "私訊成員啟用目前暫停。請在指定 GCC 群組明確 mention Bot 提問。",
    "zh-CN": "私聊成员启用目前暂停。请在指定 GCC 群组明确 mention Bot 提问。",
    "en": "Private member onboarding is paused. Mention the Bot in the configured GCC group instead.",
}

EMAIL_VERIFICATION_SHELVED = {
    "zh-TW": "郵箱驗證目前暫停，不接受新的郵箱或驗證碼。你仍可在指定 GCC 群組明確 mention Bot 提問。",
    "zh-CN": "邮箱验证目前暂停，不接受新的邮箱或验证码。你仍可在指定 GCC 群组明确 mention Bot 提问。",
    "en": "Email verification is currently paused. New addresses and verification codes are not accepted. You can still mention the Bot in the configured GCC group.",
}


def translated(lang: str, choices: dict[str, str]) -> str:
    return choices.get(lang, choices.get("zh-TW", ""))


def welcome_text(lang: str) -> str:
    return translated(lang, WELCOME)
