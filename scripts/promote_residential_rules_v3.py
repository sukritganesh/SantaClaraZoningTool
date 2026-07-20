#!/usr/bin/env python3
"""Promote the complete residential candidate into an immutable approved ruleset."""

from __future__ import annotations

import argparse
import copy
import sys
from datetime import date
from pathlib import Path
from typing import Any, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.author_patrick_henry_residential_rules import (  # noqa: E402
    DEFAULT_SCHEMA,
    DEFAULT_SOURCE as PATRICK_HENRY_PREDECESSOR,
    validate_expansion as validate_patrick_henry_expansion,
)
from scripts.migrate_r1_rules_v3 import (  # noqa: E402
    json_bytes,
    load_json,
    relative_path,
    sha256_bytes,
    sha256_file,
)
from scripts.validate_residential_rules_v3 import validate_ruleset  # noqa: E402


DEFAULT_CANDIDATE = (
    REPO_ROOT / "rulesets/santa_clara/residential/2026-07-19.4/ruleset.json"
)
DEFAULT_CANDIDATE_CROSSWALK = (
    DEFAULT_CANDIDATE.parent / "patrick-henry-expansion-crosswalk.json"
)
DEFAULT_VERSION = "2026-07-19.5"
DEFAULT_APPROVED_ON = "2026-07-19"
DEFAULT_OUTPUT_DIR = REPO_ROOT / f"rulesets/santa_clara/residential/{DEFAULT_VERSION}"
DEFAULT_CROSSWALK_NAME = "approval-crosswalk.json"
EXPECTED_CANDIDATE_RUNTIME_PREFIXES = {
    "runtime eligibility requires status approved_for_runtime",
    "runtime eligibility requires approved_on",
    "runtime ruleset has unapproved rules:",
    "runtime ruleset has unapproved special pathways:",
}


class ResidentialPromotionError(RuntimeError):
    """Raised when a residential candidate cannot be safely promoted."""


def valid_date(value: Any) -> bool:
    """Return whether value is an ISO calendar date."""

    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def iter_rules(ruleset: dict[str, Any]):
    """Yield every use-permission and profile regulation record."""

    for zone in ruleset["zones"].values():
        yield from zone["use_permissions"].values()
        for profile in zone["analysis_profiles"].values():
            yield from profile["regulations"].values()


def iter_pathways(ruleset: dict[str, Any]):
    """Yield every special-pathway record."""

    for zone in ruleset["zones"].values():
        yield from zone["special_pathways"].values()


def candidate_runtime_state_errors(
    candidate: dict[str, Any], schema: dict[str, Any]
) -> list[str]:
    """Return unexpected candidate runtime-gate errors."""

    errors = validate_ruleset(
        candidate,
        schema=schema,
        repo_root=REPO_ROOT,
        require_runtime_eligible=True,
    )
    unexpected = []
    matched_prefixes: set[str] = set()
    for error in errors:
        matches = [
            prefix
            for prefix in EXPECTED_CANDIDATE_RUNTIME_PREFIXES
            if error == prefix or error.startswith(prefix)
        ]
        if len(matches) != 1:
            unexpected.append(error)
        else:
            matched_prefixes.add(matches[0])
    missing = EXPECTED_CANDIDATE_RUNTIME_PREFIXES - matched_prefixes
    if missing:
        unexpected.append(
            "candidate lacks expected runtime-gate failures: "
            + ", ".join(sorted(missing))
        )
    return unexpected


