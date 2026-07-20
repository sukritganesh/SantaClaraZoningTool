"""Residential address, selection, and contract 2.1 pipeline tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from santa_clara_zoning import (
    ApprovedResidentialRuleset,
    PipelineIntegrityError,
    RESIDENTIAL_CONTRACT_VERSION,
    ResidentialStandardsPipeline,
    StandardsRetrievalError,
    UnsupportedSelectionError,
)
from santa_clara_zoning.lookup import (
    DEFAULT_ADDRESS_SNAPSHOT,
    DEFAULT_RESIDENTIAL_SNAPSHOT,
)
from scripts.validate_residential_result_contract_v2_1 import validate_result


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INVENTORY = (
    REPO_ROOT / "tests/fixtures/residential_gis_fixture_inventory.json"
)
RESULT_SCHEMA = (
    REPO_ROOT / "contracts/residential-result-contract-2.1.0.schema.json"
)
SNAPSHOTS_AVAILABLE = (
    (DEFAULT_ADDRESS_SNAPSHOT / "address_points.geojson").is_file()
    and (
        DEFAULT_RESIDENTIAL_SNAPSHOT / "parcels_residential.geojson"
    ).is_file()
    and (
        DEFAULT_RESIDENTIAL_SNAPSHOT
        / "current_zoning_residential.geojson"
    ).is_file()
)


def canonical_bytes(value: dict) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def successful_lookup(zone: str = "R2") -> dict:
    return {
        "status": "residential_zone_found",
        "reason_code": "supported_residential_match",
        "query": {
            "entered_address": "1 Test Street",
            "normalized_address": "1 TEST ST",
        },
        "versions": {
            "address_snapshot": "2026-07-16",
            "residential_gis_snapshot": "2026-07-18",
        },
        "sources": {},
        "address": {"display_address": "1 Test Street"},
        "parcel": {"apn": "000-00-000", "designation": zone},
        "zoning": {
            "designation": zone,
            "parcel_attribute_agrees": True,
        },
    }


@unittest.skipUnless(
    SNAPSHOTS_AVAILABLE,
    "canonical residential GIS snapshots are not present",
)
class ResidentialStandardsPipelineIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pipeline = ResidentialStandardsPipeline.from_defaults()
        cls.ruleset_data = cls.pipeline.ruleset.as_dict()
        cls.schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))
        cls.inventory = json.loads(FIXTURE_INVENTORY.read_text(encoding="utf-8"))

    def assert_contract_result(self, result: dict) -> None:
        self.assertEqual(
            validate_result(
                result,
                schema=self.schema,
                ruleset=self.ruleset_data,
            ),
            [],
        )
        self.assertEqual(
            set(result),
            {
                "contract_version",
                "status",
                "reason_code",
                "query",
                "versions",
                "property",
                "available_selections",
                "requested_selection_id",
                "selection",
                "use_permission",
                "regulations",
                "not_evaluated_topics",
                "conflicts",
                "sources",
                "disclaimer",
            },
        )

    def test_r2_zone_found_requires_one_exact_selection(self) -> None:
        result = self.pipeline.analyze_address("1240 White Drive")
        self.assert_contract_result(result)
        self.assertEqual(result["status"], "residential_zone_found")
        self.assertEqual(result["property"]["zone"], "R2")
        self.assertEqual(
            [item["selection_id"] for item in result["available_selections"]],
            ["single_family", "two_family", "multifamily"],
        )
        self.assertIsNone(result["requested_selection_id"])
        self.assertIsNone(result["regulations"])

    def test_every_live_zone_and_available_selection_emits_valid_contract(self) -> None:
        profile_results = 0
        pathway_results = 0
        for fixture in self.inventory["real_address_fixtures"]:
            address = fixture["address"]["display_address"]
            zone_result = self.pipeline.analyze_address(address)
            with self.subTest(zone=fixture["designation"], selection=None):
                self.assert_contract_result(zone_result)
                self.assertEqual(
                    zone_result["property"]["zone"],
                    fixture["designation"],
                )
            for selection in zone_result["available_selections"]:
                selection_id = selection["selection_id"]
                result = self.pipeline.analyze_address(address, selection_id)
                with self.subTest(
                    zone=fixture["designation"],
                    selection=selection_id,
                ):
                    self.assert_contract_result(result)
                    self.assertEqual(
                        result["requested_selection_id"],
                        selection_id,
                    )
                    if selection["selection_kind"] == "profile":
                        profile_results += 1
                        self.assertEqual(
                            result["status"],
                            "residential_standards_found",
                        )
                        self.assertEqual(len(result["regulations"]), 10)
                    else:
                        pathway_results += 1
                        self.assertEqual(
                            result["status"],
                            "analysis_not_evaluated",
                        )
        self.assertEqual(profile_results, 14)
        self.assertEqual(pathway_results, 2)

    def test_unavailable_profile_is_a_source_backed_controlled_result(self) -> None:
        result = self.pipeline.analyze_address(
            "1577 Pomeroy Avenue",
            "single_family",
        )
        self.assert_contract_result(result)
        self.assertEqual(result["status"], "selection_not_available")
        self.assertEqual(
            result["use_permission"]["requirement"]["code"],
            "not_listed",
        )
        self.assertIsNone(result["selection"])
        self.assertIsNone(result["regulations"])

    def test_controlled_lookup_failures_never_gain_regulations(self) -> None:
        cases = (
            (
                "1500 Warburton Avenue",
                "outside_supported_residential_snapshot",
            ),
            ("99999 No Such Street", "address_not_found"),
            ("324 Los Padres Boulevard", "address_ambiguous"),
        )
        for address, status in cases:
            with self.subTest(status=status):
                result = self.pipeline.analyze_address(address, "multifamily")
                self.assert_contract_result(result)
                self.assertEqual(result["status"], status)
                self.assertIsNone(result["requested_selection_id"])
                self.assertEqual(result["available_selections"], [])
                self.assertIsNone(result["regulations"])
                self.assertEqual(result["sources"]["citations"], {})

    def test_versions_are_independent_and_exact(self) -> None:
        result = self.pipeline.analyze_address(
            "3105 Patrick Henry Drive",
            "multifamily",
        )
        self.assert_contract_result(result)
        self.assertEqual(
            result["versions"],
            {
                "address_snapshot": "2026-07-16",
                "residential_gis_snapshot": "2026-07-18",
                "ruleset": "2026-07-19.5",
                "ruleset_schema": "3.2.0",
                "result_contract": "2.1.0",
            },
        )
        self.assertEqual(
            result["contract_version"],
            RESIDENTIAL_CONTRACT_VERSION,
        )

    def test_return_mutation_cannot_change_later_results(self) -> None:
        first = self.pipeline.analyze_address(
            "3105 Patrick Henry Drive",
            "multifamily",
        )
        first["regulations"].clear()
        first["sources"]["citations"].clear()
        first["not_evaluated_topics"].clear()
        first["available_selections"].clear()
        second = self.pipeline.analyze_address(
            "3105 Patrick Henry Drive",
            "multifamily",
        )
        self.assert_contract_result(second)
        self.assertEqual(len(second["regulations"]), 10)
        self.assertTrue(second["sources"]["citations"])
        self.assertTrue(second["not_evaluated_topics"])
        self.assertEqual(len(second["available_selections"]), 1)

    def test_repeated_and_cross_process_results_are_byte_deterministic(self) -> None:
        first = self.pipeline.analyze_address(
            "3105 Patrick Henry Drive",
            "multifamily",
        )
        second = self.pipeline.analyze_address(
            "3105 Patrick Henry Drive",
            "multifamily",
        )
        self.assertEqual(canonical_bytes(first), canonical_bytes(second))

        script = """
