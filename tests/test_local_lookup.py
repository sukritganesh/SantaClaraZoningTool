"""Integration tests over the canonical local GIS snapshots."""

from __future__ import annotations

import unittest

from santa_clara_zoning.lookup import (
    DEFAULT_ADDRESS_SNAPSHOT,
    DEFAULT_R1_SNAPSHOT,
    LocalR1Lookup,
    _spatial_result,
)


SNAPSHOTS_AVAILABLE = (
    (DEFAULT_ADDRESS_SNAPSHOT / "address_points.geojson").is_file()
    and (DEFAULT_R1_SNAPSHOT / "parcels_r1.geojson").is_file()
    and (DEFAULT_R1_SNAPSHOT / "current_zoning_r1.geojson").is_file()
)


@unittest.skipUnless(SNAPSHOTS_AVAILABLE, "canonical raw GIS snapshots are not present")
class LocalR1LookupIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.lookup = LocalR1Lookup.from_snapshots()

    def test_r1_6l_fixture(self) -> None:
        result = self.lookup.lookup("636 barto st santa clara ca")
        self.assertEqual(result["status"], "r1_zone_found")
        self.assertEqual(result["query"]["normalized_address"], "636 BARTO ST")
        self.assertEqual(result["parcel"]["apn"], "293-16-045")
        self.assertEqual(result["parcel"]["designation"], "R1-6L")
        self.assertEqual(result["zoning"]["designation"], "R1-6L")
        self.assertTrue(result["zoning"]["parcel_attribute_agrees"])

    def test_r1_8l_fixture(self) -> None:
        result = self.lookup.lookup("108 Brookside Avenue")
        self.assertEqual(result["status"], "r1_zone_found")
        self.assertEqual(result["parcel"]["apn"], "303-22-022")
        self.assertEqual(result["zoning"]["designation"], "R1-8L")

    def test_non_r1_address_is_controlled(self) -> None:
        result = self.lookup.lookup("1500 Warburton Avenue")
        self.assertEqual(result["status"], "outside_supported_r1_snapshot")
        self.assertEqual(result["spatial_match_counts"]["r1_parcels"], 0)
        self.assertEqual(result["spatial_match_counts"]["r1_zoning_features"], 0)

    def test_unit_address_matches_one_source_record(self) -> None:
        result = self.lookup.lookup("1577 Pomeroy Avenue, Unit 202")
        self.assertEqual(result["address"]["unit"], "202")
        self.assertEqual(result["address"]["source_object_id"], 193649338)

    def test_duplicate_full_address_is_not_silently_selected(self) -> None:
        result = self.lookup.lookup("324 Los Padres Boulevard")
        self.assertEqual(result["status"], "address_ambiguous")
        self.assertEqual(len(result["address_candidates"]), 2)

    def test_unmatched_address_is_controlled(self) -> None:
        result = self.lookup.lookup("99999 No Such Street")
        self.assertEqual(result["status"], "address_not_found")
        self.assertEqual(result["reason_code"], "no_exact_address_match")


class SpatialOutcomeTest(unittest.TestCase):
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

    def spatial_feature(self, object_id: int, zone: str, *, parcel: bool) -> dict:
        properties = {"OBJECTID": object_id, "ZONGDSGN": zone}
        if parcel:
            properties["APN"] = "000-00-000"
        return {"properties": properties, "geometry": None}

    def test_mismatched_designations_require_review(self) -> None:
        result = _spatial_result(
            base=self.base,
            address=self.address,
            parcel_matches=(self.spatial_feature(1, "R1-6L", parcel=True),),
            zoning_matches=(self.spatial_feature(2, "R1-8L", parcel=False),),
        )
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["reason_code"], "parcel_zoning_designation_mismatch")

    def test_incomplete_spatial_match_requires_review(self) -> None:
        result = _spatial_result(
            base=self.base,
            address=self.address,
            parcel_matches=(self.spatial_feature(1, "R1-6L", parcel=True),),
            zoning_matches=(),
        )
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["reason_code"], "spatial_match_count_unexpected")


if __name__ == "__main__":
    unittest.main()
