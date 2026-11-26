"""Format fixed, content-owner-approved GCC history answers."""

from gcc_agent.qa.messages import COMMUNITY_INVITE_FOOTER


_FALLBACK_NOTES = {
    "zh-CN": "以下为已经人工审核的繁体中文历史资料：\n\n",
    "en": "The approved historical answer is currently available in Traditional Chinese:\n\n",
}
_SOURCE_LABELS = {
    "zh-TW": "歷史資料來源",
    "zh-CN": "历史资料来源",
    "en": "Historical source",
}
_REMINDERS = COMMUNITY_INVITE_FOOTER


def format_history_projection_reply(projection: dict, lang: str) -> str:
    """Return the fixed answer, public citation and an explicit locale fallback."""
    selected_lang = lang if lang in _SOURCE_LABELS else "zh-TW"
    citation = projection.get("citation", {})
    source_label = citation.get("label", "GCC historical report")
    source_url = citation.get("url", "")
    fallback = _FALLBACK_NOTES.get(selected_lang, "")
    return (
        f"{fallback}{projection.get('answer_text', '')}\n\n"
        f"{_SOURCE_LABELS[selected_lang]}：[{source_label}]({source_url})"
        f"{_REMINDERS[selected_lang]}"
    )
