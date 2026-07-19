"""Regression tests for the approved R1 v2 to candidate residential v3 migration."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path
from typing import Any

from scripts.migrate_r1_rules_v3 import (
    DEFAULT_SCHEMA,
    build_crosswalk,
    json_bytes,
    migrate_ruleset,
    validate_migration,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "rulesets/santa_clara/r1/2026-07-17.2/ruleset.json"
TARGET_DIR = ROOT / "rulesets/santa_clara/residential/2026-07-19.1"
TARGET_PATH = TARGET_DIR / "ruleset.json"
CROSSWALK_PATH = TARGET_DIR / "migration-crosswalk.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ResidentialRulesetV3MigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = load_json(SOURCE_PATH)
        cls.target = load_json(TARGET_PATH)
        cls.crosswalk = load_json(CROSSWALK_PATH)

    def test_crosswalk_and_semantic_equivalence_validation_pass(self) -> None:
        self.assertEqual(
            validate_migration(
                self.source,
                self.target,
                self.crosswalk,
                source_path=SOURCE_PATH,
                target_path=TARGET_PATH,
                schema_path=DEFAULT_SCHEMA,
            ),
            [],
        )

    def test_migration_replays_byte_identically(self) -> None:
        reproduced, rules, topics = migrate_ruleset(
            self.source,
            source_path=SOURCE_PATH,
            version=self.target["version"],
            crosswalk_path=self.target["predecessor_rulesets"][0]["crosswalk_path"],
        )
        self.assertEqual(reproduced, self.target)
        self.assertEqual(json_bytes(reproduced), TARGET_PATH.read_bytes())
        rebuilt = build_crosswalk(
            source=self.source,
            source_path=SOURCE_PATH,
            target=reproduced,
            target_path=TARGET_PATH,
            schema_path=DEFAULT_SCHEMA,
            target_bytes=json_bytes(reproduced),
            rule_mappings=rules,
            topic_mappings=topics,
        )
        self.assertEqual(rebuilt, self.crosswalk)
        self.assertEqual(json_bytes(rebuilt), CROSSWALK_PATH.read_bytes())

    def test_crosswalk_maps_every_v2_rule_once_and_matches_checksums(self) -> None:
        source_ids = [
            rule["rule_id"]
            for zone in self.source["zones"].values()
            for rule in zone["regulations"].values()
        ]
        mapped_ids = [entry["source_rule_id"] for entry in self.crosswalk["rule_mappings"]]
        self.assertCountEqual(mapped_ids, source_ids)
        self.assertEqual(len(mapped_ids), len(set(mapped_ids)))
        self.assertEqual(self.crosswalk["source_ruleset"]["sha256"], sha256(SOURCE_PATH))
        self.assertEqual(self.crosswalk["target_ruleset"]["sha256"], sha256(TARGET_PATH))
        self.assertEqual(self.crosswalk["target_schema"]["sha256"], sha256(DEFAULT_SCHEMA))

    def test_migration_preserves_r1_conflict_and_resets_approval(self) -> None:
        conflict = self.target["conflicts"]["conflict-r1-8l-corner-side-first"]
        self.assertEqual(
            conflict["affected_rule_ids"],
            ["us.ca.santa_clara.r1-8l.single_family.setback.street_side"],
        )
        assertions = {
            item["assertion_id"]: item["value"]["number"]
            for item in conflict["assertions"]
        }
        self.assertEqual(
            assertions,
            {
                "table-2-3-10-ft": 10,
                "section-18-10-040-b-1-15-ft": 15,
            },
        )
        self.assertEqual(conflict["resolution"]["selected_value"]["number"], 15)
        self.assertEqual(self.target["status"], "candidate")
        self.assertIsNone(self.target["approved_on"])
        for zone in self.target["zones"].values():
            for permission in zone["use_permissions"].values():
                self.assertFalse(permission["approved_for_ruleset"])
            for profile in zone["analysis_profiles"].values():
                for rule in profile["regulations"].values():
                    self.assertFalse(rule["approved_for_ruleset"])

    def test_r1_special_pathway_is_separate_from_ordinary_profile(self) -> None:
        for zone_id in ("R1-6L", "R1-8L"):
            zone = self.target["zones"][zone_id]
            self.assertEqual(set(zone["analysis_profiles"]), {"single_family"})
            two_family = zone["use_permissions"]["use.two_family_dwelling"]
            self.assertEqual(two_family["requirement"]["code"], "permitted_by_right")
            self.assertEqual(
                two_family["special_pathway_id"],
                "r1_chapter_18_24_two_unit",
            )
            pathway = zone["special_pathways"]["r1_chapter_18_24_two_unit"]
            self.assertEqual(pathway["configuration_scope"], "attached_or_detached_homes")
            self.assertEqual(pathway["analysis_requirement"]["kind"], "not_evaluated")

    def test_crosswalk_mutations_fail_exhaustiveness_and_semantic_replay(self) -> None:
        changed_crosswalk = copy.deepcopy(self.crosswalk)
        changed_crosswalk["rule_mappings"].pop()
        errors = validate_migration(
            self.source,
            self.target,
            changed_crosswalk,
            source_path=SOURCE_PATH,
            target_path=TARGET_PATH,
            schema_path=DEFAULT_SCHEMA,
        )
        self.assertTrue(any("omit source rules" in item for item in errors))

        changed_target = copy.deepcopy(self.target)
        changed_target["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["standard.maximum_stories"]["requirement"]["value"]["number"] = 3
        errors = validate_migration(
            self.source,
            changed_target,
            self.crosswalk,
            source_path=SOURCE_PATH,
            target_path=TARGET_PATH,
            schema_path=DEFAULT_SCHEMA,
        )
        self.assertTrue(any("fails R1 semantic equivalence" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
