"""Compatibility facade for :mod:`gcc_agent.qa`."""

from gcc_agent.qa.handler import handle_general, is_funding_related as _is_funding_related
from gcc_agent.qa.messages import (
    APPLY_BUTTON_LABEL,
    MEETING_REMINDER,
    append_reminder,
    make_apply_markup,
)
from gcc_agent.qa.service import call_ai, get_openai_client

__all__ = [
    "APPLY_BUTTON_LABEL",
    "MEETING_REMINDER",
    "_is_funding_related",
    "append_reminder",
    "call_ai",
    "get_openai_client",
    "handle_general",
    "make_apply_markup",
]
