"""Validation tests for the public GCC history evidence layer."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

import yaml

from gcc_agent.knowledge.validate_history import (
    validate_history_registry,
    validate_history_repository,
    validate_paths,
)


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "data" / "gcc-public-history.yaml"
SCHEMA_PATH = ROOT / "schema" / "gcc-public-history.schema.json"


class PublicHistoryValidationTests(unittest.TestCase):
    def setUp(self):
        self.registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def validate_registry(self, registry):
        return validate_history_registry(registry, schema=self.schema)

    def test_current_history_source_layer_passes(self):
        self.assertEqual([], validate_paths())

    def test_source_and_five_projections_are_content_owner_approved(self):
        source = self.registry["sources"][0]
        self.assertEqual("human_reviewed", source["processing"]["sanitization_status"])
        self.assertEqual("approved", source["processing"]["review_status"])
        self.assertEqual(
            {"evidence_only", "bot_qa"}, set(source["processing"]["allowed_uses"])
        )
        self.assertEqual(5, len(self.registry["approved_projections"]))
        self.assertTrue(
            all(
                item["review"]["status"] == "approved"
                for item in self.registry["approved_projections"]
            )
        )

    def test_builder_flight_projection_uses_confirmed_person_times(self):
        projection = next(
            item
            for item in self.registry["approved_projections"]
            if item["projection_id"] == "gcc-builder-flight-history"
        )
        self.assertIn("132 人次", projection["answer_text"])
        self.assertNotIn("50.4%", projection["answer_text"])
        self.assertNotIn("50.4％", projection["answer_text"])

    def test_runtime_connection_is_rejected(self):
        registry = deepcopy(self.registry)
        registry["runtime"]["connected"] = True
        self.assertIn("schema", {issue.code for issue in self.validate_registry(registry)})

    def test_duplicate_source_id_is_rejected(self):
        registry = deepcopy(self.registry)
        registry["sources"].append(deepcopy(registry["sources"][0]))
        self.assertIn(
            "duplicate_source_id", {issue.code for issue in self.validate_registry(registry)}
        )

    def test_duplicate_section_id_is_rejected(self):
        registry = deepcopy(self.registry)
        registry["sources"][0]["sections"][1]["section_id"] = registry["sources"][0][
            "sections"
        ][0]["section_id"]
        self.assertIn(
            "duplicate_section_id", {issue.code for issue in self.validate_registry(registry)}
        )

    def test_duplicate_projection_id_is_rejected(self):
        registry = deepcopy(self.registry)
        registry["approved_projections"][1]["projection_id"] = registry[
            "approved_projections"
        ][0]["projection_id"]
        self.assertIn(
            "duplicate_projection_id", {issue.code for issue in self.validate_registry(registry)}
        )

    def test_projection_cannot_use_excluded_section(self):
        registry = deepcopy(self.registry)
        registry["approved_projections"][0]["source_references"][0]["section_ids"] = [
            "testimonials"
        ]
        self.assertIn(
            "excluded_projection_section",
            {issue.code for issue in self.validate_registry(registry)},
        )

    def test_projection_cannot_reference_unknown_section(self):
        registry = deepcopy(self.registry)
        registry["approved_projections"][0]["source_references"][0]["section_ids"] = [
            "missing-section"
        ]
        self.assertIn(
            "unknown_projection_section", {issue.code for issue in self.validate_registry(registry)}
        )

    def test_projection_rejects_unresolved_selection_rate(self):
        registry = deepcopy(self.registry)
        registry["approved_projections"][0]["answer_text"] += " 入選率是 50.4%。"
        self.assertIn(
            "unresolved_selection_rate",
            {issue.code for issue in self.validate_registry(registry)},
        )

    def test_projection_requires_approved_bot_qa_source(self):
        registry = deepcopy(self.registry)
        registry["sources"][0]["processing"]["review_status"] = "pending"
        registry["sources"][0]["processing"]["allowed_uses"] = ["evidence_only"]
        self.assertIn(
            "unapproved_projection_source", {issue.code for issue in self.validate_registry(registry)}
        )

    def test_time_bounded_aggregate_requires_both_dates(self):
        registry = deepcopy(self.registry)
        aggregate = next(
            section
            for section in registry["sources"][0]["sections"]
            if section["classification"] == "time_bounded_aggregate"
        )
        aggregate["temporal_scope"]["start"] = None
        self.assertIn(
            "missing_aggregate_period", {issue.code for issue in self.validate_registry(registry)}
        )

    def test_unreviewed_source_cannot_enable_bot_qa(self):
        registry = deepcopy(self.registry)
        registry["sources"][0]["processing"]["review_status"] = "pending"
        registry["sources"][0]["processing"]["allowed_uses"] = ["bot_qa"]
        self.assertIn(
            "unsafe_unreviewed_source_use",
            {issue.code for issue in validate_history_repository(registry, root=ROOT)},
        )

    def test_extract_checksum_is_enforced(self):
        registry = deepcopy(self.registry)
        registry["sources"][0]["extract"]["checksum"] = "sha256:" + "0" * 64
        self.assertIn(
            "extract_checksum_mismatch",
            {issue.code for issue in validate_history_repository(registry, root=ROOT)},
        )


if __name__ == "__main__":
    unittest.main()
