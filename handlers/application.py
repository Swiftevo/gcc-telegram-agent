"""Compatibility facade for :mod:`gcc_agent.applications`."""

from gcc_agent.applications.markup import make_completion_markup, make_exit_markup
from gcc_agent.applications.messages import text as _t
from gcc_agent.applications.notifier import notify_admin
from gcc_agent.applications.screening import pre_screen
from gcc_agent.applications.workflow import handle_application

__all__ = [
    "_t",
    "handle_application",
    "make_completion_markup",
    "make_exit_markup",
    "notify_admin",
    "pre_screen",
]
