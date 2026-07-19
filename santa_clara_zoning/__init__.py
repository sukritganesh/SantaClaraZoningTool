"""Deterministic lookup and regulatory-data components for Santa Clara zoning."""

from .lookup import LocalR1Lookup, LocalResidentialLookup
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
from .residential_pipeline import (
    RESIDENTIAL_CONTRACT_VERSION,
    ResidentialStandardsPipeline,
)
from .residential_standards import (
    UnsupportedSelectionError,
    available_selections,
    retrieve_residential_selection,
)
from .ruleset import (
    ApprovedR1Ruleset,
    ApprovedResidentialRuleset,
    ResidentialRulesetArtifacts,
    RulesetLoadError,
)
from .standards import (
    StandardsRetrievalError,
    UnsupportedZoneError,
    retrieve_zone_standards,
)

__all__ = [
    "ApprovedR1Ruleset",
    "ApprovedResidentialRuleset",
    "CONTRACT_VERSION",
    "LocalR1Lookup",
    "LocalResidentialLookup",
    "PRESENTATION_CONTRACT_VERSION",
    "PipelineIntegrityError",
    "PresentationIntegrityError",
    "RESIDENTIAL_CONTRACT_VERSION",
    "R1StandardsPipeline",
    "ResidentialStandardsPipeline",
    "ResidentialRulesetArtifacts",
    "RulesetLoadError",
    "StandardsRetrievalError",
    "UnsupportedZoneError",
    "UnsupportedSelectionError",
    "available_selections",
    "present_integrity_error",
    "present_pipeline_result",
    "retrieve_zone_standards",
    "retrieve_residential_selection",
]
