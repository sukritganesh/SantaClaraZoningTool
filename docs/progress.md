# R1 Prototype Progress

**Last updated:** July 18, 2026

**Current position:** Block 7.4a complete — Flask shell and route boundary validated

**Next action:** Review Block 7.4b semantic-template mapping before implementation

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
| 6. Implement deterministic standards retrieval | Complete | All five exit conditions pass across canonical fixtures, integrity gates, and deterministic repeatability checks. |
| 7. Present a simple result | In progress | Contract, presenter, and validation matrix are complete; Block 7.4a adds the validated Flask shell and route. |
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

## Pre-Block 6 ruleset v2 redesign

Block 6 is intentionally paused while the regulatory data model is improved before it becomes a runtime dependency.

| Step | Status | Evidence or next result |
|---|---|---|
| 1. Create the supported-regulations catalog | Complete | `docs/regulations/supported-regulations.md` defines capability stages, current regulation families, boundaries, and deferred items without prescribing schema fields. |
| 2. Change the canonical hierarchy to zone-first | Complete | The approved guide and v2 schema provide direct `zones[zone].regulations[capability]` lookup. |
| 3. Give each zone separate rule identities | Complete | The v2 schema requires convention-compliant zone-owned rule records without multi-zone applicability fields. |
| 4. Redesign setback representation | Complete | The v2 schema enforces typed base values, story or height triggers, total or additional effects, paired distances, and precedence for multiple adjustments. |
| 5. Preserve shared reference data | Complete | The v2 schema provides ID-keyed sources, citations, definitions, and exception families plus top-level conflicts. |
| 6. Migrate approved R1 data | Complete | A separate schema-valid candidate contains 20 zone-owned regulations, all 16 v1 rules have explicit crosswalk targets, and v1 remains unchanged. |
| 7. Expand v2 validation | Complete | V2 domain, source, migration, replay, conflict, scope, and runtime-eligibility gates pass 29 focused tests; after approval coverage, the complete 77-test suite passes. |

The project owner approved the authoring contract on July 16, 2026. `rulesets/schema/ruleset-v2.schema.json` implements its local structural requirements, and the July 17 candidate migrates every approved v1 rule without changing v1. R1-6L preserves a 10-foot street-side base and 15-foot second-story total; R1-8L selects a 15-foot base for all stories while retaining both the 10-foot table assertion and 15-foot written assertion in its conflict record.

The v2 validator now distinguishes candidate validity from runtime eligibility. It enforces the exact supported zones and capabilities, rule identities, capability-specific status and unit semantics, source and exception references, source checksums, story-based adjustments, paired-yard integrity, conflict backlinks and selected-value consistency, complete migration targets, manifest checksums, deterministic replay, and the approved-status plus approval-date runtime gate.

Step 7 found and corrected one migration-crosswalk defect: the R1-8L paired interior-side adjustment was stored correctly in the ruleset but its crosswalk component omitted the `-pair` suffix. No regulatory value changed.

The project owner approved the reviewed v2 data on July 17, 2026. The candidate remains unchanged at `2026-07-17.1`; promotion created immutable version `2026-07-17.2` with only the version, status, and approval date changed. The approved artifact passes domain and source validation, complete migration replay, and the runtime-eligibility gate. Seven approval-specific regressions bring the complete suite to 77 passing tests.

Steps 6–7 artifacts:

```text
scripts/migrate_r1_rules_v2.py
rulesets/santa_clara/r1/2026-07-17/ruleset.json
rulesets/santa_clara/r1/2026-07-17/migration-crosswalk.json
tests/test_r1_rules_v2_migration.py
scripts/validate_r1_rules_v2.py
tests/test_r1_rules_v2.py
scripts/promote_r1_rules_v2.py
rulesets/santa_clara/r1/2026-07-17.2/ruleset.json
rulesets/santa_clara/r1/2026-07-17.2/migration-crosswalk.json
tests/test_r1_rules_v2_approval.py
```

