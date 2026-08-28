"""
test_db.py — 階段 1 完成標準測試
執行：python test_db.py
全部通過才算階段 1 完成。
"""

import asyncio
import os
import sys

# 測試用獨立 DB，不污染正式資料
os.environ["DB_PATH"] = "test_gcc_agent.db"

from db import (
    complete_email_challenge,
    get_or_create_session,
    get_or_create_user,
    get_stats,
    get_user,
    init_db,
    save_exchange,
    save_session,
    set_user_blocked,
    set_user_email,
    set_user_kind,
    try_increment_daily_count,
    update_user_group_membership,
)
from models import USER_KIND_AI, USER_KIND_GCC_MEMBER, USER_KIND_REGULAR, AgentValues, ApplicationDraft, Message, Session, User

PASS = "✅"
FAIL = "❌"
results = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    msg = f"  {status} {name}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    results.append(condition)
    if not condition:
        print(f"       ↳ FAILED: {detail}")


# ── Test 1: models.py ─────────────────────────────────────────────────────────

def test_models():
    print("\n[ 1 ] models.py 資料結構測試")

    # User
    u = User(user_id=123456, username="testuser", first_name="Test")
    check("User 建立成功", u.user_id == 123456)
    check("User 預設身份 regular", u.user_kind == USER_KIND_REGULAR)
    check("User 預設不能問答（無郵箱）", not u.can_use_qa())
    u.user_kind = USER_KIND_GCC_MEMBER
    check("gcc_member 無郵箱不能問答", not u.can_use_qa())
    u.email = "member@example.com"
    check("gcc_member 未驗證郵箱不能問答", not u.can_use_qa())
    u.email_verified_at = "2026-01-01T00:00:00"
    check("gcc_member 已驗證郵箱可以問答", u.can_use_qa())
    u.user_kind = USER_KIND_AI
    check("ai 即使有郵箱也不能問答", not u.can_use_qa())
    check("User is_rate_limited（初始應為 False）", not u.is_rate_limited())

    u.daily_count = 20
    from datetime import datetime
    u.count_reset_date = datetime.utcnow().strftime("%Y-%m-%d")
    check("User is_rate_limited（20 條應為 True）", u.is_rate_limited())

    u.daily_count = 5
    u.count_reset_date = "2000-01-01"  # 舊日期
    check("User 舊日期不算超限", not u.is_rate_limited())

    reset = u.reset_if_new_day()
    check("User reset_if_new_day 返回 True（舊日期）", reset)
    check("User reset 後 daily_count = 0", u.daily_count == 0)

    # ApplicationDraft
    d = ApplicationDraft()
    check("Draft 初始 is_complete() = False", not d.is_complete())
    check("Draft 初始 collection_step = 0", d.collection_step == 0)

    q = d.next_question("zh-TW")
    check("Draft 步驟 0 問題不為空", len(q) > 0, q[:30])

    check("Draft parse_fund_type '公共'", d.parse_fund_type("公共") == "public")
    check("Draft parse_fund_type '专项'", d.parse_fund_type("专项") == "special")
    check("Draft parse_fund_type 'public'", d.parse_fund_type("public") == "public")
    check("Draft parse_fund_type '不知道'", d.parse_fund_type("不知道") == "unknown")

    d.project_name = "TestProject"
    d.fund_type = "public"
    d.executive_summary = "解決公共問題的開源工具"
    d.collection_step = 4
    check("Draft 填完四步 is_complete() = True", d.is_complete())

    # Session
    s = Session(user_id=123456)
    check("Session 建立有 session_id", len(s.session_id) > 0)
    check("Session 初始 mode = general", s.mode == "general")
    check("Session 初始 is_expired() = False", not s.is_expired())

    s.add_message("user", "你好")
    s.add_message("assistant", "你好！")
    check("Session add_message 後長度 = 2", len(s.messages) == 2)
    check("Session get_context 返回全部（< 20）", len(s.get_context()) == 2)

    # 超過 20 條測試
    for i in range(25):
        s.add_message("user", f"msg {i}")
    check("Session get_context 最多 20 條", len(s.get_context()) == 20)

    # Message
    m = Message(session_id=s.session_id, user_id=123456, role="user", content="test")
    check("Message 建立有 message_id", len(m.message_id) > 0)
    check("Message 預設 tokens_used = 0", m.tokens_used == 0)
    check("Message 預設 link_served = False", not m.link_served)

    # AgentValues
    av = AgentValues(version="1.0.0", mission_statement="GCC 使命")
    check("AgentValues 建立成功", av.version == "1.0.0")


