"""Reviewed, round-scoped answers for the public Cohort 4 announcement."""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
import logging

import yaml


logger = logging.getLogger(__name__)
_PATH = Path(__file__).resolve().parents[2] / "data" / "cohort4.yaml"
_HKT = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class Cohort4Answer:
    matched: bool
    reply: str = ""
    answer_type: str = ""


def _contains(value: str, terms: tuple[str, ...]) -> bool:
    return any(term in value for term in terms)


def _load_approved() -> dict | None:
    """Fail closed if the reviewed content or essential source metadata is absent."""
    try:
        with _PATH.open(encoding="utf-8") as source:
            data = yaml.safe_load(source)
        if not isinstance(data, dict) or data.get("schema_version") != "1.0":
            return None
        review = data.get("review", {})
        urls = data.get("source", {})
        if not isinstance(review, dict) or not isinstance(urls, dict):
            return None
        if (
            data.get("round_id") != "cohort-4"
            or review.get("status") != "approved"
            or review.get("access_level") != "public"
            or "bot_qa" not in review.get("allowed_uses", [])
            or not review.get("reviewed_at")
            or not review.get("reviewed_by_role")
            or not all(
                str(urls.get(key, "")).startswith("https://")
                for key in ("announcement_url", "public_fund_url", "special_fund_url")
            )
        ):
            return None
        application = data.get("application", {})
        if not isinstance(application, dict) or application.get("timezone") != "UTC+8":
            return None
        opens = datetime.fromisoformat(application["opens_at"])
        closes = datetime.fromisoformat(application["closes_at"])
        if (
            opens.utcoffset() != timedelta(hours=8)
            or closes.utcoffset() != timedelta(hours=8)
            or opens >= closes
        ):
            return None
        if not all(
            isinstance(data.get(key), list)
            and data[key]
            and all(isinstance(item, str) and item.strip() for item in data[key])
            for key in ("focus", "criteria", "schedule")
        ):
            return None
        if not isinstance(data.get("referral"), str) or not data["referral"].strip():
            return None
        return data
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError):
        logger.exception("approved Cohort 4 content unavailable")
        return None


def _status(application: dict, now: datetime) -> str:
    current = now.astimezone(_HKT)
    opens = datetime.fromisoformat(application["opens_at"])
    closes = datetime.fromisoformat(application["closes_at"])
    if current < opens:
        return "公告所列申请期尚未开始。"
    if current > closes:
        return "公告所列申请截止时间已过；是否延长或另开新轮次，请以官方申请页最新信息为准。"
    return "按公告日期，本轮仍在申请期内；提交前请核对官方申请页。"


def select_cohort4_answer(
    text: str,
    lang: str = "zh-TW",
    *,
    now: datetime | None = None,
) -> Cohort4Answer:
    """Answer explicit Cohort 4/current OPS intents without generalising to other rounds."""
    value = text.casefold().strip()
    explicit = _contains(value, ("cohort 4", "cohort4", "cohort-4", "第四期", "第四屆", "第四届", "第4期", "第4屆", "第4届"))
    historic = _contains(value, ("歷史", "历史", "過往", "过往", "2023", "2024", "2025", "cohort 1", "cohort 2", "cohort 3"))
    current_focus = not historic and (
        "ops" in value
        or (_contains(value, ("gcc", "今屆", "今届", "本輪", "本轮", "今年", "目前", "現在", "现在"))
            and _contains(value, ("方向", "關注", "关注", "優先", "优先", "支持什麼", "支持什么", "focus", "priorities")))
    )
    current_criteria = not historic and "gcc" in value and _contains(
        value, ("評審標準", "评审标准", "選拔標準", "选拔标准", "selection criteria")
    ) and not _contains(value, ("評分", "评分", "score", "百分制"))
    current_deadline = not historic and "gcc" in value and _contains(
        value, ("截止", "deadline", "申請期", "申请期", "open now")
    ) and not _contains(value, ("專項", "专项", "special fund"))
    if not explicit and not (current_focus or current_criteria or current_deadline):
        return Cohort4Answer(False)
    if historic and not explicit:
        return Cohort4Answer(False)
    data = _load_approved()
    if data is None:
        return Cohort4Answer(False)

    source = data["source"]
    application = data["application"]
    opens = datetime.fromisoformat(application["opens_at"]).astimezone(_HKT)
    closes = datetime.fromisoformat(application["closes_at"]).astimezone(_HKT)
    date_line = f"申请期：{opens:%Y-%m-%d} 至 {closes:%Y-%m-%d %H:%M}（UTC+8）。"
    status = _status(application, now or datetime.now(_HKT))
    if _contains(value, ("推薦", "推荐", "referr", "獎勵", "奖励", "100 usd")):
        answer_type = "referral"
        body = f"Cohort 4 推荐奖励：{data['referral']}\n这不是所有推荐或报名均可获得的奖励。"
    elif _contains(value, ("截止", "幾時申請", "几时申请", "何時申請", "何时申请", "deadline", "open now", "還能申請", "还能申请", "申請期", "申请期")):
        answer_type = "deadline"
        body = f"{date_line}\n{status}\n公共基金申请入口：{source['public_fund_url']}"
    elif _contains(value, ("時間表", "时间表", "日程", "初篩", "初筛", "demo day", "結果", "结果", "m0", "撥款", "拨款", "schedule", "timeline")):
        answer_type = "schedule"
        body = f"Cohort 4 公告时间表：\n• {date_line}\n• " + "\n• ".join(data["schedule"])
        body += "\n上述后续节点均为公告计划，不代表筛选结果或款项已实际发生。"
    elif _contains(value, ("標準", "标准", "準則", "准则", "因素", "criteria", "評分", "评分", "score", "門檻", "门槛")):
        answer_type = "criteria"
        body = "Cohort 4 公告列出的选拔标准：" + "、".join(data["criteria"]) + "。\n公告没有公布百分制权重或自动通过门槛；Bot 不作正式评审决定。"
    elif current_focus or _contains(value, ("方向", "開源", "开源", "隱私", "隐私", "安全", "focus", "priorit", "ops")):
        answer_type = "focus"
        body = "Cohort 4 本轮关注 OPS 三个方向：\n• " + "\n• ".join(data["focus"])
    else:
        answer_type = "application"
        body = f"GCC Cohort 4 公共基金申请：{date_line}\n{status}\n入口：{source['public_fund_url']}\n更紧迫的小额需求（如高校活动、机票资助）可查看常年开放的专项基金：{source['special_fund_url']}"

    fallback = {
        "zh-TW": "以下為 GCC 已核准的簡體中文 Cohort 4 公告摘要：\n\n",
        "en": "The approved Cohort 4 announcement summary is currently available in Simplified Chinese:\n\n",
    }.get(lang, "")
    reminder = {
        "zh-TW": "_如希望深入交流，歡迎參與 GCC 定期例會。_",
        "zh-CN": "_如希望深入交流，欢迎参与 GCC 定期例会。_",
        "en": "_For deeper discussion, you're welcome to join GCC's regular community calls._",
    }.get(lang, "_如希望深入交流，歡迎參與 GCC 定期例會。_")
    reply = f"{fallback}{body}\n\n公告來源：{source['announcement_url']}\n\n{reminder}"
    return Cohort4Answer(True, reply, answer_type)