## Block 6 after the redesign gate

Block 6.1 is complete as a design step. The approved contract direction separates a pure zone retriever from address orchestration, uses result-contract version `1.0.0`, preserves the existing Block 5 controlled outcomes, returns approved regulations without flattening their typed structures, includes only referenced shared provenance, and defers proposal evaluation and UI formatting.

Implementation sequence:

| Substep | Status | Intended result |
|---|---|---|
| 6.1 Define retrieval contract and test matrix | Complete | Contract direction, failure behavior, scope boundary, and fixtures are recorded in the prototype plan. |
| 6.2 Load the approved ruleset | Complete | `ApprovedR1Ruleset` validates every canonical artifact, freezes trusted data, exposes safe metadata, and returns defensive copies. |
| 6.3 Retrieve rules by exact zone | Complete | Exact R1-6L/R1-8L keys return all ten approved rules plus their transitive provenance closure. |
| 6.4 Connect Block 5 lookup | Complete | `R1StandardsPipeline` produces the combined contract only after an unambiguous supported-zone lookup. |
| 6.5 Validate Block 6 | Complete | Acceptance audit passes the approved matrix and all five exit conditions; the complete suite passes 105 tests. |

Approved Block 6 test matrix:

- Barto Street returns APN `293-16-045`, R1-6L, and the exact approved R1-6L capability set.
- Brookside Avenue returns APN `303-22-022`, R1-8L, paired side yards, and the documented street-side conflict.
- Warburton, duplicated Los Padres, and the unmatched address preserve their existing controlled Block 5 outcomes.
- Candidate, incomplete, corrupted, or otherwise runtime-ineligible rulesets are rejected.
- Missing required capabilities or broken references cannot produce partial success.
- Repeated execution against identical snapshots and ruleset version produces identical structured output.

Block 6.2 implementation:

```text
santa_clara_zoning/ruleset.py
tests/test_ruleset_loader.py
```

The loader reads the approved ruleset, schema, crosswalk, and source v1 artifact once, then runs schema and domain validation, local source checksum verification, migration completeness and replay, and runtime eligibility. Its internal JSON tree is recursively frozen; public metadata is immutable or copied, and `as_dict()` returns a defensive copy for later retrieval code. Nine focused tests reject the candidate, missing capabilities, changed regulatory values, bad source checksums, broken crosswalks, and missing files while proving repeatable loading and mutation isolation. The complete suite passes 86 tests.

Block 6.3 implementation:

```text
santa_clara_zoning/standards.py
tests/test_zone_standards.py
```

`retrieve_zone_standards()` accepts only an exact zone key and a validated loader, returns all ten approved zone-owned regulations without flattening them, and constructs the transitive closure of rule, exception-family, conflict, citation, and source-document references. R1-6L returns 12 citations, nine exception families, two source documents, and no conflicts; R1-8L returns 14 citations, nine exception families, two source documents, and the preserved street-side conflict. Nine focused tests cover exact matching, completeness, paired yards, vertical adjustments, corner applicability, missing references, mutation isolation, and byte-equivalent repeatability. The complete suite passes 95 tests.

Corner-lot classification is not currently implemented. Retrieval returns the street-side regulation with `applicability.lot_context: corner`; it does not claim that a particular parcel is a corner lot.

Block 6.4 implementation:

```text
santa_clara_zoning/pipeline.py
tests/test_standards_pipeline.py
```

`R1StandardsPipeline.from_defaults()` loads the approved ruleset and checksum-verified local GIS lookup once. `analyze_address()` adds result-contract version `1.0.0`, calls exact-zone retrieval only after `r1_zone_found`, and returns `r1_standards_found` with the parcel, zoning, regulations, provenance, limitations, and combined GIS/ruleset versions. Existing lookup failures retain their status and evidence without acquiring regulations. Inconsistent success evidence, incomplete regulatory results, and regulatory integrity failures stop the pipeline rather than becoming misleading planning-review outcomes.

