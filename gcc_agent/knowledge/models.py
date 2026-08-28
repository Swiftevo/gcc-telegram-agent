"""Knowledge configuration models."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class AgentValues:
    version: str = "1.0.0"
    updated_by_admin_id: str = ""
    mission_statement: str = ""
    priority_themes: List[str] = field(default_factory=list)
    rejection_criteria: List[str] = field(default_factory=list)
    screening_rubric: dict = field(default_factory=dict)
    tone_guidelines: str = ""
    gcc_summary: str = ""
