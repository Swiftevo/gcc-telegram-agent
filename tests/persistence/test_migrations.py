import os
import sqlite3
import tempfile
import unittest

from gcc_agent.common.persistence import database, users


class MigrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        database.DB_PATH = self.path

    async def asyncTearDown(self):
        os.remove(self.path)

    async def test_old_user_kind_values_are_mapped_idempotently(self):
        with sqlite3.connect(self.path) as db:
            db.executescript(
                """CREATE TABLE users (
                    user_id INTEGER PRIMARY KEY, username TEXT DEFAULT '',
                    first_name TEXT DEFAULT '', detected_lang TEXT DEFAULT 'zh-TW',
                    is_group_member INTEGER DEFAULT 0, is_blocked INTEGER DEFAULT 0,
                    user_kind TEXT DEFAULT 'regular', email TEXT,
                    daily_count INTEGER DEFAULT 0, count_reset_date TEXT DEFAULT '',
                    total_messages INTEGER DEFAULT 0, created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL);
                """
            )
            for user_id, kind in ((1, "regular"), (2, "gcc_member"), (3, "ai")):
                db.execute(
                    "INSERT INTO users(user_id,user_kind,created_at,last_seen_at) VALUES (?,?,?,?)",
                    (user_id, kind, "2020-01-01", "2020-01-01"),
                )
        await database.init_db()
        await database.init_db()
        regular, member, agent = [await users.get_user(i) for i in (1, 2, 3)]
        self.assertEqual(("human", "regular"), (regular.actor_type, regular.access_level))
        self.assertEqual(("human", "gcc_member"), (member.actor_type, member.access_level))
        self.assertEqual(("agent", "regular"), (agent.actor_type, agent.access_level))
        self.assertFalse(member.can_use_qa())
        with sqlite3.connect(self.path) as db:
            self.assertEqual(3, db.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0])
