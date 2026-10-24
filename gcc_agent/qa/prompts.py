"""Prompt assembly and deterministic link-first answers."""

from dataclasses import dataclass
import re

from gcc_agent.common.models import Session
from gcc_agent.knowledge.cases import select_bot_qa_case_records
from gcc_agent.knowledge.history import select_history_projection
from gcc_agent.qa.facts import check_official_fact
from gcc_agent.qa.cohort4 import select_cohort4_answer
from gcc_agent.qa.university_builder import select_university_answer
from gcc_agent.qa.case_facts import as_case_facts_system_block, format_case_fact_reply
from gcc_agent.qa.history_facts import format_history_projection_reply
from gcc_agent.qa.programme_comparison import select_reviewed_programme_comparison
from gcc_agent.qa.route_selection import (
    SourceCandidate,
    choose_qa_source,
    clarification_reply,
    last_clarified_question,
)
from gcc_agent.knowledge.loaders import (
    as_gcc_summary_block,
    as_system_block,
    load_values,
)

GCC_LINKS = {
    "about": "https://www.gccofficial.org/about",
    "projects": "https://www.gccofficial.org/project",
    "apply": "https://www.gccofficial.org/application",
    "apply_public": "https://www.gccofficial.org/application/public",
    "apply_special": "https://www.gccofficial.org/application/special",
    "donate": "https://www.gccofficial.org/donate",
    "contact": "https://www.gccofficial.org/contact",
    "vote": "https://snapshot.box/#/s:gccofficial.eth",
    "events": "https://www.gccofficial.org/event",
    "blog": "https://www.gccofficial.org/blog",
}
PROJECT_LINKS = {
    "invisible garden": "https://www.gccofficial.org/project/project-invisiblegarden",
    "primus": "https://www.gccofficial.org/project/project-primus",
    "snarkexpress": "https://www.gccofficial.org/project/project-snarkexpress",
    "snark express": "https://www.gccofficial.org/project/project-snarkexpress",
    "vyper": "https://www.gccofficial.org/project/project-vyper",
    "herstory": "https://www.gccofficial.org/project/project-herstory",
    "agora": "https://www.gccofficial.org/project/project-agora",
    "agora citizen": "https://www.gccofficial.org/project/project-agora",
    "devconnect": "https://www.gccofficial.org/project/project-devconnect-2025",
    "oskey": "https://www.gccofficial.org/project/project-oskey",
    "edcon": "https://www.gccofficial.org/project/project-edcon-2025",
    "chain mirror": "https://www.gccofficial.org/project/project-chainmirror",
    "chainmirror": "https://www.gccofficial.org/project/project-chainmirror",
    "summer of protocol": "https://www.gccofficial.org/project/project-sop2025",
    "sop": "https://www.gccofficial.org/project/project-sop2025",
    "adventure x": "https://www.gccofficial.org/project/project-adventurex2025",
    "adventurex": "https://www.gccofficial.org/project/project-adventurex2025",
    "zk punk": "https://www.gccofficial.org/project/project-zkpunk",
    "zkpunk": "https://www.gccofficial.org/project/project-zkpunk",
}
FUNDING_KEYWORDS = [
    "申請", "資助", "基金", "捐助", "捐款", "如何申請", "怎麼申請", "公共基金",
    "專項基金", "機票計劃", "資金", "申请", "资助", "如何申请", "怎么申请",
    "专项基金", "机票计划", "资金", "apply", "grant", "funding", "application",
    "how to apply", "public fund", "special fund", "travel grant",
]
LANGUAGE_INSTRUCTIONS = {
    "zh-CN": "Always answer in Simplified Chinese (简体中文).",
    "zh-TW": "Always answer in Traditional Chinese (繁體中文).",
    "en": "Always answer in English.",
}


@dataclass(frozen=True)
class LinkResult:
    matched: bool
    reply: str = ""
    link_type: str = ""


