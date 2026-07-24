#!/usr/bin/env python3
"""Build the deterministic source-evidence 1.0.0 runtime add-on."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from santa_clara_zoning.residential_pipeline import ResidentialStandardsPipeline
from santa_clara_zoning.residential_presentation import present_residential_summary
from santa_clara_zoning.residential_summary import ResidentialZoneSummaryPipeline
from santa_clara_zoning.ruleset import ApprovedResidentialRuleset
from santa_clara_zoning.source_evidence import (
    SOURCE_EVIDENCE_CATALOG_VERSION,
    SOURCE_EVIDENCE_CONTRACT_VERSION,
    sha256_file,
    sha256_text,
    source_control_contexts,
)


RULESET_PATH = REPO_ROOT / "rulesets/santa_clara/residential/2026-07-19.5/ruleset.json"
RENDERER_PATH = REPO_ROOT / "scripts/render_source_evidence_pages.py"
OUTPUT_ROOT = (
    REPO_ROOT
    / "data/source_evidence/santa_clara/residential/2026-07-22.1"
)
BUNDLE_PATH = (
    REPO_ROOT / "demo-data/santa-clara-source-evidence-runtime-data-2026-07-22.1.zip"
)
BUNDLE_MANIFEST_PATH = (
    REPO_ROOT / "demo-data/source-evidence-bundle-manifest-2026-07-22.1.json"
)
VERIFIED_DATE = "2026-07-22"
SUPPORTED_ZONES = (
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
OFFICIAL_URLS = {
    "ordinance-2085-objective-design-standards": (
        "https://santaclara.legistar1.com/santaclara/attachments/"
        "b6ae8ae3-dd0d-4bc2-bdaf-648c6605a81f.pdf"
    ),
}


class BuildError(RuntimeError):
    """Reject incomplete or nonreproducible source-evidence input."""


class _StaticLookup:
    def __init__(self, zone: str) -> None:
        self.zone = zone

    def lookup(self, entered_address: str) -> dict[str, Any]:
        return {
            "status": "residential_zone_found",
            "reason_code": "supported_residential_match",
            "query": {
                "entered_address": entered_address,
                "normalized_address": entered_address.upper(),
            },
            "versions": {
                "address_snapshot": "2026-07-16",
                "residential_gis_snapshot": "2026-07-18",
            },
            "sources": {},
            "address": {"display_address": f"1 Synthetic {self.zone} Street"},
            "parcel": {"apn": f"synthetic-{self.zone}", "designation": self.zone},
            "zoning": {
                "designation": self.zone,
                "parcel_attribute_agrees": True,
            },
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--bundle", type=Path, default=BUNDLE_PATH)
    parser.add_argument("--bundle-manifest", type=Path, default=BUNDLE_MANIFEST_PATH)
    parser.add_argument("--render-python", default=_find_pdf_python())
    parser.add_argument("--pdfinfo", default=_find_tool("pdfinfo"))
    parser.add_argument("--pdftotext", default=_find_tool("pdftotext"))
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the currently installed catalog instead of rebuilding it.",
    )
    return parser.parse_args()


def _find_tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    dependencies = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies"
    candidates = (
        dependencies / "native/poppler/poppler/bin" / name,
        dependencies / "bin/override" / name,
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return name


def _find_pdf_python() -> str:
    candidate = (
        Path.home()
        / ".cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
    )
    return str(candidate) if candidate.is_file() else "python3"


def build(args: argparse.Namespace) -> None:
    ruleset = json.loads(RULESET_PATH.read_text(encoding="utf-8"))
    if ruleset.get("version") != "2026-07-19.5":
        raise BuildError("Source evidence must bind approved ruleset 2026-07-19.5")
    output_root = args.output_root.resolve()
    if output_root.exists():
        for path in sorted(output_root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    output_root.mkdir(parents=True, exist_ok=True)
    pages_root = output_root / "pages"
    pages_root.mkdir()

    documents = _documents(ruleset, args.pdfinfo)
    citations = ruleset["shared"]["citations"]
    contexts = _all_contexts()
    expected_citations = {item["citation_id"] for item in contexts}
    missing = expected_citations - set(citations)
    if missing:
        raise BuildError(f"Rendered citations are absent from the ruleset: {sorted(missing)}")

    target_specs: list[tuple[dict[str, str], dict[str, Any], list[dict[str, Any]]]] = []
    requested_pages: set[tuple[str, int]] = set()
    for context in contexts:
        citation = citations[context["citation_id"]]
        document_id = citation["source_document_id"]
        locations = _locations_for(
            context,
            document_id=document_id,
            citation_id=context["citation_id"],
            document=documents[document_id],
        )
        for location in locations:
            if location["kind"] == "pdf":
                requested_pages.add((document_id, location["pdf_page"]))
        target_specs.append((context, citation, locations))

    pages_by_document: dict[str, list[int]] = {}
    for document_id, page in sorted(requested_pages):
        pages_by_document.setdefault(document_id, []).append(page)
    for document_id, pages in pages_by_document.items():
        document = documents[document_id]
        if max(pages) > document["page_count"]:
            raise BuildError(f"Requested page exceeds {document_id} page count")
        _render_pages(
            args.render_python,
            REPO_ROOT / document["local_path"],
            pages,
            document_id,
            pages_root,
        )

    page_images: dict[str, dict[str, Any]] = {}
    for document_id, page in sorted(requested_pages):
        document = documents[document_id]
        image_id = f"{document_id}-page-{page}"
        image_path = pages_root / f"{image_id}.png"
        width, height = _png_dimensions(image_path)
        page_images[image_id] = {
            "document_id": document_id,
            "pdf_page": page,
            "local_path": image_path.relative_to(REPO_ROOT).as_posix(),
            "renderer": "pypdfium2/PDFium at 144 DPI (pinned build runtime)",
            "width": width,
            "height": height,
            "size_bytes": image_path.stat().st_size,
            "sha256": sha256_file(image_path),
        }

    pdf_texts = {
        document_id: _extract_pdf_pages(
            args.pdftotext,
            REPO_ROOT / documents[document_id]["local_path"],
        )
        for document_id in pages_by_document
    }

    targets: dict[str, dict[str, Any]] = {}
    for context, citation, locations in target_specs:
        target_id = _target_id(context)
        if target_id in targets:
            raise BuildError(f"Duplicate target id: {target_id}")
        for location in locations:
            location["excerpt_sha256"] = sha256_text(location["excerpt"])
            location["verification_status"] = "human_verified"
            location["verified_date"] = VERIFIED_DATE
            if location["kind"] == "pdf":
                location["page_image_id"] = (
                    f"{citation['source_document_id']}-page-{location['pdf_page']}"
                )
                _verify_pdf_excerpt(
                    pdf_texts[citation["source_document_id"]],
                    location["pdf_page"],
                    location["excerpt"],
                )
            elif location["kind"] == "markdown":
                _verify_markdown_location(
                    REPO_ROOT / documents[citation["source_document_id"]]["local_path"],
                    location,
                )
            else:
                _verify_json_location(
                    REPO_ROOT / documents[citation["source_document_id"]]["local_path"],
                    location,
                )
        targets[target_id] = {
            **context,
            "document_id": citation["source_document_id"],
            "locator": citation["locator"],
            "topic": citation["topic"],
            "locations": locations,
        }

    catalog = {
        "contract_version": SOURCE_EVIDENCE_CONTRACT_VERSION,
        "catalog_version": SOURCE_EVIDENCE_CATALOG_VERSION,
        "ruleset_version": "2026-07-19.5",
        "ruleset_sha256": sha256_file(RULESET_PATH),
        "verified_date": VERIFIED_DATE,
        "supported_zones": list(SUPPORTED_ZONES),
        "documents": documents,
        "page_images": page_images,
        "targets": dict(sorted(targets.items())),
    }
    catalog_path = output_root / "catalog.json"
    _write_json(catalog_path, catalog)

    evidence_files = [catalog_path, *sorted(pages_root.glob("*.png"))]
    evidence_manifest = {
        "contract_version": SOURCE_EVIDENCE_CONTRACT_VERSION,
        "catalog_version": SOURCE_EVIDENCE_CATALOG_VERSION,
        "ruleset_version": "2026-07-19.5",
        "verified_date": VERIFIED_DATE,
        "renderer": {
            "identity": "pypdfium2/PDFium at 144 DPI (pinned build runtime)",
            "local_path": RENDERER_PATH.relative_to(REPO_ROOT).as_posix(),
            "sha256": sha256_file(RENDERER_PATH),
        },
        "source_documents": {
            document_id: {
                "local_path": document["local_path"],
                "sha256": document["sha256"],
                **(
                    {"page_count": document["page_count"]}
                    if "page_count" in document
                    else {}
                ),
            }
            for document_id, document in documents.items()
        },
        "files": {
            path.relative_to(REPO_ROOT).as_posix(): _file_record(path)
            for path in evidence_files
        },
    }
    evidence_manifest_path = output_root / "evidence-manifest.json"
    _write_json(evidence_manifest_path, evidence_manifest)

    bundle_files = [evidence_manifest_path, *evidence_files]
    _write_bundle(args.bundle.resolve(), bundle_files)
    bundle_manifest = {
        "bundle_contract_version": "1.0.0",
        "bundle_id": "santa-clara-source-evidence-runtime-data-2026-07-22.1",
        "catalog_version": SOURCE_EVIDENCE_CATALOG_VERSION,
        "install_root": ".",
        "archive": {
            "file": args.bundle.name,
            "format": "zip",
            "size_bytes": args.bundle.stat().st_size,
            "sha256": sha256_file(args.bundle),
        },
        "included_files": [
            {"path": path.relative_to(REPO_ROOT).as_posix(), **_file_record(path)}
            for path in sorted(bundle_files)
        ],
    }
    _write_json(args.bundle_manifest.resolve(), bundle_manifest)


def validate_installed(output_root: Path) -> None:
    from santa_clara_zoning.source_evidence import SourceEvidenceProvider

    provider = SourceEvidenceProvider(
        repo_root=REPO_ROOT,
        catalog_path=output_root / "catalog.json",
        manifest_path=output_root / "evidence-manifest.json",
    )
    contexts = _all_contexts()
    target_count = len(provider._targets)  # Internal count is part of this build gate.
    if target_count != len(contexts):
        raise BuildError(
            f"Catalog target count {target_count} does not match controls {len(contexts)}"
        )
    for zone in SUPPORTED_ZONES:
        provider.links_for_view(_view(zone))
    representative = {
        ("R1-6L", "maximum_primary_structure_height", "r1-standards-table"): "25",
        ("R2", "maximum_primary_structure_height", "citywide-residential-standards-table"): "32",
        ("PH-R5", "maximum_primary_structure_height", "patrick-henry-plan-standards-table"): "135",
        ("UC", "maximum_primary_structure_height", "patrick-henry-plan-standards-table"): "FAA",
    }
    for (zone, marker_suffix, citation_id), excerpt in representative.items():
        target = next(
            value
            for value in provider._targets.values()
            if value["zone"] == zone
            and value["marker_id"].endswith(marker_suffix)
            and value["citation_id"] == citation_id
        )
        if not any(excerpt in location["excerpt"] for location in target["locations"]):
            raise BuildError(f"Representative target is not exact: {zone}/{citation_id}")
    print(
        f"Validated source-evidence {provider.catalog_version}: "
        f"{target_count} contextual targets across {len(SUPPORTED_ZONES)} zones"
    )


def _documents(ruleset: dict[str, Any], pdfinfo: str) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for document_id, source in sorted(ruleset["shared"]["source_documents"].items()):
        path = REPO_ROOT / source["local_path"]
        if not path.is_file() or sha256_file(path) != source["sha256"]:
            raise BuildError(f"Checksummed source is unavailable: {document_id}")
        suffix = path.suffix.lower()
        media_type = {
            ".pdf": "application/pdf",
            ".md": "text/markdown",
            ".json": "application/json",
        }.get(suffix)
        if media_type is None:
            raise BuildError(f"Unsupported evidence document type: {path}")
        record = {
            "document_id": document_id,
            "title": source["title"],
            "version": source["version"],
            "effective_date": source.get("effective_date"),
            "local_path": source["local_path"],
            "sha256": source["sha256"],
            "verification_status": source["verification_status"],
            "classification": (
                "official_source"
                if media_type == "application/pdf"
                else "project_verification_record"
            ),
            "media_type": media_type,
        }
        if media_type == "application/pdf":
            record["page_count"] = _page_count(pdfinfo, path)
        if document_id in OFFICIAL_URLS:
            record["official_url"] = OFFICIAL_URLS[document_id]
        output[document_id] = record
    return output


def _all_contexts() -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for zone in SUPPORTED_ZONES:
        output.extend(source_control_contexts(_view(zone)))
    keys = [
        (item["zone"], item["marker_id"], item["citation_id"])
        for item in output
    ]
    if len(keys) != len(set(keys)):
        raise BuildError("Rendered source controls are not uniquely addressable")
    return output


def _view(zone: str) -> dict[str, Any]:
    ruleset = ApprovedResidentialRuleset.load()
    selection = ResidentialStandardsPipeline(
        lookup_engine=_StaticLookup(zone),
        ruleset=ruleset,
    )
    summary = ResidentialZoneSummaryPipeline(selection)
    return present_residential_summary(summary.analyze_address("1 Test Street"))


def _locations_for(
    context: dict[str, str],
    *,
    document_id: str,
    citation_id: str,
    document: dict[str, Any],
) -> list[dict[str, Any]]:
    if document["media_type"] == "text/markdown":
        start, end, excerpt = _markdown_anchor(citation_id, context)
        return [
            {
                "kind": "markdown",
                "start_line": start,
                "end_line": end,
                "excerpt": excerpt,
            }
        ]
    if document["media_type"] == "application/json":
        return [
            {
                "kind": "json",
                "json_pointer": "/not_evaluated",
                "excerpt": "Accessory structures",
            }
        ]
    return _pdf_anchor(citation_id, context)


def _pdf_anchor(citation_id: str, context: dict[str, str]) -> list[dict[str, Any]]:
    zone = context["zone"]
    marker = context["marker_id"]
    if citation_id in {"r1-standards-table", "citywide-residential-standards-table"}:
        return [_title18_table_23(context, citation_id)]
    if citation_id == "residential-density-table-2-3":
        return [_title18_table_23({**context, "marker_id": "gross_residential_density"}, citation_id)]
    if citation_id in {"use-table", "citywide-use-table"}:
        return [_title18_use_table(context)]
    if citation_id in {
        "patrick-henry-plan-standards-table",
        "patrick-henry-title18-standards-table",
    }:
        return [
            _patrick_table_42(context)
            if citation_id == "patrick-henry-plan-standards-table"
            else _title18_table_24(context)
        ]
    if citation_id in {"patrick-henry-plan-use-table", "patrick-henry-title18-use-table"}:
        return [
            _pdf(64, "58", [(62, 196, 335, 30, 792, 612), (367, 196, 40, 30, 792, 612)], "Dwelling, Multifamily")
            if citation_id == "patrick-henry-plan-use-table"
            else _pdf(23, "2-5", [(63, 215, 115, 30, 612, 792), (190, 215, 190, 30, 612, 792)], "Dwelling, Multifamily")
        ]
    if citation_id == "citywide-r1-r2-height-transition":
        return [
            _title18_table_23(
                {**context, "marker_id": "maximum_primary_structure_height"},
                citation_id,
            )
        ]
    if citation_id == "residential-density-table-1-1":
        return [_density_table_11(zone)]
    if citation_id == "residential-density-zone-purpose":
        return [_zone_purpose(zone)]
    if citation_id == "patrick-henry-plan-classifications":
        return [_patrick_classification(zone)]
    anchors: dict[str, list[dict[str, Any]]] = {
        "zoning-clearance": [
            _pdf(21, "2-3", [(32, 160, 545, 165, 612, 792)], "Zoning Clearance required"),
            _pdf(412, "6-39", [(34, 120, 544, 290, 612, 792)], "Zoning Clearance shall be required"),
        ],
        "architectural-review": [_pdf(398, "6-25", [(34, 95, 544, 410, 612, 792)], "Architectural Review Process")],
        "r1-additional-standards": [_pdf(30, "2-12", [(34, 105, 544, 590, 612, 792)], "Other Applicable Regulations")],
        "r1-8l-corner-side": [_pdf(32, "2-14", [(34, 75, 544, 160, 612, 792)], "shall not be less than 15 feet in width")],
        "conflict-rule": [
            _pdf(7, "1-5", [(34, 185, 544, 410, 612, 792)], "Rules of Interpretation"),
            _pdf(8, "1-6", [(34, 620, 544, 105, 612, 792)], "the more restrictive provisions shall apply"),
        ],
        "residential-encroachments": [_pdf(31, "2-13", [(34, 90, 544, 595, 612, 792)], "Residential Zone Setback Encroachments")],
        "general-projections": [
            _pdf(184, "3-1", [(34, 80, 544, 650, 612, 792)], "Permitted Projections into Required Setback Areas"),
            _pdf(185, "3-2", [(34, 75, 544, 650, 612, 792)], "bay window and chimney projections"),
        ],
        "height-method": [
            _pdf(186, "3-3", [(34, 85, 544, 565, 612, 792)], "Height Measurement and Exceptions"),
            _pdf(478, "8-11", [(34, 390, 544, 125, 612, 792)], "Grade (adjacent ground elevation)"),
        ],
        "setback-method": [_pdf(187, "3-4", [(34, 80, 544, 650, 612, 792)], "Setbacks – Measurement and Requirements")],
        "coverage-definition": [_pdf(492, "8-25", [(34, 570, 544, 120, 612, 792)], "Structure Coverage")],
        "nonconformities": [
            _pdf(356, "5-1", [(34, 85, 544, 580, 612, 792)], "General Nonconforming Provisions"),
            _pdf(360, "5-5", [(34, 85, 544, 580, 612, 792)], "Nonconforming Structures"),
        ],
        "r1-two-unit-pathway": [_pdf(84, "2-64", [(34, 75, 544, 315, 612, 792)], "up to two homes are permitted on a single parcel")],
        "objective-design-standards": [
            _pdf(6, "2-71", [(34, 75, 544, 610, 612, 792)], "Objective Design Standards for City-wide Multi-Family"),
            _pdf(7, "2-72", [(34, 70, 544, 420, 612, 792)], "applicable to new multi-family development")],
        "residential-density-plan-control": [
            _pdf(5, "1-3", [(34, 95, 544, 610, 612, 792)], "Relationship to General Plan"),
            _pdf(24, "2-6", [(34, 155, 544, 140, 612, 792)], "Maximum density standards shall be consistent")],
        "patrick-henry-title18-zone-purpose": [_pdf(20, "2-2", [(34, 75, 544, 620, 612, 792)], "Patrick Henry Very-High-Density Residential Zone")],
        "patrick-henry-plan-setback-guidance": [
            _pdf(148, "142", [(48, 80, 696, 470, 792, 612)], "Building Frontages and Setbacks"),
            _pdf(149, "143", [(48, 80, 696, 470, 792, 612)], "setback"),
            _pdf(150, "144", [(48, 80, 696, 470, 792, 612)], "Alleys and Service Access"),
        ],
        "patrick-henry-plan-implementation": [
            _pdf(179, "173", [(48, 80, 696, 470, 792, 612)], "Implementation"),
            _pdf(180, "174", [(48, 80, 696, 470, 792, 612)], "review"),
        ],
    }
    try:
        return anchors[citation_id]
    except KeyError as exc:
        raise BuildError(f"No PDF anchor is authored for {citation_id}/{zone}/{marker}") from exc


def _title18_table_23(context: dict[str, str], citation_id: str) -> dict[str, Any]:
    zone = context["zone"]
    marker = context["marker_id"]
    centers = {"R1-6L": 189, "R1-8L": 234, "R2": 279, "R3": 324, "R4": 369, "R5": 414, "R6": 457}
    center = centers[zone]
    if "maximum_structure_coverage" in marker:
        return _pdf(24, "2-6", [(36, 620, 132, 60, 612, 792), (center - 17, 630, 34, 48, 612, 792)], _coverage_excerpt(zone))
    rows = {
        "maximum_primary_structure_height": (554, 61, _height_excerpt(zone)),
        "maximum_stories": (614, 58, _stories_excerpt(zone)),
        "gross_residential_density": (674, 31, _density_excerpt(zone)),
        "front": (337, 48, _setback_excerpt(zone, "front")),
        "interior_side": (431, 54, _setback_excerpt(zone, "interior")),
        "street_side": (379, 48, _setback_excerpt(zone, "street")),
        "rear": (484, 46, _setback_excerpt(zone, "rear")),
    }
    key = next((name for name in rows if name in marker), None)
    if key is None:
        return _pdf(25, "2-7", [(36, 285, 540, 420, 612, 792)], "Residential Zone Development Standards")
    top, height, excerpt = rows[key]
    return _pdf(25, "2-7", [(36, top, 132, height, 612, 792), (center - 17, top, 34, height, 612, 792)], excerpt)


def _title18_table_24(context: dict[str, str]) -> dict[str, Any]:
    zone = context["zone"]
    marker = context["marker_id"]
    centers = {"PH-R5": 214, "UV": 261, "VR": 309, "UC": 360, "HDF": 406}
    center = centers[zone]
    rows = {
        "maximum_structure_coverage": (272, 86, "Structure Coverage (maximum percentage)"),
        "front": (350, 75, "Setbacks (minimum)"),
        "interior_side": (350, 75, "Setbacks (minimum)"),
        "street_side": (350, 75, "Setbacks (minimum)"),
        "rear": (350, 75, "Setbacks (minimum)"),
        "maximum_primary_structure_height": (427, 51, _patrick_height_excerpt(zone)),
        "maximum_stories": (478, 31, _patrick_stories_excerpt(zone)),
        "gross_residential_density": (510, 31, _patrick_density_excerpt(zone)),
    }
    key = next((name for name in rows if name in marker), None)
    if key is None:
        return _pdf(27, "2-9", [(36, 135, 540, 420, 612, 792)], "Patrick Henry Residential Zone Development Standards")
    top, height, excerpt = rows[key]
    return _pdf(27, "2-9", [(36, top, 153, height, 612, 792), (center - 19, top, 38, height, 612, 792)], excerpt)


def _patrick_table_42(context: dict[str, str]) -> dict[str, Any]:
    zone = context["zone"]
    marker = context["marker_id"]
    centers = {"PH-R5": 288, "UV": 366, "VR": 445, "UC": 524, "HDF": 603}
    center = centers[zone]
    rows = {
        "maximum_structure_coverage": (175, 55, "Structure Coverage (maximum percentage)"),
        "front": (230, 49, "Setbacks (minimum)"),
        "interior_side": (230, 49, "Setbacks (minimum)"),
        "street_side": (230, 49, "Setbacks (minimum)"),
        "rear": (230, 105, "Setback encroachments are allowed per the quantitative standards"),
        "maximum_primary_structure_height": (342, 64, _patrick_height_excerpt(zone)),
        "maximum_stories": (406, 32, _patrick_stories_excerpt(zone)),
        "gross_residential_density": (438, 37, _patrick_density_excerpt(zone)),
    }
    key = next((name for name in rows if name in marker), None)
    if key is None:
        return _pdf(63, "57", [(60, 95, 650, 430, 792, 612)], "Patrick Henry Residential Zone Development Standards")
    top, height, excerpt = rows[key]
    return _pdf(63, "57", [(62, top, 178, height, 792, 612), (center - 28, top, 56, height, 792, 612)], excerpt)


def _title18_use_table(context: dict[str, str]) -> dict[str, Any]:
    marker = context["marker_id"]
    zone = context["zone"]
    row = 609 if "single_family" in marker else 620 if "two_family" in marker else 598
    label = "Dwelling, Single-Family" if row == 609 else "Dwelling, Two-Family" if row == 620 else "Dwelling, Multifamily"
    centers = {"R1-6L": 211, "R1-8L": 211, "R2": 261, "R3": 312, "R4": 312, "R5": 361, "R6": 405}
    center = centers[zone]
    return _pdf(21, "2-3", [(65, row - 8, 120, 22, 612, 792), (center - 16, row - 8, 32, 22, 612, 792)], label)


def _density_table_11(zone: str) -> dict[str, Any]:
    rows = {
        "R1-6L": (139, 20, "0.1 - 10 DU/AC"),
        "R1-8L": (158, 22, "0.1 - 10 DU/AC"),
        "R2": (180, 17, "8 - 19 DU/AC"),
        "R3": (192, 22, "20 - 36 DU/AC"),
        "R4": (213, 22, "37 - 50 DU/AC"),
        "R5": (234, 22, "51 - 100 DU/AC"),
        "PH-R5": (255, 22, "51 – 100 DU/AC"),
        "R6": (276, 22, "60 - 350 DU/AC"),
        "UV": (297, 22, "100-149 DU/AC"),
        "VR": (318, 22, "60 - 149 DU/AC"),
        "UC": (339, 22, "120 - 250 DU/AC"),
        "HDF": (360, 25, "60 - 149 DU/AC"),
    }
    top, height, excerpt = rows[zone]
    return _pdf(
        12,
        "1-10",
        [
            (72, top, 218, height, 612, 792),
            (300, top, 90, height, 612, 792),
        ],
        excerpt,
    )


def _zone_purpose(zone: str) -> dict[str, Any]:
    anchors = {
        "R1-6L": (19, "2-1", 366, 82, "R1-6L Single-Family Residential"),
        "R1-8L": (19, "2-1", 453, 82, "R1-8L Single-Family"),
        "R2": (19, "2-1", 540, 82, "R2 Low Density Zone"),
        "R3": (20, "2-2", 63, 81, "R3 Medium-Low Residential"),
        "R4": (20, "2-2", 150, 81, "R4 High-Density Zone"),
        "R5": (20, "2-2", 237, 105, "R5 High- Density Zone"),
        "PH-R5": (20, "2-2", 237, 105, "PH-R5 Patrick Henry"),
        "R6": (20, "2-2", 345, 118, "R6 Transit Neighborhood"),
        "UV": (20, "2-2", 468, 81, "UV Urban Village Zone"),
        "VR": (20, "2-2", 552, 51, "VR Village Residential Zone"),
        "UC": (20, "2-2", 606, 105, "UC Urban Center Zone"),
        "HDF": (21, "2-3", 63, 81, "HD Flex High Density Flex Zone"),
    }
    page, printed, top, height, excerpt = anchors[zone]
    return _pdf(page, printed, [(104, top, 440, height, 612, 792)], excerpt)


def _patrick_classification(zone: str) -> dict[str, Any]:
    anchors = {
        "PH-R5": (60, 70, 78, 198, 272, "VERY HIGH-DENSITY RESIDENTIAL"),
        "UV": (60, 284, 78, 200, 250, "URBAN VILLAGE"),
        "UC": (60, 500, 78, 202, 390, "URBAN CENTER"),
        "HDF": (62, 70, 78, 198, 250, "HIGH-DENSITY FLEX"),
        "VR": (62, 284, 78, 200, 160, "VILLAGE RESIDENTIAL"),
    }
    page, left, top, width, height, excerpt = anchors[zone]
    return _pdf(
        page,
        str(page - 6),
        [(left, top, width, height, 792, 612)],
        excerpt,
    )


def _markdown_anchor(citation_id: str, context: dict[str, str]) -> tuple[int, int, str]:
    marker = context["marker_id"]
    if citation_id == "amendment-audit":
        return 61, 65, "No adopted post-July-2025 amendment was identified"
    if citation_id == "residential-amendment-audit":
        return 63, 67, "No adopted post-July-2025 amendment was identified"
    if citation_id == "citywide-expansion-verification":
        if "dwelling" in marker:
            return 114, 147, "Residential use and structure matrix"
        if "approval" in marker or "clearance" in marker or "review" in marker:
            return 149, 163, "Approval-path findings"
        return 165, 219, "Citywide development-standard assertions"
    if citation_id == "residential-density-verification":
        return 13, 57, "The supported result is the base-zone gross residential density range"
    if citation_id == "residential-density-amendment-audit":
        return 11, 29, "No adopted post-July-2025 amendment identified"
    if citation_id == "patrick-henry-authoring-verification":
        if "dwelling" in marker:
            return 38, 48, "Each of the five designations has three explicit use-permission records"
        if any(key in marker for key in ("maximum", "setback", "density", "stories", "coverage")):
            return 50, 78, "The successor retains exactly the ten already-supported profile capabilities"
        return 80, 96, "The successor discloses but does not evaluate"
    raise BuildError(f"No Markdown anchor is authored for {citation_id}/{marker}")


def _pdf(
    page: int,
    printed_page: str,
    raw_regions: list[tuple[float, float, float, float, float, float]],
    excerpt: str,
) -> dict[str, Any]:
    return {
        "kind": "pdf",
        "pdf_page": page,
        "printed_page": printed_page,
        "regions": [
            {
                "x": round(x / page_width, 6),
                "y": round(y / page_height, 6),
                "width": round(width / page_width, 6),
                "height": round(height / page_height, 6),
            }
            for x, y, width, height, page_width, page_height in raw_regions
        ],
        "excerpt": excerpt,
    }


def _height_excerpt(zone: str) -> str:
    return {"R1-6L": "Height (all other zones) 25", "R1-8L": "Height (all other zones) 25", "R2": "Height (all other zones) 25 25 32", "R3": "Height (all other zones) 25 25 32 40", "R4": "Height (all other zones) 25 25 32 40 80", "R5": "Height (all other zones) 25 25 32 40 80 100", "R6": "Height (all other zones) 25 25 32 40 80 100 200"}[zone]


def _stories_excerpt(zone: str) -> str:
    return "Number of Stories 2 2 2 4 8 10 20"


def _density_excerpt(zone: str) -> str:
    return {"R1-6L": "Allowable Density 0.1-10", "R1-8L": "Allowable Density 0.1-10 0.1-10", "R2": "Allowable Density 0.1-10 0.1-10 8-19", "R3": "Allowable Density 0.1-10 0.1-10 8-19 20-36", "R4": "Allowable Density 0.1-10 0.1-10 8-19 20-36 37-50", "R5": "51-99", "R6": "85-350"}[zone]


def _coverage_excerpt(zone: str) -> str:
    return "Structure Coverage (maximum percentage)"


def _setback_excerpt(zone: str, kind: str) -> str:
    labels = {"front": "Front", "interior": "Side, Interior", "street": "Side, Corner", "rear": "Rear, single-story"}
    return labels[kind]


def _patrick_height_excerpt(zone: str) -> str:
    return {"PH-R5": "Height (all other zones) 135", "UV": "Height (all other zones) 135 160", "VR": "Height (all other zones) 135 160 160", "UC": "Height (all other zones) 135 160 160 FAA", "HDF": "Height (all other zones) 135 160 160 FAA 160"}[zone]


def _patrick_stories_excerpt(zone: str) -> str:
    return "Number of Stories (all other zones) 10 12 12 FAA 12"


def _patrick_density_excerpt(zone: str) -> str:
    return {"PH-R5": "Allowable Density 51-99", "UV": "Allowable Density 51-99 100-149", "VR": "Allowable Density 51-99 100-149 60-149", "UC": "120-250", "HDF": "60-149"}[zone]


def _target_id(context: dict[str, str]) -> str:
    raw = "\0".join((context["zone"], context["marker_id"], context["citation_id"]))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    zone = re.sub(r"[^a-z0-9]+", "-", context["zone"].lower()).strip("-")
    citation = re.sub(r"[^a-z0-9]+", "-", context["citation_id"].lower()).strip("-")
    return f"{zone}-{citation}-{digest}"


def _page_count(pdfinfo: str, path: Path) -> int:
    result = subprocess.run(
        [pdfinfo, str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"^Pages:\s+(\d+)$", result.stdout, re.MULTILINE)
    if not match:
        raise BuildError(f"Could not read PDF page count: {path}")
    return int(match.group(1))


def _render_pages(
    render_python: str,
    source: Path,
    pages: list[int],
    document_id: str,
    destination_root: Path,
) -> None:
    """Render requested pages after opening each source PDF only once."""

    subprocess.run(
        [
            render_python,
            str(RENDERER_PATH),
            str(source),
            str(destination_root),
            document_id,
            ",".join(str(page) for page in sorted(set(pages))),
        ],
        check=True,
        capture_output=True,
    )
    for page in pages:
        destination = destination_root / f"{document_id}-page-{page}.png"
        if not destination.is_file():
            raise BuildError(f"PDFium did not render {source} page {page}")


def _extract_pdf_pages(pdftotext: str, source: Path) -> list[str]:
    result = subprocess.run(
        [pdftotext, "-layout", str(source), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.split("\f")


def _verify_pdf_excerpt(pages: list[str], page: int, excerpt: str) -> None:
    if page > len(pages) or _normalize(excerpt) not in _normalize(pages[page - 1]):
        raise BuildError(f"PDF excerpt was not found on page {page}: {excerpt!r}")


def _verify_markdown_location(path: Path, location: dict[str, Any]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    value = "\n".join(lines[location["start_line"] - 1 : location["end_line"]])
    if location["excerpt"] not in value:
        raise BuildError(f"Markdown excerpt is outside its line range: {path}")


def _verify_json_location(path: Path, location: dict[str, Any]) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))["not_evaluated"]
    rendered = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    if location["excerpt"] not in rendered:
        raise BuildError(f"JSON excerpt is outside its pointer value: {path}")


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("‐", "-").replace("‑", "-")).strip().casefold()


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as source:
        header = source.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise BuildError(f"Rendered page is not PNG: {path}")
    return struct.unpack(">II", header[16:24])


def _file_record(path: Path) -> dict[str, Any]:
    return {"size_bytes": path.stat().st_size, "sha256": sha256_file(path)}


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_bundle(path: Path, files: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in sorted(files):
            info = zipfile.ZipInfo(source.relative_to(REPO_ROOT).as_posix())
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def main() -> int:
    args = parse_args()
    try:
        if args.validate_only:
            validate_installed(args.output_root.resolve())
        else:
            build(args)
            validate_installed(args.output_root.resolve())
    except (BuildError, OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"Source-evidence build failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
