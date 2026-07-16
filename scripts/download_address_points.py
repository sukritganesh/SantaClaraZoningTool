#!/usr/bin/env python3
"""Download and validate Santa Clara's public address-point layer."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from arcgis_snapshot import (
    chunks,
    encode_form,
    encode_url,
    fetch_bytes,
    parse_json,
    sha256_file,
    write_bytes,
    write_json,
)


LAYER_URL = (
    "https://map.santaclaraca.gov/maps/rest/services/OPENDATA/"
    "CSCAddress_Active/MapServer/0"
)
WHERE = "1=1"
DEFAULT_SNAPSHOT_DATE = datetime.now(timezone.utc).date().isoformat()


def object_id_field(metadata: dict[str, Any]) -> str:
    """Return the layer's single object-ID field."""

    declared = metadata.get("objectIdField")
    if declared:
        return str(declared)

    candidates = [
        field.get("name")
        for field in metadata.get("fields", [])
        if field.get("type") == "esriFieldTypeOID"
    ]
    if len(candidates) != 1 or not candidates[0]:
        raise RuntimeError("Could not determine the address layer's object-ID field")
    return str(candidates[0])


def value_present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def distribution(features: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts = Counter(
        str((feature.get("properties") or {}).get(field))
        for feature in features
    )
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def build_schema_report(
    metadata: dict[str, Any], features: list[dict[str, Any]]
) -> dict[str, Any]:
    """Summarize the raw address schema without normalizing source values."""

    critical_fields = ["CSCADDR", "ADDRNUM", "STRNAME", "ADDRCITY", "ADDRZIP5"]
    missing_counts = {
        field: sum(
            not value_present((feature.get("properties") or {}).get(field))
            for feature in features
        )
        for field in critical_fields
    }

    full_addresses = [
        str((feature.get("properties") or {}).get("CSCADDR")).strip().upper()
        for feature in features
        if value_present((feature.get("properties") or {}).get("CSCADDR"))
    ]
    full_address_counts = Counter(full_addresses)
    duplicates = {
        address: count
        for address, count in full_address_counts.items()
        if count > 1
    }

    points = [
        feature.get("geometry") or {}
        for feature in features
        if (feature.get("geometry") or {}).get("type") == "Point"
    ]
    coordinates = [geometry.get("coordinates") for geometry in points]
    valid_coordinates = [
        value
        for value in coordinates
        if isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], (int, float))
        and isinstance(value[1], (int, float))
    ]

    bounds = None
    if valid_coordinates:
        xs = [value[0] for value in valid_coordinates]
        ys = [value[1] for value in valid_coordinates]
        bounds = {
            "xmin": min(xs),
            "ymin": min(ys),
            "xmax": max(xs),
            "ymax": max(ys),
        }

    fields = [
        {
            "name": field.get("name"),
            "alias": field.get("alias"),
            "type": field.get("type"),
            "length": field.get("length"),
        }
        for field in metadata.get("fields", [])
    ]

    return {
        "record_count": len(features),
        "geometry_type": metadata.get("geometryType"),
        "output_spatial_reference": "EPSG:4326",
        "coordinate_bounds": bounds,
        "fields": fields,
        "critical_field_missing_counts": missing_counts,
        "records_with_unit": sum(
            value_present((feature.get("properties") or {}).get("ADDRUNIT"))
            for feature in features
        ),
        "unique_full_address_count": len(full_address_counts),
        "duplicated_full_address_value_count": len(duplicates),
        "records_with_duplicated_full_address": sum(duplicates.values()),
        "maximum_full_address_duplicate_count": max(duplicates.values(), default=1),
        "top_duplicated_full_addresses": [
            {"address": address, "count": count}
            for address, count in sorted(
                duplicates.items(), key=lambda item: (-item[1], item[0])
            )[:20]
        ],
        "status_counts": distribution(features, "CSCSTATUS"),
        "city_counts": distribution(features, "ADDRCITY"),
        "zip_counts": distribution(features, "ADDRZIP5"),
        "street_type_counts": distribution(features, "STRTYPE"),
    }