def build_approved_ruleset(
    candidate: dict[str, Any],
    *,
    candidate_path: Path = DEFAULT_CANDIDATE,
    version: str = DEFAULT_VERSION,
    approved_on: str = DEFAULT_APPROVED_ON,
    crosswalk_path: Optional[str] = None,
) -> dict[str, Any]:
    """Return a runtime-approved copy without changing the reviewed candidate."""

    if candidate.get("schema_version") != "3.2.0":
        raise ResidentialPromotionError("Input must use residential schema 3.2.0")
    if candidate.get("version") != "2026-07-19.4":
        raise ResidentialPromotionError("Input must be complete candidate 2026-07-19.4")
    if (
        candidate.get("status") != "candidate"
        or candidate.get("approved_on") is not None
    ):
        raise ResidentialPromotionError("Input must be an unapproved candidate")
    if not valid_date(approved_on):
        raise ResidentialPromotionError("approved_on must be an ISO date")
    if not isinstance(version, str) or not version.startswith(f"{approved_on}."):
        raise ResidentialPromotionError(
            "version must use the approval date and a revision suffix"
        )
    if version == candidate.get("version"):
        raise ResidentialPromotionError(
            "approved artifact must use a new version identity"
        )
    if not all(not rule["approved_for_ruleset"] for rule in iter_rules(candidate)):
        raise ResidentialPromotionError("candidate contains preapproved rule records")
    if not all(
        not pathway["approved_for_ruleset"] for pathway in iter_pathways(candidate)
    ):
        raise ResidentialPromotionError(
            "candidate contains preapproved special pathways"
        )

    if crosswalk_path is None:
        crosswalk_path = (
            "rulesets/santa_clara/residential/2026-07-19.5/approval-crosswalk.json"
        )
    approved = copy.deepcopy(candidate)
    approved["version"] = version
    approved["status"] = "approved_for_runtime"
    approved["approved_on"] = approved_on
    approved["scope"]["description"] = (
        "Runtime-approved selected residential standards ruleset containing the "
        "accepted R1 migration, R2-R6 citywide and density tranches, and the five "
        "Patrick Henry multifamily designations."
    )
    approved["predecessor_rulesets"] = [
        {
            "ruleset_id": candidate["ruleset_id"],
            "version": candidate["version"],
            "sha256": sha256_file(candidate_path),
            "crosswalk_path": crosswalk_path,
        }
    ]
    for rule in iter_rules(approved):
        rule["approved_for_ruleset"] = True
    for pathway in iter_pathways(approved):
        pathway["approved_for_ruleset"] = True
    return approved


def semantic_projection(ruleset: dict[str, Any]) -> dict[str, Any]:
    """Return regulatory content with promotion-only lifecycle fields removed."""

    projection = copy.deepcopy(ruleset)
    for field in ("version", "status", "approved_on", "predecessor_rulesets"):
        projection.pop(field)
    projection["scope"].pop("description")
    for rule in iter_rules(projection):
        rule.pop("approved_for_ruleset")
    for pathway in iter_pathways(projection):
        pathway.pop("approved_for_ruleset")
    return projection


def record_counts(ruleset: dict[str, Any]) -> dict[str, int]:
    """Return exact approval-surface counts."""

    use_permissions = sum(
        len(zone["use_permissions"]) for zone in ruleset["zones"].values()
    )
    analysis_profiles = sum(
        len(zone["analysis_profiles"]) for zone in ruleset["zones"].values()
    )
    profile_regulations = sum(
        len(profile["regulations"])
        for zone in ruleset["zones"].values()
        for profile in zone["analysis_profiles"].values()
    )
    special_pathways = sum(
        len(zone["special_pathways"]) for zone in ruleset["zones"].values()
    )
    return {
        "zones": len(ruleset["zones"]),
        "use_permissions": use_permissions,
        "analysis_profiles": analysis_profiles,
        "profile_regulations": profile_regulations,
        "special_pathways": special_pathways,
        "conflicts": len(ruleset["conflicts"]),
        "approved_records": use_permissions + profile_regulations + special_pathways,
    }


