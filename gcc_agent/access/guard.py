"""Default-deny request guard for Telegram messages."""

from dataclasses import dataclass
import logging

from telegram import Update
from telegram.ext import ContextTypes

from gcc_agent.access.handler import send_limited_welcome
from gcc_agent.access.rules import qa_decision
from gcc_agent.common.persistence import users
from gcc_agent.config import settings

logger = logging.getLogger(__name__)
DAILY_LIMIT = 20


def detect_language(update: Update) -> str:
    code = ""
    if update.effective_user and update.effective_user.language_code:
        code = update.effective_user.language_code.lower()
    if code in ("zh-tw", "zh-hk", "zh-mo"):
        return "zh-TW"
    if code in ("zh-cn", "zh-sg", "zh"):
        return "zh-CN"
    if code.startswith("en"):
        return "en"
    return "zh-TW"


def message(lang: str, key: str) -> str:
    messages = {
        "blocked": {
            "zh-TW": "你目前無法使用此服務。如有疑問請聯絡 GCC。",
            "zh-CN": "你目前无法使用此服务。如有疑问请联系 GCC。",
            "en": "You are currently unable to use this service. Contact GCC if you have questions.",
        },
        "rate_limited": {
            "zh-TW": f"⏳ 你今天已經達到 {DAILY_LIMIT} 條對話上限。\n\n明天再來繼續交流！\n\n如希望深入交流，歡迎參與 GCC 定期例會。",
            "zh-CN": f"⏳ 你今天已达到 {DAILY_LIMIT} 条对话上限。\n\n明天再来继续交流！\n\n如希望深入交流，欢迎参与 GCC 定期例会。",
            "en": f"⏳ You've reached today's limit of {DAILY_LIMIT} messages.\n\nCome back tomorrow!\n\nFor deeper discussion, join GCC's regular community calls.",
        },
        "not_member": {
            "zh-TW": "👋 你好！\n\n你目前沒有 GCC 成員權限。\n\n🌐 https://www.gccofficial.org",
            "zh-CN": "👋 你好！\n\n你目前没有 GCC 成员权限。\n\n🌐 https://www.gccofficial.org",
            "en": "👋 Hello!\n\nYou do not currently have GCC member access.\n\n🌐 https://www.gccofficial.org",
        },
    }
    values = messages.get(key, messages["not_member"])
    return values.get(lang, values["zh-TW"])


async def verify_group_membership(
    user_id: int,
    lang: str,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """Compatibility helper used only for explicit group checks."""
    del lang
    if not settings.gcc_group_id:
        logger.warning("group membership check denied: GCC_GROUP_ID missing")
        return False
    try:
        member = await context.bot.get_chat_member(settings.gcc_group_id, user_id)
        allowed = member.status in ("member", "administrator", "creator")
        await users.update_user_group_membership(user_id, allowed)
        return allowed
    except Exception:
        logger.exception("group membership check failed user_id=%s", user_id)
        return False


@dataclass
class GuardResult:
    passed: bool
    user: object | None = None
    lang: str = "zh-TW"
    reason: str = ""


async def run_guard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> GuardResult:
    tg_user = update.effective_user
    if tg_user is None or update.message is None:
        return GuardResult(False, reason="no_user")

    lang = detect_language(update)
    user, created = await users.get_or_create_user(
        tg_user.id,
        tg_user.username or "",
        tg_user.first_name or "",
        lang,
    )
    if not created and user.detected_lang != lang:
        await users.update_user_lang(user.user_id, lang)
        user.detected_lang = lang

    access = qa_decision(user)
    if access.reason == "blocked":
        await update.message.reply_text(message(lang, "blocked"))
        return GuardResult(False, user, lang, "blocked")
    if not access.allowed:
        await send_limited_welcome(update, user, lang)
        logger.info(
            "welcome-only user_id=%s actor_type=%s access_level=%s",
            user.user_id,
            user.actor_type,
            user.access_level,
        )
        return GuardResult(False, user, lang, "welcome_only")

    if not await users.try_increment_daily_count(user.user_id, DAILY_LIMIT):
        await update.message.reply_text(message(lang, "rate_limited"))
        return GuardResult(False, user, lang, "rate_limited")
    return GuardResult(True, user, lang)
