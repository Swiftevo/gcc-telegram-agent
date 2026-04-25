"""
test_stage4.py — 階段 4 測試
執行：python test_stage4.py
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["DB_PATH"]        = "test_stage4.db"
os.environ["GCC_GROUP_ID"]   = "-1003777873964"
os.environ["ADMIN_USER_ID"]  = "999999"
os.environ["ADMIN_NOTIFY_ID"]= "999999"
os.environ["OPENAI_API_KEY"] = "sk-test-fake"

from db import init_db, get_or_create_user
from models import ApplicationDraft, Session
from handlers.application import pre_screen, notify_admin, handle_application
from handlers.guard import GuardResult

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


# ── Test 1: 預審評分邏輯 ──────────────────────────────────────────────────────

def test_pre_screen():
    print("\n[ 1 ] Values Engine 預審評分測試")

    # 高分案例：公共物品 + 開源 + 提及華語社區
    high_draft = ApplicationDraft(
        project_name="OpenDAO",
        fund_type="public",
        one_liner="一個開源的去中心化治理協議，專為華語社區設計，解決公共物品資金分配問題",
        collection_step=3,
    )
    score_high, notes_high = pre_screen(high_draft)
    check("高分案例總分 >= 70", score_high >= 70, f"score={score_high}")
    check("高分案例有評分備注", len(notes_high) > 0)
    check("高分案例有使命契合標記", "✅" in notes_high)

    # 中分案例：有開源但沒有明確華語社區
    mid_draft = ApplicationDraft(
        project_name="DevTool",
        fund_type="public",
        one_liner="一個開源的開發者工具，幫助更多人使用以太坊",
        collection_step=3,
    )
    score_mid, notes_mid = pre_screen(mid_draft)
    check("中分案例總分在 40-69", 40 <= score_mid < 70, f"score={score_mid}")

    # 低分案例：描述不清晰，無公共物品關鍵詞
    low_draft = ApplicationDraft(
        project_name="MyApp",
        fund_type="public",
        one_liner="做一個 app",
        collection_step=3,
    )
    score_low, notes_low = pre_screen(low_draft)
    check("低分案例總分 < 60", score_low < 60, f"score={score_low}")
    check("低分案例有警告標記", "🔴" in notes_low or "🔶" in notes_low)

    # 分數範圍合理
    for draft, label in [
        (high_draft, "高分"), (mid_draft, "中分"), (low_draft, "低分")
    ]:
        score, _ = pre_screen(draft)
        check(f"{label}案例分數在 0-100 之間", 0 <= score <= 100, f"score={score}")


# ── Test 2: 三步收集流程 ──────────────────────────────────────────────────────

async def test_application_flow():
    print("\n[ 2 ] 三步申請收集流程測試")

    await init_db()
    user, _ = await get_or_create_user(user_id=500001, username="apply_test")

    guard = GuardResult(passed=True, lang="zh-TW")
    guard.user = user

    def make_update(text):
        update = MagicMock()
        update.message.text = text
        update.message.reply_text = AsyncMock()
        return update

    context = MagicMock()
    context.bot.send_message = AsyncMock()

    # ── Step 0：偵測申請意圖，開始收集 ─────────────────
    update0 = make_update("我想申請資助")
    await handle_application(update0, context, guard)

    check("Step 0：回覆了訊息", update0.message.reply_text.called)
    reply0 = update0.message.reply_text.call_args[0][0]
    check("Step 0：回覆包含項目名稱詢問", "項目名稱" in reply0 or "project" in reply0.lower())

    # 驗證 Session 更新
    from core.session import get_session
    session = await get_session(guard)
    check("Step 0：collection_step = 1", session.application_draft.collection_step == 1)

    # ── Step 1：提供項目名稱 ──────────────────────────
    update1 = make_update("OpenCommons Protocol")
    await handle_application(update1, context, guard)

    check("Step 1：回覆了訊息", update1.message.reply_text.called)
    reply1 = update1.message.reply_text.call_args[0][0]
    check("Step 1：回覆包含項目名稱確認", "OpenCommons Protocol" in reply1)
    check("Step 1：回覆包含基金類型詢問", "公共" in reply1 or "專項" in reply1)

    session = await get_session(guard)
    check("Step 1：project_name 已儲存", session.application_draft.project_name == "OpenCommons Protocol")
    check("Step 1：collection_step = 2", session.application_draft.collection_step == 2)

    # ── Step 2：提供基金類型（無效輸入）────────────────
    update2a = make_update("不知道")
    await handle_application(update2a, context, guard)
    reply2a = update2a.message.reply_text.call_args[0][0]
    check("Step 2 無效輸入：重新詢問", "公共" in reply2a or "专项" in reply2a or "public" in reply2a.lower())

    # Session 仍在 step 2
    session = await get_session(guard)
    check("Step 2 無效輸入後：collection_step 仍為 2", session.application_draft.collection_step == 2)

    # ── Step 2：提供有效基金類型 ──────────────────────
    update2b = make_update("公共")
    await handle_application(update2b, context, guard)
    reply2b = update2b.message.reply_text.call_args[0][0]
    check("Step 2 有效輸入：回覆詢問一句話介紹", "一句話" in reply2b or "one sentence" in reply2b.lower())

    session = await get_session(guard)
    check("Step 2：fund_type = public", session.application_draft.fund_type == "public")
    check("Step 2：collection_step = 3", session.application_draft.collection_step == 3)

    # ── Step 3：提供一句話介紹 ────────────────────────
    update3 = make_update("一個開源的公共物品協議，讓華語社區可以更公平地分配公共資源")
    await handle_application(update3, context, guard)
    reply3 = update3.message.reply_text.call_args[0][0]

    check("Step 3：回覆收到確認", "✅" in reply3)
    check("Step 3：回覆包含申請表連結", "gccofficial.org/application" in reply3)
    check("Step 3：回覆包含例會提醒", "例會" in reply3)

    # 管理員通知已發送
    check("Step 3：管理員通知已發送", context.bot.send_message.called)
    notify_args = context.bot.send_message.call_args
    check("Step 3：通知發送到正確的 chat_id", notify_args[1]["chat_id"] == 999999)
    notify_text = notify_args[1]["text"]
    check("Step 3：通知包含項目名稱", "OpenCommons Protocol" in notify_text)
    check("Step 3：通知包含預審分數", "/100" in notify_text)
    check("Step 3：通知包含申請人 username", "apply_test" in notify_text)

    # Session 已重置回 general mode
    session = await get_session(guard)
    check("Step 3 完成：Session mode 重置為 general", session.mode == "general")


# ── Test 3: 預審分數觸發邏輯 ─────────────────────────────────────────────────

def test_score_thresholds():
    print("\n[ 3 ] 預審分數觸發閾值測試")

    # 分數 >= 70 應觸發「建議跟進」
    strong = ApplicationDraft(
        project_name="ZK Privacy Tool",
        fund_type="public",
        one_liner="開源零知識證明隱私工具，保護華語社區用戶的鏈上隱私，抗審查設計",
        collection_step=3,
    )
    score, notes = pre_screen(strong)
    check("強申請分數 >= 70", score >= 70, f"score={score}")

    # 分數 < 40 應在通知中標示紅燈
    weak = ApplicationDraft(
        project_name="App",
        fund_type="public",
        one_liner="做個 app 賺錢",
        collection_step=3,
    )
    score_weak, notes_weak = pre_screen(weak)
    check("弱申請分數 < 40", score_weak < 40, f"score={score_weak}")
    check("弱申請有紅燈標記", "🔴" in notes_weak)


# ── Test 4: 多語言申請流程 ───────────────────────────────────────────────────

async def test_multilang_application():
    print("\n[ 4 ] 多語言申請流程測試")

    await init_db()

    for user_id, lang, fund_input in [
        (500002, "zh-CN", "公共"),
        (500003, "en",    "public"),
    ]:
        user, _ = await get_or_create_user(user_id=user_id, username=f"user_{user_id}")
        guard = GuardResult(passed=True, lang=lang)
        guard.user = user

        context = MagicMock()
        context.bot.send_message = AsyncMock()

        # Step 0
        u0 = MagicMock()
        u0.message.text = "apply" if lang == "en" else "申請"
        u0.message.reply_text = AsyncMock()
        await handle_application(u0, context, guard)
        r0 = u0.message.reply_text.call_args[0][0]
        check(f"[{lang}] Step 0 回覆非空", len(r0) > 0)

        # Step 1
        u1 = MagicMock()
        u1.message.text = "TestProject"
        u1.message.reply_text = AsyncMock()
        await handle_application(u1, context, guard)

        # Step 2
        u2 = MagicMock()
        u2.message.text = fund_input
        u2.message.reply_text = AsyncMock()
        await handle_application(u2, context, guard)
        r2 = u2.message.reply_text.call_args[0][0]
        check(f"[{lang}] Step 2 回覆非空", len(r2) > 0)

        # Step 3
        u3 = MagicMock()
        u3.message.text = "An open source public goods tool for the Chinese community"
        u3.message.reply_text = AsyncMock()
        await handle_application(u3, context, guard)
        r3 = u3.message.reply_text.call_args[0][0]
        check(f"[{lang}] Step 3 確認訊息包含 ✅", "✅" in r3)
        check(f"[{lang}] Step 3 管理員已通知", context.bot.send_message.called)


# ── Test 5: admin.py 指令測試 ─────────────────────────────────────────────────

async def test_admin_commands():
    print("\n[ 5 ] Admin 指令測試")

    await init_db()
    user, _ = await get_or_create_user(user_id=999999, username="admin")
    guard = GuardResult(passed=True, lang="zh-TW")
    guard.user = user

    # /status
    update = MagicMock()
    update.effective_user.id = 999999
    update.message.reply_text = AsyncMock()

    from handlers.admin import handle_admin
    await handle_admin(update, MagicMock(), guard, "/status")
    check("/status 回覆了訊息", update.message.reply_text.called)
    reply = update.message.reply_text.call_args[0][0]
    check("/status 包含總用戶數", "總用戶數" in reply or "total" in reply.lower())
    check("/status 包含今日統計", "今日" in reply or "today" in reply.lower())

    # /update_values（values.yaml 存在時）
    update2 = MagicMock()
    update2.effective_user.id = 999999
    update2.message.reply_text = AsyncMock()

    await handle_admin(update2, MagicMock(), guard, "/update_values")
    check("/update_values 回覆了訊息", update2.message.reply_text.called)
    reply2 = update2.message.reply_text.call_args[0][0]
    # 有 values.yaml 就成功，沒有就回覆載入失敗（兩者都算通過）
    check("/update_values 有回應", len(reply2) > 0)


# ── 清理 ──────────────────────────────────────────────────────────────────────

def cleanup():
    if os.path.exists("test_stage4.db"):
        os.remove("test_stage4.db")


# ── 執行 ──────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 55)
    print("  GCC Telegram Agent — 階段 4 測試")
    print("=" * 55)

    test_pre_screen()
    await test_application_flow()
    test_score_thresholds()
    await test_multilang_application()
    await test_admin_commands()

    print("\n" + "=" * 55)
    passed = sum(results)
    total = len(results)
    failed = total - passed
    print(f"  結果：{passed}/{total} 通過  |  {failed} 失敗")
    if failed == 0:
        print("  🎉 階段 4 完成！可以進入階段 5（部署）。")
    else:
        print("  ⚠️  有測試失敗，請修正後再繼續。")
    print("=" * 55)

    cleanup()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
