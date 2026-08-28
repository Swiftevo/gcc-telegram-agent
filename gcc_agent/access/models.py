"""Identity domain model. Actor type and access level are independent."""

from dataclasses import dataclass, field
from datetime import datetime

ACTOR_HUMAN = "human"
ACTOR_AGENT = "agent"
ACTOR_TYPES = (ACTOR_HUMAN, ACTOR_AGENT)
ACCESS_REGULAR = "regular"
ACCESS_GCC_MEMBER = "gcc_member"
ACCESS_LEVELS = (ACCESS_REGULAR, ACCESS_GCC_MEMBER)

# Compatibility input values; these are not roles.
USER_KIND_REGULAR = "regular"
USER_KIND_GCC_MEMBER = "gcc_member"
USER_KIND_AI = "ai"
USER_KINDS = (USER_KIND_REGULAR, USER_KIND_GCC_MEMBER, USER_KIND_AI)


@dataclass
class User:
    user_id: int
    username: str = ""
    first_name: str = ""
    detected_lang: str = "zh-TW"
    is_group_member: bool = False
    is_blocked: bool = False
    actor_type: str = ACTOR_HUMAN
    access_level: str = ACCESS_REGULAR
    email: str = field(default="", repr=False)
    email_verified_at: str = ""
    has_agent_credential: bool = field(default=False, repr=False)
    daily_count: int = 0
    count_reset_date: str = ""
    total_messages: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_seen_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def user_kind(self) -> str:
        """Legacy projection retained for callers during migration."""
        if self.actor_type == ACTOR_AGENT:
            return USER_KIND_AI
        return self.access_level

    @user_kind.setter
    def user_kind(self, kind: str) -> None:
        if kind == USER_KIND_AI:
            self.actor_type = ACTOR_AGENT
            self.access_level = ACCESS_REGULAR
        elif kind in ACCESS_LEVELS:
            self.actor_type = ACTOR_HUMAN
            self.access_level = kind

    def can_use_qa(self, *, agent_authenticated: bool = False) -> bool:
        if self.access_level != ACCESS_GCC_MEMBER:
            return False
        if self.actor_type == ACTOR_HUMAN:
            return bool(self.email and self.email_verified_at)
        if self.actor_type == ACTOR_AGENT:
            return self.has_agent_credential and agent_authenticated
        return False

    def is_rate_limited(self) -> bool:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return self.count_reset_date == today and self.daily_count >= 20

    def reset_if_new_day(self) -> bool:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self.count_reset_date == today:
            return False
        self.daily_count = 0
        self.count_reset_date = today
        return True
