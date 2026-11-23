"""Small, fail-closed retention cleanup for the live SQLite database."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import json

from gcc_agent.common.persistence.database import connect
from gcc_agent.config import settings


SESSION_DAYS = 30
INACTIVE_USER_DAYS = 90

_EMPTY_DRAFT = {
    "project_name": "",
    "fund_type": "unknown",
    "proposal_link": "",
    "executive_summary": "",
    "collection_step": 0,
    "agent_score": -1,
    "agent_notes": "",
    "submitted_at": None,
}


@dataclass(frozen=True)
class RetentionReport:
    """Aggregate counts only; never include IDs, addresses, or message text."""

    mode: str
    sessions: int = 0
    messages: int = 0
    users: int = 0
    email_users: int = 0
    challenges: int = 0
    revoked_credentials: int = 0
    active_credentials: int = 0
    held_special_emails: int = 0
    held_legacy_sessions: int = 0
    held_invalid_timestamps: int = 0


def _utc_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _has_legacy_application(mode: str, raw_draft: str) -> bool:
    """Treat unexpected draft data or modes as protected, including invalid JSON."""
    if mode != "general":
        return True
    try:
        draft = json.loads(raw_draft or "{}")
    except (TypeError, ValueError):
        return True
    if not isinstance(draft, dict):
        return True
    return any(value != _EMPTY_DRAFT.get(key, object()) for key, value in draft.items())


async def run_retention_cleanup(
    *,
    apply: bool = False,
    now: datetime | None = None,
    operator_user_id: int | None = None,
) -> RetentionReport:
    """Preview or atomically apply the approved live-data retention policy."""
    current = now or datetime.now(UTC)
    if current.tzinfo is not None:
        current = current.astimezone(UTC).replace(tzinfo=None)
    session_cutoff = current - timedelta(days=SESSION_DAYS)
    user_cutoff = current - timedelta(days=INACTIVE_USER_DAYS)
    operator = settings.admin_user_id if operator_user_id is None else operator_user_id
    counts = {
        "mode": "apply" if apply else "dry-run",
        "sessions": 0,
        "messages": 0,
        "users": 0,
        "email_users": 0,
        "challenges": 0,
        "revoked_credentials": 0,
        "active_credentials": 0,
        "held_special_emails": 0,
        "held_legacy_sessions": 0,
        "held_invalid_timestamps": 0,
    }

    async with connect(readonly=not apply) as db:
        await db.execute("PRAGMA busy_timeout = 5000")
        await db.execute("BEGIN IMMEDIATE" if apply else "BEGIN")
        try:
            async with db.execute(
                "SELECT session_id, mode, draft_json, last_active FROM sessions"
            ) as cursor:
                sessions = await cursor.fetchall()
            expired_ids = []
            for session_id, mode, raw_draft, last_active in sessions:
                timestamp = _utc_time(last_active)
                if timestamp is None:
                    counts["held_invalid_timestamps"] += 1
                elif timestamp < session_cutoff:
                    if _has_legacy_application(mode, raw_draft):
                        counts["held_legacy_sessions"] += 1
                    else:
                        expired_ids.append(session_id)

            counts["sessions"] = len(expired_ids)
            for session_id in expired_ids:
                async with db.execute(
                    "SELECT COUNT(*) FROM messages WHERE session_id=?", (session_id,)
                ) as cursor:
                    counts["messages"] += (await cursor.fetchone())[0]
                if apply:
                    await db.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
                    await db.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))

            async with db.execute(
                "SELECT user_id, actor_type, access_level, user_kind, is_blocked, "
                "last_seen_at, email, email_verified_at FROM users"
            ) as cursor:
                user_rows = await cursor.fetchall()
            async with db.execute("SELECT user_id, revoked_at FROM agent_credentials") as cursor:
                credential_rows = await cursor.fetchall()
            credential_users = {
                user_id for user_id, revoked_at in credential_rows if revoked_at is None
            }
            counts["active_credentials"] = sum(
                revoked_at is None for _, revoked_at in credential_rows
            )
            counts["revoked_credentials"] = len(credential_rows) - counts["active_credentials"]
            if apply:
                await db.execute("DELETE FROM agent_credentials WHERE revoked_at IS NOT NULL")

            async with db.execute("SELECT COUNT(*) FROM email_verifications") as cursor:
                counts["challenges"] = (await cursor.fetchone())[0]
            if apply:
                await db.execute("DELETE FROM email_verifications")

            # Preview the state after eligible sessions would be removed.
            async with db.execute("SELECT user_id, session_id FROM sessions") as cursor:
                remaining_session_users = {
                    user_id
                    for user_id, session_id in await cursor.fetchall()
                    if session_id not in expired_ids
                }

            for (
                user_id,
                actor_type,
                access_level,
                user_kind,
                is_blocked,
                last_seen_at,
                email,
                email_verified_at,
            ) in user_rows:
                regular = (
                    actor_type == "human"
                    and access_level == "regular"
                    and user_kind == "regular"
                )
                has_email = bool(email or email_verified_at)
                if has_email:
                    if regular:
                        counts["email_users"] += 1
                        if apply:
                            await db.execute(
                                "UPDATE users SET email=NULL, email_verified_at=NULL "
                                "WHERE user_id=?",
                                (user_id,),
                            )
                    else:
                        counts["held_special_emails"] += 1

                last_seen = _utc_time(last_seen_at)
                if last_seen is None:
                    counts["held_invalid_timestamps"] += 1
                    continue
                if not (
                    regular
                    and not is_blocked
                    and user_id != operator
                    and user_id not in credential_users
                    and user_id not in remaining_session_users
                    and last_seen < user_cutoff
                ):
                    continue
                counts["users"] += 1
                if apply:
                    await db.execute("DELETE FROM users WHERE user_id=?", (user_id,))

            if apply:
                await db.commit()
            else:
                await db.rollback()
        except BaseException:
            await db.rollback()
            raise
    return RetentionReport(**counts)


if __name__ == "__main__":
    # Manual operator preview; applying changes requires the scheduled rollout mode.
    print(json.dumps(asdict(asyncio.run(run_retention_cleanup())), sort_keys=True))
