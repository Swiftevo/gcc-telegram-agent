"""Session and message repositories."""

import json
import logging
from typing import Optional

from gcc_agent.applications.models import ApplicationDraft
from gcc_agent.common.models import Message, Session
from gcc_agent.common.persistence.database import connect

logger = logging.getLogger(__name__)


def _row_to_session(row) -> Session:
    keys = set(row.keys())
    draft_data = json.loads(row["draft_json"] or "{}")
    return Session(
        session_id=row["session_id"],
        user_id=row["user_id"],
        scope_type=row["scope_type"] if "scope_type" in keys else "private",
        scope_id=row["scope_id"] if "scope_id" in keys else 0,
        thread_id=row["thread_id"] if "thread_id" in keys else 0,
        mode=row["mode"],
        messages=json.loads(row["messages_json"] or "[]"),
        application_draft=ApplicationDraft(
            project_name=draft_data.get("project_name", ""),
            fund_type=draft_data.get("fund_type", "unknown"),
            proposal_link=draft_data.get("proposal_link", ""),
            executive_summary=draft_data.get("executive_summary", ""),
            collection_step=draft_data.get("collection_step", 0),
            agent_score=draft_data.get("agent_score", -1),
            agent_notes=draft_data.get("agent_notes", ""),
            submitted_at=draft_data.get("submitted_at"),
        ),
        created_at=row["created_at"],
        last_active=row["last_active"],
    )


async def get_active_session(
    user_id: int,
    *,
    scope_type: str = "private",
    scope_id: int = 0,
    thread_id: int = 0,
) -> Optional[Session]:
    async with connect(rows=True) as db:
        async with db.execute(
            """SELECT * FROM sessions
               WHERE user_id=? AND scope_type=? AND scope_id=? AND thread_id=?
               ORDER BY last_active DESC LIMIT 1""",
            (user_id, scope_type, scope_id, thread_id),
        ) as cursor:
            row = await cursor.fetchone()
    if not row:
        return None
    session = _row_to_session(row)
    return None if session.is_expired() else session


async def create_session(
    user_id: int,
    *,
    scope_type: str = "private",
    scope_id: int = 0,
    thread_id: int = 0,
) -> Session:
    session = Session(
        user_id=user_id,
        scope_type=scope_type,
        scope_id=scope_id,
        thread_id=thread_id,
    )
    await save_session(session)
    return session


async def get_or_create_session(
    user_id: int,
    *,
    scope_type: str = "private",
    scope_id: int = 0,
    thread_id: int = 0,
) -> tuple[Session, bool]:
    session = await get_active_session(
        user_id,
        scope_type=scope_type,
        scope_id=scope_id,
        thread_id=thread_id,
    )
    if session:
        return session, False
    return (
        await create_session(
            user_id,
            scope_type=scope_type,
            scope_id=scope_id,
            thread_id=thread_id,
        ),
        True,
    )


async def save_session(session: Session) -> None:
    draft = session.application_draft
    draft_json = json.dumps(
        {
            "project_name": draft.project_name,
            "fund_type": draft.fund_type,
            "proposal_link": draft.proposal_link,
            "executive_summary": draft.executive_summary,
            "collection_step": draft.collection_step,
            "agent_score": draft.agent_score,
            "agent_notes": draft.agent_notes,
            "submitted_at": draft.submitted_at,
        },
        ensure_ascii=False,
    )
    async with connect() as db:
        await db.execute(
            """INSERT INTO sessions
               (session_id,user_id,scope_type,scope_id,thread_id,mode,messages_json,
                draft_json,created_at,last_active)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(session_id) DO UPDATE SET mode=excluded.mode,
                 messages_json=excluded.messages_json, draft_json=excluded.draft_json,
                 last_active=excluded.last_active""",
            (
                session.session_id,
                session.user_id,
                session.scope_type,
                session.scope_id,
                session.thread_id,
                session.mode,
                json.dumps(session.messages, ensure_ascii=False),
                draft_json,
                session.created_at,
                session.last_active,
            ),
        )
        await db.commit()


async def save_message(message: Message) -> None:
    async with connect() as db:
        await _insert_message(db, message)
        await db.commit()


async def _insert_message(db, message: Message) -> None:
    await db.execute(
        """INSERT INTO messages
           (message_id,session_id,user_id,role,content,tokens_used,link_served,created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            message.message_id,
            message.session_id,
            message.user_id,
            message.role,
            message.content,
            message.tokens_used,
            int(message.link_served),
            message.created_at,
        ),
    )


async def save_exchange(
    session: Session,
    user_id: int,
    user_text: str,
    assistant_text: str,
    tokens_used: int = 0,
    link_served: bool = False,
) -> None:
    user_message = Message(
        session_id=session.session_id, user_id=user_id, role="user", content=user_text
    )
    assistant_message = Message(
        session_id=session.session_id,
        user_id=user_id,
        role="assistant",
        content=assistant_text,
        tokens_used=tokens_used,
        link_served=link_served,
    )
    async with connect() as db:
        await _insert_message(db, user_message)
        await _insert_message(db, assistant_message)
        await db.commit()
