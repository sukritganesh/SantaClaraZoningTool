"""Pure exact-zone retrieval from a validated Santa Clara R1 ruleset."""

from __future__ import annotations

from typing import Any

from .ruleset import ApprovedR1Ruleset


class StandardsRetrievalError(RuntimeError):
    """Reject an unsupported zone or an incomplete regulatory result."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(message)


class UnsupportedZoneError(StandardsRetrievalError):
    """Reject any zone that is not an exact key in the approved ruleset."""

    def __init__(self, zone_code: Any, supported_zones: tuple[str, ...]) -> None:
        self.zone_code = zone_code
        self.supported_zones = supported_zones
        super().__init__(
            "unsupported_zone",
            f"Unsupported zone {zone_code!r}; expected one of {supported_zones}",
        )


def retrieve_zone_standards(
    zone_code: str,
    ruleset: ApprovedR1Ruleset,
) -> dict[str, Any]:
    """Return complete approved rules and their transitive provenance closure."""

    return _retrieve_zone_standards_data(zone_code, ruleset.as_dict())


def _retrieve_zone_standards_data(
    zone_code: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    zones = data["zones"]
    supported_zones = tuple(zones)
    if zone_code not in zones:
        raise UnsupportedZoneError(zone_code, supported_zones)

    regulations = zones[zone_code]["regulations"]
    unapproved = [
        capability
        for capability, rule in regulations.items()
        if rule["approved_for_ruleset"] is not True
    ]
    if unapproved:
        raise StandardsRetrievalError(
            "unapproved_regulation",
            f"Zone {zone_code} contains unapproved regulations: {unapproved}",
        )

    citation_ids: set[str] = set()
    exception_ids: set[str] = set()
    conflict_ids: set[str] = set()
    for rule in regulations.values():
        citation_ids.update(_requirement_source_refs(rule["requirement"]))
        exception_ids.update(rule["exception_family_ids"])
        if rule["conflict_id"] is not None:
            conflict_ids.add(rule["conflict_id"])

    shared = data["shared"]
    exception_families = _selected_records(
        shared["exception_families"],
        exception_ids,
        collection="exception families",
    )
    for exception in exception_families.values():
        citation_ids.update(exception["source_refs"])

    conflicts = _selected_records(
        data["conflicts"],
        conflict_ids,
        collection="conflicts",
    )
    for conflict in conflicts.values():
        for assertion in conflict["assertions"]:
            citation_ids.update(assertion["source_refs"])

    citations = _selected_records(
        shared["citations"],
        citation_ids,
        collection="citations",
    )
    source_document_ids = {
        citation["source_document_id"] for citation in citations.values()
    }
    source_documents = _selected_records(
        shared["source_documents"],
        source_document_ids,
        collection="source documents",
    )

    return {
        "zone": zone_code,
        "regulatory_context": {
            "jurisdiction": data["jurisdiction"],
            "ruleset_id": data["ruleset_id"],
            "ruleset_version": data["version"],
            "schema_version": data["schema_version"],
            "approved_on": data["approved_on"],
            "verified_through": data["verified_through"],
            "scope": data["scope"],
        },
        "regulations": regulations,
        "shared_references": {
            "source_documents": source_documents,
            "citations": citations,
            "exception_families": exception_families,
            "conflicts": conflicts,
        },
        "not_evaluated": data["not_evaluated"],
        "disclaimer": data["disclaimer"],
    }


def _requirement_source_refs(requirement: dict[str, Any]) -> set[str]:
    kind = requirement["kind"]
    if kind in {"status", "maximum_quantity"}:
        return set(requirement["source_refs"])
    if kind != "setback":
        raise StandardsRetrievalError(
            "unsupported_requirement",
            f"Unsupported requirement kind in approved ruleset: {kind}",
        )

    refs = set(requirement["base"]["source_refs"])
    for adjustment in requirement["adjustments"]:
        refs.update(adjustment["source_refs"])
    return refs


def _selected_records(
    records: dict[str, Any],
    selected_ids: set[str],
    *,
    collection: str,
) -> dict[str, Any]:
    missing = selected_ids - set(records)
    if missing:
        raise StandardsRetrievalError(
            "missing_reference",
            f"Selected zone references missing {collection}: {sorted(missing)}",
        )
    return {
        record_id: record
        for record_id, record in records.items()
        if record_id in selected_ids
    }
