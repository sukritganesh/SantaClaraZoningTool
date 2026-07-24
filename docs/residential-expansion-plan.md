# Santa Clara Residential Zoning Expansion Plan

**Status:** Active implementation plan

**Last updated:** July 19, 2026

**Development branch:** `codex/residential-zone-expansion`

**Released baseline:** `v0.1.0-r1-prototype`, merged through PR #1

## 1. Purpose

Expand the released R1 vertical slice into a broader Santa Clara residential zoning product. The next release should accept a Santa Clara address, determine an exact supported residential zone, distinguish the relevant residential use and primary-structure type, and return the same limited family of evidence-backed base standards that the R1 release already handles.

The active product name is **Santa Clara Zoning Explorer**, with the scope line **Selected residential zoning standards by address**. Active application modules, documentation, and interface copy should migrate to that identity during their owning blocks. Historical release names, tags, plans, reports, immutable rulesets, migrations, and tests retain their R1/prototype names when those names identify provenance accurately.

This phase is primarily a data and contract expansion, but it is not data-only internally. The released implementation assumes R1 in names, allowed designations, ruleset validation, lookup outcomes, pipeline contracts, presentation wording, fixtures, and page copy. Those assumptions must be generalized deliberately while the validated R1 behavior remains protected by regression tests.

The product still reports selected zoning standards. It does not provide a complete entitlement analysis or a legal or planning determination.

## 2. Product boundary

### Included

- Selected residential base zones in the City of Santa Clara.
- Selected multifamily residential zones in the Patrick Henry Drive Specific Plan.
- Single-family, two-family, and multifamily dwelling classifications where the controlling zone permits them.
- Separate primary-structure identities for single-family, two-family, and multifamily structures.
- The existing supported regulation families: residential use status, Zoning Clearance, Architectural Review, maximum primary-structure height, maximum stories, maximum structure coverage, and front, rear, interior-side, and street-side setbacks.
- Explicit nonnumeric outcomes when a source does not state an ordinary numeric maximum or base value.
- Exact source citations, ruleset and GIS versions, limitations, conflicts, and controlled failure outcomes.
- A zone- and structure-aware user experience that no longer describes the active product as an R1 prototype.

### Excluded from this phase

- Commercial, industrial, public, mixed-use commercial, and other nonresidential zoning analysis.
- Parking evaluation.
- Recreation-space calculations.
- The 32-foot residential-transition standard as an evaluated rule.
- Full Objective Design Standards evaluation.
- Density, density bonus, unit-yield, floor-area, remaining-coverage, or proposal-compliance calculations.
- ADUs, JADUs, SB 9, accessory structures, historic and other combining districts, legal nonconformities, variances, and parcel-specific exceptions.
- Automated interpretation of plan-dependent standards or an unsupported special pathway.

An excluded subject must be labeled `not evaluated` when relevant. It must not be represented as prohibited, inapplicable, zero, or satisfied.

## 3. Target zoning designations

The initial expansion targets these exact legal designations:

### Citywide residential zones

- `R1-6L`
- `R1-8L`
- `R2`
- `R3`
- `R4`
- `R5`
- `R6`

### Patrick Henry Drive Specific Plan residential zones

- `PH-R5`
- `UV`
- `VR`
- `UC`
- `HDF`, the exact designation currently returned by the City GIS for the plan's HD Flex zone

Legacy, combining, or otherwise distinct GIS designations such as `R2-7L`, `R1-6LHT`, and `R2HT` are outside this phase. They must not be normalized to a nearby base zone without verified legal authority and an approved mapping.

`R5` and `R6` remain in the legal and synthetic rule scope even though the July 18, 2026 live GIS inspection returned no features with either exact designation. Block 1 must preserve a new immutable query result and confirm this observation. If no real parcels remain, the rules will receive synthetic contract fixtures but no invented real-address fixtures.

## 4. Residential use and structure model

The product must keep three related concepts separate:

1. **Workflow family:** single-family or multifamily. A two-family project may use the multifamily workflow.
2. **Legal use identity:** the use category named by the zoning permission table. Two-family and multifamily dwelling permissions cannot be merged because Santa Clara distinguishes them by zone.
3. **Primary-structure type:** the physical structure category to which dimensional standards apply.

Planned legal-use capabilities:

- `use.single_family_dwelling`
- `use.two_family_dwelling`
- `use.multifamily_dwelling`

Planned primary-structure identities:

- `single_family_primary_structure`
- `two_family_primary_structure`
- `multifamily_primary_structure`

Two-family may reuse multifamily workflow and presentation machinery, but the result contract and ruleset must retain its separate legal-use and structure identities. A two-family option must not be added to a zone merely because two units are a form of multifamily development in ordinary language.

### Planned zone/use/structure matrix

| Zone | Single-family | Two-family | Multifamily | Expansion treatment |
|---|---|---|---|---|
| `R1-6L`, `R1-8L` | Listed | Listed only through the Chapter 18.24 special pathway | Not listed | Preserve the existing single-family result. Disclose the two-family pathway without applying ordinary R1 single-family dimensional rules to it. |
| `R2` | Listed | Listed | Listed | Offer all three legal/structure choices and select standards by the chosen structure. |
| `R3`, `R4` | Not listed | Listed | Listed | Offer two-family and multifamily choices. |
| `R5`, `R6` | Not listed | Not separately listed | Listed | Offer multifamily only; do not manufacture a separate two-family permission. |
| `PH-R5`, `UV`, `VR`, `UC`, `HDF` | Not listed | Not separately listed | Listed | Offer multifamily residential analysis subject to specific-plan qualifications. |

“Listed” in this matrix is a planning target derived from the current residential research. Block 1 must verify each cell against the controlling code or specific plan before it becomes approved runtime data. A permitted use must remain separate from Zoning Clearance, Architectural Review, hearing triggers, and other approvals.

## 5. Supported regulations and explicit dispositions

This phase retains a deliberately small set of key base-zone standards rather than expanding into a full multifamily entitlement model. Gross residential density was added during Block 3 after source verification and project-owner approval; density bonus and unit-yield analysis remain outside scope.

| Family | Expansion intent |
|---|---|
| Residential use | Add separate two-family and multifamily legal-use capabilities; preserve single-family. |
| Zoning Clearance | Continue reporting the applicable requirement separately from use permission. |
| Architectural Review | Continue reporting the base requirement and relevant hearing qualification without evaluating every trigger. |
| Maximum primary-structure height | Return a numeric base maximum where stated, or an explicit FAA-controlled disposition where no fixed base maximum is stated. |
| Maximum stories | Return the stated base maximum without classifying a proposal's levels. |
| Maximum structure coverage | Return the stated percentage, or state that no maximum is listed in the controlling base-zone table. |
| Gross residential density | Return the stated base-zone minimum-to-maximum range in dwelling units per acre; preserve conflicting source assertions and any project resolution. Do not calculate parcel yield or apply plan, bonus, or state-law adjustments. |
| Front, rear, interior-side, and street-side setbacks | Return supported base values and already-supported typed story adjustments; retain context and plan dependencies. |

The minimum schema generalization should support these dispositions without inventing new regulation families:

- **Numeric requirement:** an ordinary supported number and unit.
- **Numeric range requirement:** a sourced minimum and maximum in the same closed unit, used for gross residential density without converting it into a parcel unit count.
- **No maximum listed:** the controlling base-zone source states no maximum for that field. Presentation must not call this “unlimited.”
- **FAA-controlled:** the source makes height subject to FAA criteria and does not state an ordinary fixed base maximum. This remains a height result, not a new overlay capability.
- **Plan-dependent:** the controlling plan or development plan supplies the value and the base table does not establish one.
- **Not evaluated:** a relevant rule layer or special standard is disclosed but is outside the current evaluator.
- **Review required:** the evidence conflicts or is insufficient for a deterministic approved result.

Patrick Henry rear setbacks must be represented as plan-dependent when the base table does not establish a value. The system must not substitute zero. A zero-foot setback may be encoded only if an authoritative source affirmatively states zero and that assertion passes verification.

## 6. Important qualification boundaries

### R1 two-family pathway

The R1 permission is a special Chapter 18.24 pathway. The chapter allows two attached or detached homes on an eligible R1 parcel, while Title 18 separately defines a two-family dwelling as one structure containing two units. If both homes remain inside the ordinary R1 building envelope, the R1 standards apply; if any portion is outside, special height/story and least-of setback rules apply together with other proposal-specific controls.

The current product does not collect the geometry, configuration, eligibility, or existing-structure facts needed to select those branches. It may list the pathway, but must return its dimensional standards as `not evaluated`. It must never silently attach the ordinary R1 single-family result to every two-unit project. Block 2 should preserve the attached/detached distinction without expanding this phase into a full SB 9 evaluator.

### Objective Design Standards

Ordinance 2085 adds an applicable design layer for new multifamily and residential mixed-use development and certain additions. This phase should disclose that layer and preserve its source, but it will not encode or evaluate the full Chapter 18.27 standards. The existing Chapter 18.27 amendment-number collision must remain visible until authoritative codification or City clarification resolves it.

### Residential transitions and recreation space

The 32-foot transition rule and recreation-space standards remain outside the supported regulation families for this phase. They should appear as relevant `not evaluated` qualifications where the controlling source makes them applicable.

### Patrick Henry plan controls

Patrick Henry standards must retain their specific-plan identity, citations, dependencies, and precedence. They must not be flattened into citywide `R5` values merely because one designation contains `R5`. A plan-dependent value stays plan-dependent unless the controlling plan supplies a verified deterministic base value.

## 7. Source and approval boundary

The research materials in the project Google Drive—including the Residential Zoning Research document, Rule Inventory spreadsheet, raw zoning code, adopted amendments, and supplemental watchlist—are candidate inputs. They may guide extraction and test planning but do not become approved runtime data by themselves.

Block 1 must establish and preserve:

- the applicable July 2025 consolidated Title 18 provisions;
- `docs/residential-title18-amendment-audit.md`, covering later adopted or pending amendments relevant to the target zones through a stated cutoff without mutating the checksum-pinned R1 audit;
- the Patrick Henry Drive Specific Plan provisions and maps;
- Objective Design Standards applicability and the unresolved Chapter 18.27 source issue;
- exact City GIS designations, counts, source object IDs, filters, and checksums in a new immutable snapshot;
- `docs/residential-rule-verification.md`, which separates source assertions, candidate interpretations, approved dispositions, conflicts, and unresolved questions;
- checksum-pinned capability supplements when adding a capability after a predecessor already pins the active verification and audit documents; the gross-density supplements are `docs/residential-density-rule-verification.md` and `docs/residential-density-title18-amendment-audit.md`;
- `docs/patrick-henry-rule-verification-supplement.md`, which checksum-pins the final plan/code reconciliation and accepted PH-R5 density resolution without modifying predecessor-pinned evidence; and
- consequential values, use permissions, structure applicability, and nonnumeric dispositions require human approval before runtime use.

Previously approved R1 rules remain approved only within their existing scope and immutable version.

## 8. Versioning and migration strategy

- Preserve tag `v0.1.0-r1-prototype` and all artifacts used to reproduce it.
- Do not modify the approved R1 ruleset at `rulesets/santa_clara/r1/2026-07-17.2/`.
- Preserve the v1 and v2 schemas and migration artifacts as historical compatibility evidence.
- Create a new residential ruleset lineage rather than enlarging an approved R1 artifact in place.
- Expect a new major ruleset-schema version because legal-use choice, multiple structure types, and nonnumeric dispositions change existing closed contracts. Confirm the exact version during Block 2 rather than declaring schema v2 compatible prematurely.
- Define an explicit crosswalk from every approved R1 rule and result field into the new residential contract.
- Keep the old R1 acceptance matrix running until the new product acceptance suite proves equivalent R1 outcomes or records an intentional, approved contract change.
- Assign new pipeline and presentation contract versions when their success shapes or status meanings change.

Historical filenames that accurately describe the released prototype—such as `r1-prototype-plan.md`, `r1-rule-verification.md`, R1 rulesets, and R1 release tests—should remain. Active product modules and user-facing labels should be generalized during their owning implementation blocks, with compatibility wrappers retained only where they have a deliberate migration purpose.

## 9. Likely refactoring surface

| Surface | Current assumption to remove | Intended direction |
|---|---|---|
| GIS acquisition | R1-only query, filenames, manifests, and two-designation validation | New residential-zone snapshot with an explicit approved designation set and complete count/checksum validation |
| Lookup | `LocalR1Lookup`, R1-only polygons, and `outside_supported_r1_snapshot` | Exact supported residential-zone lookup with controlled unsupported and legacy/combining outcomes |
| Ruleset validation | Exactly two zones, ten capabilities, and one structure type | Zone/use/structure completeness matrix plus typed nonnumeric dispositions |
| Ruleset loading and retrieval | `ApprovedR1Ruleset` and zone-only regulation selection | Approved residential ruleset selected by exact zone and applicable legal use/structure |
| Pipeline | `R1StandardsPipeline` and R1 success statuses | Residential analysis contract that cannot return standards for an unsupported zone/use/structure combination |
| Presentation | Fixed ten-capability closure, R1 scope label, single-family overview, and prototype wording | Registered residential capabilities, explicit use/structure choice, exact disposition wording, and product-level scope |
| Web interface | One implicit building type and R1 prototype page copy | Zone-aware residential-use summary, clear conditional/special-pathway states, and no active prototype label |
| Tests | R1-only success fixtures and hardcoded status strings | Preserved R1 regressions plus one meaningful fixture per reachable zone/structure branch and synthetic coverage where GIS has no parcel |
| Documentation | R1 plan and progress ledger treated as current | Historical R1 records plus this active expansion plan and a phase-specific progress ledger |

Refactoring should follow behavior boundaries rather than a repository-wide text replacement. Names that are public contracts, historical artifacts, or source identities need explicit migration decisions.

## 10. Block 2 contract design

**Status:** Design approved by the project owner on July 19, 2026.

**Implementation status:** Complete and project-owner accepted; the immutable approved successor is residential ruleset `2026-07-19.5`.

### 10.1 Contract audit findings

The released vertical slice has a sound deterministic core, but its contracts close over the prototype scope at several different layers. Generalization must preserve the good boundaries instead of replacing them with a loose all-purpose record shape.