The initial eight focused tests covered the Barto R1-6L and Brookside R1-8L pipelines, paired yards, the documented street-side conflict, controlled Warburton/Los Padres/unmatched outcomes, no retrieval after lookup failure, fail-closed component boundaries, and byte-equivalent repeatability.

Block 6.5 acceptance evidence:

| Exit condition | Executable evidence |
|---|---|
| Load an approved runtime regulatory source | The v2 validator passes schema, domain, local source checksum, migration replay, approval-date, and runtime-eligibility gates for version `2026-07-17.2`; loader mutation tests reject candidate, incomplete, or corrupted artifacts. |
| Select the exact approved rules for the resolved zone | End-to-end R1-6L and R1-8L tests assert the exact ten capability IDs, independent zone-owned rule IDs, approval flags, status requirements, numeric values, and zone-specific setback structures. |
| Produce one versioned parcel/zoning/regulatory contract | Barto resolves to APN `293-16-045` and R1-6L; Brookside resolves to APN `303-22-022` and R1-8L. Both results carry contract `1.0.0`, GIS snapshot dates, ruleset version, and source URLs. |
| Preserve evidence, uncertainty, and controlled failures | Success tests assert source documents, citations, exception families, conditions, conflicts, `not_evaluated`, and the disclaimer. Warburton, Los Padres, unmatched, and synthetic review outcomes remain unchanged apart from `contract_version` and receive no regulations. |
| Reproduce identical output from identical inputs | Both supported zones pass repeated canonical-byte comparisons, mutation isolation, and separate-process comparisons under different Python hash seeds. |

The acceptance pass strengthened `tests/test_standards_pipeline.py` from eight to ten tests rather than adding arbitrary same-zone parcel fixtures. Additional lots would repeat the same regulatory branch after zoning resolution; one canonical real address per supported zone provides the meaningful regulatory coverage, while the existing negative and synthetic cases exercise distinct lookup and integrity paths.

Final Block 6 validation on July 18, 2026:

```text
Approved v2 runtime eligibility: yes
Approved v2 zone-owned regulations: 20
Documented conflicts: 1
Complete repository tests: 105 passed, 0 failed, 0 skipped
```

Block 6 exit conditions:

1. Load and validate the approved R1 ruleset as the runtime regulatory source.
2. Select only approved rules whose applicability includes the resolved R1 zone.
3. Combine parcel, zoning, and base-standard records in a versioned structured result contract.
4. Preserve citations, conditions, exception-family warnings, conflict status, and `not evaluated` topics.
5. Verify deterministic output for the R1-6L and R1-8L fixtures without adding proposal-level calculations or a UI.

## Block 7 presentation

The Block 7 plan is recorded in `docs/r1-prototype-plan.md`. It introduces a pure deterministic presenter between the accepted Block 6 result and the first interface. The presenter will build a UI-neutral, versioned view model without changing authoritative values or using runtime AI.

The initial overview will remain intentionally brief. It may compose the exact zone, supported single-family use, required approvals, ruleset scope, and disclaimer, but it will not interpret the `6L` or `8L` suffix or invent a per-zone narrative. Richer source-backed zone profiles are deferred.

The presentation contract will also establish the product's reuse boundary: shared capabilities use common deterministic mappings, while a future jurisdiction-specific capability must have an explicit registered extension path. Unknown capabilities or requirement shapes must fail visibly and may not be silently dropped. This safeguard does not add new regulations to the current R1 scope.

The project owner approved Block 7.1 on July 18, 2026. Presentation contract `1.0.0` fixes the successful top-level model; controlled `success`, `lookup_failure`, `review_required`, and `system_error` outcomes; deterministic wording; display order; rule and citation linkage; source-receipt behavior; and version mapping. The normative design is in `docs/r1-prototype-plan.md`; executable behavior and validation are implemented in Blocks 7.2 and 7.3.

