"""Release-level acceptance tests for the expanded residential product."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch
from typing import Any

from santa_clara_zoning import (
    PipelineIntegrityError,
    RESIDENTIAL_CONTRACT_VERSION,
    RESIDENTIAL_PRESENTATION_CONTRACT_VERSION,
    RESIDENTIAL_SUMMARY_CONTRACT_VERSION,
    R1StandardsPipeline,
    ResidentialStandardsPipeline,
    ResidentialZoneSummaryPipeline,
    present_residential_summary,
)
from santa_clara_zoning.lookup import (
    DEFAULT_ADDRESS_SNAPSHOT,
    DEFAULT_RESIDENTIAL_SNAPSHOT,
)
from santa_clara_zoning.web import create_app


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INVENTORY = (
    REPO_ROOT / "tests/fixtures/residential_gis_fixture_inventory.json"
)
PATRICK_HENRY_PLAN = (
    REPO_ROOT
    / "data/raw/2026-07-18/patrick_henry_drive_specific_plan/PatrickHenryPlan.pdf"
)
CANONICAL_ARTIFACTS_AVAILABLE = (
    (DEFAULT_ADDRESS_SNAPSHOT / "address_points.geojson").is_file()
    and (DEFAULT_RESIDENTIAL_SNAPSHOT / "parcels_residential.geojson").is_file()
    and (
        DEFAULT_RESIDENTIAL_SNAPSHOT / "current_zoning_residential.geojson"
    ).is_file()
    and PATRICK_HENRY_PLAN.is_file()
)

EXPECTED_VERSIONS = {
    "address_snapshot": "2026-07-16",
    "residential_gis_snapshot": "2026-07-18",
    "ruleset": "2026-07-19.5",
    "ruleset_schema": "3.2.0",
    "result_contract": RESIDENTIAL_CONTRACT_VERSION,
}
EXPECTED_VIEW_VERSIONS = {
    "summary_contract": RESIDENTIAL_SUMMARY_CONTRACT_VERSION,
    "source_result_contract": RESIDENTIAL_CONTRACT_VERSION,
    "address_snapshot": "2026-07-16",
    "residential_gis_snapshot": "2026-07-18",
    "ruleset": "2026-07-19.5",
    "ruleset_schema": "3.2.0",
}
EXPECTED_PROFILES = {
    "R1-6L": ["single_family"],
    "R1-8L": ["single_family"],
    "R2": ["single_family", "two_family", "multifamily"],
    "R3": ["two_family", "multifamily"],
    "R4": ["two_family", "multifamily"],
    "R5": ["multifamily"],
    "R6": ["multifamily"],
    "PH-R5": ["multifamily"],
    "UV": ["multifamily"],
    "VR": ["multifamily"],
    "UC": ["multifamily"],
    "HDF": ["multifamily"],
}
EXPECTED_CAPABILITIES = {
    "approval.zoning_clearance",
    "approval.architectural_review",
    "standard.maximum_primary_structure_height",
    "standard.maximum_stories",
    "standard.maximum_structure_coverage",
    "standard.gross_residential_density",
    "setback.front",
    "setback.interior_side",
    "setback.street_side",
    "setback.rear",
}
RELEASED_R1_CAPABILITIES = {
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
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"Expected a JSON object at {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _semantic_rule(rule: dict[str, Any]) -> dict[str, Any]:
    """Project fields that must remain identical across the R1 migration."""

    return {
        key: rule[key]
        for key in (
            "label",
            "requirement",
            "conditions",
            "exception_family_ids",
            "conflict_id",
            "validation_status",
        )
    }


def _cross_process_digests(
    addresses: tuple[str, ...],
    *,
    hash_seed: str,
) -> dict[str, dict[str, str]]:
    script = r"""
import hashlib
import json
import os

from santa_clara_zoning import present_residential_summary
from santa_clara_zoning.web import create_app

app = create_app()
if app.extensions["startup_error"] is not None:
    raise RuntimeError("Default residential application startup failed")
