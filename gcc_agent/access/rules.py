"""Default-deny access policy without RBAC."""

from dataclasses import dataclass

from gcc_agent.access.models import (
    ACCESS_GCC_MEMBER,
    ACTOR_AGENT,
    ACTOR_HUMAN,
    User,
)


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str


def qa_decision(user: User, *, agent_authenticated: bool = False) -> AccessDecision:
    if user.is_blocked:
        return AccessDecision(False, "blocked")
    if user.access_level != ACCESS_GCC_MEMBER:
        return AccessDecision(False, "welcome_only")
    if user.actor_type == ACTOR_HUMAN:
        allowed = bool(user.email and user.email_verified_at)
        return AccessDecision(allowed, "" if allowed else "verified_email_required")
    if user.actor_type == ACTOR_AGENT:
        allowed = user.has_agent_credential and agent_authenticated
        return AccessDecision(allowed, "" if allowed else "agent_authentication_required")
    return AccessDecision(False, "invalid_identity")
