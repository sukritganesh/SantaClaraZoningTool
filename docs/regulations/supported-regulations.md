# Supported Regulations Catalog

**Last updated:** July 19, 2026

**Current jurisdictional scope:** City of Santa Clara selected residential zoning expansion; the released runtime remains limited to R1-6L and R1-8L until the residential v3 approval and integration gates pass

This catalog defines the regulation families and supporting behaviors that belong to Santa Clara Zoning Explorer's selected residential scope. It explains what each capability means and where its current implementation stops. It does not define JSON fields or database tables, and it does not store jurisdiction-specific numeric values.

As regulation coverage grows, detailed family-specific documents may be added beside this catalog in `docs/regulations/`. This file remains the top-level index.

## Document boundaries

Each project artifact has a distinct role:

- This catalog defines **which regulatory capabilities are supported** and what support means.
- `ruleset-authoring-guide.md` defines the preserved approved ruleset v2 representation for the released R1 lineage.
- `residential-ruleset-authoring-guide.md` defines the approved ruleset v3 representation for the residential expansion lineage.
- The versioned ruleset stores approved Santa Clara values, citations, applicability, conditions, and provenance.
- `docs/r1-rule-verification.md` records the legal-source analysis supporting those values.
- The JSON Schema defines how supported capabilities are represented in machine-readable data.
- Deterministic application code decides which encoded rules apply and produces results.
- `docs/progress.md` records current implementation status and the next task.

Numeric standards must not be copied into this catalog. Keeping values in the versioned ruleset avoids synchronizing the same legal data across multiple documents.

## Shared core and jurisdiction extensions

The product should reuse a shared capability ID only when the regulation has the same operational and legal meaning across jurisdictions. Local terminology may map to a shared capability, but local values, citations, conditions, exceptions, conflicts, and approval details remain in the jurisdiction's versioned ruleset.

When a provision does not fit an existing shared capability exactly, it must not be flattened into a near-match. It should be proposed as a controlled jurisdiction extension. Before extension data can be authored or used, the extension must have:

- a documented meaning and product boundary;
- a collision-resistant jurisdiction identity;
- an approved standalone or embedded machine representation;
- provenance, validation, approval, and failure requirements; and
- deterministic retrieval, evaluation, and presentation behavior appropriate to its support stage.

An unrecognized extension must be rejected or reported as `not evaluated`; it must never be silently discarded. If equivalent extensions recur across jurisdictions, they may be deliberately promoted into the shared core through a versioned catalog, schema, migration, validation, and testing change.

The current Santa Clara work uses only the shared capabilities cataloged below. It does not yet implement arbitrary jurisdiction extensions.

## Capability stages

“Supported” is not a single binary state. A regulation moves through these cumulative stages:

| Stage | Meaning |
|---|---|
| Cataloged | Its meaning, boundaries, and intended behavior are documented here. |
| Encoded | Approved jurisdiction-specific data exists in a validated ruleset. |
| Retrievable | Deterministic code can select and return the applicable rule. |
| Evaluated | Deterministic code can apply the rule to parcel or proposal facts. |
| Presented | The interface displays the result, sources, limitations, and status. |

The released Santa Clara R1 rules are cataloged, encoded in approved ruleset v2 version `2026-07-17.2`, retrievable by exact R1-6L or R1-8L zone key, and attached after an unambiguous supported address-to-parcel-to-zone lookup. The residential expansion contract catalogs two-family and multifamily use identities, multiple structure profiles, and explicit nonnumeric dispositions; new-zone values remain non-runtime candidate data until their later authoring and approval gates pass. Parcel- or proposal-level compliance evaluation remains outside this phase.

## Current supported regulation families

### Use and approvals

| Capability ID | Regulation or behavior | Current scope | Current stage |
|---|---|---|---|
| `use.single_family_dwelling` | Single-family dwelling use classification | Explicit source-table status for every target-zone matrix cell; separate approvals remain visible | Retrievable for R1 from approved v2; residential v3 contract approved |
| `use.two_family_dwelling` | Two-family dwelling use classification | Separate legal-use identity; ordinary two-family structures use the multifamily workflow family, while the R1 Chapter 18.24 path remains separate | Residential v3 contract approved; no runtime data |
| `use.multifamily_dwelling` | Multifamily dwelling use classification | Explicit source-table status for every target-zone matrix cell | Residential v3 contract approved; no runtime data |
| `approval.zoning_clearance` | Zoning Clearance requirement | Construction associated with the supported permitted use | Retrievable from approved v2 |
| `approval.architectural_review` | Architectural Review requirement | Base review requirement and disclosure of hearing triggers | Retrievable from approved v2 |

