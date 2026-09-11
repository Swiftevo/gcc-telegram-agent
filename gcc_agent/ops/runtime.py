"""Production health endpoints, readiness checks, and operator alerts."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import logging
import time
from typing import Any

import tornado.web
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.httpserver import HTTPServer

from gcc_agent.common.persistence.database import connect
from gcc_agent.config import settings

logger = logging.getLogger(__name__)

ALERT_COOLDOWN_SECONDS = 15 * 60
INCIDENT_DEGRADED_SECONDS = 30 * 60
TELEGRAM_FAILURE_THRESHOLD = 3
WEBHOOK_PENDING_THRESHOLD = 20
WEBHOOK_MONITOR_INITIAL_DELAY_SECONDS = 20
WEBHOOK_MONITOR_INTERVAL_SECONDS = 60
READINESS_MONITOR_INTERVAL_SECONDS = 15


@dataclass
class OperationalState:
    """Non-sensitive, in-memory state used by production probes."""

    telegram_initialized: bool = False
    database_ready: bool = False
    telegram_monitor_ok: bool = True
    consecutive_telegram_failures: int = 0
    pending_updates_high: bool = False
    last_webhook_error_timestamp: int = 0
    started_at_timestamp: int = field(default_factory=lambda: int(time.time()))
    degraded_until: float = 0.0
    last_alert_at: dict[str, float] = field(default_factory=dict)
    monitor_task: asyncio.Task | None = None
    readiness_task: asyncio.Task | None = None
    server: "OperationsServer | None" = None

    def record_incident(
        self,
        event: str,
        *,
        now: float | None = None,
        degrade_for: float = INCIDENT_DEGRADED_SECONDS,
    ) -> bool:
        """Mark ops degraded and return whether this event should alert now."""
        current = time.monotonic() if now is None else now
        self.degraded_until = max(self.degraded_until, current + degrade_for)
        previous = self.last_alert_at.get(event, 0.0)
        if previous and current - previous < ALERT_COOLDOWN_SECONDS:
            return False
        self.last_alert_at[event] = current
        return True

    def incident_active(self, *, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        return current < self.degraded_until


_state: OperationalState | None = None


def current_state() -> OperationalState | None:
    return _state


async def check_database_readiness() -> bool:
    """Check schema access and obtain a SQLite write transaction without changing data."""
    try:
        async with asyncio.timeout(2):
            async with connect() as db:
                await db.execute("PRAGMA busy_timeout = 1000")
                async with db.execute(
                    "SELECT 1 FROM schema_migrations LIMIT 1"
                ) as cursor:
                    await cursor.fetchone()
                await db.execute("BEGIN IMMEDIATE")
                await db.execute(
                    "UPDATE schema_migrations SET applied_at = applied_at WHERE 0"
                )
                await db.rollback()
        return True
    except Exception as exc:
        logger.warning("readiness database check failed type=%s", type(exc).__name__)
        return False


async def readiness_status(
    application: Any,
    state: OperationalState,
) -> tuple[int, dict[str, Any]]:
    application_running = bool(getattr(application, "running", False))
    updater = getattr(application, "updater", None)
    updater_running = bool(updater and getattr(updater, "running", False))
    checks = {
        "application": application_running,
        "webhook": updater_running,
        "database": state.database_ready,
        "telegram_initialized": state.telegram_initialized,
    }
    ready = all(checks.values())
    return (200 if ready else 503), {
        "status": "ok" if ready else "unavailable",
        "checks": checks,
    }


async def operations_status(
    application: Any,
    state: OperationalState,
) -> tuple[int, dict[str, Any]]:
    readiness_code, readiness = await readiness_status(application, state)
    operational = (
        readiness_code == 200
        and state.telegram_monitor_ok
        and not state.pending_updates_high
        and not state.incident_active()
    )
    return (200 if operational else 503), {
        "status": "ok" if operational else "degraded",
        "checks": {
            "ready": readiness_code == 200,
            "telegram": state.telegram_monitor_ok,
            "webhook_backlog": not state.pending_updates_high,
            "recent_incident": state.incident_active(),
        },
    }


class _JsonHandler(tornado.web.RequestHandler):
    def write_json(self, status: int, payload: dict[str, Any]) -> None:
        self.set_status(status)
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.set_header("Cache-Control", "no-store")
        self.finish(json.dumps(payload, separators=(",", ":")))

    def log_exception(self, typ, value, tb) -> None:  # type: ignore[no-untyped-def]
        if isinstance(value, tornado.web.HTTPError) and value.status_code < 500:
            return
        logger.warning("operations endpoint error type=%s", getattr(typ, "__name__", "unknown"))


class LivenessHandler(_JsonHandler):
    async def get(self) -> None:
        self.write_json(200, {"status": "ok"})


class ReadinessHandler(_JsonHandler):
    def initialize(self, bot_application: Any, state: OperationalState) -> None:
        self.bot_application = bot_application
        self.state = state

    async def get(self) -> None:
        status, payload = await readiness_status(self.bot_application, self.state)
        self.write_json(status, payload)


class OperationalHandler(_JsonHandler):
    def initialize(self, bot_application: Any, state: OperationalState) -> None:
        self.bot_application = bot_application
        self.state = state

    async def get(self) -> None:
        status, payload = await operations_status(self.bot_application, self.state)
        self.write_json(status, payload)


def build_operations_web_application(
    application: Any,
    state: OperationalState,
    upstream_port: int,
) -> tornado.web.Application:
    return tornado.web.Application(
        [
            (r"/healthz/?", LivenessHandler),
            (
                r"/readyz/?",
                ReadinessHandler,
                {"bot_application": application, "state": state},
            ),
            (
                r"/opsz/?",
                OperationalHandler,
                {"bot_application": application, "state": state},
            ),
            (
                r"/webhook/?",
                TelegramProxyHandler,
                {
                    "bot_application": application,
                    "state": state,
                    "upstream_port": upstream_port,
                },
            ),
        ]
    )


def build_proxy_request(
    upstream_port: int,
    body: bytes,
    content_type: str,
    secret_token: str,
) -> HTTPRequest:
    """Create a local-only webhook request and forward only required headers."""
    headers = {"Content-Type": content_type}
    if secret_token:
        headers["X-Telegram-Bot-Api-Secret-Token"] = secret_token
    return HTTPRequest(
        url=f"http://127.0.0.1:{upstream_port}/webhook",
        method="POST",
        headers=headers,
        body=body,
        connect_timeout=3,
        request_timeout=10,
        follow_redirects=False,
    )


class TelegramProxyHandler(_JsonHandler):
    SUPPORTED_METHODS = ("POST",)

    def initialize(
        self,
        bot_application: Any,
        state: OperationalState,
        upstream_port: int,
    ) -> None:
        self.bot_application = bot_application
        self.state = state
        self.upstream_port = upstream_port

    async def post(self) -> None:
        request = build_proxy_request(
            self.upstream_port,
            self.request.body,
            self.request.headers.get("Content-Type", ""),
            self.request.headers.get("X-Telegram-Bot-Api-Secret-Token", ""),
        )
        try:
            response = await AsyncHTTPClient().fetch(request, raise_error=False)
        except Exception:
            logger.exception("webhook proxy could not reach local Telegram handler")
            await report_incident(self.bot_application.bot, "webhook_proxy_unavailable")
            self.write_json(503, {"status": "unavailable"})
            return
        self.set_status(response.code)
        self.set_header("Cache-Control", "no-store")
        if response.headers.get("Content-Type"):
            self.set_header("Content-Type", response.headers["Content-Type"])
        self.finish(response.body)


class OperationsServer:
    def __init__(
        self,
        application: Any,
        state: OperationalState,
        *,
        listen: str,
        port: int,
        upstream_port: int,
    ) -> None:
        web_app = build_operations_web_application(application, state, upstream_port)
        self._http_server = HTTPServer(web_app)
        self._listen = listen
        self._port = port

    def start(self) -> None:
        self._http_server.listen(self._port, address=self._listen)
        logger.info(
            "operations server started listen=%s port=%s endpoints=healthz,readyz,opsz",
            self._listen,
            self._port,
        )

    async def stop(self) -> None:
        self._http_server.stop()
        await self._http_server.close_all_connections()
        logger.info("operations server stopped")


async def report_incident(bot: Any, event: str) -> None:
    """Record a non-sensitive incident and send a deduplicated operator alert."""
    state = current_state()
    should_alert = state.record_incident(event) if state else True
    logger.critical("ops alert event=%s", event)
    if not should_alert or settings.admin_user_id <= 0:
        return
    message = (
        "🚨 GCC bot operations alert\n"
        f"Event: {event}\n"
        f"UTC: {datetime.now(UTC).isoformat(timespec='seconds')}\n"
        "No user content is included. Check Fly logs and docs/operations-runbook.md."
    )
    try:
        await bot.send_message(chat_id=settings.admin_user_id, text=message)
    except Exception as exc:
        logger.error(
            "operator Telegram alert failed event=%s type=%s",
            event,
            type(exc).__name__,
        )


def _webhook_error_timestamp(info: Any) -> int:
    value = getattr(info, "last_error_date", None)
    if isinstance(value, datetime):
        return int(value.timestamp())
    if isinstance(value, (int, float)):
        return int(value)
    return 0


async def check_telegram_webhook(application: Any, state: OperationalState) -> None:
    """Refresh non-sensitive Telegram/webhook monitoring state once."""
    try:
        info = await application.bot.get_webhook_info()
    except Exception:
        state.consecutive_telegram_failures += 1
        if state.consecutive_telegram_failures >= TELEGRAM_FAILURE_THRESHOLD:
            state.telegram_monitor_ok = False
            await report_incident(application.bot, "telegram_api_unreachable")
        return

    state.consecutive_telegram_failures = 0
    state.telegram_monitor_ok = bool(getattr(info, "url", "") == settings.webhook_url)
    if not state.telegram_monitor_ok:
        await report_incident(application.bot, "telegram_webhook_url_mismatch")

    pending = int(getattr(info, "pending_update_count", 0) or 0)
    state.pending_updates_high = pending >= WEBHOOK_PENDING_THRESHOLD
    if state.pending_updates_high:
        await report_incident(application.bot, "telegram_webhook_backlog")

    error_timestamp = _webhook_error_timestamp(info)
    if (
        error_timestamp >= state.started_at_timestamp
        and error_timestamp > state.last_webhook_error_timestamp
    ):
        state.last_webhook_error_timestamp = error_timestamp
        await report_incident(application.bot, "telegram_webhook_delivery_error")


async def _monitor_loop(application: Any, state: OperationalState) -> None:
    await asyncio.sleep(WEBHOOK_MONITOR_INITIAL_DELAY_SECONDS)
    while True:
        await check_telegram_webhook(application, state)
        await asyncio.sleep(WEBHOOK_MONITOR_INTERVAL_SECONDS)


async def _readiness_loop(state: OperationalState) -> None:
    while True:
        await asyncio.sleep(READINESS_MONITOR_INTERVAL_SECONDS)
        state.database_ready = await check_database_readiness()


async def start_operations(
    application: Any,
    *,
    listen: str,
    port: int,
    upstream_port: int,
) -> OperationalState:
    global _state
    state = OperationalState(telegram_initialized=True)
    state.database_ready = await check_database_readiness()
    if not state.database_ready:
        raise RuntimeError("database readiness check failed during startup")
    server = OperationsServer(
        application,
        state,
        listen=listen,
        port=port,
        upstream_port=upstream_port,
    )
    server.start()
    state.server = server
    state.monitor_task = asyncio.create_task(
        _monitor_loop(application, state),
        name="telegram-webhook-monitor",
    )
    state.readiness_task = asyncio.create_task(
        _readiness_loop(state),
        name="database-readiness-monitor",
    )
    _state = state
    return state


async def stop_operations(application: Any) -> None:
    del application
    global _state
    state = _state
    _state = None
    if state is None:
        return
    for task in (state.monitor_task, state.readiness_task):
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    if state.server:
        await state.server.stop()


async def handle_application_error(update: object, context: Any) -> None:
    del update
    error = getattr(context, "error", None)
    logger.error(
        "unhandled Telegram update error type=%s",
        type(error).__name__ if error else "unknown",
        exc_info=error,
    )
    await report_incident(context.bot, "unhandled_update_error")
