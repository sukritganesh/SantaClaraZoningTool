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

This phase should retain the existing regulation families instead of expanding into a full multifamily entitlement model.

| Family | Expansion intent |
|---|---|
| Residential use | Add separate two-family and multifamily legal-use capabilities; preserve single-family. |
| Zoning Clearance | Continue reporting the applicable requirement separately from use permission. |
| Architectural Review | Continue reporting the base requirement and relevant hearing qualification without evaluating every trigger. |
| Maximum primary-structure height | Return a numeric base maximum where stated, or an explicit FAA-controlled disposition where no fixed base maximum is stated. |
| Maximum stories | Return the stated base maximum without classifying a proposal's levels. |
| Maximum structure coverage | Return the stated percentage, or state that no maximum is listed in the controlling base-zone table. |
| Front, rear, interior-side, and street-side setbacks | Return supported base values and already-supported typed story adjustments; retain context and plan dependencies. |

The minimum schema generalization should support these dispositions without inventing new regulation families:

- **Numeric requirement:** an ordinary supported number and unit.
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
- exact City GIS designations, counts, source object IDs, filters, and checksums in a new immutable snapshot; and
- `docs/residential-rule-verification.md`, which separates source assertions, candidate interpretations, approved dispositions, conflicts, and unresolved questions.

Consequential values, use permissions, structure applicability, and nonnumeric dispositions require human approval before runtime use. Previously approved R1 rules remain approved only within their existing scope and immutable version.

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
| Web interface | One implicit building type and R1 prototype page copy | Zone-aware residential choices, clear unavailable/special-pathway states, and no active prototype label |
| Tests | R1-only success fixtures and hardcoded status strings | Preserved R1 regressions plus one meaningful fixture per reachable zone/structure branch and synthetic coverage where GIS has no parcel |
| Documentation | R1 plan and progress ledger treated as current | Historical R1 records plus this active expansion plan and a phase-specific progress ledger |

Refactoring should follow behavior boundaries rather than a repository-wide text replacement. Names that are public contracts, historical artifacts, or source identities need explicit migration decisions.

## 10. Block 2 contract design

**Status:** Design approved by the project owner on July 19, 2026.

**Proposal status:** Ready for project-owner review; no schema, validator, migration, ruleset, runtime, presentation, or interface implementation is authorized by this section alone.

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
| Web boundary | One address input and one implicit building type | Address-first flow followed by an explicit available single-family, two-family, multifamily, or special-pathway selection |
| Acceptance tests | Two R1 successes and R1-specific status, scope, version, and copy assertions | Preserve the R1 matrix and add real or synthetic coverage for every reachable or explicitly unavailable residential selection |

The address normalizer, geometry primitives, immutable-source discipline, shared provenance model, conflict preservation, defensive-copy behavior, and deterministic ordering do not require conceptual redesign.

### 10.2 Version and artifact boundary

The recommended representation is **ruleset schema `3.0.0`** in a new residential lineage. A major version is appropriate because one zone can now contain several legal-use and structure selections, requirement records can carry nonnumeric dispositions, and global string limitations become structured and profile-specific.

The new artifacts should be introduced alongside, not in place of:

- `rulesets/schema/ruleset-v2.schema.json`;
- `rulesets/santa_clara/r1/2026-07-17.2/`;
- the v1-to-v2 migration and crosswalk; and
- the released R1 validator, loader, pipeline, presenter, and acceptance tests until residential replacement gates pass.

The proposed residential ruleset ID is `santa-clara-residential-zoning`. Candidate artifacts use `status: candidate`; an approved artifact uses `status: approved_for_runtime`. Approval still requires a valid `approved_on` date and every selected rule to be individually approved. The first version number remains undecided until candidate data is generated; it must continue the existing `YYYY-MM-DD.revision` publication convention.

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

## 11. Implementation blocks

| Block | Objective | Exit conditions |
|---|---|---|
| 0. Establish the transition contract | Archive the completed R1 ledger, create this plan and a new active ledger, and update durable repository instructions. | Historical links resolve, active scope is unambiguous, no code or runtime data changes occur, and documentation validation passes. |
| 1. Verify sources and acquire residential GIS | Verify the zone/use/structure matrix and selected standards, audit amendments, and preserve a complete residential GIS snapshot. | New manifests prove exact filters, IDs, counts, checksums, and designations; a residential source-verification record is ready for owner review. |
| 2. Generalize the data and result contracts | Design the new ruleset schema, applicability model, dispositions, migration crosswalk, validators, and result contracts. | Contracts are documented, mutation-tested, owner-approved, and can replay the approved R1 data without loss. |
| 3. Author and approve residential rules | Encode independent zone- and structure-owned candidate rules with provenance and conflicts. | Every matrix cell has an explicit approved, `not_listed`, special-pathway, plan-dependent, not-evaluated, or review-required treatment; runtime eligibility passes. |
| 4. Expand lookup and retrieval | Load the residential GIS and ruleset, determine exact zones, and retrieve standards only for valid use/structure combinations. | Real and synthetic fixtures cover supported, unsupported, ambiguous, mismatch, missing-data, and integrity outcomes deterministically. |
| 5. Generalize presentation and interface | Remove active R1/prototype assumptions, add residential structure selection, and present all supported dispositions and qualifications. | Desktop and mobile states are accessible, source-linked, deterministic, and cannot display regulatory content after a failed or unsupported selection. |
| 6. Validate and release | Run the complete acceptance matrix, protect the R1 baseline, document limitations, and assign the next release identity. | Source, migration, regression, offline, determinism, interface, and complete-suite gates pass with no unexplained skips. |

Implementation should stop at each source, contract, data-approval, and release gate for project-owner review.

## 12. Block 0 file policy

This documentation transition intentionally changes only:

- `docs/residential-expansion-plan.md`, the active design and scope reference;
- `docs/progress.md`, the active expansion status ledger;
- `docs/progress-archive/2026-07-18-r1-prototype-progress.md`, the preserved R1 ledger;
- `AGENTS.md`, the durable repository instructions; and
- a historical report link that must point to the archived validation ledger.

`README.md`, the capability catalog, authoring guide, source-verification documents, schemas, rulesets, application code, scripts, tests, and user-interface copy remain unchanged in Block 0. Each will be updated in its owning later block when its actual contract or behavior changes.

## 13. Expansion completion criteria

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
