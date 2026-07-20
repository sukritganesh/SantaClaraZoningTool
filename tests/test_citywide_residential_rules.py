"""Regression and mutation tests for the nonruntime R1-R6 candidate."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path
from typing import Any

from scripts.author_citywide_residential_rules import (
    CITYWIDE_ZONE_DATA,
    DEFAULT_SCHEMA,
    DEFAULT_SOURCE,
    DEFAULT_OUTPUT_DIR,
    build_crosswalk,
    expand_ruleset,
    json_bytes,
    validate_expansion,
)
from scripts.validate_residential_rules_v3 import validate_ruleset


ROOT = Path(__file__).resolve().parents[1]
TARGET_PATH = DEFAULT_OUTPUT_DIR / "ruleset.json"
CROSSWALK_PATH = DEFAULT_OUTPUT_DIR / "citywide-expansion-crosswalk.json"
V3_SCHEMA_PATH = ROOT / "rulesets/schema/ruleset-v3.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CitywideResidentialRulesTest(unittest.TestCase):
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
        self.assertEqual(self.target["schema_version"], "3.1.0")
        self.assertEqual(self.errors(self.target, verify_source_files=True), [])

    def test_accepted_v3_predecessor_and_schema_are_unchanged(self) -> None:
        self.assertEqual(
            sha256(DEFAULT_SOURCE),
            "ad8f0ddb3eda82c724ae0c50fb23a89591ae78b72fab58e10868698eac4ed2ff",
        )
        self.assertEqual(
            sha256(V3_SCHEMA_PATH),
            "5368aeb987caab94d7e8cafe5f4d34bc9f637661b7077bfb03108ea1129ecd8c",
        )

    def test_candidate_contains_exact_r1_r6_tranche_and_profiles(self) -> None:
        self.assertEqual(
            set(self.target["zones"]),
            {"R1-6L", "R1-8L", "R2", "R3", "R4", "R5", "R6"},
        )
        for zone, data in CITYWIDE_ZONE_DATA.items():
            self.assertEqual(
                tuple(self.target["zones"][zone]["analysis_profiles"]),
                data["profiles"],
            )
            statuses = tuple(
                rule["requirement"]["code"]
                for rule in self.target["zones"][zone]["use_permissions"].values()
            )
            self.assertEqual(statuses, data["use_statuses"])

    def test_every_citywide_profile_has_the_same_nine_supported_regulations(self) -> None:
        expected = {
            "approval.zoning_clearance",
            "approval.architectural_review",
            "standard.maximum_primary_structure_height",
            "standard.maximum_stories",
            "standard.maximum_structure_coverage",
            "setback.front",
            "setback.rear",
            "setback.interior_side",
            "setback.street_side",
        }
        profile_count = 0
        regulation_count = 0
        for zone in CITYWIDE_ZONE_DATA:
            for profile in self.target["zones"][zone]["analysis_profiles"].values():
                profile_count += 1
                regulation_count += len(profile["regulations"])
                self.assertEqual(set(profile["regulations"]), expected)
        self.assertEqual(profile_count, 9)
        self.assertEqual(regulation_count, 81)

    def test_citywide_numeric_matrix_matches_approved_values(self) -> None:
        for zone, expected in CITYWIDE_ZONE_DATA.items():
            for profile in self.target["zones"][zone]["analysis_profiles"].values():
                regulations = profile["regulations"]
                self.assertEqual(
                    regulations["standard.maximum_primary_structure_height"]["requirement"][
                        "value"
                    ],
                    {"number": expected["height"], "unit": "ft"},
                )
                self.assertEqual(
                    regulations["standard.maximum_stories"]["requirement"]["value"],
                    {"number": expected["stories"], "unit": "stories"},
                )
                for capability, field in (
                    ("setback.front", "front"),
                    ("setback.interior_side", "interior"),
                    ("setback.street_side", "street"),
                ):
                    self.assertEqual(
                        regulations[capability]["requirement"]["base"]["value"]["number"],
                        expected[field],
                    )
                rear = regulations["setback.rear"]["requirement"]
                self.assertEqual(rear["base"]["value"]["number"], expected["rear"]["base"])
                expected_adjustments = 1 if "multistory" in expected["rear"] else 0
                self.assertEqual(len(rear["adjustments"]), expected_adjustments)
                if expected_adjustments:
                    self.assertEqual(
                        rear["adjustments"][0]["effect"]["value"]["number"],
                        expected["rear"]["multistory"],
                    )

    def test_coverage_preserves_numeric_tiers_and_no_maximum_listed(self) -> None:
        r2 = self.target["zones"]["R2"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["standard.maximum_structure_coverage"]["requirement"]
        self.assertEqual(r2["kind"], "maximum_quantity")
        self.assertEqual(r2["value"], {"number": 45, "unit": "percent"})

        for zone, below in (("R3", 60), ("R4", 80)):
            requirement = self.target["zones"][zone]["analysis_profiles"]["multifamily"][
                "regulations"
            ]["standard.maximum_structure_coverage"]["requirement"]
            self.assertEqual(requirement["kind"], "lot_area_tiered_maximum")
            self.assertEqual(requirement["threshold"], {"number": 10000, "unit": "sq_ft"})
            self.assertEqual(requirement["below_threshold"]["value"]["number"], below)
            self.assertEqual(
                requirement["at_or_above_threshold"]["kind"],
                "no_maximum_listed",
            )

        for zone in ("R5", "R6"):
            requirement = self.target["zones"][zone]["analysis_profiles"]["multifamily"][
                "regulations"
            ]["standard.maximum_structure_coverage"]["requirement"]
            self.assertEqual(requirement["kind"], "no_maximum_listed")
            self.assertIn("not a conclusion", requirement["explanation"])

    def test_tier_mutations_fail_schema_or_domain_semantics(self) -> None:
        changed = copy.deepcopy(self.target)
        requirement = changed["zones"]["R3"]["analysis_profiles"]["multifamily"][
            "regulations"
        ]["standard.maximum_structure_coverage"]["requirement"]
        requirement["threshold"]["number"] = 9999
        self.assertTrue(any("10000 sq_ft" in item for item in self.errors(changed)))

        changed = copy.deepcopy(self.target)
        requirement = changed["zones"]["R4"]["analysis_profiles"]["multifamily"][
            "regulations"
        ]["standard.maximum_structure_coverage"]["requirement"]
        requirement["below_threshold"]["value"]["number"] = 101
        self.assertTrue(any("cannot exceed 100" in item for item in self.errors(changed)))

        changed = copy.deepcopy(self.target)
        tier = copy.deepcopy(
            changed["zones"]["R3"]["analysis_profiles"]["multifamily"]["regulations"][
                "standard.maximum_structure_coverage"
            ]["requirement"]
        )
        changed["zones"]["R3"]["analysis_profiles"]["multifamily"]["regulations"][
            "standard.maximum_primary_structure_height"
        ]["requirement"] = tier
        self.assertTrue(any("only for structure coverage" in item for item in self.errors(changed)))

    def test_two_family_uses_multifamily_workflow_but_distinct_structure(self) -> None:
        for zone in ("R2", "R3", "R4"):
            profile = self.target["zones"][zone]["analysis_profiles"]["two_family"]
            self.assertEqual(profile["workflow_family"], "multifamily")
            self.assertEqual(profile["primary_structure_type"], "two_family_primary_structure")
            self.assertEqual(profile["legal_use_capability_id"], "use.two_family_dwelling")
        for zone in ("R5", "R6"):
            self.assertNotIn("two_family", self.target["zones"][zone]["analysis_profiles"])

    def test_deferred_layers_are_profile_specific_and_not_new_regulations(self) -> None:
        for zone in ("R3", "R4", "R5", "R6"):
            for profile_id, profile in self.target["zones"][zone]["analysis_profiles"].items():
                self.assertIn(
                    "citywide_r1_r2_height_transition",
                    profile["not_evaluated_topic_ids"],
                )
                if profile_id == "multifamily":
                    self.assertIn("objective_design_standards", profile["not_evaluated_topic_ids"])
                else:
                    self.assertNotIn(
                        "objective_design_standards",
                        profile["not_evaluated_topic_ids"],
                    )
        self.assertNotIn(
            "citywide_r1_r2_height_transition",
            self.target["zones"]["R2"]["analysis_profiles"]["multifamily"][
                "not_evaluated_topic_ids"
            ],
        )

    def test_r1_zones_conflict_and_topics_are_preserved_exactly(self) -> None:
        for zone in ("R1-6L", "R1-8L"):
            self.assertEqual(self.target["zones"][zone], self.source["zones"][zone])
        self.assertEqual(self.target["conflicts"], self.source["conflicts"])
        for topic_id, topic in self.source["not_evaluated_topics"].items():
            self.assertEqual(self.target["not_evaluated_topics"][topic_id], topic)

    def test_candidate_remains_unapproved_and_fails_runtime_gate(self) -> None:
        self.assertEqual(self.target["status"], "candidate")
        self.assertIsNone(self.target["approved_on"])
        for zone in self.target["zones"].values():
            for permission in zone["use_permissions"].values():
                self.assertFalse(permission["approved_for_ruleset"])
            for profile in zone["analysis_profiles"].values():
                for rule in profile["regulations"].values():
                    self.assertFalse(rule["approved_for_ruleset"])
        errors = self.errors(self.target, require_runtime_eligible=True)
        self.assertTrue(any("missing exact target zones" in item for item in errors))
        self.assertTrue(any("requires status approved_for_runtime" in item for item in errors))

    def test_expansion_crosswalk_and_deterministic_replay_pass(self) -> None:
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

    def test_crosswalk_counts_and_checksums_cover_the_tranche(self) -> None:
        self.assertEqual(
            self.crosswalk["counts"],
            {
                "source_zones": 2,
                "target_zones": 7,
                "carried_source_rules": 24,
                "target_rules": 120,
                "added_use_permissions": 15,
                "added_analysis_profiles": 9,
                "added_profile_regulations": 81,
                "added_not_evaluated_topics": 6,
                "carried_conflicts": 1,
            },
        )
        self.assertEqual(self.crosswalk["source_ruleset"]["sha256"], sha256(DEFAULT_SOURCE))
        self.assertEqual(self.crosswalk["target_ruleset"]["sha256"], sha256(TARGET_PATH))
        self.assertEqual(self.crosswalk["target_schema"]["sha256"], sha256(DEFAULT_SCHEMA))

    def test_lineage_mutations_fail_closed(self) -> None:
        changed = copy.deepcopy(self.target)
        changed["zones"]["R1-6L"]["analysis_profiles"]["single_family"]["regulations"][
            "standard.maximum_stories"
        ]["requirement"]["value"]["number"] = 3
        errors = validate_expansion(
            self.source,
            changed,
            self.crosswalk,
            source_path=DEFAULT_SOURCE,
            target_path=TARGET_PATH,
            schema_path=DEFAULT_SCHEMA,
        )
        self.assertTrue(any("changed preserved predecessor zone" in item for item in errors))

        changed_crosswalk = copy.deepcopy(self.crosswalk)
        changed_crosswalk["added_zone_profiles"]["R2"] = ["multifamily"]
        errors = validate_expansion(
            self.source,
            self.target,
            changed_crosswalk,
            source_path=DEFAULT_SOURCE,
            target_path=TARGET_PATH,
            schema_path=DEFAULT_SCHEMA,
        )
        self.assertTrue(any("approved citywide matrix" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
