"""
db/db.py — GCC Telegram Agent SQLite 資料庫操作
所有 DB 讀寫都在此集中，不散落在 handlers 裡。
使用 aiosqlite 進行非同步操作，配合 python-telegram-bot 的 async 架構。
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

import aiosqlite

from models import ApplicationDraft, Message, Session, User

logger = logging.getLogger(__name__)

# DB 檔案路徑。Fly.io 部署時改為 /data/gcc_agent.db（持久化磁碟）
DB_PATH = os.getenv("DB_PATH", "gcc_agent.db")


# ── Schema ────────────────────────────────────────────────────────────────────

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id          INTEGER PRIMARY KEY,
    username         TEXT    DEFAULT '',
    first_name       TEXT    DEFAULT '',
    detected_lang    TEXT    DEFAULT 'zh-TW',
    is_group_member  INTEGER DEFAULT 0,
    is_blocked       INTEGER DEFAULT 0,
    daily_count      INTEGER DEFAULT 0,
    count_reset_date TEXT    DEFAULT '',
    total_messages   INTEGER DEFAULT 0,
    created_at       TEXT    NOT NULL,
    last_seen_at     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id         TEXT    PRIMARY KEY,
    user_id            INTEGER NOT NULL,
    mode               TEXT    DEFAULT 'general',
    messages_json      TEXT    DEFAULT '[]',
    draft_json         TEXT    DEFAULT '{}',
    created_at         TEXT    NOT NULL,
    last_active        TEXT    NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS messages (
    message_id   TEXT    PRIMARY KEY,
    session_id   TEXT    NOT NULL,
    user_id      INTEGER NOT NULL,
    role         TEXT    NOT NULL,
    content      TEXT    NOT NULL,
    tokens_used  INTEGER DEFAULT 0,
    link_served  INTEGER DEFAULT 0,
    created_at   TEXT    NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (user_id)    REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id    ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active);
CREATE INDEX IF NOT EXISTS idx_messages_session_id  ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id     ON messages(user_id);
"""


# ── 初始化 ────────────────────────────────────────────────────────────────────

async def init_db() -> None:
    """建立資料庫和所有 table（Bot 啟動時呼叫一次）"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(CREATE_TABLES_SQL)
        await db.commit()
    logger.info(f"DB 初始化完成：{DB_PATH}")


# ── User CRUD ─────────────────────────────────────────────────────────────────

async def get_user(user_id: int) -> Optional[User]:
    """從 DB 取得用戶，不存在返回 None"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_user(row)


async def get_or_create_user(
    user_id: int,
    username: str = "",
    first_name: str = "",
    detected_lang: str = "zh-TW",
) -> tuple[User, bool]:
    """
    取得用戶，不存在則自動建立。
    返回 (user, created)，created=True 表示這是新用戶。
    """
    user = await get_user(user_id)
    if user is not None:
        # 更新 last_seen 和可能變動的欄位
        await update_user_last_seen(user_id, username, first_name)
        user.last_seen_at = datetime.utcnow().isoformat()
        return user, False

    # 新用戶
    now = datetime.utcnow().isoformat()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    new_user = User(
        user_id=user_id,
        username=username,
        first_name=first_name,
        detected_lang=detected_lang,
        count_reset_date=today,
        created_at=now,
        last_seen_at=now,
    )
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO users
               (user_id, username, first_name, detected_lang, is_group_member,
                is_blocked, daily_count, count_reset_date, total_messages,
                created_at, last_seen_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                new_user.user_id, new_user.username, new_user.first_name,
                new_user.detected_lang, int(new_user.is_group_member),
                int(new_user.is_blocked), new_user.daily_count,
                new_user.count_reset_date, new_user.total_messages,
                new_user.created_at, new_user.last_seen_at,
            ),
        )
        await db.commit()
    logger.info(f"新用戶建立：{user_id} (@{username})")
    return new_user, True


async def update_user_last_seen(
    user_id: int, username: str = "", first_name: str = ""
) -> None:
    """更新用戶最後上線時間和顯示名稱"""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE users
               SET last_seen_at = ?, username = ?, first_name = ?
               WHERE user_id = ?""",
            (now, username, first_name, user_id),
        )
        await db.commit()


async def update_user_group_membership(user_id: int, is_member: bool) -> None:
    """更新群組成員驗證狀態"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_group_member = ? WHERE user_id = ?",
            (int(is_member), user_id),
        )
        await db.commit()