# ── Test 2: db.py ─────────────────────────────────────────────────────────────

async def test_db():
    print("\n[ 2 ] db.py 資料庫測試")
    cleanup()

    await init_db()
    check("init_db() 完成", True)

    # 建立新用戶
    user, created = await get_or_create_user(
        user_id=999001,
        username="testuser_db",
        first_name="DB Test",
        detected_lang="zh-TW",
    )
    check("get_or_create_user 建立新用戶", created)
    check("新用戶 user_id 正確", user.user_id == 999001)

    # 重複取得同一用戶
    user2, created2 = await get_or_create_user(user_id=999001)
    check("get_or_create_user 重複不建立新的", not created2)
    check("重複取得同一 user_id", user2.user_id == 999001)

    # get_user
    fetched = await get_user(999001)
    check("get_user 取得存在的用戶", fetched is not None)
    check("get_user 不存在返回 None", await get_user(0) is None)

    # 群組成員更新
    await update_user_group_membership(999001, True)
    updated = await get_user(999001)
    check("update_user_group_membership True", updated.is_group_member)

    # 封鎖
    await set_user_blocked(999001, True)
    blocked = await get_user(999001)
    check("set_user_blocked True", blocked.is_blocked)
    await set_user_blocked(999001, False)

    err = await set_user_kind(999001, USER_KIND_GCC_MEMBER)
    check("無郵箱不能設 gcc_member", err == "gcc_email_required")
    err = await set_user_email(999001, "alpha@example.com")
    check("綁定郵箱成功", err == "")
    member = await get_user(999001)
    check("郵箱已寫入", member.email == "alpha@example.com")
    check("直接綁定的郵箱未驗證", not member.email_verified_at)
    await complete_email_challenge(999001, "alpha@example.com")
    err = await set_user_kind(999001, USER_KIND_GCC_MEMBER)
    check("已驗證郵箱可設 gcc_member", err == "")
    member = await get_user(999001)
    check("身份為 gcc_member", member.user_kind == USER_KIND_GCC_MEMBER)
    check("可以問答", member.can_use_qa())

    other, _ = await get_or_create_user(user_id=999002, username="other")
    err = await set_user_email(999002, "alpha@example.com")
    check("郵箱不可重複綁定", err == "taken")
    err = await set_user_kind(999002, USER_KIND_AI)
    check("可設為 ai", err == "")
    ai_user = await get_user(999002)
    check("ai 不能問答", not ai_user.can_use_qa())

    # Rate limit 計數
    ok1 = await try_increment_daily_count(999001)
    check("try_increment_daily_count 第一次通過", ok1)
    ok2 = await try_increment_daily_count(999001)
    check("try_increment_daily_count 第二次通過", ok2)

    # Session 建立
    session, is_new = await get_or_create_session(999001)
    check("get_or_create_session 建立新 Session", is_new)
    check("Session user_id 正確", session.user_id == 999001)

    # Session 重複取得
    session2, is_new2 = await get_or_create_session(999001)
    check("get_or_create_session 取得現有 Session", not is_new2)
    check("Session ID 相同", session.session_id == session2.session_id)

    # 儲存訊息到 Session
    session.add_message("user", "我想申請資助")
    session.add_message("assistant", "請告訴我你的項目名稱。")
    await save_session(session)
    check("save_session 不拋錯", True)

    # 重新載入 Session 確認持久化
    session3, _ = await get_or_create_session(999001)
    check("Session 訊息持久化（reload 後仍有 2 條）", len(session3.messages) == 2)
    check("Session 訊息內容正確", session3.messages[0]["content"] == "我想申請資助")

    # 儲存訊息記錄
    await save_exchange(
        session=session,
        user_id=999001,
        user_text="測試問題",
        assistant_text="測試回覆",
        tokens_used=42,
        link_served=False,
    )
    check("save_exchange 不拋錯", True)

    # 連結回應記錄
    await save_exchange(
        session=session,
        user_id=999001,
        user_text="GCC 是什麼",
        assistant_text="https://www.gccofficial.org/about",
        tokens_used=0,
        link_served=True,
    )
    check("save_exchange link_served=True 不拋錯", True)

    # ApplicationDraft 持久化
    session.mode = "application"
    session.application_draft.project_name = "TestProject"
    session.application_draft.fund_type = "public"
    session.application_draft.executive_summary = "解決公共問題"
    session.application_draft.collection_step = 4
    session.application_draft.agent_score = 75
    session.application_draft.agent_notes = "使命契合度高"
    await save_session(session)

    session4, _ = await get_or_create_session(999001)
    check("ApplicationDraft 持久化：project_name", session4.application_draft.project_name == "TestProject")
    check("ApplicationDraft 持久化：agent_score", session4.application_draft.agent_score == 75)
    check("ApplicationDraft is_complete()", session4.application_draft.is_complete())

    # Stats
    stats = await get_stats()
    check("get_stats 返回 dict", isinstance(stats, dict))
    check("get_stats 包含 total_users", "total_users" in stats)
    check("get_stats total_users >= 1", stats["total_users"] >= 1)


