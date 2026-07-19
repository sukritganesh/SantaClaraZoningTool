"""Approved-ruleset fixtures and mutations for result contract 2.1.0."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from scripts.validate_residential_result_contract_v2_1 import (
    DEFAULT_FIXTURES,
    DEFAULT_RULESET,
    DEFAULT_SCHEMA,
    load_fixture_results,
    validate_result,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class ResidentialResultContractV21Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(DEFAULT_SCHEMA)
        Draft202012Validator.check_schema(cls.schema)
        cls.ruleset = load_json(DEFAULT_RULESET)
        cls.results = dict(load_fixture_results(DEFAULT_FIXTURES))

    def changed(self, fixture_id: str) -> dict[str, Any]:
        return copy.deepcopy(self.results[fixture_id])

    def assert_contract_error(self, result: dict[str, Any], expected: str) -> None:
        errors = validate_result(
            result,
            schema=self.schema,
            ruleset=self.ruleset,
        )
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
                self.assertEqual(
                    validate_result(
                        result,
                        schema=self.schema,
                        ruleset=self.ruleset,
                    ),
                    [],
                )

    def test_every_result_pins_all_five_version_identities(self) -> None:
        for fixture_id, result in self.results.items():
            with self.subTest(fixture_id=fixture_id):
                self.assertEqual(result["contract_version"], "2.1.0")
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

    def test_zone_found_lists_the_exact_r2_profile_choices(self) -> None:
        result = self.results["zone-found-selection-required"]
        self.assertEqual(
            [item["selection_id"] for item in result["available_selections"]],
            ["single_family", "two_family", "multifamily"],
        )
        self.assertIsNone(result["selection"])
        self.assertIsNone(result["use_permission"])
        self.assertIsNone(result["regulations"])

    def test_multifamily_success_uses_the_complete_approved_ph_r5_branch(self) -> None:
        result = self.results["selected-profile-standards-found"]
        self.assertEqual(result["property"]["zone"], "PH-R5")
        self.assertEqual(
            result["selection"],
            {
                "selection_id": "multifamily",
                "selection_kind": "profile",
                "profile_id": "multifamily",
                "workflow_family": "multifamily",
                "legal_use_capability_id": "use.multifamily_dwelling",
                "primary_structure_type": "multifamily_primary_structure",
            },
        )
        self.assertEqual(len(result["regulations"]), 10)
        self.assertIn(
            "standard.gross_residential_density",
            result["regulations"],
        )
        self.assertEqual(
            result["use_permission"]["requirement"]["code"],
            "permitted_by_right",
        )
        self.assertNotIn("approved_for_ruleset", result["use_permission"])
        self.assertTrue(
            all(
                "approved_for_ruleset" not in rule
                for rule in result["regulations"].values()
            )
        )
        self.assertIn(
            "conflict-ph-r5-gross-residential-density",
            result["conflicts"],
        )
        self.assertTrue(
            set(result["use_permission"]["requirement"]["source_refs"])
            <= set(result["sources"]["citations"])
        )

    def test_special_pathway_carries_its_permission_and_limitations(self) -> None:
        result = self.results["selected-special-pathway-not-evaluated"]
        self.assertEqual(result["selection"]["selection_kind"], "special_pathway")
        self.assertEqual(
            result["use_permission"]["special_pathway_id"],
            "r1_chapter_18_24_two_unit",
        )
        self.assertEqual(
            result["use_permission"]["requirement"]["code"],
            "permitted_by_right",
        )
        self.assertIsNone(result["regulations"])
        self.assertIn(
            "r1_chapter_18_24_dimensional_analysis",
            result["not_evaluated_topics"],
        )

    def test_known_unavailable_profile_carries_not_listed_permission(self) -> None:
        result = self.results["profile-selection-not-available"]
        self.assertEqual(result["property"]["zone"], "R3")
        self.assertEqual(result["requested_selection_id"], "single_family")
        self.assertNotIn(
            "single_family",
            {item["selection_id"] for item in result["available_selections"]},
        )
        self.assertEqual(
            result["use_permission"]["requirement"]["code"],
            "not_listed",
        )
        self.assertIsNone(result["selection"])
        self.assertIsNone(result["regulations"])

    def test_outside_snapshot_preserves_only_address_evidence(self) -> None:
        result = self.results["outside-exact-residential-snapshot"]
        self.assertEqual(
            result["property"],
            {
                "matched_address": (
                    "Contract fixture: outside-exact-residential-snapshot"
                ),
                "parcel_id": None,
                "zone": None,
            },
        )
        self.assertIsNone(result["use_permission"])

    def test_empty_address_is_valid_only_for_address_not_found(self) -> None:
        not_found = self.results["address-not-found"]
        self.assertEqual(not_found["query"]["address"], "")
        self.assertEqual(
            validate_result(
                not_found,
                schema=self.schema,
                ruleset=self.ruleset,
            ),
            [],
        )

        changed = self.changed("zone-found-selection-required")
        changed["query"]["address"] = ""
        self.assertTrue(
            validate_result(
                changed,
                schema=self.schema,
                ruleset=self.ruleset,
            )
        )

    def test_no_regulations_statuses_never_carry_rules(self) -> None:
        for fixture_id, result in self.results.items():
            if result["status"] == "residential_standards_found":
                continue
            with self.subTest(fixture_id=fixture_id):
                self.assertIsNone(result["regulations"])

    def test_use_permission_is_limited_to_selection_outcomes(self) -> None:
        expected_statuses = {
            "residential_standards_found",
            "analysis_not_evaluated",
            "selection_not_available",
        }
        for fixture_id, result in self.results.items():
            with self.subTest(fixture_id=fixture_id):
                self.assertEqual(
                    result["use_permission"] is not None,
                    result["status"] in expected_statuses,
                )

    def test_rejects_a_permission_from_another_selected_branch(self) -> None:
        changed = self.changed("selected-profile-standards-found")
        changed["use_permission"] = copy.deepcopy(
            self.results["selected-special-pathway-not-evaluated"][
                "use_permission"
            ]
        )
        self.assert_contract_error(
            changed,
            "use_permission differs from the approved selected use",
        )

    def test_rejects_incomplete_profile_and_missing_permission_source(self) -> None:
        changed = self.changed("selected-profile-standards-found")
        changed["regulations"].pop("standard.gross_residential_density")
        self.assert_contract_error(changed, "complete ten-capability profile")

        changed = self.changed("selected-profile-standards-found")
        changed["sources"]["citations"].pop("patrick-henry-title18-use-table")
        self.assert_contract_error(
            changed,
            "provenance closure differs from the selected branch",
        )

    def test_unknown_profile_identity_fails_closed_without_guessing(self) -> None:
        changed = self.changed("profile-selection-not-available")
        changed["requested_selection_id"] = "nearby_multifamily_profile"
        self.assert_contract_error(
            changed,
            "unavailable selection is not a known profile identity",
        )

    def test_rejects_branch_data_and_versions_not_from_ruleset(self) -> None:
        changed = self.changed("zone-found-selection-required")
        changed["available_selections"].pop()
        self.assert_contract_error(
            changed,
            "available selections differ from the approved zone",
        )

        changed = self.changed("selected-special-pathway-not-evaluated")
        changed["not_evaluated_topics"].pop(
            "r1_chapter_18_24_dimensional_analysis"
        )
        self.assert_contract_error(
            changed,
            "not-evaluated topics differ from the selected branch",
        )

        changed = self.changed("selected-profile-standards-found")
        changed["conflicts"] = {}
        self.assert_contract_error(
            changed,
            "conflicts differ from the selected branch",
        )

        changed = self.changed("selected-profile-standards-found")
        changed["versions"]["ruleset"] = "2026-07-19.4"
        self.assert_contract_error(
            changed,
            "result ruleset version differs from its approved ruleset",
        )

    def test_rejects_guessed_outside_zone_or_nullable_runtime_version(self) -> None:
        changed = self.changed("outside-exact-residential-snapshot")
        changed["property"]["parcel_id"] = "guessed-parcel"
        changed["property"]["zone"] = "R1-6LHT"
        self.assertTrue(
            validate_result(
                changed,
                schema=self.schema,
                ruleset=self.ruleset,
            )
        )

        changed = self.changed("address-ambiguous")
        changed["versions"]["residential_gis_snapshot"] = None
        self.assertTrue(
            validate_result(
                changed,
                schema=self.schema,
                ruleset=self.ruleset,
            )
        )

    def test_failure_status_rejects_attached_permission_or_regulations(self) -> None:
        changed = self.changed("address-not-found")
        success = self.results["selected-profile-standards-found"]
        changed["use_permission"] = copy.deepcopy(success["use_permission"])
        changed["regulations"] = copy.deepcopy(success["regulations"])
        self.assertTrue(
            validate_result(
                changed,
                schema=self.schema,
                ruleset=self.ruleset,
            )
        )


if __name__ == "__main__":
    unittest.main()
