"""Deterministic lookup and regulatory-data components for the prototype."""

from .lookup import LocalR1Lookup
from .pipeline import (
    CONTRACT_VERSION,
    PipelineIntegrityError,
    R1StandardsPipeline,
)
from .presentation import (
    PRESENTATION_CONTRACT_VERSION,
    PresentationIntegrityError,
    present_integrity_error,
    present_pipeline_result,
)
from .ruleset import ApprovedR1Ruleset, RulesetLoadError
from .standards import (
    StandardsRetrievalError,
    UnsupportedZoneError,
    retrieve_zone_standards,
)

__all__ = [
    "ApprovedR1Ruleset",
    "CONTRACT_VERSION",
    "LocalR1Lookup",
    "PRESENTATION_CONTRACT_VERSION",
    "PipelineIntegrityError",
    "PresentationIntegrityError",
    "R1StandardsPipeline",
    "RulesetLoadError",
    "StandardsRetrievalError",
    "UnsupportedZoneError",
    "present_integrity_error",
    "present_pipeline_result",
    "retrieve_zone_standards",
]
