"""Thin Telegram adapter for GCC question answering."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from gcc_agent.common.session import get_session, save_exchange
from gcc_agent.qa.messages import append_reminder, make_apply_markup
from gcc_agent.qa.prompts import FUNDING_KEYWORDS, build_messages, check_link_first
from gcc_agent.qa.service import call_ai

logger = logging.getLogger(__name__)


def is_funding_related(text: str) -> bool:
    value = text.lower()
    return any(keyword in value for keyword in FUNDING_KEYWORDS)


async def handle_general(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    guard,
) -> None:
    """Answer from a deterministic link or the configured language model."""
    if update.message is None:
        return

    user_text = (update.message.text or "").strip()
    lang = guard.lang
    user_id = guard.user.user_id
    session = await get_session(guard)
    reply_markup = make_apply_markup(lang) if is_funding_related(user_text) else None

    link_result = check_link_first(user_text, lang)
    if link_result.matched:
        await update.message.reply_text(
            link_result.reply,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
        await save_exchange(
            session,
            user_id,
            user_text,
            link_result.reply,
            tokens_used=0,
            link_served=True,
        )
        logger.info(
            "link served type=%s user_id=%s",
            link_result.link_type,
            user_id,
        )
        return

    ai_reply, tokens_used = await call_ai(
        build_messages(user_text=user_text, session=session, lang=lang),
        lang,
    )
    final_reply = append_reminder(ai_reply, lang)
    if len(final_reply) > 4000:
        final_reply = final_reply[:4000] + "…"

    await update.message.reply_text(
        final_reply,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )
    await save_exchange(
        session,
        user_id,
        user_text,
        final_reply,
        tokens_used=tokens_used,
        link_served=False,
    )
    logger.info("AI reply tokens=%s user_id=%s", tokens_used, user_id)
