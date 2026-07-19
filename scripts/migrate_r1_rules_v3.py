#!/usr/bin/env python3
"""Migrate the immutable approved R1 v2 ruleset to a candidate v3 lineage.

The migration is deterministic and non-overwriting. It preserves every v2 R1
rule and conflict through an exhaustive crosswalk, adds only the source-approved
R1 permission/pathway records required by the v3 contract, and never emits a
runtime-approved ruleset.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_r1_rules_v2 import (  # noqa: E402
    runtime_eligibility_errors as v2_runtime_eligibility_errors,
    validate_ruleset as validate_v2_ruleset,
)


DEFAULT_SOURCE = (
    REPO_ROOT / "rulesets/santa_clara/r1/2026-07-17.2/ruleset.json"
)
DEFAULT_SCHEMA = REPO_ROOT / "rulesets/schema/ruleset-v3.schema.json"
DEFAULT_VERSION = "2026-07-19.1"
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT / f"rulesets/santa_clara/residential/{DEFAULT_VERSION}"
)
ZONES = ("R1-6L", "R1-8L")
SINGLE_FAMILY_PROFILE = "single_family"
SPECIAL_PATHWAY_ID = "r1_chapter_18_24_two_unit"
MIGRATED_TOPIC_IDS = {
    "Accessory structures": "accessory_structures",
    "ADUs and JADUs": "adus_and_jadus",
    "SB 9 and two-unit projects": "sb9_and_two_unit_projects",
    "Density and state-law overrides": "density_and_state_law_overrides",
    "Parcel-creation standards": "parcel_creation_standards",
    "Driveway approach length": "driveway_approach_length",
    "Daylight plane": "daylight_plane",
    "Proposal-specific compliance": "proposal_specific_compliance",
    "Buildable-envelope geometry": "buildable_envelope_geometry",
    "Historic, specific-plan, and other overlay review": (
        "historic_specific_plan_and_other_overlay_review"
    ),
}


class MigrationError(RuntimeError):
    """Raised when the approved v2 data cannot be migrated unambiguously."""


def load_json(path: Path) -> dict[str, Any]:
    """Load one JSON object."""

    with path.open(encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise MigrationError(f"Expected a JSON object at {path}")
    return value


def json_bytes(value: dict[str, Any]) -> bytes:
    """Return the repository's canonical pretty-printed JSON bytes."""

    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    """Hash bytes with SHA-256."""

    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash a file with SHA-256."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_path(path: Path) -> str:
    """Return a stable repository-relative path."""

    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def ordered_union(*groups: Iterable[str]) -> list[str]:
    """Combine sequences without changing first-seen order."""

    result: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            if item not in seen:
                result.append(item)
                seen.add(item)
    return result


def profile_rule_id(zone: str, capability: str) -> str:
    """Return the v3 identity for an R1 single-family profile rule."""

    return f"us.ca.santa_clara.{zone.lower()}.{SINGLE_FAMILY_PROFILE}.{capability}"


def use_rule_id(zone: str, capability: str) -> str:
    """Return the v3 identity for a zone-owned use permission."""

    return f"us.ca.santa_clara.{zone.lower()}.{capability}"


def migrate_profile_rule(
    source_rule: dict[str, Any],
    *,
    zone: str,
    capability: str,
) -> dict[str, Any]:
    """Move one approved v2 rule into the R1 single-family profile."""

    if source_rule.get("approved_for_ruleset") is not True:
        raise MigrationError(f"Source rule is not approved: {source_rule.get('rule_id')}")
    result = copy.deepcopy(source_rule)
    result["rule_id"] = profile_rule_id(zone, capability)
    result["applicability"] = {
        "lot_context": source_rule["applicability"]["lot_context"]
    }
    result["approved_for_ruleset"] = False
    return result


def migrate_single_family_permission(
    source_rule: dict[str, Any],
    *,
    zone: str,
) -> dict[str, Any]:
    """Move the approved v2 single-family use into use_permissions."""

    if source_rule.get("approved_for_ruleset") is not True:
        raise MigrationError(f"Source rule is not approved: {source_rule.get('rule_id')}")
    result = copy.deepcopy(source_rule)
    result.pop("applicability")
    result["rule_id"] = use_rule_id(zone, "use.single_family_dwelling")
    result["special_pathway_id"] = None
    result["approved_for_ruleset"] = False
    return result


