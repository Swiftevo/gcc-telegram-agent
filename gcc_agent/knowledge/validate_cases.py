"""Validate the public-goods case database before content is merged or used."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = ROOT / "data" / "project-case-seeds.yaml"
DEFAULT_DATABASE_SCHEMA_PATH = ROOT / "schema" / "project-case-database.schema.json"
DEFAULT_CASE_SCHEMA_PATH = ROOT / "schema" / "project.schema.json"
DEFAULT_MIGRATION_PATH = ROOT / "data" / "project-case-migration.yaml"
DEFAULT_LEGACY_CATALOG_PATH = ROOT / "projects.yaml"

_SOURCE_PRIVACY_PATTERNS = (
    (
        "wallet_address",
        re.compile(r"(?<![0-9A-Fa-f])0x[0-9A-Fa-f]{40}(?![0-9A-Fa-f])"),
    ),
    (
        "row_level_vote_data",
        re.compile(
            r"\|\s*Voter\s*\||\|\s*Voting power\s*\||^##\s+Voter Records",
            re.IGNORECASE | re.MULTILINE,
        ),
    ),
    (
        "recording_access_data",
        re.compile(r"zoom\.us/rec/share|访问密码\s*[:：]|存取密碼\s*[:：]", re.IGNORECASE),
    ),
)


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


def _normalized_text_checksum(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json_checksum(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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

            snapshots = evidence.get("snapshots", [])
            for snapshot_index, snapshot in enumerate(snapshots if isinstance(snapshots, list) else []):
                if not isinstance(snapshot, dict):
                    continue
                processing = snapshot.get("processing", {})
                expected_profile = (
                    "sanitized_public_application"
                    if snapshot.get("source_type") == "grant_application"
                    else "public_source_extract"
                )
                if processing.get("handling_profile") != expected_profile:
                    issues.append(
                        ValidationIssue(
                            "invalid_source_profile",
                            f"{case_path}.evidence.snapshots[{snapshot_index}].processing.handling_profile",
                            f"expected {expected_profile}",
                        )
                    )
                if (
                    processing.get("review_status") != "approved"
                    and processing.get("allowed_uses") != ["evidence_only"]
                ):
                    issues.append(
                        ValidationIssue(
                            "unsafe_unreviewed_source_use",
                            f"{case_path}.evidence.snapshots[{snapshot_index}].processing.allowed_uses",
                            "an unapproved source may only be used as evidence_only",
                        )
                    )

            review_status = case.get("governance", {}).get("review_status")
            if review_status in {"reviewed", "published"}:
                for snapshot_index, snapshot in enumerate(snapshots if isinstance(snapshots, list) else []):
                    if snapshot.get("processing", {}).get("review_status") != "approved":
                        issues.append(
                            ValidationIssue(
                                "unreviewed_source_in_reviewed_case",
                                f"{case_path}.evidence.snapshots[{snapshot_index}].processing.review_status",
                                "every source must be approved before the case is reviewed or published",
                            )
                        )

        public_record = case.get("public_record", {})
        funding = public_record.get("funding", {}) if isinstance(public_record, dict) else {}
        if isinstance(public_record, dict) and "amount_usd" in public_record:
            issues.append(
                ValidationIssue(
                    "deprecated_amount_field",
                    f"{case_path}.public_record.amount_usd",
                    "use the structured requested, governance_approved, and disbursed facts",
                )
            )
        if isinstance(funding, dict):
            for field in ("requested_amount_usd", "approved_amount_usd", "currency"):
                if field in funding:
                    issues.append(
                        ValidationIssue(
                            "deprecated_amount_field",
                            f"{case_path}.public_record.funding.{field}",
                            "do not duplicate structured funding facts",
                        )
                    )
            grant_status = public_record.get("lifecycle_status", {}).get("grant_status")
            disbursed_status = funding.get("disbursed", {}).get("status")
            if grant_status == "funded" and disbursed_status not in {
                "source_reported",
                "owner_confirmed",
                "verified",
            }:
                issues.append(
                    ValidationIssue(
                        "unsupported_funded_status",
                        f"{case_path}.public_record.lifecycle_status.grant_status",
                        "funded requires separate disbursement evidence; use approved when payment is unknown",
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
        if ai_allowed:
            snapshots = case.get("evidence", {}).get("snapshots", [])
            for snapshot_index, snapshot in enumerate(snapshots if isinstance(snapshots, list) else []):
                processing = snapshot.get("processing", {})
                if (
                    processing.get("review_status") != "approved"
                    or "bot_qa" not in processing.get("allowed_uses", [])
                ):
                    issues.append(
                        ValidationIssue(
                            "unsafe_ai_source",
                            f"{case_path}.evidence.snapshots[{snapshot_index}].processing",
                            "AI-enabled cases require approved sources explicitly allowed for bot_qa",
                        )
                    )

    return issues


def validate_repository_data(
    database: dict[str, Any],
    *,
    migration: dict[str, Any],
    legacy_catalog: dict[str, Any],
    root: Path = ROOT,
) -> list[ValidationIssue]:
    """Validate local evidence files and the canonical-to-legacy transition."""
    issues: list[ValidationIssue] = []
    referenced_files: set[str] = set()

    for case_index, case in enumerate(database.get("cases", [])):
        if not isinstance(case, dict):
            continue
        evidence = case.get("evidence", {})
        case_storage_uris: set[str] = set()
        for snapshot_index, snapshot in enumerate(evidence.get("snapshots", [])):
            if not isinstance(snapshot, dict):
                continue
            snapshot_path = f"$.cases[{case_index}].evidence.snapshots[{snapshot_index}]"
            storage_uri = snapshot.get("storage_uri")
            if not isinstance(storage_uri, str) or not storage_uri:
                continue
            normalized_storage_uri = storage_uri.replace("\\", "/")
            referenced_files.add(normalized_storage_uri)
            case_storage_uris.add(normalized_storage_uri)
            stored_path = (root / storage_uri).resolve()
            try:
                stored_path.relative_to(root.resolve())
            except ValueError:
                issues.append(
                    ValidationIssue("unsafe_storage_uri", f"{snapshot_path}.storage_uri", storage_uri)
                )
                continue
            if not stored_path.is_file():
                issues.append(
                    ValidationIssue("missing_source_file", f"{snapshot_path}.storage_uri", storage_uri)
                )
                continue
            expected_checksum = snapshot.get("checksum")
            actual_checksum = _normalized_text_checksum(stored_path)
            if expected_checksum != actual_checksum:
                issues.append(
                    ValidationIssue(
                        "source_checksum_mismatch",
                        f"{snapshot_path}.checksum",
                        f"expected {expected_checksum}; actual {actual_checksum}",
                    )
                )
            content = stored_path.read_text(encoding="utf-8")
            for label, pattern in _SOURCE_PRIVACY_PATTERNS:
                if pattern.search(content):
                    issues.append(
                        ValidationIssue(
                            "unsafe_source_content",
                            f"{snapshot_path}.storage_uri",
                            f"{label} detected in {storage_uri}",
                        )
                    )

        raw_storage_uri = evidence.get("raw_data_status", {}).get("storage_uri")
        if raw_storage_uri and raw_storage_uri.replace("\\", "/") not in case_storage_uris:
            issues.append(
                ValidationIssue(
                    "unregistered_raw_source",
                    f"$.cases[{case_index}].evidence.raw_data_status.storage_uri",
                    "raw data storage must point to a registered snapshot in the same case",
                )
            )

    source_root = root / "data" / "source-snapshots"
    actual_files = {
        str(path.relative_to(root)).replace("\\", "/")
        for path in source_root.rglob("*")
        if path.is_file()
    }
    for orphan in sorted(actual_files - referenced_files):
        issues.append(ValidationIssue("orphan_source_file", "$.source_files", orphan))

    legacy_config = migration.get("legacy_catalog", {})
    legacy_projects = legacy_catalog.get("funded_projects", [])
    legacy_slugs = [
        project.get("slug")
        for project in legacy_projects
        if isinstance(project, dict) and isinstance(project.get("slug"), str)
    ]
    if len(legacy_projects) != legacy_config.get("record_count"):
        issues.append(
            ValidationIssue(
                "legacy_record_count_changed",
                "$.legacy_catalog.record_count",
                f"expected {legacy_config.get('record_count')}; actual {len(legacy_projects)}",
            )
        )
    for duplicate in sorted(_duplicates(legacy_slugs)):
        issues.append(ValidationIssue("duplicate_legacy_slug", "$.legacy_catalog", duplicate))
    actual_digest = _canonical_json_checksum(legacy_catalog)
    if actual_digest != legacy_config.get("canonical_json_sha256"):
        issues.append(
            ValidationIssue(
                "legacy_catalog_digest_changed",
                "$.legacy_catalog.canonical_json_sha256",
                f"expected {legacy_config.get('canonical_json_sha256')}; actual {actual_digest}",
            )
        )

    mappings = migration.get("mappings", [])
    mapped_slugs = [item.get("legacy_slug") for item in mappings if isinstance(item, dict)]
    mapped_case_ids = [item.get("case_id") for item in mappings if isinstance(item, dict)]
    for duplicate in sorted(_duplicates(value for value in mapped_slugs if isinstance(value, str))):
        issues.append(ValidationIssue("duplicate_migration_slug", "$.mappings", duplicate))
    for duplicate in sorted(_duplicates(value for value in mapped_case_ids if isinstance(value, str))):
        issues.append(ValidationIssue("duplicate_migration_case", "$.mappings", duplicate))

    cases_by_id = {
        case.get("case_id"): case
        for case in database.get("cases", [])
        if isinstance(case, dict)
    }
    mapping_by_slug = {
        item.get("legacy_slug"): item
        for item in mappings
        if isinstance(item, dict)
    }
    allowed_mapping_statuses = {
        "migrated_seed",
        "migrated_draft",
        "migrated_reviewed",
        "migrated_published",
        "migrated_deprecated",
        "placeholder",
    }
    for index, item in enumerate(mappings):
        if not isinstance(item, dict):
            continue
        legacy_slug = item.get("legacy_slug")
        case_id = item.get("case_id")
        status = item.get("status")
        if legacy_slug not in legacy_slugs:
            issues.append(
                ValidationIssue("unknown_legacy_slug", f"$.mappings[{index}].legacy_slug", str(legacy_slug))
            )
        if case_id not in cases_by_id:
            issues.append(
                ValidationIssue("unknown_migration_case", f"$.mappings[{index}].case_id", str(case_id))
            )
        if status not in allowed_mapping_statuses:
            issues.append(
                ValidationIssue("invalid_migration_status", f"$.mappings[{index}].status", str(status))
            )
        case = cases_by_id.get(case_id)
        if isinstance(case, dict):
            expected_status = (
                "placeholder"
                if case.get("record_type") == "placeholder"
                else f"migrated_{case.get('governance', {}).get('review_status')}"
            )
            if status != expected_status:
                issues.append(
                    ValidationIssue(
                        "migration_status_mismatch",
                        f"$.mappings[{index}].status",
                        f"expected {expected_status} for {case_id}",
                    )
                )

    for case_id, case in cases_by_id.items():
        legacy_slug = case.get("canonical_project_id")
        if legacy_slug in legacy_slugs:
            mapping = mapping_by_slug.get(legacy_slug)
            if not mapping or mapping.get("case_id") != case_id:
                issues.append(
                    ValidationIssue(
                        "missing_migration_mapping",
                        f"$.cases.{case_id}.canonical_project_id",
                        str(legacy_slug),
                    )
                )

    unmapped_count = len(set(legacy_slugs) - set(mapped_slugs))
    if unmapped_count != legacy_config.get("unmapped_record_count"):
        issues.append(
            ValidationIssue(
                "legacy_unmapped_count_changed",
                "$.legacy_catalog.unmapped_record_count",
                f"expected {legacy_config.get('unmapped_record_count')}; actual {unmapped_count}",
            )
        )

    return issues


def validate_paths(
    database_path: Path = DEFAULT_DATABASE_PATH,
    database_schema_path: Path = DEFAULT_DATABASE_SCHEMA_PATH,
    case_schema_path: Path = DEFAULT_CASE_SCHEMA_PATH,
    migration_path: Path = DEFAULT_MIGRATION_PATH,
    legacy_catalog_path: Path = DEFAULT_LEGACY_CATALOG_PATH,
) -> list[ValidationIssue]:
    database = yaml.safe_load(database_path.read_text(encoding="utf-8")) or {}
    database_schema = json.loads(database_schema_path.read_text(encoding="utf-8"))
    case_schema = json.loads(case_schema_path.read_text(encoding="utf-8"))
    migration = yaml.safe_load(migration_path.read_text(encoding="utf-8")) or {}
    legacy_catalog = yaml.safe_load(legacy_catalog_path.read_text(encoding="utf-8")) or {}
    issues = validate_case_database(
        database,
        database_schema=database_schema,
        case_schema=case_schema,
    )
    issues.extend(
        validate_repository_data(
            database,
            migration=migration,
            legacy_catalog=legacy_catalog,
            root=ROOT,
        )
    )
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", nargs="?", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--database-schema", type=Path, default=DEFAULT_DATABASE_SCHEMA_PATH)
    parser.add_argument("--case-schema", type=Path, default=DEFAULT_CASE_SCHEMA_PATH)
    parser.add_argument("--migration-ledger", type=Path, default=DEFAULT_MIGRATION_PATH)
    parser.add_argument("--legacy-catalog", type=Path, default=DEFAULT_LEGACY_CATALOG_PATH)
    args = parser.parse_args()

    try:
        issues = validate_paths(
            args.database,
            args.database_schema,
            args.case_schema,
            args.migration_ledger,
            args.legacy_catalog,
        )
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
