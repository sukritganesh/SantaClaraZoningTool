#!/usr/bin/env python3
"""Build and validate nonruntime fixtures for residential result contract 2.0.0.

This module exercises the approved status, selection, no-regulations, and
provenance-closure meanings without changing the production pipeline.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_r1_rules import load_json, validate_schema_contract  # noqa: E402
from scripts.validate_residential_rules_v3 import (  # noqa: E402
    PROFILE_BINDINGS,
    PROFILE_CAPABILITIES,
    TARGET_ZONES,
)


DEFAULT_SCHEMA = (
    REPO_ROOT / "contracts/residential-result-contract-2.0.0.schema.json"
)
DEFAULT_FIXTURES = (
    REPO_ROOT / "tests/fixtures/residential_result_contract_cases.json"
)
EMPTY_SOURCES = {
    "source_documents": {},
    "citations": {},
    "exception_families": {},
}
REASON_BY_STATUS = {
    "residential_zone_found": "selection_required",
    "residential_standards_found": "selected_profile_retrieved",
    "analysis_not_evaluated": "selected_special_pathway_not_evaluated",
    "selection_not_available": "requested_selection_unavailable_for_zone",
    "outside_supported_residential_snapshot": "zone_outside_exact_target_snapshot",
    "address_not_found": "no_matching_address",
    "address_ambiguous": "multiple_address_matches",
    "review_required": "spatial_or_regulatory_review_required",
}


def requirement_source_refs(requirement: dict[str, Any]) -> list[str]:
    """Return all direct source references in a v3 requirement."""

    if requirement["kind"] == "setback":
        refs = list(requirement["base"]["source_refs"])
        for adjustment in requirement["adjustments"]:
            refs.extend(adjustment["source_refs"])
        return refs
    return list(requirement["source_refs"])


def selected_rule(rule: dict[str, Any]) -> dict[str, Any]:
    """Remove the authoring-only approval flag from a selected result rule."""

    return {
        key: copy.deepcopy(value)
        for key, value in rule.items()
        if key != "approved_for_ruleset"
    }


def available_selections(zone_record: dict[str, Any]) -> list[dict[str, Any]]:
    """Return deterministic profile and pathway selection summaries."""

    labels = {
        "single_family": "Single-family primary structure",
        "two_family": "Two-family primary structure",
        "multifamily": "Multifamily primary structure",
    }
    selections = [
        {
            "selection_id": profile_id,
            "selection_kind": "profile",
            "label": labels[profile_id],
            "workflow_family": profile["workflow_family"],
            "legal_use_capability_id": profile["legal_use_capability_id"],
            "primary_structure_type": profile["primary_structure_type"],
            "analysis_status": "available",
        }
        for profile_id, profile in zone_record["analysis_profiles"].items()
    ]
    selections.extend(
        {
            "selection_id": pathway_id,
            "selection_kind": "special_pathway",
            "label": pathway["label"],
            "workflow_family": pathway["workflow_family"],
            "legal_use_capability_id": pathway["legal_use_capability_id"],
            "primary_structure_type": None,
            "analysis_status": "not_evaluated",
        }
        for pathway_id, pathway in zone_record["special_pathways"].items()
    )
    return selections


def transitive_topic_ids(
    ruleset: dict[str, Any],
    initial_ids: Iterable[str],
) -> list[str]:
    """Return topic IDs plus their topic prerequisites in stable order."""

    result: list[str] = []
    pending = list(initial_ids)
    while pending:
        topic_id = pending.pop(0)
        if topic_id in result:
            continue
        topic = ruleset["not_evaluated_topics"][topic_id]
        result.append(topic_id)
        pending.extend(topic["prerequisite_ids"])
    return result


def source_closure(
    ruleset: dict[str, Any],
    *,
    source_refs: Iterable[str],
    exception_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Build the exact citation/document/exception closure for a result."""

    shared = ruleset["shared"]
    selected_exception_ids = list(dict.fromkeys(exception_ids))
    citation_ids = list(dict.fromkeys(source_refs))
    for exception_id in selected_exception_ids:
        for citation_id in shared["exception_families"][exception_id]["source_refs"]:
            if citation_id not in citation_ids:
                citation_ids.append(citation_id)
    source_ids: list[str] = []
    for citation_id in citation_ids:
        source_id = shared["citations"][citation_id]["source_document_id"]
        if source_id not in source_ids:
            source_ids.append(source_id)
    return {
        "source_documents": {
            source_id: copy.deepcopy(shared["source_documents"][source_id])
            for source_id in source_ids
        },
        "citations": {
            citation_id: copy.deepcopy(shared["citations"][citation_id])
            for citation_id in citation_ids
        },
        "exception_families": {
            exception_id: copy.deepcopy(shared["exception_families"][exception_id])
            for exception_id in selected_exception_ids
        },
    }