import hashlib
import json
from santa_clara_zoning import ResidentialStandardsPipeline

pipeline = ResidentialStandardsPipeline.from_defaults()
payload = [
    pipeline.analyze_address("1240 White Drive", "multifamily"),
    pipeline.analyze_address(
        "636 Barto Street", "r1_chapter_18_24_two_unit"
    ),
    pipeline.analyze_address("1577 Pomeroy Avenue", "single_family"),
    pipeline.analyze_address("1500 Warburton Avenue"),
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
            completed = subprocess.run(
                [sys.executable, "-c", script],
                cwd=REPO_ROOT,
                env={**os.environ, "PYTHONHASHSEED": seed},
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            digests.append(completed.stdout.strip())
        self.assertEqual(digests[0], digests[1])

    def test_unknown_selection_is_never_fuzzily_matched(self) -> None:
        for selection in ("MultiFamily", "multi", " multifamily "):
            with self.subTest(selection=selection):
                with self.assertRaises(UnsupportedSelectionError):
                    self.pipeline.analyze_address(
                        "1240 White Drive",
                        selection,
                    )


class ResidentialStandardsPipelineBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ruleset = ApprovedResidentialRuleset.load()
        cls.ruleset_data = cls.ruleset.as_dict()
        cls.schema = json.loads(RESULT_SCHEMA.read_text(encoding="utf-8"))

    def pipeline(self, lookup_result: dict) -> ResidentialStandardsPipeline:
        lookup = Mock()
        lookup.lookup.return_value = lookup_result
        return ResidentialStandardsPipeline(lookup, self.ruleset)

    def test_review_required_maps_to_contract_without_partial_evidence(self) -> None:
        lookup_result = {
            "status": "review_required",
            "reason_code": "parcel_zoning_designation_mismatch",
            "query": {"entered_address": "1 Test Street"},
            "versions": {
                "address_snapshot": "2026-07-16",
                "residential_gis_snapshot": "2026-07-18",
            },
            "sources": {},
        }
        result = self.pipeline(lookup_result).analyze_address(
            "1 Test Street",
            "multifamily",
        )
        self.assertEqual(result["status"], "review_required")
        self.assertIsNone(result["property"])
        self.assertIsNone(result["requested_selection_id"])
        self.assertEqual(
            validate_result(
                result,
                schema=self.schema,
                ruleset=self.ruleset_data,
            ),
            [],
        )

    def test_invalid_lookup_shapes_fail_closed(self) -> None:
        cases = (
            (None, "invalid_lookup_result"),
            ({"status": "unknown", "versions": {}}, "invalid_lookup_versions"),
            (
                {
                    "status": "unknown",
                    "versions": {
                        "address_snapshot": "2026-07-16",
                        "residential_gis_snapshot": "2026-07-18",
                    },
                },
                "invalid_lookup_status",
            ),
            (
                {
                    **successful_lookup(),
                    "zoning": {
                        "designation": "R3",
                        "parcel_attribute_agrees": True,
                    },
                },
                "invalid_lookup_success",
            ),
            (
                {
                    "status": "outside_supported_residential_snapshot",
                    "versions": {
                        "address_snapshot": "2026-07-16",
                        "residential_gis_snapshot": "2026-07-18",
                    },
                    "address": {"display_address": "1 Test Street"},
                    "spatial_match_counts": {
                        "residential_parcels": 1,
                        "residential_zoning_features": 0,
                    },
                },
                "invalid_lookup_failure",
            ),
        )
        for lookup_result, reason_code in cases:
            with self.subTest(reason=reason_code):
                pipeline = self.pipeline(lookup_result)
                with self.assertRaises(PipelineIntegrityError) as caught:
                    pipeline.analyze_address("1 Test Street")
                self.assertEqual(caught.exception.reason_code, reason_code)

    def test_retrieval_errors_are_not_recast_as_planning_review(self) -> None:
        pipeline = self.pipeline(successful_lookup())
        failure = StandardsRetrievalError(
            "missing_reference",
            "broken residential citation",
        )
        with patch(
            "santa_clara_zoning.residential_pipeline."
            "retrieve_residential_selection",
            side_effect=failure,
        ):
            with self.assertRaises(StandardsRetrievalError) as caught:
                pipeline.analyze_address("1 Test Street", "multifamily")
        self.assertIs(caught.exception, failure)

    def test_incomplete_retrieval_cannot_become_partial_success(self) -> None:
        pipeline = self.pipeline(successful_lookup())
        with patch(
            "santa_clara_zoning.residential_pipeline."
            "retrieve_residential_selection",
            return_value={"zone": "R2"},
        ):
            with self.assertRaises(PipelineIntegrityError) as caught:
                pipeline.analyze_address("1 Test Street", "multifamily")
        self.assertEqual(
            caught.exception.reason_code,
            "invalid_residential_retrieval",
        )

    def test_non_string_address_is_rejected_before_lookup(self) -> None:
        lookup = Mock()
        pipeline = ResidentialStandardsPipeline(lookup, self.ruleset)
        with self.assertRaises(PipelineIntegrityError) as caught:
            pipeline.analyze_address(None)  # type: ignore[arg-type]
        lookup.lookup.assert_not_called()
        self.assertEqual(caught.exception.reason_code, "invalid_query")

    def test_pipeline_requires_the_approved_residential_loader(self) -> None:
        with self.assertRaisesRegex(TypeError, "ApprovedResidentialRuleset"):
            ResidentialStandardsPipeline(
                Mock(),
                object(),  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
