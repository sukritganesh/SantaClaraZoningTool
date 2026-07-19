"""Expanded residential Flask interface tests."""

from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser

from santa_clara_zoning import ResidentialZoneSummaryPipeline
from santa_clara_zoning.lookup import (
    DEFAULT_ADDRESS_SNAPSHOT,
    DEFAULT_RESIDENTIAL_SNAPSHOT,
)
from santa_clara_zoning.web import create_app


SNAPSHOTS_AVAILABLE = (
    (DEFAULT_ADDRESS_SNAPSHOT / "address_points.geojson").is_file()
    and (DEFAULT_RESIDENTIAL_SNAPSHOT / "parcels_residential.geojson").is_file()
    and (
        DEFAULT_RESIDENTIAL_SNAPSHOT / "current_zoning_residential.geojson"
    ).is_file()
)


class _Document(HTMLParser):
    def __init__(self, body: str) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.fragments: list[str] = []
        self.controls: list[str] = []
        self.feed(body)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(str(values["id"]))
        href = values.get("href") or ""
        if href.startswith("#"):
            self.fragments.append(href[1:])
        if values.get("aria-controls"):
            self.controls.append(str(values["aria-controls"]))


@unittest.skipUnless(
    SNAPSHOTS_AVAILABLE,
    "canonical residential GIS snapshots are not present",
)
class ResidentialWebIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        cls.client = cls.app.test_client()
        if cls.app.extensions["startup_error"] is not None:
            raise AssertionError("Residential application reported a startup error")

    def body(self, address: str) -> str:
        response = self.client.get("/", query_string={"address": address})
        self.assertEqual(response.status_code, 200)
        return response.get_data(as_text=True)

    def test_default_application_uses_common_zone_pipeline_and_product_copy(self) -> None:
        self.assertIsInstance(
            self.app.extensions["zoning_analyzer"],
            ResidentialZoneSummaryPipeline,
        )
        landing = self.client.get("/").get_data(as_text=True)
        self.assertIn("Santa Clara Zoning Explorer", landing)
        self.assertIn("Selected residential zoning standards by address", landing)
        self.assertNotIn("prototype", landing.lower())
        self.assertNotIn('name="selection_id"', landing)

    def test_r2_shows_three_uses_and_shared_standards_without_selection(self) -> None:
        body = self.body("1240 White Drive")

        self.assertIn('data-result-kind="success"', body)
        self.assertIn("R2 base-zone standards", body)
        self.assertIn("Single-family dwelling", body)
        self.assertIn("Two-family dwelling", body)
        self.assertIn("Multifamily dwelling", body)
        self.assertIn("share the supported base-zone standards", body)
        self.assertIn("8–19 dwelling units/acre", body)
        self.assertIn("Objective Design Standards", body)
        self.assertIn("Applies to Multifamily dwelling", body)
        self.assertNotIn('name="selection_id"', body)
        self.assertNotIn("Choose a residential structure", body)
        self.assertEqual(
            len(re.findall(r'class="standard-card"', body)),
            4,
        )
        self.assertEqual(
            len(re.findall(r'class="permission-card"', body)),
            3,
        )

    def test_typed_nonnumeric_and_conflict_results_render_truthfully(self) -> None:
        r3 = self.body("1577 Pomeroy Avenue")
        self.assertIn("Lots below 10000 sq ft", r3)
        self.assertIn("60 percent", r3)
        self.assertIn("No maximum listed", r3)
        self.assertNotIn("Unlimited", r3)

        ph = self.body("3105 Patrick Henry Drive")
        self.assertIn("Plan-dependent", ph)
        self.assertIn("Zero is not a valid fallback", ph)
        self.assertIn("51–100 dwelling units/acre", ph)
        self.assertIn("Selected ruleset value", ph)
        self.assertIn("Competing source assertions", ph)
        self.assertIn("not an official City correction", ph)

        uc = self.body("4650 Old Ironsides Drive")
        self.assertGreaterEqual(uc.count("FAA-controlled"), 2)
        self.assertIn("Title 18 Table 2-4", uc)

    def test_r1_pathway_is_visible_without_receiving_dimensional_rules(self) -> None:
        body = self.body("636 Barto Street")

        self.assertIn("Special residential pathways", body)
        self.assertIn("R1 Chapter 18.24 two-home pathway", body)
        self.assertIn("Analysis not evaluated", body)
        self.assertIn("Single-family dwelling", body)
        self.assertEqual(len(re.findall(r'class="permission-card"', body)), 1)
        self.assertNotIn("Choose a residential structure", body)
        self.assertNotIn("prototype", body.lower())

    def test_failure_outcomes_never_render_regulatory_cards(self) -> None:
        cases = {
            "1500 Warburton Avenue": "outside_supported_residential_snapshot",
            "324 Los Padres Boulevard": "address_ambiguous",
            "99999 No Such Street": "address_not_found",
        }
        pipeline = self.app.extensions["zoning_analyzer"]
        for address, status in cases.items():
            with self.subTest(status=status):
                result = pipeline.analyze_address(address)
                body = self.body(address)
                self.assertEqual(result["status"], status)
                self.assertIn('data-result-kind="lookup_failure"', body)
                self.assertNotIn("data-capability-id", body)
                self.assertNotIn('class="standard-card"', body)
                self.assertNotIn('class="permission-card"', body)
                self.assertNotIn("Regulatory sources", body)

    def test_source_links_and_accessibility_relationships_are_closed(self) -> None:
        body = self.body("1240 White Drive")
        document = _Document(body)

        self.assertEqual(len(document.ids), len(set(document.ids)))
        for fragment in document.fragments:
            self.assertIn(fragment, document.ids)
        for control in document.controls:
            self.assertIn(control, document.ids)
        self.assertIn('aria-live="polite"', body)
        self.assertIn('role="search"', body)
        self.assertIn('tabindex="0"', body)
        self.assertIn('scope="col"', body)
        self.assertIn('scope="row"', body)
        self.assertNotIn("Return to result", body)


if __name__ == "__main__":
    unittest.main()