| Surface | Released contract | Residential requirement |
|---|---|---|
| Ruleset schema | Zone-first `zones[zone].regulations[capability]`; one regulation per capability in each zone | Retain zone ownership while allowing explicit legal-use availability and multiple structure-owned regulation profiles in one zone |
| Domain validator | Exactly `R1-6L` and `R1-8L`, one structure type, ten capabilities, numeric maxima, and numeric setbacks | Validate the exact residential zone/use/structure matrix, profile completeness, nonnumeric dispositions, and special-pathway closure |
| Runtime eligibility | `candidate` or `approved_for_prototype`; approved v2 must replay the v1 R1 migration exactly | Use a new residential lineage and runtime approval state while retaining full source, schema, domain, migration, and per-rule approval gates |
| Ruleset loader | `ApprovedR1Ruleset` loads one hardcoded v2 ruleset, schema, crosswalk, and v1 source | Load a separately approved residential artifact set without mutating or weakening the released R1 gate |
| Standards retrieval | Exact zone key returns exactly ten approved records | Exact zone plus an available analysis profile returns the selected use rule, profile-owned standards, qualifications, and provenance closure |
| Pipeline result | `analyze_address(address)` attaches rules immediately after `r1_zone_found` | Address resolution first exposes valid selections; standards attach only after an exact available selection is supplied |
| Presentation | Fixed ten-capability registry, numeric maxima, one single-family overview, global string limitations, and R1 statuses | Dispatch the same regulation families for the selected profile, render typed dispositions, and preserve structured profile-specific limitations |
| Web boundary | One address input and one implicit building type | Address-first zone summary that lists verified residential types and presents their common supported standards without a mandatory structure selector |
| Acceptance tests | Two R1 successes and R1-specific status, scope, version, and copy assertions | Preserve the R1 matrix and add real or synthetic coverage for every reachable or explicitly unavailable residential selection |

The address normalizer, geometry primitives, immutable-source discipline, shared provenance model, conflict preservation, defensive-copy behavior, and deterministic ordering do not require conceptual redesign.

### 10.2 Version and artifact boundary

The implemented base representation is **ruleset schema `3.0.0`** in a new residential lineage. A major version is appropriate because one zone can now contain several legal-use and structure selections, requirement records can carry nonnumeric dispositions, and global string limitations become structured and profile-specific. Accepted R1 migration candidate `2026-07-19.1` remains pinned to this schema.

The R2-R6 authoring tranche requires one additive **schema `3.1.0`** refinement: a closed lot-area-tiered maximum shape within the existing structure-coverage capability. This preserves the two Table 2-3 lot-area outcomes for R3 and R4 without flattening either tier, inventing an unlimited value, or introducing a new regulation family. Schema `3.0.0` and candidate `2026-07-19.1` remain unchanged as the direct predecessor checkpoint.

The approved Block 3 gross-density addition requires additive **schema `3.2.0`**: a closed minimum-to-maximum quantity range plus the same range shape for conflict assertions. Candidate `2026-07-19.3` adds that capability to the 11 R1-R6 ordinary profiles while preserving schemas `3.0.0` and `3.1.0` and candidates `2026-07-19.1` and `.2` as immutable checkpoints.

The Patrick Henry tranche reuses **schema `3.2.0`** in candidate `2026-07-19.4`. Numeric maxima, quantity ranges, no-maximum-listed results, FAA-controlled values, and plan-dependent rear setbacks already have approved typed shapes, so adding the five plan designations is a data/provenance successor rather than a schema expansion.

Project-owner approval produces a separate immutable **`2026-07-19.5`** successor under schema `3.2.0`. The approval promotion changes only lifecycle identity and metadata, the checksum-pinned predecessor/crosswalk pointer, equivalent scope lifecycle wording, and every rule/pathway approval flag. A lifecycle-neutral semantic projection must prove that all zone data, requirement values and dispositions, conflicts, sources, citations, conditions, exceptions, and limitations remain identical to reviewed candidate `.4`.

The new artifacts should be introduced alongside, not in place of:

- `rulesets/schema/ruleset-v2.schema.json`;
- `rulesets/santa_clara/r1/2026-07-17.2/`;
- `rulesets/santa_clara/residential/2026-07-19.5/` as the approved residential input for later application integration;
- the v1-to-v2 migration and crosswalk; and
- the released R1 validator, loader, pipeline, presenter, and acceptance tests until residential replacement gates pass.

The residential ruleset ID is `santa-clara-residential-zoning`. Candidate artifacts use `status: candidate`; an approved artifact uses `status: approved_for_runtime`. Approval still requires a valid `approved_on` date and every selected rule to be individually approved. Versions use the existing `YYYY-MM-DD.revision` publication convention.

### 10.3 Proposed zone hierarchy

The ruleset remains zone-first, with exact GIS designations as keys:

```text
ruleset
├── metadata and jurisdiction
├── shared sources, citations, definitions, and exception families
├── zones
│   └── <exact GIS designation>
│       ├── use_permissions
│       ├── analysis_profiles
│       └── special_pathways
├── conflicts
├── not_evaluated_topics
└── disclaimer
```

Each zone has three separate responsibilities:

1. `use_permissions` explicitly records the source-table treatment of single-family, two-family, and multifamily dwelling uses. The allowed codes in this phase are `permitted_by_right` and `not_listed`. `not_listed` must never be presented as `prohibited` without separate authority, and special-pathway analysis status must not overwrite the source's permission category.
2. `analysis_profiles` contains only ordinary selectable combinations that can return the supported standards. Each profile binds one stable profile ID to one workflow family, one legal-use capability, and one primary-structure type.
3. `special_pathways` discloses a source-backed route whose dimensional analysis is unavailable under the current inputs. It must not inherit the nearest ordinary profile.

The standard profile IDs are:

| Profile ID | Workflow family | Legal-use capability | Primary-structure type |
|---|---|---|---|
| `single_family` | `single_family` | `use.single_family_dwelling` | `single_family_primary_structure` |
| `two_family` | `multifamily` | `use.two_family_dwelling` | `two_family_primary_structure` |
| `multifamily` | `multifamily` | `use.multifamily_dwelling` | `multifamily_primary_structure` |

Profiles exist only where the approved use matrix provides an ordinary analyzable combination. Every zone still carries all three `use_permissions` records so that absence, availability, and special treatment are explicit rather than inferred from missing data.

The R1 two-family use-permission record remains `permitted_by_right` with its Chapter 18.24 condition and special-pathway reference. The pathway itself belongs under `special_pathways`, not under an ordinary `two_family` profile. Its record should identify the multifamily workflow, the two-family legal-use capability, the attached-or-detached configuration boundary, exact source references, and a `not_evaluated` analysis disposition. This avoids falsely describing two detached homes as one two-family primary structure and prevents ordinary R1 single-family standards from being attached automatically.

### 10.4 Rule ownership and identity

Use-permission rules remain zone-owned. Approval and dimensional rules become analysis-profile-owned because the same capability can appear more than once within a zone with different structure applicability.

The proposed rule-ID conventions are:

```text
us.ca.santa_clara.<zone-slug>.<use-capability-id>
us.ca.santa_clara.<zone-slug>.<profile-id>.<capability-id>
```

Profile-owned IDs deliberately include the profile. This prevents an existing rule identity from changing meaning when another structure is later added to the same zone. Equal values across profiles or zones remain independent rules; shared citations and exception records may be reused by reference.

