"""Conversation persistence models shared by features."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List
import uuid

from gcc_agent.applications.models import ApplicationDraft


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: int = 0
    mode: str = "general"
    messages: List[dict] = field(default_factory=list)
    application_draft: ApplicationDraft = field(default_factory=ApplicationDraft)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_active: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    SESSION_TIMEOUT_MINUTES: int = field(default=30, init=False, repr=False)
    MAX_CONTEXT_MESSAGES: int = field(default=20, init=False, repr=False)

    def is_expired(self) -> bool:
        try:
            last = datetime.fromisoformat(self.last_active)
            return (datetime.utcnow() - last).total_seconds() / 60 > self.SESSION_TIMEOUT_MINUTES
        except (TypeError, ValueError):
            return True

    def get_context(self) -> List[dict]:
        return self.messages[-self.MAX_CONTEXT_MESSAGES:]

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        self.touch()

    def touch(self) -> None:
        self.last_active = datetime.utcnow().isoformat()


@dataclass
class Message:
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    user_id: int = 0
    role: str = "user"
    content: str = ""
    tokens_used: int = 0
    link_served: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
