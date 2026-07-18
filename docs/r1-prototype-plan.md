# Santa Clara R1 Zoning Prototype Plan

**Status:** Initial research and planning

**Last updated:** July 16, 2026

**Prototype scope:** Santa Clara R1-6L and R1-8L single-family residential zones

## 1. Purpose

Build a small, end-to-end prototype that accepts a Santa Clara street address and returns a limited set of applicable R1 development standards.

Although the initial result will be deliberately narrow, the prototype must exercise the complete product pipeline:

1. Normalize an entered address.
2. Match the address to the City's GIS address data.
3. Locate the corresponding parcel and APN.
4. Determine the parcel's current zoning designation.
5. Retrieve approved, structured regulations for that zone.
6. Produce a deterministic result with source citations and version information.
7. Present the result in a simple interface.

This is a technical feasibility prototype, not an authoritative planning determination or legal opinion.

## 2. Guiding Principles

### Deterministic runtime

Given the same normalized address, GIS snapshot, approved ruleset, assumptions, and evaluation-engine version, the prototype must return the same result.

AI may assist with research and candidate rule extraction, but AI-generated interpretations do not become authoritative application data until they are checked against the source and approved.

### Parcel-centered analysis

The address is the entry point; the parcel is the unit of analysis. The intended lookup sequence is:

```text
address -> address point -> parcel/APN -> zoning -> approved rules -> result
```

### Evidence with every result

Each regulatory value should retain its source document, section or table, source version, and validation status. GIS-derived facts should retain the source service/layer and snapshot date.

### Explicit limits

The prototype must distinguish between:

- evaluated and supported;
- outside the prototype's current scope;
- unresolved because data is missing or conflicting; and
- requiring staff interpretation.

## 3. Initial Functional Scope

### Included

- Santa Clara addresses found in the City's address-point dataset.
- Parcel and APN identification.
- Current zoning lookup.
- R1-6L and R1-8L base-zone recognition.
- Maximum primary-structure height.
- Maximum stories.
- Maximum structure coverage.
- Basic front, rear, interior-side, and corner-side setbacks.
- Different first- and second-story setbacks where required.
- Source citations and data/ruleset version information.
- A simple retrieval-oriented result view.

### Explicitly deferred

- ADUs and JADUs.
- SB 9 two-unit development and urban lot splits.
- Accessory structures and garages as independent analyses.
- Parking requirements.
- Detailed architectural or design-review requirements.
- Historic properties and historic combining districts.
- Specific plans, legacy zoning, and planned-development entitlements.
- Airport, flood, environmental, and other overlays.
- Easements and private restrictions.
- Variances, legal nonconformities, and prior approvals.
- State-law overrides and density bonuses.
- Proposal-specific plan compliance.
- Parcels outside R1-6L and R1-8L.

Deferred topics should appear as **not evaluated**, not be silently omitted or treated as inapplicable.

## 4. Authoritative Sources

### 4.1 Zoning code

The Google Drive project folder contains `SantaClaraZoningCode.pdf`, titled **Santa Clara Zoning Code, Title 18 — July 2025**.

Research on July 14, 2026 found that its version, date, table of contents, and R1 provisions match the latest consolidated code currently posted by the City:

