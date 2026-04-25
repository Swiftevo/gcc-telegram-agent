"""
handlers/guard.py — GCC Telegram Agent Guard Layer
第一道防線，每條訊息都必須通過這裡。
三個關卡依序執行：封鎖檢查 → 群組驗證 → Rate Limit
"""

import logging
import os
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

import db

logger = logging.getLogger(__name__)

# 從環境變數讀取 GCC 群組 ID（負數）
GCC_GROUP_ID = int(os.getenv("GCC_GROUP_ID", "0"))

# 群組邀請連結（可選，沒設定就只說明需要加入）
GCC_GROUP_INVITE = os.getenv("GCC_GROUP_INVITE", "")

DAILY_LIMIT = 20


# ── 語言偵測 ──────────────────────────────────────────────────────────────────

def detect_language(update: Update) -> str:
    """
    從 Telegram 用戶的 language_code 偵測語言。
    返回 "zh-TW" | "zh-CN" | "en"
    優先使用 Telegram 提供的 language_code，
    若無法識別則預設繁體中文（GCC 主要社區）。
    """
    lang_code = ""
    if update.effective_user and update.effective_user.language_code:
        lang_code = update.effective_user.language_code.lower()

    if lang_code in ("zh-tw", "zh-hk", "zh-mo"):
        return "zh-TW"
    if lang_code in ("zh-cn", "zh-sg", "zh"):
        return "zh-CN"
    if lang_code.startswith("en"):
        return "en"

    # 預設繁體中文
    return "zh-TW"


# ── 回覆文字（三語）─────────────────────────────────────────────────────────

def _msg(lang: str, key: str) -> str:
    """取得對應語言的系統訊息"""
    messages = {
        "not_member": {
            "zh-TW": (
                "👋 你好！\n\n"
                "GCC AI 助手只開放給 GCC Telegram 社區成員使用。\n\n"
                "請先加入 GCC 社區，然後再來找我：\n"
                "{invite}\n\n"
                "🌐 了解更多：https://www.gccofficial.org"
            ),
            "zh-CN": (
                "👋 你好！\n\n"
                "GCC AI 助手只对 GCC Telegram 社区成员开放。\n\n"
                "请先加入 GCC 社区，然后再来找我：\n"
                "{invite}\n\n"
                "🌐 了解更多：https://www.gccofficial.org"
            ),
            "en": (
                "👋 Hello!\n\n"
                "The GCC AI assistant is only available to GCC Telegram community members.\n\n"
                "Please join the GCC community first:\n"
                "{invite}\n\n"
                "🌐 Learn more: https://www.gccofficial.org"
            ),
        },
        "rate_limited": {
            "zh-TW": (
                "⏳ 你今天已經達到 {limit} 條對話上限。\n\n"
                "明天再來繼續交流！\n\n"
                "如希望深入交流，歡迎參與 GCC 定期例會。"
            ),
            "zh-CN": (
                "⏳ 你今天已达到 {limit} 条对话上限。\n\n"
                "明天再来继续交流！\n\n"
                "如希望深入交流，欢迎参与 GCC 定期例会。"
            ),
            "en": (
                "⏳ You've reached today's limit of {limit} messages.\n\n"
                "Come back tomorrow!\n\n"
                "For deeper discussion, you're welcome to join GCC's regular community calls."
            ),
        },
        "blocked": {
            "zh-TW": "你目前無法使用此服務。如有疑問請聯絡 GCC。",
            "zh-CN": "你目前无法使用此服务。如有疑问请联系 GCC。",
            "en":    "You are currently unable to use this service. Contact GCC if you have questions.",
        },
        "group_check_error": {
            "zh-TW": "⚠️ 驗證群組成員資格時發生錯誤，請稍後再試。",
            "zh-CN": "⚠️ 验证群组成员资格时发生错误，请稍后再试。",
            "en":    "⚠️ An error occurred while verifying group membership. Please try again later.",
        },
    }
    template = messages.get(key, {}).get(lang, messages.get(key, {}).get("zh-TW", ""))
    invite_line = GCC_GROUP_INVITE if GCC_GROUP_INVITE else "（請向 GCC 管理員索取邀請連結）"
    return template.format(invite=invite_line, limit=DAILY_LIMIT)


# ── 群組成員驗證 ──────────────────────────────────────────────────────────────

