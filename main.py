"""
main.py — GCC Telegram Agent 入口
啟動 Bot，設定 Webhook，連接所有 handlers。
"""

import logging
import os
import re

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

import db
from handlers.guard import run_guard
from handlers.router import route

# ── 環境變數 ──────────────────────────────────────────────────────────────────
load_dotenv()

BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
ADMIN_USER_ID  = int(os.getenv("ADMIN_USER_ID", "0"))
WEBHOOK_URL    = os.getenv("WEBHOOK_URL", "")   # https://your-app.fly.dev/webhook
PORT           = int(os.getenv("PORT", "8080"))

# ── Logging + Token 遮蔽 ─────────────────────────────────────────────────────

class _TokenRedactionFilter(logging.Filter):
    """
    遮蔽日誌中的 Bot Token，防止 API 金鑰外洩到 Fly.io 日誌或任何日誌系統。
    格式：bot123456:ABC-DEF → bot[REDACTED]
    """
    _PATTERN = re.compile(r"bot\d+:[A-Za-z0-9_-]+")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._PATTERN.sub("bot[REDACTED]", record.msg)
        # args 也需要遮蔽（logging 會把 args 插入 msg）
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    self._PATTERN.sub("bot[REDACTED]", a) if isinstance(a, str) else a
                    for a in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: self._PATTERN.sub("bot[REDACTED]", v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
        return True


def _setup_logging() -> None:
    """設定 logging，並對所有 handler 套用 Token 遮蔽過濾器"""
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        level=logging.INFO,
    )
    redact = _TokenRedactionFilter()
    # 套用到 root logger 的所有 handler，覆蓋全部子 logger
    for handler in logging.root.handlers:
        handler.addFilter(redact)


_setup_logging()
logger = logging.getLogger(__name__)


# ── 核心訊息分發 ──────────────────────────────────────────────────────────────

async def handle_message(update: Update, context):
    """
    所有私訊和群組 @mention 都進這裡。
    Guard → Router → 對應 Handler
    """
    if update.message is None:
        return

    # ── Guard：三道關卡 ────────────────────────────────────
    guard = await run_guard(update, context)
    if not guard.passed:
        return   # Guard 已發送回覆，直接結束

    # ── 計數（通過 Guard 才算數）──────────────────────────
    await db.increment_user_message_count(guard.user.user_id)

    # ── Router：決定模式 ───────────────────────────────────
    route_result = await route(update, context, guard)

    # ── 分發到對應 Handler ─────────────────────────────────
    if route_result.mode == "admin":
        from handlers.admin import handle_admin
        await handle_admin(update, context, guard, route_result.command)

    elif route_result.mode == "application":
        from handlers.application import handle_application
        await handle_application(update, context, guard)

    else:
        from handlers.general import handle_general
        await handle_general(update, context, guard)




async def handle_callback(update, context):
    """
    處理 Inline Button 點擊（callback_data）。
    intent_apply → 進入申請模式（0 token）
    intent_exit  → 退出申請模式（0 token）
    完全繞過 AI 路由，不消耗任何 token。
    """
    query = update.callback_query
    await query.answer()  # 消除按鈕的 loading 狀態

    user_id = query.from_user.id

    # Guard：確認是群組成員且未被封鎖
    from db import get_user, get_or_create_session, save_session
    from handlers.guard import detect_language

    user = await get_user(user_id)
    if user is None or user.is_blocked:
        return

    lang_code = query.from_user.language_code or "zh-TW"
    from handlers.guard import detect_language as _dl
    # 簡易語言偵測
    lang = "zh-TW"
    if lang_code:
        lc = lang_code.lower()
        if lc in ("zh-cn", "zh-sg", "zh"):
            lang = "zh-CN"
        elif lc.startswith("en"):
            lang = "en"

    session, _ = await get_or_create_session(user_id)

    if query.data == "intent_apply":
        session.mode = "application"
        session.application_draft.__init__()  # 重置草稿，重新開始
        await save_session(session)

        # 直接發出第一個問題（項目名稱）
        from handlers.application import _t, make_exit_markup
        from models import ApplicationDraft
        session.application_draft.collection_step = 1
        await save_session(session)
        reply = _t(lang, "intro")
        await query.message.reply_text(
            reply,
            parse_mode="Markdown",
            reply_markup=make_exit_markup(lang),
        )
        logger.info(f"CALLBACK APPLY: user_id={user_id}")

    elif query.data == "intent_exit":
        session.mode = "general"
        session.application_draft.__init__()
        await save_session(session)

        exit_msg = {
            "zh-TW": "✅ 已退出申請流程。有其他問題歡迎繼續發問。\n\n_如希望深入交流，歡迎參與 GCC 定期例會。_",
            "zh-CN": "✅ 已退出申请流程。有其他问题欢迎继续提问。\n\n_如希望深入交流，欢迎参与 GCC 定期例会。_",
            "en":    "✅ You have exited the application flow. Feel free to ask anything else.\n\n_For deeper discussion, join GCC regular community calls._",
        }
        await query.message.reply_text(
            exit_msg.get(lang, exit_msg["zh-TW"]),
            parse_mode="Markdown",
        )
        logger.info(f"CALLBACK EXIT: user_id={user_id}")

