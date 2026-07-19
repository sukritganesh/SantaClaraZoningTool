#!/usr/bin/env python3
"""Promote a validated R1 v2 candidate into a new immutable approved version."""

from __future__ import annotations

import argparse
import copy
import sys
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts.migrate_r1_rules_v2 import (
    RULESET_PARENT,
    json_bytes,
    load_json,
    relative_path,
    sha256_bytes,
)
from scripts.validate_r1_rules import valid_date
from scripts.validate_r1_rules_v2 import (
    DEFAULT_SCHEMA,
    DEFAULT_V1_RULESET,
    runtime_eligibility_errors,
    validate_migration,
    validate_ruleset,
)


DEFAULT_CANDIDATE = (
    REPO_ROOT / "rulesets/santa_clara/r1/2026-07-17/ruleset.json"
)
DEFAULT_CROSSWALK = DEFAULT_CANDIDATE.parent / "migration-crosswalk.json"
EXPECTED_CANDIDATE_ELIGIBILITY_ERRORS = {
    "ruleset status is not approved_for_prototype",
    "ruleset does not have a valid approved_on date",
}


class PromotionError(RuntimeError):
    """Raised when a candidate cannot be safely promoted."""


def build_approved_ruleset(
    candidate: dict[str, Any],
    *,
    version: str,
    approved_on: str,
) -> dict[str, Any]:
    """Return an approved copy without changing the reviewed candidate."""

    if candidate.get("status") != "candidate" or candidate.get("approved_on") is not None:
        raise PromotionError("Input must be an unapproved candidate")
    if not valid_date(approved_on):
        raise PromotionError("approved_on must be an ISO date")
    if not isinstance(version, str) or not version.startswith(f"{approved_on}."):
        raise PromotionError("version must use the approval date and a revision suffix")
    if version == candidate.get("version"):
        raise PromotionError("approved artifact must use a new version identity")

    approved = copy.deepcopy(candidate)
    approved["version"] = version
    approved["status"] = "approved_for_prototype"
    approved["approved_on"] = approved_on
    return approved


def build_approved_crosswalk(
    candidate_crosswalk: dict[str, Any],
    *,
    target_path: Path,
    approved: dict[str, Any],
    target_bytes: bytes,
    approved_on: str,
) -> dict[str, Any]:
    """Return a promotion-specific crosswalk manifest for the approved artifact."""

    crosswalk = copy.deepcopy(candidate_crosswalk)
    crosswalk["generated_on"] = approved_on
    crosswalk["migration_status"] = "approved_runtime_validated"
    crosswalk["target_ruleset"] = {
        "path": relative_path(target_path),
        "version": approved["version"],
        "schema_version": approved["schema_version"],
        "status": approved["status"],
        "sha256": sha256_bytes(target_bytes),
    }
    notes = [
        note
        for note in crosswalk.get("migration_notes", [])
        if not note.startswith("The target remains a candidate")
    ]
    notes.append(
        f"Project owner approved the separately versioned v2 artifact on {approved_on}."
    )
    crosswalk["migration_notes"] = notes
    return crosswalk


def parse_args() -> argparse.Namespace:
    today = date.today().isoformat()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--source-v1", type=Path, default=DEFAULT_V1_RULESET)
    parser.add_argument("--approved-on", default=today)
    parser.add_argument("--version", default=f"{today}.2")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=RULESET_PARENT / f"{today}.2",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidate_path = args.candidate.resolve()
    candidate_crosswalk_path = args.crosswalk.resolve()
    schema_path = args.schema.resolve()
    source_v1_path = args.source_v1.resolve()
    output_dir = args.output_dir.resolve()
    target_path = output_dir / "ruleset.json"
    target_crosswalk_path = output_dir / "migration-crosswalk.json"

    if output_dir.exists():
        raise PromotionError(
            f"Destination already exists; approved versions are immutable: {output_dir}"
        )
    if output_dir.name != args.version:
        raise PromotionError("output directory name must match the approved version")

    candidate = load_json(candidate_path)
    schema = load_json(schema_path)
    candidate_crosswalk = load_json(candidate_crosswalk_path)
    source_v1 = load_json(source_v1_path)

    candidate_errors = validate_ruleset(
        candidate,
        schema=schema,
        repo_root=REPO_ROOT,
        verify_source_files=True,
    )
    candidate_errors.extend(
        validate_migration(
            candidate,
            candidate_crosswalk,
            source_v1,
            ruleset_path=candidate_path,
            schema_path=schema_path,
            source_v1_path=source_v1_path,
            repo_root=REPO_ROOT,
        )
    )
    if candidate_errors:
        raise PromotionError(
            "Candidate validation failed:\n" + "\n".join(candidate_errors)
        )
    candidate_eligibility = set(runtime_eligibility_errors(candidate))
    if candidate_eligibility != EXPECTED_CANDIDATE_ELIGIBILITY_ERRORS:
        raise PromotionError(
            "Candidate has unexpected runtime-eligibility state:\n"
            + "\n".join(sorted(candidate_eligibility))
        )

    approved = build_approved_ruleset(
        candidate,
        version=args.version,
        approved_on=args.approved_on,
    )
    approved_errors = validate_ruleset(
        approved,
        schema=schema,
        repo_root=REPO_ROOT,
        verify_source_files=True,
    )
    approved_errors.extend(runtime_eligibility_errors(approved))
    if approved_errors:
        raise PromotionError(
            "Approved artifact validation failed:\n" + "\n".join(approved_errors)
        )

    target_bytes = json_bytes(approved)
    approved_crosswalk = build_approved_crosswalk(
        candidate_crosswalk,
        target_path=target_path,
        approved=approved,
        target_bytes=target_bytes,
        approved_on=args.approved_on,
    )

    output_dir.mkdir(parents=True)
    try:
        target_path.write_bytes(target_bytes)
        target_crosswalk_path.write_bytes(json_bytes(approved_crosswalk))
        migration_errors = validate_migration(
            approved,
            approved_crosswalk,
            source_v1,
            ruleset_path=target_path,
            schema_path=schema_path,
            source_v1_path=source_v1_path,
            repo_root=REPO_ROOT,
        )
        if migration_errors:
            raise PromotionError(
                "Approved migration validation failed:\n"
                + "\n".join(migration_errors)
            )
    except Exception:
        if target_crosswalk_path.exists():
            target_crosswalk_path.unlink()
        if target_path.exists():
            target_path.unlink()
        output_dir.rmdir()
        raise

    print(f"Wrote approved v2 ruleset: {relative_path(target_path)}")
    print(f"Approval date: {args.approved_on}")
    print("Runtime eligibility: yes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
