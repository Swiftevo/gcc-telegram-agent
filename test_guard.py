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

from db import init_db, get_user, set_user_blocked, update_user_group_membership
from handlers.guard import detect_language, run_guard, GuardResult, DAILY_LIMIT
from handlers.router import route, _has_application_intent, _is_cancel

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


# ── Mock helpers ──────────────────────────────────────────────────────────────

def make_update(
    user_id: int = 100001,
    username: str = "testuser",
    first_name: str = "Test",
    language_code: str = "zh-TW",
    text: str = "你好",
):
    """建立模擬 Telegram Update 物件"""
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
    """建立模擬 Telegram Context，控制 getChatMember 回應"""
    context = MagicMock()

    if raise_error:
        context.bot.get_chat_member = AsyncMock(side_effect=Exception("API Error"))
    else:
        member = MagicMock()
        member.status = "member" if is_member else "left"
        context.bot.get_chat_member = AsyncMock(return_value=member)

    return context


# ── Test 1: 語言偵測 ──────────────────────────────────────────────────────────

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
        ("ja",     "zh-TW"),   # 不認識的語言 → 預設繁體
        ("",       "zh-TW"),   # 空字串 → 預設繁體
    ]

    for lang_code, expected in cases:
        update = make_update(language_code=lang_code)
        result = detect_language(update)
        check(f"language_code='{lang_code}' → '{expected}'", result == expected, f"got '{result}'")


# ── Test 2: 申請意圖偵測 ──────────────────────────────────────────────────────

def test_intent_detection():
    print("\n[ 2 ] 申請意圖偵測測試")

    should_trigger = [
        "我想申請資助",
        "如何申請基金",
        "申請",
        "怎麼申請",
        "I want to apply for a grant",
        "how do i apply",
        "我想申请资助",
        "申请资金",
    ]
    should_not_trigger = [
        "你好",
        "GCC 是什麼",
        "Vyper 項目介紹",
        "GCC 支持哪些方向",
        "hello",
        "what projects has GCC funded",
    ]

    for text in should_trigger:
        check(f"觸發申請意圖：'{text[:20]}'", _has_application_intent(text))

    for text in should_not_trigger:
        check(f"不觸發申請意圖：'{text[:20]}'", not _has_application_intent(text))


# ── Test 3: 取消偵測 ──────────────────────────────────────────────────────────

def test_cancel_detection():
    print("\n[ 3 ] 取消偵測測試")

    should_cancel = ["取消", "算了", "cancel", "/cancel", "stop", "不申請"]
    should_not_cancel = ["繼續", "好的", "我的項目叫做 X", "GCC"]

    for text in should_cancel:
        check(f"觸發取消：'{text}'", _is_cancel(text))
    for text in should_not_cancel:
        check(f"不觸發取消：'{text}'", not _is_cancel(text))


# ── Test 4: Guard 通過情境 ────────────────────────────────────────────────────

async def test_guard_pass():
    print("\n[ 4 ] Guard 通過情境測試")
    await init_db()

    update = make_update(user_id=200001, language_code="zh-TW")
    context = make_context(is_member=True)

    result = await run_guard(update, context)

    check("Guard 通過（is_member=True）", result.passed)
    check("GuardResult 有 user 物件", result.user is not None)
    check("GuardResult lang 正確", result.lang == "zh-TW")
    check("GuardResult reason 為空", result.reason == "")

    # 確認 reply_text 沒有被呼叫（通過不應該發系統訊息）
    check("通過時沒有回覆系統訊息", not update.message.reply_text.called)


# ── Test 5: Guard 非成員攔截 ──────────────────────────────────────────────────

async def test_guard_not_member():
    print("\n[ 5 ] Guard 非成員攔截測試")

    update = make_update(user_id=200002, language_code="zh-TW")
    context = make_context(is_member=False)

    result = await run_guard(update, context)

    check("非成員被攔截（passed=False）", not result.passed)
    check("reason = not_member", result.reason == "not_member")
    check("回覆了系統訊息", update.message.reply_text.called)

    # 確認回覆包含官網連結
    call_args = update.message.reply_text.call_args[0][0]
    check("回覆包含 gccofficial.org", "gccofficial.org" in call_args)