Because this is a major contract migration, existing R1 approval and dimensional rule IDs receive explicit predecessor-to-successor mappings rather than being ambiguously reused. The legal value, conditions, provenance, conflicts, and approval evidence remain continuous even when the v3 identity adds a profile component.

### 10.5 Requirement kinds and dispositions

The existing `status`, `maximum_quantity`, and `setback` payloads remain the typed numeric and permission representations. Schema v3 adds only the minimum nonnumeric requirement kinds needed by the approved scope:

| Requirement kind | Meaning | Allowed use in this phase |
|---|---|---|
| `status` | Source-backed use or approval category | Use permissions, Zoning Clearance, and Architectural Review |
| `maximum_quantity` | Ordinary numeric maximum with explicit unit | Height, stories, and structure coverage |
| `lot_area_tiered_maximum` | Separate maximum or no-maximum-listed outcomes below and at/above one stated lot-area threshold | Structure coverage only; added in schema `3.1.0` without creating a new capability |
| `quantity_range` | Sourced minimum and maximum in one closed unit | Gross residential density only in schema `3.2.0`; retrieves a base range without calculating unit yield |
| `setback` | Ordinary base minimum with supported typed adjustments | Front, rear, interior-side, and street-side setbacks |
| `no_maximum_listed` | The controlling base table supplies no maximum | A maximum capability only; never rendered as unlimited |
| `faa_controlled` | The source supplies `FAA` instead of an ordinary number | Patrick Henry `UC` height and stories only in this phase |
| `plan_dependent` | No universal base value is supplied; a controlling plan or project record is required | Patrick Henry rear setback in this phase; never a zero fallback |
| `not_evaluated` | A relevant rule or special pathway cannot be evaluated with current facts or capabilities | R1 Chapter 18.24 dimensions and other approved deferrals |
| `review_required` | Approved evidence cannot support one deterministic value | Unresolved conflicts or insufficient evidence; no guessed operational value. A separately approved project resolution may instead retain a typed value plus its conflict warning. |

Every nonnumeric requirement must contain exact `source_refs`, a controlled reason code, and a concise source-backed explanation. `plan_dependent`, `not_evaluated`, and `review_required` may also identify the missing plan, facts, or evaluator prerequisites. They must not contain a placeholder numeric value.

Capability-specific domain validation remains strict. For example, `faa_controlled` is not a generic escape hatch for coverage, and `no_maximum_listed` cannot be used for a minimum setback.

### 10.6 Structured not-evaluated topics

The v2 top-level list of prose strings cannot express that Objective Design Standards apply to multifamily profiles but not to every result. Schema v3 should replace it with `not_evaluated_topics`, an object keyed by stable topic ID. Each topic record contains:

- a controlled label and reason code;
- exact source references;
- the missing facts, source layer, or evaluator capability where known; and
- a concise explanation that does not imply prohibition or satisfaction.

Each analysis profile and special pathway references only its applicable topic IDs. This structure implements promoted backlog item `DATA-004` without adding the 32-foot transition, recreation space, or Objective Design Standards as evaluated regulation families.

### 10.7 Selection and result contracts

The recommended pipeline result contract is a new major version, **`2.0.0`**. Address and spatial resolution remain separate from regulatory selection:

1. Resolve the address to one exact supported residential zone.
2. Return that zone's available analysis profiles and disclosed special pathways without attaching standards when no selection was supplied.
3. Accept one exact profile or special-pathway ID; do not accept independently supplied workflow, use, and structure fields that could contradict one another.
4. Retrieve standards only for an available ordinary profile.
5. Return a controlled no-regulations outcome for an unavailable selection or a special pathway whose analysis is `not_evaluated`.

The proposed controlled statuses are:

| Status | Meaning | Regulatory content |
|---|---|---|
| `residential_zone_found` | Exact zone found; selection still required | Available profiles and special pathways only |
| `residential_standards_found` | Exact available profile selected and approved standards retrieved | Complete selected use, profile regulations, dispositions, qualifications, and provenance |
| `analysis_not_evaluated` | An approved special pathway was selected but its standards require unsupported facts or logic | Pathway evidence and structured limitations; no ordinary dimensional standards |
| `selection_not_available` | The requested profile is not listed or available for the exact zone | Availability evidence only; no standards |
| `outside_supported_residential_snapshot` | Address found outside the exact selected residential snapshot | No regulations |
| `address_not_found`, `address_ambiguous`, `review_required` | Existing controlled lookup meanings | No regulations unless a later approved contract explicitly says otherwise |

A successful `2.0.0` result includes a `selection` object containing `profile_id`, `workflow_family`, `legal_use_capability_id`, and `primary_structure_type`. It also retains the exact zone, selected rule records, transitive provenance closure, structured not-evaluated topics, disclaimer, and independent address, residential GIS, ruleset, and contract versions.

The presentation contract should likewise move to `2.0.0` during Block 5. Block 2 defines its input meanings but does not implement or restyle the interface.

### 10.8 R1 migration and equivalence crosswalk

The v3 migration must consume the immutable approved v2 artifact, not the older v1 source directly. Its crosswalk must account for every approved v2 component:

| Approved v2 component | Residential v3 destination |
|---|---|
| Ruleset identity and scope | New residential identity and expanded scope, with predecessor metadata retaining the v2 artifact identity and checksum |
| R1 zone keys | Same exact `R1-6L` and `R1-8L` keys |
| `use.single_family_dwelling` | Zone-owned single-family use-permission rule and the `single_family` profile reference |
| Two approval rules per zone | Independent `single_family` profile-owned approval rules |
| Three maximum rules per zone | Independent `single_family` profile-owned rules with unchanged quantities, units, conditions, and references |
| Four setback rules per zone | Independent `single_family` profile-owned rules with unchanged base values, paired semantics, adjustments, and references |
| R1-8L source conflict | Preserved conflict assertions and resolution, with affected rule ID mapped to its v3 successor |
| Shared documents, citations, definitions, and exception families | Retained by stable ID unless an explicit collision or source update requires a documented successor |
| Global `not_evaluated` strings | Stable structured topic records referenced by both migrated R1 single-family profiles as applicable |
| Disclaimer | Product wording with the same legal limitation and no active prototype label |

Migration acceptance is semantic, not merely a file-count comparison. A canonical R1 projection must prove that both migrated profiles retain every approved permission, value, unit, adjustment, condition, exception reference, citation, conflict assertion, selected resolution, source document, verification date, and limitation. The only permitted differences before separate approval are the new contract versions, residential identity, profile containment, successor rule IDs, structured limitation shape, and removal of active prototype wording.

The released R1 runtime remains the comparison oracle until the residential acceptance suite passes. A migration difference outside the approved list is a blocking error, not an automatic modernization.

### 10.9 Validator and mutation-test contract

Schema validation should enforce local tagged shapes. A residential domain validator must additionally enforce:

- the exact 12 target zone keys and explicit `HDF` identity;
- one explicit use-permission record for each of the three residential use capabilities in every zone;
- the approved `permitted_by_right` or `not_listed` source-table treatment for every cell, plus the required special-pathway reference for the R1 two-family use;
- profile ID, workflow, legal-use, and structure correspondence, including the multifamily workflow for `two_family`;
- absence of ordinary profiles for `not_listed` uses;
- no ordinary R1 `two_family` profile and one complete Chapter 18.24 special-pathway record;
- the required approval and dimensional capability set for every ordinary profile, even when a requirement has a nonnumeric disposition;
- independent, convention-compliant rule IDs for every zone and profile;
- capability-compatible requirement kinds, units, setback shapes, and disposition codes;
- complete source, exception, conflict, topic, profile, and special-pathway references;
- two-level runtime approval and no candidate records in an approved artifact;
- complete v2-to-v3 crosswalk coverage and deterministic R1 semantic replay;
- explicit zero-count fixture treatment for `R5` and `R6`; and
- rejection of excluded exact designations and any attempt to normalize them to a target zone.

