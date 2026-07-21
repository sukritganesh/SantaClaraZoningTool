"""Minimal Flask boundary for the deterministic residential presentation."""

from __future__ import annotations

from typing import Any, Optional, Protocol, Union

from flask import Flask, jsonify, render_template, request

from .addressing import (
    DEFAULT_SUGGESTION_LIMIT,
    MAX_SUGGESTION_QUERY_LENGTH,
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


class AddressAnalyzer(Protocol):
    """Structural interface required by the web route."""

    def analyze_address(self, entered_address: str) -> dict[str, Any]:
        """Return one complete zoning-analysis result."""


class AddressSuggester(Protocol):
    """Structural interface for local canonical address suggestions."""

    def suggest_addresses(self, query: str) -> dict[str, Any]:
        """Return one bounded suggestion response."""


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


def create_app(
    pipeline: Optional[AddressAnalyzer] = None,
    *,
    address_suggester: Optional[AddressSuggester] = None,
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

    app.extensions["zoning_analyzer"] = pipeline
    app.extensions["address_suggester"] = address_suggester
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

    @app.get("/")
    def index() -> str:
        entered_address = request.args.get("address")
        view: Optional[dict[str, Any]] = None
        if entered_address is not None:
            if startup_error is not None:
                view = present_residential_integrity_error(startup_error)
            else:
                if pipeline is None:
                    raise RuntimeError("The zoning pipeline was not initialized")
                try:
                    result = pipeline.analyze_address(entered_address)
                    if isinstance(pipeline, ResidentialZoneSummaryPipeline):
                        view = present_residential_summary(result)
                    else:
                        view = present_pipeline_result(result)
                except KNOWN_INTEGRITY_ERRORS as error:
                    if isinstance(pipeline, ResidentialZoneSummaryPipeline):
                        view = present_residential_integrity_error(error)
                    else:
                        view = present_integrity_error(error)

        return render_template(
            "index.html",
            entered_address=entered_address or "",
            view=view,
        )

    return app


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
