"""Schema-level tests for the residential ruleset v3 contract."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "rulesets/schema/ruleset-v3.schema.json"
RULESET_PATH = (
    ROOT / "rulesets/santa_clara/residential/2026-07-19.1/ruleset.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class RulesetV3SchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = load_json(SCHEMA_PATH)
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(
            cls.schema,
            format_checker=FormatChecker(),
        )
        cls.ruleset = load_json(RULESET_PATH)

    def changed(self) -> dict[str, Any]:
        return copy.deepcopy(self.ruleset)

    def messages(self, value: dict[str, Any]) -> list[str]:
        errors = sorted(
            self.validator.iter_errors(value),
            key=lambda error: [str(item) for item in error.path],
        )
        return [error.message for error in errors]

    def assert_valid(self, value: dict[str, Any]) -> None:
        self.assertEqual(self.messages(value), [])

    def test_canonical_migrated_candidate_is_schema_valid(self) -> None:
        self.assert_valid(self.ruleset)

    def test_schema_accepts_every_approved_nonnumeric_requirement_shape(self) -> None:
        base = self.changed()
        rule = base["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["standard.maximum_primary_structure_height"]
        variants = [
            {
                "kind": "no_maximum_listed",
                "reason_code": "controlling_base_table_has_no_maximum",
                "explanation": "The controlling base table lists no maximum.",
                "source_refs": ["r1-standards-table"],
            },
            {
                "kind": "faa_controlled",
                "controlling_authority": "FAA",
                "reason_code": "controlling_source_defers_to_faa",
                "explanation": "The controlling source states FAA.",
                "source_refs": ["r1-standards-table"],
            },
            {
                "kind": "plan_dependent",
                "reason_code": "controlling_source_requires_plan_or_project_review",
                "explanation": "The controlling plan requires project review.",
                "source_refs": ["r1-standards-table"],
                "required_sources_or_facts": ["Approved project plans"],
            },
            {
                "kind": "not_evaluated",
                "reason_code": "requires_unavailable_proposal_facts",
                "explanation": "Proposal facts are not available.",
                "source_refs": ["r1-standards-table"],
                "prerequisite_ids": ["proposal_specific_compliance"],
            },
            {
                "kind": "review_required",
                "reason_code": "project_specific_determination_required",
                "explanation": "A project-specific determination is required.",
                "source_refs": ["r1-standards-table"],
                "review_triggers": ["Project-specific plan review"],
            },
        ]
        for requirement in variants:
            with self.subTest(kind=requirement["kind"]):
                changed = copy.deepcopy(base)
                changed_rule = changed["zones"]["R1-6L"]["analysis_profiles"][
                    "single_family"
                ]["regulations"]["standard.maximum_primary_structure_height"]
                changed_rule["requirement"] = requirement
                self.assert_valid(changed)

    def test_schema_rejects_unknown_fields_and_permission_codes(self) -> None:
        changed = self.changed()
        changed["zones"]["R1-6L"]["prototype_hint"] = True
        self.assertTrue(self.messages(changed))

        changed = self.changed()
        changed["zones"]["R1-6L"]["use_permissions"][
            "use.multifamily_dwelling"
        ]["requirement"]["code"] = "prohibited"
        self.assertTrue(self.messages(changed))

    def test_schema_rejects_fake_nonnumeric_substitutes(self) -> None:
        changed = self.changed()
        rule = changed["zones"]["R1-6L"]["analysis_profiles"]["single_family"][
            "regulations"
        ]["standard.maximum_structure_coverage"]
        rule["requirement"] = {
            "kind": "no_maximum_listed",
            "reason_code": "controlling_base_table_has_no_maximum",
            "explanation": "No maximum is listed.",
            "source_refs": ["r1-standards-table"],
            "value": {"number": 0, "unit": "percent"},
        }
        self.assertTrue(self.messages(changed))

    def test_schema_requires_candidate_approval_date_to_remain_null(self) -> None:
        changed = self.changed()
        changed["approved_on"] = "2026-07-19"
        self.assertTrue(self.messages(changed))

    def test_schema_closes_profile_and_structure_vocabularies(self) -> None:
        changed = self.changed()
        profile = changed["zones"]["R1-6L"]["analysis_profiles"].pop(
            "single_family"
        )
        changed["zones"]["R1-6L"]["analysis_profiles"]["duplex"] = profile
        self.assertTrue(self.messages(changed))

        changed = self.changed()
        changed["scope"]["primary_structure_types"][1] = "duplex"
        self.assertTrue(self.messages(changed))


if __name__ == "__main__":
    unittest.main()
