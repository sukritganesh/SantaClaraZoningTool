"""Pure exact-zone retrieval tests for Block 6.3."""

from __future__ import annotations

import json
import unittest

from santa_clara_zoning import (
    ApprovedR1Ruleset,
    StandardsRetrievalError,
    UnsupportedZoneError,
    retrieve_zone_standards,
)
from santa_clara_zoning.standards import _retrieve_zone_standards_data


EXPECTED_CAPABILITIES = {
    "use.single_family_dwelling",
    "approval.zoning_clearance",
    "approval.architectural_review",
    "standard.maximum_primary_structure_height",
    "standard.maximum_stories",
    "standard.maximum_structure_coverage",
    "setback.front",
    "setback.interior_side",
    "setback.street_side",
    "setback.rear",
}


class ZoneStandardsRetrievalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ruleset = ApprovedR1Ruleset.load()

    def retrieve(self, zone: str) -> dict:
        return retrieve_zone_standards(zone, self.ruleset)

    def test_r1_6l_returns_complete_rules_and_filtered_provenance(self) -> None:
        result = self.retrieve("R1-6L")
        refs = result["shared_references"]

        self.assertEqual(result["zone"], "R1-6L")
        self.assertEqual(set(result["regulations"]), EXPECTED_CAPABILITIES)
        self.assertEqual(len(result["regulations"]), 10)
        self.assertEqual(len(refs["citations"]), 12)
        self.assertEqual(len(refs["exception_families"]), 9)
        self.assertEqual(len(refs["source_documents"]), 2)
        self.assertEqual(refs["conflicts"], {})
        self.assertNotIn("r1-8l-corner-side", refs["citations"])
        self.assertNotIn("conflict-rule", refs["citations"])

    def test_r1_8l_preserves_paired_yards_and_conflict(self) -> None:
        result = self.retrieve("R1-8L")
        refs = result["shared_references"]
        interior = result["regulations"]["setback.interior_side"]["requirement"]
        conflict = refs["conflicts"]["conflict-r1-8l-corner-side-first"]

        self.assertEqual(set(result["regulations"]), EXPECTED_CAPABILITIES)
        self.assertEqual(len(result["regulations"]), 10)
        self.assertEqual(len(refs["citations"]), 14)
        self.assertEqual(len(refs["exception_families"]), 9)
        self.assertEqual(len(refs["source_documents"]), 2)
        self.assertEqual(len(refs["conflicts"]), 1)
        self.assertEqual(
            [member["number"] for member in interior["base"]["value"]["members"]],
            [6, 9],
        )
        self.assertEqual(
            [
                member["number"]
                for member in interior["adjustments"][0]["effect"]["value"][
                    "members"
                ]
            ],
            [11, 14],
        )
        self.assertEqual(
            {assertion["value"]["number"] for assertion in conflict["assertions"]},
            {10, 15},
        )
        self.assertEqual(conflict["resolution"]["selected_value"]["number"], 15)

    def test_street_side_rule_remains_conditional_on_corner_context(self) -> None:
        for zone in self.ruleset.supported_zones:
            street_side = self.retrieve(zone)["regulations"]["setback.street_side"]
            self.assertEqual(street_side["applicability"]["lot_context"], "corner")

    def test_vertical_adjustments_remain_structured_and_unselected(self) -> None:
        result = self.retrieve("R1-6L")
        front = result["regulations"]["setback.front"]["requirement"]

        self.assertEqual(front["base"]["value"]["number"], 20)
        self.assertEqual(len(front["adjustments"]), 1)
        self.assertEqual(front["adjustments"][0]["trigger"]["story"], 2)
        self.assertEqual(
            front["adjustments"][0]["effect"]["value"]["number"],
            25,
        )

    def test_regulatory_context_and_scope_are_preserved(self) -> None:
        result = self.retrieve("R1-6L")
        context = result["regulatory_context"]
        canonical = self.ruleset.as_dict()

        self.assertEqual(context["ruleset_id"], self.ruleset.ruleset_id)
        self.assertEqual(context["ruleset_version"], self.ruleset.version)
        self.assertEqual(context["schema_version"], "2.0.0")
        self.assertEqual(context["approved_on"], self.ruleset.approved_on)
        self.assertEqual(context["verified_through"], self.ruleset.verified_through)
        self.assertEqual(context["scope"], canonical["scope"])
        self.assertEqual(result["not_evaluated"], canonical["not_evaluated"])
        self.assertEqual(result["disclaimer"], canonical["disclaimer"])

    def test_zone_key_must_match_exactly(self) -> None:
        for zone in ("R1", "r1-6l", " R1-6L ", "R1-7L"):
            with self.subTest(zone=zone):
                with self.assertRaises(UnsupportedZoneError) as caught:
                    self.retrieve(zone)
                self.assertEqual(caught.exception.reason_code, "unsupported_zone")

    def test_missing_transitive_reference_cannot_produce_partial_result(self) -> None:
        changed = self.ruleset.as_dict()
        changed["zones"]["R1-6L"]["regulations"][
            "standard.maximum_primary_structure_height"
        ]["requirement"]["source_refs"].append("missing-citation")

        with self.assertRaises(StandardsRetrievalError) as caught:
            _retrieve_zone_standards_data("R1-6L", changed)
        self.assertEqual(caught.exception.reason_code, "missing_reference")
        self.assertIn("missing-citation", str(caught.exception))

    def test_returned_results_cannot_mutate_loader_or_later_results(self) -> None:
        first = self.retrieve("R1-6L")
        first["regulations"].clear()
        first["shared_references"]["citations"].clear()
        first["not_evaluated"].clear()

        second = self.retrieve("R1-6L")
        self.assertEqual(len(second["regulations"]), 10)
        self.assertEqual(len(second["shared_references"]["citations"]), 12)
        self.assertEqual(second["not_evaluated"], self.ruleset.as_dict()["not_evaluated"])

    def test_repeated_retrieval_is_byte_equivalent(self) -> None:
        first = self.retrieve("R1-8L")
        second = self.retrieve("R1-8L")

        def encode(value: dict) -> bytes:
            return json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")

        self.assertEqual(encode(first), encode(second))


if __name__ == "__main__":
    unittest.main()