def download_snapshot(root: Path, batch_size: int) -> dict[str, Any]:
    layer_root = root / "address_points"
    raw_chunks = layer_root / "chunks"
    raw_chunks.mkdir(parents=True, exist_ok=False)

    metadata_url = encode_url(LAYER_URL, {"f": "pjson"})
    metadata_bytes = fetch_bytes(metadata_url)
    metadata = parse_json(metadata_bytes, source_url=metadata_url)
    write_bytes(layer_root / "metadata.json", metadata_bytes)

    oid_field = object_id_field(metadata)
    ids_url = encode_url(
        f"{LAYER_URL}/query",
        {"where": WHERE, "returnIdsOnly": "true", "f": "json"},
    )
    ids_bytes = fetch_bytes(ids_url)
    ids_response = parse_json(ids_bytes, source_url=ids_url)
    write_bytes(layer_root / "object_ids.json", ids_bytes)

    object_ids = ids_response.get("objectIds") or []
    if not isinstance(object_ids, list) or not all(isinstance(value, int) for value in object_ids):
        raise RuntimeError("Address layer returned an invalid object-ID response")
    if len(object_ids) != len(set(object_ids)):
        raise RuntimeError("Address layer returned duplicate source object IDs")
    object_ids.sort()

    feature_collection: dict[str, Any] = {
        "type": "FeatureCollection",
        "name": "santa_clara_address_points",
        "features": [],
    }
    batches = chunks(object_ids, batch_size)
    query_url = f"{LAYER_URL}/query"

    for number, object_id_batch in enumerate(batches, start=1):
        params = {
            "objectIds": ",".join(str(value) for value in object_id_batch),
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "returnZ": "false",
            "returnM": "false",
            "f": "geojson",
        }
        payload = fetch_bytes(query_url, data=encode_form(params))
        parsed = parse_json(payload, source_url=f"{query_url} (POST batch {number})")
        batch_path = raw_chunks / f"batch-{number:04d}.geojson"
        write_bytes(batch_path, payload)

        batch_features = parsed.get("features")
        if not isinstance(batch_features, list):
            raise RuntimeError(f"Invalid GeoJSON features in {batch_path}")
        feature_collection["features"].extend(batch_features)

        print(
            f"address_points: batch {number}/{len(batches)} "
            f"({len(feature_collection['features'])}/{len(object_ids)} features)",
            flush=True,
        )

    features = feature_collection["features"]
    downloaded_ids = []
    for feature in features:
        properties = feature.get("properties") or {}
        value = properties.get(oid_field)
        if value is None:
            raise RuntimeError(f"Address feature is missing object-ID field {oid_field}")
        downloaded_ids.append(value)

    source_id_set = set(object_ids)
    downloaded_id_set = set(downloaded_ids)
    if len(features) != len(object_ids):
        raise RuntimeError(
            f"Count mismatch: expected {len(object_ids)}, downloaded {len(features)}"
        )
    if downloaded_id_set != source_id_set:
        missing = sorted(source_id_set - downloaded_id_set)
        unexpected = sorted(downloaded_id_set - source_id_set)
        raise RuntimeError(
            f"Object-ID mismatch: missing={missing[:10]}, unexpected={unexpected[:10]}"
        )

    non_point_count = sum(
        (feature.get("geometry") or {}).get("type") != "Point"
        for feature in features
    )
    if non_point_count:
        raise RuntimeError(f"Address snapshot contains {non_point_count} non-point features")

    output_path = root / "address_points.geojson"
    write_json(output_path, feature_collection, indent=None)

    schema_report = build_schema_report(metadata, features)
    schema_report_path = root / "schema_report.json"
    write_json(schema_report_path, schema_report)

    return {
        "source_layer_url": LAYER_URL,
        "where": WHERE,
        "query_method": "POST",
        "metadata_file": str((layer_root / "metadata.json").relative_to(root)),
        "object_ids_file": str((layer_root / "object_ids.json").relative_to(root)),
        "raw_chunk_directory": str(raw_chunks.relative_to(root)),
        "raw_chunk_count": len(batches),
        "object_id_field": oid_field,
        "source_object_id_count": len(object_ids),
        "downloaded_feature_count": len(features),
        "unique_downloaded_object_id_count": len(downloaded_id_set),
        "output_file": output_path.name,
        "output_bytes": output_path.stat().st_size,
        "output_sha256": sha256_file(output_path),
        "output_spatial_reference": "EPSG:4326",
        "schema_report_file": schema_report_path.name,
        "schema_report_sha256": sha256_file(schema_report_path),
        "validation": "complete",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-date", default=DEFAULT_SNAPSHOT_DATE)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Object IDs per POST query (default: 1000)",
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
    if args.batch_size < 1 or args.batch_size > 5000:
        raise ValueError("--batch-size must be between 1 and 5000")

    root = args.output_parent / args.snapshot_date / "santa_clara_address_points"
    root.mkdir(parents=True, exist_ok=False)

    started = datetime.now(timezone.utc)
    try:
        result = download_snapshot(root, args.batch_size)
    except Exception:
        write_json(
            root / "manifest.failed.json",
            {
                "snapshot_date": args.snapshot_date,
                "download_started_utc": started.isoformat(),
                "download_failed_utc": datetime.now(timezone.utc).isoformat(),
                "status": "failed",
            },
        )
        raise

    manifest = {
        "snapshot_date": args.snapshot_date,
        "download_started_utc": started.isoformat(),
        "download_completed_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "purpose": "Citywide address-point source for offline parcel resolution",
        "batch_size": args.batch_size,
        "layer": result,
        "notes": [
            "This is a complete citywide source snapshot, not an R1-only subset.",
            "No address normalization, parcel join, database, or zoning evaluation was created.",
            "POST batching avoids the ArcGIS GET URL-length limit.",
        ],
    }
    write_json(root / "manifest.json", manifest)

    print(f"Snapshot complete: {root}")
    print(
        f"- address_points: {result['downloaded_feature_count']} features, "
        f"{result['output_bytes']} bytes"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
