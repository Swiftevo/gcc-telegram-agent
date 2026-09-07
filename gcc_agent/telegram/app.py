"""Telegram application composition root."""

import logging
import re

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from gcc_agent.access.messages import welcome_text
from gcc_agent.admin.handler import handle_admin
from gcc_agent.access.handler import (
    handle_email,
    handle_grant,
    handle_verify,
    handle_whoami,
)
from gcc_agent.applications.models import ApplicationDraft
from gcc_agent.applications.messages import text as application_text
from gcc_agent.applications.markup import make_exit_markup
from gcc_agent.applications.workflow import handle_application
from gcc_agent.common.persistence.database import init_db
from gcc_agent.common.persistence.conversations import get_or_create_session, save_session
from gcc_agent.common.persistence.users import get_user
from gcc_agent.config import settings
from gcc_agent.qa.handler import handle_general
from gcc_agent.access.guard import detect_language, run_group_qa_guard, run_guard
from gcc_agent.telegram.router import route

logger = logging.getLogger(__name__)
WEBHOOK_SECRET_PATTERN = re.compile(r"[A-Za-z0-9_-]{32,256}")


class TokenRedactionFilter(logging.Filter):
    pattern = re.compile(r"bot\d+:[A-Za-z0-9_-]+")

    def filter(self, record: logging.LogRecord) -> bool:
        # Redact the fully rendered message. HTTP clients pass URL objects in
        # ``record.args``; filtering only string arguments leaves bot tokens in logs.
        record.msg = self.pattern.sub("bot[REDACTED]", record.getMessage())
        record.args = ()
        return True


def setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO
    )
    for handler in logging.root.handlers:
        handler.addFilter(TokenRedactionFilter())


def validate_webhook_configuration(webhook_url: str, secret_token: str) -> None:
    """Require a strong Telegram-compatible secret whenever webhook mode is enabled."""
    if not webhook_url:
        return
    if not WEBHOOK_SECRET_PATTERN.fullmatch(secret_token or ""):
        raise ValueError(
            "WEBHOOK_SECRET_TOKEN must contain 32-256 characters using only "
            "letters, numbers, underscores, or hyphens when WEBHOOK_URL is configured"
        )


def message_mentions_bot(text: str, bot_username: str) -> bool:
    if not text or not bot_username:
        return False
    mention = rf"(?<!\w)@{re.escape(bot_username.lstrip('@'))}(?!\w)"
    return re.search(mention, text, flags=re.IGNORECASE) is not None


def remove_bot_mentions(text: str, bot_username: str) -> str:
    if not text or not bot_username:
        return (text or "").strip()
    mention = rf"(?<!\w)@{re.escape(bot_username.lstrip('@'))}(?!\w)"
    return re.sub(mention, "", text, flags=re.IGNORECASE).strip()


def group_question_required(lang: str) -> str:
    return {
        "zh-TW": "請在 mention 後加上你的問題。",
        "zh-CN": "请在 mention 后加上你的问题。",
        "en": "Please add your question after the mention.",
    }.get(lang, "請在 mention 後加上你的問題。")


async def get_bot_username(context) -> str:
    cached = context.bot_data.get("bot_username") if hasattr(context, "bot_data") else None
    if cached:
        return cached

    bot_user = await context.bot.get_me()
    username = getattr(bot_user, "username", "") or ""
    if hasattr(context, "bot_data"):
        context.bot_data["bot_username"] = username
    return username


async def should_handle_group_message(update: Update, context) -> bool:
    if update.message is None or update.effective_chat is None:
        return False
    if not settings.group_qa_enabled:
        logger.info("group message ignored because GROUP_QA_ENABLED is false")
        return False
    if not settings.gcc_group_id:
        logger.info("group message ignored because GCC_GROUP_ID is not configured")
        return False
    if update.effective_chat.id != settings.gcc_group_id:
        logger.info("group message ignored chat_id=%s", update.effective_chat.id)
        return False

    bot_username = await get_bot_username(context)
    return message_mentions_bot(update.message.text or "", bot_username)


async def handle_message(update: Update, context) -> None:
    if update.message is None:
        return
    guard = await run_guard(update, context)
    if not guard.passed:
        return
    result = await route(update, context, guard)
    if result.mode == "admin":
        await handle_admin(update, context, guard, result.command)
    elif result.mode == "application":
        await handle_application(update, context, guard)
    else:
        await handle_general(update, context, guard)


async def handle_group_message(update: Update, context) -> None:
    if not await should_handle_group_message(update, context):
        return
    guard = await run_group_qa_guard(update, context)
    if not guard.passed:
        return

    bot_username = await get_bot_username(context)
    user_text = remove_bot_mentions(update.message.text or "", bot_username)
    if not user_text:
        await update.message.reply_text(group_question_required(guard.lang))
        return
    if user_text.startswith("/"):
        logger.info("group command ignored user_id=%s", guard.user.user_id)
        return

    raw_thread_id = getattr(update.message, "message_thread_id", 0)
    thread_id = raw_thread_id if isinstance(raw_thread_id, int) else 0
    await handle_general(
        update,
        context,
        guard,
        user_text_override=user_text,
        scope_type="group",
        scope_id=update.effective_chat.id,
        thread_id=thread_id,
        allow_application=False,
    )


async def handle_callback(update: Update, context) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
    if update.effective_chat is None or update.effective_chat.type != "private":
        logger.info("non-private callback ignored")
        return
    user = await get_user(query.from_user.id)
    if user is None or user.is_blocked or not user.can_use_qa():
        return
    session, _ = await get_or_create_session(user.user_id)
    lang = detect_language(update)
    if query.data == "intent_apply":
        session.mode = "application"
        session.application_draft = ApplicationDraft(collection_step=1)
        await save_session(session)
        await query.message.reply_text(
            application_text(lang, "intro"),
            parse_mode="Markdown",
            reply_markup=make_exit_markup(lang),
        )
    elif query.data == "intent_exit":
        session.mode = "general"
        session.application_draft = ApplicationDraft()
        await save_session(session)
        await query.message.reply_text("✅ Application flow exited.")


async def handle_start(update: Update, context) -> None:
    if update.message:
        await update.message.reply_text(
            welcome_text(detect_language(update)), parse_mode="Markdown"
        )


async def post_init(application: Application) -> None:
    await init_db()
    logger.info("bot started username=%s", (await application.bot.get_me()).username)


def build_application() -> Application:
    if not settings.bot_token:
        raise ValueError("BOT_TOKEN is not configured")
    app = Application.builder().token(settings.bot_token).post_init(post_init).build()
    private = filters.ChatType.PRIVATE
    app.add_handler(CommandHandler("start", handle_start, filters=private))
    app.add_handler(CommandHandler("email", handle_email, filters=private))
    app.add_handler(CommandHandler("verify", handle_verify, filters=private))
    app.add_handler(CommandHandler("grant", handle_grant, filters=private))
    app.add_handler(CommandHandler("whoami", handle_whoami, filters=private))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_message))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_group_message))
    return app


def run() -> None:
    setup_logging()
    validate_webhook_configuration(
        settings.webhook_url,
        settings.webhook_secret_token,
    )
    app = build_application()
    if settings.webhook_url:
        logger.info(
            "webhook mode enabled listen=%s port=%s",
            settings.webhook_listen,
            settings.port,
        )
        app.run_webhook(
            listen=settings.webhook_listen,
            port=settings.port,
            webhook_url=settings.webhook_url,
            url_path="/webhook",
            secret_token=settings.webhook_secret_token,
        )
    else:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