def two_family_permission(zone: str) -> dict[str, Any]:
    """Return the source-approved R1 Chapter 18.24 permission record."""

    return {
        "rule_id": use_rule_id(zone, "use.two_family_dwelling"),
        "label": "Two-family dwelling pathway",
        "requirement": {
            "kind": "status",
            "code": "permitted_by_right",
            "source_refs": [
                "use-table",
                "r1-two-unit-pathway",
                "residential-amendment-audit",
            ],
        },
        "conditions": [
            "Subject to Chapter 18.24 eligibility and attached-or-detached configuration rules.",
            "Dimensional analysis is not evaluated by the current product.",
        ],
        "exception_family_ids": [],
        "validation_status": "verified_with_conditions",
        "conflict_id": None,
        "special_pathway_id": SPECIAL_PATHWAY_ID,
        "approved_for_ruleset": False,
    }


def multifamily_permission(zone: str) -> dict[str, Any]:
    """Return the source-table R1 multifamily not-listed record."""

    return {
        "rule_id": use_rule_id(zone, "use.multifamily_dwelling"),
        "label": "Multifamily dwelling",
        "requirement": {
            "kind": "status",
            "code": "not_listed",
            "source_refs": ["use-table", "residential-amendment-audit"],
        },
        "conditions": [
            "Not listed records the controlling base-table cell and is not a prohibition conclusion."
        ],
        "exception_family_ids": [],
        "validation_status": "verified_base_value",
        "conflict_id": None,
        "special_pathway_id": None,
        "approved_for_ruleset": False,
    }


def special_pathway() -> dict[str, Any]:
    """Return the nonnumeric R1 Chapter 18.24 analysis pathway."""

    return {
        "label": "R1 Chapter 18.24 two-home pathway",
        "workflow_family": "multifamily",
        "legal_use_capability_id": "use.two_family_dwelling",
        "configuration_scope": "attached_or_detached_homes",
        "analysis_requirement": {
            "kind": "not_evaluated",
            "reason_code": "requires_unimplemented_eligibility_and_branch_logic",
            "explanation": (
                "The controlling standards branch on eligibility, attached or detached "
                "configuration, the ordinary R1 envelope, existing setbacks, and proposal facts."
            ),
            "source_refs": [
                "r1-two-unit-pathway",
                "residential-amendment-audit",
            ],
            "prerequisite_ids": [
                "proposal_specific_compliance",
                "buildable_envelope_geometry",
            ],
        },
        "not_evaluated_topic_ids": ["r1_chapter_18_24_dimensional_analysis"],
        "validation_status": "verified_with_conditions",
        "approved_for_ruleset": False,
    }


def migrated_topics(source: dict[str, Any]) -> dict[str, Any]:
    """Convert the v2 global scope list into stable sourced topic records."""

    source_labels = source.get("not_evaluated")
    if not isinstance(source_labels, list) or set(source_labels) != set(MIGRATED_TOPIC_IDS):
        raise MigrationError("Approved v2 not_evaluated topics do not match the migration map")
    topics: dict[str, Any] = {}
    for label in source_labels:
        topic_id = MIGRATED_TOPIC_IDS[label]
        topics[topic_id] = {
            "label": label,
            "reason_code": "migrated_scope_limitation",
            "explanation": (
                "The approved R1 v2 ruleset expressly excluded this subject from its "
                "deterministic retrieval scope."
            ),
            "source_refs": ["approved-r1-v2-scope"],
            "prerequisite_ids": [],
        }
    topics["r1_chapter_18_24_dimensional_analysis"] = {
        "label": "R1 Chapter 18.24 two-home dimensional analysis",
        "reason_code": "requires_unimplemented_eligibility_and_branch_logic",
        "explanation": (
            "Permission is source verified, but the current product lacks the facts and "
            "branch logic required to return dimensional standards."
        ),
        "source_refs": [
            "r1-two-unit-pathway",
            "residential-amendment-audit",
        ],
        "prerequisite_ids": [
            "proposal_specific_compliance",
            "buildable_envelope_geometry",
        ],
    }
    return topics


def migrate_conflicts(
    source: dict[str, Any],
    *,
    rule_id_map: dict[str, str],
) -> dict[str, Any]:
    """Translate affected rule identities while preserving conflict meaning."""

    conflicts = copy.deepcopy(source["conflicts"])
    for conflict in conflicts.values():
        conflict["affected_rule_ids"] = [
            rule_id_map[rule_id] for rule_id in conflict["affected_rule_ids"]
        ]
        for assertion in conflict["assertions"]:
            assertion["disposition"] = (
                "selected_for_ruleset"
                if assertion["disposition"] == "selected_for_prototype"
                else "not_selected_for_ruleset"
            )
    return conflicts


