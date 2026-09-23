"""Validation tests for the project case database schema and references."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

import yaml

from gcc_agent.knowledge.validate_cases import validate_case_database, validate_paths


ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = ROOT / "data" / "project-case-seeds.yaml"
DATABASE_SCHEMA_PATH = ROOT / "schema" / "project-case-database.schema.json"
CASE_SCHEMA_PATH = ROOT / "schema" / "project.schema.json"


def load_inputs():
    return (
        yaml.safe_load(DATABASE_PATH.read_text(encoding="utf-8")),
        json.loads(DATABASE_SCHEMA_PATH.read_text(encoding="utf-8")),
        json.loads(CASE_SCHEMA_PATH.read_text(encoding="utf-8")),
    )


class ProjectCaseValidationTests(unittest.TestCase):
    def setUp(self):
        self.database, self.database_schema, self.case_schema = load_inputs()

    def validate(self, database):
        return validate_case_database(
            database,
            database_schema=self.database_schema,
            case_schema=self.case_schema,
        )

    @staticmethod
    def case(database, case_id):
        return next(case for case in database["cases"] if case["case_id"] == case_id)

    def test_seed_database_passes_schema_and_cross_record_validation(self):
        self.assertEqual([], validate_paths())

    def test_duplicate_case_id_is_rejected(self):
        database = deepcopy(self.database)
        database["cases"][1]["case_id"] = database["cases"][0]["case_id"]
        self.assertIn("duplicate_case_id", {issue.code for issue in self.validate(database)})

    def test_unknown_funding_track_is_rejected(self):
        database = deepcopy(self.database)
        database["cases"][0]["funding_track_id"] = "missing-track"
        self.assertIn("unknown_funding_track", {issue.code for issue in self.validate(database)})

    def test_duplicate_funding_track_is_rejected(self):
        database = deepcopy(self.database)
        programme = self.case(database, "gcc-community-eth-city-university-web3-2025")
        tracks = programme["public_record"]["program_details"]["funding_tracks"]
        tracks[1]["track_id"] = tracks[0]["track_id"]
        self.assertIn("duplicate_track_id", {issue.code for issue in self.validate(database)})

    def test_only_grant_case_can_link_to_funding_track(self):
        database = deepcopy(self.database)
        programme = self.case(database, "gcc-community-eth-city-university-web3-2025")
        programme["funding_track_id"] = "gcc-eth-city-2025"
        self.assertIn("invalid_funding_track_owner", {issue.code for issue in self.validate(database)})

    def test_unknown_snapshot_reference_is_rejected(self):
        database = deepcopy(self.database)
        database["cases"][0]["public_record"]["funding"]["requested"][
            "source_snapshot_ids"
        ] = ["missing-snapshot"]
        self.assertIn("unknown_snapshot_reference", {issue.code for issue in self.validate(database)})

    def test_duplicate_snapshot_id_is_rejected(self):
        database = deepcopy(self.database)
        first_snapshot_id = database["cases"][0]["evidence"]["snapshots"][0]["snapshot_id"]
        database["cases"][1]["evidence"]["snapshots"][0]["snapshot_id"] = first_snapshot_id
        self.assertIn("duplicate_snapshot_id", {issue.code for issue in self.validate(database)})

    def test_ai_review_requires_reviewed_public_record(self):
        database = deepcopy(self.database)
        database["cases"][1]["ai_review_usage"]["allowed"] = True
        issues = self.validate(database)
        self.assertTrue(any(issue.code == "schema" for issue in issues))

    def test_reviewed_record_requires_review_metadata(self):
        database = deepcopy(self.database)
        database["cases"][1]["governance"]["review_status"] = "reviewed"
        issues = self.validate(database)
        self.assertTrue(any(issue.code == "schema" for issue in issues))

    def test_structured_amount_requires_currency(self):
        database = deepcopy(self.database)
        database["cases"][0]["public_record"]["funding"]["requested"]["currency"] = None
        issues = self.validate(database)
        self.assertTrue(any(issue.code == "schema" for issue in issues))

    def test_pending_reconciliation_cannot_be_enabled_for_ai_review(self):
        database = deepcopy(self.database)
        case = database["cases"][0]
        case["governance"].update(
            review_status="reviewed",
            reviewed_at="2026-09-24",
            reviewed_by_role="GCC content owner",
        )
        case["ai_review_usage"]["allowed"] = True
        self.assertIn(
            "unsafe_ai_pending_reconciliation",
            {issue.code for issue in self.validate(database)},
        )


if __name__ == "__main__":
    unittest.main()
