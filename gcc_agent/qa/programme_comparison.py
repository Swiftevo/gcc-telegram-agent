"""Bounded comparisons assembled only from reviewed public programme facts."""

from dataclasses import dataclass
import re

from gcc_agent.knowledge.cases import select_bot_qa_case_records
from gcc_agent.qa.case_facts import ETH_CITY_UNIVERSITY_2025_CASE_ID
from gcc_agent.qa.route_selection import clarification_reply, last_clarified_question
from gcc_agent.qa.university_builder import load_approved_university_plan


@dataclass(frozen=True)
class ComparisonAnswer:
    matched: bool
    reply: str = ""


_COMPARISON_TERMS = (
    "比較", "比较", "不同", "差異", "差异", "區別", "区别", "對比", "对比",
    "compare", "comparison", "difference", "different", "versus", " vs ",
)
_BOTH_TERMS = ("兩者", "两者", "二者", "兩個", "两个", "both", "the two")
_HISTORIC_NAMES = (
    "高校 web3", "高校web3", "university web3", "高校興趣小組", "高校兴趣小组",
)
_CURRENT_NAMES = ("builder", "建設者計劃", "建设者计划")


def _has_pair(value: str) -> bool:
    return (
        "2025" in value
        and any(name in value for name in _HISTORIC_NAMES)
        and "2026" in value
        and any(name in value for name in _CURRENT_NAMES)
    )


def _amount(fact: dict, *, allowed_statuses: set[str]) -> str | None:
    if not isinstance(fact, dict) or fact.get("status") not in allowed_statuses:
        return None
    value, currency = fact.get("amount"), fact.get("currency")
    if not isinstance(value, (int, float)) or not currency:
        return None
    return f"{value:,} {currency}"


def _category_cap(category: str) -> str | None:
    match = re.search(r"\b[\d,]+\s+USD\b", category)
    return match.group(0) if match else None


def _unavailable(lang: str) -> str:
    return {
        "zh-TW": "目前缺少可同時核實這兩個計劃的已審核公開資料，暫不能可靠比較；請查看 GCC 的正式公告。",
        "zh-CN": "目前缺少可同时核实这两个计划的已审核公开资料，暂不能可靠比较；请查看 GCC 的正式公告。",
        "en": "Reviewed public facts for both programmes are not available, so I cannot compare them reliably. Please check GCC's official announcements.",
    }.get(lang, "目前缺少可同時核實這兩個計劃的已審核公開資料，暫不能可靠比較。")