def migrate_ruleset(
    source: dict[str, Any],
    *,
    source_path: Path = DEFAULT_SOURCE,
    version: str = DEFAULT_VERSION,
    crosswalk_path: str = (
        "rulesets/santa_clara/residential/2026-07-19.1/migration-crosswalk.json"
    ),
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return a candidate v3 ruleset, rule mappings, and topic mappings."""

    if source.get("schema_version") != "2.0.0":
        raise MigrationError("Source ruleset is not schema v2")
    if source.get("ruleset_id") != "santa-clara-r1-base-zone":
        raise MigrationError("Source ruleset identity is not the approved R1 lineage")
    if source.get("status") != "approved_for_prototype":
        raise MigrationError("Source R1 ruleset is not approved")
    if set(source.get("zones", {})) != set(ZONES):
        raise MigrationError("Source R1 ruleset must contain exactly R1-6L and R1-8L")

    source_checksum = sha256_file(source_path)
    residential_audit_path = REPO_ROOT / "docs/residential-title18-amendment-audit.md"
    shared = copy.deepcopy(source["shared"])
    shared["source_documents"]["approved-r1-ruleset-v2"] = {
        "title": "Approved Santa Clara R1 ruleset v2",
        "version": source["version"],
        "effective_date": source["approved_on"],
        "local_path": relative_path(source_path),
        "sha256": source_checksum,
        "verification_status": "verified_migration_source",
    }
    shared["source_documents"]["sc-title18-amendment-audit-2026-07-18"] = {
        "title": "Santa Clara residential Title 18 post-baseline amendment audit",
        "version": "Cutoff July 18, 2026",
        "effective_date": None,
        "local_path": relative_path(residential_audit_path),
        "sha256": sha256_file(residential_audit_path),
        "verification_status": "verified_audit_artifact",
    }
    shared["citations"]["approved-r1-v2-scope"] = {
        "source_document_id": "approved-r1-ruleset-v2",
        "locator": "not_evaluated",
        "topic": "Approved predecessor scope limitations",
    }
    shared["citations"]["r1-two-unit-pathway"] = {
        "source_document_id": "sc-title18-2025-07",
        "locator": "Chapter 18.24",
        "topic": "R1 two-home permission and dimensional pathways",
    }
    shared["citations"]["residential-amendment-audit"] = {
        "source_document_id": "sc-title18-amendment-audit-2026-07-18",
        "locator": "Residential expansion conclusion",
        "topic": "Later-legislation review for selected residential standards",
    }

    rule_mappings: list[dict[str, Any]] = []
    rule_id_map: dict[str, str] = {}
    zones: dict[str, Any] = {}
    migrated_topic_ids = list(MIGRATED_TOPIC_IDS.values())
    for zone in ZONES:
        source_regulations = source["zones"][zone]["regulations"]
        single_use = source_regulations["use.single_family_dwelling"]
        migrated_use = migrate_single_family_permission(single_use, zone=zone)
        rule_id_map[single_use["rule_id"]] = migrated_use["rule_id"]
        rule_mappings.append(
            {
                "source_rule_id": single_use["rule_id"],
                "source_zone": zone,
                "source_capability_id": "use.single_family_dwelling",
                "target_kind": "use_permission",
                "target_zone": zone,
                "target_profile_id": None,
                "target_capability_id": "use.single_family_dwelling",
                "target_rule_id": migrated_use["rule_id"],
                "preserved_components": [
                    "label",
                    "requirement",
                    "lot_context",
                    "conditions",
                    "exception_family_ids",
                    "validation_status",
                    "conflict_id",
                ],
                "representation_changes": [
                    "Removed redundant rule-level structure_type; zone use permission owns legal-use identity.",
                    "Reset approved_for_ruleset to false for the new schema lineage.",
                ],
            }
        )

        profile_regulations: dict[str, Any] = {}
        for capability, source_rule in source_regulations.items():
            if capability == "use.single_family_dwelling":
                continue
            migrated_rule = migrate_profile_rule(
                source_rule,
                zone=zone,
                capability=capability,
            )
            profile_regulations[capability] = migrated_rule
            rule_id_map[source_rule["rule_id"]] = migrated_rule["rule_id"]
            rule_mappings.append(
                {
                    "source_rule_id": source_rule["rule_id"],
                    "source_zone": zone,
                    "source_capability_id": capability,
                    "target_kind": "profile_regulation",
                    "target_zone": zone,
                    "target_profile_id": SINGLE_FAMILY_PROFILE,
                    "target_capability_id": capability,
                    "target_rule_id": migrated_rule["rule_id"],
                    "preserved_components": [
                        "label",
                        "requirement",
                        "lot_context",
                        "conditions",
                        "exception_family_ids",
                        "validation_status",
                        "conflict_id",
                    ],
                    "representation_changes": [
                        "Inserted the ordinary profile ID into the rule identity.",
                        "Derived structure_type from the enclosing profile.",
                        "Reset approved_for_ruleset to false for the new schema lineage.",
                    ],
                }
            )

        zones[zone] = {
            "label": zone,
            "use_permissions": {
                "use.single_family_dwelling": migrated_use,
                "use.two_family_dwelling": two_family_permission(zone),
                "use.multifamily_dwelling": multifamily_permission(zone),
            },
            "analysis_profiles": {
                SINGLE_FAMILY_PROFILE: {
                    "workflow_family": "single_family",
                    "legal_use_capability_id": "use.single_family_dwelling",
                    "primary_structure_type": "single_family_primary_structure",
                    "regulations": profile_regulations,
                    "not_evaluated_topic_ids": migrated_topic_ids,
                }
            },
            "special_pathways": {SPECIAL_PATHWAY_ID: special_pathway()},
        }

    topic_mappings = [
        {
            "source_label": label,
            "target_topic_id": topic_id,
            "provenance_source_ref": "approved-r1-v2-scope",
        }
        for label, topic_id in MIGRATED_TOPIC_IDS.items()
    ]
    candidate = {
        "$schema": "../../../schema/ruleset-v3.schema.json",
        "schema_version": "3.0.0",
        "ruleset_id": "santa-clara-residential-zoning",
        "version": version,
        "jurisdiction": copy.deepcopy(source["jurisdiction"]),
        "status": "candidate",
        "approved_on": None,
        "verified_through": "2026-07-18",
        "scope": {
            "description": (
                "Candidate selected residential standards contract containing the migrated "
                "R1 baseline; remaining target zones are intentionally unauthored."
            ),
            "workflow_families": ["single_family", "multifamily"],
            "legal_use_capability_ids": [
                "use.single_family_dwelling",
                "use.two_family_dwelling",
                "use.multifamily_dwelling",
            ],
            "primary_structure_types": [
                "single_family_primary_structure",
                "two_family_primary_structure",
                "multifamily_primary_structure",
            ],
            "result_kind": "selected_residential_standards_retrieval",
        },
        "predecessor_rulesets": [
            {
                "ruleset_id": source["ruleset_id"],
                "version": source["version"],
                "sha256": source_checksum,
                "crosswalk_path": crosswalk_path,
            }
        ],
        "shared": shared,
        "zones": zones,
        "conflicts": migrate_conflicts(source, rule_id_map=rule_id_map),
        "not_evaluated_topics": migrated_topics(source),
        "disclaimer": (
            "Santa Clara Zoning Explorer reports selected residential zoning standards "
            "and is not a complete entitlement analysis or legal or planning determination."
        ),
    }
    return candidate, rule_mappings, topic_mappings


def canonical_source_rule(rule: dict[str, Any]) -> dict[str, Any]:
    """Project a v2 rule onto the semantics that v3 must preserve."""

    return {
        "label": rule["label"],
        "requirement": rule["requirement"],
        "lot_context": rule["applicability"]["lot_context"],
        "conditions": rule["conditions"],
        "exception_family_ids": rule["exception_family_ids"],
        "validation_status": rule["validation_status"],
        "conflict_id": rule["conflict_id"],
    }


def canonical_target_rule(rule: dict[str, Any], *, lot_context: str) -> dict[str, Any]:
    """Project a v3 rule onto the predecessor semantic surface."""

    return {
        "label": rule["label"],
        "requirement": rule["requirement"],
        "lot_context": lot_context,
        "conditions": rule["conditions"],
        "exception_family_ids": rule["exception_family_ids"],
        "validation_status": rule["validation_status"],
        "conflict_id": rule["conflict_id"],
    }


def build_crosswalk(
    *,
    source: dict[str, Any],
    source_path: Path,
    target: dict[str, Any],
    target_path: Path,
    schema_path: Path,
    target_bytes: bytes,
    rule_mappings: list[dict[str, Any]],
    topic_mappings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the exhaustive, checksum-pinned v2-to-v3 crosswalk."""

    return {
        "crosswalk_version": "1.0.0",
        "migration_id": "santa-clara-r1-v2-to-residential-v3",
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
            "source_rules": sum(
                len(zone["regulations"]) for zone in source["zones"].values()
            ),
            "mapped_source_rules": len(rule_mappings),
            "target_zones": len(target["zones"]),
            "target_use_permissions": sum(
                len(zone["use_permissions"]) for zone in target["zones"].values()
            ),
            "target_profile_regulations": sum(
                len(profile["regulations"])
                for zone in target["zones"].values()
                for profile in zone["analysis_profiles"].values()
            ),
            "target_special_pathways": sum(
                len(zone["special_pathways"]) for zone in target["zones"].values()
            ),
            "mapped_scope_topics": len(topic_mappings),
            "conflicts": len(target["conflicts"]),
        },
        "rule_mappings": rule_mappings,
        "topic_mappings": topic_mappings,
        "added_contract_records": [
            "R1 two-family use-permission record for each migrated zone",
            "R1 multifamily not-listed record for each migrated zone",
            "R1 Chapter 18.24 not-evaluated special pathway for each migrated zone",
            "Structured R1 Chapter 18.24 dimensional-analysis topic",
        ],
        "allowed_ruleset_changes": [
            "The v3 artifact has a new lineage identity and candidate approval state.",
            "Rules are separated into zone use permissions and profile-owned regulations.",
            "Profile-owned rule IDs include the exact profile ID.",
            "Structure type moves from each rule into the enclosing exact profile.",
            "The v2 global not-evaluated list becomes structured sourced topic records.",
            "Conflict dispositions use ruleset-neutral wording while preserving selection meaning.",
            "The verified-through cutoff advances through the residential amendment audit.",
        ],
    }


