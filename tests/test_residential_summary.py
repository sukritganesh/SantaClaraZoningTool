"""Common-zone residential summary tests."""

from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

from santa_clara_zoning import (
    ApprovedResidentialRuleset,
    PipelineIntegrityError,
    ResidentialStandardsPipeline,
)
from santa_clara_zoning.residential_standards import (
    retrieve_residential_selection as exact_retrieve,
)
from santa_clara_zoning.residential_summary import (
    RESIDENTIAL_SUMMARY_CONTRACT_VERSION,
    ResidentialZoneSummaryPipeline,
)


class _StaticLookup:
    def __init__(self, zone: str | None) -> None:
        self.zone = zone

    def lookup(self, entered_address: str) -> dict:
        base = {
            "query": {
                "entered_address": entered_address,
                "normalized_address": entered_address.upper(),
            },
            "versions": {
                "address_snapshot": "2026-07-16",
                "residential_gis_snapshot": "2026-07-18",
            },
            "sources": {},
        }
        if self.zone is None:
            return {
                **base,
                "status": "address_not_found",
                "reason_code": "no_exact_address_match",
            }
        return {
            **base,
            "status": "residential_zone_found",
            "reason_code": "supported_residential_match",
            "address": {"display_address": "1 Test Street"},
            "parcel": {"apn": "000-00-000", "designation": self.zone},
            "zoning": {
                "designation": self.zone,
                "parcel_attribute_agrees": True,
            },
        }

    def suggest_addresses(self, query: str) -> dict:
        return {
            "status": "ok",
            "query": query,
            "normalized_query": query.upper(),
            "address_snapshot": "2026-07-16",
            "total_matches": 1,
            "truncated": False,
            "suggestions": [
                {
                    "value": "1 Test Street",
                    "display_address": "1 Test Street",
                    "secondary_text": "Santa Clara, CA 95050",
                    "source_record_count": 1,
                }
            ],
        }

    def property_map_context(self, entered_address: str) -> dict:
        return {
            "contract_version": "1.0.0",
            "status": "ok",
            "query": entered_address,
            "property": {"zone": self.zone},
        }


def _pipeline(zone: str | None) -> ResidentialZoneSummaryPipeline:
    selection_pipeline = ResidentialStandardsPipeline(
        lookup_engine=_StaticLookup(zone),
        ruleset=ApprovedResidentialRuleset.load(),
    )
    return ResidentialZoneSummaryPipeline(selection_pipeline)


def _canonical(value: dict) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


