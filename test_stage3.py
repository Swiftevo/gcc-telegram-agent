"""
test_stage3.py — 階段 3 測試
執行：python test_stage3.py
不需要真實 OpenAI API Key，AI 呼叫會被 Mock。
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["DB_PATH"]       = "test_stage3.db"
os.environ["GCC_GROUP_ID"]  = "-1003777873964"
os.environ["ADMIN_USER_ID"] = "999999"
os.environ["OPENAI_API_KEY"] = "sk-test-fake-key"

from db import init_db, get_or_create_user
from models import Session, AgentValues
from core.values import load_values, as_system_block, as_gcc_summary_block, reload_values
from core.prompt import check_link_first, build_messages, GCC_LINKS, PROJECT_LINKS
from core.session import get_session, save_exchange
from handlers.general import append_reminder, MEETING_REMINDER
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


# ── Test 1: values.yaml 載入 ──────────────────────────────────────────────────

def test_values_load():
    print("\n[ 1 ] core/values.py 載入測試")

    # 沒有 values.yaml 時不崩潰
    v = load_values()
    check("無 values.yaml 時返回空 AgentValues", isinstance(v, AgentValues))

    # 有 values.yaml 時正確載入（如果存在）
    if os.path.exists("values.yaml"):
        v2 = reload_values()
        check("values.yaml 載入版本號", len(v2.version) > 0)
        check("values.yaml 載入 mission_statement", len(v2.mission_statement) > 0)
        check("values.yaml 載入 priority_themes（list）", isinstance(v2.priority_themes, list))
        check("values.yaml priority_themes 不為空", len(v2.priority_themes) > 0)
        check("values.yaml 載入 screening_rubric（dict）", isinstance(v2.screening_rubric, dict))
    else:
        print("  ⚠️  values.yaml 不存在，跳過詳細載入測試")


def test_system_block():
    print("\n[ 2 ] System Block 生成測試")

    # 用假資料測試格式
    fake_values = AgentValues(
        version="1.0.0",
        mission_statement="測試使命",
        priority_themes=["開源軟件", "治理研究"],
        rejection_criteria=["商業項目", "不開源"],
        screening_rubric={
            "mission_fit": 40,
            "public_goods_nature": 30,
            "chinese_community": 20,
            "feasibility": 10,
        },
        tone_guidelines="保持簡潔。",
        gcc_summary="GCC 是資助機構。",
    )

    block = as_system_block(fake_values)
    check("System block 不為空", len(block) > 0)
    check("包含 IMMUTABLE 標記", "IMMUTABLE" in block)
    check("包含使命文字", "測試使命" in block)
    check("包含優先方向", "開源軟件" in block)
    check("包含拒絕標準", "商業項目" in block)
    check("包含評分邏輯", "40" in block)
    check("包含語氣指引", "保持簡潔" in block)
    check("包含 END OF IMMUTABLE", "END OF IMMUTABLE" in block)

    summary = as_gcc_summary_block(fake_values)
    check("GCC Summary block 不為空", len(summary) > 0)
    check("Summary 包含 gcc_summary 內容", "GCC 是資助機構" in summary)


# ── Test 3: 連結優先邏輯 ──────────────────────────────────────────────────────

def test_link_first():
    print("\n[ 3 ] 連結優先邏輯測試")

    # 項目名稱匹配
    cases_project = [
        ("Vyper 是什麼",         "zh-TW", True,  "project"),
        ("tell me about vyper",  "en",    True,  "project"),
        ("OSKey 介紹",            "zh-TW", True,  "project"),
        ("zk punk 項目",         "zh-TW", True,  "project"),
        ("primus 是什麼",        "zh-CN", True,  "project"),
        ("agora citizen 詳情",   "zh-TW", True,  "project"),
    ]

    for text, lang, expect_match, expect_type in cases_project:
        r = check_link_first(text, lang)
        check(
            f"項目匹配：'{text[:20]}'",
            r.matched == expect_match and r.link_type == expect_type,
            f"matched={r.matched} type={r.link_type}"
        )

    # 申請流程匹配
    cases_apply = [
        ("如何申請資助",         "zh-TW", True,  "apply"),
        ("申請流程是什麼",       "zh-TW", True,  "apply"),
        ("how to apply",         "en",    True,  "apply"),
        ("公共基金如何申請",     "zh-TW", True,  "apply_public"),
        ("專項基金申請",         "zh-TW", True,  "apply_special"),
        ("機票計劃怎麼申請",     "zh-TW", True,  "apply_special"),
    ]

    for text, lang, expect_match, expect_type in cases_apply:
        r = check_link_first(text, lang)
        check(
            f"申請匹配：'{text[:20]}'",
            r.matched == expect_match and r.link_type == expect_type,
            f"matched={r.matched} type={r.link_type}"
        )

    # 官網頁面匹配
    cases_page = [
        ("GCC 是什麼",           "zh-TW", True,  "about"),
        ("所有資助項目",         "zh-TW", True,  "projects"),
        ("捐款給 GCC",           "zh-TW", True,  "donate"),
        ("contact gcc",          "en",    True,  "contact"),
        ("GCC 投票",             "zh-TW", True,  "vote"),
    ]

    for text, lang, expect_match, expect_type in cases_page:
        r = check_link_first(text, lang)
        check(
            f"頁面匹配：'{text[:20]}'",
            r.matched == expect_match and r.link_type == expect_type,
            f"matched={r.matched} type={r.link_type}"
        )

    # 不應匹配（需要 AI 回答）
    cases_no_match = [
        "你好",
        "GCC 跟 Gitcoin 有什麼分別",
        "公共物品是什麼概念",
        "我的項目符合條件嗎",
        "什麼是零知識證明",
    ]

    for text in cases_no_match:
        r = check_link_first(text, "zh-TW")
        check(f"不匹配（需 AI）：'{text[:20]}'", not r.matched, f"matched={r.matched}")

    # 確認回覆包含連結和例會提醒
    r = check_link_first("Vyper 是什麼", "zh-TW")
    check("項目回覆包含項目頁面 URL", "gccofficial.org/project" in r.reply)
    check("項目回覆包含例會提醒", "例會" in r.reply)

    r_en = check_link_first("how to apply", "en")
    check("英文回覆包含例會提醒（英文）", "community calls" in r_en.reply)


# ── Test 4: Prompt 組裝 ───────────────────────────────────────────────────────

def test_build_messages():
    print("\n[ 4 ] 三層 Prompt 組裝測試")

    session = Session(user_id=100001)
    session.add_message("user", "你好")
    session.add_message("assistant", "你好！有什麼可以幫到你？")

    msgs = build_messages("GCC 支持什麼方向？", session, "zh-TW")

    check("messages 是 list", isinstance(msgs, list))
    check("至少有 4 條（layer1 + layer2 + 2條history + 新訊息）", len(msgs) >= 4)

    # Layer 1 必須是第一條 system message
    check("Layer 1 是 system role", msgs[0]["role"] == "system")
    check("Layer 1 包含 IMMUTABLE 標記", "IMMUTABLE" in msgs[0]["content"])

    # Layer 2 也是 system
    check("Layer 2 是 system role", msgs[1]["role"] == "system")
    check("Layer 2 包含 GCC 摘要", "GCC" in msgs[1]["content"])

    # 對話歷史在 Layer 1/2 之後
    check("Layer 3 第一條是 user（歷史）", msgs[2]["role"] == "user")
    check("Layer 3 第一條內容正確", msgs[2]["content"] == "你好")

    # 新訊息是最後一條 user
    check("最後一條是 user role", msgs[-1]["role"] == "user")
    check("最後一條是新訊息", msgs[-1]["content"] == "GCC 支持什麼方向？")

    # Layer 1 永遠在最前，用戶訊息永遠在後
    system_indices = [i for i, m in enumerate(msgs) if m["role"] == "system"]
    user_indices = [i for i, m in enumerate(msgs) if m["role"] == "user"]
    check("所有 system 都在第一條 user 之前", max(system_indices) < min(user_indices))

    # 超過 20 條歷史只保留 20 條
    big_session = Session(user_id=100002)
    for i in range(30):
        big_session.add_message("user", f"msg {i}")
        big_session.add_message("assistant", f"reply {i}")
    msgs_big = build_messages("新問題", big_session, "zh-TW")
    history_msgs = [m for m in msgs_big if m["role"] != "system"]
    check("超過 20 條歷史只保留 20 條", len(history_msgs) <= 21)  # 20條 + 1條新訊息


# ── Test 5: 例會提醒 ──────────────────────────────────────────────────────────

def test_meeting_reminder():
    print("\n[ 5 ] 例會提醒測試")

    text = "這是一個 AI 回覆"
    result_tw = append_reminder(text, "zh-TW")
    result_cn = append_reminder(text, "zh-CN")
    result_en = append_reminder(text, "en")

    check("繁體中文附加例會提醒", "例會" in result_tw)
    check("簡體中文附加例會提醒", "例会" in result_cn)
    check("英文附加例會提醒", "community calls" in result_en)

    # 避免重複附加
    already_has = "這個回覆已經提到例會了。"
    result_no_dup = append_reminder(already_has, "zh-TW")
    count = result_no_dup.count("例會")
    check("不重複附加提醒", count == 1, f"出現 {count} 次")


# ── Test 6: Session 管理 ─────────────────────────────────────────────────────

async def test_session():
    print("\n[ 6 ] core/session.py 測試")

    await init_db()
    user, _ = await get_or_create_user(user_id=300001, username="session_test")

    guard = GuardResult(passed=True, lang="zh-TW")
    guard.user = user

    # 取得新 Session
    session = await get_session(guard)
    check("get_session 返回 Session 物件", isinstance(session, Session))
    check("Session user_id 正確", session.user_id == 300001)

    # 儲存一問一答
    await save_exchange(
        session=session,
        user_id=300001,
        user_text="GCC 是什麼？",
        assistant_text="GCC 是全球華語數字公地資助機構。",
        tokens_used=50,
        link_served=False,
    )

    # 確認訊息已加入 session.messages
    check("save_exchange 後 session.messages 有 2 條", len(session.messages) == 2)
    check("第一條是 user", session.messages[0]["role"] == "user")
    check("第二條是 assistant", session.messages[1]["role"] == "assistant")

    # 重新載入確認持久化
    session2 = await get_session(guard)
    check("持久化後重新載入有 2 條訊息", len(session2.messages) == 2)


# ── Test 7: handle_general Mock 測試 ─────────────────────────────────────────

async def test_handle_general_link():
    print("\n[ 7 ] handle_general 連結優先測試（Mock）")

    await init_db()
    user, _ = await get_or_create_user(user_id=400001, username="general_test")

    guard = GuardResult(passed=True, lang="zh-TW")
    guard.user = user

    update = MagicMock()
    update.message.text = "Vyper 是什麼"
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    from handlers.general import handle_general
    await handle_general(update, context, guard)

    # 應該直接回覆連結，不呼叫 AI
    check("handle_general 回覆了訊息", update.message.reply_text.called)
    call_args = update.message.reply_text.call_args[0][0]
    check("回覆包含 Vyper 項目連結", "gccofficial.org/project" in call_args)
    check("回覆包含例會提醒", "例會" in call_args)


async def test_handle_general_ai():
    print("\n[ 8 ] handle_general AI 呼叫測試（Mock OpenAI）")

    await init_db()
    user, _ = await get_or_create_user(user_id=400002, username="ai_test")

    guard = GuardResult(passed=True, lang="zh-TW")
    guard.user = user

    update = MagicMock()
    update.message.text = "公共物品是什麼概念？"
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    # Mock OpenAI 回應
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "公共物品是指非排他性且非競爭性的物品。"
    mock_response.usage.total_tokens = 42

    with patch("handlers.general.get_openai_client") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_instance

        from handlers.general import handle_general
        await handle_general(update, context, guard)

    check("AI 回覆了訊息", update.message.reply_text.called)
    call_args = update.message.reply_text.call_args[0][0]
    check("回覆包含 AI 回應內容", "公共物品" in call_args)
    check("回覆包含例會提醒", "例會" in call_args)


# ── 清理 ──────────────────────────────────────────────────────────────────────

def cleanup():
    if os.path.exists("test_stage3.db"):
        os.remove("test_stage3.db")


# ── 執行 ──────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 55)
    print("  GCC Telegram Agent — 階段 3 測試")
    print("=" * 55)

    test_values_load()
    test_system_block()
    test_link_first()
    test_build_messages()
    test_meeting_reminder()
    await test_session()
    await test_handle_general_link()
    await test_handle_general_ai()

    print("\n" + "=" * 55)
    passed = sum(results)
    total = len(results)
    failed = total - passed
    print(f"  結果：{passed}/{total} 通過  |  {failed} 失敗")
    if failed == 0:
        print("  🎉 階段 3 完成！可以進入階段 4。")
    else:
        print("  ⚠️  有測試失敗，請修正後再繼續。")
    print("=" * 55)

    cleanup()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
