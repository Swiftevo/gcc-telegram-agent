"""Reviewed, programme-scoped answers for the 2026 university Builder plan."""

from dataclasses import dataclass
from pathlib import Path
import logging

import yaml


logger = logging.getLogger(__name__)
_PATH = Path(__file__).resolve().parents[2] / "data" / "university-builder-2026.yaml"


@dataclass(frozen=True)
class UniversityAnswer:
    matched: bool
    reply: str = ""
    answer_type: str = ""


def _has(value: str, *terms: str) -> bool:
    return any(term in value for term in terms)


def _load_approved() -> dict | None:
    """Fail closed on unreviewed data or broken source/essential programme facts."""
    try:
        with _PATH.open(encoding="utf-8") as source:
            data = yaml.safe_load(source)
        if not isinstance(data, dict) or data.get("schema_version") != "1.0":
            return None
        review, source = data.get("review"), data.get("source")
        if not isinstance(review, dict) or not isinstance(source, dict):
            return None
        if (
            data.get("programme_id") != "university-builder-2026"
            or review.get("status") != "approved"
            or review.get("access_level") != "public"
            or "bot_qa" not in review.get("allowed_uses", [])
            or not review.get("reviewed_at")
            or not review.get("reviewed_by_role")
            or not all(str(source.get(key, "")).startswith("https://") for key in ("application_url", "appendix_url"))
        ):
            return None
        required = {
            "scope": {"audience", "separation", "period"},
            "application": {"quarterly", "exploration", "alumni", "operations"},
            "categories": {"operations", "workshop", "sharing", "exploration", "alumni", "open"},
            "source_discrepancies": {"alumni", "operations"},
        }
        for key, keys in required.items():
            section = data.get(key)
            if not isinstance(section, dict) or not keys.issubset(section) or not all(
                isinstance(item, str) and item.strip() for item in section.values()
            ):
                return None
        if set(data["categories"]) != required["categories"]:
            return None
        if not isinstance(data.get("criteria"), list) or len(data["criteria"]) != 5:
            return None
        if not all(isinstance(item, str) and item.strip() for item in data["criteria"]):
            return None
        for key in ("focus", "exclusions", "deliverables"):
            if not isinstance(data.get(key), list) or not data[key] or not all(
                isinstance(item, str) and item.strip() for item in data[key]
            ):
                return None
        return data
    except (OSError, TypeError, ValueError, yaml.YAMLError):
        logger.exception("approved university Builder content unavailable")
        return None


def load_approved_university_plan() -> dict | None:
    """Expose only content that has passed this programme's existing QA gate."""
    return _load_approved()


