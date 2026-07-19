# Residential Ruleset Authoring Guide

**Contract:** Santa Clara residential ruleset schema `3.2.0`; accepted predecessors preserved under `3.0.0` and `3.1.0`

**Status:** Block 2 representation accepted; additive citywide and density authoring contracts implemented for Block 3

**Last updated:** July 19, 2026

## Purpose and boundary

This guide is the human- and AI-facing representation contract for the residential expansion lineage. It defines how verified residential use permissions, ordinary structure profiles, special pathways, approvals, selected dimensional standards, provenance, conflicts, and explicit nonnumeric dispositions are represented.

It does not contain Santa Clara's numeric values and does not authorize candidate data for runtime use. The capability meanings live in `supported-regulations.md`; zone-specific source conclusions live in `docs/residential-rule-verification.md` and checksum-pinned capability supplements such as `docs/residential-density-rule-verification.md`; active status and validation evidence live in `docs/progress.md`.

The released R1 ruleset remains governed by `ruleset-authoring-guide.md` and schema v2. The residential lineage consumes that artifact through deterministic, checksum-pinned successors; it does not edit or replace it. Candidate `2026-07-19.1` and schema `3.0.0` remain the accepted R1 migration checkpoint. Candidate `2026-07-19.2` and schema `3.1.0` remain the R1-R6 citywide checkpoint. Schema `3.2.0` adds the minimum closed range and conflict-assertion shapes needed for gross residential density.

## Non-negotiable semantics

- Legal-use permission, workflow family, and primary-structure identity are separate concepts.
- A zone owns all of its permission records, ordinary profiles, and special pathways.
- An ordinary profile is selected by one exact profile ID; rules are not assembled dynamically from nearby profiles.
- A special pathway is not an ordinary profile and is not a use-permission status.
- `not_listed` records only that a use is not listed in the controlling source table. It is never equivalent to `prohibited`.
- A missing numeric maximum is represented as `no_maximum_listed`, never as zero, infinity, or “unlimited.”
- FAA-controlled and plan-dependent standards remain nonnumeric unless an authoritative source supplies a universally applicable number.
- Applicable but deferred standards are explicit `not_evaluated` topics, not omitted regulations and not negative legal conclusions.
- Candidate validation is not runtime approval. Partial candidates are allowed only to prove contracts and migrations.
- The same versioned source data and deterministic migration or retrieval code must produce the same result.

## Top-level hierarchy

A v3 ruleset has this conceptual shape:

```text
ruleset
├── identity, jurisdiction, version, status, and verification cutoff
├── scope and predecessor rulesets
├── shared source documents, citations, definitions, and exception families
├── zones
│   └── <exact GIS designation>
│       ├── use_permissions
│       ├── analysis_profiles
│       └── special_pathways
├── conflicts
├── not_evaluated_topics
└── disclaimer
```

Closed JSON objects reject unknown fields. Identifiers are map keys wherever practical so lookup is deterministic and duplicate identities are impossible.

## Ruleset identity and lifecycle

The residential lineage uses:

- schema version `3.0.0` for the accepted R1 migration checkpoint, additive `3.1.0` for the R1-R6 citywide checkpoint, and additive `3.2.0` for the gross-density successor;
- ruleset ID `santa-clara-residential-zoning`;
- calendar-and-revision versions in the form `YYYY-MM-DD.N`;
- status `candidate` while any representation, source, completeness, approval, or migration gate remains open; and
- status `approved_for_runtime` only after every runtime gate succeeds.

`approved_on` must be null for a candidate and an ISO date for a runtime-approved ruleset. `verified_through` is the later-legislation audit cutoff, not the download date or authoring date.

Every migrated or expanded candidate lists its direct predecessor ruleset identity, version, checksum, and crosswalk path. A candidate must never claim the predecessor's approval status merely because its source values were previously approved or accepted.

## Scope vocabulary

The closed workflow-family vocabulary is:

- `single_family`
- `multifamily`

The closed legal-use capability vocabulary is:

- `use.single_family_dwelling`
- `use.two_family_dwelling`
- `use.multifamily_dwelling`

The closed primary-structure vocabulary is:

- `single_family_primary_structure`
- `two_family_primary_structure`
- `multifamily_primary_structure`

