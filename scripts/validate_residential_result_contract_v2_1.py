#!/usr/bin/env python3
"""Build and validate approved-ruleset fixtures for result contract 2.1.0.

The fixtures exercise the runtime-ready result representation against approved
residential ruleset 2026-07-19.5 without wiring that ruleset into production.
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Any, Iterable, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_r1_rules import load_json, validate_schema_contract  # noqa: E402
from scripts.validate_residential_result_contract import (  # noqa: E402
    EMPTY_SOURCES,
    REASON_BY_STATUS,
    available_selections,
    ordered_union,
    selected_rule,
    source_closure,
    transitive_topic_ids,
)
from scripts.validate_residential_rules_v3 import (  # noqa: E402
    PROFILE_BINDINGS,
    PROFILE_CAPABILITIES_WITH_DENSITY,
    TARGET_ZONES,
    validate_ruleset,
)


RESULT_CONTRACT_VERSION = "2.1.0"
APPROVED_RULESET_VERSION = "2026-07-19.5"
DEFAULT_SCHEMA = (
    REPO_ROOT / "contracts/residential-result-contract-2.1.0.schema.json"
)
DEFAULT_FIXTURES = (
    REPO_ROOT / "tests/fixtures/residential_result_contract_2_1_cases.json"
)
DEFAULT_RULESET = (
    REPO_ROOT
    / "rulesets/santa_clara/residential/2026-07-19.5/ruleset.json"
)
DEFAULT_RULESET_SCHEMA = REPO_ROOT / "rulesets/schema/ruleset-v3.2.schema.json"
USE_CAPABILITY_BY_PROFILE = {
    profile_id: binding["legal_use_capability_id"]
    for profile_id, binding in PROFILE_BINDINGS.items()
}
SELECTION_STATUSES = {
    "residential_zone_found",
    "residential_standards_found",
    "analysis_not_evaluated",
    "selection_not_available",
}


def requirement_source_refs(requirement: dict[str, Any]) -> list[str]:
    """Return every direct source reference from a v3.2 requirement shape."""

    kind = requirement["kind"]
    if kind == "setback":
        refs = list(requirement["base"]["source_refs"])
        for adjustment in requirement["adjustments"]:
            refs.extend(adjustment["source_refs"])
        return refs
    if kind == "lot_area_tiered_maximum":
        return ordered_union(
            requirement["below_threshold"]["source_refs"],
            requirement["at_or_above_threshold"]["source_refs"],
        )
    return list(requirement["source_refs"])


def _resolved_property(case: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Build the status-appropriate property evidence for one fixture case."""

    if case["status"] == "outside_supported_residential_snapshot":
        return {
            "matched_address": case["matched_address"],
            "parcel_id": None,
            "zone": None,
        }
    if case["zone"] is None:
        return None
    return {
        "matched_address": f"Contract fixture: {case['fixture_id']}",
        "parcel_id": f"fixture-{case['fixture_id']}",
        "zone": case["zone"],
    }


def common_result(
    case: dict[str, Any],
    ruleset: dict[str, Any],
) -> dict[str, Any]:
    """Return the complete neutral 2.1.0 envelope for one case."""

    return {
        "contract_version": RESULT_CONTRACT_VERSION,
        "status": case["status"],
        "reason_code": case["reason_code"],
        "query": {
            "address": case.get(
                "query_address", f"Contract fixture: {case['fixture_id']}"
            )
        },
        "versions": {
            "address_snapshot": "2026-07-16",
            "residential_gis_snapshot": "2026-07-18",
            "ruleset": ruleset["version"],
            "ruleset_schema": ruleset["schema_version"],
            "result_contract": RESULT_CONTRACT_VERSION,
        },
        "property": _resolved_property(case),
        "available_selections": [],
        "requested_selection_id": case["requested_selection_id"],
        "selection": None,
        "use_permission": None,
        "regulations": None,
        "not_evaluated_topics": {},
        "conflicts": {},
        "sources": copy.deepcopy(EMPTY_SOURCES),
        "disclaimer": ruleset["disclaimer"],
    }


