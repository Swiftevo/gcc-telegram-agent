"""Telegram adapters for administrator-only operations."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from gcc_agent.common.persistence.stats import get_stats
from gcc_agent.config import settings
from gcc_agent.knowledge.loaders import load_values, reload_values

logger = logging.getLogger(__name__)


async def handle_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    guard,
    command: str,
) -> None:
    del context, guard
    actual_user_id = update.effective_user.id if update.effective_user else 0
    if not settings.admin_user_id or actual_user_id != settings.admin_user_id:
        logger.warning(
            "admin access denied user_id=%s command=%s",
            actual_user_id,
            command,
        )
        return
    if command == "/status":
        await handle_status(update)
    elif command == "/update_values":
        await handle_update_values(update)
    elif update.message:
        await update.message.reply_text(f"未知指令：{command}")


async def handle_status(update: Update) -> None:
    if update.message is None:
        return
    values = load_values()
    stats = await get_stats()
    text = (
        "📊 *GCC Bot 狀態*\n"
        f"{'─' * 28}\n"
        f"🧠 Values 版本：`v{values.version}`\n"
        f"{'─' * 28}\n"
        "*今日統計*\n"
        f"👤 活躍用戶：{stats['active_today']}\n"
        f"💬 訊息總數：{stats['messages_today']}\n"
        f"🤖 AI 呼叫：{stats['ai_calls_today']}\n"
        f"🔗 連結回覆：{stats['messages_today'] - stats['ai_calls_today']}\n"
        f"🪙 Token 消耗：{stats['tokens_today']}\n"
        f"📋 新申請：{stats['applications_today']}\n"
        f"{'─' * 28}\n"
        "*累計*\n"
        f"👥 總用戶數：{stats['total_users']}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_update_values(update: Update) -> None:
    if update.message is None:
        return
    try:
        values = reload_values()
        await update.message.reply_text(
            "✅ values.yaml 已重新載入\n"
            f"版本：`v{values.version}`\n"
            f"優先方向：{len(values.priority_themes)} 項\n"
            f"拒絕標準：{len(values.rejection_criteria)} 項",
            parse_mode="Markdown",
        )
        user_id = update.effective_user.id if update.effective_user else 0
        logger.info("values reloaded user_id=%s", user_id)
    except Exception:
        logger.exception("values reload failed")
        await update.message.reply_text("❌ 載入失敗")
