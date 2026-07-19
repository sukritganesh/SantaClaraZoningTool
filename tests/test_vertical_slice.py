"""Complete-path acceptance tests for the approved R1 prototype matrix."""

from __future__ import annotations

import copy
import unittest
from typing import Any

from santa_clara_zoning import (
    CONTRACT_VERSION,
    PRESENTATION_CONTRACT_VERSION,
    PipelineIntegrityError,
    R1StandardsPipeline,
    present_pipeline_result,
)
from santa_clara_zoning.lookup import DEFAULT_ADDRESS_SNAPSHOT, DEFAULT_R1_SNAPSHOT
from santa_clara_zoning.web import create_app


CANONICAL_ARTIFACTS_AVAILABLE = (
    (DEFAULT_ADDRESS_SNAPSHOT / "address_points.geojson").is_file()
    and (DEFAULT_R1_SNAPSHOT / "parcels_r1.geojson").is_file()
    and (DEFAULT_R1_SNAPSHOT / "current_zoning_r1.geojson").is_file()
)

EXPECTED_CAPABILITIES = (
    "use.single_family_dwelling",
    "approval.zoning_clearance",
    "approval.architectural_review",
    "standard.maximum_primary_structure_height",
    "standard.maximum_stories",
    "standard.maximum_structure_coverage",
    "setback.front",
    "setback.interior_side",
    "setback.street_side",
    "setback.rear",
)

EXPECTED_VERSIONS = {
    "address_snapshot": "2026-07-16",
    "r1_gis_snapshot": "2026-07-14",
    "ruleset": "2026-07-17.2",
}

EXPECTED_NOT_EVALUATED = {
    "Accessory structures",
    "ADUs and JADUs",
    "SB 9 and two-unit projects",
    "Density and state-law overrides",
    "Parcel-creation standards",
    "Driveway approach length",
    "Daylight plane",
    "Proposal-specific compliance",
    "Buildable-envelope geometry",
    "Historic, specific-plan, and other overlay review",
}


class _StaticLookup:
    """Return one controlled lookup result through the real downstream pipeline."""

    def __init__(self, result: dict[str, Any]) -> None:
        self._result = copy.deepcopy(result)

    def lookup(self, entered_address: str) -> dict[str, Any]:
        result = copy.deepcopy(self._result)
        result["query"]["entered_address"] = entered_address
        return result


class _FailingAnalyzer:
    def analyze_address(self, entered_address: str) -> dict[str, Any]:
        raise PipelineIntegrityError(
            "acceptance_integrity_failure",
            f"private fixture detail for {entered_address}",
        )


def _authoritative_projection(result: dict[str, Any]) -> dict[str, Any]:
    """Exclude only entered-address spelling from a successful result."""

    keys = (
        "status",
        "reason_code",
        "address",
        "parcel",
        "zoning",
        "regulatory_context",
        "regulations",
        "shared_references",
        "not_evaluated",
        "disclaimer",
        "sources",
        "versions",
        "contract_version",
    )
    return {key: copy.deepcopy(result[key]) for key in keys}


