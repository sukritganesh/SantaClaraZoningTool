from __future__ import annotations

import hashlib
import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Mapping

from scripts.bootstrap_demo_data import (
    DEFAULT_MANIFESTS,
    DemoDataBootstrapError,
    install_bundle,
)
from scripts.build_demo_data_bundle import ARCHIVE_PATH, MANIFEST_PATH
from scripts.build_residential_demo_data_bundle import (
    ARCHIVE_PATH as RESIDENTIAL_ARCHIVE_PATH,
    MANIFEST_PATH as RESIDENTIAL_MANIFEST_PATH,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_RESIDENTIAL_MANIFEST_PATH = (
    REPO_ROOT / "demo-data/residential-bundle-manifest.json"
)
LEGACY_RESIDENTIAL_ARCHIVE_PATH = (
    REPO_ROOT
    / "demo-data/santa-clara-residential-runtime-data-2026-07-19.1.zip"
)
PATRICK_HENRY_PLAN_PATH = (
    "data/raw/2026-07-18/patrick_henry_drive_specific_plan/PatrickHenryPlan.pdf"
)
PATRICK_HENRY_MANIFEST_PATH = (
    "data/raw/2026-07-18/patrick_henry_drive_specific_plan/manifest.json"
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_test_bundle(
    directory: Path,
    files: Mapping[str, bytes],
    *,
    manifest_files: Mapping[str, bytes] | None = None,
) -> Path:
    archive_path = directory / "test-bundle.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, content in files.items():
            info = zipfile.ZipInfo(relative, (2026, 7, 18, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, content)

    declared = manifest_files if manifest_files is not None else files
    manifest = {
        "bundle_id": "test-runtime-data",
        "bundle_version": "1",
        "archive": {
            "file": archive_path.name,
            "format": "zip",
            "size_bytes": archive_path.stat().st_size,
            "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        },
        "install_root": ".",
        "included_files": [
            {
                "path": relative,
                "size_bytes": len(content),
                "sha256": _sha256(content),
            }
            for relative, content in declared.items()
        ],
    }
    manifest_path = directory / "bundle-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


class DemoDataBootstrapTest(unittest.TestCase):
    def test_installs_valid_bundle_and_is_idempotent(self) -> None:
        files = {
            "data/raw/2026-01-01/sample/manifest.json": b"{}\n",
            "data/raw/2026-01-01/sample/features.geojson": b'{"features": []}\n',
        }
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            bundle = root / "bundle"
            repository = root / "repository"
            bundle.mkdir()
            repository.mkdir()
            manifest_path = _write_test_bundle(bundle, files)

            self.assertEqual(install_bundle(manifest_path, repository), (2, 0))
            for relative, expected in files.items():
                self.assertEqual((repository / relative).read_bytes(), expected)

            self.assertEqual(install_bundle(manifest_path, repository), (0, 2))

    def test_rejects_changed_archive_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            repository = root / "repository"
            repository.mkdir()
            manifest_path = _write_test_bundle(
                root, {"data/raw/2026-01-01/sample/data.json": b"original"}
            )
            (root / "test-bundle.zip").write_bytes(b"modified")

            with self.assertRaisesRegex(
                DemoDataBootstrapError, "archive (size|checksum)"
            ):
                install_bundle(manifest_path, repository)

    def test_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            repository = root / "repository"
            repository.mkdir()
            unsafe_path = "data/raw/../../outside.txt"
            manifest_path = _write_test_bundle(root, {unsafe_path: b"unsafe"})

            with self.assertRaisesRegex(DemoDataBootstrapError, "Unsafe bundle"):
                install_bundle(manifest_path, repository)
            self.assertFalse((root / "outside.txt").exists())

    def test_rejects_archive_member_not_declared_by_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            repository = root / "repository"
            repository.mkdir()
            files = {
                "data/raw/2026-01-01/sample/data.json": b"approved",
                "data/raw/2026-01-01/sample/extra.json": b"unexpected",
            }
            manifest_path = _write_test_bundle(
                root,
                files,
                manifest_files={
                    "data/raw/2026-01-01/sample/data.json": b"approved"
                },
            )

            with self.assertRaisesRegex(
                DemoDataBootstrapError, "contents differ from its manifest"
            ):
                install_bundle(manifest_path, repository)

    def test_rejects_entry_with_incorrect_declared_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            repository = root / "repository"
            repository.mkdir()
            relative = "data/raw/2026-01-01/sample/data.json"
            manifest_path = _write_test_bundle(
                root,
                {relative: b"actual"},
                manifest_files={relative: b"different"},
            )

            with self.assertRaisesRegex(
                DemoDataBootstrapError, "entry (size|checksum)"
            ):
                install_bundle(manifest_path, repository)

    def test_refuses_to_overwrite_conflicting_file_without_partial_install(self) -> None:
        files = {
            "data/raw/2026-01-01/sample/conflict.json": b"approved",
            "data/raw/2026-01-01/sample/missing.json": b"would be installed",
        }
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            bundle = root / "bundle"
            repository = root / "repository"
            bundle.mkdir()
            repository.mkdir()
            manifest_path = _write_test_bundle(bundle, files)
            conflict = repository / "data/raw/2026-01-01/sample/conflict.json"
            conflict.parent.mkdir(parents=True)
            conflict.write_bytes(b"local change")

            with self.assertRaisesRegex(
                DemoDataBootstrapError, "Refusing to overwrite"
            ):
                install_bundle(manifest_path, repository)
            self.assertEqual(conflict.read_bytes(), b"local change")
            self.assertFalse(
                (repository / "data/raw/2026-01-01/sample/missing.json").exists()
            )


class CommittedDemoDataBundleTest(unittest.TestCase):
    def test_committed_archive_matches_its_manifest_and_git_size_policy(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        archive_record = manifest["archive"]

        self.assertEqual(archive_record["file"], ARCHIVE_PATH.name)
        self.assertEqual(archive_record["size_bytes"], ARCHIVE_PATH.stat().st_size)
        self.assertLess(ARCHIVE_PATH.stat().st_size, 50_000_000)
        self.assertEqual(
            archive_record["sha256"],
            hashlib.sha256(ARCHIVE_PATH.read_bytes()).hexdigest(),
        )

        declared = {record["path"] for record in manifest["included_files"]}
        with zipfile.ZipFile(ARCHIVE_PATH) as archive:
            self.assertEqual({member.filename for member in archive.infolist()}, declared)

    def test_committed_archive_installs_into_an_empty_repository(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            repository = Path(raw_temp) / "repository"
            repository.mkdir()

            installed, matched = install_bundle(MANIFEST_PATH, repository)

            self.assertEqual(installed, 17)
            self.assertEqual(matched, 0)
            self.assertTrue(
                (
                    repository
                    / "data/raw/2026-07-14/santa_clara_r1_gis/parcels_r1.geojson"
                ).is_file()
            )

    def test_residential_successor_matches_manifest_and_installs(self) -> None:
        manifest = json.loads(
            RESIDENTIAL_MANIFEST_PATH.read_text(encoding="utf-8")
        )
        archive_record = manifest["archive"]
        self.assertEqual(archive_record["file"], RESIDENTIAL_ARCHIVE_PATH.name)
        self.assertEqual(
            archive_record["size_bytes"],
            RESIDENTIAL_ARCHIVE_PATH.stat().st_size,
        )
        self.assertLess(RESIDENTIAL_ARCHIVE_PATH.stat().st_size, 50_000_000)
        self.assertEqual(
            archive_record["sha256"],
            hashlib.sha256(RESIDENTIAL_ARCHIVE_PATH.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            {record["path"] for record in manifest["included_files"]},
            {
                "data/raw/2026-07-18/santa_clara_residential_gis/manifest.json",
                "data/raw/2026-07-18/santa_clara_residential_gis/parcels_residential.geojson",
                "data/raw/2026-07-18/santa_clara_residential_gis/current_zoning_residential.geojson",
                PATRICK_HENRY_PLAN_PATH,
                PATRICK_HENRY_MANIFEST_PATH,
            },
        )
        with tempfile.TemporaryDirectory() as raw_temp:
            repository = Path(raw_temp) / "repository"
            repository.mkdir()
            installed, matched = install_bundle(
                RESIDENTIAL_MANIFEST_PATH,
                repository,
            )
            self.assertEqual((installed, matched), (5, 0))
            self.assertTrue(
                (
                    repository
                    / "data/raw/2026-07-18/santa_clara_residential_gis/manifest.json"
                ).is_file()
            )
            self.assertTrue((repository / PATRICK_HENRY_PLAN_PATH).is_file())
            self.assertTrue((repository / PATRICK_HENRY_MANIFEST_PATH).is_file())

    def test_default_bundles_install_complete_runtime_source_set(self) -> None:
        self.assertEqual(DEFAULT_MANIFESTS, (MANIFEST_PATH, RESIDENTIAL_MANIFEST_PATH))
        with tempfile.TemporaryDirectory() as raw_temp:
            repository = Path(raw_temp) / "repository"
            repository.mkdir()
            results = [
                install_bundle(manifest_path, repository)
                for manifest_path in DEFAULT_MANIFESTS
            ]

            self.assertEqual(results, [(17, 0), (5, 0)])
            self.assertTrue((repository / PATRICK_HENRY_PLAN_PATH).is_file())
            self.assertTrue((repository / PATRICK_HENRY_MANIFEST_PATH).is_file())

    def test_predecessor_residential_add_on_remains_checksum_reproducible(self) -> None:
        manifest = json.loads(
            LEGACY_RESIDENTIAL_MANIFEST_PATH.read_text(encoding="utf-8")
        )
        archive_record = manifest["archive"]

        self.assertEqual(manifest["bundle_version"], "2026-07-19.1")
        self.assertEqual(archive_record["file"], LEGACY_RESIDENTIAL_ARCHIVE_PATH.name)
        self.assertEqual(archive_record["size_bytes"], 4_186_509)
        self.assertEqual(
            archive_record["sha256"],
            "bbe2274b00b2687d4a540484e7fcf8cbdc7a8038a063cb4973b169038bb3e098",
        )
        self.assertEqual(
            hashlib.sha256(LEGACY_RESIDENTIAL_ARCHIVE_PATH.read_bytes()).hexdigest(),
            archive_record["sha256"],
        )


if __name__ == "__main__":
    unittest.main()