async def try_increment_daily_count(user_id: int, limit: int = 20) -> bool:
    """
    原子化檢查並增加每日訊息計數，同時處理跨日重置。
    回傳 True 代表更新成功（未達今日上限）；False 代表已達上限。
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    async with aiosqlite.connect(DB_PATH) as db:
        # 核心邏輯：
        # 如果日期不是今天 (跨日了) -> 強制設為 1，並更新日期
        # 如果日期是今天 -> count + 1
        # WHERE 條件：只有在「跨日」或「未達上限」時才允許執行這段 UPDATE
        cursor = await db.execute(
            """
            UPDATE users 
            SET 
                daily_count = CASE 
                    WHEN count_reset_date != ? THEN 1 
                    ELSE daily_count + 1 
                END,
                count_reset_date = ?,
                total_messages = total_messages + 1
            WHERE user_id = ? 
              AND (count_reset_date != ? OR daily_count < ?)
            """,
            (today, today, user_id, today, limit)
        )
        await db.commit()
        
        # rowcount > 0 表示成功寫入（即通過檢查）
        return cursor.rowcount > 0


async def set_user_blocked(user_id: int, blocked: bool) -> None:
    """管理員封鎖/解封用戶"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET is_blocked = ? WHERE user_id = ?",
            (int(blocked), user_id),
        )
        await db.commit()


async def update_user_lang(user_id: int, lang: str) -> None:
    """更新用戶語言偏好"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET detected_lang = ? WHERE user_id = ?",
            (lang, user_id),
        )
        await db.commit()


# ── Session CRUD ──────────────────────────────────────────────────────────────

async def get_active_session(user_id: int) -> Optional[Session]:
    """
    取得用戶最近的活躍 Session（30 分鐘內）。
    若不存在或已過期，返回 None。
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM sessions
               WHERE user_id = ?
               ORDER BY last_active DESC
               LIMIT 1""",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            session = _row_to_session(row)
            if session.is_expired():
                return None
            return session


async def create_session(user_id: int) -> Session:
    """建立新 Session"""
    session = Session(user_id=user_id)
    await _upsert_session(session)
    logger.debug(f"新 Session：{session.session_id} (user={user_id})")
    return session


async def get_or_create_session(user_id: int) -> tuple[Session, bool]:
    """
    取得活躍 Session，不存在或已過期則建立新的。
    返回 (session, is_new)。
    """
    session = await get_active_session(user_id)
    if session is not None:
        return session, False
    session = await create_session(user_id)
    return session, True


async def save_session(session: Session) -> None:
    """儲存 Session 狀態（訊息、mode、草稿）到 DB"""
    await _upsert_session(session)


async def _upsert_session(session: Session) -> None:
    """內部：INSERT OR REPLACE session"""
    messages_json = json.dumps(session.messages, ensure_ascii=False)
    draft_json = json.dumps(
        {
            "project_name":      session.application_draft.project_name,
            "fund_type":         session.application_draft.fund_type,
            "proposal_link":     session.application_draft.proposal_link,
            "executive_summary": session.application_draft.executive_summary,
            "collection_step":   session.application_draft.collection_step,
            "agent_score":       session.application_draft.agent_score,
            "agent_notes":       session.application_draft.agent_notes,
            "submitted_at":      session.application_draft.submitted_at,
        },
        ensure_ascii=False,
    )
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO sessions
               (session_id, user_id, mode, messages_json, draft_json,
                created_at, last_active)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session.session_id, session.user_id, session.mode,
                messages_json, draft_json,
                session.created_at, session.last_active,
            ),
        )
        await db.commit()


# ── Message CRUD ──────────────────────────────────────────────────────────────

async def save_message(msg: Message) -> None:
    """持久化一條訊息記錄到 DB"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO messages
               (message_id, session_id, user_id, role, content,
                tokens_used, link_served, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                msg.message_id, msg.session_id, msg.user_id,
                msg.role, msg.content, msg.tokens_used,
                int(msg.link_served), msg.created_at,
            ),
        )
        await db.commit()