- [City of Santa Clara — Zoning Code Updates](https://www.santaclaraca.gov/our-city/departments-a-f/community-development/planning-division/zoning/zoning-code-update)
- [City of Santa Clara — Zoning](https://www.santaclaraca.gov/our-city/departments-a-f/community-development/planning-division/zoning)

The match has not been verified byte-for-byte because the City server rejected automated downloading of the official PDF.

The July 2025 PDF must not be treated as a complete current-law snapshot by itself. A post-publication audit completed on July 16, 2026 identified two adopted amendments not yet incorporated into the City's consolidated code:

- Ordinance 2085 adds citywide objective design standards for multifamily and residential mixed-use projects.
- Ordinance 2086 adds El Camino Real Corridor regulations.

Neither ordinance changes the selected numeric R1 standards in Table 2-3. Both ordinances purport to add different material as Chapter 18.27, and eCode360 lists both as adopted but not yet incorporated; the prototype must not guess how that chapter-number collision will be reconciled.

Zoning Code Cleanup #3 was also reviewed. As of the audit cutoff, the official matter remained `Agenda Ready` with no passed or enactment date, and its July 14 Council event item had no recorded action or result. Its proposed tables preserve the selected R1 numeric values, but the final text must be rechecked if adopted.

The detailed evidence, source links, status treatment, and recheck triggers are in [Title 18 Amendment Audit](title18-amendment-audit.md). The immutable local source snapshot and machine-readable manifest are stored at:

```text
data/raw/2026-07-16/santa_clara_zoning_code/
```

### 4.2 GIS

The public MapSantaClara system exposes queryable ArcGIS REST services. The prototype should query or snapshot the underlying data rather than scrape the interactive map.

Verified endpoints:

| Purpose | REST endpoint |
|---|---|
| Service catalog | [ArcGIS REST catalog](https://map.santaclaraca.gov/maps/rest/services?f=pjson) |
| Address points | [CSCAddress_Active, layer 0](https://map.santaclaraca.gov/maps/rest/services/OPENDATA/CSCAddress_Active/MapServer/0) |
| Parcels | [RegionalBaseOpenData, layer 7](https://map.santaclaraca.gov/maps/rest/services/OPENDATA/RegionalBaseOpenData/MapServer/7) |
| Current zoning open data | [RegionalZoningOpenData, layer 0](https://map.santaclaraca.gov/maps/rest/services/OPENDATA/RegionalZoningOpenData/MapServer/0) |
| City user interface | [MapSantaClara](https://www.santaclaraca.gov/our-city/departments-a-f/community-development/mapsantaclara) |

The correct service catalog path is `/maps/rest/services`. The previously considered `/maps/arcgis/rest/services` path returned HTTP 404 during verification.

Useful confirmed fields include:

**Address points**

- `CSCADDR`
- `CSCSTREET`
- `ADDRNUM`
- `ADDRUNIT`
- `ADDRCITY`
- `ADDRZIP5`

**Parcels**

- `APN`
- `PARCITY`
- `ZONGDSGN`
- `GPLANCRT`
- `SPPLAN`
- `ACREAGE`
- `YEARBUILT`

**Current zoning layer**

- `ZONGDSGN`
- `SPPLAN`
- `HistoricParcelType`
- `ZoningURL`
- `GenPlanURL`
- `FEMAZONE_NOTE`

On July 14, 2026, live read-only queries successfully completed this chain for 1500 Warburton Avenue:

```text
address match
-> coordinate
-> parcel intersection
-> APN 224-25-074
-> parcel zoning PQP
-> current zoning PQP
```

This non-R1 example confirms that the required address-to-zoning path is technically available and that parcel and current-zoning attributes can be cross-checked.

### 4.3 Downloaded R1 GIS snapshot

A complete filtered snapshot was downloaded on July 14, 2026 to:

```text
data/raw/2026-07-14/santa_clara_r1_gis/
```

The snapshot contains:

- 15,757 R1-6L features from the parcel layer;
- 436 R1-8L features from the parcel layer;
- the corresponding 16,193 features from the current-zoning layer;
- source layer metadata and returned object-ID lists;
- 100-feature raw GeoJSON batches;
- consolidated `parcels_r1.geojson` and `current_zoning_r1.geojson` files; and
- a validation and checksum manifest.

For both layers, the number of downloaded features and unique downloaded object IDs exactly matched the source object-ID response. The consolidated files use EPSG:4326. No database, spatial join, or zoning-rule evaluation was created during this download step.

### 4.4 Downloaded address-point snapshot

A complete citywide address-point snapshot was downloaded on July 16, 2026 to:

```text
data/raw/2026-07-16/santa_clara_address_points/
```

All 67,243 source object IDs produced 67,243 unique point features. Core address fields have no missing values, while 45 full-address values appear more than once; lookup logic must preserve multiple exact matches instead of silently choosing a record. The citywide source is retained because address resolution precedes parcel and zoning classification.

## 5. Verified R1 Rule Inputs

The following values were transcribed from Chapter 18.10, Section 18.10.030, Table 2-3 of the July 2025 consolidated code. The post-publication amendment audit found no adopted change to these values. Rule-level verification is complete, and the first approved machine-readable version is stored at `rulesets/santa_clara/r1/2026-07-16/ruleset.json`.

| Standard | R1-6L | R1-8L | Notes |
|---|---:|---:|---|
| Minimum newly created parcel area | 6,000 sq ft | 8,000 sq ft | A subdivision/parcel-creation standard; not an automatic determination that a smaller existing parcel is unbuildable. |
| Minimum street frontage | 60 ft | 70 ft | Primarily relevant to parcel creation; initially informational or deferred. |
| Maximum structure coverage | 40% | 40% | Requires a confirmed definition of included structures/areas before calculated use. |
| Front setback, first story | 20 ft | 20 ft | Primary structure. |
| Front setback, second story | 25 ft | 25 ft | Primary structure stepback. |
| Interior side setback, first story | 5 ft | 6 ft and 9 ft | R1-8L uses unequal paired side-yard requirements. |
| Interior side setback, second story | 10 ft | 11 ft and 14 ft | R1-8L uses unequal paired side-yard requirements. |
| Corner-side setback, first story | 10 ft | 15 ft | Table 2-3 says 10 ft, but the prototype uses the specific written 15-foot provision in Section 18.10.040(B)(1), supported by the more-restrictive rule in Section 18.04.020(G). Preserve both source assertions. |
| Corner-side setback, second story | 15 ft | 15 ft | Applies to corner lots. |
| Rear setback | 20 ft | 20 ft | Listed for single- and multi-story primary structures. |
| Driveway approach setback | 20 ft | 20 ft | Candidate for deferral from the first displayed result. |
| Maximum primary-structure height | 25 ft | 25 ft | Base-zone value. |
| Maximum stories | 2 | 2 | Base-zone value. |
| Density range | 0.1–10 du/ac | 0.1–10 du/ac | Not sufficient by itself to evaluate ADUs, SB 9, or a particular proposal. |

City planning FAQs independently state a 25-foot maximum height, two-story maximum, and 40 percent maximum building coverage for single-family development:

- [City of Santa Clara — Planning FAQs](https://www.santaclaraca.gov/our-city/departments-a-f/community-development/planning-division/faqs)

The detailed source trace, applicability findings, exceptions, cross-references, deferrals, and ruleset gate are in [R1 Rule-Level Verification](r1-rule-verification.md).

Key conclusions:

- Height, stories, coverage, and most setback numbers are verified **base-zone values**, not final parcel-specific requirements.
- A permitted-by-right single-family dwelling still requires Zoning Clearance and may require Architectural Review and a public hearing.
- Setback averaging, projections, official plan lines, alley credit, narrow historical parcels, and legal nonconformities can change parcel-specific application.
- The R1-8L first-story corner-side setback contains a 10-foot/15-foot source conflict. The prototype resolves it to 15 feet while retaining the rejected 10-foot assertion and marking the decision as pending official clarification.
- Parcel-creation standards, density, driveway approach, daylight plane, and proposal-level envelope calculations remain deferred from the first ruleset.

### Regulatory conflict handling

Future multi-jurisdiction automation must treat regulatory conflicts as structured data rather than extraction noise. The workflow should retain every conflicting assertion, evaluate authority, specificity, effective date, amendment history, and explicit conflict rules, and then either record a deterministic resolution or return `review required`.

A resolution record should preserve the selected value, all source values, citations, rationale, reviewer or decision source, date, status, and re-review trigger. A project resolution must never be represented as an official correction by the source government.

## 6. Proposed Lookup Pipeline

The first local implementation is in `santa_clara_zoning/` with a command at `scripts/lookup_r1_zone.py`. It uses exact controlled address matching, checksum-verified immutable GeoJSON snapshots, bounding-box-prefiltered point-in-polygon checks, and explicit ambiguity or review outcomes. It does not use fuzzy matching, a database, the live City API, or the regulatory ruleset yet.

Because the current parcel and zoning snapshots are filtered to R1-6L and R1-8L, an address with no polygon match is labeled outside the supported R1 snapshot. The implementation does not infer that address's exact non-R1 designation. The current spatial check uses the address point and does not calculate split-zone parcel areas.

### Step 1: Normalize the address

Convert user input into controlled fields such as:

```json
{
  "house_number": "1279",
  "street_name": "Las Palmas",
  "street_type": "Drive",
  "unit": null,
  "city": "Santa Clara",
  "state": "CA"
}
```

The first implementation can use deterministic normalization and exact/controlled matching. Fuzzy matching and AI parsing can be considered later.

### Step 2: Match the city address point

Query the local snapshot or live address-point layer. Handle:

- no match;
- one unambiguous match;
- multiple units or candidates; and
- a normalized address that differs from the user's display form.

Return the source object ID and coordinate with the match.

### Step 3: Locate the parcel

Use a point-in-polygon spatial query to find the parcel containing the address point. Return at minimum:

- APN;
- parcel geometry;
- reported acreage or area;
- parcel zoning attribute; and
- source feature/object ID.

Do not assume that an address record directly supplies a trustworthy APN.

### Step 4: Determine current zoning

Intersect the point or parcel with the current zoning open-data layer. Cross-check its `ZONGDSGN` against the parcel layer's `ZONGDSGN`.

Possible outcomes:

- values agree;
- values conflict;
- multiple zoning features intersect the parcel; or
- no zoning feature is found.

Only an unambiguous `R1-6L` or `R1-8L` match should proceed to a normal prototype result. Other outcomes should return a controlled unsupported or review-required status.

### Step 5: Retrieve the approved zone rules

Use the confirmed zone code as a deterministic key into a versioned development-standards table. Do not use an LLM to select or generate numeric standards at runtime.

### Step 6: Produce a structured result

Create a machine-readable evaluation result before rendering UI. The first result is a base-zone standards retrieval, not a complete project feasibility determination.

### Step 7: Render the result

The first UI may be plain. It should prioritize correctness and traceability over elaborate design.

### Pre-Block 6 ruleset v2 gate

Deterministic standards retrieval is paused until the initial ruleset is redesigned for long-term growth. The supported capability scope is maintained in [Supported Regulations Catalog](regulations/supported-regulations.md). That catalog explains regulation meanings and boundaries without prescribing schema fields or duplicating jurisdiction-specific values.

The approved machine-readable representation and representative zone-first examples are maintained in the [Ruleset v2 Authoring Guide](regulations/ruleset-authoring-guide.md) and implemented structurally by `rulesets/schema/ruleset-v2.schema.json`.

Before Block 6 begins, the project must:

1. Establish the supported-regulations catalog.
2. Redesign the canonical hierarchy around zones and their regulations.
3. Give each zone its own rule identities even when current values match.
4. Model setbacks as base requirements plus supported vertical adjustments and paired-yard configurations.
5. Keep shared sources, citations, definitions, exceptions, and conflicts referenceable without duplicating their content in every zone.
6. Migrate the approved R1-6L and R1-8L data into the v2 representation without losing provenance.
7. Expand schema, invariant, migration, and regression validation for the v2 model.

The schema representation was deliberately left undecided during catalog step 1. Steps 2 through 7 are complete: the approved contract is structurally implemented, the reviewed candidate contains the migrated R1 data plus a complete v1 crosswalk, and expanded domain and mutation validation passes. Project-owner approval on July 17, 2026 produced separate immutable version `2026-07-17.2`, which is the canonical runtime-eligible regulatory source for Block 6.

## 7. Preliminary Data Model

The exact database technology remains undecided. The logical model should include these concepts even if the first prototype stores some of them in GeoPackage, SQLite, JSON, or another lightweight format.

The initial regulatory implementation is a normalized, versioned JSON ruleset with an executable Draft 2020-12 JSON Schema validator and additional domain-invariant checks. A database remains deferred until the lookup pipeline establishes concrete access patterns.

### `addresses`

- source object ID
- normalized address fields
- display address
- point geometry
- source layer
- snapshot version

### `parcels`

- source object ID
- APN
- parcel attributes
- polygon geometry
- source layer
- snapshot version

### `zoning_features`

- source object ID
- zone code
- relevant planning attributes
- polygon geometry
- source layer
- snapshot version

### `source_documents`

- document ID
- title
- jurisdiction
- version/date
- effective date
- source URL or local artifact
- content hash where available
- verification status

### `ruleset_versions`

- ruleset ID/version
- source-document set
- approval date
- reviewer/validation status
- notes

### `development_standards`

- rule ID
- ruleset version
- zone code
- standard type
- value
- unit
- story or location applicability
- conditions and exceptions
- source section/table
- validation status

## 8. Block 6 Retrieval Contract

The project owner approved this direction on July 17, 2026, and Block 6 passed its acceptance gate on July 18, 2026. Contract version `1.0.0` describes the shape and meaning of the combined lookup-and-regulations result; it is not an evaluation-engine version. Ruleset version `2026-07-17.2` independently identifies the approved regulatory data. A separate engine version is deferred until the prototype performs meaningful proposal evaluation or rule calculations.

Block 6 has two deterministic boundaries:

1. A pure zone retriever accepts an exact, case-sensitive supported zone key and an approved, runtime-eligible ruleset; it does not trim, normalize, or guess aliases.
2. An address orchestrator runs the existing Block 5 lookup and calls the pure retriever only after an unambiguous `r1_zone_found` result.

Conceptually:

```python
retrieve_zone_standards(zone_code, approved_ruleset)
analyze_address(address)
```

The successful combined result will follow this contract direction:

```json
{
  "contract_version": "1.0.0",
  "status": "r1_standards_found",
  "reason_code": "approved_r1_standards_retrieved",
  "query": {
    "entered_address": "636 Barto Street",
    "normalized_address": "636 BARTO ST"
  },
  "address": {
    "display_address": "636 BARTO ST"
  },
  "parcel": {
    "apn": "293-16-045",
    "designation": "R1-6L"
  },
  "zoning": {
    "designation": "R1-6L",
    "parcel_attribute_agrees": true
  },
  "regulatory_context": {
    "jurisdiction": {
      "name": "City of Santa Clara",
      "slug": "santa_clara",
      "state": "CA",
      "country": "US"
    },
    "ruleset_id": "santa-clara-r1-base-zone",
    "ruleset_version": "2026-07-17.2",
    "schema_version": "2.0.0",
    "approved_on": "2026-07-17",
    "verified_through": "2026-07-16",
    "scope": {
      "description": "Selected base-zone rules for single-family primary structures in R1-6L and R1-8L.",
      "structure_types": ["single_family_primary_structure"],
      "result_kind": "base_zone_standards_retrieval"
    }
  },
  "regulations": {
    "use.single_family_dwelling": {},
    "approval.zoning_clearance": {},
    "approval.architectural_review": {},
    "standard.maximum_primary_structure_height": {},
    "standard.maximum_stories": {},
    "standard.maximum_structure_coverage": {},
    "setback.front": {},
    "setback.interior_side": {},
    "setback.street_side": {},
    "setback.rear": {}
  },
  "shared_references": {
    "source_documents": {},
    "citations": {},
    "exception_families": {},
    "conflicts": {}
  },
  "not_evaluated": [
    "<topics copied from the approved ruleset>"
  ],
  "disclaimer": "This prototype reports selected base-zone standards and is not a complete entitlement analysis or legal or planning determination.",
  "versions": {
    "address_snapshot": "2026-07-16",
    "r1_gis_snapshot": "2026-07-14",
    "ruleset": "2026-07-17.2"
  },
  "sources": {
    "address_layer": "...",
    "parcel_layer": "...",
    "zoning_layer": "..."
  }
}
```

Empty rule and shared-reference objects in the example are structural placeholders; the real result contains the complete selected records. The `not_evaluated` array is copied from the approved ruleset rather than maintained independently in this contract document.

The actual `regulations` object preserves every approved zone-owned rule rather than flattening it into presentation-only numbers. This retains rule IDs, applicability, paired side yards, base setbacks, story-based adjustments, conditions, validation states, source references, and exception-family references. The street-side regulation is returned with `lot_context: corner`; retrieval does not determine whether the selected parcel is a corner lot.

`shared_references` contains the transitive provenance closure for the selected zone: citations referenced directly by requirements, citations referenced by selected exception families and conflict assertions, the selected exception and conflict records, and the source documents referenced by those citations. The result is therefore self-contained without copying unrelated ruleset content.

The implemented `R1StandardsPipeline` loads the validated GIS lookup and approved ruleset once. `analyze_address()` adds contract version `1.0.0` to every outcome and calls exact-zone retrieval only after `r1_zone_found`. A successful pipeline result replaces that intermediate status with `r1_standards_found`, attaches the complete regulatory result, and adds the ruleset version beside the GIS snapshot versions.

The orchestrator preserves existing Block 5 outcomes when address or spatial lookup does not produce one supported zone: `address_not_found`, `address_ambiguous`, `outside_supported_r1_snapshot`, or `review_required` with its existing reason code. Those results receive no regulations or ruleset version. Regulatory loading and retrieval fail closed for an unapproved ruleset, unsupported zone, missing required capability, invalid reference, inconsistent component result, or other integrity error. The pipeline never reports partial success or recasts a system integrity failure as parcel-specific planning review.

This contract retrieves and packages approved base-zone rules. It does not determine corner-lot facts, choose a proposed story count, calculate a building envelope or structure coverage, compare a proposal with a standard, apply state-law overrides or overlays, or produce final UI formatting.

## 9. Block 7 Deterministic Presentation Plan

### Objective

Block 7 will turn the complete Block 6 result into a concise, planner-friendly presentation without changing, recomputing, or expanding the authoritative content. It will introduce a pure deterministic presenter between `R1StandardsPipeline` and the first user interface.

The presenter answers the narrow question:

> What does the supported base R1 zoning allow, what approvals and selected standards apply, and what has not been evaluated?

It does not answer whether a particular design is compliant or whether development is ultimately feasible.

### Current overview policy

The approved ruleset does not contain a dedicated narrative description for R1-6L or R1-8L. For this iteration, the overview will therefore be brief and assembled deterministically from existing approved fields:

- jurisdiction;
- exact zone designation;
- supported structure scope;
- single-family use status;
- approval requirements; and
- the approved scope disclaimer.

A representative overview is:

> This property is zoned R1-6L. Under the supported base-zone rules, a single-family dwelling is permitted by right. Zoning Clearance and Architectural Review are required. This prototype reports selected base-zone standards only.

The presenter must not infer or explain the meaning of the `6L` or `8L` suffixes. Richer descriptions are deferred until source-backed, reviewed zone profiles exist in versioned regulatory data. A later system may compose those profiles with parcel facts, overlays, state-law effects, and proposal evaluation, but runtime AI will not invent the authoritative overview.

### Architecture boundary

```text
R1StandardsPipeline result contract 1.0.0
                 ↓
Pure deterministic presenter
                 ↓
Versioned UI-neutral presentation model
                 ↓
Initial CLI or local web interface
```

The presenter will:

- accept one complete Block 6 result;
- preserve the original result status and reason code;
- map typed regulatory records into display components;
- retain rule IDs and source-reference IDs behind every consequential item;
- carry conditions, exceptions, conflicts, limitations, and versions forward; and
- return a new object without mutating the pipeline result.

It will not contain zone-specific numeric constants, legal conclusions, spatial calculations, or fallback guesses. A candidate presentation-contract version `1.0.0` will be reviewed in Block 7.1 independently of the Block 6 result-contract version.

### Candidate presentation model

The UI-neutral model should follow this direction:

```json
{
  "presentation_contract_version": "1.0.0",
  "kind": "success",
  "source_status": "r1_standards_found",
  "property": {
    "display_address": "<matched address>",
    "apn": "<APN>",
    "zone": "<exact zone>",
    "scope_label": "R1 base-zone prototype"
  },
  "overview": {
    "headline": "<base-zoning conclusion>",
    "summary": "<brief deterministic summary>",
    "disclaimer": "<approved ruleset disclaimer>"
  },
  "use_permissions": [],
  "approvals": [],
  "key_standards": [],
  "setbacks": [],
  "warnings": [],
  "not_evaluated": [],
  "sources": [],
  "versions": {}
}
```

This is a planning direction rather than an approved schema. Block 7.1 must define required fields, controlled display statuses, ordering, source-link behavior, and failure-result shapes before implementation.

### Deterministic mapping rules

| Authoritative input | Presentation output |
|---|---|
| Address, parcel, and zoning records | Property header with matched address, APN, exact zone, and scope label |
| `use.single_family_dwelling` status | Primary-use card with controlled permission wording |
| Approval status rules | Separate required-approval rows; never merged into use permission |
| `maximum_quantity` rules | Height, stories, and structure-coverage metric cards with units and base-value qualifiers |
| Scalar setback | Base distance plus any typed story adjustment |
| Paired setback | Coordinated smaller/larger values; never averaged or assigned to physical sides |
| `lot_context: corner` | Conditional “applies only to a corner lot” label; never a parcel classification |
| Rule conditions | Concise notes attached to the affected display item |
| Exception-family references | “Additional rules may apply” warnings with inspectable detail |
| Conflict record | Prominent conflict notice showing selected value, competing assertions, status, and rationale |
| Citations and source documents | Human-readable source receipts using title, version, and locator |
| `not_evaluated` and disclaimer | Dedicated limitations section and persistent scope notice |
| Contract and data versions | Collapsible methodology or data-version details |

### Result-page hierarchy

The successful result should present, in order:

1. **Property identity:** matched address, APN, exact zoning designation, and prototype scope.
2. **Brief overview:** the supported base use, approval summary, and scope limitation.
3. **What base zoning permits:** single-family dwelling permission, using the exact controlled status.
4. **Required approvals:** Zoning Clearance and Architectural Review as distinct requirements; a Development Review Hearing remains conditional where the source condition says so.
5. **Key standards:** maximum primary-structure height, maximum stories, and maximum structure coverage.
6. **Setbacks:** front, interior-side, street-side, and rear requirements, including typed story adjustments and paired values.
7. **Warnings and conflicts:** source conflicts, proposal-dependent assignments, corner-only applicability, and other consequential conditions.
8. **Not evaluated:** deferred subjects that must not be mistaken for prohibitions or completed checks.
9. **Sources and versions:** inspectable code locators, document versions, GIS snapshot dates, ruleset version, and result-contract version.

### Wording requirements

- Say **“permitted by right under the supported base zoning,”** not “approval free” or “definitely buildable.”
- Keep use permission separate from Zoning Clearance, Architectural Review, and conditional hearing requirements.
- Label dimensional numbers as selected **base-zone** standards rather than parcel-specific computed limits.
- Describe 40 percent as structure coverage, not floor-area ratio, maximum floor area, or remaining capacity.
- Describe story-triggered setback values as total minimums, not additional distances.
- Describe paired side yards as coordinated values whose physical assignment is proposal-dependent.
- Show the street-side rule conditionally because corner-lot status is not currently determined.
- Preserve the R1-8L 10-foot/15-foot source conflict and project resolution without presenting it as an official City correction.
- Use **“not evaluated”** for unsupported subjects; do not translate them into “not allowed” or “not applicable.”
- Always retain the approved disclaimer that the result is not a complete entitlement or legal/planning determination.

### Failure and integrity presentation

| Pipeline outcome | Presentation behavior |
|---|---|
| `address_not_found` | Explain that no exact local address match was found and invite corrected input |
| `address_ambiguous` | Show candidate records without selecting one |
| `outside_supported_r1_snapshot` | Explain that the address was located but its exact non-R1 zoning was not determined by this prototype |
| `review_required` | Show the pipeline reason and available parcel/zoning evidence without attaching regulations |
| Ruleset or pipeline integrity exception | Show a system/data validation error, not a parcel-specific planning conclusion |

Suggested unsupported-zone message:

> This parcel was located successfully, but its zoning is outside the current R1-6L/R1-8L prototype. No regulations were attached.

### Block 7 implementation sequence

| Substep | Intended result |
|---|---|
| 7.1 Approve presentation contract and wording | Fix the UI-neutral success/failure shapes, controlled labels, ordering, provenance links, and presentation version |
| 7.2 Implement the pure presenter | Convert Block 6 results into independent UI-ready objects without zone-specific values or runtime AI |
| 7.3 Validate presenter behavior | Test both R1 zones, all controlled failures, conflicts, conditional applicability, provenance, mutation isolation, and repeatability |
| 7.4 Build the initial interface | Add address input and a simple result view using the approved presentation model; choose the lightest suitable local UI surface before coding |
| 7.5 Validate and close Block 7 | Confirm readable output, source visibility, limitation wording, failure states, deterministic rendering, setup instructions, and regression coverage |

### Block 7 validation matrix

- Barto renders the exact R1-6L use, approvals, metrics, scalar setbacks, story adjustments, limitations, and citations.
- Brookside renders paired R1-8L interior yards and the full street-side conflict warning.
- Street-side setbacks are labeled corner-only for both zones without classifying either test parcel as a corner lot.
- Warburton, Los Padres, unmatched, and synthetic review-required results render controlled failure views with no regulatory cards.
- Every displayed consequential value retains rule and citation references.
- Presenter output cannot mutate the Block 6 result and is byte-equivalent for identical inputs.
- Tests fail if the presenter hard-codes a zone value, drops a supported regulation, hides a conflict, or converts an unevaluated subject into a conclusion.

### Block 7 exit conditions

Block 7 is complete when:

1. a versioned presentation contract is approved;
2. a pure deterministic presenter maps every supported rule family and controlled outcome;
3. a successful view clearly presents property identity, overview, use, approvals, standards, setbacks, warnings, limitations, sources, and versions;
4. conditional and conflicting rules remain visibly qualified;
5. no displayed regulatory number is maintained separately from the Block 6 result;
6. unsupported and integrity outcomes cannot appear as successful planning conclusions;
7. the initial interface accepts an address and renders the approved presentation model; and
8. focused and full-suite validation pass with reproducible setup instructions.

## 10. Validation Strategy

At minimum, test:

- one confirmed R1-6L address;
- one confirmed R1-8L address;
- one non-R1 address as a negative control;
- an address with a unit number;
- an invalid or unmatched address;
- an ambiguous or incomplete address;
- a parcel/zoning mismatch if one can be identified;
- preservation of the street-side rule's corner-only applicability without claiming that the parcel has been classified as a corner lot; and
- repeat runs using the same snapshot and ruleset.

Initial local-snapshot fixtures:

- 636 Barto Street — APN 293-16-045 and R1-6L.
- 108 Brookside Avenue — APN 303-22-022 and R1-8L.
- 1500 Warburton Avenue — verified non-R1 negative control (PQP).
- 1577 Pomeroy Avenue 202 — unit-bearing record for parsing and matching.
- 324 Los Padres Boulevard — duplicated full-address value for ambiguity handling.
- 99999 No Such Street — unmatched-input fixture.

City staff reports are useful for test-case comparison but are not substitutes for the current GIS and zoning code.

## 11. Completion Criteria

The first prototype is complete when it can:

- accept a Santa Clara address;
- resolve it to a city address point and parcel;
- return the APN;
- determine and cross-check the current zoning designation;
- recognize R1-6L and R1-8L;
- retrieve the approved limited R1 standards deterministically;
- render a simple readable result;
- cite the governing code table;
- show source/ruleset versions;
- identify unsupported zones and error states cleanly; and
- reproduce the same output from the same versioned inputs.

## 12. Remaining Decisions After Block 6

- Block 7 presentation form: command-line renderer or small local web application.
- Application framework if a web interface is selected.
- How the result view groups permissions, approvals, dimensional standards, setbacks, sources, conflicts, and `not evaluated` topics.
- Whether and when to add authoritative corner-lot classification rather than displaying the street-side rule conditionally.
- When the direct immutable-snapshot lookup should be replaced by GeoPackage, DuckDB Spatial, PostGIS, or another indexed spatial store.
- Whether a later deployed version uses local snapshots, refreshed snapshots, live GIS services, or a controlled combination.

## 13. Likely Immediate Next Step

Review and approve Block 7.1's candidate presentation contract and wording rules. This step should fix the required success and failure fields, controlled labels, display order, provenance linkage, and presentation version before any presenter or interface code is written.

This document is the implementation-facing source of truth for the R1 prototype. The Google Doc remains the broader project-planning reference.
