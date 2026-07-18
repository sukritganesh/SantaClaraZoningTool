#!/usr/bin/env python3
"""Validate the Santa Clara R1 ruleset v2 candidate and migration.

JSON Schema validates local record shapes. This module adds the cross-record,
scope, provenance, conflict, migration, and runtime-eligibility invariants for
the retrieval-only R1 prototype.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.migrate_r1_rules_v2 import migrate_ruleset
from scripts.validate_r1_rules import (
    load_json,
    sha256_file,
    valid_date,
    validate_ruleset as validate_v1_ruleset,
    validate_schema_contract,
)


DEFAULT_RULESET = (
    REPO_ROOT / "rulesets/santa_clara/r1/2026-07-17/ruleset.json"
)
DEFAULT_SCHEMA = REPO_ROOT / "rulesets/schema/ruleset-v2.schema.json"
DEFAULT_CROSSWALK = DEFAULT_RULESET.parent / "migration-crosswalk.json"
DEFAULT_V1_RULESET = (
    REPO_ROOT / "rulesets/santa_clara/r1/2026-07-16/ruleset.json"
)

EXPECTED_RULESET_ID = "santa-clara-r1-base-zone"
EXPECTED_JURISDICTION = {
    "name": "City of Santa Clara",
    "slug": "santa_clara",
    "state": "CA",
    "country": "US",
}
SUPPORTED_ZONES = {"R1-6L", "R1-8L"}
SUPPORTED_STRUCTURE_TYPES = {"single_family_primary_structure"}
REQUIRED_CAPABILITIES = {
    "use.single_family_dwelling",
    "approval.zoning_clearance",
    "approval.architectural_review",
    "standard.maximum_primary_structure_height",
    "standard.maximum_stories",
    "standard.maximum_structure_coverage",
    "setback.front",
    "setback.interior_side",
    "setback.street_side",
    "setback.rear",
}

STATUS_CAPABILITIES = {
    "use.single_family_dwelling",
    "approval.zoning_clearance",
    "approval.architectural_review",
}
MAXIMUM_UNITS = {
    "standard.maximum_primary_structure_height": "ft",
    "standard.maximum_stories": "stories",
    "standard.maximum_structure_coverage": "percent",
}
SETBACK_CAPABILITIES = {
    "setback.front",
    "setback.interior_side",
    "setback.street_side",
    "setback.rear",
}
EXPECTED_LOT_CONTEXT = {
    "use.single_family_dwelling": "not_applicable",
    "approval.zoning_clearance": "not_applicable",
    "approval.architectural_review": "not_applicable",
    "standard.maximum_primary_structure_height": "all",
    "standard.maximum_stories": "all",
    "standard.maximum_structure_coverage": "all",
    "setback.front": "all",
    "setback.interior_side": "all",
    "setback.street_side": "corner",
    "setback.rear": "all",
}

ADJUSTMENT_COMPONENT = re.compile(
    r"^requirement\.adjustments\[([a-z0-9]+(?:[._-][a-z0-9]+)*)\]$"
)


def duplicate_values(values: Iterable[Any]) -> set[Any]:
    seen: set[Any] = set()
    duplicates: set[Any] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def version_date(version: Any) -> Optional[date]:
    if not isinstance(version, str):
        return None
    prefix = version.split(".", 1)[0]
    try:
        return date.fromisoformat(prefix)
    except ValueError:
        return None


def resolved_repo_path(repo_root: Path, relative_path: Any) -> Optional[Path]:
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


def iter_regulations(
    ruleset: dict[str, Any],
) -> Iterable[tuple[str, str, dict[str, Any]]]:
    for zone, zone_record in ruleset["zones"].items():
        for capability, rule in zone_record["regulations"].items():
            yield zone, capability, rule


def validate_source_refs(
    refs: Iterable[str],
    *,
    citation_ids: set[str],
    location: str,
    errors: list[str],
) -> None:
    unknown = set(refs) - citation_ids
    if unknown:
        errors.append(f"{location} has unknown source refs: {sorted(unknown)}")


def validate_setback_value(
    value: dict[str, Any],
    *,
    location: str,
    allow_paired: bool,
    errors: list[str],
) -> None:
    kind = value["kind"]
    if kind == "distance":
        number = value["number"]
        if isinstance(number, bool) or number <= 0:
            errors.append(f"{location}.number must be greater than zero")
        return

    if not allow_paired:
        errors.append(f"{location} uses paired distances outside interior-side setback")

    members = value["members"]
    smaller = members[0]["number"]
    larger = members[1]["number"]
    if isinstance(smaller, bool) or smaller <= 0:
        errors.append(f"{location} smaller setback must be greater than zero")
    if isinstance(larger, bool) or larger <= 0:
        errors.append(f"{location} larger setback must be greater than zero")
    if smaller > larger:
        errors.append(f"{location} smaller setback exceeds larger setback")


def validate_requirement(
    capability: str,
    rule: dict[str, Any],
    *,
    citation_ids: set[str],
    location: str,
    errors: list[str],
) -> None:
    requirement = rule["requirement"]
    kind = requirement["kind"]

    if capability in STATUS_CAPABILITIES:
        if kind != "status":
            errors.append(f"{location} must use a status requirement")
            return
        code = requirement["code"]
        if capability == "use.single_family_dwelling":
            if code != "permitted_by_right":
                errors.append(
                    f"{location} uses unsupported single-family permission status: {code}"
                )
        elif code not in {"required", "may_be_required"}:
            errors.append(f"{location} uses an approval-incompatible status: {code}")
        validate_source_refs(
            requirement["source_refs"],
            citation_ids=citation_ids,
            location=f"{location}.requirement",
            errors=errors,
        )
        return

    if capability in MAXIMUM_UNITS:
        if kind != "maximum_quantity":
            errors.append(f"{location} must use a maximum_quantity requirement")
            return
        value = requirement["value"]
        number = value["number"]
        expected_unit = MAXIMUM_UNITS[capability]
        if value["unit"] != expected_unit:
            errors.append(
                f"{location} must use {expected_unit}, not {value['unit']}"
            )
        if isinstance(number, bool) or number <= 0:
            errors.append(f"{location}.requirement.value.number must be positive")
        if capability == "standard.maximum_stories" and (
            not isinstance(number, int) or isinstance(number, bool)
        ):
            errors.append(f"{location} story maximum must be an integer")
        if capability == "standard.maximum_structure_coverage" and number > 100:
            errors.append(f"{location} coverage maximum cannot exceed 100 percent")
        validate_source_refs(
            requirement["source_refs"],
            citation_ids=citation_ids,
            location=f"{location}.requirement",
            errors=errors,
        )
        return

    if capability not in SETBACK_CAPABILITIES:
        errors.append(f"{location} has unsupported capability semantics")
        return
    if kind != "setback":
        errors.append(f"{location} must use a setback requirement")
        return

    allow_paired = capability == "setback.interior_side"
    base = requirement["base"]
    base_value = base["value"]
    validate_setback_value(
        base_value,
        location=f"{location}.requirement.base.value",
        allow_paired=allow_paired,
        errors=errors,
    )
    validate_source_refs(
        base["source_refs"],
        citation_ids=citation_ids,
        location=f"{location}.requirement.base",
        errors=errors,
    )

    adjustments = requirement["adjustments"]
    adjustment_ids = [adjustment["adjustment_id"] for adjustment in adjustments]
    duplicates = duplicate_values(adjustment_ids)
    if duplicates:
        errors.append(f"{location} has duplicate adjustment IDs: {sorted(duplicates)}")

    for index, adjustment in enumerate(adjustments):
        adjustment_location = f"{location}.requirement.adjustments[{index}]"
        trigger = adjustment["trigger"]
        if trigger["kind"] != "story_at_or_above":
            errors.append(
                f"{adjustment_location} uses unsupported operational trigger: "
                f"{trigger['kind']}"
            )
        elif trigger["story"] < 2:
            errors.append(f"{adjustment_location} must begin at story two or above")

        effect = adjustment["effect"]
        if effect["kind"] != "replace_total_minimum":
            errors.append(
                f"{adjustment_location} uses unsupported operational effect: "
                f"{effect['kind']}"
            )
        effect_value = effect["value"]
        validate_setback_value(
            effect_value,
            location=f"{adjustment_location}.effect.value",
            allow_paired=allow_paired,
            errors=errors,
        )
        if effect_value["kind"] != base_value["kind"]:
            errors.append(f"{adjustment_location} value shape differs from its base")
        validate_source_refs(
            adjustment["source_refs"],
            citation_ids=citation_ids,
            location=adjustment_location,
            errors=errors,
        )

    resolution = requirement.get("adjustment_resolution")
    if len(adjustments) > 1:
        if resolution is None:
            errors.append(f"{location} lacks adjustment precedence")
        else:
            ordered_ids = resolution["ordered_adjustment_ids"]
            if len(ordered_ids) != len(adjustment_ids):
                errors.append(f"{location} adjustment precedence has the wrong length")
            if set(ordered_ids) != set(adjustment_ids):
                errors.append(
                    f"{location} adjustment precedence does not match adjustment IDs"
                )
    elif resolution is not None:
        errors.append(f"{location} has unnecessary adjustment precedence")


def operational_assertion_value(rule: dict[str, Any]) -> dict[str, Any]:
    requirement = rule["requirement"]
    if requirement["kind"] == "status":
        return {"kind": "status", "code": requirement["code"]}
    if requirement["kind"] == "maximum_quantity":
        return {
            "kind": "quantity",
            "number": requirement["value"]["number"],
            "unit": requirement["value"]["unit"],
        }
    return requirement["base"]["value"]


def validate_ruleset(
    ruleset: dict[str, Any],
    *,
    schema: Optional[dict[str, Any]] = None,
    repo_root: Path = REPO_ROOT,
    verify_source_files: bool = False,
) -> list[str]:
    """Return schema and domain errors for a candidate or approved v2 ruleset."""

    if schema is None:
        schema = load_json(DEFAULT_SCHEMA)
    errors = validate_schema_contract(ruleset, schema)
    if errors:
        return errors

    if ruleset["ruleset_id"] != EXPECTED_RULESET_ID:
        errors.append(f"ruleset_id must be {EXPECTED_RULESET_ID}")
    if ruleset["jurisdiction"] != EXPECTED_JURISDICTION:
        errors.append("jurisdiction does not match the Santa Clara R1 prototype")
    if set(ruleset["scope"]["structure_types"]) != SUPPORTED_STRUCTURE_TYPES:
        errors.append("scope must contain only single_family_primary_structure")

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

    shared = ruleset["shared"]
    source_documents = shared["source_documents"]
    source_ids = set(source_documents)
    citations = shared["citations"]
    citation_ids = set(citations)
    exception_families = shared["exception_families"]
    exception_ids = set(exception_families)

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

    for exception_id, exception in exception_families.items():
        validate_source_refs(
            exception["source_refs"],
            citation_ids=citation_ids,
            location=f"shared.exception_families.{exception_id}",
            errors=errors,
        )

    zones = ruleset["zones"]
    if set(zones) != SUPPORTED_ZONES:
        errors.append("zones must contain exactly R1-6L and R1-8L")

    rule_ids: list[str] = []
    rules_by_id: dict[str, dict[str, Any]] = {}
    rule_locations: dict[str, str] = {}
    for zone, zone_record in zones.items():
        regulations = zone_record["regulations"]
        missing = REQUIRED_CAPABILITIES - set(regulations)
        extra = set(regulations) - REQUIRED_CAPABILITIES
        if missing:
            errors.append(f"zones.{zone} is missing capabilities: {sorted(missing)}")
        if extra:
            errors.append(f"zones.{zone} has unsupported capabilities: {sorted(extra)}")

        for capability, rule in regulations.items():
            location = f"zones.{zone}.regulations.{capability}"
            expected_rule_id = (
                f"us.ca.santa_clara.{zone.lower()}.{capability}"
            )
            if rule["rule_id"] != expected_rule_id:
                errors.append(
                    f"{location}.rule_id must be {expected_rule_id}"
                )
            rule_ids.append(rule["rule_id"])
            rules_by_id[rule["rule_id"]] = rule
            rule_locations[rule["rule_id"]] = location

            applicability = rule["applicability"]
            if applicability["structure_type"] not in SUPPORTED_STRUCTURE_TYPES:
                errors.append(f"{location} applies to an unsupported structure type")
            expected_context = EXPECTED_LOT_CONTEXT.get(capability)
            if expected_context is not None and applicability["lot_context"] != expected_context:
                errors.append(
                    f"{location}.applicability.lot_context must be {expected_context}"
                )

            unknown_exceptions = set(rule["exception_family_ids"]) - exception_ids
            if unknown_exceptions:
                errors.append(
                    f"{location} has unknown exception families: "
                    f"{sorted(unknown_exceptions)}"
                )
            if (
                rule["validation_status"] == "candidate_unverified"
                and rule["approved_for_ruleset"]
            ):
                errors.append(f"{location} is approved while still candidate_unverified")

            validate_requirement(
                capability,
                rule,
                citation_ids=citation_ids,
                location=location,
                errors=errors,
            )

    duplicates = duplicate_values(rule_ids)
    if duplicates:
        errors.append(f"duplicate rule IDs: {sorted(duplicates)}")

    conflicts = ruleset["conflicts"]
    conflict_ids = set(conflicts)
    for conflict_id, conflict in conflicts.items():
        location = f"conflicts.{conflict_id}"
        affected_ids = conflict["affected_rule_ids"]
        unknown_affected = set(affected_ids) - set(rule_ids)
        if unknown_affected:
            errors.append(
                f"{location} has unknown affected rules: {sorted(unknown_affected)}"
            )

        assertions = conflict["assertions"]
        assertion_ids = [assertion["assertion_id"] for assertion in assertions]
        duplicates = duplicate_values(assertion_ids)
        if duplicates:
            errors.append(f"{location} has duplicate assertion IDs: {sorted(duplicates)}")
        for index, assertion in enumerate(assertions):
            validate_source_refs(
                assertion["source_refs"],
                citation_ids=citation_ids,
                location=f"{location}.assertions[{index}]",
                errors=errors,
            )

        selected_assertions = [
            assertion
            for assertion in assertions
            if assertion["disposition"] == "selected_for_prototype"
        ]
        if len(selected_assertions) != 1:
            errors.append(f"{location} must contain exactly one selected assertion")

        resolution = conflict["resolution"]
        selected_matches = [
            assertion
            for assertion in assertions
            if assertion["assertion_id"] == resolution["selected_assertion_id"]
        ]
        selected: Optional[dict[str, Any]] = None
        if len(selected_matches) != 1:
            errors.append(f"{location} does not identify exactly one selected assertion")
        else:
            selected = selected_matches[0]
            if selected["disposition"] != "selected_for_prototype":
                errors.append(f"{location} selected assertion has the wrong disposition")
            if selected["value"] != resolution["selected_value"]:
                errors.append(f"{location} selected value differs from its assertion")

        decision_date = date.fromisoformat(resolution["decision_date"])
        if publication_date is not None and decision_date > publication_date:
            errors.append(f"{location} decision date is after ruleset publication")

        for affected_id in affected_ids:
            rule = rules_by_id.get(affected_id)
            if rule is None:
                continue
            if rule["conflict_id"] != conflict_id:
                errors.append(f"{location} is not linked back from {affected_id}")
            if rule["validation_status"] != "project_resolved_with_conditions":
                errors.append(
                    f"{rule_locations[affected_id]} must use project-resolved validation status"
                )
            if operational_assertion_value(rule) != resolution["selected_value"]:
                errors.append(f"{location} selected value differs from {affected_id}")

    for rule_id, rule in rules_by_id.items():
        conflict_id = rule["conflict_id"]
        if conflict_id is None:
            if rule["validation_status"] == "project_resolved_with_conditions":
                errors.append(
                    f"{rule_locations[rule_id]} has project-resolved status without a conflict"
                )
            continue
        if conflict_id not in conflict_ids:
            errors.append(f"{rule_locations[rule_id]} references unknown conflict: {conflict_id}")
        elif rule_id not in conflicts[conflict_id]["affected_rule_ids"]:
            errors.append(
                f"{rule_locations[rule_id]} is absent from conflict {conflict_id}"
            )

    return errors


def runtime_eligibility_errors(
    ruleset: dict[str, Any],
    *,
    domain_errors: Optional[list[str]] = None,
) -> list[str]:
    """Return reasons a structurally valid ruleset may not be loaded at runtime."""

    errors: list[str] = []
    if domain_errors is None:
        domain_errors = validate_ruleset(ruleset)
    if domain_errors:
        errors.append("ruleset has schema or domain validation errors")
        return errors
    if ruleset.get("status") != "approved_for_prototype":
        errors.append("ruleset status is not approved_for_prototype")
    approved_on = ruleset.get("approved_on")
    if not valid_date(approved_on):
        errors.append("ruleset does not have a valid approved_on date")
    elif valid_date(ruleset.get("verified_through")) and date.fromisoformat(
        approved_on
    ) < date.fromisoformat(ruleset["verified_through"]):
        errors.append("approved_on predates verified_through")

    for zone, capability, rule in iter_regulations(ruleset):
        location = f"zones.{zone}.regulations.{capability}"
        if rule["approved_for_ruleset"] is not True:
            errors.append(f"{location} is not approved for the ruleset")
        if rule["validation_status"] == "candidate_unverified":
            errors.append(f"{location} remains candidate_unverified")

    for source_id, source in ruleset["shared"]["source_documents"].items():
        if source["verification_status"] == "candidate_unverified":
            errors.append(f"shared.source_documents.{source_id} remains unverified")
    return errors


def validate_crosswalk_component(
    target: dict[str, Any],
    rule: dict[str, Any],
    *,
    location: str,
    errors: list[str],
) -> None:
    component = target.get("component")
    if component == "requirement":
        return
    if component == "requirement.base":
        if rule["requirement"]["kind"] != "setback":
            errors.append(f"{location} points to base on a non-setback rule")
        return
    match = ADJUSTMENT_COMPONENT.fullmatch(component or "")
    if match is None:
        errors.append(f"{location} has unsupported target component: {component}")
        return
    if rule["requirement"]["kind"] != "setback":
        errors.append(f"{location} points to an adjustment on a non-setback rule")
        return
    adjustment_id = match.group(1)
    known_ids = {
        adjustment["adjustment_id"]
        for adjustment in rule["requirement"]["adjustments"]
    }
    if adjustment_id not in known_ids:
        errors.append(f"{location} points to unknown adjustment: {adjustment_id}")


def validate_migration(
    ruleset: dict[str, Any],
    crosswalk: dict[str, Any],
    source_v1: dict[str, Any],
    *,
    ruleset_path: Path = DEFAULT_RULESET,
    schema_path: Path = DEFAULT_SCHEMA,
    source_v1_path: Path = DEFAULT_V1_RULESET,
    repo_root: Path = REPO_ROOT,
) -> list[str]:
    """Return migration-manifest, crosswalk, checksum, and replay errors."""

    errors: list[str] = []
    if crosswalk.get("migration_id") != "santa-clara-r1-v1-to-v2":
        errors.append("migration_id is unsupported")
    if not valid_date(crosswalk.get("generated_on")):
        errors.append("generated_on must be an ISO date")
    expected_migration_status = (
        "approved_runtime_validated"
        if ruleset.get("status") == "approved_for_prototype"
        else "candidate_schema_validated"
    )
    if crosswalk.get("migration_status") != expected_migration_status:
        errors.append(
            f"migration_status must be {expected_migration_status}"
        )

    path_records = [
        ("source_ruleset", source_v1_path),
        ("target_ruleset", ruleset_path),
        ("target_schema", schema_path),
    ]
    for record_name, expected_path in path_records:
        record = crosswalk.get(record_name, {})
        if not isinstance(record, dict):
            errors.append(f"{record_name} must be an object")
            continue
        recorded_path = resolved_repo_path(repo_root, record.get("path"))
        if recorded_path is None:
            errors.append(f"{record_name}.path must remain inside the repository")
            continue
        if recorded_path != expected_path.resolve():
            errors.append(f"{record_name}.path does not match the validated artifact")
        if not expected_path.is_file():
            errors.append(f"{record_name} artifact is missing: {expected_path}")
        elif record.get("sha256") != sha256_file(expected_path):
            errors.append(f"{record_name}.sha256 does not match its artifact")

    source_record = crosswalk.get("source_ruleset", {})
    if not isinstance(source_record, dict):
        source_record = {}
    if source_record.get("version") != source_v1.get("version"):
        errors.append("source_ruleset.version does not match v1")
    if source_record.get("schema_version") != source_v1.get("schema_version"):
        errors.append("source_ruleset.schema_version does not match v1")
    target_record = crosswalk.get("target_ruleset", {})
    if isinstance(target_record, dict):
        for field in ("version", "schema_version", "status"):
            if target_record.get(field) != ruleset.get(field):
                errors.append(f"target_ruleset.{field} does not match v2")

    mappings = crosswalk.get("mappings")
    if not isinstance(mappings, list):
        return errors + ["mappings must be an array"]
    v1_ids = [rule["rule_id"] for rule in source_v1["rules"]]
    mapped_v1_ids: list[Any] = []
    for index, entry in enumerate(mappings):
        if not isinstance(entry, dict):
            errors.append(f"mappings[{index}] must be an object")
            continue
        mapped_v1_ids.append(entry.get("v1_rule_id"))
    duplicates = duplicate_values(mapped_v1_ids)
    if duplicates:
        errors.append(
            f"mappings contain duplicate v1 rule IDs: "
            f"{sorted(duplicates, key=str)}"
        )
    missing_v1 = set(v1_ids) - set(mapped_v1_ids)
    extra_v1 = set(mapped_v1_ids) - set(v1_ids)
    if missing_v1:
        errors.append(f"mappings omit v1 rules: {sorted(missing_v1)}")
    if extra_v1:
        errors.append(
            f"mappings reference unknown v1 rules: {sorted(extra_v1, key=str)}"
        )

    v2_rule_ids = {
        rule["rule_id"]
        for _, _, rule in iter_regulations(ruleset)
    }
    mapped_v2_rule_ids: set[str] = set()
    for index, entry in enumerate(mappings):
        if not isinstance(entry, dict):
            continue
        targets = entry.get("v2_targets")
        location = f"mappings[{index}]"
        if not isinstance(targets, list) or not targets:
            errors.append(f"{location}.v2_targets must be a non-empty array")
            continue
        for target_index, target in enumerate(targets):
            target_location = f"{location}.v2_targets[{target_index}]"
            if not isinstance(target, dict):
                errors.append(f"{target_location} must be an object")
                continue
            zone = target.get("zone")
            capability = target.get("capability_id")
            rule_id = target.get("rule_id")
            zone_record = ruleset["zones"].get(zone)
            if zone_record is None:
                errors.append(f"{target_location} references unknown zone: {zone}")
                continue
            rule = zone_record["regulations"].get(capability)
            if rule is None:
                errors.append(
                    f"{target_location} references unknown capability: {capability}"
                )
                continue
            if rule["rule_id"] != rule_id:
                errors.append(f"{target_location}.rule_id does not match target rule")
            else:
                mapped_v2_rule_ids.add(rule_id)
            validate_crosswalk_component(
                target,
                rule,
                location=target_location,
                errors=errors,
            )

    missing_v2 = v2_rule_ids - mapped_v2_rule_ids
    if missing_v2:
        errors.append(f"mappings omit v2 rules: {sorted(missing_v2)}")

    counts = crosswalk.get("counts", {})
    if not isinstance(counts, dict):
        errors.append("counts must be an object")
        counts = {}
    actual_counts = {
        "v1_rules": len(source_v1["rules"]),
        "mapped_v1_rules": len(mappings),
        "v2_zones": len(ruleset["zones"]),
        "v2_zone_regulations": len(v2_rule_ids),
        "v2_embedded_setback_adjustments": sum(
            len(rule["requirement"].get("adjustments", []))
            for _, _, rule in iter_regulations(ruleset)
        ),
        "conflicts": len(ruleset["conflicts"]),
    }
    for field, actual in actual_counts.items():
        if counts.get(field) != actual:
            errors.append(f"counts.{field} must be {actual}")

    v1_errors = validate_v1_ruleset(source_v1)
    if v1_errors:
        errors.extend(f"source v1: {error}" for error in v1_errors)
    reproduced, reproduced_mappings = migrate_ruleset(
        source_v1,
        version=ruleset["version"],
    )
    # Approval changes package eligibility, not the migrated legal content.
    reproduced["status"] = ruleset["status"]
    reproduced["approved_on"] = ruleset["approved_on"]
    if reproduced != ruleset:
        errors.append("v2 ruleset differs from deterministic migration replay")
    if reproduced_mappings != mappings:
        errors.append("crosswalk mappings differ from deterministic migration replay")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ruleset", type=Path, default=DEFAULT_RULESET)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--source-v1", type=Path, default=DEFAULT_V1_RULESET)
    parser.add_argument(
        "--verify-source-files",
        action="store_true",
        help="Require local source artifacts and verify their SHA-256 digests",
    )
    parser.add_argument(
        "--require-runtime-eligible",
        action="store_true",
        help="Fail unless the ruleset is approved, dated, and runtime-eligible",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ruleset_path = args.ruleset.resolve()
    schema_path = args.schema.resolve()
    crosswalk_path = args.crosswalk.resolve()
    source_v1_path = args.source_v1.resolve()

    ruleset = load_json(ruleset_path)
    schema = load_json(schema_path)
    crosswalk = load_json(crosswalk_path)
    source_v1 = load_json(source_v1_path)

    errors = validate_ruleset(
        ruleset,
        schema=schema,
        repo_root=REPO_ROOT,
        verify_source_files=args.verify_source_files,
    )
    migration_errors = validate_migration(
        ruleset,
        crosswalk,
        source_v1,
        ruleset_path=ruleset_path,
        schema_path=schema_path,
        source_v1_path=source_v1_path,
    )
    all_errors = errors + migration_errors
    if all_errors:
        print("R1 ruleset v2 validation failed:")
        for error in all_errors:
            print(f"- {error}")
        return 1

    regulation_count = sum(
        len(zone["regulations"]) for zone in ruleset["zones"].values()
    )
    print(
        f"R1 ruleset v2 {ruleset['version']} valid: "
        f"{regulation_count} zone-owned regulations, "
        f"{len(ruleset['conflicts'])} documented conflict, "
        f"complete migration crosswalk"
    )

    eligibility_errors = runtime_eligibility_errors(
        ruleset,
        domain_errors=all_errors,
    )
    if eligibility_errors:
        print("Runtime eligibility: no")
        for error in eligibility_errors:
            print(f"- {error}")
        return 1 if args.require_runtime_eligible else 0

    print(f"Runtime eligibility: yes (approved {ruleset['approved_on']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