def _approved_permission(
    zone: dict[str, Any],
    use_capability_id: str,
    *,
    expected_code: str,
) -> dict[str, Any]:
    """Return one approved permission after checking its fixture disposition."""

    permission = zone["use_permissions"][use_capability_id]
    if not permission["approved_for_ruleset"]:
        raise ValueError(f"Use permission {permission['rule_id']} is not approved")
    actual_code = permission["requirement"]["code"]
    if actual_code != expected_code:
        raise ValueError(
            f"Use permission {permission['rule_id']} is {actual_code}, "
            f"not {expected_code}"
        )
    return permission


def _conflict_ids(*records: dict[str, Any]) -> list[str]:
    """Return stable non-null conflict identities from selected records."""

    return list(
        dict.fromkeys(
            record["conflict_id"]
            for record in records
            if record.get("conflict_id") is not None
        )
    )


def _attach_conflicts_and_sources(
    result: dict[str, Any],
    ruleset: dict[str, Any],
    *,
    selected_records: Iterable[dict[str, Any]],
    topic_ids: Iterable[str] = (),
    extra_source_refs: Iterable[str] = (),
) -> None:
    """Attach exact conflicts and provenance for selected rules and topics."""

    records = list(selected_records)
    stable_topic_ids = list(topic_ids)
    conflict_ids = _conflict_ids(*records)
    result["conflicts"] = {
        conflict_id: copy.deepcopy(ruleset["conflicts"][conflict_id])
        for conflict_id in conflict_ids
    }

    refs = list(extra_source_refs)
    exception_ids: list[str] = []
    for record in records:
        refs.extend(requirement_source_refs(record["requirement"]))
        exception_ids.extend(record["exception_family_ids"])
    for topic_id in stable_topic_ids:
        refs.extend(ruleset["not_evaluated_topics"][topic_id]["source_refs"])
    for conflict_id in conflict_ids:
        for assertion in ruleset["conflicts"][conflict_id]["assertions"]:
            refs.extend(assertion["source_refs"])
    result["sources"] = source_closure(
        ruleset,
        source_refs=refs,
        exception_ids=exception_ids,
    )


def build_fixture_result(
    case: dict[str, Any],
    ruleset: dict[str, Any],
) -> dict[str, Any]:
    """Build one deterministic 2.1.0 fixture from approved residential data."""

    result = common_result(case, ruleset)
    status = case["status"]
    zone_id = case["zone"]
    zone = ruleset["zones"].get(zone_id) if zone_id is not None else None
    if status in SELECTION_STATUSES:
        if zone is None:
            raise ValueError(f"Fixture {case['fixture_id']} requires an authored zone")
        result["available_selections"] = available_selections(zone)

    if status == "residential_standards_found":
        profile_id = case["requested_selection_id"]
        profile = zone["analysis_profiles"][profile_id]
        use_capability_id = profile["legal_use_capability_id"]
        permission = _approved_permission(
            zone,
            use_capability_id,
            expected_code="permitted_by_right",
        )
        regulations = list(profile["regulations"].values())
        if not all(rule["approved_for_ruleset"] for rule in regulations):
            raise ValueError(f"Profile {zone_id}.{profile_id} has unapproved rules")
        result["selection"] = {
            "selection_id": profile_id,
            "selection_kind": "profile",
            "profile_id": profile_id,
            "workflow_family": profile["workflow_family"],
            "legal_use_capability_id": use_capability_id,
            "primary_structure_type": profile["primary_structure_type"],
        }
        result["use_permission"] = selected_rule(permission)
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
        _attach_conflicts_and_sources(
            result,
            ruleset,
            selected_records=[permission, *regulations],
            topic_ids=topic_ids,
        )

    elif status == "analysis_not_evaluated":
        pathway_id = case["requested_selection_id"]
        pathway = zone["special_pathways"][pathway_id]
        if not pathway["approved_for_ruleset"]:
            raise ValueError(f"Special pathway {zone_id}.{pathway_id} is not approved")
        use_capability_id = pathway["legal_use_capability_id"]
        permission = _approved_permission(
            zone,
            use_capability_id,
            expected_code="permitted_by_right",
        )
        if permission["special_pathway_id"] != pathway_id:
            raise ValueError(
                f"Use permission {permission['rule_id']} does not bind {pathway_id}"
            )
        result["selection"] = {
            "selection_id": pathway_id,
            "selection_kind": "special_pathway",
            "special_pathway_id": pathway_id,
            "workflow_family": pathway["workflow_family"],
            "legal_use_capability_id": use_capability_id,
            "primary_structure_type": None,
        }
        result["use_permission"] = selected_rule(permission)
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
        _attach_conflicts_and_sources(
            result,
            ruleset,
            selected_records=[permission],
            topic_ids=topic_ids,
            extra_source_refs=requirement_source_refs(
                pathway["analysis_requirement"]
            ),
        )

    elif status == "selection_not_available":
        requested = case["requested_selection_id"]
        try:
            use_capability_id = USE_CAPABILITY_BY_PROFILE[requested]
        except KeyError as exc:
            raise ValueError(
                f"Fixture {case['fixture_id']} does not name a known profile"
            ) from exc
        if requested in zone["analysis_profiles"]:
            raise ValueError(
                f"Fixture {case['fixture_id']} names an available profile"
            )
        permission = _approved_permission(
            zone,
            use_capability_id,
            expected_code="not_listed",
        )
        result["use_permission"] = selected_rule(permission)
        _attach_conflicts_and_sources(
            result,
            ruleset,
            selected_records=[permission],
        )

    return result


