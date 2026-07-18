"""Focused tests for the Block 7 deterministic presentation boundary."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from santa_clara_zoning import (
    R1StandardsPipeline,
    CONTRACT_VERSION,
    PRESENTATION_CONTRACT_VERSION,
    PresentationIntegrityError,
    RulesetLoadError,
    present_integrity_error,
    present_pipeline_result,
    retrieve_zone_standards,
)
from santa_clara_zoning.lookup import DEFAULT_ADDRESS_SNAPSHOT, DEFAULT_R1_SNAPSHOT


REPO_ROOT = Path(__file__).resolve().parents[1]
RULESET_PATH = (
    REPO_ROOT / "rulesets/santa_clara/r1/2026-07-17.2/ruleset.json"
)
SNAPSHOTS_AVAILABLE = (
    (DEFAULT_ADDRESS_SNAPSHOT / "address_points.geojson").is_file()
    and (DEFAULT_R1_SNAPSHOT / "parcels_r1.geojson").is_file()
    and (DEFAULT_R1_SNAPSHOT / "current_zoning_r1.geojson").is_file()
)


class _FixtureRuleset:
    def __init__(self, data: dict) -> None:
        self._data = data

    def as_dict(self) -> dict:
        return copy.deepcopy(self._data)


def _load_ruleset() -> dict:
    with RULESET_PATH.open(encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise TypeError("Presentation fixture ruleset is not an object")
    return value


def _success_result(zone: str) -> dict:
    identity = {
        "R1-6L": ("636 BARTO ST", "293-16-045"),
        "R1-8L": ("108 BROOKSIDE AV", "303-22-022"),
    }
    display_address, apn = identity[zone]
    standards = retrieve_zone_standards(zone, _FixtureRuleset(_load_ruleset()))
    return {
        "contract_version": CONTRACT_VERSION,
        "status": "r1_standards_found",
        "reason_code": "approved_r1_standards_retrieved",
        "message": "Approved base-zone standards were retrieved.",
        "query": {
            "entered_address": display_address,
            "normalized_address": display_address,
        },
        "address": {"display_address": display_address},
        "parcel": {"apn": apn, "designation": zone},
        "zoning": {"designation": zone, "parcel_attribute_agrees": True},
        "regulatory_context": standards["regulatory_context"],
        "regulations": standards["regulations"],
        "shared_references": standards["shared_references"],
        "not_evaluated": standards["not_evaluated"],
        "disclaimer": standards["disclaimer"],
        "versions": {
            "address_snapshot": "2026-07-16",
            "r1_gis_snapshot": "2026-07-14",
            "ruleset": "2026-07-17.2",
        },
        "sources": {
            "address_layer": "https://example.test/address",
            "parcel_layer": "https://example.test/parcel",
            "zoning_layer": "https://example.test/zoning",
        },
    }


def _failure_result(status: str, reason_code: str, **extra: object) -> dict:
    return {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "reason_code": reason_code,
        "message": "Controlled fixture outcome.",
        "query": {
            "entered_address": "fixture",
            "normalized_address": "FIXTURE",
        },
        "versions": {
            "address_snapshot": "2026-07-16",
            "r1_gis_snapshot": "2026-07-14",
        },
        "sources": {
            "address_layer": "https://example.test/address",
            "parcel_layer": "https://example.test/parcel",
            "zoning_layer": "https://example.test/zoning",
        },
        **extra,
    }


def _canonical_bytes(value: dict) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


class PresentationSuccessTest(unittest.TestCase):
    def test_r1_6l_maps_every_supported_section_and_version(self) -> None:
        result = present_pipeline_result(_success_result("R1-6L"))

        self.assertEqual(
            result["presentation_contract_version"],
            PRESENTATION_CONTRACT_VERSION,
        )
        self.assertEqual(result["kind"], "success")
        self.assertEqual(result["property"]["apn"], "293-16-045")
        self.assertEqual(result["property"]["zone"], "R1-6L")
        self.assertEqual(len(result["use_permissions"]), 1)
        self.assertEqual(len(result["approvals"]), 2)
        self.assertEqual(len(result["key_standards"]), 3)
        self.assertEqual(len(result["setbacks"]), 4)
        self.assertEqual(
            result["use_permissions"][0]["status_label"],
            "Permitted by right under the supported base zoning",
        )
        self.assertIn("Zoning Clearance and Architectural Review", result["overview"]["summary"])

        standards = {
            item["capability_id"]: item for item in result["key_standards"]
        }
        self.assertEqual(
            standards["standard.maximum_primary_structure_height"]["value"],
            {"number": 25, "unit": "ft"},
        )
        setbacks = {item["capability_id"]: item for item in result["setbacks"]}
        self.assertEqual(setbacks["setback.front"]["base"]["value"]["number"], 20)
        self.assertEqual(
            setbacks["setback.front"]["adjustments"][0]["effect"]["value"][
                "number"
            ],
            25,
        )
        self.assertEqual(
            setbacks["setback.front"]["adjustments"][0]["label"],
            "Total minimum beginning at story 2",
        )
        self.assertTrue(
            any(
                warning["kind"] == "conditional_applicability"
                and warning["affected_capability_ids"] == ["setback.street_side"]
                for warning in result["warnings"]
            )
        )
        self.assertEqual(result["versions"]["pipeline_contract"], CONTRACT_VERSION)
        self.assertEqual(result["versions"]["ruleset"], "2026-07-17.2")
        self.assertEqual(
            [source["kind"] for source in result["sources"][:3]],
            ["gis_layer", "gis_layer", "gis_layer"],
        )
        self.assertTrue(
            all(item["status_code"] == "not_evaluated" for item in result["not_evaluated"])
        )

    def test_r1_8l_preserves_paired_yards_and_source_conflict(self) -> None:
        result = present_pipeline_result(_success_result("R1-8L"))
        setbacks = {item["capability_id"]: item for item in result["setbacks"]}
        interior = setbacks["setback.interior_side"]

        self.assertEqual(
            [member["number"] for member in interior["base"]["value"]["members"]],
            [6, 9],
        )
        self.assertEqual(
            [
                member["number"]
                for member in interior["adjustments"][0]["effect"]["value"][
                    "members"
                ]
            ],
            [11, 14],
        )
        conflict = next(
            warning
            for warning in result["warnings"]
            if warning["kind"] == "source_conflict"
        )
        self.assertEqual(
            conflict["resolution"]["selected_value"]["number"],
            15,
        )
        self.assertEqual(
            {assertion["value"]["number"] for assertion in conflict["assertions"]},
            {10, 15},
        )
        self.assertTrue(
            any(
                warning["kind"] == "proposal_dependent_assignment"
                for warning in result["warnings"]
            )
        )

    def test_output_is_repeatable_and_does_not_share_mutable_input(self) -> None:
        source = _success_result("R1-6L")
        original = copy.deepcopy(source)

        first = present_pipeline_result(source)
        self.assertEqual(source, original)
        first["setbacks"][0]["conditions"].append("changed")
        first["sources"][3]["document"]["title"] = "changed"

        second = present_pipeline_result(source)
        third = present_pipeline_result(source)
        self.assertNotIn("changed", second["setbacks"][0]["conditions"])
        self.assertNotEqual(second["sources"][3]["document"]["title"], "changed")
        self.assertEqual(_canonical_bytes(second), _canonical_bytes(third))


class PresentationOutcomeTest(unittest.TestCase):
    def test_controlled_lookup_and_review_outcomes_have_no_rules(self) -> None:
        outcomes = [
            _failure_result("address_not_found", "no_exact_address_match"),
            _failure_result(
                "address_ambiguous",
                "multiple_exact_address_matches",
                address_candidates=[{"display_address": "FIXTURE"}],
            ),
            _failure_result(
                "outside_supported_r1_snapshot",
                "no_r1_parcel_or_zoning_match",
                address={"display_address": "1500 WARBURTON AV"},
                spatial_match_counts={"r1_parcels": 0, "r1_zoning_features": 0},
            ),
            _failure_result(
                "review_required",
                "parcel_zoning_designation_mismatch",
                address={"display_address": "FIXTURE"},
                parcel={"apn": "fixture-apn", "designation": "R1-6L"},
                zoning={"designation": "R1-8L"},
            ),
        ]

        for source in outcomes:
            with self.subTest(status=source["status"]):
                result = present_pipeline_result(source)
                expected_kind = (
                    "review_required"
                    if source["status"] == "review_required"
                    else "lookup_failure"
                )
                self.assertEqual(result["kind"], expected_kind)
                self.assertEqual(result["use_permissions"], [])
                self.assertEqual(result["approvals"], [])
                self.assertEqual(result["key_standards"], [])
                self.assertEqual(result["setbacks"], [])
                self.assertNotIn("ruleset", result["versions"])

        ambiguous = present_pipeline_result(outcomes[1])
        self.assertEqual(ambiguous["candidates"]["addresses"][0]["display_address"], "FIXTURE")
        review = present_pipeline_result(outcomes[3])
        self.assertEqual(review["property"]["parcel_zone"], "R1-6L")
        self.assertEqual(review["property"]["zoning_zone"], "R1-8L")
        self.assertIn("parcel", review["evidence"])

    def test_failure_cannot_carry_regulations_or_ruleset_version(self) -> None:
        with self.assertRaises(PresentationIntegrityError) as attached:
            present_pipeline_result(
                _failure_result(
                    "address_not_found",
                    "no_exact_address_match",
                    regulations={},
                )
            )
        self.assertEqual(attached.exception.reason_code, "regulations_attached_to_failure")

        source = _failure_result("address_not_found", "no_exact_address_match")
        source["versions"]["ruleset"] = "2026-07-17.2"
        with self.assertRaises(PresentationIntegrityError) as versioned:
            present_pipeline_result(source)
        self.assertEqual(
            versioned.exception.reason_code,
            "ruleset_version_attached_to_failure",
        )

    def test_known_integrity_errors_have_safe_system_views(self) -> None:
        error = PresentationIntegrityError("unsupported_capability", "private detail")
        result = present_integrity_error(error)

        self.assertEqual(result["kind"], "system_error")
        self.assertEqual(result["source_reason_code"], "unsupported_capability")
        self.assertNotIn("private detail", result["overview"]["summary"])

        ruleset_result = present_integrity_error(
            RulesetLoadError("runtime eligibility", ["private artifact path"])
        )
        self.assertEqual(ruleset_result["source_reason_code"], "ruleset_load_error")
        with self.assertRaises(TypeError):
            present_integrity_error(ValueError("unexpected"))


class PresentationIntegrityTest(unittest.TestCase):
    def test_unknown_or_missing_capability_fails_closed(self) -> None:
        unknown = _success_result("R1-6L")
        unknown["regulations"]["local.example.custom_rule"] = copy.deepcopy(
            unknown["regulations"]["setback.rear"]
        )
        with self.assertRaises(PresentationIntegrityError) as unknown_error:
            present_pipeline_result(unknown)
        self.assertEqual(unknown_error.exception.reason_code, "unsupported_capability")

        missing = _success_result("R1-6L")
        del missing["regulations"]["setback.rear"]
        with self.assertRaises(PresentationIntegrityError) as missing_error:
            present_pipeline_result(missing)
        self.assertEqual(missing_error.exception.reason_code, "missing_capability")

    def test_unknown_requirement_and_adjustment_shapes_fail_closed(self) -> None:
        requirement = _success_result("R1-6L")
        requirement["regulations"]["standard.maximum_stories"]["requirement"][
            "kind"
        ] = "custom_quantity"
        with self.assertRaises(PresentationIntegrityError) as requirement_error:
            present_pipeline_result(requirement)
        self.assertEqual(
            requirement_error.exception.reason_code,
            "unsupported_requirement_kind",
        )

        adjustment = _success_result("R1-6L")
        adjustment["regulations"]["setback.front"]["requirement"]["adjustments"][
            0
        ]["trigger"]["kind"] = "height_above"
        with self.assertRaises(PresentationIntegrityError) as adjustment_error:
            present_pipeline_result(adjustment)
        self.assertEqual(
            adjustment_error.exception.reason_code,
            "unsupported_adjustment_trigger",
        )

    def test_missing_citation_and_unsupported_source_status_fail_closed(self) -> None:
        source = _success_result("R1-6L")
        del source["shared_references"]["citations"]["r1-standards-table"]
        with self.assertRaises(PresentationIntegrityError) as citation_error:
            present_pipeline_result(source)
        self.assertEqual(citation_error.exception.reason_code, "missing_reference")

        unsupported = _failure_result("r1_zone_found", "supported_r1_match")
        with self.assertRaises(PresentationIntegrityError) as status_error:
            present_pipeline_result(unsupported)
        self.assertEqual(status_error.exception.reason_code, "unsupported_source_status")


@unittest.skipUnless(SNAPSHOTS_AVAILABLE, "canonical raw GIS snapshots are not present")
class PresentationPipelineAcceptanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pipeline = R1StandardsPipeline.from_defaults()

    def test_real_r1_addresses_present_complete_results(self) -> None:
        fixtures = {
            "636 Barto Street": ("293-16-045", "R1-6L", False),
            "108 Brookside Avenue": ("303-22-022", "R1-8L", True),
        }
        for address, (apn, zone, has_conflict) in fixtures.items():
            with self.subTest(address=address):
                result = present_pipeline_result(
                    self.pipeline.analyze_address(address)
                )
                self.assertEqual(result["kind"], "success")
                self.assertEqual(result["property"]["apn"], apn)
                self.assertEqual(result["property"]["zone"], zone)
                self.assertEqual(
                    [len(result[key]) for key in (
                        "use_permissions",
                        "approvals",
                        "key_standards",
                        "setbacks",
                    )],
                    [1, 2, 3, 4],
                )
                self.assertEqual(
                    any(warning["kind"] == "source_conflict" for warning in result["warnings"]),
                    has_conflict,
                )

    def test_real_controlled_outcomes_never_gain_regulatory_cards(self) -> None:
        fixtures = {
            "1500 Warburton Avenue": "outside_supported_r1_snapshot",
            "324 Los Padres Boulevard": "address_ambiguous",
            "99999 No Such Street": "address_not_found",
            "": "address_not_found",
        }
        for address, status in fixtures.items():
            with self.subTest(address=address):
                result = present_pipeline_result(
                    self.pipeline.analyze_address(address)
                )
                self.assertEqual(result["source_status"], status)
                self.assertEqual(result["use_permissions"], [])
                self.assertEqual(result["approvals"], [])
                self.assertEqual(result["key_standards"], [])
                self.assertEqual(result["setbacks"], [])
                self.assertNotIn("ruleset", result["versions"])

    def test_cross_process_hash_seed_does_not_change_presentation(self) -> None:
        script = """
