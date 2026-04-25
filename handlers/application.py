"""
handlers/application.py — 申請流程處理
三步收集：項目名稱 → 基金類型 → 一句話介紹
完成後：Values Engine 預審評分 → 生成摘要 → 通知管理員
"""

import logging
import os
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from core.session import get_session, save_exchange, save
from handlers.guard import GuardResult
from models import ApplicationDraft

logger = logging.getLogger(__name__)

ADMIN_NOTIFY_ID = int(os.getenv("ADMIN_NOTIFY_ID", "0"))


# ── 回覆文字（三語）──────────────────────────────────────────────────────────

def _t(lang: str, key: str, **kwargs) -> str:
    texts = {
        "intro": {
            "zh-TW": "好的！讓我收集你的基本申請資料。\n\n請問你的項目名稱是什麼？",
            "zh-CN": "好的！让我收集你的基本申请资料。\n\n请问你的项目名称是什么？",
            "en":    "Sure! Let me collect some basic information about your application.\n\nWhat is the name of your project?",
        },
        "ask_fund_type": {
            "zh-TW": (
                "收到！項目名稱：*{name}*\n\n"
                "請問你想申請哪種基金？\n\n"
                "🔹 *公共基金* — 通用資助池，支持高影響力的數字公共物品，評審週期 8-12 週\n"
                "🔹 *專項基金* — 快速小額支持（機票計劃、高校 Web3、GCC×706、GCC×Mastodon）\n\n"
                "請回覆「公共」或「專項」。"
            ),
            "zh-CN": (
                "收到！项目名称：*{name}*\n\n"
                "请问你想申请哪种基金？\n\n"
                "🔹 *公共基金* — 通用资助池，支持高影响力的数字公共物品，评审周期 8-12 周\n"
                "🔹 *专项基金* — 快速小额支持（机票计划、高校 Web3、GCC×706、GCC×Mastodon）\n\n"
                "请回复「公共」或「专项」。"
            ),
            "en": (
                "Got it! Project name: *{name}*\n\n"
                "Which fund are you applying for?\n\n"
                "🔹 *Public Fund* — General pool for high-impact digital public goods, 8-12 week review\n"
                "🔹 *Special Fund* — Fast small grants (travel scholarships, university Web3, GCC×706, GCC×Mastodon)\n\n"
                "Please reply 'public' or 'special'."
            ),
        },
        "ask_one_liner": {
            "zh-TW": (
                "好的，申請 *{fund}*。\n\n"
                "最後一步：請用一句話介紹你的項目。\n"
                "_（這句話的重點：你解決了什麼公共問題？）_"
            ),
            "zh-CN": (
                "好的，申请 *{fund}*。\n\n"
                "最后一步：请用一句话介绍你的项目。\n"
                "_（这句话的重点：你解决了什么公共问题？）_"
            ),
            "en": (
                "Got it, applying for the *{fund}*.\n\n"
                "Last step: please describe your project in one sentence.\n"
                "_(Focus: what public problem does it solve?)_"
            ),
        },
        "unknown_fund_type": {
            "zh-TW": "請回覆「公共」或「專項」，讓我知道你想申請哪種基金。",
            "zh-CN": "请回复「公共」或「专项」，让我知道你想申请哪种基金。",
            "en":    "Please reply 'public' or 'special' to let me know which fund you'd like to apply for.",
        },
        "submitted": {
            "zh-TW": (
                "✅ 收到你的初步申請資料！\n\n"
                "GCC 成員會查看你的資料並與你跟進。\n\n"
                "如果想正式提交申請，可以直接填寫申請表：\n"
                "📋 https://www.gccofficial.org/application\n\n"
                "_如希望深入交流，歡迎參與 GCC 定期例會。_"
            ),
            "zh-CN": (
                "✅ 收到你的初步申请资料！\n\n"
                "GCC 成员会查看你的资料并与你跟进。\n\n"
                "如果想正式提交申请，可以直接填写申请表：\n"
                "📋 https://www.gccofficial.org/application\n\n"
                "_如希望深入交流，欢迎参与 GCC 定期例会。_"
            ),
            "en": (
                "✅ Your initial application details have been received!\n\n"
                "A GCC member will review your information and follow up with you.\n\n"
                "To submit a formal application, you can fill out the form directly:\n"
                "📋 https://www.gccofficial.org/application\n\n"
                "_For deeper discussion, you're welcome to join GCC's regular community calls._"
            ),
        },
        "cancelled": {
            "zh-TW": "申請已取消。有其他問題歡迎繼續發問。\n\n_如希望深入交流，歡迎參與 GCC 定期例會。_",
            "zh-CN": "申请已取消。有其他问题欢迎继续提问。\n\n_如希望深入交流，欢迎参与 GCC 定期例会。_",
            "en":    "Application cancelled. Feel free to ask if you have other questions.\n\n_For deeper discussion, join GCC's regular community calls._",
        },
    }

    fund_names = {
        "public":  {"zh-TW": "公共基金", "zh-CN": "公共基金", "en": "Public Fund"},
        "special": {"zh-TW": "專項基金", "zh-CN": "专项基金", "en": "Special Fund"},
    }

    template = texts.get(key, {}).get(lang, texts.get(key, {}).get("zh-TW", ""))
    if "fund" in kwargs and kwargs["fund"] in fund_names:
        kwargs["fund"] = fund_names[kwargs["fund"]].get(lang, kwargs["fund"])
    return template.format(**kwargs)


