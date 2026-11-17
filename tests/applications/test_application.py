"""The retired in-Bot application path and historical draft boundary."""

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from gcc_agent.access.guard import GuardResult, PRIVATE_GROUP_QA_REASON
from gcc_agent.applications.handoff import APPLICATION_URL, handoff_text, make_apply_markup
from gcc_agent.common.persistence import database
from gcc_agent.common.persistence.users import get_or_create_user
from gcc_agent.common.models import Session
from gcc_agent.qa.handler import handle_general
from gcc_agent.common.persistence.conversations import create_session, get_active_session, get_or_create_session, save_session
from gcc_agent.telegram.app import handle_callback, handle_message
from gcc_agent.telegram.router import route


class ApplicationRetirementTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(database, "DB_PATH", str(Path(self.directory.name) / "test.db"))
        self.db_patch.start()
        await database.init_db()
        await get_or_create_user(123)

    async def asyncTearDown(self):
        self.db_patch.stop()
        self.directory.cleanup()

    async def _legacy_session(self):
        session = await create_session(123)
        session.mode = "application"
        session.application_draft.project_name = "Private proposal"
        session.application_draft.collection_step = 4
        session.application_draft.agent_score = 73
        session.messages = [{"role": "user", "content": "Private proposal"}]
        await save_session(session)
        async with database.connect(rows=True) as db:
            async with db.execute(
                "SELECT draft_json, messages_json FROM sessions WHERE session_id=?",
                (session.session_id,),
            ) as cursor:
                row = await cursor.fetchone()
        return session, (row["draft_json"], row["messages_json"])

    async def _assert_archived_without_rewriting(self, session, original):
        async with database.connect(rows=True) as db:
            async with db.execute(
                "SELECT mode, draft_json, messages_json FROM sessions WHERE session_id=?",
                (session.session_id,),
            ) as cursor:
                row = await cursor.fetchone()
        self.assertEqual("legacy_application_closed", row["mode"])
        self.assertEqual(original, (row["draft_json"], row["messages_json"]))
        self.assertIsNone(await get_active_session(123))
        fresh, created = await get_or_create_session(123)
        self.assertTrue(created)
        self.assertNotEqual(session.session_id, fresh.session_id)
        self.assertEqual([], fresh.get_context())
        self.assertEqual("", fresh.application_draft.project_name)

    async def test_legacy_message_closes_draft_and_never_calls_qa(self):
        session, original = await self._legacy_session()
        update = SimpleNamespace(message=SimpleNamespace(text="new answer", reply_text=AsyncMock()))
        guard = GuardResult(True, user=SimpleNamespace(user_id=123), lang="zh-TW", reason=PRIVATE_GROUP_QA_REASON)
        with patch("gcc_agent.telegram.app.run_guard", new=AsyncMock(return_value=guard)):
            with patch("gcc_agent.telegram.app.handle_general", new_callable=AsyncMock) as qa:
                await handle_message(update, SimpleNamespace())
        qa.assert_not_awaited()
        self.assertIn("沒有轉交", update.message.reply_text.await_args.args[0])
        self.assertIn(APPLICATION_URL, update.message.reply_text.await_args.args[0])
        await self._assert_archived_without_rewriting(session, original)

    async def test_formerly_submitted_general_session_is_also_isolated(self):
        session, original = await self._legacy_session()
        session.mode = "general"
        await save_session(session)
        async with database.connect(rows=True) as db:
            async with db.execute(
                "SELECT draft_json, messages_json FROM sessions WHERE session_id=?",
                (session.session_id,),
            ) as cursor:
                row = await cursor.fetchone()
        original = (row["draft_json"], row["messages_json"])
        update = SimpleNamespace(message=SimpleNamespace(text="hello", reply_text=AsyncMock()))
        guard = GuardResult(True, user=SimpleNamespace(user_id=123), lang="zh-TW")
        self.assertEqual("legacy_application", (await route(update, SimpleNamespace(), guard)).mode)
        with patch("gcc_agent.telegram.app.run_guard", new=AsyncMock(return_value=guard)):
            with patch("gcc_agent.telegram.app.handle_general", new_callable=AsyncMock) as qa:
                await handle_message(update, SimpleNamespace())
        qa.assert_not_awaited()
        await self._assert_archived_without_rewriting(session, original)

    async def test_old_apply_and_exit_buttons_only_handoff(self):
        for action in ("intent_apply", "intent_exit"):
            with self.subTest(action=action):
                session, original = await self._legacy_session()
                query = SimpleNamespace(
                    data=action, from_user=SimpleNamespace(id=123),
                    message=SimpleNamespace(reply_text=AsyncMock()), answer=AsyncMock(),
                )
                update = SimpleNamespace(callback_query=query, effective_chat=SimpleNamespace(type="private"))
                user = SimpleNamespace(user_id=123, is_blocked=False, can_use_qa=lambda: True, preferred_lang="zh-TW")
                with patch("gcc_agent.telegram.app.get_user", new=AsyncMock(return_value=user)):
                    await handle_callback(update, SimpleNamespace())
                query.answer.assert_awaited_once()
                self.assertIn("沒有轉交", query.message.reply_text.await_args.args[0])
                await self._assert_archived_without_rewriting(session, original)
                async with database.connect() as db:
                    await db.execute("DELETE FROM sessions WHERE user_id=123")
                    await db.commit()

    async def test_new_button_has_only_official_url(self):
        button = make_apply_markup("zh-TW").inline_keyboard[0][0]
        self.assertEqual(APPLICATION_URL, button.url)
        self.assertIsNone(button.callback_data)
        for lang in ("zh-TW", "zh-CN", "en"):
            self.assertIn(APPLICATION_URL, handoff_text(lang))
        with self.assertRaises(ValueError):
            make_apply_markup("en", url="https://example.com/form")

    async def test_old_button_for_ineligible_user_only_shows_public_handoff(self):
        query = SimpleNamespace(
            data="intent_apply", from_user=SimpleNamespace(id=999),
            message=SimpleNamespace(reply_text=AsyncMock()), answer=AsyncMock(),
        )
        update = SimpleNamespace(
            callback_query=query, effective_chat=SimpleNamespace(type="private"),
            effective_user=SimpleNamespace(language_code="en"),
        )
        with patch("gcc_agent.telegram.app.get_user", new=AsyncMock(return_value=None)):
            await handle_callback(update, SimpleNamespace())
        self.assertIn(APPLICATION_URL, query.message.reply_text.await_args.args[0])
        self.assertIsNone(await get_active_session(999))

    async def test_public_and_special_questions_link_to_the_matching_form_page(self):
        for question, suffix in (
            ("公共基金如何申請？", "/public"),
            ("專項基金如何申請？", "/special"),
        ):
            with self.subTest(question=question):
                update = SimpleNamespace(message=SimpleNamespace(text=question, reply_text=AsyncMock()))
                guard = SimpleNamespace(lang="zh-TW", user=SimpleNamespace(user_id=123))
                with patch("gcc_agent.qa.handler.get_session", new=AsyncMock(return_value=Session(user_id=123))):
                    with patch("gcc_agent.qa.handler.save_exchange", new_callable=AsyncMock):
                        await handle_general(update, SimpleNamespace(), guard)
                kwargs = update.message.reply_text.await_args.kwargs
                button = kwargs["reply_markup"].inline_keyboard[0][0]
                self.assertEqual(APPLICATION_URL + suffix, button.url)
                self.assertIsNone(button.callback_data)
                self.assertIn("不收集或評分", update.message.reply_text.await_args.args[0])


if __name__ == "__main__":
    unittest.main()
