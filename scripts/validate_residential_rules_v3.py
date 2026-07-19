#!/usr/bin/env python3
"""Validate Santa Clara residential ruleset v3 candidates and approvals.

JSON Schema enforces closed local shapes. This module enforces target-zone,
profile, provenance, conflict, semantic, and runtime-eligibility invariants.
Partial candidates are valid for migration and contract testing; production
eligibility always requires the complete approved target matrix.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_r1_rules import (  # noqa: E402
    load_json,
    sha256_file,
    validate_schema_contract,
)


DEFAULT_SCHEMA = REPO_ROOT / "rulesets/schema/ruleset-v3.schema.json"
DEFAULT_RULESET = (
    REPO_ROOT
    / "rulesets/santa_clara/residential/2026-07-19.1/ruleset.json"
)
DEFAULT_CROSSWALK = DEFAULT_RULESET.parent / "migration-crosswalk.json"
DEFAULT_SOURCE_V2 = (
    REPO_ROOT / "rulesets/santa_clara/r1/2026-07-17.2/ruleset.json"
)
DEFAULT_GIS_FIXTURES = (
    REPO_ROOT / "tests/fixtures/residential_gis_fixture_inventory.json"
)

EXPECTED_RULESET_ID = "santa-clara-residential-zoning"
EXPECTED_JURISDICTION = {
    "name": "City of Santa Clara",
    "slug": "santa_clara",
    "state": "CA",
    "country": "US",
}
TARGET_ZONES = {
    "R1-6L",
    "R1-8L",
    "R2",
    "R3",
    "R4",
    "R5",
    "R6",
    "PH-R5",
    "UV",
    "VR",
    "UC",
    "HDF",
}
USE_CAPABILITIES = {
    "use.single_family_dwelling",
    "use.two_family_dwelling",
    "use.multifamily_dwelling",
}
PROFILE_CAPABILITIES = {
    "approval.zoning_clearance",
    "approval.architectural_review",
    "standard.maximum_primary_structure_height",
    "standard.maximum_stories",
    "standard.maximum_structure_coverage",
    "setback.front",
    "setback.rear",
    "setback.interior_side",
    "setback.street_side",
}
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
EXPECTED_PROFILES = {
    "R1-6L": {"single_family"},
    "R1-8L": {"single_family"},
    "R2": {"single_family", "two_family", "multifamily"},
    "R3": {"two_family", "multifamily"},
    "R4": {"two_family", "multifamily"},
    "R5": {"multifamily"},
    "R6": {"multifamily"},
    "PH-R5": {"multifamily"},
    "UV": {"multifamily"},
    "VR": {"multifamily"},
    "UC": {"multifamily"},
    "HDF": {"multifamily"},
}
EXPECTED_USE_STATUS = {
    "R1-6L": ("permitted_by_right", "permitted_by_right", "not_listed"),
    "R1-8L": ("permitted_by_right", "permitted_by_right", "not_listed"),
    "R2": ("permitted_by_right", "permitted_by_right", "permitted_by_right"),
    "R3": ("not_listed", "permitted_by_right", "permitted_by_right"),
    "R4": ("not_listed", "permitted_by_right", "permitted_by_right"),
    "R5": ("not_listed", "not_listed", "permitted_by_right"),
    "R6": ("not_listed", "not_listed", "permitted_by_right"),
    "PH-R5": ("not_listed", "not_listed", "permitted_by_right"),
    "UV": ("not_listed", "not_listed", "permitted_by_right"),
    "VR": ("not_listed", "not_listed", "permitted_by_right"),
    "UC": ("not_listed", "not_listed", "permitted_by_right"),
    "HDF": ("not_listed", "not_listed", "permitted_by_right"),
}
USE_CAPABILITY_ORDER = (
    "use.single_family_dwelling",
    "use.two_family_dwelling",
    "use.multifamily_dwelling",
)
SPECIAL_PATHWAY_ID = "r1_chapter_18_24_two_unit"
EXPECTED_LOT_CONTEXT = {
    "approval.zoning_clearance": "not_applicable",
    "approval.architectural_review": "not_applicable",
    "standard.maximum_primary_structure_height": "all",
    "standard.maximum_stories": "all",
    "standard.maximum_structure_coverage": "all",
    "setback.front": "all",
    "setback.rear": "all",
    "setback.interior_side": "all",
    "setback.street_side": "corner",
}
MAXIMUM_UNITS = {
    "standard.maximum_primary_structure_height": "ft",
    "standard.maximum_stories": "stories",
    "standard.maximum_structure_coverage": "percent",
}
MAXIMUM_REQUIREMENT_KINDS = {
    "maximum_quantity",
    "no_maximum_listed",
    "faa_controlled",
    "plan_dependent",
    "not_evaluated",
    "review_required",
}
MAXIMUM_REQUIREMENT_KINDS_BY_CAPABILITY = {
    "standard.maximum_primary_structure_height": MAXIMUM_REQUIREMENT_KINDS,
    "standard.maximum_stories": MAXIMUM_REQUIREMENT_KINDS,
    "standard.maximum_structure_coverage": MAXIMUM_REQUIREMENT_KINDS
    - {"faa_controlled"},
}
SETBACK_REQUIREMENT_KINDS = {
    "setback",
    "plan_dependent",
    "not_evaluated",
    "review_required",
}
ZERO_COUNT_ZONES = {"R5", "R6"}
EXCLUDED_DESIGNATIONS = {
    "R1-6LHT": "R1-6L",
    "R2-7L": "R2",
    "R2HT": "R2",
}


def duplicate_values(values: Iterable[Any]) -> set[Any]:
    """Return values that occur more than once."""

    seen: set[Any] = set()
    duplicates: set[Any] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def version_date(version: Any) -> Optional[date]:
    """Return the calendar portion of a ruleset version."""

    if not isinstance(version, str):
        return None
    try:
        return date.fromisoformat(version.split(".", 1)[0])
    except ValueError:
        return None


def resolved_repo_path(repo_root: Path, relative_path: Any) -> Optional[Path]:
    """Resolve a repository-relative path without permitting traversal."""

    if not isinstance(relative_path, str) or not relative_path:
        return None
    supplied = Path(relative_path)
    if supplied.is_absolute():
        return None
    resolved_root = repo_root.resolve()
    resolved = (resolved_root / supplied).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return None
    return resolved


def validate_source_refs(
    refs: Iterable[str],
    *,
    citation_ids: set[str],
    location: str,
    errors: list[str],
) -> None:
    """Require every local source reference to resolve."""

    unknown = set(refs) - citation_ids
    if unknown:
        errors.append(f"{location} has unknown source refs: {sorted(unknown)}")


def validate_gis_fixture_contract(inventory: dict[str, Any]) -> list[str]:
    """Validate live, zero-count, and excluded exact-designation fixtures."""

    errors: list[str] = []
    if inventory.get("fixture_contract_version") != "1.0.0":
        errors.append("GIS fixture contract version must be 1.0.0")
    if inventory.get("status") != "source_and_geometry_verified":
        errors.append("GIS fixture inventory is not source_and_geometry_verified")

    real = inventory.get("real_address_fixtures")
    zero = inventory.get("synthetic_zero_count_fixtures")
    excluded = inventory.get("synthetic_excluded_designation_fixtures")
    if not isinstance(real, list) or not isinstance(zero, list) or not isinstance(excluded, list):
        return errors + ["GIS fixture groups must be arrays"]

    real_designations = [record.get("designation") for record in real]
    expected_real = TARGET_ZONES - ZERO_COUNT_ZONES
    if set(real_designations) != expected_real or len(real_designations) != len(expected_real):
        errors.append("real GIS fixtures must cover each live target designation exactly once")
    if ZERO_COUNT_ZONES & set(real_designations):
        errors.append("R5 and R6 must not have invented real-address fixtures")

    zero_designations = [record.get("designation") for record in zero]
    if set(zero_designations) != ZERO_COUNT_ZONES or len(zero_designations) != 2:
        errors.append("synthetic zero-count fixtures must contain exactly R5 and R6")
    for index, record in enumerate(zero):
        if record.get("kind") != "synthetic_ruleset_and_contract_fixture":
            errors.append(f"synthetic_zero_count_fixtures[{index}] has the wrong kind")
        if record.get("parcel_source_count") != 0:
            errors.append(f"synthetic_zero_count_fixtures[{index}] parcel count must be zero")
        if record.get("current_zoning_source_count") != 0:
            errors.append(
                f"synthetic_zero_count_fixtures[{index}] current-zoning count must be zero"
            )

    excluded_designations = [record.get("designation") for record in excluded]
    if set(excluded_designations) != set(EXCLUDED_DESIGNATIONS) or len(
        excluded_designations
    ) != len(EXCLUDED_DESIGNATIONS):
        errors.append("excluded GIS fixtures must contain the three exact negative designations")
    for index, record in enumerate(excluded):
        designation = record.get("designation")
        if designation not in EXCLUDED_DESIGNATIONS:
            continue
        if record.get("kind") != "synthetic_negative_designation_fixture":
            errors.append(f"synthetic_excluded_designation_fixtures[{index}] has the wrong kind")
        if record.get("expected_treatment") != "unsupported_exact_designation":
            errors.append(
                f"synthetic_excluded_designation_fixtures[{index}] must fail as unsupported"
            )
        if record.get("must_not_normalize_to") != EXCLUDED_DESIGNATIONS[designation]:
            errors.append(
                f"synthetic_excluded_designation_fixtures[{index}] has the wrong no-normalize target"
            )
    return errors


def requirement_source_refs(requirement: dict[str, Any]) -> list[str]:
    """Collect source references from any supported requirement shape."""

    if requirement["kind"] == "setback":
        refs = list(requirement["base"]["source_refs"])
        for adjustment in requirement["adjustments"]:
            refs.extend(adjustment["source_refs"])
        return refs
    return list(requirement["source_refs"])


def iter_rules(
    ruleset: dict[str, Any],
) -> Iterable[tuple[str, Optional[str], str, dict[str, Any]]]:
    """Yield zone, profile, capability, and rule for permissions and profiles."""

    for zone, zone_record in ruleset["zones"].items():
        for capability, rule in zone_record["use_permissions"].items():
            yield zone, None, capability, rule
        for profile_id, profile in zone_record["analysis_profiles"].items():
            for capability, rule in profile["regulations"].items():
                yield zone, profile_id, capability, rule


def operational_assertion_value(rule: dict[str, Any]) -> dict[str, Any]:
    """Project a rule requirement onto the comparable conflict value shape."""

    requirement = rule["requirement"]
    kind = requirement["kind"]
    if kind == "status":
        return {"kind": "status", "code": requirement["code"]}
    if kind == "maximum_quantity":
        return {
            "kind": "quantity",
            "number": requirement["value"]["number"],
            "unit": requirement["value"]["unit"],
        }
    if kind == "setback":
        return requirement["base"]["value"]
    return {"kind": kind, "reason_code": requirement["reason_code"]}


def validate_setback_value(
    value: dict[str, Any],
    *,
    location: str,
    allow_paired: bool,
    errors: list[str],
) -> None:
    """Enforce operationally meaningful positive setback values."""

    if value["kind"] == "distance":
        number = value["number"]
        if isinstance(number, bool) or number <= 0:
            errors.append(f"{location}.number must be greater than zero")
        return

    if not allow_paired:
        errors.append(f"{location} uses paired distances outside interior-side setback")
    smaller = value["members"][0]["number"]
    larger = value["members"][1]["number"]
    if isinstance(smaller, bool) or smaller <= 0:
        errors.append(f"{location} smaller setback must be greater than zero")
    if isinstance(larger, bool) or larger <= 0:
        errors.append(f"{location} larger setback must be greater than zero")
    if smaller > larger:
        errors.append(f"{location} smaller setback exceeds larger setback")


def validate_requirement(
    capability: str,
    requirement: dict[str, Any],
    *,
    citation_ids: set[str],
    location: str,
    errors: list[str],
) -> None:
    """Enforce capability-to-requirement semantic compatibility."""

    kind = requirement["kind"]
    if capability.startswith("approval."):
        if kind not in {"status", "review_required"}:
            errors.append(f"{location} must use an approval-compatible requirement")
        elif kind == "status" and requirement["code"] not in {
            "required",
            "may_be_required",
        }:
            errors.append(f"{location} has an approval-incompatible status")
    elif capability in MAXIMUM_UNITS:
        if kind not in MAXIMUM_REQUIREMENT_KINDS_BY_CAPABILITY[capability]:
            errors.append(f"{location} must use a maximum-compatible requirement")
        elif kind == "maximum_quantity":
            value = requirement["value"]
            expected_unit = MAXIMUM_UNITS[capability]
            if value["unit"] != expected_unit:
                errors.append(f"{location} must use unit {expected_unit}")
            number = value["number"]
            if isinstance(number, bool) or number <= 0:
                errors.append(f"{location} numeric maximum must be positive")
            if capability == "standard.maximum_stories" and (
                not isinstance(number, int) or isinstance(number, bool)
            ):
                errors.append(f"{location} story maximum must be an integer")
            if capability == "standard.maximum_structure_coverage" and number > 100:
                errors.append(f"{location} coverage maximum cannot exceed 100 percent")
    elif capability in {
        "setback.front",
        "setback.rear",
        "setback.interior_side",
        "setback.street_side",
    }:
        if kind not in SETBACK_REQUIREMENT_KINDS:
            errors.append(f"{location} must use a setback-compatible requirement")
        elif kind == "setback":
            allow_paired = capability == "setback.interior_side"
            base_value = requirement["base"]["value"]
            validate_setback_value(
                base_value,
                location=f"{location}.base.value",
                allow_paired=allow_paired,
                errors=errors,
            )
            adjustment_ids = [
                adjustment["adjustment_id"]
                for adjustment in requirement["adjustments"]
            ]
            duplicates = duplicate_values(adjustment_ids)
            if duplicates:
                errors.append(f"{location} has duplicate adjustment IDs: {sorted(duplicates)}")
            for index, adjustment in enumerate(requirement["adjustments"]):
                adjustment_location = f"{location}.adjustments[{index}]"
                if adjustment["trigger"]["kind"] != "story_at_or_above":
                    errors.append(f"{adjustment_location} uses an unevaluated trigger")
                elif adjustment["trigger"]["story"] < 2:
                    errors.append(f"{adjustment_location} must begin at story two or above")
                if adjustment["effect"]["kind"] != "replace_total_minimum":
                    errors.append(f"{adjustment_location} uses an unevaluated effect")
                effect_value = adjustment["effect"]["value"]
                validate_setback_value(
                    effect_value,
                    location=f"{adjustment_location}.effect.value",
                    allow_paired=allow_paired,
                    errors=errors,
                )
                if effect_value["kind"] != base_value["kind"]:
                    errors.append(f"{adjustment_location} value shape differs from its base")

            resolution = requirement.get("adjustment_resolution")
            if len(adjustment_ids) > 1:
                if resolution is None:
                    errors.append(f"{location} lacks adjustment precedence")
                elif set(resolution["ordered_adjustment_ids"]) != set(adjustment_ids):
                    errors.append(f"{location} precedence does not match adjustment IDs")
            elif resolution is not None:
                errors.append(f"{location} has unnecessary adjustment precedence")
    else:
        errors.append(f"{location} uses an unsupported capability")

    validate_source_refs(
        requirement_source_refs(requirement),
        citation_ids=citation_ids,
        location=location,
        errors=errors,
    )


def validate_ruleset(
    ruleset: dict[str, Any],
    *,
    schema: Optional[dict[str, Any]] = None,
    repo_root: Path = REPO_ROOT,
    verify_source_files: bool = False,
    require_runtime_eligible: bool = False,
) -> list[str]:
    """Return schema and domain errors for a v3 candidate or approval."""

    if schema is None:
        schema = load_json(DEFAULT_SCHEMA)
    errors = validate_schema_contract(ruleset, schema)
    if errors:
        return errors

    if ruleset["ruleset_id"] != EXPECTED_RULESET_ID:
        errors.append(f"ruleset_id must be {EXPECTED_RULESET_ID}")
    if ruleset["jurisdiction"] != EXPECTED_JURISDICTION:
        errors.append("jurisdiction must identify the City of Santa Clara")

    scope = ruleset["scope"]
    if set(scope["workflow_families"]) != {"single_family", "multifamily"}:
        errors.append("scope must contain both workflow families")
    if set(scope["legal_use_capability_ids"]) != USE_CAPABILITIES:
        errors.append("scope must contain all three legal-use capabilities")
    if set(scope["primary_structure_types"]) != {
        binding["primary_structure_type"] for binding in PROFILE_BINDINGS.values()
    }:
        errors.append("scope must contain all three primary-structure identities")

    verified_date = date.fromisoformat(ruleset["verified_through"])
    publication_date = version_date(ruleset["version"])
    if publication_date is None:
        errors.append("version does not contain a valid publication date")
    elif publication_date < verified_date:
        errors.append("ruleset version predates its verification cutoff")
    if ruleset["approved_on"] is not None:
        approved_date = date.fromisoformat(ruleset["approved_on"])
        if approved_date < verified_date:
            errors.append("approved_on predates verified_through")

    for index, predecessor in enumerate(ruleset["predecessor_rulesets"]):
        crosswalk_path = resolved_repo_path(repo_root, predecessor["crosswalk_path"])
        if crosswalk_path is None:
            errors.append(
                f"predecessor_rulesets[{index}].crosswalk_path must remain inside the repository"
            )
        elif verify_source_files and not crosswalk_path.is_file():
            errors.append(
                f"predecessor_rulesets[{index}] crosswalk is missing: "
                f"{predecessor['crosswalk_path']}"
            )

    shared = ruleset["shared"]
    source_documents = shared["source_documents"]
    source_ids = set(source_documents)
    citations = shared["citations"]
    citation_ids = set(citations)
    exception_ids = set(shared["exception_families"])

    for source_id, source in source_documents.items():
        location = f"shared.source_documents.{source_id}"
        source_path = resolved_repo_path(repo_root, source["local_path"])
        if source_path is None:
            errors.append(f"{location}.local_path must remain inside the repository")
        elif verify_source_files:
            if not source_path.is_file():
                errors.append(f"{location} source file is missing: {source['local_path']}")
            elif sha256_file(source_path) != source["sha256"]:
                errors.append(f"{location} checksum does not match: {source['local_path']}")

    for citation_id, citation in citations.items():
        if citation["source_document_id"] not in source_ids:
            errors.append(
                f"shared.citations.{citation_id} references unknown source document: "
                f"{citation['source_document_id']}"
            )
    for definition_id, definition in shared["definitions"].items():
        validate_source_refs(
            definition["source_refs"],
            citation_ids=citation_ids,
            location=f"shared.definitions.{definition_id}",
            errors=errors,
        )
    for exception_id, exception in shared["exception_families"].items():
        validate_source_refs(
            exception["source_refs"],
            citation_ids=citation_ids,
            location=f"shared.exception_families.{exception_id}",
            errors=errors,
        )

    topic_ids = set(ruleset["not_evaluated_topics"])
    for topic_id, topic in ruleset["not_evaluated_topics"].items():
        validate_source_refs(
            topic["source_refs"],
            citation_ids=citation_ids,
            location=f"not_evaluated_topics.{topic_id}",
            errors=errors,
        )
        unknown_prerequisites = set(topic["prerequisite_ids"]) - topic_ids
        if unknown_prerequisites:
            errors.append(
                f"not_evaluated_topics.{topic_id} has unknown topic prerequisites: "
                f"{sorted(unknown_prerequisites)}"
            )

    zones = ruleset["zones"]
    unexpected_zones = set(zones) - TARGET_ZONES
    if unexpected_zones:
        errors.append(f"zones contains unsupported exact designations: {sorted(unexpected_zones)}")
    if require_runtime_eligible and set(zones) != TARGET_ZONES:
        missing = TARGET_ZONES - set(zones)
        errors.append(f"runtime ruleset is missing exact target zones: {sorted(missing)}")

    rule_ids: list[str] = []
    rules_by_id: dict[str, dict[str, Any]] = {}
    for zone, zone_record in zones.items():
        if zone not in TARGET_ZONES:
            # The exact-designation error above is sufficient; do not apply a
            # nearby zone's legal matrix to an unsupported key.
            continue
        permissions = zone_record["use_permissions"]
        if set(permissions) != USE_CAPABILITIES:
            errors.append(f"zones.{zone}.use_permissions must contain all three uses")
        for index, capability in enumerate(USE_CAPABILITY_ORDER):
            permission = permissions[capability]
            location = f"zones.{zone}.use_permissions.{capability}"
            expected_rule_id = f"us.ca.santa_clara.{zone.lower()}.{capability}"
            if permission["rule_id"] != expected_rule_id:
                errors.append(f"{location}.rule_id must be {expected_rule_id}")
            expected_status = EXPECTED_USE_STATUS[zone][index]
            if permission["requirement"]["code"] != expected_status:
                errors.append(f"{location} must use source-matrix status {expected_status}")
            validate_source_refs(
                permission["requirement"]["source_refs"],
                citation_ids=citation_ids,
                location=f"{location}.requirement",
                errors=errors,
            )
            unknown_exceptions = set(permission["exception_family_ids"]) - exception_ids
            if unknown_exceptions:
                errors.append(
                    f"{location} has unknown exception families: {sorted(unknown_exceptions)}"
                )
            if permission["validation_status"] == "candidate_unverified" and permission[
                "approved_for_ruleset"
            ]:
                errors.append(f"{location} is approved while candidate_unverified")
            expected_pathway = (
                SPECIAL_PATHWAY_ID
                if zone in {"R1-6L", "R1-8L"}
                and capability == "use.two_family_dwelling"
                else None
            )
            if permission["special_pathway_id"] != expected_pathway:
                errors.append(f"{location}.special_pathway_id must be {expected_pathway!r}")
            rule_ids.append(permission["rule_id"])
            rules_by_id[permission["rule_id"]] = permission

        profiles = zone_record["analysis_profiles"]
        if set(profiles) != EXPECTED_PROFILES[zone]:
            errors.append(
                f"zones.{zone}.analysis_profiles must be {sorted(EXPECTED_PROFILES[zone])}"
            )
        for profile_id, profile in profiles.items():
            location = f"zones.{zone}.analysis_profiles.{profile_id}"
            expected_binding = PROFILE_BINDINGS[profile_id]
            for field, expected in expected_binding.items():
                if profile[field] != expected:
                    errors.append(f"{location}.{field} must be {expected}")
            regulations = profile["regulations"]
            if set(regulations) != PROFILE_CAPABILITIES:
                missing = PROFILE_CAPABILITIES - set(regulations)
                extra = set(regulations) - PROFILE_CAPABILITIES
                if missing:
                    errors.append(f"{location} is missing capabilities: {sorted(missing)}")
                if extra:
                    errors.append(f"{location} has unsupported capabilities: {sorted(extra)}")
            unknown_topics = set(profile["not_evaluated_topic_ids"]) - topic_ids
            if unknown_topics:
                errors.append(f"{location} has unknown not-evaluated topics: {sorted(unknown_topics)}")

            for capability, rule in regulations.items():
                rule_location = f"{location}.regulations.{capability}"
                expected_rule_id = (
                    f"us.ca.santa_clara.{zone.lower()}.{profile_id}.{capability}"
                )
                if rule["rule_id"] != expected_rule_id:
                    errors.append(f"{rule_location}.rule_id must be {expected_rule_id}")
                expected_context = EXPECTED_LOT_CONTEXT[capability]
                if rule["applicability"]["lot_context"] != expected_context:
                    errors.append(
                        f"{rule_location}.applicability.lot_context must be {expected_context}"
                    )
                unknown_exceptions = set(rule["exception_family_ids"]) - exception_ids
                if unknown_exceptions:
                    errors.append(
                        f"{rule_location} has unknown exception families: {sorted(unknown_exceptions)}"
                    )
                if rule["validation_status"] == "candidate_unverified" and rule[
                    "approved_for_ruleset"
                ]:
                    errors.append(f"{rule_location} is approved while candidate_unverified")
                validate_requirement(
                    capability,
                    rule["requirement"],
                    citation_ids=citation_ids,
                    location=f"{rule_location}.requirement",
                    errors=errors,
                )
                rule_ids.append(rule["rule_id"])
                rules_by_id[rule["rule_id"]] = rule

        pathways = zone_record["special_pathways"]
        expected_pathways = {SPECIAL_PATHWAY_ID} if zone in {"R1-6L", "R1-8L"} else set()
        if set(pathways) != expected_pathways:
            errors.append(f"zones.{zone}.special_pathways must be {sorted(expected_pathways)}")
        for pathway_id, pathway in pathways.items():
            path_location = f"zones.{zone}.special_pathways.{pathway_id}"
            unknown_topics = set(pathway["not_evaluated_topic_ids"]) - topic_ids
            if unknown_topics:
                errors.append(f"{path_location} has unknown topics: {sorted(unknown_topics)}")
            if not set(pathway["analysis_requirement"]["prerequisite_ids"]).issubset(topic_ids):
                errors.append(f"{path_location} has unknown analysis prerequisites")
            validate_source_refs(
                pathway["analysis_requirement"]["source_refs"],
                citation_ids=citation_ids,
                location=f"{path_location}.analysis_requirement",
                errors=errors,
            )

    duplicates = duplicate_values(rule_ids)
    if duplicates:
        errors.append(f"duplicate rule IDs: {sorted(duplicates)}")

    conflict_ids = set(ruleset["conflicts"])
    for conflict_id, conflict in ruleset["conflicts"].items():
        location = f"conflicts.{conflict_id}"
        unknown_affected = set(conflict["affected_rule_ids"]) - set(rule_ids)
        if unknown_affected:
            errors.append(f"{location} has unknown affected rules: {sorted(unknown_affected)}")
        assertion_ids = [a["assertion_id"] for a in conflict["assertions"]]
        duplicates = duplicate_values(assertion_ids)
        if duplicates:
            errors.append(f"{location} has duplicate assertion IDs: {sorted(duplicates)}")
        for index, assertion in enumerate(conflict["assertions"]):
            validate_source_refs(
                assertion["source_refs"],
                citation_ids=citation_ids,
                location=f"{location}.assertions[{index}]",
                errors=errors,
            )
        selected = [
            assertion
            for assertion in conflict["assertions"]
            if assertion["disposition"] == "selected_for_ruleset"
        ]
        resolution = conflict["resolution"]
        is_resolved = (
            resolution["status"] == "project_resolved_pending_official_clarification"
        )
        if is_resolved:
            if len(selected) != 1:
                errors.append(f"{location} must contain exactly one selected assertion")
            matching = [
                assertion
                for assertion in conflict["assertions"]
                if assertion["assertion_id"] == resolution["selected_assertion_id"]
            ]
            if len(matching) != 1:
                errors.append(f"{location} does not identify exactly one selected assertion")
            elif matching[0]["disposition"] != "selected_for_ruleset":
                errors.append(f"{location} selected assertion has the wrong disposition")
            elif matching[0]["value"] != resolution["selected_value"]:
                errors.append(f"{location} selected value differs from its assertion")
            if publication_date and date.fromisoformat(
                resolution["decision_date"]
            ) > publication_date:
                errors.append(f"{location} decision date is after ruleset publication")
        else:
            if selected:
                errors.append(f"{location} unresolved conflict selects an assertion")
            if any(
                assertion["disposition"] != "unresolved"
                for assertion in conflict["assertions"]
            ):
                errors.append(f"{location} unresolved assertions must use unresolved disposition")
        for affected_id in conflict["affected_rule_ids"]:
            affected_rule = rules_by_id.get(affected_id)
            if affected_rule is None:
                continue
            if affected_rule["conflict_id"] != conflict_id:
                errors.append(f"{location} is not linked back from {affected_id}")
            if is_resolved:
                if affected_rule["validation_status"] != "project_resolved_with_conditions":
                    errors.append(
                        f"{affected_id} must use project-resolved validation status"
                    )
                if operational_assertion_value(affected_rule) != resolution["selected_value"]:
                    errors.append(f"{location} selected value differs from {affected_id}")
            elif not (
                affected_rule["requirement"]["kind"] == "review_required"
                and affected_rule["requirement"]["reason_code"]
                == "unresolved_source_conflict"
            ):
                errors.append(
                    f"{affected_id} must return review_required for an unresolved conflict"
                )

    for zone, profile_id, capability, rule in iter_rules(ruleset):
        location = (
            f"zones.{zone}.use_permissions.{capability}"
            if profile_id is None
            else f"zones.{zone}.analysis_profiles.{profile_id}.regulations.{capability}"
        )
        conflict_id = rule["conflict_id"]
        if conflict_id is not None:
            if conflict_id not in conflict_ids:
                errors.append(f"{location} references unknown conflict {conflict_id}")
            elif rule["rule_id"] not in ruleset["conflicts"][conflict_id]["affected_rule_ids"]:
                errors.append(f"{location} conflict does not list the rule as affected")
        elif rule["validation_status"] == "project_resolved_with_conditions":
            errors.append(f"{location} has project-resolved status without a conflict")

    if ruleset["status"] == "candidate":
        approved_locations = [
            rule["rule_id"]
            for _, _, _, rule in iter_rules(ruleset)
            if rule["approved_for_ruleset"]
        ]
        approved_pathways = [
            f"{zone}.{pathway_id}"
            for zone, zone_record in zones.items()
            for pathway_id, pathway in zone_record["special_pathways"].items()
            if pathway["approved_for_ruleset"]
        ]
        if approved_locations or approved_pathways:
            errors.append("candidate ruleset contains records approved for the v3 ruleset")

    if require_runtime_eligible:
        if ruleset["status"] != "approved_for_runtime":
            errors.append("runtime eligibility requires status approved_for_runtime")
        if ruleset["approved_on"] is None:
            errors.append("runtime eligibility requires approved_on")
        unresolved_conflicts = [
            conflict_id
            for conflict_id, conflict in ruleset["conflicts"].items()
            if conflict["resolution"]["status"] == "review_required_unresolved"
        ]
        if unresolved_conflicts:
            errors.append(
                f"runtime ruleset has unresolved conflicts: {sorted(unresolved_conflicts)}"
            )
        unapproved_rules = [
            rule["rule_id"]
            for _, _, _, rule in iter_rules(ruleset)
            if not rule["approved_for_ruleset"]
        ]
        if unapproved_rules:
            errors.append(f"runtime ruleset has unapproved rules: {sorted(unapproved_rules)}")
        unapproved_pathways = [
            f"{zone}.{pathway_id}"
            for zone, zone_record in zones.items()
            for pathway_id, pathway in zone_record["special_pathways"].items()
            if not pathway["approved_for_ruleset"]
        ]
        if unapproved_pathways:
            errors.append(
                f"runtime ruleset has unapproved special pathways: {sorted(unapproved_pathways)}"
            )

    return errors


def main(argv: Optional[list[str]] = None) -> int:
    """Validate a v3 ruleset from the command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ruleset", type=Path, default=DEFAULT_RULESET)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--source-v2", type=Path, default=DEFAULT_SOURCE_V2)
    parser.add_argument("--gis-fixtures", type=Path, default=DEFAULT_GIS_FIXTURES)
    parser.add_argument("--verify-source-files", action="store_true")
    parser.add_argument("--require-runtime-eligible", action="store_true")
    args = parser.parse_args(argv)

    ruleset_path = args.ruleset.resolve()
    schema_path = args.schema.resolve()
    crosswalk_path = args.crosswalk.resolve()
    source_v2_path = args.source_v2.resolve()
    ruleset = load_json(ruleset_path)
    schema = load_json(schema_path)
    errors = validate_ruleset(
        ruleset,
        schema=schema,
        verify_source_files=args.verify_source_files,
        require_runtime_eligible=args.require_runtime_eligible,
    )
    from scripts.migrate_r1_rules_v3 import validate_migration

    errors.extend(
        validate_migration(
            load_json(source_v2_path),
            ruleset,
            load_json(crosswalk_path),
            source_path=source_v2_path,
            target_path=ruleset_path,
            schema_path=schema_path,
        )
    )
    errors.extend(validate_gis_fixture_contract(load_json(args.gis_fixtures)))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"Validated residential ruleset v3 and R1 migration: {args.ruleset} "
        f"(runtime eligibility required: {args.require_runtime_eligible})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
