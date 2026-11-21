"""Focused tests for the Block 7.4 Flask interface boundary."""

from __future__ import annotations

import copy
import re
import unittest
from html.parser import HTMLParser
from unittest.mock import Mock, patch

from santa_clara_zoning import (
    PipelineIntegrityError,
    R1StandardsPipeline,
    RulesetLoadError,
    present_pipeline_result,
)
from santa_clara_zoning.lookup import DEFAULT_ADDRESS_SNAPSHOT, DEFAULT_R1_SNAPSHOT
from santa_clara_zoning.web import create_app


SNAPSHOTS_AVAILABLE = (
    (DEFAULT_ADDRESS_SNAPSHOT / "address_points.geojson").is_file()
    and (DEFAULT_R1_SNAPSHOT / "parcels_r1.geojson").is_file()
    and (DEFAULT_R1_SNAPSHOT / "current_zoning_r1.geojson").is_file()
)


def _view(kind: str = "success") -> dict:
    return {
        "presentation_contract_version": "1.0.0",
        "kind": kind,
        "source_reason_code": "fixture_reason",
        "query": {
            "entered_address": "Fixture address",
            "normalized_address": "FIXTURE ADDRESS",
        },
        "property": {
            "display_address": "Fixture address" if kind == "success" else None,
            "apn": "fixture-apn" if kind == "success" else None,
            "zone": "R1-fixture" if kind == "success" else None,
            "scope_label": "R1 base-zone prototype",
        },
        "overview": {
            "headline": "Fixture headline",
            "summary": "Fixture summary",
            "disclaimer": "Fixture scope disclaimer" if kind == "success" else None,
        },
        "use_permissions": [],
        "approvals": [],
        "key_standards": [],
        "setbacks": [],
        "warnings": [],
        "not_evaluated": [],
        "sources": [],
        "versions": {},
    }


class RenderedDocument(HTMLParser):
    """Collect structural links without adding a browser-test dependency."""

    def __init__(self, body: str) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.fragments: list[str] = []
        self.controls: list[str] = []
        self.labels_for: list[str] = []
        self.input_ids: list[str] = []
        self.tag_counts: dict[str, int] = {}
        self.result_kinds: list[str] = []
        self.rule_controls: dict[str, list[str]] = {}
        self.popover_fragments: dict[str, list[str]] = {}
        self._active_rules: list[tuple[str, str]] = []
        self._popover_id: str | None = None
        self._popover_depth = 0
        self.feed(body)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value for key, value in attrs}
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1

        element_id = values.get("id")
        if element_id:
            self.ids.append(element_id)
        href = values.get("href") or ""
        if href.startswith("#"):
            self.fragments.append(href[1:])
        control = values.get("aria-controls")
        if control:
            self.controls.append(control)
        if tag == "label" and values.get("for"):
            self.labels_for.append(str(values["for"]))
        if tag == "input" and element_id:
            self.input_ids.append(element_id)
        if values.get("data-result-kind"):
            self.result_kinds.append(str(values["data-result-kind"]))

        rule_id = values.get("data-rule-id")
        if rule_id:
            self._active_rules.append((tag, rule_id))
        classes = set((values.get("class") or "").split())
        if tag == "button" and "source-marker" in classes and control:
            if self._active_rules:
                active_rule = self._active_rules[-1][1]
                self.rule_controls.setdefault(active_rule, []).append(control)

        if self._popover_id is not None:
            self._popover_depth += 1
            if tag == "a" and href.startswith("#source-"):
                self.popover_fragments[self._popover_id].append(href[1:])
        elif element_id and element_id.startswith("source-popup-"):
            self._popover_id = element_id
            self._popover_depth = 1
            self.popover_fragments[element_id] = []

    def handle_endtag(self, tag: str) -> None:
        if self._popover_id is not None:
            self._popover_depth -= 1
            if self._popover_depth == 0:
                self._popover_id = None
        if self._active_rules and self._active_rules[-1][0] == tag:
            self._active_rules.pop()


def _rule_items(view: dict) -> list[dict]:
    return [
        item
        for section in ("use_permissions", "approvals", "key_standards", "setbacks")
        for item in view[section]
    ]


