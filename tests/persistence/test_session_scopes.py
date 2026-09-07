"""Conversation session isolation tests."""

import os
import tempfile
import unittest

from gcc_agent.common.persistence import conversations, database, users


class SessionScopeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        database.DB_PATH = self.path
        await database.init_db()
        await users.get_or_create_user(501, "scoped-user")
        await users.get_or_create_user(502, "other-user")

    async def asyncTearDown(self):
        os.remove(self.path)

    async def test_private_group_user_and_topic_sessions_are_distinct(self):
        private, _ = await conversations.get_or_create_session(501)
        group, _ = await conversations.get_or_create_session(
            501, scope_type="group", scope_id=-100123
        )
        other_group, _ = await conversations.get_or_create_session(
            501, scope_type="group", scope_id=-100999
        )
        topic, _ = await conversations.get_or_create_session(
            501, scope_type="group", scope_id=-100123, thread_id=77
        )
        other_user, _ = await conversations.get_or_create_session(
            502, scope_type="group", scope_id=-100123
        )

        session_ids = {
            private.session_id,
            group.session_id,
            other_group.session_id,
            topic.session_id,
            other_user.session_id,
        }
        self.assertEqual(5, len(session_ids))
        self.assertEqual("private", private.scope_type)
        self.assertEqual(
            ("group", -100123, 77),
            (topic.scope_type, topic.scope_id, topic.thread_id),
        )

    async def test_group_history_never_appears_in_private_session(self):
        group, _ = await conversations.get_or_create_session(
            501, scope_type="group", scope_id=-100123
        )
        group.add_message("user", "public group question")
        group.add_message("assistant", "public group answer")
        await conversations.save_session(group)

        private, _ = await conversations.get_or_create_session(501)
        self.assertEqual([], private.messages)

        loaded_group, is_new = await conversations.get_or_create_session(
            501, scope_type="group", scope_id=-100123
        )
        self.assertFalse(is_new)
        self.assertEqual(
            "public group question", loaded_group.messages[0]["content"]
        )

    async def test_private_application_mode_never_routes_into_group_session(self):
        private, _ = await conversations.get_or_create_session(501)
        private.mode = "application"
        private.application_draft.project_name = "Private draft"
        await conversations.save_session(private)

        group, _ = await conversations.get_or_create_session(
            501, scope_type="group", scope_id=-100123
        )
        self.assertEqual("general", group.mode)
        self.assertEqual("", group.application_draft.project_name)
