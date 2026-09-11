"""Source-backed, deterministic answers for high-risk GCC policy questions."""

from dataclasses import dataclass
from typing import Iterable


ABOUT_URL = "https://www.gccofficial.org/about"
PUBLIC_FUND_URL = "https://www.gccofficial.org/application/public"
SPECIAL_FUND_URL = "https://www.gccofficial.org/application/special"


@dataclass(frozen=True)
class OfficialFactAnswer:
    matched: bool
    reply: str = ""
    fact_type: str = ""


_REMINDERS = {
    "zh-TW": "\n\n_如希望深入交流，歡迎參與 GCC 定期例會。_",
    "zh-CN": "\n\n_如希望深入交流，欢迎参与 GCC 定期例会。_",
    "en": "\n\n_For deeper discussion, you're welcome to join GCC's regular community calls._",
}

_ANSWERS = {
    "process": {
        "zh-TW": f"""📋 GCC 官網公開的整體資助流程：

1. 初篩：確認使命契合度。
2. 全面評審：綜合考慮影響力、可行性及團隊能力。
3. 盡職調查：核實團隊背景及資金情況。
4. 決策：提交投票委員會；官網說明通常需三分之二以上贊成。
5. 協議與進度管理：通過後簽署協議，並進行里程碑管理及定期反饋。

公共基金按輪次申請，官網列出的評選週期為 8–12 週；專項基金則按特定主題滾動申請，具體規則可能不同。

官方來源：
{ABOUT_URL}
{PUBLIC_FUND_URL}
{SPECIAL_FUND_URL}

注意：公開的治理或決策流程本身不能證明款項已實際撥付，或 milestone 已驗收／解鎖。""",
        "zh-CN": f"""📋 GCC 官网公开的整体资助流程：

1. 初筛：确认使命契合度。
2. 全面评审：综合考虑影响力、可行性及团队能力。
3. 尽职调查：核实团队背景及资金情况。
4. 决策：提交投票委员会；官网说明通常需三分之二以上赞成。
5. 协议与进度管理：通过后签署协议，并进行里程碑管理及定期反馈。

公共基金按轮次申请，官网列出的评选周期为 8–12 周；专项基金则按特定主题滚动申请，具体规则可能不同。

官方来源：
{ABOUT_URL}
{PUBLIC_FUND_URL}
{SPECIAL_FUND_URL}

注意：公开的治理或决策流程本身不能证明款项已实际拨付，或 milestone 已验收／解锁。""",
        "en": f"""📋 GCC's published overall funding process:

1. Initial screening: check mission alignment.
2. Full review: consider impact, feasibility, and team capability.
3. Due diligence: verify team background and funding information.
4. Decision: submit to the voting committee; the website says approval usually requires at least two thirds in favour.
5. Agreement and progress management: sign an agreement, manage milestones, and provide regular feedback.

The Public Fund runs in rounds with a published 8–12 week selection cycle. Special Funds accept rolling applications for specific themes and may follow different details.

Official sources:
{ABOUT_URL}
{PUBLIC_FUND_URL}
{SPECIAL_FUND_URL}

Note: a published governance or funding decision does not by itself prove that funds were disbursed or that a milestone was accepted or unlocked.""",
    },
    "criteria": {
        "zh-TW": f"""📋 GCC 公共基金官網公開的考慮因素包括：是否符合 GCC 使命、是否屬優先支持類別、可行性及潛在影響力、領導力與團隊情況，以及資金需求。

官網沒有為這些因素公布百分制權重或通過分數。不同專項基金可能有各自規則，不能直接套用公共基金流程。

官方來源：
{PUBLIC_FUND_URL}
{SPECIAL_FUND_URL}""",
        "zh-CN": f"""📋 GCC 公共基金官网公开的考虑因素包括：是否符合 GCC 使命、是否属于优先支持类别、可行性及潜在影响力、领导力与团队情况，以及资金需求。

官网没有为这些因素公布百分制权重或通过分数。不同专项基金可能有各自规则，不能直接套用公共基金流程。

官方来源：
{PUBLIC_FUND_URL}
{SPECIAL_FUND_URL}""",
        "en": f"""📋 The GCC Public Fund page lists these considerations: alignment with GCC's mission, fit with priority categories, feasibility and potential impact, leadership and team, and funding need.

The website does not publish percentage weights or a passing score for these factors. Special Funds may have their own rules and should not automatically be treated as following the Public Fund process.

Official sources:
{PUBLIC_FUND_URL}
{SPECIAL_FUND_URL}""",
    },
    "score": {
        "zh-TW": f"""GCC 官網目前沒有公布 40/30/20/10 的正式評分權重，也沒有公布 70/40 的通過門檻。

Bot 現有的百分制只是內部初步整理 heuristic，不是 GCC 投票委員會的正式評分或決策，不能用來自動通過或拒絕申請。

官網公開的公共基金考慮因素：
{PUBLIC_FUND_URL}""",
        "zh-CN": f"""GCC 官网目前没有公布 40/30/20/10 的正式评分权重，也没有公布 70/40 的通过门槛。

Bot 现有的百分制只是内部初步整理 heuristic，不是 GCC 投票委员会的正式评分或决策，不能用来自动通过或拒绝申请。

官网公开的公共基金考虑因素：
{PUBLIC_FUND_URL}""",
        "en": f"""The GCC website does not currently publish official 40/30/20/10 weights or 70/40 passing thresholds.

The bot's existing percentage score is only an internal triage heuristic. It is not an official GCC voting-committee score or decision and must not automatically approve or reject an application.

Published Public Fund considerations:
{PUBLIC_FUND_URL}""",
    },
    "timeline": {
        "zh-TW": f"""GCC 官網目前只公開公共基金每輪評選週期為 8–12 週，沒有公布初篩、全面評審、盡職調查及決策各階段分別需時多久。專項基金是滾動申請及較快速審批，但實際時間視乎具體專項。

因此，無法從公開資料推斷每個階段的確切時間。

官方來源：
{PUBLIC_FUND_URL}
{SPECIAL_FUND_URL}""",
        "zh-CN": f"""GCC 官网目前只公开公共基金每轮评选周期为 8–12 周，没有公布初筛、全面评审、尽职调查及决策各阶段分别需要多久。专项基金是滚动申请及较快速审批，但实际时间取决于具体专项。

因此，无法从公开资料推断每个阶段的确切时间。

官方来源：
{PUBLIC_FUND_URL}
{SPECIAL_FUND_URL}""",
        "en": f"""The GCC website currently publishes an 8–12 week selection cycle for each Public Fund round, but it does not publish a duration for each individual screening, full-review, due-diligence, or decision stage. Special Funds accept rolling applications and are described as faster, but timing depends on the specific fund.

The duration of each stage therefore cannot be inferred from the public information.

Official sources:
{PUBLIC_FUND_URL}
{SPECIAL_FUND_URL}""",
    },
    "sources": {
        "zh-TW": f"""📚 官方來源：

• GCC 整體資助流程與準則：{ABOUT_URL}
• 公共基金評審因素、申請入口及 8–12 週週期：{PUBLIC_FUND_URL}
• 專項基金主題及滾動申請入口：{SPECIAL_FUND_URL}

這些頁面沒有公布 40/30/20/10 權重或 70/40 門檻；Bot 內部分數不是 GCC 正式政策。""",
        "zh-CN": f"""📚 官方来源：

• GCC 整体资助流程与准则：{ABOUT_URL}
• 公共基金评审因素、申请入口及 8–12 周周期：{PUBLIC_FUND_URL}
• 专项基金主题及滚动申请入口：{SPECIAL_FUND_URL}

这些页面没有公布 40/30/20/10 权重或 70/40 门槛；Bot 内部分数不是 GCC 正式政策。""",
        "en": f"""📚 Official sources:

• GCC's overall funding process and principles: {ABOUT_URL}
• Public Fund considerations, forms, and 8–12 week cycle: {PUBLIC_FUND_URL}
• Special Fund themes and rolling application links: {SPECIAL_FUND_URL}

These pages do not publish 40/30/20/10 weights or 70/40 thresholds. The bot's internal score is not official GCC policy.""",
    },
    "decision_execution": {
        "zh-TW": "Snapshot 的簽署、投票或提案結果只能證明相關治理提案或決定，不能單獨證明實際撥款、里程碑驗收或款項解鎖。這些執行狀態必須另以交易、會計、付款或獲授權的驗收紀錄核對；未核實前應視為尚待確認。",
        "zh-CN": "Snapshot 的签署、投票或提案结果只能证明相关治理提案或决定，不能单独证明实际拨款、里程碑验收或款项解锁。这些执行状态必须另以交易、会计、付款或获授权的验收记录核对；未核实前应视为尚待确认。",
        "en": "A signed Snapshot proposal or vote can evidence a governance proposal or decision, but it does not by itself prove an actual disbursement, milestone acceptance, or fund unlock. Those execution states require separate transaction, accounting, payment, or authorised acceptance records and remain unconfirmed until verified.",
    },
}