def build_approval_crosswalk(
    *,
    candidate: dict[str, Any],
    candidate_path: Path,
    target: dict[str, Any],
    target_path: Path,
    schema_path: Path,
    target_bytes: bytes,
) -> dict[str, Any]:
    """Build the checksum-pinned candidate-to-approved promotion crosswalk."""

    candidate_projection = semantic_projection(candidate)
    target_projection = semantic_projection(target)
    if candidate_projection != target_projection:
        raise ResidentialPromotionError("promotion changed regulatory semantics")
    projection_sha = sha256_bytes(json_bytes(candidate_projection))
    return {
        "crosswalk_version": "1.0.0",
        "promotion_id": "santa-clara-residential-v3-complete-runtime-approval",
        "promotion_status": "approved_runtime_validated",
        "approved_on": target["approved_on"],
        "decision_source": (
            "Project owner approval of candidate 2026-07-19.4 in the July 19, "
            "2026 Codex task"
        ),
        "source_ruleset": {
            "path": relative_path(candidate_path),
            "ruleset_id": candidate["ruleset_id"],
            "version": candidate["version"],
            "schema_version": candidate["schema_version"],
            "status": candidate["status"],
            "sha256": sha256_file(candidate_path),
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
        "counts": record_counts(target),
        "semantic_projection_sha256": projection_sha,
        "allowed_changes": [
            "Advance the immutable ruleset version from 2026-07-19.4 to 2026-07-19.5.",
            "Change status from candidate to approved_for_runtime and set approved_on.",
            "Replace the predecessor pointer with a checksum-pinned approval "
            "crosswalk to the reviewed candidate.",
            "Replace the nonruntime scope description with an equivalent "
            "runtime-approved lifecycle description.",
            "Set approved_for_ruleset true on all 196 rules and both special pathways.",
            "Preserve all regulatory semantics, sources, citations, conflicts, "
            "values, conditions, and limitations.",
        ],
    }


def validate_promotion(
    candidate: dict[str, Any],
    target: dict[str, Any],
    crosswalk: dict[str, Any],
    *,
    candidate_path: Path = DEFAULT_CANDIDATE,
    target_path: Path = DEFAULT_OUTPUT_DIR / "ruleset.json",
    schema_path: Path = DEFAULT_SCHEMA,
) -> list[str]:
    """Return promotion integrity, preservation, approval, and replay errors."""

    errors: list[str] = []
    if crosswalk.get("promotion_id") != (
        "santa-clara-residential-v3-complete-runtime-approval"
    ):
        errors.append("promotion_id is unsupported")
    if crosswalk.get("promotion_status") != "approved_runtime_validated":
        errors.append("promotion_status is not approved_runtime_validated")
    for record_name, expected_path in (
        ("source_ruleset", candidate_path),
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
    if predecessor.get("ruleset_id") != candidate.get("ruleset_id"):
        errors.append("target predecessor ruleset identity does not match")
    if predecessor.get("version") != candidate.get("version"):
        errors.append("target predecessor version does not match")
    if predecessor.get("sha256") != sha256_file(candidate_path):
        errors.append("target predecessor checksum does not match")
    if predecessor.get("crosswalk_path") != relative_path(
        target_path.parent / DEFAULT_CROSSWALK_NAME
    ):
        errors.append("target predecessor crosswalk path is not the approval crosswalk")

    if semantic_projection(candidate) != semantic_projection(target):
        errors.append("approved target changed regulatory semantics")
    expected_projection_sha = sha256_bytes(json_bytes(semantic_projection(candidate)))
    if crosswalk.get("semantic_projection_sha256") != expected_projection_sha:
        errors.append("semantic projection checksum does not match the candidate")
    if crosswalk.get("counts") != record_counts(target):
        errors.append("approval crosswalk counts do not match the target")
    if any(rule["approved_for_ruleset"] for rule in iter_rules(candidate)):
        errors.append("candidate contains approved rules")
    if any(pathway["approved_for_ruleset"] for pathway in iter_pathways(candidate)):
        errors.append("candidate contains approved special pathways")
    if any(not rule["approved_for_ruleset"] for rule in iter_rules(target)):
        errors.append("approved target contains unapproved rules")
    if any(
        not pathway["approved_for_ruleset"] for pathway in iter_pathways(target)
    ):
        errors.append("approved target contains unapproved special pathways")

    reproduced = build_approved_ruleset(
        candidate,
        candidate_path=candidate_path,
        version=target["version"],
        approved_on=target["approved_on"],
        crosswalk_path=target["predecessor_rulesets"][0]["crosswalk_path"],
    )
    if reproduced != target:
        errors.append("target differs from deterministic approval replay")
    try:
        reproduced_crosswalk = build_approval_crosswalk(
            candidate=candidate,
            candidate_path=candidate_path,
            target=target,
            target_path=target_path,
            schema_path=schema_path,
            target_bytes=json_bytes(target),
        )
    except ResidentialPromotionError as error:
        errors.append(f"approval crosswalk replay failed: {error}")
    else:
        if reproduced_crosswalk != crosswalk:
            errors.append("approval crosswalk differs from deterministic replay")
    return errors


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse promotion command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument(
        "--candidate-crosswalk",
        type=Path,
        default=DEFAULT_CANDIDATE_CROSSWALK,
    )
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--approved-on", default=DEFAULT_APPROVED_ON)
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Validate the complete candidate and write its approved successor."""

    args = parse_args(argv)
    candidate_path = args.candidate.resolve()
    candidate_crosswalk_path = args.candidate_crosswalk.resolve()
    schema_path = args.schema.resolve()
    output_dir = args.output_dir.resolve()
    target_path = output_dir / "ruleset.json"
    target_crosswalk_path = output_dir / DEFAULT_CROSSWALK_NAME
    if output_dir.exists():
        raise ResidentialPromotionError(
            f"Destination already exists; approved versions are immutable: {output_dir}"
        )
    if output_dir.name != args.version:
        raise ResidentialPromotionError(
            "output directory name must match the approved version"
        )

    candidate = load_json(candidate_path)
    schema = load_json(schema_path)
    candidate_errors = validate_ruleset(
        candidate,
        schema=schema,
        repo_root=REPO_ROOT,
        verify_source_files=True,
    )
    candidate_errors.extend(
        validate_patrick_henry_expansion(
            load_json(PATRICK_HENRY_PREDECESSOR),
            candidate,
            load_json(candidate_crosswalk_path),
            source_path=PATRICK_HENRY_PREDECESSOR,
            target_path=candidate_path,
            schema_path=schema_path,
        )
    )
    candidate_errors.extend(candidate_runtime_state_errors(candidate, schema))
    if candidate_errors:
        raise ResidentialPromotionError(
            "Candidate validation failed:\n" + "\n".join(candidate_errors)
        )

    crosswalk_relative = relative_path(target_crosswalk_path)
    target = build_approved_ruleset(
        candidate,
        candidate_path=candidate_path,
        version=args.version,
        approved_on=args.approved_on,
        crosswalk_path=crosswalk_relative,
    )
    target_errors = validate_ruleset(
        target,
        schema=schema,
        repo_root=REPO_ROOT,
        verify_source_files=False,
        require_runtime_eligible=True,
    )
    if target_errors:
        raise ResidentialPromotionError(
            "Approved target validation failed:\n" + "\n".join(target_errors)
        )

    target_bytes = json_bytes(target)
    crosswalk = build_approval_crosswalk(
        candidate=candidate,
        candidate_path=candidate_path,
        target=target,
        target_path=target_path,
        schema_path=schema_path,
        target_bytes=target_bytes,
    )
    output_dir.mkdir(parents=True)
    try:
        target_path.write_bytes(target_bytes)
        target_crosswalk_path.write_bytes(json_bytes(crosswalk))
        errors = validate_ruleset(
            target,
            schema=schema,
            repo_root=REPO_ROOT,
            verify_source_files=True,
            require_runtime_eligible=True,
        )
        errors.extend(
            validate_promotion(
                candidate,
                target,
                crosswalk,
                candidate_path=candidate_path,
                target_path=target_path,
                schema_path=schema_path,
            )
        )
        if errors:
            raise ResidentialPromotionError(
                "Written approval promotion failed validation:\n"
                + "\n".join(errors)
            )
    except Exception:
        if target_crosswalk_path.exists():
            target_crosswalk_path.unlink()
        if target_path.exists():
            target_path.unlink()
        output_dir.rmdir()
        raise
    print(f"Wrote approved residential ruleset: {relative_path(target_path)}")
    print(f"Approval crosswalk: {relative_path(target_crosswalk_path)}")
    print(f"Approval date: {target['approved_on']}")
    print("Runtime eligibility: yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
