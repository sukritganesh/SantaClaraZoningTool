"""Regression tests for the approved-v1 to candidate-v2 migration."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from scripts.migrate_r1_rules_v2 import migrate_ruleset


ROOT = Path(__file__).resolve().parents[1]
V1_PATH = ROOT / "rulesets" / "santa_clara" / "r1" / "2026-07-16" / "ruleset.json"
V2_DIR = ROOT / "rulesets" / "santa_clara" / "r1" / "2026-07-17"
V2_PATH = V2_DIR / "ruleset.json"
CROSSWALK_PATH = V2_DIR / "migration-crosswalk.json"
SCHEMA_PATH = ROOT / "rulesets" / "schema" / "ruleset-v2.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RulesetV2MigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.v1 = load_json(V1_PATH)
        cls.v2 = load_json(V2_PATH)
        cls.crosswalk = load_json(CROSSWALK_PATH)
        cls.schema = load_json(SCHEMA_PATH)

    def regulation(self, zone: str, capability: str) -> dict[str, Any]:
        return self.v2["zones"][zone]["regulations"][capability]

    def test_candidate_is_schema_valid_and_reproducible(self) -> None:
        validator = Draft202012Validator(
            self.schema,
            format_checker=FormatChecker(),
        )
        errors = sorted(
            validator.iter_errors(self.v2),
            key=lambda error: list(error.path),
        )
        self.assertEqual([error.message for error in errors], [])

        reproduced, mappings = migrate_ruleset(
            self.v1,
            version=self.v2["version"],
        )
        self.assertEqual(reproduced, self.v2)
        self.assertEqual(mappings, self.crosswalk["mappings"])

    def test_crosswalk_maps_every_v1_rule_and_matches_checksums(self) -> None:
        v1_ids = [rule["rule_id"] for rule in self.v1["rules"]]
        mapped_ids = [entry["v1_rule_id"] for entry in self.crosswalk["mappings"]]
        self.assertCountEqual(mapped_ids, v1_ids)
        self.assertTrue(
            all(entry["v2_targets"] for entry in self.crosswalk["mappings"])
        )
        self.assertEqual(
            self.crosswalk["source_ruleset"]["sha256"],
            sha256(V1_PATH),
        )
        self.assertEqual(
            self.crosswalk["target_ruleset"]["sha256"],
            sha256(V2_PATH),
        )

    def test_each_zone_owns_the_same_complete_capability_set(self) -> None:
        r1_6l = self.v2["zones"]["R1-6L"]["regulations"]
        r1_8l = self.v2["zones"]["R1-8L"]["regulations"]
        self.assertEqual(set(r1_6l), set(r1_8l))
        self.assertEqual(len(r1_6l), 10)
        self.assertEqual(len(r1_8l), 10)
        self.assertTrue(
            set(rule["rule_id"] for rule in r1_6l.values()).isdisjoint(
                rule["rule_id"] for rule in r1_8l.values()
            )
        )

    def test_street_side_rules_preserve_zone_specific_semantics(self) -> None:
        r1_6l = self.regulation("R1-6L", "setback.street_side")
        self.assertEqual(r1_6l["requirement"]["base"]["value"]["number"], 10)
        self.assertEqual(
            r1_6l["requirement"]["adjustments"][0]["effect"]["value"][
                "number"
            ],
            15,
        )
        self.assertIsNone(r1_6l["conflict_id"])

        r1_8l = self.regulation("R1-8L", "setback.street_side")
        self.assertEqual(r1_8l["requirement"]["base"]["value"]["number"], 15)
        self.assertEqual(r1_8l["requirement"]["adjustments"], [])
        conflict_id = r1_8l["conflict_id"]
        self.assertEqual(conflict_id, "conflict-r1-8l-corner-side-first")

        conflict = self.v2["conflicts"][conflict_id]
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


if __name__ == "__main__":
    unittest.main()
