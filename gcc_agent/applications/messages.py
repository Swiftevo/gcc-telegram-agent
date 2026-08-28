"""Localized application workflow messages."""

TEXTS = {
    "intro": {
        "zh-TW": "好的！讓我收集你的基本申請資料。\n\n請問你的項目名稱是什麼？",
        "zh-CN": "好的！让我收集你的基本申请资料。\n\n请问你的项目名称是什么？",
        "en": "Sure! Let me collect some basic information about your application.\n\nWhat is the name of your project?",
    },
    "ask_fund_type": {
        "zh-TW": "收到！項目名稱：*{name}*\n\n請問你想申請哪種基金？\n\n🔹 *公共基金* — 通用資助池，支持高影響力的數字公共物品，評審週期 8-12 週\n🔹 *專項基金* — 快速小額支持（機票計劃、高校 Web3、GCC×706、GCC×Mastodon）\n\n請回覆「公共」或「專項」。",
        "zh-CN": "收到！项目名称：*{name}*\n\n请问你想申请哪种基金？\n\n🔹 *公共基金* — 通用资助池，支持高影响力的数字公共物品，评审周期 8-12 周\n🔹 *专项基金* — 快速小额支持（机票计划、高校 Web3、GCC×706、GCC×Mastodon）\n\n请回复「公共」或「专项」。",
        "en": "Got it! Project name: *{name}*\n\nWhich fund are you applying for?\n\n🔹 *Public Fund* — General pool for high-impact digital public goods, 8-12 week review\n🔹 *Special Fund* — Fast small grants (travel scholarships, university Web3, GCC×706, GCC×Mastodon)\n\nPlease reply 'public' or 'special'.",
    },
    "ask_proposal_link": {
        "zh-TW": "好的，申請 *{fund}*。\n\n📎 *第三步：提案文件連結（選填）*\n\n如有完整提案文件，請提供連結（Google Doc / Notion / PDF）。\n尚未準備好文件？請直接回覆「跳過」。",
        "zh-CN": "好的，申请 *{fund}*。\n\n📎 *第三步：提案文件链接（选填）*\n\n如有完整提案文件，请提供链接（Google Doc / Notion / PDF）。\n尚未准备好文件？请直接回复「跳过」。",
        "en": "Got it, applying for the *{fund}*.\n\n📎 *Step 3: Proposal Document Link (optional)*\n\nIf you have a full proposal document, please share the link (Google Doc / Notion / PDF).\nNot ready yet? Just reply 'skip'.",
    },
    "ask_executive_summary": {
        "zh-TW": "📝 *最後一步：執行摘要*\n\n請用 *500 字以內* 說明你的提案核心，包括：\n\n• 你解決了什麼公共問題？\n• 你的解決方案是什麼？\n• 為什麼這個問題需要公共資金支持？\n\n_這份摘要將作為 GCC 成員初步評審的依據。_",
        "zh-CN": "📝 *最后一步：执行摘要*\n\n请用 *500 字以内* 说明你的提案核心，包括：\n\n• 你解决了什么公共问题？\n• 你的解决方案是什么？\n• 为什么这个问题需要公共资金支持？\n\n_这份摘要将作为 GCC 成员初步评审的依据。_",
        "en": "📝 *Final Step: Executive Summary*\n\nPlease describe your proposal in *under 500 words*, covering:\n\n• What public problem are you solving?\n• What is your solution?\n• Why does this problem require public funding?\n\n_This summary will be used for GCC's initial review._",
    },
    "summary_too_long": {
        "zh-TW": "你的摘要超過 500 字（目前約 {count} 字）。請精簡後重新提交，重點說明核心問題和解決方案。",
        "zh-CN": "你的摘要超过 500 字（目前约 {count} 字）。请精简后重新提交，重点说明核心问题和解决方案。",
        "en": "Your summary exceeds 500 words (currently ~{count} words). Please shorten it and resubmit, focusing on the core problem and solution.",
    },
    "unknown_fund_type": {
        "zh-TW": "請回覆「公共」或「專項」，讓我知道你想申請哪種基金。",
        "zh-CN": "请回复「公共」或「专项」，让我知道你想申请哪种基金。",
        "en": "Please reply 'public' or 'special' to let me know which fund you'd like to apply for.",
    },
    "submitted": {
        "zh-TW": "✅ 收到你的申請摘要！\n\nGCC 成員會查看你的資料並與你跟進。\n\n如果想正式提交申請，可以直接填寫申請表：\n📋 https://www.gccofficial.org/application\n\n_如希望深入交流，歡迎參與 GCC 定期例會。_",
        "zh-CN": "✅ 收到你的申请摘要！\n\nGCC 成员会查看你的资料并与你跟进。\n\n如果想正式提交申请，可以直接填写申请表：\n📋 https://www.gccofficial.org/application\n\n_如希望深入交流，欢迎参与 GCC 定期例会。_",
        "en": "✅ Your application summary has been received!\n\nA GCC member will review your information and follow up with you.\n\nTo submit a formal application, you can fill out the form directly:\n📋 https://www.gccofficial.org/application\n\n_For deeper discussion, you're welcome to join GCC's regular community calls._",
    },
}

FUND_NAMES = {
    "public": {"zh-TW": "公共基金", "zh-CN": "公共基金", "en": "Public Fund"},
    "special": {"zh-TW": "專項基金", "zh-CN": "专项基金", "en": "Special Fund"},
}


def text(lang: str, key: str, **kwargs) -> str:
    template = TEXTS.get(key, {}).get(lang, TEXTS.get(key, {}).get("zh-TW", ""))
    if "fund" in kwargs and kwargs["fund"] in FUND_NAMES:
        kwargs["fund"] = FUND_NAMES[kwargs["fund"]].get(lang, kwargs["fund"])
    return template.format(**kwargs)
