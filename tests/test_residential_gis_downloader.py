from __future__ import annotations

import json
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

from scripts import download_residential_gis as downloader


FIXTURE_INVENTORY = (
    Path(__file__).parent / "fixtures/residential_gis_fixture_inventory.json"
)


def _polygon(offset: float = 0.0) -> dict:
    west = -121.95 + offset
    south = 37.30 + offset
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [west, south],
                [west + 0.001, south],
                [west + 0.001, south + 0.001],
                [west, south + 0.001],
                [west, south],
            ]
        ],
    }


class FakeArcGIS:
    def __init__(
        self,
        object_zones: dict[int, str],
        *,
        excluded_counts: dict[str, int] | None = None,
        requested_counts: dict[str, int] | None = None,
        source_ids: list[int] | None = None,
    ) -> None:
        self.object_zones = object_zones
        self.excluded_counts = excluded_counts or {
            "R1-6LHT": 14,
            "R2-7L": 1,
            "R2HT": 2,
        }
        self.requested_counts = requested_counts or {}
        self.source_ids = source_ids
        self.feature_batch_sizes: list[int] = []

    def __call__(
        self, url: str, *, data: bytes | None = None, attempts: int = 5
    ) -> bytes:
        self.assert_get_only(data)
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        if not parsed.path.endswith("/query"):
            return json.dumps(
                {
                    "objectIdField": "OBJECTID",
                    "geometryType": "esriGeometryPolygon",
                    "fields": [
                        {"name": "OBJECTID", "type": "esriFieldTypeOID"},
                        {"name": "APN", "type": "esriFieldTypeString"},
                        {"name": "ZONGDSGN", "type": "esriFieldTypeString"},
                    ],
                }
            ).encode("utf-8")

        if params.get("returnIdsOnly") == ["true"]:
            object_ids = (
                self.source_ids
                if self.source_ids is not None
                else list(self.object_zones)
            )
            return json.dumps({"objectIds": object_ids}).encode("utf-8")

        if params.get("returnCountOnly") == ["true"]:
            where = params["where"][0]
            designation = where.split("'", 2)[1]
            count = self.excluded_counts.get(
                designation,
                self.requested_counts.get(
                    designation,
                    sum(
                        zone == designation
                        for zone in self.object_zones.values()
                    ),
                ),
            )
            return json.dumps({"count": count}).encode("utf-8")

        object_ids = [int(value) for value in params["objectIds"][0].split(",")]
        self.feature_batch_sizes.append(len(object_ids))
        if params.get("outFields") != ["*"]:
            raise AssertionError("full attributes were not requested")
        if params.get("returnGeometry") != ["true"]:
            raise AssertionError("geometry was not requested")
        if params.get("outSR") != ["4326"]:
            raise AssertionError("EPSG:4326 was not requested")
        if params.get("returnZ") != ["false"] or params.get("returnM") != [
            "false"
        ]:
            raise AssertionError("Z and M values were not disabled")

        features = [
            {
                "type": "Feature",
                "id": object_id,
                "properties": {
                    "OBJECTID": object_id,
                    "APN": f"000-00-{object_id:03d}",
                    "ZONGDSGN": self.object_zones[object_id],
                },
                "geometry": _polygon(object_id / 100_000),
            }
            for object_id in object_ids
        ]
        return json.dumps(
            {"type": "FeatureCollection", "features": features}
        ).encode("utf-8")

    @staticmethod
    def assert_get_only(data: bytes | None) -> None:
        if data is not None:
            raise AssertionError("residential feature acquisition must use GET")