def validate_migration(
    source: dict[str, Any],
    target: dict[str, Any],
    crosswalk: dict[str, Any],
    *,
    source_path: Path = DEFAULT_SOURCE,
    target_path: Path = DEFAULT_OUTPUT_DIR / "ruleset.json",
    schema_path: Path = DEFAULT_SCHEMA,
) -> list[str]:
    """Return checksum, exhaustiveness, replay, and semantic-equivalence errors."""

    errors: list[str] = []
    if crosswalk.get("migration_id") != "santa-clara-r1-v2-to-residential-v3":
        errors.append("migration_id is unsupported")

    path_records = (
        ("source_ruleset", source_path),
        ("target_ruleset", target_path),
        ("target_schema", schema_path),
    )
    for record_name, expected_path in path_records:
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

    mappings = crosswalk.get("rule_mappings")
    if not isinstance(mappings, list):
        return errors + ["rule_mappings must be an array"]
    source_rules = {
        rule["rule_id"]: (zone, capability, rule)
        for zone, zone_record in source["zones"].items()
        for capability, rule in zone_record["regulations"].items()
    }
    mapped_source_ids = [entry.get("source_rule_id") for entry in mappings]
    duplicates = [
        rule_id for rule_id in set(mapped_source_ids) if mapped_source_ids.count(rule_id) > 1
    ]
    if duplicates:
        errors.append(f"rule_mappings contain duplicate source IDs: {sorted(duplicates)}")
    missing = set(source_rules) - set(mapped_source_ids)
    extra = set(mapped_source_ids) - set(source_rules)
    if missing:
        errors.append(f"rule_mappings omit source rules: {sorted(missing)}")
    if extra:
        errors.append(f"rule_mappings reference unknown source rules: {sorted(extra)}")

    for index, mapping in enumerate(mappings):
        source_entry = source_rules.get(mapping.get("source_rule_id"))
        if source_entry is None:
            continue
        source_zone, source_capability, source_rule = source_entry
        target_zone = mapping.get("target_zone")
        target_capability = mapping.get("target_capability_id")
        zone_record = target["zones"].get(target_zone)
        if zone_record is None:
            errors.append(f"rule_mappings[{index}] references unknown target zone")
            continue
        profile_id = mapping.get("target_profile_id")
        if profile_id is None:
            target_rule = zone_record["use_permissions"].get(target_capability)
            lot_context = source_rule["applicability"]["lot_context"]
        else:
            profile = zone_record["analysis_profiles"].get(profile_id)
            if profile is None:
                errors.append(f"rule_mappings[{index}] references unknown target profile")
                continue
            target_rule = profile["regulations"].get(target_capability)
            lot_context = target_rule["applicability"]["lot_context"] if target_rule else ""
        if target_rule is None:
            errors.append(f"rule_mappings[{index}] references unknown target rule")
            continue
        if mapping.get("target_rule_id") != target_rule["rule_id"]:
            errors.append(f"rule_mappings[{index}].target_rule_id does not match")
        if source_zone != target_zone or source_capability != target_capability:
            errors.append(f"rule_mappings[{index}] changes zone or capability identity")
        if canonical_source_rule(source_rule) != canonical_target_rule(
            target_rule,
            lot_context=lot_context,
        ):
            errors.append(f"rule_mappings[{index}] fails R1 semantic equivalence")

    topic_mappings = crosswalk.get("topic_mappings")
    if not isinstance(topic_mappings, list):
        errors.append("topic_mappings must be an array")
    else:
        source_labels = set(source["not_evaluated"])
        mapped_labels = {entry.get("source_label") for entry in topic_mappings}
        if mapped_labels != source_labels:
            errors.append("topic_mappings are not exhaustive")
        for index, mapping in enumerate(topic_mappings):
            topic = target["not_evaluated_topics"].get(mapping.get("target_topic_id"))
            if topic is None or topic["label"] != mapping.get("source_label"):
                errors.append(f"topic_mappings[{index}] does not resolve exactly")

    target_crosswalk_path = target["predecessor_rulesets"][0]["crosswalk_path"]
    reproduced, reproduced_rules, reproduced_topics = migrate_ruleset(
        source,
        source_path=source_path,
        version=target["version"],
        crosswalk_path=target_crosswalk_path,
    )
    if reproduced != target:
        errors.append("target ruleset differs from deterministic migration replay")
    target_bytes = json_bytes(target)
    reproduced_crosswalk = build_crosswalk(
        source=source,
        source_path=source_path,
        target=target,
        target_path=target_path,
        schema_path=schema_path,
        target_bytes=target_bytes,
        rule_mappings=reproduced_rules,
        topic_mappings=reproduced_topics,
    )
    if reproduced_crosswalk != crosswalk:
        errors.append("crosswalk differs from deterministic migration replay")
    return errors


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse migration command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Validate the predecessor, migrate it, and write a new candidate directory."""

    args = parse_args(argv)
    source_path = args.source.resolve()
    schema_path = args.schema.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise MigrationError(
            f"Destination already exists; choose a new version directory: {output_dir}"
        )

    source = load_json(source_path)
    source_errors = validate_v2_ruleset(
        source,
        repo_root=REPO_ROOT,
        verify_source_files=True,
    )
    source_errors.extend(v2_runtime_eligibility_errors(source, domain_errors=source_errors))
    if source_errors:
        raise MigrationError("Approved v2 input is invalid:\n" + "\n".join(source_errors))

    target_path = output_dir / "ruleset.json"
    crosswalk_path = output_dir / "migration-crosswalk.json"
    candidate, rule_mappings, topic_mappings = migrate_ruleset(
        source,
        source_path=source_path,
        version=args.version,
        crosswalk_path=relative_path(crosswalk_path),
    )

    from scripts.validate_residential_rules_v3 import validate_ruleset

    candidate_errors = validate_ruleset(candidate, schema=load_json(schema_path))
    if candidate_errors:
        raise MigrationError("Candidate v3 output is invalid:\n" + "\n".join(candidate_errors))

    target_bytes = json_bytes(candidate)
    crosswalk = build_crosswalk(
        source=source,
        source_path=source_path,
        target=candidate,
        target_path=target_path,
        schema_path=schema_path,
        target_bytes=target_bytes,
        rule_mappings=rule_mappings,
        topic_mappings=topic_mappings,
    )

    output_dir.mkdir(parents=True)
    target_path.write_bytes(target_bytes)
    crosswalk_path.write_bytes(json_bytes(crosswalk))

    migration_errors = validate_migration(
        source,
        candidate,
        crosswalk,
        source_path=source_path,
        target_path=target_path,
        schema_path=schema_path,
    )
    if migration_errors:
        raise MigrationError(
            "Written migration failed replay validation:\n" + "\n".join(migration_errors)
        )

    print(f"Wrote candidate v3 ruleset: {relative_path(target_path)}")
    print(
        f"Mapped {len(rule_mappings)} approved v2 rules into two R1 zones; "
        "candidate is not runtime eligible"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
