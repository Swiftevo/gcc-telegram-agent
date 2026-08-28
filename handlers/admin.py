"""Compatibility facade for :mod:`gcc_agent.admin.handler`."""

from gcc_agent.admin.handler import (
    handle_admin,
    handle_status as _handle_status,
    handle_update_values as _handle_update_values,
)

__all__ = ["_handle_status", "_handle_update_values", "handle_admin"]
