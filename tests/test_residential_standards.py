"""Exact residential selection and provenance retrieval tests."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from santa_clara_zoning import (
    ApprovedResidentialRuleset,
    StandardsRetrievalError,
    UnsupportedSelectionError,
    UnsupportedZoneError,
    available_selections,
    retrieve_residential_selection,
)
from santa_clara_zoning.residential_standards import (
    PROFILE_SELECTION_ORDER,
    RESIDENTIAL_PROFILE_CAPABILITIES,
    _available_selections_data,
    _requirement_source_refs,
    _retrieve_residential_selection_data,
)
from scripts.validate_residential_result_contract_v2_1 import (
    build_fixture_result,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_CASES = (
    REPO_ROOT / "tests/fixtures/residential_result_contract_2_1_cases.json"
)
EXPECTED_SELECTION_IDS = {
    "R1-6L": ("single_family", "r1_chapter_18_24_two_unit"),
    "R1-8L": ("single_family", "r1_chapter_18_24_two_unit"),
    "R2": ("single_family", "two_family", "multifamily"),
    "R3": ("two_family", "multifamily"),
    "R4": ("two_family", "multifamily"),
    "R5": ("multifamily",),
    "R6": ("multifamily",),
    "PH-R5": ("multifamily",),
    "UV": ("multifamily",),
    "VR": ("multifamily",),
    "UC": ("multifamily",),
    "HDF": ("multifamily",),
}


def canonical_bytes(value: dict) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


class ResidentialSelectionRetrievalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ruleset = ApprovedResidentialRuleset.load()
        cls.data = cls.ruleset.as_dict()

    def test_available_selection_matrix_is_exact_and_ordered(self) -> None:
        self.assertEqual(
            tuple(self.ruleset.supported_zones),
            tuple(EXPECTED_SELECTION_IDS),
        )
        for zone, expected_ids in EXPECTED_SELECTION_IDS.items():
            with self.subTest(zone=zone):
                selections = available_selections(zone, self.ruleset)
                self.assertEqual(
                    tuple(item["selection_id"] for item in selections),
                    expected_ids,
                )
                profile_ids = [
                    item["selection_id"]
                    for item in selections
                    if item["selection_kind"] == "profile"
                ]
                self.assertEqual(
                    profile_ids,
                    [
                        profile
                        for profile in PROFILE_SELECTION_ORDER
                        if profile in expected_ids
                    ],
                )

    def test_every_authored_profile_and_pathway_retrieves_completely(self) -> None:
        profile_count = 0
        pathway_count = 0
        for zone, expected_ids in EXPECTED_SELECTION_IDS.items():
            for selection_id in expected_ids:
                with self.subTest(zone=zone, selection=selection_id):
                    result = retrieve_residential_selection(
                        zone,
                        selection_id,
                        self.ruleset,
                    )
                    self.assertEqual(result["zone"], zone)
                    self.assertEqual(
                        result["requested_selection_id"],
                        selection_id,
                    )
                    self.assertNotIn(
                        "approved_for_ruleset",
                        result["use_permission"],
                    )
                    self.assertEqual(
                        result["use_permission"]["requirement"]["code"],
                        "permitted_by_right",
                    )
                    self.assertTrue(result["sources"]["citations"])
                    if result["status"] == "residential_standards_found":
                        profile_count += 1
                        self.assertEqual(
                            frozenset(result["regulations"]),
                            RESIDENTIAL_PROFILE_CAPABILITIES,
                        )
                        self.assertEqual(len(result["regulations"]), 10)
                        self.assertTrue(
                            all(
                                "approved_for_ruleset" not in rule
                                for rule in result["regulations"].values()
                            )
                        )
                    else:
                        pathway_count += 1
                        self.assertEqual(
                            result["status"],
                            "analysis_not_evaluated",
                        )
                        self.assertIsNone(result["regulations"])
                        self.assertTrue(result["not_evaluated_topics"])
        self.assertEqual(profile_count, 16)
        self.assertEqual(pathway_count, 2)

    def test_known_absent_profiles_return_exact_not_listed_evidence(self) -> None:
        unavailable_count = 0
        for zone, record in self.data["zones"].items():
            for profile_id in PROFILE_SELECTION_ORDER:
                if profile_id in record["analysis_profiles"]:
                    continue
                capability = {
                    "single_family": "use.single_family_dwelling",
                    "two_family": "use.two_family_dwelling",
                    "multifamily": "use.multifamily_dwelling",
                }[profile_id]
                permission = record["use_permissions"][capability]
                if permission["requirement"]["code"] != "not_listed":
                    continue
                unavailable_count += 1
                with self.subTest(zone=zone, profile=profile_id):
                    result = retrieve_residential_selection(
                        zone,
                        profile_id,
                        self.ruleset,
                    )
                    self.assertEqual(result["status"], "selection_not_available")
                    self.assertIsNone(result["selection"])
                    self.assertIsNone(result["regulations"])
                    self.assertEqual(result["not_evaluated_topics"], {})
                    self.assertEqual(result["conflicts"], {})
                    self.assertEqual(
                        result["use_permission"]["requirement"]["code"],
                        "not_listed",
                    )
        self.assertEqual(unavailable_count, 18)

    def test_r1_two_family_profile_does_not_replace_its_pathway(self) -> None:
        for zone in ("R1-6L", "R1-8L"):
            with self.subTest(zone=zone):
                with self.assertRaises(UnsupportedSelectionError):
                    retrieve_residential_selection(
                        zone,
                        "two_family",
                        self.ruleset,
                    )

    def test_requirement_shapes_survive_selection_unchanged(self) -> None:
        cases = (
            ("R2", "multifamily", "standard.maximum_stories", "maximum_quantity"),
            (
                "R5",
                "multifamily",
                "standard.gross_residential_density",
                "quantity_range",
            ),
            (
                "R3",
                "multifamily",
                "standard.maximum_structure_coverage",
                "lot_area_tiered_maximum",
            ),
            (
                "R5",
                "multifamily",
                "standard.maximum_structure_coverage",
                "no_maximum_listed",
            ),
            (
                "UC",
                "multifamily",
                "standard.maximum_primary_structure_height",
                "faa_controlled",
            ),
            ("R2", "two_family", "setback.front", "setback"),
            ("R1-8L", "single_family", "setback.interior_side", "setback"),
            ("PH-R5", "multifamily", "setback.rear", "plan_dependent"),
        )
        for zone, profile, capability, kind in cases:
            with self.subTest(zone=zone, capability=capability):
                result = retrieve_residential_selection(
                    zone,
                    profile,
                    self.ruleset,
                )
                expected = self.data["zones"][zone]["analysis_profiles"][
                    profile
                ]["regulations"][capability]["requirement"]
                actual = result["regulations"][capability]["requirement"]
                self.assertEqual(actual, expected)
                self.assertEqual(actual["kind"], kind)

    def test_conflicts_and_transitive_sources_are_exactly_closed(self) -> None:
        expected_conflicts = {
            ("R1-8L", "single_family"): {
                "conflict-r1-8l-corner-side-first"
            },
            ("R5", "multifamily"): {
                "conflict-r5-gross-residential-density"
            },
            ("R6", "multifamily"): {
                "conflict-r6-gross-residential-density"
            },
            ("PH-R5", "multifamily"): {
                "conflict-ph-r5-gross-residential-density"
            },
        }
        for key, conflict_ids in expected_conflicts.items():
            with self.subTest(zone=key[0]):
                result = retrieve_residential_selection(
                    key[0],
                    key[1],
                    self.ruleset,
                )
                self.assertEqual(set(result["conflicts"]), conflict_ids)
                citations = result["sources"]["citations"]
                documents = result["sources"]["source_documents"]
                for citation in citations.values():
                    self.assertIn(citation["source_document_id"], documents)
                refs = set(
                    _requirement_source_refs(
                        result["use_permission"]["requirement"]
                    )
                )
                for rule in result["regulations"].values():
                    refs.update(_requirement_source_refs(rule["requirement"]))
                for topic in result["not_evaluated_topics"].values():
                    refs.update(topic["source_refs"])
                for conflict in result["conflicts"].values():
                    for assertion in conflict["assertions"]:
                        refs.update(assertion["source_refs"])
                self.assertTrue(refs.issubset(citations))

    def test_retrieval_matches_approved_contract_fixture_branches(self) -> None:
        fixture = json.loads(FIXTURE_CASES.read_text(encoding="utf-8"))
        selected_ids = {
            "selected-profile-standards-found",
            "selected-special-pathway-not-evaluated",
            "profile-selection-not-available",
        }
        fields = (
            "status",
            "reason_code",
            "available_selections",
            "requested_selection_id",
            "selection",
            "use_permission",
            "regulations",
            "not_evaluated_topics",
            "conflicts",
            "sources",
            "disclaimer",
        )
        for case in fixture["cases"]:
            if case["fixture_id"] not in selected_ids:
                continue
            expected = build_fixture_result(case, self.data)
            actual = retrieve_residential_selection(
                case["zone"],
                case["requested_selection_id"],
                self.ruleset,
            )
            with self.subTest(case=case["fixture_id"]):
                for field in fields:
                    self.assertEqual(actual[field], expected[field])

    def test_zone_and_selection_identifiers_must_match_exactly(self) -> None:
        for zone in ("r2", " R2 ", "R2-7L", "R7"):
            with self.subTest(zone=zone):
                with self.assertRaises(UnsupportedZoneError):
                    available_selections(zone, self.ruleset)
        for selection in ("MultiFamily", " multifamily ", "multi", ""):
            with self.subTest(selection=selection):
                with self.assertRaises(UnsupportedSelectionError):
                    retrieve_residential_selection(
                        "R2",
                        selection,
                        self.ruleset,
                    )
        with self.assertRaisesRegex(TypeError, "ApprovedResidentialRuleset"):
            available_selections("R2", object())  # type: ignore[arg-type]

    def test_mutated_branch_data_fails_closed_without_partial_results(self) -> None:
        mutations = []

        missing_capability = copy.deepcopy(self.data)
        del missing_capability["zones"]["R2"]["analysis_profiles"][
            "multifamily"
        ]["regulations"]["setback.rear"]
        mutations.append((missing_capability, "incomplete_profile"))

        unapproved = copy.deepcopy(self.data)
        unapproved["zones"]["R2"]["analysis_profiles"]["multifamily"][
            "regulations"
        ]["setback.rear"]["approved_for_ruleset"] = False
        mutations.append((unapproved, "unapproved_regulation"))

        missing_citation = copy.deepcopy(self.data)
        missing_citation["zones"]["R2"]["analysis_profiles"][
            "multifamily"
        ]["regulations"]["setback.rear"]["requirement"]["base"][
            "source_refs"
        ].append("missing-citation")
        mutations.append((missing_citation, "missing_reference"))

        missing_topic = copy.deepcopy(self.data)
        del missing_topic["not_evaluated_topics"][
            "citywide_proposal_specific_compliance"
        ]
        mutations.append((missing_topic, "missing_reference"))

        unknown_requirement = copy.deepcopy(self.data)
        unknown_requirement["zones"]["R2"]["analysis_profiles"][
            "multifamily"
        ]["regulations"]["setback.rear"]["requirement"] = {
            "kind": "unknown",
            "source_refs": ["citywide-residential-standards-table"],
        }
        mutations.append((unknown_requirement, "unsupported_requirement"))

        for changed, reason_code in mutations:
            with self.subTest(reason=reason_code):
                with self.assertRaises(StandardsRetrievalError) as caught:
                    _retrieve_residential_selection_data(
                        "R2",
                        "multifamily",
                        changed,
                    )
                self.assertEqual(caught.exception.reason_code, reason_code)

    def test_unapproved_pathway_and_duplicate_identity_fail_listing(self) -> None:
        unapproved = copy.deepcopy(self.data)
        unapproved["zones"]["R1-6L"]["special_pathways"][
            "r1_chapter_18_24_two_unit"
        ]["approved_for_ruleset"] = False
        with self.assertRaises(StandardsRetrievalError) as caught:
            _available_selections_data("R1-6L", unapproved)
        self.assertEqual(caught.exception.reason_code, "unapproved_pathway")

        collision = copy.deepcopy(self.data)
        collision["zones"]["R1-6L"]["special_pathways"][
            "single_family"
        ] = collision["zones"]["R1-6L"]["special_pathways"].pop(
            "r1_chapter_18_24_two_unit"
        )
        with self.assertRaises(StandardsRetrievalError) as caught:
            _available_selections_data("R1-6L", collision)
        self.assertEqual(
            caught.exception.reason_code,
            "duplicate_selection_identity",
        )

    def test_return_values_are_defensive_and_byte_deterministic(self) -> None:
        first = retrieve_residential_selection(
            "PH-R5",
            "multifamily",
            self.ruleset,
        )
        second = retrieve_residential_selection(
            "PH-R5",
            "multifamily",
            self.ruleset,
        )
        self.assertEqual(canonical_bytes(first), canonical_bytes(second))
        first["regulations"].clear()
        first["sources"]["citations"].clear()
        first["not_evaluated_topics"].clear()
        third = retrieve_residential_selection(
            "PH-R5",
            "multifamily",
            self.ruleset,
        )
        self.assertEqual(len(third["regulations"]), 10)
        self.assertTrue(third["sources"]["citations"])
        self.assertTrue(third["not_evaluated_topics"])


if __name__ == "__main__":
    unittest.main()
