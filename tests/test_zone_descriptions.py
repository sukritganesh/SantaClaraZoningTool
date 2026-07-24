"""Versioned plain-language residential zone-description catalog tests."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from santa_clara_zoning.zone_descriptions import (
    DEFAULT_AUTHORING_GUIDE_PATH,
    DEFAULT_CATALOG_PATH,
    DEFAULT_REPO_ROOT,
    DEFAULT_RULESET_PATH,
    MAX_DESCRIPTION_WORDS,
    MIN_DESCRIPTION_WORDS,
    SUPPORTED_ZONE_DESCRIPTIONS,
    ZoneDescriptionIntegrityError,
    ZoneDescriptionProvider,
)


class ZoneDescriptionCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.provider = ZoneDescriptionProvider.from_defaults()

    def test_catalog_is_complete_source_grounded_and_concise(self) -> None:
        catalog = self.provider.as_dict()

        self.assertEqual(catalog["contract_version"], "1.0.0")
        self.assertEqual(catalog["catalog_version"], "2026-07-23.1")
        self.assertEqual(
            tuple(catalog["descriptions"]),
            SUPPORTED_ZONE_DESCRIPTIONS,
        )
        for zone, entry in catalog["descriptions"].items():
            with self.subTest(zone=zone):
                description = entry["description"]
                self.assertTrue(description.startswith(f"{zone} "))
                self.assertNotIn("\n", description)
                self.assertNotIn("<", description)
                self.assertIn("Zoning Clearance", description)
                self.assertIn("Architectural Review", description)
                self.assertGreaterEqual(
                    len(description.split()),
                    MIN_DESCRIPTION_WORDS,
                )
                self.assertLessEqual(
                    len(description.split()),
                    MAX_DESCRIPTION_WORDS,
                )
                self.assertEqual(
                    len(entry["source_refs"]),
                    len(set(entry["source_refs"])),
                )

    def test_comparative_and_specific_plan_distinctions_are_explicit(self) -> None:
        r1_standard = self.provider.description_for("R1-6L")
        r1_large_lot = self.provider.description_for("R1-8L")
        r6 = self.provider.description_for("R6")
        uc = self.provider.description_for("UC")
        hdf = self.provider.description_for("HDF")

        self.assertIn("standard single-family", r1_standard)
        self.assertIn("larger-lot", r1_large_lot)
        self.assertIn("transit-neighborhood", r6)
        self.assertIn("airport flight-path requirements", uc)
        self.assertIn("flexible transition", hdf)
        self.assertIn("Explorer's residential scope", hdf)

    def test_provider_returns_defensive_catalog_data(self) -> None:
        first = self.provider.as_dict()
        first["descriptions"]["R2"]["description"] = "changed"

        second = self.provider.as_dict()
        self.assertNotEqual(
            second["descriptions"]["R2"]["description"],
            "changed",
        )
        self.assertEqual(
            self.provider.description_for("R2"),
            second["descriptions"]["R2"]["description"],
        )
        with self.assertRaises(KeyError):
            self.provider.description_for("MC")

    def test_mutated_catalogs_and_bound_artifacts_fail_closed(self) -> None:
        mutations = {
            "missing zone": lambda value: value["descriptions"].pop("R6"),
            "unknown zone": lambda value: value["descriptions"].update(
                {"MC": value["descriptions"]["R2"]}
            ),
            "html": lambda value: value["descriptions"]["R2"].update(
                {
                    "description": (
                        "R2 <strong>is untrusted rendered copy</strong> that "
                        "incorrectly bypasses the reviewed presentation boundary. "
                        "This deliberately malformed fixture contains enough words "
                        "to reach ordinary catalog length expectations while still "
                        "remaining invalid. New construction and substantial changes "
                        "generally require Zoning Clearance and Architectural Review."
                    )
                }
            ),
            "numeric standard": lambda value: value["descriptions"]["R2"].update(
                {
                    "description": (
                        "R2 is Santa Clara's low-density residential zone and this "
                        "malformed fixture improperly repeats a 32 foot standard in "
                        "presentation copy. It otherwise contains enough ordinary "
                        "language to reach the catalog's expected size and appear "
                        "plausible. New construction and substantial changes generally "
                        "require Zoning Clearance and Architectural Review."
                    )
                }
            ),
            "missing provenance": lambda value: value["descriptions"]["R2"].update(
                {"source_refs": ["zoning-clearance", "architectural-review"]}
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as directory:
                    paths = self._copy_package(Path(directory))
                    catalog = json.loads(
                        paths["catalog"].read_text(encoding="utf-8")
                    )
                    mutate(catalog)
                    paths["catalog"].write_text(
                        json.dumps(catalog, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    with self.assertRaises(ZoneDescriptionIntegrityError):
                        self._provider(Path(directory), paths)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self._copy_package(root)
            paths["guide"].write_text(
                paths["guide"].read_text(encoding="utf-8") + "\nChanged.\n",
                encoding="utf-8",
            )
            with self.assertRaises(ZoneDescriptionIntegrityError):
                self._provider(root, paths)

    def _copy_package(self, root: Path) -> dict[str, Path]:
        paths = {}
        for label, source in (
            ("catalog", DEFAULT_CATALOG_PATH),
            ("ruleset", DEFAULT_RULESET_PATH),
            ("guide", DEFAULT_AUTHORING_GUIDE_PATH),
        ):
            relative = source.relative_to(DEFAULT_REPO_ROOT)
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            paths[label] = target
        return paths

    def _provider(
        self,
        root: Path,
        paths: dict[str, Path],
    ) -> ZoneDescriptionProvider:
        return ZoneDescriptionProvider(
            repo_root=root,
            catalog_path=paths["catalog"],
            ruleset_path=paths["ruleset"],
            authoring_guide_path=paths["guide"],
        )


if __name__ == "__main__":
    unittest.main()
