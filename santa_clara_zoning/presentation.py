"""Deterministic UI-neutral presentation of Block 6 zoning results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .pipeline import CONTRACT_VERSION, PipelineIntegrityError
from .ruleset import RulesetLoadError
from .standards import StandardsRetrievalError


PRESENTATION_CONTRACT_VERSION = "1.0.0"
SCOPE_LABEL = "R1 base-zone prototype"


class PresentationIntegrityError(RuntimeError):
    """Reject input that cannot satisfy the approved presentation contract."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(message)


# Tuple order is the presentation order; values never live in this registry.
_CAPABILITIES = {
    "use.single_family_dwelling": (
        "use_permissions",
        "status",
        ("permitted_by_right",),
    ),
    "approval.zoning_clearance": ("approvals", "status", ("required",)),
    "approval.architectural_review": ("approvals", "status", ("required",)),
    "standard.maximum_primary_structure_height": (
        "key_standards",
        "maximum_quantity",
        (),
    ),
    "standard.maximum_stories": ("key_standards", "maximum_quantity", ()),
    "standard.maximum_structure_coverage": (
        "key_standards",
        "maximum_quantity",
        (),
    ),
    "setback.front": ("setbacks", "setback", ()),
    "setback.interior_side": ("setbacks", "setback", ()),
    "setback.street_side": ("setbacks", "setback", ()),
    "setback.rear": ("setbacks", "setback", ()),
}

_STATUS_LABELS = {
    "permitted_by_right": "Permitted by right under the supported base zoning",
    "required": "Required",
}

_FAILURE_KINDS = {
    "address_not_found": "lookup_failure",
    "address_ambiguous": "lookup_failure",
    "outside_supported_r1_snapshot": "lookup_failure",
    "review_required": "review_required",
}


