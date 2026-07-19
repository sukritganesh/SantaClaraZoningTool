# Santa Clara Residential Rule Verification

**Status:** Block 1 technical evidence complete and ready for project-owner approval; new-zone rules are not approved for runtime

**Verified through:** July 18, 2026

**Consolidated-code baseline:** Santa Clara Zoning Code, Title 18 - July 2025

**Product scope:** Santa Clara Zoning Explorer - selected residential zoning standards by address

This document is the source trace and approval gate for expanding beyond the released R1 rules. It records source-backed assertions, candidate product dispositions, conflicts, dependencies, and the evidence still required before machine-readable residential rules may be approved. It is not itself a ruleset, entitlement analysis, official City interpretation, or legal opinion.

The approved R1 source trace remains immutable historical evidence in `docs/r1-rule-verification.md`. This document reuses those approved conclusions by reference and owns verification for the additional zones, uses, structure types, and nonnumeric dispositions.

## 1. Verification states

| State | Meaning |
|---|---|
| Source verified | The assertion was checked against a preserved or current authoritative source, including its exact table column or operative text. |
| Source verified with conditions | The base assertion is clear, but a named plan, overlay, exception, proposal fact, or other authority can change its application. |
| Candidate disposition | The source meaning is understood, but the proposed product representation has not passed schema design and owner approval. |
| Plan-dependent | The base zoning table expressly relies on a specific plan, PDO, development plan, or other plan-level authority that has not supplied one universal value. |
| Conflict retained | Authoritative assertions differ and must remain separately visible until an approved resolution or `review required` disposition exists. |
| Not evaluated | A relevant rule is disclosed but the current product phase will not automate it. |
| Runtime approved | A source-verified rule has passed the representation, validation, review, and approval gates for a specific immutable ruleset version. |

Source verification is necessary but does not confer runtime approval. Except for the inherited R1 rules in version `2026-07-17.2`, no rule described here is runtime approved yet.

## 2. Source hierarchy and boundary

### Preserved authoritative baseline

The controlling consolidated source is:

```text
data/raw/2026-07-16/santa_clara_zoning_code/SantaClaraZoningCode-July-2025.pdf
```