def _link_reply(lang: str, link_type: str, name: str, url: str) -> str:
    reminder = {
        "zh-TW": "\n\n_如希望深入交流，歡迎參與 GCC 定期例會。_",
        "zh-CN": "\n\n_如希望深入交流，欢迎参与 GCC 定期例会。_",
        "en": "\n\n_For deeper discussion, you're welcome to join GCC's regular community calls._",
    }.get(lang, "\n\n_如希望深入交流，歡迎參與 GCC 定期例會。_")
    labels = {
        "project": {
            "zh-TW": f"📄 *{name}* 的詳細資料：",
            "zh-CN": f"📄 *{name}* 的详细资料：",
            "en": f"📄 Details about *{name}*:",
        },
        "apply": {"zh-TW": "📋 GCC 資助申請說明：", "zh-CN": "📋 GCC 资助申请说明：", "en": "📋 GCC Grant Application:"},
        "apply_public": {"zh-TW": "📋 公共基金申請說明：", "zh-CN": "📋 公共基金申请说明：", "en": "📋 Public Fund Application:"},
        "apply_special": {"zh-TW": "📋 專項基金申請說明：", "zh-CN": "📋 专项基金申请说明：", "en": "📋 Special Fund Application:"},
        "about": {"zh-TW": "ℹ️ 關於 GCC：", "zh-CN": "ℹ️ 关于 GCC：", "en": "ℹ️ About GCC:"},
        "projects": {"zh-TW": "📦 GCC 所有資助項目：", "zh-CN": "📦 GCC 所有资助项目：", "en": "📦 All GCC Funded Projects:"},
        "donate": {"zh-TW": "💚 支持 GCC：", "zh-CN": "💚 支持 GCC：", "en": "💚 Support GCC:"},
        "contact": {"zh-TW": "📬 聯絡 GCC：", "zh-CN": "📬 联络 GCC：", "en": "📬 Contact GCC:"},
        "vote": {"zh-TW": "🗳️ GCC 治理投票：", "zh-CN": "🗳️ GCC 治理投票：", "en": "🗳️ GCC Governance Voting:"},
        "events": {"zh-TW": "📅 GCC 活動與例會：", "zh-CN": "📅 GCC 活动与例会：", "en": "📅 GCC Events & Community Calls:"},
    }
    label = labels.get(link_type, {}).get(lang, labels.get(link_type, {}).get("zh-TW", ""))
    return f"{label}\n{url}{reminder}"


