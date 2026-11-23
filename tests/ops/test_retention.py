"""Retention boundaries against an isolated SQLite database."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from gcc_agent.common.persistence import database, users
from gcc_agent.ops import runtime
from gcc_agent.ops.retention import run_retention_cleanup


NOW = datetime(2026, 11, 23, 12, tzinfo=UTC)


def timestamp(days_ago: int) -> str:
    return (NOW - timedelta(days=days_ago)).replace(tzinfo=None).isoformat()


class RetentionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = str(Path(self.directory.name) / "retention.db")
        self.path_patch = patch.object(database, "DB_PATH", self.path)
        self.path_patch.start()
        await database.init_db()

    async def asyncTearDown(self):
        self.path_patch.stop()
        self.directory.cleanup()

    async def user(self, user_id: int, *, age: int = 1, **fields):
        await users.get_or_create_user(user_id, f"user-{user_id}")
        async with database.connect() as db:
            await db.execute(
                "UPDATE users SET last_seen_at=? WHERE user_id=?",
                (timestamp(age), user_id),
            )
            for key, value in fields.items():
                await db.execute(
                    f"UPDATE users SET {key}=? WHERE user_id=?", (value, user_id)
                )
            await db.commit()

    async def session(
        self, session_id: str, user_id: int, *, age: int, mode: str = "general",
        draft: str = "{}", messages: int = 1,
    ):
        async with database.connect() as db:
            await db.execute(
                "INSERT INTO sessions (session_id,user_id,mode,messages_json,draft_json,"
                "created_at,last_active) VALUES (?,?,?,?,?,?,?)",
                (session_id, user_id, mode, '[{"content":"session text"}]',
                 draft, timestamp(age), timestamp(age)),
            )
            for number in range(messages):
                await db.execute(
                    "INSERT INTO messages (message_id,session_id,user_id,role,content,"
                    "created_at) VALUES (?,?,?,?,?,?)",
                    (f"{session_id}-{number}", session_id, user_id, "user",
                     "message text", timestamp(age)),
                )
            await db.commit()

    async def count(self, table: str) -> int:
        async with database.connect() as db:
            async with db.execute(f"SELECT COUNT(*) FROM {table}") as cursor:
                return (await cursor.fetchone())[0]

    async def test_preview_apply_and_repeat_protect_legacy_and_recent_sessions(self):
        await self.user(1)
        await self.session("old", 1, age=31, messages=2)
        await self.session("new", 1, age=29)
        await self.session("boundary", 1, age=30)
        await self.session("draft", 1, age=31, draft='{"project_name":"proposal"}')
        await self.session("closed", 1, age=31, mode="legacy_application_closed")
        await self.session("invalid", 1, age=31, draft="not-json")
        await self.session("bad-date", 1, age=31)
        async with database.connect() as db:
            await db.execute(
                "UPDATE sessions SET last_active='invalid' WHERE session_id='bad-date'"
            )
            await db.commit()

        preview = await run_retention_cleanup(now=NOW)
        self.assertEqual("dry-run", preview.mode)
        self.assertEqual((1, 2), (preview.sessions, preview.messages))
        self.assertEqual(3, preview.held_legacy_sessions)
        self.assertEqual(1, preview.held_invalid_timestamps)
        self.assertEqual(7, await self.count("sessions"))
        self.assertEqual(8, await self.count("messages"))

        applied = await run_retention_cleanup(apply=True, now=NOW)
        self.assertEqual((1, 2), (applied.sessions, applied.messages))
        self.assertEqual(6, await self.count("sessions"))
        self.assertEqual(6, await self.count("messages"))
        second = await run_retention_cleanup(apply=True, now=NOW)
        self.assertEqual((0, 0), (second.sessions, second.messages))

    async def test_user_and_email_cleanup_preserves_blocked_managed_and_operator(self):
        await self.user(10, age=91, email="old@example.test", email_verified_at=timestamp(95))
        await self.user(11, age=91, is_blocked=1, email="blocked@example.test")
        await self.user(
            12, age=91, access_level="gcc_member", user_kind="gcc_member",
            email="managed@example.test", email_verified_at=timestamp(95),
        )
        await self.user(13, age=91)
        await self.user(14, age=91)
        await self.user(15, age=91)
        await self.session("recent", 15, age=1)
        await self.user(16, age=91)
        async with database.connect() as db:
            for user_id in (10, 12):
                await db.execute(
                    "INSERT INTO email_verifications "
                    "(user_id,pending_email,code_hash,expires_at,attempts_remaining,created_at) "
                    "VALUES (?,?,?,?,?,?)",
                    (user_id, f"pending-{user_id}@example.test", "hash", timestamp(1),
                     3, timestamp(2)),
                )
            for user_id, revoked_at in ((14, None), (16, timestamp(2))):
                await db.execute(
                    "INSERT INTO agent_credentials "
                    "(user_id,credential_hash,created_at,revoked_at) VALUES (?,?,?,?)",
                    (user_id, "hash", timestamp(100), revoked_at),
                )
            await db.commit()

        preview = await run_retention_cleanup(now=NOW, operator_user_id=13)
        self.assertEqual(2, preview.users)
        self.assertEqual(2, preview.email_users)
        self.assertEqual(1, preview.held_special_emails)
        self.assertEqual(2, preview.challenges)
        self.assertEqual((1, 1), (preview.active_credentials, preview.revoked_credentials))
        self.assertEqual(7, await self.count("users"))

        await run_retention_cleanup(apply=True, now=NOW, operator_user_id=13)
        self.assertEqual(5, await self.count("users"))
        self.assertEqual(0, await self.count("email_verifications"))
        self.assertEqual(1, await self.count("agent_credentials"))
        self.assertIsNone(await users.get_user(10))
        self.assertIsNone(await users.get_user(16))
        self.assertIsNotNone(await users.get_user(13))
        self.assertIsNotNone(await users.get_user(14))
        self.assertIsNotNone(await users.get_user(15))
        self.assertEqual("", (await users.get_user(11)).email)
        self.assertEqual("managed@example.test", (await users.get_user(12)).email)

    async def test_failure_rolls_back_all_deletions(self):
        await self.user(20, age=91, email="rollback@example.test")
        await self.session("old", 20, age=31)
        async with database.connect() as db:
            await db.execute(
                "CREATE TRIGGER fail_session_delete BEFORE DELETE ON sessions "
                "BEGIN SELECT RAISE(ABORT, 'simulated failure'); END"
            )
            await db.commit()

        with self.assertRaises(Exception):
            await run_retention_cleanup(apply=True, now=NOW)
        self.assertEqual(1, await self.count("users"))
        self.assertEqual(1, await self.count("sessions"))
        self.assertEqual(1, await self.count("messages"))
        self.assertEqual("rollback@example.test", (await users.get_user(20)).email)

    async def test_legacy_session_also_protects_inactive_user(self):
        await self.user(30, age=100)
        await self.session(
            "legacy", 30, age=100, draft='{"agent_score":75}',
        )

        report = await run_retention_cleanup(apply=True, now=NOW)
        self.assertEqual(1, report.held_legacy_sessions)
        self.assertEqual((0, 0), (report.sessions, report.users))
        self.assertIsNotNone(await users.get_user(30))
        self.assertEqual(1, await self.count("messages"))

    async def test_preview_does_not_create_a_missing_database(self):
        missing = str(Path(self.directory.name) / "missing.db")
        with patch.object(database, "DB_PATH", missing):
            with self.assertRaises(Exception):
                await run_retention_cleanup(now=NOW)
        self.assertFalse(Path(missing).exists())


class RetentionSchedulingTests(unittest.IsolatedAsyncioTestCase):
    async def test_schedule_is_off_by_default_and_only_started_for_explicit_mode(self):
        application = SimpleNamespace(bot=SimpleNamespace())
        for mode in ("off", "dry-run", "apply"):
            with self.subTest(mode=mode), patch.object(
                runtime, "settings", SimpleNamespace(retention_cleanup_mode=mode)
            ), patch.object(
                runtime, "check_database_readiness", AsyncMock(return_value=True)
            ), patch.object(runtime, "OperationsServer") as server_type:
                server_type.return_value.stop = AsyncMock()
                state = await runtime.start_operations(
                    application, listen="127.0.0.1", port=8080, upstream_port=8081
                )
                self.assertEqual(mode != "off", state.retention_task is not None)
                await runtime.stop_operations(application)
                server_type.return_value.stop.assert_awaited_once()

    async def test_invalid_mode_fails_before_server_starts(self):
        with patch.object(
            runtime, "settings", SimpleNamespace(retention_cleanup_mode="unexpected")
        ), patch.object(runtime, "OperationsServer") as server_type:
            with self.assertRaises(ValueError):
                await runtime.start_operations(
                    SimpleNamespace(bot=SimpleNamespace()),
                    listen="127.0.0.1", port=8080, upstream_port=8081,
                )
            server_type.assert_not_called()


if __name__ == "__main__":
    unittest.main()