async def verify_group_membership(
    user_id: int,
    lang: str,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """
    呼叫 Telegram API 確認用戶是否為 GCC 群組成員。
    是成員 → 更新 DB，返回 True
    不是成員 → 返回 False
    API 錯誤 → 返回 False（保守處理）
    """
    if GCC_GROUP_ID == 0:
        # 開發模式：未設定 GROUP_ID 時跳過驗證
        logger.warning("GCC_GROUP_ID 未設定，跳過群組驗證（開發模式）")
        return True

    try:
        member = await context.bot.get_chat_member(
            chat_id=GCC_GROUP_ID,
            user_id=user_id,
        )
        # 有效成員狀態
        valid_statuses = ("member", "administrator", "creator")
        is_member = member.status in valid_statuses

        # 同步更新 DB（不論結果）
        await db.update_user_group_membership(user_id, is_member)
        return is_member

    except Exception as e:
        logger.error(f"群組成員驗證失敗 user_id={user_id}: {e}")
        return False


# ── 主要 Guard 函數 ───────────────────────────────────────────────────────────

class GuardResult:
    """Guard 檢查結果，傳遞給後續 handler"""
    def __init__(
        self,
        passed: bool,
        user=None,
        lang: str = "zh-TW",
        reason: str = "",
    ):
        self.passed = passed      # True = 通過所有關卡
        self.user = user          # models.User 物件
        self.lang = lang          # 偵測到的語言
        self.reason = reason      # 未通過的原因（logging 用）


async def run_guard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> GuardResult:
    """
    執行所有 Guard 關卡。
    返回 GuardResult：passed=True 才繼續處理訊息。

    關卡順序：
    1. 封鎖檢查（最快，不需要 API 呼叫）
    2. 群組成員驗證（需要 Telegram API）
    3. Rate Limit（DB 查詢）
    """
    tg_user = update.effective_user
    if tg_user is None:
        return GuardResult(passed=False, reason="no_user")

    user_id = tg_user.id
    username = tg_user.username or ""
    first_name = tg_user.first_name or ""
    lang = detect_language(update)

    # ── 取得或建立用戶記錄 ────────────────────────────────
    user, is_new = await db.get_or_create_user(
        user_id=user_id,
        username=username,
        first_name=first_name,
        detected_lang=lang,
    )

    # 如果語言有變化，更新 DB
    if not is_new and user.detected_lang != lang:
        await db.update_user_lang(user_id, lang)
        user.detected_lang = lang

    # ── 關卡 1：封鎖檢查 ──────────────────────────────────
    if user.is_blocked:
        await update.message.reply_text(_msg(lang, "blocked"))
        logger.info(f"GUARD BLOCKED: user_id={user_id}")
        return GuardResult(passed=False, user=user, lang=lang, reason="blocked")

    # ── 關卡 2：群組成員驗證 ──────────────────────────────
    # 如果 DB 已記錄為成員，跳過 API 呼叫（快取邏輯）
    # 每隔一段時間重新驗證（避免已離群的用戶繼續使用）
    need_verify = (
        not user.is_group_member
        or _should_reverify(user)
    )

    if need_verify:
        is_member = await verify_group_membership(user_id, lang, context)
        if not is_member:
            await update.message.reply_text(_msg(lang, "not_member"))
            logger.info(f"GUARD NOT_MEMBER: user_id={user_id} (@{username})")
            return GuardResult(passed=False, user=user, lang=lang, reason="not_member")
        user.is_group_member = True

    # ── 關卡 3：Rate Limit ────────────────────────────────
    user.reset_if_new_day()
    if user.daily_count >= DAILY_LIMIT:
        await update.message.reply_text(_msg(lang, "rate_limited"))
        logger.info(f"GUARD RATE_LIMITED: user_id={user_id} count={user.daily_count}")
        return GuardResult(passed=False, user=user, lang=lang, reason="rate_limited")

    # ── 全部通過 ──────────────────────────────────────────
    logger.debug(f"GUARD PASS: user_id={user_id} lang={lang} count={user.daily_count}")
    return GuardResult(passed=True, user=user, lang=lang)


def _should_reverify(user) -> bool:
    """
    判斷是否需要重新驗證群組成員資格。
    策略：每 24 小時重新驗證一次。
    用 count_reset_date 作為日期基準（已有這個欄位，不需要額外欄位）。
    """
    from datetime import datetime
    today = datetime.utcnow().strftime("%Y-%m-%d")
    # 如果 reset_date 是今天，說明今天已經活躍過（驗證過），不需要重複
    # 如果是舊日期，說明隔天了，需要重新驗證
    return user.count_reset_date != today