Mutation tests must break each invariant independently: matrix completeness, profile identity, use/structure correspondence, unsupported requirement kinds, illegal disposition/capability pairs, missing sources, unresolved conflicts, approval gates, crosswalk entries, R1 replay, zero-count treatment, and excluded-designation handling.

### 10.10 Block 2 implementation sequence

Block 2 implementation proceeds in these gated steps:

1. Update the capability catalog for the two new legal-use capabilities and the approved disposition/support boundaries, while leaving additional regulation families deferred.
2. Update the ruleset authoring guide with the v3 hierarchy, identity rules, payload mappings, special-pathway contract, and structured not-evaluated representation while preserving the approved v2 contract as historical compatibility evidence.
3. Add the new schema and schema-level mutation tests without changing runtime loading.
4. Add the residential domain validator and its invariant/mutation suite.
5. Add the deterministic approved-v2-to-candidate-v3 migrator and exhaustive crosswalk.
6. Validate the migrated R1 profiles against the released oracle and document any intentionally changed identity or wording.
7. Specify executable fixtures for result contract `2.0.0` and invalid selections without wiring the production lookup or interface.
8. Obtain project-owner approval of the implemented contracts before Block 3 authors any new-zone rule records.

Block 2 does not author R2-R6 or Patrick Henry numeric data, load the residential GIS at runtime, modify the production pipeline, or change user-visible presentation.

Schema and domain validation deliberately distinguish a **partial candidate** from a **runtime-eligible ruleset**. A partial candidate may contain a nonempty subset of the exact target zones so the approved R1 rules can prove migration and contract behavior during Block 2. Runtime eligibility remains fail-closed and requires all 12 exact target designations, every approved use-permission matrix cell, every required ordinary profile or special pathway, project approval, and all source and conflict gates. Partial candidates must never be loadable by the production runtime.

## 11. Block 4 lookup and retrieval design

**Status:** Design approved by the project owner on July 19, 2026. Implementation remains gated by the five reviewable tranches below.

### 11.1 Audit findings

The released R1 runtime has good deterministic boundaries, but each public component is intentionally closed over the old two-zone, single-selection contract. Block 4 should extend those boundaries alongside the released path instead of changing every layer at once.

| Surface | Reusable foundation | Blocking R1 or pre-runtime assumption | Block 4 direction |
|---|---|---|---|
| Ruleset loader | JSON artifact loading, source checks, fail-closed errors, recursive freezing, and defensive copies | `ApprovedR1Ruleset` loads the v2 artifact set, validates only the v1-to-v2 migration, and counts `zones[*].regulations` | Add an approved residential loader that validates `.5` and its complete lineage before exposing the v3 zone/use/profile/pathway hierarchy |
| GIS lookup | Address normalization, exact matching, immutable manifest and checksum loading, spatial indexes, point-in-polygon logic, and parcel/current-zoning agreement | `LocalR1Lookup`, the snapshot paths, accepted designations, status names, count keys, and messages are R1-specific | Add exact residential lookup over the July 18 snapshot, with the 12-zone ruleset as the supported identity set and explicit validation of complete manifest counts, zero-count R5/R6, and cross-layer agreement |
| Standards retrieval | Exact case-sensitive keys, approval checks, reference closure, deterministic ordering, and no partial results | Retrieval accepts only a zone, expects the v2 flat rule map, and recognizes only the v2 requirement kinds | Split pure selection listing from exact selection retrieval; return one zone-owned use rule plus either one ordinary profile or one special pathway and its transitive evidence |
| Pipeline | One loaded lookup and ruleset, controlled failures, version attachment, result consistency checks, and deterministic replay | `R1StandardsPipeline.analyze_address(address)` immediately attaches the only profile and emits contract `1.0.0` | Add an address-first residential pipeline accepting an optional exact `selection_id`; no selection lists choices, while a valid selection retrieves only its approved branch |
| Result contract fixtures | Eight controlled statuses, profile/pathway separation, structured topics, conflict maps, and source closure | The executable fixtures use candidate `.1`, expect nine profile regulations, omit the now-approved density rule, and are explicitly nonruntime | Preserve `2.0.0` as the accepted Block 2 checkpoint and create a narrow runtime successor against approved `.5` |
| Presentation and web | Known-integrity-error boundary and the released R1 regression oracle | Presentation accepts only pipeline `1.0.0`, numeric R1 requirement shapes, one implicit selection, and R1 copy | Do not change these components in Block 4; the default web application remains on the released R1 path until Block 5 |

The result-contract audit found three mismatches that must be corrected before production data is wired:

1. Every approved `.5` ordinary profile contains ten regulations because gross residential density was added after the `.1` fixture was created; the current fixture validator hardcodes the earlier nine-capability set.
2. `outside_supported_residential_snapshot` currently requires a parcel ID and exact non-target zone. The intentionally filtered residential snapshot can prove that an address point has no matching target parcel or zoning feature, but it cannot identify the excluded zone or parcel.
3. A successful selection names its legal-use capability but does not carry the selected zone-owned use-permission rule or its provenance, despite the approved design requiring the selected use and profile standards together.

These are representation/runtime mismatches, not new zoning capabilities. Fixing them must not add a status, regulation family, inferred permission, alias, parcel calculation, or proposal evaluation.

### 11.2 Proposed runtime boundaries

The production-independent Block 4 path should have four explicit components:

```text
approved residential .5 lineage ──> ApprovedResidentialRuleset ──┐
                                                                 ├─> ResidentialStandardsPipeline
address + residential GIS ────────> LocalResidentialLookup ──────┘
                                              │
                                              └─> exact zone -> available selections
                                                                   │
                                                                   └─> one selected branch + evidence
```

1. **`ApprovedResidentialRuleset`** loads the canonical `.5` ruleset, schema, approval crosswalk, `.4` candidate, and every checksum-pinned predecessor needed by the complete approved-v2-to-v3.2 validator. It must run source, lineage, replay, semantic-preservation, per-record approval, and runtime-eligibility gates before freezing the ruleset. Candidate `.4` and a self-consistent but semantically changed `.5` must both fail.
2. **`LocalResidentialLookup`** reuses the address and geometry primitives but loads `parcels_residential.geojson` and `current_zoning_residential.geojson`. Default construction must validate the address and residential manifests, output checksums and counts, exact requested designation set, per-zone counts, explicit R5/R6 zeroes, observed positive-count designations, and parcel/current-zoning agreement. It must never normalize `R1-6LHT`, `R2-7L`, or `R2HT` to a target zone.
3. **Pure residential selection retrieval** exposes deterministic `available_selections(zone, ruleset)` and `retrieve_residential_selection(zone, selection_id, ruleset)` behavior. Profile order is single-family, two-family, then multifamily; special pathways follow in ruleset order. Callers supply one exact selection ID rather than independently supplied use, workflow, and structure fields. The retriever validates the zone-owned permission, profile/pathway binding, approval flags, complete capability set, transitive topics, conflicts, citations, exception families, and source documents.
4. **`ResidentialStandardsPipeline`** owns result-contract mapping. `analyze_address(address, selection_id=None)` returns `residential_zone_found` with choices when no selection is provided; an available profile returns `residential_standards_found`; the R1 pathway returns `analysis_not_evaluated`; a known but unavailable profile returns `selection_not_available`; lookup ambiguity, absence, outside-snapshot results, and spatial disagreement remain controlled no-regulations outcomes. Integrity errors remain exceptions for the later safe web boundary and are never recast as parcel-specific review.