@unittest.skipUnless(
    CANONICAL_ARTIFACTS_AVAILABLE,
    "canonical raw GIS snapshots are not present",
)
class VerticalSliceAcceptanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = create_app()
        cls.app.config.update(TESTING=True)
        cls.pipeline = cls.app.extensions["r1_standards_pipeline"]
        if not isinstance(cls.pipeline, R1StandardsPipeline):
            raise AssertionError("Default application startup did not load the real pipeline")
        if cls.app.extensions["r1_startup_error"] is not None:
            raise AssertionError("Default application startup reported an integrity error")
        cls.client = cls.app.test_client()

    def test_supported_fixture_matrix_closes_every_production_layer(self) -> None:
        fixtures = {
            "636 Barto Street": {
                "apn": "293-16-045",
                "zone": "R1-6L",
                "citation_count": 12,
                "conflict_count": 0,
            },
            "108 Brookside Avenue": {
                "apn": "303-22-022",
                "zone": "R1-8L",
                "citation_count": 14,
                "conflict_count": 1,
            },
        }

        for address, expected in fixtures.items():
            with self.subTest(address=address):
                result = self.pipeline.analyze_address(address)
                view = present_pipeline_result(result)
                response = self.client.get("/", query_string={"address": address})
                body = response.get_data(as_text=True)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(result["status"], "r1_standards_found")
                self.assertEqual(result["contract_version"], CONTRACT_VERSION)
                self.assertEqual(result["parcel"]["apn"], expected["apn"])
                self.assertEqual(result["parcel"]["designation"], expected["zone"])
                self.assertEqual(result["zoning"]["designation"], expected["zone"])
                self.assertTrue(result["zoning"]["parcel_attribute_agrees"])
                self.assertEqual(tuple(result["regulations"]), EXPECTED_CAPABILITIES)
                self.assertEqual(result["versions"], EXPECTED_VERSIONS)
                self.assertEqual(
                    len(result["shared_references"]["citations"]),
                    expected["citation_count"],
                )
                self.assertEqual(
                    len(result["shared_references"]["conflicts"]),
                    expected["conflict_count"],
                )

                requirements = {
                    capability: rule["requirement"]
                    for capability, rule in result["regulations"].items()
                }
                self.assertEqual(
                    requirements["standard.maximum_primary_structure_height"]["value"],
                    {"number": 25, "unit": "ft"},
                )
                self.assertEqual(
                    requirements["standard.maximum_stories"]["value"],
                    {"number": 2, "unit": "stories"},
                )
                self.assertEqual(
                    requirements["standard.maximum_structure_coverage"]["value"],
                    {"number": 40, "unit": "percent"},
                )
                self.assertEqual(
                    result["regulations"]["setback.street_side"]["applicability"][
                        "lot_context"
                    ],
                    "corner",
                )

                self.assertEqual(view["kind"], "success")
                self.assertEqual(
                    view["presentation_contract_version"],
                    PRESENTATION_CONTRACT_VERSION,
                )
                self.assertEqual(view["property"]["apn"], expected["apn"])
                self.assertEqual(view["property"]["zone"], expected["zone"])
                self.assertEqual(
                    [
                        len(view[section])
                        for section in (
                            "use_permissions",
                            "approvals",
                            "key_standards",
                            "setbacks",
                        )
                    ],
                    [1, 2, 3, 4],
                )
                self.assertEqual(
                    {item["topic"] for item in view["not_evaluated"]},
                    EXPECTED_NOT_EVALUATED,
                )
                self.assertEqual(
                    view["versions"],
                    {
                        "pipeline_contract": CONTRACT_VERSION,
                        **EXPECTED_VERSIONS,
                    },
                )

                regulatory_source_ids = {
                    source["citation_id"]
                    for source in view["sources"]
                    if source["kind"] == "regulatory_citation"
                }
                for section in (
                    "use_permissions",
                    "approvals",
                    "key_standards",
                    "setbacks",
                ):
                    for item in view[section]:
                        self.assertLessEqual(
                            set(item["citation_ids"]),
                            regulatory_source_ids,
                        )

                self.assertIn('data-result-kind="success"', body)
                self.assertIn(expected["apn"], body)
                self.assertIn(expected["zone"], body)
                self.assertIn(EXPECTED_VERSIONS["ruleset"], body)
                self.assertIn("25 ft", body)
                self.assertIn("2 stories", body)
                self.assertIn("40 percent", body)
                for capability in EXPECTED_CAPABILITIES:
                    self.assertIn(f'data-capability-id="{capability}"', body)
                for citation_id in regulatory_source_ids:
                    self.assertIn(f'id="source-{citation_id}"', body)

                conflicts = [
                    warning
                    for warning in view["warnings"]
                    if warning["kind"] == "source_conflict"
                ]
                if expected["zone"] == "R1-8L":
                    self.assertEqual(len(conflicts), 1)
                    conflict = conflicts[0]
                    self.assertEqual(
                        conflict["resolution"]["selected_value"]["number"],
                        15,
                    )
                    self.assertEqual(
                        {item["value"]["number"] for item in conflict["assertions"]},
                        {10, 15},
                    )
                    interior = requirements["setback.interior_side"]
                    self.assertEqual(
                        [
                            member["number"]
                            for member in interior["base"]["value"]["members"]
                        ],
                        [6, 9],
                    )
                    self.assertEqual(
                        [
                            member["number"]
                            for member in interior["adjustments"][0]["effect"][
                                "value"
                            ]["members"]
                        ],
                        [11, 14],
                    )
                    self.assertIn("Prototype-selected value", body)
                    self.assertIn("pending official clarification", body)
                else:
                    self.assertEqual(conflicts, [])
                    self.assertEqual(
                        requirements["setback.street_side"]["base"]["value"][
                            "number"
                        ],
                        10,
                    )
                    self.assertEqual(
                        requirements["setback.street_side"]["adjustments"][0][
                            "effect"
                        ]["value"]["number"],
                        15,
                    )

    def test_controlled_fixture_matrix_remains_non_regulatory(self) -> None:
        fixtures = {
            "1500 Warburton Avenue": "outside_supported_r1_snapshot",
            "1577 Pomeroy Avenue, Unit 202": "outside_supported_r1_snapshot",
            "324 Los Padres Boulevard": "address_ambiguous",
            "99999 No Such Street": "address_not_found",
            "": "address_not_found",
        }

        for address, expected_status in fixtures.items():
            with self.subTest(address=address or "<empty>"):
                result = self.pipeline.analyze_address(address)
                view = present_pipeline_result(result)
                response = self.client.get("/", query_string={"address": address})
                body = response.get_data(as_text=True)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(result["status"], expected_status)
                self.assertNotIn("regulations", result)
                self.assertNotIn("ruleset", result["versions"])
                self.assertEqual(view["kind"], "lookup_failure")
                self.assertEqual(view["source_status"], expected_status)
                self.assertEqual(view["use_permissions"], [])
                self.assertEqual(view["approvals"], [])
                self.assertEqual(view["key_standards"], [])
                self.assertEqual(view["setbacks"], [])
                self.assertNotIn("ruleset", view["versions"])
                self.assertTrue(
                    all(source["kind"] == "gis_layer" for source in view["sources"])
                )
                self.assertIn('data-result-kind="lookup_failure"', body)
                self.assertNotIn("data-capability-id", body)
                self.assertNotIn('class="source-marker"', body)
                self.assertNotIn("Regulatory sources", body)
                self.assertNotIn("<dt>Ruleset</dt>", body)

                if "Pomeroy" in address:
                    self.assertEqual(result["address"]["unit"], "202")
                    self.assertEqual(result["address"]["source_object_id"], 193649338)
                elif "Los Padres" in address:
                    self.assertEqual(len(result["address_candidates"]), 2)
                elif not address:
                    self.assertEqual(result["reason_code"], "empty_or_invalid_address")

    def test_normalized_variants_preserve_the_authoritative_result(self) -> None:
        variants = (
            "636 Barto Street",
            "636 barto st santa clara ca",
            "636 Barto St., Santa Clara, CA 95050",
        )
        results = [self.pipeline.analyze_address(address) for address in variants]
        projections = [_authoritative_projection(result) for result in results]
        presented = [present_pipeline_result(result) for result in results]

        self.assertEqual(
            {result["query"]["normalized_address"] for result in results},
            {"636 BARTO ST"},
        )
        self.assertTrue(all(value == projections[0] for value in projections[1:]))
        for view in presented:
            self.assertEqual(view["property"]["display_address"], "636 Barto Street")
            self.assertEqual(view["property"]["apn"], "293-16-045")
            self.assertEqual(view["property"]["zone"], "R1-6L")

    def test_spatial_disagreement_stays_review_required_through_the_web(self) -> None:
        review_result = copy.deepcopy(
            self.pipeline.lookup_engine.lookup("636 Barto Street")
        )
        review_result.update(
            status="review_required",
            reason_code="parcel_zoning_designation_mismatch",
            message="Parcel and current-zoning designations disagree.",
        )
        review_result["zoning"]["designation"] = "R1-8L"
        review_result["zoning"]["parcel_attribute_agrees"] = False

        review_pipeline = R1StandardsPipeline(
            lookup_engine=_StaticLookup(review_result),
            ruleset=self.pipeline.ruleset,
        )
        result = review_pipeline.analyze_address("Review fixture")
        view = present_pipeline_result(result)
        app = create_app(review_pipeline)
        app.config.update(TESTING=True)
        body = app.test_client().get(
            "/",
            query_string={"address": "Review fixture"},
        ).get_data(as_text=True)

        self.assertEqual(result["status"], "review_required")
        self.assertNotIn("regulations", result)
        self.assertNotIn("ruleset", result["versions"])
        self.assertEqual(view["kind"], "review_required")
        self.assertIn('data-result-kind="review_required"', body)
        self.assertNotIn("data-capability-id", body)
        self.assertNotIn("Regulatory sources", body)
        self.assertNotIn("<dt>Ruleset</dt>", body)

    def test_integrity_failure_becomes_a_safe_non_regulatory_view(self) -> None:
        app = create_app(_FailingAnalyzer())
        app.config.update(TESTING=True)
        body = app.test_client().get(
            "/",
            query_string={"address": "636 Barto Street"},
        ).get_data(as_text=True)

        self.assertIn('data-result-kind="system_error"', body)
        self.assertIn("System or data validation error", body)
        self.assertNotIn("private fixture detail", body)
        self.assertNotIn("data-capability-id", body)
        self.assertNotIn("Regulatory sources", body)
        self.assertNotIn("<dt>Ruleset</dt>", body)


if __name__ == "__main__":
    unittest.main()
