"""Group mention routing tests."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from gcc_agent.telegram.app import (
    handle_group_message,
    message_mentions_bot,
    should_handle_group_message,
)


def make_update(chat_id: int, text: str):
    message = MagicMock()
    message.text = text

    update = MagicMock()
    update.message = message
    update.effective_chat = SimpleNamespace(id=chat_id)
    return update


def make_context(username: str = "GCCpublicgoods_bot"):
    context = MagicMock()
    context.bot_data = {}
    context.bot.get_me = AsyncMock(return_value=SimpleNamespace(username=username))
    return context


class GroupMentionTests(unittest.IsolatedAsyncioTestCase):
    def test_message_mentions_bot(self):
        self.assertTrue(message_mentions_bot("@GCCpublicgoods_bot 請問 GCC 是什麼？", "GCCpublicgoods_bot"))
        self.assertTrue(message_mentions_bot("hi @gccpublicgoods_bot", "GCCpublicgoods_bot"))
        self.assertFalse(message_mentions_bot("沒有 tag", "GCCpublicgoods_bot"))
        self.assertFalse(message_mentions_bot("@GCCpublicgoods_bot_extra", "GCCpublicgoods_bot"))

    async def test_group_message_requires_configured_chat_and_mention(self):
        with patch("gcc_agent.telegram.app.settings", SimpleNamespace(gcc_group_id=-100123)):
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

    async def test_group_handler_only_delegates_when_allowed(self):
        with patch("gcc_agent.telegram.app.settings", SimpleNamespace(gcc_group_id=-100123)):
            with patch("gcc_agent.telegram.app.handle_message", new_callable=AsyncMock) as handle_message:
                await handle_group_message(
                    make_update(-100123, "@GCCpublicgoods_bot 請問如何申請？"),
                    make_context(),
                )
                self.assertEqual(handle_message.await_count, 1)

                await handle_group_message(
                    make_update(-100123, "請問如何申請？"),
                    make_context(),
                )
                self.assertEqual(handle_message.await_count, 1)


if __name__ == "__main__":
    unittest.main()
