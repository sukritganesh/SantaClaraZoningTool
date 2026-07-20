#!/usr/bin/env python3
"""Build the deterministic residential runtime-data successor and manifest."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import zipfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_VERSION = "2026-07-19.2"
BUNDLE_ID = "santa-clara-residential-runtime-data"
ARCHIVE_NAME = f"{BUNDLE_ID}-{BUNDLE_VERSION}.zip"
BUNDLE_DIRECTORY = REPO_ROOT / "demo-data"
ARCHIVE_PATH = BUNDLE_DIRECTORY / ARCHIVE_NAME
MANIFEST_PATH = BUNDLE_DIRECTORY / f"residential-bundle-manifest-{BUNDLE_VERSION}.json"
FIXED_ZIP_TIMESTAMP = (2026, 7, 19, 0, 0, 0)

BUNDLE_FILES = (
    "data/raw/2026-07-18/santa_clara_residential_gis/manifest.json",
    "data/raw/2026-07-18/santa_clara_residential_gis/parcels_residential.geojson",
    "data/raw/2026-07-18/santa_clara_residential_gis/current_zoning_residential.geojson",
    "data/raw/2026-07-18/patrick_henry_drive_specific_plan/manifest.json",
    "data/raw/2026-07-18/patrick_henry_drive_specific_plan/PatrickHenryPlan.pdf",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build_bundle() -> dict[str, Any]:
    """Write a byte-reproducible ZIP and checksum-backed manifest."""

    sources = [(relative, REPO_ROOT / relative) for relative in BUNDLE_FILES]
    missing = [relative for relative, source in sources if not source.is_file()]
    if missing:
        raise FileNotFoundError(f"Residential bundle sources are missing: {missing}")

    BUNDLE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    temporary_archive = ARCHIVE_PATH.with_suffix(".zip.tmp")
    try:
        with zipfile.ZipFile(
            temporary_archive,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for relative, source in sorted(sources):
                info = zipfile.ZipInfo(relative, FIXED_ZIP_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                with source.open("rb") as input_file, archive.open(info, "w") as output:
                    shutil.copyfileobj(input_file, output, length=1024 * 1024)
        os.replace(temporary_archive, ARCHIVE_PATH)
    finally:
        temporary_archive.unlink(missing_ok=True)

    manifest: dict[str, Any] = {
        "bundle_id": BUNDLE_ID,
        "bundle_version": BUNDLE_VERSION,
        "archive": {
            "file": ARCHIVE_NAME,
            "format": "zip",
            "size_bytes": ARCHIVE_PATH.stat().st_size,
            "sha256": sha256_file(ARCHIVE_PATH),
        },
        "install_root": ".",
        "snapshots": {
            "patrick_henry_drive_specific_plan": "2026-07-18",
            "residential_gis": "2026-07-18",
        },
        "included_files": [
            {
                "path": relative,
                "size_bytes": source.stat().st_size,
                "sha256": sha256_file(source),
            }
            for relative, source in sorted(sources)
        ],
        "excluded_from_runtime_bundle": [
            "Raw ArcGIS response chunks, metadata, object-ID responses, and count "
            "responses remain in the immutable research snapshot but are excluded "
            "because the validated manifest and consolidated layers are sufficient "
            "for deterministic runtime lookup. The checksum-pinned Patrick Henry "
            "adopted plan and its snapshot manifest are included because complete "
            "approved-ruleset lineage validation requires the authoritative source."
        ],
    }
    temporary_manifest = MANIFEST_PATH.with_suffix(".json.tmp")
    try:
        temporary_manifest.write_bytes(json_bytes(manifest))
        os.replace(temporary_manifest, MANIFEST_PATH)
    finally:
        temporary_manifest.unlink(missing_ok=True)
    return manifest


def main() -> int:
    manifest = build_bundle()
    archive = manifest["archive"]
    print(
        f"Built {archive['file']}: {archive['size_bytes']} bytes, "
        f"SHA-256 {archive['sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
