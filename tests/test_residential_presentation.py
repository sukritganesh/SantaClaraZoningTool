"""Residential common-zone presentation contract tests."""

from __future__ import annotations

import copy
import json
import unittest

from santa_clara_zoning import PresentationIntegrityError
from santa_clara_zoning.residential_presentation import (
    RESIDENTIAL_PRESENTATION_CONTRACT_VERSION,
    present_residential_integrity_error,
    present_residential_summary,
)

from tests.test_residential_summary import _pipeline


def _view(zone: str) -> dict:
    return present_residential_summary(
        _pipeline(zone).analyze_address("1 Test Street")
    )


def _canonical(value: dict) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


class ResidentialPresentationSuccessTest(unittest.TestCase):
    def test_r2_maps_common_standards_and_all_listed_uses(self) -> None:
        result = _view("R2")

        self.assertEqual(
            result["presentation_contract_version"],
            RESIDENTIAL_PRESENTATION_CONTRACT_VERSION,
        )
        self.assertEqual(result["kind"], "success")
        self.assertEqual(result["property"]["zone"], "R2")
        self.assertEqual(
            [item["label"] for item in result["use_permissions"]],
            [
                "Single-family dwelling",
                "Two-family dwelling",
                "Multifamily dwelling",
            ],
        )
        self.assertEqual(len(result["approvals"]), 2)
        self.assertEqual(len(result["key_standards"]), 4)
        self.assertEqual(len(result["setbacks"]), 4)
        self.assertIn("share the supported base-zone standards", result["overview"]["summary"])
        self.assertNotIn("selection", result["overview"]["summary"].lower())

        density = next(
            item
            for item in result["key_standards"]
            if item["capability_id"] == "standard.gross_residential_density"
        )
        self.assertEqual(
            density["requirement"],
            {
                "kind": "quantity_range",
                "minimum": 8,
                "maximum": 19,
                "unit": "dwelling_units_per_acre",
            },
        )
        objective_design = next(
            item
            for item in result["not_evaluated"]
            if item["topic_id"] == "objective_design_standards"
        )
        self.assertTrue(objective_design["is_conditional"])
        self.assertEqual(
            objective_design["applies_to_labels"],
            ["Multifamily dwelling"],
        )

    def test_all_current_requirement_shapes_are_preserved(self) -> None:
        r3 = _view("R3")
        r3_coverage = next(
            item
            for item in r3["key_standards"]
            if item["capability_id"] == "standard.maximum_structure_coverage"
        )["requirement"]
        self.assertEqual(r3_coverage["kind"], "lot_area_tiered_maximum")
        self.assertEqual(r3_coverage["threshold"], {"number": 10000, "unit": "sq_ft"})
        self.assertEqual(r3_coverage["below_threshold"]["value"]["number"], 60)
        self.assertEqual(
            r3_coverage["at_or_above_threshold"]["kind"],
            "no_maximum_listed",
        )

        r5 = _view("R5")
        r5_coverage = next(
            item
            for item in r5["key_standards"]
            if item["capability_id"] == "standard.maximum_structure_coverage"
        )["requirement"]
        self.assertEqual(r5_coverage["kind"], "no_maximum_listed")
        density_conflict = next(
            warning
            for warning in r5["warnings"]
            if warning["kind"] == "source_conflict"
        )
        self.assertEqual(
            density_conflict["resolution"]["presented_value"],
            {
                "kind": "quantity_range",
                "minimum": 51,
                "maximum": 100,
                "unit": "dwelling_units_per_acre",
            },
        )

        uc = _view("UC")
        height = next(
            item
            for item in uc["key_standards"]
            if item["capability_id"]
            == "standard.maximum_primary_structure_height"
        )["requirement"]
        self.assertEqual(height["kind"], "faa_controlled")
        self.assertEqual(height["controlling_authority"], "FAA")

        ph = _view("PH-R5")
        rear = next(
            item
            for item in ph["setbacks"]
            if item["capability_id"] == "setback.rear"
        )["requirement"]
        self.assertEqual(rear["kind"], "plan_dependent")
        self.assertTrue(rear["required_sources_or_facts"])

        r1 = _view("R1-8L")
        interior = next(
            item
            for item in r1["setbacks"]
            if item["capability_id"] == "setback.interior_side"
        )["requirement"]
        self.assertEqual(interior["base"]["value"]["kind"], "paired_distances")
        r1_conflict = next(
            warning
            for warning in r1["warnings"]
            if warning["kind"] == "source_conflict"
        )
        self.assertEqual(
            r1_conflict["resolution"]["presented_value"],
            {"kind": "distance", "number": 15, "unit": "ft"},
        )

    def test_r1_special_pathway_is_a_separate_not_evaluated_card(self) -> None:
        result = _view("R1-6L")

        self.assertEqual(len(result["use_permissions"]), 1)
        self.assertEqual(len(result["special_pathways"]), 1)
        pathway = result["special_pathways"][0]
        self.assertEqual(pathway["status_code"], "not_evaluated")
        self.assertTrue(pathway["topics"])
        self.assertNotIn("requirement", pathway)

    def test_every_displayed_citation_has_one_source_receipt(self) -> None:
        result = _view("PH-R5")
        source_ids = {
            item["citation_id"]
            for item in result["sources"]
            if item["kind"] == "regulatory_citation"
        }
        for section in (
            "use_permissions",
            "special_pathways",
            "approvals",
            "key_standards",
            "setbacks",
            "not_evaluated",
        ):
            for item in result[section]:
                self.assertLessEqual(set(item["citation_ids"]), source_ids)

    def test_output_is_repeatable_and_defensive(self) -> None:
        source = _pipeline("R4").analyze_address("1 Test Street")
        original = copy.deepcopy(source)
        first = present_residential_summary(source)
        self.assertEqual(source, original)
        first["key_standards"][0]["conditions"].append("changed")

        second = present_residential_summary(source)
        third = present_residential_summary(source)
        self.assertNotIn("changed", second["key_standards"][0]["conditions"])
        self.assertEqual(_canonical(second), _canonical(third))


