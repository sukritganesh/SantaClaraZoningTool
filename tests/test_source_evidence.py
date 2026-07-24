"""Source-evidence catalog, viewer, and document-boundary tests."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from santa_clara_zoning.source_evidence import (
    DEFAULT_CATALOG_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_REPO_ROOT,
    SourceEvidenceIntegrityError,
    SourceEvidenceProvider,
)
from santa_clara_zoning.web import create_app
from tests.test_residential_presentation import _view


EVIDENCE_AVAILABLE = DEFAULT_CATALOG_PATH.is_file() and DEFAULT_MANIFEST_PATH.is_file()


class _IdCollector(HTMLParser):
    def __init__(self, body: str) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.feed(body)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element_id = dict(attrs).get("id")
        if element_id:
            self.ids.append(element_id)


def _target(
    provider: SourceEvidenceProvider,
    *,
    zone: str,
    marker_suffix: str,
    citation_id: str,
) -> dict:
    return next(
        provider.get_target(target_id)
        for target_id, value in provider._targets.items()
        if value["zone"] == zone
        and value["marker_id"].endswith(marker_suffix)
        and value["citation_id"] == citation_id
    )


@unittest.skipUnless(EVIDENCE_AVAILABLE, "source-evidence runtime add-on is not installed")
class SourceEvidenceCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.provider = SourceEvidenceProvider.from_defaults()

    def test_catalog_covers_every_rendered_control_for_all_twelve_zones(self) -> None:
        counts = {}
        for zone in (
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
        ):
            links = self.provider.links_for_view(_view(zone))
            counts[zone] = sum(len(citations) for citations in links.values())
            self.assertGreater(counts[zone], 0)
        self.assertEqual(sum(counts.values()), 443)

    def test_contextual_table_cells_are_distinct_and_exact(self) -> None:
        cases = (
            ("R1-6L", "maximum_primary_structure_height", "r1-standards-table", 25, "25"),
            ("R2", "maximum_primary_structure_height", "citywide-residential-standards-table", 25, "32"),
            ("PH-R5", "maximum_primary_structure_height", "patrick-henry-plan-standards-table", 63, "135"),
            ("UC", "maximum_primary_structure_height", "patrick-henry-plan-standards-table", 63, "FAA"),
        )
        target_ids = set()
        for zone, marker, citation, page, excerpt in cases:
            with self.subTest(zone=zone):
                target = _target(
                    self.provider,
                    zone=zone,
                    marker_suffix=marker,
                    citation_id=citation,
                )
                target_ids.add(target["target_id"])
                self.assertEqual(target["locations"][0]["pdf_page"], page)
                self.assertIn(excerpt, target["locations"][0]["excerpt"])
                self.assertEqual(len(target["locations"][0]["regions"]), 2)
        self.assertEqual(len(target_ids), len(cases))

    def test_density_and_plan_classification_anchors_are_zone_specific(self) -> None:
        density_cases = (
            ("R1-6L", "0.1 - 10 DU/AC"),
            ("R6", "60 - 350 DU/AC"),
            ("PH-R5", "51 – 100 DU/AC"),
            ("UC", "120 - 250 DU/AC"),
            ("HDF", "60 - 149 DU/AC"),
        )
        density_regions = set()
        for zone, excerpt in density_cases:
            target = _target(
                self.provider,
                zone=zone,
                marker_suffix="gross_residential_density",
                citation_id="residential-density-table-1-1",
            )
            location = target["locations"][0]
            self.assertEqual(location["pdf_page"], 12)
            self.assertEqual(len(location["regions"]), 2)
            self.assertIn(excerpt, location["excerpt"])
            density_regions.add(json.dumps(location["regions"], sort_keys=True))
        self.assertEqual(len(density_regions), len(density_cases))

        classification = _target(
            self.provider,
            zone="VR",
            marker_suffix="gross_residential_density",
            citation_id="patrick-henry-plan-classifications",
        )
        self.assertEqual(classification["locations"][0]["pdf_page"], 62)
        self.assertIn(
            "VILLAGE RESIDENTIAL",
            classification["locations"][0]["excerpt"],
        )
        self.assertEqual(len(classification["locations"][0]["regions"]), 1)

    def test_native_records_keep_original_format_and_hidden_paths_have_no_target(self) -> None:
        markdown = _target(
            self.provider,
            zone="R1-6L",
            marker_suffix="maximum_primary_structure_height",
            citation_id="amendment-audit",
        )
        self.assertEqual(
            markdown["document"]["classification"],
            "project_verification_record",
        )
        self.assertEqual(markdown["locations"][0]["kind"], "markdown")
        self.assertIn("No adopted post-July-2025", markdown["locations"][0]["native_text"])

        self.assertFalse(
            any(
                target["zone"] == "R1-6L"
                and target["citation_id"] == "approved-r1-v2-scope"
                for target in self.provider._targets.values()
            )
        )

    def test_results_and_page_metadata_are_defensive_copies(self) -> None:
        target_id = next(iter(self.provider._targets))
        first = self.provider.get_target(target_id)
        first["locations"][0]["excerpt"] = "changed"
        second = self.provider.get_target(target_id)
        self.assertNotEqual(second["locations"][0]["excerpt"], "changed")
        if second["locations"][0]["kind"] == "pdf":
            _, image = self.provider.get_page_image(target_id, 0)
            image["sha256"] = "changed"
            _, again = self.provider.get_page_image(target_id, 0)
            self.assertNotEqual(again["sha256"], "changed")

    def test_unknown_ids_fail_closed(self) -> None:
        with self.assertRaises(KeyError):
            self.provider.get_target("missing")
        with self.assertRaises(KeyError):
            self.provider.get_document("../../etc/passwd")


class SourceEvidenceMutationTest(unittest.TestCase):
    def test_out_of_bounds_region_rejects_entire_provider(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.pdf"
            page = root / "page.png"
            source.write_bytes(b"checksummed source")
            page.write_bytes(b"checksummed page")
            catalog_path = root / "catalog.json"
            manifest_path = root / "manifest.json"
            catalog = {
                "contract_version": "1.0.0",
                "catalog_version": "2026-07-22.1",
                "ruleset_version": "2026-07-19.5",
                "documents": {
                    "doc": {
                        "document_id": "doc",
                        "title": "Document",
                        "version": "1",
                        "effective_date": None,
                        "local_path": "source.pdf",
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "verification_status": "verified",
                        "classification": "official_source",
                        "media_type": "application/pdf",
                        "page_count": 1,
                    }
                },
                "page_images": {
                    "page": {
                        "document_id": "doc",
                        "pdf_page": 1,
                        "local_path": "page.png",
                        "width": 10,
                        "height": 10,
                        "sha256": hashlib.sha256(page.read_bytes()).hexdigest(),
                    }
                },
                "targets": {
                    "target": {
                        "zone": "R1-6L",
                        "marker_id": "rule",
                        "citation_id": "citation",
                        "regulation_label": "Height",
                        "displayed_result": "25 feet",
                        "document_id": "doc",
                        "locator": "Page 1",
                        "locations": [
                            {
                                "kind": "pdf",
                                "pdf_page": 1,
                                "printed_page": "1",
                                "page_image_id": "page",
                                "regions": [
                                    {"x": 0.9, "y": 0.1, "width": 0.2, "height": 0.2}
                                ],
                                "excerpt": "25",
                                "excerpt_sha256": hashlib.sha256(b"25").hexdigest(),
                                "verification_status": "human_verified",
                                "verified_date": "2026-07-22",
                            }
                        ],
                    }
                },
            }
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            manifest = {
                "contract_version": "1.0.0",
                "catalog_version": "2026-07-22.1",
                "ruleset_version": "2026-07-19.5",
                "renderer": {
                    "identity": "test renderer",
                    "local_path": "renderer.py",
                    "sha256": hashlib.sha256(b"test renderer").hexdigest(),
                },
                "source_documents": {
                    "doc": {
                        "local_path": "source.pdf",
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "page_count": 1,
                    }
                },
                "files": {
                    "catalog.json": {
                        "size_bytes": catalog_path.stat().st_size,
                        "sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
                    },
                    "page.png": {
                        "size_bytes": page.stat().st_size,
                        "sha256": hashlib.sha256(page.read_bytes()).hexdigest(),
                    },
                },
            }
            (root / "renderer.py").write_bytes(b"test renderer")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(
                SourceEvidenceIntegrityError,
                "normalized bounds",
            ):
                SourceEvidenceProvider(
                    repo_root=root,
                    catalog_path=catalog_path,
                    manifest_path=manifest_path,
                )


@unittest.skipUnless(EVIDENCE_AVAILABLE, "source-evidence runtime add-on is not installed")
class SourceEvidenceWebTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        cls.client = cls.app.test_client()

    def test_popover_has_new_tab_exact_link_and_bottom_appendix(self) -> None:
        response = self.client.get(
            "/",
            query_string={"address": "2852 Sycamore Way"},
        )
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("View exact source", body)
        self.assertIn('target="_blank"', body)
        self.assertIn('rel="noopener"', body)
        self.assertNotIn("Source receipt", body)
        self.assertNotIn('href="#source-r1-standards-table"', body)
        self.assertIn('id="source-r1-standards-table"', body)

    def test_official_evidence_page_is_accessible_and_does_not_leak_paths(self) -> None:
        target = _target(
            self.app.extensions["source_evidence_provider"],
            zone="R1-6L",
            marker_suffix="maximum_primary_structure_height",
            citation_id="r1-standards-table",
        )
        response = self.client.get(f"/source-evidence/{target['target_id']}")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Official source", body)
        self.assertIn("Maximum primary-structure height", body)
        self.assertIn("R1-6L displayed result", body)
        self.assertIn("Open original PDF at this page", body)
        self.assertIn("data-evidence-zoom-in", body)
        self.assertIn("data-evidence-previous", body)
        self.assertIn("Matching text excerpt", body)
        self.assertIn("navigation aid", body)
        self.assertLess(
            body.index("Highlighted source page"),
            body.index("Source identity"),
        )
        self.assertNotIn(str(DEFAULT_REPO_ROOT), body)
        self.assertNotIn("data/raw/", body)
        self.assertNotIn("Google Drive", body)
        document = _IdCollector(body)
        self.assertEqual(len(document.ids), len(set(document.ids)))
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("object-src 'none'", response.headers["Content-Security-Policy"])

    def test_native_project_record_is_escaped_and_labeled(self) -> None:
        target = _target(
            self.app.extensions["source_evidence_provider"],
            zone="R1-6L",
            marker_suffix="maximum_primary_structure_height",
            citation_id="amendment-audit",
        )
        response = self.client.get(f"/source-evidence/{target['target_id']}")
        body = response.get_data(as_text=True)
        self.assertIn("Project verification record", body)
        self.assertIn("Lines 61–65", body)
        self.assertIn("No adopted post-July-2025 amendment", body)

    def test_document_route_supports_ranges_and_safe_headers(self) -> None:
        response = self.client.get(
            "/source-documents/sc-title18-2025-07",
            headers={"Range": "bytes=0-99"},
        )
        self.assertEqual(response.status_code, 206)
        self.assertEqual(len(response.data), 100)
        self.assertTrue(response.headers["Content-Range"].startswith("bytes 0-99/"))
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("inline", response.headers["Content-Disposition"])
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("max-age=31536000", response.headers["Cache-Control"])
        response.close()

    def test_page_route_and_controlled_failures(self) -> None:
        target = _target(
            self.app.extensions["source_evidence_provider"],
            zone="R2",
            marker_suffix="maximum_primary_structure_height",
            citation_id="citywide-residential-standards-table",
        )
        page = self.client.get(
            f"/source-evidence/{target['target_id']}/pages/0.png"
        )
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.mimetype, "image/png")
        page.close()
        self.assertEqual(
            self.client.get(
                f"/source-evidence/{target['target_id']}/pages/99.png"
            ).status_code,
            404,
        )
        self.assertEqual(self.client.get("/source-evidence/missing").status_code, 404)
        self.assertEqual(self.client.get("/source-documents/missing").status_code, 404)
        self.assertEqual(
            self.client.get("/source-documents/..%2F..%2Fetc%2Fpasswd").status_code,
            404,
        )

    def test_multi_page_evidence_is_available_without_javascript(self) -> None:
        target = _target(
            self.app.extensions["source_evidence_provider"],
            zone="R1-6L",
            marker_suffix="maximum_primary_structure_height",
            citation_id="height-method",
        )
        self.assertGreater(len(target["locations"]), 1)
        response = self.client.get(f"/source-evidence/{target['target_id']}")
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body.count("data-evidence-page data-page-index="), 2)
        self.assertIn("Page 1 of 2", body)

    def test_explicitly_unconfigured_provider_is_controlled_503(self) -> None:
        app = create_app(source_evidence_provider=None)
        app.config.update(TESTING=True)
        response = app.test_client().get("/source-evidence/anything")
        self.assertEqual(response.status_code, 503)
        self.assertIn("source receipt remain unchanged", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
