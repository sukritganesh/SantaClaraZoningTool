#!/usr/bin/env python3
"""Download a validated Santa Clara residential-zoning GIS snapshot.

The snapshot contains only source parcel and current-zoning polygons for the
exact residential designations approved for expansion research. It does not
normalize zone names, join layers, infer permissions, or evaluate regulations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from .arcgis_snapshot import (
        chunks,
        encode_url,
        fetch_bytes,
        parse_json,
        sha256_file,
        write_bytes,
        write_json,
    )
except ImportError:  # Direct execution from the repository root.
    from arcgis_snapshot import (
        chunks,
        encode_url,
        fetch_bytes,
        parse_json,
        sha256_file,
        write_bytes,
        write_json,
    )


SUPPORTED_DESIGNATIONS = (
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
)
EXCLUDED_PREFLIGHT_DESIGNATIONS = ("R1-6LHT", "R2-7L", "R2HT")
WHERE = "ZONGDSGN IN (" + ",".join(
    f"'{designation}'" for designation in SUPPORTED_DESIGNATIONS
) + ")"
DEFAULT_SNAPSHOT_DATE = datetime.now(timezone.utc).date().isoformat()
MAX_GET_BATCH_SIZE = 100


@dataclass(frozen=True)
class Layer:
    """One zoning-bearing ArcGIS layer included in the snapshot."""

    slug: str
    url: str
    output_name: str
    required_fields: tuple[str, ...]


LAYERS = (
    Layer(
        slug="parcels",
        url=(
            "https://map.santaclaraca.gov/maps/rest/services/OPENDATA/"
            "RegionalBaseOpenData/MapServer/7"
        ),
        output_name="parcels_residential.geojson",
        required_fields=("APN", "ZONGDSGN"),
    ),
    Layer(
        slug="current_zoning",
        url=(
            "https://map.santaclaraca.gov/maps/rest/services/OPENDATA/"
            "RegionalZoningOpenData/MapServer/0"
        ),
        output_name="current_zoning_residential.geojson",
        required_fields=("ZONGDSGN",),
    ),
)


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_record(path: Path, root: Path) -> dict[str, Any]:
    return {
        "file": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _safe_designation_filename(designation: str) -> str:
    normalized = "".join(
        character.lower() if character.isalnum() else "_"
        for character in designation
    ).strip("_")
    return f"{normalized}.json"


def _object_id_field(metadata: dict[str, Any], layer: Layer) -> str:
    declared = metadata.get("objectIdField")
    if declared:
        return str(declared)

    candidates = [
        field.get("name")
        for field in metadata.get("fields", [])
        if isinstance(field, dict)
        and field.get("type") == "esriFieldTypeOID"
        and field.get("name")
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"Could not determine object ID field for {layer.slug}")
    return str(candidates[0])


def _validate_metadata(
    metadata: dict[str, Any], layer: Layer, object_id_field: str
) -> None:
    if metadata.get("geometryType") != "esriGeometryPolygon":
        raise RuntimeError(
            f"{layer.slug} metadata is not polygonal: "
            f"{metadata.get('geometryType')!r}"
        )

    field_names = {
        str(field.get("name"))
        for field in metadata.get("fields", [])
        if isinstance(field, dict) and field.get("name")
    }
    missing = sorted(
        {object_id_field, *layer.required_fields}.difference(field_names)
    )
    if missing:
        raise RuntimeError(
            f"{layer.slug} metadata is missing required fields: {missing}"
        )


def _validate_position(position: Any, *, context: str) -> None:
    if not isinstance(position, list) or len(position) != 2:
        raise RuntimeError(f"{context} is not a two-dimensional coordinate")
    longitude, latitude = position
    if (
        isinstance(longitude, bool)
        or isinstance(latitude, bool)
        or not isinstance(longitude, (int, float))
        or not isinstance(latitude, (int, float))
        or not math.isfinite(longitude)
        or not math.isfinite(latitude)
    ):
        raise RuntimeError(f"{context} contains a non-finite coordinate")
    if not -180 <= longitude <= 180 or not -90 <= latitude <= 90:
        raise RuntimeError(f"{context} is outside EPSG:4326 coordinate bounds")


def _validate_ring(ring: Any, *, context: str) -> None:
    if not isinstance(ring, list) or len(ring) < 4:
        raise RuntimeError(f"{context} is not a valid GeoJSON linear ring")
    for index, position in enumerate(ring):
        _validate_position(position, context=f"{context} position {index}")
    if ring[0] != ring[-1]:
        raise RuntimeError(f"{context} is not closed")


def _validate_polygon_coordinates(coordinates: Any, *, context: str) -> None:
    if not isinstance(coordinates, list) or not coordinates:
        raise RuntimeError(f"{context} has no polygon rings")
    for index, ring in enumerate(coordinates):
        _validate_ring(ring, context=f"{context} ring {index}")


def _validate_geometry(geometry: Any, *, context: str) -> None:
    if not isinstance(geometry, dict):
        raise RuntimeError(f"{context} has no GeoJSON geometry")
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Polygon":
        _validate_polygon_coordinates(coordinates, context=context)
        return
    if geometry_type == "MultiPolygon":
        if not isinstance(coordinates, list) or not coordinates:
            raise RuntimeError(f"{context} has no multipolygon members")
        for index, polygon in enumerate(coordinates):
            _validate_polygon_coordinates(
                polygon, context=f"{context} polygon {index}"
            )
        return
    raise RuntimeError(
        f"{context} has unsupported geometry type {geometry_type!r}"
    )


def _validated_feature_identity(
    feature: Any,
    *,
    layer: Layer,
    object_id_field: str,
) -> tuple[int, str]:
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        raise RuntimeError(f"{layer.slug} response contains a non-Feature record")
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        raise RuntimeError(f"{layer.slug} feature has no properties object")

    missing = [
        field
        for field in layer.required_fields
        if properties.get(field) is None or str(properties.get(field)).strip() == ""
    ]
    if missing:
        raise RuntimeError(
            f"{layer.slug} feature is missing required values: {missing}"
        )

    object_id = properties.get(object_id_field)
    if type(object_id) is not int:
        raise RuntimeError(
            f"{layer.slug} feature has invalid {object_id_field}: {object_id!r}"
        )
    designation = properties.get("ZONGDSGN")
    if not isinstance(designation, str) or designation not in SUPPORTED_DESIGNATIONS:
        raise RuntimeError(
            f"{layer.slug} feature has unexpected designation {designation!r}"
        )

    _validate_geometry(
        feature.get("geometry"),
        context=f"{layer.slug} feature {object_id}",
    )
    return object_id, designation


def _download_designation_counts(
    *,
    layer: Layer,
    layer_root: Path,
    root: Path,
    group: str,
    designations: Iterable[str],
) -> tuple[dict[str, int], list[dict[str, Any]]]:
    counts: dict[str, int] = {}
    inventory: list[dict[str, Any]] = []

    for designation in designations:
        where = f"ZONGDSGN = '{designation}'"
        query_url = encode_url(
            f"{layer.url}/query",
            {
                "where": where,
                "returnCountOnly": "true",
                "f": "json",
            },
        )
        payload = fetch_bytes(query_url)
        parsed = parse_json(payload, source_url=query_url)
        count = parsed.get("count")
        if type(count) is not int or count < 0:
            raise RuntimeError(
                f"Invalid {group} count for {layer.slug} {designation}: {count!r}"
            )

        response_path = (
            layer_root
            / "counts"
            / group
            / _safe_designation_filename(designation)
        )
        write_bytes(response_path, payload)
        record = _file_record(response_path, root)
        record.update(
            {
                "designation": designation,
                "where": where,
                "query_url": query_url,
                "count": count,
            }
        )
        counts[designation] = count
        inventory.append(record)

    return counts, inventory


def download_layer(layer: Layer, root: Path, batch_size: int) -> dict[str, Any]:
    """Download and validate one complete filtered ArcGIS layer."""

    layer_root = root / layer.slug
    raw_chunks = layer_root / "chunks"
    raw_chunks.mkdir(parents=True, exist_ok=False)

    metadata_url = encode_url(layer.url, {"f": "pjson"})
    metadata_bytes = fetch_bytes(metadata_url)
    metadata = parse_json(metadata_bytes, source_url=metadata_url)
    metadata_path = layer_root / "metadata.json"
    write_bytes(metadata_path, metadata_bytes)

    object_id_field = _object_id_field(metadata, layer)
    _validate_metadata(metadata, layer, object_id_field)

    ids_url = encode_url(
        f"{layer.url}/query",
        {
            "where": WHERE,
            "returnIdsOnly": "true",
            "f": "json",
        },
    )
    ids_bytes = fetch_bytes(ids_url)
    ids_response = parse_json(ids_bytes, source_url=ids_url)
    object_ids_path = layer_root / "object_ids.json"
    write_bytes(object_ids_path, ids_bytes)

    object_ids = ids_response.get("objectIds") or []
    if not isinstance(object_ids, list) or not all(
        type(value) is int for value in object_ids
    ):
        raise RuntimeError(f"Invalid object ID response for {layer.slug}")
    if len(object_ids) != len(set(object_ids)):
        raise RuntimeError(f"Duplicate source object IDs returned for {layer.slug}")
    object_ids.sort()

    requested_counts, requested_count_inventory = _download_designation_counts(
        layer=layer,
        layer_root=layer_root,
        root=root,
        group="requested",
        designations=SUPPORTED_DESIGNATIONS,
    )
    excluded_counts, excluded_count_inventory = _download_designation_counts(
        layer=layer,
        layer_root=layer_root,
        root=root,
        group="excluded_preflight",
        designations=EXCLUDED_PREFLIGHT_DESIGNATIONS,
    )

    source_count_total = sum(requested_counts.values())
    if source_count_total != len(object_ids):
        raise RuntimeError(
            f"Source count mismatch for {layer.slug}: object IDs={len(object_ids)}, "
            f"per-zone counts={source_count_total}"
        )

    feature_collection: dict[str, Any] = {
        "type": "FeatureCollection",
        "name": f"santa_clara_residential_{layer.slug}",
        "features": [],
    }
    batch_inventory: list[dict[str, Any]] = []
    batches = chunks(object_ids, batch_size)

    for number, object_id_batch in enumerate(batches, start=1):
        query_url = encode_url(
            f"{layer.url}/query",
            {
                "objectIds": ",".join(str(value) for value in object_id_batch),
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": "4326",
                "returnZ": "false",
                "returnM": "false",
                "f": "geojson",
            },
        )
        payload = fetch_bytes(query_url)
        parsed = parse_json(payload, source_url=query_url)
        batch_path = raw_chunks / f"batch-{number:04d}.geojson"
        write_bytes(batch_path, payload)

        batch_features = parsed.get("features")
        if parsed.get("type") != "FeatureCollection" or not isinstance(
            batch_features, list
        ):
            raise RuntimeError(f"Invalid GeoJSON collection in {batch_path}")

        batch_ids = [
            _validated_feature_identity(
                feature,
                layer=layer,
                object_id_field=object_id_field,
            )[0]
            for feature in batch_features
        ]
        if len(batch_ids) != len(set(batch_ids)):
            raise RuntimeError(f"Duplicate downloaded IDs in {batch_path}")
        if set(batch_ids) != set(object_id_batch):
            missing = sorted(set(object_id_batch).difference(batch_ids))
            unexpected = sorted(set(batch_ids).difference(object_id_batch))
            raise RuntimeError(
                f"Batch ID mismatch for {layer.slug}: missing={missing[:10]}, "
                f"unexpected={unexpected[:10]}"
            )

        feature_collection["features"].extend(batch_features)
        chunk_record = _file_record(batch_path, root)
        chunk_record.update(
            {
                "query_url": query_url,
                "requested_object_id_count": len(object_id_batch),
                "first_object_id": object_id_batch[0],
                "last_object_id": object_id_batch[-1],
                "downloaded_feature_count": len(batch_features),
            }
        )
        batch_inventory.append(chunk_record)

        print(
            f"{layer.slug}: batch {number}/{len(batches)} "
            f"({len(feature_collection['features'])}/{len(object_ids)} features)",
            flush=True,
        )

    features = feature_collection["features"]
    downloaded_ids: list[int] = []
    zone_counts = {designation: 0 for designation in SUPPORTED_DESIGNATIONS}
    for feature in features:
        object_id, designation = _validated_feature_identity(
            feature,
            layer=layer,
            object_id_field=object_id_field,
        )
        downloaded_ids.append(object_id)
        zone_counts[designation] += 1

    downloaded_id_set = set(downloaded_ids)
    source_id_set = set(object_ids)
    if len(features) != len(object_ids):
        raise RuntimeError(
            f"Count mismatch for {layer.slug}: expected {len(object_ids)}, "
            f"got {len(features)}"
        )
    if len(downloaded_ids) != len(downloaded_id_set):
        raise RuntimeError(f"Duplicate downloaded object IDs for {layer.slug}")
    if downloaded_id_set != source_id_set:
        missing = sorted(source_id_set.difference(downloaded_id_set))
        unexpected = sorted(downloaded_id_set.difference(source_id_set))
        raise RuntimeError(
            f"ID mismatch for {layer.slug}: missing={missing[:10]}, "
            f"unexpected={unexpected[:10]}"
        )
    if zone_counts != requested_counts:
        differences = {
            designation: {
                "source_count": requested_counts[designation],
                "downloaded_count": zone_counts[designation],
            }
            for designation in SUPPORTED_DESIGNATIONS
            if requested_counts[designation] != zone_counts[designation]
        }
        raise RuntimeError(
            f"Per-zone count mismatch for {layer.slug}: {differences}"
        )

    consolidated_path = root / layer.output_name
    write_json(consolidated_path, feature_collection, indent=None)
    observed_designations = sorted(
        designation for designation, count in zone_counts.items() if count
    )

    metadata_record = _file_record(metadata_path, root)
    object_ids_record = _file_record(object_ids_path, root)
    output_record = _file_record(consolidated_path, root)
    return {
        "slug": layer.slug,
        "source_layer_url": layer.url,
        "metadata_query_url": metadata_url,
        "object_ids_query_url": ids_url,
        "where": WHERE,
        "query_method": "GET",
        "object_id_field": object_id_field,
        "required_fields": list(layer.required_fields),
        "metadata": metadata_record,
        "metadata_file": metadata_record["file"],
        "object_ids": object_ids_record,
        "object_ids_file": object_ids_record["file"],
        "source_object_id_count": len(object_ids),
        "downloaded_feature_count": len(features),
        "unique_downloaded_object_id_count": len(downloaded_id_set),
        "requested_designation_counts": requested_counts,
        "downloaded_zone_counts": zone_counts,
        "observed_designations": observed_designations,
        "excluded_designation_preflight_counts": excluded_counts,
        "count_response_inventory": {
            "requested": requested_count_inventory,
            "excluded_preflight": excluded_count_inventory,
            "inventory_sha256": _canonical_sha256(
                requested_count_inventory + excluded_count_inventory
            ),
        },
        "raw_chunks": {
            "directory": raw_chunks.relative_to(root).as_posix(),
            "count": len(batch_inventory),
            "inventory": batch_inventory,
            "inventory_sha256": _canonical_sha256(batch_inventory),
        },
        "raw_chunk_directory": raw_chunks.relative_to(root).as_posix(),
        "raw_chunk_count": len(batch_inventory),
        "output": output_record,
        "output_file": output_record["file"],
        "output_bytes": output_record["bytes"],
        "output_sha256": output_record["sha256"],
        "output_spatial_reference": "EPSG:4326",
        "validation": "complete",
    }


def validate_cross_layer_results(
    layer_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Require exact requested and excluded counts to agree across layers."""

    by_slug = {result.get("slug"): result for result in layer_results}
    expected_slugs = {layer.slug for layer in LAYERS}
    if len(by_slug) != len(layer_results) or set(by_slug) != expected_slugs:
        raise RuntimeError(
            f"Layer result set mismatch: expected={sorted(expected_slugs)}, "
            f"observed={sorted(str(value) for value in by_slug)}"
        )

    parcel = by_slug["parcels"]
    zoning = by_slug["current_zoning"]
    requested_differences = {
        designation: {
            "parcels": parcel["downloaded_zone_counts"][designation],
            "current_zoning": zoning["downloaded_zone_counts"][designation],
        }
        for designation in SUPPORTED_DESIGNATIONS
        if parcel["downloaded_zone_counts"][designation]
        != zoning["downloaded_zone_counts"][designation]
    }
    if requested_differences:
        raise RuntimeError(
            f"Parcel/current-zoning requested counts differ: {requested_differences}"
        )

    excluded_differences = {
        designation: {
            "parcels": parcel["excluded_designation_preflight_counts"][designation],
            "current_zoning": zoning[
                "excluded_designation_preflight_counts"
            ][designation],
        }
        for designation in EXCLUDED_PREFLIGHT_DESIGNATIONS
        if parcel["excluded_designation_preflight_counts"][designation]
        != zoning["excluded_designation_preflight_counts"][designation]
    }
    if excluded_differences:
        raise RuntimeError(
            f"Parcel/current-zoning excluded counts differ: {excluded_differences}"
        )

    return {
        "requested_zone_counts_agree": True,
        "excluded_preflight_counts_agree": True,
        "requested_zone_counts": parcel["downloaded_zone_counts"],
        "excluded_preflight_counts": parcel[
            "excluded_designation_preflight_counts"
        ],
    }