class ResidentialGISContractTest(unittest.TestCase):
    def test_exact_zone_scope_and_url_safe_batch_limit(self) -> None:
        self.assertEqual(
            downloader.SUPPORTED_DESIGNATIONS,
            (
                "R1-6L",
                "R1-8L",
                "R2",
                "R3",
                "R4",
                "R5",
                "R6",
                "PH-R5",
                "UV",
                "VR",
                "UC",
                "HDF",
            ),
        )
        self.assertEqual(
            downloader.WHERE,
            "ZONGDSGN IN ('R1-6L','R1-8L','R2','R3','R4','R5','R6',"
            "'PH-R5','UV','VR','UC','HDF')",
        )
        self.assertEqual(downloader.MAX_GET_BATCH_SIZE, 100)

        with self.assertRaisesRegex(ValueError, "between 1 and 100"):
            downloader._validate_inputs("2026-07-18", 101)
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            downloader._validate_inputs("../../unsafe", 100)

    def test_download_layer_preserves_and_validates_complete_evidence(self) -> None:
        fake = FakeArcGIS({3: "R2", 1: "R1-6L", 2: "R1-6L"})
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp) / "snapshot"
            root.mkdir()
            with mock.patch.object(downloader, "fetch_bytes", side_effect=fake):
                result = downloader.download_layer(
                    downloader.LAYERS[0], root, batch_size=2
                )

            self.assertEqual(result["source_object_id_count"], 3)
            self.assertEqual(result["downloaded_feature_count"], 3)
            self.assertEqual(result["unique_downloaded_object_id_count"], 3)
            self.assertEqual(result["downloaded_zone_counts"]["R1-6L"], 2)
            self.assertEqual(result["downloaded_zone_counts"]["R2"], 1)
            self.assertEqual(result["downloaded_zone_counts"]["R5"], 0)
            self.assertEqual(result["downloaded_zone_counts"]["R6"], 0)
            self.assertEqual(
                set(result["downloaded_zone_counts"]),
                set(downloader.SUPPORTED_DESIGNATIONS),
            )
            self.assertEqual(result["observed_designations"], ["R1-6L", "R2"])
            self.assertEqual(
                result["excluded_designation_preflight_counts"],
                {"R1-6LHT": 14, "R2-7L": 1, "R2HT": 2},
            )
            self.assertEqual(result["raw_chunks"]["count"], 2)
            self.assertEqual(fake.feature_batch_sizes, [2, 1])
            self.assertEqual(result["output_spatial_reference"], "EPSG:4326")
            self.assertEqual(result["query_method"], "GET")

            evidence_records = [
                result["metadata"],
                result["object_ids"],
                result["output"],
                *result["raw_chunks"]["inventory"],
                *result["count_response_inventory"]["requested"],
                *result["count_response_inventory"]["excluded_preflight"],
            ]
            for record in evidence_records:
                evidence_path = root / record["file"]
                self.assertTrue(evidence_path.is_file())
                self.assertEqual(record["bytes"], evidence_path.stat().st_size)
                self.assertEqual(
                    record["sha256"], downloader.sha256_file(evidence_path)
                )

            output = json.loads((root / result["output_file"]).read_text())
            self.assertEqual(output["type"], "FeatureCollection")
            self.assertEqual(len(output["features"]), 3)

    def test_rejects_duplicate_source_ids_before_feature_batches(self) -> None:
        fake = FakeArcGIS({1: "R1-6L"}, source_ids=[1, 1])
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp) / "snapshot"
            root.mkdir()
            with mock.patch.object(downloader, "fetch_bytes", side_effect=fake):
                with self.assertRaisesRegex(RuntimeError, "Duplicate source"):
                    downloader.download_layer(
                        downloader.LAYERS[0], root, batch_size=100
                    )
            self.assertEqual(fake.feature_batch_sizes, [])

    def test_rejects_designation_outside_exact_filter(self) -> None:
        fake = FakeArcGIS(
            {1: "R2HT"},
            excluded_counts={},
            requested_counts={"R1-6L": 1},
        )
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp) / "snapshot"
            root.mkdir()
            with mock.patch.object(downloader, "fetch_bytes", side_effect=fake):
                with self.assertRaisesRegex(RuntimeError, "unexpected designation"):
                    downloader.download_layer(
                        downloader.LAYERS[0], root, batch_size=100
                    )

    def test_cross_layer_zone_count_mismatch_stops_validation(self) -> None:
        base_counts = {
            designation: 0 for designation in downloader.SUPPORTED_DESIGNATIONS
        }
        base_counts["R1-6L"] = 2
        excluded = {
            designation: 0
            for designation in downloader.EXCLUDED_PREFLIGHT_DESIGNATIONS
        }
        parcels = {
            "slug": "parcels",
            "downloaded_zone_counts": base_counts,
            "excluded_designation_preflight_counts": excluded,
        }
        zoning = {
            "slug": "current_zoning",
            "downloaded_zone_counts": {**base_counts, "R1-6L": 1},
            "excluded_designation_preflight_counts": excluded,
        }

        with self.assertRaisesRegex(RuntimeError, "requested counts differ"):
            downloader.validate_cross_layer_results([parcels, zoning])

    def test_failed_acquisition_records_completed_layer_evidence(self) -> None:
        completed = {"slug": "parcels", "validation": "complete"}
        with tempfile.TemporaryDirectory() as raw_temp:
            output_parent = Path(raw_temp)
            with mock.patch.object(
                downloader,
                "download_layer",
                side_effect=[completed, RuntimeError("simulated failure")],
            ):
                with self.assertRaisesRegex(RuntimeError, "simulated failure"):
                    downloader.run_snapshot(
                        snapshot_date="2026-07-18",
                        batch_size=100,
                        output_parent=output_parent,
                    )

            root = (
                output_parent / "2026-07-18" / "santa_clara_residential_gis"
            )
            failure = json.loads(
                (root / "manifest.failed.json").read_text(encoding="utf-8")
            )
            self.assertEqual(failure["status"], "failed")
            self.assertEqual(failure["failed_stage"], "current_zoning")
            self.assertEqual(failure["completed_layers"], [completed])
            self.assertEqual(failure["error_type"], "RuntimeError")

    def test_snapshot_refuses_to_overwrite_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            output_parent = Path(raw_temp)
            root = (
                output_parent / "2026-07-18" / "santa_clara_residential_gis"
            )
            root.mkdir(parents=True)
            marker = root / "owner-data.txt"
            marker.write_text("preserve", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                downloader.run_snapshot(
                    snapshot_date="2026-07-18",
                    batch_size=100,
                    output_parent=output_parent,
                )
            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")

    def test_fixture_inventory_closes_reachable_and_synthetic_scope(self) -> None:
        inventory = json.loads(FIXTURE_INVENTORY.read_text(encoding="utf-8"))
        real = inventory["real_address_fixtures"]
        real_by_zone = {fixture["designation"]: fixture for fixture in real}
        self.assertEqual(
            set(real_by_zone),
            set(downloader.SUPPORTED_DESIGNATIONS).difference({"R5", "R6"}),
        )
        self.assertEqual(len(real_by_zone), len(real))

        for designation, fixture in real_by_zone.items():
            self.assertEqual(fixture["address"]["unit"], None)
            self.assertEqual(fixture["parcel"]["designation"], designation)
            self.assertEqual(
                fixture["current_zoning"]["designation"], designation
            )
            self.assertEqual(
                fixture["parcel"]["source_object_id"],
                fixture["current_zoning"]["source_object_id"],
            )
            self.assertEqual(
                fixture["verification"],
                {
                    "exact_address_match_count": 1,
                    "parcel_match_count": 1,
                    "current_zoning_match_count": 1,
                    "parcel_and_current_zoning_agree": True,
                },
            )

        zero_count = {
            fixture["designation"]: fixture
            for fixture in inventory["synthetic_zero_count_fixtures"]
        }
        self.assertEqual(set(zero_count), {"R5", "R6"})
        for fixture in zero_count.values():
            self.assertEqual(fixture["parcel_source_count"], 0)
            self.assertEqual(fixture["current_zoning_source_count"], 0)

        excluded = {
            fixture["designation"]: fixture
            for fixture in inventory[
                "synthetic_excluded_designation_fixtures"
            ]
        }
        self.assertEqual(
            set(excluded), set(downloader.EXCLUDED_PREFLIGHT_DESIGNATIONS)
        )
        for fixture in excluded.values():
            self.assertEqual(
                fixture["expected_treatment"], "unsupported_exact_designation"
            )
            self.assertNotEqual(
                fixture["designation"], fixture["must_not_normalize_to"]
            )


if __name__ == "__main__":
    unittest.main()
