"""Thin Telegram command adapters for access services."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from gcc_agent.access.email_sender import SMTPEmailSender
from gcc_agent.access.messages import NEED_VERIFICATION, translated, welcome_text
from gcc_agent.access.models import (
    ACCESS_GCC_MEMBER,
    ACCESS_LEVELS,
    ACCESS_REGULAR,
    ACTOR_AGENT,
    ACTOR_HUMAN,
    ACTOR_TYPES,
    USER_KIND_AI,
)
from gcc_agent.access.service import EmailVerificationService, mask_email
from gcc_agent.common.persistence import users
from gcc_agent.config import settings

logger = logging.getLogger(__name__)
GROUP_GRANT_STATUSES = ("member", "administrator", "creator")


def _service() -> EmailVerificationService:
    return EmailVerificationService(SMTPEmailSender(settings), settings.email_verification_secret)


async def is_group_grantor(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if settings.admin_user_id and user_id == settings.admin_user_id:
        return True
    if not settings.gcc_group_id:
        logger.warning("grant denied because GCC_GROUP_ID is not configured")
        return False
    try:
        member = await context.bot.get_chat_member(settings.gcc_group_id, user_id)
        allowed = member.status in GROUP_GRANT_STATUSES
        await users.update_user_group_membership(user_id, allowed)
        return allowed
    except Exception:
        logger.exception("grant membership check failed user_id=%s", user_id)
        return False


async def _current_user(update: Update, lang: str):
    tg = update.effective_user
    if tg is None:
        return None
    user, _ = await users.get_or_create_user(
        tg.id, tg.username or "", tg.first_name or "", lang
    )
    return user


async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from handlers.guard import detect_language

    if update.message is None:
        return
    lang = detect_language(update)
    user = await _current_user(update, lang)
    if user is None:
        return
    args = context.args or []
    if not args:
        status = "verified" if user.email_verified_at else "unverified"
        await update.message.reply_text(
            f"email: `{mask_email(user.email) or '—'}`\nstatus: `{status}`\n"
            "Request verification: `/email you@example.com`",
            parse_mode="Markdown",
        )
        return
    error = await _service().request(user.user_id, args[0])
    messages = {
        "": {
            "zh-TW": "驗證碼已發送。請在 10 分鐘內使用 `/verify 六位驗證碼`。",
            "zh-CN": "验证码已发送。请在 10 分钟内使用 `/verify 六位验证码`。",
            "en": "Verification code sent. Use `/verify six-digit-code` within 10 minutes.",
        },
        "invalid": {"zh-TW": "郵箱格式不正確。", "zh-CN": "邮箱格式不正确。", "en": "Invalid email."},
        "taken": {"zh-TW": "這個郵箱已被使用。", "zh-CN": "这个邮箱已被使用。", "en": "Email already in use."},
        "delivery_unavailable": {
            "zh-TW": "郵箱驗證寄送目前不可用，請聯絡管理員。",
            "zh-CN": "邮箱验证发送目前不可用，请联系管理员。",
            "en": "Email verification delivery is unavailable. Contact an administrator.",
        },
        "delivery_failed": {
            "zh-TW": "驗證郵件寄送失敗，請稍後再試。",
            "zh-CN": "验证邮件发送失败，请稍后再试。",
            "en": "Verification delivery failed. Try again later.",
        },
    }
    await update.message.reply_text(translated(lang, messages.get(error, messages["delivery_failed"])), parse_mode="Markdown")


async def handle_verify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from handlers.guard import detect_language

    if update.message is None:
        return
    lang = detect_language(update)
    user = await _current_user(update, lang)
    if user is None:
        return
    args = context.args or []
    error = await _service().confirm(user.user_id, args[0] if args else "")
    if not error:
        promoted = False
        if user.actor_type == ACTOR_HUMAN and await is_group_grantor(user.user_id, context):
            promoted = not await users.set_identity(user.user_id, ACTOR_HUMAN, ACCESS_GCC_MEMBER)
        text = "✅ Email verified."
        if promoted:
            text += " GCC-member access granted."
        await update.message.reply_text(text)
        return
    text = {
        "not_requested": "No active verification request.",
        "expired": "Verification code expired. Request a new one with /email.",
        "invalid_code": "Invalid verification code.",
        "taken": "That email is already in use.",
    }.get(error, "Verification failed.")
    await update.message.reply_text(text)


async def handle_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from handlers.guard import detect_language

    if update.message is None:
        return
    user = await _current_user(update, detect_language(update))
    if user is None:
        return
    await update.message.reply_text(
        f"user_id: `{user.user_id}`\nactor_type: `{user.actor_type}`\n"
        f"access_level: `{user.access_level}`\nemail: `{mask_email(user.email) or '—'}`\n"
        f"email_verified: `{'yes' if user.email_verified_at else 'no'}`\n"
        f"qa: `{'yes' if user.can_use_qa() else 'no'}`",
        parse_mode="Markdown",
    )


def _parse_identity(args: list[str]):
    if len(args) < 2:
        return None
    value = args[1].lower()
    if value == USER_KIND_AI:
        return ACTOR_AGENT, ACCESS_REGULAR
    if value in ACCESS_LEVELS:
        return ACTOR_HUMAN, value
    if len(args) >= 3 and value in ACTOR_TYPES and args[2].lower() in ACCESS_LEVELS:
        return value, args[2].lower()
    return None


async def handle_grant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from handlers.guard import detect_language

    if update.message is None or update.effective_user is None:
        return
    lang = detect_language(update)
    await _current_user(update, lang)
    if not await is_group_grantor(update.effective_user.id, context):
        await update.message.reply_text("Only GCC group members may grant identity.")
        return
    args = context.args or []
    identity = _parse_identity(args)
    if not identity:
        await update.message.reply_text(
            "Usage: `/grant <user_id|@username> regular|gcc_member|ai` or "
            "`/grant <user_id|@username> human|agent regular|gcc_member`",
            parse_mode="Markdown",
        )
        return
    target = await _resolve_target(args[0])
    if target is None:
        await update.message.reply_text("User not found.")
        return
    error = await users.set_identity(target.user_id, *identity)
    errors = {
        "verified_email_required": "Human GCC members require a verified email.",
        "agent_credential_required": "GCC-member agents require an agent credential.",
    }
    if error:
        await update.message.reply_text(errors.get(error, "Identity update failed."))
        return
    logger.info(
        "identity granted actor=%s target=%s actor_type=%s access_level=%s",
        update.effective_user.id, target.user_id, identity[0], identity[1],
    )
    await update.message.reply_text(
        f"✅ `{target.user_id}`: `{identity[0]}` / `{identity[1]}`", parse_mode="Markdown"
    )


async def _resolve_target(token: str):
    value = (token or "").strip()
    if value.lstrip("-").isdigit():
        user, _ = await users.get_or_create_user(int(value))
        return user
    return await users.get_user_by_username(value)


async def send_limited_welcome(update: Update, user, lang: str) -> None:
    if update.message is None:
        return
    if (
        user.actor_type == ACTOR_HUMAN
        and user.access_level == ACCESS_GCC_MEMBER
        and not user.email_verified_at
    ):
        text = translated(lang, NEED_VERIFICATION)
    else:
        text = welcome_text(lang)
    await update.message.reply_text(text, parse_mode="Markdown")


async def maybe_promote_group_member_after_email(user_id, context):
    """Compatibility helper; promotion now occurs only after verification."""
    return await users.get_user(user_id)