# ── Values Engine 預審 ────────────────────────────────────────────────────────

def pre_screen(draft: ApplicationDraft) -> tuple[int, str]:
    """
    根據 values.yaml 的 screening_rubric 對申請草稿進行預審評分。
    返回 (score, notes)。

    這是基於關鍵詞的輕量評分，不呼叫 AI API。
    目的是給管理員一個初步參考，而不是最終判斷。
    """
    from core.values import load_values
    values = load_values()
    rubric = values.screening_rubric

    weights = {
        "mission_fit":         int(rubric.get("mission_fit", 40)),
        "public_goods_nature": int(rubric.get("public_goods_nature", 30)),
        "chinese_community":   int(rubric.get("chinese_community", 20)),
        "feasibility":         int(rubric.get("feasibility", 10)),
    }

    text = f"{draft.project_name} {draft.one_liner}".lower()
    notes = []
    score = 0

    # ── mission_fit（使命契合度）────────────────────────────
    mission_keywords = [
        "開源", "开源", "open source", "公共", "public good", "治理", "governance",
        "隱私", "隐私", "privacy", "抗審查", "抗审查", "censorship",
        "去中心", "decentrali", "區塊鏈", "blockchain", "以太坊", "ethereum",
        "協議", "协议", "protocol", "公民", "citizen", "社區", "社区", "community",
    ]
    mission_hits = sum(1 for kw in mission_keywords if kw in text)
    if mission_hits >= 3:
        mission_score = weights["mission_fit"]
        notes.append(f"✅ 使命契合度高（{mission_hits} 個相關關鍵詞）")
    elif mission_hits >= 1:
        mission_score = int(weights["mission_fit"] * 0.6)
        notes.append(f"🔶 使命契合度中等（{mission_hits} 個相關關鍵詞）")
    else:
        mission_score = int(weights["mission_fit"] * 0.2)
        notes.append("🔴 使命契合度低，需進一步了解")
    score += mission_score

    # ── public_goods_nature（公共物品屬性）──────────────────
    pg_keywords = [
        "開源", "开源", "open source", "免費", "free", "公共", "public",
        "非營利", "non-profit", "nonprofit", "基礎設施", "infrastructure",
        "工具", "tool", "平台", "platform", "協議", "protocol",
    ]
    reject_keywords = [kw.lower() for kw in values.rejection_criteria]
    reject_hit = any(kw in text for kw in [
        "commercial", "商業", "商业", "proprietary", "closed source",
        "核心部分不開源", "不開源",
    ])

    if reject_hit:
        pg_score = 0
        notes.append("🔴 疑似不符合公共物品標準（含商業/閉源關鍵詞）")
    else:
        pg_hits = sum(1 for kw in pg_keywords if kw in text)
        if pg_hits >= 2:
            pg_score = weights["public_goods_nature"]
            notes.append(f"✅ 公共物品屬性明顯（{pg_hits} 個相關詞）")
        elif pg_hits >= 1:
            pg_score = int(weights["public_goods_nature"] * 0.6)
            notes.append("🔶 公共物品屬性待確認")
        else:
            pg_score = int(weights["public_goods_nature"] * 0.3)
            notes.append("🔴 公共物品屬性不明確")
    score += pg_score

    # ── chinese_community（華語社區影響）────────────────────
    cn_keywords = [
        "華語", "华语", "中文", "chinese", "台灣", "taiwan", "香港", "hong kong",
        "中國", "china", "東南亞", "southeast asia", "華人", "华人",
    ]
    cn_hits = sum(1 for kw in cn_keywords if kw in text)
    if cn_hits >= 1:
        cn_score = weights["chinese_community"]
        notes.append("✅ 明確提及華語社區")
    else:
        cn_score = int(weights["chinese_community"] * 0.4)
        notes.append("🔶 未明確提及華語社區影響（可在例會中進一步說明）")
    score += cn_score

    # ── feasibility（可行性）────────────────────────────────
    # 基於描述長度和清晰度的粗略判斷
    one_liner_len = len(draft.one_liner.strip())
    if one_liner_len >= 30:
        feasibility_score = weights["feasibility"]
        notes.append("✅ 項目描述清晰")
    elif one_liner_len >= 10:
        feasibility_score = int(weights["feasibility"] * 0.6)
        notes.append("🔶 項目描述較簡短，可行性待確認")
    else:
        feasibility_score = 0
        notes.append("🔴 項目描述過於簡短")
    score += feasibility_score

    return score, "\n".join(notes)


