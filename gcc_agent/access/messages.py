"""User-facing access messages."""

WELCOME = {
    "zh-TW": (
        "👋 你好！我是 *GCC AI 助手*。\n\n"
        "我可以幫你了解 GCC 的資助方向、已資助項目，以及如何申請資助。\n\n"
        "🔗 官方網站：https://www.gccofficial.org\n\n"
        "指定 GCC 群組的現任成員可直接在此私訊提問，亦可在群組明確 mention Bot。"
        "郵箱驗證目前暫停。\n\n"
        "資料告知：`/privacy`"
    ),
    "zh-CN": (
        "👋 你好！我是 *GCC AI 助手*。\n\n"
        "我可以帮你了解 GCC 的资助方向、已资助项目，以及如何申请资助。\n\n"
        "🔗 官方网站：https://www.gccofficial.org\n\n"
        "指定 GCC 群组的当前成员可直接在此私聊提问，也可在群组明确 mention Bot。"
        "邮箱验证目前暂停。\n\n"
        "数据告知：`/privacy`"
    ),
    "en": (
        "👋 Hello! I'm the *GCC AI Assistant*.\n\n"
        "I can help with GCC funding, funded projects, and applications.\n\n"
        "🔗 Website: https://www.gccofficial.org\n\n"
        "Current members of the configured GCC group can ask here in private or by "
        "explicitly mentioning the Bot in that group. Email verification is paused.\n\n"
        "Data notice: `/privacy`"
    ),
}

NEED_VERIFICATION = {
    "zh-TW": "郵箱驗證目前暫停。指定 GCC 群組的現任成員可在此私訊或在群組 mention Bot 提問。",
    "zh-CN": "邮箱验证目前暂停。指定 GCC 群组的当前成员可在此私聊或在群组 mention Bot 提问。",
    "en": "Email verification is paused. Current members of the configured GCC group can ask here privately or mention the Bot in that group.",
}

EMAIL_VERIFICATION_SHELVED = {
    "zh-TW": "郵箱驗證目前暫停，不接受新的郵箱或驗證碼。指定 GCC 群組的現任成員可直接在此私訊提問。",
    "zh-CN": "邮箱验证目前暂停，不接受新的邮箱或验证码。指定 GCC 群组的当前成员可直接在此私聊提问。",
    "en": "Email verification is currently paused. New addresses and verification codes are not accepted. Current members of the configured GCC group can ask here privately.",
}


def translated(lang: str, choices: dict[str, str]) -> str:
    return choices.get(lang, choices.get("zh-TW", ""))


def welcome_text(lang: str) -> str:
    return translated(lang, WELCOME)
