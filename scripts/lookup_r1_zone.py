#!/usr/bin/env python3
"""Resolve a Santa Clara address to a local R1 parcel and zoning feature."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from santa_clara_zoning.lookup import (
    DEFAULT_ADDRESS_SNAPSHOT,
    DEFAULT_R1_SNAPSHOT,
    LocalR1Lookup,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("address", help="Santa Clara street address")
    parser.add_argument(
        "--address-snapshot",
        type=Path,
        default=DEFAULT_ADDRESS_SNAPSHOT,
        help="Address snapshot directory",
    )
    parser.add_argument(
        "--r1-snapshot",
        type=Path,
        default=DEFAULT_R1_SNAPSHOT,
        help="R1 GIS snapshot directory",
    )
    parser.add_argument(
        "--skip-checksums",
        action="store_true",
        help="Skip source checksum verification (not recommended)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lookup = LocalR1Lookup.from_snapshots(
        address_snapshot=args.address_snapshot,
        r1_snapshot=args.r1_snapshot,
        verify_checksums=not args.skip_checksums,
    )
    print(json.dumps(lookup.lookup(args.address), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
