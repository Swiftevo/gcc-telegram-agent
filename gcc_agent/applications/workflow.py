"""Four-step application collection workflow."""

from datetime import UTC, datetime
import logging

from telegram import Update
from telegram.ext import ContextTypes

from gcc_agent.applications.markup import make_completion_markup, make_exit_markup
from gcc_agent.applications.messages import text
from gcc_agent.applications.notifier import notify_admin
from gcc_agent.applications.screening import pre_screen
from gcc_agent.common.session import get_session, save, save_exchange

logger = logging.getLogger(__name__)


async def handle_application(
    update: Update, context: ContextTypes.DEFAULT_TYPE, guard
) -> None:
    if update.message is None:
        return
    user_text = (update.message.text or "").strip()
    lang, user = guard.lang, guard.user
    session = await get_session(guard)
    draft = session.application_draft

    if draft.collection_step == 1:
        draft.project_name = user_text
        draft.collection_step = 2
        reply = text(lang, "ask_fund_type", name=user_text)
        await update.message.reply_text(
            reply, parse_mode="Markdown", reply_markup=make_exit_markup(lang)
        )
        await save_exchange(session, user.user_id, user_text, reply)
        await save(session)
        return

    if draft.collection_step == 2:
        fund_type = draft.parse_fund_type(user_text)
        if fund_type == "unknown":
            reply = text(lang, "unknown_fund_type")
            await update.message.reply_text(
                reply, parse_mode="Markdown", reply_markup=make_exit_markup(lang)
            )
            await save_exchange(session, user.user_id, user_text, reply)
            return
        draft.fund_type = fund_type
        draft.collection_step = 3
        reply = text(lang, "ask_proposal_link", fund=fund_type)
        await update.message.reply_text(
            reply, parse_mode="Markdown", reply_markup=make_exit_markup(lang)
        )
        await save_exchange(session, user.user_id, user_text, reply)
        await save(session)
        return

    if draft.collection_step == 3:
        skip = any(
            word in user_text.lower()
            for word in ("跳過", "跳过", "skip", "沒有", "没有", "no", "none")
        )
        if not skip:
            draft.proposal_link = user_text
        draft.collection_step = 4
        reply = text(lang, "ask_executive_summary")
        await update.message.reply_text(
            reply, parse_mode="Markdown", reply_markup=make_exit_markup(lang)
        )
        await save_exchange(session, user.user_id, user_text, reply)
        await save(session)
        return

    if draft.collection_step != 4:
        return
    words, characters = len(user_text.split()), len(user_text)
    if characters > 1200 or words > 500:
        reply = text(
            lang, "summary_too_long", count=characters if characters > 1200 else words
        )
        await update.message.reply_text(
            reply, parse_mode="Markdown", reply_markup=make_exit_markup(lang)
        )
        await save_exchange(session, user.user_id, user_text, reply)
        return

    draft.executive_summary = user_text
    draft.agent_score, draft.agent_notes = pre_screen(draft)
    draft.submitted_at = datetime.now(UTC).isoformat()
    await notify_admin(context, draft, user, lang)
    reply = text(lang, "submitted")
    await update.message.reply_text(
        reply, parse_mode="Markdown", reply_markup=make_completion_markup(lang)
    )
    await save_exchange(session, user.user_id, user_text, reply)
    session.mode = "general"
    await save(session)
    logger.info(
        "application completed user_id=%s score=%s has_link=%s",
        user.user_id,
        draft.agent_score,
        bool(draft.proposal_link),
    )
