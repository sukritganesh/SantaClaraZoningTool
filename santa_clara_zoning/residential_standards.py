"""Pure exact-selection retrieval from an approved residential ruleset."""

from __future__ import annotations

import copy
from typing import Any, Iterable

from .ruleset import ApprovedResidentialRuleset
from .standards import StandardsRetrievalError, UnsupportedZoneError


PROFILE_SELECTION_ORDER = ("single_family", "two_family", "multifamily")
PROFILE_BINDINGS = {
    "single_family": {
        "workflow_family": "single_family",
        "legal_use_capability_id": "use.single_family_dwelling",
        "primary_structure_type": "single_family_primary_structure",
    },
    "two_family": {
        "workflow_family": "multifamily",
        "legal_use_capability_id": "use.two_family_dwelling",
        "primary_structure_type": "two_family_primary_structure",
    },
    "multifamily": {
        "workflow_family": "multifamily",
        "legal_use_capability_id": "use.multifamily_dwelling",
        "primary_structure_type": "multifamily_primary_structure",
    },
}
PROFILE_LABELS = {
    "single_family": "Single-family primary structure",
    "two_family": "Two-family primary structure",
    "multifamily": "Multifamily primary structure",
}
RESIDENTIAL_PROFILE_CAPABILITIES = frozenset(
    {
        "approval.zoning_clearance",
        "approval.architectural_review",
        "standard.maximum_primary_structure_height",
        "standard.maximum_stories",
        "standard.maximum_structure_coverage",
        "standard.gross_residential_density",
        "setback.front",
        "setback.rear",
        "setback.interior_side",
        "setback.street_side",
    }
)
DIRECT_SOURCE_REQUIREMENT_KINDS = frozenset(
    {
        "status",
        "maximum_quantity",
        "quantity_range",
        "no_maximum_listed",
        "faa_controlled",
        "plan_dependent",
        "not_evaluated",
        "review_required",
    }
)


class UnsupportedSelectionError(StandardsRetrievalError):
    """Reject a selection that is neither exact nor controllably unavailable."""

    def __init__(
        self,
        selection_id: Any,
        available_ids: tuple[str, ...],
    ) -> None:
        self.selection_id = selection_id
        self.available_ids = available_ids
        super().__init__(
            "unsupported_selection",
            f"Unsupported selection {selection_id!r}; exact available IDs are "
            f"{available_ids}",
        )


def available_selections(
    zone_code: str,
    ruleset: ApprovedResidentialRuleset,
) -> list[dict[str, Any]]:
    """Return approved profiles then pathways in deterministic display order."""

    if not isinstance(ruleset, ApprovedResidentialRuleset):
        raise TypeError("ruleset must be an ApprovedResidentialRuleset")
    return _available_selections_data(zone_code, ruleset.as_dict())


def retrieve_residential_selection(
    zone_code: str,
    selection_id: str,
    ruleset: ApprovedResidentialRuleset,
) -> dict[str, Any]:
    """Return one exact approved profile, pathway, or unavailable use result."""

    if not isinstance(ruleset, ApprovedResidentialRuleset):
        raise TypeError("ruleset must be an ApprovedResidentialRuleset")
    return _retrieve_residential_selection_data(
        zone_code,
        selection_id,
        ruleset.as_dict(),
    )


