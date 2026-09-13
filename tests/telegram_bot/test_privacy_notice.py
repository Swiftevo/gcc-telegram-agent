"""Minimum privacy notice behavior and content boundaries."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from gcc_agent.privacy import CONTACT_URL, is_privacy_request, privacy_notice
from gcc_agent.telegram.app import build_application, handle_privacy


def make_update(language_code: str):
    return SimpleNamespace(
        message=SimpleNamespace(reply_text=AsyncMock()),
        effective_user=SimpleNamespace(language_code=language_code),
    )


class PrivacyNoticeTests(unittest.IsolatedAsyncioTestCase):
    def test_private_privacy_command_is_registered(self):
        fake_settings = SimpleNamespace(
            bot_token="123456:abcdefghijklmnopqrstuvwxyzABCDEFGH"
        )
        with patch("gcc_agent.telegram.app.settings", fake_settings):
            application = build_application()

        commands = {
            command
            for handlers in application.handlers.values()
            for handler in handlers
            for command in (getattr(handler, "commands", ()) or ())
        }
        self.assertIn("privacy", commands)

    def test_notices_cover_current_storage_recipients_and_contact(self):
        for lang in ("zh-TW", "zh-CN", "en"):
            with self.subTest(lang=lang):
                notice = privacy_notice(lang)
                for required in ("Telegram", "Fly.io", "SQLite", "OpenAI", "SMTP", CONTACT_URL):
                    self.assertIn(required, notice)
                self.assertIn("20", notice)
                self.assertLessEqual(len(notice), 4096)

    def test_notices_disclose_unsettled_retention_without_promising_a_period(self):
        self.assertIn("沒有自動刪除期限", privacy_notice("zh-TW"))
        self.assertIn("郵箱驗證目前暫停", privacy_notice("zh-TW"))
        self.assertIn("没有自动删除期限", privacy_notice("zh-CN"))
        self.assertIn("邮箱验证目前暂停", privacy_notice("zh-CN"))
        self.assertIn("no automatic deletion period", privacy_notice("en"))
        self.assertIn("Email verification is paused", privacy_notice("en"))

    def test_unknown_language_falls_back_to_traditional_chinese(self):
        self.assertEqual(privacy_notice("zh-TW"), privacy_notice("fr"))

    def test_short_explicit_privacy_requests_only(self):
        for value in ("/privacy", "privacy?", "私隱說明", "隐私说明。", "data notice"):
            with self.subTest(value=value):
                self.assertTrue(is_privacy_request(value))
        self.assertFalse(is_privacy_request("GCC 如何保護資助申請的私隱？"))

    async def test_private_command_uses_locale_without_persisting_or_authenticating(self):
        update = make_update("en-US")

        await handle_privacy(update, None)

        update.message.reply_text.assert_awaited_once_with(privacy_notice("en"))


if __name__ == "__main__":
    unittest.main()
