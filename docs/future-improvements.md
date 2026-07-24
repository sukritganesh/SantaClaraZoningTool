# Future Improvements Backlog

**Status:** Active backlog

**Last updated:** July 23, 2026

This document records worthwhile improvements that are not all part of the current implementation block. It prevents design observations from being lost while keeping active milestone status in `docs/progress.md`.

An item here does not expand the current active scope or authorize implementation. When an item becomes active, `docs/progress.md` owns its execution status and the relevant design, catalog, schema, or verification document owns its detailed contract.

The deferred regulation-family queue remains in `docs/regulations/supported-regulations.md`; it is linked rather than duplicated here.

## Status meanings

| Status | Meaning |
|---|---|
| Proposed | Worth retaining, but not scheduled for the current block |
| Promoted | Accepted into current or explicitly planned work; execution status lives in `docs/progress.md` |
| Complete | Implemented and validated, with evidence linked here |
| Dropped | Deliberately rejected or superseded, with the reason retained |

## Current burndown

### Validation and runtime safety

| ID | Improvement | Intended outcome | Horizon | Status |
|---|---|---|---|---|
| `VAL-001` | Enforce two-level runtime eligibility | A ruleset is runtime-eligible only when its top-level status is approved, `approved_on` is a valid date, validation passes, and the selected rule is individually approved. Candidate rulesets are never loaded operationally. | Pre-Block 6 redesign step 7 | Complete |
| `VAL-002` | Enforce conflict integrity and selected-value consistency | Every conflict reference resolves, identifies the affected rule, contains exactly one selected assertion, and matches the operational value. Unresolved conflicts return `review required` unless an approved project resolution explicitly permits a warned result. | Pre-Block 6 redesign step 7 | Complete |
| `VAL-003` | Add mutation-based domain regression tests | Deliberately broken approval, reference, identity, conflict, adjustment, and migration fixtures must be rejected by the v2 validator. | Pre-Block 6 redesign step 7 | Complete |

### Regulatory data expressiveness

| ID | Improvement | Intended outcome | Horizon | Status |
|---|---|---|---|---|
| `DATA-001` | Populate source-backed shared definitions | Encode materially relevant terms such as Grade, Structure, Structure Coverage, Story, Corner Lot, and lot-line classifications without duplicating them across zones. | Before proposal-level evaluation of affected rules | Proposed |
| `DATA-002` | Link rules explicitly to definitions and measurement methods | Replace implicit glossary relationships with validated references such as `definition_ids` or typed measurement-method references. | Ruleset schema later version | Proposed |
| `DATA-003` | Replace consequential prose conditions with typed logic | Incrementally encode conditions that affect applicability, numbers, triggers, or operations; retain prose only for explanation and unsupported behavior. | As each evaluator is implemented | Proposed |
| `DATA-004` | Structure `not evaluated` topics | Give deferred subjects stable identifiers, reasons, source references, and the facts or capabilities required before evaluation. | Residential expansion Block 2 | Promoted |
| `DATA-005` | Add rule lifecycle and supersession metadata | Represent effective periods, replaced provisions, amendment lineage, and re-review triggers without mutating prior approved rulesets. | Multi-version maintenance phase | Proposed |
| `DATA-006` | Add source-backed zone profiles | Store reviewed per-zone names, purposes, characteristic-use descriptions, and source references so richer overviews can be composed without interpreting zone codes or inventing narrative at runtime. | [Post-`v0.2.0` UX Block 10](progress.md#block-10-source-grounded-zone-overview-implementation) | Complete |

### Provenance and explanation

| ID | Improvement | Intended outcome | Horizon | Status |
|---|---|---|---|---|
| `PROV-001` | Enrich citations for inspectable UI receipts | Add official source URLs, useful page or section anchors, and concise supporting excerpts or evidence metadata while retaining local checksums and locators. | [Post-`v0.2.0` UX Block 9](progress.md#block-9-exact-regulatory-source-evidence-implementation) | Complete |
| `PROV-002` | Distinguish supporting, conflicting, and contextual sources | Prevent renderers from presenting a rejected assertion as support for the selected value; conflict dispositions and source roles must remain visible. | Domain validation and presentation iterations | Proposed |
| `PROV-003` | Provide audience-appropriate deterministic explanations | Generate staff-facing and public-facing summaries from the same evaluation trace without changing the underlying conclusion. | Presentation iteration | Proposed |

### Presentation and interaction

| ID | Improvement | Intended outcome | Horizon | Status |
|---|---|---|---|---|
| `UX-001` | Add conditional structure-specific selection | Reuse the existing exact profile-selection backend when supported standards or evaluation inputs genuinely differ by residential structure; keep the common zone summary as the default while the approved profiles remain semantically equivalent. | A later ruleset or proposal-input phase that introduces a material profile difference | Proposed |
| `UX-002` | Add local Santa Clara address autocomplete | Suggest canonical addresses from the validated citywide snapshot as the user types, support accessible keyboard and pointer selection, and submit the chosen address without adding a third-party geocoder or weakening exact final lookup. | [Post-`v0.2.0` UX Block 7](progress.md#block-7-local-address-autocomplete-implementation) | Complete |
| `UX-003` | Add supported parcel and zoning context maps | Show the exact selected parcel and nearby supported zoning from the validated local snapshot beside successful results, using a distinct 12-zone categorical palette and optional street tiles without changing the zoning conclusion. | [Post-`v0.2.0` UX Block 8](progress.md#block-8-supported-parcel-context-map-implementation) | Complete |
| `UX-004` | Add exact regulatory source evidence | Open each displayed citation at its exact checksummed PDF cell or paragraph, or its immutable native project verification record, without presenting candidate research as authority. | [Post-`v0.2.0` UX Block 9](progress.md#block-9-exact-regulatory-source-evidence-implementation) | Complete |

### Workflow automation and expansion

| ID | Improvement | Intended outcome | Horizon | Status |
|---|---|---|---|---|
| `AUTO-001` | Build an AI-assisted candidate extraction workflow | Extract candidate rules, definitions, exceptions, cross-references, and conflicts into validated schemas while preventing AI from approving its own output. | Later product workflow automation | Proposed |
| `AUTO-002` | Automate source-change and amendment impact detection | Compare new code editions and ordinances with approved snapshots, identify affected capabilities and zones, and require focused re-verification. | Later product maintenance workflow | Proposed |
| `AUTO-003` | Generalize onboarding for additional jurisdictions | Map exact semantic matches into a validated shared capability core while preserving unmatched local rules as typed, source-backed, namespaced extensions; do not carry Santa Clara values or silently discard local differences. | Multi-jurisdiction phase | Proposed |

For additional zoning capabilities—including ADUs, SB 9, density bonus, parking, overlays, averaging, encroachments, and nonconformities—use the authoritative deferred queue in `docs/regulations/supported-regulations.md`.

## Backlog maintenance

1. Add an item when a useful improvement is discovered but is not being implemented immediately.
2. Keep the item concise and avoid copying detailed design or regulatory values into this file.
3. When work is accepted, mark it `Promoted` and place the active task and exit evidence in `docs/progress.md`.
4. Update the owning design, schema, catalog, source-verification, or runbook document only when that artifact's contract changes.
5. Mark an item `Complete` only after its validation criteria pass, and link the resulting artifact or commit.
6. Retain dropped items with a short rationale so rejected approaches are not repeatedly reconsidered without new evidence.