def _partial_file_inventory(root: Path) -> list[dict[str, Any]]:
    return [
        _file_record(path, root)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != "manifest.failed.json"
    ]


def _validate_inputs(snapshot_date: str, batch_size: int) -> None:
    try:
        parsed_date = date.fromisoformat(snapshot_date)
    except ValueError as exc:
        raise ValueError("--snapshot-date must use YYYY-MM-DD") from exc
    if parsed_date.isoformat() != snapshot_date:
        raise ValueError("--snapshot-date must use YYYY-MM-DD")
    if batch_size < 1 or batch_size > MAX_GET_BATCH_SIZE:
        raise ValueError(
            f"--batch-size must be between 1 and {MAX_GET_BATCH_SIZE} for GET requests"
        )


def run_snapshot(
    *, snapshot_date: str, batch_size: int, output_parent: Path
) -> tuple[Path, dict[str, Any]]:
    """Create one non-overwriting snapshot and return its manifest."""

    _validate_inputs(snapshot_date, batch_size)
    root = output_parent / snapshot_date / "santa_clara_residential_gis"
    root.mkdir(parents=True, exist_ok=False)

    started = datetime.now(timezone.utc)
    layer_results: list[dict[str, Any]] = []
    current_stage = "initialization"
    try:
        for layer in LAYERS:
            current_stage = layer.slug
            layer_results.append(download_layer(layer, root, batch_size))
        current_stage = "cross_layer_validation"
        cross_layer_validation = validate_cross_layer_results(layer_results)
    except Exception as exc:
        partial_inventory = _partial_file_inventory(root)
        failure_manifest = {
            "manifest_schema_version": "1.0.0",
            "snapshot_date": snapshot_date,
            "download_started_utc": started.isoformat(),
            "download_failed_utc": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "failed_stage": current_stage,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "filter": WHERE,
            "requested_designations": list(SUPPORTED_DESIGNATIONS),
            "excluded_preflight_designations": list(
                EXCLUDED_PREFLIGHT_DESIGNATIONS
            ),
            "batch_size": batch_size,
            "completed_layers": layer_results,
            "partial_file_inventory": partial_inventory,
            "partial_file_inventory_sha256": _canonical_sha256(partial_inventory),
        }
        write_json(root / "manifest.failed.json", failure_manifest)
        raise

    completed = datetime.now(timezone.utc)
    manifest = {
        "manifest_schema_version": "1.0.0",
        "snapshot_date": snapshot_date,
        "download_started_utc": started.isoformat(),
        "download_completed_utc": completed.isoformat(),
        "status": "complete",
        "purpose": "Selected Santa Clara residential-zone source polygons",
        "filter": WHERE,
        "requested_designations": list(SUPPORTED_DESIGNATIONS),
        "excluded_preflight_designations": list(
            EXCLUDED_PREFLIGHT_DESIGNATIONS
        ),
        "query_method": "GET",
        "batch_size": batch_size,
        "maximum_get_batch_size": MAX_GET_BATCH_SIZE,
        "layers": layer_results,
        "cross_layer_validation": cross_layer_validation,
        "notes": [
            "This snapshot contains source GIS features only.",
            "Exact zone codes are preserved; no prefix or similarity normalization is used.",
            "Zero requested-zone counts are explicit source results, not legal conclusions.",
            "No database, spatial join, legal-use inference, or regulatory evaluation was created.",
            "Consolidated GeoJSON is validated as two-dimensional EPSG:4326 polygonal data.",
        ],
    }
    write_json(root / "manifest.json", manifest)
    return root, manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-date", default=DEFAULT_SNAPSHOT_DATE)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=MAX_GET_BATCH_SIZE,
        help=(
            "Object IDs per GET query; values above 100 are refused to preserve "
            "the tested URL-length boundary (default: 100)"
        ),
    )
    parser.add_argument(
        "--output-parent",
        type=Path,
        default=Path("data/raw"),
        help="Parent directory for dated snapshots (default: data/raw)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root, manifest = run_snapshot(
        snapshot_date=args.snapshot_date,
        batch_size=args.batch_size,
        output_parent=args.output_parent,
    )

    print(f"Snapshot complete: {root}")
    for result in manifest["layers"]:
        print(
            f"- {result['slug']}: {result['downloaded_feature_count']} features, "
            f"{result['output_bytes']} bytes"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
