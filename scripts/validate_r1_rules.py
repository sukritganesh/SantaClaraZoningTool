#!/usr/bin/env python3
"""Validate the versioned Santa Clara R1 prototype ruleset.

The repository remains dependency-free. This validator enforces the ruleset's
cross-record and zoning-specific invariants; the accompanying JSON Schema is
available for tools that support JSON Schema Draft 2020-12.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULESET = (
    REPO_ROOT / "rulesets/santa_clara/r1/2026-07-16/ruleset.json"
)
DEFAULT_SCHEMA = REPO_ROOT / "rulesets/schema/r1-ruleset.schema.json"
SUPPORTED_ZONES = {"R1-6L", "R1-8L"}
ROOT_KEYS = {
    "$schema",
    "schema_version",
    "ruleset_id",
    "version",
    "jurisdiction",
    "status",
    "approved_on",
    "verified_through",
    "scope",
    "supported_zones",
    "source_documents",
    "citations",
    "exception_families",
    "rules",
    "conflicts",
    "not_evaluated",
    "disclaimer",
}


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object and reject non-object roots."""

    with path.open(encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object at {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def duplicate_values(values: Iterable[Any]) -> set[Any]:
    seen: set[Any] = set()
    duplicates: set[Any] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def valid_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def validate_rule_value(value: Any, location: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{location} must be an object")
        return

    kind = value.get("kind")
    if kind == "number":
        if set(value) != {"kind", "number", "unit"}:
            errors.append(f"{location} has invalid number-value fields")
        number = value.get("number")
        if not isinstance(number, (int, float)) or isinstance(number, bool) or number < 0:
            errors.append(f"{location}.number must be a non-negative number")
        if value.get("unit") not in {"ft", "percent", "stories"}:
            errors.append(f"{location}.unit is unsupported")
    elif kind == "paired_numbers":
        expected = {"kind", "numbers", "unit", "relationship"}
        if set(value) != expected:
            errors.append(f"{location} has invalid paired-number fields")
        numbers = value.get("numbers")
        if (
            not isinstance(numbers, list)
            or len(numbers) != 2
            or any(
                not isinstance(number, (int, float))
                or isinstance(number, bool)
                or number < 0
                for number in numbers
            )
        ):
            errors.append(f"{location}.numbers must contain two non-negative numbers")
        if value.get("unit") != "ft":
            errors.append(f"{location}.unit must be ft")
        if value.get("relationship") != "required_paired_yards":
            errors.append(f"{location}.relationship is unsupported")
    elif kind == "status":
        if set(value) != {"kind", "code"}:
            errors.append(f"{location} has invalid status fields")
        if value.get("code") not in {
            "permitted_by_right",
            "required",
            "may_be_required",
        }:
            errors.append(f"{location}.code is unsupported")
    else:
        errors.append(f"{location}.kind is unsupported")


def validate_ruleset(
    ruleset: dict[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    verify_source_files: bool = False,
) -> list[str]:
    """Return all structural, reference, and domain validation errors."""

    errors: list[str] = []
    missing_keys = ROOT_KEYS - set(ruleset)
    extra_keys = set(ruleset) - ROOT_KEYS
    if missing_keys:
        errors.append(f"Missing root fields: {sorted(missing_keys)}")
    if extra_keys:
        errors.append(f"Unexpected root fields: {sorted(extra_keys)}")

    if ruleset.get("schema_version") != "1.0.0":
        errors.append("schema_version must be 1.0.0")
    if ruleset.get("status") != "approved_for_prototype":
        errors.append("status must be approved_for_prototype")
    for field in ("approved_on", "verified_through"):
        if not valid_date(ruleset.get(field)):
            errors.append(f"{field} must be an ISO date")

    zones = ruleset.get("supported_zones")
    if not isinstance(zones, list) or set(zones) != SUPPORTED_ZONES or len(zones) != 2:
        errors.append("supported_zones must contain exactly R1-6L and R1-8L")

    source_documents = ruleset.get("source_documents")
    if not isinstance(source_documents, list):
        errors.append("source_documents must be an array")
        source_documents = []
    source_ids = [item.get("source_document_id") for item in source_documents if isinstance(item, dict)]
    duplicates = duplicate_values(source_ids)
    if duplicates:
        errors.append(f"Duplicate source_document_id values: {sorted(duplicates)}")
    source_id_set = set(source_ids)

    for index, source_document in enumerate(source_documents):
        location = f"source_documents[{index}]"
        if not isinstance(source_document, dict):
            errors.append(f"{location} must be an object")
            continue
        sha256 = source_document.get("sha256")
        if not isinstance(sha256, str) or len(sha256) != 64:
            errors.append(f"{location}.sha256 must be a 64-character digest")
        effective_date = source_document.get("effective_date")
        if effective_date is not None and not valid_date(effective_date):
            errors.append(f"{location}.effective_date must be null or an ISO date")
        if verify_source_files:
            relative_path = source_document.get("local_path")
            if not isinstance(relative_path, str):
                errors.append(f"{location}.local_path must be a string")
                continue
            source_path = repo_root / relative_path
            if not source_path.is_file():
                errors.append(f"{location} source file is missing: {relative_path}")
            elif sha256_file(source_path) != sha256:
                errors.append(f"{location} checksum does not match: {relative_path}")

    citations = ruleset.get("citations")
    if not isinstance(citations, list):
        errors.append("citations must be an array")
        citations = []
    citation_ids = [item.get("citation_id") for item in citations if isinstance(item, dict)]
    duplicates = duplicate_values(citation_ids)
    if duplicates:
        errors.append(f"Duplicate citation_id values: {sorted(duplicates)}")
    citation_id_set = set(citation_ids)
    for index, citation in enumerate(citations):
        if not isinstance(citation, dict):
            errors.append(f"citations[{index}] must be an object")
            continue
        if citation.get("source_document_id") not in source_id_set:
            errors.append(f"citations[{index}] references an unknown source document")

    exception_families = ruleset.get("exception_families")
    if not isinstance(exception_families, list):
        errors.append("exception_families must be an array")
        exception_families = []
    exception_ids = [
        item.get("exception_family_id")
        for item in exception_families
        if isinstance(item, dict)
    ]
    duplicates = duplicate_values(exception_ids)
    if duplicates:
        errors.append(f"Duplicate exception_family_id values: {sorted(duplicates)}")
    exception_id_set = set(exception_ids)
    for index, family in enumerate(exception_families):
        if not isinstance(family, dict):
            errors.append(f"exception_families[{index}] must be an object")
            continue
        if family.get("treatment") != "not_evaluated":
            errors.append(f"exception_families[{index}].treatment must be not_evaluated")
        unknown_refs = set(family.get("source_refs", [])) - citation_id_set
        if unknown_refs:
            errors.append(
                f"exception_families[{index}] has unknown source refs: {sorted(unknown_refs)}"
            )

    rules = ruleset.get("rules")
    if not isinstance(rules, list):
        errors.append("rules must be an array")
        rules = []
    rule_ids = [item.get("rule_id") for item in rules if isinstance(item, dict)]
    duplicates = duplicate_values(rule_ids)
    if duplicates:
        errors.append(f"Duplicate rule_id values: {sorted(duplicates)}")
    rule_id_set = set(rule_ids)

    conflicts = ruleset.get("conflicts")
    if not isinstance(conflicts, list):
        errors.append("conflicts must be an array")
        conflicts = []
    conflict_ids = [item.get("conflict_id") for item in conflicts if isinstance(item, dict)]
    duplicates = duplicate_values(conflict_ids)
    if duplicates:
        errors.append(f"Duplicate conflict_id values: {sorted(duplicates)}")
    conflict_id_set = set(conflict_ids)

    for index, rule in enumerate(rules):
        location = f"rules[{index}]"
        if not isinstance(rule, dict):
            errors.append(f"{location} must be an object")
            continue
        validate_rule_value(rule.get("value"), f"{location}.value", errors)
        applicability = rule.get("applicability")
        if not isinstance(applicability, dict):
            errors.append(f"{location}.applicability must be an object")
        else:
            rule_zones = applicability.get("zones")
            if not isinstance(rule_zones, list) or not rule_zones:
                errors.append(f"{location}.applicability.zones must be a non-empty array")
            elif not set(rule_zones) <= SUPPORTED_ZONES:
                errors.append(f"{location} applies to an unsupported zone")
        if rule.get("approved_for_ruleset") is not True:
            errors.append(f"{location} is not approved for the ruleset")
        unknown_sources = set(rule.get("source_refs", [])) - citation_id_set
        if unknown_sources:
            errors.append(f"{location} has unknown source refs: {sorted(unknown_sources)}")
        unknown_exceptions = set(rule.get("exception_family_ids", [])) - exception_id_set
        if unknown_exceptions:
            errors.append(
                f"{location} has unknown exception families: {sorted(unknown_exceptions)}"
            )
        conflict_id = rule.get("conflict_id")
        if conflict_id is not None and conflict_id not in conflict_id_set:
            errors.append(f"{location} references an unknown conflict")

    rules_by_id = {
        rule["rule_id"]: rule
        for rule in rules
        if isinstance(rule, dict) and isinstance(rule.get("rule_id"), str)
    }
    for index, conflict in enumerate(conflicts):
        location = f"conflicts[{index}]"
        if not isinstance(conflict, dict):
            errors.append(f"{location} must be an object")
            continue
        affected_ids = conflict.get("affected_rule_ids", [])
        unknown_rule_ids = set(affected_ids) - rule_id_set
        if unknown_rule_ids:
            errors.append(f"{location} has unknown affected rules: {sorted(unknown_rule_ids)}")

        assertions = conflict.get("assertions")
        if not isinstance(assertions, list) or len(assertions) < 2:
            errors.append(f"{location}.assertions must contain at least two assertions")
            continue
        assertion_ids = [
            assertion.get("assertion_id")
            for assertion in assertions
            if isinstance(assertion, dict)
        ]
        duplicates = duplicate_values(assertion_ids)
        if duplicates:
            errors.append(f"{location} has duplicate assertion IDs: {sorted(duplicates)}")
        for assertion_index, assertion in enumerate(assertions):
            if not isinstance(assertion, dict):
                errors.append(f"{location}.assertions[{assertion_index}] must be an object")
                continue
            validate_rule_value(
                assertion.get("value"),
                f"{location}.assertions[{assertion_index}].value",
                errors,
            )
            unknown_refs = set(assertion.get("source_refs", [])) - citation_id_set
            if unknown_refs:
                errors.append(
                    f"{location}.assertions[{assertion_index}] has unknown source refs: "
                    f"{sorted(unknown_refs)}"
                )

        resolution = conflict.get("resolution")
        if not isinstance(resolution, dict):
            errors.append(f"{location}.resolution must be an object")
            continue
        selected_id = resolution.get("selected_assertion_id")
        selected = [
            assertion
            for assertion in assertions
            if isinstance(assertion, dict) and assertion.get("assertion_id") == selected_id
        ]
        if len(selected) != 1:
            errors.append(f"{location} does not identify exactly one selected assertion")
            continue
        if selected[0].get("disposition") != "selected_for_prototype":
            errors.append(f"{location} selected assertion has the wrong disposition")
        if resolution.get("selected_value") != selected[0].get("value"):
            errors.append(f"{location} selected value differs from the selected assertion")
        if resolution.get("status") != "project_resolved_pending_official_clarification":
            errors.append(f"{location} has an unsupported resolution status")
        if not valid_date(resolution.get("decision_date")):
            errors.append(f"{location}.resolution.decision_date must be an ISO date")
        for affected_rule_id in affected_ids:
            rule = rules_by_id.get(affected_rule_id)
            if rule and rule.get("value") != resolution.get("selected_value"):
                errors.append(f"{location} selected value differs from {affected_rule_id}")
            if rule and rule.get("conflict_id") != conflict.get("conflict_id"):
                errors.append(f"{location} is not linked back from {affected_rule_id}")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ruleset", type=Path, default=DEFAULT_RULESET)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument(
        "--verify-source-files",
        action="store_true",
        help="Also require local source artifacts and verify their SHA-256 digests",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ruleset = load_json(args.ruleset)
    schema = load_json(args.schema)
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        print("Schema must declare JSON Schema Draft 2020-12")
        return 1

    errors = validate_ruleset(
        ruleset,
        repo_root=REPO_ROOT,
        verify_source_files=args.verify_source_files,
    )
    if errors:
        print("R1 ruleset validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"R1 ruleset {ruleset['version']} valid: "
        f"{len(ruleset['rules'])} rules, "
        f"{len(ruleset['conflicts'])} documented conflict"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
