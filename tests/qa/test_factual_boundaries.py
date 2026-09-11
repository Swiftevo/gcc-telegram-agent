"""Regression tests for source-backed GCC funding-policy answers."""

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gcc_agent.common.models import Session
from gcc_agent.knowledge.loaders import as_system_block
from gcc_agent.knowledge.models import AgentValues
from gcc_agent.qa.facts import ABOUT_URL, PUBLIC_FUND_URL, SPECIAL_FUND_URL
from gcc_agent.qa.handler import handle_general
from gcc_agent.qa.prompts import check_link_first


class FundingFactRoutingTests(unittest.TestCase):
    def test_funding_and_review_process_are_source_backed_in_all_languages(self):
        cases = (
            ("GCC 的資助流程", "zh-TW", "盡職調查", "三分之二"),
            ("gcc 的评审流程", "zh-CN", "尽职调查", "三分之二"),
            ("What is GCC's grant review process?", "en", "Due diligence", "two thirds"),
        )
        for question, lang, due_diligence, decision_rule in cases:
            with self.subTest(lang=lang):
                result = check_link_first(question, lang)
                self.assertTrue(result.matched)
                self.assertEqual("fact_process", result.link_type)
                self.assertIn(due_diligence, result.reply)
                self.assertIn(decision_rule, result.reply)
                self.assertIn(ABOUT_URL, result.reply)
                self.assertIn(PUBLIC_FUND_URL, result.reply)
                self.assertIn(SPECIAL_FUND_URL, result.reply)
                self.assertNotIn("40/30/20/10", result.reply)
                self.assertNotIn("70/40", result.reply)

    def test_published_criteria_are_not_presented_as_a_score(self):
        result = check_link_first("GCC 的評審標準和評分制是甚麼？", "zh-TW")
        self.assertEqual("fact_score", result.link_type)
        self.assertIn("沒有公布", result.reply)
        self.assertIn("不是 GCC", result.reply)
        self.assertIn(PUBLIC_FUND_URL, result.reply)

    def test_natural_review_wording_still_uses_deterministic_process(self):
        cases = (
            ("GCC 怎樣審核申請？", "zh-TW"),
            ("GCC 怎么评审申请？", "zh-CN"),
            ("How are applications reviewed by GCC?", "en"),
        )
        for question, lang in cases:
            with self.subTest(lang=lang):
                result = check_link_first(question, lang)
                self.assertEqual("fact_process", result.link_type)
                self.assertIn(ABOUT_URL, result.reply)

    def test_generic_score_question_needs_gcc_policy_context(self):
        self.assertFalse(check_link_first("你會怎樣評分這段文章？", "zh-TW").matched)
        self.assertFalse(check_link_first("考試 70 分算合格嗎？", "zh-TW").matched)
        self.assertEqual(
            "fact_score",
            check_link_first("GCC 的評分是怎樣？", "zh-TW").link_type,
        )

    def test_public_timeline_does_not_invent_stage_durations(self):
        result = check_link_first("GCC 每個評審階段要多久？", "zh-TW")
        self.assertEqual("fact_timeline", result.link_type)
        self.assertIn("8–12 週", result.reply)
        self.assertIn("沒有公布", result.reply)
        self.assertFalse(
            check_link_first("application 文案需要多長？", "zh-TW").matched
        )

    def test_standalone_source_follow_up_uses_recent_policy_context(self):
        process = check_link_first("GCC 的資助流程", "zh-TW")
        history = [
            {"role": "user", "content": "GCC 的資助流程"},
            {"role": "assistant", "content": process.reply},
        ]
        result = check_link_first("來源？", "zh-TW", history)
        self.assertEqual("fact_sources", result.link_type)
        self.assertIn(ABOUT_URL, result.reply)
        self.assertIn(PUBLIC_FUND_URL, result.reply)

    def test_direct_review_process_source_question_returns_sources(self):
        result = check_link_first("gcc 评审流程来源？", "zh-CN")
        self.assertEqual("fact_sources", result.link_type)
        self.assertIn(ABOUT_URL, result.reply)
        self.assertIn("没有公布", result.reply)

    def test_unrelated_source_question_is_not_forced_to_gcc_policy_sources(self):
        result = check_link_first("這句話的來源？", "zh-TW")
        self.assertFalse(result.matched)

        unrelated_history = [
            {"role": "user", "content": "請替我修改一份 application 文案"},
            {"role": "assistant", "content": "可以，請貼上內容。"},
        ]
        result = check_link_first("來源？", "zh-TW", unrelated_history)
        self.assertFalse(result.matched)

    def test_snapshot_decision_is_separated_from_execution(self):
        result = check_link_first("Snapshot 通過是否代表款項已解鎖？", "zh-TW")
        self.assertEqual("fact_decision_execution", result.link_type)
        self.assertIn("不能單獨證明", result.reply)
        self.assertIn("交易、會計、付款", result.reply)


class QAFactPromptTests(unittest.TestCase):
    def test_general_qa_prompt_excludes_internal_rubric_and_thresholds(self):
        values = AgentValues(
            version="test",
            mission_statement="測試使命",
            priority_themes=["開源"],
            rejection_criteria=["欺詐"],
            screening_rubric={
                "mission_fit": 40,
                "public_goods_nature": 30,
                "chinese_community": 20,
                "feasibility": 10,
            },
            qa_fact_policy="沒有公開來源時必須明確回答未知，不得推斷。",
            tone_guidelines="保持簡潔。",
        )
        prompt = as_system_block(values)
        self.assertIn("不是投票委員會", prompt)
        self.assertIn("回答未知", prompt)
        self.assertNotIn("使命契合度 40", prompt)
        self.assertNotIn(">= 70", prompt)
        self.assertNotIn("40-69", prompt)


class FundingFactHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_question_never_calls_the_language_model(self):
        update = MagicMock()
        update.message.text = "gcc 的评审流程"
        update.message.reply_text = AsyncMock()
        guard = SimpleNamespace(
            lang="zh-CN",
            user=SimpleNamespace(user_id=123),
        )
        session = Session(user_id=123)

        with (
            patch("gcc_agent.qa.handler.get_session", new=AsyncMock(return_value=session)),
            patch("gcc_agent.qa.handler.save_exchange", new=AsyncMock()) as save_exchange,
            patch("gcc_agent.qa.handler.call_ai", new=AsyncMock()) as call_ai,
        ):
            await handle_general(update, MagicMock(), guard)

        call_ai.assert_not_awaited()
        update.message.reply_text.assert_awaited_once()
        reply = update.message.reply_text.await_args.args[0]
        self.assertIn("尽职调查", reply)
        self.assertIn(ABOUT_URL, reply)
        self.assertTrue(save_exchange.await_args.kwargs["link_served"])


if __name__ == "__main__":
    unittest.main()
