"""Runtime-loader gates for the approved Santa Clara residential ruleset."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterator, Optional
from unittest.mock import patch

from santa_clara_zoning import (
    ApprovedResidentialRuleset,
    ResidentialRulesetArtifacts,
    RulesetLoadError,
)
from santa_clara_zoning.ruleset import REPO_ROOT
from scripts.validate_approved_residential_rules import (
    DEFAULT_APPROVED_RESIDENTIAL_ARTIFACTS,
    load_approved_residential_lineage,
    validate_complete_approved_lineage,
)


TARGET_ZONES = (
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
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


@contextmanager
def modified_artifact(
    field: str,
    value: dict[str, Any],
    *,
    content: Optional[bytes] = None,
) -> Iterator[ResidentialRulesetArtifacts]:
    """Replace one lineage file with a temporary JSON artifact."""

    with tempfile.TemporaryDirectory(
        prefix=".residential-loader-test-",
        dir=REPO_ROOT,
    ) as raw:
        directory = Path(raw)
        original = getattr(DEFAULT_APPROVED_RESIDENTIAL_ARTIFACTS, field)
        path = directory / original.name
        path.write_bytes(content if content is not None else json_bytes(value))
        yield replace(DEFAULT_APPROVED_RESIDENTIAL_ARTIFACTS, **{field: path})


class ApprovedResidentialRulesetLoaderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.approved = load_json(
            DEFAULT_APPROVED_RESIDENTIAL_ARTIFACTS.ruleset
        )
        cls.approval_crosswalk = load_json(
            DEFAULT_APPROVED_RESIDENTIAL_ARTIFACTS.approval_crosswalk
        )
        cls.citywide_crosswalk = load_json(
            DEFAULT_APPROVED_RESIDENTIAL_ARTIFACTS.citywide_crosswalk
        )

    def assert_rejected(
        self,
        artifacts: ResidentialRulesetArtifacts,
        *,
        stage: str,
        evidence: str,
    ) -> None:
        with self.assertRaises(RulesetLoadError) as caught:
            ApprovedResidentialRuleset.load(artifacts)
        self.assertEqual(caught.exception.ruleset_name, "residential")
        self.assertEqual(caught.exception.stage, stage)
        self.assertIn(evidence, str(caught.exception))

    def test_callable_complete_lineage_gate_accepts_canonical_artifacts(self) -> None:
        lineage = load_approved_residential_lineage()
        self.assertEqual(
            validate_complete_approved_lineage(
                lineage,
                repo_root=REPO_ROOT,
                verify_source_files=True,
            ),
            [],
        )
        self.assertEqual(lineage.ruleset["version"], "2026-07-19.5")
        self.assertEqual(
            lineage.artifacts,
            DEFAULT_APPROVED_RESIDENTIAL_ARTIFACTS.resolved(),
        )

    def test_canonical_approved_ruleset_loads_into_residential_view(self) -> None:
        loaded = ApprovedResidentialRuleset.load()
        self.assertEqual(loaded.ruleset_id, "santa-clara-residential-zoning")
        self.assertEqual(loaded.version, "2026-07-19.5")
        self.assertEqual(loaded.schema_version, "3.2.0")
        self.assertEqual(loaded.approved_on, "2026-07-19")
        self.assertEqual(loaded.verified_through, "2026-07-18")
        self.assertEqual(loaded.jurisdiction["name"], "City of Santa Clara")
        self.assertEqual(loaded.supported_zones, TARGET_ZONES)
        self.assertEqual(loaded.regulation_count, 196)
        self.assertEqual(loaded.analysis_profile_count, 16)
        self.assertEqual(loaded.special_pathway_count, 2)

    def test_authoritative_state_is_recursively_frozen(self) -> None:
        loaded = ApprovedResidentialRuleset.load()
        with self.assertRaises(TypeError):
            loaded._data["zones"]["R2"] = {}  # type: ignore[index]
        conditions = loaded._data["zones"]["R2"]["use_permissions"][
            "use.two_family_dwelling"
        ]["conditions"]
        self.assertIsInstance(conditions, tuple)
        with self.assertRaises(TypeError):
            conditions[0] = "Changed"  # type: ignore[index]

    def test_defensive_copies_cannot_mutate_authoritative_state(self) -> None:
        loaded = ApprovedResidentialRuleset.load()
        changed = loaded.as_dict()
        changed["zones"]["R2"]["use_permissions"].clear()
        changed["zones"]["PH-R5"]["analysis_profiles"]["multifamily"][
            "regulations"
        ].clear()
        changed["jurisdiction"]["name"] = "Changed"

        fresh = loaded.as_dict()
        self.assertEqual(len(fresh["zones"]["R2"]["use_permissions"]), 3)
        self.assertEqual(
            len(
                fresh["zones"]["PH-R5"]["analysis_profiles"][
                    "multifamily"
                ]["regulations"]
            ),
            10,
        )
        self.assertEqual(fresh["jurisdiction"]["name"], "City of Santa Clara")

    def test_repeated_loads_are_equivalent_and_independent(self) -> None:
        first = ApprovedResidentialRuleset.load()
        second = ApprovedResidentialRuleset.load()
        self.assertEqual(first.as_dict(), second.as_dict())
        self.assertIsNot(first, second)
        self.assertIsNot(first.as_dict(), second.as_dict())

    def test_complete_candidate_is_rejected_by_runtime_gate(self) -> None:
        artifacts = replace(
            DEFAULT_APPROVED_RESIDENTIAL_ARTIFACTS,
            ruleset=DEFAULT_APPROVED_RESIDENTIAL_ARTIFACTS.candidate,
        )
        self.assert_rejected(
            artifacts,
            stage="complete lineage validation",
            evidence="runtime eligibility requires status approved_for_runtime",
        )

    def test_changed_source_checksum_is_rejected(self) -> None:
        changed = copy.deepcopy(self.approved)
        changed["shared"]["source_documents"]["sc-title18-2025-07"][
            "sha256"
        ] = "0" * 64
        with modified_artifact("ruleset", changed) as artifacts:
            self.assert_rejected(
                artifacts,
                stage="complete lineage validation",
                evidence="checksum does not match",
            )

    def test_byte_changed_target_is_rejected_by_crosswalk_checksum(self) -> None:
        compact = json.dumps(
            self.approved,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        with modified_artifact(
            "ruleset",
            self.approved,
            content=compact,
        ) as artifacts:
            self.assert_rejected(
                artifacts,
                stage="complete lineage validation",
                evidence="target_ruleset.sha256 does not match its artifact",
            )

    def test_regulatory_mutation_is_rejected_by_semantic_gate(self) -> None:
        changed = copy.deepcopy(self.approved)
        changed["zones"]["R5"]["analysis_profiles"]["multifamily"][
            "regulations"
        ]["standard.gross_residential_density"]["conditions"].append(
            "Deliberate semantic mutation."
        )
        with modified_artifact("ruleset", changed) as artifacts:
            self.assert_rejected(
                artifacts,
                stage="complete lineage validation",
                evidence="approved target changed regulatory semantics",
            )

    def test_unapproved_record_is_rejected_by_runtime_gate(self) -> None:
        changed = copy.deepcopy(self.approved)
        changed["zones"]["R2"]["analysis_profiles"]["two_family"][
            "regulations"
        ]["setback.rear"]["approved_for_ruleset"] = False
        with modified_artifact("ruleset", changed) as artifacts:
            self.assert_rejected(
                artifacts,
                stage="complete lineage validation",
                evidence="runtime ruleset has unapproved rules",
            )

    def test_broken_earlier_crosswalk_is_rejected_by_lineage_gate(self) -> None:
        changed = copy.deepcopy(self.citywide_crosswalk)
        changed["added_zone_profiles"]["R2"] = ["multifamily"]
        with modified_artifact("citywide_crosswalk", changed) as artifacts:
            self.assert_rejected(
                artifacts,
                stage="complete lineage validation",
                evidence="approved citywide matrix",
            )

    def test_changed_approval_crosswalk_is_rejected(self) -> None:
        changed = copy.deepcopy(self.approval_crosswalk)
        changed["semantic_projection_sha256"] = "0" * 64
        with modified_artifact("approval_crosswalk", changed) as artifacts:
            self.assert_rejected(
                artifacts,
                stage="complete lineage validation",
                evidence="semantic projection checksum does not match",
            )

    def test_missing_predecessor_is_reported_as_artifact_loading_failure(self) -> None:
        artifacts = replace(
            DEFAULT_APPROVED_RESIDENTIAL_ARTIFACTS,
            density_predecessor=(
                REPO_ROOT / "rulesets/santa_clara/residential/missing.json"
            ),
        )
        self.assert_rejected(
            artifacts,
            stage="artifact loading",
            evidence="missing.json",
        )

    def test_unexpected_validator_exception_is_wrapped_fail_closed(self) -> None:
        with patch(
            "santa_clara_zoning.ruleset.validate_complete_approved_lineage",
            side_effect=RuntimeError("deliberate validator failure"),
        ):
            self.assert_rejected(
                DEFAULT_APPROVED_RESIDENTIAL_ARTIFACTS,
                stage="complete lineage validation",
                evidence="validator raised RuntimeError",
            )


if __name__ == "__main__":
    unittest.main()
