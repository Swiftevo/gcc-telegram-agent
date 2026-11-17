"""Legacy application data shape, retained only for historical SQLite rows."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ApplicationDraft:
    project_name: str = ""
    fund_type: str = "unknown"
    proposal_link: str = ""
    executive_summary: str = ""
    collection_step: int = 0
    agent_score: int = -1
    agent_notes: str = ""
    submitted_at: Optional[str] = None
