"""Onboarding content foundation contract tests."""

from copy import deepcopy
from pathlib import Path
import unittest

from gcc_agent.knowledge.onboarding import (
    approved_topics,
    load_onboarding,
    validate_onboarding,
)


ROOT = Path(__file__).resolve().parents[2]
ONBOARDING_PATH = ROOT / "data" / "onboarding.yaml"


class OnboardingContentTests(unittest.TestCase):
    def setUp(self):
        self.data = load_onboarding(ONBOARDING_PATH)

    def test_owner_supplied_baseline_is_valid_and_disconnected(self):
        self.assertEqual("0.1.0", self.data["schema_version"])
        self.assertFalse(self.data["runtime"]["connected"])
        self.assertEqual(
            "configured_group_members",
            self.data["audience"]["eligibility"],
        )
        self.assertEqual("none", self.data["audience"]["navigation_buttons"])
        self.assertFalse(self.data["provenance"]["automatic_sync"])
        self.assertFalse(self.data["provenance"]["internal_source_urls_stored"])
        self.assertEqual(["zh-CN"], self.data["provenance"]["available_locales"])

    def test_all_nine_owner_topics_are_approved_for_later_integration(self):
        topics = approved_topics(self.data)
        self.assertEqual(9, len(topics))
        self.assertEqual(
            {
                "gcc-overview",
                "gcc-beliefs",
                "gcc-focus",
                "why-participate",
                "official-channels",
                "join-volunteer-community",
                "activities-and-tasks",
                "volunteer-and-builder",
                "become-gcc-builder",
            },
            {topic["id"] for topic in topics},
        )
        self.assertTrue(
            all(set(topic["content"]) == {"zh-CN"} for topic in topics)
        )

    def test_public_channels_match_the_owner_supplied_values(self):
        channels = self.data["public_channels"]
        self.assertEqual("https://www.gccofficial.org/", channels["website"])
        self.assertEqual("https://x.com/GCCofCommons", channels["x"])
        self.assertEqual(
            "https://t.me/+GpdpcPIN2fY5YTZl",
            channels["telegram"]["url"],
        )
        self.assertEqual("admin@gccofficial.org", channels["email"])

    def test_owner_wording_keeps_slogan_ops_and_builder_boundary(self):
        by_id = {topic["id"]: topic for topic in self.data["topics"]}
        overview = by_id["gcc-overview"]["content"]["zh-CN"]
        focus = by_id["gcc-focus"]
        builder = by_id["become-gcc-builder"]["content"]["zh-CN"]

        self.assertIn(
            "Fund & Support Public Goods We Believe In",
            " ".join(overview["paragraphs"]),
        )
        self.assertEqual("2026 H2", focus["context_label"])
        self.assertEqual(3, len(focus["content"]["zh-CN"]["bullets"]))
        self.assertIn("以最新发布为准", " ".join(builder["paragraphs"]))

    def test_internal_feishu_reference_is_rejected(self):
        invalid = deepcopy(self.data)
        invalid["topics"][0]["content"]["zh-CN"]["links"].append(
            {"label": "internal", "url": "https://my.feishu.cn/wiki/internal"}
        )
        with self.assertRaisesRegex(ValueError, "Feishu"):
            validate_onboarding(invalid)

    def test_duplicate_topic_or_incomplete_journey_is_rejected(self):
        duplicate = deepcopy(self.data)
        duplicate["topics"].append(deepcopy(duplicate["topics"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate topic"):
            validate_onboarding(duplicate)

        missing = deepcopy(self.data)
        missing["journey"][0]["topic_ids"].pop()
        with self.assertRaisesRegex(ValueError, "every topic"):
            validate_onboarding(missing)


if __name__ == "__main__":
    unittest.main()
