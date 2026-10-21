"""Runtime gates and deterministic routing for approved GCC history projections."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import yaml

from gcc_agent.common.models import Session
from gcc_agent.knowledge.history import (
    load_bot_history_projections,
    select_history_projection,
)
from gcc_agent.qa.handler import handle_general
from gcc_agent.qa.history_facts import format_history_projection_reply
from gcc_agent.qa.prompts import build_messages, check_link_first


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "data" / "gcc-public-history.yaml"
REPORT_URL = "https://drive.google.com/file/d/15HztLjCcUtatmknZuUZbjb1ifEojzKfR/view"
RUNTIME_FIELDS = {
    "projection_id",
    "topic",
    "language",
    "scope",
    "question_examples",
    "answer_text",
    "citation",
}


class HistoryRuntimeGateTests(unittest.TestCase):
    def setUp(self):
        self.registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))

    def load_with_registry(self, registry):
        with patch(
            "gcc_agent.knowledge.history.load_history_registry",
            return_value=registry,
        ):
            return load_bot_history_projections(force_reload=True)

    def test_registry_exposes_exactly_seven_minimal_runtime_records(self):
        records = load_bot_history_projections(force_reload=True)
        self.assertEqual(7, len(records))
        self.assertTrue(all(set(record) == RUNTIME_FIELDS for record in records))
        serialized = repr(records)
        self.assertNotIn("storage_uri", serialized)
        self.assertNotIn("excluded_claims", serialized)
        self.assertNotIn("source_references", serialized)
        self.assertIn("50.4", serialized)
        self.assertIn("沒有交代分母", serialized)

    def test_runtime_fails_closed_when_disconnected_or_schema_is_wrong(self):
        disconnected = deepcopy(self.registry)
        disconnected["runtime"]["connected"] = False
        self.assertEqual([], self.load_with_registry(disconnected))

        wrong_schema = deepcopy(self.registry)
        wrong_schema["schema_version"] = "0.2.0"
        self.assertEqual([], self.load_with_registry(wrong_schema))

    def test_runtime_fails_closed_for_unapproved_source_or_projection(self):
        unapproved_source = deepcopy(self.registry)
        unapproved_source["sources"][0]["processing"]["review_status"] = "pending"
        self.assertEqual([], self.load_with_registry(unapproved_source))

        unapproved_projection = deepcopy(self.registry)
        unapproved_projection["approved_projections"][0]["review"]["status"] = "pending"
        records = self.load_with_registry(unapproved_projection)
        self.assertEqual(6, len(records))
        self.assertNotIn(
            "gcc-history-2022-2025",
            {record["projection_id"] for record in records},
        )

    def test_runtime_rejects_unbounded_rate_and_excluded_section(self):
        unsafe_answer = deepcopy(self.registry)
        unsafe_answer["approved_projections"][0]["answer_text"] += " 50.4%"
        self.assertEqual(6, len(self.load_with_registry(unsafe_answer)))

        excluded = deepcopy(self.registry)
        excluded["approved_projections"][0]["source_references"][0]["section_ids"] = [
            "testimonials"
        ]
        self.assertEqual(6, len(self.load_with_registry(excluded)))

    def test_runtime_rejects_citation_mismatch(self):
        registry = deepcopy(self.registry)
        registry["approved_projections"][0]["citation"]["url"] = "https://example.com"
        self.assertEqual(6, len(self.load_with_registry(registry)))


class HistorySelectionTests(unittest.TestCase):
    def test_each_approved_topic_has_a_deterministic_match(self):
        cases = (
            ("GCC 的發展歷史是怎樣？", "gcc-history-2022-2025"),
            ("GCC 過往支持哪些公共物品方向？", "gcc-historical-funding-directions"),
            ("GCC 報告列出過哪些項目？", "gcc-historical-project-catalogue"),
            ("Builder flight 過往支持了多少人？", "gcc-builder-flight-history"),
            ("GCC 當時的治理方式是怎樣？", "gcc-historical-governance-process"),
            ("報告中的兩年捐贈數據是多少？", "gcc-historical-aggregate-data"),
            ("GCC 歷史總捐贈了多少？", "gcc-historical-aggregate-data"),
            ("What was the historical regional distribution?", "gcc-historical-aggregate-data"),
            ("ETH City 過往覆蓋多少地區？", "gcc-historical-programme-reach"),
        )
        for query, expected in cases:
            with self.subTest(query=query):
                projection = select_history_projection(query)
                self.assertIsNotNone(projection)
                self.assertEqual(expected, projection["projection_id"])

    def test_current_policy_and_application_questions_do_not_use_history(self):
        for query in (
            "GCC 的資助流程",
            "GCC 目前支持哪些方向？",
            "機票計劃怎麼申請？",
            "Builder flight 現在可以申請嗎？",
        ):
            with self.subTest(query=query):
                self.assertIsNone(select_history_projection(query))

        current = check_link_first("GCC 的資助流程", "zh-TW")
        self.assertEqual("fact_process", current.link_type)
        historical = check_link_first("報告中的歷史資助流程是甚麼？", "zh-TW")
        self.assertEqual(
            "history_gcc-historical-governance-process",
            historical.link_type,
        )

    def test_builder_answer_uses_132_and_report_stated_50_4_with_boundary(self):
        result = check_link_first("GCC Builder 機票計劃是甚麼？", "zh-TW")
        self.assertEqual("history_gcc-builder-flight-history", result.link_type)
        self.assertIn("132 人次", result.reply)
        self.assertIn("50.4%", result.reply)
        self.assertIn("沒有交代分母", result.reply)
        self.assertIn(REPORT_URL, result.reply)

    def test_aggregate_answer_includes_regional_figures_and_evidence_boundary(self):
        result = check_link_first("GCC 歷史總捐贈了多少？", "zh-TW")
        self.assertEqual("history_gcc-historical-aggregate-data", result.link_type)
        self.assertIn("北美 7.1 萬美元", result.reply)
        self.assertIn("中國 53.3 萬美元", result.reply)
        self.assertIn("不是交易級付款", result.reply)
        self.assertIn(REPORT_URL, result.reply)

    def test_source_follow_up_reuses_the_recent_history_projection(self):
        first = check_link_first("GCC 的發展歷史是怎樣？", "zh-TW")
        context = [
            {"role": "user", "content": "GCC 的發展歷史是怎樣？"},
            {"role": "assistant", "content": first.reply},
        ]
        follow_up = check_link_first("來源？", "zh-TW", context)
        self.assertEqual("history_gcc-history-2022-2025", follow_up.link_type)
        self.assertIn(REPORT_URL, follow_up.reply)

    def test_untranslated_locales_have_explicit_safe_fallbacks(self):
        projection = select_history_projection("Builder flight 支持了多少人？")
        simplified = format_history_projection_reply(projection, "zh-CN")
        english = format_history_projection_reply(projection, "en")
        self.assertIn("繁体中文", simplified)
        self.assertIn("Traditional Chinese", english)
        self.assertIn("132 人次", simplified)
        self.assertIn("132 人次", english)

    def test_history_is_not_injected_into_the_ai_prompt(self):
        messages = build_messages(
            "請解釋公共物品",
            Session(user_id=123),
            "zh-TW",
            case_records=[],
        )
        serialized = repr(messages)
        self.assertNotIn(REPORT_URL, serialized)
        self.assertNotIn("132 人次", serialized)


class HistoryPrivateAndGroupHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def _run(self, *, scope_type: str, scope_id: int):
        update = MagicMock()
        update.message.text = "Builder flight 過往支持了多少人？"
        update.message.reply_text = AsyncMock()
        guard = SimpleNamespace(
            lang="zh-TW",
            user=SimpleNamespace(user_id=123),
        )
        session = Session(user_id=123, scope_type=scope_type, scope_id=scope_id)
        with (
            patch(
                "gcc_agent.qa.handler.get_session",
                new=AsyncMock(return_value=session),
            ),
            patch("gcc_agent.qa.handler.save_exchange", new=AsyncMock()) as save_exchange,
            patch("gcc_agent.qa.handler.call_ai", new=AsyncMock()) as call_ai,
        ):
            await handle_general(
                update,
                MagicMock(),
                guard,
                scope_type=scope_type,
                scope_id=scope_id,
                allow_application=False,
            )
        call_ai.assert_not_awaited()
        reply = update.message.reply_text.await_args.args[0]
        self.assertIn("132 人次", reply)
        self.assertIn(REPORT_URL, reply)
        self.assertIn("50.4%", reply)
        self.assertIn("沒有交代分母", reply)
        self.assertTrue(save_exchange.await_args.kwargs["link_served"])

    async def test_private_history_question_uses_fixed_projection(self):
        await self._run(scope_type="private", scope_id=0)

    async def test_group_history_question_uses_same_fixed_projection(self):
        await self._run(scope_type="group", scope_id=-100123)


if __name__ == "__main__":
    unittest.main()
