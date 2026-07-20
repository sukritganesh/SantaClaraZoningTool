"""Executable fixture and mutation tests for residential result contract 2.0.0."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from scripts.validate_residential_result_contract import (
    DEFAULT_FIXTURES,
    DEFAULT_SCHEMA,
    load_fixture_results,
    validate_result,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class ResidentialResultContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(DEFAULT_SCHEMA)
        Draft202012Validator.check_schema(cls.schema)
        cls.results = dict(load_fixture_results(DEFAULT_FIXTURES))

    def changed(self, fixture_id: str) -> dict[str, Any]:
        return copy.deepcopy(self.results[fixture_id])

    def assert_contract_error(self, result: dict[str, Any], expected: str) -> None:
        errors = validate_result(result, schema=self.schema)
        self.assertTrue(
            any(expected in error for error in errors),
            f"Expected {expected!r} in {errors!r}",
        )

    def test_all_eight_controlled_status_fixtures_validate(self) -> None:
        self.assertEqual(
            {result["status"] for result in self.results.values()},
            {
                "residential_zone_found",
                "residential_standards_found",
                "analysis_not_evaluated",
                "selection_not_available",
                "outside_supported_residential_snapshot",
                "address_not_found",
                "address_ambiguous",
                "review_required",
            },
        )
        for fixture_id, result in self.results.items():
            with self.subTest(fixture_id=fixture_id):
                self.assertEqual(validate_result(result, schema=self.schema), [])

    def test_zone_found_lists_choices_without_attaching_standards(self) -> None:
        result = self.results["zone-found-selection-required"]
        self.assertTrue(result["available_selections"])
        self.assertIsNone(result["selection"])
        self.assertIsNone(result["regulations"])
        self.assertEqual(result["not_evaluated_topics"], {})

    def test_success_binds_one_exact_profile_and_complete_rules(self) -> None:
        result = self.results["selected-profile-standards-found"]
        self.assertEqual(result["requested_selection_id"], "single_family")
        self.assertEqual(
            result["selection"],
            {
                "selection_id": "single_family",
                "selection_kind": "profile",
                "profile_id": "single_family",
                "workflow_family": "single_family",
                "legal_use_capability_id": "use.single_family_dwelling",
                "primary_structure_type": "single_family_primary_structure",
            },
        )
        self.assertEqual(len(result["regulations"]), 9)
        self.assertIn("conflict-r1-8l-corner-side-first", result["conflicts"])
        self.assertTrue(result["sources"]["citations"])
        self.assertTrue(result["sources"]["source_documents"])

    def test_special_pathway_returns_limitations_without_ordinary_standards(self) -> None:
        result = self.results["selected-special-pathway-not-evaluated"]
        self.assertEqual(result["selection"]["selection_kind"], "special_pathway")
        self.assertIsNone(result["selection"]["primary_structure_type"])
        self.assertIsNone(result["regulations"])
        self.assertIn(
            "r1_chapter_18_24_dimensional_analysis",
            result["not_evaluated_topics"],
        )

    def test_unavailable_selection_is_not_returned_as_a_selected_profile(self) -> None:
        result = self.results["profile-selection-not-available"]
        available = {item["selection_id"] for item in result["available_selections"]}
        self.assertNotIn(result["requested_selection_id"], available)
        self.assertIsNone(result["selection"])
        self.assertIsNone(result["regulations"])

    def test_no_regulations_statuses_never_carry_rules(self) -> None:
        for fixture_id, result in self.results.items():
            if result["status"] == "residential_standards_found":
                continue
            with self.subTest(fixture_id=fixture_id):
                self.assertIsNone(result["regulations"])

    def test_rejects_reason_status_mismatch(self) -> None:
        changed = self.changed("zone-found-selection-required")
        changed["reason_code"] = "selected_profile_retrieved"
        self.assert_contract_error(changed, "selection_required")

    def test_rejects_mismatched_or_unavailable_selection_identity(self) -> None:
        changed = self.changed("selected-profile-standards-found")
        changed["selection"]["selection_id"] = "multifamily"
        self.assert_contract_error(changed, "differs from requested_selection_id")

        changed = self.changed("profile-selection-not-available")
        changed["requested_selection_id"] = "single_family"
        self.assert_contract_error(changed, "names an available selection")

    def test_rejects_incomplete_success_and_dangling_source_closure(self) -> None:
        changed = self.changed("selected-profile-standards-found")
        changed["regulations"].pop("setback.rear")
        self.assert_contract_error(changed, "complete profile capability set")

        changed = self.changed("selected-profile-standards-found")
        changed["sources"]["citations"].pop("r1-standards-table")
        self.assert_contract_error(changed, "outside its closure")

    def test_failure_status_rejects_attached_regulations(self) -> None:
        changed = self.changed("address-not-found")
        changed["regulations"] = copy.deepcopy(
            self.results["selected-profile-standards-found"]["regulations"]
        )
        self.assertTrue(validate_result(changed, schema=self.schema))

    def test_outside_snapshot_cannot_use_an_exact_target_zone(self) -> None:
        changed = self.changed("outside-exact-residential-snapshot")
        changed["property"]["zone"] = "R1-6L"
        self.assert_contract_error(changed, "uses a target residential zone")


if __name__ == "__main__":
    unittest.main()
