"""Validated, presentation-only access to exact regulatory source evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import mimetypes
import re
from pathlib import Path
from typing import Any, Mapping


SOURCE_EVIDENCE_CONTRACT_VERSION = "1.0.0"
SOURCE_EVIDENCE_CATALOG_VERSION = "2026-07-22.1"
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE_ROOT = (
    DEFAULT_REPO_ROOT
    / "data/source_evidence/santa_clara/residential/2026-07-22.1"
)
DEFAULT_CATALOG_PATH = DEFAULT_EVIDENCE_ROOT / "catalog.json"
DEFAULT_MANIFEST_PATH = DEFAULT_EVIDENCE_ROOT / "evidence-manifest.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class SourceEvidenceIntegrityError(RuntimeError):
    """Reject an incomplete, modified, or unsafe source-evidence package."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class SourceEvidenceProvider:
    """Load one immutable catalog and return defensive, allowlisted evidence."""

    def __init__(
        self,
        *,
        repo_root: Path,
        catalog_path: Path,
        manifest_path: Path,
    ) -> None:
        self._repo_root = repo_root.resolve()
        self._catalog_path = catalog_path.resolve()
        self._manifest_path = manifest_path.resolve()
        manifest = _load_json(self._manifest_path, "evidence manifest")
        catalog = _load_json(self._catalog_path, "source-evidence catalog")
        self._documents = catalog.get("documents", {})
        self._page_images = catalog.get("page_images", {})
        if not isinstance(self._documents, dict) or not isinstance(
            self._page_images,
            dict,
        ):
            raise SourceEvidenceIntegrityError(
                "Evidence catalog inventories must be objects"
            )
        self._validate_manifest(manifest)
        self._validate_catalog(catalog)
        self._manifest = manifest
        self._catalog = catalog
        self._targets = catalog["targets"]
        self._documents = catalog["documents"]
        self._page_images = catalog["page_images"]
        self._binding_index = {
            (target["zone"], target["marker_id"], target["citation_id"]): target_id
            for target_id, target in self._targets.items()
        }

    @classmethod
    def from_defaults(cls) -> "SourceEvidenceProvider":
        """Load the released evidence add-on from its installed default path."""

        return cls(
            repo_root=DEFAULT_REPO_ROOT,
            catalog_path=DEFAULT_CATALOG_PATH,
            manifest_path=DEFAULT_MANIFEST_PATH,
        )

    @property
    def catalog_version(self) -> str:
        return str(self._catalog["catalog_version"])

    def links_for_view(self, view: Mapping[str, Any]) -> dict[str, dict[str, str]]:
        """Resolve every rendered source control to one exact catalog target."""

        if view.get("kind") != "success":
            return {}
        output: dict[str, dict[str, str]] = {}
        missing: list[tuple[str, str, str]] = []
        for context in source_control_contexts(view):
            key = (
                context["zone"],
                context["marker_id"],
                context["citation_id"],
            )
            target_id = self._binding_index.get(key)
            if target_id is None:
                missing.append(key)
                continue
            output.setdefault(context["marker_id"], {})[
                context["citation_id"]
            ] = target_id
        if missing:
            raise SourceEvidenceIntegrityError(
                "The evidence catalog does not cover every rendered source control: "
                + ", ".join("/".join(item) for item in missing[:5])
            )
        return copy.deepcopy(output)

    def get_target(self, target_id: str) -> dict[str, Any]:
        """Return one validated target with native record text when applicable."""

        target = self._targets.get(target_id)
        if not isinstance(target, dict):
            raise KeyError(target_id)
        result = copy.deepcopy(target)
        result["target_id"] = target_id
        result["catalog_version"] = self.catalog_version
        result["document"] = copy.deepcopy(self._documents[target["document_id"]])
        for location in result["locations"]:
            if location["kind"] == "pdf":
                location["page_image"] = copy.deepcopy(
                    self._page_images[location["page_image_id"]]
                )
            elif location["kind"] == "markdown":
                source = self._document_path(target["document_id"])
                lines = source.read_text(encoding="utf-8").splitlines()
                location["native_text"] = "\n".join(
                    lines[location["start_line"] - 1 : location["end_line"]]
                )
            elif location["kind"] == "json":
                source = _load_json(
                    self._document_path(target["document_id"]),
                    "project verification record",
                )
                value = _resolve_json_pointer(source, location["json_pointer"])
                location["native_text"] = json.dumps(
                    value,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
        return result

    def get_document(self, document_id: str) -> tuple[Path, dict[str, Any]]:
        """Return an allowlisted, checksum-verified document and metadata."""

        document = self._documents.get(document_id)
        if not isinstance(document, dict):
            raise KeyError(document_id)
        path = self._document_path(document_id)
        if sha256_file(path) != document["sha256"]:
            raise SourceEvidenceIntegrityError(
                f"Source document checksum changed: {document_id}"
            )
        return path, copy.deepcopy(document)

    def get_page_image(
        self,
        target_id: str,
        location_index: int,
    ) -> tuple[Path, dict[str, Any]]:
        """Return one allowlisted rendered page used by a target location."""

        target = self._targets.get(target_id)
        if not isinstance(target, dict):
            raise KeyError(target_id)
        locations = target["locations"]
        if not 0 <= location_index < len(locations):
            raise KeyError(location_index)
        location = locations[location_index]
        if location["kind"] != "pdf":
            raise KeyError(location_index)
        image_id = location["page_image_id"]
        image = self._page_images[image_id]
        path = self._safe_repo_path(image["local_path"])
        if sha256_file(path) != image["sha256"]:
            raise SourceEvidenceIntegrityError(
                f"Evidence page checksum changed: {image_id}"
            )
        return path, copy.deepcopy(image)

    def _document_path(self, document_id: str) -> Path:
        document = self._documents[document_id]
        return self._safe_repo_path(document["local_path"])

    def _safe_repo_path(self, relative: str) -> Path:
        if not isinstance(relative, str) or not relative:
            raise SourceEvidenceIntegrityError("Evidence paths must be non-empty")
        path = (self._repo_root / relative).resolve()
        if self._repo_root not in path.parents:
            raise SourceEvidenceIntegrityError("Evidence path escaped the repository")
        if not path.is_file():
            raise SourceEvidenceIntegrityError(f"Evidence artifact is missing: {relative}")
        return path

    def _validate_manifest(self, manifest: dict[str, Any]) -> None:
        if (
            manifest.get("contract_version") != SOURCE_EVIDENCE_CONTRACT_VERSION
            or manifest.get("catalog_version") != SOURCE_EVIDENCE_CATALOG_VERSION
            or manifest.get("ruleset_version") != "2026-07-19.5"
            or not isinstance(manifest.get("renderer"), dict)
            or not isinstance(manifest.get("source_documents"), dict)
            or not isinstance(manifest.get("files"), dict)
        ):
            raise SourceEvidenceIntegrityError("Unsupported evidence manifest")
        renderer = manifest["renderer"]
        if (
            not isinstance(renderer.get("identity"), str)
            or not renderer["identity"].strip()
            or not isinstance(renderer.get("local_path"), str)
            or not SHA256_RE.fullmatch(str(renderer.get("sha256", "")))
        ):
            raise SourceEvidenceIntegrityError("Invalid evidence renderer record")
        renderer_path = self._safe_repo_path(renderer["local_path"])
        if sha256_file(renderer_path) != renderer["sha256"]:
            raise SourceEvidenceIntegrityError("Evidence renderer checksum changed")
        try:
            relative_catalog = self._catalog_path.relative_to(self._repo_root).as_posix()
        except ValueError as exc:
            raise SourceEvidenceIntegrityError(
                "Evidence catalog must be inside the repository"
            ) from exc
        record = manifest["files"].get(relative_catalog)
        if not _valid_file_record(record):
            raise SourceEvidenceIntegrityError("Catalog is absent from its manifest")
        if (
            self._catalog_path.stat().st_size != record["size_bytes"]
            or sha256_file(self._catalog_path) != record["sha256"]
        ):
            raise SourceEvidenceIntegrityError("Catalog checksum does not match manifest")

        expected_files = {relative_catalog}
        for image_id, image in self._page_images.items():
            if not isinstance(image, dict) or not isinstance(
                image.get("local_path"), str
            ):
                raise SourceEvidenceIntegrityError(
                    f"Invalid evidence page manifest binding: {image_id}"
                )
            relative = image["local_path"]
            expected_files.add(relative)
            image_record = manifest["files"].get(relative)
            if not _valid_file_record(image_record):
                raise SourceEvidenceIntegrityError(
                    f"Evidence page is absent from its manifest: {image_id}"
                )
            path = self._safe_repo_path(relative)
            if (
                path.stat().st_size != image_record["size_bytes"]
                or sha256_file(path) != image_record["sha256"]
            ):
                raise SourceEvidenceIntegrityError(
                    f"Evidence page checksum does not match manifest: {image_id}"
                )
        if set(manifest["files"]) != expected_files:
            raise SourceEvidenceIntegrityError(
                "Evidence manifest file inventory does not match the catalog"
            )

        source_manifest = manifest["source_documents"]
        if set(source_manifest) != set(self._documents):
            raise SourceEvidenceIntegrityError(
                "Evidence source inventory does not match the catalog"
            )
        for document_id, document in self._documents.items():
            source_record = source_manifest.get(document_id)
            if (
                not isinstance(source_record, dict)
                or source_record.get("local_path") != document.get("local_path")
                or source_record.get("sha256") != document.get("sha256")
                or (
                    document.get("media_type") == "application/pdf"
                    and source_record.get("page_count") != document.get("page_count")
                )
            ):
                raise SourceEvidenceIntegrityError(
                    f"Evidence source manifest mismatch: {document_id}"
                )

    def _validate_catalog(self, catalog: dict[str, Any]) -> None:
        if (
            catalog.get("contract_version") != SOURCE_EVIDENCE_CONTRACT_VERSION
            or catalog.get("catalog_version") != SOURCE_EVIDENCE_CATALOG_VERSION
            or catalog.get("ruleset_version") != "2026-07-19.5"
            or not isinstance(catalog.get("documents"), dict)
            or not isinstance(catalog.get("page_images"), dict)
            or not isinstance(catalog.get("targets"), dict)
        ):
            raise SourceEvidenceIntegrityError("Unsupported source-evidence catalog")
        documents = catalog["documents"]
        page_images = catalog["page_images"]
        targets = catalog["targets"]
        if not documents or not targets:
            raise SourceEvidenceIntegrityError("Evidence catalog is empty")

        for document_id, document in documents.items():
            if (
                not isinstance(document_id, str)
                or not isinstance(document, dict)
                or document.get("classification")
                not in {"official_source", "project_verification_record"}
                or document.get("media_type")
                not in {"application/pdf", "text/markdown", "application/json"}
                or not SHA256_RE.fullmatch(str(document.get("sha256", "")))
                or (
                    document.get("media_type") == "application/pdf"
                    and (
                        not isinstance(document.get("page_count"), int)
                        or document["page_count"] < 1
                    )
                )
            ):
                raise SourceEvidenceIntegrityError(
                    f"Invalid evidence document record: {document_id}"
                )
            path = self._safe_repo_path(document["local_path"])
            if sha256_file(path) != document["sha256"]:
                raise SourceEvidenceIntegrityError(
                    f"Source document checksum changed: {document_id}"
                )

        for image_id, image in page_images.items():
            if (
                not isinstance(image, dict)
                or image.get("document_id") not in documents
                or not isinstance(image.get("pdf_page"), int)
                or image["pdf_page"] < 1
                or image["pdf_page"]
                > documents[image["document_id"]].get("page_count", 0)
                or not isinstance(image.get("width"), int)
                or not isinstance(image.get("height"), int)
                or image["width"] < 1
                or image["height"] < 1
                or not SHA256_RE.fullmatch(str(image.get("sha256", "")))
            ):
                raise SourceEvidenceIntegrityError(
                    f"Invalid evidence page image: {image_id}"
                )
            path = self._safe_repo_path(image["local_path"])
            if sha256_file(path) != image["sha256"]:
                raise SourceEvidenceIntegrityError(
                    f"Evidence page checksum changed: {image_id}"
                )

        bindings: set[tuple[str, str, str]] = set()
        for target_id, target in targets.items():
            if (
                not isinstance(target_id, str)
                or not isinstance(target, dict)
                or target.get("document_id") not in documents
                or not all(
                    isinstance(target.get(key), str) and target[key]
                    for key in (
                        "zone",
                        "marker_id",
                        "citation_id",
                        "regulation_label",
                        "displayed_result",
                        "locator",
                    )
                )
                or not isinstance(target.get("locations"), list)
                or not target["locations"]
            ):
                raise SourceEvidenceIntegrityError(
                    f"Invalid evidence target: {target_id}"
                )
            binding = (
                target["zone"],
                target["marker_id"],
                target["citation_id"],
            )
            if binding in bindings:
                raise SourceEvidenceIntegrityError(
                    f"Duplicate contextual evidence binding: {binding}"
                )
            bindings.add(binding)
            for location in target["locations"]:
                self._validate_location(
                    location,
                    document_id=target["document_id"],
                    documents=documents,
                    page_images=page_images,
                )

    def _validate_location(
        self,
        location: Any,
        *,
        document_id: str,
        documents: dict[str, Any],
        page_images: dict[str, Any],
    ) -> None:
        if not isinstance(location, dict):
            raise SourceEvidenceIntegrityError("Evidence location must be an object")
        kind = location.get("kind")
        if (
            kind not in {"pdf", "markdown", "json"}
            or not isinstance(location.get("excerpt"), str)
            or not location["excerpt"].strip()
            or not SHA256_RE.fullmatch(str(location.get("excerpt_sha256", "")))
            or sha256_text(location["excerpt"]) != location["excerpt_sha256"]
            or location.get("verification_status") != "human_verified"
            or not isinstance(location.get("verified_date"), str)
        ):
            raise SourceEvidenceIntegrityError("Invalid evidence location metadata")
        document = documents[document_id]
        if kind == "pdf":
            image = page_images.get(location.get("page_image_id"))
            regions = location.get("regions")
            if (
                document["media_type"] != "application/pdf"
                or not isinstance(location.get("pdf_page"), int)
                or location["pdf_page"] < 1
                or location["pdf_page"] > document.get("page_count", 0)
                or not isinstance(location.get("printed_page"), str)
                or not location["printed_page"].strip()
                or not isinstance(image, dict)
                or image["document_id"] != document_id
                or image["pdf_page"] != location["pdf_page"]
                or not isinstance(regions, list)
                or not regions
            ):
                raise SourceEvidenceIntegrityError("Invalid PDF evidence location")
            for region in regions:
                if not _valid_region(region):
                    raise SourceEvidenceIntegrityError(
                        "PDF highlight region is outside normalized bounds"
                    )
        elif kind == "markdown":
            if (
                document["media_type"] != "text/markdown"
                or not isinstance(location.get("start_line"), int)
                or not isinstance(location.get("end_line"), int)
                or location["start_line"] < 1
                or location["end_line"] < location["start_line"]
            ):
                raise SourceEvidenceIntegrityError("Invalid Markdown evidence location")
            lines = self._document_path(document_id).read_text(
                encoding="utf-8"
            ).splitlines()
            if location["end_line"] > len(lines):
                raise SourceEvidenceIntegrityError("Markdown line range is invalid")
            native = "\n".join(
                lines[location["start_line"] - 1 : location["end_line"]]
            )
            if location["excerpt"] not in native:
                raise SourceEvidenceIntegrityError(
                    "Markdown evidence excerpt is outside its line range"
                )
        else:
            if document["media_type"] != "application/json" or not isinstance(
                location.get("json_pointer"), str
            ):
                raise SourceEvidenceIntegrityError("Invalid JSON evidence location")
            value = _resolve_json_pointer(
                _load_json(self._document_path(document_id), "JSON evidence"),
                location["json_pointer"],
            )
            native = json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            if location["excerpt"] not in native:
                raise SourceEvidenceIntegrityError(
                    "JSON evidence excerpt is outside its pointer value"
                )


def source_control_contexts(view: Mapping[str, Any]) -> list[dict[str, str]]:
    """Return the source controls rendered by ``_success.html`` in stable order."""

    if view.get("kind") != "success":
        return []
    property_record = view.get("property")
    if not isinstance(property_record, Mapping) or not isinstance(
        property_record.get("zone"), str
    ):
        raise SourceEvidenceIntegrityError("Successful view has no zone")
    zone = property_record["zone"]
    output: list[dict[str, str]] = []

    for group in (
        "use_permissions",
        "approvals",
        "key_standards",
        "setbacks",
    ):
        items = view.get(group)
        if not isinstance(items, list):
            raise SourceEvidenceIntegrityError(f"View group is invalid: {group}")
        for item in items:
            if not isinstance(item, Mapping):
                raise SourceEvidenceIntegrityError(f"View item is invalid: {group}")
            _append_contexts(
                output,
                zone=zone,
                marker_id=str(item["rule_id"]),
                label=str(item["label"]),
                displayed_result=_displayed_result(item),
                citation_ids=item.get("citation_ids"),
            )

    warnings = view.get("warnings")
    if not isinstance(warnings, list):
        raise SourceEvidenceIntegrityError("View warnings are invalid")
    for warning in warnings:
        if not isinstance(warning, Mapping):
            raise SourceEvidenceIntegrityError("View warning is invalid")
        if warning.get("kind") == "source_conflict":
            for assertion in warning.get("assertions", []):
                marker_id = f"{warning['warning_id']}-{assertion['assertion_id']}"
                _append_contexts(
                    output,
                    zone=zone,
                    marker_id=marker_id,
                    label=str(warning["title"]),
                    displayed_result=_displayed_result(assertion),
                    citation_ids=assertion.get("source_refs"),
                )
        elif warning.get("kind") == "not_evaluated_exception":
            _append_contexts(
                output,
                zone=zone,
                marker_id=str(warning["warning_id"]),
                label=str(warning["title"]),
                displayed_result="Not evaluated",
                citation_ids=warning.get("citation_ids"),
            )
    return output


def _append_contexts(
    output: list[dict[str, str]],
    *,
    zone: str,
    marker_id: str,
    label: str,
    displayed_result: str,
    citation_ids: Any,
) -> None:
    if not isinstance(citation_ids, list) or not all(
        isinstance(item, str) and item for item in citation_ids
    ):
        raise SourceEvidenceIntegrityError("Source-control citations are invalid")
    for citation_id in citation_ids:
        output.append(
            {
                "zone": zone,
                "marker_id": marker_id,
                "citation_id": citation_id,
                "regulation_label": label,
                "displayed_result": displayed_result,
            }
        )


def _displayed_result(value: Mapping[str, Any]) -> str:
    for key in ("status_label", "label"):
        if isinstance(value.get(key), str) and key == "status_label":
            return str(value[key])
    requirement = value.get("requirement")
    if isinstance(requirement, Mapping):
        return _format_requirement(requirement)
    presented = value.get("presented_value")
    if isinstance(presented, Mapping):
        return _format_requirement(presented)
    raw = value.get("value")
    if isinstance(raw, Mapping):
        return _format_requirement(raw)
    return "Source-backed requirement"


def _format_requirement(value: Mapping[str, Any]) -> str:
    kind = value.get("kind")
    if kind in {"maximum_quantity", "distance"}:
        nested = value.get("value") if kind == "maximum_quantity" else value
        if isinstance(nested, Mapping):
            return _format_quantity(nested)
    if kind == "quantity_range":
        unit = _unit_label(value.get("unit"))
        return f"{value.get('minimum')}–{value.get('maximum')} {unit}".strip()
    if kind == "setback":
        base = value.get("base")
        if isinstance(base, Mapping) and isinstance(base.get("value"), Mapping):
            return _format_requirement(base["value"])
    if kind == "paired_distances":
        members = value.get("members")
        if isinstance(members, list):
            return "; ".join(
                _format_quantity(item)
                for item in members
                if isinstance(item, Mapping)
            )
    if kind == "lot_area_tiered_maximum":
        return "Tiered maximum structure coverage"
    if kind == "no_maximum_listed":
        return "No maximum listed"
    if kind == "plan_dependent":
        return "Plan/project review required"
    if isinstance(value.get("label"), str):
        return str(value["label"])
    return "Source-backed requirement"


def _format_quantity(value: Mapping[str, Any]) -> str:
    number = value.get("number")
    return f"{number} {_unit_label(value.get('unit'))}".strip()


def _unit_label(value: Any) -> str:
    return {
        "ft": "feet",
        "percent": "percent",
        "sq_ft": "square feet",
        "dwelling_units_per_acre": "dwelling units/acre",
        "stories": "stories",
    }.get(value, str(value or ""))


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceEvidenceIntegrityError(f"Could not read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise SourceEvidenceIntegrityError(f"{label} must contain one object")
    return value


def _resolve_json_pointer(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise SourceEvidenceIntegrityError("JSON Pointer must begin with a slash")
    current = value
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and token.isdigit():
            index = int(token)
            if index >= len(current):
                raise SourceEvidenceIntegrityError("JSON Pointer index is invalid")
            current = current[index]
        else:
            raise SourceEvidenceIntegrityError("JSON Pointer does not resolve")
    return current


def _valid_region(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {"x", "y", "width", "height"}:
        return False
    if not all(
        isinstance(value[key], (int, float)) and not isinstance(value[key], bool)
        for key in value
    ):
        return False
    return (
        0 <= value["x"] < 1
        and 0 <= value["y"] < 1
        and 0 < value["width"] <= 1
        and 0 < value["height"] <= 1
        and value["x"] + value["width"] <= 1.000001
        and value["y"] + value["height"] <= 1.000001
    )


def _valid_file_record(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("size_bytes"), int)
        and value["size_bytes"] >= 0
        and isinstance(value.get("sha256"), str)
        and SHA256_RE.fullmatch(value["sha256"]) is not None
    )


def document_download_name(document: Mapping[str, Any]) -> str:
    """Return a safe human-readable filename for a served document."""

    suffix = mimetypes.guess_extension(str(document["media_type"])) or ""
    base = re.sub(r"[^a-z0-9]+", "-", str(document["document_id"]).lower()).strip(
        "-"
    )
    return f"{base}{suffix}"
