#!/usr/bin/env python3
"""Migrate the approved Santa Clara R1 ruleset from v1 to candidate v2.

The migration is deterministic and non-overwriting. It validates the approved
v1 input, emits zone-owned v2 records, validates the v2 schema, and records a
complete v1-to-v2 crosswalk before writing a new versioned directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Optional

from jsonschema import Draft202012Validator, FormatChecker


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_r1_rules import validate_ruleset as validate_v1_ruleset


DEFAULT_SOURCE = (
    REPO_ROOT / "rulesets/santa_clara/r1/2026-07-16/ruleset.json"
)
DEFAULT_V2_SCHEMA = REPO_ROOT / "rulesets/schema/ruleset-v2.schema.json"
RULESET_PARENT = REPO_ROOT / "rulesets/santa_clara/r1"
ZONES = ("R1-6L", "R1-8L")
STRUCTURE_TYPE = "single_family_primary_structure"


class MigrationError(RuntimeError):
    """Raised when the approved v1 data cannot be migrated without ambiguity."""


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise MigrationError(f"Expected a JSON object at {path}")
    return value


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def ordered_union(*groups: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            if item not in seen:
                result.append(item)
                seen.add(item)
    return result


def keyed_records(records: list[dict[str, Any]], id_field: str) -> dict[str, Any]:
    keyed: dict[str, Any] = {}
    for record in records:
        record_id = record.get(id_field)
        if not isinstance(record_id, str) or not record_id:
            raise MigrationError(f"Missing {id_field} in shared v1 record")
        if record_id in keyed:
            raise MigrationError(f"Duplicate {id_field}: {record_id}")
        keyed[record_id] = {key: value for key, value in record.items() if key != id_field}
    return keyed


def rule_id(zone: str, capability_id: str) -> str:
    return f"us.ca.santa_clara.{zone.lower()}.{capability_id}"


def validation_status(rules: Iterable[dict[str, Any]]) -> str:
    priority = {
        "candidate_unverified": 0,
        "verified_base_value": 1,
        "verified_with_conditions": 2,
        "project_resolved_with_conditions": 3,
    }
    statuses = [rule["validation_status"] for rule in rules]
    try:
        return max(statuses, key=priority.__getitem__)
    except KeyError as exc:
        raise MigrationError(f"Unsupported validation status: {exc.args[0]}") from exc


def v2_setback_value(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("kind") == "number" and value.get("unit") == "ft":
        return {"kind": "distance", "number": value["number"], "unit": "ft"}
    if value.get("kind") == "paired_numbers" and value.get("unit") == "ft":
        numbers = value.get("numbers")
        if not isinstance(numbers, list) or len(numbers) != 2:
            raise MigrationError("Paired setback must contain exactly two values")
        return {
            "kind": "paired_distances",
            "members": [
                {"role": "smaller_setback", "number": numbers[0], "unit": "ft"},
                {"role": "larger_setback", "number": numbers[1], "unit": "ft"},
            ],
            "relationship": "coordinated_pair",
            "physical_assignment": "proposal_dependent",
        }
    raise MigrationError(f"Cannot convert v1 value to a setback: {value!r}")


def common_regulation(
    *,
    zone: str,
    capability_id: str,
    label: str,
    source_rules: list[dict[str, Any]],
    requirement: dict[str, Any],
    lot_context: str,
) -> dict[str, Any]:
    conflict_ids = {
        rule["conflict_id"]
        for rule in source_rules
        if rule.get("conflict_id") is not None
    }
    if len(conflict_ids) > 1:
        raise MigrationError(
            f"{zone} {capability_id} references multiple conflicts: {conflict_ids}"
        )
    if not all(rule.get("approved_for_ruleset") is True for rule in source_rules):
        raise MigrationError(f"Unapproved v1 input for {zone} {capability_id}")

    return {
        "rule_id": rule_id(zone, capability_id),
        "label": label,
        "requirement": requirement,
        "applicability": {
            "structure_type": STRUCTURE_TYPE,
            "lot_context": lot_context,
        },
        "conditions": ordered_union(
            *(rule.get("conditions", []) for rule in source_rules)
        ),
        "exception_family_ids": ordered_union(
            *(rule.get("exception_family_ids", []) for rule in source_rules)
        ),
        "validation_status": validation_status(source_rules),
        "conflict_id": next(iter(conflict_ids), None),
        "approved_for_ruleset": True,
    }


def status_requirement(rule: dict[str, Any]) -> dict[str, Any]:
    value = rule["value"]
    if value.get("kind") != "status":
        raise MigrationError(f"Expected status value for {rule['rule_id']}")
    return {
        "kind": "status",
        "code": value["code"],
        "source_refs": list(rule["source_refs"]),
    }


def maximum_requirement(rule: dict[str, Any]) -> dict[str, Any]:
    value = rule["value"]
    if value.get("kind") != "number":
        raise MigrationError(f"Expected numeric value for {rule['rule_id']}")
    return {
        "kind": "maximum_quantity",
        "value": {"number": value["number"], "unit": value["unit"]},
        "source_refs": list(rule["source_refs"]),
    }


def setback_requirement(
    base_rule: dict[str, Any],
    adjustment_rule: Optional[dict[str, Any]] = None,
    *,
    base_source_rules: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    source_rules = base_source_rules or [base_rule]
    requirement: dict[str, Any] = {
        "kind": "setback",
        "base": {
            "value": v2_setback_value(base_rule["value"]),
            "source_refs": ordered_union(
                *(rule["source_refs"] for rule in source_rules)
            ),
        },
        "adjustments": [],
    }
    if adjustment_rule is not None:
        paired = adjustment_rule["value"].get("kind") == "paired_numbers"
        requirement["adjustments"].append(
            {
                "adjustment_id": (
                    "second-story-total-pair" if paired else "second-story-total"
                ),
                "trigger": {"kind": "story_at_or_above", "story": 2},
                "effect": {
                    "kind": "replace_total_minimum",
                    "value": v2_setback_value(adjustment_rule["value"]),
                },
                "source_refs": list(adjustment_rule["source_refs"]),
            }
        )
    return requirement


def migrate_ruleset(
    source: dict[str, Any],
    *,
    version: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rules = source.get("rules")
    if not isinstance(rules, list):
        raise MigrationError("v1 rules must be an array")
    rules_by_id = {rule["rule_id"]: rule for rule in rules}
    if len(rules_by_id) != len(rules):
        raise MigrationError("v1 rule IDs are not unique")

    mappings: dict[str, list[dict[str, str]]] = {
        rule_id: [] for rule_id in rules_by_id
    }

    def source_rule(v1_rule_id: str) -> dict[str, Any]:
        try:
            return rules_by_id[v1_rule_id]
        except KeyError as exc:
            raise MigrationError(f"Required v1 rule is missing: {v1_rule_id}") from exc

    def map_rule(
        v1_rule_id: str,
        zone: str,
        capability_id: str,
        component: str,
    ) -> None:
        if v1_rule_id not in mappings:
            raise MigrationError(f"Cannot map unknown v1 rule: {v1_rule_id}")
        mappings[v1_rule_id].append(
            {
                "zone": zone,
                "capability_id": capability_id,
                "rule_id": rule_id(zone, capability_id),
                "component": component,
            }
        )

    shared_status = [
        (
            "use-single-family-dwelling",
            "use.single_family_dwelling",
            "Single-family dwelling",
        ),
        (
            "approval-zoning-clearance",
            "approval.zoning_clearance",
            "Zoning Clearance",
        ),
        (
            "approval-architectural-review",
            "approval.architectural_review",
            "Architectural Review",
        ),
    ]
    shared_maximums = [
        (
            "standard-max-primary-height",
            "standard.maximum_primary_structure_height",
            "Maximum primary-structure height",
        ),
        (
            "standard-max-stories",
            "standard.maximum_stories",
            "Maximum stories",
        ),
        (
            "standard-max-structure-coverage",
            "standard.maximum_structure_coverage",
            "Maximum structure coverage",
        ),
    ]

    zones: dict[str, Any] = {}
    for zone in ZONES:
        regulations: dict[str, Any] = {}

        for v1_id, capability_id, label in shared_status:
            rule = source_rule(v1_id)
            regulations[capability_id] = common_regulation(
                zone=zone,
                capability_id=capability_id,
                label=label,
                source_rules=[rule],
                requirement=status_requirement(rule),
                lot_context="not_applicable",
            )
            map_rule(v1_id, zone, capability_id, "requirement")

        for v1_id, capability_id, label in shared_maximums:
            rule = source_rule(v1_id)
            regulations[capability_id] = common_regulation(
                zone=zone,
                capability_id=capability_id,
                label=label,
                source_rules=[rule],
                requirement=maximum_requirement(rule),
                lot_context="all",
            )
            map_rule(v1_id, zone, capability_id, "requirement")

        front_base = source_rule("standard-front-setback-first")
        front_second = source_rule("standard-front-setback-second")
        regulations["setback.front"] = common_regulation(
            zone=zone,
            capability_id="setback.front",
            label="Front setback",
            source_rules=[front_base, front_second],
            requirement=setback_requirement(front_base, front_second),
            lot_context="all",
        )
        map_rule(front_base["rule_id"], zone, "setback.front", "requirement.base")
        map_rule(
            front_second["rule_id"],
            zone,
            "setback.front",
            "requirement.adjustments[second-story-total]",
        )

        interior_base = source_rule(
            f"standard-interior-side-first-{zone.lower()}"
        )
        interior_second = source_rule(
            f"standard-interior-side-second-{zone.lower()}"
        )
        regulations["setback.interior_side"] = common_regulation(
            zone=zone,
            capability_id="setback.interior_side",
            label="Interior-side setback",
            source_rules=[interior_base, interior_second],
            requirement=setback_requirement(interior_base, interior_second),
            lot_context="all",
        )
        map_rule(
            interior_base["rule_id"],
            zone,
            "setback.interior_side",
            "requirement.base",
        )
        map_rule(
            interior_second["rule_id"],
            zone,
            "setback.interior_side",
            (
                "requirement.adjustments[second-story-total-pair]"
                if interior_second["value"].get("kind") == "paired_numbers"
                else "requirement.adjustments[second-story-total]"
            ),
        )

        street_base = source_rule(f"standard-corner-side-first-{zone.lower()}")
        street_second = source_rule("standard-corner-side-second")
        if zone == "R1-6L":
            street_requirement = setback_requirement(street_base, street_second)
            second_component = "requirement.adjustments[second-story-total]"
        else:
            # The R1-8L-specific narrative and conflict resolution establish a
            # 15-foot base for all stories; the table's second-story 15-foot
            # assertion remains represented through the base source references.
            street_requirement = setback_requirement(
                street_base,
                base_source_rules=[street_base, street_second],
            )
            second_component = "requirement.base"
        regulations["setback.street_side"] = common_regulation(
            zone=zone,
            capability_id="setback.street_side",
            label="Street-side (corner-side) setback",
            source_rules=[street_base, street_second],
            requirement=street_requirement,
            lot_context="corner",
        )
        map_rule(
            street_base["rule_id"],
            zone,
            "setback.street_side",
            "requirement.base",
        )
        map_rule(
            street_second["rule_id"],
            zone,
            "setback.street_side",
            second_component,
        )

        rear = source_rule("standard-rear-setback")
        regulations["setback.rear"] = common_regulation(
            zone=zone,
            capability_id="setback.rear",
            label="Rear setback",
            source_rules=[rear],
            requirement=setback_requirement(rear),
            lot_context="all",
        )
        map_rule(rear["rule_id"], zone, "setback.rear", "requirement.base")

        zones[zone] = {"regulations": regulations}

    unmapped = sorted(rule_id for rule_id, targets in mappings.items() if not targets)
    if unmapped:
        raise MigrationError(f"Unmapped approved v1 rules: {unmapped}")

    source_documents = keyed_records(
        source["source_documents"], "source_document_id"
    )
    citations = keyed_records(source["citations"], "citation_id")
    exception_families = keyed_records(
        source["exception_families"], "exception_family_id"
    )

    conflicts: dict[str, Any] = {}
    for conflict in source["conflicts"]:
        conflict_id = conflict["conflict_id"]
        migrated = {
            "affected_rule_ids": [
                rule_id("R1-8L", "setback.street_side")
            ],
            "assertions": [
                {
                    **{
                        key: value
                        for key, value in assertion.items()
                        if key != "value"
                    },
                    "value": v2_setback_value(assertion["value"]),
                }
                for assertion in conflict["assertions"]
            ],
            "resolution": {
                **{
                    key: value
                    for key, value in conflict["resolution"].items()
                    if key != "selected_value"
                },
                "selected_value": v2_setback_value(
                    conflict["resolution"]["selected_value"]
                ),
            },
        }
        conflicts[conflict_id] = migrated

    candidate = {
        "$schema": "../../../schema/ruleset-v2.schema.json",
        "schema_version": "2.0.0",
        "ruleset_id": source["ruleset_id"],
        "version": version,
        "jurisdiction": {
            "name": source["jurisdiction"]["name"],
            "slug": "santa_clara",
            "state": source["jurisdiction"]["state"],
            "country": source["jurisdiction"]["country"],
        },
        "status": "candidate",
        "approved_on": None,
        "verified_through": source["verified_through"],
        "scope": {
            "description": source["scope"]["description"],
            "structure_types": [source["scope"]["structure_type"]],
            "result_kind": source["scope"]["result_kind"],
        },
        "shared": {
            "source_documents": source_documents,
            "citations": citations,
            "definitions": {},
            "exception_families": exception_families,
        },
        "zones": zones,
        "conflicts": conflicts,
        "not_evaluated": list(source["not_evaluated"]),
        "disclaimer": source["disclaimer"],
    }
    crosswalk = [
        {"v1_rule_id": rule["rule_id"], "v2_targets": mappings[rule["rule_id"]]}
        for rule in rules
    ]
    return candidate, crosswalk


def schema_errors(candidate: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"{error.json_path}: {error.message}"
        for error in sorted(
            validator.iter_errors(candidate), key=lambda item: item.json_path
        )
    ]


def build_crosswalk_manifest(
    *,
    source_path: Path,
    source: dict[str, Any],
    schema_path: Path,
    target_path: Path,
    candidate: dict[str, Any],
    target_bytes: bytes,
    mappings: list[dict[str, Any]],
) -> dict[str, Any]:
    regulation_count = sum(
        len(zone["regulations"]) for zone in candidate["zones"].values()
    )
    adjustment_count = sum(
        len(regulation["requirement"].get("adjustments", []))
        for zone in candidate["zones"].values()
        for regulation in zone["regulations"].values()
    )
    return {
        "migration_id": "santa-clara-r1-v1-to-v2",
        "generated_on": date.today().isoformat(),
        "migration_status": "candidate_schema_validated",
        "source_ruleset": {
            "path": relative_path(source_path),
            "version": source["version"],
            "schema_version": source["schema_version"],
            "sha256": sha256_file(source_path),
        },
        "target_ruleset": {
            "path": relative_path(target_path),
            "version": candidate["version"],
            "schema_version": candidate["schema_version"],
            "status": candidate["status"],
            "sha256": sha256_bytes(target_bytes),
        },
        "target_schema": {
            "path": relative_path(schema_path),
            "sha256": sha256_file(schema_path),
        },
        "counts": {
            "v1_rules": len(source["rules"]),
            "mapped_v1_rules": len(mappings),
            "v2_zones": len(candidate["zones"]),
            "v2_zone_regulations": regulation_count,
            "v2_embedded_setback_adjustments": adjustment_count,
            "conflicts": len(candidate["conflicts"]),
        },
        "mappings": mappings,
        "migration_notes": [
            "Every approved v1 rule has at least one explicit v2 target.",
            "Equal values were duplicated into independent zone-owned records.",
            "V1 contained no structured definition records; v2 definitions remain empty.",
            "R1-6L street-side setback is 10 feet at base and 15 feet from story two.",
            "R1-8L street-side setback selects 15 feet while preserving the 10-foot and 15-foot assertions in the conflict record.",
            "The target remains a candidate until expanded v2 domain validation passes.",
        ],
    }


def parse_args() -> argparse.Namespace:
    today = date.today().isoformat()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--schema", type=Path, default=DEFAULT_V2_SCHEMA)
    parser.add_argument("--version", default=f"{today}.1")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=RULESET_PARENT / today,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = args.source.resolve()
    schema_path = args.schema.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise MigrationError(
            f"Destination already exists; choose a new version directory: {output_dir}"
        )

    source = load_json(source_path)
    v1_errors = validate_v1_ruleset(source, verify_source_files=True)
    if v1_errors:
        raise MigrationError("Approved v1 input is invalid:\n" + "\n".join(v1_errors))

    schema = load_json(schema_path)
    candidate, mappings = migrate_ruleset(source, version=args.version)
    v2_errors = schema_errors(candidate, schema)
    if v2_errors:
        raise MigrationError("Candidate v2 output is invalid:\n" + "\n".join(v2_errors))

    target_path = output_dir / "ruleset.json"
    target_bytes = json_bytes(candidate)
    manifest = build_crosswalk_manifest(
        source_path=source_path,
        source=source,
        schema_path=schema_path,
        target_path=target_path,
        candidate=candidate,
        target_bytes=target_bytes,
        mappings=mappings,
    )

    output_dir.mkdir(parents=True)
    target_path.write_bytes(target_bytes)
    (output_dir / "migration-crosswalk.json").write_bytes(json_bytes(manifest))

    print(f"Wrote candidate v2 ruleset: {relative_path(target_path)}")
    regulation_count = sum(
        len(zone["regulations"]) for zone in candidate["zones"].values()
    )
    print(
        f"Mapped {len(mappings)} v1 rules to "
        f"{regulation_count} zone-owned v2 regulations"
    )
    print("Candidate is schema-valid but is not yet the operational ruleset")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
