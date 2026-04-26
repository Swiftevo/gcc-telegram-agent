"""
core/prompt.py — 三層 Prompt 組裝 + 連結優先邏輯

三層結構（順序不可改變）：
  Layer 1 [system] — AgentValues（固定，最高優先）
  Layer 2 [system] — GCC 背景摘要
  Layer 3 [user/assistant] — Session 對話窗口（最近 20 條）
  + 新訊息 [user]

連結優先：
  偵測到用戶問及特定項目/申請/官網內容
  → 直接返回連結，不呼叫 AI API
  → 節省 token，回應更快更準確
"""

import logging
import re
from typing import Optional

from core.values import as_system_block, as_gcc_summary_block, load_values
from models import Session

logger = logging.getLogger(__name__)


# ── GCC 官網連結對照表 ─────────────────────────────────────────────────────────

GCC_LINKS = {
    "about":          "https://www.gccofficial.org/about",
    "projects":       "https://www.gccofficial.org/project",
    "apply":          "https://www.gccofficial.org/application",
    "apply_public":   "https://www.gccofficial.org/application/public",
    "apply_special":  "https://www.gccofficial.org/application/special",
    "apply_form_project":  "https://tally.so/r/w5R8R6",
    "apply_form_personal": "https://tally.so/r/nPKbb5",
    "donate":         "https://www.gccofficial.org/donate",
    "contact":        "https://www.gccofficial.org/contact",
    "vote":           "https://snapshot.box/#/s:gccofficial.eth",
    "events":         "https://www.gccofficial.org/event",
    "blog":           "https://www.gccofficial.org/blog",
}

# 已資助項目連結（前 10 個）
PROJECT_LINKS = {
    "invisible garden": "https://www.gccofficial.org/project/project-invisiblegarden",
    "primus":           "https://www.gccofficial.org/project/project-primus",
    "snarkexpress":     "https://www.gccofficial.org/project/project-snarkexpress",
    "snark express":    "https://www.gccofficial.org/project/project-snarkexpress",
    "vyper":            "https://www.gccofficial.org/project/project-vyper",
    "herstory":         "https://www.gccofficial.org/project/project-herstory",
    "agora":            "https://www.gccofficial.org/project/project-agora",
    "agora citizen":    "https://www.gccofficial.org/project/project-agora",
    "devconnect":       "https://www.gccofficial.org/project/project-devconnect-2025",
    "oskey":            "https://www.gccofficial.org/project/project-oskey",
    "edcon":            "https://www.gccofficial.org/project/project-edcon-2025",
    "chain mirror":     "https://www.gccofficial.org/project/project-chainmirror",
    "chainmirror":      "https://www.gccofficial.org/project/project-chainmirror",
    "summer of protocol": "https://www.gccofficial.org/project/project-sop2025",
    "sop":              "https://www.gccofficial.org/project/project-sop2025",
    "adventure x":      "https://www.gccofficial.org/project/project-adventurex2025",
    "adventurex":       "https://www.gccofficial.org/project/project-adventurex2025",
    "zk punk":          "https://www.gccofficial.org/project/project-zkpunk",
    "zkpunk":           "https://www.gccofficial.org/project/project-zkpunk",
}


# ── 資助相關關鍵詞（供 general.py 判斷是否顯示申請按鈕）────────────────────────
# 這裡只用於「是否顯示按鈕」的輕量判斷，不用於路由決策

FUNDING_KEYWORDS = [
    # 繁體中文
    "申請", "資助", "基金", "捐助", "捐款", "如何申請", "怎麼申請",
    "公共基金", "專項基金", "機票計劃", "資金",
    # 簡體中文
    "申请", "资助", "捐助", "捐款", "如何申请", "怎么申请",
    "公共基金", "专项基金", "机票计划", "资金",
    # 英文
    "apply", "grant", "funding", "application", "how to apply",
    "public fund", "special fund", "travel grant",
]


# ── 連結優先邏輯 ──────────────────────────────────────────────────────────────

class LinkResult:
    """連結優先檢查結果"""
    def __init__(self, matched: bool, reply: str = "", link_type: str = ""):
        self.matched = matched    # True = 直接回覆連結，不需要呼叫 AI
        self.reply = reply        # 要回覆的文字
        self.link_type = link_type