def _expected_permission(
    result: dict[str, Any],
    ruleset: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Return the exact approved permission selected by a result."""

    status = result["status"]
    if status not in {
        "residential_standards_found",
        "analysis_not_evaluated",
        "selection_not_available",
    }:
        return None
    zone = ruleset["zones"][result["property"]["zone"]]
    if status == "selection_not_available":
        use_capability_id = USE_CAPABILITY_BY_PROFILE.get(
            result["requested_selection_id"]
        )
        if use_capability_id is None:
            return None
    else:
        use_capability_id = result["selection"]["legal_use_capability_id"]
    return selected_rule(zone["use_permissions"][use_capability_id])


def _expected_topics_and_conflicts(
    result: dict[str, Any],
    ruleset: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return the exact topic and conflict maps implied by a selection."""

    status = result["status"]
    if status not in {
        "residential_standards_found",
        "analysis_not_evaluated",
        "selection_not_available",
    }:
        return {}, {}
    zone = ruleset["zones"][result["property"]["zone"]]
    authored_permission = zone["use_permissions"][
        result["selection"]["legal_use_capability_id"]
        if result["selection"] is not None
        else USE_CAPABILITY_BY_PROFILE[result["requested_selection_id"]]
    ]
    records = [authored_permission]
    topic_ids: list[str] = []
    if status == "residential_standards_found":
        profile = zone["analysis_profiles"][result["selection"]["profile_id"]]
        records.extend(profile["regulations"].values())
        topic_ids = transitive_topic_ids(
            ruleset,
            profile["not_evaluated_topic_ids"],
        )
    elif status == "analysis_not_evaluated":
        pathway = zone["special_pathways"][
            result["selection"]["special_pathway_id"]
        ]
        topic_ids = transitive_topic_ids(
            ruleset,
            ordered_union(
                pathway["not_evaluated_topic_ids"],
                pathway["analysis_requirement"]["prerequisite_ids"],
            ),
        )
    conflict_ids = _conflict_ids(*records)
    topics = {
        topic_id: copy.deepcopy(ruleset["not_evaluated_topics"][topic_id])
        for topic_id in topic_ids
    }
    conflicts = {
        conflict_id: copy.deepcopy(ruleset["conflicts"][conflict_id])
        for conflict_id in conflict_ids
    }
    return topics, conflicts


def _expected_sources(
    result: dict[str, Any],
    ruleset: dict[str, Any],
) -> dict[str, Any]:
    """Return the exact approved provenance closure implied by a result."""

    status = result["status"]
    if status not in {
        "residential_standards_found",
        "analysis_not_evaluated",
        "selection_not_available",
    }:
        return copy.deepcopy(EMPTY_SOURCES)
    zone = ruleset["zones"][result["property"]["zone"]]
    use_capability_id = (
        result["selection"]["legal_use_capability_id"]
        if result["selection"] is not None
        else USE_CAPABILITY_BY_PROFILE[result["requested_selection_id"]]
    )
    permission = zone["use_permissions"][use_capability_id]
    records = [permission]
    topic_ids: list[str] = []
    extra_refs: list[str] = []
    if status == "residential_standards_found":
        profile = zone["analysis_profiles"][result["selection"]["profile_id"]]
        records.extend(profile["regulations"].values())
        topic_ids = transitive_topic_ids(
            ruleset,
            profile["not_evaluated_topic_ids"],
        )
    elif status == "analysis_not_evaluated":
        pathway = zone["special_pathways"][
            result["selection"]["special_pathway_id"]
        ]
        topic_ids = transitive_topic_ids(
            ruleset,
            ordered_union(
                pathway["not_evaluated_topic_ids"],
                pathway["analysis_requirement"]["prerequisite_ids"],
            ),
        )
        extra_refs = requirement_source_refs(pathway["analysis_requirement"])

    refs = list(extra_refs)
    exception_ids: list[str] = []
    for record in records:
        refs.extend(requirement_source_refs(record["requirement"]))
        exception_ids.extend(record["exception_family_ids"])
    for topic_id in topic_ids:
        refs.extend(ruleset["not_evaluated_topics"][topic_id]["source_refs"])
    for conflict_id in _conflict_ids(*records):
        for assertion in ruleset["conflicts"][conflict_id]["assertions"]:
            refs.extend(assertion["source_refs"])
    return source_closure(
        ruleset,
        source_refs=refs,
        exception_ids=exception_ids,
    )


def validate_result(
    result: dict[str, Any],
    *,
    schema: Optional[dict[str, Any]] = None,
    ruleset: Optional[dict[str, Any]] = None,
) -> list[str]:
    """Return schema, binding, approved-data, and provenance errors."""

    if schema is None:
        schema = load_json(DEFAULT_SCHEMA)
    if ruleset is None:
        ruleset = load_json(DEFAULT_RULESET)
    errors = validate_schema_contract(result, schema)
    if errors:
        return errors

    status = result["status"]
    if result["reason_code"] != REASON_BY_STATUS[status]:
        errors.append(f"{status} has the wrong reason_code")
    versions = result["versions"]
    if versions["ruleset"] != ruleset["version"]:
        errors.append("result ruleset version differs from its approved ruleset")
    if versions["ruleset_schema"] != ruleset["schema_version"]:
        errors.append("result ruleset schema differs from its approved ruleset")
    if versions["result_contract"] != result["contract_version"]:
        errors.append("result-contract versions disagree")

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
    selected_branch_is_known = True
    if status in SELECTION_STATUSES:
        zone_id = property_record["zone"]
        if zone_id not in TARGET_ZONES:
            errors.append("residential result uses a zone outside the exact target set")
            selected_branch_is_known = False
        else:
            zone = ruleset["zones"][zone_id]
            expected_available = available_selections(zone)
            if result["available_selections"] != expected_available:
                errors.append("available selections differ from the approved zone")
            if status == "residential_standards_found":
                profile_id = result["selection"]["profile_id"]
                if profile_id not in zone["analysis_profiles"]:
                    errors.append(
                        "selected profile is unavailable for the approved zone"
                    )
                    selected_branch_is_known = False
            elif status == "analysis_not_evaluated":
                pathway_id = result["selection"]["special_pathway_id"]
                if pathway_id not in zone["special_pathways"]:
                    errors.append(
                        "selected pathway is unavailable for the approved zone"
                    )
                    selected_branch_is_known = False
            elif status == "selection_not_available":
                if requested not in USE_CAPABILITY_BY_PROFILE:
                    errors.append(
                        "unavailable selection is not a known profile identity"
                    )
                    selected_branch_is_known = False
                elif requested in zone["analysis_profiles"]:
                    selected_branch_is_known = False

    if selected_branch_is_known:
        expected_permission = _expected_permission(result, ruleset)
        if result["use_permission"] != expected_permission:
            errors.append("use_permission differs from the approved selected use")
        expected_topics, expected_conflicts = _expected_topics_and_conflicts(
            result,
            ruleset,
        )
        if result["not_evaluated_topics"] != expected_topics:
            errors.append("not-evaluated topics differ from the selected branch")
        if result["conflicts"] != expected_conflicts:
            errors.append("conflicts differ from the selected branch")

    if status == "residential_standards_found" and selected_branch_is_known:
        selection = result["selection"]
        profile_id = selection["profile_id"]
        expected_binding = PROFILE_BINDINGS[profile_id]
        for field, expected in expected_binding.items():
            if selection[field] != expected:
                errors.append(f"selection.{field} must be {expected}")
        if set(result["regulations"]) != PROFILE_CAPABILITIES_WITH_DENSITY:
            errors.append(
                "successful result must contain the complete ten-capability profile"
            )
        zone = ruleset["zones"][property_record["zone"]]
        expected_rules = {
            capability: selected_rule(rule)
            for capability, rule in zone["analysis_profiles"][profile_id][
                "regulations"
            ].items()
        }
        if result["regulations"] != expected_rules:
            errors.append("regulations differ from the approved selected profile")

    if selected_branch_is_known:
        expected_sources = _expected_sources(result, ruleset)
        if result["sources"] != expected_sources:
            errors.append("result provenance closure differs from the selected branch")
    return errors


def _load_approved_fixture_ruleset(
    fixture: dict[str, Any],
) -> dict[str, Any]:
    """Load and domain-check the exact approved ruleset named by the fixture."""

    if fixture.get("fixture_contract_version") != "1.0.0":
        raise ValueError("Unsupported fixture contract version")
    if fixture.get("result_contract_version") != RESULT_CONTRACT_VERSION:
        raise ValueError("Fixture does not target result contract 2.1.0")
    if fixture.get("approved_ruleset_contract_fixtures") is not True:
        raise ValueError("Fixtures must opt into approved-ruleset contract data")
    if fixture.get("production_pipeline_results") is not False:
        raise ValueError("Fixtures must not claim to be production pipeline results")
    ruleset_path = (REPO_ROOT / fixture["ruleset_path"]).resolve()
    if ruleset_path != DEFAULT_RULESET.resolve():
        raise ValueError("Fixtures must use the canonical approved .5 ruleset")
    ruleset = load_json(ruleset_path)
    if ruleset["version"] != APPROVED_RULESET_VERSION:
        raise ValueError("Fixture ruleset has an unexpected approved version")
    errors = validate_ruleset(
        ruleset,
        schema=load_json(DEFAULT_RULESET_SCHEMA),
        require_runtime_eligible=True,
    )
    if errors:
        raise ValueError(f"Fixture ruleset is not runtime eligible: {errors}")
    return ruleset


def load_fixture_results(
    fixture_path: Path = DEFAULT_FIXTURES,
) -> list[tuple[str, dict[str, Any]]]:
    """Load case specifications and build their complete result payloads."""

    fixture = load_json(fixture_path)
    ruleset = _load_approved_fixture_ruleset(fixture)
    return [
        (case["fixture_id"], build_fixture_result(case, ruleset))
        for case in fixture["cases"]
    ]


def main(argv: Optional[list[str]] = None) -> int:
    """Validate every approved-ruleset 2.1.0 contract fixture."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    args = parser.parse_args(argv)

    schema = load_json(args.schema)
    fixture = load_json(args.fixtures)
    ruleset = _load_approved_fixture_ruleset(fixture)
    results = [
        (case["fixture_id"], build_fixture_result(case, ruleset))
        for case in fixture["cases"]
    ]
    failures: list[str] = []
    for fixture_id, result in results:
        failures.extend(
            f"{fixture_id}: {error}"
            for error in validate_result(result, schema=schema, ruleset=ruleset)
        )
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1
    print(
        f"Validated {len(results)} residential result-contract 2.1.0 fixtures "
        f"against approved ruleset {ruleset['version']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