- Title: Santa Clara Zoning Code, Title 18 - July 2025
- Pages: 497
- SHA-256: `d6461e366cd214beb5c96ee8abe7498d80464879ac63f216119db7c3af6c9c35`
- Manifest: `data/raw/2026-07-16/santa_clara_zoning_code/manifest.json`
- Current City publication check: the official [Zoning Code Updates page](https://www.santaclaraca.gov/our-city/departments-a-f/community-development/planning-division/zoning/zoning-code-update) still identifies July 2025 as the latest consolidated edition as of July 18, 2026.

The controlling Patrick Henry plan source is now preserved at:

```text
data/raw/2026-07-18/patrick_henry_drive_specific_plan/PatrickHenryPlan.pdf
```

- Title: Patrick Henry Drive Final Adopted Focus Area Plan
- Version: March 2022; adopted March 22, 2022
- Pages: 191
- SHA-256: `cefd7df91819c61d26b5cdddd0d395b74445078f2dc6e0d57995dc6992b16b87`
- Manifest: `data/raw/2026-07-18/patrick_henry_drive_specific_plan/manifest.json`
- Retrieval: original PDF supplied by the project owner in Google Drive after the official City PDF endpoint rejected direct automated retrieval

The relevant baseline locations were extracted and visually checked:

| Subject | Code location | PDF pages | Printed pages |
|---|---|---:|---|
| Citywide dwelling permissions | Section 18.10.020; Table 2-1 | 21-22 | 2-3 to 2-4 |
| Patrick Henry dwelling permissions | Section 18.10.020; Table 2-2 | 23 | 2-5 |
| Citywide development standards | Section 18.10.030; Table 2-3 | 24-26 | 2-6 to 2-8 |
| Patrick Henry development standards | Section 18.10.030; Table 2-4 | 27-28 | 2-9 to 2-10 |
| Patrick Henry land-use classifications and purposes | Specific Plan Section 4.3.2 | 58, 60, 62 | 52, 54, 56 |
| Patrick Henry development standards | Specific Plan Table 4.2 | 63 | 57 |
| Patrick Henry residential use permissions | Specific Plan Table 4.3 | 64-65 | 58-59 |
| Patrick Henry setback design standards | Specific Plan Section 5.5.3 | 148-150 | 142-144 |
| Patrick Henry regulatory implementation | Specific Plan Section 7.1 | 179-180 | 173-174 |
| R1 two-unit pathway | Chapter 18.24 | 83-87 | 2-63 to 2-67 |
| Dwelling and primary-structure definitions | Sections 18.160.040 and 18.160.190 | 475, 492-493 | 8-8, 8-25 to 8-26 |
| Architectural Review | Chapter 18.120 | Existing R1 trace plus current official process page | - |
| Zoning Clearance | Section 18.10.020(D); Chapter 18.126 | Existing R1 trace plus Table 2-1/2-2 gate | - |

### Later authoritative layers

- Expansion amendment status and recheck triggers are recorded in `docs/residential-title18-amendment-audit.md`. The approved R1 rulesets continue to checksum-pin the historical `docs/title18-amendment-audit.md` and that source must not be edited in place.
- Ordinance 2085, adopted March 10, 2026 and effective April 9, 2026, adds Citywide Objective Design Standards for multifamily and residential mixed-use projects. Its applicability must be disclosed, but its detailed standards are not evaluated in this phase.
- Ordinance 2086, adopted June 9, 2026 and effective July 9, 2026, separately adds El Camino Real Corridor material as Chapter 18.27. The chapter-number collision with Ordinance 2085 remains unresolved in the published source stack.
- The Patrick Henry Drive Specific Plan was adopted March 22, 2022. The official [City project page](https://www.santaclaraca.gov/our-city/departments-a-f/community-development/planning-division/specific-plans/patrick-henry-drive) and [final adopted plan PDF](https://www.santaclaraca.gov/home/showpublisheddocument/72222/637921162111370000) identify it as the plan-level authority. The exact user-supplied PDF is now preserved locally with source metadata and checksum.
- The City parcel and current-zoning ArcGIS layers establish exact live designations. They do not establish legal permission or dimensional values by themselves.

### Candidate research inputs

The Google Drive `Santa Clara Residential Zoning Research`, `Santa Clara Residential Zoning Rule Inventory`, and supplemental watchlist provide a thorough candidate extraction from the July 2025 baseline. They are useful cross-checks and extraction aids, not approval sources. The rule-inventory tabs inspected for this pass were `Overview`, `Zone Standards`, `Use Permissions`, `Dependencies & Flags`, and `Source Trace`.

## 3. Exact zoning scope and GIS identity

### Target designations

| Source family | Legal/source label | Exact live GIS key | Treatment |
|---|---|---|---|
| Citywide | R1-6L | `R1-6L` | Supported target; existing approved R1 lineage |
| Citywide | R1-8L | `R1-8L` | Supported target; existing approved R1 lineage |
| Citywide | R2 | `R2` | Supported target |
| Citywide | R3 | `R3` | Supported target |
| Citywide | R4 | `R4` | Supported target |
| Citywide | R5 | `R5` | Legal rule target; no exact live features observed |
| Citywide | R6 | `R6` | Legal rule target; no exact live features observed |
| Patrick Henry | PH-R5 | `PH-R5` | Supported target; plan qualifications retained |
| Patrick Henry | UV | `UV` | Supported target; plan qualifications retained |
| Patrick Henry | VR | `VR` | Supported target; plan qualifications retained |
| Patrick Henry | UC | `UC` | Supported target; plan qualifications retained |
| Patrick Henry | High-Density Flex / HD Flex | `HDF` | Candidate explicit crosswalk; never normalize by string similarity at runtime |

The Specific Plan uses `High-Density Flex` and `HD Flex`; Title 18 uses `HD-Flex`; the live GIS uses `HDF`. That three-source crosswalk requires explicit owner approval in the ruleset contract. It is not a general permission to abbreviate or normalize other zone names.

### Explicitly excluded designations

`R1-6LHT`, `R2-7L`, and `R2HT` remain distinct legacy or combining designations. They must not be treated as `R1-6L` or `R2` without a separately verified authority and precedence model.

## 4. Residential use and structure matrix

`P` means allowed by right in Tables 2-1 or 2-2. Under Section 18.10.020(D), a `P` use involving construction still requires Zoning Clearance. Use permission does not eliminate Architectural Review or a required hearing.

| Zone group | Single-family dwelling row | Two-family dwelling row | Multifamily dwelling row | Source status |
|---|---|---|---|---|
| `R1-6L`, `R1-8L` | `P` | `P`, subject to Chapter 18.24 | Not listed | Source verified in Table 2-1 and Chapter 18.24; special dimensional disposition required |
| `R2` | `P` | `P` | `P` | Source verified in Table 2-1 |
| `R3`, `R4` | Not listed | `P` | `P` | Source verified in Table 2-1 |
| `R5`, `R6` | Not listed | Not separately listed | `P` | Source verified in Table 2-1 |
| `PH-R5`, `UV`, `VR`, `UC`, HD Flex source column | Not listed | Not separately listed | `P` | Source verified in Title 18 Table 2-2 and Specific Plan Table 4.3; `HDF` key crosswalk remains a candidate contract decision |

“Not listed” records the source-table cell and does not independently resolve every definitional or nonconforming-use question. The product will not offer a separate two-family selection in a zone whose table supplies only the multifamily row; it will use the multifamily selection and preserve the source's legal-use identity.

Planned product identities:

| Workflow family | Legal-use capability | Primary-structure identity | Boundary |
|---|---|---|---|
| Single-family | `use.single_family_dwelling` | `single_family_primary_structure` | Offered only where Table 2-1 lists the use |
| Multifamily | `use.two_family_dwelling` | `two_family_primary_structure` | May reuse the multifamily workflow, but retains separate legal and structural identity |
| Multifamily | `use.multifamily_dwelling` | `multifamily_primary_structure` | Offered only where Table 2-1 or 2-2 lists the use |

Title 18 definitions establish that:

- a single-family dwelling is one residential structure containing one dwelling unit on one parcel;
- a two-family dwelling is one residential structure containing two dwelling units on one parcel;
- a multifamily dwelling is a residential structure or complex containing three or more dwelling units and expressly excludes two-family dwellings;
- a primary structure is the structure in which the principal use is conducted; and
- structure coverage is the portion of a parcel covered by structures, subject to the stated exclusions.

Chapter 18.24 is broader than the ordinary two-family-structure definition because it authorizes two attached or detached homes on an eligible R1 parcel. When both units are entirely within the ordinary R1 building envelope, the applicable R1 zone standards apply to each house. When any portion lies outside that envelope, Section 18.24.060 applies different height/story rules and makes side and rear setbacks the least of the zone value, four feet, or a qualifying existing-structure setback. It also carries additional size, window, balcony, entrance, garage, landscaping, and waiver provisions.

The planned `two_family_primary_structure` identity accurately describes one two-unit structure, but it does not by itself represent two detached single-family primary structures. The current product has no proposal geometry, configuration, existing-structure facts, or eligibility evaluator needed to select the Chapter 18.24 branches. The R1 two-unit pathway may therefore be listed, but its dimensional result remains `not evaluated`; it must not silently receive the ordinary single-family R1 result.

## 5. Approval-path findings

### Zoning Clearance

Section 18.10.020(D) expressly requires Zoning Clearance when a land use marked `P` includes additions, alterations, new construction, reconstruction, or remodeling. Chapter 18.126 governs the clearance. The candidate product disposition remains a separate `approval.zoning_clearance` rule rather than a qualification hidden inside use status.

**State:** Source verified; new-zone rule records not runtime approved.

### Architectural Review

Chapter 18.120 generally requires Architectural Review before exterior building, structure, or sign work unless exempt. The current official City process page states that new multifamily developments of any size require Development Review Hearing review and directs projects in specific plans to the applicable plan requirements.

The product may disclose the base Architectural Review requirement and the new-multifamily hearing trigger. It will not evaluate every exemption, alteration threshold, finding, public-notice requirement, appeal, or project condition in this phase.

**State:** Source verified with conditions; new-zone rule records not runtime approved.

## 6. Citywide development-standard assertions

Section 18.10.030(A) describes Tables 2-3 and 2-4 as the basic site and structure regulations applying to development in each residential zone. These values are base-zone assertions, not parcel-specific envelopes.

### Height, stories, and structure coverage

| Zone | Base height outside the R1/R2 transition | Stories | Coverage below 10,000 sf | Coverage at or above 10,000 sf | Verification |
|---|---:|---:|---:|---:|---|
| `R1-6L` | 25 ft | 2 | 40% | 40% | Inherited approved R1 conclusion |
| `R1-8L` | 25 ft | 2 | 40% | 40% | Inherited approved R1 conclusion |
| `R2` | 32 ft | 2 | 45% | 45% | Source verified |
| `R3` | 40 ft | 4 | 60% | No maximum listed | Source verified |
| `R4` | 80 ft | 8 | 80% | No maximum listed | Source verified |
| `R5` | 100 ft | 10 | No maximum listed | No maximum listed | Source verified; no live GIS feature observed |
| `R6` | 200 ft | 20 | No maximum listed | No maximum listed | Source verified; no live GIS feature observed |

Table 2-3 separately limits height to 32 feet when a structure is within 20 feet of `R1-6L`, `R1-8L`, or `R2`. This transition rule is source verified but outside the present evaluator because the product does not yet calculate the required adjacency and distance facts. It must appear as a `not evaluated` qualification where relevant.

“No maximum listed” means the controlling base table places `None` in that cell. It does not mean unlimited development, approval-free development, or the absence of other controlling standards.

### Setbacks

| Zone | Front | Street-side/corner-side | Interior-side | Rear | Verification |
|---|---|---|---|---|---|
| `R1-6L` | 20 ft; 25 ft second story | 10 ft; 15 ft second story | 5 ft; 10 ft second story | 20 ft | Inherited approved R1 conclusion |
| `R1-8L` | 20 ft; 25 ft second story | Selected 15 ft with retained 10/15 conflict; 15 ft second story | Paired 6/9 ft; paired 11/14 ft second story | 20 ft | Inherited approved R1 conclusion and conflict policy |
| `R2` | 15 ft | 10 ft | 5 ft | 10 ft single-story; 15 ft multistory | Source verified |
| `R3` | 10 ft | 10 ft | 5 ft | 10 ft single-story; 15 ft multistory | Source verified |
| `R4` | 10 ft | 15 ft | 10 ft | 20 ft | Source verified |
| `R5` | 10 ft | 15 ft | 10 ft | 20 ft | Source verified; no live GIS feature observed |
| `R6` | 10 ft | 15 ft | 10 ft | 20 ft | Source verified; no live GIS feature observed |

The source distinguishes single-story from multistory rear setbacks; it does not use “multistory” to mean “multifamily.” The representation must preserve this trigger precisely.

The existing setback measurement, averaging, plan-line, alley-credit, encroachment, narrow-parcel, and nonconformity limitations documented in `docs/r1-rule-verification.md` remain relevant unless a source verification proves otherwise. This phase retrieves base values and does not calculate a parcel-specific building envelope.

## 7. Patrick Henry development-standard assertions

| GIS key | Source zone | Height outside transition | Stories | Coverage | Front, street-side, and interior-side residential setbacks | Rear setback |
|---|---|---:|---:|---|---|---|
| `PH-R5` | PH-R5 | 135 ft | 10 | No maximum listed | 10 ft from back of walk | No universal numeric value listed; plan/project review required |
| `UV` | UV | 160 ft | 12 | No maximum listed | 10 ft from back of walk | No universal numeric value listed; plan/project review required |
| `VR` | VR | 160 ft | 12 | No maximum listed | 10 ft from back of walk | No universal numeric value listed; plan/project review required |
| `UC` | UC | FAA-controlled | FAA-controlled | No maximum listed | 10 ft from back of walk | No universal numeric value listed; plan/project review required |
| `HDF` | High-Density Flex / HD Flex / HD-Flex | 160 ft | 12 | No maximum listed | 10 ft from back of walk | No universal numeric value listed; plan/project review required |

Title 18 Table 2-4 and Specific Plan Table 4.2 group only the residential front, corner-side, and interior-side setbacks. Neither provides a rear-setback row. A full-plan text search found `rear` only in service-access guidance on PDF page 150, not as a rear-yard number. The candidate product disposition therefore remains plan/project review required, with no universal numeric base value. Zero is not a permissible fallback.

For `UC`, the literal table value is `FAA` for both height and stories. The candidate disposition is `FAA-controlled`; the product must not invent a fixed number or describe the absence of a table number as no limit.

Table 2-4 also provides a 32-foot height within 20 feet of R1/R2 zones and defers recreation space and setback encroachments to the PDO and Patrick Henry plan. The transition, recreation-space, and detailed encroachment rules are relevant but `not evaluated` in this phase.

Specific Plan Section 4.3.2.4 confirms that HD Flex accommodates multifamily residential development interspersed with an optional office path. Only the residential standards and residential use are in this product phase; the office path is not evaluated.

Specific Plan Section 7.1 states that the Zoning Ordinance translates the plan into use regulations and development standards, and that projects must meet the development standards and substantially conform to the Chapter 5 design guidelines. The plan and Title 18 assertions therefore remain separately cited; neither source is silently flattened into the other.

**State:** Patrick Henry base assertions and the absence of a universal rear number are source verified. The `HDF` crosswalk and product dispositions remain candidates pending owner approval.

## 8. Amendment and conflict findings

### Ordinance 2085 - Objective Design Standards

The adopted standards apply to new multifamily and residential mixed-use development and additions to existing multifamily or residential mixed-use development. The ordinance states that the standards are additive to Chapters 18.10 and 18.14 and that specific-plan standards control a conflict.

The product must disclose this applicable layer for multifamily results. Detailed Objective Design Standards evaluation remains outside the current capability scope and must be labeled `not evaluated`.

### Ordinance 2086 - El Camino Real Corridor

The adopted ordinance is geographically outside the selected residential base-zone scope, but it also purports to add different text as Chapter 18.27. The project must preserve the chapter-number collision and must not guess how codification will reconcile it.

### Cleanup #3, File 26-735

The official Legistar matter remained `Agenda Ready` on July 18, 2026, with no passed date, enactment date, or enactment number. The July 14 event item still had no action, result, passed flag, tally, mover, or seconder.

The matter title includes rezoning properties currently designated `TN` to `R6`. This proposed map action is a direct recheck trigger for live `R6` availability. Until a final action and effective ordinance are established, Cleanup #3 is not treated as law and its proposed `R6` parcels must not be anticipated in runtime data.

## 9. Residential GIS acquisition contract

The residential snapshot reuses the validated ArcGIS acquisition primitives while creating a new non-R1 artifact. The implementation is `scripts/download_residential_gis.py`; its contract tests are in `tests/test_residential_gis_downloader.py`.

### Sources and exact filter

| Layer | Endpoint | Required identity field |
|---|---|---|
| Land parcels | `https://map.santaclaraca.gov/maps/rest/services/OPENDATA/RegionalBaseOpenData/MapServer/7` | `OBJECTID`; parcel identity also requires `APN` |
| Current zoning | `https://map.santaclaraca.gov/maps/rest/services/OPENDATA/RegionalZoningOpenData/MapServer/0` | `OBJECTID` |

Exact filter:

```sql
ZONGDSGN IN ('R1-6L','R1-8L','R2','R3','R4','R5','R6','PH-R5','UV','VR','UC','HDF')
```

No legacy, combining, or similar-looking designation may enter through normalization or prefix matching.

### Required destination and files

```text
data/raw/<snapshot-date>/santa_clara_residential_gis/
```

Required canonical outputs:

- `parcels_residential.geojson`
- `current_zoning_residential.geojson`
- per-layer `metadata.json`
- per-layer `object_ids.json`
- preserved raw response batches
- `manifest.json`, or `manifest.failed.json` on an interrupted or invalid acquisition

### Completeness and integrity requirements

1. Refuse to overwrite an existing snapshot directory.
2. Preserve the exact source URLs, query filter, retrieval timestamps, object-ID field, source object IDs, batch size, raw responses, and output spatial reference.
3. Retrieve the complete source object-ID list first and reject duplicate source IDs.
4. Keep GET feature batches at 100 IDs or fewer unless a separately tested transport replaces that limit.
5. Request full attributes and geometry in EPSG:4326 without Z or M values.
6. Require downloaded feature count, downloaded unique-ID count, and source-ID count to match exactly for each layer.
7. Require the downloaded ID set to equal the source ID set; report missing and unexpected IDs on failure.
8. Record per-zone counts for every requested designation, including explicit zeros for `R5` and `R6` if they remain absent.
9. Record the observed designation set and reject any designation outside the exact filter.
10. Record a separate preflight count for explicitly excluded `R1-6LHT`, `R2-7L`, and `R2HT` so their deliberate exclusion is inspectable.
11. Require parcel and current-zoning counts to match per supported designation or stop for review; do not silently choose one layer as correct.
12. Preserve checksums for consolidated outputs, metadata, object-ID responses, and a deterministic inventory of raw chunks.
13. Validate GeoJSON collection and feature shapes, polygonal geometry, required fields, and declared EPSG:4326 output.
14. Treat a zero-feature requested designation as an explicit source result, not a failed download and not evidence that the legal zone does not exist.
15. Write a failed manifest containing completed-layer evidence before surfacing an acquisition error.

### July 18, 2026 preflight observations

The official parcel and current-zoning layers returned identical counts:

| Designation | Parcel count | Current-zoning count |
|---|---:|---:|
| `HDF` | 5 | 5 |
| `PH-R5` | 2 | 2 |
| `R1-6L` | 15,757 | 15,757 |
| `R1-8L` | 436 | 436 |
| `R2` | 752 | 752 |
| `R3` | 1,685 | 1,685 |
| `R4` | 2 | 2 |
| `R5` | 0 | 0 |
| `R6` | 0 | 0 |
| `UC` | 2 | 2 |
| `UV` | 9 | 9 |
| `VR` | 27 | 27 |
| **Total** | **18,677** | **18,677** |

The excluded-designation preflight returned `R1-6LHT: 14`, `R2-7L: 1`, and `R2HT: 2` in each layer.

These counts are preflight observations, not hardcoded acceptance values. The authoritative snapshot manifest must record the source response at acquisition time. A changed count requires inspection, not automatic rejection merely because it differs from July 18.

### July 18, 2026 immutable acquisition result

The completed source snapshot is preserved at:

```text
data/raw/2026-07-18/santa_clara_residential_gis/
```

Its authoritative `manifest.json` has SHA-256 `f71138d11eabdff773cb3f8fe156a41d0940b1adde72370f9bbab74a397aeb38`. The acquisition returned the same 18,677 features and the same per-zone and excluded-designation counts shown in the preflight table for both source layers. Those values are now snapshot evidence rather than acceptance constants.

The snapshot passed all 15 requirements above:

- both source object-ID responses, downloaded feature arrays, and downloaded unique-ID sets contain exactly 18,677 IDs, with exact set equality;
- 187 GET batches per layer stayed at 100 IDs or fewer, and every batch returned exactly its requested IDs;
- requested count responses include explicit zeroes for `R5` and `R6`, while the only observed nonzero designations are the 10 exact live keys in the table;
- both layers independently report excluded preflight counts of `R1-6LHT: 14`, `R2-7L: 1`, and `R2HT: 2`;
- every feature has the required identity values and valid two-dimensional polygonal geometry within EPSG:4326 bounds;
- parcel and current-zoning counts agree for every requested and excluded designation; and
- all 410 recorded evidence files—metadata, object-ID responses, count responses, raw chunks, and consolidated outputs—were re-read and matched their manifest sizes and checksums.

Canonical consolidated outputs:

| Layer | Features | Bytes | SHA-256 |
|---|---:|---:|---|
| `parcels_residential.geojson` | 18,677 | 14,191,101 | `e31ce5afb81c717ddcbd639c17b57a4625bcf257175a14cc03a09bfc90f5ecc3` |
| `current_zoning_residential.geojson` | 18,677 | 16,554,895 | `cb18cf0a8f7b2ebc8754334285b0f73e3160ca7d7f3fc64eeb6df3963b23f862` |

## 10. Fixture-selection contract and result

After the snapshot passes integrity validation:

1. Identify at least one real address whose address point, parcel polygon, and current-zoning polygon agree for every designation that has reachable parcels.
2. Prefer fixtures that exercise distinct rule shapes rather than arbitrary repeated addresses.
3. Inspect the two `R4` features and the small Patrick Henry groups individually before selecting fixtures.
4. Use synthetic ruleset and contract fixtures for `R5` and `R6` while their live count is zero; do not invent a real address.
5. Add explicit negative fixtures for the excluded `R1-6LHT`, `R2-7L`, and `R2HT` designations.
6. Preserve existing ambiguous, unmatched, unit-bearing, spatial-mismatch, and integrity-failure cases from the R1 acceptance matrix.
7. Never infer legal-use permission from an address fixture or GIS label; fixtures test routing into independently verified rules.

The committed machine-readable inventory is `tests/fixtures/residential_gis_fixture_inventory.json`. Every real fixture below has one exact address record, one intersecting residential parcel, one intersecting current-zoning feature, and matching exact designations in the preserved snapshots.

| Designation | Selected address | APN | Parcel/zoning object ID |
|---|---|---|---:|
| `R1-6L` | 636 Barto Street | 293-16-045 | 7535 |
| `R1-8L` | 108 Brookside Avenue | 303-22-022 | 7103 |
| `R2` | 1240 White Drive | 290-14-206 | 589 |
| `R3` | 1577 Pomeroy Avenue | 290-03-090 | 51 |
| `R4` | 1400 Coleman Avenue | 230-05-021 | 2434 |
| `PH-R5` | 3105 Patrick Henry Drive | 104-04-131 | 10467 |
| `UV` | 3200 Patrick Henry Drive | 104-04-124 | 10134 |
| `VR` | 4701 Patrick Henry Drive | 104-53-000 | 10070 |
| `UC` | 4650 Old Ironsides Drive | 104-04-077 | 23092 |
| `HDF` | 4633 Old Ironsides Drive | 104-04-141 | 11750 |

Both live `R4` features were inspected. The selected 1400 Coleman Avenue feature carries `SPPLAN: SCS`; the other feature is 2250 El Camino Real, object ID 23128, with `SPPLAN: ECR`. The fixture tests exact routing only and does not erase those plan attributes or claim that the citywide base table is a complete parcel determination. All PH-R5, UV, VR, UC, and HDF polygons were likewise inspected for address-point intersections before selecting one non-unit fixture per designation.

`R5` and `R6` have explicit synthetic ruleset/contract fixtures with zero source counts and no invented address. `R1-6LHT`, `R2-7L`, and `R2HT` have explicit synthetic negative-designation fixtures that require an unsupported exact-designation treatment and forbid normalization to `R1-6L` or `R2`. Existing ambiguous, unmatched, unit-bearing, spatial-mismatch, and integrity cases remain in the released R1 acceptance suite for later migration.

## 11. Remaining verification work

- Obtain owner approval for the exact `High-Density Flex`/`HD Flex`/`HD-Flex` to `HDF` crosswalk and the plan/project-review rear-setback disposition.
- Preserve any parcel-specific PDO or development-plan material only when a selected project requires it; recreation-space and project-specific plan values remain `not evaluated` in this phase.
- Decide the Block 2 representation for one two-family structure versus the R1 Chapter 18.24 option for two detached homes, while keeping the latter `not evaluated` in this phase.
- Decide and document the schema representation for numeric, no-maximum-listed, FAA-controlled, plan-dependent, not-evaluated, and review-required dispositions in Block 2.
- Obtain project-owner approval of the source matrix and explicit candidate dispositions before ruleset authoring.

## 12. Block 1 approval gate

Block 1 is not complete until:

1. the authoritative Title 18 baseline and current amendment cutoff are preserved and reproducible;
2. every target zone/use/structure cell has an exact source citation and explicit disposition;
3. every selected dimensional standard has been checked against the correct table column and relevant operative text;
4. Patrick Henry source dependencies are locally preserved and either resolved or assigned an explicit plan/project-review disposition;
5. the `HDF` crosswalk is approved;
6. the residential GIS snapshot passes the complete acquisition contract;
7. reachable-zone fixtures are source- and geometry-verified;
8. R5/R6 and excluded designations receive controlled test treatment; and
9. the project owner approves the verification record for candidate ruleset authoring.

Items 1 through 4 and 6 through 8 have passed. Items 5 and 9 remain the project-owner approval gate: approve the explicit `High-Density Flex`/`HD Flex`/`HD-Flex` to `HDF` crosswalk and approve the Patrick Henry rear-setback treatment as no universal numeric base value listed, with plan/project review required and no zero default.