def check_link_first(
    text: str,
    lang: str = "zh-TW",
    previous_messages: list[dict] | None = None,
) -> LinkResult:
    value = text.lower().strip()
    history_projection = select_history_projection(
        text,
        previous_messages=previous_messages,
    )
    university = select_university_answer(text, lang)
    cohort4 = select_cohort4_answer(text, lang)
    fact = check_official_fact(text, lang, previous_messages)
    approved_cases = select_bot_qa_case_records(text, explicit_only=True, limit=2)
    comparison = select_reviewed_programme_comparison(text, lang, previous_messages)
    project_match = None
    for name, url in PROJECT_LINKS.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", value):
            project_match = (name, url)
            break

    candidates = []
    if history_projection:
        candidates.append(SourceCandidate(
            "history", "historical_report", detail=history_projection["projection_id"]
        ))
    if approved_cases:
        candidates.append(SourceCandidate("case", "named_reviewed_case", True))
    if university.matched:
        explicit_university = (
            "builder" in value and any(term in value for term in ("高校", "大学", "大學", "university", "campus"))
        ) or ("2026" in value and any(term in value for term in ("高校", "大学", "大學", "university", "campus")))
        candidates.append(SourceCandidate("university", "current_programme", explicit_university))
    if cohort4.matched:
        explicit_cohort4 = any(term in value for term in (
            "cohort 4", "cohort4", "cohort-4", "第四期", "第四屆", "第四届", "第4期", "第4屆", "第4届"
        ))
        candidates.append(SourceCandidate("cohort4", "current_programme", explicit_cohort4))
    if fact.matched:
        candidates.append(SourceCandidate("fact", "general_policy"))
    if project_match:
        candidates.append(SourceCandidate("project", "named_project_link", True))
    if comparison.matched:
        candidates.append(SourceCandidate("comparison", "reviewed_comparison", True))

    selected = choose_qa_source(text, candidates)
    if selected == "comparison":
        return LinkResult(True, comparison.reply, "reviewed_comparison")
    if selected == "history":
        return LinkResult(True, format_history_projection_reply(history_projection, lang), f"history_{history_projection['projection_id']}")
    if selected == "case":
        return LinkResult(True, format_case_fact_reply(approved_cases, lang, text), "canonical_case")
    if selected == "university":
        return LinkResult(True, university.reply, f"university2026_{university.answer_type}")
    if selected == "cohort4":
        return LinkResult(True, cohort4.reply, f"cohort4_{cohort4.answer_type}")
    if selected == "fact":
        return LinkResult(True, fact.reply, f"fact_{fact.fact_type}")
    if selected == "project":
        name, url = project_match
        return LinkResult(True, _link_reply(lang, "project", name.title(), url), "project")
    if selected == "clarify":
        return LinkResult(True, clarification_reply(lang), "route_clarification")
    special = ("專項", "专项", "special fund", "機票", "机票", "travel", "高校", "university", "706", "mastodon")
    if any(word in value for word in special):
        return LinkResult(True, _link_reply(lang, "apply_special", "", GCC_LINKS["apply_special"]), "apply_special")
    if any(word in value for word in ("公共基金", "public fund", "通用", "general fund")) and any(
        word in value for word in ("申請", "申请", "apply")
    ):
        return LinkResult(True, _link_reply(lang, "apply_public", "", GCC_LINKS["apply_public"]), "apply_public")
    apply_words = (
        "申請流程", "怎麼申請", "如何申請", "申請表", "申請資助", "申請基金",
        "申请流程", "怎么申请", "如何申请", "申请表", "申请资助", "申请基金",
        "how to apply", "application process", "application form", "apply for funding",
        "apply for a grant",
    )
    if any(word in value for word in apply_words):
        return LinkResult(True, _link_reply(lang, "apply", "", GCC_LINKS["apply"]), "apply")
    pages = (
        (("關於 gcc", "gcc 是什麼", "gcc 背景", "about gcc", "关于 gcc", "gcc是什么", "gcc介绍", "gcc 介紹"), "about"),
        (("所有項目", "資助項目", "已資助", "funded projects", "所有项目", "资助项目", "project list", "項目列表"), "projects"),
        (("捐款", "捐贈", "donate", "捐助 gcc", "支持 gcc"), "donate"),
        (("聯絡", "联络", "contact", "聯繫", "联系"), "contact"),
        (("投票", "vote", "snapshot", "治理投票"), "vote"),
        (("活動", "活动", "event", "例會", "例会", "meetup"), "events"),
    )
    for words, page in pages:
        if any(word in value for word in words):
            return LinkResult(True, _link_reply(lang, page, "", GCC_LINKS[page]), page)
    if last_clarified_question(previous_messages):
        # A one-turn follow-up with no resolved subject must not fall through
        # to an unconstrained model response about either programme.
        return LinkResult(True, clarification_reply(lang), "route_clarification")
    return LinkResult(False)


def build_messages(
    user_text: str,
    session: Session,
    lang: str = "zh-TW",
    *,
    case_records: list[dict] | None = None,
) -> list[dict]:
    values = load_values()
    selected_cases = (
        select_bot_qa_case_records(user_text)
        if case_records is None
        else case_records
    )
    messages = [
        {"role": "system", "content": as_system_block(values)},
        {
            "role": "system",
            "content": as_gcc_summary_block(values)
            + "\n\n"
            + LANGUAGE_INSTRUCTIONS.get(lang, LANGUAGE_INSTRUCTIONS["zh-TW"]),
        },
    ]
    case_block = as_case_facts_system_block(selected_cases)
    if case_block:
        messages.append({"role": "system", "content": case_block})
    messages.extend((*session.get_context(), {"role": "user", "content": user_text}))
    return messages
