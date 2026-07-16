# R1 Prototype Progress

**Last updated:** July 16, 2026

**Current position:** Block 5 complete

**Next block:** Implement deterministic standards retrieval

This is the authoritative project-status ledger. The design and scope remain in `docs/r1-prototype-plan.md`; setup and commands remain in `README.md`.

## Milestone tracker

| Block | Status | Exit evidence |
|---|---|---|
| 0. Define the R1 vertical slice | Complete | Scope and completion criteria recorded in the prototype plan. |
| 1. Verify authoritative sources | Complete | Zoning-code and live ArcGIS findings recorded in the prototype plan. |
| 2. Download R1 parcel and zoning GIS | Complete | Two validated 16,193-feature layers and a complete manifest exist. |
| 3. Download and inspect address-point data | Complete | A validated 67,243-feature citywide snapshot and schema report exist. |
| 4. Approve and structure initial R1 rules | Complete | Versioned ruleset, executable schema validation, domain checks, source checksum validation, and regression tests pass. |
| 5. Implement address-to-parcel-to-zone lookup | Complete | Checksum-verified local lookup and all address, spatial, ambiguity, and failure fixtures pass. |
| 6. Implement deterministic standards retrieval | Not started | Requires versioned rule lookup and result contract. |
| 7. Present a simple result | Not started | Requires a working retrieval path and readable output. |
| 8. Validate the vertical slice | Not started | Requires expected fixtures, failure cases, and repeatability evidence. |

## Completed-block evidence

### Blocks 0–1: scope and source verification

- Design, source findings, candidate standards, limitations, and completion criteria: `docs/r1-prototype-plan.md`.
- Shared zoning-code and planning sources: `GOOGLE_DRIVE_SOURCE.txt`.

### Block 2: R1 GIS acquisition

Canonical snapshot:

```text
data/raw/2026-07-14/santa_clara_r1_gis/
```

Validation summary:

| Layer | R1-6L | R1-8L | Total | Validation |
|---|---:|---:|---:|---|
| Parcels | 15,757 | 436 | 16,193 | Feature and unique object-ID counts match the source response. |
| Current zoning | 15,757 | 436 | 16,193 | Feature and unique object-ID counts match the source response. |

Key artifacts:

- `manifest.json` — source URLs, filter, counts, output files, SHA-256 checksums, and validation status.
- `parcels_r1.geojson` — parcel polygons and attributes including APN.
- `current_zoning_r1.geojson` — current parcel-level zoning polygons and attributes.
- `scripts/download_r1_gis.py` — reproducible downloader.

Block 2 created no database, address snapshot, normalization, spatial join, rules engine, API, or UI.

### Block 3: address-point acquisition

Canonical snapshot:

```text
data/raw/2026-07-16/santa_clara_address_points/
```

Validation summary:

- All 67,243 source object IDs produced 67,243 features and unique downloaded object IDs.
- Every feature is a point in EPSG:4326; the consolidated GeoJSON and schema-report checksums match the manifest.
- `CSCADDR`, `ADDRNUM`, `STRNAME`, `ADDRCITY`, and `ADDRZIP5` have no missing values.
- The layer contains 36,793 records with unit values and 45 duplicated full-address values. Exact-address lookup must therefore preserve multiple matches.

Key artifacts:

- `manifest.json` — source, query method, counts, checksums, and validation status.
- `address_points.geojson` — complete citywide address-point layer.
- `schema_report.json` — field inventory, completeness counts, value distributions, duplicate summary, and coordinate bounds.
- `scripts/download_address_points.py` — reproducible downloader.
- `scripts/arcgis_snapshot.py` — shared ArcGIS request, serialization, batching, and checksum utilities.

The canonical raw input is citywide rather than R1-only. Address resolution precedes parcel and zoning classification, and the complete source supports controlled unsupported-zone outcomes.

Initial lookup fixtures identified from the local snapshots:

