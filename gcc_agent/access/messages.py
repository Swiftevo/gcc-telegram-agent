"""User-facing access messages."""

WELCOME = {
    "zh-TW": (
        "👋 你好！我是 *GCC AI 助手*。\n\n"
        "我可以幫你了解 GCC 的資助方向、已資助項目，以及如何申請資助。\n\n"
        "🔗 官方網站：https://www.gccofficial.org\n\n"
        "目前問答與申請只開放給已驗證郵箱的 GCC 人類成員。"
        "普通用戶與一般 Agent 僅會收到這則說明。\n\n"
        "驗證郵箱：`/email 你的郵箱`，收到郵件後使用 `/verify 驗證碼`。"
    ),
    "zh-CN": (
        "👋 你好！我是 *GCC AI 助手*。\n\n"
        "我可以帮你了解 GCC 的资助方向、已资助项目，以及如何申请资助。\n\n"
        "🔗 官方网站：https://www.gccofficial.org\n\n"
        "目前问答与申请只开放给已验证邮箱的 GCC 人类成员。"
        "普通用户与一般 Agent 只会收到这则说明。\n\n"
        "验证邮箱：`/email 你的邮箱`，收到邮件后使用 `/verify 验证码`。"
    ),
    "en": (
        "👋 Hello! I'm the *GCC AI Assistant*.\n\n"
        "I can help with GCC funding, funded projects, and applications.\n\n"
        "🔗 Website: https://www.gccofficial.org\n\n"
        "Q&A and applications require GCC-member access. Human members must have "
        "a verified email. Regular users and agents receive this welcome note only.\n\n"
        "Verify email with `/email you@example.com`, then `/verify code`."
    ),
}

NEED_VERIFICATION = {
    "zh-TW": "你的 GCC 成員身份需要已驗證郵箱。請先使用 `/email 你的郵箱`。",
    "zh-CN": "你的 GCC 成员身份需要已验证邮箱。请先使用 `/email 你的邮箱`。",
    "en": "Your GCC-member access requires a verified email. Use `/email you@example.com`.",
}


def translated(lang: str, choices: dict[str, str]) -> str:
    return choices.get(lang, choices.get("zh-TW", ""))


def welcome_text(lang: str) -> str:
    return translated(lang, WELCOME)