import hashlib
import json
from santa_clara_zoning import R1StandardsPipeline, present_pipeline_result

pipeline = R1StandardsPipeline.from_defaults()
payload = [
    present_pipeline_result(pipeline.analyze_address("636 Barto Street")),
    present_pipeline_result(pipeline.analyze_address("108 Brookside Avenue")),
    present_pipeline_result(pipeline.analyze_address("1500 Warburton Avenue")),
]
encoded = json.dumps(
    payload,
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
).encode("utf-8")
print(hashlib.sha256(encoded).hexdigest())
"""
        digests = []
        for seed in ("1", "987654"):
            environment = {**os.environ, "PYTHONHASHSEED": seed}
            completed = subprocess.run(
                [sys.executable, "-B", "-c", script],
                cwd=REPO_ROOT,
                env=environment,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            digests.append(completed.stdout.strip())
        self.assertEqual(digests[0], digests[1])


class PresentationContractAcceptanceTest(unittest.TestCase):
    def test_contract_shapes_are_stable_and_json_serializable(self) -> None:
        common_fields = {
            "presentation_contract_version",
            "kind",
            "source_status",
            "source_reason_code",
            "query",
            "property",
            "overview",
            "use_permissions",
            "approvals",
            "key_standards",
            "setbacks",
            "warnings",
            "not_evaluated",
            "sources",
            "versions",
        }
        success = present_pipeline_result(_success_result("R1-6L"))
        failure = present_pipeline_result(
            _failure_result("address_not_found", "no_exact_address_match")
        )
        system_error = present_integrity_error(
            PresentationIntegrityError("fixture_error", "private detail")
        )

        self.assertEqual(set(success), common_fields)
        self.assertEqual(set(failure), common_fields)
        self.assertEqual(set(system_error), common_fields - {"source_status"})
        for result in (success, failure, system_error):
            self.assertIsInstance(json.dumps(result, sort_keys=True), str)

    def test_display_order_and_wording_preserve_approved_semantics(self) -> None:
        result = present_pipeline_result(_success_result("R1-8L"))
        self.assertEqual(
            [item["capability_id"] for item in result["approvals"]],
            ["approval.zoning_clearance", "approval.architectural_review"],
        )
        self.assertEqual(
            [item["capability_id"] for item in result["key_standards"]],
            [
                "standard.maximum_primary_structure_height",
                "standard.maximum_stories",
                "standard.maximum_structure_coverage",
            ],
        )
        self.assertEqual(
            [item["capability_id"] for item in result["setbacks"]],
            [
                "setback.front",
                "setback.interior_side",
                "setback.street_side",
                "setback.rear",
            ],
        )
        self.assertEqual(
            result["use_permissions"][0]["status_label"],
            "Permitted by right under the supported base zoning",
        )
        self.assertTrue(
            all(item["qualifier"] == "Base-zone maximum" for item in result["key_standards"])
        )
        self.assertTrue(
            all(item["qualifier"] == "Base-zone minimum" for item in result["setbacks"])
        )
        self.assertEqual(
            result["setbacks"][0]["adjustments"][0]["label"],
            "Total minimum beginning at story 2",
        )
        rendered = json.dumps(result).lower()
        self.assertNotIn("floor-area ratio", rendered)
        self.assertNotIn("maximum floor area", rendered)
        self.assertNotIn("not allowed", rendered)
        self.assertTrue(
            all(item["status_label"] == "Not evaluated" for item in result["not_evaluated"])
        )
        self.assertIn("not a complete entitlement", result["overview"]["disclaimer"])

    def test_corner_rules_and_pairs_remain_explicitly_conditional(self) -> None:
        for zone in ("R1-6L", "R1-8L"):
            with self.subTest(zone=zone):
                result = present_pipeline_result(_success_result(zone))
                street_side = next(
                    item
                    for item in result["setbacks"]
                    if item["capability_id"] == "setback.street_side"
                )
                self.assertEqual(street_side["applicability"]["lot_context"], "corner")
                self.assertNotIn("corner_lot", result["property"])
                self.assertTrue(
                    any(
                        warning["kind"] == "conditional_applicability"
                        and warning["affected_capability_ids"] == ["setback.street_side"]
                        for warning in result["warnings"]
                    )
                )

        paired = present_pipeline_result(_success_result("R1-8L"))
        interior = next(
            item
            for item in paired["setbacks"]
            if item["capability_id"] == "setback.interior_side"
        )
        self.assertEqual(
            interior["base"]["value"]["physical_assignment"],
            "proposal_dependent",
        )
        self.assertNotIn("left", json.dumps(interior).lower())
        self.assertNotIn("right", json.dumps(interior).lower())

    def test_every_display_reference_resolves_to_a_source_receipt(self) -> None:
        result = present_pipeline_result(_success_result("R1-8L"))
        citation_receipts = {
            source["citation_id"]: source
            for source in result["sources"]
            if source["kind"] == "regulatory_citation"
        }
        items = (
            result["use_permissions"]
            + result["approvals"]
            + result["key_standards"]
            + result["setbacks"]
        )
        for item in items:
            self.assertTrue(item["citation_ids"])
            self.assertLessEqual(set(item["citation_ids"]), set(citation_receipts))
            for citation_id in item["citation_ids"]:
                receipt = citation_receipts[citation_id]
                self.assertTrue(receipt["locator"])
                self.assertTrue(receipt["document"]["title"])
                self.assertNotIn("official_url", receipt["document"])
                self.assertNotIn("url", receipt["document"])

        for warning in result["warnings"]:
            if "citation_ids" in warning:
                self.assertLessEqual(set(warning["citation_ids"]), set(citation_receipts))
        conflict = next(
            warning for warning in result["warnings"] if warning["kind"] == "source_conflict"
        )
        assertion_refs = {
            source_ref
            for assertion in conflict["assertions"]
            for source_ref in assertion["source_refs"]
        }
        self.assertLessEqual(assertion_refs, set(citation_receipts))
        self.assertEqual(conflict["resolution"]["selected_value"]["number"], 15)
        self.assertEqual(
            {assertion["value"]["number"] for assertion in conflict["assertions"]},
            {10, 15},
        )
        self.assertTrue(conflict["resolution"]["re_review_triggers"])

    def test_input_order_and_mutated_values_do_not_create_hidden_constants(self) -> None:
        source = _success_result("R1-6L")
        baseline = present_pipeline_result(source)
        source["regulations"] = dict(reversed(list(source["regulations"].items())))
        source["shared_references"]["citations"] = dict(
            reversed(list(source["shared_references"]["citations"].items()))
        )
        self.assertEqual(
            _canonical_bytes(present_pipeline_result(source)),
            _canonical_bytes(baseline),
        )

        source["parcel"]["designation"] = "TEST-R1"
        source["zoning"]["designation"] = "TEST-R1"
        source["regulations"]["standard.maximum_primary_structure_height"][
            "requirement"
        ]["value"]["number"] = 31
        source["regulations"]["standard.maximum_structure_coverage"][
            "requirement"
        ]["value"]["number"] = 47
        source["regulations"]["setback.front"]["requirement"]["base"]["value"][
            "number"
        ] = 22
        result = present_pipeline_result(source)
        standards = {
            item["capability_id"]: item for item in result["key_standards"]
        }
        setbacks = {item["capability_id"]: item for item in result["setbacks"]}
        self.assertEqual(result["property"]["zone"], "TEST-R1")
        self.assertEqual(
            standards["standard.maximum_primary_structure_height"]["value"]["number"],
            31,
        )
        self.assertEqual(
            standards["standard.maximum_structure_coverage"]["value"]["number"],
            47,
        )
        self.assertEqual(setbacks["setback.front"]["base"]["value"]["number"], 22)

    def test_display_critical_mutations_fail_closed(self) -> None:
        mutations = []

        missing_conflict = _success_result("R1-8L")
        missing_conflict["regulations"]["setback.street_side"]["conflict_id"] = None
        mutations.append((missing_conflict, "missing_conflict_reference"))

        bad_status = _success_result("R1-6L")
        bad_status["regulations"]["use.single_family_dwelling"]["requirement"][
            "code"
        ] = "prohibited"
        mutations.append((bad_status, "unsupported_status_code"))

        bad_pair = _success_result("R1-8L")
        bad_pair["regulations"]["setback.interior_side"]["requirement"]["base"][
            "value"
        ]["members"].pop()
        mutations.append((bad_pair, "invalid_paired_setback"))

        bad_effect = _success_result("R1-6L")
        bad_effect["regulations"]["setback.front"]["requirement"]["adjustments"][
            0
        ]["effect"]["kind"] = "add_to_base"
        mutations.append((bad_effect, "unsupported_adjustment_effect"))

        for source, reason_code in mutations:
            with self.subTest(reason_code=reason_code):
                with self.assertRaises(PresentationIntegrityError) as caught:
                    present_pipeline_result(source)
                self.assertEqual(caught.exception.reason_code, reason_code)


if __name__ == "__main__":
    unittest.main()
