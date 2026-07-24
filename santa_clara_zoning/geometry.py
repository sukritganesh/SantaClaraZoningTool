"""Small GeoJSON point-in-polygon implementation for offline lookup."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Sequence


Point = tuple[float, float]
BOUNDARY_EPSILON = 1e-12


@dataclass(frozen=True)
class BoundingBox:
    xmin: float
    ymin: float
    xmax: float
    ymax: float

    def contains(self, point: Point) -> bool:
        x, y = point
        return self.xmin <= x <= self.xmax and self.ymin <= y <= self.ymax

    def intersects(self, other: "BoundingBox") -> bool:
        """Return whether two inclusive bounding boxes overlap."""

        return not (
            self.xmax < other.xmin
            or other.xmax < self.xmin
            or self.ymax < other.ymin
            or other.ymax < self.ymin
        )


@dataclass(frozen=True)
class SpatialFeature:
    feature: dict[str, Any]
    bounds: BoundingBox


class SpatialIndex:
    """Bounding-box-prefiltered polygon collection."""

    def __init__(self, features: Iterable[dict[str, Any]], *, layer_name: str) -> None:
        indexed = []
        for position, feature in enumerate(features):
            if not isinstance(feature, dict):
                raise ValueError(f"{layer_name} feature {position} is not an object")
            geometry = feature.get("geometry")
            if not isinstance(geometry, dict):
                raise ValueError(f"{layer_name} feature {position} has invalid geometry")
            if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
                raise ValueError(
                    f"{layer_name} feature {position} has unsupported geometry "
                    f"{geometry.get('type')}"
                )
            indexed.append(SpatialFeature(feature=feature, bounds=geometry_bounds(geometry)))
        self._features = tuple(indexed)

    def match(self, point: Point) -> tuple[dict[str, Any], ...]:
        matches = [
            indexed.feature
            for indexed in self._features
            if indexed.bounds.contains(point)
            and point_intersects_geometry(point, indexed.feature["geometry"])
        ]
        return tuple(sorted(matches, key=_object_id))

    def intersecting(self, bounds: BoundingBox) -> tuple[dict[str, Any], ...]:
        """Return source features whose bounds intersect the requested extent."""

        matches = [
            indexed.feature
            for indexed in self._features
            if indexed.bounds.intersects(bounds)
        ]
        return tuple(sorted(matches, key=_object_id))


def geometry_bounds(geometry: dict[str, Any]) -> BoundingBox:
    positions = list(_positions(geometry.get("coordinates")))
    if not positions:
        raise ValueError("Polygon geometry contains no coordinate positions")
    xs = [point[0] for point in positions]
    ys = [point[1] for point in positions]
    return BoundingBox(min(xs), min(ys), max(xs), max(ys))


def point_intersects_geometry(point: Point, geometry: dict[str, Any]) -> bool:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Polygon":
        return _point_intersects_polygon(point, coordinates)
    if geometry_type == "MultiPolygon":
        return isinstance(coordinates, list) and any(
            _point_intersects_polygon(point, polygon) for polygon in coordinates
        )
    raise ValueError(f"Unsupported geometry type: {geometry_type}")


def _point_intersects_polygon(point: Point, rings: Any) -> bool:
    if not isinstance(rings, list) or not rings:
        return False
    exterior = _ring_state(point, rings[0])
    if exterior == "boundary":
        return True
    if exterior != "inside":
        return False
    for hole in rings[1:]:
        state = _ring_state(point, hole)
        if state == "boundary":
            return True
        if state == "inside":
            return False
    return True


def _ring_state(point: Point, ring: Any) -> str:
    if not isinstance(ring, list) or len(ring) < 3:
        return "outside"

    x, y = point
    inside = False
    previous = _point(ring[-1])
    for raw_current in ring:
        current = _point(raw_current)
        if _point_on_segment(point, previous, current):
            return "boundary"
        x1, y1 = previous
        x2, y2 = current
        if (y1 > y) != (y2 > y):
            crossing_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < crossing_x:
                inside = not inside
        previous = current
    return "inside" if inside else "outside"


def _point_on_segment(point: Point, start: Point, end: Point) -> bool:
    x, y = point
    x1, y1 = start
    x2, y2 = end
    cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
    if abs(cross) > BOUNDARY_EPSILON:
        return False
    return (
        min(x1, x2) - BOUNDARY_EPSILON <= x <= max(x1, x2) + BOUNDARY_EPSILON
        and min(y1, y2) - BOUNDARY_EPSILON
        <= y
        <= max(y1, y2) + BOUNDARY_EPSILON
    )


def _positions(value: Any) -> Iterator[Point]:
    if (
        isinstance(value, list)
        and len(value) >= 2
        and _is_number(value[0])
        and _is_number(value[1])
    ):
        yield float(value[0]), float(value[1])
        return
    if isinstance(value, list):
        for nested in value:
            yield from _positions(nested)


def _point(value: Any) -> Point:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or len(value) < 2
        or not _is_number(value[0])
        or not _is_number(value[1])
    ):
        raise ValueError("Invalid coordinate position")
    return float(value[0]), float(value[1])


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _object_id(feature: dict[str, Any]) -> int:
    value = (feature.get("properties") or {}).get("OBJECTID")
    if not isinstance(value, int):
        raise ValueError("Spatial feature is missing an integer OBJECTID")
    return value
