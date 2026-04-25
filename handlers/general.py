"""
handlers/general.py — 一般問答處理
Guard 和 Router 確認為 general mode 後進入這裡。
流程：連結優先檢查 → （如需要）呼叫 AI API → 附加例會提醒 → 儲存記錄
"""

import logging
import os
from typing import Optional

from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import ContextTypes

from core.prompt import build_messages, check_link_first
from core.session import get_session, save_exchange
from handlers.guard import GuardResult

logger = logging.getLogger(__name__)

# OpenAI 設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "800"))

_openai_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """取得 OpenAI 客戶端（單例）"""
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


# ── 例會提醒 ──────────────────────────────────────────────────────────────────

MEETING_REMINDER = {
    "zh-TW": "\n\n_如希望深入交流，歡迎參與 GCC 定期例會。_",
    "zh-CN": "\n\n_如希望深入交流，欢迎参与 GCC 定期例会。_",
    "en":    "\n\n_For deeper discussion, you're welcome to join GCC's regular community calls._",
}


def append_reminder(text: str, lang: str) -> str:
    """在回覆末尾附加例會提醒（如果尚未包含）"""
    reminder = MEETING_REMINDER.get(lang, MEETING_REMINDER["zh-TW"])
    # 避免重複附加
    if "例會" in text or "例会" in text or "community calls" in text:
        return text
    return text + reminder


# ── AI 呼叫 ───────────────────────────────────────────────────────────────────

async def call_ai(messages: list[dict], lang: str) -> tuple[str, int]:
    """
    呼叫 OpenAI API。
    返回 (response_text, tokens_used)。
    失敗時返回友好的錯誤訊息，不崩潰。
    """
    error_msg = {
        "zh-TW": "⚠️ 暫時無法回應，請稍後再試。",
        "zh-CN": "⚠️ 暂时无法回应，请稍后再试。",
        "en":    "⚠️ Unable to respond right now. Please try again later.",
    }

    try:
        client = get_openai_client()
        response = await client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0.7,
        )
        text = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0
        logger.debug(f"AI 回應：{tokens} tokens")
        return text.strip(), tokens

    except Exception as e:
        logger.error(f"OpenAI API 呼叫失敗：{e}")
        return error_msg.get(lang, error_msg["zh-TW"]), 0


# ── 主要 Handler ──────────────────────────────────────────────────────────────

async def handle_general(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    guard: GuardResult,
) -> None:
    """
    一般問答主流程：
    1. 連結優先檢查（不呼叫 AI）
    2. 若需要 AI → 組裝三層 Prompt → 呼叫 OpenAI
    3. 附加例會提醒
    4. 回覆用戶 + 儲存記錄
    """
    user_text = (update.message.text or "").strip()
    lang = guard.lang
    user_id = guard.user.user_id

    # 取得 Session
    session = await get_session(guard)

    # ── 步驟 1：連結優先檢查 ──────────────────────────────
    link_result = check_link_first(user_text, lang)

    if link_result.matched:
        # 直接回覆連結，不呼叫 AI
        reply = link_result.reply
        await update.message.reply_text(reply, parse_mode="Markdown")
        await save_exchange(
            session=session,
            user_id=user_id,
            user_text=user_text,
            assistant_text=reply,
            tokens_used=0,
            link_served=True,
        )
        logger.info(f"LINK_SERVED: {link_result.link_type} user_id={user_id}")
        return

    # ── 步驟 2：組裝 Prompt，呼叫 AI ──────────────────────
    messages = build_messages(
        user_text=user_text,
        session=session,
        lang=lang,
    )

    ai_reply, tokens_used = await call_ai(messages, lang)

    # ── 步驟 3：附加例會提醒 ──────────────────────────────
    final_reply = append_reminder(ai_reply, lang)

    # ── 步驟 4：回覆 + 儲存 ───────────────────────────────
    # Telegram 訊息上限 4096 字，安全截斷
    if len(final_reply) > 4000:
        final_reply = final_reply[:4000] + "…"

    await update.message.reply_text(final_reply, parse_mode="Markdown")
    await save_exchange(
        session=session,
        user_id=user_id,
        user_text=user_text,
        assistant_text=final_reply,
        tokens_used=tokens_used,
        link_served=False,
    )
    logger.info(f"AI_REPLY: {tokens_used} tokens user_id={user_id}")