### Dimensional standards

| Capability ID | Regulation or behavior | Current scope | Current stage |
|---|---|---|---|
| `standard.maximum_primary_structure_height` | Maximum primary-structure height | Base numeric limit with measurement and exception warnings | Retrievable from approved v2 |
| `standard.maximum_stories` | Maximum number of stories | Base numeric limit; automated story classification is excluded | Retrievable from approved v2 |
| `standard.maximum_structure_coverage` | Maximum structure coverage | Base percentage only; remaining development capacity is not calculated | Retrievable from approved v2 |

### Setbacks

| Capability ID | Regulation or behavior | Current scope | Current stage |
|---|---|---|---|
| `setback.front` | Front setback | Base requirement and supported upper-story difference | Retrievable from approved v2 |
| `setback.rear` | Rear setback | Base requirement | Retrievable from approved v2 |
| `setback.interior_side` | Interior-side setback | Scalar or paired base requirements and supported upper-story difference | Retrievable from approved v2 |
| `setback.street_side` | Street-side setback on a corner lot | Santa Clara calls this the corner-side setback; base and upper-story requirements are supported | Retrievable from approved v2 |
| `setback.adjustment.story_based` | Story-triggered setback or stepback | A different minimum may apply beginning at a specified story | Retrievable as embedded approved-v2 behavior |
| `setback.configuration.paired_side_yards` | Unequal paired interior-side yards | Preserves two coordinated side-yard requirements rather than collapsing them into one value | Retrievable as embedded approved-v2 behavior |

## Use and approval capabilities

### Single-family dwelling use classification

The system may report the base permission category for a single-family dwelling in a supported zone. “Permitted by right” must never be translated into “no approvals required.” Use classification and approval requirements remain separate outputs.

The current capability does not evaluate ADUs, JADUs, SB 9 eligibility, home occupations, or other residential and accessory uses.

### Two-family dwelling use classification

The expansion keeps two-family as a distinct legal-use capability and `two_family_primary_structure` as a distinct structure identity. Its ordinary dimensional analysis uses the `multifamily` workflow family; this reuse must not erase its separate use or structure identity.

R1's Chapter 18.24 two-home pathway is not an ordinary two-family profile. It can involve attached or detached homes and branches on eligibility, configuration, existing improvements, and proposal facts. The product may list that permission pathway, but its dimensional analysis remains `not evaluated` until those inputs and rules are implemented.

### Multifamily dwelling use classification

The expansion may report the source-table permission status for a multifamily dwelling in a target residential zone. A source-table `not_listed` result means only that the use is not listed in the controlling base table; it must not be presented as a prohibition or as a complete entitlement conclusion.

### Zoning Clearance

The system may disclose that Zoning Clearance applies to construction associated with the supported permitted use. It does not yet evaluate an application package or determine whether a particular scope of work is exempt.

### Architectural Review

The system may disclose the base Architectural Review requirement and note that specified projects can require a Development Review Hearing. It does not yet classify a proposal against every hearing trigger.

## Dimensional-standard capabilities

### Maximum primary-structure height

The system may retrieve the base maximum height for a primary structure and disclose that measurement rules and allowed appurtenance exceptions exist. It does not yet measure a proposed building, determine grade, classify roof form, or evaluate rooftop elements.

### Maximum stories

The system may retrieve the base maximum number of stories. It does not yet determine whether a proposed level, basement, attic, or half-story counts as a story under the applicable code.

### Maximum structure coverage

The system may retrieve the base maximum coverage percentage and explain that coverage can include structures beyond the primary dwelling. It does not yet calculate existing coverage, remaining buildable area, or the treatment of every site feature.

## Setback capabilities

All currently supported setbacks are **base-zone requirements**, not computed building envelopes. The system may retrieve the applicable minimums and disclose known unevaluated exception families. It does not yet derive setback lines from parcel geometry or decide which exceptions alter a specific project.

### Front setback

The supported capability includes the base front setback and a different upper-story requirement where the code supplies one. Front-setback averaging is not currently evaluated.

### Rear setback

The supported capability includes the base rear setback. Alley credit, encroachments, accessory-structure standards, and legal nonconformities are not currently evaluated.

### Interior-side setback

The supported capability includes a base interior-side requirement and a different upper-story requirement where applicable. It can preserve unequal paired side yards when the code requires two coordinated values.