Block 7.2 is implemented in `santa_clara_zoning/presentation.py`. `present_pipeline_result()` maps complete Block 6 results through an explicit supported-capability registry and typed handlers for status, maximum-quantity, scalar-setback, paired-setback, and story-based total-minimum records. `present_integrity_error()` separately maps known internal integrity failures to safe `system_error` views so the pure presenter does not swallow malformed data.

The presenter preserves rule identity, applicability, conditions, exception families, source conflicts, citations, GIS sources, limitations, and versions. It uses fixed ordering, constructs independent output objects, rejects unknown capabilities and requirement shapes, and attaches no regulations to controlled lookup or review outcomes. Real local checks produced successful R1-6L and R1-8L views plus controlled non-R1, ambiguous, and unmatched views.

Block 7.3 hardens that boundary with real-pipeline acceptance tests for Barto and Brookside plus Warburton, Los Padres, unmatched, empty-input, and review-required outcomes. Contract-shape, JSON-serialization, wording, display-order, conditional-applicability, provenance-closure, source-link, mutation-isolation, input-order, and cross-process repeatability checks pass. Mutation tests prove that numeric and zone values flow from authoritative input, while removed conflicts, unsupported statuses, malformed paired setbacks, and unsupported adjustment effects fail closed. A project-resolved rule now cannot be presented without its conflict reference.

The project owner approved the initial Block 7.4 interface direction on July 18, 2026. It is a lightweight, scroll-first local web application with persistent address search; property identity and zoning; supported use; separate approvals; compact standards; a setback table; visible warnings; expandable limitations; and superscript references leading to a bottom source-and-version section. Error states preserve the entered address, provide a direct retry path, and never attach regulatory cards.

The project owner also approved Flask `3.1.3`, server-rendered Jinja, custom CSS, minimal JavaScript, one `GET /?address=...` route, an application-factory boundary that loads or accepts the pipeline once, semantic template partials, and Flask test-client coverage within the existing `unittest` suite. The approved 7.4a–7.4d sequence is Flask shell, semantic templates, visual implementation, and web validation. The complete architecture and test boundary are in `docs/r1-prototype-plan.md`.

Block 7.4a is implemented in `santa_clara_zoning/web.py` and `santa_clara_zoning/templates/index.html`. Flask `3.1.3` is pinned in `requirements.txt`; `create_app()` loads or accepts one pipeline instance, exposes only `GET /`, skips analysis for the initial landing state, calls the pipeline and presenter once per submitted address, converts only known integrity failures to safe system views, and leaves unexpected exceptions visible as server failures. The minimum template proves Jinja autoescaping and the presentation-kind boundary without implementing the semantic result sections or approved styling early.

`tests/test_web.py` adds eight isolated shell/error tests and one canonical Barto smoke test. Flask route discovery reports only the application route and Flask's static-file route. The README records the local development command and identifies the shell as intentionally incomplete pending Blocks 7.4b and 7.4c.

Block 7.4a validation evidence:

```text
.venv/bin/python -B -m unittest tests.test_web -v
9 passed, 0 failed, 0 skipped

.venv/bin/python -B -m unittest discover -s tests -v
132 passed, 0 failed, 0 skipped

.venv/bin/python -m flask --app santa_clara_zoning.web routes
index GET /; static GET /static/<path:filename>
```

Block 7.4b is implemented in `santa_clara_zoning/templates/`. `base.html` provides the page landmarks and skip link; `index.html` retains the persistent address search and dispatches only on presentation kind; `_success.html` renders property identity, overview, use, approvals, standards, setbacks, qualifications, and limitations; `_outcome.html` renders controlled non-regulatory outcomes and available evidence; `_sources.html` renders linked regulatory receipts, GIS layers, and versions; and `_macros.html` centralizes typed quantities, paired setbacks, conditions, and citation references.

The semantic layer contains no zone-specific values, regulatory calculations, CSS framework, or runtime AI. Scalar and paired setbacks remain distinct, second-story values remain total minimums, street-side applicability remains conditional, and the R1-8L conflict remains a visible project resolution with both assertions and re-review triggers. Every non-success kind uses the outcome template and renders no regulatory sections.

