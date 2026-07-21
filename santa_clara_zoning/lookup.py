"""Local address-to-parcel-to-zone lookup over immutable GIS snapshots."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .addressing import AddressIndex, normalize_address
from .geometry import Point, SpatialIndex
from .ruleset import ApprovedResidentialRuleset


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ADDRESS_SNAPSHOT = (
    REPO_ROOT / "data/raw/2026-07-16/santa_clara_address_points"
)
DEFAULT_R1_SNAPSHOT = REPO_ROOT / "data/raw/2026-07-14/santa_clara_r1_gis"
DEFAULT_RESIDENTIAL_SNAPSHOT = (
    REPO_ROOT / "data/raw/2026-07-18/santa_clara_residential_gis"
)
SUPPORTED_ZONES = {"R1-6L", "R1-8L"}
EXCLUDED_RESIDENTIAL_DESIGNATIONS = ("R1-6LHT", "R2-7L", "R2HT")
RESIDENTIAL_LAYER_FILES = {
    "parcels": "parcels_residential.geojson",
    "current_zoning": "current_zoning_residential.geojson",
}


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


class LocalResidentialLookup:
    """Resolve exact addresses against the approved residential GIS scope."""

    def __init__(
        self,
        *,
        address_index: AddressIndex,
        parcel_index: SpatialIndex,
        zoning_index: SpatialIndex,
        supported_zones: tuple[str, ...],
        designation_counts: Mapping[str, int],
        excluded_designation_counts: Mapping[str, int],
        versions: Mapping[str, str],
        sources: Mapping[str, str],
    ) -> None:
        if not supported_zones or len(set(supported_zones)) != len(supported_zones):
            raise ValueError("Residential supported zones must be nonempty and unique")
        self.address_index = address_index
        self.parcel_index = parcel_index
        self.zoning_index = zoning_index
        self._supported_zones = supported_zones
        self._supported_zone_set = frozenset(supported_zones)
        self._designation_counts = MappingProxyType(dict(designation_counts))
        self._excluded_designation_counts = MappingProxyType(
            dict(excluded_designation_counts)
        )
        self._versions = MappingProxyType(dict(versions))
        self._sources = MappingProxyType(dict(sources))

    @classmethod
    def from_snapshots(
        cls,
        *,
        ruleset: ApprovedResidentialRuleset,
        address_snapshot: Path = DEFAULT_ADDRESS_SNAPSHOT,
        residential_snapshot: Path = DEFAULT_RESIDENTIAL_SNAPSHOT,
        verify_checksums: bool = True,
    ) -> "LocalResidentialLookup":
        """Validate canonical manifests and load their exact filtered layers."""

        if not isinstance(ruleset, ApprovedResidentialRuleset):
            raise TypeError("ruleset must be an ApprovedResidentialRuleset")
        supported_zones = ruleset.supported_zones
        address_manifest = _load_json(address_snapshot / "manifest.json")
        residential_manifest = _load_json(
            residential_snapshot / "manifest.json"
        )
        address_layer = _validated_address_layer(address_manifest)
        parcel_layer, zoning_layer, designation_counts = (
            _validated_residential_manifest(
                residential_manifest,
                supported_zones=supported_zones,
            )
        )

        address_features = _load_layer(
            address_snapshot,
            address_layer,
            verify_checksum=verify_checksums,
        )
        parcel_features = _load_layer(
            residential_snapshot,
            parcel_layer,
            verify_checksum=verify_checksums,
        )
        zoning_features = _load_layer(
            residential_snapshot,
            zoning_layer,
            verify_checksum=verify_checksums,
        )
        parcel_counts = _validate_residential_features(
            parcel_features,
            layer_name="residential parcels",
            supported_zones=frozenset(supported_zones),
        )
        zoning_counts = _validate_residential_features(
            zoning_features,
            layer_name="residential current zoning",
            supported_zones=frozenset(supported_zones),
        )
        if parcel_counts != designation_counts:
            raise ValueError(
                "Residential parcel feature counts do not match the manifest"
            )
        if zoning_counts != designation_counts:
            raise ValueError(
                "Residential zoning feature counts do not match the manifest"
            )

        excluded_counts = residential_manifest["cross_layer_validation"][
            "excluded_preflight_counts"
        ]
        return cls(
            address_index=AddressIndex(address_features),
            parcel_index=SpatialIndex(
                parcel_features,
                layer_name="residential parcels",
            ),
            zoning_index=SpatialIndex(
                zoning_features,
                layer_name="residential current zoning",
            ),
            supported_zones=supported_zones,
            designation_counts=designation_counts,
            excluded_designation_counts=excluded_counts,
            versions={
                "address_snapshot": str(address_manifest["snapshot_date"]),
                "residential_gis_snapshot": str(
                    residential_manifest["snapshot_date"]
                ),
            },
            sources={
                "address_layer": str(address_layer["source_layer_url"]),
                "parcel_layer": str(parcel_layer["source_layer_url"]),
                "zoning_layer": str(zoning_layer["source_layer_url"]),
            },
        )

    @property
    def supported_zones(self) -> tuple[str, ...]:
        return self._supported_zones

    @property
    def designation_counts(self) -> dict[str, int]:
        return dict(self._designation_counts)

    @property
    def excluded_designation_counts(self) -> dict[str, int]:
        return dict(self._excluded_designation_counts)

    @property
    def versions(self) -> dict[str, str]:
        return dict(self._versions)

    @property
    def sources(self) -> dict[str, str]:
        return dict(self._sources)

    def lookup(self, entered_address: str) -> dict[str, Any]:
        """Return one controlled exact residential lookup outcome."""

        normalized = normalize_address(entered_address)
        result: dict[str, Any] = {
            "query": {
                "entered_address": entered_address,
                "normalized_address": normalized,
            },
            "versions": self.versions,
            "sources": self.sources,
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
                "message": (
                    "No exact normalized match was found in the local address "
                    "snapshot."
                ),
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
        return _residential_spatial_result(
            base=result,
            address=address,
            parcel_matches=self.parcel_index.match(point),
            zoning_matches=self.zoning_index.match(point),
            supported_zones=self._supported_zone_set,
        )

    def suggest_addresses(self, query: str) -> dict[str, Any]:
        """Return local citywide suggestions with their snapshot identity."""

        result = self.address_index.suggest(query)
        return {
            **result,
            "address_snapshot": self._versions["address_snapshot"],
        }


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


def _residential_spatial_result(
    *,
    base: dict[str, Any],
    address: dict[str, Any],
    parcel_matches: tuple[dict[str, Any], ...],
    zoning_matches: tuple[dict[str, Any], ...],
    supported_zones: frozenset[str],
) -> dict[str, Any]:
    result = {
        **base,
        "address": _address_summary(address),
        "spatial_match_counts": {
            "residential_parcels": len(parcel_matches),
            "residential_zoning_features": len(zoning_matches),
        },
    }
    if not parcel_matches and not zoning_matches:
        return {
            **result,
            "status": "outside_supported_residential_snapshot",
            "reason_code": "no_residential_parcel_or_zoning_match",
            "message": (
                "The address was found, but its point does not intersect the "
                "exact filtered residential snapshot. Its zoning is not "
                "determined here."
            ),
        }

    if len(parcel_matches) != 1 or len(zoning_matches) != 1:
        return {
            **result,
            "status": "review_required",
            "reason_code": "spatial_match_count_unexpected",
            "message": (
                "The residential parcel and zoning layers did not produce one "
                "match each."
            ),
            "parcel_candidates": [
                _parcel_summary(value) for value in parcel_matches
            ],
            "zoning_candidates": [
                _zoning_summary(value) for value in zoning_matches
            ],
        }

    parcel = _parcel_summary(parcel_matches[0])
    zoning = _zoning_summary(zoning_matches[0])
    parcel_zone = parcel["designation"]
    zoning_zone = zoning["designation"]
    if parcel_zone not in supported_zones or zoning_zone not in supported_zones:
        return {
            **result,
            "status": "review_required",
            "reason_code": "unexpected_zone_in_residential_snapshot",
            "message": (
                "A filtered source feature contains a designation outside the "
                "approved residential ruleset."
            ),
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
        "status": "residential_zone_found",
        "reason_code": "supported_residential_match",
        "message": (
            "One address, parcel, and current residential zoning feature "
            "matched."
        ),
        "parcel": parcel,
        "zoning": zoning,
    }


def _validated_address_layer(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("status") != "complete":
        raise ValueError("Address snapshot manifest is not complete")
    if not _is_nonempty_string(manifest.get("snapshot_date")):
        raise ValueError("Address snapshot manifest has no snapshot date")
    layer = manifest.get("layer")
    if not isinstance(layer, dict):
        raise ValueError("Address snapshot manifest has an unsupported structure")
    if layer.get("validation") != "complete":
        raise ValueError("Address snapshot layer validation is not complete")
    if layer.get("output_file") != "address_points.geojson":
        raise ValueError("Address snapshot output file is not canonical")
    if not _is_nonempty_string(layer.get("source_layer_url")):
        raise ValueError("Address snapshot source layer URL is missing")
    _validate_complete_layer_counts(layer, label="Address snapshot")
    return layer


def _validated_residential_manifest(
    manifest: dict[str, Any],
    *,
    supported_zones: tuple[str, ...],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    if manifest.get("status") != "complete":
        raise ValueError("Residential snapshot manifest is not complete")
    if manifest.get("manifest_schema_version") != "1.0.0":
        raise ValueError("Residential snapshot manifest schema is unsupported")
    if not _is_nonempty_string(manifest.get("snapshot_date")):
        raise ValueError("Residential snapshot manifest has no snapshot date")
    if tuple(manifest.get("requested_designations", ())) != supported_zones:
        raise ValueError(
            "Residential manifest designations do not exactly match the "
            "approved ruleset"
        )
    if tuple(manifest.get("excluded_preflight_designations", ())) != (
        EXCLUDED_RESIDENTIAL_DESIGNATIONS
    ):
        raise ValueError(
            "Residential manifest excluded designations are not the exact "
            "approved preflight set"
        )

    expected_filter = "ZONGDSGN IN (" + ",".join(
        f"'{zone}'" for zone in supported_zones
    ) + ")"
    if manifest.get("filter") != expected_filter:
        raise ValueError("Residential manifest filter does not match its zones")

    layers = manifest.get("layers")
    if not isinstance(layers, list) or len(layers) != 2:
        raise ValueError(
            "Residential manifest must contain exactly two source layers"
        )
    if any(not isinstance(layer, dict) for layer in layers):
        raise ValueError("Residential manifest layer metadata is invalid")
    layers_by_slug = {layer.get("slug"): layer for layer in layers}
    if set(layers_by_slug) != set(RESIDENTIAL_LAYER_FILES):
        raise ValueError(
            "Residential manifest must contain exact parcel and zoning layers"
        )

    expected_zones = frozenset(supported_zones)
    layer_counts: dict[str, dict[str, int]] = {}
    excluded_counts: dict[str, dict[str, int]] = {}
    for slug, output_file in RESIDENTIAL_LAYER_FILES.items():
        layer = layers_by_slug[slug]
        if layer.get("validation") != "complete":
            raise ValueError(f"Residential {slug} validation is not complete")
        if layer.get("output_file") != output_file:
            raise ValueError(f"Residential {slug} output file is not canonical")
        if not _is_nonempty_string(layer.get("source_layer_url")):
            raise ValueError(f"Residential {slug} source layer URL is missing")
        if layer.get("where") != expected_filter:
            raise ValueError(f"Residential {slug} filter does not match")
        _validate_complete_layer_counts(layer, label=f"Residential {slug}")
        requested_counts = _validated_count_map(
            layer.get("requested_designation_counts"),
            expected_keys=expected_zones,
            label=f"Residential {slug} requested counts",
        )
        downloaded_counts = _validated_count_map(
            layer.get("downloaded_zone_counts"),
            expected_keys=expected_zones,
            label=f"Residential {slug} downloaded counts",
        )
        if requested_counts != downloaded_counts:
            raise ValueError(
                f"Residential {slug} requested and downloaded counts differ"
            )
        if sum(requested_counts.values()) != layer["downloaded_feature_count"]:
            raise ValueError(
                f"Residential {slug} designation counts do not total the "
                "feature count"
            )
        positive_zones = frozenset(
            zone for zone, count in requested_counts.items() if count > 0
        )
        observed = layer.get("observed_designations")
        if (
            not isinstance(observed, list)
            or any(not isinstance(zone, str) for zone in observed)
            or len(observed) != len(set(observed))
            or frozenset(observed) != positive_zones
        ):
            raise ValueError(
                f"Residential {slug} observed designations do not match "
                "positive counts"
            )
        layer_counts[slug] = requested_counts
        excluded_counts[slug] = _validated_count_map(
            layer.get("excluded_designation_preflight_counts"),
            expected_keys=frozenset(EXCLUDED_RESIDENTIAL_DESIGNATIONS),
            label=f"Residential {slug} excluded counts",
        )

    if layer_counts["parcels"] != layer_counts["current_zoning"]:
        raise ValueError("Residential parcel and zoning designation counts differ")
    designation_counts = layer_counts["parcels"]
    if designation_counts.get("R5") != 0 or designation_counts.get("R6") != 0:
        raise ValueError("Residential R5 and R6 counts must be explicit zeroes")
    if frozenset(
        zone for zone, count in designation_counts.items() if count > 0
    ) != expected_zones - {"R5", "R6"}:
        raise ValueError(
            "Residential positive-count designations do not match the live scope"
        )
    if excluded_counts["parcels"] != excluded_counts["current_zoning"]:
        raise ValueError(
            "Residential parcel and zoning excluded-designation counts differ"
        )
    if any(count <= 0 for count in excluded_counts["parcels"].values()):
        raise ValueError(
            "Residential excluded-designation preflights must remain explicit"
        )

    cross_layer = manifest.get("cross_layer_validation")
    if not isinstance(cross_layer, dict):
        raise ValueError("Residential cross-layer validation is missing")
    if cross_layer.get("requested_zone_counts_agree") is not True:
        raise ValueError("Residential requested-zone agreement is not complete")
    if cross_layer.get("excluded_preflight_counts_agree") is not True:
        raise ValueError("Residential excluded-zone agreement is not complete")
    if cross_layer.get("requested_zone_counts") != designation_counts:
        raise ValueError("Residential cross-layer zone counts do not match")
    if (
        cross_layer.get("excluded_preflight_counts")
        != excluded_counts["parcels"]
    ):
        raise ValueError("Residential cross-layer excluded counts do not match")
    return (
        layers_by_slug["parcels"],
        layers_by_slug["current_zoning"],
        designation_counts,
    )


def _validate_complete_layer_counts(
    layer: dict[str, Any],
    *,
    label: str,
) -> None:
    counts = (
        layer.get("source_object_id_count"),
        layer.get("downloaded_feature_count"),
        layer.get("unique_downloaded_object_id_count"),
    )
    if any(not _is_nonnegative_int(value) for value in counts):
        raise ValueError(f"{label} has invalid completeness counts")
    if len(set(counts)) != 1:
        raise ValueError(f"{label} completeness counts disagree")


def _validated_count_map(
    value: Any,
    *,
    expected_keys: frozenset[str],
    label: str,
) -> dict[str, int]:
    if not isinstance(value, dict) or frozenset(value) != expected_keys:
        raise ValueError(f"{label} do not contain the exact designations")
    if any(not _is_nonnegative_int(count) for count in value.values()):
        raise ValueError(f"{label} contain an invalid count")
    return dict(value)


def _validate_residential_features(
    features: list[dict[str, Any]],
    *,
    layer_name: str,
    supported_zones: frozenset[str],
) -> dict[str, int]:
    counts = Counter({zone: 0 for zone in supported_zones})
    object_ids: set[int] = set()
    for position, feature in enumerate(features):
        properties = feature.get("properties") if isinstance(feature, dict) else None
        if not isinstance(properties, dict):
            raise ValueError(f"{layer_name} feature {position} has invalid properties")
        object_id = properties.get("OBJECTID")
        if (
            not isinstance(object_id, int)
            or isinstance(object_id, bool)
            or object_id in object_ids
        ):
            raise ValueError(
                f"{layer_name} feature {position} has an invalid or duplicate "
                "OBJECTID"
            )
        object_ids.add(object_id)
        designation = properties.get("ZONGDSGN")
        if not isinstance(designation, str) or designation not in supported_zones:
            raise ValueError(
                f"{layer_name} feature {position} has an unsupported exact "
                "designation"
            )
        counts[designation] += 1
    return {zone: counts[zone] for zone in supported_zones}


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


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
