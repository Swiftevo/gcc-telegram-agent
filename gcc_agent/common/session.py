"""Conversation session application service."""

import logging

from gcc_agent.common.models import Session
from gcc_agent.common.persistence import conversations

logger = logging.getLogger(__name__)


async def get_session(guard) -> Session:
    session, is_new = await conversations.get_or_create_session(guard.user.user_id)
    if is_new:
        logger.debug("new session user_id=%s", guard.user.user_id)
    return session


async def save(session: Session) -> None:
    await conversations.save_session(session)


async def save_exchange(
    session: Session,
    user_id: int,
    user_text: str,
    assistant_text: str,
    tokens_used: int = 0,
    link_served: bool = False,
) -> None:
    session.add_message("user", user_text)
    session.add_message("assistant", assistant_text)
    await conversations.save_exchange(
        session, user_id, user_text, assistant_text, tokens_used, link_served
    )
    await conversations.save_session(session)
