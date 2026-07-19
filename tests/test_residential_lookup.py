"""Residential GIS lookup and immutable-snapshot integrity gates."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from santa_clara_zoning import (
    ApprovedResidentialRuleset,
    LocalResidentialLookup,
)
from santa_clara_zoning.lookup import (
    DEFAULT_ADDRESS_SNAPSHOT,
    DEFAULT_RESIDENTIAL_SNAPSHOT,
    EXCLUDED_RESIDENTIAL_DESIGNATIONS,
    _residential_spatial_result,
)


FIXTURE_INVENTORY = (
    Path(__file__).resolve().parent
    / "fixtures/residential_gis_fixture_inventory.json"
)
SNAPSHOTS_AVAILABLE = (
    (DEFAULT_ADDRESS_SNAPSHOT / "address_points.geojson").is_file()
    and (
        DEFAULT_RESIDENTIAL_SNAPSHOT / "parcels_residential.geojson"
    ).is_file()
    and (
        DEFAULT_RESIDENTIAL_SNAPSHOT
        / "current_zoning_residential.geojson"
    ).is_file()
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> str:
    content = (
        json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def _polygon(index: int) -> dict[str, Any]:
    start = float(index * 2)
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [start, 0.0],
                [start + 1.0, 0.0],
                [start + 1.0, 1.0],
                [start, 1.0],
                [start, 0.0],
            ]
        ],
    }


def _residential_feature(
    object_id: int,
    designation: str,
) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {
            "OBJECTID": object_id,
            "APN": f"000-00-{object_id:03d}",
            "ZONGDSGN": designation,
            "ACREAGE": 1.0,
            "GPLANCRT": None,
            "SPPLAN": None,
            "HistoricParcelType": None,
        },
        "geometry": _polygon(object_id - 1),
    }


@contextmanager
def synthetic_snapshots(
    supported_zones: tuple[str, ...],
) -> Iterator[tuple[Path, Path]]:
    """Create a small, internally consistent snapshot pair for mutations."""

    with tempfile.TemporaryDirectory(
        prefix="residential-lookup-test-"
    ) as raw:
        root = Path(raw)
        address_root = root / "addresses"
        residential_root = root / "residential"
        address_root.mkdir()
        residential_root.mkdir()

        address_collection = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "OBJECTID": 1,
                        "CSCADDID": 10,
                        "CSCADDR": "1 Synthetic Street",
                        "CSCSTATUS": "A",
                        "ADDRUNIT": None,
                        "ADDRCITY": "SANTA CLARA",
                        "ADDRZIP5": 95050,
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [0.5, 0.5],
                    },
                }
            ],
        }
        address_sha = _write_json(
            address_root / "address_points.geojson",
            address_collection,
        )
        _write_json(
            address_root / "manifest.json",
            {
                "status": "complete",
                "snapshot_date": "2026-07-16",
                "layer": {
                    "validation": "complete",
                    "source_layer_url": "https://example.test/addresses",
                    "source_object_id_count": 1,
                    "downloaded_feature_count": 1,
                    "unique_downloaded_object_id_count": 1,
                    "output_file": "address_points.geojson",
                    "output_sha256": address_sha,
                    "output_spatial_reference": "EPSG:4326",
                },
            },
        )

        positive_zones = [
            zone for zone in supported_zones if zone not in {"R5", "R6"}
        ]
        features = [
            _residential_feature(index, zone)
            for index, zone in enumerate(positive_zones, start=1)
        ]
        collection = {"type": "FeatureCollection", "features": features}
        parcel_sha = _write_json(
            residential_root / "parcels_residential.geojson",
            collection,
        )
        zoning_sha = _write_json(
            residential_root / "current_zoning_residential.geojson",
            collection,
        )
        counts = {
            zone: 0 if zone in {"R5", "R6"} else 1
            for zone in supported_zones
        }
        excluded_counts = {
            zone: 1 for zone in EXCLUDED_RESIDENTIAL_DESIGNATIONS
        }
        filter_value = "ZONGDSGN IN (" + ",".join(
            f"'{zone}'" for zone in supported_zones
        ) + ")"

        def layer(
            slug: str,
            output_file: str,
            output_sha: str,
        ) -> dict[str, Any]:
            return {
                "slug": slug,
                "validation": "complete",
                "source_layer_url": f"https://example.test/{slug}",
                "source_object_id_count": len(features),
                "downloaded_feature_count": len(features),
                "unique_downloaded_object_id_count": len(features),
                "requested_designation_counts": dict(counts),
                "downloaded_zone_counts": dict(counts),
                "observed_designations": list(positive_zones),
                "excluded_designation_preflight_counts": dict(
                    excluded_counts
                ),
                "where": filter_value,
                "output_file": output_file,
                "output_sha256": output_sha,
                "output_spatial_reference": "EPSG:4326",
            }

        _write_json(
            residential_root / "manifest.json",
            {
                "manifest_schema_version": "1.0.0",
                "status": "complete",
                "snapshot_date": "2026-07-18",
                "requested_designations": list(supported_zones),
                "excluded_preflight_designations": list(
                    EXCLUDED_RESIDENTIAL_DESIGNATIONS
                ),
                "filter": filter_value,
                "layers": [
                    layer(
                        "parcels",
                        "parcels_residential.geojson",
                        parcel_sha,
                    ),
                    layer(
                        "current_zoning",
                        "current_zoning_residential.geojson",
                        zoning_sha,
                    ),
                ],
                "cross_layer_validation": {
                    "requested_zone_counts_agree": True,
                    "requested_zone_counts": dict(counts),
                    "excluded_preflight_counts_agree": True,
                    "excluded_preflight_counts": dict(excluded_counts),
                },
            },
        )
        yield address_root, residential_root


@unittest.skipUnless(
    SNAPSHOTS_AVAILABLE,
    "canonical residential GIS snapshots are not present",
)
class LocalResidentialLookupIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ruleset = ApprovedResidentialRuleset.load()
        cls.lookup = LocalResidentialLookup.from_snapshots(
            ruleset=cls.ruleset
        )
        cls.inventory = _load_json(FIXTURE_INVENTORY)

    def test_all_ten_live_designations_resolve_exactly(self) -> None:
        fixtures = self.inventory["real_address_fixtures"]
        self.assertEqual(len(fixtures), 10)
        for fixture in fixtures:
            with self.subTest(fixture=fixture["id"]):
                result = self.lookup.lookup(
                    fixture["address"]["display_address"]
                )
                self.assertEqual(result["status"], "residential_zone_found")
                self.assertEqual(
                    result["parcel"]["designation"],
                    fixture["designation"],
                )
                self.assertEqual(
                    result["zoning"]["designation"],
                    fixture["designation"],
                )
                self.assertEqual(
                    result["parcel"]["source_object_id"],
                    fixture["parcel"]["source_object_id"],
                )
                self.assertTrue(result["zoning"]["parcel_attribute_agrees"])

    def test_snapshot_scope_and_zero_counts_are_preserved(self) -> None:
        self.assertEqual(self.lookup.supported_zones, self.ruleset.supported_zones)
        self.assertEqual(self.lookup.designation_counts["R5"], 0)
        self.assertEqual(self.lookup.designation_counts["R6"], 0)
        self.assertEqual(
            self.lookup.excluded_designation_counts,
            {"R1-6LHT": 14, "R2-7L": 1, "R2HT": 2},
        )
        self.assertEqual(
            self.lookup.versions,
            {
                "address_snapshot": "2026-07-16",
                "residential_gis_snapshot": "2026-07-18",
            },
        )

    def test_address_and_outside_snapshot_outcomes_are_controlled(self) -> None:
        outside = self.lookup.lookup("1500 Warburton Avenue")
        self.assertEqual(
            outside["status"],
            "outside_supported_residential_snapshot",
        )
        self.assertEqual(
            outside["spatial_match_counts"],
            {"residential_parcels": 0, "residential_zoning_features": 0},
        )
        ambiguous = self.lookup.lookup("324 Los Padres Boulevard")
        self.assertEqual(ambiguous["status"], "address_ambiguous")
        self.assertEqual(len(ambiguous["address_candidates"]), 2)
        missing = self.lookup.lookup("99999 No Such Street")
        self.assertEqual(missing["status"], "address_not_found")
        empty = self.lookup.lookup("")
        self.assertEqual(empty["reason_code"], "empty_or_invalid_address")

    def test_repeated_lookup_is_deterministic_and_metadata_is_defensive(self) -> None:
        first = self.lookup.lookup("1240 White Drive")
        second = self.lookup.lookup("1240 White Drive")
        self.assertEqual(first, second)
        changed = self.lookup.designation_counts
        changed["R2"] = 0
        self.assertEqual(self.lookup.designation_counts["R2"], 752)


class ResidentialSpatialOutcomeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = {"query": {}, "versions": {}, "sources": {}}
        self.address = {
            "properties": {
                "OBJECTID": 1,
                "CSCADDID": 1,
                "CSCADDR": "1 Test Street",
                "ADDRUNIT": None,
                "ADDRCITY": "SANTA CLARA",
                "ADDRZIP5": 95050,
            },
            "geometry": {"type": "Point", "coordinates": [-121.9, 37.3]},
        }
        self.supported = frozenset({"R2", "R3"})

    def spatial_feature(
        self,
        object_id: int,
        zone: str,
        *,
        parcel: bool,
    ) -> dict[str, Any]:
        properties = {"OBJECTID": object_id, "ZONGDSGN": zone}
        if parcel:
            properties["APN"] = "000-00-000"
        return {"properties": properties, "geometry": None}

    def result(
        self,
        parcels: tuple[dict[str, Any], ...],
        zoning: tuple[dict[str, Any], ...],
    ) -> dict[str, Any]:
        return _residential_spatial_result(
            base=self.base,
            address=self.address,
            parcel_matches=parcels,
            zoning_matches=zoning,
            supported_zones=self.supported,
        )

    def test_exact_supported_match_succeeds(self) -> None:
        result = self.result(
            (self.spatial_feature(1, "R3", parcel=True),),
            (self.spatial_feature(2, "R3", parcel=False),),
        )
        self.assertEqual(result["status"], "residential_zone_found")

    def test_mismatch_and_overlap_require_review(self) -> None:
        mismatch = self.result(
            (self.spatial_feature(1, "R2", parcel=True),),
            (self.spatial_feature(2, "R3", parcel=False),),
        )
        self.assertEqual(
            mismatch["reason_code"],
            "parcel_zoning_designation_mismatch",
        )
        overlap = self.result(
            (
                self.spatial_feature(1, "R2", parcel=True),
                self.spatial_feature(2, "R2", parcel=True),
            ),
            (self.spatial_feature(3, "R2", parcel=False),),
        )
        self.assertEqual(overlap["reason_code"], "spatial_match_count_unexpected")

    def test_excluded_designations_are_never_normalized(self) -> None:
        for zone in EXCLUDED_RESIDENTIAL_DESIGNATIONS:
            with self.subTest(zone=zone):
                result = self.result(
                    (self.spatial_feature(1, zone, parcel=True),),
                    (self.spatial_feature(2, zone, parcel=False),),
                )
                self.assertEqual(result["status"], "review_required")
                self.assertEqual(
                    result["reason_code"],
                    "unexpected_zone_in_residential_snapshot",
                )


class ResidentialSnapshotIntegrityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ruleset = ApprovedResidentialRuleset.load()
        cls.zones = cls.ruleset.supported_zones

    def load(
        self,
        address_root: Path,
        residential_root: Path,
        *,
        verify_checksums: bool = True,
    ) -> LocalResidentialLookup:
        return LocalResidentialLookup.from_snapshots(
            ruleset=self.ruleset,
            address_snapshot=address_root,
            residential_snapshot=residential_root,
            verify_checksums=verify_checksums,
        )

    def test_small_complete_snapshot_loads(self) -> None:
        with synthetic_snapshots(self.zones) as roots:
            lookup = self.load(*roots)
            result = lookup.lookup("1 Synthetic Street")
        self.assertEqual(result["status"], "residential_zone_found")
        self.assertEqual(result["parcel"]["designation"], "R1-6L")

    def test_output_checksum_and_feature_count_fail_closed(self) -> None:
        with synthetic_snapshots(self.zones) as roots:
            manifest_path = roots[1] / "manifest.json"
            manifest = _load_json(manifest_path)
            manifest["layers"][0]["output_sha256"] = "0" * 64
            _write_json(manifest_path, manifest)
            with self.assertRaisesRegex(ValueError, "checksum"):
                self.load(*roots)

        with synthetic_snapshots(self.zones) as roots:
            path = roots[1] / "parcels_residential.geojson"
            collection = _load_json(path)
            collection["features"].pop()
            _write_json(path, collection)
            with self.assertRaisesRegex(ValueError, "Feature count differs"):
                self.load(*roots, verify_checksums=False)

    def test_manifest_scope_count_and_agreement_failures(self) -> None:
        def drift_layer_counts(value: dict[str, Any]) -> None:
            layer = value["layers"][1]
            layer["requested_designation_counts"]["R2"] = 2
            layer["downloaded_zone_counts"]["R2"] = 2
            layer["source_object_id_count"] += 1
            layer["downloaded_feature_count"] += 1
            layer["unique_downloaded_object_id_count"] += 1

        cases = (
            (
                "incomplete status",
                "not complete",
                lambda value: value.update(status="failed"),
            ),
            (
                "ruleset scope drift",
                "do not exactly match",
                lambda value: value["requested_designations"].pop(),
            ),
            (
                "excluded scope drift",
                "excluded designations",
                lambda value: value["excluded_preflight_designations"].pop(),
            ),
            (
                "observed designation drift",
                "observed designations",
                lambda value: value["layers"][0][
                    "observed_designations"
                ].pop(),
            ),
            (
                "cross-layer disagreement",
                "agreement is not complete",
                lambda value: value["cross_layer_validation"].update(
                    requested_zone_counts_agree=False
                ),
            ),
            (
                "cross-layer count drift",
                "designation counts differ",
                drift_layer_counts,
            ),
        )
        for label, evidence, mutate in cases:
            with self.subTest(case=label):
                with synthetic_snapshots(self.zones) as roots:
                    path = roots[1] / "manifest.json"
                    manifest = _load_json(path)
                    mutate(manifest)
                    _write_json(path, manifest)
                    with self.assertRaisesRegex(ValueError, evidence):
                        self.load(*roots)

    def test_address_manifest_and_checksum_fail_closed(self) -> None:
        with synthetic_snapshots(self.zones) as roots:
            path = roots[0] / "manifest.json"
            manifest = _load_json(path)
            manifest["status"] = "failed"
            _write_json(path, manifest)
            with self.assertRaisesRegex(ValueError, "not complete"):
                self.load(*roots)

        with synthetic_snapshots(self.zones) as roots:
            path = roots[0] / "manifest.json"
            manifest = _load_json(path)
            manifest["layer"]["unique_downloaded_object_id_count"] = 0
            _write_json(path, manifest)
            with self.assertRaisesRegex(ValueError, "counts disagree"):
                self.load(*roots)

        with synthetic_snapshots(self.zones) as roots:
            path = roots[0] / "manifest.json"
            manifest = _load_json(path)
            manifest["layer"]["output_sha256"] = "0" * 64
            _write_json(path, manifest)
            with self.assertRaisesRegex(ValueError, "checksum"):
                self.load(*roots)

    def test_explicit_r5_r6_zeroes_are_required(self) -> None:
        with synthetic_snapshots(self.zones) as roots:
            path = roots[1] / "manifest.json"
            manifest = _load_json(path)
            for layer in manifest["layers"]:
                layer["requested_designation_counts"]["R5"] = 1
                layer["downloaded_zone_counts"]["R5"] = 1
                layer["observed_designations"].append("R5")
                layer["source_object_id_count"] += 1
                layer["downloaded_feature_count"] += 1
                layer["unique_downloaded_object_id_count"] += 1
            manifest["cross_layer_validation"]["requested_zone_counts"][
                "R5"
            ] = 1
            _write_json(path, manifest)
            with self.assertRaisesRegex(ValueError, "explicit zeroes"):
                self.load(*roots)

    def test_unsupported_feature_designation_is_rejected_exactly(self) -> None:
        with synthetic_snapshots(self.zones) as roots:
            output_path = roots[1] / "parcels_residential.geojson"
            collection = _load_json(output_path)
            collection["features"][0]["properties"][
                "ZONGDSGN"
            ] = "R1-6LHT"
            output_sha = _write_json(output_path, collection)
            manifest_path = roots[1] / "manifest.json"
            manifest = _load_json(manifest_path)
            manifest["layers"][0]["output_sha256"] = output_sha
            _write_json(manifest_path, manifest)
            with self.assertRaisesRegex(ValueError, "unsupported exact"):
                self.load(*roots)

    def test_only_an_approved_residential_ruleset_can_define_scope(self) -> None:
        with self.assertRaisesRegex(TypeError, "ApprovedResidentialRuleset"):
            LocalResidentialLookup.from_snapshots(
                ruleset=object(),  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