An ordinary single-family profile binds the `single_family` workflow to the single-family use and structure. Ordinary two-family and multifamily profiles both bind the `multifamily` workflow, but retain their separate use and structure identities.

## Zone identity

Zone keys are exact GIS designations. They are case-sensitive and must not be normalized into a nearby code. Human-readable labels may differ, but routing uses the exact key.

Contract validation permits a nonempty subset of the expansion's exact target-zone set for migration and fixture candidates. Runtime eligibility requires the complete exact target-zone set defined by the active plan and domain validator. Unexpected, aliased, excluded, or merely similar designations fail closed.

## Use-permission records

Every included zone contains exactly one record for each of the three legal-use capabilities. Each record contains:

- a stable rule ID;
- a display label;
- a typed `status` requirement;
- conditions;
- exception-family references;
- validation status;
- an optional conflict reference;
- an optional special-pathway reference; and
- an `approved_for_ruleset` flag.

The source-table status codes are closed to:

- `permitted_by_right`
- `not_listed`

No other permission conclusion may be inferred from a blank or unlisted table cell. Approvals such as Zoning Clearance and Architectural Review are profile-owned regulations and remain separate from legal-use permission.

Use-permission rule IDs follow:

```text
us.ca.santa_clara.<zone-slug>.<use-capability-id>
```

The R1 two-family permission may reference the Chapter 18.24 special pathway. That reference does not make its dimensional standards an ordinary R1 profile.

## Ordinary analysis profiles

An ordinary profile contains:

- `workflow_family`;
- `legal_use_capability_id`;
- `primary_structure_type`;
- a complete regulation map for the selected phase; and
- explicit `not_evaluated_topic_ids`.

Profile IDs are closed to `single_family`, `two_family`, and `multifamily`. The profile ID and all three binding fields must agree with the scope vocabulary above.

For the current phase, every ordinary profile contains exactly these evaluated or retrievable capability identities:

- `approval.zoning_clearance`
- `approval.architectural_review`
- `standard.maximum_primary_structure_height`
- `standard.maximum_stories`
- `standard.maximum_structure_coverage`
- `standard.gross_residential_density`
- `setback.front`
- `setback.rear`
- `setback.interior_side`
- `setback.street_side`

The requirement attached to a capability may be numeric or an approved nonnumeric disposition. The regulation family does not change merely because a source supplies no universal numeric value.

Profile-owned rule IDs follow:

```text
us.ca.santa_clara.<zone-slug>.<profile-id>.<capability-id>
```

Each profile rule keeps its own label, conditions, exception-family references, validation status, conflict reference, and approval flag. Lot context remains rule-owned; structure applicability is derived from the exact enclosing profile and must not be contradicted in a rule.

## Special pathways

A special pathway records a source-verified legal path whose dimensional analysis cannot be represented by one ordinary profile without additional facts or branch logic. It contains:

- a label;
- workflow family;
- legal-use capability ID;
- configuration scope;
- a typed `not_evaluated` analysis requirement;
- topic references;
- source references;
- validation status; and
- approval flag.

The R1 Chapter 18.24 path uses configuration scope `attached_or_detached_homes`. Its workflow family is `multifamily` and its legal-use capability is `use.two_family_dwelling`, but it does not claim that every permitted configuration is one `two_family_primary_structure`.

A pathway may be listed while dimensional analysis remains unavailable. Retrieval must return an explicit `analysis_not_evaluated` result rather than silently using the zone's ordinary single-family profile.

## Requirement kinds

### Status

`status` represents a closed code with source references. Use permissions use only `permitted_by_right` or `not_listed`; approval regulations use only `required` or `may_be_required`.

### Maximum quantity

`maximum_quantity` stores a finite numeric value and a closed unit such as feet, stories, or percent. It is used only when a controlling source states a universal base maximum for that zone/profile/capability.

### Lot-area-tiered maximum

`lot_area_tiered_maximum` is an additive schema `3.1.0` requirement shape within `standard.maximum_structure_coverage`; it is not a new regulation family. It contains:

- one positive `threshold` in square feet;
- a `below_threshold` outcome; and
- an `at_or_above_threshold` outcome.

