"""
handlers/router.py — GCC Telegram Agent Intent Router
Guard 通過後，判斷這條訊息屬於哪種模式：
  - admin       → 管理員指令（只有 ADMIN_USER_ID 可執行）
  - application → Session 已在申請模式（由按鈕觸發進入，不再靠關鍵詞）
  - general     → 一般 GCC 問答

重要設計變更：
  申請流程的「進入」改由 Inline Button（callback_data="intent_apply"）觸發，
  「退出」改由 callback_data="intent_exit" 觸發。
  Router 不再做關鍵詞語義判斷，大幅減少誤觸發和 token 浪費。
"""

import logging
import os

from telegram import Update
from telegram.ext import ContextTypes

from handlers.guard import GuardResult
import db

logger = logging.getLogger(__name__)

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

# ── 管理員指令 ────────────────────────────────────────────────────────────────

ADMIN_COMMANDS = {
    "/update_values",
    "/status",
    "/block",
    "/unblock",
}


# ── Router ────────────────────────────────────────────────────────────────────

class RouteResult:
    def __init__(self, mode: str, command: str = ""):
        self.mode = mode        # "admin" | "application" | "general"
        self.command = command  # 管理員指令名稱（如 "/status"）


async def route(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    guard: GuardResult,
) -> RouteResult:
    """
    決定訊息應該交給哪個 handler 處理。
    優先順序：admin > application（session 狀態）> general

    申請流程的進入/退出完全由按鈕 callback 控制，
    這裡只檢查 Session 目前的 mode，不做語義判斷。
    """
    text = (update.message.text or "").strip()
    user_id = guard.user.user_id if guard.user else 0

    # ── 1. 管理員指令 ──────────────────────────────────────
    if user_id == ADMIN_USER_ID and text.startswith("/"):
        command = text.split()[0].lower()
        if command in ADMIN_COMMANDS:
            logger.info(f"ROUTE ADMIN: {command} from {user_id}")
            return RouteResult(mode="admin", command=command)

    # ── 2. 檢查 Session mode ───────────────────────────────
    # 申請模式完全由按鈕觸發（intent_apply / intent_exit），
    # 不再靠關鍵詞判斷。
    session, _ = await db.get_or_create_session(user_id)

    if session.mode == "application":
        logger.debug(f"ROUTE APPLICATION (session mode): user_id={user_id}")
        return RouteResult(mode="application")

    # ── 3. 預設：一般問答 ──────────────────────────────────
    logger.debug(f"ROUTE GENERAL: user_id={user_id}")
    return RouteResult(mode="general")