| Case | Address | Expected acquisition/spatial result |
|---|---|---|
| R1-6L | 636 Barto Street | One address point; APN `293-16-045`; R1-6L. |
| R1-8L | 108 Brookside Avenue | One address point; APN `303-22-022`; R1-8L. |
| Unsupported zone | 1500 Warburton Avenue | One address point; outside the downloaded R1 polygons; previously verified as PQP. |
| Unit address | 1577 Pomeroy Avenue 202 | One unit-bearing address record with a sub-address identifier. |
| Duplicate full address | 324 Los Padres Boulevard | Two source records; lookup must not silently select one. |
| Unmatched | 99999 No Such Street | No local address-point match. |

Block 3 itself created no normalization, parcel join, database, rules engine, API, or UI; address and spatial lookup were added later in Block 5.

### Block 4 source baseline and amendment audit

Canonical local source snapshot:

```text
data/raw/2026-07-16/santa_clara_zoning_code/
```

Completed evidence:

- Preserved the 497-page July 2025 zoning-code PDF with SHA-256 `d6461e366cd214beb5c96ee8abe7498d80464879ac63f216119db7c3af6c9c35`.
- Verified the R1 source location as Chapter 18.10, Section 18.10.030, Table 2-3.
- Preserved adopted Ordinances 2085 and 2086 and the proposed Cleanup #3 tables with checksums in the snapshot manifest.
- Audited post-July-2025 adoption and pending-amendment records through July 16, 2026.
- Found no adopted later amendment changing the selected R1-6L or R1-8L Table 2-3 numeric values.
- Recorded the unresolved Chapter 18.27 collision between Ordinances 2085 and 2086.

Human-readable audit: `docs/title18-amendment-audit.md`.

Rule-level verification is recorded in `docs/r1-rule-verification.md`. It traces use permission, approval requirements, definitions, measurement methods, exceptions, cross-references, nonconformity effects, and deferrals for the selected R1 standards.

Important findings:

- The 25-foot height, two-story limit, 40-percent structure coverage, and most setback cells are verified as base-zone values.
- Base setbacks cannot yet be converted into a parcel-specific building envelope because averaging, encroachments, official plan lines, alley credit, narrow historical parcels, and nonconformities may apply.
- Table 2-3 gives a 10-foot first-story corner-side setback for R1-8L, while Section 18.10.040(B)(1) requires at least 15 feet. The prototype now uses 15 feet under the specific written provision and Section 18.04.020(G), while preserving both source assertions and marking the resolution as pending official clarification.
- `Permitted by right` does not mean approval-free: Zoning Clearance and Architectural Review paths remain applicable.

Canonical ruleset artifacts:

```text
rulesets/santa_clara/r1/2026-07-16/ruleset.json
rulesets/schema/r1-ruleset.schema.json
scripts/validate_r1_rules.py
tests/test_r1_rules.py
```

Validation evidence:

- The validator applies the Draft 2020-12 schema and then accepts all 16 approved rules and the documented conflict record under additional domain invariants.
- Source-file verification confirms the recorded SHA-256 digests for the July 2025 zoning-code PDF and amendment audit.
- Twelve regression tests confirm the selected values, R1-8L paired side yards, approval-path separation, deferred subjects, required fields, enums, malformed-input handling, and conflict integrity.
- The conflict mutation test rejects drift between the selected R1-8L 15-foot rule and its resolution record.

### Block 5: local address-to-parcel-to-zone lookup

Canonical implementation:

```text
santa_clara_zoning/addressing.py
santa_clara_zoning/geometry.py
santa_clara_zoning/lookup.py
scripts/lookup_r1_zone.py
```

Completed evidence:

- Address normalization handles suffix variants, locality text, ZIP codes, punctuation, and unit markers without fuzzy or AI matching.
- Exact duplicate source records remain ambiguous rather than being silently deduplicated.
- Snapshot loading verifies manifests, feature counts, EPSG:4326, SHA-256 checksums, and R1 designation scope.
- Bounding-box-prefiltered point-in-polygon checks support Polygon, MultiPolygon, holes, and boundaries.
- Parcel and current-zoning designations must agree before a supported result is returned.
- Barto and Brookside resolve to their expected APNs and R1 zones; Warburton, Pomeroy unit 202, Los Padres, and the unmatched fixture return their expected controlled outcomes.
- The full suite passes 29 tests, including synthetic designation-mismatch and incomplete-spatial-match cases.

