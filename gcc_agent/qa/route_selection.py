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
CLARIFICATION_REPLIES = {
    "zh-TW": "這個問題涉及不同的資料範圍或資助計劃。請指定想查哪一個項目／年度，或分開提問；我才可以用相應的已審核來源回答。",
    "zh-CN": "这个问题涉及不同的资料范围或资助计划。请指定想查哪一个项目／年度，或分开提问；我才可以用相应的已审核来源回答。",
    "en": "This question spans different evidence scopes or grant programmes. Please name one project and year, or ask about each separately, so I can use the corresponding reviewed source.",
}


def clarification_reply(lang: str) -> str:
    return CLARIFICATION_REPLIES.get(lang, CLARIFICATION_REPLIES["zh-TW"])


def last_clarified_question(previous_messages: list[dict] | None) -> str | None:
    """Recover only the immediately preceding question after our fixed reply."""
    if not previous_messages or len(previous_messages) < 2:
        return None
    user, assistant = previous_messages[-2:]
    if (
        user.get("role") == "user"
        and assistant.get("role") == "assistant"
        and assistant.get("content") in CLARIFICATION_REPLIES.values()
    ):
        return str(user.get("content", "")) or None
    return None


def choose_qa_source(query: str, candidates: list[SourceCandidate]) -> str | None:
    """Resolve named subjects, report metrics and general rules consistently."""
    by_name = {candidate.name: candidate for candidate in candidates}
    if "comparison" in by_name:
        return "comparison"
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
