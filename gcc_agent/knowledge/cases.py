"""Load structured GCC public-goods case records."""

from copy import deepcopy
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

_BOT_QA_REVIEW_STATES = {"reviewed", "published"}
_BOT_QA_SOURCE_ACCESS = {"public", "redacted"}
_BOT_QA_PUBLIC_RECORD_FIELDS = (
    "grant_year",
    "activity_year",
    "language_community",
    "regions",
    "tags",
    "summary",
    "why_funded",
    "funding",
    "execution_events",
    "public_goods_dimensions",
    "impact_evidence",
    "lifecycle_status",
    "links",
)


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


def _contains_status(value, expected: str) -> bool:
    if isinstance(value, dict):
        return any(_contains_status(child, expected) for child in value.values())
    if isinstance(value, list):
        return any(_contains_status(child, expected) for child in value)
    return value == expected


def _source_reference_ids(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "source_snapshot_ids" and isinstance(child, list):
                yield from (item for item in child if isinstance(item, str))
            yield from _source_reference_ids(child)
    elif isinstance(value, list):
        for child in value:
            yield from _source_reference_ids(child)


def is_bot_qa_eligible_case(case: dict) -> bool:
    """Apply the runtime gate independently of schema and merge-time validation."""
    if (
        not isinstance(case, dict)
        or case.get("schema_version") != "0.4.0"
        or case.get("record_type") == "placeholder"
    ):
        return False
    if case.get("ai_review_usage", {}).get("allowed") is not True:
        return False

    governance = case.get("governance", {})
    if (
        governance.get("visibility") != "public"
        or governance.get("review_status") not in _BOT_QA_REVIEW_STATES
        or not governance.get("reviewed_at")
        or not governance.get("reviewed_by_role")
    ):
        return False
    if _contains_status(case, "pending_reconciliation"):
        return False

    snapshots = case.get("evidence", {}).get("snapshots", [])
    if not isinstance(snapshots, list) or not snapshots:
        return False
    approved_source_ids: set[str] = set()
    for snapshot in snapshots:
        if not isinstance(snapshot, dict):
            return False
        processing = snapshot.get("processing", {})
        access_level = snapshot.get("access_level")
        if (
            access_level not in _BOT_QA_SOURCE_ACCESS
            or processing.get("review_status") != "approved"
            or "bot_qa" not in processing.get("allowed_uses", [])
            or not processing.get("reviewed_at")
            or not processing.get("reviewed_by_role")
        ):
            return False
        if (
            access_level == "redacted"
            and processing.get("sanitization_status") != "human_reviewed"
        ):
            return False
        snapshot_id = snapshot.get("snapshot_id")
        if not isinstance(snapshot_id, str) or not snapshot_id:
            return False
        approved_source_ids.add(snapshot_id)

    referenced_ids = set(_source_reference_ids(case.get("public_record", {})))
    referenced_ids.update(
        _source_reference_ids(case.get("evidence", {}).get("vote_summary", {}))
    )
    if not referenced_ids.issubset(approved_source_ids):
        return False
    return bool(case.get("public_record", {}).get("summary", "").strip())


def load_bot_qa_cases(force_reload: bool = False) -> list[dict]:
    """Return only canonical cases that pass the strict Bot QA runtime gate."""
    database = load_project_case_database(force_reload)
    if database.get("schema_version") != "0.4.0":
        logger.error(
            "bot QA case loading refused schema_version=%s",
            database.get("schema_version"),
        )
        return []
    return [case for case in database.get("cases", []) if is_bot_qa_eligible_case(case)]


def case_to_bot_qa_record(case: dict, *, database_updated_at: str = "") -> dict:
    """Project an eligible case onto the explicit public runtime allowlist."""
    if not is_bot_qa_eligible_case(case):
        raise ValueError("case is not eligible for Bot QA")

    public_record = case.get("public_record", {})
    safe_public_record = {
        field: deepcopy(public_record[field])
        for field in _BOT_QA_PUBLIC_RECORD_FIELDS
        if field in public_record
    }
    program_details = public_record.get("program_details", {})
    if isinstance(program_details, dict):
        safe_public_record["program_details"] = {
            field: deepcopy(program_details[field])
            for field in (
                "start_date",
                "end_date",
                "application_deadline",
                "location",
                "eligibility",
                "deliverables",
                "funding_tracks",
                "milestones",
            )
            if field in program_details
        }

    sources = []
    for snapshot in case.get("evidence", {}).get("snapshots", []):
        source = {
            "snapshot_id": snapshot.get("snapshot_id"),
            "source_type": snapshot.get("source_type"),
            "access_level": snapshot.get("access_level"),
            "captured_at": snapshot.get("captured_at"),
        }
        if snapshot.get("access_level") == "public" and snapshot.get("source_url"):
            source["source_url"] = snapshot["source_url"]
        sources.append(source)

    result = {
        "case_id": case.get("case_id"),
        "record_type": case.get("record_type"),
        "title": case.get("title"),
        "category": case.get("category"),
        "fund_type": case.get("fund_type"),
        "database_updated_at": database_updated_at,
        "case_reviewed_at": case.get("governance", {}).get("reviewed_at"),
        "public_record": safe_public_record,
        "sources": sources,
    }
    vote_summary = case.get("evidence", {}).get("vote_summary")
    if isinstance(vote_summary, dict):
        result["aggregate_vote_summary"] = deepcopy(vote_summary)
    return result


def _case_aliases(case: dict) -> set[str]:
    aliases = {str(case.get("title", "")).strip().casefold()}
    legacy_slug = str(case.get("legacy_project_slug", "")).strip().casefold()
    if legacy_slug.startswith("project-"):
        aliases.add(legacy_slug.removeprefix("project-").replace("-", " "))
    return {alias for alias in aliases if len(alias) >= 2}


def select_bot_qa_case_records(
    query: str,
    *,
    explicit_only: bool = False,
    limit: int = 3,
    force_reload: bool = False,
) -> list[dict]:
    """Select a small deterministic set of safe records for one user question."""
    value = query.casefold().strip()
    if not value or limit < 1:
        return []
    database = load_project_case_database(force_reload)
    if database.get("schema_version") != "0.4.0":
        return []

    matches: list[tuple[int, int, dict]] = []
    for index, case in enumerate(database.get("cases", [])):
        if not is_bot_qa_eligible_case(case):
            continue
        aliases = _case_aliases(case)
        explicit_match = any(alias in value for alias in aliases)
        score = 100 if explicit_match else 0
        if not explicit_only and not explicit_match:
            searchable = {
                str(case.get("category", "")).casefold(),
                *(
                    str(tag).casefold()
                    for tag in case.get("public_record", {}).get("tags", [])
                ),
            }
            score = sum(10 for term in searchable if len(term) >= 3 and term in value)
        if score:
            matches.append((score, -index, case))

    selected = [item[2] for item in sorted(matches, reverse=True)[:limit]]
    return [
        case_to_bot_qa_record(
            case,
            database_updated_at=str(database.get("updated_at", "")),
        )
        for case in selected
    ]


def case_to_legacy_project(case: dict) -> dict:
    public_record = case.get("public_record", {})
    links = public_record.get("links", {})
    funding = public_record.get("funding", {})
    approved_amount = funding.get("governance_approved", {}).get("amount")
    requested_amount = funding.get("requested", {}).get("amount")
    amount = approved_amount if approved_amount is not None else requested_amount
    return {
        "name": case.get("title", ""),
        "slug": case.get("legacy_project_slug", ""),
        "category": case.get("category", ""),
        "fund_type": case.get("fund_type", "unknown"),
        "amount": amount,
        "keywords": public_record.get("tags", []),
        "region": public_record.get("regions", []),
        "summary": public_record.get("summary", ""),
        "why_funded": public_record.get("why_funded", ""),
        "project_url": links.get("gcc_project_url"),
        "official_website": links.get("official_website"),
    }
