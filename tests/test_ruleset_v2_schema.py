"""Schema-level tests for the approved zone-first ruleset v2 contract."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "rulesets" / "schema" / "ruleset-v2.schema.json"


def height_rule(zone_slug: str) -> dict[str, Any]:
    return {
        "rule_id": (
            f"us.ca.santa_clara.{zone_slug}."
            "standard.maximum_primary_structure_height"
        ),
        "label": "Maximum primary-structure height",
        "requirement": {
            "kind": "maximum_quantity",
            "value": {"number": 25, "unit": "ft"},
            "source_refs": ["r1-standards-table", "height-method"],
        },
        "applicability": {
            "structure_type": "single_family_primary_structure",
            "lot_context": "all",
        },
        "conditions": ["Base maximum; appurtenances are not evaluated."],
        "exception_family_ids": ["height-measurement-and-appurtenances"],
        "validation_status": "verified_with_conditions",
        "conflict_id": None,
        "approved_for_ruleset": True,
    }


def front_setback_rule() -> dict[str, Any]:
    return {
        "rule_id": "us.ca.santa_clara.r1-6l.setback.front",
        "label": "Front setback",
        "requirement": {
            "kind": "setback",
            "base": {
                "value": {"kind": "distance", "number": 20, "unit": "ft"},
                "source_refs": ["r1-standards-table"],
            },
            "adjustments": [
                {
                    "adjustment_id": "second-story-total",
                    "trigger": {"kind": "story_at_or_above", "story": 2},
                    "effect": {
                        "kind": "replace_total_minimum",
                        "value": {
                            "kind": "distance",
                            "number": 25,
                            "unit": "ft",
                        },
                    },
                    "source_refs": ["r1-standards-table"],
                }
            ],
        },
        "applicability": {
            "structure_type": "single_family_primary_structure",
            "lot_context": "all",
        },
        "conditions": ["Block-face averaging is not evaluated."],
        "exception_family_ids": ["front-setback-block-average"],
        "validation_status": "verified_with_conditions",
        "conflict_id": None,
        "approved_for_ruleset": True,
    }


def paired_side_setback_rule() -> dict[str, Any]:
    return {
        "rule_id": "us.ca.santa_clara.r1-8l.setback.interior_side",
        "label": "Interior-side setbacks",
        "requirement": {
            "kind": "setback",
            "base": {
                "value": {
                    "kind": "paired_distances",
                    "members": [
                        {"role": "smaller_setback", "number": 6, "unit": "ft"},
                        {"role": "larger_setback", "number": 9, "unit": "ft"},
                    ],
                    "relationship": "coordinated_pair",
                    "physical_assignment": "proposal_dependent",
                },
                "source_refs": ["r1-standards-table"],
            },
            "adjustments": [
                {
                    "adjustment_id": "second-story-total-pair",
                    "trigger": {"kind": "story_at_or_above", "story": 2},
                    "effect": {
                        "kind": "replace_total_minimum",
                        "value": {
                            "kind": "paired_distances",
                            "members": [
                                {
                                    "role": "smaller_setback",
                                    "number": 11,
                                    "unit": "ft",
                                },
                                {
                                    "role": "larger_setback",
                                    "number": 14,
                                    "unit": "ft",
                                },
                            ],
                            "relationship": "coordinated_pair",
                            "physical_assignment": "proposal_dependent",
                        },
                    },
                    "source_refs": ["r1-standards-table"],
                }
            ],
        },
        "applicability": {
            "structure_type": "single_family_primary_structure",
            "lot_context": "all",
        },
        "conditions": ["The paired yards must remain coordinated."],
        "exception_family_ids": ["narrow-pre-1955-parcel-side-setback"],
        "validation_status": "verified_with_conditions",
        "conflict_id": None,
        "approved_for_ruleset": True,
    }


def representative_ruleset() -> dict[str, Any]:
    return {
        "$schema": "../../../schema/ruleset-v2.schema.json",
        "schema_version": "2.0.0",
        "ruleset_id": "santa-clara-r1-base-zone-v2",
        "version": "2026-07-16.2",
        "jurisdiction": {
            "name": "City of Santa Clara",
            "slug": "santa_clara",
            "state": "CA",
            "country": "US",
        },
        "status": "approved_for_prototype",
        "approved_on": "2026-07-16",
        "verified_through": "2026-07-16",
        "scope": {
            "description": "Representative ruleset v2 schema fixture.",
            "structure_types": ["single_family_primary_structure"],
            "result_kind": "base_zone_standards_retrieval",
        },
        "shared": {
            "source_documents": {
                "sc-title18-2025-07": {
                    "title": "Santa Clara Zoning Code, Title 18",
                    "version": "July 2025",
                    "effective_date": None,
                    "local_path": "data/raw/example.pdf",
                    "sha256": "a" * 64,
                    "verification_status": "verified_baseline",
                }
            },
            "citations": {
                "r1-standards-table": {
                    "source_document_id": "sc-title18-2025-07",
                    "locator": "Section 18.10.030, Table 2-3",
                    "topic": "R1 base development standards",
                },
                "height-method": {
                    "source_document_id": "sc-title18-2025-07",
                    "locator": "Section 18.30.040",
                    "topic": "Height measurement",
                },
            },
            "definitions": {},
            "exception_families": {
                "height-measurement-and-appurtenances": {
                    "label": "Height measurement and appurtenances",
                    "treatment": "not_evaluated",
                    "source_refs": ["height-method"],
                },
                "front-setback-block-average": {
                    "label": "Front setback averaging",
                    "treatment": "not_evaluated",
                    "source_refs": ["r1-standards-table"],
                },
                "narrow-pre-1955-parcel-side-setback": {
                    "label": "Historical narrow-parcel exception",
                    "treatment": "not_evaluated",
                    "source_refs": ["r1-standards-table"],
                },
            },
        },
        "zones": {
            "R1-6L": {
                "regulations": {
                    "standard.maximum_primary_structure_height": height_rule(
                        "r1-6l"
                    ),
                    "setback.front": front_setback_rule(),
                }
            },
            "R1-8L": {
                "regulations": {
                    "standard.maximum_primary_structure_height": height_rule(
                        "r1-8l"
                    ),
                    "setback.interior_side": paired_side_setback_rule(),
                }
            },
        },
        "conflicts": {},
        "not_evaluated": ["Proposal-specific compliance"],
        "disclaimer": "Prototype output is not a legal or planning determination.",
    }


class RulesetV2SchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(
            cls.schema,
            format_checker=FormatChecker(),
        )

    def assert_valid(self, value: dict[str, Any]) -> None:
        errors = sorted(
            self.validator.iter_errors(value),
            key=lambda error: list(error.path),
        )
        self.assertEqual([error.message for error in errors], [])

    def assert_invalid(self, value: dict[str, Any]) -> None:
        self.assertTrue(list(self.validator.iter_errors(value)))

    def test_representative_zone_first_ruleset_is_valid(self) -> None:
        ruleset = representative_ruleset()
        self.assert_valid(ruleset)
        self.assertNotEqual(
            ruleset["zones"]["R1-6L"]["regulations"][
                "standard.maximum_primary_structure_height"
            ]["rule_id"],
            ruleset["zones"]["R1-8L"]["regulations"][
                "standard.maximum_primary_structure_height"
            ]["rule_id"],
        )

    def test_rejects_top_level_rule_array(self) -> None:
        changed = representative_ruleset()
        changed["rules"] = []
        self.assert_invalid(changed)

    def test_rejects_multi_zone_applicability(self) -> None:
        changed = representative_ruleset()
        rule = changed["zones"]["R1-6L"]["regulations"][
            "standard.maximum_primary_structure_height"
        ]
        rule["applicability"]["zones"] = ["R1-6L", "R1-8L"]
        self.assert_invalid(changed)

    def test_rejects_adjustment_without_effect_semantics(self) -> None:
        changed = representative_ruleset()
        adjustment = changed["zones"]["R1-6L"]["regulations"]["setback.front"][
            "requirement"
        ]["adjustments"][0]
        adjustment.pop("effect")
        self.assert_invalid(changed)

    def test_rejects_unordered_paired_roles(self) -> None:
        changed = representative_ruleset()
        members = changed["zones"]["R1-8L"]["regulations"][
            "setback.interior_side"
        ]["requirement"]["base"]["value"]["members"]
        members[0]["role"] = "larger_setback"
        self.assert_invalid(changed)

    def test_accepts_explicit_future_height_addition_shape(self) -> None:
        changed = representative_ruleset()
        adjustments = changed["zones"]["R1-6L"]["regulations"]["setback.front"][
            "requirement"
        ]["adjustments"]
        adjustments[0] = {
            "adjustment_id": "illustrative-height-stepback",
            "trigger": {
                "kind": "height_above",
                "height": {"number": 20, "unit": "ft"},
            },
            "effect": {
                "kind": "add_to_base",
                "value": {"kind": "distance", "number": 3, "unit": "ft"},
            },
            "source_refs": ["r1-standards-table"],
        }
        self.assert_valid(changed)

    def test_multiple_adjustments_require_explicit_precedence(self) -> None:
        changed = representative_ruleset()
        requirement = changed["zones"]["R1-6L"]["regulations"]["setback.front"][
            "requirement"
        ]
        requirement["adjustments"].append(
            {
                "adjustment_id": "third-story-total",
                "trigger": {"kind": "story_at_or_above", "story": 3},
                "effect": {
                    "kind": "replace_total_minimum",
                    "value": {"kind": "distance", "number": 30, "unit": "ft"},
                },
                "source_refs": ["r1-standards-table"],
            }
        )
        self.assert_invalid(changed)
        requirement["adjustment_resolution"] = {
            "kind": "highest_precedence_applicable",
            "ordered_adjustment_ids": [
                "third-story-total",
                "second-story-total",
            ],
        }
        self.assert_valid(changed)

    def test_candidate_ruleset_cannot_have_approval_date(self) -> None:
        changed = representative_ruleset()
        changed["status"] = "candidate"
        self.assert_invalid(changed)
        changed["approved_on"] = None
        self.assert_valid(changed)


if __name__ == "__main__":
    unittest.main()
