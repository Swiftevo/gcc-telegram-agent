"""Minimum, current-state privacy notice for Telegram users."""

from __future__ import annotations


CONTACT_URL = "https://www.gccofficial.org/contact"

PRIVACY_NOTICES = {
    "zh-TW": (
        "🔒 GCC AI 助手資料告知（現況）\n\n"
        "處理的資料：Telegram 用戶、群組及 topic 識別碼、公開個人檔案與語言、"
        "存取狀態，以及你傳送的訊息和 Bot 回覆。現行申請流程亦會處理申請草稿。"
        "當你在私訊提出一般問題或使用 /whoami 時，Bot 會向 Telegram 查核你是否仍是"
        "指定 GCC 群組成員，並更新本機存取狀態。"
        "郵箱驗證目前暫停，不接受新郵箱或驗證碼；SQLite 及備份仍可能包含 legacy "
        "郵箱驗證欄位或記錄。\n\n"
        "保存與接收者：Telegram 傳送互動；Fly.io 託管程式、logs、SQLite volume 及"
        "scheduled snapshots，operator 亦可建立手動備份。官方連結或既定事實不足以回答時，OpenAI 會收到目前問題及同一 session"
        " 最多 20 條近期訊息。目前不會透過 SMTP 發送驗證郵件。"
        "完成現行申請時，內容可能另傳至 GCC 管理員的 Telegram。\n\n"
        "部分記錄目前沒有自動刪除期限；第三方或管理員 Telegram 內的複本也不由 Bot "
        "資料庫控制。請勿傳送密碼、私鑰或不必要的敏感資料。GCC 尚在制定保存及資料"
        "要求流程，本告知不承諾尚未批准的期限或程序。\n\n"
        f"私隱問題或意見：{CONTACT_URL}"
    ),
    "zh-CN": (
        "🔒 GCC AI 助手数据告知（现状）\n\n"
        "处理的数据：Telegram 用户、群组及 topic 标识符、公开个人资料与语言、"
        "访问状态，以及你发送的消息和 Bot 回复。现行申请流程还会处理申请草稿。"
        "当你在私聊提出一般问题或使用 /whoami 时，Bot 会向 Telegram 查询你是否仍是"
        "指定 GCC 群组成员，并更新本地访问状态。"
        "邮箱验证目前暂停，不接受新邮箱或验证码；SQLite 及备份仍可能包含 legacy "
        "邮箱验证字段或记录。\n\n"
        "保存与接收方：Telegram 传送互动；Fly.io 托管程序、logs、SQLite volume 及"
        "scheduled snapshots，operator 也可建立手动备份。官方链接或既定事实不足以回答时，OpenAI 会收到当前问题及同一 session"
        " 最多 20 条近期消息。目前不会通过 SMTP 发送验证邮件。"
        "完成现行申请时，内容可能另传至 GCC 管理员的 Telegram。\n\n"
        "部分记录目前没有自动删除期限；第三方或管理员 Telegram 内的副本也不由 Bot "
        "数据库控制。请勿发送密码、私钥或不必要的敏感数据。GCC 尚在制定保存及数据"
        "请求流程，本告知不承诺尚未批准的期限或程序。\n\n"
        f"隐私问题或意见：{CONTACT_URL}"
    ),
    "en": (
        "🔒 GCC AI Assistant data notice (current state)\n\n"
        "Data processed: Telegram user, group, and topic identifiers; public profile "
        "and language; access state; and the messages you send and the Bot's replies. "
        "For a general private question or /whoami, the Bot asks Telegram whether you "
        "are still a member of the configured GCC group and updates the local access state. The "
        "current application flow also processes application drafts. Email "
        "verification is paused and no new address or code is accepted; SQLite and "
        "backups may still contain legacy email-verification fields or records.\n\n"
        "Storage and recipients: Telegram carries the interaction. Fly.io hosts the "
        "application, logs, the SQLite volume, and scheduled snapshots; an operator "
        "can also create a manual backup. When an official link or "
        "established fact cannot answer the question, OpenAI receives the current "
        "question and up to 20 recent messages from the same session. No verification "
        "mail is currently sent through SMTP. A completed application may also be sent to a GCC administrator on "
        "Telegram.\n\n"
        "Some records currently have no automatic deletion period. Copies held by "
        "third parties or in an administrator's Telegram are not controlled by the "
        "Bot database. Do not send passwords, private keys, or unnecessary sensitive "
        "data. GCC is still defining retention and data-request procedures; this "
        "notice does not promise an unapproved period or process.\n\n"
        f"Privacy questions or feedback: {CONTACT_URL}"
    ),
}


def privacy_notice(lang: str) -> str:
    """Return the notice in a supported locale, falling back to Traditional Chinese."""
    return PRIVACY_NOTICES.get(lang, PRIVACY_NOTICES["zh-TW"])


def is_privacy_request(text: str) -> bool:
    """Match only explicit short requests so normal privacy discussions still reach Q&A."""
    normalized = " ".join((text or "").strip().lower().split()).rstrip("?？.!。！")
    return normalized in {
        "/privacy",
        "privacy",
        "privacy notice",
        "data notice",
        "私隱",
        "私隱說明",
        "資料告知",
        "隐私",
        "隐私说明",
        "数据告知",
    }
