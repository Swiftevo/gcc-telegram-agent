"""Deterministic application pre-screening."""

from gcc_agent.applications.models import ApplicationDraft
from gcc_agent.knowledge.loaders import load_projects, load_values


def pre_screen(draft: ApplicationDraft) -> tuple[int, str]:
    values = load_values()
    weights = {
        "mission_fit": int(values.screening_rubric.get("mission_fit", 40)),
        "public_goods_nature": int(values.screening_rubric.get("public_goods_nature", 30)),
        "chinese_community": int(values.screening_rubric.get("chinese_community", 20)),
        "feasibility": int(values.screening_rubric.get("feasibility", 10)),
    }
    text = f"{draft.project_name} {draft.executive_summary}".lower()
    notes: list[str] = []

    best_name, best_overlap = "", 0
    for project in load_projects():
        overlap = sum(1 for word in project.get("keywords", []) if word.lower() in text)
        if overlap > best_overlap:
            best_name, best_overlap = project.get("name", ""), overlap
    notes.append(
        f"🔍 與已資助項目相似：{best_name}（{best_overlap} 個關鍵詞重疊）"
        if best_overlap
        else "🔍 未找到與已資助項目的明顯相似性，需人工判斷"
    )

    mission = (
        "開源", "开源", "open source", "公共", "public good", "治理", "governance",
        "隱私", "隐私", "privacy", "抗審查", "抗审查", "去中心", "decentrali",
        "區塊鏈", "blockchain", "以太坊", "ethereum", "協議", "协议", "protocol",
        "社區", "社区", "community", "零知識", "零知识", "zk", "安全", "security",
    )
    hits = sum(word in text for word in mission)
    mission_score = weights["mission_fit"] if hits >= 3 else int(weights["mission_fit"] * (0.6 if hits else 0.2))
    notes.append("✅ 使命契合度高" if hits >= 3 else "🔶 使命契合度待確認")

    rejected = any(word in text for word in ("commercial", "商業", "商业", "proprietary", "closed source", "不開源"))
    public_hits = sum(
        word in text for word in
        ("開源", "开源", "open source", "免費", "free", "公共", "public", "非營利",
         "infrastructure", "工具", "tool", "平台", "platform", "協議", "protocol")
    )
    public_score = 0 if rejected else (
        weights["public_goods_nature"] if public_hits >= 2
        else int(weights["public_goods_nature"] * (0.6 if public_hits else 0.3))
    )
    notes.append("🔴 疑似不符合公共物品標準" if rejected else "✅ 公共物品屬性已評估")

    chinese_hits = any(
        word in text for word in
        ("華語", "华语", "中文", "chinese", "台灣", "taiwan", "香港", "中國", "china")
    )
    chinese_score = weights["chinese_community"] if chinese_hits else int(weights["chinese_community"] * 0.4)
    notes.append("✅ 明確提及華語社區" if chinese_hits else "🔶 未明確提及華語社區影響")

    length = len(draft.executive_summary.strip())
    feasibility = weights["feasibility"] if length >= 200 else (
        int(weights["feasibility"] * 0.6) if length >= 80 else 0
    )
    notes.append(
        "✅ 摘要詳盡"
        if length >= 200
        else ("🔶 摘要可行性待確認" if length >= 80 else "🔴 摘要過於簡短")
    )
    return mission_score + public_score + chinese_score + feasibility, "\n".join(notes)
