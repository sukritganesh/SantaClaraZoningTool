"""Address-to-approved-standards integration tests for Block 6.4."""

from __future__ import annotations

import json
import unittest
from unittest.mock import Mock, patch

from santa_clara_zoning import (
    ApprovedR1Ruleset,
    CONTRACT_VERSION,
    PipelineIntegrityError,
    R1StandardsPipeline,
    StandardsRetrievalError,
)
from santa_clara_zoning.lookup import DEFAULT_ADDRESS_SNAPSHOT, DEFAULT_R1_SNAPSHOT


SNAPSHOTS_AVAILABLE = (
    (DEFAULT_ADDRESS_SNAPSHOT / "address_points.geojson").is_file()
    and (DEFAULT_R1_SNAPSHOT / "parcels_r1.geojson").is_file()
    and (DEFAULT_R1_SNAPSHOT / "current_zoning_r1.geojson").is_file()
)


@unittest.skipUnless(SNAPSHOTS_AVAILABLE, "canonical raw GIS snapshots are not present")
class R1StandardsPipelineIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pipeline = R1StandardsPipeline.from_defaults()

    def test_barto_connects_r1_6l_lookup_to_complete_rules(self) -> None:
        result = self.pipeline.analyze_address("636 barto st santa clara ca")

        self.assertEqual(result["contract_version"], CONTRACT_VERSION)
        self.assertEqual(result["status"], "r1_standards_found")
        self.assertEqual(
            result["reason_code"],
            "approved_r1_standards_retrieved",
        )
        self.assertEqual(result["query"]["normalized_address"], "636 BARTO ST")
        self.assertEqual(result["parcel"]["apn"], "293-16-045")
        self.assertEqual(result["zoning"]["designation"], "R1-6L")
        self.assertEqual(len(result["regulations"]), 10)
        self.assertEqual(len(result["shared_references"]["citations"]), 12)
        self.assertEqual(result["versions"]["ruleset"], "2026-07-17.2")
        self.assertEqual(result["versions"]["address_snapshot"], "2026-07-16")
        self.assertEqual(result["versions"]["r1_gis_snapshot"], "2026-07-14")

    def test_brookside_preserves_r1_8l_pair_and_conflict(self) -> None:
        result = self.pipeline.analyze_address("108 Brookside Avenue")
        interior = result["regulations"]["setback.interior_side"]["requirement"]
        conflict = result["shared_references"]["conflicts"][
            "conflict-r1-8l-corner-side-first"
        ]

        self.assertEqual(result["parcel"]["apn"], "303-22-022")
        self.assertEqual(result["zoning"]["designation"], "R1-8L")
        self.assertEqual(
            [member["number"] for member in interior["base"]["value"]["members"]],
            [6, 9],
        )
        self.assertEqual(conflict["resolution"]["selected_value"]["number"], 15)

    def test_controlled_lookup_outcomes_do_not_gain_regulations(self) -> None:
        fixtures = {
            "1500 Warburton Avenue": "outside_supported_r1_snapshot",
            "324 Los Padres Boulevard": "address_ambiguous",
            "99999 No Such Street": "address_not_found",
        }

        for address, expected_status in fixtures.items():
            with self.subTest(address=address):
                result = self.pipeline.analyze_address(address)
                self.assertEqual(result["contract_version"], CONTRACT_VERSION)
                self.assertEqual(result["status"], expected_status)
                self.assertNotIn("regulations", result)
                self.assertNotIn("regulatory_context", result)
                self.assertNotIn("ruleset", result["versions"])

    def test_repeated_pipeline_results_are_byte_equivalent(self) -> None:
        first = self.pipeline.analyze_address("636 Barto Street")
        second = self.pipeline.analyze_address("636 Barto Street")

        def encode(value: dict) -> bytes:
            return json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")

        self.assertEqual(encode(first), encode(second))


class R1StandardsPipelineBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ruleset = ApprovedR1Ruleset.load()

    def test_non_successes_are_preserved_without_regulatory_retrieval(self) -> None:
        outcomes = {
            "address_not_found": "no_exact_address_match",
            "address_ambiguous": "multiple_exact_address_matches",
            "outside_supported_r1_snapshot": "no_r1_parcel_or_zoning_match",
            "review_required": "parcel_zoning_designation_mismatch",
        }

        for status, reason_code in outcomes.items():
            with self.subTest(status=status):
                lookup_result = {
                    "status": status,
                    "reason_code": reason_code,
                    "query": {"entered_address": "fixture"},
                    "versions": {},
                    "sources": {},
                }
                lookup = Mock()
                lookup.lookup.return_value = lookup_result
                pipeline = R1StandardsPipeline(lookup, self.ruleset)

                with patch(
                    "santa_clara_zoning.pipeline.retrieve_zone_standards"
                ) as retrieve:
                    result = pipeline.analyze_address("fixture")

                retrieve.assert_not_called()
                self.assertEqual(
                    result,
                    {"contract_version": CONTRACT_VERSION, **lookup_result},
                )

    def test_inconsistent_lookup_success_fails_closed(self) -> None:
        lookup = Mock()
        lookup.lookup.return_value = {
            "status": "r1_zone_found",
            "parcel": {"designation": "R1-6L"},
            "zoning": {
                "designation": "R1-8L",
                "parcel_attribute_agrees": True,
            },
            "versions": {},
            "sources": {},
        }
        pipeline = R1StandardsPipeline(lookup, self.ruleset)

        with self.assertRaises(PipelineIntegrityError) as caught:
            pipeline.analyze_address("1 Test Street")
        self.assertEqual(caught.exception.reason_code, "invalid_lookup_success")

    def test_regulatory_integrity_error_is_not_changed_to_planning_review(self) -> None:
        lookup = Mock()
        lookup.lookup.return_value = {
            "status": "r1_zone_found",
            "parcel": {"designation": "R1-6L"},
            "zoning": {
                "designation": "R1-6L",
                "parcel_attribute_agrees": True,
            },
            "versions": {},
            "sources": {},
        }
        pipeline = R1StandardsPipeline(lookup, self.ruleset)
        failure = StandardsRetrievalError("missing_reference", "broken citation")

        with patch(
            "santa_clara_zoning.pipeline.retrieve_zone_standards",
            side_effect=failure,
        ):
            with self.assertRaises(StandardsRetrievalError) as caught:
                pipeline.analyze_address("1 Test Street")

        self.assertIs(caught.exception, failure)

    def test_incomplete_regulatory_result_cannot_become_partial_success(self) -> None:
        lookup = Mock()
        lookup.lookup.return_value = {
            "status": "r1_zone_found",
            "parcel": {"designation": "R1-6L"},
            "zoning": {
                "designation": "R1-6L",
                "parcel_attribute_agrees": True,
            },
            "versions": {},
            "sources": {},
        }
        pipeline = R1StandardsPipeline(lookup, self.ruleset)

        with patch(
            "santa_clara_zoning.pipeline.retrieve_zone_standards",
            return_value={"zone": "R1-6L"},
        ):
            with self.assertRaises(PipelineIntegrityError) as caught:
                pipeline.analyze_address("1 Test Street")

        self.assertEqual(caught.exception.reason_code, "invalid_standards_result")


if __name__ == "__main__":
    unittest.main()
