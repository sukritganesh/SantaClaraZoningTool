"""Deterministic presentation contract for common residential zone summaries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from .pipeline import PipelineIntegrityError
from .presentation import PresentationIntegrityError
from .residential_summary import RESIDENTIAL_SUMMARY_CONTRACT_VERSION
from .ruleset import RulesetLoadError
from .standards import StandardsRetrievalError
from .zone_descriptions import ZoneDescriptionIntegrityError


RESIDENTIAL_PRESENTATION_CONTRACT_VERSION = "2.0.0"
RESIDENTIAL_SCOPE_LABEL = "Selected residential standards"

_CAPABILITIES = {
    "approval.zoning_clearance": "approvals",
    "approval.architectural_review": "approvals",
    "standard.maximum_primary_structure_height": "key_standards",
    "standard.maximum_stories": "key_standards",
    "standard.maximum_structure_coverage": "key_standards",
    "standard.gross_residential_density": "key_standards",
    "setback.front": "setbacks",
    "setback.interior_side": "setbacks",
    "setback.street_side": "setbacks",
    "setback.rear": "setbacks",
}
_STATUS_LABELS = {
    "permitted_by_right": "Permitted by right under the supported base zoning",
    "required": "Required",
    "not_listed": "Not listed in the controlling base table",
}
_FAILURE_KINDS = {
    "address_not_found": "lookup_failure",
    "address_ambiguous": "lookup_failure",
    "outside_supported_residential_snapshot": "lookup_failure",
    "review_required": "review_required",
}


class ZoneDescriptionLookup(Protocol):
    """Presentation-only lookup for one reviewed exact-zone description."""

    def description_for(self, zone: str) -> str:
        """Return one plain-language paragraph for an exact designation."""


def present_residential_summary(
    result: Mapping[str, Any],
    *,
    zone_description_provider: ZoneDescriptionLookup | None = None,
) -> dict[str, Any]:
    """Map one common-zone result to presentation contract 2.0.0."""

    source = _object(result, "result")
    if _text(source, "contract_version", "result") != (
        RESIDENTIAL_SUMMARY_CONTRACT_VERSION
    ):
        _fail(
            "unsupported_summary_contract",
            "Residential presentation received an unsupported summary contract.",
        )
    status = _text(source, "status", "result")
    _text(source, "reason_code", "result")
    _object(source.get("query"), "result.query")
    _object(source.get("versions"), "result.versions")

    if status == "residential_zone_summary_found":
        return _present_success(
            source,
            zone_description_provider=zone_description_provider,
        )
    if status in _FAILURE_KINDS:
        return _present_failure(source, _FAILURE_KINDS[status])
    _fail(
        "unsupported_summary_status",
        f"Unsupported residential summary status: {status}",
    )


def present_residential_integrity_error(error: Exception) -> dict[str, Any]:
    """Convert a known residential integrity failure to a safe view."""

    if isinstance(error, RulesetLoadError):
        reason = "ruleset_load_error"
        summary = "The approved regulatory data could not be validated for use."
    elif isinstance(
        error,
        (
            PresentationIntegrityError,
            PipelineIntegrityError,
            StandardsRetrievalError,
        ),
    ):
        reason = error.reason_code
        summary = (
            "The result could not be safely presented because validated data was "
            "incomplete or inconsistent."
        )
    else:
        raise TypeError("Only known zoning integrity errors may be presented")
    return _empty_view(
        kind="system_error",
        reason=reason,
        headline="System or data validation error",
        summary=summary,
    )


def _present_success(
    source: Mapping[str, Any],
    *,
    zone_description_provider: ZoneDescriptionLookup | None,
) -> dict[str, Any]:
    if source["reason_code"] != "common_zone_standards_retrieved":
        _fail("invalid_success_reason", "Unexpected zone-summary reason code.")
    property_record = _object(source.get("property"), "result.property")
    regulations = _object(source.get("regulations"), "result.regulations")
    raw_uses = _array(source.get("residential_uses"), "result.residential_uses")
    raw_pathways = _array(
        source.get("special_pathways"),
        "result.special_pathways",
    )
    raw_topics = _array(
        source.get("not_evaluated_topics"),
        "result.not_evaluated_topics",
    )
    sources = _object(source.get("sources"), "result.sources")
    conflicts = _object(source.get("conflicts"), "result.conflicts")

    if set(regulations) != set(_CAPABILITIES):
        unknown = set(regulations) - set(_CAPABILITIES)
        missing = set(_CAPABILITIES) - set(regulations)
        _fail(
            "unsupported_capability_set",
            f"Residential presentation has unknown {sorted(unknown)} or missing "
            f"{sorted(missing)} capabilities.",
        )

    uses = [_present_use(_object(item, "residential use")) for item in raw_uses]
    if not uses:
        _fail("missing_residential_use", "A zone summary must list an ordinary use.")
    use_labels = {item["selection_id"]: item["label"] for item in uses}
    pathways = [
        _present_pathway(_object(item, "special pathway"))
        for item in raw_pathways
    ]
    topics = [
        _present_topic(_object(item, "not-evaluated topic"), use_labels)
        for item in raw_topics
    ]

    sections: dict[str, list[dict[str, Any]]] = {
        "approvals": [],
        "key_standards": [],
        "setbacks": [],
    }
    items: dict[str, dict[str, Any]] = {}
    for capability, section in _CAPABILITIES.items():
        item = _present_rule(
            capability,
            _object(regulations[capability], f"regulations.{capability}"),
        )
        sections[section].append(item)
        items[capability] = item

    citation_ids, exception_records = _reference_closure(
        uses=uses,
        pathways=pathways,
        topics=topics,
        items=items,
        conflicts=conflicts,
        sources=sources,
    )
    zone = _text(property_record, "zone", "result.property")
    approval_labels = [item["label"] for item in sections["approvals"]]
    use_list = _join([item["label"] for item in uses])
    if len(uses) == 1:
        standards_sentence = (
            f"The standards below apply to the listed {uses[0]['label'].lower()} "
            "profile."
        )
    else:
        standards_sentence = (
            "The listed residential types share the supported base-zone standards "
            "shown below."
        )
    fallback_summary = (
        f"This property is zoned {zone}. The controlling base table lists "
        f"{use_list.lower()}. {standards_sentence} "
        f"{_join(approval_labels)} are required."
    )
    summary = _zone_description(
        zone,
        fallback=fallback_summary,
        provider=zone_description_provider,
    )

    return {
        "presentation_contract_version": (
            RESIDENTIAL_PRESENTATION_CONTRACT_VERSION
        ),
        "kind": "success",
        "source_status": str(source["status"]),
        "source_reason_code": str(source["reason_code"]),
        "query": _clone(source["query"]),
        "property": {
            "display_address": _text(
                property_record,
                "matched_address",
                "result.property",
            ),
            "apn": _text(property_record, "parcel_id", "result.property"),
            "zone": zone,
            "scope_label": RESIDENTIAL_SCOPE_LABEL,
        },
        "overview": {
            "headline": "Property Overview",
            "summary": summary,
            "disclaimer": _text(source, "disclaimer", "result"),
        },
        "use_permissions": uses,
        "special_pathways": pathways,
        **sections,
        "warnings": _warnings(items, exception_records, conflicts),
        "not_evaluated": topics,
        "sources": _sources(sources, citation_ids),
        "versions": _versions(source),
    }


def _zone_description(
    zone: str,
    *,
    fallback: str,
    provider: ZoneDescriptionLookup | None,
) -> str:
    """Prefer reviewed presentation copy without risking the zoning result."""

    if provider is None:
        return fallback
    try:
        description = provider.description_for(zone)
    except (
        KeyError,
        OSError,
        TypeError,
        ValueError,
        ZoneDescriptionIntegrityError,
    ):
        return fallback
    if (
        not isinstance(description, str)
        or not description.strip()
        or description != description.strip()
        or "\n" in description
        or "\r" in description
        or "<" in description
        or ">" in description
    ):
        return fallback
    return description


def _present_use(value: Mapping[str, Any]) -> dict[str, Any]:
    permission = _object(value.get("use_permission"), "use permission")
    requirement = _object(permission.get("requirement"), "use requirement")
    if requirement.get("kind") != "status":
        _fail("unsupported_use_requirement", "Use permission is not a status.")
    code = _text(requirement, "code", "use requirement")
    if code != "permitted_by_right":
        _fail("unsupported_use_status", f"Unexpected listed-use status: {code}")
    capability = _text(value, "legal_use_capability_id", "residential use")
    return {
        "selection_id": _text(value, "selection_id", "residential use"),
        "capability_id": capability,
        "primary_structure_type": _text(
            value,
            "primary_structure_type",
            "residential use",
        ),
        "workflow_family": _text(value, "workflow_family", "residential use"),
        "rule_id": _text(permission, "rule_id", "use permission"),
        "label": _text(permission, "label", "use permission"),
        "profile_label": _text(value, "profile_label", "residential use"),
        "status_code": code,
        "status_label": _STATUS_LABELS[code],
        "conditions": _text_array(permission.get("conditions"), "use conditions"),
        "citation_ids": sorted(_requirement_refs(requirement)),
    }


def _present_pathway(value: Mapping[str, Any]) -> dict[str, Any]:
    permission = _object(value.get("use_permission"), "pathway permission")
    requirement = _object(permission.get("requirement"), "pathway permission")
    if requirement.get("kind") != "status" or requirement.get("code") != (
        "permitted_by_right"
    ):
        _fail("unsupported_pathway_permission", "Pathway permission is invalid.")
    topics = []
    citation_ids = set(_requirement_refs(requirement))
    for raw_topic in _array(
        value.get("not_evaluated_topics"),
        "pathway topics",
    ):
        topic = _object(raw_topic, "pathway topic")
        refs = set(_text_array(topic.get("source_refs"), "pathway topic refs"))
        citation_ids.update(refs)
        topics.append(
            {
                "topic_id": _text(topic, "topic_id", "pathway topic"),
                "label": _text(topic, "label", "pathway topic"),
                "explanation": _text(topic, "explanation", "pathway topic"),
                "citation_ids": sorted(refs),
            }
        )
    return {
        "selection_id": _text(value, "selection_id", "special pathway"),
        "capability_id": _text(
            value,
            "legal_use_capability_id",
            "special pathway",
        ),
        "rule_id": _text(permission, "rule_id", "pathway permission"),
        "label": _text(value, "label", "special pathway"),
        "status_code": "not_evaluated",
        "status_label": "Analysis not evaluated",
        "permission_status_label": _STATUS_LABELS["permitted_by_right"],
        "conditions": _text_array(
            permission.get("conditions"),
            "pathway conditions",
        ),
        "topics": topics,
        "citation_ids": sorted(citation_ids),
    }


def _present_topic(
    value: Mapping[str, Any],
    use_labels: Mapping[str, str],
) -> dict[str, Any]:
    selection_ids = _text_array(
        value.get("applies_to_selection_ids"),
        "topic applicability",
    )
    if not selection_ids or any(item not in use_labels for item in selection_ids):
        _fail("invalid_topic_applicability", "Topic references an unknown profile.")
    refs = sorted(_text_array(value.get("source_refs"), "topic source refs"))
    return {
        "topic_id": _text(value, "topic_id", "not-evaluated topic"),
        "label": _text(value, "label", "not-evaluated topic"),
        "explanation": _text(value, "explanation", "not-evaluated topic"),
        "status_code": "not_evaluated",
        "status_label": "Not evaluated",
        "citation_ids": refs,
        "applies_to_selection_ids": selection_ids,
        "applies_to_labels": [use_labels[item] for item in selection_ids],
        "is_conditional": len(selection_ids) != len(use_labels),
    }


def _present_rule(capability: str, rule: Mapping[str, Any]) -> dict[str, Any]:
    requirement = _object(rule.get("requirement"), f"{capability}.requirement")
    conflict_id = rule.get("conflict_id")
    if conflict_id is not None and not isinstance(conflict_id, str):
        _fail("invalid_conflict_reference", f"Invalid conflict on {capability}.")
    validation_status = _text(rule, "validation_status", capability)
    if validation_status.startswith("project_resolved") and conflict_id is None:
        _fail(
            "missing_conflict_reference",
            f"{capability} is project-resolved without conflict evidence.",
        )
    source_rule_ids = _text_array(
        rule.get("source_rule_ids"),
        f"{capability}.source_rule_ids",
    )
    rule_id = _text(rule, "rule_id", capability)
    if rule_id != source_rule_ids[0] or len(set(source_rule_ids)) != len(
        source_rule_ids
    ):
        _fail("invalid_source_rule_ids", f"Invalid source rules for {capability}.")
    item = {
        "capability_id": capability,
        "rule_id": rule_id,
        "source_rule_ids": source_rule_ids,
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
        "requirement": _present_requirement(requirement, capability),
    }
    if capability.startswith("approval."):
        if requirement.get("kind") != "status":
            _fail("unsupported_approval_requirement", capability)
        code = _text(requirement, "code", f"{capability}.requirement")
        if code != "required":
            _fail("unsupported_approval_status", f"Unexpected status {code}.")
        item.update(status_code=code, status_label=_STATUS_LABELS[code])
    elif capability.startswith("setback."):
        if requirement.get("kind") not in {"setback", "plan_dependent"}:
            _fail("unsupported_setback_requirement", capability)
    elif requirement.get("kind") not in {
        "maximum_quantity",
        "quantity_range",
        "lot_area_tiered_maximum",
        "no_maximum_listed",
        "faa_controlled",
        "not_evaluated",
        "review_required",
    }:
        _fail("unsupported_standard_requirement", capability)
    return item


def _present_requirement(value: Mapping[str, Any], path: str) -> dict[str, Any]:
    kind = _text(value, "kind", path)
    if kind == "status":
        return {"kind": kind, "code": _text(value, "code", path)}
    if kind == "maximum_quantity":
        return {
            "kind": kind,
            "value": _quantity(value.get("value"), f"{path}.value"),
        }
    if kind == "quantity_range":
        minimum = _number(value.get("minimum"), f"{path}.minimum")
        maximum = _number(value.get("maximum"), f"{path}.maximum")
        if minimum > maximum:
            _fail("invalid_quantity_range", f"Minimum exceeds maximum at {path}.")
        return {
            "kind": kind,
            "minimum": minimum,
            "maximum": maximum,
            "unit": _text(value, "unit", path),
        }
    if kind == "lot_area_tiered_maximum":
        return {
            "kind": kind,
            "threshold": _quantity(value.get("threshold"), f"{path}.threshold"),
            "below_threshold": _present_tier(
                value.get("below_threshold"),
                f"{path}.below_threshold",
            ),
            "at_or_above_threshold": _present_tier(
                value.get("at_or_above_threshold"),
                f"{path}.at_or_above_threshold",
            ),
        }
    if kind == "setback":
        base = _object(value.get("base"), f"{path}.base")
        return {
            "kind": kind,
            "base": {
                "value": _setback_value(base.get("value"), f"{path}.base.value"),
                "citation_ids": sorted(
                    _text_array(base.get("source_refs"), f"{path}.base.refs")
                ),
            },
            "adjustments": _adjustments(value.get("adjustments"), path),
        }
    if kind in {
        "no_maximum_listed",
        "faa_controlled",
        "plan_dependent",
        "not_evaluated",
        "review_required",
    }:
        labels = {
            "no_maximum_listed": "No maximum listed",
            "faa_controlled": "FAA-controlled",
            "plan_dependent": "Plan-dependent",
            "not_evaluated": "Not evaluated",
            "review_required": "Review required",
        }
        presented = {
            "kind": kind,
            "label": labels[kind],
            "explanation": _text(value, "explanation", path),
        }
        if kind == "faa_controlled":
            presented["controlling_authority"] = _text(
                value,
                "controlling_authority",
                path,
            )
        if kind in {"plan_dependent", "review_required"}:
            facts = value.get("required_sources_or_facts", [])
            presented["required_sources_or_facts"] = _text_array(
                facts,
                f"{path}.required_sources_or_facts",
            )
        return presented
    _fail("unsupported_requirement_kind", f"Unsupported requirement {kind} at {path}.")


def _present_tier(value: Any, path: str) -> dict[str, Any]:
    tier = _object(value, path)
    kind = tier.get("kind")
    if kind == "maximum_quantity":
        return {
            "kind": kind,
            "value": _quantity(tier.get("value"), f"{path}.value"),
        }
    if kind == "no_maximum_listed":
        return {
            "kind": kind,
            "label": "No maximum listed",
            "explanation": _text(tier, "explanation", path),
        }
    _fail("unsupported_tier_outcome", f"Unsupported tier outcome at {path}.")


def _quantity(value: Any, path: str) -> dict[str, Any]:
    quantity = _object(value, path)
    return {
        "number": _number(quantity.get("number"), path),
        "unit": _text(quantity, "unit", path),
    }


def _number(value: Any, path: str) -> int | float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        _fail("invalid_quantity", f"{path} has no numeric value.")
    return value


def _setback_value(value: Any, path: str) -> dict[str, Any]:
    setback = _object(value, path)
    kind = _text(setback, "kind", path)
    if kind == "distance":
        return {"kind": kind, **_quantity(setback, path)}
    if kind != "paired_distances":
        _fail("unsupported_setback_value", f"Unsupported {path} kind: {kind}")
    members: dict[str, dict[str, Any]] = {}
    for index, raw_member in enumerate(_array(setback.get("members"), path)):
        member = _object(raw_member, f"{path}.members[{index}]")
        role = _text(member, "role", path)
        if role in members:
            _fail("invalid_paired_setback", f"Duplicate {path} role: {role}")
        members[role] = {"role": role, **_quantity(member, f"{path}.{role}")}
    roles = ("smaller_setback", "larger_setback")
    if set(members) != set(roles):
        _fail("invalid_paired_setback", f"{path} must contain {roles}.")
    if (
        setback.get("relationship") != "coordinated_pair"
        or setback.get("physical_assignment") != "proposal_dependent"
    ):
        _fail("unsupported_paired_setback_semantics", path)
    return {
        "kind": kind,
        "members": [members[role] for role in roles],
        "relationship": "coordinated_pair",
        "physical_assignment": "proposal_dependent",
    }


def _adjustments(value: Any, capability: str) -> list[dict[str, Any]]:
    output = []
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
            _fail("unsupported_adjustment_trigger", path)
        if effect.get("kind") != "replace_total_minimum":
            _fail("unsupported_adjustment_effect", path)
        output.append(
            {
                "adjustment_id": _text(adjustment, "adjustment_id", path),
                "label": f"Total minimum beginning at story {story}",
                "trigger": {"kind": "story_at_or_above", "story": story},
                "effect": {
                    "kind": "replace_total_minimum",
                    "value": _setback_value(
                        effect.get("value"),
                        f"{path}.effect.value",
                    ),
                },
                "citation_ids": sorted(
                    _text_array(adjustment.get("source_refs"), f"{path}.refs")
                ),
            }
        )
    return output


def _reference_closure(
    *,
    uses: list[dict[str, Any]],
    pathways: list[dict[str, Any]],
    topics: list[dict[str, Any]],
    items: Mapping[str, Mapping[str, Any]],
    conflicts: Mapping[str, Any],
    sources: Mapping[str, Any],
) -> tuple[set[str], Mapping[str, Any]]:
    citations = _object(sources.get("citations"), "sources.citations")
    documents = _object(
        sources.get("source_documents"),
        "sources.source_documents",
    )
    exceptions = _object(
        sources.get("exception_families"),
        "sources.exception_families",
    )
    citation_ids = {
        ref
        for collection in (uses, pathways, topics, list(items.values()))
        for item in collection
        for ref in item["citation_ids"]
    }
    exception_ids = {
        ref
        for item in items.values()
        for ref in item["exception_family_ids"]
    }
    conflict_ids = {
        item["conflict_id"]
        for item in items.values()
        if item["conflict_id"] is not None
    }
    _require_refs(exceptions, exception_ids, "exception families")
    _require_refs(conflicts, conflict_ids, "conflicts")
    for exception_id in exception_ids:
        exception = _object(exceptions[exception_id], f"exception {exception_id}")
        citation_ids.update(
            _text_array(exception.get("source_refs"), f"exception {exception_id}")
        )
    for conflict_id in conflict_ids:
        conflict = _object(conflicts[conflict_id], f"conflict {conflict_id}")
        for raw_assertion in _array(conflict.get("assertions"), conflict_id):
            assertion = _object(raw_assertion, f"{conflict_id}.assertion")
            citation_ids.update(
                _text_array(assertion.get("source_refs"), conflict_id)
            )
    _require_refs(citations, citation_ids, "citations")
    for citation_id in citation_ids:
        citation = _object(citations[citation_id], f"citation {citation_id}")
        document_id = _text(citation, "source_document_id", citation_id)
        if document_id not in documents:
            _fail(
                "missing_source_document",
                f"Citation {citation_id} references missing document {document_id}.",
            )
    return citation_ids, exceptions


def _warnings(
    items: Mapping[str, Mapping[str, Any]],
    exceptions: Mapping[str, Any],
    conflicts: Mapping[str, Any],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    by_rule_id = {
        rule_id: capability
        for capability, item in items.items()
        for rule_id in item["source_rule_ids"]
    }
    conflict_ids = sorted(
        item["conflict_id"] for item in items.values() if item["conflict_id"]
    )
    for conflict_id in conflict_ids:
        conflict = _object(conflicts[conflict_id], f"conflict {conflict_id}")
        affected = _text_array(conflict.get("affected_rule_ids"), conflict_id)
        if not affected or any(rule_id not in by_rule_id for rule_id in affected):
            _fail("invalid_conflict_reference", conflict_id)
        resolution = _object(conflict.get("resolution"), f"{conflict_id}.resolution")
        assertions = []
        for raw_assertion in _array(conflict.get("assertions"), conflict_id):
            assertion = _object(raw_assertion, f"{conflict_id}.assertion")
            assertions.append(
                {
                    **_clone(assertion),
                    "presented_value": _present_conflict_value(
                        assertion.get("value"),
                        f"{conflict_id}.assertion.value",
                    ),
                }
            )
        warnings.append(
            {
                "kind": "source_conflict",
                "warning_id": conflict_id,
                "title": "Source conflict",
                "affected_capability_ids": [
                    by_rule_id[rule_id] for rule_id in affected
                ],
                "status": _text(resolution, "status", f"{conflict_id}.resolution"),
                "assertions": assertions,
                "resolution": {
                    **_clone(resolution),
                    "decision_source_label": _decision_source_label(
                        _text(
                            resolution,
                            "decision_source",
                            f"{conflict_id}.resolution",
                        )
                    ),
                    "presented_value": _present_conflict_value(
                        resolution.get("selected_value"),
                        f"{conflict_id}.resolution.selected_value",
                    ),
                },
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
                        "The current lookup does not classify the selected parcel as "
                        "a corner lot."
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


def _present_conflict_value(value: Any, path: str) -> dict[str, Any]:
    item = _object(value, path)
    kind = _text(item, "kind", path)
    if kind == "quantity_range":
        return _present_requirement(item, path)
    if kind == "distance":
        return {"kind": kind, **_quantity(item, path)}
    _fail("unsupported_conflict_value", f"Unsupported conflict value at {path}.")


def _decision_source_label(value: str) -> str:
    if value == "Project owner direction for the prototype":
        return "Project owner direction for the released R1 baseline"
    return value


def _sources(source_data: Mapping[str, Any], citation_ids: set[str]) -> list[dict[str, Any]]:
    citations = _object(source_data.get("citations"), "sources.citations")
    documents = _object(
        source_data.get("source_documents"),
        "sources.source_documents",
    )
    output = []
    for citation_id in sorted(citation_ids):
        citation = _object(citations[citation_id], f"citation {citation_id}")
        document_id = _text(citation, "source_document_id", citation_id)
        document = _object(documents[document_id], f"document {document_id}")
        receipt = {
            "title": _text(document, "title", document_id),
            "version": _text(document, "version", document_id),
            "effective_date": document.get("effective_date"),
            "local_path": _text(document, "local_path", document_id),
            "verification_status": _text(
                document,
                "verification_status",
                document_id,
            ),
        }
        for key in ("official_url", "url"):
            if isinstance(document.get(key), str) and document[key]:
                receipt[key] = document[key]
        output.append(
            {
                "kind": "regulatory_citation",
                "citation_id": citation_id,
                "topic": _text(citation, "topic", citation_id),
                "locator": _text(citation, "locator", citation_id),
                "source_document_id": document_id,
                "document": receipt,
            }
        )
    return output


def _present_failure(source: Mapping[str, Any], kind: str) -> dict[str, Any]:
    if (
        source.get("residential_uses") != []
        or source.get("special_pathways") != []
        or source.get("regulations") is not None
        or source.get("not_evaluated_topics") != []
        or source.get("conflicts") != {}
    ):
        _fail(
            "regulations_attached_to_failure",
            "A controlled lookup outcome contains residential analysis data.",
        )
    status = str(source["status"])
    reason = str(source["reason_code"])
    headline, summary = _failure_copy(status, reason)
    property_data: dict[str, Any] = {"scope_label": RESIDENTIAL_SCOPE_LABEL}
    raw_property = source.get("property")
    if isinstance(raw_property, Mapping):
        if isinstance(raw_property.get("matched_address"), str):
            property_data["display_address"] = raw_property["matched_address"]
        if isinstance(raw_property.get("parcel_id"), str):
            property_data["apn"] = raw_property["parcel_id"]
        if isinstance(raw_property.get("zone"), str):
            property_data["zone"] = raw_property["zone"]
    return _empty_view(
        kind=kind,
        reason=reason,
        headline=headline,
        summary=summary,
        status=status,
        query=_clone(_object(source["query"], "result.query")),
        property_data=property_data,
        versions=_versions(source),
    )


def _empty_view(
    *,
    kind: str,
    reason: str,
    headline: str,
    summary: str,
    status: str | None = None,
    query: dict[str, Any] | None = None,
    property_data: dict[str, Any] | None = None,
    versions: dict[str, str] | None = None,
) -> dict[str, Any]:
    view = {
        "presentation_contract_version": (
            RESIDENTIAL_PRESENTATION_CONTRACT_VERSION
        ),
        "kind": kind,
        "source_reason_code": reason,
        "query": query or {},
        "property": property_data or {"scope_label": RESIDENTIAL_SCOPE_LABEL},
        "overview": {"headline": headline, "summary": summary, "disclaimer": None},
        "use_permissions": [],
        "special_pathways": [],
        "approvals": [],
        "key_standards": [],
        "setbacks": [],
        "warnings": [],
        "not_evaluated": [],
        "sources": [],
        "versions": versions or {},
    }
    if status is not None:
        view["source_status"] = status
    return view


def _versions(source: Mapping[str, Any]) -> dict[str, str]:
    versions = _object(source.get("versions"), "result.versions")
    return {
        "summary_contract": str(source["contract_version"]),
        "source_result_contract": _text(
            source,
            "source_result_contract",
            "result",
        ),
        "address_snapshot": _text(versions, "address_snapshot", "result.versions"),
        "residential_gis_snapshot": _text(
            versions,
            "residential_gis_snapshot",
            "result.versions",
        ),
        "ruleset": _text(versions, "ruleset", "result.versions"),
        "ruleset_schema": _text(versions, "ruleset_schema", "result.versions"),
    }


def _failure_copy(status: str, reason: str) -> tuple[str, str]:
    if status == "address_not_found" and reason == "no_matching_address":
        return (
            "Address not found",
            "No exact local address match was found. Check the address and try again.",
        )
    if status == "address_not_found":
        return "Enter an address", "Enter a non-empty Santa Clara street address."
    if status == "address_ambiguous":
        return (
            "Multiple address records matched",
            "Review the entered address; the lookup will not choose one record "
            "automatically.",
        )
    if status == "outside_supported_residential_snapshot":
        return (
            "Outside the supported residential zones",
            "This address was located, but it does not intersect the selected "
            "residential zoning snapshot. No regulations were attached.",
        )
    return (
        "Review required",
        "The available parcel or zoning evidence could not support one automatic "
        "result. No regulations were attached.",
    )


def _requirement_refs(requirement: Mapping[str, Any]) -> set[str]:
    kind = requirement.get("kind")
    if kind in {
        "status",
        "maximum_quantity",
        "quantity_range",
        "no_maximum_listed",
        "faa_controlled",
        "plan_dependent",
        "not_evaluated",
        "review_required",
    }:
        return set(_text_array(requirement.get("source_refs"), "requirement.refs"))
    if kind == "lot_area_tiered_maximum":
        refs: set[str] = set()
        for key in ("below_threshold", "at_or_above_threshold"):
            tier = _object(requirement.get(key), f"requirement.{key}")
            refs.update(_text_array(tier.get("source_refs"), f"{key}.refs"))
        return refs
    if kind == "setback":
        base = _object(requirement.get("base"), "setback.base")
        refs = set(_text_array(base.get("source_refs"), "setback.base.refs"))
        for raw_adjustment in _array(requirement.get("adjustments"), "adjustments"):
            adjustment = _object(raw_adjustment, "adjustment")
            refs.update(
                _text_array(adjustment.get("source_refs"), "adjustment.refs")
            )
        return refs
    _fail("unsupported_requirement_kind", f"Cannot collect refs for {kind}.")


def _has_pair(item: Mapping[str, Any]) -> bool:
    requirement = item.get("requirement", {})
    if requirement.get("kind") != "setback":
        return False
    base = requirement.get("base", {})
    if base.get("value", {}).get("kind") == "paired_distances":
        return True
    return any(
        adjustment.get("effect", {}).get("value", {}).get("kind")
        == "paired_distances"
        for adjustment in requirement.get("adjustments", [])
    )


def _join(labels: list[str]) -> str:
    if not labels:
        _fail("missing_label", "Cannot compose an empty label list.")
    if len(labels) == 1:
        return labels[0]
    return f"{', '.join(labels[:-1])} and {labels[-1]}"


def _require_refs(records: Mapping[str, Any], refs: set[str], label: str) -> None:
    missing = refs - set(records)
    if missing:
        _fail("missing_reference", f"Missing {label}: {sorted(missing)}")


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("invalid_presentation_input", f"Expected {path} to be an object.")
    return value


def _array(value: Any, path: str) -> list[Any] | tuple[Any, ...]:
    if not isinstance(value, (list, tuple)):
        _fail("invalid_presentation_input", f"Expected {path} to be an array.")
    return value


def _text(value: Mapping[str, Any], key: str, path: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        _fail("invalid_presentation_input", f"Expected {path}.{key} to contain text.")
    return item


def _text_array(value: Any, path: str) -> list[str]:
    items = _array(value, path)
    if any(not isinstance(item, str) or not item for item in items):
        _fail("invalid_presentation_input", f"Expected text entries in {path}.")
    return list(items)


def _clone(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clone(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clone(item) for item in value]
    return value


def _fail(reason_code: str, message: str) -> None:
    raise PresentationIntegrityError(reason_code, message)
