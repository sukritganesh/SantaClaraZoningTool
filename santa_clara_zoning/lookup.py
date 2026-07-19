"""Local address-to-parcel-to-R1-zone lookup over immutable snapshots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .addressing import AddressIndex, normalize_address
from .geometry import Point, SpatialIndex


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ADDRESS_SNAPSHOT = (
    REPO_ROOT / "data/raw/2026-07-16/santa_clara_address_points"
)
DEFAULT_R1_SNAPSHOT = REPO_ROOT / "data/raw/2026-07-14/santa_clara_r1_gis"
SUPPORTED_ZONES = {"R1-6L", "R1-8L"}


class LocalR1Lookup:
    """Resolve exact addresses against validated local R1 GIS snapshots."""

    def __init__(
        self,
        *,
        address_index: AddressIndex,
        parcel_index: SpatialIndex,
        zoning_index: SpatialIndex,
        versions: dict[str, str],
        sources: dict[str, str],
    ) -> None:
        self.address_index = address_index
        self.parcel_index = parcel_index
        self.zoning_index = zoning_index
        self.versions = versions
        self.sources = sources

    @classmethod
    def from_snapshots(
        cls,
        *,
        address_snapshot: Path = DEFAULT_ADDRESS_SNAPSHOT,
        r1_snapshot: Path = DEFAULT_R1_SNAPSHOT,
        verify_checksums: bool = True,
    ) -> "LocalR1Lookup":
        """Load and validate the canonical address and R1 source snapshots."""

        address_manifest = _load_json(address_snapshot / "manifest.json")
        r1_manifest = _load_json(r1_snapshot / "manifest.json")
        if address_manifest.get("status") != "complete":
            raise ValueError("Address snapshot manifest is not complete")
        if r1_manifest.get("status") != "complete":
            raise ValueError("R1 snapshot manifest is not complete")

        address_layer = address_manifest.get("layer")
        r1_layers = r1_manifest.get("layers")
        if not isinstance(address_layer, dict) or not isinstance(r1_layers, list):
            raise ValueError("Snapshot manifest has an unsupported structure")
        layers_by_slug = {
            layer.get("slug"): layer for layer in r1_layers if isinstance(layer, dict)
        }
        parcel_layer = layers_by_slug.get("parcels")
        zoning_layer = layers_by_slug.get("current_zoning")
        if not isinstance(parcel_layer, dict) or not isinstance(zoning_layer, dict):
            raise ValueError("R1 manifest is missing parcel or zoning metadata")

        address_features = _load_layer(
            address_snapshot,
            address_layer,
            verify_checksum=verify_checksums,
        )
        parcel_features = _load_layer(
            r1_snapshot,
            parcel_layer,
            verify_checksum=verify_checksums,
        )
        zoning_features = _load_layer(
            r1_snapshot,
            zoning_layer,
            verify_checksum=verify_checksums,
        )
        _validate_r1_features(parcel_features, layer_name="parcels")
        _validate_r1_features(zoning_features, layer_name="current zoning")

        return cls(
            address_index=AddressIndex(address_features),
            parcel_index=SpatialIndex(parcel_features, layer_name="parcels"),
            zoning_index=SpatialIndex(zoning_features, layer_name="current zoning"),
            versions={
                "address_snapshot": str(address_manifest.get("snapshot_date")),
                "r1_gis_snapshot": str(r1_manifest.get("snapshot_date")),
            },
            sources={
                "address_layer": str(address_layer.get("source_layer_url")),
                "parcel_layer": str(parcel_layer.get("source_layer_url")),
                "zoning_layer": str(zoning_layer.get("source_layer_url")),
            },
        )

    def lookup(self, entered_address: str) -> dict[str, Any]:
        """Return a controlled lookup result without guessing among matches."""

        normalized = normalize_address(entered_address)
        result: dict[str, Any] = {
            "query": {
                "entered_address": entered_address,
                "normalized_address": normalized,
            },
            "versions": dict(self.versions),
            "sources": dict(self.sources),
        }
        if not normalized:
            return {
                **result,
                "status": "address_not_found",
                "reason_code": "empty_or_invalid_address",
                "message": "Enter a non-empty Santa Clara street address.",
            }

        address_matches = self.address_index.match(entered_address)
        if not address_matches:
            return {
                **result,
                "status": "address_not_found",
                "reason_code": "no_exact_address_match",
                "message": "No exact normalized match was found in the local address snapshot.",
            }
        if len(address_matches) > 1:
            return {
                **result,
                "status": "address_ambiguous",
                "reason_code": "multiple_exact_address_matches",
                "message": "Multiple source records share this normalized address.",
                "address_candidates": [
                    _address_summary(feature) for feature in address_matches
                ],
            }

        address = address_matches[0]
        point = _address_point(address)
        parcel_matches = self.parcel_index.match(point)
        zoning_matches = self.zoning_index.match(point)
        return _spatial_result(
            base=result,
            address=address,
            parcel_matches=parcel_matches,
            zoning_matches=zoning_matches,
        )


def _spatial_result(
    *,
    base: dict[str, Any],
    address: dict[str, Any],
    parcel_matches: tuple[dict[str, Any], ...],
    zoning_matches: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    result = {
        **base,
        "address": _address_summary(address),
        "spatial_match_counts": {
            "r1_parcels": len(parcel_matches),
            "r1_zoning_features": len(zoning_matches),
        },
    }
    if not parcel_matches and not zoning_matches:
        return {
            **result,
            "status": "outside_supported_r1_snapshot",
            "reason_code": "no_r1_parcel_or_zoning_match",
            "message": (
                "The address was found, but its point does not intersect the filtered "
                "R1-6L/R1-8L snapshot. Its exact non-R1 zoning is not determined here."
            ),
        }

    if len(parcel_matches) != 1 or len(zoning_matches) != 1:
        return {
            **result,
            "status": "review_required",
            "reason_code": "spatial_match_count_unexpected",
            "message": "The R1 parcel and zoning layers did not produce one match each.",
            "parcel_candidates": [_parcel_summary(value) for value in parcel_matches],
            "zoning_candidates": [_zoning_summary(value) for value in zoning_matches],
        }

    parcel = _parcel_summary(parcel_matches[0])
    zoning = _zoning_summary(zoning_matches[0])
    parcel_zone = parcel["designation"]
    zoning_zone = zoning["designation"]
    if parcel_zone not in SUPPORTED_ZONES or zoning_zone not in SUPPORTED_ZONES:
        return {
            **result,
            "status": "review_required",
            "reason_code": "unexpected_zone_in_r1_snapshot",
            "message": "A filtered source feature contains an unsupported designation.",
            "parcel": parcel,
            "zoning": zoning,
        }
    if parcel_zone != zoning_zone:
        return {
            **result,
            "status": "review_required",
            "reason_code": "parcel_zoning_designation_mismatch",
            "message": "The parcel and current-zoning source attributes disagree.",
            "parcel": parcel,
            "zoning": zoning,
        }

    zoning["parcel_attribute_agrees"] = True
    return {
        **result,
        "status": "r1_zone_found",
        "reason_code": "supported_r1_match",
        "message": "One address, parcel, and current R1 zoning feature matched.",
        "parcel": parcel,
        "zoning": zoning,
    }


def _load_layer(
    snapshot_root: Path,
    layer_manifest: dict[str, Any],
    *,
    verify_checksum: bool,
) -> list[dict[str, Any]]:
    if layer_manifest.get("output_spatial_reference") != "EPSG:4326":
        raise ValueError("Lookup layers must use EPSG:4326")
    output_file = layer_manifest.get("output_file")
    if not isinstance(output_file, str):
        raise ValueError("Layer manifest is missing output_file")
    path = snapshot_root / output_file
    if verify_checksum:
        expected = layer_manifest.get("output_sha256")
        if not isinstance(expected, str) or _sha256_file(path) != expected:
            raise ValueError(f"Layer checksum does not match manifest: {path}")
    feature_collection = _load_json(path)
    if feature_collection.get("type") != "FeatureCollection":
        raise ValueError(f"Expected a FeatureCollection at {path}")
    features = feature_collection.get("features")
    if not isinstance(features, list):
        raise ValueError(f"FeatureCollection has no feature array: {path}")
    expected_count = layer_manifest.get("downloaded_feature_count")
    if len(features) != expected_count:
        raise ValueError(
            f"Feature count differs from manifest at {path}: "
            f"expected {expected_count}, got {len(features)}"
        )
    return features


def _validate_r1_features(
    features: list[dict[str, Any]], *, layer_name: str
) -> None:
    for position, feature in enumerate(features):
        properties = feature.get("properties") if isinstance(feature, dict) else None
        if not isinstance(properties, dict):
            raise ValueError(f"{layer_name} feature {position} has invalid properties")
        if properties.get("ZONGDSGN") not in SUPPORTED_ZONES:
            raise ValueError(
                f"{layer_name} feature {position} has an unsupported designation"
            )


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object at {path}")
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _address_point(feature: dict[str, Any]) -> Point:
    coordinates = (feature.get("geometry") or {}).get("coordinates")
    if (
        not isinstance(coordinates, list)
        or len(coordinates) < 2
        or not _is_number(coordinates[0])
        or not _is_number(coordinates[1])
    ):
        raise ValueError("Matched address has invalid point coordinates")
    return float(coordinates[0]), float(coordinates[1])


def _address_summary(feature: dict[str, Any]) -> dict[str, Any]:
    properties = feature.get("properties") or {}
    point = _address_point(feature)
    return {
        "source_object_id": properties.get("OBJECTID"),
        "source_address_id": properties.get("CSCADDID"),
        "display_address": properties.get("CSCADDR"),
        "unit": properties.get("ADDRUNIT"),
        "city": properties.get("ADDRCITY"),
        "zip": properties.get("ADDRZIP5"),
        "longitude": point[0],
        "latitude": point[1],
    }


def _parcel_summary(feature: dict[str, Any]) -> dict[str, Any]:
    properties = feature.get("properties") or {}
    return {
        "source_object_id": properties.get("OBJECTID"),
        "apn": properties.get("APN"),
        "designation": properties.get("ZONGDSGN"),
        "acreage": properties.get("ACREAGE"),
        "general_plan": properties.get("GPLANCRT"),
        "specific_plan": properties.get("SPPLAN"),
        "historic_parcel_type": properties.get("HistoricParcelType"),
    }


def _zoning_summary(feature: dict[str, Any]) -> dict[str, Any]:
    properties = feature.get("properties") or {}
    return {
        "source_object_id": properties.get("OBJECTID"),
        "designation": properties.get("ZONGDSGN"),
        "specific_plan": properties.get("SPPLAN"),
        "historic_parcel_type": properties.get("HistoricParcelType"),
    }


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
