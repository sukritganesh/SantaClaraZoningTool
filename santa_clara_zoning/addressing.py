"""Deterministic address normalization, matching, and local suggestions."""

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
MIN_SUGGESTION_CHARACTERS = 3
MAX_SUGGESTION_QUERY_LENGTH = 120
DEFAULT_SUGGESTION_LIMIT = 8


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
    """Index active source features for exact lookup and local suggestions."""

    def __init__(self, features: Iterable[dict[str, Any]]) -> None:
        by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
        by_display_address: dict[str, list[dict[str, Any]]] = defaultdict(list)
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
            by_display_address[source_address].append(feature)

        self._by_key = {
            key: tuple(sorted(values, key=_object_id))
            for key, values in by_key.items()
        }
        self._suggestion_records = tuple(
            sorted(
                (
                    _suggestion_record(display_address, values)
                    for display_address, values in by_display_address.items()
                ),
                key=lambda record: (
                    _natural_key(record["normalized_address"]),
                    record["minimum_object_id"],
                ),
            )
        )

    def match(self, entered_address: str) -> tuple[dict[str, Any], ...]:
        """Return every exact normalized match without selecting a duplicate."""

        return self._by_key.get(normalize_address(entered_address), ())

    def suggest(
        self,
        query: str,
        *,
        limit: int = DEFAULT_SUGGESTION_LIMIT,
    ) -> dict[str, Any]:
        """Return bounded canonical suggestions without guessing an address."""

        if not isinstance(query, str):
            raise TypeError("Address suggestion query must be a string")
        if len(query) > MAX_SUGGESTION_QUERY_LENGTH:
            raise ValueError(
                "Address suggestion query exceeds the 120-character limit"
            )
        if (
            not isinstance(limit, int)
            or isinstance(limit, bool)
            or limit < 1
            or limit > DEFAULT_SUGGESTION_LIMIT
        ):
            raise ValueError(
                f"Address suggestion limit must be between 1 and "
                f"{DEFAULT_SUGGESTION_LIMIT}"
            )

        normalized_query = normalize_address(query)
        if _alphanumeric_length(normalized_query) < MIN_SUGGESTION_CHARACTERS:
            return {
                "status": "query_too_short",
                "query": query,
                "normalized_query": normalized_query,
                "total_matches": 0,
                "truncated": False,
                "suggestions": [],
            }

        query_tokens = tuple(normalized_query.split())
        ranked: list[tuple[int, tuple[Any, ...], int, dict[str, Any]]] = []
        for record in self._suggestion_records:
            normalized_address = record["normalized_address"]
            if normalized_address == normalized_query:
                rank = 0
            elif normalized_address.startswith(normalized_query):
                rank = 1
            elif _ordered_token_prefix_match(
                query_tokens,
                record["normalized_tokens"],
            ):
                rank = 2
            else:
                continue
            ranked.append(
                (
                    rank,
                    _natural_key(normalized_address),
                    record["minimum_object_id"],
                    record,
                )
            )

        ranked.sort(key=lambda item: item[:3])
        selected = ranked[:limit]
        suggestions = [
            {
                "value": record["display_address"],
                "display_address": record["display_address"],
                "secondary_text": record["secondary_text"],
                "source_record_count": record["source_record_count"],
            }
            for _, _, _, record in selected
        ]
        return {
            "status": "ok",
            "query": query,
            "normalized_query": normalized_query,
            "total_matches": len(ranked),
            "truncated": len(ranked) > limit,
            "suggestions": suggestions,
        }


def _suggestion_record(
    display_address: str,
    features: list[dict[str, Any]],
) -> dict[str, Any]:
    ordered = sorted(features, key=_object_id)
    properties = ordered[0].get("properties") or {}
    city = properties.get("ADDRCITY")
    if not isinstance(city, str) or not city.strip():
        city = "SANTA CLARA"
    zip_code = properties.get("ADDRZIP5")
    locality = f"{city.title()}, CA"
    if isinstance(zip_code, int) and not isinstance(zip_code, bool):
        locality += f" {zip_code:05d}"
    elif isinstance(zip_code, str) and zip_code.strip():
        locality += f" {zip_code.strip()}"
    normalized = normalize_address(display_address)
    return {
        "display_address": display_address,
        "normalized_address": normalized,
        "normalized_tokens": tuple(normalized.split()),
        "secondary_text": locality,
        "source_record_count": len(ordered),
        "minimum_object_id": _object_id(ordered[0]),
    }


def _ordered_token_prefix_match(
    query_tokens: tuple[str, ...],
    address_tokens: tuple[str, ...],
) -> bool:
    position = 0
    for query_token in query_tokens:
        while position < len(address_tokens) and not address_tokens[
            position
        ].startswith(query_token):
            position += 1
        if position == len(address_tokens):
            return False
        position += 1
    return True


def _natural_key(value: str) -> tuple[Any, ...]:
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in re.findall(r"[A-Z]+|[0-9]+", value)
    )


def _alphanumeric_length(value: str) -> int:
    return sum(character.isalnum() for character in value)


def _object_id(feature: dict[str, Any]) -> int:
    value = (feature.get("properties") or {}).get("OBJECTID")
    if not isinstance(value, int):
        raise ValueError("Address feature is missing an integer OBJECTID")
    return value
