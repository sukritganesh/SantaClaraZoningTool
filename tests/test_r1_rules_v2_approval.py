"""Approval and runtime-gate tests for the canonical R1 ruleset v2."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.promote_r1_rules_v2 import (
    DEFAULT_CANDIDATE,
    DEFAULT_CROSSWALK,
    PromotionError,
    build_approved_crosswalk,
    build_approved_ruleset,
)
from scripts.validate_r1_rules_v2 import (
    DEFAULT_SCHEMA,
    DEFAULT_V1_RULESET,
    runtime_eligibility_errors,
    validate_migration,
    validate_ruleset,
)


ROOT = Path(__file__).resolve().parents[1]
APPROVED_DIR = ROOT / "rulesets/santa_clara/r1/2026-07-17.2"
APPROVED_RULESET = APPROVED_DIR / "ruleset.json"
APPROVED_CROSSWALK = APPROVED_DIR / "migration-crosswalk.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class RulesetV2ApprovalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.candidate = load_json(DEFAULT_CANDIDATE)
        cls.candidate_crosswalk = load_json(DEFAULT_CROSSWALK)
        cls.approved = load_json(APPROVED_RULESET)
        cls.approved_crosswalk = load_json(APPROVED_CROSSWALK)
        cls.schema = load_json(DEFAULT_SCHEMA)
        cls.source_v1 = load_json(DEFAULT_V1_RULESET)

    def test_approved_artifact_passes_domain_source_and_runtime_gates(self) -> None:
        domain_errors = validate_ruleset(
            self.approved,
            schema=self.schema,
            repo_root=ROOT,
            verify_source_files=True,
        )
        self.assertEqual(domain_errors, [])
        self.assertEqual(
            runtime_eligibility_errors(self.approved, domain_errors=domain_errors),
            [],
        )

    def test_approved_artifact_passes_migration_replay(self) -> None:
        self.assertEqual(
            validate_migration(
                self.approved,
                self.approved_crosswalk,
                self.source_v1,
                ruleset_path=APPROVED_RULESET,
                schema_path=DEFAULT_SCHEMA,
                source_v1_path=DEFAULT_V1_RULESET,
                repo_root=ROOT,
            ),
            [],
        )

    def test_promotion_changes_only_version_and_approval_metadata(self) -> None:
        expected = build_approved_ruleset(
            self.candidate,
            version="2026-07-17.2",
            approved_on="2026-07-17",
        )
        self.assertEqual(self.approved, expected)

    def test_approved_crosswalk_is_deterministic(self) -> None:
        target_bytes = (json.dumps(self.approved, indent=2, ensure_ascii=False) + "\n").encode(
            "utf-8"
        )
        expected = build_approved_crosswalk(
            self.candidate_crosswalk,
            target_path=APPROVED_RULESET,
            approved=self.approved,
            target_bytes=target_bytes,
            approved_on="2026-07-17",
        )
        self.assertEqual(self.approved_crosswalk, expected)

    def test_promotion_rejects_an_already_approved_input(self) -> None:
        with self.assertRaises(PromotionError):
            build_approved_ruleset(
                self.approved,
                version="2026-07-17.3",
                approved_on="2026-07-17",
            )

    def test_promotion_requires_dated_version_identity(self) -> None:
        with self.assertRaises(PromotionError):
            build_approved_ruleset(
                self.candidate,
                version="2026-07-18.1",
                approved_on="2026-07-17",
            )

    def test_promotion_requires_a_new_version_identity(self) -> None:
        with self.assertRaises(PromotionError):
            build_approved_ruleset(
                self.candidate,
                version=self.candidate["version"],
                approved_on="2026-07-17",
            )


if __name__ == "__main__":
    unittest.main()
