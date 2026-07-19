"""Regression and mutation tests for the nonruntime R1-R6 density candidate."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path
from typing import Any

from scripts.author_density_residential_rules import (
    CONFLICT_IDS,
    DEFAULT_CROSSWALK_NAME,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SCHEMA,
    DEFAULT_SOURCE,
    DENSITY_CAPABILITY,
    DENSITY_RANGES,
    build_crosswalk,
    expand_ruleset,
    json_bytes,
    validate_expansion,
)
from scripts.validate_residential_rules_v3 import validate_ruleset


ROOT = Path(__file__).resolve().parents[1]
TARGET_PATH = DEFAULT_OUTPUT_DIR / "ruleset.json"
CROSSWALK_PATH = DEFAULT_OUTPUT_DIR / DEFAULT_CROSSWALK_NAME
V3_1_SCHEMA_PATH = ROOT / "rulesets/schema/ruleset-v3.1.schema.json"
CITYWIDE_CROSSWALK_PATH = DEFAULT_SOURCE.parent / "citywide-expansion-crosswalk.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DensityResidentialRulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = load_json(DEFAULT_SOURCE)
        cls.target = load_json(TARGET_PATH)
        cls.schema = load_json(DEFAULT_SCHEMA)
        cls.crosswalk = load_json(CROSSWALK_PATH)

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

    def test_canonical_candidate_passes_schema_domain_and_source_validation(self) -> None:
        self.assertEqual(self.target["schema_version"], "3.2.0")
        self.assertEqual(self.target["version"], "2026-07-19.3")
        self.assertEqual(self.errors(self.target, verify_source_files=True), [])

    def test_every_r1_r6_profile_has_the_approved_density_range(self) -> None:
        profile_count = 0
        for zone, zone_record in self.target["zones"].items():
            for profile in zone_record["analysis_profiles"].values():
                profile_count += 1
                rule = profile["regulations"][DENSITY_CAPABILITY]
                minimum, maximum = DENSITY_RANGES[zone]
                self.assertEqual(
                    rule["requirement"],
                    {
                        "kind": "quantity_range",
                        "minimum": minimum,
                        "maximum": maximum,
                        "unit": "dwelling_units_per_acre",
                        "source_refs": rule["requirement"]["source_refs"],
                    },
                )
                self.assertEqual(rule["applicability"], {"lot_context": "all"})
        self.assertEqual(profile_count, 11)

    def test_r5_and_r6_conflicts_retain_assertions_and_select_table_1_1(self) -> None:
        expected = {
            "R5": {
                "table-1-1-51-100": (51, 100, "selected_for_ruleset"),
                "zone-purpose-51-99": (51, 99, "not_selected_for_ruleset"),
                "table-2-3-51-99": (51, 99, "not_selected_for_ruleset"),
            },
            "R6": {
                "table-1-1-60-350": (60, 350, "selected_for_ruleset"),
                "zone-purpose-60-350": (60, 350, "not_selected_for_ruleset"),
                "table-2-3-85-350": (85, 350, "not_selected_for_ruleset"),
            },
        }
        for zone, conflict_id in CONFLICT_IDS.items():
            conflict = self.target["conflicts"][conflict_id]
            actual = {
                assertion["assertion_id"]: (
                    assertion["value"]["minimum"],
                    assertion["value"]["maximum"],
                    assertion["disposition"],
                )
                for assertion in conflict["assertions"]
            }
            self.assertEqual(actual, expected[zone])
            self.assertEqual(
                conflict["resolution"]["decision_source"],
                "Project owner direction in the July 19, 2026 Codex task",
            )
            self.assertEqual(
                conflict["resolution"]["status"],
                "project_resolved_pending_official_clarification",
            )
            for affected_id in conflict["affected_rule_ids"]:
                profile_id = affected_id.split(".")[4]
                rule = self.target["zones"][zone]["analysis_profiles"][profile_id][
                    "regulations"
                ][DENSITY_CAPABILITY]
                self.assertEqual(rule["conflict_id"], conflict_id)
                self.assertEqual(rule["validation_status"], "project_resolved_with_conditions")

    def test_r1_r4_density_rules_are_verified_without_conflicts(self) -> None:
        for zone in ("R1-6L", "R1-8L", "R2", "R3", "R4"):
            for profile in self.target["zones"][zone]["analysis_profiles"].values():
                rule = profile["regulations"][DENSITY_CAPABILITY]
                self.assertIsNone(rule["conflict_id"])
                self.assertEqual(rule["validation_status"], "verified_with_conditions")

    def test_density_sources_are_checksum_pinned(self) -> None:
        sources = self.target["shared"]["source_documents"]
        for source_id in (
            "residential-density-verification-2026-07-19",
            "residential-density-amendment-audit-2026-07-18",
        ):
            source = sources[source_id]
            path = ROOT / source["local_path"]
            self.assertTrue(path.is_file())
            self.assertEqual(source["sha256"], sha256(path))
        for citation_id in (
            "residential-density-table-1-1",
            "residential-density-zone-purpose",
            "residential-density-table-2-3",
            "residential-density-plan-control",
            "residential-density-verification",
            "residential-density-amendment-audit",
        ):
            self.assertIn(citation_id, self.target["shared"]["citations"])

    def test_every_predecessor_permission_and_regulation_is_preserved(self) -> None:
        for zone, source_zone in self.source["zones"].items():
            target_zone = self.target["zones"][zone]
            self.assertEqual(target_zone["use_permissions"], source_zone["use_permissions"])
            self.assertEqual(target_zone["special_pathways"], source_zone["special_pathways"])
            for profile_id, source_profile in source_zone["analysis_profiles"].items():
                target_profile = target_zone["analysis_profiles"][profile_id]
                for capability, source_rule in source_profile["regulations"].items():
                    self.assertEqual(target_profile["regulations"][capability], source_rule)
        for conflict_id, conflict in self.source["conflicts"].items():
            self.assertEqual(self.target["conflicts"][conflict_id], conflict)

    def test_lineage_crosswalk_and_deterministic_replay_pass(self) -> None:
        self.assertEqual(
            validate_expansion(
                self.source,
                self.target,
                self.crosswalk,
                source_path=DEFAULT_SOURCE,
                target_path=TARGET_PATH,
                schema_path=DEFAULT_SCHEMA,
            ),
            [],
        )
        reproduced = expand_ruleset(
            self.source,
            source_path=DEFAULT_SOURCE,
            version=self.target["version"],
            crosswalk_path=self.target["predecessor_rulesets"][0]["crosswalk_path"],
        )
        self.assertEqual(json_bytes(reproduced), TARGET_PATH.read_bytes())
        rebuilt = build_crosswalk(
            source=self.source,
            source_path=DEFAULT_SOURCE,
            target=reproduced,
            target_path=TARGET_PATH,
            schema_path=DEFAULT_SCHEMA,
            target_bytes=json_bytes(reproduced),
        )
        self.assertEqual(json_bytes(rebuilt), CROSSWALK_PATH.read_bytes())

    def test_crosswalk_counts_and_predecessor_checksums_are_exact(self) -> None:
        self.assertEqual(
            self.crosswalk["counts"],
            {
                "source_zones": 7,
                "target_zones": 7,
                "carried_source_rules": 120,
                "target_rules": 131,
                "added_profile_regulations": 11,
                "modified_not_evaluated_topics": 2,
                "added_profile_topic_references": 1,
                "carried_conflicts": 1,
                "added_conflicts": 2,
            },
        )
        self.assertEqual(self.crosswalk["source_ruleset"]["sha256"], sha256(DEFAULT_SOURCE))
        self.assertEqual(self.crosswalk["target_ruleset"]["sha256"], sha256(TARGET_PATH))
        self.assertEqual(self.crosswalk["target_schema"]["sha256"], sha256(DEFAULT_SCHEMA))

    def test_range_shape_and_matrix_mutations_fail_closed(self) -> None:
        changed = copy.deepcopy(self.target)
        requirement = changed["zones"]["R3"]["analysis_profiles"]["multifamily"][
            "regulations"
        ][DENSITY_CAPABILITY]["requirement"]
        requirement["minimum"] = 40
        self.assertTrue(any("minimum exceeds maximum" in item for item in self.errors(changed)))

        changed = copy.deepcopy(self.target)
        requirement = changed["zones"]["R2"]["analysis_profiles"]["single_family"][
            "regulations"
        ][DENSITY_CAPABILITY]["requirement"]
        requirement["unit"] = "units"
        self.assertTrue(self.errors(changed))

        changed = copy.deepcopy(self.target)
        del changed["zones"]["R4"]["analysis_profiles"]["two_family"]["regulations"][
            DENSITY_CAPABILITY
        ]
        self.assertTrue(any("missing capabilities" in item for item in self.errors(changed)))

    def test_conflict_and_selected_value_mutations_fail_closed(self) -> None:
        changed = copy.deepcopy(self.target)
        rule = changed["zones"]["R5"]["analysis_profiles"]["multifamily"]["regulations"][
            DENSITY_CAPABILITY
        ]
        rule["requirement"]["maximum"] = 99
        errors = self.errors(changed)
        self.assertTrue(any("source-approved range" in item for item in errors))
        self.assertTrue(any("selected value differs" in item for item in errors))

        changed = copy.deepcopy(self.target)
        changed["conflicts"][CONFLICT_IDS["R6"]]["assertions"][2]["value"]["minimum"] = 84
        errors = validate_expansion(
            self.source,
            changed,
            self.crosswalk,
            source_path=DEFAULT_SOURCE,
            target_path=TARGET_PATH,
            schema_path=DEFAULT_SCHEMA,
        )
        self.assertTrue(any("deterministic density authoring replay" in item for item in errors))

    def test_candidate_remains_unapproved_and_fails_runtime_gate(self) -> None:
        self.assertEqual(self.target["status"], "candidate")
        self.assertIsNone(self.target["approved_on"])
        for zone in self.target["zones"].values():
            for profile in zone["analysis_profiles"].values():
                self.assertFalse(
                    profile["regulations"][DENSITY_CAPABILITY]["approved_for_ruleset"]
                )
        errors = self.errors(self.target, require_runtime_eligible=True)
        self.assertTrue(any("missing exact target zones" in item for item in errors))
        self.assertTrue(any("requires status approved_for_runtime" in item for item in errors))

    def test_citywide_predecessor_and_schema_are_byte_unchanged(self) -> None:
        self.assertEqual(
            sha256(DEFAULT_SOURCE),
            "57166a693fbab477fec631e251cc909541db912ee01e2a3ef2345dbbc06f0d94",
        )
        self.assertEqual(
            sha256(V3_1_SCHEMA_PATH),
            "7fa85189f1c8a1c5dbee3537cb494f2661ad80f77a1e9bda50e050f6f68e8103",
        )
        self.assertEqual(
            sha256(CITYWIDE_CROSSWALK_PATH),
            "c8b7fcdba8ef4081cb2d02b68dd0c483f0812835a7074f33cc91fc57b1337c07",
        )


if __name__ == "__main__":
    unittest.main()
