"""
test_guard.py — 階段 2 Guard Layer 測試
測試不需要真實 Telegram 連線，用 Mock 物件模擬 Update。
執行：python test_guard.py
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

os.environ["DB_PATH"] = "test_guard.db"
os.environ["GCC_GROUP_ID"] = "-1003777873964"
os.environ["ADMIN_USER_ID"] = "999999"

from db import (
    complete_email_challenge,
    get_or_create_user,
    init_db,
    set_user_blocked,
    set_user_email,
    set_user_kind,
)
from handlers.access import is_valid_email, mask_email, normalize_email
from handlers.guard import DAILY_LIMIT, GuardResult, detect_language, run_guard
from handlers.router import route
from models import USER_KIND_AI, USER_KIND_GCC_MEMBER

PASS = "✅"
FAIL = "❌"
results = []


def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    msg = f"  {status} {name}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    results.append(condition)
    if not condition:
        print(f"       ↳ FAILED: {detail or 'condition was False'}")


def make_update(
    user_id: int = 100001,
    username: str = "testuser",
    first_name: str = "Test",
    language_code: str = "zh-TW",
    text: str = "你好",
):
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.first_name = first_name
    user.language_code = language_code

    message = MagicMock()
    message.text = text
    message.reply_text = AsyncMock()

    update = MagicMock()
    update.effective_user = user
    update.message = message
    return update


def make_context(is_member: bool = True, raise_error: bool = False):
    context = MagicMock()

    if raise_error:
        context.bot.get_chat_member = AsyncMock(side_effect=Exception("API Error"))
    else:
        member = MagicMock()
        member.status = "member" if is_member else "left"
        context.bot.get_chat_member = AsyncMock(return_value=member)

    return context


async def make_gcc_member(user_id: int, username: str = "gcc") -> None:
    await get_or_create_user(user_id=user_id, username=username)
    await set_user_email(user_id, f"u{user_id}@example.com")
    await complete_email_challenge(user_id, f"u{user_id}@example.com")
    err = await set_user_kind(user_id, USER_KIND_GCC_MEMBER)
    if err:
        raise RuntimeError(err)


def test_language_detection():
    print("\n[ 1 ] 語言偵測測試")

    cases = [
        ("zh-tw",  "zh-TW"),
        ("zh-hk",  "zh-TW"),
        ("zh-mo",  "zh-TW"),
        ("zh-cn",  "zh-CN"),
        ("zh-sg",  "zh-CN"),
        ("zh",     "zh-CN"),
        ("en",     "en"),
        ("en-us",  "en"),
        ("en-gb",  "en"),
        ("ja",     "zh-TW"),
        ("",       "zh-TW"),
    ]

    for lang_code, expected in cases:
        update = make_update(language_code=lang_code)
        result = detect_language(update)
        check(f"language_code='{lang_code}' → '{expected}'", result == expected, f"got '{result}'")


def test_email_helpers():
    print("\n[ 2 ] 郵箱格式與遮罩")
    check("合法郵箱", is_valid_email("Name+tag@GCC.org"))
    check("非法郵箱", not is_valid_email("not-an-email"))
    check("歸一化小寫", normalize_email("Name@GCC.org") == "name@gcc.org")
    masked = mask_email("alice@gcc.org")
    check("遮罩不含完整 local", masked != "alice@gcc.org" and masked.endswith("@gcc.org"))


async def test_guard_pass():
    print("\n[ 3 ] Guard 通過（gcc_member + 郵箱）")
    cleanup()
    await init_db()
    await make_gcc_member(200001, "pass_user")

    update = make_update(user_id=200001, language_code="zh-TW")
    context = make_context(is_member=False)

    result = await run_guard(update, context)

    check("已授權成員通過（不需當前在群裡）", result.passed)
    check("GuardResult 有 user 物件", result.user is not None)
    check("GuardResult lang 正確", result.lang == "zh-TW")
    check("GuardResult reason 為空", result.reason == "")
    check("通過時沒有回覆系統訊息", not update.message.reply_text.called)


async def test_guard_welcome_only():
    print("\n[ 4 ] 普通用戶 / AI 只回歡迎語")

    update = make_update(user_id=200002, language_code="zh-TW")
    context = make_context(is_member=True)
    result = await run_guard(update, context)
    check("普通用戶 passed=False", not result.passed)
    check("reason = welcome_only", result.reason == "welcome_only")
    check("回覆了歡迎語", update.message.reply_text.called)
    call_args = update.message.reply_text.call_args[0][0]
    check("回覆包含 gccofficial.org", "gccofficial.org" in call_args)

    await get_or_create_user(user_id=200022, username="botish")
    await set_user_kind(200022, USER_KIND_AI)
    update_ai = make_update(user_id=200022)
    result_ai = await run_guard(update_ai, context)
    check("AI 也是 welcome_only", result_ai.reason == "welcome_only")


async def test_guard_rate_limit():
    print("\n[ 5 ] Guard Rate Limit 測試")

    user_id = 200003
    from datetime import datetime
    import aiosqlite

    await make_gcc_member(user_id, "ratelimit_test")

    today = datetime.utcnow().strftime("%Y-%m-%d")
    async with aiosqlite.connect("test_guard.db") as conn:
        await conn.execute(
            "UPDATE users SET daily_count = ?, count_reset_date = ? WHERE user_id = ?",
            (DAILY_LIMIT, today, user_id),
        )
        await conn.commit()

    update = make_update(user_id=user_id, language_code="en")
    context = make_context(is_member=True)

    result = await run_guard(update, context)

    check("Rate Limit 攔截（passed=False）", not result.passed)
    check("reason = rate_limited", result.reason == "rate_limited")
    check("回覆了限制訊息", update.message.reply_text.called)

    call_args = update.message.reply_text.call_args[0][0]
    check("回覆包含上限數字", str(DAILY_LIMIT) in call_args)


async def test_guard_blocked():
    print("\n[ 6 ] Guard 封鎖用戶測試")

    user_id = 200004
    await make_gcc_member(user_id, "blocked_test")
    await set_user_blocked(user_id, True)

    update = make_update(user_id=user_id)
    context = make_context(is_member=True)

    result = await run_guard(update, context)

    check("封鎖用戶被攔截（passed=False）", not result.passed)
    check("reason = blocked", result.reason == "blocked")
    check("回覆了封鎖訊息", update.message.reply_text.called)

    await set_user_blocked(user_id, False)


async def test_gcc_member_needs_email():
    print("\n[ 7 ] gcc_member 缺郵箱不能問答")
    user_id = 200005
    await get_or_create_user(user_id=user_id, username="noemail")
    # 直接寫 identity，繞過 service 驗證（模擬資料不完整）
    import aiosqlite
    async with aiosqlite.connect("test_guard.db") as conn:
        await conn.execute(
            "UPDATE users SET user_kind = ?, actor_type = 'human', access_level = 'gcc_member' WHERE user_id = ?",
            (USER_KIND_GCC_MEMBER, user_id),
        )
        await conn.commit()

    update = make_update(user_id=user_id)
    result = await run_guard(update, make_context())
    check("缺郵箱 welcome_only", result.reason == "welcome_only")
    body = update.message.reply_text.call_args[0][0]
    check("提示去綁定郵箱", "/email" in body)


async def test_router():
    print("\n[ 8 ] Router 模式識別測試")

    user_id = 200006
    user, _ = await get_or_create_user(user_id=user_id)

    guard = GuardResult(passed=True, lang="zh-TW")
    guard.user = user

    update = make_update(user_id=user_id, text="GCC 支持哪些方向？")
    context = make_context()
    result = await route(update, context, guard)
    check("一般問答 → general mode", result.mode == "general")

    update2 = make_update(user_id=user_id, text="我想申請資助")
    result2 = await route(update2, context, guard)
    check("申請關鍵詞仍走 general（由按鈕進入申請）", result2.mode == "general")

    from gcc_agent.config import settings
    original_admin = settings.admin_user_id
    object.__setattr__(settings, "admin_user_id", user_id)

    update5 = make_update(user_id=user_id, text="/status")
    guard5 = GuardResult(passed=True, lang="zh-TW")
    guard5.user = user
    result5 = await route(update5, context, guard5)
    check("管理員 /status → admin mode", result5.mode == "admin")
    check("admin mode 帶有 command", result5.command == "/status")

    object.__setattr__(settings, "admin_user_id", original_admin)


def cleanup():
    if os.path.exists("test_guard.db"):
        os.remove("test_guard.db")


async def main():
    print("=" * 55)
    print("  GCC Telegram Agent — 階段 2 測試")
    print("=" * 55)

    test_language_detection()
    test_email_helpers()
    await test_guard_pass()
    await test_guard_welcome_only()
    await test_guard_rate_limit()
    await test_guard_blocked()
    await test_gcc_member_needs_email()
    await test_router()

    print("\n" + "=" * 55)
    passed = sum(results)
    total = len(results)
    failed = total - passed
    print(f"  結果：{passed}/{total} 通過  |  {failed} 失敗")
    if failed == 0:
        print("  🎉 階段 2 完成！可以進入階段 3。")
    else:
        print("  ⚠️  有測試失敗，請修正後再繼續。")
    print("=" * 55)

    cleanup()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
