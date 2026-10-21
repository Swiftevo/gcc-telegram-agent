"""Load and select the explicitly approved GCC history projections."""

from copy import deepcopy
import logging
import os
from typing import Optional

import yaml


logger = logging.getLogger(__name__)
PUBLIC_HISTORY_PATH = os.getenv(
    "PUBLIC_HISTORY_PATH",
    "data/gcc-public-history.yaml",
)
HISTORY_SCHEMA_VERSION = "0.3.0"
_cached_history_registry: Optional[dict] = None

_RUNTIME_RECORD_FIELDS = (
    "projection_id",
    "topic",
    "language",
    "scope",
    "question_examples",
    "answer_text",
    "citation",
)
_HISTORICAL_CONTEXT_TERMS = (
    "歷史",
    "历史",
    "過往",
    "过往",
    "以前",
    "當時",
    "当时",
    "曾經",
    "曾经",
    "報告",
    "报告",
    "2022",
    "2023",
    "2024",
    "2025",
    "history",
    "historical",
    "previously",
    "in the past",
    "report",
)
_CURRENT_OR_ACTION_TERMS = (
    "現在",
    "现在",
    "目前",
    "現行",
    "现行",
    "最新",
    "今年",
    "申請",
    "申请",
    "報名",
    "报名",
    "加入",
    "current",
    "currently",
    "latest",
    "today",
    "apply",
    "application",
    "register",
    "join",
    "available",
    "open now",
)
_SOURCE_TERMS = (
    "來源",
    "来源",
    "依據",
    "依据",
    "哪裡寫",
    "哪里写",
    "source",
    "citation",
    "where is this documented",
)


def load_history_registry(force_reload: bool = False) -> dict:
    """Load the registry without ever opening its cleaned full-text extract."""
    global _cached_history_registry
    if _cached_history_registry is not None and not force_reload:
        return _cached_history_registry
    if not os.path.exists(PUBLIC_HISTORY_PATH):
        logger.warning("public history registry missing path=%s", PUBLIC_HISTORY_PATH)
        _cached_history_registry = {}
        return _cached_history_registry
    try:
        with open(PUBLIC_HISTORY_PATH, encoding="utf-8") as source:
            value = yaml.safe_load(source) or {}
    except Exception:
        logger.exception("public history registry failed to load")
        value = {}
    _cached_history_registry = value if isinstance(value, dict) else {}
    return _cached_history_registry


def _approved_sources_and_sections(registry: dict) -> tuple[dict, dict]:
    approved_sources: dict[str, dict] = {}
    sections: dict[str, dict[str, dict]] = {}
    for source in registry.get("sources", []):
        if not isinstance(source, dict):
            continue
        source_id = source.get("source_id")
        processing = source.get("processing", {})
        if (
            isinstance(source_id, str)
            and source.get("access_level") == "public"
            and isinstance(processing, dict)
            and processing.get("sanitization_status") == "human_reviewed"
            and processing.get("review_status") == "approved"
            and "bot_qa" in processing.get("allowed_uses", [])
            and processing.get("reviewed_at")
            and processing.get("reviewed_by_role")
            and str(source.get("source_url", "")).startswith("https://")
        ):
            approved_sources[source_id] = source
            sections[source_id] = {
                section.get("section_id"): section
                for section in source.get("sections", [])
                if isinstance(section, dict)
                and isinstance(section.get("section_id"), str)
            }
    return approved_sources, sections


def is_history_projection_eligible(
    projection: dict,
    *,
    approved_sources: dict,
    sections: dict,
) -> bool:
    """Apply the production history gate independently of merge-time validation."""
    if not isinstance(projection, dict):
        return False
    review = projection.get("review", {})
    answer = projection.get("answer_text", "")
    citation = projection.get("citation", {})
    if (
        projection.get("scope") != "historical_only"
        or projection.get("language") != "zh-Hant"
        or not projection.get("projection_id")
        or not isinstance(answer, str)
        or not answer.strip()
        or ("歷史" not in answer and "報告期" not in answer)
        or (
            ("50.4%" in answer or "50.4％" in answer)
            and not any(
                boundary in answer
                for boundary in (
                    "沒有交代分母",
                    "没有交代分母",
                    "未交代分母",
                    "分母或計算方法",
                    "分母或计算方法",
                )
            )
        )
        or not isinstance(review, dict)
        or review.get("status") != "approved"
        or not review.get("reviewed_at")
        or not review.get("reviewed_by_role")
        or not isinstance(citation, dict)
        or not str(citation.get("url", "")).startswith("https://")
    ):
        return False

    references = projection.get("source_references", [])
    if not isinstance(references, list) or not references:
        return False
    for reference in references:
        if not isinstance(reference, dict):
            return False
        source_id = reference.get("source_id")
        source = approved_sources.get(source_id)
        if source is None or citation.get("url") != source.get("source_url"):
            return False
        section_ids = reference.get("section_ids", [])
        if not isinstance(section_ids, list) or not section_ids:
            return False
        for section_id in section_ids:
            section = sections.get(source_id, {}).get(section_id)
            if section is None or section.get("classification") == "excluded_from_bot":
                return False
    return True


