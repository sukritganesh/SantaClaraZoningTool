"""Unit tests for dependency-free GeoJSON point-in-polygon behavior."""

from __future__ import annotations

import unittest

from santa_clara_zoning.geometry import point_intersects_geometry


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


if __name__ == "__main__":
    unittest.main()