Narrow historical parcel exceptions, encroachments, and legal nonconformities are not currently evaluated.

### Street-side setback

This is the setback from the additional street frontage of a corner lot. Santa Clara refers to it as the corner-side setback. The supported capability includes a base requirement and a different upper-story requirement where applicable.

Determining corner orientation, street measurement lines, landscaping requirements, and permitted encroachments remains outside the current evaluator.

### Story-based setback adjustments

The supported scope recognizes that an upper story can require a greater total setback than the base building level. This is commonly described as a stepback. The current scope supports story-triggered differences that state an absolute minimum total setback.

Height-triggered stepbacks and rules requiring an additional distance rather than a total minimum are not yet supported operationally. Schema v2 can represent them, but no approved Santa Clara data or deterministic evaluator uses those shapes.

### Paired side-yard requirements

The supported scope preserves unequal paired interior-side requirements as a coordinated pair. The application must not average them or replace them with one symmetric value. Assigning the paired requirements to physical sides of a proposed design is not yet evaluated.

## Supported regulatory-data behaviors

These are cross-cutting platform capabilities rather than individual zoning regulations:

- Versioned rulesets and source-document identity
- Exact citations for consequential rule records
- Validation and approval status
- Applicability by jurisdiction, zone, structure type, and relevant site context
- Explicit conditions and unevaluated exception-family warnings
- Preservation of conflicting source assertions
- Documented project resolutions that remain distinct from official government corrections
- Controlled `not evaluated` and `review required` outcomes
- Explicit `no maximum listed`, `FAA-controlled`, and `plan-dependent` source dispositions without invented numeric substitutes
- Separation of legal-use permission, workflow family, primary-structure identity, ordinary analysis profiles, and special pathways
- Partial-candidate validation that remains distinct from complete runtime eligibility

## Identified but not currently supported

| Capability | Status or boundary |
|---|---|
| Height-triggered setback stepbacks | Representable in schema v2; no approved rule data or evaluator exists |
| Additional-distance setback stepbacks | Representable in schema v2; current approved data only recognizes absolute total minimums |
| Front-setback averaging | Source provision identified; required neighboring-development facts and evaluator are absent |
| Setback encroachments and projections | Source provisions identified; proposal-feature evaluation is absent |
| Narrow historical parcel exceptions | Source provision identified; qualifying parcel facts and evaluator are absent |
| Alley credit toward rear setback | Source provision identified; alley geometry and evaluator are absent |
| Official plan lines and right-of-way measurement | Required data layers and measurement logic are absent |
| Legal nonconforming structures | Source provisions identified; legal-status facts and evaluator are absent |
| Accessory structures | Deferred from the initial primary-structure scope |
| ADUs and JADUs | Deferred; local and state-law interaction is not encoded |
| R1 Chapter 18.24 two-home dimensional analysis | Permission pathway is cataloged; eligibility, configuration, and branch-specific dimensional evaluation remain `not evaluated` |
| SB 9 project evaluation beyond the source-verified local pathway | Deferred; state-law eligibility and override analysis are not encoded |
| Density and density bonus | Deferred; project and affordability inputs are not encoded |
| Minimum parcel area and frontage | Values identified but parcel-creation evaluation is deferred |
| Driveway approach length | Value identified but proposal-specific applicability is deferred |
| Daylight plane | Geometry and applicability interpretation are deferred |
| Parking | Not researched or encoded for this selected residential phase |
| Historic, specific-plan, airport, and other overlays | GIS and regulatory evaluation are deferred |
| Proposal-specific compliance | No project geometry or detailed proposal evaluator exists |

An item in this table must not be described as prohibited, irrelevant, or evaluated. The correct result is `not evaluated` until its capability is implemented and validated.

## Adding a regulation family

A new capability should move through this sequence:

1. Determine whether an existing shared capability is an exact semantic fit.
2. If no exact fit exists, classify the proposal as a new shared capability or a controlled jurisdiction extension and document that decision.
3. Define its meaning and boundaries in this catalog or a future jurisdiction-extension catalog governed by it.
4. Verify the controlling provisions, definitions, exceptions, and amendment status.
5. Define and validate its machine-readable representation.
6. Add approved jurisdiction-specific rule data with provenance.
7. Implement deterministic retrieval or evaluation and explicit failure states.
8. Add positive, negative, ambiguity, unknown-capability, and repeatability tests.
9. Expose it in the interface only with its sources and limitations.

Cataloging a capability does not by itself authorize runtime use. It becomes operational only after its rules and deterministic behavior pass their applicable gates.
