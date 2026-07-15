#!/usr/bin/env python3
"""Download a validated Santa Clara R1 GIS snapshot from ArcGIS REST.

This utility only downloads source data. It does not create a database,
normalize fields, perform spatial joins, or evaluate zoning regulations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WHERE = "ZONGDSGN IN ('R1-6L','R1-8L')"
DEFAULT_SNAPSHOT_DATE = datetime.now(timezone.utc).date().isoformat()


@dataclass(frozen=True)
class Layer:
    slug: str
    url: str
    output_name: str


LAYERS = (
    Layer(
        slug="parcels",
        url=(
            "https://map.santaclaraca.gov/maps/rest/services/OPENDATA/"
            "RegionalBaseOpenData/MapServer/7"
        ),
        output_name="parcels_r1.geojson",
    ),
    Layer(
        slug="current_zoning",
        url=(
            "https://map.santaclaraca.gov/maps/rest/services/OPENDATA/"
            "RegionalZoningOpenData/MapServer/0"
        ),
        output_name="current_zoning_r1.geojson",
    ),
)


def encode_url(url: str, params: dict[str, str]) -> str:
    return f"{url}?{urllib.parse.urlencode(params)}"


def fetch_bytes(url: str, *, attempts: int = 5) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json, application/geo+json",
            "User-Agent": "SantaClaraZoningPortal-R1-Snapshot/0.1",
        },
    )

    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == attempts:
                raise RuntimeError(f"Failed after {attempts} attempts: {url}") from exc
            time.sleep(min(2**attempt, 20))

    raise AssertionError("unreachable")


def parse_json(payload: bytes, *, source_url: str) -> dict[str, Any]:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response from {source_url}") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected JSON response from {source_url}")
    if "error" in parsed:
        raise RuntimeError(f"ArcGIS error from {source_url}: {parsed['error']}")
    return parsed


def write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def write_json(path: Path, value: Any, *, indent: int | None = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=indent, sort_keys=indent is not None) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def chunks(values: list[int], size: int) -> list[list[int]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def download_layer(layer: Layer, root: Path, batch_size: int) -> dict[str, Any]:
    layer_root = root / layer.slug
    raw_chunks = layer_root / "chunks"
    raw_chunks.mkdir(parents=True, exist_ok=False)

    metadata_url = encode_url(layer.url, {"f": "pjson"})
    metadata_bytes = fetch_bytes(metadata_url)
    metadata = parse_json(metadata_bytes, source_url=metadata_url)
    write_bytes(layer_root / "metadata.json", metadata_bytes)

    object_id_field = metadata.get("objectIdField")
    if not object_id_field:
        object_id_fields = [
            field.get("name")
            for field in metadata.get("fields", [])
            if field.get("type") == "esriFieldTypeOID"
        ]
        if len(object_id_fields) != 1:
            raise RuntimeError(f"Could not determine object ID field for {layer.slug}")
        object_id_field = object_id_fields[0]

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
    write_bytes(layer_root / "object_ids.json", ids_bytes)

    object_ids = ids_response.get("objectIds") or []
    if not isinstance(object_ids, list) or not all(isinstance(value, int) for value in object_ids):
        raise RuntimeError(f"Invalid object ID response for {layer.slug}")
    if len(object_ids) != len(set(object_ids)):
        raise RuntimeError(f"Duplicate source object IDs returned for {layer.slug}")

    object_ids.sort()
    feature_collection: dict[str, Any] = {
        "type": "FeatureCollection",
        "name": layer.slug,
        "features": [],
    }

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
        if not isinstance(batch_features, list):
            raise RuntimeError(f"Invalid GeoJSON features in {batch_path}")
        feature_collection["features"].extend(batch_features)

        print(
            f"{layer.slug}: batch {number}/{len(batches)} "
            f"({len(feature_collection['features'])}/{len(object_ids)} features)",
            flush=True,
        )

    features = feature_collection["features"]
    downloaded_ids = []
    for feature in features:
        properties = feature.get("properties") or {}
        value = properties.get(object_id_field)
        if value is None:
            raise RuntimeError(
                f"Feature in {layer.slug} is missing object ID field {object_id_field}"
            )
        downloaded_ids.append(value)

    source_id_set = set(object_ids)
    downloaded_id_set = set(downloaded_ids)
    if len(features) != len(object_ids):
        raise RuntimeError(
            f"Count mismatch for {layer.slug}: expected {len(object_ids)}, got {len(features)}"
        )
    if downloaded_id_set != source_id_set:
        missing = sorted(source_id_set - downloaded_id_set)
        unexpected = sorted(downloaded_id_set - source_id_set)
        raise RuntimeError(
            f"ID mismatch for {layer.slug}: missing={missing[:10]}, "
            f"unexpected={unexpected[:10]}"
        )

    consolidated_path = root / layer.output_name
    write_json(consolidated_path, feature_collection, indent=None)

    zone_counts: dict[str, int] = {}
    for feature in features:
        zone = str((feature.get("properties") or {}).get("ZONGDSGN"))
        zone_counts[zone] = zone_counts.get(zone, 0) + 1

    return {
        "slug": layer.slug,
        "source_layer_url": layer.url,
        "where": WHERE,
        "metadata_file": str((layer_root / "metadata.json").relative_to(root)),
        "object_ids_file": str((layer_root / "object_ids.json").relative_to(root)),
        "raw_chunk_directory": str(raw_chunks.relative_to(root)),
        "raw_chunk_count": len(batches),
        "object_id_field": object_id_field,
        "source_object_id_count": len(object_ids),
        "downloaded_feature_count": len(features),
        "unique_downloaded_object_id_count": len(downloaded_id_set),
        "zone_counts": dict(sorted(zone_counts.items())),
        "output_file": consolidated_path.name,
        "output_bytes": consolidated_path.stat().st_size,
        "output_sha256": sha256_file(consolidated_path),
        "output_spatial_reference": "EPSG:4326",
        "validation": "complete",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-date", default=DEFAULT_SNAPSHOT_DATE)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Object IDs per query; 100 stays below the City's URL limit (default: 100)",
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
    if args.batch_size < 1 or args.batch_size > 1000:
        raise ValueError("--batch-size must be between 1 and 1000")

    root = args.output_parent / args.snapshot_date / "santa_clara_r1_gis"
    root.mkdir(parents=True, exist_ok=False)

    started = datetime.now(timezone.utc)
    layer_results = []
    try:
        for layer in LAYERS:
            layer_results.append(download_layer(layer, root, args.batch_size))
    except Exception:
        failure_manifest = {
            "snapshot_date": args.snapshot_date,
            "download_started_utc": started.isoformat(),
            "download_failed_utc": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "completed_layers": layer_results,
        }
        write_json(root / "manifest.failed.json", failure_manifest)
        raise

    completed = datetime.now(timezone.utc)
    manifest = {
        "snapshot_date": args.snapshot_date,
        "download_started_utc": started.isoformat(),
        "download_completed_utc": completed.isoformat(),
        "status": "complete",
        "purpose": "R1-6L and R1-8L prototype research snapshot",
        "filter": WHERE,
        "batch_size": args.batch_size,
        "layers": layer_results,
        "notes": [
            "This snapshot contains source GIS features only.",
            "No database, spatial join, or regulatory evaluation was created.",
            "Consolidated GeoJSON is EPSG:4326; source metadata is preserved per layer.",
        ],
    }
    write_json(root / "manifest.json", manifest)

    print(f"Snapshot complete: {root}")
    for result in layer_results:
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
