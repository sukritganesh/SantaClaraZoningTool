"""Regression tests for the first Santa Clara R1 ruleset."""

from __future__ import annotations

import copy
import unittest

from scripts.validate_r1_rules import DEFAULT_RULESET, load_json, validate_ruleset


class R1RulesetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ruleset = load_json(DEFAULT_RULESET)
        cls.rules_by_id = {rule["rule_id"]: rule for rule in cls.ruleset["rules"]}

    def assert_number(self, rule_id: str, number: int, unit: str) -> None:
        self.assertEqual(
            self.rules_by_id[rule_id]["value"],
            {"kind": "number", "number": number, "unit": unit},
        )

    def test_contract_and_cross_references_are_valid(self) -> None:
        self.assertEqual(validate_ruleset(self.ruleset), [])

    def test_supported_zones_are_exact(self) -> None:
        self.assertEqual(set(self.ruleset["supported_zones"]), {"R1-6L", "R1-8L"})

    def test_shared_base_values(self) -> None:
        self.assert_number("standard-max-structure-coverage", 40, "percent")
        self.assert_number("standard-max-primary-height", 25, "ft")
        self.assert_number("standard-max-stories", 2, "stories")
        self.assert_number("standard-front-setback-first", 20, "ft")
        self.assert_number("standard-front-setback-second", 25, "ft")
        self.assert_number("standard-corner-side-second", 15, "ft")
        self.assert_number("standard-rear-setback", 20, "ft")

    def test_r1_6l_side_values(self) -> None:
        self.assert_number("standard-interior-side-first-r1-6l", 5, "ft")
        self.assert_number("standard-interior-side-second-r1-6l", 10, "ft")
        self.assert_number("standard-corner-side-first-r1-6l", 10, "ft")

    def test_r1_8l_paired_side_yards_remain_paired(self) -> None:
        self.assertEqual(
            self.rules_by_id["standard-interior-side-first-r1-8l"]["value"],
            {
                "kind": "paired_numbers",
                "numbers": [6, 9],
                "unit": "ft",
                "relationship": "required_paired_yards",
            },
        )
        self.assertEqual(
            self.rules_by_id["standard-interior-side-second-r1-8l"]["value"],
            {
                "kind": "paired_numbers",
                "numbers": [11, 14],
                "unit": "ft",
                "relationship": "required_paired_yards",
            },
        )

    def test_r1_8l_corner_conflict_preserves_both_assertions(self) -> None:
        self.assert_number("standard-corner-side-first-r1-8l", 15, "ft")
        conflict = self.ruleset["conflicts"][0]
        assertions = {
            assertion["value"]["number"]: assertion["disposition"]
            for assertion in conflict["assertions"]
        }
        self.assertEqual(
            assertions,
            {10: "not_selected_for_prototype", 15: "selected_for_prototype"},
        )
        self.assertEqual(
            conflict["resolution"]["status"],
            "project_resolved_pending_official_clarification",
        )

    def test_permission_does_not_erase_approval_requirements(self) -> None:
        self.assertEqual(
            self.rules_by_id["use-single-family-dwelling"]["value"]["code"],
            "permitted_by_right",
        )
        self.assertEqual(
            self.rules_by_id["approval-zoning-clearance"]["value"]["code"],
            "required",
        )
        self.assertEqual(
            self.rules_by_id["approval-architectural-review"]["value"]["code"],
            "required",
        )

    def test_deferred_subjects_are_not_encoded_as_rules(self) -> None:
        standard_codes = {rule["standard_code"] for rule in self.ruleset["rules"]}
        self.assertTrue(
            {
                "density",
                "minimum_parcel_area",
                "minimum_street_frontage",
                "driveway_approach_length",
                "daylight_plane",
            }.isdisjoint(standard_codes)
        )

    def test_validator_rejects_conflict_value_drift(self) -> None:
        changed = copy.deepcopy(self.ruleset)
        changed_rule = next(
            rule
            for rule in changed["rules"]
            if rule["rule_id"] == "standard-corner-side-first-r1-8l"
        )
        changed_rule["value"]["number"] = 10
        errors = validate_ruleset(changed)
        self.assertTrue(any("selected value differs" in error for error in errors))

    def test_validator_enforces_required_fields_and_enums(self) -> None:
        mutations = {
            "missing rule label": lambda data: data["rules"][0].pop("label"),
            "invalid rule category": lambda data: data["rules"][0].__setitem__(
                "category", "invented_category"
            ),
            "invalid applicability story": lambda data: data["rules"][0][
                "applicability"
            ].__setitem__("story", "third"),
            "missing citation locator": lambda data: data["citations"][0].pop(
                "locator"
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                changed = copy.deepcopy(self.ruleset)
                mutate(changed)
                self.assertTrue(validate_ruleset(changed))

    def test_validator_reports_malformed_array_elements(self) -> None:
        changed = copy.deepcopy(self.ruleset)
        changed["supported_zones"] = [{"bad": "type"}]
        errors = validate_ruleset(changed)
        self.assertTrue(errors)
        self.assertTrue(any("supported_zones" in error for error in errors))

    def test_validator_rejects_multiple_selected_assertions(self) -> None:
        changed = copy.deepcopy(self.ruleset)
        changed["conflicts"][0]["assertions"][0][
            "disposition"
        ] = "selected_for_prototype"
        errors = validate_ruleset(changed)
        self.assertTrue(any("exactly one" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
