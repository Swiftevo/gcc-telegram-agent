"""
handlers/general.py — 一般問答處理
流程：連結優先檢查 → （如需要）呼叫 AI API → 附加例會提醒 + 申請按鈕 → 儲存記錄

按鈕設計：
  - 連結回覆：問及申請相關內容時附帶「開始申請」按鈕
  - AI 回覆：問及資助相關內容時附帶「開始申請」按鈕
  - 其他問答：只有例會提醒，無按鈕
"""

import logging
import os
from typing import Optional

from openai import AsyncOpenAI
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from core.prompt import build_messages, check_link_first, FUNDING_KEYWORDS
from core.session import get_session, save_exchange
from handlers.guard import GuardResult

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
AI_MODEL       = os.getenv("AI_MODEL", "gpt-4o-mini")
MAX_TOKENS     = int(os.getenv("AI_MAX_TOKENS", "800"))

_openai_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
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
    reminder = MEETING_REMINDER.get(lang, MEETING_REMINDER["zh-TW"])
    if "例會" in text or "例会" in text or "community calls" in text:
        return text
    return text + reminder


# ── 申請按鈕 ──────────────────────────────────────────────────────────────────

APPLY_BUTTON_LABEL = {
    "zh-TW": "🚀 開始申請資助",
    "zh-CN": "🚀 开始申请资助",
    "en":    "🚀 Apply for Funding",
}


def make_apply_markup(lang: str) -> InlineKeyboardMarkup:
    """生成「開始申請資助」Inline Keyboard"""
    label = APPLY_BUTTON_LABEL.get(lang, APPLY_BUTTON_LABEL["zh-TW"])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="intent_apply")]
    ])


def _is_funding_related(text: str) -> bool:
    """
    判斷用戶的問題是否與資助申請相關。
    只有在相關時才顯示「開始申請」按鈕。
    使用 prompt.py 已定義的 FUNDING_KEYWORDS，不重複維護。
    """
    text_lower = text.lower()
    return any(kw in text_lower for kw in FUNDING_KEYWORDS)


# ── AI 呼叫 ───────────────────────────────────────────────────────────────────

async def call_ai(messages: list[dict], lang: str) -> tuple[str, int]:
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
        text   = response.choices[0].message.content or ""
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
    1. 連結優先檢查
    2. 若需要 AI → 三層 Prompt → OpenAI
    3. 附加例會提醒
    4. 判斷是否附帶「開始申請」按鈕（只在問及資助相關時出現）
    5. 回覆 + 儲存
    """
    user_text = (update.message.text or "").strip()
    lang      = guard.lang
    user_id   = guard.user.user_id

    session = await get_session(guard)

    # 判斷是否需要顯示申請按鈕
    show_apply_button = _is_funding_related(user_text)
    reply_markup      = make_apply_markup(lang) if show_apply_button else None

    # ── 步驟 1：連結優先 ──────────────────────────────────
    link_result = check_link_first(user_text, lang)

    if link_result.matched:
        await update.message.reply_text(
            link_result.reply,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
        await save_exchange(
            session=session,
            user_id=user_id,
            user_text=user_text,
            assistant_text=link_result.reply,
            tokens_used=0,
            link_served=True,
        )
        logger.info(f"LINK_SERVED: {link_result.link_type} user_id={user_id} apply_btn={show_apply_button}")
        return

    # ── 步驟 2：AI 回覆 ───────────────────────────────────
    messages = build_messages(user_text=user_text, session=session, lang=lang)
    ai_reply, tokens_used = await call_ai(messages, lang)

    final_reply = append_reminder(ai_reply, lang)
    if len(final_reply) > 4000:
        final_reply = final_reply[:4000] + "…"

    await update.message.reply_text(
        final_reply,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )
    await save_exchange(
        session=session,
        user_id=user_id,
        user_text=user_text,
        assistant_text=final_reply,
        tokens_used=tokens_used,
        link_served=False,
    )
    logger.info(f"AI_REPLY: {tokens_used} tokens user_id={user_id} apply_btn={show_apply_button}")