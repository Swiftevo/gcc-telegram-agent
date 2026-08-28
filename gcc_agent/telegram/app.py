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
from gcc_agent.access.guard import detect_language, run_guard
from gcc_agent.telegram.router import route

logger = logging.getLogger(__name__)


class TokenRedactionFilter(logging.Filter):
    pattern = re.compile(r"bot\d+:[A-Za-z0-9_-]+")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self.pattern.sub("bot[REDACTED]", record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                self.pattern.sub("bot[REDACTED]", value) if isinstance(value, str) else value
                for value in record.args
            )
        return True


def setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", level=logging.INFO
    )
    for handler in logging.root.handlers:
        handler.addFilter(TokenRedactionFilter())


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


async def handle_callback(update: Update, context) -> None:
    query = update.callback_query
    if query is None:
        return
    await query.answer()
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
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("email", handle_email))
    app.add_handler(CommandHandler("verify", handle_verify))
    app.add_handler(CommandHandler("grant", handle_grant))
    app.add_handler(CommandHandler("whoami", handle_whoami))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_message))
    return app


def run() -> None:
    setup_logging()
    app = build_application()
    if settings.webhook_url:
        logger.info("webhook mode enabled")
        app.run_webhook(
            listen="127.0.0.1",
            port=settings.port,
            webhook_url=settings.webhook_url,
            url_path="/webhook",
        )
    else:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
