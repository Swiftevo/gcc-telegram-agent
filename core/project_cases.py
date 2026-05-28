"""
Load GCC public goods project case records.

This module is deliberately separate from core.values because the public goods
database is meant to become reusable infrastructure, not only bot prompt data.
"""

import logging
import os
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

PROJECT_CASES_PATH = os.getenv("PROJECT_CASES_PATH", "data/project-case-seeds.yaml")

_cached_case_database: Optional[dict] = None


def load_project_case_database(force_reload: bool = False) -> dict:
    """
    Load the project case seed database.

    Returns the full database object so callers can inspect metadata such as
    schema version and update time.
    """
    global _cached_case_database

    if _cached_case_database is not None and not force_reload:
        return _cached_case_database

    if not os.path.exists(PROJECT_CASES_PATH):
        logger.warning("Project case database not found at %s", PROJECT_CASES_PATH)
        _cached_case_database = {"schema_version": "0.0.0", "cases": []}
        return _cached_case_database

    try:
        with open(PROJECT_CASES_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as exc:
        logger.error("Failed to load project case database: %s", exc)
        data = {}

    cases = data.get("cases", [])
    if not isinstance(cases, list):
        logger.error("Project case database has invalid 'cases' value")
        cases = []

    _cached_case_database = {
        **data,
        "cases": cases,
    }
    logger.info("Loaded %s project case records", len(cases))
    return _cached_case_database


def load_project_cases(force_reload: bool = False) -> list[dict]:
    """Return only the case records."""
    return load_project_case_database(force_reload=force_reload).get("cases", [])


def load_ai_review_cases(force_reload: bool = False) -> list[dict]:
    """Return cases that are explicitly allowed for AI screening context."""
    return [
        case
        for case in load_project_cases(force_reload=force_reload)
        if case.get("ai_review_usage", {}).get("allowed") is True
    ]


def case_to_legacy_project(case: dict) -> dict:
    """
    Convert a project case into a projects.yaml-like dict.

    This gives us a low-risk migration path: the existing bot can keep using the
    legacy shape while the richer case database grows underneath it.
    """
    public_record = case.get("public_record", {})
    links = public_record.get("links", {})

    return {
        "name": case.get("title", ""),
        "slug": case.get("canonical_project_id", ""),
        "category": case.get("category", ""),
        "fund_type": case.get("fund_type", "unknown"),
        "amount": public_record.get("amount_usd"),
        "keywords": public_record.get("tags", []),
        "region": public_record.get("regions", []),
        "summary": public_record.get("summary", ""),
        "why_funded": public_record.get("why_funded", ""),
        "project_url": links.get("gcc_project_url"),
        "official_website": links.get("official_website"),
    }

