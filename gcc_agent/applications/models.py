"""Application workflow state."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ApplicationDraft:
    project_name: str = ""
    fund_type: str = "unknown"
    proposal_link: str = ""
    executive_summary: str = ""
    collection_step: int = 0
    agent_score: int = -1
    agent_notes: str = ""
    submitted_at: Optional[str] = None

    def is_complete(self) -> bool:
        return (
            self.collection_step >= 4
            and bool(self.project_name.strip())
            and self.fund_type in ("public", "special")
            and bool(self.executive_summary.strip())
        )

    def next_question(self, lang: str = "zh-TW") -> str:
        questions = {
            "zh-TW": [
                "請問你的項目名稱是什麼？",
                "請問你想申請哪種基金？\n\n🔹 *公共基金* — 通用資助池，支持高影響力的數字公共物品\n🔹 *專項基金* — 小額快速支持（機票計劃、高校專項等）\n\n請回覆「公共」或「專項」。",
                "最後，請用一句話介紹你的項目（解決了什麼公共問題）。",
            ],
            "zh-CN": [
                "请问你的项目名称是什么？",
                "请问你想申请哪种基金？\n\n🔹 *公共基金* — 通用资助池，支持高影响力的数字公共物品\n🔹 *专项基金* — 小额快速支持（机票计划、高校专项等）\n\n请回复「公共」或「专项」。",
                "最后，请用一句话介绍你的项目（解决了什么公共问题）。",
            ],
            "en": [
                "What is the name of your project?",
                "Which fund are you applying for?\n\n🔹 *Public Fund* — General pool supporting high-impact digital public goods\n🔹 *Special Fund* — Small, fast grants\n\nPlease reply 'public' or 'special'.",
                "Finally, describe your project in one sentence.",
            ],
        }
        choices = questions.get(lang, questions["zh-TW"])
        return choices[self.collection_step] if self.collection_step < len(choices) else ""

    def parse_fund_type(self, text: str) -> str:
        value = text.strip().lower()
        if any(word in value for word in ("公共", "public", "通用", "general")):
            return "public"
        if any(word in value for word in ("專項", "专项", "special", "小額", "小额")):
            return "special"
        return "unknown"
