"""Small state-based Telegram message router."""

from dataclasses import dataclass
import logging

from telegram import Update
from telegram.ext import ContextTypes

from gcc_agent.common.persistence.conversations import get_or_create_session
from gcc_agent.config import settings

logger = logging.getLogger(__name__)

ADMIN_COMMANDS = {
    "/update_values",
    "/status",
    "/block",
    "/unblock",
}


@dataclass(frozen=True)
class RouteResult:
    mode: str
    command: str = ""


async def route(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    guard,
) -> RouteResult:
    del context
    text = (update.message.text or "").strip() if update.message else ""
    user_id = guard.user.user_id if guard.user else 0

    if user_id == settings.admin_user_id and text.startswith("/"):
        command = text.split()[0].lower()
        if command in ADMIN_COMMANDS:
            logger.info("admin route command=%s user_id=%s", command, user_id)
            return RouteResult("admin", command)

    session, _ = await get_or_create_session(user_id)
    if session.mode == "application":
        return RouteResult("application")
    return RouteResult("general")