def load_bot_history_projections(force_reload: bool = False) -> list[dict]:
    """Return the minimal runtime allowlist; fail closed on any registry gate."""
    registry = load_history_registry(force_reload)
    runtime = registry.get("runtime", {})
    if (
        registry.get("schema_version") != HISTORY_SCHEMA_VERSION
        or not isinstance(runtime, dict)
        or runtime.get("connected") is not True
    ):
        return []
    approved_sources, sections = _approved_sources_and_sections(registry)
    records = []
    for projection in registry.get("approved_projections", []):
        if is_history_projection_eligible(
            projection,
            approved_sources=approved_sources,
            sections=sections,
        ):
            records.append(
                {
                    field: deepcopy(projection[field])
                    for field in _RUNTIME_RECORD_FIELDS
                    if field in projection
                }
            )
    return records


def _contains(value: str, terms: tuple[str, ...]) -> bool:
    return any(term in value for term in terms)


def _matched_projection_id(value: str) -> str | None:
    historical = _contains(value, _HISTORICAL_CONTEXT_TERMS)
    current_or_action = _contains(value, _CURRENT_OR_ACTION_TERMS)

    historical = historical and not current_or_action

    programme = _contains(
        value,
        ("eth city", "高校 web3", "高校web3", "university web3"),
    )
    reach = _contains(
        value,
        ("覆蓋", "覆盖", "地區", "地区", "節點", "节点", "region", "node", "universit"),
    )
    if programme and reach and not current_or_action:
        return "gcc-historical-programme-reach"

    builder = "builder" in value and ("flight" in value or "機票" in value or "机票" in value)
    builder = builder or "機票計劃" in value or "机票计划" in value
    if builder and not current_or_action:
        return "gcc-builder-flight-history"

    if not historical:
        return None
    if _contains(
        value,
        (
            "捐贈數據",
            "捐赠数据",
            "兩年數據",
            "两年数据",
            "捐贈金額",
            "捐赠金额",
            "總捐贈",
            "总捐赠",
            "總資助金額",
            "总资助金额",
            "營運開支",
            "运营开支",
            "開支率",
            "开支率",
            "里程碑完成率",
            "捐了多少",
            "捐贈了多少",
            "捐赠了多少",
            "115 萬",
            "115万",
            "1.15m",
            "donation data",
            "donation figure",
            "donation amount",
            "operating expense",
            "regional amount",
            "regional distribution",
            "milestone completion",
        ),
    ):
        return "gcc-historical-aggregate-data"
    if _contains(value, ("治理", "投委", "流程", "governance", "committee", "process")):
        return "gcc-historical-governance-process"
    if _contains(value, ("項目", "项目", "類別", "类别", "project", "catalog", "category")):
        return "gcc-historical-project-catalogue"
    if _contains(value, ("方向", "基金", "支持", "fund", "funding", "support")):
        return "gcc-historical-funding-directions"
    if _contains(value, ("發展", "发展", "做過", "做过", "歷程", "历程", "timeline", "develop")):
        return "gcc-history-2022-2025"
    return None


def _projection_from_recent_answer(
    projections: list[dict], previous_messages: list[dict] | None
) -> dict | None:
    if not previous_messages:
        return None
    recent_assistant = [
        str(message.get("content", ""))
        for message in previous_messages[-4:]
        if message.get("role") == "assistant"
    ]
    for projection in projections:
        answer = str(projection.get("answer_text", ""))
        if answer and any(answer in message for message in recent_assistant):
            return projection
    return None


def select_history_projection(
    query: str,
    *,
    previous_messages: list[dict] | None = None,
    force_reload: bool = False,
) -> dict | None:
    """Select at most one fixed answer by explicit, deterministic intent rules."""
    value = query.casefold().strip()
    if not value:
        return None
    projections = load_bot_history_projections(force_reload)
    if not projections:
        return None
    if _contains(value, _SOURCE_TERMS):
        recent = _projection_from_recent_answer(projections, previous_messages)
        if recent is not None:
            return recent
    projection_id = _matched_projection_id(value)
    if projection_id is None:
        return None
    return next(
        (
            projection
            for projection in projections
            if projection.get("projection_id") == projection_id
        ),
        None,
    )