# ── Test 6: Guard Rate Limit ──────────────────────────────────────────────────

async def test_guard_rate_limit():
    print("\n[ 6 ] Guard Rate Limit 測試")

    user_id = 200003
    from datetime import datetime

    # 先建立用戶並設定已達上限
    await init_db()
    from db import get_or_create_user
    import db as db_module

    user, _ = await get_or_create_user(user_id=user_id, username="ratelimit_test")

    # 直接設定 daily_count 到上限
    import aiosqlite
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


# ── Test 7: Guard 封鎖用戶 ────────────────────────────────────────────────────

async def test_guard_blocked():
    print("\n[ 7 ] Guard 封鎖用戶測試")

    user_id = 200004
    from db import get_or_create_user

    await get_or_create_user(user_id=user_id, username="blocked_test")
    await set_user_blocked(user_id, True)

    update = make_update(user_id=user_id)
    context = make_context(is_member=True)

    result = await run_guard(update, context)

    check("封鎖用戶被攔截（passed=False）", not result.passed)
    check("reason = blocked", result.reason == "blocked")
    check("回覆了封鎖訊息", update.message.reply_text.called)

    # 恢復（清理）
    await set_user_blocked(user_id, False)


# ── Test 8: Guard API 錯誤處理 ───────────────────────────────────────────────

async def test_guard_api_error():
    print("\n[ 8 ] Guard API 錯誤處理測試")

    update = make_update(user_id=200005)
    context = make_context(raise_error=True)

    result = await run_guard(update, context)

    # API 錯誤時應保守處理（拒絕），不崩潰
    check("API 錯誤時不崩潰", True)
    check("API 錯誤時攔截（保守）", not result.passed)


# ── Test 9: Router 模式識別 ───────────────────────────────────────────────────

async def test_router():
    print("\n[ 9 ] Router 模式識別測試")

    from db import get_or_create_user

    # 建立測試用戶
    user_id = 200006
    user, _ = await get_or_create_user(user_id=user_id)

    guard = GuardResult(passed=True, lang="zh-TW")
    guard.user = user

    # 一般問答
    update = make_update(user_id=user_id, text="GCC 支持哪些方向？")
    context = make_context()
    result = await route(update, context, guard)
    check("一般問答 → general mode", result.mode == "general")

    # 申請意圖
    update2 = make_update(user_id=user_id, text="我想申請資助")
    result2 = await route(update2, context, guard)
    check("申請意圖 → application mode", result2.mode == "application")

    # Session 已在 application mode，繼續申請
    update3 = make_update(user_id=user_id, text="我的項目叫 TestProject")
    result3 = await route(update3, context, guard)
    check("Session 已在 application → 繼續 application", result3.mode == "application")

    # 取消申請
    update4 = make_update(user_id=user_id, text="取消")
    result4 = await route(update4, context, guard)
    check("取消 → general mode", result4.mode == "general")

    # 管理員指令（正確 user_id）
    os.environ["ADMIN_USER_ID"] = str(user_id)
    import importlib
    import handlers.router as router_module
    importlib.reload(router_module)
    from handlers.router import route as route_reloaded

    update5 = make_update(user_id=user_id, text="/status")
    guard5 = GuardResult(passed=True, lang="zh-TW")
    guard5.user = user
    result5 = await route_reloaded(update5, context, guard5)
    check("管理員 /status → admin mode", result5.mode == "admin")
    check("admin mode 帶有 command", result5.command == "/status")

    # 恢復 ADMIN_USER_ID
    os.environ["ADMIN_USER_ID"] = "999999"


# ── 清理 ──────────────────────────────────────────────────────────────────────

def cleanup():
    if os.path.exists("test_guard.db"):
        os.remove("test_guard.db")


# ── 執行 ──────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 55)
    print("  GCC Telegram Agent — 階段 2 測試")
    print("=" * 55)

    test_language_detection()
    test_intent_detection()
    test_cancel_detection()
    await test_guard_pass()
    await test_guard_not_member()
    await test_guard_rate_limit()
    await test_guard_blocked()
    await test_guard_api_error()
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