The new components may share private loaders and immutable-copy helpers with the R1 implementation, but the released public classes, contract `1.0.0`, default Flask application, templates, static assets, and R1 tests remain operational until Block 5 deliberately switches consumers.

### 11.3 Runtime result-contract successor

Create an immutable contract successor, proposed as **`2.1.0`**, rather than rewriting accepted `2.0.0`. It retains the same eight statuses and selection identities and makes only these runtime corrections:

- use approved ruleset `.5` and require the exact ten-capability profile selected from that ruleset instead of validating against the earlier nine-capability fixture expectation;
- add the selected zone-owned `use_permission` record to successful ordinary-profile and special-pathway results, and the relevant `not_listed` permission to known unavailable-profile results;
- include use-permission sources in the transitive regulatory closure;
- allow the outside-snapshot property evidence to contain the matched address with null parcel and zone identities, without guessing the excluded zoning designation;
- allow an empty entered address to produce the controlled `address_not_found` result rather than an invalid result envelope; and
- preserve independent address, residential-GIS, ruleset, schema, and result-contract versions on every normal pipeline outcome.

No independently supplied workflow family, legal-use capability, or structure type is accepted. Those fields always come from the selected approved profile or pathway. Unknown or malformed selection IDs fail closed; they do not trigger fuzzy matching or the nearest available profile.

### 11.4 Gated implementation sequence

Block 4 should proceed in five reviewable tranches:

1. **Contract correction and runtime fixtures:** add contract `2.1.0`, its validator, and approved-`.5` fixtures for all eight statuses; preserve the `2.0.0` checkpoint and tests.
2. **Approved residential loader:** expose a callable complete-lineage validator, add the frozen runtime loader, and mutation-test candidate, checksum, lineage, semantic, approval, missing-artifact, and defensive-copy failures.
3. **Residential GIS lookup:** implement exact snapshot loading and the ten real-address fixtures; add synthetic R5/R6 and excluded-designation coverage plus ambiguity, no-match, mismatch, overlap, checksum, count, and manifest failures.
4. **Selection retrieval and pipeline:** implement deterministic choice listing, exact profile/pathway retrieval, complete provenance closure, all controlled outcomes, and cross-process repeatability without touching presentation or Flask.
5. **Block 4 acceptance:** run the full zone/selection matrix, requirement-shape and conflict cases, released R1 regressions, approved ruleset validator, focused runtime suites, and complete repository suite; record evidence before Block 5 begins.

Each tranche must leave the default application on the released R1 pipeline. Block 4 is complete only when the backend contract is accepted and all gates pass; file existence or one successful multifamily address is insufficient.

### 11.5 Acceptance matrix

| Boundary | Required evidence |
|---|---|
| Approved artifacts | Canonical `.5` loads; `.4`, unapproved records, checksum changes, lineage drift, semantic mutations, missing files, and unsupported identities fail closed |
| Real residential lookup | One verified address succeeds for each live designation: `R1-6L`, `R1-8L`, `R2`, `R3`, `R4`, `PH-R5`, `UV`, `VR`, `UC`, and `HDF` |
| Zero and excluded GIS scope | R5/R6 work through synthetic retrieval fixtures only; `R1-6LHT`, `R2-7L`, and `R2HT` remain exact unsupported designations and never become target zones |
| Selection matrix | R1 single-family and special pathway; all three R2 profiles; R3/R4 two-family and multifamily; R5/R6 and Patrick Henry multifamily; every source-verified unavailable profile |
| Requirement shapes | Numeric maximum, quantity range, lot-area-tiered maximum, no maximum listed, FAA-controlled, numeric setback, paired setback, and plan-dependent setback all survive retrieval unchanged |
| Conflicts and limitations | R1-8L, R5, R6, and PH-R5 conflicts retain selected and competing assertions; applicable structured topics and prerequisites are complete |
| Controlled outcomes | Selection required, standards found, special pathway not evaluated, selection unavailable, outside snapshot, address not found, address ambiguous, and review required never leak partial regulations |
| Regression and determinism | Released R1 loader/lookup/pipeline/presentation/web tests remain green; repeated and cross-process residential results are byte-equivalent for identical inputs |

### 11.6 Block 4 file and scope policy

Expected implementation surfaces are the runtime loader, lookup, standards retrieval, pipeline, result-contract successor and validator, focused fixtures/tests, README commands if a new runnable entry point is added, this plan if the approved design changes, and `docs/progress.md` for execution evidence.

Block 4 does **not** change regulatory values, schemas `3.0.0` through `3.2.0`, approved ruleset `.5`, source snapshots, the capability catalog, presentation contract, templates, CSS, JavaScript, or active page copy. It does not add a database, live GIS call, fuzzy address or zone matching, commercial use, density bonus, unit-yield calculation, proposal compliance, or a new regulation family.

## 12. Block 5 common-zone presentation design

The approved runtime ruleset retains separate legal-use, workflow, and primary-structure profiles, and the contract-`2.1.0` backend retains exact selection retrieval. Those identities remain necessary regulatory data and future application infrastructure. They do not, by themselves, require a blocking selection step in the current public interface.

A direct audit of approved ruleset `2026-07-19.5` found that every zone with more than one ordinary profile currently has semantically identical supported regulations across those profiles:

- R2 single-family, two-family, and multifamily profiles have the same ten requirements, applicability, conditions, exception references, validation statuses, and conflict treatment after profile-specific rule identity is excluded;
- R3 and R4 two-family and multifamily profiles pass the same comparison; and
- the only profile-specific presentation difference in those zones is the structured Objective Design Standards `not evaluated` topic attached to multifamily.

Block 5 therefore uses a **common zone summary** rather than requiring the user to select a structure:

1. Resolve the address and exact zone once.
2. Retrieve every approved ordinary profile internally and verify semantic equality before presenting one shared set of supported standards.
3. List each source-verified residential use and structure identity separately, with its own use-permission evidence.
4. Preserve profile-specific `not evaluated` topics as conditional disclosures naming the residential type to which they apply.
5. Retain each R1 Chapter 18.24 pathway as structured `not evaluated` backend data, but do not render unavailable pathway cards in the staff interface or merge them into the ordinary R1 standards.
6. Fail closed without regulatory cards if ordinary profiles in one zone differ. A later interface may then activate the already implemented exact selection path under backlog item `UX-001`.

The comparison excludes only profile-specific rule IDs. Requirement payloads, applicability, conditions, exception references, validation status, and conflict identity must match. The interface must not silently choose one profile, relabel a representative profile as universal, or suppress a conditional topic.

