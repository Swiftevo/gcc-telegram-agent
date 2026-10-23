"""Manual language selection and persistence behavior."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from gcc_agent.access.guard import run_group_qa_guard
from gcc_agent.common.models import Session
from gcc_agent.qa.prompts import build_messages
from gcc_agent.telegram.app import build_application, handle_callback, handle_language
from gcc_agent.telegram.language import normalize_language


def make_private_update(language_code: str = "en"):
    user = SimpleNamespace(
        id=123,
        username="member",
        first_name="Member",
        language_code=language_code,
    )
    return SimpleNamespace(
        effective_user=user,
        effective_chat=SimpleNamespace(type="private"),
        message=SimpleNamespace(reply_text=AsyncMock()),
    )


class LanguageSelectionTests(unittest.IsolatedAsyncioTestCase):
    def test_language_commands_are_registered(self):
        with patch(
            "gcc_agent.telegram.app.settings",
            SimpleNamespace(bot_token="123456:abcdefghijklmnopqrstuvwxyzABCDEFGH"),
        ):
            application = build_application()
        commands = {
            command
            for handlers in application.handlers.values()
            for handler in handlers
            for command in (getattr(handler, "commands", ()) or ())
        }
        self.assertTrue({"language", "lang"} <= commands)

    def test_simplified_chinese_aliases(self):
        for value in ("zh-CN", "zh-hans", "cn", "简体", "简体中文"):
            with self.subTest(value=value):
                self.assertEqual("zh-CN", normalize_language(value))

    def test_ai_prompt_requires_simplified_chinese(self):
        messages = build_messages("Please introduce GCC", Session(user_id=123), "zh-CN")
        system_text = "\n".join(
            message["content"] for message in messages if message["role"] == "system"
        )
        self.assertIn("Always answer in Simplified Chinese", system_text)

    async def test_command_persists_simplified_chinese(self):
        update = make_private_update()
        user = SimpleNamespace(user_id=123, preferred_lang="")
        with patch(
            "gcc_agent.telegram.app.ensure_user",
            new=AsyncMock(return_value=user),
        ):
            with patch(
                "gcc_agent.telegram.app.users.update_user_preferred_lang",
                new_callable=AsyncMock,
            ) as save:
                await handle_language(update, SimpleNamespace(args=["简体中文"]))

        save.assert_awaited_once_with(123, "zh-CN")
        self.assertIn("简体中文", update.message.reply_text.await_args.args[0])

    async def test_button_persists_simplified_chinese_without_access_gate(self):
        query = SimpleNamespace(
            data="language:zh-CN",
            answer=AsyncMock(),
            message=SimpleNamespace(reply_text=AsyncMock()),
            from_user=SimpleNamespace(id=123),
        )
        update = SimpleNamespace(
            callback_query=query,
            effective_chat=SimpleNamespace(type="private"),
            effective_user=SimpleNamespace(
                id=123,
                username="member",
                first_name="Member",
                language_code="en",
            ),
        )
        with patch(
            "gcc_agent.telegram.app.ensure_user",
            new=AsyncMock(return_value=SimpleNamespace(user_id=123)),
        ):
            with patch(
                "gcc_agent.telegram.app.users.update_user_preferred_lang",
                new_callable=AsyncMock,
            ) as save:
                with patch(
                    "gcc_agent.telegram.app.get_user", new_callable=AsyncMock
                ) as access_lookup:
                    await handle_callback(update, MagicMock())

        query.answer.assert_awaited_once()
        save.assert_awaited_once_with(123, "zh-CN")
        access_lookup.assert_not_awaited()
        self.assertIn("简体中文", query.message.reply_text.await_args.args[0])

    async def test_guard_prefers_saved_language_over_telegram_locale(self):
        update = make_private_update("en")
        user = SimpleNamespace(
            user_id=123,
            detected_lang="en",
            preferred_lang="zh-CN",
            is_blocked=False,
        )
        with patch(
            "gcc_agent.access.guard.users.get_or_create_user",
            new=AsyncMock(return_value=(user, False)),
        ):
            with patch(
                "gcc_agent.access.guard.users.try_increment_daily_count",
                new=AsyncMock(return_value=True),
            ):
                result = await run_group_qa_guard(update, MagicMock())

        self.assertTrue(result.passed)
        self.assertEqual("zh-CN", result.lang)


if __name__ == "__main__":
    unittest.main()
