#!/usr/bin/env python3
"""Validate the checked-in plain-language residential zone descriptions."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from santa_clara_zoning.zone_descriptions import (  # noqa: E402
    DEFAULT_AUTHORING_GUIDE_PATH,
    DEFAULT_CATALOG_PATH,
    DEFAULT_RULESET_PATH,
    SUPPORTED_ZONE_DESCRIPTIONS,
    ZoneDescriptionIntegrityError,
    ZoneDescriptionProvider,
)


def parse_args() -> argparse.Namespace:
    """Parse optional artifact overrides for focused validation."""

    parser = argparse.ArgumentParser(
        description="Validate the Santa Clara zone-description catalog."
    )
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG_PATH)
    parser.add_argument("--ruleset", type=Path, default=DEFAULT_RULESET_PATH)
    parser.add_argument(
        "--authoring-guide",
        type=Path,
        default=DEFAULT_AUTHORING_GUIDE_PATH,
    )
    return parser.parse_args()


def main() -> int:
    """Validate the catalog and report its exact supported scope."""

    args = parse_args()
    try:
        provider = ZoneDescriptionProvider(
            repo_root=REPO_ROOT,
            catalog_path=args.catalog,
            ruleset_path=args.ruleset,
            authoring_guide_path=args.authoring_guide,
        )
    except ZoneDescriptionIntegrityError as error:
        print(f"Zone-description validation failed: {error}", file=sys.stderr)
        return 1
    print(
        f"Validated zone-description catalog {provider.catalog_version}: "
        f"{len(SUPPORTED_ZONE_DESCRIPTIONS)} exact supported zones."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
