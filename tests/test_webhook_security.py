"""Tests for authenticated Telegram webhook configuration."""

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from telegram import Update

from gcc_agent.telegram import app as telegram_app


class WebhookConfigurationTests(unittest.TestCase):
    def test_webhook_requires_strong_telegram_compatible_secret(self) -> None:
        invalid_secrets = (
            "",
            "too-short",
            "x" * 31,
            "x" * 31 + "!",
            "x" * 257,
        )

        for secret in invalid_secrets:
            with self.subTest(secret_length=len(secret)):
                with self.assertRaisesRegex(ValueError, "WEBHOOK_SECRET_TOKEN"):
                    telegram_app.validate_webhook_configuration(
                        "https://example.fly.dev/webhook",
                        secret,
                    )

    def test_polling_does_not_require_webhook_secret(self) -> None:
        telegram_app.validate_webhook_configuration("", "")

    @patch.object(telegram_app, "setup_logging")
    @patch.object(telegram_app, "build_application")
    def test_run_passes_secret_to_webhook_server_and_telegram(
        self,
        build_application: MagicMock,
        _setup_logging: MagicMock,
    ) -> None:
        application = build_application.return_value
        secret = "secure_webhook_token_with_32_chars"
        webhook_settings = SimpleNamespace(
            webhook_url="https://example.fly.dev/webhook",
            webhook_listen="0.0.0.0",
            webhook_secret_token=secret,
            port=8080,
        )

        with patch.object(telegram_app, "settings", webhook_settings):
            telegram_app.run()

        application.run_webhook.assert_called_once_with(
            listen="0.0.0.0",
            port=8080,
            webhook_url="https://example.fly.dev/webhook",
            url_path="/webhook",
            secret_token=secret,
        )
        application.run_polling.assert_not_called()

    @patch.object(telegram_app, "setup_logging")
    @patch.object(telegram_app, "build_application")
    def test_run_fails_before_building_app_when_secret_is_missing(
        self,
        build_application: MagicMock,
        _setup_logging: MagicMock,
    ) -> None:
        webhook_settings = SimpleNamespace(
            webhook_url="https://example.fly.dev/webhook",
            webhook_listen="0.0.0.0",
            webhook_secret_token="",
            port=8080,
        )

        with patch.object(telegram_app, "settings", webhook_settings):
            with self.assertRaisesRegex(ValueError, "WEBHOOK_SECRET_TOKEN"):
                telegram_app.run()

        build_application.assert_not_called()

    @patch.object(telegram_app, "setup_logging")
    @patch.object(telegram_app, "build_application")
    def test_polling_mode_still_uses_all_updates(
        self,
        build_application: MagicMock,
        _setup_logging: MagicMock,
    ) -> None:
        application = build_application.return_value
        polling_settings = SimpleNamespace(
            webhook_url="",
            webhook_listen="127.0.0.1",
            webhook_secret_token="",
            port=8080,
        )

        with patch.object(telegram_app, "settings", polling_settings):
            telegram_app.run()

        application.run_polling.assert_called_once_with(
            allowed_updates=Update.ALL_TYPES
        )
        application.run_webhook.assert_not_called()


if __name__ == "__main__":
    unittest.main()
