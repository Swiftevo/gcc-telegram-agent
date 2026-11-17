"""External application handoff; the Bot never collects or submits proposals."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


APPLICATION_URL = "https://www.gccofficial.org/application"

_LABELS = {
    "zh-TW": "📋 查看官方申請表",
    "zh-CN": "📋 查看官方申请表",
    "en": "📋 View official application forms",
}

_TEXT = {
    "zh-TW": (
        "GCC 資助申請請使用官方網站的外部表格：\n"
        f"{APPLICATION_URL}\n\n"
        "請在網站確認目前開放的計劃及申請條件。Bot 不收集、評分或提交申請。"
    ),
    "zh-CN": (
        "申请 GCC 资助请使用官网的外部表格：\n"
        f"{APPLICATION_URL}\n\n"
        "请在网站确认当前开放的计划和申请条件。Bot 不收集、评分或提交申请。"
    ),
    "en": (
        "Apply for GCC funding through the official external forms:\n"
        f"{APPLICATION_URL}\n\n"
        "Check the website for current programmes and eligibility. The Bot does not "
        "collect, score, or submit applications."
    ),
}

_LEGACY = {
    "zh-TW": "舊 Bot 內草稿沒有轉交到外部表格，也不代表已正式提交。請在官方表格重新填寫。",
    "zh-CN": "旧 Bot 内草稿没有转入外部表格，也不代表已正式提交。请在官方表格重新填写。",
    "en": "Your old in-Bot draft was not transferred to the external form and is not a formal submission. Please complete the official form.",
}


def handoff_text(lang: str, *, legacy: bool = False) -> str:
    selected = lang if lang in _TEXT else "zh-TW"
    return _TEXT[selected] + ("\n\n" + _LEGACY[selected] if legacy else "")


def make_apply_markup(lang: str, *, url: str = APPLICATION_URL) -> InlineKeyboardMarkup:
    if url not in (
        APPLICATION_URL,
        "https://www.gccofficial.org/application/public",
        "https://www.gccofficial.org/application/special",
    ):
        raise ValueError("application URL must be an approved official landing page")
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(_LABELS.get(lang, _LABELS["zh-TW"]), url=url)
    ]])