Each outcome is independently either `maximum_quantity` in percent or `no_maximum_listed`, with its own source references. The two tiers must never be flattened into one percentage, and a no-maximum-listed tier must never be converted to infinity or “unlimited.” The Santa Clara domain validator pins the current approved source-table split to 10,000 square feet while the shared JSON shape remains typed rather than jurisdiction-named.

### Quantity range

`quantity_range` stores one sourced minimum and maximum using the same closed unit. Schema `3.2.0` uses it for `standard.gross_residential_density` with unit `dwelling_units_per_acre`. The minimum must be positive and must not exceed the maximum.

This shape retrieves a source range only. It must not encode or imply parcel acreage, an allowed unit count, rounding, density-bonus eligibility, plan reconciliation, or proposal compliance.

### Setback

`setback` preserves the v2 typed model: a sourced base scalar or paired distance plus zero or more sourced story- or height-triggered adjustments. Paired side yards remain coordinated requirements and must not be averaged.

### No maximum listed

`no_maximum_listed` means the controlling base table does not state a maximum for that capability. It requires:

- `reason_code: controlling_base_table_has_no_maximum`;
- a concise explanation; and
- exact source references.

It does not assert that no other law, plan, overlay, condition, or review authority can constrain the proposal.

### FAA controlled

`faa_controlled` means the controlling source delegates the base result to FAA control instead of stating a universal local numeric maximum. It requires:

- `controlling_authority: FAA`;
- `reason_code: controlling_source_defers_to_faa`;
- a concise explanation; and
- exact source references.

The product must not fabricate a local height or story number.

### Plan dependent

`plan_dependent` means the source supplies no universal number and requires project-, plan-, or approval-specific facts. It requires:

- a controlled reason code;
- a concise explanation;
- exact source references; and
- a nonempty list of required sources or facts.

The Patrick Henry rear-setback case must not use zero as a placeholder.

### Not evaluated

`not_evaluated` means the subject may apply, but the current product does not implement the facts or logic needed to decide it. It requires a reason code, explanation, exact source references, and a list of prerequisite topic or fact IDs. It is not a prohibition and not an assertion that the subject is irrelevant.

### Review required

`review_required` means the product has reached a source- or fact-dependent boundary requiring human review. It requires a reason code, explanation, exact source references, and a nonempty list of review triggers.

It is distinct from an unresolved source conflict, which remains recorded in the top-level conflict map and also prevents runtime approval where applicable.

## Structured not-evaluated topics

`not_evaluated_topics` is a map of stable topic IDs to records containing:

- label;
- controlled reason code;
- plain-language explanation;
- exact source or predecessor-scope references; and
- prerequisite IDs.

Profiles and pathways reference topic IDs; they do not copy prose. This supports consistent retrieval and presentation while keeping deferred regulation families outside the evaluated rule map.

For migrated v2 scope statements, provenance may point to the checksum-pinned predecessor ruleset through a dedicated citation. That records what the predecessor declared without falsely presenting project scope prose as a legal citation.

## Shared provenance

The shared maps preserve the v2 provenance model:

- `source_documents` identify official documents, audits, and checksum-pinned migration inputs;
- `citations` identify exact table, section, page, or predecessor locations;
- `definitions` preserve consequential defined terms; and
- `exception_families` disclose known rule families that are not fully evaluated.

Every source reference must resolve to a shared citation. Every citation must resolve to a source document. Local source files record SHA-256 checksums. External-only sources record stable URLs and verification dates.

A source reference is provenance, not a substitute for a typed requirement or a validation disposition.

## Conflicts

Conflicting source assertions remain separate from the selected rule value. Each conflict records:

- every assertion and its source references;
- which assertion the project selected, if any;
- the affected rule IDs;
- rationale, decision source, decision date, and resolution status;
- the selected value, if deterministically resolved; and
- re-review triggers.

Schema `3.2.0` permits a typed `quantity_range` assertion value so competing minimum/maximum density ranges can be retained without prose or scalar flattening. A project resolution selects one assertion only when the decision source is explicit. The selected rule uses `project_resolved_with_conditions`, matches the selected range exactly, and remains distinguishable from an official correction.

Migration may change affected rule IDs to their profile-owned v3 identities, but it must preserve all assertion values, sources, and resolution meaning. A project resolution is not an official government correction.

## Candidate and runtime gates

A schema-valid candidate must:

