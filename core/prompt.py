"""Compatibility facade for :mod:`gcc_agent.qa.prompts`."""

from gcc_agent.qa.prompts import (
    FUNDING_KEYWORDS,
    GCC_LINKS,
    PROJECT_LINKS,
    LinkResult,
    build_messages,
    check_link_first,
)

__all__ = [
    "FUNDING_KEYWORDS",
    "GCC_LINKS",
    "PROJECT_LINKS",
    "LinkResult",
    "build_messages",
    "check_link_first",
]
