"""
handlers/router.py — GCC Telegram Agent Intent Router
Guard 通過後，判斷這條訊息屬於哪種模式：
  - admin    → 管理員指令（只有 ADMIN_USER_ID 可執行）
  - application → 申請資助流程（已偵測到申請意圖，或 Session 已在 application mode）
  - general  → 一般 GCC 問答
"""

import logging
import os

from telegram import Update
from telegram.ext import ContextTypes

from handlers.guard import GuardResult
import db

logger = logging.getLogger(__name__)

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

# ── 申請意圖關鍵詞 ────────────────────────────────────────────────────────────
# 出現這些詞時，把 Session 切換到 application mode

APPLICATION_KEYWORDS = {
    "zh-TW": [
        "申請", "申請資助", "申請資金", "資助", "基金", "捐助", "捐款",
        "我想申請", "如何申請", "怎麼申請", "怎樣申請",
    ],
    "zh-CN": [
        "申请", "申请资助", "申请资金", "资助", "基金", "捐助", "捐款",
        "我想申请", "如何申请", "怎么申请", "怎样申请",
    ],
    "en": [
        "apply", "application", "grant", "funding",
        "i want to apply", "how to apply", "how do i apply",
        "request funding", "request a grant",
        "apply for", "applying for",
    ],
}

# 所有語言的關鍵詞合併（一次偵測，不需要先確定語言）
ALL_APPLICATION_KEYWORDS = [
    kw for kws in APPLICATION_KEYWORDS.values() for kw in kws
]

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
    優先順序：admin > application > general
    """
    text = (update.message.text or "").strip()
    user_id = guard.user.user_id if guard.user else 0

    # ── 1. 管理員指令 ──────────────────────────────────────
    if user_id == ADMIN_USER_ID and text.startswith("/"):
        command = text.split()[0].lower()
        if command in ADMIN_COMMANDS:
            logger.info(f"ROUTE ADMIN: {command} from {user_id}")
            return RouteResult(mode="admin", command=command)

    # ── 2. 載入 Session，確認目前 mode ─────────────────────
    session, _ = await db.get_or_create_session(user_id)

    # 如果 Session 已在 application mode，繼續申請流程
    if session.mode == "application":
        # 除非用戶明確取消
        if _is_cancel(text):
            session.mode = "general"
            session.application_draft.__init__()  # 重置草稿
            await db.save_session(session)
            logger.info(f"ROUTE CANCEL APPLICATION: user_id={user_id}")
            return RouteResult(mode="general")
        logger.debug(f"ROUTE APPLICATION (existing session): user_id={user_id}")
        return RouteResult(mode="application")

    # ── 3. 偵測申請意圖 ────────────────────────────────────
    if _has_application_intent(text):
        session.mode = "application"
        await db.save_session(session)
        logger.info(f"ROUTE APPLICATION (new intent): user_id={user_id}")
        return RouteResult(mode="application")

    # ── 4. 預設：一般問答 ──────────────────────────────────
    logger.debug(f"ROUTE GENERAL: user_id={user_id}")
    return RouteResult(mode="general")


def _has_application_intent(text: str) -> bool:
    """偵測文字中是否含有申請意圖關鍵詞（不分大小寫）"""
    text_lower = text.lower()
    return any(kw in text_lower for kw in ALL_APPLICATION_KEYWORDS)


def _is_cancel(text: str) -> bool:
    """用戶是否要取消申請流程"""
    cancel_words = [
        "取消", "算了", "不申請", "不申请", "cancel", "stop", "quit", "exit",
        "/cancel", "/stop",
    ]
    text_lower = text.lower().strip()
    return any(w in text_lower for w in cancel_words)
