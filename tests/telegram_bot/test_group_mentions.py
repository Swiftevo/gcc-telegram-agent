"""Scoped group Q&A and mention routing tests."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from gcc_agent.access.guard import GuardResult, run_group_qa_guard
from gcc_agent.common.models import Session
from gcc_agent.qa.handler import handle_general as handle_qa
from gcc_agent.telegram.app import (
    handle_callback,
    handle_group_message,
    message_mentions_bot,
    remove_bot_mentions,
    should_handle_group_message,
)


def make_update(
    chat_id: int,
    text: str,
    *,
    user_id: int = 123,
    thread_id: int = 0,
    language_code: str = "zh-TW",
):
    message = SimpleNamespace(
        text=text,
        message_thread_id=thread_id,
        reply_text=AsyncMock(),
    )
    user = SimpleNamespace(
        id=user_id,
        username="group_user",
        first_name="Group",
        language_code=language_code,
        is_bot=False,
    )
    return SimpleNamespace(
        message=message,
        effective_chat=SimpleNamespace(id=chat_id),
        effective_user=user,
    )


def make_context(username: str = "GCCpublicgoods_bot"):
    context = MagicMock()
    context.bot_data = {}
    context.bot.get_me = AsyncMock(return_value=SimpleNamespace(username=username))
    return context


def group_settings(*, enabled: bool = True, chat_id: int = -100123):
    return SimpleNamespace(group_qa_enabled=enabled, gcc_group_id=chat_id)


class GroupMentionTests(unittest.IsolatedAsyncioTestCase):
    def test_message_mentions_bot(self):
        self.assertTrue(message_mentions_bot("@GCCpublicgoods_bot 請問 GCC 是什麼？", "GCCpublicgoods_bot"))
        self.assertTrue(message_mentions_bot("hi @gccpublicgoods_bot", "GCCpublicgoods_bot"))
        self.assertFalse(message_mentions_bot("沒有 tag", "GCCpublicgoods_bot"))
        self.assertFalse(message_mentions_bot("@GCCpublicgoods_bot_extra", "GCCpublicgoods_bot"))

    def test_remove_bot_mentions_before_sending_question_to_qa(self):
        self.assertEqual(
            "請問 GCC 是什麼？",
            remove_bot_mentions(
                "@GCCpublicgoods_bot 請問 GCC 是什麼？",
                "GCCpublicgoods_bot",
            ),
        )
        self.assertEqual(
            "問題",
            remove_bot_mentions(
                "@gccpublicgoods_bot 問題 @GCCpublicgoods_bot",
                "GCCpublicgoods_bot",
            ),
        )

    async def test_group_message_requires_feature_flag_configured_chat_and_mention(self):
        with patch("gcc_agent.telegram.app.settings", group_settings()):
            self.assertTrue(
                await should_handle_group_message(
                    make_update(-100123, "@GCCpublicgoods_bot 請問如何申請？"),
                    make_context(),
                )
            )
            self.assertFalse(
                await should_handle_group_message(
                    make_update(-100123, "請問如何申請？"),
                    make_context(),
                )
            )
            self.assertFalse(
                await should_handle_group_message(
                    make_update(-100999, "@GCCpublicgoods_bot 請問如何申請？"),
                    make_context(),
                )
            )

        with patch("gcc_agent.telegram.app.settings", group_settings(enabled=False)):
            self.assertFalse(
                await should_handle_group_message(
                    make_update(-100123, "@GCCpublicgoods_bot 請問如何申請？"),
                    make_context(),
                )
            )

    async def test_group_handler_bypasses_private_router_but_only_calls_scoped_qa(self):
        update = make_update(
            -100123,
            "@GCCpublicgoods_bot 請問如何申請？",
            thread_id=77,
        )
        user = SimpleNamespace(user_id=123)
        guard = GuardResult(True, user=user, lang="zh-TW", reason="group_qa")

        with patch("gcc_agent.telegram.app.settings", group_settings()):
            with patch(
                "gcc_agent.telegram.app.run_group_qa_guard",
                new=AsyncMock(return_value=guard),
            ):
                with patch(
                    "gcc_agent.telegram.app.handle_general", new_callable=AsyncMock
                ) as handle_general:
                    await handle_group_message(update, make_context())

        handle_general.assert_awaited_once()
        args, kwargs = handle_general.await_args
        self.assertIs(args[0], update)
        self.assertEqual("請問如何申請？", kwargs["user_text_override"])
        self.assertEqual("group", kwargs["scope_type"])
        self.assertEqual(-100123, kwargs["scope_id"])
        self.assertEqual(77, kwargs["thread_id"])
        self.assertFalse(kwargs["allow_application"])

    async def test_mention_without_question_gets_prompt_and_does_not_call_qa(self):
        update = make_update(-100123, "@GCCpublicgoods_bot")
        guard = GuardResult(
            True,
            user=SimpleNamespace(user_id=123),
            lang="zh-TW",
            reason="group_qa",
        )
        with patch("gcc_agent.telegram.app.settings", group_settings()):
            with patch(
                "gcc_agent.telegram.app.run_group_qa_guard",
                new=AsyncMock(return_value=guard),
            ):
                with patch(
                    "gcc_agent.telegram.app.handle_general", new_callable=AsyncMock
                ) as handle_general:
                    await handle_group_message(update, make_context())

        handle_general.assert_not_awaited()
        update.message.reply_text.assert_awaited_once()
        self.assertIn("問題", update.message.reply_text.await_args.args[0])

    async def test_group_command_is_not_routed_to_qa(self):
        update = make_update(-100123, "@GCCpublicgoods_bot /email person@example.com")
        guard = GuardResult(
            True,
            user=SimpleNamespace(user_id=123),
            lang="zh-TW",
            reason="group_qa",
        )
        with patch("gcc_agent.telegram.app.settings", group_settings()):
            with patch(
                "gcc_agent.telegram.app.run_group_qa_guard",
                new=AsyncMock(return_value=guard),
            ):
                with patch(
                    "gcc_agent.telegram.app.handle_general", new_callable=AsyncMock
                ) as handle_general:
                    await handle_group_message(update, make_context())

        handle_general.assert_not_awaited()

    async def test_explicit_group_privacy_request_bypasses_guard_and_is_not_saved(self):
        update = make_update(-100123, "@GCCpublicgoods_bot /privacy")
        with patch("gcc_agent.telegram.app.settings", group_settings()):
            with patch(
                "gcc_agent.telegram.app.run_group_qa_guard", new_callable=AsyncMock
            ) as guard:
                with patch(
                    "gcc_agent.telegram.app.handle_general", new_callable=AsyncMock
                ) as handle_general:
                    await handle_group_message(update, make_context())

        guard.assert_not_awaited()
        handle_general.assert_not_awaited()
        update.message.reply_text.assert_awaited_once()
        self.assertIn("資料告知", update.message.reply_text.await_args.args[0])
        self.assertIn("https://www.gccofficial.org/contact", update.message.reply_text.await_args.args[0])

    async def test_group_qa_does_not_offer_application_callback(self):
        update = make_update(-100123, "@GCCpublicgoods_bot 如何申請資助？")
        guard = GuardResult(
            True,
            user=SimpleNamespace(user_id=123),
            lang="zh-TW",
            reason="group_qa",
        )
        with patch(
            "gcc_agent.qa.handler.get_session",
            new=AsyncMock(return_value=Session(user_id=123, scope_type="group", scope_id=-100123)),
        ):
            with patch(
                "gcc_agent.qa.handler.save_exchange", new_callable=AsyncMock
            ):
                await handle_qa(
                    update,
                    make_context(),
                    guard,
                    user_text_override="如何申請資助？",
                    scope_type="group",
                    scope_id=-100123,
                    allow_application=False,
                )

        self.assertIsNone(update.message.reply_text.await_args.kwargs["reply_markup"])

    async def test_group_callback_is_acknowledged_but_not_processed(self):
        query = SimpleNamespace(answer=AsyncMock())
        update = SimpleNamespace(
            callback_query=query,
            effective_chat=SimpleNamespace(type="supergroup"),
        )
        with patch(
            "gcc_agent.telegram.app.get_user", new_callable=AsyncMock
        ) as get_user:
            await handle_callback(update, make_context())

        query.answer.assert_awaited_once()
        get_user.assert_not_awaited()

    async def test_private_callback_still_reaches_private_access_check(self):
        query = SimpleNamespace(
            answer=AsyncMock(),
            from_user=SimpleNamespace(id=123),
        )
        update = SimpleNamespace(
            callback_query=query,
            effective_chat=SimpleNamespace(type="private"),
        )
        with patch(
            "gcc_agent.telegram.app.get_user",
            new=AsyncMock(return_value=None),
        ) as get_user:
            await handle_callback(update, make_context())

        query.answer.assert_awaited_once()
        get_user.assert_awaited_once_with(123)


class GroupGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_regular_human_without_email_can_use_group_qa(self):
        update = make_update(-100123, "@GCCpublicgoods_bot 問題")
        regular_user = SimpleNamespace(
            user_id=123,
            detected_lang="zh-TW",
            is_blocked=False,
            access_level="regular",
            email="",
            email_verified_at="",
        )
        with patch(
            "gcc_agent.access.guard.users.get_or_create_user",
            new=AsyncMock(return_value=(regular_user, True)),
        ):
            with patch(
                "gcc_agent.access.guard.users.try_increment_daily_count",
                new=AsyncMock(return_value=True),
            ) as increment:
                result = await run_group_qa_guard(update, make_context())

        self.assertTrue(result.passed)
        self.assertEqual("group_qa", result.reason)
        increment.assert_awaited_once_with(123, 20)
        update.message.reply_text.assert_not_awaited()

    async def test_blocked_group_user_is_silently_denied(self):
        update = make_update(-100123, "@GCCpublicgoods_bot 問題")
        blocked_user = SimpleNamespace(
            user_id=123,
            detected_lang="zh-TW",
            is_blocked=True,
        )
        with patch(
            "gcc_agent.access.guard.users.get_or_create_user",
            new=AsyncMock(return_value=(blocked_user, True)),
        ):
            with patch(
                "gcc_agent.access.guard.users.try_increment_daily_count",
                new_callable=AsyncMock,
            ) as increment:
                result = await run_group_qa_guard(update, make_context())

        self.assertFalse(result.passed)
        self.assertEqual("blocked", result.reason)
        increment.assert_not_awaited()
        update.message.reply_text.assert_not_awaited()

    async def test_group_user_still_obeys_daily_limit(self):
        update = make_update(
            -100123,
            "@GCCpublicgoods_bot question",
            language_code="en",
        )
        regular_user = SimpleNamespace(
            user_id=123,
            detected_lang="en",
            is_blocked=False,
        )
        with patch(
            "gcc_agent.access.guard.users.get_or_create_user",
            new=AsyncMock(return_value=(regular_user, True)),
        ):
            with patch(
                "gcc_agent.access.guard.users.try_increment_daily_count",
                new=AsyncMock(return_value=False),
            ):
                result = await run_group_qa_guard(update, make_context())

        self.assertFalse(result.passed)
        self.assertEqual("rate_limited", result.reason)
        update.message.reply_text.assert_awaited_once()
        self.assertIn("20", update.message.reply_text.await_args.args[0])


if __name__ == "__main__":
    unittest.main()