class ResidentialZoneSummaryTest(unittest.TestCase):
    def test_suggestions_delegate_through_the_loaded_pipeline_defensively(self) -> None:
        pipeline = _pipeline("R2")

        first = pipeline.suggest_addresses("1 test")
        first["suggestions"][0]["value"] = "changed"
        second = pipeline.suggest_addresses("1 test")

        self.assertEqual(second["suggestions"][0]["value"], "1 Test Street")
        self.assertEqual(second["address_snapshot"], "2026-07-16")

    def test_property_map_delegates_through_the_loaded_pipeline_defensively(self) -> None:
        pipeline = _pipeline("R2")

        first = pipeline.property_map_context("1 Test Street")
        first["property"]["zone"] = "changed"
        second = pipeline.property_map_context("1 Test Street")

        self.assertEqual(second["property"]["zone"], "R2")

    def test_r2_presents_three_uses_and_one_common_rule_set(self) -> None:
        result = _pipeline("R2").analyze_address("1 Test Street")

        self.assertEqual(
            result["contract_version"],
            RESIDENTIAL_SUMMARY_CONTRACT_VERSION,
        )
        self.assertEqual(result["status"], "residential_zone_summary_found")
        self.assertEqual(
            [item["selection_id"] for item in result["residential_uses"]],
            ["single_family", "two_family", "multifamily"],
        )
        self.assertEqual(len(result["regulations"]), 10)
        for rule in result["regulations"].values():
            self.assertEqual(len(rule["source_rule_ids"]), 3)
            self.assertEqual(
                rule["applies_to_selection_ids"],
                ["single_family", "two_family", "multifamily"],
            )
        self.assertEqual(result["special_pathways"], [])

    def test_profile_specific_topic_remains_conditional(self) -> None:
        for zone, profiles in (
            ("R2", ["single_family", "two_family", "multifamily"]),
            ("R3", ["two_family", "multifamily"]),
            ("R4", ["two_family", "multifamily"]),
        ):
            with self.subTest(zone=zone):
                result = _pipeline(zone).analyze_address("1 Test Street")
                self.assertEqual(
                    [item["selection_id"] for item in result["residential_uses"]],
                    profiles,
                )
                objective_design = next(
                    topic
                    for topic in result["not_evaluated_topics"]
                    if topic["topic_id"] == "objective_design_standards"
                )
                self.assertEqual(
                    objective_design["applies_to_selection_ids"],
                    ["multifamily"],
                )

    def test_r1_pathway_never_inherits_ordinary_standards(self) -> None:
        result = _pipeline("R1-6L").analyze_address("1 Test Street")

        self.assertEqual(
            [item["selection_id"] for item in result["residential_uses"]],
            ["single_family"],
        )
        self.assertEqual(len(result["special_pathways"]), 1)
        pathway = result["special_pathways"][0]
        self.assertEqual(pathway["analysis_status"], "not_evaluated")
        self.assertTrue(pathway["not_evaluated_topics"])
        self.assertNotIn("regulations", pathway)

    def test_single_profile_zones_remain_direct(self) -> None:
        for zone in ("R5", "R6", "PH-R5", "UV", "VR", "UC", "HDF"):
            with self.subTest(zone=zone):
                result = _pipeline(zone).analyze_address("1 Test Street")
                self.assertEqual(
                    [item["selection_id"] for item in result["residential_uses"]],
                    ["multifamily"],
                )
                self.assertEqual(len(result["regulations"]), 10)

    def test_profile_divergence_fails_closed(self) -> None:
        def divergent(zone: str, selection_id: str, ruleset: object) -> dict:
            result = exact_retrieve(zone, selection_id, ruleset)
            if selection_id == "two_family":
                result = copy.deepcopy(result)
                result["regulations"]["standard.maximum_stories"]["requirement"][
                    "value"
                ]["number"] = 99
            return result

        with patch(
            "santa_clara_zoning.residential_summary.retrieve_residential_selection",
            side_effect=divergent,
        ):
            with self.assertRaises(PipelineIntegrityError) as raised:
                _pipeline("R2").analyze_address("1 Test Street")
        self.assertEqual(
            raised.exception.reason_code,
            "structure_specific_standards_require_selection",
        )

    def test_lookup_failure_never_gains_regulatory_content(self) -> None:
        result = _pipeline(None).analyze_address("Missing Street")

        self.assertEqual(result["status"], "address_not_found")
        self.assertEqual(result["residential_uses"], [])
        self.assertEqual(result["special_pathways"], [])
        self.assertIsNone(result["regulations"])
        self.assertEqual(result["not_evaluated_topics"], [])
        self.assertEqual(result["conflicts"], {})
        self.assertEqual(result["sources"]["citations"], {})

    def test_results_are_repeatable_and_defensive(self) -> None:
        pipeline = _pipeline("R3")
        first = pipeline.analyze_address("1 Test Street")
        second = pipeline.analyze_address("1 Test Street")
        self.assertEqual(_canonical(first), _canonical(second))

        first["regulations"].clear()
        first["residential_uses"].clear()
        third = pipeline.analyze_address("1 Test Street")
        self.assertEqual(len(third["regulations"]), 10)
        self.assertEqual(len(third["residential_uses"]), 2)


if __name__ == "__main__":
    unittest.main()
