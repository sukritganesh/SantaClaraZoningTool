"""Build one fail-closed common-zone result from exact residential profiles."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from .pipeline import PipelineIntegrityError
from .residential_pipeline import (
    RESIDENTIAL_CONTRACT_VERSION,
    ResidentialStandardsPipeline,
)
from .residential_standards import retrieve_residential_selection


RESIDENTIAL_SUMMARY_CONTRACT_VERSION = "1.0.0"


@dataclass(frozen=True)
class ResidentialZoneSummaryPipeline:
    """Project exact profiles into shared zone standards for presentation."""

    selection_pipeline: ResidentialStandardsPipeline

    def __post_init__(self) -> None:
        if not isinstance(self.selection_pipeline, ResidentialStandardsPipeline):
            raise TypeError(
                "selection_pipeline must be a ResidentialStandardsPipeline"
            )

    @classmethod
    def from_defaults(cls) -> "ResidentialZoneSummaryPipeline":
        """Load the approved selection pipeline once for zone summaries."""

        return cls(ResidentialStandardsPipeline.from_defaults())

    def analyze_address(self, entered_address: str) -> dict[str, Any]:
        """Return common standards only after every ordinary profile agrees."""

        base = self.selection_pipeline.analyze_address(entered_address)
        _validate_base_result(base)
        summary = _summary_envelope(base)
        if base["status"] != "residential_zone_found":
            return summary

        property_record = _object(base.get("property"), "property")
        zone = _text(property_record, "zone", "property")
        raw_selections = _array(base.get("available_selections"), "available_selections")
        choices = [
            _object(choice, "available_selections[]") for choice in raw_selections
        ]
        unknown_kinds = {
            choice.get("selection_kind")
            for choice in choices
            if choice.get("selection_kind") not in {"profile", "special_pathway"}
        }
        if unknown_kinds:
            _fail(
                "invalid_summary_selection_kind",
                "Zone summary received an unsupported selection kind.",
            )
        profile_choices = [
            choice for choice in choices if choice["selection_kind"] == "profile"
        ]
        pathway_choices = [
            choice
            for choice in choices
            if choice["selection_kind"] == "special_pathway"
        ]
        if not profile_choices:
            _fail(
                "missing_ordinary_profile",
                f"Zone {zone} has no ordinary profile for a common summary.",
            )

        profile_results = [
            _retrieve(zone, choice, self.selection_pipeline)
            for choice in profile_choices
        ]
        pathway_results = [
            _retrieve(zone, choice, self.selection_pipeline)
            for choice in pathway_choices
        ]
        summary.update(
            status="residential_zone_summary_found",
            reason_code="common_zone_standards_retrieved",
            residential_uses=_residential_uses(profile_choices, profile_results),
            special_pathways=_special_pathways(
                pathway_choices,
                pathway_results,
            ),
            regulations=_common_regulations(profile_choices, profile_results),
            not_evaluated_topics=_merged_topics(
                profile_choices,
                profile_results,
            ),
            conflicts=_merged_records(profile_results, "conflicts"),
            sources=_merged_sources([*profile_results, *pathway_results]),
        )
        return summary

    def suggest_addresses(self, query: str) -> dict[str, Any]:
        """Expose local suggestions through the default application boundary."""

        return self.selection_pipeline.suggest_addresses(query)

    def property_map_context(self, entered_address: str) -> dict[str, Any]:
        """Expose local map context through the default application boundary."""

        return self.selection_pipeline.property_map_context(entered_address)


def _validate_base_result(result: Any) -> None:
    source = _object(result, "result")
    if source.get("contract_version") != RESIDENTIAL_CONTRACT_VERSION:
        _fail(
            "unsupported_residential_contract",
            "Zone summary received an unsupported residential result contract.",
        )
    for field in (
        "status",
        "reason_code",
        "query",
        "versions",
        "available_selections",
        "not_evaluated_topics",
        "conflicts",
        "sources",
        "disclaimer",
    ):
        if field not in source:
            _fail(
                "incomplete_residential_result",
                f"Zone summary input omitted {field}.",
            )
    status = source["status"]
    supported = {
        "residential_zone_found",
        "outside_supported_residential_snapshot",
        "address_not_found",
        "address_ambiguous",
        "review_required",
    }
    if status not in supported:
        _fail(
            "unexpected_residential_status",
            f"Zone summary cannot consume status {status!r}.",
        )
    if status == "residential_zone_found":
        if (
            source.get("requested_selection_id") is not None
            or source.get("selection") is not None
            or source.get("use_permission") is not None
            or source.get("regulations") is not None
        ):
            _fail(
                "preselected_zone_summary",
                "Zone summary input must not contain a selected profile.",
            )
    elif (
        source.get("available_selections") != []
        or source.get("selection") is not None
        or source.get("use_permission") is not None
        or source.get("regulations") is not None
        or source.get("not_evaluated_topics") != {}
        or source.get("conflicts") != {}
    ):
        _fail(
            "regulatory_data_attached_to_lookup_failure",
            "A nonregulatory lookup outcome contains residential analysis data.",
        )


def _summary_envelope(base: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": RESIDENTIAL_SUMMARY_CONTRACT_VERSION,
        "source_result_contract": RESIDENTIAL_CONTRACT_VERSION,
        "status": base["status"],
        "reason_code": base["reason_code"],
        "query": copy.deepcopy(base["query"]),
        "versions": copy.deepcopy(base["versions"]),
        "property": copy.deepcopy(base["property"]),
        "residential_uses": [],
        "special_pathways": [],
        "regulations": None,
        "not_evaluated_topics": [],
        "conflicts": {},
        "sources": {
            "source_documents": {},
            "citations": {},
            "exception_families": {},
        },
        "disclaimer": base["disclaimer"],
    }


def _retrieve(
    zone: str,
    choice: dict[str, Any],
    pipeline: ResidentialStandardsPipeline,
) -> dict[str, Any]:
    selection_id = _text(choice, "selection_id", "available selection")
    result = retrieve_residential_selection(
        zone,
        selection_id,
        pipeline.ruleset,
    )
    expected_status = (
        "residential_standards_found"
        if choice["selection_kind"] == "profile"
        else "analysis_not_evaluated"
    )
    if (
        result.get("status") != expected_status
        or result.get("requested_selection_id") != selection_id
    ):
        _fail(
            "invalid_summary_selection",
            f"Zone {zone} selection {selection_id} returned an invalid branch.",
        )
    return result


def _residential_uses(
    choices: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    output = []
    for choice, result in zip(choices, results):
        permission = _object(result.get("use_permission"), "use_permission")
        output.append(
            {
                "selection_id": _text(choice, "selection_id", "profile choice"),
                "profile_label": _text(choice, "label", "profile choice"),
                "workflow_family": _text(
                    choice,
                    "workflow_family",
                    "profile choice",
                ),
                "legal_use_capability_id": _text(
                    choice,
                    "legal_use_capability_id",
                    "profile choice",
                ),
                "primary_structure_type": _text(
                    choice,
                    "primary_structure_type",
                    "profile choice",
                ),
                "use_permission": copy.deepcopy(permission),
            }
        )
    return output


def _special_pathways(
    choices: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    output = []
    for choice, result in zip(choices, results):
        topics = _object(result.get("not_evaluated_topics"), "pathway topics")
        output.append(
            {
                "selection_id": _text(choice, "selection_id", "pathway choice"),
                "label": _text(choice, "label", "pathway choice"),
                "workflow_family": _text(
                    choice,
                    "workflow_family",
                    "pathway choice",
                ),
                "legal_use_capability_id": _text(
                    choice,
                    "legal_use_capability_id",
                    "pathway choice",
                ),
                "analysis_status": "not_evaluated",
                "use_permission": copy.deepcopy(
                    _object(result.get("use_permission"), "pathway permission")
                ),
                "not_evaluated_topics": [
                    {"topic_id": topic_id, **copy.deepcopy(topic)}
                    for topic_id, topic in topics.items()
                ],
            }
        )
    return output


def _common_regulations(
    choices: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    first = _object(results[0].get("regulations"), "profile regulations")
    selection_ids = [choice["selection_id"] for choice in choices]
    expected_capabilities = set(first)
    for result in results[1:]:
        regulations = _object(result.get("regulations"), "profile regulations")
        if set(regulations) != expected_capabilities:
            _fail(
                "structure_specific_standards_require_selection",
                "Zone profiles expose different supported capabilities.",
            )

    output: dict[str, Any] = {}
    for capability, raw_rule in first.items():
        rule = _object(raw_rule, f"regulations.{capability}")
        semantic = _semantic_rule(rule)
        source_rule_ids = [_text(rule, "rule_id", capability)]
        for result in results[1:]:
            regulations = _object(result.get("regulations"), "profile regulations")
            compared = _object(regulations.get(capability), f"regulations.{capability}")
            if _semantic_rule(compared) != semantic:
                _fail(
                    "structure_specific_standards_require_selection",
                    f"Zone profiles differ for {capability}; common presentation is unsafe.",
                )
            source_rule_ids.append(_text(compared, "rule_id", capability))
        presented = copy.deepcopy(rule)
        presented["source_rule_ids"] = source_rule_ids
        presented["applies_to_selection_ids"] = selection_ids
        output[capability] = presented
    return output


def _semantic_rule(rule: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(rule)
    value.pop("rule_id", None)
    return value


def _merged_topics(
    choices: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    applicable: dict[str, list[str]] = {}
    for choice, result in zip(choices, results):
        topics = _object(result.get("not_evaluated_topics"), "profile topics")
        for topic_id, raw_topic in topics.items():
            topic = _object(raw_topic, f"topic {topic_id}")
            if topic_id in by_id and by_id[topic_id] != topic:
                _fail(
                    "inconsistent_topic_definition",
                    f"Profile topic {topic_id} has inconsistent definitions.",
                )
            by_id[topic_id] = copy.deepcopy(topic)
            applicable.setdefault(topic_id, []).append(choice["selection_id"])
    return [
        {
            "topic_id": topic_id,
            **topic,
            "applies_to_selection_ids": applicable[topic_id],
        }
        for topic_id, topic in by_id.items()
    ]


def _merged_records(
    results: list[dict[str, Any]],
    field: str,
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for result in results:
        records = _object(result.get(field), field)
        for record_id, record in records.items():
            if record_id in output and output[record_id] != record:
                _fail(
                    "inconsistent_summary_evidence",
                    f"Evidence record {record_id} differs between profiles.",
                )
            output[record_id] = copy.deepcopy(record)
    return output


def _merged_sources(results: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, dict[str, Any]] = {
        "source_documents": {},
        "citations": {},
        "exception_families": {},
    }
    for result in results:
        sources = _object(result.get("sources"), "sources")
        for collection in output:
            records = _object(sources.get(collection), f"sources.{collection}")
            for record_id, record in records.items():
                if record_id in output[collection] and (
                    output[collection][record_id] != record
                ):
                    _fail(
                        "inconsistent_summary_evidence",
                        f"Source record {record_id} differs between profiles.",
                    )
                output[collection][record_id] = copy.deepcopy(record)
    return output


def _object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("invalid_summary_input", f"Expected {path} to be an object.")
    return value


def _array(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        _fail("invalid_summary_input", f"Expected {path} to be an array.")
    return value


def _text(value: dict[str, Any], key: str, path: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        _fail("invalid_summary_input", f"Expected {path}.{key} to contain text.")
    return item


def _fail(reason_code: str, message: str) -> None:
    raise PipelineIntegrityError(reason_code, message)
