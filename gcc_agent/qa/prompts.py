"""Prompt assembly and deterministic link-first answers."""

from dataclasses import dataclass

from gcc_agent.common.models import Session
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
    "apply_form_project": "https://tally.so/r/w5R8R6",
    "apply_form_personal": "https://tally.so/r/nPKbb5",
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


def check_link_first(text: str, lang: str = "zh-TW") -> LinkResult:
    value = text.lower().strip()
    for name, url in PROJECT_LINKS.items():
        if name in value:
            return LinkResult(True, _link_reply(lang, "project", name.title(), url), "project")
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
    return LinkResult(False)


def build_messages(user_text: str, session: Session, lang: str = "zh-TW") -> list[dict]:
    values = load_values()
    return [
        {"role": "system", "content": as_system_block(values)},
        {"role": "system", "content": as_gcc_summary_block(values)},
        *session.get_context(),
        {"role": "user", "content": user_text},
    ]
