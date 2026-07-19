"""Runtime-loader tests for the approved Santa Clara R1 ruleset v2."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from santa_clara_zoning.ruleset import (
    DEFAULT_APPROVED_ARTIFACTS,
    REPO_ROOT,
    ApprovedR1Ruleset,
    RulesetArtifacts,
    RulesetLoadError,
)


CANDIDATE_DIR = REPO_ROOT / "rulesets/santa_clara/r1/2026-07-17"
CANDIDATE_ARTIFACTS = RulesetArtifacts(
    ruleset=CANDIDATE_DIR / "ruleset.json",
    schema=DEFAULT_APPROVED_ARTIFACTS.schema,
    crosswalk=CANDIDATE_DIR / "migration-crosswalk.json",
    source_v1=DEFAULT_APPROVED_ARTIFACTS.source_v1,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


@contextmanager
def modified_artifacts(
    ruleset: dict[str, Any],
    crosswalk: dict[str, Any],
) -> Iterator[RulesetArtifacts]:
    """Write a self-consistent target manifest around deliberately changed data."""

    with tempfile.TemporaryDirectory(prefix=".ruleset-loader-test-", dir=REPO_ROOT) as raw:
        directory = Path(raw)
        ruleset_path = directory / "ruleset.json"
        crosswalk_path = directory / "migration-crosswalk.json"
        ruleset_content = json_bytes(ruleset)
        ruleset_path.write_bytes(ruleset_content)

        changed_crosswalk = copy.deepcopy(crosswalk)
        changed_crosswalk["target_ruleset"].update(
            {
                "path": ruleset_path.relative_to(REPO_ROOT).as_posix(),
                "version": ruleset["version"],
                "schema_version": ruleset["schema_version"],
                "status": ruleset["status"],
                "sha256": hashlib.sha256(ruleset_content).hexdigest(),
            }
        )
        crosswalk_path.write_bytes(json_bytes(changed_crosswalk))
        yield RulesetArtifacts(
            ruleset=ruleset_path,
            schema=DEFAULT_APPROVED_ARTIFACTS.schema,
            crosswalk=crosswalk_path,
            source_v1=DEFAULT_APPROVED_ARTIFACTS.source_v1,
        )


class ApprovedR1RulesetLoaderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.canonical_ruleset = load_json(DEFAULT_APPROVED_ARTIFACTS.ruleset)
        cls.canonical_crosswalk = load_json(DEFAULT_APPROVED_ARTIFACTS.crosswalk)

    def assert_rejected(
        self,
        artifacts: RulesetArtifacts,
        *,
        stage: str,
        evidence: str,
    ) -> None:
        with self.assertRaises(RulesetLoadError) as caught:
            ApprovedR1Ruleset.load(artifacts)
        self.assertEqual(caught.exception.stage, stage)
        self.assertIn(evidence, str(caught.exception))

    def test_canonical_approved_ruleset_loads_once_into_runtime_view(self) -> None:
        loaded = ApprovedR1Ruleset.load()
        self.assertEqual(loaded.ruleset_id, "santa-clara-r1-base-zone")
        self.assertEqual(loaded.version, "2026-07-17.2")
        self.assertEqual(loaded.approved_on, "2026-07-17")
        self.assertEqual(loaded.verified_through, "2026-07-16")
        self.assertEqual(loaded.jurisdiction["name"], "City of Santa Clara")
        self.assertEqual(loaded.supported_zones, ("R1-6L", "R1-8L"))
        self.assertEqual(loaded.regulation_count, 20)

    def test_defensive_copies_cannot_mutate_authoritative_state(self) -> None:
        loaded = ApprovedR1Ruleset.load()
        changed = loaded.as_dict()
        changed["zones"]["R1-6L"]["regulations"].clear()
        changed["jurisdiction"]["name"] = "Changed"

        fresh = loaded.as_dict()
        self.assertEqual(len(fresh["zones"]["R1-6L"]["regulations"]), 10)
        self.assertEqual(fresh["jurisdiction"]["name"], "City of Santa Clara")

    def test_repeated_loads_are_equivalent_and_independent(self) -> None:
        first = ApprovedR1Ruleset.load()
        second = ApprovedR1Ruleset.load()
        self.assertEqual(first.as_dict(), second.as_dict())
        self.assertIsNot(first, second)
        self.assertIsNot(first.as_dict(), second.as_dict())

    def test_candidate_is_rejected_by_runtime_gate(self) -> None:
        self.assert_rejected(
            CANDIDATE_ARTIFACTS,
            stage="runtime eligibility",
            evidence="status is not approved_for_prototype",
        )

    def test_missing_required_capability_is_rejected_before_runtime(self) -> None:
        changed = copy.deepcopy(self.canonical_ruleset)
        del changed["zones"]["R1-6L"]["regulations"]["setback.rear"]
        with modified_artifacts(changed, self.canonical_crosswalk) as artifacts:
            self.assert_rejected(
                artifacts,
                stage="schema/domain validation",
                evidence="missing capabilities",
            )

    def test_changed_regulatory_value_is_rejected_by_migration_replay(self) -> None:
        changed = copy.deepcopy(self.canonical_ruleset)
        changed["zones"]["R1-6L"]["regulations"][
            "standard.maximum_primary_structure_height"
        ]["requirement"]["value"]["number"] = 26
        with modified_artifacts(changed, self.canonical_crosswalk) as artifacts:
            self.assert_rejected(
                artifacts,
                stage="migration validation",
                evidence="differs from deterministic migration replay",
            )

    def test_changed_source_checksum_is_rejected(self) -> None:
        changed = copy.deepcopy(self.canonical_ruleset)
        changed["shared"]["source_documents"]["sc-title18-2025-07"][
            "sha256"
        ] = "0" * 64
        with modified_artifacts(changed, self.canonical_crosswalk) as artifacts:
            self.assert_rejected(
                artifacts,
                stage="schema/domain validation",
                evidence="checksum does not match",
            )

    def test_broken_crosswalk_is_rejected(self) -> None:
        changed_crosswalk = copy.deepcopy(self.canonical_crosswalk)
        changed_crosswalk["mappings"].pop()
        with modified_artifacts(
            copy.deepcopy(self.canonical_ruleset),
            changed_crosswalk,
        ) as artifacts:
            self.assert_rejected(
                artifacts,
                stage="migration validation",
                evidence="mappings omit v1 rules",
            )

    def test_missing_artifact_is_reported_as_loading_failure(self) -> None:
        missing = RulesetArtifacts(
            ruleset=REPO_ROOT / "rulesets/does-not-exist.json",
            schema=DEFAULT_APPROVED_ARTIFACTS.schema,
            crosswalk=DEFAULT_APPROVED_ARTIFACTS.crosswalk,
            source_v1=DEFAULT_APPROVED_ARTIFACTS.source_v1,
        )
        self.assert_rejected(
            missing,
            stage="artifact loading",
            evidence="Could not read ruleset",
        )


if __name__ == "__main__":
    unittest.main()
