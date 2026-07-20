"""Approval, preservation, and runtime tests for residential ruleset v3."""

from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path
from typing import Any

from scripts.promote_residential_rules_v3 import (
    DEFAULT_CANDIDATE,
    DEFAULT_CROSSWALK_NAME,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SCHEMA,
    ResidentialPromotionError,
    build_approval_crosswalk,
    build_approved_ruleset,
    iter_pathways,
    iter_rules,
    json_bytes,
    record_counts,
    semantic_projection,
    validate_promotion,
)
from scripts.validate_residential_rules_v3 import validate_ruleset


ROOT = Path(__file__).resolve().parents[1]
APPROVED_RULESET = DEFAULT_OUTPUT_DIR / "ruleset.json"
APPROVAL_CROSSWALK = DEFAULT_OUTPUT_DIR / DEFAULT_CROSSWALK_NAME
CANDIDATE_CROSSWALK = (
    DEFAULT_CANDIDATE.parent / "patrick-henry-expansion-crosswalk.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ResidentialRulesV3ApprovalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = load_json(DEFAULT_CANDIDATE)
        cls.approved = load_json(APPROVED_RULESET)
        cls.crosswalk = load_json(APPROVAL_CROSSWALK)
        cls.schema = load_json(DEFAULT_SCHEMA)

    def test_approved_artifact_passes_source_domain_and_runtime_gates(self) -> None:
        self.assertEqual(
            validate_ruleset(
                self.approved,
                schema=self.schema,
                repo_root=ROOT,
                verify_source_files=True,
                require_runtime_eligible=True,
            ),
            [],
        )

    def test_approval_lifecycle_identity_is_exact(self) -> None:
        self.assertEqual(self.approved["version"], "2026-07-19.5")
        self.assertEqual(self.approved["schema_version"], "3.2.0")
        self.assertEqual(self.approved["status"], "approved_for_runtime")
        self.assertEqual(self.approved["approved_on"], "2026-07-19")
        self.assertEqual(
            self.approved["predecessor_rulesets"],
            [
                {
                    "ruleset_id": "santa-clara-residential-zoning",
                    "version": "2026-07-19.4",
                    "sha256": sha256(DEFAULT_CANDIDATE),
                    "crosswalk_path": (
                        "rulesets/santa_clara/residential/2026-07-19.5/"
                        "approval-crosswalk.json"
                    ),
                }
            ],
        )

    def test_every_rule_and_pathway_is_approved(self) -> None:
        rules = list(iter_rules(self.approved))
        pathways = list(iter_pathways(self.approved))
        self.assertEqual(len(rules), 196)
        self.assertEqual(len(pathways), 2)
        self.assertTrue(all(rule["approved_for_ruleset"] for rule in rules))
        self.assertTrue(
            all(pathway["approved_for_ruleset"] for pathway in pathways)
        )
        self.assertEqual(record_counts(self.approved)["approved_records"], 198)

    def test_promotion_preserves_every_regulatory_semantic(self) -> None:
        self.assertEqual(
            semantic_projection(self.approved),
            semantic_projection(self.candidate),
        )
        self.assertEqual(set(self.approved["zones"]), set(self.candidate["zones"]))
        self.assertEqual(self.approved["conflicts"], self.candidate["conflicts"])

    def test_approval_crosswalk_is_checksum_pinned_and_exact(self) -> None:
        self.assertEqual(
            self.crosswalk["counts"],
            {
                "zones": 12,
                "use_permissions": 36,
                "analysis_profiles": 16,
                "profile_regulations": 160,
                "special_pathways": 2,
                "conflicts": 4,
                "approved_records": 198,
            },
        )
        self.assertEqual(
            self.crosswalk["source_ruleset"]["sha256"],
            "7e4261277aeb527cd479249a6f580cb6006f5e186c911106c9d4ab9f9ce734b7",
        )
        self.assertEqual(
            self.crosswalk["target_ruleset"]["sha256"],
            sha256(APPROVED_RULESET),
        )
        self.assertIn("Project owner approval", self.crosswalk["decision_source"])

    def test_promotion_and_crosswalk_replay_are_deterministic(self) -> None:
        self.assertEqual(
            validate_promotion(
                self.candidate,
                self.approved,
                self.crosswalk,
                candidate_path=DEFAULT_CANDIDATE,
                target_path=APPROVED_RULESET,
                schema_path=DEFAULT_SCHEMA,
            ),
            [],
        )
        reproduced = build_approved_ruleset(
            self.candidate,
            candidate_path=DEFAULT_CANDIDATE,
            version=self.approved["version"],
            approved_on=self.approved["approved_on"],
            crosswalk_path=self.approved["predecessor_rulesets"][0][
                "crosswalk_path"
            ],
        )
        self.assertEqual(json_bytes(reproduced), APPROVED_RULESET.read_bytes())
        rebuilt_crosswalk = build_approval_crosswalk(
            candidate=self.candidate,
            candidate_path=DEFAULT_CANDIDATE,
            target=reproduced,
            target_path=APPROVED_RULESET,
            schema_path=DEFAULT_SCHEMA,
            target_bytes=json_bytes(reproduced),
        )
        self.assertEqual(json_bytes(rebuilt_crosswalk), APPROVAL_CROSSWALK.read_bytes())

    def test_promotion_rejects_an_already_approved_input(self) -> None:
        with self.assertRaises(ResidentialPromotionError):
            build_approved_ruleset(
                self.approved,
                version="2026-07-19.6",
                approved_on="2026-07-19",
            )

    def test_promotion_requires_a_valid_dated_new_version(self) -> None:
        with self.assertRaises(ResidentialPromotionError):
            build_approved_ruleset(
                self.candidate,
                version="2026-07-20.1",
                approved_on="2026-07-19",
            )
        with self.assertRaises(ResidentialPromotionError):
            build_approved_ruleset(
                self.candidate,
                version=self.candidate["version"],
                approved_on="2026-07-19",
            )
        with self.assertRaises(ResidentialPromotionError):
            build_approved_ruleset(
                self.candidate,
                version="2026-07-19.5",
                approved_on="not-a-date",
            )

    def test_regulatory_mutation_fails_semantic_preservation_gate(self) -> None:
        changed = copy.deepcopy(self.approved)
        changed["zones"]["R5"]["analysis_profiles"]["multifamily"][
            "regulations"
        ]["standard.gross_residential_density"]["requirement"]["maximum"] = 61
        errors = validate_promotion(
            self.candidate,
            changed,
            self.crosswalk,
            candidate_path=DEFAULT_CANDIDATE,
            target_path=APPROVED_RULESET,
            schema_path=DEFAULT_SCHEMA,
        )
        self.assertTrue(
            any("changed regulatory semantics" in error for error in errors)
        )

    def test_reviewed_candidate_inputs_remain_immutable(self) -> None:
        self.assertEqual(
            sha256(DEFAULT_CANDIDATE),
            "7e4261277aeb527cd479249a6f580cb6006f5e186c911106c9d4ab9f9ce734b7",
        )
        self.assertEqual(
            sha256(CANDIDATE_CROSSWALK),
            "e6f789acf82d79ff3ab9dfff462d05779349bab19c3286d1b60a926708fbefea",
        )


if __name__ == "__main__":
    unittest.main()
