"""Operator-only account changes, audit, and immediate access revocation."""

import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from gcc_agent.access.guard import run_group_qa_guard
from gcc_agent.access.handler import handle_block, handle_grant, handle_unblock
from gcc_agent.common.persistence import operator_actions, users
from gcc_agent.common.persistence import database
from gcc_agent.telegram.app import build_application


def _update(actor_id):
    message = SimpleNamespace(text="", reply_text=AsyncMock())
    actor = SimpleNamespace(id=actor_id, username=f"u{actor_id}", first_name="Test",
                            language_code="zh-hk", is_bot=False)
    return SimpleNamespace(message=message, effective_user=actor)


class OperatorManagementTests(IsolatedAsyncioTestCase):
    def test_management_commands_bind_to_designated_handlers(self):
        with patch("gcc_agent.telegram.app.settings", SimpleNamespace(
            bot_token="123456:abcdefghijklmnopqrstuvwxyzABCDEFGH"
        )):
            application = build_application()
        callbacks = {
            command: handler.callback
            for handlers in application.handlers.values()
            for handler in handlers
            for command in (getattr(handler, "commands", ()) or ())
        }
        self.assertIs(callbacks["grant"], handle_grant)
        self.assertIs(callbacks["block"], handle_block)
        self.assertIs(callbacks["unblock"], handle_unblock)

    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        database.DB_PATH = str(Path(self.temp.name) / "management.db")
        await database.init_db()
        await users.get_or_create_user(1, "operator")
        await users.get_or_create_user(2, "target")

    async def asyncTearDown(self):
        database.DB_PATH = self.original_db_path
        self.temp.cleanup()

    def _audit(self):
        with closing(sqlite3.connect(database.DB_PATH)) as db:
            return db.execute(
                "SELECT actor_user_id,target_user_id,action,result,before_state,"
                "after_state,created_at FROM operator_actions ORDER BY action_id"
            ).fetchall()

    async def test_group_member_cannot_grant_block_or_unblock(self):
        with patch("gcc_agent.access.handler.settings", SimpleNamespace(admin_user_id=1)):
            for handler, args in ((handle_grant, ["2", "ai"]),
                                  (handle_block, ["2"]),
                                  (handle_unblock, ["2"])):
                update = _update(3)
                await handler(update, SimpleNamespace(args=args))
                self.assertIn("Only the designated GCC operator", update.message.reply_text.call_args.args[0])
        target = await users.get_user(2)
        self.assertEqual((target.actor_type, target.access_level, target.is_blocked),
                         ("human", "regular", False))
        self.assertEqual(self._audit(), [])
        self.assertIsNone(await users.get_user(3))

    async def test_missing_operator_configuration_fails_closed(self):
        with patch("gcc_agent.access.handler.settings", SimpleNamespace(admin_user_id=0)):
            await handle_grant(_update(1), SimpleNamespace(args=["2", "ai"]))
        self.assertEqual((await users.get_user(2)).actor_type, "human")
        self.assertEqual(self._audit(), [])

    async def test_grant_revoke_block_unblock_are_audited(self):
        with patch("gcc_agent.access.handler.settings", SimpleNamespace(admin_user_id=1)):
            await handle_grant(_update(1), SimpleNamespace(args=["2", "ai"]))
            self.assertEqual((await users.get_user(2)).actor_type, "agent")
            await handle_grant(_update(1), SimpleNamespace(args=["2", "regular"]))
            self.assertEqual((await users.get_user(2)).actor_type, "human")
            await handle_block(_update(1), SimpleNamespace(args=["2"]))
            target = _update(2)
            denied = await run_group_qa_guard(target, SimpleNamespace())
            self.assertEqual((denied.passed, denied.reason), (False, "blocked"))
            await handle_unblock(_update(1), SimpleNamespace(args=["2"]))
            allowed = await run_group_qa_guard(_update(2), SimpleNamespace())
            self.assertTrue(allowed.passed)
        audit = self._audit()
        self.assertEqual([(r[0], r[1], r[2], r[3]) for r in audit],
                         [(1, 2, "grant", "changed"), (1, 2, "grant", "changed"),
                          (1, 2, "block", "changed"), (1, 2, "unblock", "changed")])
        self.assertEqual([(r[4], r[5]) for r in audit],
                         [("human/regular", "agent/regular"),
                          ("agent/regular", "human/regular"),
                          ("active", "blocked"), ("blocked", "active")])
        self.assertTrue(all(r[6] for r in audit))

    async def test_invalid_and_unknown_target_are_recorded_without_creating_user(self):
        with patch("gcc_agent.access.handler.settings", SimpleNamespace(admin_user_id=1)):
            await handle_grant(_update(1), SimpleNamespace(args=[]))
            await handle_block(_update(1), SimpleNamespace(args=["999"]))
        self.assertIsNone(await users.get_user(999))
        self.assertEqual([(r[1], r[2], r[3]) for r in self._audit()],
                         [(None, "grant", "invalid_request"), (999, "block", "not_found")])

    async def test_audit_failure_rolls_back_identity_change(self):
        with closing(sqlite3.connect(database.DB_PATH)) as db:
            db.execute("CREATE TRIGGER reject_audit BEFORE INSERT ON operator_actions "
                       "BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            await operator_actions.change_identity(1, 2, "agent", "regular")
        self.assertEqual((await users.get_user(2)).actor_type, "human")
