"""Minimal Flask boundary for the deterministic residential presentation."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Optional, Protocol, Union

from flask import Flask, abort, jsonify, make_response, render_template, request, send_file

from .addressing import (
    DEFAULT_SUGGESTION_LIMIT,
    MAX_SUGGESTION_QUERY_LENGTH,
)
from .geometry import BoundingBox, geometry_bounds
from .lookup import (
    MAX_PROPERTY_MAP_ZONING_FEATURES,
    PROPERTY_MAP_CONTRACT_VERSION,
)
from .pipeline import PipelineIntegrityError, R1StandardsPipeline
from .presentation import (
    PresentationIntegrityError,
    present_integrity_error,
    present_pipeline_result,
)
from .residential_presentation import (
    present_residential_integrity_error,
    present_residential_summary,
)
from .residential_summary import (
    ResidentialZoneSummaryPipeline,
)
from .ruleset import RulesetLoadError
from .standards import StandardsRetrievalError
from .source_evidence import (
    SourceEvidenceIntegrityError,
    SourceEvidenceProvider,
    document_download_name,
)
from .zone_descriptions import (
    ZoneDescriptionIntegrityError,
    ZoneDescriptionProvider,
)


class AddressAnalyzer(Protocol):
    """Structural interface required by the web route."""

    def analyze_address(self, entered_address: str) -> dict[str, Any]:
        """Return one complete zoning-analysis result."""


class AddressSuggester(Protocol):
    """Structural interface for local canonical address suggestions."""

    def suggest_addresses(self, query: str) -> dict[str, Any]:
        """Return one bounded suggestion response."""


class PropertyMapProvider(Protocol):
    """Structural interface for local parcel and zoning map context."""

    def property_map_context(self, address: str) -> dict[str, Any]:
        """Return one bounded property-map response."""


class RegulatorySourceEvidenceProvider(Protocol):
    """Structural interface for presentation-only regulatory evidence."""

    def links_for_view(self, view: dict[str, Any]) -> dict[str, dict[str, str]]:
        """Return exact target ids for one rendered success view."""

    def get_target(self, target_id: str) -> dict[str, Any]:
        """Return one validated evidence target."""

    def get_document(self, document_id: str) -> tuple[Path, dict[str, Any]]:
        """Return one allowlisted source document."""

    def get_page_image(
        self,
        target_id: str,
        location_index: int,
    ) -> tuple[Path, dict[str, Any]]:
        """Return one allowlisted source-page image."""


class ResidentialZoneDescriptionProvider(Protocol):
    """Structural interface for reviewed presentation-only zone copy."""

    def description_for(self, zone: str) -> str:
        """Return one plain-language paragraph for an exact zone."""


KnownIntegrityError = Union[
    RulesetLoadError,
    PipelineIntegrityError,
    StandardsRetrievalError,
    PresentationIntegrityError,
]
KNOWN_INTEGRITY_ERRORS = (
    RulesetLoadError,
    PipelineIntegrityError,
    StandardsRetrievalError,
    PresentationIntegrityError,
)
PROPERTY_MAP_PROVIDER_ERRORS = (*KNOWN_INTEGRITY_ERRORS, TypeError, ValueError)
SOURCE_EVIDENCE_ERRORS = (
    SourceEvidenceIntegrityError,
    OSError,
    TypeError,
    ValueError,
)
ZONE_DESCRIPTION_ERRORS = (
    ZoneDescriptionIntegrityError,
    OSError,
    TypeError,
    ValueError,
)
_AUTO_SOURCE_EVIDENCE = object()
_AUTO_ZONE_DESCRIPTIONS = object()
DEFAULT_MAP_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
DEFAULT_MAP_ATTRIBUTION_TEXT = "© OpenStreetMap contributors"
DEFAULT_MAP_ATTRIBUTION_URL = "https://www.openstreetmap.org/copyright"
PROPERTY_MAP_OUTCOME_COPY = {
    "address_not_found": (
        "property_map_address_not_found",
        "No exact supported property map was found for this address.",
    ),
    "outside_supported_residential_snapshot": (
        "property_map_outside_supported_snapshot",
        "This address is outside the Explorer’s supported residential map snapshot.",
    ),
    "address_ambiguous": (
        "property_map_address_ambiguous",
        "Multiple address records matched, so no property map was selected.",
    ),
    "review_required": (
        "property_map_review_required",
        "The parcel and zoning geometry requires review, so no map was displayed.",
    ),
    "map_context_unavailable": (
        "property_map_context_unavailable",
        "Complete local map context could not be displayed safely.",
    ),
}


def create_app(
    pipeline: Optional[AddressAnalyzer] = None,
    *,
    address_suggester: Optional[AddressSuggester] = None,
    property_map_provider: Optional[PropertyMapProvider] = None,
    zone_description_provider: (
        Optional[ResidentialZoneDescriptionProvider] | object
    ) = _AUTO_ZONE_DESCRIPTIONS,
    source_evidence_provider: (
        Optional[RegulatorySourceEvidenceProvider] | object
    ) = _AUTO_SOURCE_EVIDENCE,
) -> Flask:
    """Create one local web app and load or accept its pipeline once."""

    app = Flask(__name__)
    startup_error: Optional[KnownIntegrityError] = None
    if pipeline is None:
        try:
            pipeline = ResidentialZoneSummaryPipeline.from_defaults()
        except RulesetLoadError as error:
            startup_error = error
        except (OSError, ValueError) as error:
            startup_error = PipelineIntegrityError(
                "runtime_data_load_error",
                f"Residential runtime data could not be loaded: {error}",
            )
    if address_suggester is None and isinstance(
        pipeline,
        ResidentialZoneSummaryPipeline,
    ):
        address_suggester = pipeline
    if property_map_provider is None and isinstance(
        pipeline,
        ResidentialZoneSummaryPipeline,
    ):
        property_map_provider = pipeline
    zone_description_startup_error: Optional[Exception] = None
    if zone_description_provider is _AUTO_ZONE_DESCRIPTIONS:
        zone_description_provider = None
        if isinstance(pipeline, ResidentialZoneSummaryPipeline):
            try:
                zone_description_provider = ZoneDescriptionProvider.from_defaults()
            except ZONE_DESCRIPTION_ERRORS as error:
                zone_description_startup_error = error
    evidence_startup_error: Optional[Exception] = None
    if source_evidence_provider is _AUTO_SOURCE_EVIDENCE:
        source_evidence_provider = None
        if isinstance(pipeline, ResidentialZoneSummaryPipeline):
            try:
                source_evidence_provider = SourceEvidenceProvider.from_defaults()
            except SOURCE_EVIDENCE_ERRORS as error:
                evidence_startup_error = error

    app.config.setdefault("MAP_TILE_URL", DEFAULT_MAP_TILE_URL)
    app.config.setdefault("MAP_ATTRIBUTION_TEXT", DEFAULT_MAP_ATTRIBUTION_TEXT)
    app.config.setdefault("MAP_ATTRIBUTION_URL", DEFAULT_MAP_ATTRIBUTION_URL)

    app.extensions["zoning_analyzer"] = pipeline
    app.extensions["address_suggester"] = address_suggester
    app.extensions["property_map_provider"] = property_map_provider
    app.extensions["zone_description_provider"] = zone_description_provider
    app.extensions["zone_description_startup_error"] = (
        zone_description_startup_error
    )
    app.extensions["source_evidence_provider"] = source_evidence_provider
    app.extensions["source_evidence_startup_error"] = evidence_startup_error
    app.extensions["residential_summary_pipeline"] = (
        pipeline if isinstance(pipeline, ResidentialZoneSummaryPipeline) else None
    )
    # Retain the historical extension alias for injected-test and release tooling.
    app.extensions["r1_standards_pipeline"] = pipeline
    app.extensions["startup_error"] = startup_error
    app.extensions["r1_startup_error"] = startup_error

    @app.get("/api/address-suggestions")
    def address_suggestions():
        query = request.args.get("q", "")
        if len(query) > MAX_SUGGESTION_QUERY_LENGTH:
            return (
                jsonify(
                    {
                        "status": "invalid_query",
                        "reason_code": "query_too_long",
                        "message": (
                            "Address suggestions accept at most 120 characters."
                        ),
                        "suggestions": [],
                    }
                ),
                400,
            )
        if address_suggester is None:
            return (
                jsonify(
                    {
                        "status": "unavailable",
                        "reason_code": "address_suggestions_unavailable",
                        "message": (
                            "Address suggestions are unavailable; enter the full "
                            "address and use the lookup button."
                        ),
                        "suggestions": [],
                    }
                ),
                503,
            )
        try:
            result = address_suggester.suggest_addresses(query)
            payload = _safe_suggestion_payload(result, query=query)
        except KNOWN_INTEGRITY_ERRORS:
            return (
                jsonify(
                    {
                        "status": "unavailable",
                        "reason_code": "address_suggestions_unavailable",
                        "message": (
                            "Address suggestions are unavailable; enter the full "
                            "address and use the lookup button."
                        ),
                        "suggestions": [],
                    }
                ),
                503,
            )
        return jsonify(payload)

    @app.get("/api/property-map")
    def property_map():
        address = request.args.get("address")
        if (
            address is None
            or not address.strip()
            or len(address) > MAX_SUGGESTION_QUERY_LENGTH
        ):
            return (
                jsonify(
                    {
                        "contract_version": PROPERTY_MAP_CONTRACT_VERSION,
                        "status": "invalid_query",
                        "reason_code": "invalid_property_map_address",
                        "message": (
                            "Property maps require a non-empty address of at most "
                            "120 characters."
                        ),
                    }
                ),
                400,
            )
        if property_map_provider is None:
            return _property_map_unavailable()
        try:
            result = property_map_provider.property_map_context(address)
            payload = _safe_property_map_payload(result, query=address)
        except PROPERTY_MAP_PROVIDER_ERRORS:
            return _property_map_unavailable()

        status_code = {
            "ok": 200,
            "address_not_found": 404,
            "outside_supported_residential_snapshot": 404,
            "address_ambiguous": 409,
            "review_required": 409,
            "map_context_unavailable": 503,
        }[payload["status"]]
        return jsonify(payload), status_code

    @app.get("/")
    def index() -> str:
        entered_address = request.args.get("address")
        view: Optional[dict[str, Any]] = None
        evidence_links: dict[str, dict[str, str]] = {}
        if entered_address is not None:
            if startup_error is not None:
                view = present_residential_integrity_error(startup_error)
            else:
                if pipeline is None:
                    raise RuntimeError("The zoning pipeline was not initialized")
                try:
                    result = pipeline.analyze_address(entered_address)
                    if isinstance(pipeline, ResidentialZoneSummaryPipeline):
                        view = present_residential_summary(
                            result,
                            zone_description_provider=zone_description_provider,
                        )
                    else:
                        view = present_pipeline_result(result)
                except KNOWN_INTEGRITY_ERRORS as error:
                    if isinstance(pipeline, ResidentialZoneSummaryPipeline):
                        view = present_residential_integrity_error(error)
                    else:
                        view = present_integrity_error(error)

        if (
            view is not None
            and view.get("kind") == "success"
            and source_evidence_provider is not None
        ):
            try:
                evidence_links = source_evidence_provider.links_for_view(view)
            except SOURCE_EVIDENCE_ERRORS:
                evidence_links = {}

        return render_template(
            "index.html",
            entered_address=entered_address or "",
            evidence_links=evidence_links,
            map_attribution_text=app.config["MAP_ATTRIBUTION_TEXT"],
            map_attribution_url=app.config["MAP_ATTRIBUTION_URL"],
            map_tile_url=app.config["MAP_TILE_URL"],
            property_map_enabled=property_map_provider is not None,
            view=view,
        )

    @app.get("/source-evidence/<target_id>")
    def source_evidence(target_id: str):
        if source_evidence_provider is None:
            return _source_evidence_unavailable()
        try:
            target = source_evidence_provider.get_target(target_id)
        except KeyError:
            abort(404)
        except SOURCE_EVIDENCE_ERRORS:
            return _source_evidence_unavailable()
        response = make_response(
            render_template("source_evidence.html", target=target)
        )
        return _harden_evidence_response(response)

    @app.get("/source-evidence/<target_id>/pages/<int:location_index>.png")
    def source_evidence_page(target_id: str, location_index: int):
        if source_evidence_provider is None:
            return _source_evidence_unavailable()
        try:
            path, image = source_evidence_provider.get_page_image(
                target_id,
                location_index,
            )
        except KeyError:
            abort(404)
        except SOURCE_EVIDENCE_ERRORS:
            return _source_evidence_unavailable()
        response = send_file(
            path,
            mimetype="image/png",
            conditional=True,
            etag=image["sha256"],
            max_age=31536000,
        )
        return _harden_evidence_response(response)

    @app.get("/source-documents/<document_id>")
    def source_document(document_id: str):
        if source_evidence_provider is None:
            return _source_evidence_unavailable()
        try:
            path, document = source_evidence_provider.get_document(document_id)
        except KeyError:
            abort(404)
        except SOURCE_EVIDENCE_ERRORS:
            return _source_evidence_unavailable()
        response = send_file(
            path,
            mimetype=document["media_type"],
            as_attachment=False,
            download_name=document_download_name(document),
            conditional=True,
            etag=document["sha256"],
            max_age=31536000,
        )
        return _harden_evidence_response(response)

    return app


def _source_evidence_unavailable():
    response = make_response(
        render_template(
            "source_evidence_unavailable.html",
            message=(
                "Exact source evidence is temporarily unavailable. The zoning "
                "result and its source receipt remain unchanged."
            ),
        ),
        503,
    )
    return _harden_evidence_response(response)


def _harden_evidence_response(response):
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; object-src 'none'; base-uri 'none'; "
        "frame-ancestors 'self'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def _safe_suggestion_payload(
    result: Any,
    *,
    query: str,
) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise PipelineIntegrityError(
            "invalid_address_suggestions",
            "Address suggestion provider did not return an object.",
        )
    status = result.get("status")
    suggestions = result.get("suggestions")
    total_matches = result.get("total_matches")
    truncated = result.get("truncated")
    if (
        status not in {"ok", "query_too_short"}
        or result.get("query") != query
        or not isinstance(result.get("normalized_query"), str)
        or not isinstance(result.get("address_snapshot"), str)
        or not result["address_snapshot"]
        or not isinstance(suggestions, list)
        or len(suggestions) > DEFAULT_SUGGESTION_LIMIT
        or not isinstance(total_matches, int)
        or isinstance(total_matches, bool)
        or total_matches < 0
        or not isinstance(truncated, bool)
    ):
        raise PipelineIntegrityError(
            "invalid_address_suggestions",
            "Address suggestion provider returned an invalid envelope.",
        )

    safe_suggestions: list[dict[str, Any]] = []
    for suggestion in suggestions:
        if not isinstance(suggestion, dict):
            raise PipelineIntegrityError(
                "invalid_address_suggestions",
                "Address suggestion provider returned an invalid choice.",
            )
        value = suggestion.get("value")
        display_address = suggestion.get("display_address")
        secondary_text = suggestion.get("secondary_text")
        source_record_count = suggestion.get("source_record_count")
        if (
            not isinstance(value, str)
            or not value
            or not isinstance(display_address, str)
            or not display_address
            or not isinstance(secondary_text, str)
            or not secondary_text
            or not isinstance(source_record_count, int)
            or isinstance(source_record_count, bool)
            or source_record_count < 1
        ):
            raise PipelineIntegrityError(
                "invalid_address_suggestions",
                "Address suggestion provider returned incomplete choice data.",
            )
        safe_suggestions.append(
            {
                "value": value,
                "display_address": display_address,
                "secondary_text": secondary_text,
                "source_record_count": source_record_count,
            }
        )

    if status == "query_too_short":
        if safe_suggestions or total_matches != 0 or truncated:
            raise PipelineIntegrityError(
                "invalid_address_suggestions",
                "A short suggestion query returned address choices.",
            )
    elif (
        total_matches < len(safe_suggestions)
        or truncated != (total_matches > len(safe_suggestions))
    ):
        raise PipelineIntegrityError(
            "invalid_address_suggestions",
            "Address suggestion counts are inconsistent.",
        )

    return {
        "status": status,
        "query": query,
        "normalized_query": result["normalized_query"],
        "address_snapshot": result["address_snapshot"],
        "total_matches": total_matches,
        "truncated": truncated,
        "suggestions": safe_suggestions,
    }


def _property_map_unavailable():
    return (
        jsonify(
            {
                "contract_version": PROPERTY_MAP_CONTRACT_VERSION,
                "status": "unavailable",
                "reason_code": "property_map_unavailable",
                "message": (
                    "Parcel and zoning map context is unavailable; the zoning "
                    "result remains usable."
                ),
            }
        ),
        503,
    )


def _safe_property_map_payload(
    result: Any,
    *,
    query: str,
) -> dict[str, Any]:
    if (
        not isinstance(result, dict)
        or result.get("contract_version") != PROPERTY_MAP_CONTRACT_VERSION
        or result.get("query") != query
    ):
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map provider returned an invalid envelope.",
        )
    status = result.get("status")
    allowed_statuses = {
        "ok",
        "address_not_found",
        "outside_supported_residential_snapshot",
        "address_ambiguous",
        "review_required",
        "map_context_unavailable",
    }
    if status not in allowed_statuses:
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map provider returned an unsupported status.",
        )

    versions = _safe_property_map_versions(result.get("versions"))
    if status != "ok":
        reason_code = result.get("reason_code")
        message = result.get("message")
        if (
            not isinstance(reason_code, str)
            or not reason_code
            or not isinstance(message, str)
            or not message
        ):
            raise PipelineIntegrityError(
                "invalid_property_map",
                "Unavailable map context omitted its controlled explanation.",
            )
        safe_reason, safe_message = PROPERTY_MAP_OUTCOME_COPY[status]
        return {
            "contract_version": PROPERTY_MAP_CONTRACT_VERSION,
            "status": status,
            "reason_code": safe_reason,
            "message": safe_message,
            "query": query,
            "versions": versions,
        }

    property_record = result.get("property")
    supported_zones = result.get("supported_zones")
    if (
        not isinstance(property_record, dict)
        or not isinstance(supported_zones, list)
        or not supported_zones
        or len(supported_zones) != len(set(supported_zones))
        or any(not isinstance(zone, str) or not zone for zone in supported_zones)
    ):
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map provider returned an invalid supported-zone scope.",
        )
    display_address = property_record.get("display_address")
    apn = property_record.get("apn")
    selected_zone = property_record.get("zone")
    if (
        not isinstance(display_address, str)
        or not display_address
        or not isinstance(apn, str)
        or not apn
        or selected_zone not in supported_zones
    ):
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map provider returned incomplete property identity.",
        )

    selected_bounds = _safe_bounds(result.get("selected_bounds"))
    context_bounds = _safe_bounds(result.get("context_bounds"))
    if not _bounds_contains(context_bounds, selected_bounds):
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map context does not contain the selected parcel bounds.",
        )

    selected_parcel = _safe_map_feature(
        result.get("selected_parcel"),
        allowed_properties={"apn": apn, "zone": selected_zone},
    )
    parcel_bounds = geometry_bounds(selected_parcel["geometry"])
    if not _bounds_equal(selected_bounds, parcel_bounds):
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Selected parcel geometry does not match its declared bounds.",
        )

    zoning_collection = result.get("supported_zoning")
    feature_count = result.get("zoning_feature_count")
    if (
        not isinstance(zoning_collection, dict)
        or zoning_collection.get("type") != "FeatureCollection"
        or not isinstance(zoning_collection.get("features"), list)
        or not isinstance(feature_count, int)
        or isinstance(feature_count, bool)
        or feature_count != len(zoning_collection["features"])
        or feature_count < 1
        or feature_count > MAX_PROPERTY_MAP_ZONING_FEATURES
    ):
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map provider returned an invalid zoning collection.",
        )

    safe_zoning = []
    selected_zone_present = False
    for feature in zoning_collection["features"]:
        if not isinstance(feature, dict):
            raise PipelineIntegrityError(
                "invalid_property_map",
                "Property map provider returned an invalid zoning feature.",
            )
        properties = feature.get("properties")
        zone = properties.get("zone") if isinstance(properties, dict) else None
        if zone not in supported_zones:
            raise PipelineIntegrityError(
                "invalid_property_map",
                "Property map provider exposed an unsupported zoning feature.",
            )
        safe_feature = _safe_map_feature(
            feature,
            allowed_properties={"zone": zone},
        )
        if not geometry_bounds(safe_feature["geometry"]).intersects(context_bounds):
            raise PipelineIntegrityError(
                "invalid_property_map",
                "Property map provider returned zoning outside its context.",
            )
        selected_zone_present = selected_zone_present or zone == selected_zone
        safe_zoning.append(safe_feature)
    if not selected_zone_present:
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map context omitted the selected zoning designation.",
        )

    return {
        "contract_version": PROPERTY_MAP_CONTRACT_VERSION,
        "status": "ok",
        "query": query,
        "property": {
            "display_address": display_address,
            "apn": apn,
            "zone": selected_zone,
        },
        "versions": versions,
        "selected_bounds": _bounds_dict(selected_bounds),
        "context_bounds": _bounds_dict(context_bounds),
        "selected_parcel": selected_parcel,
        "supported_zoning": {
            "type": "FeatureCollection",
            "features": safe_zoning,
        },
        "zoning_feature_count": feature_count,
        "supported_zones": list(supported_zones),
    }


def _safe_property_map_versions(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map provider omitted snapshot versions.",
        )
    safe = {}
    for key in ("address_snapshot", "residential_gis_snapshot"):
        version = value.get(key)
        if not isinstance(version, str) or not version:
            raise PipelineIntegrityError(
                "invalid_property_map",
                f"Property map provider omitted {key}.",
            )
        safe[key] = version
    return safe


def _safe_bounds(value: Any) -> BoundingBox:
    if not isinstance(value, dict):
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map provider returned invalid bounds.",
        )
    values = [value.get(key) for key in ("west", "south", "east", "north")]
    if any(
        not isinstance(number, (int, float))
        or isinstance(number, bool)
        or not math.isfinite(number)
        for number in values
    ):
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map bounds contain invalid coordinates.",
        )
    west, south, east, north = (float(number) for number in values)
    if (
        west > east
        or south > north
        or not -180 <= west <= 180
        or not -180 <= east <= 180
        or not -90 <= south <= 90
        or not -90 <= north <= 90
    ):
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map bounds are invalid.",
        )
    return BoundingBox(west, south, east, north)


def _safe_map_feature(
    value: Any,
    *,
    allowed_properties: dict[str, str],
) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("type") != "Feature":
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map provider returned an invalid GeoJSON feature.",
        )
    properties = value.get("properties")
    if not isinstance(properties, dict) or any(
        properties.get(key) != expected
        for key, expected in allowed_properties.items()
    ):
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map GeoJSON properties are inconsistent.",
        )
    return {
        "type": "Feature",
        "properties": dict(allowed_properties),
        "geometry": _safe_polygon_geometry(value.get("geometry")),
    }


def _safe_polygon_geometry(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map geometry is not an object.",
        )
    geometry_type = value.get("type")
    coordinates = value.get("coordinates")
    if geometry_type == "Polygon":
        safe_coordinates = _safe_polygon_coordinates(coordinates)
    elif geometry_type == "MultiPolygon":
        if not isinstance(coordinates, list) or not coordinates:
            raise PipelineIntegrityError(
                "invalid_property_map",
                "Property map multipolygon is empty.",
            )
        safe_coordinates = [
            _safe_polygon_coordinates(polygon) for polygon in coordinates
        ]
    else:
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map geometry is not a polygon or multipolygon.",
        )
    return {"type": geometry_type, "coordinates": safe_coordinates}


def _safe_polygon_coordinates(value: Any) -> list[list[list[float]]]:
    if not isinstance(value, list) or not value:
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map polygon has no rings.",
        )
    return [_safe_ring(ring) for ring in value]


def _safe_ring(value: Any) -> list[list[float]]:
    if not isinstance(value, list) or len(value) < 4:
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map polygon ring is incomplete.",
        )
    ring = [_safe_position(position) for position in value]
    if ring[0] != ring[-1]:
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map polygon ring is not closed.",
        )
    return ring


def _safe_position(value: Any) -> list[float]:
    if not isinstance(value, list) or len(value) < 2:
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map polygon position is invalid.",
        )
    longitude, latitude = value[:2]
    if (
        not isinstance(longitude, (int, float))
        or isinstance(longitude, bool)
        or not math.isfinite(longitude)
        or not isinstance(latitude, (int, float))
        or isinstance(latitude, bool)
        or not math.isfinite(latitude)
        or not -180 <= longitude <= 180
        or not -90 <= latitude <= 90
    ):
        raise PipelineIntegrityError(
            "invalid_property_map",
            "Property map polygon position is outside WGS84 bounds.",
        )
    return [float(longitude), float(latitude)]


def _bounds_contains(container: BoundingBox, child: BoundingBox) -> bool:
    return (
        container.xmin <= child.xmin
        and container.ymin <= child.ymin
        and container.xmax >= child.xmax
        and container.ymax >= child.ymax
    )


def _bounds_equal(left: BoundingBox, right: BoundingBox) -> bool:
    return all(
        math.isclose(first, second, rel_tol=0.0, abs_tol=1e-12)
        for first, second in (
            (left.xmin, right.xmin),
            (left.ymin, right.ymin),
            (left.xmax, right.xmax),
            (left.ymax, right.ymax),
        )
    )


def _bounds_dict(bounds: BoundingBox) -> dict[str, float]:
    return {
        "west": bounds.xmin,
        "south": bounds.ymin,
        "east": bounds.xmax,
        "north": bounds.ymax,
    }
