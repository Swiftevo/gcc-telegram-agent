"""Transactional operator changes and their minimal SQLite audit trail."""

from gcc_agent.access.models import (
    ACCESS_GCC_MEMBER,
    ACCESS_LEVELS,
    ACTOR_AGENT,
    ACTOR_HUMAN,
    ACTOR_TYPES,
    USER_KIND_AI,
)
from gcc_agent.common.persistence.database import connect


async def _record(db, actor_id: int, target_id: int | None, action: str,
                  result: str, before: str | None = None,
                  after: str | None = None) -> None:
    await db.execute(
        """INSERT INTO operator_actions
           (actor_user_id,target_user_id,action,result,before_state,after_state)
           VALUES (?,?,?,?,?,?)""",
        (actor_id, target_id, action, result, before, after),
    )


async def record_invalid_request(actor_id: int, action: str) -> None:
    """Record an authorized command with invalid arguments, without raw text."""
    async with connect() as db:
        await _record(db, actor_id, None, action, "invalid_request")
        await db.commit()


async def change_identity(
    actor_id: int, target_id: int, actor_type: str, access_level: str
) -> str:
    """Apply an operator identity change and audit the outcome atomically."""
    if actor_type not in ACTOR_TYPES or access_level not in ACCESS_LEVELS:
        raise ValueError("invalid identity")
    async with connect(rows=True) as db:
        await db.execute("BEGIN IMMEDIATE")
        async with db.execute(
            """SELECT u.actor_type,u.access_level,u.email_verified_at,
                      EXISTS(SELECT 1 FROM agent_credentials c
                             WHERE c.user_id=u.user_id AND c.revoked_at IS NULL)
                      AS has_agent_credential
               FROM users u WHERE u.user_id=?""",
            (target_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            await _record(db, actor_id, target_id, "grant", "not_found")
            await db.commit()
            return "not_found"

        before = f"{row['actor_type']}/{row['access_level']}"
        after = f"{actor_type}/{access_level}"
        if access_level == ACCESS_GCC_MEMBER and actor_type == ACTOR_HUMAN and not row["email_verified_at"]:
            result = "verified_email_required"
        elif access_level == ACCESS_GCC_MEMBER and actor_type == ACTOR_AGENT and not row["has_agent_credential"]:
            result = "agent_credential_required"
        elif before == after:
            result = "unchanged"
        else:
            result = "changed"
            legacy_kind = USER_KIND_AI if actor_type == ACTOR_AGENT else access_level
            await db.execute(
                "UPDATE users SET actor_type=?,access_level=?,user_kind=? WHERE user_id=?",
                (actor_type, access_level, legacy_kind, target_id),
            )
        await _record(db, actor_id, target_id, "grant", result, before,
                      after if result in ("changed", "unchanged") else before)
        await db.commit()
        return "" if result in ("changed", "unchanged") else result


async def change_block(actor_id: int, target_id: int, blocked: bool) -> str:
    """Block or unblock a user and audit the outcome atomically."""
    action = "block" if blocked else "unblock"
    async with connect(rows=True) as db:
        await db.execute("BEGIN IMMEDIATE")
        async with db.execute(
            "SELECT is_blocked FROM users WHERE user_id=?", (target_id,)
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            await _record(db, actor_id, target_id, action, "not_found")
            await db.commit()
            return "not_found"
        before = "blocked" if row["is_blocked"] else "active"
        after = "blocked" if blocked else "active"
        if before == after:
            result = "unchanged"
        else:
            result = "changed"
            await db.execute(
                "UPDATE users SET is_blocked=? WHERE user_id=?",
                (int(blocked), target_id),
            )
        await _record(db, actor_id, target_id, action, result, before, after)
        await db.commit()
        return ""
