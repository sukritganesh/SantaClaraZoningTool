"""Minimal Flask boundary for the deterministic residential presentation."""

from __future__ import annotations

from typing import Any, Optional, Protocol, Union

from flask import Flask, render_template, request

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


def create_app(pipeline: Optional[AddressAnalyzer] = None) -> Flask:
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

    app.extensions["zoning_analyzer"] = pipeline
    app.extensions["residential_summary_pipeline"] = (
        pipeline if isinstance(pipeline, ResidentialZoneSummaryPipeline) else None
    )
    # Retain the historical extension alias for injected-test and release tooling.
    app.extensions["r1_standards_pipeline"] = pipeline
    app.extensions["startup_error"] = startup_error
    app.extensions["r1_startup_error"] = startup_error

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