def select_university_answer(text: str, lang: str = "zh-TW") -> UniversityAnswer:
    """Answer current university-plan intents without absorbing history or ETH City."""
    value = text.casefold().strip()
    university = _has(value, "高校", "大学", "大學", "university", "campus", "校友", "链协", "鏈協")
    builder = _has(value, "builder", "建设者计划", "建設者計劃")
    historic = _has(value, "2025", "2024", "历史", "歷史", "往年", "以前", "去年")
    explicit_current = _has(value, "2026", "今年", "今年度", "新计划", "新計劃", "目前", "现在", "現在")
    if not (university or (builder and "gcc" in value)) or (historic and not explicit_current):
        return UniversityAnswer(False)
    if _has(value, "eth city", "ethcity", "城市级", "城市級", "黑客松") and not university:
        return UniversityAnswer(False)
    # General questions about current GCC policy belong to the public-fund route.
    if not university and not _has(value, "高校 builder", "university builder"):
        return UniversityAnswer(False)
    data = _load_approved()
    if data is None:
        return UniversityAnswer(False)
    scope, application, categories, source = (
        data["scope"], data["application"], data["categories"], data["source"]
    )
    discrepancies = data["source_discrepancies"]
    if _has(value, "评分", "評分", "权重", "權重", "评审", "評審", "标准", "標準", "criteria"):
        kind = "criteria"
        body = "高校 Builder 计划 2026 的评审权重：\n• " + "\n• ".join(data["criteria"])
        body += "\n这些只适用于本计划，不是 Cohort 4 或 GCC 所有资助的通用评分；最终由人工评审。"
    elif _has(value, "校友", "alumni"):
        kind = "alumni"
        body = f"{categories['alumni']}\n{application['alumni']}\n注意：{discrepancies['alumni']}申请前请向 GCC 确认最终额度。"
    elif _has(value, "日常运营", "日常運營", "运营", "營運", "operations"):
        kind = "operations"
        body = f"{categories['operations']}\n{application['operations']}\n注意：{discrepancies['operations']}"
    elif _has(value, "金额", "金額", "额度", "額度", "上限", "多少", "六类", "六類", "类别", "類別", "类型", "類型", "categories"):
        kind = "categories"
        body = "高校 Builder 计划 2026 的六类资助上限：\n• " + "\n• ".join(categories.values())
        body += f"\n注意：{discrepancies['alumni']}申请前请向 GCC 确认最终额度。"
    elif _has(value, "何时", "何時", "什么时候", "幾時", "几时", "截止", "日期", "时间", "時間", "季度", "学期", "學期", "随时", "隨時", "deadline", "when"):
        kind = "schedule"
        body = f"{scope['period']}\n• {application['quarterly']}\n• {application['exploration']}\n• {application['alumni']}\n• {application['operations']}\n这是公告申请节奏，不保证某一批次仍开放；提交前请查看表格。"
    elif _has(value, "拨款", "撥款", "到账", "到賬", "付款", "milestone", "里程碑"):
        kind = "payments"
        body = "本计划按项目资助、约定里程碑后分期核验和拨款；不同类别节奏不同，日常运营按季度凭票据报销。公告与申请表不证明任何个别项目已经获批、完成里程碑或实际到账。"
    elif _has(value, "不资助", "不資助", "不支持", "排除", "不能申请", "不能申請", "excluded"):
        kind = "exclusions"
        body = "本计划不资助：\n• " + "\n• ".join(data["exclusions"])
    elif _has(value, "交付", "成果", "产出", "產出", "workshop", "探索类", "探索類", "deliverable"):
        kind = "deliverables"
        body = "本计划的公开交付要求：\n• " + "\n• ".join(data["deliverables"])
    elif _has(value, "方向", "课题", "課題", "支持什么", "支持什麼", "focus"):
        kind = "focus"
        body = "高校 Builder 计划 2026 关注：\n• " + "\n• ".join(data["focus"])
    elif _has(value, "谁", "誰", "资格", "資格", "要求", "可以申请", "可以申請", "eligible"):
        kind = "eligibility"
        body = f"{scope['audience']}\n{scope['separation']}"
    else:
        kind = "overview"
        body = f"GCC 高校 Builder 计划 2026 按项目资助、按里程碑核验，支持公开可复用的课程、研究、开源及产业对接。\n{scope['audience']}\n{scope['separation']}\n申请入口：{source['application_url']}"
    fallback = {
        "zh-TW": "以下為 GCC 已核准的簡體中文高校 Builder 計劃摘要：\n\n",
        "en": "The approved university Builder plan summary is currently available in Simplified Chinese:\n\n",
    }.get(lang, "")
    reminder = {
        "zh-TW": "如希望深入交流，歡迎參與 GCC 定期例會。",
        "zh-CN": "如希望深入交流，欢迎参与 GCC 定期例会。",
        "en": "For deeper discussion, you're welcome to join GCC's regular community calls.",
    }.get(lang, "如希望深入交流，歡迎參與 GCC 定期例會。")
    reply = f"{fallback}{body}\n\n申请表：{source['application_url']}\n计划附录：{source['appendix_url']}\n\n{reminder}"
    return UniversityAnswer(True, reply, kind)