class WebShellTest(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = Mock()
        self.app = create_app(self.pipeline)
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def test_landing_page_does_not_run_the_pipeline(self) -> None:
        response = self.client.get("/")
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('name="address"', body)
        self.assertIn('href="/static/vendor/leaflet/leaflet.css"', body)
        self.assertIn('href="/static/app.css"', body)
        self.assertIn('src="/static/vendor/leaflet/leaflet.js"', body)
        self.assertIn('src="/static/app.js"', body)
        self.assertIn('class="lookup-panel"', body)
        self.assertIn("Search a Santa Clara address", body)
        self.assertIn('<label for="address">Santa Clara street address</label>', body)
        self.assertIn('role="combobox"', body)
        self.assertIn('aria-autocomplete="list"', body)
        self.assertIn('aria-controls="address-suggestion-list"', body)
        self.assertIn('aria-expanded="false"', body)
        self.assertIn('role="listbox"', body)
        self.assertIn('id="address-suggestion-status"', body)
        self.assertIn('aria-live="polite"', body)
        self.assertNotIn("Look up a property", body)
        self.assertNotIn("Enter one street address within the City of Santa Clara.", body)
        self.assertNotIn("data-result-kind", body)
        self.pipeline.analyze_address.assert_not_called()

    def test_stylesheet_is_served_as_a_local_static_asset(self) -> None:
        response = self.client.get("/static/app.css")
        self.addCleanup(response.close)
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/css")
        self.assertIn("--green: #17633e", body)
        self.assertIn("color: var(--text-muted);", body)
        self.assertIn("min-width: 1.5rem", body)
        self.assertIn("min-height: 1.5rem", body)
        self.assertIn('.address-suggestion-popup[data-state="loading"]', body)
        self.assertIn('.address-suggestion-popup[data-state="no-results"]', body)
        self.assertIn('.address-suggestion-popup[data-state="truncated"]', body)
        self.assertIn(".property-context-grid", body)
        self.assertIn("grid-template-columns: minmax(18rem, 2fr) minmax(0, 3fr);", body)
        self.assertIn(".property-map-frame", body)
        self.assertIn(".selected-parcel-outline", body)
        self.assertIn(".property-map-legend-panel", body)
        self.assertIn(".zoning-hover-tooltip", body)
        self.assertIn("width: min(15rem, calc(100vw - 5rem));", body)
        self.assertIn(".map-swatch--unshaded", body)
        self.assertIn("@media (prefers-reduced-motion: reduce)", body)
        self.assertIn("@media (forced-colors: active)", body)

    def test_local_enhancement_script_is_served_as_a_static_asset(self) -> None:
        response = self.client.get("/static/app.js")
        self.addCleanup(response.close)
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(response.mimetype, {"text/javascript", "application/javascript"})
        self.assertIn("data-source-popover", body)
        self.assertIn("data-address-search-form", body)
        self.assertIn("/api/address-suggestions?q=", body)
        self.assertIn("AbortController", body)
        self.assertIn("requestSubmit", body)
        self.assertIn("aria-activedescendant", body)
        self.assertIn("textContent", body)
        self.assertIn("window.setTimeout(() => fetchSuggestions(query), 150)", body)
        self.assertIn('event.key === "ArrowDown"', body)
        self.assertIn('event.key === "ArrowUp"', body)
        self.assertIn('event.key === "Home"', body)
        self.assertIn('event.key === "End"', body)
        self.assertIn('event.key === "Enter"', body)
        self.assertIn('event.key === "Tab"', body)
        self.assertIn("Continue typing a street or unit number", body)
        self.assertIn("data-property-map", body)
        self.assertIn("zoneDisplayColors", body)
        expected_zone_palette = (
            'HDF: "#444444"',
            '"PH-R5": "#c51b7d"',
            '"R1-6L": "#0067c5"',
            '"R1-8L": "#f28e00"',
            'R2: "#009e49"',
            'R3: "#7a3e9d"',
            'R4: "#d62728"',
            'R5: "#00a6d6"',
            'R6: "#e6c200"',
            'UC: "#8c510a"',
            'UV: "#008c95"',
            'VR: "#7a9a01"',
        )
        expected_zone_colors = tuple(
            palette_entry.rsplit('"', 2)[1]
            for palette_entry in expected_zone_palette
        )
        self.assertEqual(len(expected_zone_colors), 12)
        self.assertEqual(len(set(expected_zone_colors)), 12)
        for palette_entry in expected_zone_palette:
            with self.subTest(palette_entry=palette_entry):
                self.assertIn(palette_entry, body)
        self.assertIn("fillOpacity: selected ? 0.62 : 0.48", body)
        self.assertIn("map.fitBounds", body)
        self.assertIn("map.setMaxBounds", body)
        self.assertNotIn("other supported designation", body)
        self.assertNotIn("selected designation", body)
        self.assertIn("onEachFeature: bindZoningTooltip", body)
        self.assertIn("tooltip.textContent = `Zoning: ${zone}`", body)
        self.assertIn("layer.bindTooltip(tooltip", body)
        self.assertRegex(
            body,
            r'(?s)className: "selected-parcel-halo".*?weight: 10,',
        )
        self.assertRegex(
            body,
            r'(?s)className: "selected-parcel-outline".*?weight: 5,',
        )
        self.assertIn('event.key === "Enter" || event.key === " "', body)
        self.assertIn('event.key === "Escape" && mapLegend.open', body)
        self.assertIn("textContent", body)
        self.assertIn('trigger.addEventListener("mouseenter"', body)
        self.assertIn('trigger.addEventListener("focus"', body)
        self.assertIn('trigger.addEventListener("click"', body)
        self.assertIn('region.addEventListener("keydown"', body)
        self.assertIn('event.key === "Escape"', body)
        self.assertIn('document.addEventListener("click"', body)
        self.assertIn('if (disclosure) disclosure.open = true', body)
        self.assertIn('target.focus({ preventScroll: true })', body)

    def test_suggestions_are_unavailable_for_an_injected_legacy_pipeline(self) -> None:
        response = self.client.get(
            "/api/address-suggestions",
            query_string={"q": "1240 whi"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["status"], "unavailable")
        self.pipeline.analyze_address.assert_not_called()

    def test_property_maps_are_unavailable_for_an_injected_legacy_pipeline(self) -> None:
        response = self.client.get(
            "/api/property-map",
            query_string={"address": "636 Barto Street"},
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["status"], "unavailable")
        self.pipeline.analyze_address.assert_not_called()

    def test_leaflet_assets_and_license_are_served_locally(self) -> None:
        for path, evidence in (
            ("/static/vendor/leaflet/leaflet.js", "1.9.4"),
            ("/static/vendor/leaflet/leaflet.css", ".leaflet-container"),
            ("/static/vendor/leaflet/LICENSE", "BSD 2-Clause"),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.addCleanup(response.close)
                self.assertEqual(response.status_code, 200)
                self.assertIn(evidence, response.get_data(as_text=True))

    def test_address_runs_pipeline_and_presenter_once(self) -> None:
        pipeline_result = {"fixture": "pipeline result"}
        self.pipeline.analyze_address.return_value = pipeline_result

        with patch(
            "santa_clara_zoning.web.present_pipeline_result",
            return_value=_view(),
        ) as presenter:
            response = self.client.get("/", query_string={"address": "636 Barto St"})

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-result-kind="success"', response.get_data(as_text=True))
        self.assertIn('value="636 Barto St"', response.get_data(as_text=True))
        self.pipeline.analyze_address.assert_called_once_with("636 Barto St")
        presenter.assert_called_once_with(pipeline_result)

    def test_same_injected_pipeline_is_reused_across_requests(self) -> None:
        self.pipeline.analyze_address.return_value = {"fixture": True}

        with patch(
            "santa_clara_zoning.web.present_pipeline_result",
            return_value=_view(),
        ):
            self.client.get("/", query_string={"address": "First address"})
            self.client.get("/", query_string={"address": "Second address"})

        self.assertIs(
            self.app.extensions["r1_standards_pipeline"],
            self.pipeline,
        )
        self.assertEqual(self.pipeline.analyze_address.call_count, 2)

    def test_known_integrity_error_becomes_safe_system_view(self) -> None:
        self.pipeline.analyze_address.side_effect = PipelineIntegrityError(
            "fixture_integrity_error",
            "private diagnostic detail",
        )

        response = self.client.get("/", query_string={"address": "636 Barto St"})
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-result-kind="system_error"', body)
        self.assertIn('class="outcome-card outcome-card--system_error"', body)
        self.assertIn("System or data validation error", body)
        self.assertNotIn("private diagnostic detail", body)
        self.assertNotIn("data-capability-id", body)
        self.assertNotIn("data-rule-id", body)
        self.assertNotIn('class="source-marker"', body)
        self.assertNotIn("Regulatory sources", body)
        self.assertNotIn("<dt>Ruleset</dt>", body)

    def test_post_is_not_an_application_route(self) -> None:
        response = self.client.post("/", data={"address": "636 Barto St"})

        self.assertEqual(response.status_code, 405)
        self.pipeline.analyze_address.assert_not_called()

    def test_unexpected_error_is_not_relabelled(self) -> None:
        self.pipeline.analyze_address.side_effect = RuntimeError("programming defect")

        with self.assertRaisesRegex(RuntimeError, "programming defect"):
            self.client.get("/", query_string={"address": "636 Barto St"})

    def test_entered_address_is_html_escaped(self) -> None:
        self.pipeline.analyze_address.return_value = {"fixture": True}
        entered = '<script>alert("x")</script>'

        with patch(
            "santa_clara_zoning.web.present_pipeline_result",
            return_value=_view("lookup_failure"),
        ):
            response = self.client.get("/", query_string={"address": entered})

        body = response.get_data(as_text=True)
        self.assertNotIn(entered, body)
        self.assertIn("&lt;script&gt;", body)

    def test_review_required_view_contains_no_regulatory_sections(self) -> None:
        self.pipeline.analyze_address.return_value = {"fixture": True}

        with patch(
            "santa_clara_zoning.web.present_pipeline_result",
            return_value=_view("review_required"),
        ):
            response = self.client.get(
                "/",
                query_string={"address": "Review fixture"},
            )

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('data-result-kind="review_required"', body)
        self.assertIn("Edit the address and try again", body)
        self.assertNotIn("What base zoning permits", body)
        self.assertNotIn("Key base-zone standards", body)
        self.assertNotIn("data-capability-id", body)
        self.assertNotIn("data-rule-id", body)
        self.assertNotIn('class="source-marker"', body)
        self.assertNotIn("Regulatory sources", body)
        self.assertNotIn("<dt>Ruleset</dt>", body)


def _suggestion_result(query: str) -> dict:
    return {
        "status": "ok",
        "query": query,
        "normalized_query": "1240 WHI",
        "address_snapshot": "2026-07-16",
        "total_matches": 1,
        "truncated": False,
        "suggestions": [
            {
                "value": "1240 WHITE DR",
                "display_address": "1240 WHITE DR",
                "secondary_text": "Santa Clara, CA 95051",
                "source_record_count": 1,
                "longitude": -121.9,
                "zoning": "must not leak",
            }
        ],
        "regulations": {"must": "not leak"},
    }


class AddressSuggestionEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = Mock()
        self.suggester = Mock()
        self.app = create_app(
            self.pipeline,
            address_suggester=self.suggester,
        )
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def test_endpoint_returns_only_the_public_suggestion_shape(self) -> None:
        query = "1240 whi"
        self.suggester.suggest_addresses.return_value = _suggestion_result(query)

        response = self.client.get(
            "/api/address-suggestions",
            query_string={"q": query},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        payload = response.get_json()
        self.assertEqual(
            set(payload),
            {
                "status",
                "query",
                "normalized_query",
                "address_snapshot",
                "total_matches",
                "truncated",
                "suggestions",
            },
        )
        self.assertEqual(
            set(payload["suggestions"][0]),
            {
                "value",
                "display_address",
                "secondary_text",
                "source_record_count",
            },
        )
        self.assertEqual(payload["suggestions"][0]["value"], "1240 WHITE DR")
        self.assertEqual(payload["address_snapshot"], "2026-07-16")
        self.assertNotIn("longitude", payload["suggestions"][0])
        self.assertNotIn("zoning", payload["suggestions"][0])
        self.assertNotIn("regulations", payload)
        self.suggester.suggest_addresses.assert_called_once_with(query)

    def test_short_query_shape_is_preserved(self) -> None:
        for query in ("", "12"):
            with self.subTest(query=query):
                self.suggester.reset_mock()
                self.suggester.suggest_addresses.return_value = {
                    "status": "query_too_short",
                    "query": query,
                    "normalized_query": query,
                    "address_snapshot": "2026-07-16",
                    "total_matches": 0,
                    "truncated": False,
                    "suggestions": [],
                }

                response = self.client.get(
                    "/api/address-suggestions",
                    query_string={"q": query} if query else None,
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.get_json()["status"],
                    "query_too_short",
                )
                self.suggester.suggest_addresses.assert_called_once_with(query)

    def test_overlong_query_is_rejected_before_provider_use(self) -> None:
        response = self.client.get(
            "/api/address-suggestions",
            query_string={"q": "a" * 121},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["reason_code"], "query_too_long")
        self.suggester.suggest_addresses.assert_not_called()

    def test_malformed_or_oversized_provider_output_fails_closed(self) -> None:
        malformed_cases = [
            {"status": "ok"},
            {
                **_suggestion_result("1240 whi"),
                "suggestions": [
                    _suggestion_result("1240 whi")["suggestions"][0]
                    for _ in range(9)
                ],
                "total_matches": 9,
                "truncated": False,
            },
        ]
        for result in malformed_cases:
            with self.subTest(result=result):
                self.suggester.reset_mock()
                self.suggester.suggest_addresses.return_value = result
                response = self.client.get(
                    "/api/address-suggestions",
                    query_string={"q": "1240 whi"},
                )
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.get_json()["status"], "unavailable")


def _map_polygon(west: float, south: float, east: float, north: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[
            [west, south],
            [east, south],
            [east, north],
            [west, north],
            [west, south],
        ]],
    }


def _property_map_result(query: str) -> dict:
    return {
        "contract_version": "1.0.0",
        "status": "ok",
        "query": query,
        "property": {
            "display_address": "1 Test Street",
            "apn": "000-00-001",
            "zone": "R2",
            "source_object_id": 44,
        },
        "versions": {
            "address_snapshot": "2026-07-16",
            "residential_gis_snapshot": "2026-07-18",
            "ruleset": "must not leak",
        },
        "selected_bounds": {
            "west": -121.95,
            "south": 37.30,
            "east": -121.94,
            "north": 37.31,
        },
        "context_bounds": {
            "west": -121.96,
            "south": 37.29,
            "east": -121.92,
            "north": 37.33,
        },
        "selected_parcel": {
            "type": "Feature",
            "id": 44,
            "properties": {
                "apn": "000-00-001",
                "zone": "R2",
                "acreage": 1.0,
            },
            "geometry": _map_polygon(-121.95, 37.30, -121.94, 37.31),
        },
        "supported_zoning": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": 44,
                    "properties": {"zone": "R2", "OBJECTID": 44},
                    "geometry": _map_polygon(
                        -121.95,
                        37.30,
                        -121.94,
                        37.31,
                    ),
                },
                {
                    "type": "Feature",
                    "id": 45,
                    "properties": {"zone": "R3", "OBJECTID": 45},
                    "geometry": _map_polygon(
                        -121.94,
                        37.30,
                        -121.93,
                        37.31,
                    ),
                },
            ],
        },
        "zoning_feature_count": 2,
        "supported_zones": ["R1-6L", "R2", "R3"],
        "regulations": {"must": "not leak"},
    }


class PropertyMapEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = Mock()
        self.provider = Mock()
        self.app = create_app(
            self.pipeline,
            property_map_provider=self.provider,
        )
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

    def test_endpoint_returns_only_the_public_map_shape(self) -> None:
        query = "1 Test Street"
        self.provider.property_map_context.return_value = _property_map_result(query)

        response = self.client.get(
            "/api/property-map",
            query_string={"address": query},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(
            set(payload),
            {
                "contract_version",
                "status",
                "query",
                "property",
                "versions",
                "selected_bounds",
                "context_bounds",
                "selected_parcel",
                "supported_zoning",
                "zoning_feature_count",
                "supported_zones",
            },
        )
        self.assertEqual(set(payload["versions"]), {
            "address_snapshot",
            "residential_gis_snapshot",
        })
        self.assertEqual(
            set(payload["selected_parcel"]["properties"]),
            {"apn", "zone"},
        )
        self.assertNotIn("id", payload["selected_parcel"])
        for feature in payload["supported_zoning"]["features"]:
            self.assertEqual(set(feature["properties"]), {"zone"})
            self.assertNotIn("id", feature)
        serialized = str(payload).lower()
        for forbidden in (
            "objectid",
            "source_object_id",
            "acreage",
            "ruleset",
            "regulations",
        ):
            self.assertNotIn(forbidden, serialized)
        self.provider.property_map_context.assert_called_once_with(query)

    def test_invalid_queries_are_rejected_before_provider_use(self) -> None:
        cases = (None, "", "   ", "a" * 121)
        for address in cases:
            with self.subTest(address=address):
                self.provider.reset_mock()
                response = self.client.get(
                    "/api/property-map",
                    query_string=None if address is None else {"address": address},
                )
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["status"], "invalid_query")
                self.provider.property_map_context.assert_not_called()

    def test_controlled_lookup_outcomes_have_fixed_http_statuses(self) -> None:
        cases = {
            "address_not_found": 404,
            "outside_supported_residential_snapshot": 404,
            "address_ambiguous": 409,
            "review_required": 409,
            "map_context_unavailable": 503,
        }
        for status, expected_code in cases.items():
            with self.subTest(status=status):
                self.provider.property_map_context.return_value = {
                    "contract_version": "1.0.0",
                    "status": status,
                    "reason_code": f"fixture_{status}",
                    "message": "Controlled map outcome.",
                    "query": "1 Test Street",
                    "versions": {
                        "address_snapshot": "2026-07-16",
                        "residential_gis_snapshot": "2026-07-18",
                    },
                }
                response = self.client.get(
                    "/api/property-map",
                    query_string={"address": "1 Test Street"},
                )
                self.assertEqual(response.status_code, expected_code)
                payload = response.get_json()
                self.assertEqual(payload["status"], status)
                self.assertNotIn("selected_parcel", payload)
                self.assertNotIn("fixture_", str(payload))
                self.assertNotIn("Controlled map outcome", str(payload))

    def test_malformed_or_oversized_context_fails_closed(self) -> None:
        malformed = _property_map_result("1 Test Street")
        malformed["selected_parcel"]["geometry"]["coordinates"][0].pop()
        self.provider.property_map_context.return_value = malformed
        response = self.client.get(
            "/api/property-map",
            query_string={"address": "1 Test Street"},
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["status"], "unavailable")

        invalid_bounds = _property_map_result("1 Test Street")
        invalid_bounds["context_bounds"]["east"] = 181
        self.provider.property_map_context.return_value = invalid_bounds
        response = self.client.get(
            "/api/property-map",
            query_string={"address": "1 Test Street"},
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["status"], "unavailable")

        self.provider.property_map_context.return_value = _property_map_result(
            "1 Test Street"
        )
        with patch("santa_clara_zoning.web.MAX_PROPERTY_MAP_ZONING_FEATURES", 1):
            response = self.client.get(
                "/api/property-map",
                query_string={"address": "1 Test Street"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["status"], "unavailable")


class WebStartupFailureTest(unittest.TestCase):
    def test_ruleset_startup_failure_is_presented_after_search(self) -> None:
        failure = RulesetLoadError("fixture gate", ["private diagnostic detail"])
        with patch(
            "santa_clara_zoning.web.ResidentialZoneSummaryPipeline.from_defaults",
            side_effect=failure,
        ):
            app = create_app()
        app.config.update(TESTING=True)

        response = app.test_client().get(
            "/",
            query_string={"address": "636 Barto St"},
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-result-kind="system_error"', body)
        self.assertNotIn("private diagnostic detail", body)


@unittest.skipUnless(SNAPSHOTS_AVAILABLE, "canonical raw GIS snapshots are not present")
class WebShellIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pipeline = R1StandardsPipeline.from_defaults()
        cls.barto_view = present_pipeline_result(
            cls.pipeline.analyze_address("636 Barto Street")
        )
        cls.brookside_view = present_pipeline_result(
            cls.pipeline.analyze_address("108 Brookside Avenue")
        )
        cls.app = create_app(cls.pipeline)
        cls.app.config.update(TESTING=True)

    def test_default_app_runs_real_barto_pipeline_and_presenter(self) -> None:
        response = self.app.test_client().get(
            "/",
            query_string={"address": "636 Barto Street"},
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-result-kind="success"', body)
        self.assertIn("Property Overview", body)

    def test_barto_renders_semantic_success_sections_and_source_links(self) -> None:
        response = self.app.test_client().get(
            "/",
            query_string={"address": "636 Barto Street"},
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        expected_sections = (
            "Property Overview",
            "What base zoning permits",
            "Required approvals",
            "Key base-zone standards",
            "Setbacks",
            "Limitations",
            "Sources and data versions",
        )
        for heading in expected_sections:
            with self.subTest(heading=heading):
                self.assertIn(heading, body)
        self.assertIn('<table class="setbacks-table">', body)
        self.assertIn('class="table-scroll"', body)
        self.assertIn('tabindex="0"', body)
        self.assertIn('scope="col"', body)
        self.assertIn('scope="row"', body)
        self.assertIn("Total minimum beginning at story 2", body)
        self.assertIn('id="source-r1-standards-table"', body)
        self.assertNotIn("Source receipt", body)
        self.assertNotIn('href="#source-r1-standards-table"', body)
        self.assertIn("Not evaluated", body)

        setback_rows = re.findall(
            r'<tr data-capability-id="setback\.[^"]+".*?</tr>',
            body,
            flags=re.DOTALL,
        )
        self.assertEqual(len(setback_rows), 4)
        for row in setback_rows:
            with self.subTest(row=row[:80]):
                self.assertEqual(row.count('class="source-marker"'), 1)
                self.assertIn('aria-label="View ', row)
                self.assertIn('class="source-popover-list"', row)
        self.assertIn("Santa Clara Zoning Code, Title 18", setback_rows[0])
        self.assertIn("Section 18.10.030, Table 2-3", setback_rows[0])
        self.assertNotIn('class="metric-qualifier"', body)
        self.assertNotIn(">Base-zone maximum<", body)
        self.assertIn('class="rule-title approval-title"', body)
        self.assertIn('class="item-notes"', body)

        view = self.barto_view
        for value in view["property"].values():
            with self.subTest(property_value=value):
                self.assertIn(str(value), body)
        for standard in view["key_standards"]:
            rendered_value = f'{standard["value"]["number"]} {standard["value"]["unit"]}'
            with self.subTest(rule_id=standard["rule_id"]):
                self.assertIn(rendered_value, body)
        for item in view["not_evaluated"]:
            with self.subTest(topic=item["topic"]):
                self.assertIn(item["topic"], body)
        for version in view["versions"].values():
            with self.subTest(version=version):
                self.assertIn(version, body)

    def test_brookside_renders_paired_values_and_full_conflict_notice(self) -> None:
        response = self.app.test_client().get(
            "/",
            query_string={"address": "108 Brookside Avenue"},
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-pair-role="smaller_setback"', body)
        self.assertIn('data-pair-role="larger_setback"', body)
        self.assertIn('data-warning-kind="source_conflict"', body)
        self.assertIn("Selected ruleset value", body)
        self.assertIn("not an official City correction", body)
        self.assertIn("Review competing source values", body)
        self.assertIn("Official City or codifier clarification", body)
        self.assertNotIn("Left setback", body)
        self.assertNotIn("Right setback", body)

        conflict = next(
            warning
            for warning in self.brookside_view["warnings"]
            if warning["kind"] == "source_conflict"
        )
        self.assertIn(conflict["resolution"]["rationale"], body)
        for assertion in conflict["assertions"]:
            rendered_value = f'{assertion["value"]["number"]} {assertion["value"]["unit"]}'
            with self.subTest(assertion=assertion["assertion_id"]):
                self.assertIn(rendered_value, body)

    def test_success_html_has_complete_source_and_semantic_closure(self) -> None:
        fixtures = {
            "636 Barto Street": self.barto_view,
            "108 Brookside Avenue": self.brookside_view,
        }

        for address, view in fixtures.items():
            with self.subTest(address=address):
                response = self.app.test_client().get(
                    "/",
                    query_string={"address": address},
                )
                document = RenderedDocument(response.get_data(as_text=True))

                self.assertEqual(document.tag_counts.get("h1"), 1)
                self.assertEqual(document.tag_counts.get("main"), 1)
                self.assertIn("address", document.labels_for)
                self.assertIn("address", document.input_ids)
                self.assertEqual(document.result_kinds, ["success"])
                self.assertEqual(len(document.ids), len(set(document.ids)))
                self.assertLessEqual(set(document.fragments), set(document.ids))
                self.assertLessEqual(set(document.controls), set(document.ids))

                for item in _rule_items(view):
                    controls = document.rule_controls.get(item["rule_id"], [])
                    self.assertGreaterEqual(len(controls), 1, item["rule_id"])
                    expected_control = (
                        "source-popup-"
                        + item["rule_id"]
                        .replace(".", "-")
                        .replace(":", "-")
                        .replace("/", "-")
                    )
                    self.assertIn(expected_control, controls)
                    for citation_id in item["citation_ids"]:
                        self.assertIn(f"source-{citation_id}", document.ids)
                    self.assertEqual(
                        document.popover_fragments[expected_control],
                        [],
                    )

    def test_success_sections_render_in_the_approved_order(self) -> None:
        response = self.app.test_client().get(
            "/",
            query_string={"address": "636 Barto Street"},
        )
        body = response.get_data(as_text=True)
        ordered_ids = (
            "result-heading",
            "overview-heading",
            "permissions-heading",
            "approvals-heading",
            "standards-heading",
            "setbacks-heading",
            "limitations-heading",
            "sources-heading",
        )

        positions = [body.index(f'id="{element_id}"') for element_id in ordered_ids]
        self.assertEqual(positions, sorted(positions))

    def test_controlled_lookup_outcomes_render_no_regulatory_sections(self) -> None:
        fixtures = {
            "1500 Warburton Avenue": "Outside the supported R1 prototype",
            "324 Los Padres Boulevard": "Multiple address records matched",
            "not a real santa clara address": "Address not found",
            "": "Enter an address",
        }

        for address, headline in fixtures.items():
            with self.subTest(address=address):
                response = self.app.test_client().get(
                    "/",
                    query_string={"address": address},
                )
                body = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('data-result-kind="lookup_failure"', body)
                self.assertIn(headline, body)
                self.assertIn("Edit the address and try again", body)
                self.assertNotIn("What base zoning permits", body)
                self.assertNotIn("Key base-zone standards", body)
                self.assertNotIn("data-capability-id", body)
                self.assertNotIn("data-rule-id", body)
                self.assertNotIn('class="source-marker"', body)
                self.assertNotIn("Regulatory sources", body)
                self.assertNotIn("<dt>Ruleset</dt>", body)

    def test_ambiguous_address_lists_candidates_without_selecting_one(self) -> None:
        response = self.app.test_client().get(
            "/",
            query_string={"address": "324 Los Padres Boulevard"},
        )
        body = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Matching address records", body)
        self.assertIn("No candidate was selected automatically", body)
        self.assertIn("unit 1", body)

    def test_route_renders_presenter_values_without_hidden_web_constants(self) -> None:
        pipeline = Mock()
        pipeline_result = {"sentinel": "pipeline-result"}
        pipeline.analyze_address.return_value = pipeline_result
        view = copy.deepcopy(self.barto_view)
        view["property"]["display_address"] = "987 Sentinel Place"
        view["property"]["zone"] = "R1-SENTINEL"
        view["overview"]["summary"] = "Sentinel presentation summary"
        view["key_standards"][0]["value"] = {
            "number": 913.5,
            "unit": "widgets",
        }
        regulatory_source = next(
            source
            for source in view["sources"]
            if source["kind"] == "regulatory_citation"
        )
        regulatory_source["document"]["title"] = "<script>source</script>"
        app = create_app(pipeline)
        app.config.update(TESTING=True)

        with patch(
            "santa_clara_zoning.web.present_pipeline_result",
            return_value=view,
        ) as presenter:
            response = app.test_client().get(
                "/",
                query_string={"address": "<script>address</script>"},
            )

        body = response.get_data(as_text=True)
        self.assertIn("987 Sentinel Place", body)
        self.assertIn("R1-SENTINEL", body)
        self.assertIn("Sentinel presentation summary", body)
        self.assertIn("913.5 widgets", body)
        self.assertIn("&lt;script&gt;source&lt;/script&gt;", body)
        self.assertIn('value="&lt;script&gt;address&lt;/script&gt;"', body)
        self.assertNotIn("<script>source</script>", body)
        pipeline.analyze_address.assert_called_once_with("<script>address</script>")
        presenter.assert_called_once_with(pipeline_result)

    def test_rendered_success_is_repeatable_across_request_order(self) -> None:
        client = self.app.test_client()
        first = client.get(
            "/",
            query_string={"address": "636 Barto Street"},
        ).get_data()
        client.get("/", query_string={"address": "108 Brookside Avenue"})
        repeated = client.get(
            "/",
            query_string={"address": "636 Barto Street"},
        ).get_data()

        self.assertEqual(first, repeated)


if __name__ == "__main__":
    unittest.main()
