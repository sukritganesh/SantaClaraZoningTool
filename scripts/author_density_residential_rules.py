#!/usr/bin/env python3
"""Author the nonruntime R1-R6 gross-density ruleset successor.

The R1-R6 v3.1 candidate is an immutable predecessor. This deterministic,
non-overwriting author adds one typed gross residential density range to every
ordinary profile, retains the R5/R6 source conflicts, records the project-owner
Table 1-1 selections, and emits a checksum-pinned v3.2 lineage crosswalk.
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
    REPO_ROOT / "rulesets/santa_clara/residential/2026-07-19.2/ruleset.json"
)
DEFAULT_SOURCE_SCHEMA = REPO_ROOT / "rulesets/schema/ruleset-v3.1.schema.json"
DEFAULT_SCHEMA = REPO_ROOT / "rulesets/schema/ruleset-v3.2.schema.json"
DEFAULT_VERSION = "2026-07-19.3"
DEFAULT_OUTPUT_DIR = REPO_ROOT / f"rulesets/santa_clara/residential/{DEFAULT_VERSION}"
DEFAULT_CROSSWALK_NAME = "density-expansion-crosswalk.json"
DENSITY_CAPABILITY = "standard.gross_residential_density"
DENSITY_RANGES = {
    "R1-6L": (0.1, 10),
    "R1-8L": (0.1, 10),
    "R2": (8, 19),
    "R3": (20, 36),
    "R4": (37, 50),
    "R5": (51, 100),
    "R6": (60, 350),
}
CONFLICT_IDS = {
    "R5": "conflict-r5-gross-residential-density",
    "R6": "conflict-r6-gross-residential-density",
}


class DensityAuthoringError(RuntimeError):
    """Raised when the R1-R6 predecessor cannot be expanded exactly."""


def profile_rule_id(zone: str, profile: str) -> str:
    """Return the profile-owned gross-density rule identity."""

    return f"us.ca.santa_clara.{zone.lower()}.{profile}.{DENSITY_CAPABILITY}"


def range_value(minimum: float, maximum: float) -> dict[str, Any]:
    """Return a comparable density-range assertion value."""

    return {
        "kind": "quantity_range",
        "minimum": minimum,
        "maximum": maximum,
        "unit": "dwelling_units_per_acre",
    }


def density_rule(zone: str, profile: str) -> dict[str, Any]:
    """Return one nonapproved gross-density profile regulation."""

    minimum, maximum = DENSITY_RANGES[zone]
    conflict_id = CONFLICT_IDS.get(zone)
    source_refs = [
        "residential-density-table-1-1",
        "residential-density-table-2-3",
        "residential-density-plan-control",
        "residential-density-verification",
        "residential-density-amendment-audit",
    ]
    if conflict_id:
        source_refs.insert(1, "residential-density-zone-purpose")
    return {
        "rule_id": profile_rule_id(zone, profile),
        "label": "Gross residential density",
        "requirement": {
            **range_value(minimum, maximum),
            "source_refs": source_refs,
        },
        "applicability": {"lot_context": "all"},
        "conditions": [
            "This is a base-zone gross density range, not a parcel unit-yield calculation.",
            (
                "General Plan and applicable Master, Specific, or Area Plan controls "
                "are disclosed but not reconciled for a parcel."
            ),
            (
                "Density bonus, affordable-housing, development-agreement, and "
                "state-law adjustments are not evaluated."
            ),
        ],
        "exception_family_ids": [],
        "validation_status": (
            "project_resolved_with_conditions"
            if conflict_id
            else "verified_with_conditions"
        ),
        "conflict_id": conflict_id,
        "approved_for_ruleset": False,
    }


def add_density_sources(shared: dict[str, Any]) -> None:
    """Add checksum-pinned evidence and exact density citations."""

    verification_path = REPO_ROOT / "docs/residential-density-rule-verification.md"
    audit_path = REPO_ROOT / "docs/residential-density-title18-amendment-audit.md"
    shared["source_documents"].update(
        {
            "residential-density-verification-2026-07-19": {
                "title": "Santa Clara residential density rule verification",
                "version": "Project-owner decision July 19, 2026",
                "effective_date": None,
                "local_path": relative_path(verification_path),
                "sha256": sha256_file(verification_path),
                "verification_status": "verified_source_matrix",
            },
            "residential-density-amendment-audit-2026-07-18": {
                "title": "Santa Clara residential density amendment audit supplement",
                "version": "Cutoff July 18, 2026",
                "effective_date": None,
                "local_path": relative_path(audit_path),
                "sha256": sha256_file(audit_path),
                "verification_status": "verified_audit_artifact",
            },
        }
    )
    shared["citations"].update(
        {
            "residential-density-table-1-1": {
                "source_document_id": "sc-title18-2025-07",
                "locator": "Section 18.06.020, Table 1-1, PDF page 12 / printed page 1-10",
                "topic": "Zones implementing the General Plan and allowable residential density",
            },
            "residential-density-zone-purpose": {
                "source_document_id": "sc-title18-2025-07",
                "locator": "Section 18.10.010, PDF pages 19-20 / printed pages 2-1 to 2-2",
                "topic": "Residential zone purposes and density ranges",
            },
            "residential-density-table-2-3": {
                "source_document_id": "sc-title18-2025-07",
                "locator": "Section 18.10.030, Table 2-3, PDF page 25 / printed page 2-7",
                "topic": "Gross residential density development standard",
            },
            "residential-density-plan-control": {
                "source_document_id": "sc-title18-2025-07",
                "locator": "Sections 18.02.050(C) and 18.10.030(B)",
                "topic": "Density inconsistency and applicable-plan controls",
            },
            "residential-density-verification": {
                "source_document_id": "residential-density-verification-2026-07-19",
                "locator": "Capability boundary, source matrix, and approved conflict dispositions",
                "topic": "Gross-density verification and project decisions",
            },
            "residential-density-amendment-audit": {
                "source_document_id": "residential-density-amendment-audit-2026-07-18",
                "locator": "Finding and recheck triggers",
                "topic": "Post-baseline gross-density amendment status",
            },
        }
    )


def density_conflict(zone: str, affected_rule_ids: list[str]) -> dict[str, Any]:
    """Return the retained and project-resolved R5 or R6 source conflict."""

    if zone == "R5":
        assertions = [
            ("table-1-1-51-100", 51, 100, "residential-density-table-1-1", True),
            ("zone-purpose-51-99", 51, 99, "residential-density-zone-purpose", False),
            ("table-2-3-51-99", 51, 99, "residential-density-table-2-3", False),
        ]
        selected_id = "table-1-1-51-100"
        selected_value = range_value(51, 100)
    else:
        assertions = [
            ("table-1-1-60-350", 60, 350, "residential-density-table-1-1", True),
            ("zone-purpose-60-350", 60, 350, "residential-density-zone-purpose", False),
            ("table-2-3-85-350", 85, 350, "residential-density-table-2-3", False),
        ]
        selected_id = "table-1-1-60-350"
        selected_value = range_value(60, 350)
    return {
        "affected_rule_ids": affected_rule_ids,
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
            "selected_assertion_id": selected_id,
            "selected_value": selected_value,
            "rationale": (
                "The project owner directed the ruleset to retain every conflicting "
                "code assertion and use the Table 1-1 range for the candidate result."
            ),
            "decision_source": "Project owner direction in the July 19, 2026 Codex task",
            "decision_date": "2026-07-19",
            "status": "project_resolved_pending_official_clarification",
            "re_review_triggers": [
                "Official City or codifier clarification of the density discrepancy",
                "A newly consolidated Title 18 edition",
                "An adopted amendment affecting any cited density provision",
                "Parcel-specific General Plan or applicable plan reconciliation",
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
    """Return the deterministic v3.2 density successor."""

    if source.get("schema_version") != "3.1.0":
        raise DensityAuthoringError("Density authoring requires a schema 3.1.0 predecessor")
    if source.get("version") != "2026-07-19.2":
        raise DensityAuthoringError("Density authoring requires predecessor 2026-07-19.2")
    if source.get("status") != "candidate":
        raise DensityAuthoringError("Density authoring requires the nonruntime candidate")

    if crosswalk_path is None:
        crosswalk_path = (
            "rulesets/santa_clara/residential/2026-07-19.3/"
            "density-expansion-crosswalk.json"
        )
    target = copy.deepcopy(source)
    target["$schema"] = "../../../schema/ruleset-v3.2.schema.json"
    target["schema_version"] = "3.2.0"
    target["version"] = version
    target["scope"]["description"] = (
        "Nonruntime selected residential standards candidate containing the accepted R1 migration, "
        "the owner-approved R2-R6 citywide tranche, and owner-approved base-zone gross density ranges; "
        "Patrick Henry zones remain intentionally unauthored."
    )
    target["predecessor_rulesets"] = [
        {
            "ruleset_id": source["ruleset_id"],
            "version": source["version"],
            "sha256": sha256_file(source_path),
            "crosswalk_path": crosswalk_path,
        }
    ]
    add_density_sources(target["shared"])

    target["not_evaluated_topics"]["density_and_state_law_overrides"].update(
        {
            "label": "Density adjustments, yield, and state-law overrides",
            "explanation": (
                "The base-zone gross density range is supported, but parcel yield, plan reconciliation, density bonus, affordable-housing, and state-law adjustments remain outside the evaluator."
            ),
            "source_refs": ["residential-density-verification"],
        }
    )
    target["not_evaluated_topics"]["citywide_density_and_state_law_overrides"].update(
        {
            "label": "Density adjustments, yield, and state-law overrides",
            "explanation": (
                "The base-zone gross density range is supported, but parcel yield, plan reconciliation, density bonus, affordable-housing, and state-law adjustments remain outside the evaluator."
            ),
            "source_refs": ["residential-density-verification"],
        }
    )

    for zone, zone_record in target["zones"].items():
        for profile_id, profile in zone_record["analysis_profiles"].items():
            profile["regulations"][DENSITY_CAPABILITY] = density_rule(zone, profile_id)
            if zone == "R2" and profile_id == "single_family":
                profile["not_evaluated_topic_ids"].append(
                    "citywide_density_and_state_law_overrides"
                )

    for zone, conflict_id in CONFLICT_IDS.items():
        affected = [
            profile_rule_id(zone, profile_id)
            for profile_id in target["zones"][zone]["analysis_profiles"]
        ]
        target["conflicts"][conflict_id] = density_conflict(zone, affected)
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
    """Build the checksum-pinned v3.1-to-v3.2 density crosswalk."""

    return {
        "crosswalk_version": "1.0.0",
        "migration_id": "santa-clara-residential-v3-add-gross-density-r1-r6",
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
            "added_profile_regulations": 11,
            "modified_not_evaluated_topics": 2,
            "added_profile_topic_references": 1,
            "carried_conflicts": len(source["conflicts"]),
            "added_conflicts": 2,
        },
        "preserved_components": [
            {
                "component_path": f"zones.{zone}.use_permissions",
                "sha256": component_hash(record["use_permissions"]),
            }
            for zone, record in source["zones"].items()
        ]
        + [
            {
                "component_path": f"conflicts.{conflict_id}",
                "sha256": component_hash(conflict),
            }
            for conflict_id, conflict in source["conflicts"].items()
        ],
        "added_capability": DENSITY_CAPABILITY,
        "added_rule_ids": [
            profile_rule_id(zone, profile_id)
            for zone, record in target["zones"].items()
            for profile_id in record["analysis_profiles"]
        ],
        "allowed_ruleset_changes": [
            "Advance the closed authoring contract from schema 3.1.0 to additive schema 3.2.0.",
            "Add one gross residential density range to each of 11 ordinary R1-R6 profiles.",
            "Retain and project-resolve the R5 and R6 density conflicts using Table 1-1 values.",
            "Update density limitation topics to distinguish base-range support from deferred yield and adjustments.",
            "Add checksum-pinned density verification, audit, and citation records.",
            "Retain candidate status, null approval, and false rule approvals pending the complete target matrix.",
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
    """Return density lineage, preservation, checksum, and replay errors."""

    errors: list[str] = []
    if crosswalk.get("migration_id") != (
        "santa-clara-residential-v3-add-gross-density-r1-r6"
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
        target_zone = target["zones"].get(zone, {})
        if target_zone.get("use_permissions") != source_zone["use_permissions"]:
            errors.append(f"target changed predecessor use permissions for {zone}")
        if target_zone.get("special_pathways") != source_zone["special_pathways"]:
            errors.append(f"target changed predecessor special pathways for {zone}")
        for profile_id, source_profile in source_zone["analysis_profiles"].items():
            target_profile = target_zone.get("analysis_profiles", {}).get(profile_id, {})
            for field in (
                "workflow_family",
                "legal_use_capability_id",
                "primary_structure_type",
            ):
                if target_profile.get(field) != source_profile[field]:
                    errors.append(f"target changed {zone}.{profile_id}.{field}")
            for capability, source_rule in source_profile["regulations"].items():
                if target_profile.get("regulations", {}).get(capability) != source_rule:
                    errors.append(
                        f"target changed predecessor regulation {zone}.{profile_id}.{capability}"
                    )

    for conflict_id, conflict in source["conflicts"].items():
        if target["conflicts"].get(conflict_id) != conflict:
            errors.append(f"target changed predecessor conflict {conflict_id}")
    for group in ("source_documents", "citations", "definitions", "exception_families"):
        for record_id, record in source["shared"][group].items():
            if target["shared"][group].get(record_id) != record:
                errors.append(f"target changed shared predecessor record {group}.{record_id}")
    for topic_id, topic in source["not_evaluated_topics"].items():
        if topic_id in {
            "density_and_state_law_overrides",
            "citywide_density_and_state_law_overrides",
        }:
            continue
        if target["not_evaluated_topics"].get(topic_id) != topic:
            errors.append(f"target changed predecessor topic {topic_id}")

    if set(target.get("zones", {})) != set(source["zones"]):
        errors.append("target zone set differs from the R1-R6 predecessor")
    if set(target.get("conflicts", {})) != set(source["conflicts"]) | set(CONFLICT_IDS.values()):
        errors.append("target conflicts do not contain exactly the predecessor and density conflicts")
    for zone, zone_record in target.get("zones", {}).items():
        for profile_id, profile in zone_record["analysis_profiles"].items():
            rule = profile["regulations"].get(DENSITY_CAPABILITY)
            if not isinstance(rule, dict):
                errors.append(f"{zone}.{profile_id} lacks gross residential density")
                continue
            if (rule["requirement"]["minimum"], rule["requirement"]["maximum"]) != DENSITY_RANGES[zone]:
                errors.append(f"{zone}.{profile_id} has the wrong gross-density range")

    reproduced = expand_ruleset(
        source,
        source_path=source_path,
        version=target["version"],
        crosswalk_path=target["predecessor_rulesets"][0]["crosswalk_path"],
    )
    if reproduced != target:
        errors.append("target ruleset differs from deterministic density authoring replay")
    reproduced_crosswalk = build_crosswalk(
        source=source,
        source_path=source_path,
        target=target,
        target_path=target_path,
        schema_path=schema_path,
        target_bytes=json_bytes(target),
    )
    if reproduced_crosswalk != crosswalk:
        errors.append("crosswalk differs from deterministic density authoring replay")
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
    """Validate the predecessor and write a new density candidate."""

    args = parse_args(argv)
    source_path = args.source.resolve()
    source_schema_path = args.source_schema.resolve()
    schema_path = args.schema.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise DensityAuthoringError(
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
        raise DensityAuthoringError(
            "R1-R6 predecessor failed validation:\n" + "\n".join(source_errors)
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
        raise DensityAuthoringError(
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
        raise DensityAuthoringError(
            "Written density expansion failed replay validation:\n" + "\n".join(errors)
        )
    print(f"Authored nonruntime R1-R6 density candidate: {target_path}")
    print(f"Density expansion crosswalk: {crosswalk_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
