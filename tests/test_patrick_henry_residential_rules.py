"""Regression and mutation tests for the complete nonruntime 12-zone candidate."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path
from typing import Any

from scripts.author_patrick_henry_residential_rules import (
    DEFAULT_CROSSWALK_NAME,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SCHEMA,
    DEFAULT_SOURCE,
    DENSITY_CAPABILITY,
    PATRICK_HENRY_ZONE_DATA,
    PH_R5_CONFLICT_ID,
    build_crosswalk,
    expand_ruleset,
    json_bytes,
    validate_expansion,
)
from scripts.validate_residential_rules_v3 import validate_ruleset


ROOT = Path(__file__).resolve().parents[1]
TARGET_PATH = DEFAULT_OUTPUT_DIR / "ruleset.json"
CROSSWALK_PATH = DEFAULT_OUTPUT_DIR / DEFAULT_CROSSWALK_NAME
DENSITY_CROSSWALK_PATH = DEFAULT_SOURCE.parent / "density-expansion-crosswalk.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PatrickHenryResidentialRulesTest(unittest.TestCase):
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
        self.assertEqual(self.target["version"], "2026-07-19.4")
        self.assertEqual(self.errors(self.target, verify_source_files=True), [])

    def test_candidate_contains_the_exact_complete_zone_and_profile_matrix(self) -> None:
        self.assertEqual(
            set(self.target["zones"]),
            {
                "R1-6L",
                "R1-8L",
                "R2",
                "R3",
                "R4",
                "R5",
                "R6",
                "PH-R5",
                "UV",
                "VR",
                "UC",
                "HDF",
            },
        )
        for zone in PATRICK_HENRY_ZONE_DATA:
            record = self.target["zones"][zone]
            self.assertEqual(set(record["analysis_profiles"]), {"multifamily"})
            self.assertEqual(record["special_pathways"], {})
            self.assertEqual(
                tuple(
                    permission["requirement"]["code"]
                    for permission in record["use_permissions"].values()
                ),
                ("not_listed", "not_listed", "permitted_by_right"),
            )
            profile = record["analysis_profiles"]["multifamily"]
            self.assertEqual(profile["workflow_family"], "multifamily")
            self.assertEqual(
                profile["primary_structure_type"],
                "multifamily_primary_structure",
            )

    def test_each_patrick_henry_profile_has_only_the_ten_supported_rules(self) -> None:
        expected = {
            "approval.zoning_clearance",
            "approval.architectural_review",
            "standard.maximum_primary_structure_height",
            "standard.maximum_stories",
            "standard.maximum_structure_coverage",
            DENSITY_CAPABILITY,
            "setback.front",
            "setback.rear",
            "setback.interior_side",
            "setback.street_side",
        }
        for zone in PATRICK_HENRY_ZONE_DATA:
            regulations = self.target["zones"][zone]["analysis_profiles"]["multifamily"][
                "regulations"
            ]
            self.assertEqual(set(regulations), expected)

    def test_numeric_faa_no_maximum_and_density_matrix_are_exact(self) -> None:
        for zone, data in PATRICK_HENRY_ZONE_DATA.items():
            regulations = self.target["zones"][zone]["analysis_profiles"]["multifamily"][
                "regulations"
            ]
            height = regulations["standard.maximum_primary_structure_height"]["requirement"]
            stories = regulations["standard.maximum_stories"]["requirement"]
            if zone == "UC":
                self.assertEqual(height["kind"], "faa_controlled")
                self.assertEqual(stories["kind"], "faa_controlled")
                self.assertEqual(height["controlling_authority"], "FAA")
            else:
                self.assertEqual(
                    height["value"],
                    {"number": data["height"], "unit": "ft"},
                )
                self.assertEqual(
                    stories["value"],
                    {"number": data["stories"], "unit": "stories"},
                )
            coverage = regulations["standard.maximum_structure_coverage"]["requirement"]
            self.assertEqual(coverage["kind"], "no_maximum_listed")
            self.assertIn("not an unlimited-project", coverage["explanation"])
            density = regulations[DENSITY_CAPABILITY]["requirement"]
            self.assertEqual(
                (density["minimum"], density["maximum"]),
                data["density"],
            )
            self.assertEqual(density["unit"], "dwelling_units_per_acre")

    def test_setbacks_preserve_back_of_walk_and_plan_dependent_rear(self) -> None:
        for zone in PATRICK_HENRY_ZONE_DATA:
            regulations = self.target["zones"][zone]["analysis_profiles"]["multifamily"][
                "regulations"
            ]
            for capability in ("setback.front", "setback.interior_side", "setback.street_side"):
                requirement = regulations[capability]["requirement"]
                self.assertEqual(requirement["kind"], "setback")
                self.assertEqual(requirement["base"]["value"]["number"], 10)
                self.assertIn("back of walk", regulations[capability]["conditions"][0])
            rear = regulations["setback.rear"]["requirement"]
            self.assertEqual(rear["kind"], "plan_dependent")
            self.assertTrue(rear["required_sources_or_facts"])
            self.assertNotIn("number", rear)
            self.assertIn("Zero is not", rear["explanation"])

    def test_ph_r5_conflict_retains_five_assertions_and_selects_table_1_1(self) -> None:
        conflict = self.target["conflicts"][PH_R5_CONFLICT_ID]
        actual = {
            assertion["assertion_id"]: (
                assertion["value"]["minimum"],
                assertion["value"]["maximum"],
                assertion["disposition"],
            )
            for assertion in conflict["assertions"]
        }
        self.assertEqual(
            actual,
            {
                "title18-table-1-1-51-100": (51, 100, "selected_for_ruleset"),
                "title18-zone-purpose-51-99": (51, 99, "not_selected_for_ruleset"),
                "title18-table-2-4-51-99": (51, 99, "not_selected_for_ruleset"),
                "specific-plan-section-4-3-2-51-99": (
                    51,
                    99,
                    "not_selected_for_ruleset",
                ),
                "specific-plan-table-4-2-51-99": (
                    51,
                    99,
                    "not_selected_for_ruleset",
                ),
            },
        )
        rule = self.target["zones"]["PH-R5"]["analysis_profiles"]["multifamily"][
            "regulations"
        ][DENSITY_CAPABILITY]
        self.assertEqual(rule["conflict_id"], PH_R5_CONFLICT_ID)
        self.assertEqual(rule["validation_status"], "project_resolved_with_conditions")
        self.assertEqual(
            conflict["resolution"]["selected_value"],
            {
                "kind": "quantity_range",
                "minimum": 51,
                "maximum": 100,
                "unit": "dwelling_units_per_acre",
            },
        )
        self.assertIn("Project owner", conflict["resolution"]["decision_source"])

    def test_deferred_topics_are_disclosed_without_new_regulation_families(self) -> None:
        for zone in PATRICK_HENRY_ZONE_DATA:
            topic_ids = self.target["zones"][zone]["analysis_profiles"]["multifamily"][
                "not_evaluated_topic_ids"
            ]
            self.assertIn("patrick_henry_r1_r2_height_transition", topic_ids)
            self.assertIn("patrick_henry_recreation_space_and_encroachments", topic_ids)
            self.assertIn("patrick_henry_design_guidelines_and_project_review", topic_ids)
            self.assertIn("objective_design_standards", topic_ids)
            if zone == "UC":
                self.assertIn(
                    "patrick_henry_uc_community_benefits_density_path",
                    topic_ids,
                )
            else:
                self.assertNotIn(
                    "patrick_henry_uc_community_benefits_density_path",
                    topic_ids,
                )
            if zone == "HDF":
                self.assertIn("patrick_henry_hdf_nonresidential_option", topic_ids)
            else:
                self.assertNotIn("patrick_henry_hdf_nonresidential_option", topic_ids)

    def test_patrick_henry_sources_are_checksum_pinned(self) -> None:
        sources = self.target["shared"]["source_documents"]
        for source_id in (
            "patrick-henry-plan-2022-03",
            "patrick-henry-authoring-verification-2026-07-19",
        ):
            source = sources[source_id]
            path = ROOT / source["local_path"]
            self.assertTrue(path.is_file())
            self.assertEqual(source["sha256"], sha256(path))
        self.assertEqual(
            sources["patrick-henry-plan-2022-03"]["sha256"],
            "cefd7df91819c61d26b5cdddd0d395b74445078f2dc6e0d57995dc6992b16b87",
        )

    def test_every_predecessor_component_is_preserved(self) -> None:
        for zone, zone_record in self.source["zones"].items():
            self.assertEqual(self.target["zones"][zone], zone_record)
        for conflict_id, conflict in self.source["conflicts"].items():
            self.assertEqual(self.target["conflicts"][conflict_id], conflict)
        for topic_id, topic in self.source["not_evaluated_topics"].items():
            self.assertEqual(self.target["not_evaluated_topics"][topic_id], topic)
        for group in ("source_documents", "citations", "definitions", "exception_families"):
            for record_id, record in self.source["shared"][group].items():
                self.assertEqual(self.target["shared"][group][record_id], record)

    def test_crosswalk_and_deterministic_replay_pass(self) -> None:
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
                "target_zones": 12,
                "carried_source_rules": 131,
                "target_rules": 196,
                "added_use_permissions": 15,
                "added_analysis_profiles": 5,
                "added_profile_regulations": 50,
                "added_not_evaluated_topics": 8,
                "added_source_documents": 2,
                "added_citations": 9,
                "added_exception_families": 2,
                "carried_conflicts": 3,
                "added_conflicts": 1,
            },
        )
        self.assertEqual(self.crosswalk["source_ruleset"]["sha256"], sha256(DEFAULT_SOURCE))
        self.assertEqual(self.crosswalk["target_ruleset"]["sha256"], sha256(TARGET_PATH))
        self.assertEqual(self.crosswalk["target_schema"]["sha256"], sha256(DEFAULT_SCHEMA))

    def test_source_matrix_and_nonnumeric_mutations_fail_closed(self) -> None:
        changed = copy.deepcopy(self.target)
        density = changed["zones"]["UV"]["analysis_profiles"]["multifamily"][
            "regulations"
        ][DENSITY_CAPABILITY]["requirement"]
        density["maximum"] = 150
        self.assertTrue(any("source-approved range" in item for item in self.errors(changed)))

        changed = copy.deepcopy(self.target)
        changed["zones"]["UC"]["analysis_profiles"]["multifamily"]["regulations"][
            "standard.maximum_primary_structure_height"
        ]["requirement"] = {
            "kind": "maximum_quantity",
            "value": {"number": 160, "unit": "ft"},
            "source_refs": ["patrick-henry-title18-standards-table"],
        }
        errors = validate_expansion(
            self.source,
            changed,
            self.crosswalk,
            source_path=DEFAULT_SOURCE,
            target_path=TARGET_PATH,
            schema_path=DEFAULT_SCHEMA,
        )
        self.assertTrue(any("deterministic Patrick Henry" in item for item in errors))

        changed = copy.deepcopy(self.target)
        changed["zones"]["VR"]["analysis_profiles"]["multifamily"]["regulations"][
            "setback.rear"
        ]["requirement"] = {
            "kind": "setback",
            "base": {
                "value": {"kind": "distance", "number": 0, "unit": "ft"},
                "source_refs": ["patrick-henry-plan-standards-table"],
            },
            "adjustments": [],
        }
        errors = validate_expansion(
            self.source,
            changed,
            self.crosswalk,
            source_path=DEFAULT_SOURCE,
            target_path=TARGET_PATH,
            schema_path=DEFAULT_SCHEMA,
        )
        self.assertTrue(any("deterministic Patrick Henry" in item for item in errors))

    def test_candidate_has_complete_matrix_but_still_fails_runtime_approval(self) -> None:
        self.assertEqual(self.target["status"], "candidate")
        self.assertIsNone(self.target["approved_on"])
        errors = self.errors(self.target, require_runtime_eligible=True)
        self.assertFalse(any("missing exact target zones" in item for item in errors))
        self.assertTrue(any("requires status approved_for_runtime" in item for item in errors))
        self.assertTrue(any("unapproved rules" in item for item in errors))

    def test_density_predecessor_schema_and_crosswalk_are_byte_unchanged(self) -> None:
        self.assertEqual(
            sha256(DEFAULT_SOURCE),
            "7f54eb7569a007ce4b5bdac334aa3fd051990937df2717e270960cdde6e426d6",
        )
        self.assertEqual(
            sha256(DEFAULT_SCHEMA),
            "186204364b72f6aac4b8615030c874681c6aa5ea4fac976aff03214f7347c6ef",
        )
        self.assertEqual(
            sha256(DENSITY_CROSSWALK_PATH),
            "4c0746efd77d061a00f9a7b54186eb61cdd513b520531c57847d29f3ef28ec4e",
        )


if __name__ == "__main__":
    unittest.main()
