# Santa Clara R1 Zoning Prototype Plan

**Status:** Initial research and planning

**Last updated:** July 14, 2026

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

The July 2025 PDF must not be treated as a complete current-law snapshot by itself. Later Title 18 amendment activity exists, including 2026 Objective Design Standards and Zoning Code Cleanup #3 materials:

- [Ordinance No. 2085 materials](https://santaclara.legistar.com/View.ashx?GUID=7E3FCE92-F615-4895-A3EE-D0B7FA2F2FC9&ID=15351662&M=F)
- [Zoning Code Cleanup #3 public notice](https://www.santaclaraca.gov/home/showpublisheddocument/89371)

The known Objective Design Standards addition concerns multifamily and residential mixed-use development and appears outside this R1 prototype. Cleanup #3 principally concerns other subjects, but its final adopted text must be checked before the R1 ruleset is declared authoritative.

The prototype should eventually maintain an amendment ledger containing:

- ordinance or resolution identifier;
- adoption and effective dates;
- affected Title 18 sections;
- whether the consolidated PDF includes the amendment;
- effect on the prototype ruleset; and
- verification status.

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

## 5. Candidate R1 Ruleset

The following values were transcribed from Chapter 18.10, Section 18.10.030, Table 2-3 of the July 2025 consolidated code. They are **candidate approved values** pending a final amendment audit and source review before implementation.

| Standard | R1-6L | R1-8L | Notes |
|---|---:|---:|---|
| Minimum newly created parcel area | 6,000 sq ft | 8,000 sq ft | A subdivision/parcel-creation standard; not an automatic determination that a smaller existing parcel is unbuildable. |
| Minimum street frontage | 60 ft | 70 ft | Primarily relevant to parcel creation; initially informational or deferred. |
| Maximum structure coverage | 40% | 40% | Requires a confirmed definition of included structures/areas before calculated use. |
| Front setback, first story | 20 ft | 20 ft | Primary structure. |
| Front setback, second story | 25 ft | 25 ft | Primary structure stepback. |
| Interior side setback, first story | 5 ft | 6 ft and 9 ft | R1-8L uses unequal paired side-yard requirements. |
| Interior side setback, second story | 10 ft | 11 ft and 14 ft | R1-8L uses unequal paired side-yard requirements. |
| Corner-side setback, first story | 10 ft | 10 ft | Applies to corner lots. |
| Corner-side setback, second story | 15 ft | 15 ft | Applies to corner lots. |
| Rear setback | 20 ft | 20 ft | Listed for single- and multi-story primary structures. |
| Driveway approach setback | 20 ft | 20 ft | Candidate for deferral from the first displayed result. |
| Maximum primary-structure height | 25 ft | 25 ft | Base-zone value. |
| Maximum stories | 2 | 2 | Base-zone value. |
| Density range | 0.1–10 du/ac | 0.1–10 du/ac | Not sufficient by itself to evaluate ADUs, SB 9, or a particular proposal. |

City planning FAQs independently state a 25-foot maximum height, two-story maximum, and 40 percent maximum building coverage for single-family development:

- [City of Santa Clara — Planning FAQs](https://www.santaclaraca.gov/our-city/departments-a-f/community-development/planning-division/faqs)

Table notes, definitions, exceptions, and other applicable sections must be retained. A numeric cell must not be implemented without its applicability conditions.

## 6. Proposed Lookup Pipeline

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

## 7. Preliminary Data Model

The exact database technology remains undecided. The logical model should include these concepts even if the first prototype stores some of them in GeoPackage, SQLite, JSON, or another lightweight format.

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

## 8. Preliminary Result Contract

Illustrative only; exact field names remain a pending implementation decision.

```json
{
  "query": {
    "entered_address": "1279 Las Palmas Drive",
    "normalized_address": "1279 LAS PALMAS DR, SANTA CLARA, CA"
  },
  "parcel": {
    "apn": "290-07-024",
    "lot_area_sqft": null,
    "source": "RegionalBaseOpenData/MapServer/7"
  },
  "zoning": {
    "designation": "R1-6L",
    "parcel_attribute_agrees": true,
    "source": "RegionalZoningOpenData/MapServer/0"
  },
  "base_zone_standards": {
    "max_height_ft": 25,
    "max_stories": 2,
    "max_structure_coverage_pct": 40,
    "front_setback_first_story_ft": 20,
    "front_setback_second_story_ft": 25,
    "interior_side_setback_first_story_ft": 5,
    "interior_side_setback_second_story_ft": 10,
    "rear_setback_ft": 20
  },
  "status": "base_zone_standards_found",
  "not_evaluated": [
    "ADU/JADU rules",
    "SB 9 eligibility",
    "historic review",
    "specific plans and overlays",
    "proposal-specific compliance"
  ],
  "sources": [
    {
      "document": "Santa Clara Zoning Code, Title 18",
      "version": "July 2025",
      "citation": "Section 18.10.030, Table 2-3"
    }
  ],
  "versions": {
    "gis_snapshot": null,
    "ruleset": null,
    "evaluation_engine": null
  }
}
```

## 9. Initial UI Content

The first result page should show:

1. Matched address.
2. APN and zoning designation.
3. A clear scope label: **R1 base-zone prototype**.
4. Height, stories, coverage, and setback values.
5. A citation for the standards.
6. GIS and ruleset version dates.
7. A prominent list of topics not evaluated.
8. Warnings for address ambiguity, conflicting zoning data, or unsupported zones.

Suggested unsupported-zone message:

> This parcel was located successfully, but its zoning designation is outside the current R1-6L/R1-8L prototype.

Suggested scope disclaimer:

> This prototype reports selected base-zone standards and does not constitute a complete entitlement or buildability determination.

## 10. Validation Strategy

At minimum, test:

- one confirmed R1-6L address;
- one confirmed R1-8L address;
- one non-R1 address as a negative control;
- an address with a unit number;
- an invalid or unmatched address;
- an ambiguous or incomplete address;
- a parcel/zoning mismatch if one can be identified;
- a corner lot to confirm side-yard presentation; and
- repeat runs using the same snapshot and ruleset.

Candidate public examples for later live confirmation:

- 1279 Las Palmas Drive — described in public City materials as R1-6L.
- 108 Brookside Avenue — described in public City materials as R1-8L.
- 1500 Warburton Avenue — verified non-R1 negative control (PQP).

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

## 12. Decisions Pending Before Implementation

- Prototype form: notebook, command-line script, or small web application.
- Application language and framework.
- Local spatial storage: GeoPackage/SQLite, DuckDB Spatial, PostGIS, or another option.
- Whether the first run uses live GIS services, a local snapshot, or both.
- Exact address-normalization strategy.
- Exact rule schema and result JSON contract.
- Which setback notes and exceptions are necessary for the first approved ruleset.
- Process for auditing post-July-2025 amendments.
- Initial test-address set and manually verified expected results.
- UI layout for the first retrieval view.
- Repository structure for raw data, canonical data, manifests, code, and tests.

## 13. Likely Immediate Next Step

Before writing implementation code, decide the smallest executable shape for this vertical slice and finalize:

1. storage technology;
2. live-versus-snapshot GIS behavior;
3. exact approved R1 rule fields;
4. result schema; and
5. test addresses and expected outputs.

This document is the implementation-facing source of truth for the R1 prototype. The Google Doc remains the broader project-planning reference.
