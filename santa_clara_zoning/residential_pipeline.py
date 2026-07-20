"""Contract 2.1 orchestration for residential lookup and exact selection."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Optional

from .lookup import LocalResidentialLookup
from .pipeline import AddressLookup, PipelineIntegrityError
from .residential_standards import (
    RESIDENTIAL_PROFILE_CAPABILITIES,
    available_selections,
    retrieve_residential_selection,
)
from .ruleset import ApprovedResidentialRuleset


RESIDENTIAL_CONTRACT_VERSION = "2.1.0"
LOOKUP_REASON_BY_STATUS = {
    "outside_supported_residential_snapshot": (
        "zone_outside_exact_target_snapshot"
    ),
    "address_not_found": "no_matching_address",
    "address_ambiguous": "multiple_address_matches",
    "review_required": "spatial_or_regulatory_review_required",
}


@dataclass(frozen=True)
class ResidentialStandardsPipeline:
    """Combine approved residential data with exact local GIS resolution."""

    lookup_engine: AddressLookup
    ruleset: ApprovedResidentialRuleset

    def __post_init__(self) -> None:
        if not isinstance(self.ruleset, ApprovedResidentialRuleset):
            raise TypeError("ruleset must be an ApprovedResidentialRuleset")

    @classmethod
    def from_defaults(cls) -> "ResidentialStandardsPipeline":
        """Load the approved ruleset once, then bind its exact GIS scope."""

        ruleset = ApprovedResidentialRuleset.load()
        lookup_engine = LocalResidentialLookup.from_snapshots(ruleset=ruleset)
        return cls(lookup_engine=lookup_engine, ruleset=ruleset)

    def analyze_address(
        self,
        entered_address: str,
        selection_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Return one complete contract result or raise on invalid identity."""

        if not isinstance(entered_address, str):
            raise PipelineIntegrityError(
                "invalid_query",
                "Residential analysis requires a string address.",
            )
        lookup_result = self.lookup_engine.lookup(entered_address)
        if not isinstance(lookup_result, dict):
            raise PipelineIntegrityError(
                "invalid_lookup_result",
                "Residential lookup did not return an object.",
            )
        result = _neutral_result(
            entered_address,
            lookup_result,
            self.ruleset,
        )
        lookup_status = lookup_result.get("status")
        if lookup_status != "residential_zone_found":
            return _controlled_lookup_result(
                result,
                lookup_result,
                lookup_status,
            )

        property_record = _resolved_property(lookup_result)
        zone_code = property_record["zone"]
        selections = available_selections(zone_code, self.ruleset)
        result["property"] = property_record
        result["available_selections"] = selections
        if selection_id is None:
            result["status"] = "residential_zone_found"
            result["reason_code"] = "selection_required"
            return result

        retrieval = retrieve_residential_selection(
            zone_code,
            selection_id,
            self.ruleset,
        )
        _validate_retrieval_result(
            retrieval,
            expected_zone=zone_code,
            expected_selection_id=selection_id,
            expected_selections=selections,
            expected_disclaimer=result["disclaimer"],
        )
        for field in (
            "status",
            "reason_code",
            "available_selections",
            "requested_selection_id",
            "selection",
            "use_permission",
            "regulations",
            "not_evaluated_topics",
            "conflicts",
            "sources",
        ):
            result[field] = copy.deepcopy(retrieval[field])
        return result


def _neutral_result(
    entered_address: str,
    lookup_result: dict[str, Any],
    ruleset: ApprovedResidentialRuleset,
) -> dict[str, Any]:
    versions = lookup_result.get("versions")
    if not isinstance(versions, dict):
        raise PipelineIntegrityError(
            "invalid_lookup_versions",
            "Residential lookup omitted source versions.",
        )
    selected_versions: dict[str, str] = {}
    for key in ("address_snapshot", "residential_gis_snapshot"):
        value = versions.get(key)
        if not isinstance(value, str) or not value:
            raise PipelineIntegrityError(
                "invalid_lookup_versions",
                f"Residential lookup has no valid {key} version.",
            )
        selected_versions[key] = value
    disclaimer = ruleset.disclaimer
    if not isinstance(disclaimer, str) or not disclaimer:
        raise PipelineIntegrityError(
            "invalid_ruleset_disclaimer",
            "Approved residential ruleset has no disclaimer.",
        )
    return {
        "contract_version": RESIDENTIAL_CONTRACT_VERSION,
        "status": "review_required",
        "reason_code": "spatial_or_regulatory_review_required",
        "query": {"address": entered_address},
        "versions": {
            **selected_versions,
            "ruleset": ruleset.version,
            "ruleset_schema": ruleset.schema_version,
            "result_contract": RESIDENTIAL_CONTRACT_VERSION,
        },
        "property": None,
        "available_selections": [],
        "requested_selection_id": None,
        "selection": None,
        "use_permission": None,
        "regulations": None,
        "not_evaluated_topics": {},
        "conflicts": {},
        "sources": {
            "source_documents": {},
            "citations": {},
            "exception_families": {},
        },
        "disclaimer": disclaimer,
    }


def _controlled_lookup_result(
    result: dict[str, Any],
    lookup_result: dict[str, Any],
    lookup_status: Any,
) -> dict[str, Any]:
    reason_code = LOOKUP_REASON_BY_STATUS.get(lookup_status)
    if reason_code is None:
        raise PipelineIntegrityError(
            "invalid_lookup_status",
            f"Residential lookup returned unsupported status {lookup_status!r}.",
        )
    result["status"] = lookup_status
    result["reason_code"] = reason_code
    if lookup_status == "outside_supported_residential_snapshot":
        counts = lookup_result.get("spatial_match_counts")
        if counts != {
            "residential_parcels": 0,
            "residential_zoning_features": 0,
        }:
            raise PipelineIntegrityError(
                "invalid_lookup_failure",
                "Outside-snapshot result contains spatial matches.",
            )
        result["property"] = {
            "matched_address": _matched_address(lookup_result),
            "parcel_id": None,
            "zone": None,
        }
    elif lookup_status == "address_ambiguous":
        candidates = lookup_result.get("address_candidates")
        if not isinstance(candidates, list) or len(candidates) < 2:
            raise PipelineIntegrityError(
                "invalid_lookup_failure",
                "Ambiguous lookup omitted its address candidates.",
            )
    return result


