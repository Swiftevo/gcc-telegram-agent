"""Tests for health, readiness, webhook monitoring, and safe proxying."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
import tempfile
import tomllib
import unittest
from unittest.mock import AsyncMock, patch

from tornado.testing import AsyncHTTPTestCase

from gcc_agent.common.persistence import database
from gcc_agent.applications.models import ApplicationDraft
from gcc_agent.applications import notifier
from gcc_agent.ops import runtime


class DatabaseReadinessTests(unittest.IsolatedAsyncioTestCase):
    async def test_database_readiness_checks_integrity_and_write_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "readiness.db")
            with patch.object(database, "DB_PATH", db_path):
                await database.init_db()
                self.assertTrue(await runtime.check_database_readiness())

    async def test_database_readiness_fails_closed_for_missing_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "empty.db")
            with patch.object(database, "DB_PATH", db_path):
                self.assertFalse(await runtime.check_database_readiness())


class EndpointStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_readiness_requires_application_webhook_database_and_telegram(self) -> None:
        application = SimpleNamespace(running=True, updater=SimpleNamespace(running=True))
        state = runtime.OperationalState(
            telegram_initialized=True,
            database_ready=True,
        )
        code, payload = await runtime.readiness_status(application, state)
        self.assertEqual(200, code)
        self.assertEqual("ok", payload["status"])
        self.assertTrue(all(payload["checks"].values()))

        application.running = False
        code, payload = await runtime.readiness_status(application, state)
        self.assertEqual(503, code)
        self.assertFalse(payload["checks"]["application"])

    async def test_ops_status_reports_recent_incident_without_exposing_details(self) -> None:
        application = SimpleNamespace(running=True, updater=SimpleNamespace(running=True))
        state = runtime.OperationalState(
            telegram_initialized=True,
            database_ready=True,
        )
        state.record_incident("private-internal-detail", now=100.0)
        with patch.object(runtime.time, "monotonic", return_value=101.0):
            code, payload = await runtime.operations_status(application, state)
        self.assertEqual(503, code)
        self.assertTrue(payload["checks"]["recent_incident"])
        self.assertNotIn("private-internal-detail", str(payload))


class EndpointHTTPTests(AsyncHTTPTestCase):
    def get_app(self):
        self.application = SimpleNamespace(
            running=True,
            updater=SimpleNamespace(running=True),
            bot=SimpleNamespace(send_message=AsyncMock()),
        )
        self.state = runtime.OperationalState(
            telegram_initialized=True,
            database_ready=True,
        )
        return runtime.build_operations_web_application(
            self.application,
            self.state,
            8081,
        )

    def test_health_and_readiness_are_json_and_do_not_expose_runtime_details(self) -> None:
        health = self.fetch("/healthz")
        ready = self.fetch("/readyz")
        self.assertEqual(200, health.code)
        self.assertEqual(200, ready.code)
        self.assertEqual("no-store", ready.headers["Cache-Control"])
        body = ready.body.decode()
        self.assertIn('"status":"ok"', body)
        for sensitive in ("BOT_TOKEN", "DB_PATH", "user_id", "gcc_agent.db"):
            self.assertNotIn(sensitive, body)

    def test_webhook_does_not_accept_get(self) -> None:
        response = self.fetch("/webhook")
        self.assertEqual(405, response.code)

    def test_webhook_forwards_secret_and_returns_upstream_status(self) -> None:
        upstream_response = SimpleNamespace(
            code=200,
            headers={"Content-Type": "application/json; charset=utf-8"},
            body=b"{}",
        )
        client = SimpleNamespace(fetch=AsyncMock(return_value=upstream_response))
        with patch.object(runtime, "AsyncHTTPClient", return_value=client):
            response = self.fetch(
                "/webhook",
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "X-Telegram-Bot-Api-Secret-Token": "expected-secret",
                },
                body=b'{"update_id":1}',
            )

        self.assertEqual(200, response.code)
        forwarded = client.fetch.await_args.args[0]
        self.assertEqual(b'{"update_id":1}', forwarded.body)
        self.assertEqual(
            "expected-secret",
            forwarded.headers["X-Telegram-Bot-Api-Secret-Token"],
        )


class ProxyRequestTests(unittest.TestCase):
    def test_proxy_forwards_only_body_content_type_and_secret_to_loopback(self) -> None:
        request = runtime.build_proxy_request(
            8081,
            b'{"update_id":1}',
            "application/json",
            "secret-value",
        )
        self.assertEqual("http://127.0.0.1:8081/webhook", request.url)
        self.assertEqual(b'{"update_id":1}', request.body)
        self.assertEqual("application/json", request.headers["Content-Type"])
        self.assertEqual(
            "secret-value",
            request.headers["X-Telegram-Bot-Api-Secret-Token"],
        )
        self.assertNotIn("Authorization", request.headers)


class MonitoringTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.previous_state = runtime._state
        runtime._state = runtime.OperationalState(started_at_timestamp=100)

    async def asyncTearDown(self) -> None:
        runtime._state = self.previous_state

    async def test_webhook_error_and_backlog_create_generic_deduplicated_alerts(self) -> None:
        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 9, 16, 13, 53, 25, tzinfo=tz)

        state = runtime._state
        bot = SimpleNamespace(
            get_webhook_info=AsyncMock(
                return_value=SimpleNamespace(
                    url="https://example.test/webhook",
                    pending_update_count=25,
                    last_error_date=FixedDateTime.fromtimestamp(110, tz=UTC),
                )
            ),
            send_message=AsyncMock(),
        )
        application = SimpleNamespace(bot=bot)
        fake_settings = SimpleNamespace(
            webhook_url="https://example.test/webhook",
            admin_user_id=42,
        )
        with patch.object(runtime, "settings", fake_settings), patch.object(runtime, "datetime", FixedDateTime):
            await runtime.check_telegram_webhook(application, state)
            await runtime.check_telegram_webhook(application, state)

        self.assertTrue(state.pending_updates_high)
        self.assertEqual(110, state.last_webhook_error_timestamp)
        self.assertEqual(2, bot.send_message.await_count)
        alert_texts = [call.kwargs["text"] for call in bot.send_message.await_args_list]
        messages = " ".join(alert_texts)
        self.assertIn("telegram_webhook_backlog", messages)
        self.assertIn("telegram_webhook_delivery_error", messages)
        self.assertTrue(all("UTC: 2026-09-16T13:53:25+00:00" in alert for alert in alert_texts))
        # The timestamp can contain "25" even though the backlog count is omitted.
        non_timestamp_lines = " ".join(
            line
            for alert in alert_texts
            for line in alert.splitlines()
            if not line.startswith("UTC: ")
        )
        self.assertNotIn("25", non_timestamp_lines)
        self.assertNotIn("110", non_timestamp_lines)

    async def test_three_telegram_failures_mark_ops_degraded(self) -> None:
        state = runtime._state
        bot = SimpleNamespace(
            get_webhook_info=AsyncMock(side_effect=OSError("network detail")),
            send_message=AsyncMock(side_effect=OSError("still unavailable")),
        )
        application = SimpleNamespace(bot=bot)
        fake_settings = SimpleNamespace(webhook_url="https://example.test/webhook", admin_user_id=42)
        with patch.object(runtime, "settings", fake_settings):
            for _ in range(runtime.TELEGRAM_FAILURE_THRESHOLD):
                await runtime.check_telegram_webhook(application, state)

        self.assertFalse(state.telegram_monitor_ok)
        self.assertEqual(runtime.TELEGRAM_FAILURE_THRESHOLD, state.consecutive_telegram_failures)
        self.assertEqual(1, bot.send_message.await_count)

    async def test_webhook_url_mismatch_is_an_incident(self) -> None:
        state = runtime._state
        bot = SimpleNamespace(
            get_webhook_info=AsyncMock(
                return_value=SimpleNamespace(
                    url="https://wrong.example/webhook",
                    pending_update_count=0,
                    last_error_date=None,
                )
            ),
            send_message=AsyncMock(),
        )
        application = SimpleNamespace(bot=bot)
        fake_settings = SimpleNamespace(
            webhook_url="https://expected.example/webhook",
            admin_user_id=42,
        )
        with patch.object(runtime, "settings", fake_settings):
            await runtime.check_telegram_webhook(application, state)

        self.assertFalse(state.telegram_monitor_ok)
        self.assertIn("telegram_webhook_url_mismatch", bot.send_message.await_args.kwargs["text"])

    def test_incident_alerts_are_rate_limited(self) -> None:
        state = runtime.OperationalState()
        self.assertGreater(runtime.INCIDENT_DEGRADED_SECONDS, 15 * 60)
        self.assertTrue(state.record_incident("same", now=100.0))
        self.assertFalse(state.record_incident("same", now=101.0))
        self.assertTrue(
            state.record_incident("same", now=100.0 + runtime.ALERT_COOLDOWN_SECONDS)
        )

    async def test_admin_notification_failure_uses_generic_fallback_alert(self) -> None:
        bot = SimpleNamespace(
            send_message=AsyncMock(side_effect=[RuntimeError("private detail"), None])
        )
        context = SimpleNamespace(bot=bot)
        draft = ApplicationDraft(
            project_name="Private project name",
            fund_type="public",
            executive_summary="Private application content",
            agent_score=50,
            agent_notes="Private notes",
        )
        user = SimpleNamespace(username="private", user_id=123, first_name="Private")
        notify_settings = SimpleNamespace(admin_notify_id=41)
        ops_settings = SimpleNamespace(admin_user_id=42)
        with (
            patch.object(notifier, "settings", notify_settings),
            patch.object(runtime, "settings", ops_settings),
        ):
            sent = await notifier.notify_admin(context, draft, user, "zh-TW")

        self.assertFalse(sent)
        self.assertEqual(2, bot.send_message.await_count)
        fallback = bot.send_message.await_args_list[1].kwargs["text"]
        self.assertIn("admin_notification_failure", fallback)
        self.assertNotIn("Private project name", fallback)
        self.assertNotIn("Private application content", fallback)


class DeploymentConfigurationTests(unittest.TestCase):
    def test_fly_routes_only_after_cached_database_readiness_passes(self) -> None:
        with open("fly.toml", "rb") as config_file:
            config = tomllib.load(config_file)
        checks = config["http_service"]["checks"]
        self.assertEqual("/readyz", checks[0]["path"])
        self.assertEqual("GET", checks[0]["method"])
        self.assertEqual("15s", checks[0]["interval"])

    def test_external_monitor_and_deploy_failure_alerts_are_configured(self) -> None:
        monitor = Path(".github/workflows/ops-monitor.yml").read_text(encoding="utf-8")
        deploy = Path(".github/workflows/fly.yml").read_text(encoding="utf-8")
        self.assertIn("*/15 * * * *", monitor)
        self.assertIn("/opsz", monitor)
        self.assertIn("gh issue create", monitor)
        self.assertIn("Alert on production deploy failure", deploy)
        self.assertIn("issues: write", deploy)


if __name__ == "__main__":
    unittest.main()
