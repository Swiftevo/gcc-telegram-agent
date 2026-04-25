"""
core/session.py — Session 管理封裝
Guard 通過後，handlers 透過這裡取得 Session，不直接呼叫 db。
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

import db
from handlers.guard import GuardResult
from models import Session

logger = logging.getLogger(__name__)


async def get_session(guard: GuardResult) -> Session:
    """
    取得用戶的活躍 Session，不存在或已過期則建立新的。
    這是 handlers 的標準入口，不直接呼叫 db.get_or_create_session。
    """
    session, is_new = await db.get_or_create_session(guard.user.user_id)
    if is_new:
        logger.debug(f"新 Session：user_id={guard.user.user_id}")
    return session


async def save(session: Session) -> None:
    """儲存 Session 狀態"""
    await db.save_session(session)


async def save_exchange(
    session: Session,
    user_id: int,
    user_text: str,
    assistant_text: str,
    tokens_used: int = 0,
    link_served: bool = False,
) -> None:
    """
    完整儲存一問一答：
    1. 更新 session.messages（記憶體）
    2. 持久化兩條 Message 記錄到 DB
    3. 更新 session.last_active
    """
    # 更新記憶體中的對話窗口
    session.add_message("user", user_text)
    session.add_message("assistant", assistant_text)

    # 持久化到 DB
    await db.save_exchange(
        session=session,
        user_id=user_id,
        user_text=user_text,
        assistant_text=assistant_text,
        tokens_used=tokens_used,
        link_served=link_served,
    )

    # 同步更新 Session 狀態
    await db.save_session(session)
