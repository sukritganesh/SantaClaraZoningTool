#!/usr/bin/env python3
"""Build the deterministic, committed runtime-data ZIP and its manifest."""

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
BUNDLE_VERSION = "2026-07-18.1"
BUNDLE_ID = "santa-clara-r1-runtime-data"
ARCHIVE_NAME = f"{BUNDLE_ID}-{BUNDLE_VERSION}.zip"
BUNDLE_DIRECTORY = REPO_ROOT / "demo-data"
ARCHIVE_PATH = BUNDLE_DIRECTORY / ARCHIVE_NAME
MANIFEST_PATH = BUNDLE_DIRECTORY / "bundle-manifest.json"
FIXED_ZIP_TIMESTAMP = (2026, 7, 18, 0, 0, 0)

BUNDLE_FILES = (
    "data/raw/2026-07-14/santa_clara_r1_gis/parcels/metadata.json",
    "data/raw/2026-07-14/santa_clara_r1_gis/parcels/object_ids.json",
    "data/raw/2026-07-14/santa_clara_r1_gis/current_zoning/metadata.json",
    "data/raw/2026-07-14/santa_clara_r1_gis/current_zoning/object_ids.json",
    "data/raw/2026-07-14/santa_clara_r1_gis/manifest.json",
    "data/raw/2026-07-14/santa_clara_r1_gis/current_zoning_r1.geojson",
    "data/raw/2026-07-14/santa_clara_r1_gis/parcels_r1.geojson",
    "data/raw/2026-07-16/santa_clara_address_points/schema_report.json",
    "data/raw/2026-07-16/santa_clara_address_points/manifest.json",
    "data/raw/2026-07-16/santa_clara_address_points/address_points.geojson",
    "data/raw/2026-07-16/santa_clara_address_points/address_points/metadata.json",
    "data/raw/2026-07-16/santa_clara_address_points/address_points/object_ids.json",
    "data/raw/2026-07-16/santa_clara_zoning_code/amendments/Ordinance-2085-adopted.pdf",
    "data/raw/2026-07-16/santa_clara_zoning_code/amendments/Ordinance-2086-adopted.pdf",
    "data/raw/2026-07-16/santa_clara_zoning_code/amendments/Zoning-Code-Cleanup-3-proposed-tables.docx",
    "data/raw/2026-07-16/santa_clara_zoning_code/SantaClaraZoningCode-July-2025.pdf",
    "data/raw/2026-07-16/santa_clara_zoning_code/manifest.json",
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
    """Write a byte-reproducible ZIP and checksum-backed external manifest."""

    sources = [(relative, REPO_ROOT / relative) for relative in BUNDLE_FILES]
    missing = [relative for relative, source in sources if not source.is_file()]
    if missing:
        raise FileNotFoundError(f"Bundle sources are missing: {missing}")

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

    included_files = [
        {
            "path": relative,
            "size_bytes": source.stat().st_size,
            "sha256": sha256_file(source),
        }
        for relative, source in sorted(sources)
    ]
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
            "address_points": "2026-07-16",
            "r1_gis": "2026-07-14",
            "zoning_code_and_amendment_audit": "2026-07-16",
        },
        "included_files": included_files,
        "excluded_from_runtime_bundle": [
            "Raw ArcGIS response chunks are preserved in the research workspace but "
            "excluded because the validated consolidated files, source metadata, object "
            "IDs, and manifests are sufficient to run and verify the prototype."
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
