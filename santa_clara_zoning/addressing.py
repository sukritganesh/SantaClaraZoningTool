"""Deterministic address normalization and exact source-record matching."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Any, Iterable


TOKEN_ALIASES = {
    "AV": "AVE",
    "AVENUE": "AVE",
    "BL": "BLVD",
    "BOULEVARD": "BLVD",
    "CIRCLE": "CIR",
    "COURT": "CT",
    "DRIVE": "DR",
    "EAST": "E",
    "HIGHWAY": "HWY",
    "LANE": "LN",
    "NORTH": "N",
    "PARKWAY": "PKWY",
    "PLACE": "PL",
    "ROAD": "RD",
    "SOUTH": "S",
    "STREET": "ST",
    "TERRACE": "TER",
    "WEST": "W",
}
UNIT_MARKERS = {"APARTMENT", "APT", "SUITE", "STE", "UNIT"}
LOCALITY_SUFFIXES = (
    ("SANTA", "CLARA", "CALIFORNIA"),
    ("SANTA", "CLARA", "CA"),
    ("SANTA", "CLARA"),
)


def normalize_address(value: str) -> str:
    """Return the controlled exact-match key for a Santa Clara address."""

    if not isinstance(value, str) or not value.strip():
        return ""

    text = unicodedata.normalize("NFKC", value).upper()
    tokens = re.findall(r"[A-Z0-9]+", text)
    if tokens and re.fullmatch(r"9[0-9]{4}", tokens[-1]):
        tokens.pop()
    for suffix in LOCALITY_SUFFIXES:
        if tuple(tokens[-len(suffix) :]) == suffix:
            del tokens[-len(suffix) :]
            break

    tokens = [token for token in tokens if token not in UNIT_MARKERS]
    return " ".join(TOKEN_ALIASES.get(token, token) for token in tokens)


class AddressIndex:
    """Index active source features by a normalized full-address key."""

    def __init__(self, features: Iterable[dict[str, Any]]) -> None:
        by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for position, feature in enumerate(features):
            if not isinstance(feature, dict):
                raise ValueError(f"Address feature {position} is not an object")
            properties = feature.get("properties")
            geometry = feature.get("geometry")
            if not isinstance(properties, dict):
                raise ValueError(f"Address feature {position} has invalid properties")
            if not isinstance(geometry, dict) or geometry.get("type") != "Point":
                raise ValueError(f"Address feature {position} is not a point")
            if properties.get("CSCSTATUS") != "A":
                continue
            source_address = properties.get("CSCADDR")
            key = normalize_address(source_address)
            if not key:
                raise ValueError(f"Address feature {position} has no usable CSCADDR")
            by_key[key].append(feature)

        self._by_key = {
            key: tuple(sorted(values, key=_object_id))
            for key, values in by_key.items()
        }

    def match(self, entered_address: str) -> tuple[dict[str, Any], ...]:
        """Return every exact normalized match without selecting a duplicate."""

        return self._by_key.get(normalize_address(entered_address), ())


def _object_id(feature: dict[str, Any]) -> int:
    value = (feature.get("properties") or {}).get("OBJECTID")
    if not isinstance(value, int):
        raise ValueError("Address feature is missing an integer OBJECTID")
    return value
