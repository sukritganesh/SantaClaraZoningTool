"""Block 6 integration and acceptance tests for address-to-standards retrieval."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
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
REPO_ROOT = Path(__file__).resolve().parents[1]
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


def canonical_bytes(value: dict) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


@unittest.skipUnless(SNAPSHOTS_AVAILABLE, "canonical raw GIS snapshots are not present")
class R1StandardsPipelineIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pipeline = R1StandardsPipeline.from_defaults()

    def assert_complete_success(
        self,
        result: dict,
        *,
        apn: str,
        zone: str,
        citation_count: int,
        conflict_count: int,
    ) -> None:
        canonical_ruleset = self.pipeline.ruleset.as_dict()
        context = result["regulatory_context"]
        references = result["shared_references"]

        self.assertEqual(result["contract_version"], CONTRACT_VERSION)
        self.assertEqual(result["status"], "r1_standards_found")
        self.assertEqual(
            result["reason_code"],
            "approved_r1_standards_retrieved",
        )
        self.assertEqual(result["parcel"]["apn"], apn)
        self.assertEqual(result["parcel"]["designation"], zone)
        self.assertEqual(result["zoning"]["designation"], zone)
        self.assertIs(result["zoning"]["parcel_attribute_agrees"], True)
        self.assertEqual(set(result["regulations"]), EXPECTED_CAPABILITIES)

        zone_slug = zone.lower()
        for capability, rule in result["regulations"].items():
            self.assertEqual(
                rule["rule_id"],
                f"us.ca.santa_clara.{zone_slug}.{capability}",
            )
            self.assertIs(rule["approved_for_ruleset"], True)
            self.assertTrue(rule["conditions"])

        self.assertEqual(context["jurisdiction"], canonical_ruleset["jurisdiction"])
        self.assertEqual(context["ruleset_id"], self.pipeline.ruleset.ruleset_id)
        self.assertEqual(context["ruleset_version"], self.pipeline.ruleset.version)
        self.assertEqual(context["schema_version"], "2.0.0")
        self.assertEqual(context["approved_on"], self.pipeline.ruleset.approved_on)
        self.assertEqual(
            context["verified_through"],
            self.pipeline.ruleset.verified_through,
        )
        self.assertEqual(context["scope"], canonical_ruleset["scope"])

        self.assertEqual(len(references["source_documents"]), 2)
        self.assertEqual(len(references["citations"]), citation_count)
        self.assertEqual(len(references["exception_families"]), 9)
        self.assertEqual(len(references["conflicts"]), conflict_count)
        self.assertEqual(result["not_evaluated"], canonical_ruleset["not_evaluated"])
        self.assertEqual(result["disclaimer"], canonical_ruleset["disclaimer"])
        self.assertEqual(result["versions"]["ruleset"], "2026-07-17.2")
        self.assertEqual(result["versions"]["address_snapshot"], "2026-07-16")
        self.assertEqual(result["versions"]["r1_gis_snapshot"], "2026-07-14")
        self.assertEqual(
            set(result["sources"]),
            {"address_layer", "parcel_layer", "zoning_layer"},
        )

        requirements = {
            capability: result["regulations"][capability]["requirement"]
            for capability in EXPECTED_CAPABILITIES
        }
        self.assertEqual(
            requirements["use.single_family_dwelling"]["code"],
            "permitted_by_right",
        )
        self.assertEqual(requirements["approval.zoning_clearance"]["code"], "required")
        self.assertEqual(
            requirements["approval.architectural_review"]["code"],
            "required",
        )
        self.assertEqual(
            requirements["standard.maximum_primary_structure_height"]["value"],
            {"number": 25, "unit": "ft"},
        )
        self.assertEqual(
            requirements["standard.maximum_stories"]["value"],
            {"number": 2, "unit": "stories"},
        )
        self.assertEqual(
            requirements["standard.maximum_structure_coverage"]["value"],
            {"number": 40, "unit": "percent"},
        )
        self.assertEqual(
            result["regulations"]["setback.street_side"]["applicability"][
                "lot_context"
            ],
            "corner",
        )

    def test_barto_connects_r1_6l_lookup_to_complete_rules(self) -> None:
        result = self.pipeline.analyze_address("636 barto st santa clara ca")

        self.assert_complete_success(
            result,
            apn="293-16-045",
            zone="R1-6L",
            citation_count=12,
            conflict_count=0,
        )
        self.assertEqual(result["query"]["normalized_address"], "636 BARTO ST")
        street_side = result["regulations"]["setback.street_side"]["requirement"]
        self.assertEqual(street_side["base"]["value"]["number"], 10)
        self.assertEqual(
            street_side["adjustments"][0]["effect"]["value"]["number"],
            15,
        )

    def test_brookside_preserves_r1_8l_pair_and_conflict(self) -> None:
        result = self.pipeline.analyze_address("108 Brookside Avenue")
        interior = result["regulations"]["setback.interior_side"]["requirement"]
        street_side = result["regulations"]["setback.street_side"]["requirement"]
        conflict = result["shared_references"]["conflicts"][
            "conflict-r1-8l-corner-side-first"
        ]

        self.assert_complete_success(
            result,
            apn="303-22-022",
            zone="R1-8L",
            citation_count=14,
            conflict_count=1,
        )
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
        self.assertEqual(street_side["base"]["value"]["number"], 15)
        self.assertEqual(
            {assertion["value"]["number"] for assertion in conflict["assertions"]},
            {10, 15},
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
                lookup_result = self.pipeline.lookup_engine.lookup(address)
                result = self.pipeline.analyze_address(address)
                self.assertEqual(
                    result,
                    {**lookup_result, "contract_version": CONTRACT_VERSION},
                )
                self.assertEqual(result["status"], expected_status)

    def test_repeated_pipeline_results_are_byte_equivalent(self) -> None:
        for address in ("636 Barto Street", "108 Brookside Avenue"):
            with self.subTest(address=address):
                first = self.pipeline.analyze_address(address)
                second = self.pipeline.analyze_address(address)
                self.assertEqual(canonical_bytes(first), canonical_bytes(second))

    def test_cross_process_hash_seed_does_not_change_canonical_results(self) -> None:
        script = """
import hashlib
import json
from santa_clara_zoning import R1StandardsPipeline

pipeline = R1StandardsPipeline.from_defaults()
payload = [
    pipeline.analyze_address("636 Barto Street"),
    pipeline.analyze_address("108 Brookside Avenue"),
]
encoded = json.dumps(
    payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
).encode("utf-8")
print(hashlib.sha256(encoded).hexdigest())
"""
        digests = []
        for seed in ("1", "987654"):
            environment = {**os.environ, "PYTHONHASHSEED": seed}
            completed = subprocess.run(
                [sys.executable, "-c", script],
                cwd=REPO_ROOT,
                env=environment,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            digests.append(completed.stdout.strip())

        self.assertEqual(digests[0], digests[1])

    def test_returned_result_mutation_cannot_change_later_pipeline_results(self) -> None:
        first = self.pipeline.analyze_address("636 Barto Street")
        first["regulations"].clear()
        first["shared_references"]["citations"].clear()
        first["not_evaluated"].clear()
        first["versions"]["ruleset"] = "changed"

        second = self.pipeline.analyze_address("636 Barto Street")
        self.assertEqual(set(second["regulations"]), EXPECTED_CAPABILITIES)
        self.assertEqual(len(second["shared_references"]["citations"]), 12)
        self.assertEqual(
            second["not_evaluated"],
            self.pipeline.ruleset.as_dict()["not_evaluated"],
        )
        self.assertEqual(second["versions"]["ruleset"], "2026-07-17.2")


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
