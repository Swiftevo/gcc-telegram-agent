"""Compatibility re-exports for the modular persistence package."""

from gcc_agent.common.persistence.database import DB_PATH, init_db
from gcc_agent.common.persistence.conversations import (
    create_session,
    get_active_session,
    get_or_create_session,
    save_exchange,
    save_message,
    save_session,
)
from gcc_agent.common.persistence.stats import get_stats
from gcc_agent.common.persistence.users import (
    complete_email_challenge,
    fail_email_challenge,
    get_email_challenge,
    get_or_create_user,
    get_user,
    get_user_by_username,
    save_email_challenge,
    set_identity,
    set_user_blocked,
    set_user_email,
    set_user_kind,
    store_agent_credential,
    try_increment_daily_count,
    update_user_group_membership,
    update_user_lang,
    verify_agent_credential,
)

__all__ = [name for name in globals() if not name.startswith("_")]