async def handle_start(update: Update, context):
    """/start 指令：歡迎訊息"""
    from handlers.guard import run_guard, detect_language
    lang = detect_language(update)

    welcome = {
        "zh-TW": (
            "👋 你好！我是 *GCC AI 助手*。\n\n"
            "我可以幫你了解 GCC 的資助方向、已資助項目，"
            "以及如何申請資助。\n\n"
            "🔗 官方網站：https://www.gccofficial.org\n\n"
            "有什麼想問的，直接說吧！\n\n"
            "_如希望深入交流，歡迎參與 GCC 定期例會。_"
        ),
        "zh-CN": (
            "👋 你好！我是 *GCC AI 助手*。\n\n"
            "我可以帮你了解 GCC 的资助方向、已资助项目，"
            "以及如何申请资助。\n\n"
            "🔗 官方网站：https://www.gccofficial.org\n\n"
            "有什么想问的，直接说吧！\n\n"
            "_如希望深入交流，欢迎参与 GCC 定期例会。_"
        ),
        "en": (
            "👋 Hello! I'm the *GCC AI Assistant*.\n\n"
            "I can help you learn about GCC's funding directions, "
            "funded projects, and how to apply for a grant.\n\n"
            "🔗 Website: https://www.gccofficial.org\n\n"
            "Feel free to ask me anything!\n\n"
            "_For deeper discussion, join GCC's regular community calls._"
        ),
    }

    # /start 不需要通過 Guard，直接回覆歡迎訊息
    msg = welcome.get(lang, welcome["zh-TW"])
    await update.message.reply_text(msg, parse_mode="Markdown")


# ── 啟動 ──────────────────────────────────────────────────────────────────────

async def post_init(application: Application) -> None:
    """Bot 啟動後執行：初始化 DB"""
    await db.init_db()
    logger.info("DB 初始化完成")
    logger.info(f"Bot 啟動：@{(await application.bot.get_me()).username}")


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN 未設定，請檢查 .env 檔案")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # 指令 handlers
    app.add_handler(CommandHandler("start", handle_start))

    # Inline Button 點擊（最高優先，完全不消耗 token）
    app.add_handler(CallbackQueryHandler(handle_callback))

    # 所有私訊
    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_message)
    )

    # 群組中被 @mention（可選，初期用私訊即可）
    # app.add_handler(
    #     MessageHandler(filters.TEXT & filters.Entity("mention"), handle_message)
    # )

    # ── 啟動模式 ──────────────────────────────────────────
    if WEBHOOK_URL:
        # 生產環境：Webhook 模式（Fly.io）
        logger.info(f"Webhook 模式啟動：{WEBHOOK_URL}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=WEBHOOK_URL,
            url_path="/webhook",
        )
    else:
        # 本地開發：Polling 模式
        logger.info("Polling 模式啟動（本地開發）")
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
