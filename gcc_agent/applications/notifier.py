"""Application notification composition and delivery."""

from datetime import UTC, datetime
import logging

from telegram.ext import ContextTypes

from gcc_agent.applications.models import ApplicationDraft
from gcc_agent.config import settings

logger = logging.getLogger(__name__)


async def notify_admin(
    context: ContextTypes.DEFAULT_TYPE,
    draft: ApplicationDraft,
    user,
    lang: str,
) -> bool:
    if settings.admin_notify_id == 0:
        logger.warning("ADMIN_NOTIFY_ID is not configured; notification skipped")
        return False
    fund = {
        "public": "公共基金 (Public Fund)",
        "special": "專項基金 (Special Fund)",
        "unknown": "未知",
    }.get(draft.fund_type, "未知")
    if draft.agent_score >= 70:
        score = f"🟢 {draft.agent_score}/100（建議跟進）"
    elif draft.agent_score >= 40:
        score = f"🟡 {draft.agent_score}/100（可參與例會進一步了解）"
    else:
        score = f"🔴 {draft.agent_score}/100（可能不符合方向）"
    applicant = f"@{user.username}" if user.username else f"ID: {user.user_id}"
    link = f"🔗 提案連結：{draft.proposal_link}\n" if draft.proposal_link else ""
    body = (
        "📬 *新申請通知*\n"
        f"{'─' * 30}\n"
        f"👤 申請人：{applicant}（{user.first_name}）\n"
        f"🆔 User ID：`{user.user_id}`\n🌐 語言：{lang}\n"
        f"{'─' * 30}\n📌 項目名稱：*{draft.project_name}*\n"
        f"💰 申請基金：{fund}\n{link}"
        f"📝 執行摘要：\n_{draft.executive_summary}_\n"
        f"{'─' * 30}\n🤖 *Agent 預審*\n總分：{score}\n\n"
        f"{draft.agent_notes}\n{'─' * 30}\n"
        f"📅 提交時間：{datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}"
    )
    try:
        await context.bot.send_message(
            chat_id=settings.admin_notify_id, text=body, parse_mode="Markdown"
        )
        logger.info(
            "application notification sent user_id=%s score=%s",
            user.user_id,
            draft.agent_score,
        )
        return True
    except Exception:
        logger.exception("application notification failed user_id=%s", user.user_id)
        return False
