"""User, identity, email-challenge, and agent-credential persistence."""

from datetime import UTC, datetime
import hashlib
import hmac
import os
from typing import Optional

from gcc_agent.access.models import (
    ACCESS_GCC_MEMBER,
    ACCESS_LEVELS,
    ACTOR_AGENT,
    ACTOR_HUMAN,
    ACTOR_TYPES,
    USER_KIND_AI,
    USER_KIND_GCC_MEMBER,
    User,
)
from gcc_agent.common.persistence.database import connect


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _row_to_user(row) -> User:
    keys = set(row.keys())
    return User(
        user_id=row["user_id"],
        username=row["username"] or "",
        first_name=row["first_name"] or "",
        detected_lang=row["detected_lang"] or "zh-TW",
        is_group_member=bool(row["is_group_member"]),
        is_blocked=bool(row["is_blocked"]),
        actor_type=row["actor_type"] if "actor_type" in keys else ACTOR_HUMAN,
        access_level=row["access_level"] if "access_level" in keys else "regular",
        email=(row["email"] or "") if "email" in keys else "",
        email_verified_at=(row["email_verified_at"] or "") if "email_verified_at" in keys else "",
        has_agent_credential=bool(row["has_agent_credential"]) if "has_agent_credential" in keys else False,
        daily_count=row["daily_count"],
        count_reset_date=row["count_reset_date"] or "",
        total_messages=row["total_messages"],
        created_at=row["created_at"],
        last_seen_at=row["last_seen_at"],
    )


_USER_SELECT = """
SELECT u.*, EXISTS(
    SELECT 1 FROM agent_credentials c
    WHERE c.user_id = u.user_id AND c.revoked_at IS NULL
) AS has_agent_credential
FROM users u
"""


