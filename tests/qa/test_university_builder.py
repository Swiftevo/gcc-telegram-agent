"""The 2026 university plan must not leak into other GCC funding tracks."""

from types import SimpleNamespace
from unittest import TestCase, IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from gcc_agent.common.models import Session
from gcc_agent.qa.handler import handle_general
from gcc_agent.qa.prompts import check_link_first
from gcc_agent.qa.university_builder import select_university_answer


class UniversityBuilderTests(TestCase):
    def test_application_uses_distinct_external_form(self):
        result = check_link_first("高校 Builder 计划 2026 怎么申请？", "zh-CN")
        self.assertEqual(result.link_type, "university2026_overview")
        self.assertIn("survey.gccofficial.org/552158?lang=zh-Hans", result.reply)
        self.assertIn("社团提交", result.reply)
        self.assertNotIn("/application/special", result.reply)

    def test_six_category_amounts_and_owner_override(self):
        result = check_link_first("高校 Builder 2026 六类资助上限是多少？", "zh-CN")
        self.assertEqual(result.link_type, "university2026_categories")
        for amount in ("500 USD／年", "1,000 USD／课程", "100 USD／场", "3,000 USD／项目", "150 USD／场"):
            self.assertIn(amount, result.reply)
        self.assertIn("表格目前写 200", result.reply)
        self.assertNotIn("200 USD／场；每社团", result.reply)

    def test_alumni_and_operations_discrepancies_are_transparent(self):
        alumni = check_link_first("高校校友联动专项一场多少？", "zh-CN")
        self.assertEqual(alumni.link_type, "university2026_alumni")
        self.assertIn("150 USD／场", alumni.reply)
        self.assertIn("200 USD／场", alumni.reply)
        ops = check_link_first("高校日常运营按学期还是年度申请？", "zh-CN")
        self.assertEqual(ops.link_type, "university2026_operations")
        self.assertIn("按年度申请", ops.reply)
        self.assertIn("附录写按学期", ops.reply)

    def test_university_weights_are_not_general_public_fund_weights(self):
        specific = check_link_first("高校 Builder 2026 评分权重？", "zh-CN")
        self.assertEqual(specific.link_type, "university2026_criteria")
        self.assertIn("产业相关性 30%", specific.reply)
        self.assertIn("不是 Cohort 4", specific.reply)
        general = check_link_first("Cohort 4 的评审标准和评分门槛？", "zh-CN")
        self.assertEqual(general.link_type, "cohort4_criteria")
        self.assertNotIn("产业相关性 30%", general.reply)

    def test_rhythm_and_payment_cannot_be_evidence_of_execution(self):
        schedule = check_link_first("高校 Builder 2026 截止日期？", "zh-CN")
        self.assertEqual(schedule.link_type, "university2026_schedule")
        self.assertIn("每季度首月 1–25 日", schedule.reply)
        self.assertIn("日常运营类按年度申请", schedule.reply)
        self.assertNotIn("日常运营、Workshop", schedule.reply)
        self.assertIn("不保证某一批次仍开放", schedule.reply)
        payment = check_link_first("高校 Builder 2026 已拨款了吗？", "zh-CN")
        self.assertEqual(payment.link_type, "university2026_payments")
        self.assertIn("不证明任何个别项目", payment.reply)

    def test_exclusions_deliverables_and_focus(self):
        excluded = check_link_first("高校 Builder 2026 不资助什么？", "zh-CN")
        self.assertEqual(excluded.link_type, "university2026_exclusions")
        self.assertIn("独立 ETH City", excluded.reply)
        deliverables = check_link_first("高校 Builder 2026 探索类交付要求？", "zh-CN")
        self.assertEqual(deliverables.link_type, "university2026_deliverables")
        self.assertIn("不以论文录用", deliverables.reply)
        focus = check_link_first("高校 Builder 2026 支持什么方向？", "zh-CN")
        self.assertEqual(focus.link_type, "university2026_focus")
        self.assertIn("非封闭清单", focus.reply)

    def test_history_and_eth_city_not_swallowed(self):
        self.assertFalse(select_university_answer("2025 高校 Web3 兴趣小组资助金额？").matched)
        self.assertFalse(select_university_answer("ETH City 计划怎么申请？").matched)
        self.assertFalse(select_university_answer("GCC 目前资助方向？").matched)
        self.assertEqual(check_link_first("GCC 目前资助方向？").link_type, "cohort4_focus")

    def test_english_fallback_and_approval_gate(self):
        result = check_link_first("GCC university Builder 2026 apply", "en")
        self.assertIn("Simplified Chinese", result.reply)
        with patch("gcc_agent.qa.university_builder._load_approved", return_value=None):
            self.assertFalse(select_university_answer("高校 Builder 2026 怎么申请？").matched)


class UniversityBuilderHandlerTests(IsolatedAsyncioTestCase):
    async def test_no_legacy_application_button_or_ai_for_specific_route(self):
        update = MagicMock()
        update.message.text = "高校 Builder 2026 怎么申请？"
        update.message.reply_text = AsyncMock()
        guard = SimpleNamespace(lang="zh-CN", user=SimpleNamespace(user_id=123))
        with (
            patch("gcc_agent.qa.handler.get_session", new=AsyncMock(return_value=Session(user_id=123))),
            patch("gcc_agent.qa.handler.save_exchange", new=AsyncMock()),
            patch("gcc_agent.qa.handler.call_ai", new=AsyncMock()) as call_ai,
        ):
            await handle_general(update, MagicMock(), guard)
        call_ai.assert_not_awaited()
        self.assertIsNone(update.message.reply_text.await_args.kwargs["reply_markup"])


if __name__ == "__main__":
    import unittest

    unittest.main()