def check_link_first(text: str, lang: str = "zh-TW") -> LinkResult:
    """
    檢查用戶訊息是否可以直接用官網連結回答。
    返回 LinkResult。matched=True 表示找到對應連結。

    策略：
    1. 先檢查是否提及具體項目名稱
    2. 再檢查是否問及申請流程
    3. 再檢查是否問及 GCC 官網特定頁面
    """
    text_lower = text.lower().strip()

    # ── 1. 具體項目查詢 ────────────────────────────────────
    for project_name, url in PROJECT_LINKS.items():
        if project_name in text_lower:
            reply = _link_reply(lang, "project", project_name.title(), url)
            return LinkResult(matched=True, reply=reply, link_type="project")

    # ── 2. 申請流程查詢 ────────────────────────────────────
    apply_keywords = {
        "zh-TW": ["申請流程", "怎麼申請", "如何申請", "申請表", "申請資助", "申請基金"],
        "zh-CN": ["申请流程", "怎么申请", "如何申请", "申请表", "申请资助", "申请基金"],
        "en":    ["how to apply", "application process", "application form",
                  "apply for funding", "apply for a grant"],
    }
    all_apply = [kw for kws in apply_keywords.values() for kw in kws]

    # 專項基金相關
    special_keywords = ["專項", "专项", "special fund", "機票", "机票",
                        "travel", "高校", "university", "706", "mastodon"]
    public_keywords = ["公共基金", "public fund", "通用", "general fund"]

    if any(kw in text_lower for kw in special_keywords):
        reply = _link_reply(lang, "apply_special", "", GCC_LINKS["apply_special"])
        return LinkResult(matched=True, reply=reply, link_type="apply_special")

    if any(kw in text_lower for kw in public_keywords) and \
       any(kw in text_lower for kw in ["申請", "apply", "申请"]):
        reply = _link_reply(lang, "apply_public", "", GCC_LINKS["apply_public"])
        return LinkResult(matched=True, reply=reply, link_type="apply_public")

    if any(kw in text_lower for kw in all_apply):
        reply = _link_reply(lang, "apply", "", GCC_LINKS["apply"])
        return LinkResult(matched=True, reply=reply, link_type="apply")

    # ── 3. GCC 官網頁面查詢 ────────────────────────────────
    page_patterns = [
        (["關於 gcc", "gcc 是什麼", "gcc 背景", "about gcc",
          "关于 gcc", "gcc是什么", "gcc介绍", "gcc 介紹"],
         "about", GCC_LINKS["about"]),
        (["所有項目", "資助項目", "已資助", "funded projects",
          "所有项目", "资助项目", "project list", "項目列表"],
         "projects", GCC_LINKS["projects"]),
        (["捐款", "捐贈", "donate", "捐助 gcc", "支持 gcc"],
         "donate", GCC_LINKS["donate"]),
        (["聯絡", "联络", "contact", "聯繫", "联系"],
         "contact", GCC_LINKS["contact"]),
        (["投票", "vote", "snapshot", "治理投票"],
         "vote", GCC_LINKS["vote"]),
        (["活動", "活动", "event", "例會", "例会", "meetup"],
         "events", GCC_LINKS["events"]),
    ]

    for keywords, page_type, url in page_patterns:
        if any(kw in text_lower for kw in keywords):
            reply = _link_reply(lang, page_type, "", url)
            return LinkResult(matched=True, reply=reply, link_type=page_type)

    return LinkResult(matched=False)


