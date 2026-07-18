"""Validated runtime loading for the approved Santa Clara R1 ruleset."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from scripts.validate_r1_rules_v2 import (
    runtime_eligibility_errors,
    validate_migration,
    validate_ruleset,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_APPROVED_RULESET_DIR = (
    REPO_ROOT / "rulesets/santa_clara/r1/2026-07-17.2"
)


@dataclass(frozen=True)
class RulesetArtifacts:
    """Files required to prove that one v2 ruleset is safe for runtime use."""

    ruleset: Path
    schema: Path
    crosswalk: Path
    source_v1: Path

    def resolved(self) -> "RulesetArtifacts":
        return RulesetArtifacts(
            ruleset=self.ruleset.resolve(),
            schema=self.schema.resolve(),
            crosswalk=self.crosswalk.resolve(),
            source_v1=self.source_v1.resolve(),
        )


DEFAULT_APPROVED_ARTIFACTS = RulesetArtifacts(
    ruleset=DEFAULT_APPROVED_RULESET_DIR / "ruleset.json",
    schema=REPO_ROOT / "rulesets/schema/ruleset-v2.schema.json",
    crosswalk=DEFAULT_APPROVED_RULESET_DIR / "migration-crosswalk.json",
    source_v1=REPO_ROOT / "rulesets/santa_clara/r1/2026-07-16/ruleset.json",
)


class RulesetLoadError(RuntimeError):
    """Report the gate that rejected a runtime ruleset and its evidence."""

    def __init__(self, stage: str, errors: list[str]) -> None:
        self.stage = stage
        self.errors = tuple(errors)
        detail = "\n".join(f"- {error}" for error in self.errors)
        super().__init__(f"Approved R1 ruleset rejected during {stage}:\n{detail}")


@dataclass(frozen=True)
class ApprovedR1Ruleset:
    """A validated, read-only runtime view of one approved ruleset version."""

    _data: Mapping[str, Any]
    artifacts: RulesetArtifacts

    @classmethod
    def load(
        cls,
        artifacts: RulesetArtifacts = DEFAULT_APPROVED_ARTIFACTS,
    ) -> "ApprovedR1Ruleset":
        """Load all artifacts, run every runtime gate once, and freeze the result."""

        paths = artifacts.resolved()
        ruleset = _read_json_object(paths.ruleset, "ruleset")
        schema = _read_json_object(paths.schema, "schema")
        crosswalk = _read_json_object(paths.crosswalk, "crosswalk")
        source_v1 = _read_json_object(paths.source_v1, "source v1 ruleset")

        try:
            domain_errors = validate_ruleset(
                ruleset,
                schema=schema,
                repo_root=REPO_ROOT,
                verify_source_files=True,
            )
        except Exception as exc:
            raise RulesetLoadError(
                "schema/domain validation",
                [f"validator raised {type(exc).__name__}: {exc}"],
            ) from exc
        if domain_errors:
            raise RulesetLoadError("schema/domain validation", domain_errors)

        try:
            migration_errors = validate_migration(
                ruleset,
                crosswalk,
                source_v1,
                ruleset_path=paths.ruleset,
                schema_path=paths.schema,
                source_v1_path=paths.source_v1,
                repo_root=REPO_ROOT,
            )
        except Exception as exc:
            raise RulesetLoadError(
                "migration validation",
                [f"validator raised {type(exc).__name__}: {exc}"],
            ) from exc
        if migration_errors:
            raise RulesetLoadError("migration validation", migration_errors)

        eligibility_errors = runtime_eligibility_errors(
            ruleset,
            domain_errors=domain_errors,
        )
        if eligibility_errors:
            raise RulesetLoadError("runtime eligibility", eligibility_errors)

        frozen = _freeze_json(ruleset)
        if not isinstance(frozen, Mapping):
            raise RulesetLoadError("internal representation", ["ruleset is not an object"])
        return cls(_data=frozen, artifacts=paths)

    @property
    def ruleset_id(self) -> str:
        return str(self._data["ruleset_id"])

    @property
    def version(self) -> str:
        return str(self._data["version"])

    @property
    def approved_on(self) -> str:
        return str(self._data["approved_on"])

    @property
    def verified_through(self) -> str:
        return str(self._data["verified_through"])

    @property
    def jurisdiction(self) -> dict[str, Any]:
        value = _thaw_json(self._data["jurisdiction"])
        if not isinstance(value, dict):
            raise RuntimeError("Validated jurisdiction is not an object")
        return value

    @property
    def supported_zones(self) -> tuple[str, ...]:
        zones = self._data["zones"]
        if not isinstance(zones, Mapping):
            raise RuntimeError("Validated zones collection is not an object")
        return tuple(str(zone) for zone in zones)

    @property
    def regulation_count(self) -> int:
        zones = self._data["zones"]
        if not isinstance(zones, Mapping):
            raise RuntimeError("Validated zones collection is not an object")
        return sum(
            len(zone["regulations"])
            for zone in zones.values()
            if isinstance(zone, Mapping)
        )

    def as_dict(self) -> dict[str, Any]:
        """Return a defensive mutable copy without exposing authoritative state."""

        value = _thaw_json(self._data)
        if not isinstance(value, dict):
            raise RuntimeError("Validated ruleset is not an object")
        return value


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as source:
            value = json.load(source)
    except (OSError, json.JSONDecodeError) as exc:
        raise RulesetLoadError(
            "artifact loading",
            [f"Could not read {label} at {path}: {exc}"],
        ) from exc
    if not isinstance(value, dict):
        raise RulesetLoadError(
            "artifact loading",
            [f"Expected {label} to contain a JSON object: {path}"],
        )
    return value


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value