async def get_user(user_id: int) -> Optional[User]:
    async with connect(rows=True) as db:
        async with db.execute(_USER_SELECT + " WHERE u.user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
    return _row_to_user(row) if row else None


async def get_user_by_username(username: str) -> Optional[User]:
    handle = (username or "").lstrip("@").strip()
    if not handle:
        return None
    async with connect(rows=True) as db:
        async with db.execute(
            _USER_SELECT + " WHERE lower(u.username) = lower(?) LIMIT 1", (handle,)
        ) as cursor:
            row = await cursor.fetchone()
    return _row_to_user(row) if row else None


async def get_or_create_user(
    user_id: int, username: str = "", first_name: str = "", detected_lang: str = "zh-TW"
) -> tuple[User, bool]:
    user = await get_user(user_id)
    now = _utcnow().isoformat()
    if user:
        async with connect() as db:
            await db.execute(
                "UPDATE users SET last_seen_at=?, username=?, first_name=? WHERE user_id=?",
                (now, username, first_name, user_id),
            )
            await db.commit()
        user.last_seen_at = now
        return user, False
    today = _utcnow().strftime("%Y-%m-%d")
    async with connect() as db:
        await db.execute(
            """INSERT INTO users
               (user_id, username, first_name, detected_lang, actor_type, access_level,
                user_kind, count_reset_date, created_at, last_seen_at)
               VALUES (?, ?, ?, ?, 'human', 'regular', 'regular', ?, ?, ?)""",
            (user_id, username, first_name, detected_lang, today, now, now),
        )
        await db.commit()
    return (await get_user(user_id)), True


async def update_user_group_membership(user_id: int, is_member: bool) -> None:
    await _update("is_group_member", int(is_member), user_id)


async def set_user_blocked(user_id: int, blocked: bool) -> None:
    await _update("is_blocked", int(blocked), user_id)


async def update_user_lang(user_id: int, lang: str) -> None:
    await _update("detected_lang", lang, user_id)


async def _update(column: str, value, user_id: int) -> None:
    allowed = {"is_group_member", "is_blocked", "detected_lang"}
    if column not in allowed:
        raise ValueError("unsupported user field")
    async with connect() as db:
        await db.execute(f"UPDATE users SET {column}=? WHERE user_id=?", (value, user_id))
        await db.commit()


async def try_increment_daily_count(user_id: int, limit: int = 20) -> bool:
    today = _utcnow().strftime("%Y-%m-%d")
    async with connect() as db:
        cursor = await db.execute(
            """UPDATE users SET
                 daily_count=CASE WHEN count_reset_date != ? THEN 1 ELSE daily_count + 1 END,
                 count_reset_date=?, total_messages=total_messages + 1
               WHERE user_id=? AND (count_reset_date != ? OR daily_count < ?)""",
            (today, today, user_id, today, limit),
        )
        await db.commit()
        return cursor.rowcount > 0


async def set_identity(user_id: int, actor_type: str, access_level: str) -> str:
    if actor_type not in ACTOR_TYPES or access_level not in ACCESS_LEVELS:
        return "invalid_identity"
    user = await get_user(user_id)
    if not user:
        return "not_found"
    if access_level == ACCESS_GCC_MEMBER:
        if actor_type == ACTOR_HUMAN and not user.email_verified_at:
            return "verified_email_required"
        if actor_type == ACTOR_AGENT and not user.has_agent_credential:
            return "agent_credential_required"
    legacy_kind = USER_KIND_AI if actor_type == ACTOR_AGENT else access_level
    async with connect() as db:
        await db.execute(
            "UPDATE users SET actor_type=?, access_level=?, user_kind=? WHERE user_id=?",
            (actor_type, access_level, legacy_kind, user_id),
        )
        await db.commit()
    return ""


async def set_user_kind(user_id: int, kind: str) -> str:
    if kind == USER_KIND_AI:
        return await set_identity(user_id, ACTOR_AGENT, "regular")
    if kind in ("regular", USER_KIND_GCC_MEMBER):
        error = await set_identity(user_id, ACTOR_HUMAN, kind)
        return "gcc_email_required" if error == "verified_email_required" else error
    return "invalid_kind"


async def set_user_email(user_id: int, email: str) -> str:
    """Compatibility primitive: stores an address as unverified."""
    value = (email or "").strip().lower()
    try:
        async with connect() as db:
            await db.execute(
                "UPDATE users SET email=?, email_verified_at=NULL WHERE user_id=?",
                (value or None, user_id),
            )
            await db.commit()
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            return "taken"
        raise
    return ""


async def save_email_challenge(
    user_id: int, pending_email: str, code_hash: str, expires_at: str, attempts: int
) -> str:
    try:
        async with connect() as db:
            await db.execute(
                """INSERT INTO email_verifications
                   (user_id, pending_email, code_hash, expires_at, attempts_remaining, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET pending_email=excluded.pending_email,
                     code_hash=excluded.code_hash, expires_at=excluded.expires_at,
                     attempts_remaining=excluded.attempts_remaining, created_at=excluded.created_at""",
                (user_id, pending_email, code_hash, expires_at, attempts, _utcnow().isoformat()),
            )
            await db.commit()
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            return "taken"
        raise
    return ""


async def get_email_challenge(user_id: int):
    async with connect(rows=True) as db:
        async with db.execute(
            "SELECT * FROM email_verifications WHERE user_id=?", (user_id,)
        ) as cursor:
            return await cursor.fetchone()


async def fail_email_challenge(user_id: int) -> None:
    async with connect() as db:
        await db.execute(
            "UPDATE email_verifications SET attempts_remaining=attempts_remaining-1 WHERE user_id=?",
            (user_id,),
        )
        await db.execute(
            "DELETE FROM email_verifications WHERE user_id=? AND attempts_remaining <= 0",
            (user_id,),
        )
        await db.commit()


async def complete_email_challenge(user_id: int, email: str) -> None:
    async with connect() as db:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE users SET email=?, email_verified_at=? WHERE user_id=?",
            (email, _utcnow().isoformat(), user_id),
        )
        await db.execute("DELETE FROM email_verifications WHERE user_id=?", (user_id,))
        await db.commit()


def _credential_hash(raw: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.scrypt(raw.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


async def store_agent_credential(user_id: int, raw_credential: str) -> str:
    if not raw_credential or len(raw_credential) < 32:
        return "weak_credential"
    encoded = _credential_hash(raw_credential)
    async with connect() as db:
        await db.execute(
            """INSERT INTO agent_credentials(user_id, credential_hash, created_at, revoked_at)
               VALUES (?, ?, ?, NULL)
               ON CONFLICT(user_id) DO UPDATE SET credential_hash=excluded.credential_hash,
                 created_at=excluded.created_at, revoked_at=NULL""",
            (user_id, encoded, _utcnow().isoformat()),
        )
        await db.commit()
    return ""


async def verify_agent_credential(user_id: int, raw_credential: str) -> bool:
    async with connect(rows=True) as db:
        async with db.execute(
            "SELECT credential_hash FROM agent_credentials WHERE user_id=? AND revoked_at IS NULL",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
    if not row:
        return False
    try:
        _, salt_hex, expected = row["credential_hash"].split("$", 2)
        actual = _credential_hash(raw_credential, bytes.fromhex(salt_hex)).split("$", 2)[2]
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False
