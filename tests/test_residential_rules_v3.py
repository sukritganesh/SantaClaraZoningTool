"""Domain and mutation tests for Santa Clara residential ruleset v3."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

from scripts.validate_residential_rules_v3 import (
    DEFAULT_GIS_FIXTURES,
    DEFAULT_RULESET,
    DEFAULT_SCHEMA,
    TARGET_ZONES,
    validate_gis_fixture_contract,
    validate_ruleset,
)


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class ResidentialRulesetV3DomainTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ruleset = load_json(DEFAULT_RULESET)
        cls.schema = load_json(DEFAULT_SCHEMA)

    def changed(self) -> dict[str, Any]:
        return copy.deepcopy(self.ruleset)

    def errors(
        self,
        changed: dict[str, Any],
        *,
        verify_source_files: bool = False,
        require_runtime_eligible: bool = False,
    ) -> list[str]:
        return validate_ruleset(
            changed,
            schema=self.schema,
            repo_root=ROOT,
            verify_source_files=verify_source_files,
            require_runtime_eligible=require_runtime_eligible,
        )

    def assert_domain_error(
        self,
        changed: dict[str, Any],
        expected: str,
        *,
        verify_source_files: bool = False,
        require_runtime_eligible: bool = False,
    ) -> None:
        errors = self.errors(
            changed,
            verify_source_files=verify_source_files,
            require_runtime_eligible=require_runtime_eligible,
        )
        self.assertTrue(
            any(expected in error for error in errors),
            f"Expected {expected!r} in {errors!r}",
        )

    def profile_rule(self, zone: str, capability: str) -> dict[str, Any]:
        return self.ruleset["zones"][zone]["analysis_profiles"]["single_family"][
            "regulations"
        ][capability]

    def test_canonical_partial_candidate_passes_domain_and_source_validation(self) -> None:
        self.assertEqual(self.errors(self.ruleset, verify_source_files=True), [])

    def test_partial_candidate_fails_closed_runtime_gate(self) -> None:
        errors = self.errors(self.ruleset, require_runtime_eligible=True)
        self.assertTrue(any("missing exact target zones" in item for item in errors))
        self.assertTrue(any("requires status approved_for_runtime" in item for item in errors))
        self.assertTrue(any("unapproved rules" in item for item in errors))

    def test_runtime_gate_requires_every_exact_target_zone(self) -> None:
        self.assertEqual(set(self.ruleset["zones"]), {"R1-6L", "R1-8L"})
        self.assertEqual(
            TARGET_ZONES - set(self.ruleset["zones"]),
            {"R2", "R3", "R4", "R5", "R6", "PH-R5", "UV", "VR", "UC", "HDF"},
        )

    def test_gis_fixture_contract_preserves_zero_count_and_excluded_zones(self) -> None:
        inventory = load_json(DEFAULT_GIS_FIXTURES)
        self.assertEqual(validate_gis_fixture_contract(inventory), [])

        changed = copy.deepcopy(inventory)
        changed["synthetic_zero_count_fixtures"][0]["parcel_source_count"] = 1
        errors = validate_gis_fixture_contract(changed)
        self.assertTrue(any("parcel count must be zero" in item for item in errors))

        changed = copy.deepcopy(inventory)
        changed["synthetic_excluded_designation_fixtures"][0][
            "must_not_normalize_to"
        ] = "R1-8L"
        errors = validate_gis_fixture_contract(changed)
        self.assertTrue(any("wrong no-normalize target" in item for item in errors))

    def test_rejects_unexpected_exact_zone_and_wrong_zone_matrix(self) -> None:
        changed = self.changed()
        changed["zones"]["R1-6LHT"] = changed["zones"].pop("R1-6L")
        self.assert_domain_error(changed, "unsupported exact designations")

        changed = self.changed()
        changed["zones"]["R1-6L"]["use_permissions"][
            "use.multifamily_dwelling"
        ]["requirement"]["code"] = "permitted_by_right"
        self.assert_domain_error(changed, "source-matrix status not_listed")

    def test_not_listed_cannot_be_replaced_with_a_prohibition(self) -> None:
        changed = self.changed()
        changed["zones"]["R1-6L"]["use_permissions"][
            "use.multifamily_dwelling"
        ]["requirement"]["code"] = "prohibited"
        self.assertTrue(self.errors(changed))

    def test_rejects_profile_binding_and_rule_identity_drift(self) -> None:
        changed = self.changed()
        changed["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "workflow_family"
        ] = "multifamily"
        self.assert_domain_error(changed, "workflow_family must be single_family")

        changed = self.changed()
        changed["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["setback.rear"]["rule_id"] = "us.ca.santa_clara.r1-6l.setback.rear"
        self.assert_domain_error(changed, ".rule_id must be")

    def test_rejects_missing_profile_capability_and_wrong_lot_context(self) -> None:
        changed = self.changed()
        changed["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "regulations"
        ].pop("setback.rear")
        self.assert_domain_error(changed, "is missing capabilities")

        changed = self.changed()
        changed["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["setback.street_side"]["applicability"]["lot_context"] = "all"
        self.assert_domain_error(changed, "lot_context must be corner")

    def test_rejects_capability_incompatible_requirement_kinds(self) -> None:
        changed = self.changed()
        changed["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["setback.rear"]["requirement"] = {
            "kind": "no_maximum_listed",
            "reason_code": "controlling_base_table_has_no_maximum",
            "explanation": "Test mutation.",
            "source_refs": ["r1-standards-table"],
        }
        self.assert_domain_error(changed, "setback-compatible requirement")

        changed = self.changed()
        changed["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["approval.zoning_clearance"]["requirement"] = {
            "kind": "maximum_quantity",
            "value": {"number": 1, "unit": "stories"},
            "source_refs": ["zoning-clearance"],
        }
        self.assert_domain_error(changed, "approval-compatible requirement")

        changed = self.changed()
        changed["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["standard.maximum_structure_coverage"]["requirement"] = {
            "kind": "faa_controlled",
            "controlling_authority": "FAA",
            "reason_code": "controlling_source_defers_to_faa",
            "explanation": "Test-only incompatible mutation.",
            "source_refs": ["r1-standards-table"],
        }
        self.assert_domain_error(changed, "maximum-compatible requirement")

    def test_rejects_wrong_units_ranges_and_setback_values(self) -> None:
        changed = self.changed()
        changed["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["standard.maximum_stories"]["requirement"]["value"]["number"] = 2.5
        self.assert_domain_error(changed, "story maximum must be an integer")

        changed = self.changed()
        changed["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["standard.maximum_structure_coverage"]["requirement"]["value"]["number"] = 101
        self.assert_domain_error(changed, "cannot exceed 100 percent")

        changed = self.changed()
        changed["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["setback.rear"]["requirement"]["base"]["value"]["number"] = 0
        self.assert_domain_error(changed, "must be greater than zero")

    def test_rejects_dangling_source_topic_exception_and_pathway_references(self) -> None:
        changed = self.changed()
        changed["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["standard.maximum_stories"]["requirement"]["source_refs"] = ["missing"]
        self.assert_domain_error(changed, "unknown source refs")

        changed = self.changed()
        changed["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "not_evaluated_topic_ids"
        ].append("missing_topic")
        self.assert_domain_error(changed, "unknown not-evaluated topics")

        changed = self.changed()
        changed["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["setback.rear"]["exception_family_ids"].append("missing_exception")
        self.assert_domain_error(changed, "unknown exception families")

        changed = self.changed()
        changed["zones"]["R1-6L"]["use_permissions"][
            "use.two_family_dwelling"
        ]["special_pathway_id"] = None
        self.assert_domain_error(changed, "special_pathway_id must be")

    def test_rejects_modified_source_checksum(self) -> None:
        changed = self.changed()
        changed["shared"]["source_documents"]["approved-r1-ruleset-v2"][
            "sha256"
        ] = "0" * 64
        self.assert_domain_error(
            changed,
            "checksum does not match",
            verify_source_files=True,
        )

    def test_candidate_cannot_contain_approved_records(self) -> None:
        changed = self.changed()
        changed["zones"]["R1-6L"]["use_permissions"][
            "use.single_family_dwelling"
        ]["approved_for_ruleset"] = True
        self.assert_domain_error(changed, "candidate ruleset contains records approved")

    def test_rejects_conflict_drift_and_broken_links(self) -> None:
        conflict_id = "conflict-r1-8l-corner-side-first"
        changed = self.changed()
        changed["conflicts"][conflict_id]["resolution"]["selected_value"]["number"] = 14
        self.assert_domain_error(changed, "selected value differs from its assertion")

        changed = self.changed()
        changed["zones"]["R1-8L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["setback.street_side"]["conflict_id"] = None
        # The conflict still points to a rule, so the bidirectional invariant must fail.
        errors = self.errors(changed)
        self.assertTrue(errors)

        changed = self.changed()
        changed["zones"]["R1-8L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["setback.street_side"]["requirement"]["base"]["value"]["number"] = 14
        self.assert_domain_error(changed, "selected value differs from")

    def test_unresolved_conflict_is_representable_but_not_runtime_eligible(self) -> None:
        changed = self.changed()
        conflict_id = "conflict-r1-8l-corner-side-first"
        conflict = changed["conflicts"][conflict_id]
        for assertion in conflict["assertions"]:
            assertion["disposition"] = "unresolved"
        conflict["resolution"] = {
            "selected_assertion_id": None,
            "selected_value": None,
            "rationale": "No approved precedence decision resolves this test mutation.",
            "decision_source": None,
            "decision_date": None,
            "status": "review_required_unresolved",
            "re_review_triggers": ["Human source review"],
        }
        rule = changed["zones"]["R1-8L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["setback.street_side"]
        rule["requirement"] = {
            "kind": "review_required",
            "reason_code": "unresolved_source_conflict",
            "explanation": "Conflicting source assertions require review.",
            "source_refs": ["r1-standards-table", "r1-8l-corner-side"],
            "review_triggers": ["Approved precedence decision"],
        }
        rule["validation_status"] = "verified_with_conditions"

        self.assertEqual(self.errors(changed), [])
        runtime_errors = self.errors(changed, require_runtime_eligible=True)
        self.assertTrue(any("unresolved conflicts" in item for item in runtime_errors))


if __name__ == "__main__":
    unittest.main()