- use only exact target-zone keys;
- contain all three use-permission records for every included zone;
- contain exactly the ordinary profiles and special pathways allowed for each included zone;
- contain all required capability IDs in every ordinary profile;
- use closed requirement kinds and reason codes;
- resolve every reference;
- preserve every conflict; and
- keep every rule and pathway `approved_for_ruleset: false` until v3 approval.

A runtime-eligible ruleset must additionally:

- contain all exact target zones;
- match the complete source-approved legal-use/profile/pathway matrix;
- have no missing, extra, candidate, or unresolved records;
- pass source-file checksum and amendment-cutoff checks;
- pass the complete R1 semantic-equivalence gate;
- have project approval and `approved_for_ruleset: true` on every runtime record;
- use status `approved_for_runtime` with an approval date; and
- pass the application loader's fail-closed version and identity checks.

Schema validity alone never authorizes production loading.

## Deterministic lineage

The first migration consumes the immutable approved R1 v2 artifact directly and emits candidate `2026-07-19.1` plus an exhaustive crosswalk. It must:

- verify the predecessor identity, version, status, and checksum;
- migrate each v2 rule exactly once;
- move the single-family use rule into `use_permissions`;
- move approval and dimensional rules into the `single_family` profile;
- insert the profile ID into profile-owned rule identities;
- add the source-verified R1 two-family permission/pathway and multifamily `not_listed` record without inventing dimensional rules;
- convert global v2 scope limitations into structured topics with predecessor provenance;
- translate affected conflict rule IDs without losing assertions or resolution meaning;
- mark all v3 records nonapproved; and
- prove a canonical semantic projection of every migrated R1 rule equals its v2 source except for explicitly crosswalked representation changes.

Running the migrator twice against the same input must produce byte-identical ruleset and crosswalk content.

The citywide authoring successor consumes accepted candidate `2026-07-19.1` directly and emits candidate `2026-07-19.2` plus a separate expansion crosswalk. It must:

- preserve both R1 zone records, all inherited shared records, structured topics, and the R1-8L conflict exactly;
- add exactly R2 through R6 with the approved use/profile matrix;
- add exactly nine ordinary profiles and nine existing supported regulations per profile;
- keep `not_listed`, `no_maximum_listed`, the R1/R2 proximity transition, and Objective Design Standards disclosures semantically distinct;
- keep every new record nonapproved and the artifact nonruntime while Patrick Henry remains absent; and
- prove byte-identical target and crosswalk replay from the pinned predecessor and authoring code.

The additive schema version does not authorize changing the accepted `3.0.0` schema or `2026-07-19.1` artifact in place.

The density authoring successor consumes candidate `2026-07-19.2` directly and emits candidate `2026-07-19.3` plus a separate expansion crosswalk. It must:

- preserve every predecessor use permission and the existing nine regulations in every ordinary profile exactly;
- add `standard.gross_residential_density` once to each of the 11 R1-R6 ordinary profiles;
- use `quantity_range` in dwelling units per acre;
- preserve the R5 and R6 competing assertions, while selecting the project-owner-approved Table 1-1 values through project-resolved conflict records;
- pin the density-specific verification and amendment-audit supplements without changing predecessor-pinned documents;
- keep every candidate rule nonapproved and the artifact nonruntime; and
- prove byte-identical target and crosswalk replay from the checksum-pinned predecessor.

The additive density schema does not authorize changing schema `3.1.0` or candidate `2026-07-19.2` in place.

## Authoring workflow

1. Confirm the capability already exists in `supported-regulations.md`.
2. Verify the exact source and later-legislation status in the owning verification records.
3. Choose the exact zone, legal-use, profile or pathway, and primary-structure identities.
4. Choose the typed requirement that preserves the source meaning; never guess a number.
5. Add exact citations, conditions, exception families, and not-evaluated topics.
6. Record conflicts before applying any approved resolution.
7. Keep new or migrated records nonapproved.
8. Run schema, domain, mutation, source-integrity, migration, and determinism checks.
9. Obtain project approval for the complete candidate.
10. Only then produce a separately versioned runtime-approved artifact and integrate it through the loader and result contract.

AI-assisted extraction may propose records, mappings, or citations, but it must not set approval flags, resolve conflicts, or create runtime-eligible data.