async def save_exchange(
    session: Session,
    user_id: int,
    user_text: str,
    assistant_text: str,
    tokens_used: int = 0,
    link_served: bool = False,
) -> None:
    """
    一次儲存一問一答（用戶訊息 + 助手回覆）。
    大部分 handler 呼叫這個，而不是兩次 save_message。
    """
    user_msg = Message(
        session_id=session.session_id,
        user_id=user_id,
        role="user",
        content=user_text,
    )
    assistant_msg = Message(
        session_id=session.session_id,
        user_id=user_id,
        role="assistant",
        content=assistant_text,
        tokens_used=tokens_used,
        link_served=link_served,
    )
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO messages
               (message_id, session_id, user_id, role, content,
                tokens_used, link_served, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                user_msg.message_id, user_msg.session_id, user_msg.user_id,
                user_msg.role, user_msg.content, 0, 0, user_msg.created_at,
            ),
        )
        await db.execute(
            """INSERT INTO messages
               (message_id, session_id, user_id, role, content,
                tokens_used, link_served, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                assistant_msg.message_id, assistant_msg.session_id,
                assistant_msg.user_id, assistant_msg.role, assistant_msg.content,
                assistant_msg.tokens_used, int(assistant_msg.link_served),
                assistant_msg.created_at,
            ),
        )
        await db.commit()


# ── Stats（管理員用）──────────────────────────────────────────────────────────

async def get_stats() -> dict:
    """
    取得 Bot 使用統計，供 /status 指令使用。
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("SELECT COUNT(*) as n FROM users") as c:
            total_users = (await c.fetchone())["n"]

        async with db.execute(
            "SELECT COUNT(*) as n FROM users WHERE count_reset_date = ? AND daily_count > 0",
            (today,),
        ) as c:
            active_today = (await c.fetchone())["n"]

        async with db.execute(
            "SELECT COUNT(*) as n FROM messages WHERE created_at LIKE ?",
            (f"{today}%",),
        ) as c:
            messages_today = (await c.fetchone())["n"]

        async with db.execute(
            "SELECT COUNT(*) as n FROM messages WHERE role = 'assistant' AND link_served = 0"
            " AND created_at LIKE ?",
            (f"{today}%",),
        ) as c:
            ai_calls_today = (await c.fetchone())["n"]

        async with db.execute(
            "SELECT COALESCE(SUM(tokens_used), 0) as n FROM messages WHERE created_at LIKE ?",
            (f"{today}%",),
        ) as c:
            tokens_today = (await c.fetchone())["n"]

        async with db.execute(
            """SELECT COUNT(*) as n FROM sessions
               WHERE draft_json LIKE '%\"collection_step\": 3%'
               AND created_at LIKE ?""",
            (f"{today}%",),
        ) as c:
            applications_today = (await c.fetchone())["n"]

    return {
        "total_users": total_users,
        "active_today": active_today,
        "messages_today": messages_today,
        "ai_calls_today": ai_calls_today,
        "tokens_today": tokens_today,
        "applications_today": applications_today,
    }


# ── 內部轉換 helpers ──────────────────────────────────────────────────────────

def _row_to_user(row: aiosqlite.Row) -> User:
    return User(
        user_id=row["user_id"],
        username=row["username"] or "",
        first_name=row["first_name"] or "",
        detected_lang=row["detected_lang"] or "zh-TW",
        is_group_member=bool(row["is_group_member"]),
        is_blocked=bool(row["is_blocked"]),
        daily_count=row["daily_count"],
        count_reset_date=row["count_reset_date"] or "",
        total_messages=row["total_messages"],
        created_at=row["created_at"],
        last_seen_at=row["last_seen_at"],
    )


def _row_to_session(row: aiosqlite.Row) -> Session:
    messages = json.loads(row["messages_json"] or "[]")
    draft_data = json.loads(row["draft_json"] or "{}")
    draft = ApplicationDraft(
        project_name=      draft_data.get("project_name", ""),
        fund_type=         draft_data.get("fund_type", "unknown"),
        proposal_link=     draft_data.get("proposal_link", ""),
        executive_summary= draft_data.get("executive_summary", ""),
        collection_step=   draft_data.get("collection_step", 0),
        agent_score=       draft_data.get("agent_score", -1),
        agent_notes=       draft_data.get("agent_notes", ""),
        submitted_at=      draft_data.get("submitted_at"),
    )
    return Session(
        session_id=row["session_id"],
        user_id=row["user_id"],
        mode=row["mode"],
        messages=messages,
        application_draft=draft,
        created_at=row["created_at"],
        last_active=row["last_active"],
    )