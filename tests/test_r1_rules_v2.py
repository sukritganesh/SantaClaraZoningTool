"""Domain and mutation tests for the Santa Clara R1 ruleset v2 candidate."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

from scripts.validate_r1_rules_v2 import (
    DEFAULT_CROSSWALK,
    DEFAULT_RULESET,
    DEFAULT_SCHEMA,
    DEFAULT_V1_RULESET,
    runtime_eligibility_errors,
    validate_migration,
    validate_ruleset,
)


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class RulesetV2DomainTest(unittest.TestCase):
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
    ) -> list[str]:
        return validate_ruleset(
            changed,
            schema=self.schema,
            repo_root=ROOT,
            verify_source_files=verify_source_files,
        )

    def assert_domain_error(
        self,
        changed: dict[str, Any],
        expected: str,
        *,
        verify_source_files: bool = False,
    ) -> None:
        errors = self.errors(
            changed,
            verify_source_files=verify_source_files,
        )
        self.assertTrue(
            any(expected in error for error in errors),
            f"Expected {expected!r} in {errors!r}",
        )

    def regulation(self, zone: str, capability: str) -> dict[str, Any]:
        return self.ruleset["zones"][zone]["regulations"][capability]

    def test_canonical_candidate_passes_domain_and_source_validation(self) -> None:
        self.assertEqual(
            self.errors(self.ruleset, verify_source_files=True),
            [],
        )

    def test_candidate_is_valid_but_not_runtime_eligible(self) -> None:
        domain_errors = self.errors(self.ruleset)
        eligibility = runtime_eligibility_errors(
            self.ruleset,
            domain_errors=domain_errors,
        )
        self.assertEqual(domain_errors, [])
        self.assertIn("ruleset status is not approved_for_prototype", eligibility)
        self.assertIn("ruleset does not have a valid approved_on date", eligibility)

    def test_simulated_approved_ruleset_is_runtime_eligible(self) -> None:
        changed = self.changed()
        changed["status"] = "approved_for_prototype"
        changed["approved_on"] = "2026-07-17"
        domain_errors = self.errors(changed)
        self.assertEqual(domain_errors, [])
        self.assertEqual(
            runtime_eligibility_errors(changed, domain_errors=domain_errors),
            [],
        )

    def test_runtime_gate_rejects_unapproved_rule(self) -> None:
        changed = self.changed()
        changed["status"] = "approved_for_prototype"
        changed["approved_on"] = "2026-07-17"
        changed["zones"]["R1-6L"]["regulations"][
            "standard.maximum_stories"
        ]["approved_for_ruleset"] = False
        eligibility = runtime_eligibility_errors(
            changed,
            domain_errors=self.errors(changed),
        )
        self.assertTrue(any("is not approved for the ruleset" in item for item in eligibility))

    def test_rejects_approval_before_verification_cutoff(self) -> None:
        changed = self.changed()
        changed["status"] = "approved_for_prototype"
        changed["approved_on"] = "2026-07-15"
        self.assert_domain_error(changed, "approved_on predates verified_through")

    def test_requires_exact_supported_zones_and_capabilities(self) -> None:
        changed = self.changed()
        changed["zones"].pop("R1-8L")
        self.assert_domain_error(
            changed,
            "zones must contain exactly R1-6L and R1-8L",
        )

        changed = self.changed()
        changed["zones"]["R1-6L"]["regulations"].pop("setback.rear")
        self.assert_domain_error(changed, "is missing capabilities")

        changed = self.changed()
        extra = copy.deepcopy(
            changed["zones"]["R1-6L"]["regulations"]["setback.rear"]
        )
        extra["rule_id"] = "us.ca.santa_clara.r1-6l.setback.illustrative"
        changed["zones"]["R1-6L"]["regulations"]["setback.illustrative"] = extra
        self.assert_domain_error(changed, "has unsupported capabilities")

    def test_rejects_duplicate_or_misplaced_rule_identity(self) -> None:
        changed = self.changed()
        duplicate = changed["zones"]["R1-6L"]["regulations"][
            "standard.maximum_primary_structure_height"
        ]["rule_id"]
        changed["zones"]["R1-8L"]["regulations"][
            "standard.maximum_primary_structure_height"
        ]["rule_id"] = duplicate
        errors = self.errors(changed)
        self.assertTrue(any(".rule_id must be" in item for item in errors))
        self.assertTrue(any("duplicate rule IDs" in item for item in errors))

    def test_rejects_dangling_shared_and_rule_references(self) -> None:
        changed = self.changed()
        changed["shared"]["citations"]["use-table"][
            "source_document_id"
        ] = "missing-source"
        self.assert_domain_error(changed, "references unknown source document")

        changed = self.changed()
        changed["shared"]["definitions"]["illustrative-definition"] = {
            "term": "Illustrative",
            "text": "Test-only definition.",
            "source_refs": ["missing-citation"],
        }
        self.assert_domain_error(changed, "has unknown source refs")

        changed = self.changed()
        changed["zones"]["R1-6L"]["regulations"][
            "standard.maximum_stories"
        ]["requirement"]["source_refs"] = ["missing-citation"]
        self.assert_domain_error(changed, "has unknown source refs")

        changed = self.changed()
        changed["zones"]["R1-6L"]["regulations"]["setback.rear"][
            "exception_family_ids"
        ].append("missing-exception")
        self.assert_domain_error(changed, "has unknown exception families")

    def test_rejects_unsafe_or_modified_source_files(self) -> None:
        changed = self.changed()
        changed["shared"]["source_documents"]["sc-title18-2025-07"][
            "local_path"
        ] = "../../outside.pdf"
        self.assert_domain_error(changed, "must remain inside the repository")

        changed = self.changed()
        changed["shared"]["source_documents"]["sc-title18-2025-07"][
            "sha256"
        ] = "0" * 64
        self.assert_domain_error(
            changed,
            "checksum does not match",
            verify_source_files=True,
        )

    def test_rejects_capability_incompatible_status_codes(self) -> None:
        changed = self.changed()
        changed["zones"]["R1-6L"]["regulations"][
            "use.single_family_dwelling"
        ]["requirement"]["code"] = "required"
        self.assert_domain_error(changed, "unsupported single-family permission status")

        changed = self.changed()
        changed["zones"]["R1-6L"]["regulations"][
            "approval.zoning_clearance"
        ]["requirement"]["code"] = "permitted_by_right"
        self.assert_domain_error(changed, "approval-incompatible status")

    def test_rejects_wrong_units_and_numeric_ranges(self) -> None:
        changed = self.changed()
        changed["zones"]["R1-6L"]["regulations"][
            "standard.maximum_primary_structure_height"
        ]["requirement"]["value"]["unit"] = "percent"
        self.assert_domain_error(changed, "must use ft, not percent")

        changed = self.changed()
        changed["zones"]["R1-6L"]["regulations"][
            "standard.maximum_stories"
        ]["requirement"]["value"]["number"] = 2.5
        self.assert_domain_error(changed, "story maximum must be an integer")

        changed = self.changed()
        changed["zones"]["R1-6L"]["regulations"][
            "standard.maximum_structure_coverage"
        ]["requirement"]["value"]["number"] = 101
        self.assert_domain_error(changed, "cannot exceed 100 percent")

    def test_rejects_wrong_lot_context(self) -> None:
        changed = self.changed()
        changed["zones"]["R1-6L"]["regulations"]["setback.street_side"][
            "applicability"
        ]["lot_context"] = "all"
        self.assert_domain_error(changed, "lot_context must be corner")

    def test_rejects_schema_expressive_but_unsupported_adjustments(self) -> None:
        changed = self.changed()
        adjustment = changed["zones"]["R1-6L"]["regulations"]["setback.front"][
            "requirement"
        ]["adjustments"][0]
        adjustment["trigger"] = {
            "kind": "height_above",
            "height": {"number": 20, "unit": "ft"},
        }
        adjustment["effect"] = {
            "kind": "add_to_base",
            "value": {"kind": "distance", "number": 5, "unit": "ft"},
        }
        errors = self.errors(changed)
        self.assertTrue(any("unsupported operational trigger" in item for item in errors))
        self.assertTrue(any("unsupported operational effect" in item for item in errors))

    def test_rejects_first_story_adjustment(self) -> None:
        changed = self.changed()
        changed["zones"]["R1-6L"]["regulations"]["setback.front"][
            "requirement"
        ]["adjustments"][0]["trigger"]["story"] = 1
        self.assert_domain_error(changed, "must begin at story two or above")

    def test_rejects_inverted_or_incompatible_paired_setbacks(self) -> None:
        changed = self.changed()
        members = changed["zones"]["R1-8L"]["regulations"][
            "setback.interior_side"
        ]["requirement"]["base"]["value"]["members"]
        members[0]["number"] = 10
        members[1]["number"] = 9
        self.assert_domain_error(changed, "smaller setback exceeds larger setback")

        changed = self.changed()
        changed["zones"]["R1-8L"]["regulations"]["setback.interior_side"][
            "requirement"
        ]["adjustments"][0]["effect"]["value"] = {
            "kind": "distance",
            "number": 14,
            "unit": "ft",
        }
        self.assert_domain_error(changed, "value shape differs from its base")

    def test_rejects_unnecessary_adjustment_precedence(self) -> None:
        changed = self.changed()
        changed["zones"]["R1-6L"]["regulations"]["setback.front"][
            "requirement"
        ]["adjustment_resolution"] = {
            "kind": "highest_precedence_applicable",
            "ordered_adjustment_ids": ["second-story-total", "unused"],
        }
        self.assert_domain_error(changed, "has unnecessary adjustment precedence")

    def test_rejects_conflict_value_drift_and_selection_ambiguity(self) -> None:
        conflict_id = "conflict-r1-8l-corner-side-first"
        changed = self.changed()
        changed["conflicts"][conflict_id]["resolution"]["selected_value"][
            "number"
        ] = 14
        errors = self.errors(changed)
        self.assertTrue(any("selected value differs from its assertion" in item for item in errors))
        self.assertTrue(any("selected value differs from" in item for item in errors))

        changed = self.changed()
        changed["conflicts"][conflict_id]["assertions"][0][
            "disposition"
        ] = "selected_for_prototype"
        self.assert_domain_error(changed, "must contain exactly one selected assertion")

    def test_rejects_broken_conflict_links(self) -> None:
        conflict_id = "conflict-r1-8l-corner-side-first"
        changed = self.changed()
        rule = changed["zones"]["R1-8L"]["regulations"]["setback.street_side"]
        rule["conflict_id"] = None
        rule["validation_status"] = "verified_with_conditions"
        self.assert_domain_error(changed, "is not linked back from")

        changed = self.changed()
        changed["conflicts"][conflict_id]["affected_rule_ids"] = [
            "us.ca.santa_clara.r1-8l.setback.unknown"
        ]
        self.assert_domain_error(changed, "has unknown affected rules")

    def test_rejects_project_resolved_status_without_conflict(self) -> None:
        changed = self.changed()
        changed["zones"]["R1-6L"]["regulations"]["setback.rear"][
            "validation_status"
        ] = "project_resolved_with_conditions"
        self.assert_domain_error(changed, "project-resolved status without a conflict")

    def test_canonical_status_and_numeric_fixtures(self) -> None:
        for zone in ("R1-6L", "R1-8L"):
            self.assertEqual(
                self.regulation(zone, "use.single_family_dwelling")["requirement"][
                    "code"
                ],
                "permitted_by_right",
            )
            self.assertEqual(
                self.regulation(zone, "approval.zoning_clearance")["requirement"][
                    "code"
                ],
                "required",
            )
            self.assertEqual(
                self.regulation(zone, "approval.architectural_review")[
                    "requirement"
                ]["code"],
                "required",
            )
            expected = {
                "standard.maximum_primary_structure_height": (25, "ft"),
                "standard.maximum_stories": (2, "stories"),
                "standard.maximum_structure_coverage": (40, "percent"),
            }
            for capability, (number, unit) in expected.items():
                value = self.regulation(zone, capability)["requirement"]["value"]
                self.assertEqual((value["number"], value["unit"]), (number, unit))

    def test_canonical_setback_fixtures(self) -> None:
        for zone in ("R1-6L", "R1-8L"):
            front = self.regulation(zone, "setback.front")["requirement"]
            self.assertEqual(front["base"]["value"]["number"], 20)
            self.assertEqual(
                front["adjustments"][0]["effect"]["value"]["number"],
                25,
            )
            rear = self.regulation(zone, "setback.rear")["requirement"]
            self.assertEqual(rear["base"]["value"]["number"], 20)
            self.assertEqual(rear["adjustments"], [])

        r1_6l_interior = self.regulation("R1-6L", "setback.interior_side")[
            "requirement"
        ]
        self.assertEqual(r1_6l_interior["base"]["value"]["number"], 5)
        self.assertEqual(
            r1_6l_interior["adjustments"][0]["effect"]["value"]["number"],
            10,
        )
        r1_6l_street = self.regulation("R1-6L", "setback.street_side")[
            "requirement"
        ]
        self.assertEqual(r1_6l_street["base"]["value"]["number"], 10)
        self.assertEqual(
            r1_6l_street["adjustments"][0]["effect"]["value"]["number"],
            15,
        )

        r1_8l_interior = self.regulation("R1-8L", "setback.interior_side")[
            "requirement"
        ]
        self.assertEqual(
            [item["number"] for item in r1_8l_interior["base"]["value"]["members"]],
            [6, 9],
        )
        self.assertEqual(
            [
                item["number"]
                for item in r1_8l_interior["adjustments"][0]["effect"]["value"][
                    "members"
                ]
            ],
            [11, 14],
        )
        r1_8l_street = self.regulation("R1-8L", "setback.street_side")[
            "requirement"
        ]
        self.assertEqual(r1_8l_street["base"]["value"]["number"], 15)
        self.assertEqual(r1_8l_street["adjustments"], [])

    def test_deferred_scope_remains_explicit(self) -> None:
        expected = {
            "Accessory structures",
            "ADUs and JADUs",
            "SB 9 and two-unit projects",
            "Density and state-law overrides",
            "Parcel-creation standards",
            "Driveway approach length",
            "Daylight plane",
            "Proposal-specific compliance",
            "Buildable-envelope geometry",
            "Historic, specific-plan, and other overlay review",
        }
        self.assertEqual(set(self.ruleset["not_evaluated"]), expected)


class RulesetV2MigrationDomainTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ruleset = load_json(DEFAULT_RULESET)
        cls.crosswalk = load_json(DEFAULT_CROSSWALK)
        cls.source_v1 = load_json(DEFAULT_V1_RULESET)

    def changed_crosswalk(self) -> dict[str, Any]:
        return copy.deepcopy(self.crosswalk)

    def errors(self, changed: dict[str, Any]) -> list[str]:
        return validate_migration(
            self.ruleset,
            changed,
            self.source_v1,
            ruleset_path=DEFAULT_RULESET,
            schema_path=DEFAULT_SCHEMA,
            source_v1_path=DEFAULT_V1_RULESET,
            repo_root=ROOT,
        )

    def assert_migration_error(self, changed: dict[str, Any], expected: str) -> None:
        errors = self.errors(changed)
        self.assertTrue(
            any(expected in error for error in errors),
            f"Expected {expected!r} in {errors!r}",
        )

    def test_canonical_migration_is_complete_and_reproducible(self) -> None:
        self.assertEqual(self.errors(self.crosswalk), [])

    def test_approval_metadata_is_not_migration_content_drift(self) -> None:
        ruleset = copy.deepcopy(self.ruleset)
        ruleset["status"] = "approved_for_prototype"
        ruleset["approved_on"] = "2026-07-17"
        crosswalk = self.changed_crosswalk()
        crosswalk["migration_status"] = "approved_runtime_validated"
        crosswalk["target_ruleset"]["status"] = "approved_for_prototype"
        errors = validate_migration(
            ruleset,
            crosswalk,
            self.source_v1,
            ruleset_path=DEFAULT_RULESET,
            schema_path=DEFAULT_SCHEMA,
            source_v1_path=DEFAULT_V1_RULESET,
            repo_root=ROOT,
        )
        self.assertEqual(errors, [])

    def test_rejects_missing_or_duplicate_v1_mapping(self) -> None:
        changed = self.changed_crosswalk()
        changed["mappings"].pop()
        self.assert_migration_error(changed, "mappings omit v1 rules")

        changed = self.changed_crosswalk()
        changed["mappings"].append(copy.deepcopy(changed["mappings"][0]))
        self.assert_migration_error(changed, "duplicate v1 rule IDs")

    def test_rejects_empty_or_nonexistent_target(self) -> None:
        changed = self.changed_crosswalk()
        changed["mappings"][0]["v2_targets"] = []
        self.assert_migration_error(changed, "v2_targets must be a non-empty array")

        changed = self.changed_crosswalk()
        changed["mappings"][0]["v2_targets"][0][
            "capability_id"
        ] = "use.unknown"
        self.assert_migration_error(changed, "references unknown capability")

    def test_rejects_nonexistent_target_component(self) -> None:
        changed = self.changed_crosswalk()
        entry = next(
            item
            for item in changed["mappings"]
            if item["v1_rule_id"] == "standard-interior-side-second-r1-8l"
        )
        entry["v2_targets"][0][
            "component"
        ] = "requirement.adjustments[missing-adjustment]"
        self.assert_migration_error(changed, "points to unknown adjustment")

    def test_rejects_count_or_checksum_drift(self) -> None:
        changed = self.changed_crosswalk()
        changed["counts"]["v2_zone_regulations"] = 19
        self.assert_migration_error(changed, "counts.v2_zone_regulations must be 20")

        changed = self.changed_crosswalk()
        changed["target_ruleset"]["sha256"] = "0" * 64
        self.assert_migration_error(changed, "target_ruleset.sha256 does not match")

    def test_rejects_malformed_crosswalk_records(self) -> None:
        changed = self.changed_crosswalk()
        changed["mappings"][0] = []
        self.assert_migration_error(changed, "mappings[0] must be an object")

        changed = self.changed_crosswalk()
        changed["counts"] = []
        self.assert_migration_error(changed, "counts must be an object")


if __name__ == "__main__":
    unittest.main()