class ResidentialPresentationOutcomeTest(unittest.TestCase):
    def test_lookup_failure_has_no_regulatory_cards(self) -> None:
        source = _pipeline(None).analyze_address("Missing Street")
        result = present_residential_summary(source)

        self.assertEqual(result["kind"], "lookup_failure")
        for section in (
            "use_permissions",
            "special_pathways",
            "approvals",
            "key_standards",
            "setbacks",
            "warnings",
            "not_evaluated",
            "sources",
        ):
            self.assertEqual(result[section], [])
        self.assertEqual(result["versions"]["ruleset"], "2026-07-19.5")

    def test_known_integrity_error_has_safe_product_level_view(self) -> None:
        error = PresentationIntegrityError("fixture_error", "private detail")
        result = present_residential_integrity_error(error)

        self.assertEqual(result["kind"], "system_error")
        self.assertEqual(result["source_reason_code"], "fixture_error")
        self.assertNotIn("private detail", result["overview"]["summary"])
        self.assertEqual(
            result["presentation_contract_version"],
            RESIDENTIAL_PRESENTATION_CONTRACT_VERSION,
        )
        with self.assertRaises(TypeError):
            present_residential_integrity_error(ValueError("unexpected"))


class ResidentialPresentationIntegrityTest(unittest.TestCase):
    def test_unknown_capability_and_topic_profile_fail_closed(self) -> None:
        unknown = _pipeline("R2").analyze_address("1 Test Street")
        unknown["regulations"]["local.example.custom"] = copy.deepcopy(
            unknown["regulations"]["setback.rear"]
        )
        with self.assertRaises(PresentationIntegrityError) as capability_error:
            present_residential_summary(unknown)
        self.assertEqual(
            capability_error.exception.reason_code,
            "unsupported_capability_set",
        )

        topic = _pipeline("R2").analyze_address("1 Test Street")
        topic["not_evaluated_topics"][0]["applies_to_selection_ids"] = [
            "unknown_profile"
        ]
        with self.assertRaises(PresentationIntegrityError) as topic_error:
            present_residential_summary(topic)
        self.assertEqual(
            topic_error.exception.reason_code,
            "invalid_topic_applicability",
        )


if __name__ == "__main__":
    unittest.main()