def common_result(
    case: dict[str, Any],
    ruleset: dict[str, Any],
) -> dict[str, Any]:
    """Return the complete neutral result envelope for one case."""

    zone = case["zone"]
    property_record = (
        {
            "matched_address": f"Contract fixture: {case['fixture_id']}",
            "parcel_id": f"fixture-{case['fixture_id']}",
            "zone": zone,
        }
        if zone is not None
        else None
    )
    return {
        "contract_version": "2.0.0",
        "status": case["status"],
        "reason_code": case["reason_code"],
        "query": {"address": f"Contract fixture: {case['fixture_id']}"},
        "versions": {
            "address_snapshot": "2026-07-16",
            "residential_gis_snapshot": "2026-07-18",
            "ruleset": ruleset["version"],
            "ruleset_schema": ruleset["schema_version"],
        },
        "property": property_record,
        "available_selections": [],
        "requested_selection_id": case["requested_selection_id"],
        "selection": None,
        "regulations": None,
        "not_evaluated_topics": {},
        "conflicts": {},
        "sources": copy.deepcopy(EMPTY_SOURCES),
        "disclaimer": ruleset["disclaimer"],
    }


def build_fixture_result(
    case: dict[str, Any],
    ruleset: dict[str, Any],
) -> dict[str, Any]:
    """Build one deterministic result-contract fixture from candidate R1 data."""

    result = common_result(case, ruleset)
    status = case["status"]
    zone_id = case["zone"]
    zone = ruleset["zones"].get(zone_id) if zone_id is not None else None
    if status in {
        "residential_zone_found",
        "residential_standards_found",
        "analysis_not_evaluated",
        "selection_not_available",
    }:
        if zone is None:
            raise ValueError(f"Fixture {case['fixture_id']} requires an authored zone")
        result["available_selections"] = available_selections(zone)

    if status == "residential_standards_found":
        profile_id = case["requested_selection_id"]
        profile = zone["analysis_profiles"][profile_id]
        result["selection"] = {
            "selection_id": profile_id,
            "selection_kind": "profile",
            "profile_id": profile_id,
            "workflow_family": profile["workflow_family"],
            "legal_use_capability_id": profile["legal_use_capability_id"],
            "primary_structure_type": profile["primary_structure_type"],
        }
        result["regulations"] = {
            capability: selected_rule(rule)
            for capability, rule in profile["regulations"].items()
        }
        topic_ids = transitive_topic_ids(
            ruleset,
            profile["not_evaluated_topic_ids"],
        )
        result["not_evaluated_topics"] = {
            topic_id: copy.deepcopy(ruleset["not_evaluated_topics"][topic_id])
            for topic_id in topic_ids
        }
        conflict_ids = list(
            dict.fromkeys(
                rule["conflict_id"]
                for rule in profile["regulations"].values()
                if rule["conflict_id"] is not None
            )
        )
        result["conflicts"] = {
            conflict_id: copy.deepcopy(ruleset["conflicts"][conflict_id])
            for conflict_id in conflict_ids
        }
        refs: list[str] = []
        exception_ids: list[str] = []
        for rule in profile["regulations"].values():
            refs.extend(requirement_source_refs(rule["requirement"]))
            exception_ids.extend(rule["exception_family_ids"])
        for topic_id in topic_ids:
            refs.extend(ruleset["not_evaluated_topics"][topic_id]["source_refs"])
        for conflict_id in conflict_ids:
            for assertion in ruleset["conflicts"][conflict_id]["assertions"]:
                refs.extend(assertion["source_refs"])
        result["sources"] = source_closure(
            ruleset,
            source_refs=refs,
            exception_ids=exception_ids,
        )

    elif status == "analysis_not_evaluated":
        pathway_id = case["requested_selection_id"]
        pathway = zone["special_pathways"][pathway_id]
        result["selection"] = {
            "selection_id": pathway_id,
            "selection_kind": "special_pathway",
            "special_pathway_id": pathway_id,
            "workflow_family": pathway["workflow_family"],
            "legal_use_capability_id": pathway["legal_use_capability_id"],
            "primary_structure_type": None,
        }
        topic_ids = transitive_topic_ids(
            ruleset,
            ordered_union(
                pathway["not_evaluated_topic_ids"],
                pathway["analysis_requirement"]["prerequisite_ids"],
            ),
        )
        result["not_evaluated_topics"] = {
            topic_id: copy.deepcopy(ruleset["not_evaluated_topics"][topic_id])
            for topic_id in topic_ids
        }
        refs = requirement_source_refs(pathway["analysis_requirement"])
        for topic_id in topic_ids:
            refs.extend(ruleset["not_evaluated_topics"][topic_id]["source_refs"])
        result["sources"] = source_closure(ruleset, source_refs=refs)

    elif status == "selection_not_available":
        requested = case["requested_selection_id"]
        use_capability = {
            "single_family": "use.single_family_dwelling",
            "two_family": "use.two_family_dwelling",
            "multifamily": "use.multifamily_dwelling",
        }[requested]
        permission = zone["use_permissions"][use_capability]
        result["sources"] = source_closure(
            ruleset,
            source_refs=permission["requirement"]["source_refs"],
            exception_ids=permission["exception_family_ids"],
        )

    return result


