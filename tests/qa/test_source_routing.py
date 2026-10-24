"""Cross-source QA routing contracts, not individual keyword examples."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from gcc_agent.common.models import Session
from gcc_agent.qa.handler import handle_general
from gcc_agent.qa.prompts import check_link_first


class SourceRoutingTests(unittest.TestCase):
    def test_named_case_stays_named_case_when_generic_terms_are_added(self):
        questions = (
            ("ETH City 2025 的資助額度？", "zh-TW"),
            ("ETH City 2025 的治理核准額度？", "zh-TW"),
            ("高校 Web3 2025 的治理核准额度？", "zh-CN"),
            ("What was ETH City 2025's governance-approved allocation?", "en"),
            ("OSKey 2025 的治理核准額度？", "zh-TW"),
            ("OpenRPC Snapshot 已撥款嗎？", "zh-TW"),
        )
        for question, lang in questions:
            with self.subTest(question=question):
                result = check_link_first(question, lang)
                self.assertEqual("canonical_case", result.link_type)
                self.assertIn("snapshot.org", result.reply)
        self.assertIn(
            "30,000 USD",
            check_link_first("ETH City 2025 的治理核准額度？", "zh-TW").reply,
        )

    def test_named_case_replaces_previous_history_subject(self):
        previous = check_link_first("GCC 當時的治理方式是怎樣？", "zh-TW")
        context = [
            {"role": "user", "content": "GCC 當時的治理方式是怎樣？"},
            {"role": "assistant", "content": previous.reply},
        ]
        result = check_link_first("ETH City 2025 的資料來源？", "zh-TW", context)
        self.assertEqual("canonical_case", result.link_type)
        self.assertIn("snapshot.org", result.reply)
        self.assertIn("mp.weixin.qq.com", result.reply)

    def test_report_metric_and_general_questions_keep_their_own_sources(self):
        expected = (
            ("ETH City 2025 覆蓋多少地區？", "history_gcc-historical-programme-reach"),
            ("GCC 當時的治理方式是怎樣？", "history_gcc-historical-governance-process"),
            ("Snapshot 通過是否代表款項已解鎖？", "fact_decision_execution"),
            ("高校 Builder 2026 怎樣申請？", "university2026_overview"),
            ("Cohort 4 的申請截止日期？", "cohort4_deadline"),
        )
        for question, route in expected:
            with self.subTest(question=question):
                self.assertEqual(route, check_link_first(question, "zh-TW").link_type)

    def test_distinct_named_programmes_do_not_collapse_into_one_answer(self):
        result = check_link_first("高校 Web3 2025 和高校 Builder 2026 有何不同？", "zh-TW")
        self.assertEqual("route_clarification", result.link_type)
        self.assertNotIn("申请表", result.reply)

    def test_unreviewed_named_project_is_not_replaced_by_global_history(self):
        result = check_link_first("Vyper 2025 的治理核准額度？", "zh-TW")
        self.assertEqual("project", result.link_type)
        self.assertIn("project-vyper", result.reply)


class SourceRoutingHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_original_question_uses_case_in_private_and_group(self):
        for scope_type in ("private", "group"):
            with self.subTest(scope_type=scope_type):
                update = MagicMock()
                update.message.text = "ETH City 2025 的治理核准額度？"
                update.message.reply_text = AsyncMock()
                guard = SimpleNamespace(lang="zh-TW", user=SimpleNamespace(user_id=123))
                with (
                    patch("gcc_agent.qa.handler.get_session", new=AsyncMock(return_value=Session(user_id=123))),
                    patch("gcc_agent.qa.handler.save_exchange", new=AsyncMock()),
                    patch("gcc_agent.qa.handler.call_ai", new=AsyncMock()) as call_ai,
                ):
                    await handle_general(
                        update, MagicMock(), guard,
                        scope_type=scope_type,
                        scope_id=-100123 if scope_type == "group" else 123,
                    )
                answer = update.message.reply_text.await_args
                self.assertIn("30,000 USD", answer.args[0])
                self.assertIn("snapshot.org", answer.args[0])
                self.assertIsNone(answer.kwargs["parse_mode"])
                self.assertIsNone(answer.kwargs["reply_markup"])
                call_ai.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
