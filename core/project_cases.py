"""Compatibility facade for :mod:`gcc_agent.knowledge.cases`."""

from gcc_agent.knowledge.cases import (
    PROJECT_CASES_PATH,
    case_to_legacy_project,
    load_ai_review_cases,
    load_project_case_database,
    load_project_cases,
)

__all__ = [
    "PROJECT_CASES_PATH",
    "case_to_legacy_project",
    "load_ai_review_cases",
    "load_project_case_database",
    "load_project_cases",
]
