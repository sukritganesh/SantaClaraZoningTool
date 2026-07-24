"""Expanded residential Flask interface tests."""

from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser

from santa_clara_zoning import ResidentialZoneSummaryPipeline
from santa_clara_zoning.lookup import (
    DEFAULT_ADDRESS_SNAPSHOT,
    DEFAULT_RESIDENTIAL_SNAPSHOT,
)
from santa_clara_zoning.web import create_app
from santa_clara_zoning.zone_descriptions import ZoneDescriptionProvider


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

    def suggestions(self, query: str) -> dict:
        response = self.client.get(
            "/api/address-suggestions",
            query_string={"q": query},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        return response.get_json()

    def map_context(self, address: str) -> tuple[int, dict]:
        response = self.client.get(
            "/api/property-map",
            query_string={"address": address},
        )
        self.assertEqual(response.mimetype, "application/json")
        return response.status_code, response.get_json()

    def test_default_application_uses_common_zone_pipeline_and_product_copy(self) -> None:
        self.assertIsInstance(
            self.app.extensions["zoning_analyzer"],
            ResidentialZoneSummaryPipeline,
        )
        self.assertIs(
            self.app.extensions["property_map_provider"],
            self.app.extensions["zoning_analyzer"],
        )
        self.assertIsInstance(
            self.app.extensions["zone_description_provider"],
            ZoneDescriptionProvider,
        )
        self.assertIsNone(
            self.app.extensions["zone_description_startup_error"]
        )
        landing = self.client.get("/").get_data(as_text=True)
        self.assertIn("Santa Clara Zoning Explorer", landing)
        self.assertIn("Selected residential zoning standards by address", landing)
        self.assertIn(
            '<span class="hero-easter-egg" aria-hidden="true">YIMBY</span>',
            landing,
        )
        self.assertNotIn("prototype", landing.lower())
        self.assertNotIn('name="selection_id"', landing)
        self.assertIn(
            '<label for="address">Santa Clara street address</label>',
            landing,
        )
        self.assertIn('role="combobox"', landing)
        self.assertIn('aria-autocomplete="list"', landing)
        self.assertIn('aria-controls="address-suggestion-list"', landing)
        self.assertIn('role="listbox"', landing)
        self.assertIn('aria-live="polite"', landing)
        document = _Document(landing)
        self.assertEqual(len(document.ids), len(set(document.ids)))
        for control in document.controls:
            self.assertIn(control, document.ids)

    def test_real_property_map_payloads_are_local_bounded_and_public(self) -> None:
        cases = {
            "2852 Sycamore Way": "R1-6L",
            "1240 White Drive": "R2",
            "3105 Patrick Henry Drive": "PH-R5",
            "4650 Old Ironsides Drive": "UC",
        }
        for address, zone in cases.items():
            with self.subTest(address=address):
                status_code, payload = self.map_context(address)
                self.assertEqual(status_code, 200)
                self.assertEqual(payload["contract_version"], "1.0.0")
                self.assertEqual(payload["status"], "ok")
                self.assertEqual(payload["property"]["zone"], zone)
                self.assertEqual(
                    payload["versions"],
                    {
                        "address_snapshot": "2026-07-16",
                        "residential_gis_snapshot": "2026-07-18",
                    },
                )
                self.assertGreater(payload["zoning_feature_count"], 0)
                self.assertEqual(
                    payload["zoning_feature_count"],
                    len(payload["supported_zoning"]["features"]),
                )
                self.assertEqual(
                    set(payload["selected_parcel"]["properties"]),
                    {"apn", "zone"},
                )
                serialized = json.dumps(payload).lower()
                for forbidden in (
                    '"objectid"',
                    '"source_object_id"',
                    '"acreage"',
                    '"general_plan"',
                    '"regulations"',
                    '"citations"',
                ):
                    self.assertNotIn(forbidden, serialized)

    def test_property_map_controlled_outcomes_do_not_expose_geometry(self) -> None:
        cases = {
            "1500 Warburton Avenue": (404, "outside_supported_residential_snapshot"),
            "324 Los Padres Boulevard": (409, "address_ambiguous"),
            "99999 No Such Street": (404, "address_not_found"),
        }
        for address, (expected_code, expected_status) in cases.items():
            with self.subTest(address=address):
                status_code, payload = self.map_context(address)
                self.assertEqual(status_code, expected_code)
                self.assertEqual(payload["status"], expected_status)
                self.assertNotIn("selected_parcel", payload)
                self.assertNotIn("supported_zoning", payload)

    def test_success_renders_accessible_responsive_map_context(self) -> None:
        body = self.body("2852 Sycamore Way")
        document = _Document(body)

        self.assertIn('class="property-context-grid"', body)
        self.assertIn('id="property-map-heading"', body)
        self.assertIn("Parcel and zoning context", body)
        self.assertIn('id="property-map"', body)
        self.assertIn('data-property-map', body)
        self.assertIn('role="region"', body)
        self.assertIn('tabindex="0"', body)
        self.assertIn('data-selected-zone="R1-6L"', body)
        self.assertIn('/api/property-map?address=2852+Sycamore+Way', body)
        self.assertIn('<details class="property-map-legend"', body)
        self.assertIn("<summary>Map legend</summary>", body)
        self.assertNotIn('<details class="property-map-legend" open', body)
        self.assertIn("Map layers", body)
        self.assertIn("Selected parcel", body)
        self.assertIn("Outside supported overlay", body)
        self.assertIn(
            "Unshaded areas are outside the Explorer’s currently supported "
            "zoning overlay and are not necessarily unzoned.",
            body,
        )
        self.assertIn("© OpenStreetMap contributors", body)
        self.assertIn('id="property-map-status"', body)
        self.assertIn('aria-live="polite"', body)
        self.assertEqual(len(document.ids), len(set(document.ids)))
        for control in document.controls:
            self.assertIn(control, document.ids)

    def test_local_suggestions_select_r2_without_exposing_analysis_data(self) -> None:
        payload = self.suggestions("1240 whi")

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["normalized_query"], "1240 WHI")
        self.assertEqual(payload["address_snapshot"], "2026-07-16")
        self.assertEqual(payload["total_matches"], 1)
        self.assertFalse(payload["truncated"])
        self.assertEqual(len(payload["suggestions"]), 1)
        suggestion = payload["suggestions"][0]
        self.assertEqual(suggestion["value"], "1240 White Drive")
        self.assertEqual(suggestion["source_record_count"], 1)
        serialized = json.dumps(payload).lower()
        for forbidden_key in (
            '"longitude"',
            '"latitude"',
            '"coordinates"',
            '"objectid"',
            '"apn"',
            '"parcel"',
            '"zoning"',
            '"regulations"',
        ):
            self.assertNotIn(forbidden_key, serialized)

        selected = self.app.extensions["zoning_analyzer"].analyze_address(
            suggestion["value"]
        )
        self.assertEqual(selected["status"], "residential_zone_summary_found")
        self.assertEqual(selected["property"]["zone"], "R2")

    def test_citywide_suggestion_keeps_outside_scope_outcome_safe(self) -> None:
        payload = self.suggestions("1500 warburton")

        self.assertEqual(payload["total_matches"], 1)
        value = payload["suggestions"][0]["value"]
        self.assertEqual(value, "1500 Warburton Avenue")
        selected = self.app.extensions["zoning_analyzer"].analyze_address(value)
        self.assertEqual(
            selected["status"],
            "outside_supported_residential_snapshot",
        )
        body = self.body(value)
        self.assertIn('data-result-kind="lookup_failure"', body)
        self.assertNotIn('class="standard-card"', body)

    def test_duplicate_suggestion_keeps_controlled_ambiguity(self) -> None:
        payload = self.suggestions("324 los padres")

        self.assertEqual(payload["total_matches"], 1)
        self.assertEqual(len(payload["suggestions"]), 1)
        suggestion = payload["suggestions"][0]
        self.assertEqual(suggestion["value"], "324 Los Padres Boulevard")
        self.assertEqual(suggestion["source_record_count"], 2)
        selected = self.app.extensions["zoning_analyzer"].analyze_address(
            suggestion["value"]
        )
        self.assertEqual(selected["status"], "address_ambiguous")

    def test_unit_heavy_base_reports_total_and_never_selects_a_unit(self) -> None:
        payload = self.suggestions("3710 el camino real")

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["total_matches"], 577)
        self.assertTrue(payload["truncated"])
        self.assertEqual(len(payload["suggestions"]), 8)
        self.assertEqual(
            payload["suggestions"][0]["value"],
            "3710 El Camino Real",
        )

    def test_r2_shows_three_uses_and_shared_standards_without_selection(self) -> None:
        body = self.body("1240 White Drive")

        self.assertIn('data-result-kind="success"', body)
        self.assertIn("Property Overview", body)
        self.assertIn("R2 is Santa Clara&#39;s low-density residential zone", body)
        self.assertIn("How to use this result", body)
        self.assertIn("Single-family dwelling", body)
        self.assertIn("Two-family dwelling", body)
        self.assertIn("Multifamily dwelling", body)
        self.assertNotIn("share the supported base-zone standards", body)
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
        permission_cards = re.findall(
            r'<article class="permission-card".*?</article>',
            body,
            flags=re.DOTALL,
        )
        self.assertEqual(len(permission_cards), 3)
        for card in permission_cards:
            self.assertIn("Permitted by right under the supported base zoning", card)
            self.assertNotIn("primary structure", card)
            self.assertNotIn("approval-free construction", card)
            self.assertNotIn('class="profile-note"', card)
            self.assertNotIn('class="item-notes"', card)

    def test_overview_and_staff_guidance_are_separate_accessible_sections(self) -> None:
        body = self.body("1240 White Drive")
        overview = re.search(
            r'<section class="content-section overview-panel".*?</section>',
            body,
            flags=re.DOTALL,
        )
        guidance = re.search(
            r'<section class="content-section result-guidance".*?</section>',
            body,
            flags=re.DOTALL,
        )

        self.assertIsNotNone(overview)
        self.assertIsNotNone(guidance)
        self.assertIn('aria-labelledby="overview-heading"', overview.group(0))
        self.assertIn('id="overview-heading">Property Overview</h2>', overview.group(0))
        self.assertIn('class="zone-overview-description"', overview.group(0))
        self.assertNotIn("Scope notice", overview.group(0))
        self.assertNotIn("Source details", overview.group(0))
        self.assertIn(
            'aria-labelledby="result-guidance-heading"',
            guidance.group(0),
        )
        self.assertIn(
            'id="result-guidance-heading">How to use this result</h2>',
            guidance.group(0),
        )
        self.assertIn("Scope notice", guidance.group(0))
        self.assertIn("Source details", guidance.group(0))

    def test_missing_description_provider_keeps_the_zoning_result(self) -> None:
        fallback_app = create_app(
            self.app.extensions["zoning_analyzer"],
            zone_description_provider=None,
            source_evidence_provider=None,
        )
        fallback_app.config.update(TESTING=True)
        response = fallback_app.test_client().get(
            "/",
            query_string={"address": "1240 White Drive"},
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-result-kind="success"', body)
        self.assertIn("Property Overview", body)
        self.assertIn("share the supported base-zone standards", body)
        self.assertNotIn('data-result-kind="system_error"', body)

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
        self.assertIn("Review competing source values", ph)
        self.assertIn("not an official City correction", ph)

        uc = self.body("4650 Old Ironsides Drive")
        self.assertGreaterEqual(uc.count("FAA-controlled"), 2)
        self.assertIn("Title 18 Table 2-4", uc)

    def test_unavailable_r1_pathway_stays_in_data_but_is_not_presented(self) -> None:
        body = self.body("636 Barto Street")
        result = self.app.extensions["zoning_analyzer"].analyze_address(
            "636 Barto Street"
        )

        self.assertTrue(result["special_pathways"])
        self.assertNotIn("Special residential pathways", body)
        self.assertNotIn("R1 Chapter 18.24 two-home pathway", body)
        self.assertNotIn("Analysis not evaluated", body)
        self.assertIn("Single-family dwelling", body)
        self.assertEqual(len(re.findall(r'class="permission-card"', body)), 1)
        self.assertNotIn("Choose a residential structure", body)
        self.assertNotIn("prototype", body.lower())
        self.assertIn('class="source-help" aria-label="Source help"', body)
        self.assertIn('class="source-help-icon" aria-hidden="true">i</span>', body)
        self.assertIn(
            "Select an “i” icon beside any rule to view its supporting citations and exact source.",
            body,
        )

    def test_consequential_qualifications_render_beside_affected_rules(self) -> None:
        barto = self.body("636 Barto Street")
        street_side = re.search(
            r'<tr data-capability-id="setback\.street_side".*?</tr>',
            barto,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(street_side)
        self.assertIn(
            'data-warning-kind="conditional_applicability"',
            street_side.group(0),
        )
        self.assertNotIn("Important qualifications", barto)

        brookside = self.body("108 Brookside Avenue")
        street_side = re.search(
            r'<tr data-capability-id="setback\.street_side".*?</tr>',
            brookside,
            flags=re.DOTALL,
        )
        interior_side = re.search(
            r'<tr data-capability-id="setback\.interior_side".*?</tr>',
            brookside,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(street_side)
        self.assertIsNotNone(interior_side)
        self.assertIn('data-warning-kind="source_conflict"', street_side.group(0))
        self.assertIn("Review competing source values", street_side.group(0))
        self.assertIn(
            'data-warning-kind="proposal_dependent_assignment"',
            interior_side.group(0),
        )

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
                self.assertNotIn('data-property-map', body)
                self.assertNotIn("Parcel and zoning context", body)
                self.assertNotIn('class="source-help"', body)

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
