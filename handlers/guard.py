"""Compatibility facade for :mod:`gcc_agent.access.guard`."""

from gcc_agent.access.guard import (
    DAILY_LIMIT,
    GuardResult,
    detect_language,
    message as _msg,
    run_guard,
    verify_group_membership,
)

__all__ = [
    "DAILY_LIMIT",
    "GuardResult",
    "_msg",
    "detect_language",
    "run_guard",
    "verify_group_membership",
]
