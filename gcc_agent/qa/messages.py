"""QA response messages and Telegram markup."""

COMMUNITY_INVITE_URL = "https://t.me/+VPm1urIRC0s4NzJl"
COMMUNITY_INVITE_FOOTER = {
    "zh-TW": f"\n\n如希望深入交流，歡迎加入 GCC Telegram group\n{COMMUNITY_INVITE_URL}",
    "zh-CN": f"\n\n如希望深入交流，欢迎加入 GCC Telegram group\n{COMMUNITY_INVITE_URL}",
    "en": f"\n\nFor deeper discussion, join the GCC Telegram group\n{COMMUNITY_INVITE_URL}",
}
# Compatibility for existing imports; new replies use the shared invite footer.
MEETING_REMINDER = COMMUNITY_INVITE_FOOTER
AI_ERROR = {
    "zh-TW": "⚠️ 暫時無法回應，請稍後再試。",
    "zh-CN": "⚠️ 暂时无法回应，请稍后再试。",
    "en": "⚠️ Unable to respond right now. Please try again later.",
}


def append_reminder(text: str, lang: str) -> str:
    if COMMUNITY_INVITE_URL in text:
        return text
    return text + COMMUNITY_INVITE_FOOTER.get(lang, COMMUNITY_INVITE_FOOTER["zh-TW"])