def ordered_union(*groups: Iterable[str]) -> list[str]:
    """Combine sequences without changing first-seen order."""

    result: list[str] = []
    for group in groups:
        for item in group:
            if item not in result:
                result.append(item)
    return result


def result_source_refs(result: dict[str, Any]) -> set[str]:
    """Collect every citation identity referenced by result content."""

    refs: set[str] = set()
    regulations = result["regulations"] or {}
    for rule in regulations.values():
        refs.update(requirement_source_refs(rule["requirement"]))
    for topic in result["not_evaluated_topics"].values():
        refs.update(topic["source_refs"])
    for conflict in result["conflicts"].values():
        for assertion in conflict["assertions"]:
            refs.update(assertion["source_refs"])
    for exception in result["sources"]["exception_families"].values():
        refs.update(exception["source_refs"])
    return refs


def validate_result(
    result: dict[str, Any],
    *,
    schema: Optional[dict[str, Any]] = None,
) -> list[str]:
    """Return schema and cross-field errors for one 2.0.0 result."""

    if schema is None:
        schema = load_json(DEFAULT_SCHEMA)
    errors = validate_schema_contract(result, schema)
    if errors:
        return errors

    status = result["status"]
    if result["reason_code"] != REASON_BY_STATUS[status]:
        errors.append(f"{status} has the wrong reason_code")
    available_ids = [item["selection_id"] for item in result["available_selections"]]
    if len(available_ids) != len(set(available_ids)):
        errors.append("available selection IDs are not unique")
    requested = result["requested_selection_id"]
    if status in {"residential_standards_found", "analysis_not_evaluated"}:
        if requested not in available_ids:
            errors.append("selected analysis is absent from available_selections")
        if result["selection"]["selection_id"] != requested:
            errors.append("selection identity differs from requested_selection_id")
    elif status == "selection_not_available" and requested in available_ids:
        errors.append("selection_not_available names an available selection")

    property_record = result["property"]
    if status in {
        "residential_zone_found",
        "residential_standards_found",
        "analysis_not_evaluated",
        "selection_not_available",
    } and property_record["zone"] not in TARGET_ZONES:
        errors.append("residential result uses a zone outside the exact target set")
    if status == "outside_supported_residential_snapshot" and property_record[
        "zone"
    ] in TARGET_ZONES:
        errors.append("outside-snapshot result uses a target residential zone")

    if status == "residential_standards_found":
        selection = result["selection"]
        profile_id = selection["profile_id"]
        expected_binding = PROFILE_BINDINGS[profile_id]
        for field, expected in expected_binding.items():
            if selection[field] != expected:
                errors.append(f"selection.{field} must be {expected}")
        if set(result["regulations"]) != PROFILE_CAPABILITIES:
            errors.append("successful result must contain the complete profile capability set")

    citations = result["sources"]["citations"]
    source_documents = result["sources"]["source_documents"]
    refs = result_source_refs(result)
    unknown_refs = refs - set(citations)
    if unknown_refs:
        errors.append(f"result has source refs outside its closure: {sorted(unknown_refs)}")
    for citation_id, citation in citations.items():
        if citation["source_document_id"] not in source_documents:
            errors.append(f"citation {citation_id} lacks its source document")
    return errors


def load_fixture_results(
    fixture_path: Path = DEFAULT_FIXTURES,
) -> list[tuple[str, dict[str, Any]]]:
    """Load case specifications and build their complete result payloads."""

    fixture = load_json(fixture_path)
    if fixture.get("fixture_contract_version") != "1.0.0":
        raise ValueError("Unsupported fixture contract version")
    if fixture.get("result_contract_version") != "2.0.0":
        raise ValueError("Fixture does not target result contract 2.0.0")
    if fixture.get("nonruntime_contract_fixtures") is not True:
        raise ValueError("Fixtures must be explicitly marked nonruntime")
    ruleset_path = REPO_ROOT / fixture["ruleset_path"]
    ruleset = load_json(ruleset_path)
    return [
        (case["fixture_id"], build_fixture_result(case, ruleset))
        for case in fixture["cases"]
    ]


def main(argv: Optional[list[str]] = None) -> int:
    """Validate every executable contract fixture."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    args = parser.parse_args(argv)

    schema = load_json(args.schema)
    failures: list[str] = []
    results = load_fixture_results(args.fixtures)
    for fixture_id, result in results:
        failures.extend(
            f"{fixture_id}: {error}"
            for error in validate_result(result, schema=schema)
        )
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    print(f"Validated {len(results)} residential result-contract 2.0.0 fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