pipeline = app.extensions["residential_summary_pipeline"]
client = app.test_client()
digests = {}
for address in json.loads(os.environ["RESIDENTIAL_ACCEPTANCE_ADDRESSES"]):
    result = pipeline.analyze_address(address)
    view = present_residential_summary(result)
    response = client.get("/", query_string={"address": address})
    if response.status_code != 200:
        raise RuntimeError(f"Unexpected response for {address}")
    canonical = lambda value: json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    digests[address] = {
        "structured": hashlib.sha256(canonical(result)).hexdigest(),
        "presented": hashlib.sha256(canonical(view)).hexdigest(),
        "rendered": hashlib.sha256(response.data).hexdigest(),
    }
print(json.dumps(digests, sort_keys=True, separators=(",", ":")))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=REPO_ROOT,
        env={
            **os.environ,
            "PYTHONHASHSEED": hash_seed,
            "RESIDENTIAL_ACCEPTANCE_ADDRESSES": json.dumps(addresses),
        },
        check=True,
        capture_output=True,
        text=True,
    )
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise AssertionError("Independent process did not return digest records")
    return value


class _StaticResidentialLookup:
    """Supply an exact synthetic zone or a controlled review outcome."""

    def __init__(self, zone: str | None) -> None:
        self.zone = zone

    def lookup(self, entered_address: str) -> dict[str, Any]:
        base = {
            "query": {
                "entered_address": entered_address,
                "normalized_address": entered_address.upper(),
            },
            "versions": {
                "address_snapshot": "2026-07-16",
                "residential_gis_snapshot": "2026-07-18",
            },
            "sources": {},
        }
        if self.zone is None:
            return {
                **base,
                "status": "review_required",
                "reason_code": "parcel_zoning_designation_mismatch",
            }
        return {
            **base,
            "status": "residential_zone_found",
            "reason_code": "supported_residential_match",
            "address": {"display_address": entered_address},
            "parcel": {"apn": "SYNTHETIC", "designation": self.zone},
            "zoning": {
                "designation": self.zone,
                "parcel_attribute_agrees": True,
            },
        }


def _synthetic_summary_pipeline(
    zone: str | None,
    ruleset: Any,
) -> ResidentialZoneSummaryPipeline:
    return ResidentialZoneSummaryPipeline(
        ResidentialStandardsPipeline(
            lookup_engine=_StaticResidentialLookup(zone),
            ruleset=ruleset,
        )
    )


