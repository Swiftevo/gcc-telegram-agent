"""
handlers/admin.py — 管理員指令
只有 ADMIN_USER_ID 可以執行。
目前支援：/update_values, /status
"""

import logging
import os

from telegram import Update
from telegram.ext import ContextTypes

from core.values import reload_values
from db import get_stats
from handlers.guard import GuardResult

logger = logging.getLogger(__name__)

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))


async def handle_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    guard: GuardResult,
    command: str,
) -> None:
    """
    分發管理員指令。
    雙重驗證：Router 已過濾一次，這裡再驗證一次。
    防止 Router 邏輯失效時一般用戶能執行管理員指令。
    """
    # 二次驗證：不信任 Router，自己再確認一次
    actual_user_id = update.effective_user.id if update.effective_user else 0
    if actual_user_id != ADMIN_USER_ID:
        logger.warning(f"ADMIN ACCESS DENIED: user_id={actual_user_id} tried command={command}")
        return  # 靜默拒絕，不給任何回覆

    if command == "/status":
        await _handle_status(update)
    elif command == "/update_values":
        await _handle_update_values(update)
    else:
        await update.message.reply_text(f"未知指令：{command}")


async def _handle_status(update: Update) -> None:
    """回覆 Bot 目前狀態統計"""
    from core.values import load_values
    values = load_values()
    stats = await get_stats()

    text = (
        f"📊 *GCC Bot 狀態*\n"
        f"{'─' * 28}\n"
        f"🧠 Values 版本：`v{values.version}`\n"
        f"{'─' * 28}\n"
        f"*今日統計*\n"
        f"👤 活躍用戶：{stats['active_today']}\n"
        f"💬 訊息總數：{stats['messages_today']}\n"
        f"🤖 AI 呼叫：{stats['ai_calls_today']}\n"
        f"🔗 連結回覆：{stats['messages_today'] - stats['ai_calls_today']}\n"
        f"🪙 Token 消耗：{stats['tokens_today']}\n"
        f"📋 新申請：{stats['applications_today']}\n"
        f"{'─' * 28}\n"
        f"*累計*\n"
        f"👥 總用戶數：{stats['total_users']}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def _handle_update_values(update: Update) -> None:
    """
    重新載入 values.yaml。
    直接在伺服器上編輯 values.yaml 後，發送 /update_values 即可生效。
    """
    try:
        values = reload_values()
        await update.message.reply_text(
            f"✅ values.yaml 已重新載入\n"
            f"版本：`v{values.version}`\n"
            f"優先方向：{len(values.priority_themes)} 項\n"
            f"拒絕標準：{len(values.rejection_criteria)} 項",
            parse_mode="Markdown",
        )
        logger.info(f"values.yaml 重新載入 by admin {update.effective_user.id}")
    except Exception as e:
        await update.message.reply_text(f"❌ 載入失敗：{e}")
        logger.error(f"update_values 失敗：{e}")