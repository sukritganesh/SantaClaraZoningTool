"""Unit tests for dependency-free GeoJSON point-in-polygon behavior."""

from __future__ import annotations

import unittest

from santa_clara_zoning.geometry import (
    BoundingBox,
    SpatialIndex,
    geometry_bounds,
    point_intersects_geometry,
)


class PointInPolygonTest(unittest.TestCase):
    def setUp(self) -> None:
        self.polygon = {
            "type": "Polygon",
            "coordinates": [
                [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
                [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]],
            ],
        }

    def test_inside_exterior(self) -> None:
        self.assertTrue(point_intersects_geometry((2, 2), self.polygon))

    def test_outside_exterior(self) -> None:
        self.assertFalse(point_intersects_geometry((12, 2), self.polygon))

    def test_inside_hole_is_excluded(self) -> None:
        self.assertFalse(point_intersects_geometry((5, 5), self.polygon))

    def test_boundary_intersects(self) -> None:
        self.assertTrue(point_intersects_geometry((0, 5), self.polygon))
        self.assertTrue(point_intersects_geometry((4, 5), self.polygon))

    def test_multipolygon(self) -> None:
        multipolygon = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                [[[3, 3], [4, 3], [4, 4], [3, 4], [3, 3]]],
            ],
        }
        self.assertTrue(point_intersects_geometry((3.5, 3.5), multipolygon))
        self.assertFalse(point_intersects_geometry((2, 2), multipolygon))

    def test_bounding_box_intersection_is_inclusive(self) -> None:
        bounds = BoundingBox(0, 0, 10, 10)

        self.assertTrue(bounds.intersects(BoundingBox(10, 4, 12, 6)))
        self.assertTrue(bounds.intersects(BoundingBox(2, 2, 3, 3)))
        self.assertFalse(bounds.intersects(BoundingBox(10.1, 0, 12, 2)))

    def test_spatial_index_returns_intersections_in_source_id_order(self) -> None:
        def feature(object_id: int, start: float) -> dict:
            return {
                "type": "Feature",
                "properties": {"OBJECTID": object_id},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [start, 0],
                        [start + 1, 0],
                        [start + 1, 1],
                        [start, 1],
                        [start, 0],
                    ]],
                },
            }

        index = SpatialIndex(
            [feature(9, 2), feature(2, 0), feature(5, 1)],
            layer_name="fixtures",
        )
        matches = index.intersecting(BoundingBox(0.5, -1, 2.2, 2))

        self.assertEqual(
            [match["properties"]["OBJECTID"] for match in matches],
            [2, 5, 9],
        )
        self.assertEqual(
            geometry_bounds(matches[0]["geometry"]),
            BoundingBox(0, 0, 1, 1),
        )


if __name__ == "__main__":
    unittest.main()
