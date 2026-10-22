"""Round-specific announcement facts must stay current, sourced and bounded."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import TestCase, IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from gcc_agent.qa.cohort4 import select_cohort4_answer
from gcc_agent.qa.prompts import check_link_first, build_messages
from gcc_agent.common.models import Session
from gcc_agent.qa.handler import handle_general


HKT = timezone(timedelta(hours=8))


class Cohort4Tests(TestCase):
    def test_approved_focus_precedes_legacy_website_copy(self):
        result = check_link_first("GCC Cohort 4 支持什么方向？", "zh-CN")
        self.assertEqual(result.link_type, "cohort4_focus")
        self.assertIn("Open Source", result.reply)
        self.assertIn("Privacy", result.reply)
        self.assertIn("Security", result.reply)
        self.assertIn("2103414364414079142", result.reply)
        self.assertNotIn("抗审查、全球公共人才", result.reply)

    def test_current_focus_but_not_historical_focus(self):
        self.assertEqual(check_link_first("GCC 目前的资助方向？").link_type, "cohort4_focus")
        self.assertNotEqual(check_link_first("GCC 2023 年的资助方向？").link_type, "cohort4_focus")

    def test_generic_current_round_criteria_and_deadline_use_announcement(self):
        self.assertEqual(check_link_first("GCC 的评审标准？").link_type, "cohort4_criteria")
        self.assertEqual(check_link_first("GCC 的申请截止日期？").link_type, "cohort4_deadline")

    def test_criteria_no_fake_precision(self):
        result = check_link_first("Cohort 4 的评审标准和评分门槛？", "zh-CN")
        self.assertEqual(result.link_type, "cohort4_criteria")
        self.assertIn("可持续性", result.reply)
        self.assertIn("没有公布百分制权重", result.reply)
        self.assertNotIn("40/30/20/10", result.reply)

    def test_announcement_schedule_is_not_execution_evidence(self):
        result = check_link_first("Cohort 4 M0 何時撥款？")
        self.assertEqual(result.link_type, "cohort4_schedule")
        self.assertIn("2026-12-10", result.reply)
        self.assertIn("计划", result.reply)
        self.assertIn("不代表", result.reply)

    def test_deadline_expiry_does_not_continue_claiming_open(self):
        before = select_cohort4_answer(
            "Cohort 4 申请截止？", "zh-CN", now=datetime(2026, 10, 22, tzinfo=HKT)
        )
        after = select_cohort4_answer(
            "Cohort 4 申请截止？", "zh-CN", now=datetime(2026, 11, 1, tzinfo=HKT)
        )
        self.assertIn("仍在申请期", before.reply)
        self.assertIn("已过", after.reply)
        self.assertNotIn("仍在申请期", after.reply)
        self.assertIn("2026-10-31 23:59", after.reply)

    def test_referral_is_conditional(self):
        result = check_link_first("Cohort 4 推荐奖励是多少？", "zh-CN")
        self.assertEqual(result.link_type, "cohort4_referral")
        self.assertIn("成功入围 Demo Day", result.reply)
        self.assertIn("100 USD", result.reply)

    def test_general_application_and_special_fund_are_distinct(self):
        result = check_link_first("Cohort 4 如何申请？", "zh-CN")
        self.assertEqual(result.link_type, "cohort4_application")
        self.assertIn("/application/public", result.reply)
        self.assertIn("/application/special", result.reply)
        self.assertNotIn("tally.so/r/nPKbb5", result.reply)

    def test_other_round_and_non_policy_questions_not_captured(self):
        self.assertFalse(select_cohort4_answer("Cohort 3 的申请时间？").matched)
        self.assertFalse(select_cohort4_answer("什么是形式化验证？").matched)

    def test_locale_fallback_explicit_and_no_unverified_total(self):
        result = check_link_first("Cohort 4 的申请截止？", "en")
        self.assertIn("Simplified Chinese", result.reply)
        self.assertIn("community calls", result.reply)
        self.assertNotIn("160 万", result.reply)

    def test_review_gate_fails_closed(self):
        with patch("gcc_agent.qa.cohort4._load_approved", return_value=None):
            self.assertFalse(select_cohort4_answer("Cohort 4 方向？").matched)

    def test_prompt_priority_themes_are_aligned(self):
        messages = build_messages("GCC 支持什么方向？", Session(user_id=1), "zh-CN")
        self.assertIn("Cohort 4", messages[0]["content"])
        self.assertIn("OPS", messages[0]["content"])
        self.assertNotIn("全球公共人才網絡", messages[0]["content"])


class Cohort4HandlerTests(IsolatedAsyncioTestCase):
    async def test_round_answer_does_not_show_legacy_internal_apply_button(self):
        update = MagicMock()
        update.message.text = "Cohort 4 如何申请？"
        update.message.reply_text = AsyncMock()
        guard = SimpleNamespace(lang="zh-CN", user=SimpleNamespace(user_id=123))
        with (
            patch("gcc_agent.qa.handler.get_session", new=AsyncMock(return_value=Session(user_id=123))),
            patch("gcc_agent.qa.handler.save_exchange", new=AsyncMock()),
            patch("gcc_agent.qa.handler.call_ai", new=AsyncMock()) as call_ai,
        ):
            await handle_general(update, MagicMock(), guard)
        call_ai.assert_not_awaited()
        self.assertIn("/application/public", update.message.reply_text.await_args.args[0])
        self.assertIsNone(update.message.reply_text.await_args.kwargs["reply_markup"])


if __name__ == "__main__":
    import unittest

    unittest.main()