def select_reviewed_programme_comparison(
    text: str,
    lang: str = "zh-TW",
    previous_messages: list[dict] | None = None,
) -> ComparisonAnswer:
    """Compare the supported pair; never send an unresolved two-subject query to AI."""
    value = text.casefold().strip()
    if not any(term in value for term in _COMPARISON_TERMS):
        return ComparisonAnswer(False)

    subject_query = text
    if not _has_pair(value):
        prior = last_clarified_question(previous_messages)
        if prior and _has_pair(prior.casefold()):
            subject_query = prior
        elif any(term in value for term in _BOTH_TERMS):
            return ComparisonAnswer(True, clarification_reply(lang))
        else:
            return ComparisonAnswer(False)

    records = select_bot_qa_case_records(subject_query, explicit_only=True, limit=3)
    record = next(
        (item for item in records if item.get("case_id") == ETH_CITY_UNIVERSITY_2025_CASE_ID),
        None,
    )
    plan = load_approved_university_plan()
    if not record or not plan:
        return ComparisonAnswer(True, _unavailable(lang))

    tracks = record.get("public_record", {}).get("program_details", {}).get("funding_tracks", [])
    historic = next((item for item in tracks if item.get("track_id") == "gcc-university-web3-2025"), None)
    if not historic:
        return ComparisonAnswer(True, _unavailable(lang))
    pool = _amount(historic.get("total_pool", {}), allowed_statuses={"owner_confirmed"})
    minimum = _amount(historic.get("min_grant", {}), allowed_statuses={"source_reported", "owner_confirmed"})
    maximum = _amount(historic.get("max_grant", {}), allowed_statuses={"source_reported", "owner_confirmed"})
    workshop = _category_cap(plan["categories"]["workshop"])
    exploration = _category_cap(plan["categories"]["exploration"])
    deadline_match = re.search(
        r"\b\d{4}-\d{2}-\d{2}\b",
        record.get("public_record", {}).get("program_details", {}).get("application_deadline", ""),
    )
    if not all((pool, minimum, maximum, workshop, exploration, deadline_match)):
        return ComparisonAnswer(True, _unavailable(lang))
    deadline = deadline_match.group(0)

    if lang == "en":
        lines = [
            "These are separate programmes from different years:",
            "1. Scope: The 2025 University Web3 interest-group track supported campus groups' workshops, open-source student work and community activities. The 2026 University Builder plan funds specified projects with public deliverables and milestone checks.",
            f"2. Amounts: {pool} was the governance-approved pool for the 2025 university track, with announced grants of {minimum}–{maximum} per group. The reviewed 2026 material lists caps by six categories, for example {workshop} per workshop and {exploration} per exploration project; it does not state a comparable total programme pool.",
            f"3. Application and review: The 2025 track described rolling applications through {deadline} or until slots filled. The 2026 plan has quarterly windows for some categories and rolling applications for exploration work, with five published weighted review criteria. The Bot's reviewed 2025 projection has no comparable review weights, so I cannot say either plan was easier to pass.",
            "The 2025 allocation is not evidence of an individual award or payment. The 2026 announcement is not evidence that any project was approved, accepted or paid. Check the current application form before applying.",
            "Reviewed public sources:",
        ]
    elif lang == "zh-CN":
        lines = [
            "这属于两个不同年份的独立计划：",
            "1. 定位：2025 高校 Web3 兴趣小组线支持高校社团的技术教学、开源学生项目及社区活动；2026 高校 Builder 按具体项目申请，要求公开交付并按约定里程碑核验。",
            f"2. 额度：{pool} 是 2025 高校线的治理核准总额度，公告单个社团资助范围为 {minimum}–{maximum}。已审核的 2026 资料按六类列单项上限，例如 Workshop 每课程 {workshop}、工程／学术探索每项目 {exploration}；没有提供可直接对比的计划总额度。",
            f"3. 申请与评审：2025 高校线当时滚动收件，原定至 {deadline} 或名额用完；2026 计划部分类别按季度收件，探索类随时申请，并公布五项带权重的评审因素。Bot 可用的 2025 审核资料没有可比的评审权重，不能说哪一年更容易通过。",
            "2025 的治理额度不证明个别项目获批或拨款；2026 的公告也不证明个别项目已获批、验收或付款。申请前请核对现行表格。",
            "已审核公开来源：",
        ]
    else:
        lines = [
            "這是兩個不同年份的獨立計劃：",
            "1. 定位：2025 高校 Web3 興趣小組線支持高校社團的技術教學、開源學生項目及社群活動；2026 高校 Builder 按具體項目申請，要求公開交付並按約定里程碑核驗。",
            f"2. 額度：{pool} 是 2025 高校線的治理核准總額度，公告單個社團資助範圍為 {minimum}–{maximum}。已審核的 2026 資料按六類列單項上限，例如 Workshop 每課程 {workshop}、工程／學術探索每項目 {exploration}；沒有提供可直接對比的計劃總額度。",
            f"3. 申請與評審：2025 高校線當時滾動收件，原定至 {deadline} 或名額用完；2026 計劃部分類別按季度收件，探索類隨時申請，並公布五項帶權重的評審因素。Bot 可用的 2025 審核資料沒有可比的評審權重，不能說哪一年更容易通過。",
            "2025 的治理額度不證明個別項目獲批或撥款；2026 的公告也不證明個別項目已獲批、驗收或付款。申請前請核對現行表格。",
            "已審核公開來源：",
        ]

    source_urls = list(dict.fromkeys(
        source["source_url"]
        for source in record.get("sources", [])
        if source.get("source_url")
    ))
    source_urls.append(plan["source"]["appendix_url"])
    lines.extend(source_urls)
    return ComparisonAnswer(True, "\n\n".join(lines))
