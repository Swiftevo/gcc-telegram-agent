"""Choose one reviewed QA source after all applicable sources have been found.

The route is based on the subject and scope of the evidence, not the order in
which a keyword happened to be checked.  Reply formatting stays with each
source's existing formatter.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceCandidate:
    name: str
    scope: str
    explicit_subject: bool = False
    detail: str = ""


_REPORT_CUES = ("報告", "报告", "2023–2025 公共物品之路", "2023-2025 公共物品之路", "report")
_REPORT_METRICS = {"gcc-historical-programme-reach", "gcc-builder-flight-history"}


def choose_qa_source(query: str, candidates: list[SourceCandidate]) -> str | None:
    """Resolve named subjects, report metrics and general rules consistently."""
    by_name = {candidate.name: candidate for candidate in candidates}
    case = next((candidate for candidate in candidates if candidate.scope == "named_reviewed_case"), None)
    history = by_name.get("history")
    project = next((candidate for candidate in candidates if candidate.scope == "named_project_link"), None)
    current = [
        candidate
        for candidate in candidates
        if candidate.scope == "current_programme" and candidate.explicit_subject
    ]

    # A single answer from either programme would silently omit the other.
    if (case and current) or len(current) > 1:
        return "clarify"

    if case:
        if history and history.detail in _REPORT_METRICS:
            return "history"
        if history and any(cue in query.casefold() for cue in _REPORT_CUES):
            return "clarify"
        return "case"

    if current:
        return current[0].name

    if project and project.explicit_subject:
        if history and history.detail in _REPORT_METRICS:
            return "history"
        if history and any(cue in query.casefold() for cue in _REPORT_CUES):
            return "history"
        return "project"

    for name in ("history", "university", "cohort4", "fact", "project"):
        if name in by_name:
            return name
    return None
