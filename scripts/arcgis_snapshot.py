"""Shared primitives for reproducible ArcGIS REST snapshots."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_HEADERS = {
    "Accept": "application/json, application/geo+json",
    "User-Agent": "SantaClaraZoningPortal-Snapshot/0.1",
}


def encode_url(url: str, params: dict[str, str]) -> str:
    """Encode query parameters for a GET request."""

    return f"{url}?{urllib.parse.urlencode(params)}"


def encode_form(params: dict[str, str]) -> bytes:
    """Encode ArcGIS query parameters for a POST request."""

    return urllib.parse.urlencode(params).encode("utf-8")


def fetch_bytes(url: str, *, data: bytes | None = None, attempts: int = 5) -> bytes:
    """Fetch a response with bounded retries for transient network failures."""

    request = urllib.request.Request(url, data=data, headers=DEFAULT_HEADERS)
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == attempts:
                raise RuntimeError(f"Failed after {attempts} attempts: {url}") from exc
            time.sleep(min(2**attempt, 20))

    raise AssertionError("unreachable")


def parse_json(payload: bytes, *, source_url: str) -> dict[str, Any]:
    """Parse JSON and surface ArcGIS error payloads as exceptions."""

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response from {source_url}") from exc

    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected JSON response from {source_url}")
    if "error" in parsed:
        raise RuntimeError(f"ArcGIS error from {source_url}: {parsed['error']}")
    return parsed


def write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def write_json(path: Path, value: Any, *, indent: int | None = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=indent, sort_keys=indent is not None) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def chunks(values: list[int], size: int) -> list[list[int]]:
    return [values[index : index + size] for index in range(0, len(values), size)]