def _link_reply(lang: str, link_type: str, name: str, url: str) -> str:
    """生成連結回覆文字（三語）"""
    meeting_reminder = {
        "zh-TW": "\n\n_如希望深入交流，歡迎參與 GCC 定期例會。_",
        "zh-CN": "\n\n_如希望深入交流，欢迎参与 GCC 定期例会。_",
        "en":    "\n\n_For deeper discussion, you're welcome to join GCC's regular community calls._",
    }
    reminder = meeting_reminder.get(lang, meeting_reminder["zh-TW"])

    templates = {
        "project": {
            "zh-TW": f"📄 *{name}* 的詳細資料：\n{url}{reminder}",
            "zh-CN": f"📄 *{name}* 的详细资料：\n{url}{reminder}",
            "en":    f"📄 Details about *{name}*:\n{url}{reminder}",
        },
        "apply": {
            "zh-TW": f"📋 GCC 資助申請說明：\n{url}{reminder}",
            "zh-CN": f"📋 GCC 资助申请说明：\n{url}{reminder}",
            "en":    f"📋 GCC Grant Application:\n{url}{reminder}",
        },
        "apply_public": {
            "zh-TW": f"📋 公共基金申請說明：\n{url}{reminder}",
            "zh-CN": f"📋 公共基金申请说明：\n{url}{reminder}",
            "en":    f"📋 Public Fund Application:\n{url}{reminder}",
        },
        "apply_special": {
            "zh-TW": f"📋 專項基金申請說明：\n{url}{reminder}",
            "zh-CN": f"📋 专项基金申请说明：\n{url}{reminder}",
            "en":    f"📋 Special Fund Application:\n{url}{reminder}",
        },
        "about": {
            "zh-TW": f"ℹ️ 關於 GCC：\n{url}{reminder}",
            "zh-CN": f"ℹ️ 关于 GCC：\n{url}{reminder}",
            "en":    f"ℹ️ About GCC:\n{url}{reminder}",
        },
        "projects": {
            "zh-TW": f"📦 GCC 所有資助項目：\n{url}{reminder}",
            "zh-CN": f"📦 GCC 所有资助项目：\n{url}{reminder}",
            "en":    f"📦 All GCC Funded Projects:\n{url}{reminder}",
        },
        "donate": {
            "zh-TW": f"💚 支持 GCC：\n{url}{reminder}",
            "zh-CN": f"💚 支持 GCC：\n{url}{reminder}",
            "en":    f"💚 Support GCC:\n{url}{reminder}",
        },
        "contact": {
            "zh-TW": f"📬 聯絡 GCC：\n{url}{reminder}",
            "zh-CN": f"📬 联络 GCC：\n{url}{reminder}",
            "en":    f"📬 Contact GCC:\n{url}{reminder}",
        },
        "vote": {
            "zh-TW": f"🗳️ GCC 治理投票：\n{url}{reminder}",
            "zh-CN": f"🗳️ GCC 治理投票：\n{url}{reminder}",
            "en":    f"🗳️ GCC Governance Voting:\n{url}{reminder}",
        },
        "events": {
            "zh-TW": f"📅 GCC 活動與例會：\n{url}{reminder}",
            "zh-CN": f"📅 GCC 活动与例会：\n{url}{reminder}",
            "en":    f"📅 GCC Events & Community Calls:\n{url}{reminder}",
        },
    }

    lang_key = lang if lang in ("zh-TW", "zh-CN", "en") else "zh-TW"
    return templates.get(link_type, {}).get(lang_key, f"{url}{reminder}")


# ── 三層 Prompt 組裝 ──────────────────────────────────────────────────────────

def build_messages(
    user_text: str,
    session: Session,
    lang: str = "zh-TW",
) -> list[dict]:
    """
    組裝傳給 AI API 的 messages 陣列。

    Layer 1 [system] — AgentValues（固定，從 values.yaml 載入）
    Layer 2 [system] — GCC 背景摘要
    Layer 3 [user/assistant] — Session 對話窗口（最近 20 條）
    新訊息 [user] — 用戶這條訊息

    Layer 1 永遠排在最前，用戶對話永遠排在它後面。
    """
    values = load_values()

    messages = []

    # ── Layer 1：價值觀（最高優先，固定）──────────────────
    messages.append({
        "role": "system",
        "content": as_system_block(values),
    })

    # ── Layer 2：GCC 背景摘要 ──────────────────────────────
    messages.append({
        "role": "system",
        "content": as_gcc_summary_block(values),
    })

    # ── Layer 3：對話窗口（最近 20 條）────────────────────
    context = session.get_context()
    messages.extend(context)

    # ── 新訊息 ────────────────────────────────────────────
    messages.append({
        "role": "user",
        "content": user_text,
    })

    return messages