_PROCESS_TERMS = (
    "資助流程", "资助流程", "評審流程", "评审流程", "審核流程", "审核流程",
    "審批流程", "审批流程", "評審步驟", "评审步骤", "審核步驟", "审核步骤",
    "審批步驟", "审批步骤", "如何評審", "如何评审", "怎樣評審", "怎样评审",
    "怎麼評審", "怎么评审", "如何審核", "如何审核", "怎樣審核", "怎样审核",
    "怎麼審核", "怎么审核", "funding process", "grant process", "review process",
    "review stages", "how does gcc review", "how are applications reviewed",
)
_CRITERIA_TERMS = (
    "評審標準", "评审标准", "審核標準", "审核标准", "評審因素", "评审因素",
    "資助準則", "资助准则", "資助標準", "资助标准", "考慮因素", "考虑因素",
    "funding criteria", "review criteria", "selection criteria",
)
_UNIQUE_SCORE_TERMS = ("40/30/20/10", "70/40")
_STRONG_SCORE_TERMS = (
    "70 分", "70分", "40 分", "40分", "百分制",
    "評分制", "评分制", "評分門檻", "评分门槛", "passing score", "score threshold",
    "scoring system", "達到 70", "达到 70",
    "達到70", "达到70", "40 至 69", "40至69", "40 到 69", "40到69", "40 to 69",
)
_GENERIC_SCORE_TERMS = ("評分", "评分", "打分", "scoring", "score")
_TIME_TERMS = (
    "多久", "幾耐", "几耐", "多少天", "幾天", "几天", "需時", "需要多长",
    "時間", "时间", "timeline", "how long",
)
_POLICY_CONTEXT_TERMS = _PROCESS_TERMS + _CRITERIA_TERMS + (
    "資助", "资助", "評審", "评审", "審核", "审核", "申請", "申请",
    "funding", "grant", "review", "application",
)
_TIMELINE_CONTEXT_TERMS = _PROCESS_TERMS + (
    "資助", "资助", "評審", "评审", "審核", "审核", "審批", "审批",
    "funding", "grant", "review", "selection",
)
_SOURCE_TERMS = (
    "來源", "来源", "依據", "依据", "哪裡寫", "哪里写", "source", "sources",
    "citation", "where is this documented",
)


