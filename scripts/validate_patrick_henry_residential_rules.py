#!/usr/bin/env python3
"""Validate the complete nonruntime 12-zone candidate and chained lineage."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.author_citywide_residential_rules import (  # noqa: E402
    DEFAULT_SCHEMA as CITYWIDE_SCHEMA,
    DEFAULT_SOURCE as R1_V3_CANDIDATE,
    DEFAULT_SOURCE_SCHEMA as R1_V3_SCHEMA,
    validate_expansion as validate_citywide_expansion,
)
from scripts.author_density_residential_rules import (  # noqa: E402
    DEFAULT_SCHEMA as DENSITY_SCHEMA,
    DEFAULT_SOURCE as CITYWIDE_CANDIDATE,
    DEFAULT_SOURCE_SCHEMA as CITYWIDE_PREDECESSOR_SCHEMA,
    validate_expansion as validate_density_expansion,
)
from scripts.author_patrick_henry_residential_rules import (  # noqa: E402
    DEFAULT_CROSSWALK_NAME,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SCHEMA,
    DEFAULT_SOURCE,
    DEFAULT_SOURCE_SCHEMA,
    validate_expansion as validate_patrick_henry_expansion,
)
from scripts.migrate_r1_rules_v3 import DEFAULT_SOURCE as APPROVED_R1_V2  # noqa: E402
from scripts.migrate_r1_rules_v3 import validate_migration  # noqa: E402
from scripts.validate_r1_rules import load_json  # noqa: E402
from scripts.validate_residential_rules_v3 import (  # noqa: E402
    DEFAULT_GIS_FIXTURES,
    validate_gis_fixture_contract,
    validate_ruleset,
)


DEFAULT_RULESET = DEFAULT_OUTPUT_DIR / "ruleset.json"
DEFAULT_CROSSWALK = DEFAULT_OUTPUT_DIR / DEFAULT_CROSSWALK_NAME
DEFAULT_DENSITY_CROSSWALK = DEFAULT_SOURCE.parent / "density-expansion-crosswalk.json"
DEFAULT_CITYWIDE_CROSSWALK = CITYWIDE_CANDIDATE.parent / "citywide-expansion-crosswalk.json"
DEFAULT_R1_MIGRATION_CROSSWALK = R1_V3_CANDIDATE.parent / "migration-crosswalk.json"


def main(argv: Optional[list[str]] = None) -> int:
    """Run schema, source, lineage, replay, approval, and GIS-fixture checks."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ruleset", type=Path, default=DEFAULT_RULESET)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--predecessor", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--predecessor-schema", type=Path, default=DEFAULT_SOURCE_SCHEMA)
    parser.add_argument("--density-predecessor", type=Path, default=CITYWIDE_CANDIDATE)
    parser.add_argument(
        "--density-predecessor-schema",
        type=Path,
        default=CITYWIDE_PREDECESSOR_SCHEMA,
    )
    parser.add_argument(
        "--density-crosswalk",
        type=Path,
        default=DEFAULT_DENSITY_CROSSWALK,
    )
    parser.add_argument("--citywide-predecessor", type=Path, default=R1_V3_CANDIDATE)
    parser.add_argument(
        "--citywide-predecessor-schema",
        type=Path,
        default=R1_V3_SCHEMA,
    )
    parser.add_argument(
        "--citywide-crosswalk",
        type=Path,
        default=DEFAULT_CITYWIDE_CROSSWALK,
    )
    parser.add_argument(
        "--r1-migration-crosswalk",
        type=Path,
        default=DEFAULT_R1_MIGRATION_CROSSWALK,
    )
    parser.add_argument("--approved-r1-v2", type=Path, default=APPROVED_R1_V2)
    parser.add_argument("--gis-fixtures", type=Path, default=DEFAULT_GIS_FIXTURES)
    parser.add_argument("--verify-source-files", action="store_true")
    parser.add_argument("--require-runtime-eligible", action="store_true")
    args = parser.parse_args(argv)

    target_path = args.ruleset.resolve()
    schema_path = args.schema.resolve()
    source_path = args.predecessor.resolve()
    source_schema_path = args.predecessor_schema.resolve()
    density_predecessor_path = args.density_predecessor.resolve()
    density_predecessor_schema_path = args.density_predecessor_schema.resolve()
    citywide_predecessor_path = args.citywide_predecessor.resolve()
    citywide_predecessor_schema_path = args.citywide_predecessor_schema.resolve()
    approved_r1_v2_path = args.approved_r1_v2.resolve()

    target = load_json(target_path)
    source = load_json(source_path)
    density_predecessor = load_json(density_predecessor_path)
    citywide_predecessor = load_json(citywide_predecessor_path)
    errors = validate_ruleset(
        citywide_predecessor,
        schema=load_json(citywide_predecessor_schema_path),
        verify_source_files=args.verify_source_files,
    )
    errors.extend(
        validate_migration(
            load_json(approved_r1_v2_path),
            citywide_predecessor,
            load_json(args.r1_migration_crosswalk),
            source_path=approved_r1_v2_path,
            target_path=citywide_predecessor_path,
            schema_path=citywide_predecessor_schema_path,
        )
    )
    errors.extend(
        validate_ruleset(
            density_predecessor,
            schema=load_json(density_predecessor_schema_path),
            verify_source_files=args.verify_source_files,
        )
    )
    errors.extend(
        validate_citywide_expansion(
            citywide_predecessor,
            density_predecessor,
            load_json(args.citywide_crosswalk),
            source_path=citywide_predecessor_path,
            target_path=density_predecessor_path,
            schema_path=CITYWIDE_SCHEMA,
        )
    )
    errors.extend(
        validate_ruleset(
            source,
            schema=load_json(source_schema_path),
            verify_source_files=args.verify_source_files,
        )
    )
    errors.extend(
        validate_density_expansion(
            density_predecessor,
            source,
            load_json(args.density_crosswalk),
            source_path=density_predecessor_path,
            target_path=source_path,
            schema_path=DENSITY_SCHEMA,
        )
    )
    errors.extend(
        validate_ruleset(
            target,
            schema=load_json(schema_path),
            verify_source_files=args.verify_source_files,
            require_runtime_eligible=args.require_runtime_eligible,
        )
    )
    errors.extend(
        validate_patrick_henry_expansion(
            source,
            target,
            load_json(args.crosswalk),
            source_path=source_path,
            target_path=target_path,
            schema_path=schema_path,
        )
    )
    errors.extend(validate_gis_fixture_contract(load_json(args.gis_fixtures)))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "Validated complete 12-zone residential candidate and approved-v2-to-v3.2 "
        f"lineage: {args.ruleset} (runtime eligibility required: "
        f"{args.require_runtime_eligible})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