Block 7.4b validation evidence:

```text
.venv/bin/python -B -m unittest tests.test_web -v
14 passed, 0 failed, 0 skipped

.venv/bin/python -B -m unittest discover -s tests -v
137 passed, 0 failed, 0 skipped
```

Validation evidence:

```text
.venv/bin/python -B -m unittest discover -s tests -p 'test_presentation.py' -v
18 passed, 0 failed, 0 skipped

.venv/bin/python -B -m unittest discover -s tests -v
123 passed, 0 failed, 0 skipped
```

Implementation sequence:

| Substep | Status | Intended result |
|---|---|---|
| 7.1 Approve presentation contract and wording | Complete | Presentation contract `1.0.0` and its success/failure semantics were approved by the project owner on July 18, 2026. |
| 7.2 Implement the pure presenter | Complete | Pure presentation and known-integrity-error APIs map contract `1.0.0` without hard-coded zone values or runtime AI; focused and full tests pass. |
| 7.3 Validate presenter behavior | Complete | Real-pipeline, controlled-outcome, contract, wording, provenance, mutation, ordering, isolation, and cross-process checks pass. |
| 7.4 Build the initial interface | In progress | Blocks 7.4a–7.4b complete: the Flask shell and semantic templates pass 14 focused and 137 full tests; review Block 7.4c visual implementation next. |
| 7.5 Validate and close Block 7 | Pending | Confirm readable, deterministic, evidence-backed output and reproducible setup instructions. |

Planning boundaries:

