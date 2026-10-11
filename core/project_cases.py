"""Compatibility facade for :mod:`gcc_agent.knowledge.cases`."""

from gcc_agent.knowledge.cases import (
    PROJECT_CASES_PATH,
    case_to_legacy_project,
    case_to_bot_qa_record,
    is_bot_qa_eligible_case,
    load_ai_review_cases,
    load_bot_qa_cases,
    load_project_case_database,
    load_project_cases,
    select_bot_qa_case_records,
)

__all__ = [
    "PROJECT_CASES_PATH",
    "case_to_legacy_project",
    "case_to_bot_qa_record",
    "is_bot_qa_eligible_case",
    "load_ai_review_cases",
    "load_bot_qa_cases",
    "load_project_case_database",
    "load_project_cases",
    "select_bot_qa_case_records",
]