@unittest.skipUnless(
    CANONICAL_ARTIFACTS_AVAILABLE,
    "source-complete residential runtime data are not present",
)
class ResidentialVerticalSliceAcceptanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inventory = _read_json(FIXTURE_INVENTORY)
        cls.pipeline = ResidentialZoneSummaryPipeline.from_defaults()
        cls.selection_pipeline = cls.pipeline.selection_pipeline
        cls.ruleset = cls.selection_pipeline.ruleset
        cls.app = create_app(cls.pipeline)
        cls.app.config.update(TESTING=True)
        if cls.app.extensions["startup_error"] is not None:
            raise AssertionError("Default residential application failed startup")
        cls.client = cls.app.test_client()

    def test_offline_default_application_closes_ten_live_zone_matrix(self) -> None:
        def reject_connection(*args: Any, **kwargs: Any) -> None:
            raise AssertionError("Residential runtime attempted an outbound connection")

        with (
            patch.object(socket, "create_connection", side_effect=reject_connection),
            patch.object(socket.socket, "connect", side_effect=reject_connection),
            patch.object(socket.socket, "connect_ex", side_effect=reject_connection),
        ):
            app = create_app()
            app.config.update(TESTING=True)
            self.assertIsNone(app.extensions["startup_error"])
            self.assertIsInstance(
                app.extensions["residential_summary_pipeline"],
                ResidentialZoneSummaryPipeline,
            )
            pipeline = app.extensions["residential_summary_pipeline"]
            client = app.test_client()

            fixtures = self.inventory["real_address_fixtures"]
            self.assertEqual(len(fixtures), 10)
            self.assertEqual(
                {fixture["designation"] for fixture in fixtures},
                set(EXPECTED_PROFILES) - {"R5", "R6"},
            )
            for fixture in fixtures:
                address = fixture["address"]["display_address"]
                zone = fixture["designation"]
                with self.subTest(zone=zone, address=address):
                    result = pipeline.analyze_address(address)
                    view = present_residential_summary(result)
                    response = client.get("/", query_string={"address": address})
                    body = response.get_data(as_text=True)

                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(
                        result["contract_version"],
                        RESIDENTIAL_SUMMARY_CONTRACT_VERSION,
                    )
                    self.assertEqual(
                        result["source_result_contract"],
                        RESIDENTIAL_CONTRACT_VERSION,
                    )
                    self.assertEqual(
                        result["status"],
                        "residential_zone_summary_found",
                    )
                    self.assertEqual(result["versions"], EXPECTED_VERSIONS)
                    self.assertEqual(result["property"]["zone"], zone)
                    self.assertEqual(
                        result["property"]["parcel_id"],
                        fixture["parcel"]["apn"],
                    )
                    self.assertEqual(
                        [
                            item["selection_id"]
                            for item in result["residential_uses"]
                        ],
                        EXPECTED_PROFILES[zone],
                    )
                    self.assertEqual(set(result["regulations"]), EXPECTED_CAPABILITIES)
                    self.assertEqual(
                        len(result["special_pathways"]),
                        1 if zone.startswith("R1-") else 0,
                    )

                    self.assertEqual(view["kind"], "success")
                    self.assertEqual(
                        view["presentation_contract_version"],
                        RESIDENTIAL_PRESENTATION_CONTRACT_VERSION,
                    )
                    self.assertEqual(view["versions"], EXPECTED_VIEW_VERSIONS)
                    self.assertEqual(
                        [
                            len(view[section])
                            for section in (
                                "approvals",
                                "key_standards",
                                "setbacks",
                            )
                        ],
                        [2, 4, 4],
                    )
                    citation_ids = set(result["sources"]["citations"])
                    self.assertEqual(
                        {
                            item["citation_id"]
                            for item in view["sources"]
                            if item["kind"] == "regulatory_citation"
                        },
                        citation_ids,
                    )

                    self.assertIn('data-result-kind="success"', body)
                    self.assertIn(
                        f'<span class="zone-badge">{zone}</span>',
                        body,
                    )
                    self.assertIn(fixture["parcel"]["apn"], body)
                    self.assertNotIn('name="selection_id"', body)
                    for capability in EXPECTED_CAPABILITIES:
                        self.assertIn(
                            f'data-capability-id="{capability}"',
                            body,
                        )
                    for citation_id in citation_ids:
                        self.assertIn(f'id="source-{citation_id}"', body)

    def test_zero_count_r5_r6_render_from_rules_without_invented_addresses(self) -> None:
        inventory = self.inventory
        self.assertEqual(
            {
                item["designation"]: (
                    item["parcel_source_count"],
                    item["current_zoning_source_count"],
                )
                for item in inventory["synthetic_zero_count_fixtures"]
            },
            {"R5": (0, 0), "R6": (0, 0)},
        )
        self.assertTrue(
            {"R5", "R6"}.isdisjoint(
                {
                    fixture["designation"]
                    for fixture in inventory["real_address_fixtures"]
                }
            )
        )

        expected_density = {"R5": (51, 100), "R6": (60, 350)}
        for zone, density_range in expected_density.items():
            with self.subTest(zone=zone):
                address = f"1 Synthetic {zone} Street"
                pipeline = _synthetic_summary_pipeline(zone, self.ruleset)
                result = pipeline.analyze_address(address)
                view = present_residential_summary(result)
                app = create_app(pipeline)
                app.config.update(TESTING=True)
                body = app.test_client().get(
                    "/",
                    query_string={"address": address},
                ).get_data(as_text=True)

                self.assertEqual(result["property"]["parcel_id"], "SYNTHETIC")
                self.assertEqual(
                    [item["selection_id"] for item in result["residential_uses"]],
                    ["multifamily"],
                )
                coverage = next(
                    item
                    for item in view["key_standards"]
                    if item["capability_id"]
                    == "standard.maximum_structure_coverage"
                )
                density = next(
                    item
                    for item in view["key_standards"]
                    if item["capability_id"]
                    == "standard.gross_residential_density"
                )
                self.assertEqual(coverage["requirement"]["kind"], "no_maximum_listed")
                self.assertEqual(
                    (
                        density["requirement"]["minimum"],
                        density["requirement"]["maximum"],
                    ),
                    density_range,
                )
                self.assertTrue(
                    any(
                        warning["kind"] == "source_conflict"
                        for warning in view["warnings"]
                    )
                )
                self.assertIn('data-result-kind="success"', body)
                self.assertIn(f"{density_range[0]}–{density_range[1]}", body)
                self.assertIn("No maximum listed", body)

    def test_released_r1_semantics_and_injected_web_path_are_preserved(self) -> None:
        released_pipeline = R1StandardsPipeline.from_defaults()
        released_app = create_app(released_pipeline)
        released_app.config.update(TESTING=True)
        released_client = released_app.test_client()

        for address, zone in (
            ("636 Barto Street", "R1-6L"),
            ("108 Brookside Avenue", "R1-8L"),
        ):
            with self.subTest(zone=zone):
                released = released_pipeline.analyze_address(address)
                expanded = self.pipeline.analyze_address(address)
                self.assertEqual(released["status"], "r1_standards_found")
                self.assertEqual(expanded["status"], "residential_zone_summary_found")
                self.assertEqual(set(released["regulations"]), RELEASED_R1_CAPABILITIES)

                expanded_use = expanded["residential_uses"][0]["use_permission"]
                self.assertEqual(
                    _semantic_rule(
                        released["regulations"]["use.single_family_dwelling"]
                    ),
                    _semantic_rule(expanded_use),
                )
                for capability in RELEASED_R1_CAPABILITIES - {
                    "use.single_family_dwelling"
                }:
                    self.assertEqual(
                        _semantic_rule(released["regulations"][capability]),
                        _semantic_rule(expanded["regulations"][capability]),
                    )

                response = released_client.get(
                    "/",
                    query_string={"address": address},
                )
                body = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('data-result-kind="success"', body)
                self.assertIn(zone, body)
                self.assertIn("2026-07-17.2", body)

                if zone == "R1-8L":
                    old_conflict = released["shared_references"]["conflicts"][
                        "conflict-r1-8l-corner-side-first"
                    ]
                    new_conflict = expanded["conflicts"][
                        "conflict-r1-8l-corner-side-first"
                    ]
                    self.assertEqual(
                        old_conflict["resolution"]["selected_value"],
                        new_conflict["resolution"]["selected_value"],
                    )

    def test_all_controlled_outcomes_remain_nonregulatory_except_success(self) -> None:
        selection_cases = (
            ("1240 White Drive", None, "residential_zone_found", False),
            ("1240 White Drive", "multifamily", "residential_standards_found", True),
            (
                "636 Barto Street",
                "r1_chapter_18_24_two_unit",
                "analysis_not_evaluated",
                False,
            ),
            ("1577 Pomeroy Avenue", "single_family", "selection_not_available", False),
            (
                "1500 Warburton Avenue",
                None,
                "outside_supported_residential_snapshot",
                False,
            ),
            ("99999 No Such Street", None, "address_not_found", False),
            ("324 Los Padres Boulevard", None, "address_ambiguous", False),
        )
        for address, selection_id, status, has_regulations in selection_cases:
            with self.subTest(status=status):
                result = self.selection_pipeline.analyze_address(
                    address,
                    selection_id,
                )
                self.assertEqual(result["status"], status)
                self.assertEqual(result["regulations"] is not None, has_regulations)

        review_pipeline = _synthetic_summary_pipeline(None, self.ruleset)
        review = review_pipeline.analyze_address("Review fixture")
        self.assertEqual(review["status"], "review_required")
        self.assertIsNone(review["regulations"])

        for address, kind in (
            ("1500 Warburton Avenue", "lookup_failure"),
            ("99999 No Such Street", "lookup_failure"),
            ("324 Los Padres Boulevard", "lookup_failure"),
            ("", "lookup_failure"),
        ):
            with self.subTest(address=address or "<empty>"):
                body = self.client.get(
                    "/",
                    query_string={"address": address},
                ).get_data(as_text=True)
                self.assertIn(f'data-result-kind="{kind}"', body)
                self.assertNotIn("data-capability-id", body)
                self.assertNotIn("Regulatory sources", body)

        review_app = create_app(review_pipeline)
        review_app.config.update(TESTING=True)
        review_body = review_app.test_client().get(
            "/",
            query_string={"address": "Review fixture"},
        ).get_data(as_text=True)
        self.assertIn('data-result-kind="review_required"', review_body)
        self.assertNotIn("data-capability-id", review_body)

        with patch.object(
            ResidentialZoneSummaryPipeline,
            "analyze_address",
            side_effect=PipelineIntegrityError(
                "acceptance_integrity_failure",
                "private acceptance detail",
            ),
        ):
            system_body = self.client.get(
                "/",
                query_string={"address": "1240 White Drive"},
            ).get_data(as_text=True)
        self.assertIn('data-result-kind="system_error"', system_body)
        self.assertNotIn("private acceptance detail", system_body)
        self.assertNotIn("data-capability-id", system_body)

    def test_versions_provenance_and_source_checksums_close(self) -> None:
        address_manifest = _read_json(DEFAULT_ADDRESS_SNAPSHOT / "manifest.json")
        residential_manifest = _read_json(
            DEFAULT_RESIDENTIAL_SNAPSHOT / "manifest.json"
        )
        lookup = self.selection_pipeline.lookup_engine
        ruleset = self.ruleset.as_dict()

        self.assertEqual(lookup.versions, {
            "address_snapshot": address_manifest["snapshot_date"],
            "residential_gis_snapshot": residential_manifest["snapshot_date"],
        })
        residential_layers = {
            layer["slug"]: layer for layer in residential_manifest["layers"]
        }
        self.assertEqual(
            lookup.sources,
            {
                "address_layer": address_manifest["layer"]["source_layer_url"],
                "parcel_layer": residential_layers["parcels"]["source_layer_url"],
                "zoning_layer": residential_layers["current_zoning"][
                    "source_layer_url"
                ],
            },
        )
        for root, record in (
            (DEFAULT_ADDRESS_SNAPSHOT, address_manifest["layer"]),
            (DEFAULT_RESIDENTIAL_SNAPSHOT, residential_layers["parcels"]),
            (
                DEFAULT_RESIDENTIAL_SNAPSHOT,
                residential_layers["current_zoning"],
            ),
        ):
            self.assertEqual(
                _sha256(root / record["output_file"]),
                record["output_sha256"],
            )

        self.assertEqual(ruleset["version"], EXPECTED_VERSIONS["ruleset"])
        self.assertEqual(ruleset["schema_version"], EXPECTED_VERSIONS["ruleset_schema"])
        self.assertEqual(ruleset["status"], "approved_for_runtime")
        self.assertTrue(ruleset["approved_on"])
        for document in ruleset["shared"]["source_documents"].values():
            self.assertEqual(
                _sha256(REPO_ROOT / document["local_path"]),
                document["sha256"],
            )

        for fixture in self.inventory["real_address_fixtures"]:
            address = fixture["address"]["display_address"]
            with self.subTest(zone=fixture["designation"]):
                result = self.pipeline.analyze_address(address)
                view = present_residential_summary(result)
                self.assertEqual(result["versions"], EXPECTED_VERSIONS)
                source_documents = result["sources"]["source_documents"]
                for citation in result["sources"]["citations"].values():
                    self.assertIn(citation["source_document_id"], source_documents)
                for document in source_documents.values():
                    self.assertEqual(
                        _sha256(REPO_ROOT / document["local_path"]),
                        document["sha256"],
                    )
                self.assertEqual(
                    {
                        item["citation_id"]
                        for item in view["sources"]
                        if item["kind"] == "regulatory_citation"
                    },
                    set(result["sources"]["citations"]),
                )

    def test_structured_presented_and_rendered_output_is_cross_process_stable(self) -> None:
        addresses = tuple(
            fixture["address"]["display_address"]
            for fixture in self.inventory["real_address_fixtures"]
        ) + (
            "1500 Warburton Avenue",
            "324 Los Padres Boulevard",
            "99999 No Such Street",
        )
        forward = _cross_process_digests(addresses, hash_seed="1")
        reverse = _cross_process_digests(
            tuple(reversed(addresses)),
            hash_seed="987654",
        )

        self.assertEqual(forward, reverse)
        self.assertEqual(set(forward), set(addresses))
        for digests in forward.values():
            self.assertEqual(set(digests), {"structured", "presented", "rendered"})
            self.assertTrue(all(len(value) == 64 for value in digests.values()))


if __name__ == "__main__":
    unittest.main()