The active product copy is **Santa Clara Zoning Explorer** with scope line **Selected residential zoning standards by address**. The established page hierarchy, green visual system, search interaction, property card, approval and standard cards, setback table, disclosures, numbered source appendix, accessibility behavior, and responsive layout should be extended rather than redesigned. A single source-help note near the top of every successful result explains that the `i` controls open supporting citations and exact evidence. Residential-use cards show only the use identity, its evidence control, and permission status; repetitive profile labels and permission boilerplate remain in presentation data but are not repeated in each card. Consequential conditional, proposal-dependent, and source-conflict qualifications appear beside the affected standard rather than in a detached section.

## 13. Implementation blocks

| Block | Objective | Exit conditions |
|---|---|---|
| 0. Establish the transition contract | Archive the completed R1 ledger, create this plan and a new active ledger, and update durable repository instructions. | Historical links resolve, active scope is unambiguous, no code or runtime data changes occur, and documentation validation passes. |
| 1. Verify sources and acquire residential GIS | Verify the zone/use/structure matrix and selected standards, audit amendments, and preserve a complete residential GIS snapshot. | New manifests prove exact filters, IDs, counts, checksums, and designations; a residential source-verification record is ready for owner review. |
| 2. Generalize the data and result contracts | Design the new ruleset schema, applicability model, dispositions, migration crosswalk, validators, and result contracts. | Contracts are documented, mutation-tested, owner-approved, and can replay the approved R1 data without loss. |
| 3. Author and approve residential rules | Encode independent zone- and structure-owned candidate rules with provenance and conflicts. | Every matrix cell has an explicit approved, `not_listed`, special-pathway, plan-dependent, not-evaluated, or review-required treatment; runtime eligibility passes. |
| 4. Expand lookup and retrieval | Load the residential GIS and ruleset, determine exact zones, and retrieve standards only for valid use/structure combinations. | Real and synthetic fixtures cover supported, unsupported, ambiguous, mismatch, missing-data, and integrity outcomes deterministically. |
| 5. Generalize presentation and interface | Remove active R1/prototype assumptions, present the verified common zone standards and residential-use matrix, and render all supported dispositions and qualifications without a mandatory structure selector. | Desktop and mobile states are accessible, source-linked, deterministic, preserve profile-specific disclosures, keep unavailable special pathways in backend data without presenting them as results, place consequential qualifications beside affected rules, and fail closed if profiles diverge or lookup evidence is insufficient. |
| 6. Validate and release | Run the complete acceptance matrix, protect the R1 baseline, document limitations, and assign the next release identity. | Source, migration, regression, offline, determinism, interface, and complete-suite gates pass with no unexplained skips. |
| 7. Add local address autocomplete | Use the validated citywide address snapshot to progressively enhance address discovery without changing exact final lookup. | Bounded deterministic suggestions, strict public response fields, duplicate and unit safety, accessible pointer and keyboard selection, manual fallback, real-snapshot outcomes, and the complete release matrix pass before owner acceptance and `v0.3.0` release work. |
| 8. Add supported parcel context maps | Use the validated residential GIS snapshot to show the selected parcel and nearby supported zoning beside successful results without changing the zoning conclusion. | Bounded local GeoJSON, safe public fields and controlled failures, a distinct 12-zone categorical palette, accessible responsive mapping, tile-independent geometry, real-fixture coverage, and the complete release matrix pass before owner acceptance and `v0.3.0` release work. |

Implementation should stop at each source, contract, data-approval, and release gate for project-owner review.

## 14. Block 0 file policy

This documentation transition intentionally changes only:

- `docs/residential-expansion-plan.md`, the active design and scope reference;
- `docs/progress.md`, the active expansion status ledger;
- `docs/progress-archive/2026-07-18-r1-prototype-progress.md`, the preserved R1 ledger;
- `AGENTS.md`, the durable repository instructions; and
- a historical report link that must point to the archived validation ledger.

`README.md`, the capability catalog, authoring guide, source-verification documents, schemas, rulesets, application code, scripts, tests, and user-interface copy remain unchanged in Block 0. Each will be updated in its owning later block when its actual contract or behavior changes.

## 15. Expansion completion criteria

The phase is complete when the product can:

- resolve an address through validated local data to an exact supported residential zone;
- list only the residential uses and primary-structure types verified for that zone;
- distinguish single-family, two-family, and multifamily legal and structural identities without duplicating or inventing permission;
- retrieve the selected supported regulation families for the exact zone/use/structure combination;
- present numeric, no-maximum-listed, FAA-controlled, plan-dependent, not-evaluated, conflict, and review-required outcomes without semantic loss;
- retain citations, source versions, ruleset versions, conditions, amendment status, and limitations;
- preserve the released R1 results or document and approve any intentional change;
- fail closed on unsupported designations, invalid selections, incomplete data, and integrity errors;
- reproduce the same structured and rendered results from the same versioned inputs; and
- describe itself as a selected residential zoning information product, not as a complete entitlement analysis or legal or planning determination.

## 16. Post-release local address autocomplete

**Status:** Owner-approved post-`v0.2.0` UX design; Block 7 implementation is validated and owner accepted, with normal `v0.3.0` release gates in progress.

The address field should progressively suggest canonical records from the already validated July 16 citywide address snapshot. This is a discovery aid over the existing exact lookup boundary, not a new geocoder, zoning source, or regulatory conclusion. Suggestions cover all active Santa Clara address records, including addresses outside the selected residential snapshot; final submission continues through the unchanged address, parcel, zoning, ruleset, summary, and presentation gates.

The local suggestion contract is:

- begin after three normalized alphanumeric characters and reject queries longer than 120 characters;
- rank exact normalized matches, full-address prefixes, then ordered token-prefix matches without fuzzy correction;
- collapse identical canonical address values, retain their source-record count, return no more than eight choices, and report truncation so unit-heavy addresses prompt more typing rather than an arbitrary selection;
- expose only canonical address display/value, Santa Clara locality and ZIP, duplicate count, total unique match count, truncation, and address-snapshot identity through a same-origin endpoint;
- never expose coordinates, object IDs, parcel facts, zoning facts, or regulations in a suggestion response; and
- keep ordinary GET form submission operational when JavaScript or suggestions are unavailable.

The interface follows the editable ARIA combobox pattern, debounces and cancels stale requests, supports pointer and keyboard selection, and immediately submits an explicitly chosen suggestion. It remains local vanilla JavaScript with no API key, online provider, frontend package manager, or runtime third-party request. Rulesets, source snapshots, regulatory schemas, result contracts, supported capabilities, and zoning-analysis behavior remain unchanged.

## 17. Post-release supported parcel context maps

**Status:** Owner-approved post-`v0.2.0` UX design; Block 8 implementation and local automated validation are complete and owner accepted, with normal `v0.3.0` release gates in progress.

A successful supported lookup places its property identity beside a focused map of the selected parcel and nearby polygons from the already validated July 18 residential GIS snapshot. The map is a presentation receipt for staff confidence, not another zoning source: exact address matching, parcel/current-zoning agreement, supported designation selection, ruleset retrieval, and presentation continue through the unchanged deterministic pipeline before any geometry is exposed.

The local map-context contract:

- returns geometry only for one exact supported address, parcel, and agreeing current-zoning match;
- expands the selected parcel bounds by a deterministic meter-based neighborhood buffer with a 200-meter minimum, returns complete intersecting supported zoning features in stable source order, and fails closed rather than truncating an oversized context;
- exposes only contract and snapshot versions, canonical address, APN, selected zone, named bounds, selected-parcel GeoJSON, supported-zoning GeoJSON, feature count, and the exact supported-zone scope through `GET /api/property-map?address=...`;
- strips source object IDs and unrelated parcel, regulatory, citation, ruleset, and source-record fields; and
- keeps not-found and outside-snapshot responses at 404, ambiguity and spatial review at 409, invalid addresses at 400, and unavailable or invalid context at 503 without changing the server-rendered zoning result.

The successful-result header becomes a 40/60 property/context grid so the map receives more horizontal space, then stacks at the existing narrow-screen breakpoint. Locally vendored Leaflet 1.9.4 fits the selected parcel with padding and a maximum initial zoom of 19, restricts panning to the returned context, permits only one additional zoom-out level, and draws the optional street tiles below local zoning and parcel paths. The selected parcel uses a prominent high-contrast white halo and five-pixel dark-green outline so it remains obvious over every zoning color. Pointer hover over a supported zoning polygon reveals only its designation through a DOM-built tooltip. A narrow collapsed native **Map legend** disclosure overlays the map and contains the parcel, unshaded-area key, and concise visible zone codes; text, live status, keyboard controls, touch behavior, reduced motion, forced colors, JavaScript fallback, endpoint failure, and basemap failure remain explicit.

The checked-in presentation palette prioritizes hue separation and saturation over visual correspondence with the City map. Every supported designation has a unique color, including the zero-count R5 and R6 ruleset zones. Fill opacity remains high enough to distinguish neighboring polygons while retaining street context. These are presentation values only and do not change the pinned GIS or regulatory data:

| Supported designation | Local display color | Categorical color family |
|---|---|---|
| `R1-6L` | `#0067c5` | Cobalt blue |
| `R1-8L` | `#f28e00` | Orange |
| `R2` | `#009e49` | Emerald green |
| `R3` | `#7a3e9d` | Purple |
| `R4` | `#d62728` | Red |
| `R5` | `#00a6d6` | Cyan |
| `R6` | `#e6c200` | Yellow |
| `PH-R5` | `#c51b7d` | Magenta |
| `UC` | `#8c510a` | Brown |
| `UV` | `#008c95` | Teal |
| `VR` | `#7a9a01` | Olive-lime |
| `HDF` | `#444444` | Charcoal |

The browser may request the current viewport from the configurable default OpenStreetMap tile URL. The application retains visible attribution, ordinary browser caching and referrer behavior, and never proxies, prefetches, bulk-downloads, or packages those tiles. Leaflet code and all authoritative parcel/zoning geometry remain local; tile failure leaves the colored zoning and parcel outline visible over a neutral background. No live City GIS call, external geocoder, API key, billing account, result-contract change, ruleset change, capability change, or raw snapshot change is part of Block 8.

## 18. Post-release exact regulatory source evidence

**Status:** Owner-approved post-`v0.2.0` UX design; Block 9 implementation and local automated validation are complete and owner accepted, with normal `v0.3.0` release gates in progress.

Every source control rendered from approved ruleset `2026-07-19.5` resolves through a separate, versioned source-evidence catalog. The sidecar binds the exact `(zone, rendered rule or capability, citation)` context to the approved source location; reused tables therefore open different cells for different zones instead of one generic page. PDF locations carry one-based PDF and printed-page numbers, normalized rectangles for the controlling cell, row label, paragraph, or heading, a short verified excerpt, and human-verification metadata. Markdown project records use immutable line ranges and excerpt checksums, and JSON predecessor evidence uses JSON Pointers. Native records are clearly labeled **Project verification record** and are not presented as official law.

The catalog covers only the approved runtime evidence chain: checksum-pinned official documents and the project audits, verification supplements, and predecessor record explicitly referenced by approved rules. Candidate Google Drive research and inventories are not staff-facing authority. Source, catalog, page-image, and renderer identities are preserved in an evidence manifest. Only referenced PDF pages are rendered at 144 DPI; the source PDF is never altered, and highlight overlays are drawn separately in HTML. The source-evidence add-on installs alongside the unchanged base and residential bundles, with no live Drive, City document, or other evidence request at runtime.

The Flask application accepts an optional source-evidence provider. The provider fails closed unless the catalog version, complete rendered-control coverage, source checksums, page counts, region bounds, excerpts, native anchors, and evidence-manifest checksums all validate. Dedicated evidence and document routes accept only catalog IDs, never arbitrary filesystem paths. The document route provides inline, range-capable, checksum-verified artifacts with restrictive content headers and immutable caching. Evidence unavailability returns a controlled 503 while the numbered source appendix and zoning result remain intact.

The established source popover retains its numbered citation and provides **View exact source** in a dedicated `noopener` tab; the redundant fragment link to the bottom source appendix is omitted. That view presents the displayed regulation and zone context, then prioritizes the highlighted full-page context, parallel accessible excerpt, and zoom or multi-page navigation before the supporting document identity, locator, checksum, verification status, checksummed-original action, and optional official URL. It states that highlighting is only a navigation aid and the checksummed original controls. Server-rendered pages remain usable without JavaScript; enhancement adds keyboard navigation and automatic highlight scrolling. Mobile panning, printing, forced colors, reduced motion, screen readers, and evidence failure are explicit acceptance paths. PDF.js and runtime frontend/network dependencies remain out of scope.

Block 9 changes no regulatory value, capability, ruleset schema, result contract, lookup outcome, raw snapshot, or zoning-analysis behavior. Future approved runtime citations must receive a verified contextual catalog binding before presentation approval.

## 19. Post-release source-grounded zone overviews

**Status:** Owner-approved post-`v0.2.0` UX design; Block 10 implementation and local automated validation are complete and owner accepted, with normal `v0.3.0` release gates in progress.

Every successful supported lookup should begin its regulatory content with a concise **Property Overview** that explains the selected zone in ordinary language. The overview identifies the exact designation, summarizes its general residential character and characteristic housing forms, distinguishes materially related zones when helpful, and names the approvals required by the approved ruleset. Exact density, height, coverage, story, and setback values remain in the detailed sections below rather than being repeated in the overview.

The copy comes from a separate zone-description catalog bound to approved ruleset `2026-07-19.5`, its checksum, the checked-in authoring guide, and exact existing source references. The catalog covers all 12 supported designations, including zero-GIS-count R5 and R6. Codex drafts new or materially affected descriptions offline from the complete supported-zone matrix and official purpose provisions; source review and project-owner acceptance remain release gates. The running application never calls an AI service, and candidate research never becomes presentation authority.

The catalog loads and validates once at application startup. Exact coverage, stable ordering, artifact checksums, source-reference closure, one-paragraph length, approval language, and the absence of numeric standards or raw HTML are enforced before the richer copy is used. A missing, stale, or invalid catalog falls back to the existing deterministic factual summary without changing or suppressing the zoning result.

The overview panel contains only its heading and reviewed description. A separate **How to use this result** section contains the existing scope notice and the explanation that `i` controls open supporting citations and exact evidence. This keeps orientation, operating guidance, detailed standards, and provenance visually distinct without changing any regulatory value, ruleset schema, result contract, lookup outcome, source-evidence target, raw snapshot, dependency, runtime-data bundle, or zoning-analysis behavior.
