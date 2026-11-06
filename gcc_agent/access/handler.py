"""Thin Telegram command adapters for access services."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from gcc_agent.access.email_sender import SMTPEmailSender
from gcc_agent.access.messages import EMAIL_VERIFICATION_SHELVED, translated, welcome_text
from gcc_agent.access.models import (
    ACCESS_LEVELS,
    ACCESS_REGULAR,
    ACTOR_AGENT,
    ACTOR_HUMAN,
    ACTOR_TYPES,
    USER_KIND_AI,
)
from gcc_agent.access.service import EmailVerificationService, mask_email
from gcc_agent.common.persistence import users
from gcc_agent.common.persistence import operator_actions
from gcc_agent.config import settings

logger = logging.getLogger(__name__)


def _service() -> EmailVerificationService:
    return EmailVerificationService(SMTPEmailSender(settings), settings.email_verification_secret)


def is_management_operator(user_id: int) -> bool:
    """Only the explicitly configured Telegram operator may manage identities."""
    return settings.admin_user_id > 0 and user_id == settings.admin_user_id


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


async def handle_email_shelved(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Reject legacy email commands without reading arguments or creating user data."""
    from handlers.guard import detect_language

    del context
    if update.message is None:
        return
    await update.message.reply_text(
        translated(detect_language(update), EMAIL_VERIFICATION_SHELVED)
    )


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
        await update.message.reply_text("✅ Email verified.")
        return
    text = {
        "not_requested": "No active verification request.",
        "expired": "Verification code expired. Request a new one with /email.",
        "invalid_code": "Invalid verification code.",
        "taken": "That email is already in use.",
    }.get(error, "Verification failed.")
    await update.message.reply_text(text)


async def handle_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from handlers.guard import detect_language, verify_group_membership

    if update.message is None:
        return
    lang = detect_language(update)
    user = await _current_user(update, lang)
    if user is None:
        return
    if user.is_blocked:
        qa_allowed = False
    elif user.actor_type == ACTOR_HUMAN:
        qa_allowed = await verify_group_membership(user.user_id, lang, context)
    else:
        qa_allowed = user.can_use_qa()
    await update.message.reply_text(
        f"user_id: {user.user_id}\nactor_type: {user.actor_type}\n"
        f"access_level: {user.access_level}\n"
        f"qa: {'yes' if qa_allowed else 'no'}"
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
    if update.message is None or update.effective_user is None:
        return
    actor_id = update.effective_user.id
    if not is_management_operator(actor_id):
        logger.warning("grant denied actor=%s", actor_id)
        await update.message.reply_text("Only the designated GCC operator may change identity.")
        return
    args = context.args or []
    identity = _parse_identity(args)
    if not identity:
        await operator_actions.record_invalid_request(actor_id, "grant")
        await update.message.reply_text(
            "Usage: `/grant <user_id|@username> regular|gcc_member|ai` or "
            "`/grant <user_id|@username> human|agent regular|gcc_member`",
            parse_mode="Markdown",
        )
        return
    target_id = await _resolve_target_id(args[0])
    if target_id is None:
        await operator_actions.record_invalid_request(actor_id, "grant")
        await update.message.reply_text("User not found.")
        return
    error = await operator_actions.change_identity(actor_id, target_id, *identity)
    errors = {
        "verified_email_required": "New human GCC-member onboarding is currently paused.",
        "agent_credential_required": "GCC-member agents require an agent credential.",
    }
    if error:
        await update.message.reply_text(errors.get(error, "Identity update failed."))
        return
    logger.info(
        "identity granted actor=%s target=%s actor_type=%s access_level=%s",
        actor_id, target_id, identity[0], identity[1],
    )
    await update.message.reply_text(
        f"✅ {target_id}: {identity[0]} / {identity[1]}"
    )


async def handle_block(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_block_change(update, context, True)


async def handle_unblock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _handle_block_change(update, context, False)


async def _handle_block_change(update: Update, context: ContextTypes.DEFAULT_TYPE,
                               blocked: bool) -> None:
    if update.message is None or update.effective_user is None:
        return
    actor_id = update.effective_user.id
    action = "block" if blocked else "unblock"
    if not is_management_operator(actor_id):
        logger.warning("%s denied actor=%s", action, actor_id)
        await update.message.reply_text("Only the designated GCC operator may change access.")
        return
    args = context.args or []
    if len(args) != 1:
        await operator_actions.record_invalid_request(actor_id, action)
        await update.message.reply_text(f"Usage: /{action} <user_id|@username>")
        return
    target_id = await _resolve_target_id(args[0])
    if target_id is None:
        await operator_actions.record_invalid_request(actor_id, action)
        await update.message.reply_text("User not found.")
        return
    error = await operator_actions.change_block(actor_id, target_id, blocked)
    if error:
        await update.message.reply_text("User not found.")
        return
    logger.info("access change actor=%s target=%s action=%s", actor_id, target_id, action)
    await update.message.reply_text(f"✅ {target_id}: {'blocked' if blocked else 'unblocked'}")


async def _resolve_target_id(token: str) -> int | None:
    value = (token or "").strip()
    if value.isdigit() and int(value) > 0:
        return int(value)
    target = await users.get_user_by_username(value)
    return target.user_id if target else None


async def send_limited_welcome(update: Update, user, lang: str) -> None:
    if update.message is None:
        return
    await update.message.reply_text(welcome_text(lang), parse_mode="Markdown")


async def maybe_promote_group_member_after_email(user_id, context):
    """Compatibility helper; promotion now occurs only after verification."""
    return await users.get_user(user_id)
