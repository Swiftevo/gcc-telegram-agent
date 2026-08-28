"""Shared SQLite connection and versioned migration runner."""

from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)
DB_PATH = os.getenv("DB_PATH", "gcc_agent.db")
MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


@asynccontextmanager
async def connect(*, rows: bool = False):
    db = await aiosqlite.connect(DB_PATH)
    if rows:
        db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
    finally:
        await db.close()


async def _columns(db: aiosqlite.Connection, table: str) -> set[str]:
    async with db.execute(f"PRAGMA table_info({table})") as cursor:
        return {row[1] for row in await cursor.fetchall()}


async def _migration_002_identity(db: aiosqlite.Connection) -> None:
    columns = await _columns(db, "users")
    additions = {
        "actor_type": "TEXT NOT NULL DEFAULT 'human'",
        "access_level": "TEXT NOT NULL DEFAULT 'regular'",
        "email_verified_at": "TEXT",
    }
    for name, definition in additions.items():
        if name not in columns:
            await db.execute(f"ALTER TABLE users ADD COLUMN {name} {definition}")
    if "user_kind" in columns:
        await db.execute(
            """UPDATE users
               SET actor_type = CASE user_kind WHEN 'ai' THEN 'agent' ELSE 'human' END,
                   access_level = CASE user_kind WHEN 'gcc_member' THEN 'gcc_member' ELSE 'regular' END"""
        )


async def _migration_003_credentials(db: aiosqlite.Connection) -> None:
    await db.executescript(
        """
        CREATE TABLE IF NOT EXISTS email_verifications (
            user_id INTEGER PRIMARY KEY,
            pending_email TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            attempts_remaining INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_email_verifications_pending
            ON email_verifications(pending_email);
        CREATE TABLE IF NOT EXISTS agent_credentials (
            user_id INTEGER PRIMARY KEY,
            credential_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            revoked_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        );
        """
    )


async def init_db() -> None:
    async with connect() as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        async with db.execute("SELECT version FROM schema_migrations") as cursor:
            applied = {row[0] for row in await cursor.fetchall()}

        if 1 not in applied:
            sql = (MIGRATIONS_DIR / "001_initial.sql").read_text(encoding="utf-8")
            await db.executescript(sql)
            await db.execute("INSERT INTO schema_migrations(version) VALUES (1)")
        if 2 not in applied:
            await _migration_002_identity(db)
            await db.execute("INSERT INTO schema_migrations(version) VALUES (2)")
        if 3 not in applied:
            await _migration_003_credentials(db)
            await db.execute("INSERT INTO schema_migrations(version) VALUES (3)")
        await db.commit()
    logger.info("database initialized path=%s", DB_PATH)
