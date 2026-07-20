#!/usr/bin/env python3
"""Validate the approved 12-zone residential ruleset and its complete lineage."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.author_citywide_residential_rules import (  # noqa: E402
    DEFAULT_SOURCE as R1_V3_CANDIDATE,
    DEFAULT_SOURCE_SCHEMA as R1_V3_SCHEMA,
    validate_expansion as validate_citywide_expansion,
)
from scripts.author_density_residential_rules import (  # noqa: E402
    DEFAULT_SOURCE as CITYWIDE_CANDIDATE,
    DEFAULT_SOURCE_SCHEMA as CITYWIDE_PREDECESSOR_SCHEMA,
    validate_expansion as validate_density_expansion,
)
from scripts.author_patrick_henry_residential_rules import (  # noqa: E402
    DEFAULT_SCHEMA,
    DEFAULT_SOURCE as DENSITY_CANDIDATE,
    DEFAULT_SOURCE_SCHEMA as DENSITY_PREDECESSOR_SCHEMA,
    validate_expansion as validate_patrick_henry_expansion,
)
from scripts.migrate_r1_rules_v3 import DEFAULT_SOURCE as APPROVED_R1_V2  # noqa: E402
from scripts.migrate_r1_rules_v3 import validate_migration  # noqa: E402
from scripts.promote_residential_rules_v3 import (  # noqa: E402
    DEFAULT_CANDIDATE,
    DEFAULT_CANDIDATE_CROSSWALK,
    DEFAULT_CROSSWALK_NAME,
    DEFAULT_OUTPUT_DIR,
    validate_promotion,
)
from scripts.validate_r1_rules import load_json  # noqa: E402
from scripts.validate_residential_rules_v3 import (  # noqa: E402
    DEFAULT_GIS_FIXTURES,
    validate_gis_fixture_contract,
    validate_ruleset,
)


DEFAULT_RULESET = DEFAULT_OUTPUT_DIR / "ruleset.json"
DEFAULT_APPROVAL_CROSSWALK = DEFAULT_OUTPUT_DIR / DEFAULT_CROSSWALK_NAME
DEFAULT_DENSITY_CROSSWALK = (
    DENSITY_CANDIDATE.parent / "density-expansion-crosswalk.json"
)
DEFAULT_CITYWIDE_CROSSWALK = (
    CITYWIDE_CANDIDATE.parent / "citywide-expansion-crosswalk.json"
)
DEFAULT_R1_MIGRATION_CROSSWALK = (
    R1_V3_CANDIDATE.parent / "migration-crosswalk.json"
)


@dataclass(frozen=True)
class ResidentialRulesetArtifacts:
    """Every immutable artifact required to prove approved v3 runtime lineage."""

    ruleset: Path
    schema: Path
    approval_crosswalk: Path
    candidate: Path
    candidate_crosswalk: Path
    density_predecessor: Path
    density_predecessor_schema: Path
    density_crosswalk: Path
    citywide_predecessor: Path
    citywide_predecessor_schema: Path
    citywide_crosswalk: Path
    r1_v3_candidate: Path
    r1_v3_schema: Path
    r1_migration_crosswalk: Path
    approved_r1_v2: Path
    gis_fixtures: Path

    def resolved(self) -> "ResidentialRulesetArtifacts":
        """Return an equivalent artifact set with absolute normalized paths."""

        return ResidentialRulesetArtifacts(
            **{
                item.name: getattr(self, item.name).resolve()
                for item in fields(self)
            }
        )


DEFAULT_APPROVED_RESIDENTIAL_ARTIFACTS = ResidentialRulesetArtifacts(
    ruleset=DEFAULT_RULESET,
    schema=DEFAULT_SCHEMA,
    approval_crosswalk=DEFAULT_APPROVAL_CROSSWALK,
    candidate=DEFAULT_CANDIDATE,
    candidate_crosswalk=DEFAULT_CANDIDATE_CROSSWALK,
    density_predecessor=DENSITY_CANDIDATE,
    density_predecessor_schema=DENSITY_PREDECESSOR_SCHEMA,
    density_crosswalk=DEFAULT_DENSITY_CROSSWALK,
    citywide_predecessor=CITYWIDE_CANDIDATE,
    citywide_predecessor_schema=CITYWIDE_PREDECESSOR_SCHEMA,
    citywide_crosswalk=DEFAULT_CITYWIDE_CROSSWALK,
    r1_v3_candidate=R1_V3_CANDIDATE,
    r1_v3_schema=R1_V3_SCHEMA,
    r1_migration_crosswalk=DEFAULT_R1_MIGRATION_CROSSWALK,
    approved_r1_v2=APPROVED_R1_V2,
    gis_fixtures=DEFAULT_GIS_FIXTURES,
)


@dataclass(frozen=True)
class LoadedApprovedResidentialLineage:
    """One in-memory snapshot of the complete approved residential lineage."""

    artifacts: ResidentialRulesetArtifacts
    ruleset: dict[str, Any]
    schema: dict[str, Any]
    approval_crosswalk: dict[str, Any]
    candidate: dict[str, Any]
    candidate_crosswalk: dict[str, Any]
    density_predecessor: dict[str, Any]
    density_predecessor_schema: dict[str, Any]
    density_crosswalk: dict[str, Any]
    citywide_predecessor: dict[str, Any]
    citywide_predecessor_schema: dict[str, Any]
    citywide_crosswalk: dict[str, Any]
    r1_v3_candidate: dict[str, Any]
    r1_v3_schema: dict[str, Any]
    r1_migration_crosswalk: dict[str, Any]
    approved_r1_v2: dict[str, Any]
    gis_fixtures: dict[str, Any]


def load_approved_residential_lineage(
    artifacts: ResidentialRulesetArtifacts = DEFAULT_APPROVED_RESIDENTIAL_ARTIFACTS,
) -> LoadedApprovedResidentialLineage:
    """Load every lineage artifact exactly once without validating it."""

    paths = artifacts.resolved()
    return LoadedApprovedResidentialLineage(
        artifacts=paths,
        ruleset=load_json(paths.ruleset),
        schema=load_json(paths.schema),
        approval_crosswalk=load_json(paths.approval_crosswalk),
        candidate=load_json(paths.candidate),
        candidate_crosswalk=load_json(paths.candidate_crosswalk),
        density_predecessor=load_json(paths.density_predecessor),
        density_predecessor_schema=load_json(paths.density_predecessor_schema),
        density_crosswalk=load_json(paths.density_crosswalk),
        citywide_predecessor=load_json(paths.citywide_predecessor),
        citywide_predecessor_schema=load_json(paths.citywide_predecessor_schema),
        citywide_crosswalk=load_json(paths.citywide_crosswalk),
        r1_v3_candidate=load_json(paths.r1_v3_candidate),
        r1_v3_schema=load_json(paths.r1_v3_schema),
        r1_migration_crosswalk=load_json(paths.r1_migration_crosswalk),
        approved_r1_v2=load_json(paths.approved_r1_v2),
        gis_fixtures=load_json(paths.gis_fixtures),
    )


def validate_complete_approved_lineage(
    lineage: LoadedApprovedResidentialLineage,
    *,
    repo_root: Path = REPO_ROOT,
    verify_source_files: bool = False,
) -> list[str]:
    """Return all source, replay, approval, and runtime-lineage errors."""

    paths = lineage.artifacts
    r1_errors = validate_ruleset(
        lineage.r1_v3_candidate,
        schema=lineage.r1_v3_schema,
        repo_root=repo_root,
        verify_source_files=verify_source_files,
    )
    errors = list(r1_errors)
    if not r1_errors:
        errors.extend(
            validate_migration(
                lineage.approved_r1_v2,
                lineage.r1_v3_candidate,
                lineage.r1_migration_crosswalk,
                source_path=paths.approved_r1_v2,
                target_path=paths.r1_v3_candidate,
                schema_path=paths.r1_v3_schema,
            )
        )

    citywide_errors = validate_ruleset(
        lineage.citywide_predecessor,
        schema=lineage.citywide_predecessor_schema,
        repo_root=repo_root,
        verify_source_files=verify_source_files,
    )
    errors.extend(citywide_errors)
    if not r1_errors and not citywide_errors:
        errors.extend(
            validate_citywide_expansion(
                lineage.r1_v3_candidate,
                lineage.citywide_predecessor,
                lineage.citywide_crosswalk,
                source_path=paths.r1_v3_candidate,
                target_path=paths.citywide_predecessor,
                schema_path=paths.citywide_predecessor_schema,
            )
        )

    density_errors = validate_ruleset(
        lineage.density_predecessor,
        schema=lineage.density_predecessor_schema,
        repo_root=repo_root,
        verify_source_files=verify_source_files,
    )
    errors.extend(density_errors)
    if not citywide_errors and not density_errors:
        errors.extend(
            validate_density_expansion(
                lineage.citywide_predecessor,
                lineage.density_predecessor,
                lineage.density_crosswalk,
                source_path=paths.citywide_predecessor,
                target_path=paths.density_predecessor,
                schema_path=paths.density_predecessor_schema,
            )
        )

    candidate_errors = validate_ruleset(
        lineage.candidate,
        schema=lineage.schema,
        repo_root=repo_root,
        verify_source_files=verify_source_files,
    )
    errors.extend(candidate_errors)
    if not density_errors and not candidate_errors:
        errors.extend(
            validate_patrick_henry_expansion(
                lineage.density_predecessor,
                lineage.candidate,
                lineage.candidate_crosswalk,
                source_path=paths.density_predecessor,
                target_path=paths.candidate,
                schema_path=paths.schema,
            )
        )

    target_errors = validate_ruleset(
        lineage.ruleset,
        schema=lineage.schema,
        repo_root=repo_root,
        verify_source_files=verify_source_files,
        require_runtime_eligible=True,
    )
    errors.extend(target_errors)
    if not candidate_errors and not target_errors:
        errors.extend(
            validate_promotion(
                lineage.candidate,
                lineage.ruleset,
                lineage.approval_crosswalk,
                candidate_path=paths.candidate,
                target_path=paths.ruleset,
                schema_path=paths.schema,
            )
        )
    errors.extend(validate_gis_fixture_contract(lineage.gis_fixtures))
    return errors


def main(argv: Optional[list[str]] = None) -> int:
    """Run the complete source, lineage, replay, approval, and runtime gates."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ruleset", type=Path, default=DEFAULT_RULESET)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument(
        "--approval-crosswalk", type=Path, default=DEFAULT_APPROVAL_CROSSWALK
    )
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument(
        "--candidate-crosswalk", type=Path, default=DEFAULT_CANDIDATE_CROSSWALK
    )
    parser.add_argument(
        "--density-predecessor", type=Path, default=DENSITY_CANDIDATE
    )
    parser.add_argument(
        "--density-predecessor-schema",
        type=Path,
        default=DENSITY_PREDECESSOR_SCHEMA,
    )
    parser.add_argument(
        "--density-crosswalk", type=Path, default=DEFAULT_DENSITY_CROSSWALK
    )
    parser.add_argument(
        "--citywide-predecessor", type=Path, default=CITYWIDE_CANDIDATE
    )
    parser.add_argument(
        "--citywide-predecessor-schema",
        type=Path,
        default=CITYWIDE_PREDECESSOR_SCHEMA,
    )
    parser.add_argument(
        "--citywide-crosswalk", type=Path, default=DEFAULT_CITYWIDE_CROSSWALK
    )
    parser.add_argument("--r1-v3-candidate", type=Path, default=R1_V3_CANDIDATE)
    parser.add_argument("--r1-v3-schema", type=Path, default=R1_V3_SCHEMA)
    parser.add_argument(
        "--r1-migration-crosswalk",
        type=Path,
        default=DEFAULT_R1_MIGRATION_CROSSWALK,
    )
    parser.add_argument("--approved-r1-v2", type=Path, default=APPROVED_R1_V2)
    parser.add_argument("--gis-fixtures", type=Path, default=DEFAULT_GIS_FIXTURES)
    parser.add_argument("--verify-source-files", action="store_true")
    args = parser.parse_args(argv)

    artifacts = ResidentialRulesetArtifacts(
        ruleset=args.ruleset,
        schema=args.schema,
        approval_crosswalk=args.approval_crosswalk,
        candidate=args.candidate,
        candidate_crosswalk=args.candidate_crosswalk,
        density_predecessor=args.density_predecessor,
        density_predecessor_schema=args.density_predecessor_schema,
        density_crosswalk=args.density_crosswalk,
        citywide_predecessor=args.citywide_predecessor,
        citywide_predecessor_schema=args.citywide_predecessor_schema,
        citywide_crosswalk=args.citywide_crosswalk,
        r1_v3_candidate=args.r1_v3_candidate,
        r1_v3_schema=args.r1_v3_schema,
        r1_migration_crosswalk=args.r1_migration_crosswalk,
        approved_r1_v2=args.approved_r1_v2,
        gis_fixtures=args.gis_fixtures,
    )
    lineage = load_approved_residential_lineage(artifacts)
    errors = validate_complete_approved_lineage(
        lineage,
        verify_source_files=args.verify_source_files,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "Validated approved 12-zone residential ruleset, runtime eligibility, and "
        f"complete approved-v2-to-v3.2 lineage: {args.ruleset}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