- no proposal-specific compliance evaluation;
- no building-envelope, remaining-coverage, or maximum-floor-area calculation;
- no corner-lot classification;
- no ADU, SB 9, parking, overlay, density-bonus, or state-law expansion;
- no AI-generated runtime conclusions; and
- no new database or replacement of the accepted Block 6 contract.

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
| 2026-07-16 | Maintain a dedicated supported-regulations catalog before redesigning schema v2. | Regulation meaning and product support boundaries should be explicit before deciding their machine-readable representation. |
| 2026-07-16 | Keep jurisdiction-specific values and schema field designs out of the capability catalog. | Values belong to versioned rulesets, while representation belongs to schema design; separating them prevents duplicated sources of truth. |
| 2026-07-16 | Adopt zone-first v2 rules with independent per-zone identities. | Direct capability lookup is deterministic, while independently amendable zone rules no longer share one legal identity merely because current values match. |
| 2026-07-16 | Represent setbacks as base values plus typed adjustments. | Explicit triggers, total-versus-additional effects, paired values, and precedence prevent prose-dependent or ambiguous stepback interpretation. |
| 2026-07-16 | Add schema v2 beside the operational v1 contract. | Preserves the validated v1 ruleset until migration and expanded cross-record validation are complete. |
| 2026-07-16 | Map every catalog capability to a standalone rule or embedded typed structure. | Gives humans and AI one unambiguous authoring path while allowing supporting behaviors such as stepbacks and paired yards to remain inside their parent setback rule. |
| 2026-07-17 | Migrate v1 into a separate non-overwriting v2 candidate with a complete crosswalk. | Makes the transformation reproducible and reviewable while preserving the approved operational v1 artifact until the expanded validation gate passes. |
| 2026-07-17 | Maintain cross-cutting deferred enhancements in `docs/future-improvements.md`. | Preserves useful design observations without duplicating active status, regulatory capability scope, or detailed contracts across project documents. |
| 2026-07-17 | Separate candidate validity from runtime eligibility. | Allows unapproved v2 data to pass structural and semantic review while preventing runtime use until the whole version is approved, dated, and all selected rules are approved. |
| 2026-07-17 | Limit v2 operational semantics to cataloged prototype capabilities even when the schema supports future shapes. | Height-triggered and additive setbacks remain representable for future work but cannot silently enter the current R1 runtime contract. |
| 2026-07-17 | Promote the reviewed candidate into separate immutable ruleset v2 version `2026-07-17.2`. | Preserves the exact reviewed candidate while recording explicit project-owner approval and providing a runtime-eligible source for Block 6. |
| 2026-07-17 | Version the Block 6 output contract separately from regulatory data. | `contract_version` describes result shape and semantics, while `ruleset_version` identifies the regulations; a separate engine version is deferred until meaningful evaluation logic exists. |
| 2026-07-18 | Validate and freeze the approved JSON ruleset once at application startup. | Keeps JSON authoritative for the prototype, prevents per-address revalidation and accidental mutation, and leaves storage replaceable by a future database-backed repository. |
| 2026-07-18 | Require exact zone keys and retrieve every approved rule without parcel-fact filtering. | GIS already establishes the canonical zone; preserving lot-context and story applicability avoids guessing whether a parcel is a corner lot or what a proposal contains. |
| 2026-07-18 | Keep address orchestration thin and preserve Block 5 failures without regulatory attachment. | Regulations are safe to retrieve only after one unambiguous parcel and current-zoning match; regulatory integrity failures are system errors, not parcel-specific review outcomes. |
| 2026-07-18 | Close Block 6 with one canonical real address per supported regulatory branch instead of arbitrary parcel sampling. | After exact zoning resolution, same-zone parcels retrieve the same base-zone rules; stronger contract, provenance, failure, mutation, and cross-process determinism checks add more distinct coverage. |
| 2026-07-18 | Put a pure UI-neutral presenter between Block 6 and the first interface. | Keeps display wording and grouping testable while preventing frontend code from interpreting raw regulations or maintaining duplicate values. |
| 2026-07-18 | Use a brief template-derived zone overview for the current prototype. | The approved ruleset has no source-backed per-zone narrative; the presenter can safely compose existing zone, use, approval, scope, and disclaimer fields without inventing suffix meanings. |
| 2026-07-18 | Build toward a shared regulatory core with controlled jurisdiction extensions. | Common semantics and renderers should be reusable across cities, while unique local rules remain typed, source-backed, validated, and visible instead of being forced into a near-match or silently omitted. |
| 2026-07-18 | Approve UI-neutral presentation contract `1.0.0`. | Fixes deterministic success and failure semantics, controlled wording, display order, provenance linkage, source behavior, and version mapping before presenter implementation begins. |
| 2026-07-18 | Use explicit capability and requirement dispatch in the presenter. | Shared capability mappings remain deterministic and ordered; unknown capabilities, status codes, and setback shapes fail visibly rather than being guessed or omitted. |
| 2026-07-18 | Keep integrity-error adaptation separate from pure result presentation. | The presenter stays stateless and fail-closed, while a deliberate application boundary can produce a safe `system_error` view without exposing internal details. |
| 2026-07-18 | Require every project-resolved display rule to retain its conflict reference. | Prevents a presentation mutation or malformed input from hiding the competing source assertions behind a selected project value. |
| 2026-07-18 | Validate presenter determinism with reordered inputs, mutated authoritative values, and independent hash-seeded processes. | Proves that presentation order is deliberate, regulatory values are not hard-coded, and identical versioned inputs serialize identically across processes. |
| 2026-07-18 | Use a scroll-first local web interface with expandable secondary detail. | Keeps the main planning answer immediately visible while making limitations, source receipts, and versions inspectable without dominating the page. |
| 2026-07-18 | Use Flask 3.1.3, Jinja, custom CSS, and one read-only address route for the prototype interface. | Preserves the existing synchronous Python pipeline, provides precise semantic and visual control, and avoids a separate API, frontend build system, database, or duplicated client-side regulatory state. |
| 2026-07-18 | Load or inject one pipeline at Flask application creation and catch only known integrity failures at the route boundary. | Avoids repeated snapshot and ruleset loading, keeps tests isolated, produces approved system-error views, and prevents programming defects from being mislabeled as zoning outcomes. |
