"""Load structured GCC public-goods case records."""

import logging
import os
from typing import Optional

import yaml

logger = logging.getLogger(__name__)
PROJECT_CASES_PATH = os.getenv(
    "PROJECT_CASES_PATH",
    "data/project-case-seeds.yaml",
)
_cached_case_database: Optional[dict] = None


def load_project_case_database(force_reload: bool = False) -> dict:
    global _cached_case_database
    if _cached_case_database is not None and not force_reload:
        return _cached_case_database
    if not os.path.exists(PROJECT_CASES_PATH):
        logger.warning("project case database missing path=%s", PROJECT_CASES_PATH)
        _cached_case_database = {"schema_version": "0.0.0", "cases": []}
        return _cached_case_database

    try:
        with open(PROJECT_CASES_PATH, encoding="utf-8") as source:
            data = yaml.safe_load(source) or {}
    except Exception:
        logger.exception("project case database load failed")
        data = {}

    cases = data.get("cases", [])
    if not isinstance(cases, list):
        logger.error("project case database has invalid cases value")
        cases = []
    _cached_case_database = {**data, "cases": cases}
    return _cached_case_database


def load_project_cases(force_reload: bool = False) -> list[dict]:
    return load_project_case_database(force_reload).get("cases", [])


def load_ai_review_cases(force_reload: bool = False) -> list[dict]:
    return [
        case
        for case in load_project_cases(force_reload)
        if case.get("ai_review_usage", {}).get("allowed") is True
    ]


def case_to_legacy_project(case: dict) -> dict:
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
