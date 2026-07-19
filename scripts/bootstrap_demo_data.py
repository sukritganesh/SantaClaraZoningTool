#!/usr/bin/env python3
"""Safely install the committed Santa Clara runtime-data bundles."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "demo-data/bundle-manifest.json"
DEFAULT_MANIFESTS = (
    DEFAULT_MANIFEST,
    REPO_ROOT / "demo-data/residential-bundle-manifest-2026-07-19.2.json",
)
ALLOWED_PREFIX = PurePosixPath("data/raw")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class DemoDataBootstrapError(RuntimeError):
    """Reject an unsafe, incomplete, modified, or conflicting data bundle."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DemoDataBootstrapError(f"Could not read bundle manifest {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DemoDataBootstrapError("Bundle manifest must contain one JSON object")
    return value


def _safe_relative_path(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise DemoDataBootstrapError("Bundle file path must be a non-empty string")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or ".." in path.parts
        or "\\" in value
        or path.as_posix() != value
        or path.parts[: len(ALLOWED_PREFIX.parts)] != ALLOWED_PREFIX.parts
    ):
        raise DemoDataBootstrapError(f"Unsafe bundle file path: {value!r}")
    return path


def _manifest_records(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    archive = manifest.get("archive")
    records = manifest.get("included_files")
    if (
        manifest.get("install_root") != "."
        or not isinstance(archive, dict)
        or archive.get("format") != "zip"
        or not isinstance(archive.get("file"), str)
        or not isinstance(archive.get("size_bytes"), int)
        or archive.get("size_bytes") < 0
        or not isinstance(archive.get("sha256"), str)
        or not SHA256_PATTERN.fullmatch(archive["sha256"])
        or not isinstance(records, list)
        or not records
    ):
        raise DemoDataBootstrapError("Bundle manifest has an unsupported structure")

    archive_name = PurePosixPath(archive["file"])
    if (
        archive_name.is_absolute()
        or len(archive_name.parts) != 1
        or archive_name.as_posix() != archive["file"]
    ):
        raise DemoDataBootstrapError("Bundle archive filename must be a plain filename")

    by_path: dict[str, dict[str, Any]] = {}
    for position, record in enumerate(records):
        if not isinstance(record, dict):
            raise DemoDataBootstrapError(f"Bundle record {position} is not an object")
        relative = _safe_relative_path(record.get("path")).as_posix()
        if relative in by_path:
            raise DemoDataBootstrapError(f"Duplicate bundle manifest path: {relative}")
        if (
            not isinstance(record.get("size_bytes"), int)
            or record["size_bytes"] < 0
            or not isinstance(record.get("sha256"), str)
            or not SHA256_PATTERN.fullmatch(record["sha256"])
        ):
            raise DemoDataBootstrapError(f"Bundle record is incomplete: {relative}")
        by_path[relative] = record
    return by_path


def install_bundle(manifest_path: Path, repo_root: Path) -> tuple[int, int]:
    """Validate and install the bundle; return installed and already-matching counts."""

    manifest_path = manifest_path.resolve()
    repo_root = repo_root.resolve()
    manifest = load_manifest(manifest_path)
    records = _manifest_records(manifest)
    archive_record = manifest["archive"]
    archive_path = manifest_path.parent / archive_record["file"]
    if not archive_path.is_file():
        raise DemoDataBootstrapError(f"Bundle archive is missing: {archive_path}")
    if archive_path.stat().st_size != archive_record["size_bytes"]:
        raise DemoDataBootstrapError("Bundle archive size does not match its manifest")
    if sha256_file(archive_path) != archive_record["sha256"]:
        raise DemoDataBootstrapError("Bundle archive checksum does not match its manifest")

    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        if len(names) != len(set(names)):
            raise DemoDataBootstrapError("Bundle archive contains duplicate paths")
        if set(names) != set(records):
            missing = sorted(set(records) - set(names))
            unexpected = sorted(set(names) - set(records))
            raise DemoDataBootstrapError(
                f"Bundle archive contents differ from its manifest: "
                f"missing={missing}, unexpected={unexpected}"
            )
        for member in members:
            _safe_relative_path(member.filename)
            file_type = (member.external_attr >> 16) & 0o170000
            if member.is_dir() or file_type == stat.S_IFLNK:
                raise DemoDataBootstrapError(
                    f"Bundle archive contains an unsupported entry: {member.filename}"
                )
            if member.file_size != records[member.filename]["size_bytes"]:
                raise DemoDataBootstrapError(
                    f"Bundle entry size does not match: {member.filename}"
                )

        with tempfile.TemporaryDirectory(
            prefix=".demo-data-stage-", dir=repo_root
        ) as raw_staging:
            staging = Path(raw_staging)
            for member in members:
                staged = staging / member.filename
                staged.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                size = 0
                with archive.open(member) as source, staged.open("wb") as destination:
                    while True:
                        block = source.read(1024 * 1024)
                        if not block:
                            break
                        destination.write(block)
                        digest.update(block)
                        size += len(block)
                expected = records[member.filename]
                if size != expected["size_bytes"] or digest.hexdigest() != expected["sha256"]:
                    raise DemoDataBootstrapError(
                        f"Bundle entry checksum does not match: {member.filename}"
                    )

            conflicts = []
            already_matching = 0
            for relative, record in records.items():
                destination = repo_root / relative
                if destination.exists():
                    if not destination.is_file() or (
                        destination.stat().st_size != record["size_bytes"]
                        or sha256_file(destination) != record["sha256"]
                    ):
                        conflicts.append(relative)
                    else:
                        already_matching += 1
            if conflicts:
                raise DemoDataBootstrapError(
                    "Refusing to overwrite different existing data files: "
                    + ", ".join(sorted(conflicts))
                )

            installed = 0
            for relative in records:
                destination = repo_root / relative
                if destination.exists():
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staging / relative, destination)
                installed += 1
    return installed, already_matching


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        action="append",
        help=(
            "Bundle manifest path; repeat to install several. By default, install "
            "the released R1 bundle and the residential runtime add-on."
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root receiving data/raw (default: current project)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifests = tuple(args.manifest) if args.manifest else DEFAULT_MANIFESTS
    installed_total = 0
    matched_total = 0
    try:
        for manifest in manifests:
            installed, matched = install_bundle(manifest, args.repo_root)
            installed_total += installed
            matched_total += matched
    except (DemoDataBootstrapError, OSError, zipfile.BadZipFile) as exc:
        print(f"Demo data installation failed: {exc}")
        return 1
    print(
        f"Demo data ready: {installed_total} files installed, "
        f"{matched_total} already matched the approved bundles."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
