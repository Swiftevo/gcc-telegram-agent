"""Validate the non-runtime GCC public-history evidence registry."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = ROOT / "data" / "gcc-public-history.yaml"
DEFAULT_SCHEMA_PATH = ROOT / "schema" / "gcc-public-history.schema.json"

_UNSAFE_CONTENT_PATTERNS = (
    ("wallet_address", re.compile(r"(?<![0-9A-Fa-f])0x[0-9A-Fa-f]{40}(?![0-9A-Fa-f])")),
    ("row_level_vote_data", re.compile(r"\|\s*Voter\s*\||\|\s*Voting power\s*\|", re.I)),
    (
        "recording_access_data",
        re.compile(r"zoom\.us/rec/share|访问密码\s*[:：]|存取密碼\s*[:：]", re.I),
    ),
)
_REQUIRED_EXTRACT_MARKERS = (
    "Historical source - not current policy.",
    "pending_reconciliation",
    "not a complete transcription",
)


@dataclass(frozen=True)
class HistoryValidationIssue:
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


def _normalized_text_checksum(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_history_registry(
    registry: dict[str, Any], *, schema: dict[str, Any]
) -> list[HistoryValidationIssue]:
    """Validate the registry schema and identifiers without reading source files."""
    issues: list[HistoryValidationIssue] = []
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for error in sorted(validator.iter_errors(registry), key=lambda item: list(item.absolute_path)):
        issues.append(
            HistoryValidationIssue("schema", _format_path(error.absolute_path), error.message)
        )

    sources = registry.get("sources", [])
    if not isinstance(sources, list):
        return issues
    source_ids = [item.get("source_id") for item in sources if isinstance(item, dict)]
    for duplicate in sorted(_duplicates(value for value in source_ids if isinstance(value, str))):
        issues.append(HistoryValidationIssue("duplicate_source_id", "$.sources", duplicate))

    section_ids: list[str] = []
    for source_index, source in enumerate(sources):
        if not isinstance(source, dict):
            continue
        for section_index, section in enumerate(source.get("sections", [])):
            if not isinstance(section, dict):
                continue
            section_id = section.get("section_id")
            if isinstance(section_id, str):
                section_ids.append(section_id)
            pages = section.get("pages", {})
            if isinstance(pages, dict) and isinstance(pages.get("start"), int) and isinstance(
                pages.get("end"), int
            ):
                if pages["end"] < pages["start"]:
                    issues.append(
                        HistoryValidationIssue(
                            "invalid_page_range",
                            f"$.sources[{source_index}].sections[{section_index}].pages",
                            "end must be greater than or equal to start",
                        )
                    )
            if section.get("classification") == "time_bounded_aggregate":
                scope = section.get("temporal_scope", {})
                if not isinstance(scope, dict) or not scope.get("start") or not scope.get("end"):
                    issues.append(
                        HistoryValidationIssue(
                            "missing_aggregate_period",
                            f"$.sources[{source_index}].sections[{section_index}].temporal_scope",
                            "time-bounded aggregates require explicit start and end",
                        )
                    )

    for duplicate in sorted(_duplicates(section_ids)):
        issues.append(HistoryValidationIssue("duplicate_section_id", "$.sources[].sections", duplicate))
    return issues


def validate_history_repository(
    registry: dict[str, Any], *, root: Path = ROOT
) -> list[HistoryValidationIssue]:
    """Validate local extracts, checksums, use gates and content-minimization markers."""
    issues: list[HistoryValidationIssue] = []
    source_root = (root / "data" / "source-snapshots").resolve()
    for source_index, source in enumerate(registry.get("sources", [])):
        if not isinstance(source, dict):
            continue
        source_path = f"$.sources[{source_index}]"
        processing = source.get("processing", {})
        if isinstance(processing, dict) and processing.get("review_status") != "approved":
            if processing.get("allowed_uses") != ["evidence_only"]:
                issues.append(
                    HistoryValidationIssue(
                        "unsafe_unreviewed_source_use",
                        f"{source_path}.processing.allowed_uses",
                        "an unapproved history source may only be evidence_only",
                    )
                )

        extract = source.get("extract", {})
        storage_uri = extract.get("storage_uri") if isinstance(extract, dict) else None
        if not isinstance(storage_uri, str) or not storage_uri:
            continue
        stored_path = (root / storage_uri).resolve()
        try:
            stored_path.relative_to(source_root)
        except ValueError:
            issues.append(
                HistoryValidationIssue(
                    "unsafe_storage_uri", f"{source_path}.extract.storage_uri", storage_uri
                )
            )
            continue
        if not stored_path.is_file():
            issues.append(
                HistoryValidationIssue(
                    "missing_extract", f"{source_path}.extract.storage_uri", storage_uri
                )
            )
            continue

        expected_checksum = extract.get("checksum")
        actual_checksum = _normalized_text_checksum(stored_path)
        if expected_checksum != actual_checksum:
            issues.append(
                HistoryValidationIssue(
                    "extract_checksum_mismatch",
                    f"{source_path}.extract.checksum",
                    f"expected {expected_checksum}; actual {actual_checksum}",
                )
            )
        content = stored_path.read_text(encoding="utf-8")
        for marker in _REQUIRED_EXTRACT_MARKERS:
            if marker not in content:
                issues.append(
                    HistoryValidationIssue(
                        "missing_extract_boundary",
                        f"{source_path}.extract.storage_uri",
                        f"required marker missing: {marker}",
                    )
                )
        source_url = source.get("source_url")
        if isinstance(source_url, str) and source_url not in content:
            issues.append(
                HistoryValidationIssue(
                    "missing_source_url",
                    f"{source_path}.extract.storage_uri",
                    "the cleaned extract must preserve its public source URL",
                )
            )
        for label, pattern in _UNSAFE_CONTENT_PATTERNS:
            if pattern.search(content):
                issues.append(
                    HistoryValidationIssue(
                        "unsafe_extract_content",
                        f"{source_path}.extract.storage_uri",
                        f"{label} detected in {storage_uri}",
                    )
                )
    return issues


def validate_paths(
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
) -> list[HistoryValidationIssue]:
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return [
        *validate_history_registry(registry, schema=schema),
        *validate_history_repository(registry, root=registry_path.resolve().parents[1]),
    ]


def main() -> int:
    issues = validate_paths()
    if issues:
        print(f"GCC public-history validation failed with {len(issues)} issue(s):")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("GCC public-history validation passed: source layer is evidence-only and runtime-disconnected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