The local polygon snapshot contains only R1-6L and R1-8L. An address with no R1 polygon match is therefore labeled `outside_supported_r1_snapshot`; its exact non-R1 zone is not inferred. Split-zone parcel-area analysis remains deferred.

## Next block: deterministic standards retrieval

Block 6 exit conditions:

1. Load and validate the approved R1 ruleset as the runtime regulatory source.
2. Select only approved rules whose applicability includes the resolved R1 zone.
3. Combine parcel, zoning, and base-standard records in a versioned structured result contract.
4. Preserve citations, conditions, exception-family warnings, conflict status, and `not evaluated` topics.
5. Verify deterministic output for the R1-6L and R1-8L fixtures without adding proposal-level calculations or a UI.

## Blockers

None currently recorded.

## Implementation decision log

| Date | Decision | Reason |
|---|---|---|
| 2026-07-14 | Preserve raw GIS before choosing a database. | Enables offline inspection without committing to an application storage model. |
| 2026-07-14 | Download all matching R1 features instead of a sample. | The complete filtered set is manageable and avoids sampling blind spots. |
| 2026-07-14 | Download by ArcGIS object ID and validate completeness. | Prevents silent truncation from service record limits. |
| 2026-07-14 | Limit GET batches to 100 features. | A 500-ID URL was rejected by the City/proxy. |
| 2026-07-15 | Assign one owner to each kind of project information. | Avoids synchronizing milestone state and commands across multiple documents. |
| 2026-07-15 | Exclude downloaded GIS snapshots from Git. | Raw data is reproducible, potentially large, and retains its own local manifest and checksums. |
| 2026-07-16 | Use the complete citywide address layer as the canonical raw address input. | Address resolution occurs before zoning classification and must also support unsupported-zone results. |
| 2026-07-16 | Use POST requests with 1,000-ID batches for address acquisition. | Avoids GET URL-length limits while preserving complete object-ID validation with fewer requests. |
| 2026-07-16 | Share ArcGIS snapshot primitives between downloaders. | Keeps retry, parsing, serialization, batching, and checksum behavior consistent without duplicating code. |
| 2026-07-16 | Treat the July 2025 code as a versioned baseline plus an amendment ledger. | The City still labels July 2025 as the latest consolidation, while later adopted ordinances remain unincorporated. |
| 2026-07-16 | Do not resolve the competing Chapter 18.27 enactments in application logic. | Ordinances 2085 and 2086 assign different text to the same chapter number; City or codifier clarification is required. |
| 2026-07-16 | Treat verified dimensional numbers as base-zone standards rather than final parcel requirements. | Setback averaging, encroachments, official plan lines, alleys, historical parcels, and legal nonconformities can change site-specific application. |
| 2026-07-16 | Resolve the R1-8L first-story corner-side setback to 15 feet while preserving the conflict. | The zone-specific written provision states at least 15 feet, and Section 18.04.020(G) directs use of the more restrictive requirement; the 10-foot table assertion remains provenance, not discarded data. |
| 2026-07-16 | Store the first regulatory implementation as versioned normalized JSON. | The small prototype ruleset remains directly inspectable and testable without committing to an application database before lookup access patterns are known. |
| 2026-07-16 | Validate rules with executable Draft 2020-12 schema validation, domain invariants, and regression tests. | The schema must actually reject malformed records, while custom checks separately enforce cross-record provenance and selected-value consistency. |
| 2026-07-16 | Start address resolution with normalized exact matching rather than fuzzy matching. | Exact matching is reproducible and makes unmatched and duplicate outcomes explicit while the prototype remains narrow. |
| 2026-07-16 | Query immutable GeoJSON snapshots directly before choosing a database. | The current data volume supports a simple validated vertical slice and preserves the option to select storage after access patterns are proven. |
| 2026-07-16 | Verify snapshot checksums and source invariants when loading lookup data. | Runtime lookup must not silently use incomplete, modified, misprojected, or out-of-scope polygon data. |
| 2026-07-16 | Label no-polygon results outside the supported R1 snapshot rather than naming a non-R1 zone. | The local polygon snapshot is intentionally R1-filtered and cannot establish the exact designation of an unsupported parcel. |
