#!/usr/bin/env python3
"""Author the nonruntime R1-R6 residential ruleset candidate.

The accepted R1-only v3.0 candidate is an immutable predecessor. This script
adds only the owner-approved R2-R6 citywide matrix, emits an additive v3.1
candidate in a new version directory, and records a checksum-pinned expansion
crosswalk. It never approves a rule or overwrites an existing candidate.
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Any, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.migrate_r1_rules_v3 import (  # noqa: E402
    json_bytes,
    load_json,
    relative_path,
    sha256_bytes,
    sha256_file,
)


DEFAULT_SOURCE = (
    REPO_ROOT / "rulesets/santa_clara/residential/2026-07-19.1/ruleset.json"
)
DEFAULT_SOURCE_SCHEMA = REPO_ROOT / "rulesets/schema/ruleset-v3.schema.json"
DEFAULT_SCHEMA = REPO_ROOT / "rulesets/schema/ruleset-v3.1.schema.json"
DEFAULT_VERSION = "2026-07-19.2"
DEFAULT_OUTPUT_DIR = REPO_ROOT / f"rulesets/santa_clara/residential/{DEFAULT_VERSION}"
DEFAULT_CROSSWALK_NAME = "citywide-expansion-crosswalk.json"

USE_CAPABILITIES = (
    "use.single_family_dwelling",
    "use.two_family_dwelling",
    "use.multifamily_dwelling",
)
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
CITYWIDE_ZONE_DATA: dict[str, dict[str, Any]] = {
    "R2": {
        "use_statuses": ("permitted_by_right", "permitted_by_right", "permitted_by_right"),
        "profiles": ("single_family", "two_family", "multifamily"),
        "height": 32,
        "stories": 2,
        "coverage": {"kind": "maximum", "number": 45},
        "front": 15,
        "street": 10,
        "interior": 5,
        "rear": {"base": 10, "multistory": 15},
    },
    "R3": {
        "use_statuses": ("not_listed", "permitted_by_right", "permitted_by_right"),
        "profiles": ("two_family", "multifamily"),
        "height": 40,
        "stories": 4,
        "coverage": {"kind": "tiered", "below": 60},
        "front": 10,
        "street": 10,
        "interior": 5,
        "rear": {"base": 10, "multistory": 15},
    },
    "R4": {
        "use_statuses": ("not_listed", "permitted_by_right", "permitted_by_right"),
        "profiles": ("two_family", "multifamily"),
        "height": 80,
        "stories": 8,
        "coverage": {"kind": "tiered", "below": 80},
        "front": 10,
        "street": 15,
        "interior": 10,
        "rear": {"base": 20},
    },
    "R5": {
        "use_statuses": ("not_listed", "not_listed", "permitted_by_right"),
        "profiles": ("multifamily",),
        "height": 100,
        "stories": 10,
        "coverage": {"kind": "no_maximum_listed"},
        "front": 10,
        "street": 15,
        "interior": 10,
        "rear": {"base": 20},
    },
    "R6": {
        "use_statuses": ("not_listed", "not_listed", "permitted_by_right"),
        "profiles": ("multifamily",),
        "height": 200,
        "stories": 20,
        "coverage": {"kind": "no_maximum_listed"},
        "front": 10,
        "street": 15,
        "interior": 10,
        "rear": {"base": 20},
    },
}


class CitywideAuthoringError(RuntimeError):
    """Raised when the accepted predecessor cannot be expanded exactly."""


def use_rule_id(zone: str, capability: str) -> str:
    """Return the zone-owned use-permission identity."""

    return f"us.ca.santa_clara.{zone.lower()}.{capability}"


def profile_rule_id(zone: str, profile: str, capability: str) -> str:
    """Return the profile-owned regulation identity."""

    return f"us.ca.santa_clara.{zone.lower()}.{profile}.{capability}"


def status_requirement(code: str, source_ref: str) -> dict[str, Any]:
    """Return a sourced status requirement."""

    return {"kind": "status", "code": code, "source_refs": [source_ref]}


def maximum_requirement(number: int, unit: str) -> dict[str, Any]:
    """Return a Table 2-3 numeric maximum."""

    return {
        "kind": "maximum_quantity",
        "value": {"number": number, "unit": unit},
        "source_refs": ["citywide-residential-standards-table"],
    }


def no_maximum_listed_requirement() -> dict[str, Any]:
    """Return the explicit source-table no-maximum-listed outcome."""

    return {
        "kind": "no_maximum_listed",
        "reason_code": "controlling_base_table_has_no_maximum",
        "explanation": (
            "Table 2-3 lists no base structure-coverage maximum for this lot-area tier. "
            "This is not a conclusion that every proposal has unlimited coverage."
        ),
        "source_refs": ["citywide-residential-standards-table"],
    }


def coverage_requirement(specification: dict[str, Any]) -> dict[str, Any]:
    """Return a universal or lot-area-tiered coverage requirement."""

    if specification["kind"] == "maximum":
        return maximum_requirement(specification["number"], "percent")
    if specification["kind"] == "no_maximum_listed":
        return no_maximum_listed_requirement()
    return {
        "kind": "lot_area_tiered_maximum",
        "threshold": {"number": 10000, "unit": "sq_ft"},
        "below_threshold": maximum_requirement(specification["below"], "percent"),
        "at_or_above_threshold": no_maximum_listed_requirement(),
    }


def setback_requirement(base: int, *, multistory: Optional[int] = None) -> dict[str, Any]:
    """Return a base setback and the source-table multistory replacement, if any."""

    requirement: dict[str, Any] = {
        "kind": "setback",
        "base": {
            "value": {"kind": "distance", "number": base, "unit": "ft"},
            "source_refs": ["citywide-residential-standards-table"],
        },
        "adjustments": [],
    }
    if multistory is not None:
        requirement["adjustments"] = [
            {
                "adjustment_id": "multistory-minimum",
                "trigger": {"kind": "story_at_or_above", "story": 2},
                "effect": {
                    "kind": "replace_total_minimum",
                    "value": {
                        "kind": "distance",
                        "number": multistory,
                        "unit": "ft",
                    },
                },
                "source_refs": ["citywide-residential-standards-table"],
            }
        ]
    return requirement


def regulation(
    zone: str,
    profile: str,
    capability: str,
    label: str,
    requirement: dict[str, Any],
    *,
    lot_context: str,
    conditions: list[str],
    exception_family_ids: list[str],
    validation_status: str = "verified_with_conditions",
) -> dict[str, Any]:
    """Return one nonapproved profile regulation."""

    return {
        "rule_id": profile_rule_id(zone, profile, capability),
        "label": label,
        "requirement": requirement,
        "applicability": {"lot_context": lot_context},
        "conditions": conditions,
        "exception_family_ids": exception_family_ids,
        "validation_status": validation_status,
        "conflict_id": None,
        "approved_for_ruleset": False,
    }


def use_permission(zone: str, capability: str, status: str) -> dict[str, Any]:
    """Return one explicit Table 2-1 use-permission cell."""

    labels = {
        "use.single_family_dwelling": "Single-family dwelling",
        "use.two_family_dwelling": "Two-family dwelling",
        "use.multifamily_dwelling": "Multifamily dwelling",
    }
    condition = (
        "Permitted by right does not mean approval-free construction."
        if status == "permitted_by_right"
        else (
            "Not listed records the controlling base-table cell and is not a "
            "prohibition conclusion."
        )
    )
    return {
        "rule_id": use_rule_id(zone, capability),
        "label": labels[capability],
        "requirement": status_requirement(status, "citywide-use-table"),
        "conditions": [condition],
        "exception_family_ids": [],
        "validation_status": "verified_base_value",
        "conflict_id": None,
        "special_pathway_id": None,
        "approved_for_ruleset": False,
    }


def profile_topics(zone: str, profile: str) -> list[str]:
    """Return the structured limitations applicable to one ordinary profile."""

    topics = [
        "citywide_proposal_specific_compliance",
        "citywide_buildable_envelope_geometry",
        "citywide_specific_plan_and_overlay_review",
    ]
    if profile in {"two_family", "multifamily"}:
        topics.append("citywide_density_and_state_law_overrides")
    if zone in {"R3", "R4", "R5", "R6"}:
        topics.append("citywide_r1_r2_height_transition")
    if profile == "multifamily":
        topics.append("objective_design_standards")
    return topics


def analysis_profile(zone: str, profile: str, data: dict[str, Any]) -> dict[str, Any]:
    """Return the nine selected regulations for one citywide profile."""

    height_conditions = [
        "This is the base-zone maximum outside any more restrictive applicable layer."
    ]
    if zone in {"R3", "R4", "R5", "R6"}:
        height_conditions.append(
            "The 32-foot transition within 20 feet of R1 or R2 is disclosed but not evaluated."
        )
    coverage_conditions = [
        "Coverage depends on the code definitions and projection rules identified as exceptions."
    ]
    if data["coverage"]["kind"] in {"tiered", "no_maximum_listed"}:
        coverage_conditions.append(
            "A no-maximum-listed tier is a source-table outcome, not an unlimited-project finding."
        )

    regulations = {
        "approval.zoning_clearance": regulation(
            zone,
            profile,
            "approval.zoning_clearance",
            "Zoning Clearance",
            status_requirement("required", "zoning-clearance"),
            lot_context="not_applicable",
            conditions=[
                "The permitted-use table requires Zoning Clearance for construction of a permitted use."
            ],
            exception_family_ids=[],
        ),
        "approval.architectural_review": regulation(
            zone,
            profile,
            "approval.architectural_review",
            "Architectural Review",
            status_requirement("required", "architectural-review"),
            lot_context="not_applicable",
            conditions=[
                "Automated classification of exemptions and Development Review Hearing triggers is not included."
            ],
            exception_family_ids=[],
        ),
        "standard.maximum_primary_structure_height": regulation(
            zone,
            profile,
            "standard.maximum_primary_structure_height",
            "Maximum primary-structure height",
            maximum_requirement(data["height"], "ft"),
            lot_context="all",
            conditions=height_conditions,
            exception_family_ids=["height-measurement-and-appurtenances-citywide"],
        ),
        "standard.maximum_stories": regulation(
            zone,
            profile,
            "standard.maximum_stories",
            "Maximum stories",
            maximum_requirement(data["stories"], "stories"),
            lot_context="all",
            conditions=["This is the Table 2-3 base-zone story maximum."],
            exception_family_ids=[],
            validation_status="verified_base_value",
        ),
        "standard.maximum_structure_coverage": regulation(
            zone,
            profile,
            "standard.maximum_structure_coverage",
            "Maximum structure coverage",
            coverage_requirement(data["coverage"]),
            lot_context="all",
            conditions=coverage_conditions,
            exception_family_ids=["coverage-definition-and-projections"],
        ),
        "setback.front": regulation(
            zone,
            profile,
            "setback.front",
            "Front setback",
            setback_requirement(data["front"]),
            lot_context="all",
            conditions=["Base-zone minimum before unevaluated measurement and exception rules."],
            exception_family_ids=[
                "setback-measurement-and-plan-lines-citywide",
                "front-setback-block-average",
                "setback-encroachments",
                "legal-nonconformities",
            ],
        ),
        "setback.interior_side": regulation(
            zone,
            profile,
            "setback.interior_side",
            "Interior-side setback",
            setback_requirement(data["interior"]),
            lot_context="all",
            conditions=["Base-zone minimum before unevaluated measurement and exception rules."],
            exception_family_ids=[
                "setback-measurement-and-plan-lines-citywide",
                "setback-encroachments",
                "legal-nonconformities",
            ],
        ),
        "setback.street_side": regulation(
            zone,
            profile,
            "setback.street_side",
            "Street-side (corner-side) setback",
            setback_requirement(data["street"]),
            lot_context="corner",
            conditions=["Applies to the street side of a corner lot."],
            exception_family_ids=[
                "setback-measurement-and-plan-lines-citywide",
                "setback-encroachments",
                "legal-nonconformities",
            ],
        ),
        "setback.rear": regulation(
            zone,
            profile,
            "setback.rear",
            "Rear setback",
            setback_requirement(
                data["rear"]["base"],
                multistory=data["rear"].get("multistory"),
            ),
            lot_context="all",
            conditions=[
                "The multistory replacement, where present, applies beginning with a two-story structure."
            ],
            exception_family_ids=[
                "setback-measurement-and-plan-lines-citywide",
                "alley-rear-setback-credit",
                "setback-encroachments",
                "legal-nonconformities",
            ],
        ),
    }
    return {
        **copy.deepcopy(PROFILE_BINDINGS[profile]),
        "regulations": regulations,
        "not_evaluated_topic_ids": profile_topics(zone, profile),
    }


def citywide_zone(zone: str, data: dict[str, Any]) -> dict[str, Any]:
    """Return one exact R2-R6 zone record."""

    permissions = {
        capability: use_permission(zone, capability, data["use_statuses"][index])
        for index, capability in enumerate(USE_CAPABILITIES)
    }
    profiles = {
        profile: analysis_profile(zone, profile, data) for profile in data["profiles"]
    }
    return {
        "label": zone,
        "use_permissions": permissions,
        "analysis_profiles": profiles,
        "special_pathways": {},
    }


def add_citywide_shared_records(shared: dict[str, Any]) -> None:
    """Add the verified source, citation, and exception records for R2-R6."""

    verification_path = REPO_ROOT / "docs/residential-rule-verification.md"
    ordinance_path = (
        REPO_ROOT
        / "data/raw/2026-07-16/santa_clara_zoning_code/amendments/Ordinance-2085-adopted.pdf"
    )
    shared["source_documents"]["residential-rule-verification-2026-07-19"] = {
        "title": "Santa Clara residential rule verification and approved source matrix",
        "version": "Owner-approved July 19, 2026",
        "effective_date": None,
        "local_path": relative_path(verification_path),
        "sha256": sha256_file(verification_path),
        "verification_status": "verified_source_matrix",
    }
    shared["source_documents"]["ordinance-2085-objective-design-standards"] = {
        "title": "Santa Clara Ordinance 2085 Objective Design Standards",
        "version": "Ordinance 2085",
        "effective_date": "2026-04-09",
        "local_path": relative_path(ordinance_path),
        "sha256": sha256_file(ordinance_path),
        "verification_status": "verified_enactment",
    }
    shared["citations"].update(
        {
            "citywide-use-table": {
                "source_document_id": "sc-title18-2025-07",
                "locator": "Section 18.10.020, Table 2-1",
                "topic": "R2-R6 residential use permissions",
            },
            "citywide-residential-standards-table": {
                "source_document_id": "sc-title18-2025-07",
                "locator": "Section 18.10.030, Table 2-3",
                "topic": "R2-R6 base residential development standards",
            },
            "citywide-r1-r2-height-transition": {
                "source_document_id": "sc-title18-2025-07",
                "locator": "Section 18.10.030, Table 2-3",
                "topic": "32-foot height transition within 20 feet of R1 or R2",
            },
            "objective-design-standards": {
                "source_document_id": "ordinance-2085-objective-design-standards",
                "locator": "Chapter 18.27 applicability provisions",
                "topic": "Objective Design Standards for multifamily development",
            },
            "citywide-expansion-verification": {
                "source_document_id": "residential-rule-verification-2026-07-19",
                "locator": "Approved rule and zone matrices and implementation boundary",
                "topic": "R2-R6 source dispositions and deferred analysis boundary",
            },
        }
    )
    shared["exception_families"].update(
        {
            "height-measurement-and-appurtenances-citywide": {
                "label": "Citywide grade measurement, roof form, and appurtenance rules",
                "treatment": "not_evaluated",
                "source_refs": [
                    "height-method",
                    "citywide-residential-standards-table",
                ],
            },
            "setback-measurement-and-plan-lines-citywide": {
                "label": "Citywide parcel-line, curb, right-of-way, and plan-line measurement",
                "treatment": "not_evaluated",
                "source_refs": [
                    "citywide-residential-standards-table",
                    "setback-method",
                ],
            },
        }
    )


def add_citywide_topics(topics: dict[str, Any]) -> None:
    """Add structured R2-R6 limitations without adding regulation families."""

    project_source = ["citywide-expansion-verification"]
    topics.update(
        {
            "citywide_proposal_specific_compliance": {
                "label": "Citywide proposal-specific compliance",
                "reason_code": "requires_unavailable_proposal_facts",
                "explanation": (
                    "The selected base standards do not determine compliance without exact "
                    "proposal dimensions, configuration, and project facts."
                ),
                "source_refs": project_source,
                "prerequisite_ids": [],
            },
            "citywide_buildable_envelope_geometry": {
                "label": "Citywide buildable-envelope geometry",
                "reason_code": "requires_unavailable_proposal_facts",
                "explanation": (
                    "The current product retrieves selected standards but does not construct "
                    "a parcel-specific three-dimensional buildable envelope."
                ),
                "source_refs": project_source,
                "prerequisite_ids": [],
            },
            "citywide_specific_plan_and_overlay_review": {
                "label": "Specific-plan and overlay review",
                "reason_code": "deferred_regulation_family",
                "explanation": (
                    "Specific plans, overlays, and parcel attributes may supply controlling "
                    "or additional standards and are not evaluated in this tranche."
                ),
                "source_refs": project_source,
                "prerequisite_ids": [],
            },
            "citywide_density_and_state_law_overrides": {
                "label": "Density and state-law overrides",
                "reason_code": "deferred_regulation_family",
                "explanation": (
                    "Density, density bonus, affordable-housing, and other state-law "
                    "adjustments remain outside the selected-standards evaluator."
                ),
                "source_refs": project_source,
                "prerequisite_ids": [],
            },
            "citywide_r1_r2_height_transition": {
                "label": "R1/R2 proximity height transition",
                "reason_code": "requires_unavailable_proposal_facts",
                "explanation": (
                    "Table 2-3 limits height to 32 feet within 20 feet of R1-6L, R1-8L, "
                    "or R2, but the product does not calculate adjacency and distance facts."
                ),
                "source_refs": ["citywide-r1-r2-height-transition"],
                "prerequisite_ids": [],
            },
            "objective_design_standards": {
                "label": "Objective Design Standards",
                "reason_code": "deferred_regulation_family",
                "explanation": (
                    "Ordinance 2085 applies an additional Objective Design Standards layer "
                    "to covered multifamily projects; its detailed standards are not evaluated."
                ),
                "source_refs": [
                    "objective-design-standards",
                    "residential-amendment-audit",
                ],
                "prerequisite_ids": [],
            },
        }
    )


def expand_ruleset(
    source: dict[str, Any],
    *,
    source_path: Path = DEFAULT_SOURCE,
    version: str = DEFAULT_VERSION,
    crosswalk_path: str = (
        "rulesets/santa_clara/residential/2026-07-19.2/"
        "citywide-expansion-crosswalk.json"
    ),
) -> dict[str, Any]:
    """Return the deterministic candidate containing the preserved R1 and new R2-R6 data."""

    if source.get("schema_version") != "3.0.0":
        raise CitywideAuthoringError("Source candidate is not schema v3.0.0")
    if source.get("ruleset_id") != "santa-clara-residential-zoning":
        raise CitywideAuthoringError("Source candidate has the wrong ruleset identity")
    if source.get("status") != "candidate" or source.get("approved_on") is not None:
        raise CitywideAuthoringError("Source candidate must remain nonruntime and unapproved")
    if set(source.get("zones", {})) != {"R1-6L", "R1-8L"}:
        raise CitywideAuthoringError("Source candidate must contain exactly the accepted R1 zones")

    candidate = copy.deepcopy(source)
    candidate["$schema"] = "../../../schema/ruleset-v3.1.schema.json"
    candidate["schema_version"] = "3.1.0"
    candidate["version"] = version
    candidate["scope"]["description"] = (
        "Candidate selected residential standards contract containing the accepted R1 "
        "migration and the owner-approved R2-R6 citywide tranche; Patrick Henry zones "
        "remain intentionally unauthored."
    )
    candidate["predecessor_rulesets"] = [
        {
            "ruleset_id": source["ruleset_id"],
            "version": source["version"],
            "sha256": sha256_file(source_path),
            "crosswalk_path": crosswalk_path,
        }
    ]
    add_citywide_shared_records(candidate["shared"])
    add_citywide_topics(candidate["not_evaluated_topics"])
    for zone, data in CITYWIDE_ZONE_DATA.items():
        candidate["zones"][zone] = citywide_zone(zone, data)
    return candidate


def component_hash(value: dict[str, Any]) -> str:
    """Return a canonical hash for one preserved JSON component."""

    return sha256_bytes(json_bytes(value))


def build_crosswalk(
    *,
    source: dict[str, Any],
    source_path: Path,
    target: dict[str, Any],
    target_path: Path,
    schema_path: Path,
    target_bytes: bytes,
) -> dict[str, Any]:
    """Build the checksum-pinned v3.0-to-v3.1 citywide expansion crosswalk."""

    source_rule_count = sum(
        len(zone["use_permissions"])
        + sum(len(profile["regulations"]) for profile in zone["analysis_profiles"].values())
        for zone in source["zones"].values()
    )
    target_rule_count = sum(
        len(zone["use_permissions"])
        + sum(len(profile["regulations"]) for profile in zone["analysis_profiles"].values())
        for zone in target["zones"].values()
    )
    return {
        "crosswalk_version": "1.0.0",
        "migration_id": "santa-clara-residential-v3-r1-to-citywide-r1-r6",
        "generated_on": target["version"].split(".", 1)[0],
        "migration_status": "candidate_contract_validated",
        "source_ruleset": {
            "path": relative_path(source_path),
            "ruleset_id": source["ruleset_id"],
            "version": source["version"],
            "schema_version": source["schema_version"],
            "status": source["status"],
            "sha256": sha256_file(source_path),
        },
        "target_ruleset": {
            "path": relative_path(target_path),
            "ruleset_id": target["ruleset_id"],
            "version": target["version"],
            "schema_version": target["schema_version"],
            "status": target["status"],
            "sha256": sha256_bytes(target_bytes),
        },
        "target_schema": {
            "path": relative_path(schema_path),
            "sha256": sha256_file(schema_path),
        },
        "counts": {
            "source_zones": len(source["zones"]),
            "target_zones": len(target["zones"]),
            "carried_source_rules": source_rule_count,
            "target_rules": target_rule_count,
            "added_use_permissions": 15,
            "added_analysis_profiles": 9,
            "added_profile_regulations": 81,
            "added_not_evaluated_topics": 6,
            "carried_conflicts": len(source["conflicts"]),
        },
        "preserved_components": [
            {
                "component_path": f"zones.{zone}",
                "sha256": component_hash(source["zones"][zone]),
            }
            for zone in source["zones"]
        ]
        + [
            {
                "component_path": "conflicts",
                "sha256": component_hash(source["conflicts"]),
            },
            {
                "component_path": "jurisdiction",
                "sha256": component_hash(source["jurisdiction"]),
            },
        ],
        "added_zone_profiles": {
            zone: list(data["profiles"]) for zone, data in CITYWIDE_ZONE_DATA.items()
        },
        "allowed_ruleset_changes": [
            "Advance the closed authoring contract from schema 3.0.0 to additive schema 3.1.0.",
            "Add the exact R2-R6 zones, use permissions, ordinary profiles, and selected standards.",
            "Add a lot-area-tiered shape within maximum structure coverage for R3 and R4.",
            "Add verified citywide sources, citations, exception disclosures, and not-evaluated topics.",
            "Retain candidate status, null approval, and false rule approvals pending the full target matrix.",
        ],
    }


def validate_expansion(
    source: dict[str, Any],
    target: dict[str, Any],
    crosswalk: dict[str, Any],
    *,
    source_path: Path = DEFAULT_SOURCE,
    target_path: Path = DEFAULT_OUTPUT_DIR / "ruleset.json",
    schema_path: Path = DEFAULT_SCHEMA,
) -> list[str]:
    """Return lineage, preservation, checksum, count, and replay errors."""

    errors: list[str] = []
    if crosswalk.get("migration_id") != "santa-clara-residential-v3-r1-to-citywide-r1-r6":
        errors.append("migration_id is unsupported")
    for record_name, expected_path in (
        ("source_ruleset", source_path),
        ("target_ruleset", target_path),
        ("target_schema", schema_path),
    ):
        record = crosswalk.get(record_name)
        if not isinstance(record, dict):
            errors.append(f"{record_name} must be an object")
            continue
        if record.get("path") != relative_path(expected_path):
            errors.append(f"{record_name}.path does not match the validated artifact")
        if not expected_path.is_file():
            errors.append(f"{record_name} artifact is missing: {expected_path}")
        elif record.get("sha256") != sha256_file(expected_path):
            errors.append(f"{record_name}.sha256 does not match its artifact")

    predecessor = target.get("predecessor_rulesets", [{}])[0]
    if predecessor.get("ruleset_id") != source.get("ruleset_id"):
        errors.append("target predecessor ruleset identity does not match")
    if predecessor.get("version") != source.get("version"):
        errors.append("target predecessor version does not match")
    if predecessor.get("sha256") != sha256_file(source_path):
        errors.append("target predecessor checksum does not match")

    for zone in source["zones"]:
        if target["zones"].get(zone) != source["zones"][zone]:
            errors.append(f"target changed preserved predecessor zone {zone}")
    if target.get("conflicts") != source.get("conflicts"):
        errors.append("target changed preserved predecessor conflicts")
    for topic_id, topic in source["not_evaluated_topics"].items():
        if target["not_evaluated_topics"].get(topic_id) != topic:
            errors.append(f"target changed predecessor topic {topic_id}")
    for shared_group in ("source_documents", "citations", "definitions", "exception_families"):
        for record_id, record in source["shared"][shared_group].items():
            if target["shared"][shared_group].get(record_id) != record:
                errors.append(f"target changed shared predecessor record {shared_group}.{record_id}")

    expected_zones = set(source["zones"]) | set(CITYWIDE_ZONE_DATA)
    if set(target.get("zones", {})) != expected_zones:
        errors.append("target does not contain exactly the predecessor and R2-R6 zones")
    expected_profiles = {
        zone: list(data["profiles"]) for zone, data in CITYWIDE_ZONE_DATA.items()
    }
    if crosswalk.get("added_zone_profiles") != expected_profiles:
        errors.append("added_zone_profiles does not match the approved citywide matrix")

    crosswalk_path = target["predecessor_rulesets"][0]["crosswalk_path"]
    reproduced = expand_ruleset(
        source,
        source_path=source_path,
        version=target["version"],
        crosswalk_path=crosswalk_path,
    )
    if reproduced != target:
        errors.append("target ruleset differs from deterministic citywide authoring replay")
    reproduced_crosswalk = build_crosswalk(
        source=source,
        source_path=source_path,
        target=target,
        target_path=target_path,
        schema_path=schema_path,
        target_bytes=json_bytes(target),
    )
    if reproduced_crosswalk != crosswalk:
        errors.append("crosswalk differs from deterministic citywide authoring replay")
    return errors


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse authoring command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--source-schema", type=Path, default=DEFAULT_SOURCE_SCHEMA)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Validate the accepted predecessor and write a new citywide candidate."""

    args = parse_args(argv)
    source_path = args.source.resolve()
    source_schema_path = args.source_schema.resolve()
    schema_path = args.schema.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise CitywideAuthoringError(
            f"Destination already exists; choose a new version directory: {output_dir}"
        )

    source = load_json(source_path)
    from scripts.validate_residential_rules_v3 import validate_ruleset

    source_errors = validate_ruleset(
        source,
        schema=load_json(source_schema_path),
        verify_source_files=True,
    )
    if source_errors:
        raise CitywideAuthoringError(
            "Accepted predecessor failed validation:\n" + "\n".join(source_errors)
        )

    crosswalk_relative = relative_path(output_dir / DEFAULT_CROSSWALK_NAME)
    target = expand_ruleset(
        source,
        source_path=source_path,
        version=args.version,
        crosswalk_path=crosswalk_relative,
    )
    target_errors = validate_ruleset(
        target,
        schema=load_json(schema_path),
        verify_source_files=False,
    )
    if target_errors:
        raise CitywideAuthoringError(
            "Authored target failed validation:\n" + "\n".join(target_errors)
        )

    target_path = output_dir / "ruleset.json"
    target_bytes = json_bytes(target)
    crosswalk = build_crosswalk(
        source=source,
        source_path=source_path,
        target=target,
        target_path=target_path,
        schema_path=schema_path,
        target_bytes=target_bytes,
    )
    output_dir.mkdir(parents=True)
    target_path.write_bytes(target_bytes)
    crosswalk_path = output_dir / DEFAULT_CROSSWALK_NAME
    crosswalk_path.write_bytes(json_bytes(crosswalk))
    errors = validate_expansion(
        source,
        target,
        crosswalk,
        source_path=source_path,
        target_path=target_path,
        schema_path=schema_path,
    )
    if errors:
        raise CitywideAuthoringError(
            "Written expansion failed replay validation:\n" + "\n".join(errors)
        )
    print(f"Authored nonruntime R1-R6 candidate: {target_path}")
    print(f"Expansion crosswalk: {crosswalk_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