def _contains(value: str, terms: Iterable[str]) -> bool:
    return any(term in value for term in terms)


def _recent_policy_context(previous_messages: Iterable[dict] | None) -> bool:
    if not previous_messages:
        return False
    recent = " ".join(
        str(message.get("content", "")).lower()
        for message in list(previous_messages)[-4:]
    )
    return (
        ABOUT_URL in recent
        or PUBLIC_FUND_URL in recent
        or SPECIAL_FUND_URL in recent
        or _contains(
            recent,
            _PROCESS_TERMS
            + _CRITERIA_TERMS
            + _UNIQUE_SCORE_TERMS
            + _STRONG_SCORE_TERMS,
        )
    )


def _answer(fact_type: str, lang: str) -> OfficialFactAnswer:
    selected_lang = lang if lang in _REMINDERS else "zh-TW"
    reply = _ANSWERS[fact_type][selected_lang] + _REMINDERS[selected_lang]
    return OfficialFactAnswer(True, reply, fact_type)


def check_official_fact(
    text: str,
    lang: str = "zh-TW",
    previous_messages: Iterable[dict] | None = None,
) -> OfficialFactAnswer:
    """Match policy questions that must never be answered from model inference."""
    value = text.lower().strip()

    execution_terms = (
        "撥款", "拨款", "付款", "已付", "解鎖", "解锁", "執行", "执行",
        "落實", "落实", "到賬", "到账", "實際發生", "实际发生", "milestone",
        "unlock", "disburse", "paid", "received funds", "executed",
    )
    if "snapshot" in value and _contains(value, execution_terms):
        return _answer("decision_execution", lang)

    has_policy_context = _contains(value, _POLICY_CONTEXT_TERMS)
    has_recent_policy_context = _recent_policy_context(previous_messages)
    if _contains(value, _SOURCE_TERMS) and (
        has_policy_context or has_recent_policy_context
    ):
        return _answer("sources", lang)

    has_score_context = "gcc" in value or has_policy_context or has_recent_policy_context
    if _contains(value, _UNIQUE_SCORE_TERMS) or (
        _contains(value, _STRONG_SCORE_TERMS + _GENERIC_SCORE_TERMS)
        and has_score_context
    ):
        return _answer("score", lang)

    if _contains(value, _TIME_TERMS) and (
        "gcc" in value or _contains(value, _TIMELINE_CONTEXT_TERMS)
    ):
        return _answer("timeline", lang)

    if _contains(value, _CRITERIA_TERMS):
        return _answer("criteria", lang)

    if _contains(value, _PROCESS_TERMS):
        return _answer("process", lang)

    return OfficialFactAnswer(False)
