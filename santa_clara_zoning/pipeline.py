"""Versioned orchestration for local address-to-R1-standards retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .lookup import LocalR1Lookup
from .ruleset import ApprovedR1Ruleset
from .standards import retrieve_zone_standards


CONTRACT_VERSION = "1.0.0"


class AddressLookup(Protocol):
    """Structural interface required from the address and spatial lookup."""

    def lookup(self, entered_address: str) -> dict[str, Any]:
        """Return one controlled Block 5 lookup outcome."""


class PipelineIntegrityError(RuntimeError):
    """Reject an internally inconsistent success instead of returning partial data."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(message)


@dataclass(frozen=True)
class R1StandardsPipeline:
    """Combine validated local GIS lookup with approved R1 rule retrieval."""

    lookup_engine: AddressLookup
    ruleset: ApprovedR1Ruleset

    @classmethod
    def from_defaults(cls) -> "R1StandardsPipeline":
        """Load canonical, validated regulatory and GIS inputs once."""

        ruleset = ApprovedR1Ruleset.load()
        lookup_engine = LocalR1Lookup.from_snapshots()
        return cls(lookup_engine=lookup_engine, ruleset=ruleset)

    def analyze_address(self, entered_address: str) -> dict[str, Any]:
        """Return a versioned combined result or preserve a controlled lookup failure."""

        lookup_result = self.lookup_engine.lookup(entered_address)
        if not isinstance(lookup_result, dict):
            raise PipelineIntegrityError(
                "invalid_lookup_result",
                "Address lookup did not return an object.",
            )

        versioned_lookup = {
            **lookup_result,
            "contract_version": CONTRACT_VERSION,
        }
        if lookup_result.get("status") != "r1_zone_found":
            return versioned_lookup

        zone = _successful_zone(lookup_result)
        standards = retrieve_zone_standards(zone, self.ruleset)
        _validate_standards_result(standards, zone, self.ruleset.version)

        versions = lookup_result.get("versions")
        if not isinstance(versions, dict):
            raise PipelineIntegrityError(
                "invalid_lookup_versions",
                "Successful address lookup omitted its source versions.",
            )

        return {
            **versioned_lookup,
            "status": "r1_standards_found",
            "reason_code": "approved_r1_standards_retrieved",
            "message": (
                "One address, parcel, and current R1 zoning feature matched; "
                "approved base-zone standards were retrieved."
            ),
            "regulatory_context": standards["regulatory_context"],
            "regulations": standards["regulations"],
            "shared_references": standards["shared_references"],
            "not_evaluated": standards["not_evaluated"],
            "disclaimer": standards["disclaimer"],
            "versions": {
                **versions,
                "ruleset": self.ruleset.version,
            },
        }


def _successful_zone(lookup_result: dict[str, Any]) -> str:
    parcel = lookup_result.get("parcel")
    zoning = lookup_result.get("zoning")
    if not isinstance(parcel, dict) or not isinstance(zoning, dict):
        raise PipelineIntegrityError(
            "invalid_lookup_success",
            "Successful address lookup omitted parcel or zoning evidence.",
        )

    parcel_zone = parcel.get("designation")
    zoning_zone = zoning.get("designation")
    if (
        not isinstance(parcel_zone, str)
        or zoning_zone != parcel_zone
        or zoning.get("parcel_attribute_agrees") is not True
    ):
        raise PipelineIntegrityError(
            "invalid_lookup_success",
            "Successful address lookup contains inconsistent zoning evidence.",
        )
    return parcel_zone


def _validate_standards_result(
    standards: dict[str, Any],
    expected_zone: str,
    expected_ruleset_version: str,
) -> None:
    if not isinstance(standards, dict):
        raise PipelineIntegrityError(
            "invalid_standards_result",
            "Regulatory retrieval did not return an object.",
        )

    required_fields = {
        "regulatory_context",
        "regulations",
        "shared_references",
        "not_evaluated",
        "disclaimer",
    }
    missing = required_fields - set(standards)
    context = standards.get("regulatory_context")
    if (
        standards.get("zone") != expected_zone
        or missing
        or not isinstance(context, dict)
        or context.get("ruleset_version") != expected_ruleset_version
    ):
        raise PipelineIntegrityError(
            "invalid_standards_result",
            "Regulatory retrieval returned incomplete or inconsistent data.",
        )
