"""Validate the GCC public-history evidence and approved runtime projections."""

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
    sources_by_id: dict[str, dict[str, Any]] = {}
    sections_by_source: dict[str, dict[str, dict[str, Any]]] = {}
    for source_index, source in enumerate(sources):
        if not isinstance(source, dict):
            continue
        source_id = source.get("source_id")
        if isinstance(source_id, str):
            sources_by_id[source_id] = source
            sections_by_source[source_id] = {}
        processing = source.get("processing", {})
        if isinstance(processing, dict) and processing.get("review_status") == "approved":
            if processing.get("sanitization_status") != "human_reviewed":
                issues.append(
                    HistoryValidationIssue(
                        "unsafe_approved_source",
                        f"$.sources[{source_index}].processing.sanitization_status",
                        "an approved history source must be human reviewed",
                    )
                )
            if set(processing.get("allowed_uses", [])) != {"evidence_only", "bot_qa"}:
                issues.append(
                    HistoryValidationIssue(
                        "unsafe_approved_source",
                        f"$.sources[{source_index}].processing.allowed_uses",
                        "an approved history source must retain evidence_only and explicitly allow bot_qa",
                    )
                )
        for section_index, section in enumerate(source.get("sections", [])):
            if not isinstance(section, dict):
                continue
            section_id = section.get("section_id")
            if isinstance(section_id, str):
                section_ids.append(section_id)
                if isinstance(source_id, str):
                    sections_by_source[source_id][section_id] = section
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

    projections = registry.get("approved_projections", [])
    projection_ids = [
        item.get("projection_id") for item in projections if isinstance(item, dict)
    ]
    for duplicate in sorted(
        _duplicates(value for value in projection_ids if isinstance(value, str))
    ):
        issues.append(
            HistoryValidationIssue("duplicate_projection_id", "$.approved_projections", duplicate)
        )
    for projection_index, projection in enumerate(projections):
        if not isinstance(projection, dict):
            continue
        projection_path = f"$.approved_projections[{projection_index}]"
        answer_text = projection.get("answer_text")
        if isinstance(answer_text, str):
            if "歷史" not in answer_text and "報告期" not in answer_text:
                issues.append(
                    HistoryValidationIssue(
                        "missing_historical_boundary",
                        f"{projection_path}.answer_text",
                        "an approved projection must state its historical scope",
                    )
                )
            if (
                ("50.4%" in answer_text or "50.4％" in answer_text)
                and not any(
                    boundary in answer_text
                    for boundary in (
                        "沒有交代分母",
                        "没有交代分母",
                        "未交代分母",
                        "分母或計算方法",
                        "分母或计算方法",
                    )
                )
            ):
                issues.append(
                    HistoryValidationIssue(
                        "unbounded_selection_rate",
                        f"{projection_path}.answer_text",
                        "the report-stated 50.4% selection rate requires an explicit undefined-denominator boundary",
                    )
                )
        citation = projection.get("citation")
        citation_url = citation.get("url") if isinstance(citation, dict) else None
        source_references = projection.get("source_references")
        for reference_index, reference in enumerate(
            source_references if isinstance(source_references, list) else []
        ):
            if not isinstance(reference, dict):
                continue
            reference_path = f"{projection_path}.source_references[{reference_index}]"
            referenced_source_id = reference.get("source_id")
            referenced_source = sources_by_id.get(referenced_source_id)
            if referenced_source is None:
                issues.append(
                    HistoryValidationIssue(
                        "unknown_projection_source", f"{reference_path}.source_id", str(referenced_source_id)
                    )
                )
                continue
            source_processing = referenced_source.get("processing")
            if not isinstance(source_processing, dict):
                source_processing = {}
            if (
                source_processing.get("review_status") != "approved"
                or "bot_qa" not in source_processing.get("allowed_uses", [])
            ):
                issues.append(
                    HistoryValidationIssue(
                        "unapproved_projection_source",
                        f"{reference_path}.source_id",
                        "approved projections require an approved source with bot_qa allowed",
                    )
                )
            if citation_url != referenced_source.get("source_url"):
                issues.append(
                    HistoryValidationIssue(
                        "projection_citation_mismatch",
                        f"{projection_path}.citation.url",
                        "citation URL must match the registered public source",
                    )
                )
            known_sections = sections_by_source.get(referenced_source_id, {})
            referenced_section_ids = reference.get("section_ids")
            for section_reference_index, referenced_section_id in enumerate(
                referenced_section_ids if isinstance(referenced_section_ids, list) else []
            ):
                section = known_sections.get(referenced_section_id)
                section_reference_path = (
                    f"{reference_path}.section_ids[{section_reference_index}]"
                )
                if section is None:
                    issues.append(
                        HistoryValidationIssue(
                            "unknown_projection_section",
                            section_reference_path,
                            str(referenced_section_id),
                        )
                    )
                elif section.get("classification") == "excluded_from_bot":
                    issues.append(
                        HistoryValidationIssue(
                            "excluded_projection_section",
                            section_reference_path,
                            "excluded_from_bot sections cannot support a projection",
                        )
                    )
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
    print("GCC public-history validation passed: approved projections are connected through the deterministic runtime gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
