"""
models.py — GCC Telegram Agent 資料結構定義
所有 dataclass 在此定義，db.py 和 handlers 都從這裡 import
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid


# ── User ──────────────────────────────────────────────────────────────────────

@dataclass
class User:
    """
    Telegram 用戶記錄。
    首次發訊息時自動建立，之後每次請求都會更新 daily_count。
    """
    user_id: int                          # Telegram user ID（主鍵）
    username: str = ""                    # @username（可能為空，不是每個用戶都有）
    first_name: str = ""                  # Telegram 顯示名字
    detected_lang: str = "zh-TW"         # 自動偵測語言，跟隨用戶回應
    is_group_member: bool = False         # 是否已通過 GCC 群組驗證
    is_blocked: bool = False              # 管理員封鎖標記
    daily_count: int = 0                  # 今日已發訊息數（上限 20）
    count_reset_date: str = ""            # 上次重置日期，格式 "YYYY-MM-DD"
    total_messages: int = 0              # 歷史累計訊息數（監控用）
    created_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    last_seen_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    def is_rate_limited(self) -> bool:
        """檢查今日是否已達上限（20 條）"""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self.count_reset_date != today:
            return False  # 日期已變，計數器尚未重置，不算超限
        return self.daily_count >= 20

    def reset_if_new_day(self) -> bool:
        """
        如果已是新的一天，重置計數器。
        返回 True 表示有重置，False 表示今天已經重置過了。
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self.count_reset_date != today:
            self.daily_count = 0
            self.count_reset_date = today
            return True
        return False


# ── ApplicationDraft ──────────────────────────────────────────────────────────

@dataclass
class ApplicationDraft:
    """
    申請草稿，嵌入在 Session 內。
    四步收集流程：名稱 → 類型 → 提案連結（選填）→ 執行摘要（500字）
    完成後觸發 Values Engine 預審，生成摘要通知管理員。
    """
    project_name:      str = ""       # 步驟 1：項目名稱
    fund_type:         str = "unknown"  # 步驟 2："public" | "special" | "unknown"
    proposal_link:     str = ""       # 步驟 3：提案文件連結（選填，可跳過）
    executive_summary: str = ""       # 步驟 4：500 字以內執行摘要（必填）
    collection_step:   int = 0        # 目前收集進度（0=未開始，1，2，3，4=完成）

    # 預審結果（步驟 4 完成後由 Values Engine 填入）
    agent_score: int = -1             # 預審總分（0-100），-1 表示尚未評分
    agent_notes: str = ""             # 各維度分析文字
    submitted_at: Optional[str] = None  # 提交給管理員的時間

    def is_complete(self) -> bool:
        """四個必填欄位都已收集完畢（proposal_link 為選填）"""
        return (
            self.collection_step >= 4
            and self.project_name.strip() != ""
            and self.fund_type in ("public", "special")
            and self.executive_summary.strip() != ""
        )

    def next_question(self, lang: str = "zh-TW") -> str:
        """根據目前進度，返回下一個要問用戶的問題"""
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
                "Which fund are you applying for?\n\n🔹 *Public Fund* — General pool supporting high-impact digital public goods\n🔹 *Special Fund* — Small, fast grants (travel scholarships, university grants, etc.)\n\nPlease reply 'public' or 'special'.",
                "Finally, please describe your project in one sentence (what public problem does it solve?).",
            ],
        }
        lang_key = lang if lang in questions else "zh-TW"
        step = self.collection_step  # 0, 1, 2
        if step < len(questions[lang_key]):
            return questions[lang_key][step]
        return ""

    def parse_fund_type(self, text: str) -> str:
        """
        解析用戶輸入的基金類型，容錯處理繁簡中英文。
        返回 "public" | "special" | "unknown"
        """
        t = text.strip().lower()
        public_keywords = ["公共", "public", "通用", "general"]
        special_keywords = ["專項", "专项", "special", "小額", "小额"]
        if any(k in t for k in public_keywords):
            return "public"
        if any(k in t for k in special_keywords):
            return "special"
        return "unknown"


# ── Session ───────────────────────────────────────────────────────────────────

@dataclass
class Session:
    """
    對話 Session。
    30 分鐘無活動後自動建立新 Session。
    保留最近 20 條訊息用於 AI context。
    """
    session_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    user_id: int = 0
    mode: str = "general"                # "general" | "application"
    messages: List[dict] = field(
        default_factory=list
    )                                    # [{"role": "user"|"assistant", "content": "..."}]
    application_draft: ApplicationDraft = field(
        default_factory=ApplicationDraft
    )
    created_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    last_active: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    SESSION_TIMEOUT_MINUTES: int = field(default=30, init=False, repr=False)
    MAX_CONTEXT_MESSAGES: int = field(default=20, init=False, repr=False)

    def is_expired(self) -> bool:
        """檢查 Session 是否已超過 30 分鐘無活動"""
        try:
            last = datetime.fromisoformat(self.last_active)
            delta = (datetime.utcnow() - last).total_seconds() / 60
            return delta > self.SESSION_TIMEOUT_MINUTES
        except Exception:
            return True

    def get_context(self) -> List[dict]:
        """返回最近 20 條訊息，用於組裝 AI Prompt"""
        return self.messages[-self.MAX_CONTEXT_MESSAGES:]

    def add_message(self, role: str, content: str) -> None:
        """新增一條訊息到 Session"""
        self.messages.append({"role": role, "content": content})
        self.last_active = datetime.utcnow().isoformat()

    def touch(self) -> None:
        """更新最後活動時間"""
        self.last_active = datetime.utcnow().isoformat()


# ── Message ───────────────────────────────────────────────────────────────────

@dataclass
class Message:
    """
    單條訊息記錄，持久化到 DB。
    Session.messages 是記憶體中的輕量版本（只存 role + content）。
    Message 是完整的 DB 記錄，包含 token 追蹤。
    """
    message_id: str = field(
        default_factory=lambda: str(uuid.uuid4())
    )
    session_id: str = ""
    user_id: int = 0
    role: str = "user"                   # "user" | "assistant"
    content: str = ""
    tokens_used: int = 0                 # 此次 API 呼叫消耗的 token（assistant 訊息才有）
    link_served: bool = False            # True 表示以網站連結代替 AI 回應（節省 token）
    created_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


# ── AgentValues ───────────────────────────────────────────────────────────────
# 注意：AgentValues 不儲存到 DB，從 values.yaml 載入。
# 完整實作在 core/values.py。
# 這裡只定義資料結構供 type hint 使用。

@dataclass
class AgentValues:
    """
    價值觀模組。從 values.yaml 載入，永不寫入 DB。
    用戶對話無法修改此物件的任何欄位。
    """
    version: str = "1.0.0"
    updated_by_admin_id: str = ""
    mission_statement: str = ""
    priority_themes: List[str] = field(default_factory=list)
    rejection_criteria: List[str] = field(default_factory=list)
    screening_rubric: dict = field(default_factory=dict)
    tone_guidelines: str = ""
    gcc_summary: str = ""