def _available_selections_data(
    zone_code: str,
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    zone = _zone_record(zone_code, data)
    profiles = _object_map(
        zone.get("analysis_profiles"),
        context=f"Zone {zone_code} analysis profiles",
    )
    pathways = _object_map(
        zone.get("special_pathways"),
        context=f"Zone {zone_code} special pathways",
    )
    unknown_profiles = set(profiles) - set(PROFILE_SELECTION_ORDER)
    if unknown_profiles:
        raise StandardsRetrievalError(
            "unsupported_profile_identity",
            f"Zone {zone_code} contains unknown profiles: "
            f"{sorted(unknown_profiles)}",
        )
    collisions = set(profiles) & set(pathways)
    if collisions:
        raise StandardsRetrievalError(
            "duplicate_selection_identity",
            f"Zone {zone_code} reuses selection IDs: {sorted(collisions)}",
        )

    selections: list[dict[str, Any]] = []
    for profile_id in PROFILE_SELECTION_ORDER:
        if profile_id not in profiles:
            continue
        profile = _validated_profile(
            zone_code,
            profile_id,
            profiles[profile_id],
            zone,
        )
        selections.append(
            {
                "selection_id": profile_id,
                "selection_kind": "profile",
                "label": PROFILE_LABELS[profile_id],
                "workflow_family": profile["workflow_family"],
                "legal_use_capability_id": profile[
                    "legal_use_capability_id"
                ],
                "primary_structure_type": profile[
                    "primary_structure_type"
                ],
                "analysis_status": "available",
            }
        )

    for pathway_id, raw_pathway in pathways.items():
        pathway = _validated_pathway(
            zone_code,
            pathway_id,
            raw_pathway,
            zone,
        )
        selections.append(
            {
                "selection_id": pathway_id,
                "selection_kind": "special_pathway",
                "label": pathway["label"],
                "workflow_family": pathway["workflow_family"],
                "legal_use_capability_id": pathway[
                    "legal_use_capability_id"
                ],
                "primary_structure_type": None,
                "analysis_status": "not_evaluated",
            }
        )
    if not selections:
        raise StandardsRetrievalError(
            "missing_selection",
            f"Zone {zone_code} has no approved analysis selection",
        )
    return selections


def _retrieve_residential_selection_data(
    zone_code: str,
    selection_id: Any,
    data: dict[str, Any],
) -> dict[str, Any]:
    zone = _zone_record(zone_code, data)
    selections = _available_selections_data(zone_code, data)
    available_ids = tuple(item["selection_id"] for item in selections)
    if not isinstance(selection_id, str) or not selection_id:
        raise UnsupportedSelectionError(selection_id, available_ids)

    profiles = zone["analysis_profiles"]
    pathways = zone["special_pathways"]
    if selection_id in profiles:
        return _profile_result(
            zone_code,
            selection_id,
            profiles[selection_id],
            zone,
            selections,
            data,
        )
    if selection_id in pathways:
        return _pathway_result(
            zone_code,
            selection_id,
            pathways[selection_id],
            zone,
            selections,
            data,
        )
    if selection_id in PROFILE_BINDINGS:
        capability_id = PROFILE_BINDINGS[selection_id][
            "legal_use_capability_id"
        ]
        permissions = _object_map(
            zone.get("use_permissions"),
            context=f"Zone {zone_code} use permissions",
        )
        permission = permissions.get(capability_id)
        if (
            not isinstance(permission, dict)
            or not isinstance(permission.get("requirement"), dict)
            or permission["requirement"].get("code") != "not_listed"
            or permission.get("special_pathway_id") is not None
        ):
            raise UnsupportedSelectionError(selection_id, available_ids)
        return _unavailable_profile_result(
            zone_code,
            selection_id,
            zone,
            selections,
            data,
        )
    raise UnsupportedSelectionError(selection_id, available_ids)


def _profile_result(
    zone_code: str,
    profile_id: str,
    raw_profile: Any,
    zone: dict[str, Any],
    selections: list[dict[str, Any]],
    data: dict[str, Any],
) -> dict[str, Any]:
    profile = _validated_profile(
        zone_code,
        profile_id,
        raw_profile,
        zone,
    )
    permission = _validated_permission(
        zone_code,
        zone,
        profile["legal_use_capability_id"],
        expected_code="permitted_by_right",
        expected_pathway_id=None,
    )
    regulations = list(profile["regulations"].values())
    topic_ids = _transitive_topic_ids(
        data,
        profile["not_evaluated_topic_ids"],
    )
    topics, conflicts, sources = _evidence_closure(
        data,
        selected_records=[permission, *regulations],
        topic_ids=topic_ids,
    )
    return {
        "zone": zone_code,
        "status": "residential_standards_found",
        "reason_code": "selected_profile_retrieved",
        "available_selections": selections,
        "requested_selection_id": profile_id,
        "selection": {
            "selection_id": profile_id,
            "selection_kind": "profile",
            "profile_id": profile_id,
            "workflow_family": profile["workflow_family"],
            "legal_use_capability_id": profile[
                "legal_use_capability_id"
            ],
            "primary_structure_type": profile["primary_structure_type"],
        },
        "use_permission": _selected_rule(permission),
        "regulations": {
            capability: _selected_rule(rule)
            for capability, rule in profile["regulations"].items()
        },
        "not_evaluated_topics": topics,
        "conflicts": conflicts,
        "sources": sources,
        "disclaimer": data["disclaimer"],
    }


def _pathway_result(
    zone_code: str,
    pathway_id: str,
    raw_pathway: Any,
    zone: dict[str, Any],
    selections: list[dict[str, Any]],
    data: dict[str, Any],
) -> dict[str, Any]:
    pathway = _validated_pathway(
        zone_code,
        pathway_id,
        raw_pathway,
        zone,
    )
    permission = _validated_permission(
        zone_code,
        zone,
        pathway["legal_use_capability_id"],
        expected_code="permitted_by_right",
        expected_pathway_id=pathway_id,
    )
    topic_ids = _transitive_topic_ids(
        data,
        _ordered_union(
            pathway["not_evaluated_topic_ids"],
            pathway["analysis_requirement"]["prerequisite_ids"],
        ),
    )
    topics, conflicts, sources = _evidence_closure(
        data,
        selected_records=[permission],
        topic_ids=topic_ids,
        extra_source_refs=_requirement_source_refs(
            pathway["analysis_requirement"]
        ),
    )
    return {
        "zone": zone_code,
        "status": "analysis_not_evaluated",
        "reason_code": "selected_special_pathway_not_evaluated",
        "available_selections": selections,
        "requested_selection_id": pathway_id,
        "selection": {
            "selection_id": pathway_id,
            "selection_kind": "special_pathway",
            "special_pathway_id": pathway_id,
            "workflow_family": pathway["workflow_family"],
            "legal_use_capability_id": pathway[
                "legal_use_capability_id"
            ],
            "primary_structure_type": None,
        },
        "use_permission": _selected_rule(permission),
        "regulations": None,
        "not_evaluated_topics": topics,
        "conflicts": conflicts,
        "sources": sources,
        "disclaimer": data["disclaimer"],
    }


def _unavailable_profile_result(
    zone_code: str,
    profile_id: str,
    zone: dict[str, Any],
    selections: list[dict[str, Any]],
    data: dict[str, Any],
) -> dict[str, Any]:
    use_capability_id = PROFILE_BINDINGS[profile_id][
        "legal_use_capability_id"
    ]
    permission = _validated_permission(
        zone_code,
        zone,
        use_capability_id,
        expected_code="not_listed",
        expected_pathway_id=None,
    )
    topics, conflicts, sources = _evidence_closure(
        data,
        selected_records=[permission],
    )
    return {
        "zone": zone_code,
        "status": "selection_not_available",
        "reason_code": "requested_selection_unavailable_for_zone",
        "available_selections": selections,
        "requested_selection_id": profile_id,
        "selection": None,
        "use_permission": _selected_rule(permission),
        "regulations": None,
        "not_evaluated_topics": topics,
        "conflicts": conflicts,
        "sources": sources,
        "disclaimer": data["disclaimer"],
    }


def _validated_profile(
    zone_code: str,
    profile_id: str,
    value: Any,
    zone: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StandardsRetrievalError(
            "invalid_profile",
            f"Zone {zone_code} profile {profile_id} is not an object",
        )
    binding = PROFILE_BINDINGS[profile_id]
    for field, expected in binding.items():
        if value.get(field) != expected:
            raise StandardsRetrievalError(
                "invalid_profile_binding",
                f"Zone {zone_code} profile {profile_id} has invalid {field}",
            )
    regulations = _object_map(
        value.get("regulations"),
        context=f"Zone {zone_code} profile {profile_id} regulations",
    )
    if frozenset(regulations) != RESIDENTIAL_PROFILE_CAPABILITIES:
        raise StandardsRetrievalError(
            "incomplete_profile",
            f"Zone {zone_code} profile {profile_id} does not contain the "
            "complete ten-capability set",
        )
    unapproved = [
        capability
        for capability, rule in regulations.items()
        if not isinstance(rule, dict)
        or rule.get("approved_for_ruleset") is not True
    ]
    if unapproved:
        raise StandardsRetrievalError(
            "unapproved_regulation",
            f"Zone {zone_code} profile {profile_id} has unapproved rules: "
            f"{unapproved}",
        )
    topic_ids = value.get("not_evaluated_topic_ids")
    if not _unique_string_list(topic_ids):
        raise StandardsRetrievalError(
            "invalid_topic_reference",
            f"Zone {zone_code} profile {profile_id} has invalid topic IDs",
        )
    _validated_permission(
        zone_code,
        zone,
        binding["legal_use_capability_id"],
        expected_code="permitted_by_right",
        expected_pathway_id=None,
    )
    return value


def _validated_pathway(
    zone_code: str,
    pathway_id: str,
    value: Any,
    zone: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(pathway_id, str) or not pathway_id or not isinstance(
        value, dict
    ):
        raise StandardsRetrievalError(
            "invalid_pathway",
            f"Zone {zone_code} has an invalid special pathway",
        )
    if value.get("approved_for_ruleset") is not True:
        raise StandardsRetrievalError(
            "unapproved_pathway",
            f"Zone {zone_code} pathway {pathway_id} is not approved",
        )
    if (
        value.get("workflow_family") != "multifamily"
        or value.get("legal_use_capability_id")
        != "use.two_family_dwelling"
    ):
        raise StandardsRetrievalError(
            "invalid_pathway_binding",
            f"Zone {zone_code} pathway {pathway_id} has an invalid binding",
        )
    if not isinstance(value.get("label"), str) or not value["label"]:
        raise StandardsRetrievalError(
            "invalid_pathway",
            f"Zone {zone_code} pathway {pathway_id} has no label",
        )
    requirement = value.get("analysis_requirement")
    if not isinstance(requirement, dict) or requirement.get("kind") != (
        "not_evaluated"
    ):
        raise StandardsRetrievalError(
            "invalid_pathway_requirement",
            f"Zone {zone_code} pathway {pathway_id} is not a typed "
            "not-evaluated analysis",
        )
    _requirement_source_refs(requirement)
    if not _unique_string_list(requirement.get("prerequisite_ids")):
        raise StandardsRetrievalError(
            "invalid_topic_reference",
            f"Zone {zone_code} pathway {pathway_id} has invalid prerequisites",
        )
    if not _unique_string_list(value.get("not_evaluated_topic_ids")):
        raise StandardsRetrievalError(
            "invalid_topic_reference",
            f"Zone {zone_code} pathway {pathway_id} has invalid topic IDs",
        )
    _validated_permission(
        zone_code,
        zone,
        "use.two_family_dwelling",
        expected_code="permitted_by_right",
        expected_pathway_id=pathway_id,
    )
    return value


def _validated_permission(
    zone_code: str,
    zone: dict[str, Any],
    capability_id: str,
    *,
    expected_code: str,
    expected_pathway_id: Any,
) -> dict[str, Any]:
    permissions = _object_map(
        zone.get("use_permissions"),
        context=f"Zone {zone_code} use permissions",
    )
    permission = permissions.get(capability_id)
    if not isinstance(permission, dict):
        raise StandardsRetrievalError(
            "missing_use_permission",
            f"Zone {zone_code} has no {capability_id} permission",
        )
    requirement = permission.get("requirement")
    if (
        permission.get("approved_for_ruleset") is not True
        or not isinstance(requirement, dict)
        or requirement.get("kind") != "status"
    ):
        raise StandardsRetrievalError(
            "unapproved_use_permission",
            f"Zone {zone_code} has an invalid or unapproved "
            f"{capability_id} permission",
        )
    if requirement.get("code") != expected_code:
        raise StandardsRetrievalError(
            "use_permission_mismatch",
            f"Zone {zone_code} permission {capability_id} is "
            f"{requirement.get('code')}, not {expected_code}",
        )
    if permission.get("special_pathway_id") != expected_pathway_id:
        raise StandardsRetrievalError(
            "pathway_binding_mismatch",
            f"Zone {zone_code} permission {capability_id} has an unexpected "
            "special-pathway binding",
        )
    _requirement_source_refs(requirement)
    if not _unique_string_list(permission.get("exception_family_ids")):
        raise StandardsRetrievalError(
            "invalid_exception_reference",
            f"Zone {zone_code} permission {capability_id} has invalid "
            "exception IDs",
        )
    return permission


def _evidence_closure(
    data: dict[str, Any],
    *,
    selected_records: Iterable[dict[str, Any]],
    topic_ids: Iterable[str] = (),
    extra_source_refs: Iterable[str] = (),
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    records = list(selected_records)
    stable_topic_ids = list(topic_ids)
    topic_map = _object_map(
        data.get("not_evaluated_topics"),
        context="Not-evaluated topics",
    )
    topics = _selected_records(
        topic_map,
        stable_topic_ids,
        collection="not-evaluated topics",
    )
    conflict_ids = _ordered_union(
        record["conflict_id"]
        for record in records
        if record.get("conflict_id") is not None
    )
    conflicts = _selected_records(
        _object_map(data.get("conflicts"), context="Conflicts"),
        conflict_ids,
        collection="conflicts",
    )

    source_refs = list(extra_source_refs)
    exception_ids: list[str] = []
    for record in records:
        source_refs.extend(_requirement_source_refs(record["requirement"]))
        raw_exception_ids = record.get("exception_family_ids")
        if not _unique_string_list(raw_exception_ids):
            raise StandardsRetrievalError(
                "invalid_exception_reference",
                f"Rule {record.get('rule_id')} has invalid exception IDs",
            )
        exception_ids.extend(raw_exception_ids)
    for topic in topics.values():
        refs = topic.get("source_refs")
        if not _nonempty_unique_string_list(refs):
            raise StandardsRetrievalError(
                "invalid_source_reference",
                "A selected not-evaluated topic has invalid source refs",
            )
        source_refs.extend(refs)
    for conflict in conflicts.values():
        assertions = conflict.get("assertions")
        if not isinstance(assertions, list):
            raise StandardsRetrievalError(
                "invalid_conflict",
                "A selected conflict has no assertion list",
            )
        for assertion in assertions:
            refs = assertion.get("source_refs") if isinstance(assertion, dict) else None
            if not _nonempty_unique_string_list(refs):
                raise StandardsRetrievalError(
                    "invalid_source_reference",
                    "A selected conflict assertion has invalid source refs",
                )
            source_refs.extend(refs)
    return (
        copy.deepcopy(topics),
        copy.deepcopy(conflicts),
        _source_closure(
            data,
            source_refs=source_refs,
            exception_ids=exception_ids,
        ),
    )


def _source_closure(
    data: dict[str, Any],
    *,
    source_refs: Iterable[str],
    exception_ids: Iterable[str],
) -> dict[str, Any]:
    shared = _object_map(data.get("shared"), context="Shared references")
    citations = _object_map(shared.get("citations"), context="Citations")
    documents = _object_map(
        shared.get("source_documents"),
        context="Source documents",
    )
    exceptions = _object_map(
        shared.get("exception_families"),
        context="Exception families",
    )
    selected_exception_ids = _ordered_union(exception_ids)
    selected_exceptions = _selected_records(
        exceptions,
        selected_exception_ids,
        collection="exception families",
    )
    citation_ids = _ordered_union(source_refs)
    for exception in selected_exceptions.values():
        refs = exception.get("source_refs")
        if not _nonempty_unique_string_list(refs):
            raise StandardsRetrievalError(
                "invalid_source_reference",
                "A selected exception family has invalid source refs",
            )
        citation_ids = _ordered_union(citation_ids, refs)
    selected_citations = _selected_records(
        citations,
        citation_ids,
        collection="citations",
    )
    document_ids: list[str] = []
    for citation in selected_citations.values():
        document_id = citation.get("source_document_id")
        if not isinstance(document_id, str) or not document_id:
            raise StandardsRetrievalError(
                "invalid_source_reference",
                "A selected citation has no source document",
            )
        document_ids = _ordered_union(document_ids, [document_id])
    selected_documents = _selected_records(
        documents,
        document_ids,
        collection="source documents",
    )
    return {
        "source_documents": copy.deepcopy(selected_documents),
        "citations": copy.deepcopy(selected_citations),
        "exception_families": copy.deepcopy(selected_exceptions),
    }


def _transitive_topic_ids(
    data: dict[str, Any],
    initial_ids: Iterable[str],
) -> list[str]:
    topics = _object_map(
        data.get("not_evaluated_topics"),
        context="Not-evaluated topics",
    )
    result: list[str] = []
    pending = list(initial_ids)
    while pending:
        topic_id = pending.pop(0)
        if topic_id in result:
            continue
        topic = topics.get(topic_id)
        if not isinstance(topic, dict):
            raise StandardsRetrievalError(
                "missing_reference",
                f"Selected branch references missing topic {topic_id}",
            )
        prerequisites = topic.get("prerequisite_ids")
        if not _unique_string_list(prerequisites):
            raise StandardsRetrievalError(
                "invalid_topic_reference",
                f"Topic {topic_id} has invalid prerequisite IDs",
            )
        result.append(topic_id)
        pending.extend(prerequisites)
    return result


def _requirement_source_refs(requirement: Any) -> list[str]:
    if not isinstance(requirement, dict):
        raise StandardsRetrievalError(
            "unsupported_requirement",
            "Selected rule has no typed requirement",
        )
    kind = requirement.get("kind")
    if kind == "setback":
        base = requirement.get("base")
        adjustments = requirement.get("adjustments")
        if not isinstance(base, dict) or not isinstance(adjustments, list):
            raise StandardsRetrievalError(
                "unsupported_requirement",
                "Selected setback requirement is malformed",
            )
        groups = [base.get("source_refs")]
        groups.extend(
            adjustment.get("source_refs")
            if isinstance(adjustment, dict)
            else None
            for adjustment in adjustments
        )
        if any(not _nonempty_unique_string_list(group) for group in groups):
            raise StandardsRetrievalError(
                "invalid_source_reference",
                "Selected setback has invalid source refs",
            )
        return _ordered_union(*groups)
    if kind == "lot_area_tiered_maximum":
        groups = []
        for field in ("below_threshold", "at_or_above_threshold"):
            outcome = requirement.get(field)
            if not isinstance(outcome, dict):
                raise StandardsRetrievalError(
                    "unsupported_requirement",
                    "Selected tiered maximum is malformed",
                )
            groups.append(outcome.get("source_refs"))
        if any(not _nonempty_unique_string_list(group) for group in groups):
            raise StandardsRetrievalError(
                "invalid_source_reference",
                "Selected tiered maximum has invalid source refs",
            )
        return _ordered_union(*groups)
    if kind not in DIRECT_SOURCE_REQUIREMENT_KINDS:
        raise StandardsRetrievalError(
            "unsupported_requirement",
            f"Unsupported residential requirement kind: {kind}",
        )
    refs = requirement.get("source_refs")
    if not _nonempty_unique_string_list(refs):
        raise StandardsRetrievalError(
            "invalid_source_reference",
            f"Requirement {kind} has invalid source refs",
        )
    return list(refs)


def _zone_record(zone_code: Any, data: dict[str, Any]) -> dict[str, Any]:
    zones = _object_map(data.get("zones"), context="Residential zones")
    if zone_code not in zones:
        raise UnsupportedZoneError(zone_code, tuple(zones))
    zone = zones[zone_code]
    if not isinstance(zone, dict):
        raise StandardsRetrievalError(
            "invalid_zone",
            f"Zone {zone_code} is not an object",
        )
    return zone


def _object_map(value: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise StandardsRetrievalError(
            "invalid_ruleset_shape",
            f"{context} is not an object",
        )
    return value


def _selected_records(
    records: dict[str, Any],
    selected_ids: Iterable[str],
    *,
    collection: str,
) -> dict[str, Any]:
    stable_ids = _ordered_union(selected_ids)
    missing = set(stable_ids) - set(records)
    if missing:
        raise StandardsRetrievalError(
            "missing_reference",
            f"Selected branch references missing {collection}: "
            f"{sorted(missing)}",
        )
    return {
        record_id: records[record_id]
        for record_id in stable_ids
    }


def _selected_rule(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in rule.items()
        if key != "approved_for_ruleset"
    }


def _ordered_union(*groups: Iterable[str]) -> list[str]:
    result: list[str] = []
    for group in groups:
        for item in group:
            if item not in result:
                result.append(item)
    return result


def _unique_string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) and item for item in value)
        and len(value) == len(set(value))
    )


def _nonempty_unique_string_list(value: Any) -> bool:
    return bool(value) and _unique_string_list(value)
