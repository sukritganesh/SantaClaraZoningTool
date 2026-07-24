"""Validated, presentation-only plain-language residential zone descriptions."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ZONE_DESCRIPTION_CONTRACT_VERSION = "1.0.0"
ZONE_DESCRIPTION_CATALOG_VERSION = "2026-07-23.1"
ZONE_DESCRIPTION_RULESET_VERSION = "2026-07-19.5"
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG_PATH = (
    DEFAULT_REPO_ROOT
    / "data/presentation/santa_clara/residential/2026-07-23.1/catalog.json"
)
DEFAULT_RULESET_PATH = (
    DEFAULT_REPO_ROOT
    / "rulesets/santa_clara/residential/2026-07-19.5/ruleset.json"
)
DEFAULT_AUTHORING_GUIDE_PATH = (
    DEFAULT_REPO_ROOT / "docs/zone-description-authoring-guide.md"
)
SUPPORTED_ZONE_DESCRIPTIONS = (
    "R1-6L",
    "R1-8L",
    "R2",
    "R3",
    "R4",
    "R5",
    "R6",
    "PH-R5",
    "UV",
    "VR",
    "UC",
    "HDF",
)
_ZONE_FAMILY_LABELS = ("R1", "R2", "R3", "R4", "R5", "R6")
MIN_DESCRIPTION_WORDS = 55
MAX_DESCRIPTION_WORDS = 100
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_CITYWIDE_ZONES = frozenset({"R2", "R3", "R4", "R5", "R6"})
_PATRICK_HENRY_ZONES = frozenset({"PH-R5", "UV", "VR", "UC", "HDF"})
_COMMON_APPROVAL_REFS = frozenset(
    {"zoning-clearance", "architectural-review"}
)
_TOP_LEVEL_FIELDS = {
    "contract_version",
    "catalog_version",
    "jurisdiction",
    "authoring_method",
    "ruleset",
    "authoring_guide",
    "descriptions",
}
_RULESET_FIELDS = {"ruleset_id", "version", "local_path", "sha256"}
_GUIDE_FIELDS = {"local_path", "sha256"}
_DESCRIPTION_FIELDS = {"description", "source_refs"}


class ZoneDescriptionIntegrityError(RuntimeError):
    """Reject incomplete, stale, or unsupported zone-description copy."""


def sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 digest for one local artifact."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class ZoneDescriptionProvider:
    """Load one checked-in catalog and serve exact-zone descriptions."""

    def __init__(
        self,
        *,
        repo_root: Path,
        catalog_path: Path,
        ruleset_path: Path,
        authoring_guide_path: Path,
    ) -> None:
        self._repo_root = repo_root.resolve()
        self._catalog_path = catalog_path.resolve()
        self._ruleset_path = ruleset_path.resolve()
        self._authoring_guide_path = authoring_guide_path.resolve()
        catalog = self._load_json(self._catalog_path, "zone-description catalog")
        ruleset = self._load_json(self._ruleset_path, "approved residential ruleset")
        self._validate_catalog(catalog, ruleset)
        self._catalog = catalog
        self._descriptions = catalog["descriptions"]

    @classmethod
    def from_defaults(cls) -> "ZoneDescriptionProvider":
        """Load the checked-in Santa Clara residential description catalog."""

        return cls(
            repo_root=DEFAULT_REPO_ROOT,
            catalog_path=DEFAULT_CATALOG_PATH,
            ruleset_path=DEFAULT_RULESET_PATH,
            authoring_guide_path=DEFAULT_AUTHORING_GUIDE_PATH,
        )

    @property
    def catalog_version(self) -> str:
        """Return the validated presentation catalog version."""

        return str(self._catalog["catalog_version"])

    def description_for(self, zone: str) -> str:
        """Return the reviewed paragraph for one exact supported designation."""

        if not isinstance(zone, str) or zone not in self._descriptions:
            raise KeyError(zone)
        return str(self._descriptions[zone]["description"])

    def as_dict(self) -> dict[str, Any]:
        """Return a defensive copy for validation and maintenance tooling."""

        return copy.deepcopy(self._catalog)

    def _safe_repo_file(self, path: Path, label: str) -> Path:
        resolved = path.resolve()
        if self._repo_root != resolved and self._repo_root not in resolved.parents:
            raise ZoneDescriptionIntegrityError(f"{label} escaped the repository")
        if not resolved.is_file():
            raise ZoneDescriptionIntegrityError(f"{label} is missing: {resolved}")
        return resolved

    def _load_json(self, path: Path, label: str) -> dict[str, Any]:
        source_path = self._safe_repo_file(path, label)
        try:
            value = json.loads(source_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ZoneDescriptionIntegrityError(
                f"Could not read {label}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise ZoneDescriptionIntegrityError(f"{label} must contain an object")
        return value

    def _validate_catalog(
        self,
        catalog: dict[str, Any],
        ruleset: dict[str, Any],
    ) -> None:
        if set(catalog) != _TOP_LEVEL_FIELDS:
            raise ZoneDescriptionIntegrityError(
                "Zone-description catalog fields do not match contract 1.0.0"
            )
        if (
            catalog.get("contract_version") != ZONE_DESCRIPTION_CONTRACT_VERSION
            or catalog.get("catalog_version") != ZONE_DESCRIPTION_CATALOG_VERSION
            or catalog.get("jurisdiction") != "City of Santa Clara"
            or catalog.get("authoring_method") != "offline_codex_source_grounded"
        ):
            raise ZoneDescriptionIntegrityError(
                "Unsupported zone-description catalog identity"
            )

        ruleset_record = catalog.get("ruleset")
        if not isinstance(ruleset_record, dict) or set(ruleset_record) != (
            _RULESET_FIELDS
        ):
            raise ZoneDescriptionIntegrityError("Invalid ruleset binding")
        expected_ruleset_path = self._relative_path(self._ruleset_path)
        if (
            ruleset_record.get("ruleset_id") != "santa-clara-residential-zoning"
            or ruleset_record.get("version") != ZONE_DESCRIPTION_RULESET_VERSION
            or ruleset_record.get("local_path") != expected_ruleset_path
            or not SHA256_RE.fullmatch(str(ruleset_record.get("sha256", "")))
            or sha256_file(self._ruleset_path) != ruleset_record.get("sha256")
        ):
            raise ZoneDescriptionIntegrityError(
                "Zone-description ruleset binding is stale or modified"
            )
        if (
            ruleset.get("ruleset_id") != ruleset_record["ruleset_id"]
            or ruleset.get("version") != ruleset_record["version"]
            or ruleset.get("status") != "approved_for_runtime"
        ):
            raise ZoneDescriptionIntegrityError(
                "Zone descriptions require the approved residential ruleset"
            )

        guide_record = catalog.get("authoring_guide")
        if not isinstance(guide_record, dict) or set(guide_record) != _GUIDE_FIELDS:
            raise ZoneDescriptionIntegrityError("Invalid authoring-guide binding")
        expected_guide_path = self._relative_path(self._authoring_guide_path)
        if (
            guide_record.get("local_path") != expected_guide_path
            or not SHA256_RE.fullmatch(str(guide_record.get("sha256", "")))
            or sha256_file(self._authoring_guide_path) != guide_record.get("sha256")
        ):
            raise ZoneDescriptionIntegrityError(
                "Zone-description authoring-guide binding is stale or modified"
            )

        zones = ruleset.get("zones")
        shared = ruleset.get("shared")
        citations = shared.get("citations") if isinstance(shared, dict) else None
        if (
            not isinstance(zones, dict)
            or tuple(zones) != SUPPORTED_ZONE_DESCRIPTIONS
            or not isinstance(citations, dict)
        ):
            raise ZoneDescriptionIntegrityError(
                "Approved ruleset zone or citation scope is unsupported"
            )

        descriptions = catalog.get("descriptions")
        if (
            not isinstance(descriptions, dict)
            or tuple(descriptions) != SUPPORTED_ZONE_DESCRIPTIONS
        ):
            raise ZoneDescriptionIntegrityError(
                "Zone-description coverage or ordering is incomplete"
            )
        for zone, entry in descriptions.items():
            self._validate_description(zone, entry, citations)

    def _validate_description(
        self,
        zone: str,
        entry: Any,
        citations: dict[str, Any],
    ) -> None:
        if not isinstance(entry, dict) or set(entry) != _DESCRIPTION_FIELDS:
            raise ZoneDescriptionIntegrityError(
                f"Invalid zone-description record: {zone}"
            )
        description = entry.get("description")
        if (
            not isinstance(description, str)
            or description != description.strip()
            or not description.startswith(f"{zone} ")
            or "\n" in description
            or "\r" in description
            or "<" in description
            or ">" in description
        ):
            raise ZoneDescriptionIntegrityError(
                f"Invalid zone-description paragraph: {zone}"
            )
        word_count = len(description.split())
        if not MIN_DESCRIPTION_WORDS <= word_count <= MAX_DESCRIPTION_WORDS:
            raise ZoneDescriptionIntegrityError(
                f"Zone description has {word_count} words instead of "
                f"{MIN_DESCRIPTION_WORDS}-{MAX_DESCRIPTION_WORDS}: {zone}"
            )
        if (
            "Zoning Clearance" not in description
            or "Architectural Review" not in description
        ):
            raise ZoneDescriptionIntegrityError(
                f"Zone description omits approved review steps: {zone}"
            )
        without_zone_codes = description
        for supported_zone in sorted(
            SUPPORTED_ZONE_DESCRIPTIONS,
            key=len,
            reverse=True,
        ):
            without_zone_codes = without_zone_codes.replace(supported_zone, "")
        for zone_family in _ZONE_FAMILY_LABELS:
            without_zone_codes = without_zone_codes.replace(zone_family, "")
        if re.search(r"\d", without_zone_codes):
            raise ZoneDescriptionIntegrityError(
                f"Zone description repeats a numeric standard: {zone}"
            )

        refs = entry.get("source_refs")
        if (
            not isinstance(refs, list)
            or not refs
            or any(not isinstance(ref, str) or ref not in citations for ref in refs)
            or len(refs) != len(set(refs))
        ):
            raise ZoneDescriptionIntegrityError(
                f"Zone description has invalid source references: {zone}"
            )
        required_refs = set(_COMMON_APPROVAL_REFS)
        if zone.startswith("R1-"):
            required_refs.update(
                {"residential-density-zone-purpose", "use-table"}
            )
        elif zone in _CITYWIDE_ZONES:
            required_refs.update(
                {"residential-density-zone-purpose", "citywide-use-table"}
            )
        elif zone in _PATRICK_HENRY_ZONES:
            required_refs.update(
                {
                    "patrick-henry-title18-zone-purpose",
                    "patrick-henry-title18-use-table",
                    "patrick-henry-plan-classifications",
                }
            )
        if not required_refs.issubset(refs):
            raise ZoneDescriptionIntegrityError(
                f"Zone description lacks required provenance: {zone}"
            )

    def _relative_path(self, path: Path) -> str:
        try:
            return path.relative_to(self._repo_root).as_posix()
        except ValueError as exc:
            raise ZoneDescriptionIntegrityError(
                "Zone-description artifact escaped the repository"
            ) from exc
