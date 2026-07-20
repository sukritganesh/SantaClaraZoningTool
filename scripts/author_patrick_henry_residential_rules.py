#!/usr/bin/env python3
"""Author the nonruntime Patrick Henry residential ruleset successor.

Candidate 2026-07-19.3 is an immutable R1-R6 predecessor. This deterministic,
non-overwriting author adds the five source-approved Patrick Henry residential
designations, their multifamily profiles, and the retained PH-R5 density
conflict without changing the schema or approving any record for runtime use.
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
    REPO_ROOT / "rulesets/santa_clara/residential/2026-07-19.3/ruleset.json"
)
DEFAULT_SOURCE_SCHEMA = REPO_ROOT / "rulesets/schema/ruleset-v3.2.schema.json"
DEFAULT_SCHEMA = DEFAULT_SOURCE_SCHEMA
DEFAULT_VERSION = "2026-07-19.4"
DEFAULT_OUTPUT_DIR = REPO_ROOT / f"rulesets/santa_clara/residential/{DEFAULT_VERSION}"
DEFAULT_CROSSWALK_NAME = "patrick-henry-expansion-crosswalk.json"

USE_CAPABILITIES = (
    "use.single_family_dwelling",
    "use.two_family_dwelling",
    "use.multifamily_dwelling",
)
PROFILE_BINDING = {
    "workflow_family": "multifamily",
    "legal_use_capability_id": "use.multifamily_dwelling",
    "primary_structure_type": "multifamily_primary_structure",
}
DENSITY_CAPABILITY = "standard.gross_residential_density"
PH_R5_CONFLICT_ID = "conflict-ph-r5-gross-residential-density"
PATRICK_HENRY_ZONE_DATA: dict[str, dict[str, Any]] = {
    "PH-R5": {
        "label": "Patrick Henry Very-High-Density Residential (PH-R5)",
        "height": 135,
        "stories": 10,
        "density": (51, 100),
    },
    "UV": {
        "label": "Urban Village (UV)",
        "height": 160,
        "stories": 12,
        "density": (100, 149),
    },
    "VR": {
        "label": "Village Residential (VR)",
        "height": 160,
        "stories": 12,
        "density": (60, 149),
    },
    "UC": {
        "label": "Urban Center (UC)",
        "height": "FAA",
        "stories": "FAA",
        "density": (120, 250),
    },
    "HDF": {
        "label": "High-Density Flex (HDF)",
        "height": 160,
        "stories": 12,
        "density": (60, 149),
    },
}


class PatrickHenryAuthoringError(RuntimeError):
    """Raised when the density predecessor cannot be expanded exactly."""


def use_rule_id(zone: str, capability: str) -> str:
    """Return one zone-owned use-permission identity."""

    return f"us.ca.santa_clara.{zone.lower()}.{capability}"


def profile_rule_id(zone: str, capability: str) -> str:
    """Return one Patrick Henry multifamily profile-owned identity."""

    return f"us.ca.santa_clara.{zone.lower()}.multifamily.{capability}"


def status_requirement(code: str, source_refs: list[str]) -> dict[str, Any]:
    """Return a sourced status requirement."""

    return {"kind": "status", "code": code, "source_refs": source_refs}


def maximum_requirement(number: int, unit: str) -> dict[str, Any]:
    """Return a numeric Patrick Henry maximum."""

    return {
        "kind": "maximum_quantity",
        "value": {"number": number, "unit": unit},
        "source_refs": [
            "patrick-henry-title18-standards-table",
            "patrick-henry-plan-standards-table",
            "patrick-henry-authoring-verification",
        ],
    }


def faa_controlled_requirement() -> dict[str, Any]:
    """Return the literal UC FAA-controlled source disposition."""

    return {
        "kind": "faa_controlled",
        "controlling_authority": "FAA",
        "reason_code": "controlling_source_defers_to_faa",
        "explanation": (
            "Title 18 Table 2-4 and Specific Plan Table 4.2 state FAA instead of "
            "a universal local numeric maximum."
        ),
        "source_refs": [
            "patrick-henry-title18-standards-table",
            "patrick-henry-plan-standards-table",
            "patrick-henry-authoring-verification",
        ],
    }


def no_maximum_listed_requirement() -> dict[str, Any]:
    """Return the explicit Patrick Henry no-coverage-maximum outcome."""

    return {
        "kind": "no_maximum_listed",
        "reason_code": "controlling_base_table_has_no_maximum",
        "explanation": (
            "Title 18 Table 2-4 and Specific Plan Table 4.2 list no base "
            "structure-coverage maximum. This is not an unlimited-project conclusion."
        ),
        "source_refs": [
            "patrick-henry-title18-standards-table",
            "patrick-henry-plan-standards-table",
            "patrick-henry-authoring-verification",
        ],
    }


def setback_requirement() -> dict[str, Any]:
    """Return the 10-foot residential setback measured from back of walk."""

    return {
        "kind": "setback",
        "base": {
            "value": {"kind": "distance", "number": 10, "unit": "ft"},
            "source_refs": [
                "patrick-henry-title18-standards-table",
                "patrick-henry-plan-standards-table",
            ],
        },
        "adjustments": [],
    }


def rear_plan_dependent_requirement() -> dict[str, Any]:
    """Return the verified absence of a universal Patrick Henry rear value."""

    return {
        "kind": "plan_dependent",
        "reason_code": "controlling_source_requires_plan_or_project_review",
        "explanation": (
            "Neither controlling development-standards table supplies a rear-setback "
            "row, and the plan supplies no universal numeric rear value. Zero is not "
            "a valid fallback."
        ),
        "source_refs": [
            "patrick-henry-title18-standards-table",
            "patrick-henry-plan-standards-table",
            "patrick-henry-plan-setback-guidance",
            "patrick-henry-authoring-verification",
        ],
        "required_sources_or_facts": [
            "Applicable PDO, development plan, or project approval",
            "Parcel and proposal configuration",
            "Any project-specific setback or substantial-conformance determination",
        ],
    }


def density_range_requirement(zone: str) -> dict[str, Any]:
    """Return one verified base gross-density range."""

    minimum, maximum = PATRICK_HENRY_ZONE_DATA[zone]["density"]
    return {
        "kind": "quantity_range",
        "minimum": minimum,
        "maximum": maximum,
        "unit": "dwelling_units_per_acre",
        "source_refs": [
            "residential-density-table-1-1",
            "patrick-henry-title18-zone-purpose",
            "patrick-henry-title18-standards-table",
            "patrick-henry-plan-classifications",
            "patrick-henry-plan-standards-table",
            "residential-density-plan-control",
            "patrick-henry-authoring-verification",
            "residential-amendment-audit",
        ],
    }


def regulation(
    zone: str,
    capability: str,
    label: str,
    requirement: dict[str, Any],
    *,
    lot_context: str,
    conditions: list[str],
    exception_family_ids: list[str],
    validation_status: str = "verified_with_conditions",
    conflict_id: Optional[str] = None,
) -> dict[str, Any]:
    """Return one nonapproved Patrick Henry multifamily regulation."""

    return {
        "rule_id": profile_rule_id(zone, capability),
        "label": label,
        "requirement": requirement,
        "applicability": {"lot_context": lot_context},
        "conditions": conditions,
        "exception_family_ids": exception_family_ids,
        "validation_status": validation_status,
        "conflict_id": conflict_id,
        "approved_for_ruleset": False,
    }


def use_permission(zone: str, capability: str, status: str) -> dict[str, Any]:
    """Return one explicit Patrick Henry residential-use cell."""

    labels = {
        "use.single_family_dwelling": "Single-family dwelling",
        "use.two_family_dwelling": "Two-family dwelling",
        "use.multifamily_dwelling": "Multifamily dwelling",
    }
    condition = (
        "Permitted by right does not mean approval-free construction or plan conformance."
        if status == "permitted_by_right"
        else (
            "Not listed records the controlling residential table treatment and is not "
            "a complete prohibition or nonconforming-use conclusion."
        )
    )
    return {
        "rule_id": use_rule_id(zone, capability),
        "label": labels[capability],
        "requirement": status_requirement(
            status,
            [
                "patrick-henry-title18-use-table",
                "patrick-henry-plan-use-table",
                "patrick-henry-authoring-verification",
            ],
        ),
        "conditions": [condition],
        "exception_family_ids": [],
        "validation_status": "verified_base_value",
        "conflict_id": None,
        "special_pathway_id": None,
        "approved_for_ruleset": False,
    }


def profile_topics(zone: str) -> list[str]:
    """Return the structured qualifications for one Patrick Henry profile."""

    topics = [
        "patrick_henry_proposal_specific_compliance",
        "patrick_henry_buildable_envelope_geometry",
        "patrick_henry_r1_r2_height_transition",
        "patrick_henry_recreation_space_and_encroachments",
        "patrick_henry_design_guidelines_and_project_review",
        "patrick_henry_density_adjustments_and_state_law",
        "objective_design_standards",
    ]
    if zone == "UC":
        topics.append("patrick_henry_uc_community_benefits_density_path")
    if zone == "HDF":
        topics.append("patrick_henry_hdf_nonresidential_option")
    return topics


def analysis_profile(zone: str, data: dict[str, Any]) -> dict[str, Any]:
    """Return the ten supported regulations for one multifamily profile."""

    height_requirement = (
        faa_controlled_requirement()
        if data["height"] == "FAA"
        else maximum_requirement(data["height"], "ft")
    )
    stories_requirement = (
        faa_controlled_requirement()
        if data["stories"] == "FAA"
        else maximum_requirement(data["stories"], "stories")
    )
    density_conditions = [
        "This is a base-zone gross density range, not a parcel unit-yield calculation.",
        (
            "General Plan, Specific Plan, development-agreement, density-bonus, "
            "affordable-housing, and state-law adjustments are not evaluated."
        ),
    ]
    if zone == "PH-R5":
        density_conditions.append(
            "The project-selected Table 1-1 range retains a source conflict and is "
            "not an official City correction."
        )
    if zone == "UC":
        density_conditions.append(
            "The possible above-250 DU/AC community-benefits path requires a "
            "development agreement and is not evaluated."
        )

    regulations = {
        "approval.zoning_clearance": regulation(
            zone,
            "approval.zoning_clearance",
            "Zoning Clearance",
            status_requirement(
                "required",
                ["zoning-clearance", "patrick-henry-title18-use-table"],
            ),
            lot_context="not_applicable",
            conditions=[
                "Construction associated with a permitted residential use requires "
                "Zoning Clearance."
            ],
            exception_family_ids=[],
        ),
        "approval.architectural_review": regulation(
            zone,
            "approval.architectural_review",
            "Architectural Review",
            status_requirement(
                "required",
                ["architectural-review", "patrick-henry-plan-implementation"],
            ),
            lot_context="not_applicable",
            conditions=[
                "New multifamily development may require a Development Review Hearing "
                "and must satisfy applicable plan review; detailed triggers are not evaluated."
            ],
            exception_family_ids=[],
        ),
        "standard.maximum_primary_structure_height": regulation(
            zone,
            "standard.maximum_primary_structure_height",
            "Maximum primary-structure height",
            height_requirement,
            lot_context="all",
            conditions=[
                "This is the base result outside the unevaluated 32-foot R1/R2 "
                "proximity transition."
            ],
            exception_family_ids=[
                "patrick-henry-height-measurement-transition-and-airport-controls"
            ],
            validation_status=(
                "verified_with_conditions"
                if data["height"] == "FAA"
                else "verified_base_value"
            ),
        ),
        "standard.maximum_stories": regulation(
            zone,
            "standard.maximum_stories",
            "Maximum stories",
            stories_requirement,
            lot_context="all",
            conditions=[
                "This is the controlling table's base story result; automated level "
                "classification is not evaluated."
            ],
            exception_family_ids=[],
            validation_status=(
                "verified_with_conditions"
                if data["stories"] == "FAA"
                else "verified_base_value"
            ),
        ),
        "standard.maximum_structure_coverage": regulation(
            zone,
            "standard.maximum_structure_coverage",
            "Maximum structure coverage",
            no_maximum_listed_requirement(),
            lot_context="all",
            conditions=[
                "The source-table outcome does not eliminate other plan, design, or "
                "proposal constraints."
            ],
            exception_family_ids=["coverage-definition-and-projections"],
        ),
        DENSITY_CAPABILITY: regulation(
            zone,
            DENSITY_CAPABILITY,
            "Gross residential density",
            density_range_requirement(zone),
            lot_context="all",
            conditions=density_conditions,
            exception_family_ids=[],
            validation_status=(
                "project_resolved_with_conditions"
                if zone == "PH-R5"
                else "verified_with_conditions"
            ),
            conflict_id=PH_R5_CONFLICT_ID if zone == "PH-R5" else None,
        ),
        "setback.front": regulation(
            zone,
            "setback.front",
            "Front setback",
            setback_requirement(),
            lot_context="all",
            conditions=[
                "The residential minimum is measured from the back of walk; detailed "
                "plan and project conditions are not evaluated."
            ],
            exception_family_ids=[
                "patrick-henry-setback-measurement-and-encroachments"
            ],
        ),
        "setback.interior_side": regulation(
            zone,
            "setback.interior_side",
            "Interior-side setback",
            setback_requirement(),
            lot_context="all",
            conditions=[
                "The residential minimum is measured from the back of walk; detailed "
                "plan and project conditions are not evaluated."
            ],
            exception_family_ids=[
                "patrick-henry-setback-measurement-and-encroachments"
            ],
        ),
        "setback.street_side": regulation(
            zone,
            "setback.street_side",
            "Street-side (corner-side) setback",
            setback_requirement(),
            lot_context="corner",
            conditions=[
                "Applies to the residential corner-side setback measured from the back of walk."
            ],
            exception_family_ids=[
                "patrick-henry-setback-measurement-and-encroachments"
            ],
        ),
        "setback.rear": regulation(
            zone,
            "setback.rear",
            "Rear setback",
            rear_plan_dependent_requirement(),
            lot_context="all",
            conditions=[
                "Plan and project review is required; the product does not display "
                "zero or invent a base rear value."
            ],
            exception_family_ids=[
                "patrick-henry-setback-measurement-and-encroachments"
            ],
        ),
    }
    return {
        **copy.deepcopy(PROFILE_BINDING),
        "regulations": regulations,
        "not_evaluated_topic_ids": profile_topics(zone),
    }


def patrick_henry_zone(zone: str, data: dict[str, Any]) -> dict[str, Any]:
    """Return one exact Patrick Henry residential zone record."""

    statuses = ("not_listed", "not_listed", "permitted_by_right")
    return {
        "label": data["label"],
        "use_permissions": {
            capability: use_permission(zone, capability, statuses[index])
            for index, capability in enumerate(USE_CAPABILITIES)
        },
        "analysis_profiles": {"multifamily": analysis_profile(zone, data)},
        "special_pathways": {},
    }


def add_shared_records(shared: dict[str, Any]) -> None:
    """Add checksum-pinned Patrick Henry sources, citations, and exceptions."""

    plan_path = (
        REPO_ROOT
        / "data/raw/2026-07-18/patrick_henry_drive_specific_plan/PatrickHenryPlan.pdf"
    )
    verification_path = (
        REPO_ROOT / "docs/patrick-henry-rule-verification-supplement.md"
    )
    shared["source_documents"].update(
        {
            "patrick-henry-plan-2022-03": {
                "title": "Patrick Henry Drive Final Adopted Focus Area Plan",
                "version": "March 2022",
                "effective_date": "2022-03-22",
                "local_path": relative_path(plan_path),
                "sha256": sha256_file(plan_path),
                "verification_status": "verified_baseline",
            },
            "patrick-henry-authoring-verification-2026-07-19": {
                "title": "Patrick Henry residential rule verification supplement",
                "version": "Project-owner decision July 19, 2026",
                "effective_date": None,
                "local_path": relative_path(verification_path),
                "sha256": sha256_file(verification_path),
                "verification_status": "verified_source_matrix",
            },
        }
    )
    shared["citations"].update(
        {
            "patrick-henry-title18-use-table": {
                "source_document_id": "sc-title18-2025-07",
                "locator": (
                    "Section 18.10.020, Table 2-2, PDF page 23 / printed page 2-5"
                ),
                "topic": "Patrick Henry residential use permissions",
            },
            "patrick-henry-title18-standards-table": {
                "source_document_id": "sc-title18-2025-07",
                "locator": (
                    "Section 18.10.030, Table 2-4, PDF page 27 / printed page 2-9"
                ),
                "topic": "Patrick Henry residential development standards",
            },
            "patrick-henry-title18-zone-purpose": {
                "source_document_id": "sc-title18-2025-07",
                "locator": "Section 18.10.010, PDF page 20 / printed page 2-2",
                "topic": "Patrick Henry zone purposes and gross-density ranges",
            },
            "patrick-henry-plan-classifications": {
                "source_document_id": "patrick-henry-plan-2022-03",
                "locator": (
                    "Section 4.3.2, PDF pages 58, 60, and 62 / printed pages "
                    "52, 54, and 56"
                ),
                "topic": "Patrick Henry land-use classifications and residential densities",
            },
            "patrick-henry-plan-standards-table": {
                "source_document_id": "patrick-henry-plan-2022-03",
                "locator": "Table 4.2, PDF page 63 / printed page 57",
                "topic": "Patrick Henry residential development standards",
            },
            "patrick-henry-plan-use-table": {
                "source_document_id": "patrick-henry-plan-2022-03",
                "locator": "Table 4.3, PDF pages 64-65 / printed pages 58-59",
                "topic": "Patrick Henry residential uses and permit requirements",
            },
            "patrick-henry-plan-setback-guidance": {
                "source_document_id": "patrick-henry-plan-2022-03",
                "locator": "Section 5.5.3, PDF pages 148-150 / printed pages 142-144",
                "topic": "Patrick Henry frontage, setback, and service-access guidance",
            },
            "patrick-henry-plan-implementation": {
                "source_document_id": "patrick-henry-plan-2022-03",
                "locator": "Section 7.1, PDF pages 179-180 / printed pages 173-174",
                "topic": "Patrick Henry regulatory implementation and project review",
            },
            "patrick-henry-authoring-verification": {
                "source_document_id": "patrick-henry-authoring-verification-2026-07-19",
                "locator": (
                    "Source matrix, PH-R5 conflict resolution, and approval boundary"
                ),
                "topic": "Patrick Henry authoring evidence and project decisions",
            },
        }
    )
    shared["exception_families"].update(
        {
            "patrick-henry-height-measurement-transition-and-airport-controls": {
                "label": (
                    "Patrick Henry height measurement, R1/R2 transition, and "
                    "airport controls"
                ),
                "treatment": "not_evaluated",
                "source_refs": [
                    "patrick-henry-title18-standards-table",
                    "patrick-henry-plan-standards-table",
                    "patrick-henry-authoring-verification",
                ],
            },
            "patrick-henry-setback-measurement-and-encroachments": {
                "label": (
                    "Patrick Henry setback measurement, encroachments, and "
                    "project conditions"
                ),
                "treatment": "not_evaluated",
                "source_refs": [
                    "patrick-henry-title18-standards-table",
                    "patrick-henry-plan-standards-table",
                    "patrick-henry-plan-setback-guidance",
                ],
            },
        }
    )


def add_topics(topics: dict[str, Any]) -> None:
    """Add structured Patrick Henry limitations without adding capabilities."""

    verification_ref = ["patrick-henry-authoring-verification"]
    topics.update(
        {
            "patrick_henry_proposal_specific_compliance": {
                "label": "Patrick Henry proposal-specific compliance",
                "reason_code": "requires_unavailable_proposal_facts",
                "explanation": (
                    "The selected base standards do not decide compliance without exact "
                    "proposal dimensions, configuration, approvals, and project facts."
                ),
                "source_refs": verification_ref,
                "prerequisite_ids": [],
            },
            "patrick_henry_buildable_envelope_geometry": {
                "label": "Patrick Henry buildable-envelope geometry",
                "reason_code": "requires_unavailable_proposal_facts",
                "explanation": (
                    "The product retrieves selected plan standards but does not construct a "
                    "parcel-specific three-dimensional building envelope."
                ),
                "source_refs": verification_ref,
                "prerequisite_ids": [],
            },
            "patrick_henry_r1_r2_height_transition": {
                "label": "Patrick Henry R1/R2 proximity height transition",
                "reason_code": "requires_unavailable_proposal_facts",
                "explanation": (
                    "The controlling tables limit height to 32 feet within 20 feet of an R1 "
                    "or R2 zone, but adjacency and distance are not calculated."
                ),
                "source_refs": [
                    "patrick-henry-title18-standards-table",
                    "patrick-henry-plan-standards-table",
                ],
                "prerequisite_ids": [],
            },
            "patrick_henry_recreation_space_and_encroachments": {
                "label": "Patrick Henry recreation space and setback encroachments",
                "reason_code": "deferred_regulation_family",
                "explanation": (
                    "Recreation-space requirements and detailed setback-encroachment rules "
                    "remain outside the supported regulation map."
                ),
                "source_refs": [
                    "patrick-henry-title18-standards-table",
                    "patrick-henry-plan-standards-table",
                    "patrick-henry-plan-setback-guidance",
                ],
                "prerequisite_ids": [],
            },
            "patrick_henry_design_guidelines_and_project_review": {
                "label": "Patrick Henry design guidelines and project review",
                "reason_code": "deferred_regulation_family",
                "explanation": (
                    "Plan design guidelines, substantial-conformance review, PDOs, and "
                    "project-specific approval conditions are not evaluated."
                ),
                "source_refs": ["patrick-henry-plan-implementation"],
                "prerequisite_ids": [],
            },
            "patrick_henry_density_adjustments_and_state_law": {
                "label": "Patrick Henry density adjustments and state-law effects",
                "reason_code": "deferred_regulation_family",
                "explanation": (
                    "The base gross-density range is supported, but parcel yield, plan "
                    "reconciliation, density bonus, affordability, development agreements, "
                    "and state-law adjustments are not evaluated."
                ),
                "source_refs": verification_ref,
                "prerequisite_ids": [],
            },
            "patrick_henry_uc_community_benefits_density_path": {
                "label": "UC community-benefits density path",
                "reason_code": "requires_unavailable_proposal_facts",
                "explanation": (
                    "Density above 250 DU/AC may require community benefits formalized in a "
                    "development agreement; that discretionary path is not evaluated."
                ),
                "source_refs": [
                    "patrick-henry-title18-zone-purpose",
                    "patrick-henry-plan-classifications",
                ],
                "prerequisite_ids": [],
            },
            "patrick_henry_hdf_nonresidential_option": {
                "label": "HD Flex nonresidential option",
                "reason_code": "deferred_regulation_family",
                "explanation": (
                    "The plan's optional office path is outside this residential-only "
                    "product phase."
                ),
                "source_refs": ["patrick-henry-plan-classifications"],
                "prerequisite_ids": [],
            },
        }
    )


def range_value(minimum: int, maximum: int) -> dict[str, Any]:
    """Return a comparable gross-density assertion value."""

    return {
        "kind": "quantity_range",
        "minimum": minimum,
        "maximum": maximum,
        "unit": "dwelling_units_per_acre",
    }


def ph_r5_density_conflict() -> dict[str, Any]:
    """Return every PH-R5 density assertion and the project selection."""

    assertions = [
        (
            "title18-table-1-1-51-100",
            51,
            100,
            "residential-density-table-1-1",
            True,
        ),
        (
            "title18-zone-purpose-51-99",
            51,
            99,
            "patrick-henry-title18-zone-purpose",
            False,
        ),
        (
            "title18-table-2-4-51-99",
            51,
            99,
            "patrick-henry-title18-standards-table",
            False,
        ),
        (
            "specific-plan-section-4-3-2-51-99",
            51,
            99,
            "patrick-henry-plan-classifications",
            False,
        ),
        (
            "specific-plan-table-4-2-51-99",
            51,
            99,
            "patrick-henry-plan-standards-table",
            False,
        ),
    ]
    return {
        "affected_rule_ids": [profile_rule_id("PH-R5", DENSITY_CAPABILITY)],
        "assertions": [
            {
                "assertion_id": assertion_id,
                "value": range_value(minimum, maximum),
                "source_refs": [source_ref],
                "disposition": (
                    "selected_for_ruleset" if selected else "not_selected_for_ruleset"
                ),
            }
            for assertion_id, minimum, maximum, source_ref, selected in assertions
        ],
        "resolution": {
            "selected_assertion_id": "title18-table-1-1-51-100",
            "selected_value": range_value(51, 100),
            "rationale": (
                "The project owner approved applying the established R5 policy to PH-R5: "
                "retain every conflicting assertion and use the Table 1-1 range for the "
                "candidate result."
            ),
            "decision_source": (
                "Project owner acceptance and PH-R5 direction in the July 19, 2026 Codex task"
            ),
            "decision_date": "2026-07-19",
            "status": "project_resolved_pending_official_clarification",
            "re_review_triggers": [
                "Official City or codifier clarification of the PH-R5 density discrepancy",
                "A newly consolidated Title 18 edition or adopted relevant amendment",
                "A revised or superseding Patrick Henry plan",
                (
                    "Parcel-specific General Plan, development-agreement, or approval "
                    "reconciliation"
                ),
            ],
        },
    }


def expand_ruleset(
    source: dict[str, Any],
    *,
    source_path: Path = DEFAULT_SOURCE,
    version: str = DEFAULT_VERSION,
    crosswalk_path: Optional[str] = None,
) -> dict[str, Any]:
    """Return the deterministic complete 12-zone nonruntime candidate."""

    if source.get("schema_version") != "3.2.0":
        raise PatrickHenryAuthoringError("Patrick Henry authoring requires schema 3.2.0")
    if source.get("version") != "2026-07-19.3":
        raise PatrickHenryAuthoringError(
            "Patrick Henry authoring requires predecessor 2026-07-19.3"
        )
    if source.get("status") != "candidate" or source.get("approved_on") is not None:
        raise PatrickHenryAuthoringError(
            "Patrick Henry authoring requires the unapproved candidate"
        )
    if set(source.get("zones", {})) != {
        "R1-6L",
        "R1-8L",
        "R2",
        "R3",
        "R4",
        "R5",
        "R6",
    }:
        raise PatrickHenryAuthoringError("Predecessor must contain exactly R1-R6")

    if crosswalk_path is None:
        crosswalk_path = (
            "rulesets/santa_clara/residential/2026-07-19.4/"
            "patrick-henry-expansion-crosswalk.json"
        )
    target = copy.deepcopy(source)
    target["version"] = version
    target["scope"]["description"] = (
        "Nonruntime selected residential standards candidate containing the accepted R1 "
        "migration, the owner-approved R2-R6 and density tranches, and the five source-verified "
        "Patrick Henry multifamily designations."
    )
    target["predecessor_rulesets"] = [
        {
            "ruleset_id": source["ruleset_id"],
            "version": source["version"],
            "sha256": sha256_file(source_path),
            "crosswalk_path": crosswalk_path,
        }
    ]
    add_shared_records(target["shared"])
    add_topics(target["not_evaluated_topics"])
    for zone, data in PATRICK_HENRY_ZONE_DATA.items():
        target["zones"][zone] = patrick_henry_zone(zone, data)
    target["conflicts"][PH_R5_CONFLICT_ID] = ph_r5_density_conflict()
    return target


def component_hash(value: Any) -> str:
    """Return a canonical hash for one preserved JSON component."""

    return sha256_bytes(json_bytes(value))


def rule_count(ruleset: dict[str, Any]) -> int:
    """Count zone-owned permissions and profile-owned regulations."""

    return sum(
        len(zone["use_permissions"])
        + sum(len(profile["regulations"]) for profile in zone["analysis_profiles"].values())
        for zone in ruleset["zones"].values()
    )


def build_crosswalk(
    *,
    source: dict[str, Any],
    source_path: Path,
    target: dict[str, Any],
    target_path: Path,
    schema_path: Path,
    target_bytes: bytes,
) -> dict[str, Any]:
    """Build the checksum-pinned density-to-Patrick-Henry crosswalk."""

    return {
        "crosswalk_version": "1.0.0",
        "migration_id": "santa-clara-residential-v3-add-patrick-henry-zones",
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
            "carried_source_rules": rule_count(source),
            "target_rules": rule_count(target),
            "added_use_permissions": 15,
            "added_analysis_profiles": 5,
            "added_profile_regulations": 50,
            "added_not_evaluated_topics": 8,
            "added_source_documents": 2,
            "added_citations": 9,
            "added_exception_families": 2,
            "carried_conflicts": len(source["conflicts"]),
            "added_conflicts": 1,
        },
        "preserved_components": [
            {
                "component_path": f"zones.{zone}",
                "sha256": component_hash(zone_record),
            }
            for zone, zone_record in source["zones"].items()
        ]
        + [
            {
                "component_path": "conflicts",
                "sha256": component_hash(source["conflicts"]),
            },
            {
                "component_path": "not_evaluated_topics",
                "sha256": component_hash(source["not_evaluated_topics"]),
            },
        ],
        "added_zone_profiles": {
            zone: ["multifamily"] for zone in PATRICK_HENRY_ZONE_DATA
        },
        "allowed_ruleset_changes": [
            (
                "Retain schema 3.2.0 and advance the candidate version without widening "
                "the regulation map."
            ),
            (
                "Add exactly PH-R5, UV, VR, UC, and HDF with three use permissions and "
                "one multifamily profile each."
            ),
            (
                "Add ten existing supported capabilities per Patrick Henry profile, "
                "including gross density."
            ),
            (
                "Retain every PH-R5 density assertion and project-select Table 1-1's "
                "51-100 DU/AC range."
            ),
            (
                "Add checksum-pinned Patrick Henry source, verification, qualification, "
                "and exception records."
            ),
            (
                "Retain candidate status, null approval, and false record approvals "
                "pending full candidate review."
            ),
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
    """Return Patrick Henry lineage, preservation, checksum, and replay errors."""

    errors: list[str] = []
    if crosswalk.get("migration_id") != (
        "santa-clara-residential-v3-add-patrick-henry-zones"
    ):
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

    for zone, source_zone in source["zones"].items():
        if target["zones"].get(zone) != source_zone:
            errors.append(f"target changed preserved predecessor zone {zone}")
    for conflict_id, conflict in source["conflicts"].items():
        if target["conflicts"].get(conflict_id) != conflict:
            errors.append(f"target changed predecessor conflict {conflict_id}")
    for topic_id, topic in source["not_evaluated_topics"].items():
        if target["not_evaluated_topics"].get(topic_id) != topic:
            errors.append(f"target changed predecessor topic {topic_id}")
    for group in ("source_documents", "citations", "definitions", "exception_families"):
        for record_id, record in source["shared"][group].items():
            if target["shared"][group].get(record_id) != record:
                errors.append(f"target changed shared predecessor record {group}.{record_id}")

    expected_zones = set(source["zones"]) | set(PATRICK_HENRY_ZONE_DATA)
    if set(target.get("zones", {})) != expected_zones:
        errors.append("target does not contain exactly the complete 12-zone matrix")
    expected_conflicts = set(source["conflicts"]) | {PH_R5_CONFLICT_ID}
    if set(target.get("conflicts", {})) != expected_conflicts:
        errors.append("target conflicts are not exactly the predecessor plus PH-R5")
    expected_profiles = {
        zone: ["multifamily"] for zone in PATRICK_HENRY_ZONE_DATA
    }
    if crosswalk.get("added_zone_profiles") != expected_profiles:
        errors.append("added_zone_profiles does not match the Patrick Henry matrix")

    reproduced = expand_ruleset(
        source,
        source_path=source_path,
        version=target["version"],
        crosswalk_path=target["predecessor_rulesets"][0]["crosswalk_path"],
    )
    if reproduced != target:
        errors.append("target ruleset differs from deterministic Patrick Henry authoring replay")
    reproduced_crosswalk = build_crosswalk(
        source=source,
        source_path=source_path,
        target=target,
        target_path=target_path,
        schema_path=schema_path,
        target_bytes=json_bytes(target),
    )
    if reproduced_crosswalk != crosswalk:
        errors.append("crosswalk differs from deterministic Patrick Henry authoring replay")
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
    """Validate the predecessor and write a new Patrick Henry candidate."""

    args = parse_args(argv)
    source_path = args.source.resolve()
    source_schema_path = args.source_schema.resolve()
    schema_path = args.schema.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise PatrickHenryAuthoringError(
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
        raise PatrickHenryAuthoringError(
            "R1-R6 density predecessor failed validation:\n" + "\n".join(source_errors)
        )

    crosswalk_relative = relative_path(output_dir / DEFAULT_CROSSWALK_NAME)
    target = expand_ruleset(
        source,
        source_path=source_path,
        version=args.version,
        crosswalk_path=crosswalk_relative,
    )
    target_errors = validate_ruleset(target, schema=load_json(schema_path))
    if target_errors:
        raise PatrickHenryAuthoringError(
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
        raise PatrickHenryAuthoringError(
            "Written Patrick Henry expansion failed replay validation:\n"
            + "\n".join(errors)
        )
    print(f"Authored nonruntime 12-zone residential candidate: {target_path}")
    print(f"Patrick Henry expansion crosswalk: {crosswalk_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
