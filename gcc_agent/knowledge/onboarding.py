"""Load and validate the owner-supplied onboarding content foundation."""

from copy import deepcopy
import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_ONBOARDING_PATH = Path(
    os.getenv("ONBOARDING_PATH", "data/onboarding.yaml")
)
SCHEMA_VERSION = "0.1.0"
APPROVED_STATUS = "approved_for_integration"
ALLOWED_STATUSES = {"draft", APPROVED_STATUS, "retired"}
INTERNAL_SOURCE_HOSTS = ("feishu.cn", "feishu.com")


def _require_mapping(value: Any, field: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a mapping")
    return value


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _walk_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_strings(key)
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)


def validate_onboarding(data: Any) -> dict:
    """Validate the content contract without enabling it in the Bot runtime."""
    root = _require_mapping(data, "onboarding")
    if root.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")

    runtime = _require_mapping(root.get("runtime"), "runtime")
    if runtime.get("connected") is not False:
        raise ValueError("the content-only baseline must remain disconnected")

    audience = _require_mapping(root.get("audience"), "audience")
    if audience.get("eligibility") != "configured_group_members":
        raise ValueError("onboarding audience must be configured group members")
    if audience.get("navigation_buttons") != "none":
        raise ValueError("the lightweight onboarding baseline cannot require buttons")

    provenance = _require_mapping(root.get("provenance"), "provenance")
    if provenance.get("automatic_sync") is not False:
        raise ValueError("automatic internal-document sync is not allowed")
    if provenance.get("internal_source_urls_stored") is not False:
        raise ValueError("internal source URLs cannot be stored")
    if provenance.get("available_locales") != ["zh-CN"]:
        raise ValueError("the approved baseline currently contains only zh-CN")

    topics = root.get("topics")
    if not isinstance(topics, list) or not topics:
        raise ValueError("topics must be a non-empty list")

    topic_ids: set[str] = set()
    journey_ids: set[str] = set()
    for index, topic_value in enumerate(topics):
        topic = _require_mapping(topic_value, f"topics[{index}]")
        topic_id = _require_nonempty_string(topic.get("id"), f"topics[{index}].id")
        if topic_id in topic_ids:
            raise ValueError(f"duplicate topic id: {topic_id}")
        topic_ids.add(topic_id)

        journey_ids.add(
            _require_nonempty_string(
                topic.get("journey_id"), f"topics[{index}].journey_id"
            )
        )
        if topic.get("status") not in ALLOWED_STATUSES:
            raise ValueError(f"invalid topic status: {topic.get('status')}")

        questions = topic.get("suggested_questions")
        if not isinstance(questions, list) or not questions:
            raise ValueError(f"{topic_id} must have suggested questions")

        content = _require_mapping(topic.get("content"), f"{topic_id}.content")
        if set(content) != {"zh-CN"}:
            raise ValueError(f"{topic_id} must contain only the approved zh-CN locale")
        locale = _require_mapping(content["zh-CN"], f"{topic_id}.content.zh-CN")
        for field in ("title", "short_answer", "next_prompt"):
            _require_nonempty_string(locale.get(field), f"{topic_id}.{field}")
        for field in ("paragraphs", "bullets", "links"):
            if not isinstance(locale.get(field), list):
                raise ValueError(f"{topic_id}.{field} must be a list")

    journey = root.get("journey")
    if not isinstance(journey, list) or not journey:
        raise ValueError("journey must be a non-empty list")
    referenced_topics: list[str] = []
    defined_journeys: set[str] = set()
    for index, stage_value in enumerate(journey):
        stage = _require_mapping(stage_value, f"journey[{index}]")
        stage_id = _require_nonempty_string(stage.get("id"), f"journey[{index}].id")
        if stage_id in defined_journeys:
            raise ValueError(f"duplicate journey id: {stage_id}")
        defined_journeys.add(stage_id)
        refs = stage.get("topic_ids")
        if not isinstance(refs, list) or not refs:
            raise ValueError(f"journey {stage_id} must reference topics")
        referenced_topics.extend(refs)

    if journey_ids != defined_journeys:
        raise ValueError("topic journey_id values must match defined journey stages")
    if len(referenced_topics) != len(set(referenced_topics)):
        raise ValueError("journey topic references must be unique")
    if set(referenced_topics) != topic_ids:
        raise ValueError("journey must reference every topic exactly once")

    for text in _walk_strings(root):
        lowered = text.lower()
        if any(host in lowered for host in INTERNAL_SOURCE_HOSTS):
            raise ValueError("internal Feishu URLs cannot be stored in onboarding content")

    return root


def load_onboarding(path: str | Path | None = None) -> dict:
    """Load one validated onboarding document from disk."""
    source_path = Path(path) if path is not None else DEFAULT_ONBOARDING_PATH
    with source_path.open(encoding="utf-8") as source:
        payload = yaml.safe_load(source) or {}
    return validate_onboarding(payload)


def approved_topics(data: dict | None = None) -> list[dict]:
    """Return defensive copies of content approved for later runtime integration."""
    payload = validate_onboarding(data) if data is not None else load_onboarding()
    return [
        deepcopy(topic)
        for topic in payload["topics"]
        if topic["status"] == APPROVED_STATUS
    ]
