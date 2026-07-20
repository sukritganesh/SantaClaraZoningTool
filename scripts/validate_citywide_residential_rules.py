#!/usr/bin/env python3
"""Validate the nonruntime R1-R6 citywide residential candidate and lineage."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.author_citywide_residential_rules import (  # noqa: E402
    DEFAULT_SCHEMA,
    DEFAULT_SOURCE,
    DEFAULT_SOURCE_SCHEMA,
    DEFAULT_OUTPUT_DIR,
    validate_expansion,
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
DEFAULT_CROSSWALK = DEFAULT_OUTPUT_DIR / "citywide-expansion-crosswalk.json"
DEFAULT_SOURCE_CROSSWALK = DEFAULT_SOURCE.parent / "migration-crosswalk.json"


def main(argv: Optional[list[str]] = None) -> int:
    """Run schema, domain, source, lineage, replay, and GIS-fixture checks."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ruleset", type=Path, default=DEFAULT_RULESET)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--predecessor", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--predecessor-schema", type=Path, default=DEFAULT_SOURCE_SCHEMA)
    parser.add_argument("--predecessor-crosswalk", type=Path, default=DEFAULT_SOURCE_CROSSWALK)
    parser.add_argument("--approved-r1-v2", type=Path, default=APPROVED_R1_V2)
    parser.add_argument("--gis-fixtures", type=Path, default=DEFAULT_GIS_FIXTURES)
    parser.add_argument("--verify-source-files", action="store_true")
    parser.add_argument("--require-runtime-eligible", action="store_true")
    args = parser.parse_args(argv)

    target_path = args.ruleset.resolve()
    schema_path = args.schema.resolve()
    source_path = args.predecessor.resolve()
    source_schema_path = args.predecessor_schema.resolve()
    source_crosswalk_path = args.predecessor_crosswalk.resolve()
    approved_r1_v2_path = args.approved_r1_v2.resolve()
    target = load_json(target_path)
    source = load_json(source_path)

    errors = validate_ruleset(
        source,
        schema=load_json(source_schema_path),
        verify_source_files=args.verify_source_files,
    )
    errors.extend(
        validate_migration(
            load_json(approved_r1_v2_path),
            source,
            load_json(source_crosswalk_path),
            source_path=approved_r1_v2_path,
            target_path=source_path,
            schema_path=source_schema_path,
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
        validate_expansion(
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
        f"Validated R1-R6 citywide residential candidate and complete lineage: "
        f"{args.ruleset} (runtime eligibility required: {args.require_runtime_eligible})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
