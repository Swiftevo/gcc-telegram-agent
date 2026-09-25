"""Validation tests for the project case database schema and references."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import yaml

from gcc_agent.knowledge.validate_cases import (
    validate_case_database,
    validate_paths,
    validate_repository_data,
)


ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = ROOT / "data" / "project-case-seeds.yaml"
DATABASE_SCHEMA_PATH = ROOT / "schema" / "project-case-database.schema.json"
CASE_SCHEMA_PATH = ROOT / "schema" / "project.schema.json"
MIGRATION_PATH = ROOT / "data" / "project-case-migration.yaml"
LEGACY_CATALOG_PATH = ROOT / "projects.yaml"


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

    def validate_repository(self, database=None, migration=None, legacy_catalog=None):
        return validate_repository_data(
            self.database if database is None else database,
            migration=(
                yaml.safe_load(MIGRATION_PATH.read_text(encoding="utf-8"))
                if migration is None
                else migration
            ),
            legacy_catalog=(
                yaml.safe_load(LEGACY_CATALOG_PATH.read_text(encoding="utf-8"))
                if legacy_catalog is None
                else legacy_catalog
            ),
            root=ROOT,
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

    def test_deprecated_amount_fields_are_rejected(self):
        database = deepcopy(self.database)
        database["cases"][0]["public_record"]["amount_usd"] = 40000
        self.assertIn(
            "deprecated_amount_field",
            {issue.code for issue in self.validate(database)},
        )

    def test_funded_status_requires_disbursement_evidence(self):
        database = deepcopy(self.database)
        case = self.case(database, "gcc-eth-city-eth-beijing-2025")
        case["public_record"]["lifecycle_status"]["grant_status"] = "funded"
        self.assertIn(
            "unsupported_funded_status",
            {issue.code for issue in self.validate(database)},
        )

    def test_grant_application_requires_sanitized_profile(self):
        database = deepcopy(self.database)
        case = self.case(database, "gcc-open-source-oskey")
        application = next(
            snapshot
            for snapshot in case["evidence"]["snapshots"]
            if snapshot["source_type"] == "grant_application"
        )
        application["processing"]["handling_profile"] = "public_source_extract"
        self.assertIn(
            "invalid_source_profile",
            {issue.code for issue in self.validate(database)},
        )

    def test_unreviewed_source_is_evidence_only(self):
        database = deepcopy(self.database)
        source = database["cases"][0]["evidence"]["snapshots"][0]
        source["processing"]["allowed_uses"] = ["bot_qa"]
        self.assertIn(
            "unsafe_unreviewed_source_use",
            {issue.code for issue in self.validate(database)},
        )

    def test_case_cannot_be_reviewed_before_all_sources(self):
        database = deepcopy(self.database)
        case = self.case(database, "gcc-open-source-oskey")
        case["governance"].update(
            review_status="reviewed",
            reviewed_at="2026-09-25",
            reviewed_by_role="GCC content owner",
        )
        self.assertIn(
            "unreviewed_source_in_reviewed_case",
            {issue.code for issue in self.validate(database)},
        )

    def test_source_checksum_is_enforced(self):
        database = deepcopy(self.database)
        database["cases"][0]["evidence"]["snapshots"][0]["checksum"] = "sha256:" + "0" * 64
        self.assertIn(
            "source_checksum_mismatch",
            {issue.code for issue in self.validate_repository(database=database)},
        )

    def test_legacy_catalog_digest_is_enforced(self):
        legacy_catalog = yaml.safe_load(LEGACY_CATALOG_PATH.read_text(encoding="utf-8"))
        legacy_catalog["funded_projects"][0]["summary"] += " changed"
        self.assertIn(
            "legacy_catalog_digest_changed",
            {
                issue.code
                for issue in self.validate_repository(legacy_catalog=legacy_catalog)
            },
        )

    def test_every_migrated_legacy_case_has_one_mapping(self):
        migration = yaml.safe_load(MIGRATION_PATH.read_text(encoding="utf-8"))
        migration["mappings"] = migration["mappings"][1:]
        self.assertIn(
            "missing_migration_mapping",
            {issue.code for issue in self.validate_repository(migration=migration)},
        )

    def test_repository_scan_rejects_row_level_wallet_vote_data(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_directory = root / "data" / "source-snapshots"
            source_directory.mkdir(parents=True)
            content = "| Voter | Choice | Voting power |\n| 0x" + "1" * 40 + " | For | 1 |\n"
            source_path = source_directory / "unsafe.md"
            source_path.write_text(content, encoding="utf-8")
            checksum = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
            database = {
                "cases": [
                    {
                        "case_id": "test-case",
                        "canonical_project_id": "new-project",
                        "evidence": {
                            "snapshots": [
                                {
                                    "storage_uri": "data/source-snapshots/unsafe.md",
                                    "checksum": checksum,
                                }
                            ]
                        },
                    }
                ]
            }
            legacy_catalog = {"funded_projects": []}
            legacy_digest = hashlib.sha256(
                json.dumps(
                    legacy_catalog,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            migration = {
                "legacy_catalog": {
                    "record_count": 0,
                    "unmapped_record_count": 0,
                    "canonical_json_sha256": legacy_digest,
                },
                "mappings": [],
            }
            issues = validate_repository_data(
                database,
                migration=migration,
                legacy_catalog=legacy_catalog,
                root=root,
            )
            self.assertIn("unsafe_source_content", {issue.code for issue in issues})

    def test_repository_scan_rejects_orphan_source_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_directory = root / "data" / "source-snapshots"
            source_directory.mkdir(parents=True)
            (source_directory / "orphan.md").write_text("unused", encoding="utf-8")
            legacy_catalog = {"funded_projects": []}
            legacy_digest = hashlib.sha256(
                json.dumps(
                    legacy_catalog,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            issues = validate_repository_data(
                {"cases": []},
                migration={
                    "legacy_catalog": {
                        "record_count": 0,
                        "unmapped_record_count": 0,
                        "canonical_json_sha256": legacy_digest,
                    },
                    "mappings": [],
                },
                legacy_catalog=legacy_catalog,
                root=root,
            )
            self.assertIn("orphan_source_file", {issue.code for issue in issues})


if __name__ == "__main__":
    unittest.main()
