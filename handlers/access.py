"""Compatibility adapter for the access feature."""

from gcc_agent.access.handler import (
    handle_email,
    handle_grant,
    handle_verify,
    handle_whoami,
    is_group_grantor,
    maybe_promote_group_member_after_email,
    send_limited_welcome,
)
from gcc_agent.access.messages import NEED_VERIFICATION as NEED_EMAIL, welcome_text
from gcc_agent.access.service import is_valid_email, mask_email, normalize_email

__all__ = [name for name in globals() if not name.startswith("_")]