# ── Test 3: values.yaml 載入（如果存在）──────────────────────────────────────

def test_values_yaml():
    print("\n[ 3 ] values.yaml 格式測試")
    if not os.path.exists("values.yaml"):
        print("  ⚠️  values.yaml 不存在，跳過此測試（部署時必須存在）")
        return

    import yaml
    try:
        with open("values.yaml") as f:
            data = yaml.safe_load(f)
        check("values.yaml 解析成功", True)
        check("包含 version", "version" in data)
        check("包含 mission_statement", "mission_statement" in data)
        check("包含 priority_themes（列表）", isinstance(data.get("priority_themes"), list))
        check("包含 rejection_criteria（列表）", isinstance(data.get("rejection_criteria"), list))
        check("包含 screening_rubric（字典）", isinstance(data.get("screening_rubric"), dict))
        check("包含 tone_guidelines", "tone_guidelines" in data)
        check("包含 gcc_summary", "gcc_summary" in data)
        rubric = data.get("screening_rubric", {})
        check("screening_rubric 包含 mission_fit", "mission_fit" in rubric)
        check("screening_rubric 總分 = 100",
              sum(int(v) for v in rubric.values() if str(v).isdigit()) == 100)
    except Exception as e:
        check(f"values.yaml 解析失敗：{e}", False)


# ── 清理測試 DB ───────────────────────────────────────────────────────────────

def cleanup():
    if os.path.exists("test_gcc_agent.db"):
        os.remove("test_gcc_agent.db")


# ── 執行 ──────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 55)
    print("  GCC Telegram Agent — 階段 1 測試")
    print("=" * 55)

    test_models()
    await test_db()
    test_values_yaml()

    print("\n" + "=" * 55)
    passed = sum(results)
    total = len(results)
    failed = total - passed
    print(f"  結果：{passed}/{total} 通過  |  {failed} 失敗")
    if failed == 0:
        print("  🎉 階段 1 完成！可以進入階段 2。")
    else:
        print("  ⚠️  有測試失敗，請修正後再繼續。")
    print("=" * 55)

    cleanup()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