def _resolved_property(lookup_result: dict[str, Any]) -> dict[str, str]:
    parcel = lookup_result.get("parcel")
    zoning = lookup_result.get("zoning")
    if not isinstance(parcel, dict) or not isinstance(zoning, dict):
        raise PipelineIntegrityError(
            "invalid_lookup_success",
            "Residential lookup success omitted parcel or zoning evidence.",
        )
    parcel_zone = parcel.get("designation")
    parcel_id = parcel.get("apn")
    if (
        not isinstance(parcel_zone, str)
        or not parcel_zone
        or zoning.get("designation") != parcel_zone
        or zoning.get("parcel_attribute_agrees") is not True
        or not isinstance(parcel_id, str)
        or not parcel_id
    ):
        raise PipelineIntegrityError(
            "invalid_lookup_success",
            "Residential lookup success contains inconsistent property evidence.",
        )
    return {
        "matched_address": _matched_address(lookup_result),
        "parcel_id": parcel_id,
        "zone": parcel_zone,
    }


def _matched_address(lookup_result: dict[str, Any]) -> str:
    address = lookup_result.get("address")
    display = address.get("display_address") if isinstance(address, dict) else None
    if not isinstance(display, str) or not display:
        raise PipelineIntegrityError(
            "invalid_lookup_address",
            "Residential lookup omitted its matched address.",
        )
    return display


def _validate_retrieval_result(
    retrieval: Any,
    *,
    expected_zone: str,
    expected_selection_id: str,
    expected_selections: list[dict[str, Any]],
    expected_disclaimer: str,
) -> None:
    if not isinstance(retrieval, dict):
        raise PipelineIntegrityError(
            "invalid_residential_retrieval",
            "Residential selection retrieval did not return an object.",
        )
    required = {
        "zone",
        "status",
        "reason_code",
        "available_selections",
        "requested_selection_id",
        "selection",
        "use_permission",
        "regulations",
        "not_evaluated_topics",
        "conflicts",
        "sources",
        "disclaimer",
    }
    if (
        required - set(retrieval)
        or retrieval.get("zone") != expected_zone
        or retrieval.get("requested_selection_id") != expected_selection_id
        or retrieval.get("available_selections") != expected_selections
        or retrieval.get("disclaimer") != expected_disclaimer
    ):
        raise PipelineIntegrityError(
            "invalid_residential_retrieval",
            "Residential selection retrieval is incomplete or inconsistent.",
        )
    status = retrieval.get("status")
    reason_by_status = {
        "residential_standards_found": "selected_profile_retrieved",
        "analysis_not_evaluated": (
            "selected_special_pathway_not_evaluated"
        ),
        "selection_not_available": (
            "requested_selection_unavailable_for_zone"
        ),
    }
    if status not in reason_by_status:
        raise PipelineIntegrityError(
            "invalid_residential_retrieval",
            f"Residential retrieval returned unsupported status {status!r}.",
        )
    if retrieval.get("reason_code") != reason_by_status[status]:
        raise PipelineIntegrityError(
            "invalid_residential_retrieval",
            "Residential retrieval returned an inconsistent reason code.",
        )
    permission = retrieval.get("use_permission")
    sources = retrieval.get("sources")
    if (
        not isinstance(permission, dict)
        or "approved_for_ruleset" in permission
        or not isinstance(sources, dict)
        or not isinstance(sources.get("source_documents"), dict)
        or not isinstance(sources.get("citations"), dict)
        or not isinstance(sources.get("exception_families"), dict)
        or not sources["source_documents"]
        or not sources["citations"]
    ):
        raise PipelineIntegrityError(
            "invalid_residential_retrieval",
            "Residential retrieval omitted approved use or provenance evidence.",
        )
    if status == "residential_standards_found":
        regulations = retrieval.get("regulations")
        if not isinstance(regulations, dict) or frozenset(regulations) != (
            RESIDENTIAL_PROFILE_CAPABILITIES
        ):
            raise PipelineIntegrityError(
                "invalid_residential_retrieval",
                "Residential profile retrieval is not the complete ten-rule set.",
            )
        if (
            not isinstance(retrieval.get("selection"), dict)
            or any(
                not isinstance(rule, dict)
                or "approved_for_ruleset" in rule
                for rule in regulations.values()
            )
        ):
            raise PipelineIntegrityError(
                "invalid_residential_retrieval",
                "Residential profile retrieval contains invalid selected data.",
            )
    elif status == "analysis_not_evaluated":
        if (
            not isinstance(retrieval.get("selection"), dict)
            or retrieval.get("regulations") is not None
            or not retrieval.get("not_evaluated_topics")
        ):
            raise PipelineIntegrityError(
                "invalid_residential_retrieval",
                "Residential pathway retrieval is incomplete.",
            )
    elif (
        retrieval.get("selection") is not None
        or retrieval.get("regulations") is not None
        or retrieval.get("not_evaluated_topics") != {}
        or retrieval.get("conflicts") != {}
    ):
        raise PipelineIntegrityError(
            "invalid_residential_retrieval",
            "Unavailable residential selection leaked analysis data.",
        )
