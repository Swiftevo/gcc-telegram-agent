"""Validate the public-goods case database before content is merged or used."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = ROOT / "data" / "project-case-seeds.yaml"
DEFAULT_DATABASE_SCHEMA_PATH = ROOT / "schema" / "project-case-database.schema.json"
DEFAULT_CASE_SCHEMA_PATH = ROOT / "schema" / "project.schema.json"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.code} {self.path}: {self.message}"


def _format_path(parts: Iterable[Any]) -> str:
    path = "$"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _walk_source_references(value: Any, path: tuple[Any, ...] = ()):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = (*path, key)
            if key == "source_snapshot_id" and isinstance(child, str) and child:
                yield child, child_path
            elif key == "source_snapshot_ids" and isinstance(child, list):
                for index, snapshot_id in enumerate(child):
                    if isinstance(snapshot_id, str) and snapshot_id:
                        yield snapshot_id, (*child_path, index)
            yield from _walk_source_references(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_source_references(child, (*path, index))


def _contains_status(value: Any, expected: str) -> bool:
    if isinstance(value, dict):
        return any(_contains_status(child, expected) for child in value.values())
    if isinstance(value, list):
        return any(_contains_status(child, expected) for child in value)
    return value == expected


def validate_case_database(
    database: dict[str, Any],
    *,
    database_schema: dict[str, Any],
    case_schema: dict[str, Any],
) -> list[ValidationIssue]:
    """Return all JSON Schema and cross-record validation failures."""
    issues: list[ValidationIssue] = []
    Draft202012Validator.check_schema(case_schema)
    Draft202012Validator.check_schema(database_schema)
    registry = Registry().with_resource(
        case_schema["$id"],
        Resource.from_contents(case_schema),
    )
    validator = Draft202012Validator(
        database_schema,
        registry=registry,
        format_checker=FormatChecker(),
    )
    for error in sorted(validator.iter_errors(database), key=lambda item: list(item.absolute_path)):
        issues.append(
            ValidationIssue(
                "schema",
                _format_path(error.absolute_path),
                error.message,
            )
        )

    cases = database.get("cases", [])
    if not isinstance(cases, list):
        return issues

    case_ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    for duplicate in sorted(_duplicates(value for value in case_ids if isinstance(value, str))):
        issues.append(ValidationIssue("duplicate_case_id", "$.cases", duplicate))

    track_ids: list[str] = []
    snapshot_ids: list[str] = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        details = case.get("public_record", {}).get("program_details", {})
        for track in details.get("funding_tracks", []) if isinstance(details, dict) else []:
            track_id = track.get("track_id") if isinstance(track, dict) else None
            if isinstance(track_id, str) and track_id:
                track_ids.append(track_id)
        evidence = case.get("evidence", {})
        for snapshot in evidence.get("snapshots", []) if isinstance(evidence, dict) else []:
            snapshot_id = snapshot.get("snapshot_id") if isinstance(snapshot, dict) else None
            if isinstance(snapshot_id, str) and snapshot_id:
                snapshot_ids.append(snapshot_id)

    for duplicate in sorted(_duplicates(track_ids)):
        issues.append(ValidationIssue("duplicate_track_id", "$.cases", duplicate))
    for duplicate in sorted(_duplicates(snapshot_ids)):
        issues.append(ValidationIssue("duplicate_snapshot_id", "$.cases", duplicate))

    known_track_ids = set(track_ids)
    known_snapshot_ids = set(snapshot_ids)
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            continue
        case_path = f"$.cases[{index}]"
        funding_track_id = case.get("funding_track_id")
        if funding_track_id and funding_track_id not in known_track_ids:
            issues.append(
                ValidationIssue(
                    "unknown_funding_track",
                    f"{case_path}.funding_track_id",
                    str(funding_track_id),
                )
            )
        if funding_track_id and case.get("record_type") != "grant_case":
            issues.append(
                ValidationIssue(
                    "invalid_funding_track_owner",
                    f"{case_path}.funding_track_id",
                    "only grant_case records may link to a funding track",
                )
            )

        for snapshot_id, relative_path in _walk_source_references(case):
            if snapshot_id not in known_snapshot_ids:
                issues.append(
                    ValidationIssue(
                        "unknown_snapshot_reference",
                        _format_path(("cases", index, *relative_path)),
                        snapshot_id,
                    )
                )
        evidence = case.get("evidence", {})
        if isinstance(evidence, dict):
            for pointer_name in ("grant_application", "voting_record"):
                pointer = evidence.get(pointer_name, {})
                snapshot_id = pointer.get("snapshot_id") if isinstance(pointer, dict) else None
                if snapshot_id and snapshot_id not in known_snapshot_ids:
                    issues.append(
                        ValidationIssue(
                            "unknown_snapshot_reference",
                            f"{case_path}.evidence.{pointer_name}.snapshot_id",
                            str(snapshot_id),
                        )
                    )

        ai_allowed = case.get("ai_review_usage", {}).get("allowed") is True
        if ai_allowed and _contains_status(case, "pending_reconciliation"):
            issues.append(
                ValidationIssue(
                    "unsafe_ai_pending_reconciliation",
                    f"{case_path}.ai_review_usage.allowed",
                    "a case with pending reconciliation cannot be enabled for AI review",
                )
            )

    return issues


def validate_paths(
    database_path: Path = DEFAULT_DATABASE_PATH,
    database_schema_path: Path = DEFAULT_DATABASE_SCHEMA_PATH,
    case_schema_path: Path = DEFAULT_CASE_SCHEMA_PATH,
) -> list[ValidationIssue]:
    database = yaml.safe_load(database_path.read_text(encoding="utf-8")) or {}
    database_schema = json.loads(database_schema_path.read_text(encoding="utf-8"))
    case_schema = json.loads(case_schema_path.read_text(encoding="utf-8"))
    return validate_case_database(
        database,
        database_schema=database_schema,
        case_schema=case_schema,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", nargs="?", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--database-schema", type=Path, default=DEFAULT_DATABASE_SCHEMA_PATH)
    parser.add_argument("--case-schema", type=Path, default=DEFAULT_CASE_SCHEMA_PATH)
    args = parser.parse_args()

    try:
        issues = validate_paths(args.database, args.database_schema, args.case_schema)
    except (OSError, json.JSONDecodeError, yaml.YAMLError, SchemaError) as exc:
        print(f"case database validation could not run: {type(exc).__name__}: {exc}")
        return 2
    if issues:
        for issue in issues:
            print(issue)
        print(f"case database validation failed: {len(issues)} issue(s)")
        return 1
    print(f"case database validation passed: {args.database}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