def present_pipeline_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Map one complete Block 6 result to presentation contract 1.0.0."""

    source = _object(result, "result")
    contract = _text(source, "contract_version", "result")
    if contract != CONTRACT_VERSION:
        _fail(
            "unsupported_pipeline_contract",
            f"Expected pipeline contract {CONTRACT_VERSION}, got {contract}",
        )

    status = _text(source, "status", "result")
    _text(source, "reason_code", "result")
    _object(source.get("query"), "result.query")
    _object(source.get("versions"), "result.versions")
    _object(source.get("sources"), "result.sources")

    if status == "r1_standards_found":
        return _present_success(source)
    if status in _FAILURE_KINDS:
        return _present_failure(source, _FAILURE_KINDS[status])
    _fail("unsupported_source_status", f"Unsupported Block 6 status: {status}")


def present_integrity_error(error: Exception) -> dict[str, Any]:
    """Convert a known internal integrity failure to a safe system-error view."""

    if isinstance(error, RulesetLoadError):
        reason = "ruleset_load_error"
        summary = "The approved regulatory data could not be validated for use."
    elif isinstance(
        error,
        (PresentationIntegrityError, PipelineIntegrityError, StandardsRetrievalError),
    ):
        reason = error.reason_code
        summary = (
            "The result could not be safely presented because validated data was "
            "incomplete or inconsistent."
        )
    else:
        raise TypeError("Only known zoning-pipeline integrity errors may be presented")

    return _empty_view(
        kind="system_error",
        reason=reason,
        headline="System or data validation error",
        summary=summary,
    )


def _present_success(source: Mapping[str, Any]) -> dict[str, Any]:
    if source["reason_code"] != "approved_r1_standards_retrieved":
        _fail("invalid_success_reason", "Unexpected successful-result reason code")

    address = _object(source.get("address"), "result.address")
    parcel = _object(source.get("parcel"), "result.parcel")
    zoning = _object(source.get("zoning"), "result.zoning")
    context = _object(source.get("regulatory_context"), "regulatory_context")
    regulations = _object(source.get("regulations"), "result.regulations")
    shared = _object(source.get("shared_references"), "shared_references")

    parcel_zone = _text(parcel, "designation", "result.parcel")
    zoning_zone = _text(zoning, "designation", "result.zoning")
    if parcel_zone != zoning_zone or zoning.get("parcel_attribute_agrees") is not True:
        _fail("inconsistent_success_zoning", "Successful zoning evidence disagrees")

    unknown = set(regulations) - set(_CAPABILITIES)
    missing = set(_CAPABILITIES) - set(regulations)
    if unknown:
        _fail(
            "unsupported_capability",
            f"No approved presenter for capabilities: {sorted(unknown)}",
        )
    if missing:
        _fail(
            "missing_capability",
            f"Successful result omitted capabilities: {sorted(missing)}",
        )

    sections: dict[str, list[dict[str, Any]]] = {
        "use_permissions": [],
        "approvals": [],
        "key_standards": [],
        "setbacks": [],
    }
    items: dict[str, dict[str, Any]] = {}
    for capability, (section, kind, status_codes) in _CAPABILITIES.items():
        item = _present_rule(
            capability,
            _object(regulations[capability], f"regulations.{capability}"),
            expected_kind=kind,
            allowed_status_codes=status_codes,
        )
        sections[section].append(item)
        items[capability] = item

    citations, documents, exceptions, conflicts, selected_citations = (
        _reference_closure(items, shared)
    )
    approvals = [item["label"] for item in sections["approvals"]]
    use_label = sections["use_permissions"][0]["label"].lower()
    summary = (
        f"This property is zoned {parcel_zone}. Under the supported base-zone rules, "
        f"{use_label} is permitted by right. {_join(approvals)} are required. "
        "This prototype reports selected base-zone standards only."
    )

    return {
        "presentation_contract_version": PRESENTATION_CONTRACT_VERSION,
        "kind": "success",
        "source_status": "r1_standards_found",
        "source_reason_code": str(source["reason_code"]),
        "query": _clone(_object(source["query"], "result.query")),
        "property": {
            "display_address": _text(address, "display_address", "result.address"),
            "apn": _text(parcel, "apn", "result.parcel"),
            "zone": parcel_zone,
            "scope_label": SCOPE_LABEL,
        },
        "overview": {
            "headline": "Property Overview",
            "summary": summary,
            "disclaimer": _text(source, "disclaimer", "result"),
        },
        **sections,
        "warnings": _warnings(items, exceptions, conflicts),
        "not_evaluated": [
            {
                "topic": topic,
                "status_code": "not_evaluated",
                "status_label": "Not evaluated",
            }
            for topic in _text_array(source.get("not_evaluated"), "not_evaluated")
        ],
        "sources": _sources(
            source["sources"],
            citations,
            documents,
            selected_citations,
        ),
        "versions": _versions(
            source,
            expected_ruleset=_text(context, "ruleset_version", "regulatory_context"),
        ),
    }


def _present_rule(
    capability: str,
    rule: Mapping[str, Any],
    *,
    expected_kind: str,
    allowed_status_codes: tuple[str, ...],
) -> dict[str, Any]:
    requirement = _object(rule.get("requirement"), f"{capability}.requirement")
    kind = _text(requirement, "kind", f"{capability}.requirement")
    if kind != expected_kind:
        _fail(
            "unsupported_requirement_kind",
            f"{capability} expected {expected_kind}, got {kind}",
        )

    conflict_id = rule.get("conflict_id")
    if conflict_id is not None and not isinstance(conflict_id, str):
        _fail("invalid_conflict_reference", f"Invalid conflict on {capability}")
    validation_status = _text(rule, "validation_status", capability)
    if validation_status.startswith("project_resolved") and conflict_id is None:
        _fail(
            "missing_conflict_reference",
            f"{capability} is project-resolved but has no conflict reference",
        )

    item = {
        "capability_id": capability,
        "rule_id": _text(rule, "rule_id", capability),
        "label": _text(rule, "label", capability),
        "applicability": _clone(_object(rule.get("applicability"), capability)),
        "conditions": _text_array(rule.get("conditions"), f"{capability}.conditions"),
        "citation_ids": sorted(_requirement_refs(requirement)),
        "exception_family_ids": _text_array(
            rule.get("exception_family_ids"),
            f"{capability}.exception_family_ids",
        ),
        "conflict_id": conflict_id,
        "validation_status": validation_status,
    }

    if kind == "status":
        code = _text(requirement, "code", f"{capability}.requirement")
        if code not in allowed_status_codes or code not in _STATUS_LABELS:
            _fail("unsupported_status_code", f"Unsupported {capability} status: {code}")
        item.update(status_code=code, status_label=_STATUS_LABELS[code])
    elif kind == "maximum_quantity":
        item.update(
            qualifier="Base-zone maximum",
            value=_quantity(requirement.get("value"), f"{capability}.value"),
        )
    else:
        base = _object(requirement.get("base"), f"{capability}.base")
        item.update(
            qualifier="Base-zone minimum",
            base={
                "value": _setback_value(base.get("value"), f"{capability}.base"),
                "citation_ids": sorted(
                    _text_array(base.get("source_refs"), f"{capability}.base.refs")
                ),
            },
            adjustments=_adjustments(requirement.get("adjustments"), capability),
        )
    return item


def _quantity(value: Any, path: str) -> dict[str, Any]:
    quantity = _object(value, path)
    number = quantity.get("number")
    if not isinstance(number, (int, float)) or isinstance(number, bool):
        _fail("invalid_quantity", f"{path} has no numeric value")
    return {"number": number, "unit": _text(quantity, "unit", path)}


def _setback_value(value: Any, path: str) -> dict[str, Any]:
    setback = _object(value, path)
    kind = _text(setback, "kind", path)
    if kind == "distance":
        return {"kind": kind, **_quantity(setback, path)}
    if kind != "paired_distances":
        _fail("unsupported_setback_value", f"Unsupported {path} kind: {kind}")

    members = {}
    for index, raw_member in enumerate(_array(setback.get("members"), f"{path}.members")):
        member = _object(raw_member, f"{path}.members[{index}]")
        role = _text(member, "role", f"{path}.members[{index}]")
        if role in members:
            _fail("invalid_paired_setback", f"Duplicate {path} role: {role}")
        members[role] = {"role": role, **_quantity(member, f"{path}.{role}")}

    roles = ("smaller_setback", "larger_setback")
    if set(members) != set(roles):
        _fail("invalid_paired_setback", f"{path} must contain {roles}")
    relationship = _text(setback, "relationship", path)
    assignment = _text(setback, "physical_assignment", path)
    if relationship != "coordinated_pair" or assignment != "proposal_dependent":
        _fail("unsupported_paired_setback_semantics", f"Unsupported semantics at {path}")
    return {
        "kind": kind,
        "members": [members[role] for role in roles],
        "relationship": relationship,
        "physical_assignment": assignment,
    }


def _adjustments(value: Any, capability: str) -> list[dict[str, Any]]:
    presented = []
    for index, raw_adjustment in enumerate(_array(value, f"{capability}.adjustments")):
        path = f"{capability}.adjustments[{index}]"
        adjustment = _object(raw_adjustment, path)
        trigger = _object(adjustment.get("trigger"), f"{path}.trigger")
        effect = _object(adjustment.get("effect"), f"{path}.effect")
        story = trigger.get("story")
        if (
            trigger.get("kind") != "story_at_or_above"
            or not isinstance(story, int)
            or isinstance(story, bool)
            or story < 1
        ):
            _fail("unsupported_adjustment_trigger", f"Unsupported trigger at {path}")
        if effect.get("kind") != "replace_total_minimum":
            _fail("unsupported_adjustment_effect", f"Unsupported effect at {path}")
        presented.append(
            {
                "adjustment_id": _text(adjustment, "adjustment_id", path),
                "label": f"Total minimum beginning at story {story}",
                "trigger": {"kind": "story_at_or_above", "story": story},
                "effect": {
                    "kind": "replace_total_minimum",
                    "value": _setback_value(effect.get("value"), f"{path}.effect"),
                },
                "citation_ids": sorted(
                    _text_array(adjustment.get("source_refs"), f"{path}.refs")
                ),
            }
        )
    return presented


def _reference_closure(
    items: Mapping[str, Mapping[str, Any]],
    shared: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], set[str]]:
    citations = _object(shared.get("citations"), "shared.citations")
    documents = _object(shared.get("source_documents"), "shared.source_documents")
    exceptions = _object(shared.get("exception_families"), "shared.exceptions")
    conflicts = _object(shared.get("conflicts"), "shared.conflicts")
    citation_ids = {ref for item in items.values() for ref in item["citation_ids"]}
    exception_ids = {
        ref for item in items.values() for ref in item["exception_family_ids"]
    }
    conflict_ids = {
        item["conflict_id"]
        for item in items.values()
        if item["conflict_id"] is not None
    }
    _require_refs(citations, citation_ids, "citations")
    _require_refs(exceptions, exception_ids, "exception families")
    _require_refs(conflicts, conflict_ids, "conflicts")

    for exception_id in exception_ids:
        exception = _object(exceptions[exception_id], f"exception {exception_id}")
        citation_ids.update(_text_array(exception.get("source_refs"), exception_id))

    selected_rule_ids = {item["rule_id"] for item in items.values()}
    for conflict_id in conflict_ids:
        conflict = _object(conflicts[conflict_id], f"conflict {conflict_id}")
        affected = set(_text_array(conflict.get("affected_rule_ids"), conflict_id))
        if not affected or not affected.issubset(selected_rule_ids):
            _fail("invalid_conflict_reference", f"Invalid affected rules in {conflict_id}")
        for raw_assertion in _array(conflict.get("assertions"), conflict_id):
            assertion = _object(raw_assertion, f"{conflict_id}.assertion")
            citation_ids.update(_text_array(assertion.get("source_refs"), conflict_id))
    _require_refs(citations, citation_ids, "citations")
    return citations, documents, exceptions, conflicts, citation_ids


def _warnings(
    items: Mapping[str, Mapping[str, Any]],
    exceptions: Mapping[str, Any],
    conflicts: Mapping[str, Any],
) -> list[dict[str, Any]]:
    warnings = []
    by_rule_id = {item["rule_id"]: capability for capability, item in items.items()}

    for conflict_id in sorted(
        {item["conflict_id"] for item in items.values() if item["conflict_id"]}
    ):
        conflict = _object(conflicts[conflict_id], f"conflict {conflict_id}")
        affected = _text_array(conflict.get("affected_rule_ids"), conflict_id)
        resolution = _object(conflict.get("resolution"), f"{conflict_id}.resolution")
        warnings.append(
            {
                "kind": "source_conflict",
                "warning_id": conflict_id,
                "title": "Source conflict",
                "affected_capability_ids": [by_rule_id[rule_id] for rule_id in affected],
                "status": _text(resolution, "status", f"{conflict_id}.resolution"),
                "assertions": _clone(_array(conflict.get("assertions"), conflict_id)),
                "resolution": _clone(resolution),
            }
        )

    for capability, item in items.items():
        if item["applicability"].get("lot_context") == "corner":
            warnings.append(
                {
                    "kind": "conditional_applicability",
                    "warning_id": f"{item['rule_id']}:corner-lot",
                    "title": "Applies only to a corner lot",
                    "message": (
                        "This prototype does not classify the selected parcel as a "
                        "corner lot."
                    ),
                    "affected_capability_ids": [capability],
                }
            )
        if _has_pair(item):
            warnings.append(
                {
                    "kind": "proposal_dependent_assignment",
                    "warning_id": f"{item['rule_id']}:paired-assignment",
                    "title": "Paired side-yard assignment is proposal-dependent",
                    "message": (
                        "The smaller and larger requirements must not be averaged or "
                        "assigned to physical sides without proposal facts."
                    ),
                    "affected_capability_ids": [capability],
                }
            )

    affected_by_exception: dict[str, list[str]] = {}
    for capability, item in items.items():
        for exception_id in item["exception_family_ids"]:
            affected_by_exception.setdefault(exception_id, []).append(capability)
    for exception_id in sorted(affected_by_exception):
        exception = _object(exceptions[exception_id], f"exception {exception_id}")
        warnings.append(
            {
                "kind": "not_evaluated_exception",
                "warning_id": exception_id,
                "title": _text(exception, "label", exception_id),
                "status_code": _text(exception, "treatment", exception_id),
                "affected_capability_ids": affected_by_exception[exception_id],
                "citation_ids": sorted(
                    _text_array(exception.get("source_refs"), exception_id)
                ),
            }
        )
    return warnings


def _sources(
    raw_gis: Any,
    citations: Mapping[str, Any],
    documents: Mapping[str, Any],
    citation_ids: set[str],
) -> list[dict[str, Any]]:
    receipts = _gis_sources(raw_gis)
    for citation_id in sorted(citation_ids):
        citation = _object(citations[citation_id], f"citation {citation_id}")
        document_id = _text(citation, "source_document_id", citation_id)
        if document_id not in documents:
            _fail(
                "missing_source_document",
                f"{citation_id} references missing document {document_id}",
            )
        document = _object(documents[document_id], f"document {document_id}")
        document_receipt = {
            "title": _text(document, "title", document_id),
            "version": _text(document, "version", document_id),
            "effective_date": document.get("effective_date"),
            "local_path": _text(document, "local_path", document_id),
            "verification_status": _text(document, "verification_status", document_id),
        }
        for key in ("official_url", "url"):
            if isinstance(document.get(key), str) and document[key]:
                document_receipt[key] = document[key]
        receipts.append(
            {
                "kind": "regulatory_citation",
                "citation_id": citation_id,
                "topic": _text(citation, "topic", citation_id),
                "locator": _text(citation, "locator", citation_id),
                "source_document_id": document_id,
                "document": document_receipt,
            }
        )
    return receipts


def _present_failure(source: Mapping[str, Any], kind: str) -> dict[str, Any]:
    if any(key in source for key in ("regulatory_context", "regulations", "shared_references")):
        _fail(
            "regulations_attached_to_failure",
            "A controlled lookup or review outcome must not contain regulations",
        )
    status = str(source["status"])
    reason = str(source["reason_code"])
    headline, summary = _failure_copy(status, reason)
    view = _empty_view(
        kind=kind,
        reason=reason,
        headline=headline,
        summary=summary,
        status=status,
        query=_clone(_object(source["query"], "result.query")),
        property_data=_available_property(source),
        sources=_gis_sources(source["sources"]),
        versions=_versions(source),
    )
    candidates = _selected_objects(
        source,
        {
            "addresses": "address_candidates",
            "parcels": "parcel_candidates",
            "zoning": "zoning_candidates",
        },
        arrays=True,
    )
    evidence = _selected_objects(
        source,
        {
            "spatial_match_counts": "spatial_match_counts",
            "parcel": "parcel",
            "zoning": "zoning",
        },
    )
    if candidates:
        view["candidates"] = candidates
    if evidence:
        view["evidence"] = evidence
    return view


def _empty_view(
    *,
    kind: str,
    reason: str,
    headline: str,
    summary: str,
    status: str | None = None,
    query: dict[str, Any] | None = None,
    property_data: dict[str, Any] | None = None,
    sources: list[dict[str, Any]] | None = None,
    versions: dict[str, str] | None = None,
) -> dict[str, Any]:
    view = {
        "presentation_contract_version": PRESENTATION_CONTRACT_VERSION,
        "kind": kind,
        "source_reason_code": reason,
        "query": query or {},
        "property": property_data or {"scope_label": SCOPE_LABEL},
        "overview": {"headline": headline, "summary": summary, "disclaimer": None},
        "use_permissions": [],
        "approvals": [],
        "key_standards": [],
        "setbacks": [],
        "warnings": [],
        "not_evaluated": [],
        "sources": sources or [],
        "versions": versions or {},
    }
    if status is not None:
        view["source_status"] = status
    return view


def _versions(
    source: Mapping[str, Any],
    *,
    expected_ruleset: str | None = None,
) -> dict[str, str]:
    versions = _object(source.get("versions"), "result.versions")
    output = {
        "pipeline_contract": str(source["contract_version"]),
        "address_snapshot": _text(versions, "address_snapshot", "result.versions"),
        "r1_gis_snapshot": _text(versions, "r1_gis_snapshot", "result.versions"),
    }
    if expected_ruleset is None:
        if "ruleset" in versions:
            _fail(
                "ruleset_version_attached_to_failure",
                "A failed lookup must not include a ruleset version",
            )
        return output
    ruleset = _text(versions, "ruleset", "result.versions")
    if ruleset != expected_ruleset:
        _fail("inconsistent_ruleset_version", "Ruleset versions disagree")
    output["ruleset"] = ruleset
    return output


def _gis_sources(value: Any) -> list[dict[str, Any]]:
    sources = _object(value, "result.sources")
    preferred = ("address_layer", "parcel_layer", "zoning_layer")
    source_ids = [key for key in preferred if key in sources]
    source_ids += sorted(set(sources) - set(source_ids))
    output = []
    for source_id in source_ids:
        url = sources[source_id]
        if not isinstance(url, str) or not url:
            _fail("invalid_gis_source", f"GIS source {source_id} has no URL")
        output.append({"kind": "gis_layer", "source_id": source_id, "url": url})
    return output


def _available_property(source: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {"scope_label": SCOPE_LABEL}
    address, parcel, zoning = source.get("address"), source.get("parcel"), source.get("zoning")
    if isinstance(address, Mapping) and isinstance(address.get("display_address"), str):
        output["display_address"] = address["display_address"]
    if isinstance(parcel, Mapping):
        if isinstance(parcel.get("apn"), str):
            output["apn"] = parcel["apn"]
        if isinstance(parcel.get("designation"), str):
            output["parcel_zone"] = parcel["designation"]
    if isinstance(zoning, Mapping) and isinstance(zoning.get("designation"), str):
        output["zoning_zone"] = zoning["designation"]
    if (
        "parcel_zone" in output
        and "zoning_zone" in output
        and output["parcel_zone"] == output["zoning_zone"]
    ):
        output["zone"] = output.pop("parcel_zone")
        output.pop("zoning_zone")
    return output


def _selected_objects(
    source: Mapping[str, Any],
    keys: Mapping[str, str],
    *,
    arrays: bool = False,
) -> dict[str, Any]:
    output = {}
    for output_key, source_key in keys.items():
        if source_key not in source:
            continue
        value = (
            _array(source[source_key], source_key)
            if arrays
            else _object(source[source_key], source_key)
        )
        output[output_key] = _clone(value)
    return output


def _failure_copy(status: str, reason: str) -> tuple[str, str]:
    if status == "address_not_found" and reason == "empty_or_invalid_address":
        return "Enter an address", "Enter a non-empty Santa Clara street address."
    if status == "address_not_found":
        return (
            "Address not found",
            "No exact local address match was found. Check the address and try again.",
        )
    if status == "address_ambiguous":
        return (
            "Multiple address records matched",
            "Review the matching address records; this prototype will not select "
            "one automatically.",
        )
    if status == "outside_supported_r1_snapshot":
        return (
            "Outside the supported R1 prototype",
            "This address was located successfully, but its parcel is outside the "
            "filtered R1-6L/R1-8L snapshot. Its exact non-R1 zoning was not "
            "determined, and no regulations were attached.",
        )
    return (
        "Review required",
        "The available parcel or zoning evidence could not support one automatic "
        "result. No regulations were attached.",
    )


def _requirement_refs(requirement: Mapping[str, Any]) -> set[str]:
    if requirement["kind"] in {"status", "maximum_quantity"}:
        return set(_text_array(requirement.get("source_refs"), "requirement.refs"))
    base = _object(requirement.get("base"), "setback.base")
    refs = set(_text_array(base.get("source_refs"), "setback.base.refs"))
    for raw_adjustment in _array(requirement.get("adjustments"), "adjustments"):
        adjustment = _object(raw_adjustment, "adjustment")
        refs.update(_text_array(adjustment.get("source_refs"), "adjustment.refs"))
    return refs


def _has_pair(item: Mapping[str, Any]) -> bool:
    base = item.get("base")
    if isinstance(base, Mapping) and base.get("value", {}).get("kind") == "paired_distances":
        return True
    return any(
        adjustment.get("effect", {}).get("value", {}).get("kind") == "paired_distances"
        for adjustment in item.get("adjustments", [])
    )


def _join(labels: list[str]) -> str:
    if not labels:
        _fail("missing_approval", "Successful result has no approval records")
    if len(labels) == 1:
        return labels[0]
    return f"{', '.join(labels[:-1])} and {labels[-1]}"


def _require_refs(records: Mapping[str, Any], refs: set[str], label: str) -> None:
    missing = refs - set(records)
    if missing:
        _fail("missing_reference", f"Missing {label}: {sorted(missing)}")


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("invalid_presentation_input", f"Expected {path} to be an object")
    return value


def _array(value: Any, path: str) -> list[Any] | tuple[Any, ...]:
    if not isinstance(value, (list, tuple)):
        _fail("invalid_presentation_input", f"Expected {path} to be an array")
    return value


def _text(value: Mapping[str, Any], key: str, path: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        _fail("invalid_presentation_input", f"Expected {path}.{key} to contain text")
    return item


def _text_array(value: Any, path: str) -> list[str]:
    items = _array(value, path)
    if any(not isinstance(item, str) or not item for item in items):
        _fail("invalid_presentation_input", f"Expected text entries in {path}")
    return list(items)


def _clone(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clone(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clone(item) for item in value]
    return value


def _fail(reason_code: str, message: str) -> None:
    raise PresentationIntegrityError(reason_code, message)
