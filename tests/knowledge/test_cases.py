"""Project case database smoke tests."""

import json
import unittest
from pathlib import Path

from core.project_cases import (
    case_to_legacy_project,
    load_ai_review_cases,
    load_project_case_database,
    load_project_cases,
)


ROOT = Path(__file__).resolve().parents[2]


class ProjectCaseDatabaseTest(unittest.TestCase):
    def test_project_case_database(self):
        db = load_project_case_database(force_reload=True)
        cases = load_project_cases()
        ai_cases = load_ai_review_cases()
        categories = {case.get("category") for case in cases}

        self.assertEqual(db.get("schema_version"), "0.1.0")
        self.assertEqual(len(cases), 6)
        self.assertEqual(
            categories,
            {
                "Open Source",
                "Community",
                "Event",
                "ETH City Series",
                "Travel Scholarship",
                "Gitcoin",
            },
        )
        self.assertEqual(len(ai_cases), 5)
        self.assertTrue(
            any(
                case.get("case_id") == "gcc-gitcoin-placeholder"
                and case.get("ai_review_usage", {}).get("allowed") is False
                for case in cases
            ),
        )

        for case in cases:
            evidence = case.get("evidence", {})
            public_record = case.get("public_record", {})
            is_placeholder = case.get("case_id") == "gcc-gitcoin-placeholder"
            with self.subTest(case_id=case.get("case_id")):
                self.assertEqual(case.get("schema_version"), "0.1.0")
                self.assertTrue(evidence.get("snapshots") or is_placeholder)
                self.assertIn("grant_application", evidence)
                self.assertIn("voting_record", evidence)
                self.assertIn("funding", public_record)
                self.assertIn("public_goods_dimensions", public_record)
                self.assertIn("impact_evidence", public_record)
                self.assertIn("lifecycle_status", public_record)
                self.assertIn("raw_data_status", evidence)

    def test_legacy_conversion(self):
        cases = load_project_cases(force_reload=True)
        legacy = case_to_legacy_project(cases[0])
        self.assertEqual(legacy["name"], cases[0]["title"])
        self.assertTrue(legacy["summary"])

    def test_seed_case_known_values(self):
        cases = {
            case["case_id"]: case
            for case in load_project_cases(force_reload=True)
        }

        vyper = cases["gcc-open-source-vyper"]
        self.assertEqual(
            vyper["public_record"]["links"]["repository_url"],
            "https://github.com/vyperlang/vyper",
        )

        eth_city = cases["gcc-community-eth-city-university-web3-2025"]
        eth_city_details = eth_city["public_record"]["program_details"]
        self.assertEqual(
            eth_city_details["application_deadline"],
            "rolling until 2025-12-30 or until quota filled",
        )
        self.assertEqual(eth_city["public_record"]["lifecycle_status"]["delivery_status"], "in_progress")
        self.assertEqual(eth_city["public_record"]["links"]["announcement_url"], "https://mp.weixin.qq.com/s/p8oXiK90tbZbsjTC-g7GhQ")
        self.assertEqual(len(eth_city_details["funding_tracks"]), 2)
        self.assertEqual(
            [track["track_type"] for track in eth_city_details["funding_tracks"]],
            ["university_group", "city_event"],
        )
        self.assertEqual(
            [track["total_pool_usd"] for track in eth_city_details["funding_tracks"]],
            [30000, 30000],
        )
        self.assertEqual(
            [track["child_records_status"] for track in eth_city_details["funding_tracks"]],
            ["pending_import", "pending_import"],
        )
        self.assertEqual(len(eth_city["evidence"]["snapshots"]), 2)

        eth_beijing = cases["gcc-eth-city-eth-beijing-2025"]
        self.assertEqual(eth_beijing["public_record"]["amount_usd"], 3000)
        self.assertEqual(eth_beijing["public_record"]["activity_year"], 2025)
        self.assertEqual(
            eth_beijing["public_record"]["lifecycle_status"]["delivery_status"],
            "completed",
        )
        self.assertEqual(
            eth_beijing["public_record"]["lifecycle_status"]["grant_status"],
            "funded",
        )
        self.assertEqual(eth_beijing["public_record"]["funding"]["approved_amount_usd"], 3000)

        devconnect = cases["gcc-travel-scholarship-devconnect-2025"]
        self.assertEqual(devconnect["public_record"]["amount_usd"], 5000)
        self.assertEqual(devconnect["public_record"]["funding"]["approved_amount_usd"], 5000)
        self.assertEqual(
            devconnect["public_record"]["links"]["official_website"],
            "https://devconnect.org/",
        )
        self.assertEqual(
            devconnect["public_record"]["links"]["announcement_url"],
            "https://x.com/GCCofCommons/status/1978782504216559740",
        )
        self.assertEqual(
            devconnect["public_record"]["lifecycle_status"]["grant_status"],
            "funded",
        )
        self.assertEqual(
            devconnect["public_record"]["lifecycle_status"]["delivery_status"],
            "unknown",
        )
        self.assertEqual(len(devconnect["evidence"]["snapshots"]), 2)

    def test_schema_v0_1_contract_files_exist(self):
        case_schema_path = ROOT / "schema" / "project.schema.json"
        database_schema_path = ROOT / "schema" / "project-case-database.schema.json"
        case_schema = json.loads(case_schema_path.read_text(encoding="utf-8"))
        database_schema = json.loads(database_schema_path.read_text(encoding="utf-8"))

        self.assertEqual(case_schema["properties"]["schema_version"]["const"], "0.1.0")
        self.assertEqual(database_schema["properties"]["schema_version"]["const"], "0.1.0")
        self.assertIn("cases", database_schema["required"])
        self.assertEqual(database_schema["properties"]["cases"]["items"]["$ref"], "project.schema.json")
        self.assertIn("funding_tracks", case_schema["$defs"]["programDetails"]["properties"])
        self.assertIn("fundingTrack", case_schema["$defs"])
        for field in ("public_record", "evidence", "ai_review_usage"):
            self.assertIn(field, case_schema["required"])


if __name__ == "__main__":
    unittest.main()