# ── 管理員通知 ────────────────────────────────────────────────────────────────

async def notify_admin(
    context: ContextTypes.DEFAULT_TYPE,
    draft: ApplicationDraft,
    user,
    lang: str,
) -> bool:
    """
    發送申請摘要到管理員指定帳號。
    返回 True 表示發送成功。
    """
    if ADMIN_NOTIFY_ID == 0:
        logger.warning("ADMIN_NOTIFY_ID 未設定，跳過管理員通知")
        return False

    fund_label = {
        "public":  "公共基金 (Public Fund)",
        "special": "專項基金 (Special Fund)",
        "unknown": "未知",
    }.get(draft.fund_type, "未知")

    score = draft.agent_score
    if score >= 70:
        score_label = f"🟢 {score}/100（建議跟進）"
    elif score >= 40:
        score_label = f"🟡 {score}/100（可參與例會進一步了解）"
    else:
        score_label = f"🔴 {score}/100（可能不符合方向）"

    username_display = f"@{user.username}" if user.username else f"ID: {user.user_id}"

    summary = (
        f"📬 *新申請通知*\n"
        f"{'─' * 30}\n"
        f"👤 申請人：{username_display}（{user.first_name}）\n"
        f"🆔 User ID：`{user.user_id}`\n"
        f"🌐 語言：{lang}\n"
        f"{'─' * 30}\n"
        f"📌 項目名稱：*{draft.project_name}*\n"
        f"💰 申請基金：{fund_label}\n"
        f"📝 一句話介紹：\n_{draft.one_liner}_\n"
        f"{'─' * 30}\n"
        f"🤖 *Agent 預審*\n"
        f"總分：{score_label}\n\n"
        f"{draft.agent_notes}\n"
        f"{'─' * 30}\n"
        f"📅 提交時間：{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_NOTIFY_ID,
            text=summary,
            parse_mode="Markdown",
        )
        logger.info(f"管理員通知已發送：{draft.project_name} score={score}")
        return True
    except Exception as e:
        logger.error(f"管理員通知發送失敗：{e}")
        return False


# ── 主要 Handler ──────────────────────────────────────────────────────────────

async def handle_application(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    guard: GuardResult,
) -> None:
    """
    申請流程主處理器。
    根據 session.application_draft.collection_step 決定目前在哪一步。

    Step 0 → 介紹流程，詢問項目名稱
    Step 1 → 收到名稱，詢問基金類型
    Step 2 → 收到類型，詢問一句話介紹
    Step 3 → 收到介紹，預審 + 通知管理員 + 確認用戶
    """
    text = (update.message.text or "").strip()
    lang = guard.lang
    user = guard.user
    user_id = user.user_id

    session = await get_session(guard)
    draft = session.application_draft

    # ── Step 0：開始收集，詢問項目名稱 ───────────────────
    if draft.collection_step == 0:
        reply = _t(lang, "intro")
        draft.collection_step = 1
        await update.message.reply_text(reply, parse_mode="Markdown")
        await save_exchange(session, user_id, text, reply)
        return

    # ── Step 1：收到項目名稱，詢問基金類型 ───────────────
    if draft.collection_step == 1:
        draft.project_name = text
        draft.collection_step = 2
        reply = _t(lang, "ask_fund_type", name=text)
        await update.message.reply_text(reply, parse_mode="Markdown")
        await save_exchange(session, user_id, text, reply)
        await save(session)
        return

    # ── Step 2：收到基金類型，詢問一句話介紹 ─────────────
    if draft.collection_step == 2:
        fund_type = draft.parse_fund_type(text)

        if fund_type == "unknown":
            # 沒有識別到有效的基金類型，重新詢問
            reply = _t(lang, "unknown_fund_type")
            await update.message.reply_text(reply, parse_mode="Markdown")
            await save_exchange(session, user_id, text, reply)
            return

        draft.fund_type = fund_type
        draft.collection_step = 3
        reply = _t(lang, "ask_one_liner", fund=fund_type)
        await update.message.reply_text(reply, parse_mode="Markdown")
        await save_exchange(session, user_id, text, reply)
        await save(session)
        return

    # ── Step 3：收到一句話介紹，預審 + 通知 ──────────────
    if draft.collection_step == 3:
        draft.one_liner = text

        # Values Engine 預審評分
        score, notes = pre_screen(draft)
        draft.agent_score = score
        draft.agent_notes = notes
        draft.submitted_at = datetime.utcnow().isoformat()

        # 通知管理員
        await notify_admin(context, draft, user, lang)

        # 回覆用戶確認
        reply = _t(lang, "submitted")
        await update.message.reply_text(reply, parse_mode="Markdown")
        await save_exchange(session, user_id, text, reply)

        # 重置 Session 回 general mode（申請流程結束）
        session.mode = "general"
        await save(session)

        logger.info(
            f"申請完成：user_id={user_id} project='{draft.project_name}' "
            f"fund={draft.fund_type} score={score}"
        )
