"""User-facing email verification is shelved without deleting compatibility code."""

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from gcc_agent.access.handler import handle_email_shelved, handle_whoami
from gcc_agent.access.messages import welcome_text
from gcc_agent.telegram.app import build_application


ROOT = Path(__file__).resolve().parents[2]


def make_update(language_code: str = "zh-TW", text: str = "/email secret@example.com"):
    return SimpleNamespace(
        message=SimpleNamespace(text=text, reply_text=AsyncMock()),
        effective_user=SimpleNamespace(language_code=language_code),
    )


class ShelvedEmailTests(unittest.IsolatedAsyncioTestCase):
    def test_welcome_has_no_email_onboarding_and_points_to_group_and_privacy(self):
        for lang in ("zh-TW", "zh-CN", "en"):
            with self.subTest(lang=lang):
                text = welcome_text(lang)
                self.assertNotIn("/email", text)
                self.assertNotIn("/verify", text)
                self.assertIn("mention", text)
                self.assertIn("/privacy", text)

    def test_legacy_commands_are_bound_only_to_non_persisting_handler(self):
        fake_settings = SimpleNamespace(
            bot_token="123456:abcdefghijklmnopqrstuvwxyzABCDEFGH"
        )
        with patch("gcc_agent.telegram.app.settings", fake_settings):
            application = build_application()

        callbacks = {}
        for handlers in application.handlers.values():
            for handler in handlers:
                for command in getattr(handler, "commands", ()) or ():
                    callbacks[command] = getattr(handler, "callback", None)

        self.assertIs(handle_email_shelved, callbacks["email"])
        self.assertIs(handle_email_shelved, callbacks["verify"])

    async def test_legacy_command_does_not_load_user_or_email_service(self):
        with patch(
            "gcc_agent.access.handler._current_user", new_callable=AsyncMock
        ) as current_user:
            with patch("gcc_agent.access.handler._service") as service:
                replies = {}
                for locale, expected in (
                    ("zh-TW", "郵箱驗證目前暫停"),
                    ("zh-CN", "邮箱验证目前暂停"),
                    ("en-US", "Email verification is currently paused"),
                ):
                    update = make_update(locale)
                    await handle_email_shelved(update, None)
                    update.message.reply_text.assert_awaited_once()
                    replies[locale] = update.message.reply_text.await_args.args[0]

        current_user.assert_not_awaited()
        service.assert_not_called()
        for locale, expected in (
            ("zh-TW", "郵箱驗證目前暫停"),
            ("zh-CN", "邮箱验证目前暂停"),
            ("en-US", "Email verification is currently paused"),
        ):
            self.assertIn(expected, replies[locale])
            self.assertNotIn("secret@example.com", replies[locale])

    async def test_whoami_no_longer_displays_legacy_email_fields(self):
        update = make_update(text="/whoami")
        user = SimpleNamespace(
            user_id=42,
            actor_type="human",
            access_level="regular",
            email="legacy@example.com",
            email_verified_at="2026-01-01T00:00:00+00:00",
            can_use_qa=lambda: False,
        )
        with patch(
            "gcc_agent.access.handler._current_user",
            new=AsyncMock(return_value=user),
        ):
            await handle_whoami(update, None)

        reply = update.message.reply_text.await_args.args[0]
        self.assertNotIn("legacy@example.com", reply)
        self.assertNotIn("email", reply.lower())
        self.assertIn("access_level", reply)
        self.assertNotIn("`", reply)
        self.assertNotIn("parse_mode", update.message.reply_text.await_args.kwargs)

    def test_public_setup_no_longer_invites_email_or_smtp_configuration(self):
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        for key in ("EMAIL_VERIFICATION_SECRET", "SMTP_HOST", "SMTP_PASSWORD"):
            self.assertNotIn(key, env_example)

        for readme in ("README.md", "README.zh-TW.md", "README.en.md"):
            text = (ROOT / readme).read_text(encoding="utf-8")
            with self.subTest(readme=readme):
                self.assertNotIn("/email you@example.com", text)
                self.assertNotIn("SMTP_HOST=", text)


if __name__ == "__main__":
    unittest.main()
