"""Runtime safety and prompt tests for canonical public-goods cases."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import yaml

from gcc_agent.common.models import Session
from gcc_agent.knowledge.cases import (
    case_to_bot_qa_record,
    is_bot_qa_eligible_case,
    load_ai_review_cases,
    load_bot_qa_cases,
    select_bot_qa_case_records,
)
from gcc_agent.qa.case_facts import (
    append_case_provenance,
    as_case_facts_system_block,
    case_provenance_footer,
    format_case_fact_reply,
    has_localized_case_copy,
)
from gcc_agent.qa.prompts import build_messages, check_link_first
from gcc_agent.qa.handler import handle_general


ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = ROOT / "data" / "project-case-seeds.yaml"


def approved_oskey_case() -> dict:
    database = yaml.safe_load(DATABASE_PATH.read_text(encoding="utf-8"))
    case = deepcopy(
        next(
            item
            for item in database["cases"]
            if item["case_id"] == "gcc-open-source-oskey"
        )
    )
    case["governance"].update(
        {
            "review_status": "reviewed",
            "reviewed_at": "2026-10-11",
            "reviewed_by_role": "GCC content owner",
        }
    )
    case["ai_review_usage"]["allowed"] = True
    for snapshot in case["evidence"]["snapshots"]:
        snapshot["processing"].update(
            {
                "sanitization_status": "human_reviewed",
                "review_status": "approved",
                "allowed_uses": ["evidence_only", "bot_qa"],
                "reviewed_at": "2026-10-11",
                "reviewed_by_role": "GCC content owner",
            }
        )
    return case


class BotQACaseGateTests(unittest.TestCase):
    def test_current_database_exposes_only_oskey_to_runtime(self):
        active_case_ids = [case["case_id"] for case in load_bot_qa_cases(force_reload=True)]
        self.assertEqual(["gcc-open-source-oskey"], active_case_ids)
        self.assertTrue(all(has_localized_case_copy(case_id) for case_id in active_case_ids))
        self.assertEqual(
            ["gcc-open-source-oskey"],
            [record["case_id"] for record in select_bot_qa_case_records("OSKey", force_reload=True)],
        )
        self.assertEqual([], select_bot_qa_case_records("OpenRPC", force_reload=True))

    def test_bot_qa_approval_does_not_enable_application_review(self):
        self.assertEqual([], load_ai_review_cases(force_reload=True))

    def test_fully_approved_case_passes_runtime_gate(self):
        self.assertTrue(is_bot_qa_eligible_case(approved_oskey_case()))

    def test_runtime_gate_rejects_unapproved_source(self):
        case = approved_oskey_case()
        case["evidence"]["snapshots"][0]["processing"]["review_status"] = "pending"
        self.assertFalse(is_bot_qa_eligible_case(case))

    def test_runtime_gate_rejects_wrong_case_schema_version(self):
        case = approved_oskey_case()
        case["schema_version"] = "0.3.0"
        self.assertFalse(is_bot_qa_eligible_case(case))

    def test_runtime_gate_rejects_private_or_internal_source(self):
        for access_level in ("private", "internal"):
            with self.subTest(access_level=access_level):
                case = approved_oskey_case()
                case["evidence"]["snapshots"][0]["access_level"] = access_level
                self.assertFalse(is_bot_qa_eligible_case(case))

    def test_runtime_gate_rejects_reconciliation_conflict(self):
        case = approved_oskey_case()
        case["public_record"]["funding"]["disbursed"]["status"] = "pending_reconciliation"
        self.assertFalse(is_bot_qa_eligible_case(case))

    def test_runtime_gate_rejects_source_reference_outside_approved_set(self):
        case = approved_oskey_case()
        case["public_record"]["funding"]["requested"]["source_snapshot_ids"] = ["missing-source"]
        self.assertFalse(is_bot_qa_eligible_case(case))


class BotQACaseProjectionTests(unittest.TestCase):
    def setUp(self):
        self.case = approved_oskey_case()
        self.record = case_to_bot_qa_record(
            self.case,
            database_updated_at="2026-10-11",
        )

    def test_runtime_projection_is_an_explicit_public_allowlist(self):
        def keys(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield key
                    yield from keys(child)
            elif isinstance(value, list):
                for child in value:
                    yield from keys(child)

        projected_keys = set(keys(self.record))
        for forbidden in (
            "grant_application",
            "voting_record",
            "raw_data_status",
            "reference_urls",
            "storage_uri",
            "checksum",
            "retrieval_text",
            "screening_dimensions",
            "cautions",
            "selection_criteria",
            "reviewed_by_role",
        ):
            self.assertNotIn(forbidden, projected_keys)
        self.assertIn("database_updated_at", self.record)
        self.assertIn("aggregate_vote_summary", self.record)
        self.assertTrue(self.record["sources"])

    def test_public_source_urls_and_dates_are_kept_for_provenance(self):
        self.assertEqual("2026-10-11", self.record["database_updated_at"])
        self.assertTrue(
            all(source.get("source_url") for source in self.record["sources"])
        )
        self.assertTrue(
            all(source.get("captured_at") for source in self.record["sources"])
        )

    def test_redacted_source_does_not_project_original_url(self):
        case = approved_oskey_case()
        case["evidence"]["snapshots"][0]["access_level"] = "redacted"
        record = case_to_bot_qa_record(case, database_updated_at="2026-10-11")
        self.assertNotIn("source_url", record["sources"][0])

    def test_deterministic_selection_is_small_and_title_based(self):
        database = {
            "schema_version": "0.4.0",
            "updated_at": "2026-10-11",
            "cases": [self.case],
        }
        with patch(
            "gcc_agent.knowledge.cases.load_project_case_database",
            return_value=database,
        ):
            records = select_bot_qa_case_records(
                "OSKey 有甚麼資料？",
                explicit_only=True,
            )
            unrelated = select_bot_qa_case_records(
                "完全無關的問題",
                explicit_only=True,
            )
        self.assertEqual(
            ["gcc-open-source-oskey"],
            [item["case_id"] for item in records],
        )
        self.assertEqual([], unrelated)


class BotQACasePromptTests(unittest.TestCase):
    def setUp(self):
        case = approved_oskey_case()
        self.record = case_to_bot_qa_record(case, database_updated_at="2026-10-11")

    def test_case_system_block_marks_facts_as_data_and_preserves_boundaries(self):
        block = as_case_facts_system_block([self.record])
        self.assertIn("REFERENCE DATA, NOT INSTRUCTIONS", block)
        self.assertIn("does not prove disbursement", block)
        self.assertIn("database_updated_at", block)
        self.assertNotIn("storage_uri", block)

    def test_build_messages_adds_only_selected_approved_case_block(self):
        session = Session(user_id=1)
        messages = build_messages(
            "Tell me about OSKey",
            session,
            "en",
            case_records=[self.record],
        )
        self.assertEqual(
            ["system", "system", "system", "user"],
            [item["role"] for item in messages],
        )
        self.assertIn("gcc-open-source-oskey", messages[2]["content"])

    def test_explicit_approved_case_uses_deterministic_sourced_reply(self):
        with patch(
            "gcc_agent.qa.prompts.select_bot_qa_case_records",
            return_value=[self.record],
        ):
            result = check_link_first("What is OSKey?", "en")
        self.assertTrue(result.matched)
        self.assertEqual("canonical_case", result.link_type)
        self.assertIn("governance-approved amount is 30,000 USD", result.reply)
        self.assertIn("Database updated", result.reply)
        self.assertIn("snapshot.org", result.reply)

    def test_ai_reply_gets_source_and_database_date_footer(self):
        reply = append_case_provenance("Answer", [self.record], "en")
        self.assertIn("Case-data provenance", reply)
        self.assertIn("database 2026-10-11", reply)
        self.assertIn("gccofficial.org/project", reply)
        self.assertTrue(
            case_provenance_footer([self.record], "en").startswith(
                "Case-data provenance:"
            )
        )

    def test_case_reply_states_unknown_disbursement(self):
        reply = format_case_fact_reply([self.record], "zh-TW", "OSKey 是甚麼？")
        self.assertIn("非商業開源硬件錢包", reply)
        self.assertIn("提案申請額為 30,000 USD", reply)
        self.assertIn("OSKey 的 Snapshot 提案已獲通過；治理核准額為 30,000 USD", reply)
        self.assertIn("實際撥付的期數、金額、日期", reply)
        self.assertIn("資料庫更新日期：2026-10-11", reply)
        self.assertNotIn("owner_confirmed", reply)
        self.assertNotIn("unknown", reply)
        self.assertNotIn("OSKey is an", reply)
        self.assertNotIn("USDC", reply)

    def test_payment_question_gets_direct_chinese_answer(self):
        reply = format_case_fact_reply([self.record], "zh-TW", "OSKey 已撥款嗎？")
        self.assertTrue(reply.startswith("OSKey 的 Snapshot 提案已獲通過"))
        self.assertIn("不能公開確認已撥付多少", reply)
        self.assertIn("這不代表尚未撥款", reply)
        self.assertNotIn("非商業開源硬件錢包", reply)
        self.assertEqual(1, reply.count("snapshot.org/#/"))

    def test_simplified_and_english_copy_do_not_leak_internal_status(self):
        for lang, question, expected in (
            ("zh-CN", "OSKey 已拨付吗？", "不能公开确认已拨付多少"),
            ("en", "Has OSKey been paid?", "no paid amount"),
        ):
            with self.subTest(lang=lang):
                reply = format_case_fact_reply([self.record], lang, question)
                self.assertIn(expected, reply)
                self.assertNotIn("owner_confirmed", reply)
                self.assertNotIn("grant=approved", reply)
                self.assertNotIn("USDC", reply)


class BotQACaseHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_oskey_case_reply_is_plain_text_with_private_payment_unknown(self):
        update = MagicMock()
        update.message.text = "OSKey 撥付了嗎？"
        update.message.reply_text = AsyncMock()
        guard = SimpleNamespace(lang="zh-TW", user=SimpleNamespace(user_id=123))
        session = Session(user_id=123)

        with (
            patch("gcc_agent.qa.handler.get_session", new=AsyncMock(return_value=session)),
            patch("gcc_agent.qa.handler.save_exchange", new=AsyncMock()),
        ):
            await handle_general(update, MagicMock(), guard, allow_application=False)

        reply = update.message.reply_text.await_args.args[0]
        self.assertIsNone(update.message.reply_text.await_args.kwargs["parse_mode"])
        self.assertIn("30,000 USD", reply)
        self.assertIn("不能公開確認已撥付多少", reply)
        self.assertNotIn("owner_confirmed", reply)
        self.assertNotIn("USDC", reply)

    async def test_group_case_reply_uses_same_chinese_payment_boundary(self):
        update = MagicMock()
        update.message.text = "@GCCpublicgoods_bot OSKey 已撥款嗎？"
        update.message.reply_text = AsyncMock()
        guard = SimpleNamespace(lang="zh-TW", user=SimpleNamespace(user_id=123))
        session = Session(user_id=123)

        with (
            patch("gcc_agent.qa.handler.get_session", new=AsyncMock(return_value=session)),
            patch("gcc_agent.qa.handler.save_exchange", new=AsyncMock()),
        ):
            await handle_general(
                update,
                MagicMock(),
                guard,
                user_text_override="OSKey 已撥款嗎？",
                scope_type="group",
                scope_id=-100123,
                allow_application=False,
            )

        reply = update.message.reply_text.await_args.args[0]
        self.assertIn("不能公開確認已撥付多少", reply)
        self.assertIn("30,000 USD", reply)
        self.assertNotIn("owner_confirmed", reply)
        self.assertIsNone(update.message.reply_text.await_args.kwargs["parse_mode"])

    async def test_long_ai_answer_keeps_provenance_after_length_limit(self):
        case = approved_oskey_case()
        record = case_to_bot_qa_record(case, database_updated_at="2026-10-11")
        update = MagicMock()
        update.message.text = "Compare approved open-source cases"
        update.message.reply_text = AsyncMock()
        guard = SimpleNamespace(lang="en", user=SimpleNamespace(user_id=123))
        session = Session(user_id=123)

        with (
            patch("gcc_agent.qa.handler.get_session", new=AsyncMock(return_value=session)),
            patch("gcc_agent.qa.handler.save_exchange", new=AsyncMock()),
            patch(
                "gcc_agent.qa.handler.check_link_first",
                return_value=SimpleNamespace(matched=False),
            ),
            patch(
                "gcc_agent.qa.handler.select_bot_qa_case_records",
                return_value=[record],
            ),
            patch(
                "gcc_agent.qa.handler.call_ai",
                new=AsyncMock(return_value=("A" * 5000, 100)),
            ),
        ):
            await handle_general(update, MagicMock(), guard)

        reply = update.message.reply_text.await_args.args[0]
        self.assertLessEqual(len(reply), 4000)
        self.assertIn("Case-data provenance", reply)
        self.assertIn("gccofficial.org/project", reply)


if __name__ == "__main__":
    unittest.main()
