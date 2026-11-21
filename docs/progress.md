# Residential Zoning Expansion Progress

**Last updated:** November 20, 2026

**Current position:** Residential expansion Blocks 0-6 remain complete and released as `v0.2.0`; post-release Blocks 7-10 are complete, locally validated, and owner accepted; the normal `v0.3.0` PR, hosted CI, merge, and release gates are in progress

**Next action:** Commit and publish the accepted Blocks 7-10 branch, then complete the normal PR, hosted CI, guarded merge, and `v0.3.0` release-record gates

This is the sole active project-status ledger. Scope, architecture, and block exit conditions live in `docs/residential-expansion-plan.md`. The completed R1 ledger is preserved at `docs/progress-archive/2026-07-18-r1-prototype-progress.md`.

On November 20, 2026, the project owner requested removal of the **How to use this result** row. The local result now goes directly from **Property Overview** to residential uses. All 47 web tests passed with `python -m unittest discover -s tests -p "test*web.py"`. A live lookup for `1240 White Drive` confirmed the section order and a working source link.

## Baseline and active scope

- Released baseline: `v0.1.0-r1-prototype`, merged through PR #1.
- Current product release: `v0.2.0`, with the residential implementation merged through PR #2 and the final release record tagged from `main`.
- Completed expansion branch: `codex/residential-zone-expansion`.
- Target citywide zones: `R1-6L`, `R1-8L`, `R2`, `R3`, `R4`, `R5`, and `R6`.
- Target Patrick Henry designations: `PH-R5`, `UV`, `VR`, `UC`, and GIS designation `HDF`.
- Target structure identities: single-family, two-family, and multifamily primary structures.
- Target regulations: the existing use, approval, height, stories, coverage, and four setback families plus the approved base-zone gross residential density range, with only the minimum additional dispositions needed for no maximum listed, FAA-controlled, plan-dependent, not evaluated, and review-required results.
- Commercial analysis and additional regulation families remain outside the phase.

## Canonical artifacts

- Citywide address snapshot: `data/raw/2026-07-16/santa_clara_address_points/manifest.json`
- Released R1 parcel and zoning snapshot: `data/raw/2026-07-14/santa_clara_r1_gis/manifest.json`
- Residential parcel and zoning snapshot: `data/raw/2026-07-18/santa_clara_residential_gis/manifest.json`
- Released zoning-code and amendment snapshot: `data/raw/2026-07-16/santa_clara_zoning_code/manifest.json`
- Adopted Patrick Henry plan snapshot: `data/raw/2026-07-18/patrick_henry_drive_specific_plan/manifest.json`
- Approved R1 ruleset: `rulesets/santa_clara/r1/2026-07-17.2/ruleset.json`
- Accepted R1 migration schema: `rulesets/schema/ruleset-v3.schema.json`
- Additive citywide schema: `rulesets/schema/ruleset-v3.1.schema.json`
- Additive density schema: `rulesets/schema/ruleset-v3.2.schema.json`
- Nonruntime migrated R1 v3 candidate: `rulesets/santa_clara/residential/2026-07-19.1/ruleset.json`
- Approved-v2-to-candidate-v3 crosswalk: `rulesets/santa_clara/residential/2026-07-19.1/migration-crosswalk.json`
- Nonruntime R1-R6 v3.1 candidate: `rulesets/santa_clara/residential/2026-07-19.2/ruleset.json`
- R1-candidate-to-citywide expansion crosswalk: `rulesets/santa_clara/residential/2026-07-19.2/citywide-expansion-crosswalk.json`
- Nonruntime R1-R6 v3.2 density candidate: `rulesets/santa_clara/residential/2026-07-19.3/ruleset.json`
- Citywide-candidate-to-density expansion crosswalk: `rulesets/santa_clara/residential/2026-07-19.3/density-expansion-crosswalk.json`
- Patrick Henry source and decision supplement: `docs/patrick-henry-rule-verification-supplement.md`
- Complete nonruntime 12-zone v3.2 candidate: `rulesets/santa_clara/residential/2026-07-19.4/ruleset.json`
- Density-candidate-to-Patrick-Henry expansion crosswalk: `rulesets/santa_clara/residential/2026-07-19.4/patrick-henry-expansion-crosswalk.json`
- Approved runtime-eligible 12-zone v3.2 ruleset: `rulesets/santa_clara/residential/2026-07-19.5/ruleset.json`
- Candidate-to-approved promotion crosswalk: `rulesets/santa_clara/residential/2026-07-19.5/approval-crosswalk.json`
- Accepted residential result-contract checkpoint: `contracts/residential-result-contract-2.0.0.schema.json`
- Runtime-ready residential result contract: `contracts/residential-result-contract-2.1.0.schema.json`
- Reproducible runtime bundle: `demo-data/santa-clara-r1-runtime-data-2026-07-18.1.zip`
- Preserved residential GIS-only add-on: `demo-data/santa-clara-residential-runtime-data-2026-07-19.1.zip`
- Preserved residential GIS-only add-on manifest: `demo-data/residential-bundle-manifest.json`
- Source-complete residential runtime add-on: `demo-data/santa-clara-residential-runtime-data-2026-07-19.2.zip`
- Source-complete residential add-on manifest: `demo-data/residential-bundle-manifest-2026-07-19.2.json`
- Versioned zone-description catalog: `data/presentation/santa_clara/residential/2026-07-23.1/catalog.json`
- Zone-description authoring guide: `docs/zone-description-authoring-guide.md`
- Whole-project report: `docs/santa-clara-zoning-explorer-report.md`
- Full R1 validation and decision record: `docs/progress-archive/2026-07-18-r1-prototype-progress.md`

The released R1 artifacts remain the immutable inherited baseline. The Patrick Henry and residential GIS snapshots are Block 1 expansion artifacts and must likewise remain immutable.

## Milestone tracker

| Block | Status | Exit evidence or next result |
|---|---|---|
| 0. Establish the transition contract | Complete | The R1 ledger is archived; the expansion plan, fresh active ledger, and durable instructions establish the new phase without code or runtime-data changes. |
| 1. Verify sources and acquire residential GIS | Complete | The checked source matrix, Patrick Henry source, explicit `HDF` crosswalk, Patrick Henry rear disposition, immutable 18,677-feature-per-layer GIS snapshot, and real/synthetic fixture inventory passed their technical gates and received project-owner approval on July 19, 2026. |
| 2. Generalize the data and result contracts | Complete and owner accepted | Schema v3, domain and GIS-fixture gates, the deterministic 20-rule R1 migration and crosswalk, structured limitations, special pathways, result contract `2.0.0`, eight executable status fixtures, and 38 focused tests passed; the project owner accepted the implementation on July 19, 2026. |
| 3. Author and approve residential rules | Complete and owner accepted | The accepted `.4` candidate was promoted without semantic change into immutable ruleset `2026-07-19.5`; all 196 rules and two pathways are approved, the complete lineage replays, and runtime eligibility passes. |
| 4. Expand lookup and retrieval | Complete and owner accepted | The complete backend passed its exact matrix, approved-artifact, released-R1, determinism, complete-suite, and scope-boundary gates; the project owner accepted Block 4 on July 19, 2026. |
| 5. Generalize presentation and interface | Complete and owner accepted | The default application presents semantically shared zone standards immediately, lists residential types and conditional topics separately, preserves R1 special pathways as backend data without presenting their unavailable analysis, and retains exact selection only as backend/future infrastructure. Owner review covered the generalized desktop and responsive interface and accepted the source cleanup, manual test sheet, and faint responsive `YIMBY` hero easter egg on July 19, 2026. |
| 6. Validate and release | Complete and owner accepted | Source-complete startup, consolidated release acceptance, clean-checkout CI, the accessible report, the final local matrix, PR #2, and post-merge `main` validation all pass. Release `v0.2.0` records the resulting Santa Clara Zoning Explorer residential product without modifying the preserved R1 baseline. |
| 7. Add local address autocomplete | Complete and owner accepted | The startup-loaded 67,243-record citywide index, bounded same-origin endpoint, strict public response boundary, and accessible auto-submit combobox pass unit, integration, browser, clean-checkout, release-harness, complete-suite, bundle, validator, and whitespace gates without changing zoning-analysis or regulatory artifacts. |
| 8. Add supported parcel context maps | Complete and owner accepted | The startup-loaded residential geometry supplies bounded same-origin GeoJSON for exact supported results; the responsive Leaflet map, distinct 12-zone categorical palette, selected-parcel emphasis, tile-independent fallback, strict public response boundary, complete repository suite, clean-checkout reconstruction, release harness, validators, and bundle reproduction pass without changing zoning analysis or regulatory artifacts. |
| 9. Add exact regulatory source evidence | Complete and owner accepted | The validated 443-target evidence sidecar, exact highlighted source locations, checksummed local assets, secure evidence routes, accessible dedicated viewer, bootstrap add-on, complete suite, release harness, validators, and deterministic bundle reproduction pass without changing approved rules or zoning conclusions. |
| 10. Add source-grounded zone overviews | Complete and owner accepted | The versioned 12-zone presentation catalog, offline authoring contract, startup-loaded provider, safe factual fallback, concise Property Overview, separate result guidance, complete suite, release harness, validators, bundle reproduction, and desktop/mobile browser checks pass without runtime AI or regulatory changes. |

## Block 0 evidence

Created or transitioned:

- `docs/residential-expansion-plan.md`
- `docs/progress.md`
- `docs/progress-archive/2026-07-18-r1-prototype-progress.md`
- `AGENTS.md`
- the R1 prototype report's link to its archived validation ledger

Historical R1 plans, verification records, rulesets, schemas, scripts, tests, and release artifacts retain their existing names and contents. Their R1/prototype terminology identifies the released baseline and is not active product copy to be mechanically renamed.

No application code, ruleset, schema, source snapshot, dependency, command, or runtime behavior changed in Block 0.

Documentation validation:

- the archived ledger body matches the former active ledger from `## Post-prototype release readiness` through the final decision-log entry;
- the prototype report now links to the archived R1 validation record;
- active instructions and status references resolve to the residential expansion documents; and
- `git diff --check` passes.

## Block 1 evidence and approval

Created and reviewed:

- `docs/residential-rule-verification.md`, the active new-zone source trace and approval gate;
- an exact 12-designation citywide and Patrick Henry target map, including an explicit candidate `HD Flex`/`HD-Flex` to `HDF` crosswalk;
- the legal-use and primary-structure matrix for single-family, two-family, and multifamily selections;
- base height, story, coverage, and setback assertions from the correct Table 2-3 and Table 2-4 columns;
- explicit candidate handling for no maximum listed, FAA-controlled, plan-dependent, `not evaluated`, and review-required outcomes;
- a complete residential GIS acquisition contract covering exact filters, object IDs, batch limits, raw responses, checksums, zero-count zones, excluded designations, cross-layer count agreement, and failed manifests; and
- a fixture-selection contract that separates real-address coverage from synthetic ruleset coverage.

Source work performed:

- read the candidate Google Drive Residential Zoning Research, Rule Inventory, and supplemental watchlist without treating them as approval sources;
- checked the preserved 497-page July 2025 Title 18 PDF, including visually verifying Tables 2-1 through 2-4 against their correct zone columns;
- rechecked later Title 18 legislation through July 18 and created `docs/residential-title18-amendment-audit.md` for multifamily applicability and the proposed `TN`-to-`R6` map trigger, while preserving the checksum-pinned R1 audit byte-for-byte;
- checked the official Patrick Henry page and adopted-plan identity;
- retrieved the project-owner-provided official Patrick Henry plan from Google Drive, preserved its 21,816,482 bytes and 191 pages in a non-overwriting raw snapshot, verified SHA-256 `cefd7df91819c61d26b5cdddd0d395b74445078f2dc6e0d57995dc6992b16b87`, and visually checked the controlling Table 4.2 and Table 4.3 columns;
- verified Chapter 18.24 and the Title 18 dwelling, primary-structure, and structure-coverage definitions, including the distinction between one two-family structure and the R1 pathway's attached-or-detached two-home configurations; and
- queried both official ArcGIS zoning-bearing layers with the exact proposed residential filter.

Implemented and preserved:

- `scripts/download_residential_gis.py`, a new non-overwriting multi-zone acquisition path that leaves the released R1 downloader intact;
- `tests/test_residential_gis_downloader.py`, covering exact scope, GET batch bounds, complete evidence, duplicate and unexpected data, cross-layer disagreement, failure manifests, overwrite refusal, and fixture closure;
- `data/raw/2026-07-18/santa_clara_residential_gis/manifest.json`, the ignored immutable raw snapshot with 18,677 validated features in each source layer;
- `tests/fixtures/residential_gis_fixture_inventory.json`, with one source- and geometry-verified real address for every live target designation, synthetic zero-count R5/R6 fixtures, and synthetic negative fixtures for the three excluded exact codes; and
- README commands and repository orientation for the residential downloader, while retaining the historical R1 downloader and released runtime instructions.

July 18 immutable ArcGIS evidence:

- both layers returned 18,677 target features and identical per-zone counts;
- exact counts included `R1-6L: 15,757`, `R1-8L: 436`, `R2: 752`, `R3: 1,685`, `R4: 2`, `PH-R5: 2`, `UV: 9`, `VR: 27`, `UC: 2`, and `HDF: 5`;
- exact `R5` and `R6` counts were zero in both layers; they remain legal and synthetic rule targets, not real-address fixtures;
- deliberately excluded exact designations were also observed in both layers: `R1-6LHT: 14`, `R2-7L: 1`, and `R2HT: 2`; and
- the matching preflight observations were not used as hardcoded acceptance values; the immutable acquisition independently preserved and validated the source results returned at retrieval time.

The completed snapshot reproduced those observations exactly. It preserved 187 GET feature batches per layer plus metadata, object-ID responses, and 15 per-designation count responses per layer. Independent post-download verification re-read all 410 recorded evidence files and found no size or checksum mismatch. Canonical outputs are:

- `parcels_residential.geojson`: 14,191,101 bytes; SHA-256 `e31ce5afb81c717ddcbd639c17b57a4625bcf257175a14cc03a09bfc90f5ecc3`;
- `current_zoning_residential.geojson`: 16,554,895 bytes; SHA-256 `cb18cf0a8f7b2ebc8754334285b0f73e3160ca7d7f3fc64eeb6df3963b23f862`; and
- `manifest.json`: SHA-256 `f71138d11eabdff773cb3f8fe156a41d0940b1adde72370f9bbab74a397aeb38`.

Selected real-address fixtures are 636 Barto Street (`R1-6L`), 108 Brookside Avenue (`R1-8L`), 1240 White Drive (`R2`), 1577 Pomeroy Avenue (`R3`), 1400 Coleman Avenue (`R4`), 3105 Patrick Henry Drive (`PH-R5`), 3200 Patrick Henry Drive (`UV`), 4701 Patrick Henry Drive (`VR`), 4650 Old Ironsides Drive (`UC`), and 4633 Old Ironsides Drive (`HDF`). Each address point intersects exactly one parcel and current-zoning feature with matching exact designations. Both R4 features and every small Patrick Henry group were inspected before selection; fixtures test routing and do not establish legal permission.

The source and acquisition work added developer tooling and fixture data, but did not change application runtime code, schemas, rulesets, dependencies, or user-visible behavior. The Block 1 evidence is project-owner approved as input to contract design; new-zone assertions remain non-runtime candidate data until the later representation, validation, rule-authoring, and approval gates pass.

## Block 2 contract audit, design, and implementation

The read-only audit covered:

- `rulesets/schema/ruleset-v2.schema.json` and the immutable approved R1 v2 ruleset and crosswalk;
- `scripts/migrate_r1_rules_v2.py` and `scripts/validate_r1_rules_v2.py`;
- the approved capability catalog and ruleset authoring guide;
- runtime ruleset loading, exact-zone retrieval, lookup orchestration, pipeline result contract, deterministic presenter, Flask boundary, and rendered templates; and
- schema, domain, migration, loader, retrieval, pipeline, presentation, web, and vertical-slice tests.

The audit found that the reusable v2 foundations are zone ownership, independent rule identities, shared provenance, typed setbacks, conflict preservation, runtime eligibility, immutable loading, defensive copies, and fail-closed behavior. The expansion pressure comes from closed assumptions around exactly two zones, one structure type, ten rules per zone, numeric maximums and setbacks, immediate retrieval after address lookup, fixed R1 statuses, a single-family presentation summary, and global prose-only limitations.

The approved design is recorded in Section 10 of `docs/residential-expansion-plan.md`. It establishes:

- a separate residential ruleset/schema `3.0.0` lineage, preserving v1, v2, and the approved R1 artifact;
- exact zone-owned `use_permissions`, ordinary `analysis_profiles`, and separate `special_pathways`;
- one explicit `permitted_by_right` or `not_listed` use-permission treatment for every single-family, two-family, and multifamily matrix cell, with special pathways represented separately from permission status;
- independent profile-owned approvals and dimensional rules selected through one exact profile ID;
- typed no-maximum-listed, FAA-controlled, plan-dependent, not-evaluated, and review-required requirement kinds within the existing regulation families;
- structured, profile-specific not-evaluated topics without promoting deferred standards into evaluated capabilities;
- pipeline result contract `2.0.0`, separating address/zone resolution from an explicit analysis selection; and
- an exhaustive approved-v2-to-v3 R1 crosswalk and semantic equivalence gate.

The project owner approved this proposal on July 19, 2026. Implementation remains gated so that a schema-valid partial candidate can exercise migration and contract semantics without becoming runtime eligible; the later runtime-eligibility gate requires the complete exact 12-zone matrix and project approval.

No application code, schema, validator, ruleset, migration, source snapshot, dependency, command, test behavior, or user-visible output changed during the preceding audit and proposal step.

Proposal validation evidence:

- `git diff --check` passes;
- `.venv/bin/python -m unittest discover -s tests -q` passes all 167 tests;
- `.venv/bin/python scripts/validate_r1_rules_v2.py --ruleset rulesets/santa_clara/r1/2026-07-17.2/ruleset.json --crosswalk rulesets/santa_clara/r1/2026-07-17.2/migration-crosswalk.json --verify-source-files --require-runtime-eligible` confirms all 20 approved R1 regulations, the preserved conflict, complete migration crosswalk, source checksums, and runtime eligibility; and
- focused stale-state scans find no remaining claim in the active plan or ledger that Block 2 is unstarted, Block 1 still awaits approval, `special_pathway` is a use-permission status, or a source-table `not_listed` cell means prohibited.

Implementation artifacts and behavior:

- `docs/regulations/residential-ruleset-authoring-guide.md` preserves the released v2 guide and owns the active v3 representation, authoring, migration, and approval contract;
- `rulesets/schema/ruleset-v3.schema.json` closes the zone/use/profile/pathway hierarchy and the numeric and nonnumeric requirement shapes;
- `scripts/validate_residential_rules_v3.py` enforces exact target identities, the complete approved use/profile matrix for every included zone, capability-compatible requirement kinds, provenance and conflict closure, partial-candidate versus complete-runtime gates, R5/R6 zero-count fixtures, and excluded-designation handling;
- `scripts/migrate_r1_rules_v3.py` deterministically consumes the immutable approved v2 ruleset and emits the nonoverwriting `2026-07-19.1` candidate and exhaustive crosswalk;
- the candidate contains two R1 zones, six explicit use-permission records, 18 ordinary single-family profile regulations, two Chapter 18.24 special pathways, 11 structured not-evaluated topics, and the preserved R1-8L conflict;
- the crosswalk maps all 20 approved v2 rules and all ten predecessor scope limitations exactly once, records the new contract-only records, and proves byte-identical replay plus canonical R1 semantic equivalence;
- `contracts/residential-result-contract-2.0.0.schema.json`, `scripts/validate_residential_result_contract.py`, and `tests/fixtures/residential_result_contract_cases.json` encode all eight approved result statuses and bar regulations from every outcome except an exact selected ordinary profile; and
- no R2-R6 or Patrick Henry numeric value was authored, no production module was changed, no residential GIS snapshot was loaded at runtime, and no user-visible output changed.

Canonical Block 2 checksums:

- schema v3: `5368aeb987caab94d7e8cafe5f4d34bc9f637661b7077bfb03108ea1129ecd8c`;
- migrated candidate: `ad8f0ddb3eda82c724ae0c50fb23a89591ae78b72fab58e10868698eac4ed2ff`;
- migration crosswalk: `084d3da4c34ead935f8b33c44df7821d69c7751b1f696108b9b7b898317c8c69`;
- result-contract schema: `d1b74bd2df940d3dab8c9d36c03577e5467d2d1abb1903cbd4ac3d442b7a41d1`; and
- executable case inventory: `bb3bb3d595575b6e00176e37bceef36e7d74999ffad63af0c6e6e26f96bc4438`.

Implementation validation evidence:

- `.venv/bin/python -B scripts/validate_residential_rules_v3.py --verify-source-files` passes schema, domain, source checksum, GIS-fixture, complete crosswalk, deterministic replay, and R1 semantic-equivalence gates;
- the same validator with `--require-runtime-eligible` fails closed as expected because the candidate lacks ten target zones, runtime approval, approved records, and approved pathways;
- `.venv/bin/python -B scripts/validate_residential_result_contract.py` passes all eight nonruntime result fixtures;
- `.venv/bin/python -B -m unittest discover -s tests` passes all 205 tests, including 38 new v3 schema, domain-mutation, GIS-fixture, migration, equivalence, and result-contract tests;
- the released R1 v2 validator continues to pass all schema, domain, source, migration, and runtime-eligibility gates; and
- `git diff --check` passes.

## Block 3 citywide R2-R6 authoring evidence

The citywide tranche is implemented as a new direct successor rather than an edit to the accepted Block 2 checkpoint:

- `rulesets/schema/ruleset-v3.1.schema.json` preserves the closed v3 hierarchy and adds only `lot_area_tiered_maximum` within maximum structure coverage, plus exact source-document verification statuses for the approved matrix and adopted enactment;
- `scripts/author_citywide_residential_rules.py` consumes immutable candidate `2026-07-19.1`, preserves its R1 zones and inherited records, and deterministically authors nonoverwriting candidate `2026-07-19.2` plus its expansion crosswalk;
- `scripts/validate_citywide_residential_rules.py` validates the entire approved-v2-to-v3.0-to-v3.1 lineage, both schema/domain contracts, local source checksums, deterministic replays, exact inherited R1 preservation, and the GIS fixture contract;
- candidate `2026-07-19.2` contains seven exact zones, 21 explicit use-permission records, 11 ordinary profiles, 99 profile regulations, two preserved R1 special pathways, 17 structured not-evaluated topics, and the preserved R1-8L conflict;
- the added citywide tranche contributes 15 use-permission records, nine ordinary profiles, and 81 independent profile regulations while retaining the same nine supported regulation families per profile;
- R2 includes single-family, two-family, and multifamily profiles; R3 and R4 include two-family and multifamily profiles; R5 and R6 include multifamily only, while all zones retain three explicit source-table permission cells;
- R3 and R4 coverage preserves separate outcomes below and at or above 10,000 square feet; R5 and R6 preserve `no_maximum_listed` rather than zero, infinity, or “unlimited”;
- the R1/R2 32-foot proximity transition is attached as `not evaluated` to R3-R6 profiles, and Ordinance 2085 Objective Design Standards are attached as `not evaluated` only to multifamily profiles; neither becomes a new evaluated regulation;
- R5 and R6 remain legal and synthetic contract targets with no invented address despite their zero live-feature counts; and
- the production loader, GIS lookup, standards retrieval, pipeline, presenter, templates, and frontend remain unchanged, so the released R1 application still loads only approved v2 data.

Canonical citywide-tranche checksums:

- schema v3.1: `7fa85189f1c8a1c5dbee3537cb494f2661ad80f77a1e9bda50e050f6f68e8103`;
- R1-R6 candidate: `57166a693fbab477fec631e251cc909541db912ee01e2a3ef2345dbbc06f0d94`; and
- citywide expansion crosswalk: `c8b7fcdba8ef4081cb2d02b68dd0c483f0812835a7074f33cc91fc57b1337c07`.

Validation evidence:

- `.venv/bin/python -B scripts/validate_citywide_residential_rules.py --verify-source-files` passes the complete chained lineage, schema, domain, source-checksum, matrix, replay, R1-preservation, and GIS-fixture gates;
- the same validator with `--require-runtime-eligible` fails closed as expected because `PH-R5`, `UV`, `VR`, `UC`, and `HDF` are absent, the candidate is not approved, and every candidate record remains unapproved;
- `.venv/bin/python -B scripts/validate_residential_rules_v3.py --verify-source-files` continues to validate accepted candidate `2026-07-19.1` and its original R1 migration byte-for-byte;
- `.venv/bin/python -B scripts/validate_r1_rules_v2.py --ruleset rulesets/santa_clara/r1/2026-07-17.2/ruleset.json --crosswalk rulesets/santa_clara/r1/2026-07-17.2/migration-crosswalk.json --verify-source-files --require-runtime-eligible` continues to validate the released 20-rule R1 artifact as runtime eligible;
- `.venv/bin/python -B scripts/validate_residential_result_contract.py` continues to pass all eight nonruntime result fixtures;
- `.venv/bin/python -B -m unittest discover -s tests -q` passes all 219 tests, including 14 new citywide matrix, tier semantics, source, approval, mutation, preservation, checksum, and deterministic replay tests; and
- `git diff --check` passes.

At this checkpoint, the R2-R6 tranche was ready for project-owner review but not runtime use. The later density, Patrick Henry, and approval successors preserve this candidate while completing the remaining Block 3 gates.

## Block 3 gross residential density evidence

The project owner approved adding base-zone gross residential density through the current nonruntime Block 3 stage and directed the project to retain the R5/R6 source conflicts while selecting the Table 1-1 values. The implementation preserves the accepted citywide checkpoint and creates a direct successor:

- `docs/residential-density-rule-verification.md` records the visually checked Table 1-1, zone-purpose, and Table 2-3 assertions, the capability boundary, and the July 19 project decisions without changing the checksum-pinned predecessor verification record;
- `docs/residential-density-title18-amendment-audit.md` records that no adopted post-baseline amendment identified through July 18 changes the selected R1-R6 ranges and preserves the internal baseline conflicts separately;
- `rulesets/schema/ruleset-v3.2.schema.json` adds only typed `quantity_range` requirements and conflict assertion values in `dwelling_units_per_acre`;
- `scripts/author_density_residential_rules.py` deterministically consumes immutable candidate `2026-07-19.2` and emits nonoverwriting candidate `2026-07-19.3` plus its density expansion crosswalk;
- `scripts/validate_density_residential_rules.py` validates the complete approved-v2-to-v3.0-to-v3.1-to-v3.2 lineage, source checksums, conflict consistency, deterministic replay, exact predecessor-rule preservation, and GIS fixtures;
- candidate `2026-07-19.3` contains the same seven zones, 21 use permissions, 11 ordinary profiles, and two R1 special pathways; it adds exactly 11 density rules for 110 total profile regulations and 131 total permission/regulation records;
- R1-6L and R1-8L use 0.1-10, R2 uses 8-19, R3 uses 20-36, and R4 uses 37-50 dwelling units per acre;
- R5 retains 51-100 from Table 1-1 against the 51-99 purpose/Table 2-3 assertions, and R6 retains 60-350 from Table 1-1 and the purpose text against Table 2-3's 85-350 assertion;
- the R5/R6 rules use `project_resolved_with_conditions`, and the conflict records identify project-owner direction rather than claiming an official City correction;
- density limitation topics now distinguish supported base-zone range retrieval from deferred parcel yield, plan reconciliation, density bonus, affordability, development-agreement, and state-law evaluation; and
- production loading, lookup, retrieval, pipeline, presentation, templates, and frontend remain unchanged.

Canonical density-tranche checksums:

- schema v3.2: `186204364b72f6aac4b8615030c874681c6aa5ea4fac976aff03214f7347c6ef`;
- R1-R6 density candidate: `7f54eb7569a007ce4b5bdac334aa3fd051990937df2717e270960cdde6e426d6`; and
- density expansion crosswalk: `4c0746efd77d061a00f9a7b54186eb61cdd513b520531c57847d29f3ef28ec4e`.

Validation evidence:

- `.venv/bin/python -B scripts/validate_density_residential_rules.py --verify-source-files` passes the complete schema, domain, source-checksum, conflict, chained-lineage, deterministic-replay, preservation, and GIS-fixture gates;
- the same validator with `--require-runtime-eligible` fails closed as expected because five Patrick Henry zones are absent, the artifact is a candidate, and its rules remain unapproved;
- `.venv/bin/python -B -m unittest tests.test_density_residential_rules -v` passes 12 new source-matrix, conflict, range-shape, mutation, preservation, checksum, runtime-boundary, and replay tests;
- `.venv/bin/python -B -m unittest discover -s tests -q` passes all 231 tests; and
- `git diff --check` passes.

The project owner accepted candidate `2026-07-19.3` on July 19, 2026 and authorized Patrick Henry authoring using the same conflict-preservation and Table 1-1 selection policy for PH-R5. The checkpoint remains nonruntime and immutable.

## Block 3 Patrick Henry authoring evidence

The Patrick Henry tranche preserves accepted density candidate `2026-07-19.3` and creates a direct schema-`3.2.0` successor without adding a regulation family:

- `docs/patrick-henry-rule-verification-supplement.md` checksum-pins the final visual reconciliation of Title 18 and the adopted plan, records the accepted PH-R5 density policy, and keeps commercial and office analysis outside the tranche;
- `scripts/author_patrick_henry_residential_rules.py` deterministically consumes immutable candidate `2026-07-19.3` and emits nonoverwriting candidate `2026-07-19.4` plus its expansion crosswalk;
- `scripts/validate_patrick_henry_residential_rules.py` validates the complete approved-v2-to-v3.0-to-v3.1-to-v3.2 lineage, both v3.2 successors, source checksums, deterministic replay, exact predecessor preservation, the full 12-zone matrix, and GIS fixtures;
- candidate `2026-07-19.4` contains 12 zones, 36 use permissions, 16 ordinary profiles, two R1 special pathways, 160 profile regulations, and 196 total permission/regulation records;
- each of `PH-R5`, `UV`, `VR`, `UC`, and `HDF` contains only one multifamily profile and the same ten supported regulation capabilities already used by the predecessor;
- all five zones record single-family and two-family as `not_listed` and multifamily as `permitted_by_right`, while keeping use status separate from Zoning Clearance, Architectural Review, hearing, and plan-conformance requirements;
- PH-R5 uses 135 feet, 10 stories, no coverage maximum listed, 10-foot front/street-side/interior-side setbacks from back of walk, a plan-dependent rear setback, and project-selected density of 51-100 DU/AC;
- UV uses 160 feet, 12 stories, and 100-149 DU/AC; VR uses 160 feet, 12 stories, and 60-149 DU/AC; UC preserves literal FAA-controlled height and stories with 120-250 DU/AC; and HDF uses 160 feet, 12 stories, and 60-149 DU/AC;
- the PH-R5 conflict separately retains Title 18 Table 1-1's 51-100 assertion and four 51-99 assertions from the zone-purpose text, Title 18 Table 2-4, Specific Plan Section 4.3.2, and Specific Plan Table 4.2, with the Table 1-1 range selected only by explicit project policy;
- every Patrick Henry rear setback remains `plan_dependent`, never zero, and every coverage result remains `no_maximum_listed`, never unlimited;
- the 32-foot transition, recreation space, detailed encroachments, plan design/project review, Objective Design Standards, UC above-250 community-benefits path, HDF office option, and density adjustments remain structured `not evaluated` qualifications rather than new rules; and
- the production loader, GIS lookup, retrieval, pipeline, presentation, templates, and frontend remain unchanged.

Canonical Patrick Henry tranche checksums:

- preserved schema v3.2: `186204364b72f6aac4b8615030c874681c6aa5ea4fac976aff03214f7347c6ef`;
- Patrick Henry verification supplement: `7aab62cc482fe462c5430006556e383fe7cb54fe70b05499661f326c7ca3659f`;
- complete 12-zone candidate: `7e4261277aeb527cd479249a6f580cb6006f5e186c911106c9d4ab9f9ce734b7`; and
- Patrick Henry expansion crosswalk: `e6f789acf82d79ff3ab9dfff462d05779349bab19c3286d1b60a926708fbefea`.

Validation evidence:

- `.venv/bin/python -B scripts/validate_patrick_henry_residential_rules.py --verify-source-files` passes the complete schema, domain, source-checksum, conflict, chained-lineage, deterministic-replay, preservation, 12-zone, and GIS-fixture gates;
- the same validator with `--require-runtime-eligible` fails closed as expected because the complete artifact remains a candidate with null approval and unapproved rules and pathways, not because any target zone is missing;
- `.venv/bin/python -B -m unittest tests.test_patrick_henry_residential_rules -v` passes 14 new matrix, source, conflict, nonnumeric-disposition, limitation, mutation, preservation, checksum, runtime-boundary, and replay tests;
- `.venv/bin/python -B -m unittest discover -s tests -q` passes all 245 tests; and
- `git diff --check` passes.

This evidence made candidate `2026-07-19.4` ready for project-owner review. The subsequent approval promotion below closes Block 3 without altering that reviewed checkpoint.

## Block 3 complete-candidate approval and runtime promotion

The project owner approved complete candidate `2026-07-19.4` on July 19, 2026. Approval is recorded as a new immutable successor rather than an in-place edit:

- `scripts/promote_residential_rules_v3.py` revalidates the complete candidate, its Patrick Henry replay, local sources, and the candidate's expected fail-closed runtime state before writing anything;
- approved ruleset `2026-07-19.5` retains schema `3.2.0`, all 12 zones, 36 use permissions, 16 profiles, 160 profile regulations, two special pathways, four conflicts, every source and citation, every selected value, and every condition and limitation from `.4`;
- the promotion changes only the immutable version and lifecycle metadata, predecessor/crosswalk pointer, scope lifecycle wording, and `approved_for_ruleset` flags on the 196 rules and two pathways;
- `approval-crosswalk.json` pins the source, target, and schema checksums, records the owner decision, counts all 198 approval-bearing records, and records a checksum of the regulatory-semantic projection shared by `.4` and `.5`;
- `scripts/validate_approved_residential_rules.py` validates the complete approved-R1-v2 through residential-v3.2 lineage, every deterministic authoring replay, source-file integrity, GIS fixtures, the approval replay, semantic preservation, and runtime eligibility in one command; and
- production application modules remain unchanged. Runtime eligibility makes `.5` valid input for Block 4 integration; it does not silently switch the released R1 loader or user experience.

Canonical approval checksums:

- approved 12-zone ruleset: `ed72cfd24cc43755ddcfbcf566a2c6212592155bb491807cb747748addbb05c4`;
- approval crosswalk: `778dd129b35fdd4026a76b6b5cf40c875d26795daadff0dcfe7827bd556e4e5b`;
- preserved reviewed candidate: `7e4261277aeb527cd479249a6f580cb6006f5e186c911106c9d4ab9f9ce734b7`;
- preserved Patrick Henry crosswalk: `e6f789acf82d79ff3ab9dfff462d05779349bab19c3286d1b60a926708fbefea`; and
- preserved schema v3.2: `186204364b72f6aac4b8615030c874681c6aa5ea4fac976aff03214f7347c6ef`.

Validation evidence:

- `.venv/bin/python -B scripts/validate_approved_residential_rules.py --verify-source-files` passes the complete source, schema, conflict, lineage, replay, semantic-preservation, GIS-fixture, per-record approval, and runtime-eligibility gates;
- `.venv/bin/python -B -m unittest tests.test_residential_rules_v3_approval -v` passes 10 approval, checksum, replay, immutability, and mutation tests, including rejection of an R5-density semantic change;
- `.venv/bin/python -B -m unittest discover -s tests -q` passes all 255 tests; and
- `git diff --check` passes.

Block 3 is complete and project-owner accepted. Block 4 may now integrate the approved residential artifact through the production loader and exact lookup/retrieval boundaries, but no user-visible expansion is claimed yet.

## Block 4 read-only runtime audit and proposal

The audit inspected the released R1 runtime and its focused regression boundaries without changing application behavior:

- `santa_clara_zoning/ruleset.py` and `tests/test_ruleset_loader.py` for artifact loading, v1-to-v2 replay, runtime eligibility, recursive freezing, mutation rejection, and defensive copies;
- `santa_clara_zoning/lookup.py`, the July 16 address manifest, the July 18 residential manifest, `tests/test_local_lookup.py`, and `tests/fixtures/residential_gis_fixture_inventory.json` for exact matching, manifest/checksum loading, spatial outcomes, all ten live target fixtures, R5/R6 zero counts, and excluded designations;
- `santa_clara_zoning/standards.py` and `tests/test_zone_standards.py` for exact-zone retrieval, approved-record checks, requirement-source traversal, and transitive provenance closure;
- `santa_clara_zoning/pipeline.py` and `tests/test_standards_pipeline.py` for orchestration, controlled failures, integrity exceptions, versioning, defensive output, and determinism;
- result contract `2.0.0`, its nonruntime `.1` fixture builder, eight fixture cases, and mutation tests; and
- the presentation, Flask, and vertical-slice boundaries to identify what Block 4 must leave unchanged until Block 5.

The detailed proposal is Section 11 of `docs/residential-expansion-plan.md`. Its principal conclusions are:

- add approved residential loader, lookup, selection-retrieval, and pipeline components alongside the released R1 public path;
- validate the complete `.5` lineage at load time rather than treating schema validity or the final approval flag as sufficient;
- use the ruleset's exact 12-zone identities to validate the filtered residential snapshot, while retaining synthetic-only R5/R6 retrieval coverage and never normalizing the three excluded designations;
- accept one exact selection ID and derive legal use, workflow family, and structure identity from the approved profile or pathway rather than accepting contradictory independent fields;
- preserve the eight approved result statuses and introduce a narrow immutable `2.1.0` contract successor before runtime wiring; and
- keep presentation, templates, frontend assets, and the default Flask application on the released R1 pipeline throughout Block 4.

The contract successor is necessary because the Block 2 fixtures deliberately use candidate `.1` and nine regulations, while approved `.5` profiles contain ten after density; the `2.0.0` outside-snapshot shape requires non-target parcel/zone facts absent from the filtered snapshot; and successful results currently omit the selected use-permission rule and its evidence. These corrections do not add a regulation, status, GIS source, or evaluation capability.

Read-only validation evidence:

- `.venv/bin/python -B -m unittest tests.test_ruleset_loader tests.test_local_lookup tests.test_zone_standards tests.test_standards_pipeline tests.test_residential_result_contract -q` passes all 47 focused current-runtime and contract tests; and
- `.venv/bin/python -B -m unittest discover -s tests -q` passes all 255 repository tests;
- `git diff --check` passes; and
- no application, ruleset, schema, contract, source snapshot, fixture, test, README, dependency, or user-visible file changed during the audit.

The project owner approved the proposal on July 19, 2026. Implementation began with the contract-successor tranche and remains bounded away from Block 5 presentation work.

## Block 4 tranche 4.1 result-contract implementation

Tranche 4.1 preserves accepted contract `2.0.0` and adds a separately versioned runtime-ready successor:

- `contracts/residential-result-contract-2.1.0.schema.json` keeps the same eight statuses and exact selection identities while adding one selected `use_permission` field;
- the successful ordinary-profile fixture uses the approved PH-R5 multifamily branch, including all ten supported capabilities, the base-zone density range, the retained density conflict, and exact transitive provenance;
- the special-pathway fixture carries the approved R1 two-family permission and remains explicitly `analysis_not_evaluated` without ordinary standards;
- the unavailable-profile fixture uses R3 single-family and carries the exact source-backed `not_listed` permission without treating it as a prohibition;
- the R2 zone-found fixture lists single-family, two-family, and multifamily selections in deterministic order;
- outside-snapshot evidence retains the matched address but leaves parcel and zone null instead of guessing facts absent from the filtered GIS snapshot;
- an empty entered address is valid only for the controlled `address_not_found` result; and
- every result carries non-null address-snapshot, residential-GIS, ruleset, ruleset-schema, and result-contract versions.

`scripts/validate_residential_result_contract_v2_1.py` builds the eight cases directly from runtime-eligible ruleset `2026-07-19.5`, strips authoring-only approval flags from selected output, verifies exact choices and branch bindings, requires complete topics/conflicts/provenance closure, rejects unknown profile identities without fuzzy matching, and domain-checks the fixture ruleset before use. The fixtures explicitly state that they are approved-ruleset contract cases and are not production-pipeline results.

Canonical tranche checksums:

- result contract `2.1.0`: `212aa17543cec4059e7d3b05ceb06a81a462f4481a9cba47e967f26046d6a0d0`;
- executable case inventory: `dd8c48666f08e5fe7f63bfe45ba7b43159190b8e834568588b3363d0d87cdcc8`.

Validation evidence:

- `.venv/bin/python -B scripts/validate_residential_result_contract_v2_1.py` validates all eight `2.1.0` cases against approved ruleset `.5`;
- `.venv/bin/python -B -m unittest tests.test_residential_result_contract tests.test_residential_result_contract_v2_1 -q` passes all 27 preserved and successor contract tests;
- `.venv/bin/python -B scripts/validate_approved_residential_rules.py --verify-source-files` passes the complete approved lineage, source, semantic-preservation, per-record approval, and runtime-eligibility gates;
- `.venv/bin/python -B -m unittest discover -s tests -q` passes all 271 repository tests; and
- `git diff --check` passes.

No production module, ruleset, ruleset schema, raw source snapshot, dependency, presentation component, template, static asset, or default Flask behavior changed. The project owner accepted tranche 4.1 and authorized the approved residential loader on July 19, 2026.

## Block 4 tranche 4.2 approved residential loader implementation

Tranche 4.2 adds a production-independent, fail-closed loader alongside the released R1 path:

- `scripts/validate_approved_residential_rules.py` now exposes `ResidentialRulesetArtifacts`, one exact loaded-lineage snapshot, and `validate_complete_approved_lineage()`; the existing CLI delegates to that same callable gate;
- the callable validates the approved R1 v2 input, migrated R1 v3.0 checkpoint, citywide v3.1 expansion, density v3.2 expansion, complete Patrick Henry candidate, `.4`-to-`.5` approval promotion, source files, GIS-fixture contract, deterministic replays, regulatory-semantic preservation, per-record approval, and runtime eligibility;
- dependent replay checks run only after their source and target artifacts pass schema/domain validation, so malformed or candidate targets fail with controlled evidence instead of crashing a later replay helper;
- `ApprovedResidentialRuleset.load()` reads all 16 required artifacts once, validates that loaded graph, recursively freezes the exact `.5` target that passed, and exposes only defensive mutable copies through `as_dict()`;
- the public loader reports exact identity and summary metadata: 12 supported zones in ruleset order, schema `3.2.0`, 196 use/profile rule records, 16 ordinary profiles, and two special pathways; and
- residential load failures reuse `RulesetLoadError` with explicit `artifact loading`, `complete lineage validation`, or `internal representation` stages and never fall back to candidate or partially validated data.

Focused mutation coverage rejects the complete `.4` candidate, an altered source checksum, byte-changed target checksum, changed regulatory condition, unapproved profile rule, broken citywide crosswalk, altered approval crosswalk, missing density predecessor, and an unexpected validator exception. Separate tests prove recursive tuple/mapping immutability, defensive-copy isolation, repeatable independent loads, public package exports, and preservation of all released R1 loader behavior.

Validation evidence:

- `.venv/bin/python -B scripts/validate_approved_residential_rules.py --verify-source-files` passes the callable complete source, lineage, replay, semantic-preservation, GIS-fixture, approval, and runtime gates;
- `.venv/bin/python -B -m unittest tests.test_ruleset_loader tests.test_residential_ruleset_loader tests.test_residential_rules_v3_approval -q` passes all 33 released-R1, residential-loader, and approval tests;
- `.venv/bin/python -B -m unittest discover -s tests -q` passes all 285 repository tests; and
- `git diff --check` passes.

No GIS lookup class, standards retriever, pipeline, result fixture, ruleset, ruleset schema, source snapshot, dependency, presentation component, template, static asset, or default Flask behavior changed during tranche 4.2; owner acceptance remained the gate for residential GIS lookup.

The project owner accepted tranche 4.2 and authorized the residential GIS lookup on July 19, 2026.

## Block 4 tranche 4.3 residential GIS lookup implementation

Tranche 4.3 adds an exact, production-independent `LocalResidentialLookup` alongside the released `LocalR1Lookup`:

- construction requires an already validated `ApprovedResidentialRuleset`; its ordered 12-zone identity set must exactly match the July 18 manifest's requested designations and filter;
- the citywide address manifest must be complete, checksum-backed, EPSG:4326, and internally count-consistent before address indexing;
- the residential manifest must contain exactly the parcel and current-zoning layers, canonical consolidated filenames, complete validation status, exact source filters, output checksums, and equal source/downloaded/unique counts;
- requested and downloaded per-zone counts must agree with each other, the consolidated feature contents, and the manifest's cross-layer evidence;
- R5 and R6 must remain explicit zero-count supported identities, while every other approved designation must remain in the observed positive-count set;
- `R1-6LHT`, `R2-7L`, and `R2HT` must remain the exact excluded preflight set with matching positive parcel/zoning counts and are never prefix-normalized to a supported zone;
- every consolidated feature must have a unique integer object ID and one exact supported designation before the polygon indexes are built; and
- versions, source URLs, zone counts, and excluded counts are held behind defensive-copy properties.

Lookup preserves exact normalized address matching and deterministic geometry behavior. One matching address, parcel, and zoning feature with agreeing designations returns `residential_zone_found`; no filtered spatial match returns `outside_supported_residential_snapshot`; duplicate addresses, missing addresses, overlaps, incomplete layer matches, designation disagreements, and unexpected exact codes remain controlled outcomes without standards data.

The new tests execute all ten source-verified live fixtures (`R1-6L`, `R1-8L`, `R2`, `R3`, `R4`, `PH-R5`, `UV`, `VR`, `UC`, and `HDF`), preserve synthetic-only R5/R6 evidence, reject all three excluded codes, and mutation-test address and residential manifest status, scope, checksums, completeness counts, feature counts, observed designations, cross-layer counts, agreement flags, explicit zeroes, and unsupported feature values. Repeated lookups and returned metadata copies are deterministic and isolated.

Validation evidence:

- `.venv/bin/python -B scripts/validate_approved_residential_rules.py --verify-source-files` passes the complete approved ruleset lineage and runtime gates used to define lookup scope;
- `.venv/bin/python -B -m unittest tests.test_residential_lookup -q` passes all 14 residential lookup and snapshot-integrity tests;
- `.venv/bin/python -B -m unittest tests.test_ruleset_loader tests.test_residential_ruleset_loader tests.test_local_lookup tests.test_residential_lookup tests.test_residential_result_contract_v2_1 -q` passes all 61 released and residential backend boundary tests;
- `.venv/bin/python -B -m unittest discover -s tests -q` passes all 299 repository tests; and
- `git diff --check` passes.

No standards retriever, pipeline, result contract or fixture, ruleset, ruleset schema, source snapshot, dependency, presentation component, template, static asset, or default Flask behavior changed. The project owner accepted tranche 4.3 on July 19, 2026 and authorized exact selection retrieval and residential pipeline orchestration as tranche 4.4.

## Block 4 tranche 4.4 selection retrieval and pipeline implementation

Tranche 4.4 adds a pure, production-independent retrieval boundary over the already approved residential artifact:

- `available_selections()` validates and lists ordinary profiles in the closed `single_family`, `two_family`, `multifamily` order, followed by approved special pathways in authored order;
- `retrieve_residential_selection()` accepts only an exact zone and exact selection identity from an `ApprovedResidentialRuleset`, without aliases, prefix matching, profile synthesis, or nearby-zone fallback;
- all 16 approved ordinary profiles retrieve the exact ten-capability map, approved legal-use permission, transitive not-evaluated topics, retained conflicts, exception families, citations, and source documents required by that selected branch;
- both R1 Chapter 18.24 pathway selections return `analysis_not_evaluated` with their prerequisites and provenance, never the ordinary R1 single-family standards;
- all 18 profile/use combinations recorded as `not_listed` return the controlled `selection_not_available` outcome and the source evidence for that conclusion; and
- malformed, unapproved, incomplete, unknown, or wrongly bound records fail closed. In particular, requesting the ordinary `two_family` profile in an R1 zone cannot silently substitute its differently named special pathway.

`ResidentialStandardsPipeline` loads the approved residential ruleset once, binds `LocalResidentialLookup` to its exact identity set, and emits the accepted contract `2.1.0` envelope. A resolved zone with no selection returns `residential_zone_found` and its exact available choices. An exact profile, pathway, or known-unavailable profile returns `residential_standards_found`, `analysis_not_evaluated`, or `selection_not_available`, respectively. Outside-snapshot, not-found, ambiguous, and review-required lookup branches remain nonregulatory and never receive selected rules. Unknown selection identities and integrity failures remain exceptions rather than being mislabeled as parcel-specific planning review.

The retrieval boundary strips authoring-only approval flags from returned use and regulation records, computes branch-specific transitive provenance closure, and returns defensive copies. The pipeline preserves separate address-snapshot, residential-GIS-snapshot, ruleset, ruleset-schema, and result-contract identities, verifies successful lookup/property agreement, and rejects incomplete retrieval output before returning it.

Validation evidence:

- `.venv/bin/python -B scripts/validate_approved_residential_rules.py --verify-source-files` passes the approved `.5` lineage and all runtime gates;
- `.venv/bin/python -B scripts/validate_residential_result_contract_v2_1.py` passes all eight accepted contract fixtures;
- `.venv/bin/python -B -m unittest tests.test_residential_standards -q` passes 11 exact-selection, profile/pathway, requirement-shape, evidence-closure, mutation, and determinism tests;
- `.venv/bin/python -B -m unittest tests.test_residential_pipeline -q` passes 14 integration, status-matrix, contract-validation, integrity, mutation, and cross-process determinism tests;
- the focused released/residential loader, lookup, retrieval, pipeline, and contract regression passes all 105 tests;
- `.venv/bin/python -B -m unittest discover -s tests -q` passes all 324 repository tests; and
- `git diff --check` passes.

No result-contract fixture, ruleset, ruleset schema, raw snapshot, dependency, presentation component, template, static asset, web route, or default Flask behavior changed. The project owner accepted tranche 4.4 on July 19, 2026 and authorized the Block 4.5 full-backend acceptance gate.

## Block 4 tranche 4.5 full-backend acceptance

Tranche 4.5 executed the approved Block 4 acceptance matrix as one combined backend gate. No corrective implementation was required:

- the canonical approved residential `.5` artifact passes complete source, schema, lineage, replay, semantic-preservation, per-record approval, and runtime-eligibility validation;
- a direct exact-matrix audit covers all 12 supported zone identities, 16 ordinary profiles, both R1 special pathways, and all 18 source-backed unavailable profile selections;
- the same matrix preserves all eight authored requirement kinds: status, numeric maximum, quantity range, lot-area-tiered maximum, no maximum listed, FAA controlled, setback, and plan dependent;
- the exact R1-8L, R5, R6, and PH-R5 conflict records and their selected and competing assertions remain in retrieved evidence;
- the residential runtime suite exercises the ten live GIS designations, synthetic-only R5/R6 behavior, the three exact excluded designations, complete profile/pathway provenance, all eight controlled result statuses, integrity mutations, defensive copies, repeatability, and cross-process byte determinism; and
- the accepted result-contract `2.0.0` checkpoint and runtime successor `2.1.0` each validate all eight fixture statuses independently.

Released-path protection also passes as an independent gate:

- approved R1 v1 remains valid with 16 rules and its documented conflict;
- canonical approved R1 v2 `2026-07-17.2` passes source checks, schema and domain validation, complete migration replay, per-record approval, and runtime eligibility with 20 zone-owned regulations;
- 82 focused released loader, lookup, exact retrieval, pipeline, presentation, web, and vertical-slice tests pass; and
- `santa_clara_zoning/web.py` still constructs `R1StandardsPipeline`, so no residential backend component is an implicit default-application consumer.

Validation evidence:

- `.venv/bin/python -B scripts/validate_approved_residential_rules.py --verify-source-files` passes;
- `.venv/bin/python -B scripts/validate_residential_result_contract.py` validates all eight preserved contract-`2.0.0` fixtures;
- `.venv/bin/python -B scripts/validate_residential_result_contract_v2_1.py` validates all eight contract-`2.1.0` fixtures against approved ruleset `.5`;
- the focused residential loader, lookup, retrieval, pipeline, and contract suite passes all 69 tests;
- the focused released R1 loader, lookup, retrieval, pipeline, presentation, web, and vertical-slice suite passes all 82 tests;
- a `unittest` discovery run over `tests/` passes all 324 repository tests with zero failures, errors, skips, or unexpected successes; and
- `git diff --check` passes.

A path-level audit from the approved Block 4 design commit through the completed backend confirms no changes to dependencies, ruleset schemas, versioned rulesets, raw snapshots, presentation, Flask, templates, CSS, or JavaScript. Block 4.5 therefore changed only this status ledger. The project owner accepted the complete Block 4 backend and authorized the Block 5 interface audit and implementation on July 19, 2026.

## Block 5 common-zone presentation implementation

The owner-approved interface design deliberately avoids a mandatory structure selector in this phase. `ResidentialZoneSummaryPipeline` resolves an address once, retrieves every approved ordinary profile for its exact zone through the existing selection backend, and exposes one common regulation map only after their capability sets and regulatory semantics agree. Rule identities remain traceable through `source_rule_ids`; allowed single-family, two-family, and multifamily uses remain separate records; profile-specific not-evaluated topics retain their exact applicability; and R1 Chapter 18.24 pathways remain separate `not evaluated` disclosures. Any future profile difference fails closed with `structure_specific_standards_require_selection` rather than showing misleading common cards.

`residential_presentation.py` adds presentation contract `2.0.0` for the common-zone result. The default Flask application now uses the approved residential summary pipeline and the active **Santa Clara Zoning Explorer** identity while still accepting an explicitly injected released `R1StandardsPipeline` for historical regression tests. The established page hierarchy and green visual system remain intact, with generalized use, approval, standard, setback, conflict, limitation, pathway, provenance, and failure rendering. The presenter covers all approved requirement shapes: status, numeric maximum, quantity range, lot-area-tiered maximum, no maximum listed, FAA controlled, ordinary and paired/story-adjusted setbacks, plan dependent, not evaluated, and review required.

The released R1 runtime archive remains unchanged. A separately versioned, deterministic residential GIS add-on supplies the three additional snapshot files needed by the new default application. `scripts/build_residential_demo_data_bundle.py` reproduces its fixed-timestamp ZIP and manifest; repeated generation produces the same 4,186,509-byte archive and SHA-256 `bbe2274b00b2687d4a540484e7fcf8cbdc7a8038a063cb4973b169038bb3e098`. `scripts/bootstrap_demo_data.py` installs or verifies both the historical R1 bundle and the residential add-on by default and remains repeatable.

Automated validation evidence:

- `.venv/bin/python -B scripts/validate_approved_residential_rules.py --verify-source-files` passes the complete source, schema, lineage, replay, semantic-preservation, approval, and runtime gates;
- `.venv/bin/python -B scripts/validate_residential_result_contract_v2_1.py` validates all eight runtime contract fixtures against approved ruleset `.5`;
- `.venv/bin/python -B scripts/build_residential_demo_data_bundle.py` reproduces the expected archive size and checksum;
- `.venv/bin/python -B scripts/bootstrap_demo_data.py` reports all 20 files already matching the two approved bundles;
- the new summary, presentation, Flask, and bundle tests cover common R2/R3/R4 profiles, all supported requirement shapes, R1 pathways, Patrick Henry conflicts and plan-dependent treatment, UC FAA treatment, controlled failures, semantic-divergence rejection, evidence closure, deterministic copies, accessibility structure, and source links;
- the preserved released R1 presentation, web, and vertical-slice suites pass through explicit historical-pipeline injection;
- `.venv/bin/python -B -m unittest discover -s tests -q` passes all 346 repository tests; and
- `git diff --check` passes.

The available in-app browser blocked navigation to the local Flask URL under its URL policy, so the project owner completed the visual review in a locally launched application. During that review, redundant per-citation `Return to result` links were removed, `docs/manual-testing-addresses.md` was added with every live supported designation and controlled failure cases, and a purely decorative, assistive-technology-hidden `YIMBY` wordmark was added behind the hero content using viewport-relative sizing. Automated rendered-document structure and accessibility checks pass, no JavaScript changed, and the owner accepted the complete Block 5 interface on July 19, 2026. No dependency, versioned ruleset, schema, result fixture, raw source snapshot, or approved regulatory value changed in Block 5.

## Block 6 read-only release audit and proposal

The project owner accepted Block 5 and authorized a read-only Block 6 audit on July 19, 2026. The audit changed no application code, ruleset, schema, source snapshot, runtime bundle, dependency, test, or user interface. The owner's separate edit to `docs/manual-testing-addresses.md` remained untouched and outside the audit.

Release-baseline findings:

- `codex/residential-zone-expansion` contains the residential expansion commits beyond `main`, and released tag `v0.1.0-r1-prototype` remains an ancestor of the branch;
- the approved R1 ruleset, released R1 runtime archive and manifest, R1 amendment audit, and R1 verification record have no branch diff from the released tag;
- the current branch has no successor release tag, application-version artifact, release report, or GitHub Actions workflow;
- exact dependency pins remain `jsonschema==4.23.0` and `Flask==3.1.3`, the active Python environment is 3.9.6, and `pip check` passes;
- the current checkout passes the approved residential source/lineage/runtime validator, both residential result-contract validators, and all 346 repository tests; and
- the complete suite reports no skips because both local runtime bundles and the ignored research snapshots are present.

The clean-checkout gate exposed one concrete release blocker. A temporary archive created from committed `HEAD` successfully bootstrapped all 20 files from the released R1 bundle and residential GIS add-on, but the default application then rejected approved ruleset `2026-07-19.5` during complete-lineage validation. Both runtime bundles omit `data/raw/2026-07-18/patrick_henry_drive_specific_plan/PatrickHenryPlan.pdf`, even though the approved ruleset checksum-pins that 21,816,482-byte source at SHA-256 `cefd7df91819c61d26b5cdddd0d395b74445078f2dc6e0d57995dc6992b16b87`. The clean-checkout suite consequently ran 304 tests with eight failures and 34 errors, all downstream of the same missing source. This is a packaging defect, not a regulatory-value or application-logic conflict; the runtime correctly fails closed instead of bypassing source verification.

The proposed Block 6 implementation is deliberately release-only:

1. Create a nonoverwriting successor residential runtime add-on that includes the adopted Patrick Henry plan and its snapshot manifest alongside the existing residential GIS files; update bootstrap defaults and bundle tests without weakening source or lineage validation or changing the released R1 archive.
2. Add one consolidated residential vertical-slice acceptance harness covering the ten live default-application zones, synthetic R5/R6 presentation, exact R1 regressions, controlled failures, provenance/version closure, offline startup, and cross-process structured and rendered determinism.
3. Add a minimal Python CI workflow that bootstraps committed bundles in a clean checkout and runs the approved-ruleset validator, both result-contract validators, the complete suite, and whitespace checks so ignored local research files cannot mask release defects again.
4. Re-run the source, migration, regression, offline, determinism, interface, clean-checkout, and complete-suite matrix with no unexplained skips, then publish a residential-expansion release report with exact artifact versions, checksums, limitations, and validation evidence.
5. Use semantic version `v0.2.0` for the proposed next Git tag and **Santa Clara Zoning Explorer v0.2.0 — Residential Expansion** as the proposed release title, subject to owner approval and the normal PR, CI, review, merge, and post-merge tag gates.

Block 6 does not add a regulation, zoning designation, regulatory value, live GIS source, selection screen, commercial analysis, proposal-level compliance logic, or deployment system. Existing immutable source snapshots and released artifacts remain unchanged; any corrected runtime package is a new versioned successor.

### Tranche 6.1 source-complete runtime package

The project owner approved the Block 6 proposal and authorized implementation on July 19, 2026. Tranche 6.1 fixes only the clean-checkout source-packaging defect:

- `scripts/build_residential_demo_data_bundle.py` now builds successor version `2026-07-19.2` with a version-specific external manifest rather than overwriting the accepted `.1` manifest;
- the successor contains the same three immutable residential GIS runtime artifacts plus the checksum-pinned Patrick Henry adopted-plan PDF and its immutable snapshot manifest;
- the released R1 archive, its manifest, residential GIS-only archive `.1`, and the accepted `.1` manifest remain byte-for-byte unchanged and separately regression-tested;
- `scripts/bootstrap_demo_data.py` selects the released R1 manifest and source-complete residential `.2` manifest by default, installing 17 plus five files without loading the redundant `.1` archive;
- bootstrap retains archive and entry size/checksum checks, safe-path validation, complete manifest/archive agreement, atomic staging, conflict refusal, and repeatable already-matching behavior; and
- README fresh-clone setup and repository orientation now identify the selected successor and its storage requirement.

Canonical successor evidence:

- archive: 25,213,418 bytes; SHA-256 `17ccccba8714c3a09d85e18db3dbfedc21a4b79c701ac8f7a1a6cdd4a264d0f0`;
- external manifest: 2,011 bytes; SHA-256 `b797305b8af79f777d97334cf087d1fd3cac4ee6d232ef2158f122dff63dbb33`;
- Patrick Henry plan entry: 21,816,482 bytes; SHA-256 `cefd7df91819c61d26b5cdddd0d395b74445078f2dc6e0d57995dc6992b16b87`; and
- preserved GIS-only `.1` archive: 4,186,509 bytes; SHA-256 `bbe2274b00b2687d4a540484e7fcf8cbdc7a8038a063cb4973b169038bb3e098`.

Validation evidence:

- two consecutive builder runs produce the same successor byte count and SHA-256;
- the 11 focused bundle/bootstrap tests pass, including exact successor contents, empty-repository install, default-manifest closure, unsafe and conflicting archive rejection, idempotence, and predecessor checksum preservation;
- a temporary archive of the staged committed-only tree installs all 22 selected bundle files into an empty `data/raw/` tree, then reports all 22 already matching on a second run;
- the clean-checkout approved residential validator passes complete source, schema, lineage, deterministic replay, semantic-preservation, per-record approval, and runtime-eligibility validation;
- the clean-checkout default Flask application starts without a startup error and renders the verified R2 result for 1240 White Drive; and
- `.venv/bin/python -B -m unittest discover -s tests -q` in the clean checkout passes all 348 tests with no failures, errors, or skips.

No ruleset, schema, result contract, source snapshot, approved regulation, lookup behavior, presentation behavior, template, CSS, JavaScript, or released artifact changed in tranche 6.1.

### Tranche 6.2 consolidated residential acceptance harness

The project owner accepted tranche 6.1 and authorized continued Block 6 work on July 19, 2026. `tests/test_residential_vertical_slice.py` adds one self-contained release gate over the existing focused test layers. Its six tests prove:

- the default Flask application starts with outbound sockets blocked and carries each of the ten source-verified live designations through local address lookup, exact zoning, common-zone summary, deterministic presentation, source receipts, and rendered HTML;
- synthetic-only `R5` and `R6` render their approved multifamily standards, no-maximum-listed coverage, selected density ranges, and retained conflicts without inventing a real address or contradicting the preserved zero GIS counts;
- both released R1 addresses retain the exact shared rule semantics, selected R1-8L conflict value, historical ruleset version, and explicitly injected released web path while the expanded path adds density and keeps special pathways separate;
- all eight residential backend outcomes remain controlled: selection required, standards found, special pathway not evaluated, selection unavailable, outside snapshot, address not found, address ambiguous, and review required; only standards found contains regulations;
- public lookup, review, and known integrity failures render no regulatory cards or private integrity details;
- exact address, residential GIS, ruleset, schema, result, summary, and presentation versions close to the loaded artifacts, every displayed citation closes to a source document, and every local regulatory and GIS output checksum matches its manifest; and
- two independent processes with different hash seeds and reversed request order produce identical structured-result, presented-view, and rendered-HTML SHA-256 values for all ten live addresses plus outside-snapshot, ambiguous, and missing-address outcomes.

Validation evidence:

- `.venv/bin/python -B -m unittest tests.test_residential_vertical_slice -v` passes all six acceptance tests;
- the approved 12-zone source/lineage/runtime validator and both eight-case residential result-contract validators pass;
- the working checkout passes all 354 repository tests;
- a temporary archive of the staged committed-only tree bootstraps all 22 runtime files into an empty `data/raw/` tree;
- the committed-only checkout passes all six release-harness tests and all 354 repository tests with no failures, errors, or skips; and
- `git diff --check` passes.

Tranche 6.2 adds tests and status evidence only. It does not change production code, rulesets, schemas, contracts, source snapshots, runtime bundles, dependencies, commands, presentation, or user-visible behavior.

### Tranche 6.3 clean-checkout continuous integration

The project owner accepted tranche 6.2 and authorized continued Block 6 work on July 19, 2026. `.github/workflows/ci.yml` defines one bounded **Residential release validation** workflow for pushes, pull requests, and explicit manual dispatches. It grants only `contents: read`, cancels superseded runs on the same ref, uses a 15-minute timeout, and performs no write, release, deployment, issue, pull-request, or external-service action.

The Python 3.9 clean-checkout job:

1. checks out the repository with `actions/checkout@v6.0.1` and configures Python with `actions/setup-python@v6.2.0` plus the exact-pinned `requirements.txt` cache key;
2. installs the pinned dependencies and runs `pip check`;
3. bootstraps both selected runtime bundles twice, proving empty-checkout installation and idempotent checksum matching;
4. rebuilds source-complete residential bundle `.2` and rejects any archive or manifest byte drift;
5. runs the approved 12-zone source/lineage/runtime validator and both residential result-contract validators;
6. runs the six-test residential release harness and the complete repository suite;
7. checks the unchanged JavaScript enhancement with Node and runs `git diff --check`; and
8. fails immediately on any unexplained error because no step uses `continue-on-error` or an allowed-failure path.

Validation evidence:

- the workflow file passes local YAML parsing and `git diff --check`;
- push commit `7dc9c0b5d53195276f43ca27517256d2e38095a6` triggered **Residential release validation** run `29706880910` on July 19, 2026;
- hosted job `88245280734`, **Python 3.9 clean-checkout gate**, completed successfully in 4 minutes 51 seconds;
- every substantive step passed: checkout, Python setup, dependency installation and `pip check`, two bootstrap passes, byte-identical residential bundle reproduction, the approved residential validator, both result-contract validators, the six-test release harness, the complete 354-test repository suite, JavaScript syntax, and whitespace integrity; and
- the successful implementation-head run is recorded at `https://github.com/sukritganesh/SantaClaraZoningTool/actions/runs/29706880910`;
- final-head commit `7448a7ccca2582413f235a7adb7bbb11a5565ceb` then triggered run `29707062838`, whose Python 3.9 job `88245745563` passed every step in 4 minutes 1 second; and
- the project owner accepted tranche 6.3 and authorized release reporting on July 19, 2026.

No CI step has write authority or an allowed-failure path. Tranche 6.3 changes automation and status evidence only; it does not change dependencies, production code, regulatory data, source snapshots, runtime archives, contracts, presentation, or user-visible behavior.

### Tranche 6.4 accessible whole-project report

The owner accepted tranche 6.3 and requested one accessible report covering the first R1 release and the residential expansion as a continuous workflow. `docs/santa-clara-zoning-explorer-report.md` is the current whole-project account. It:

- begins with the ordinary user question and current product experience rather than implementation internals;
- explains the exact 12-designation scope, single-family/two-family/multifamily treatment, supported standard families, and the distinction between ten live GIS designations and synthetic-only R5/R6 rule coverage;
- retains the historical report's evidence-preparation versus deterministic-runtime structure while updating its Mermaid diagram for the approved residential path;
- presents the R1 release, source expansion, contract generalization, regulatory authoring, runtime integration, interface work, and release hardening as one staged project;
- explains versioning, conflicts, fail-closed behavior, AI's candidate-only role, and nonnumeric outcomes in plain language;
- records the 67,243-address snapshot, paired 18,677-feature residential layers, approved 196-rule/two-pathway package, 354-test suite, clean-checkout bundle, and hosted CI evidence;
- states the proposed `v0.2.0` release identity without creating a tag or GitHub release; and
- retains a prominent boundary against complete entitlement, buildability, legal, or planning conclusions.

The historical `docs/prototype-report.md` remains unchanged as the report for released baseline `v0.1.0-r1-prototype`. README navigation now identifies both reports and makes their roles explicit. No production code, dependency, ruleset, schema, source snapshot, runtime package, test, interface, tag, or release changed in tranche 6.4.

Validation evidence:

- every local Markdown link in the new report and updated README resolves;
- the report's zone, use, capability, artifact-version, count, conflict, limitation, and validation statements were checked against the active plan, regulatory catalog, verification records, approved ruleset, runtime manifests, and progress ledger;
- the final Mermaid block renders on GitHub and in an isolated full-width check with 22 nodes, eight labeled decision edges, no node overlap, and no label-to-node collision;
- the historical R1 report has no working-tree diff; and
- `git diff --check` passes.

The project owner accepted the final report and authorized the final release matrix and pull-request workflow on July 19, 2026.

### Tranche 6.5 final release matrix and PR readiness

The final local release matrix ran from clean branch head `60af6e911e17b4f0a5552430d23f30366656806f` after report acceptance. It changed no production code, ruleset, schema, contract, source snapshot, runtime package, dependency, test, interface, or release identity.

Validation evidence:

- two consecutive `.venv/bin/python -B scripts/bootstrap_demo_data.py` runs report all 22 runtime files already matching the selected committed bundles;
- `.venv/bin/python -B scripts/build_residential_demo_data_bundle.py` reproduces source-complete add-on `.2` at 25,213,418 bytes and SHA-256 `17ccccba8714c3a09d85e18db3dbfedc21a4b79c701ac8f7a1a6cdd4a264d0f0`;
- `pip check` reports no broken requirements;
- the approved 12-zone source, schema, lineage, replay, semantic-preservation, per-record approval, and runtime-eligibility validator passes with source-file verification;
- both eight-case residential result-contract validators pass for contracts `2.0.0` and `2.1.0`;
- the released tag `v0.1.0-r1-prototype` is an ancestor of the branch, and its runtime archive, manifest, approved R1 ruleset, amendment audit, and rule-verification record have no branch diff;
- the six-test residential release harness passes all live-zone, R5/R6, R1-regression, controlled-failure, provenance, offline, and cross-process determinism gates in 17.577 seconds;
- `.venv/bin/python -B -m unittest discover -s tests -v` passes all 354 repository tests in 123.582 seconds with no failures, errors, skips, or unexpected successes;
- the bundled Node.js runtime accepts `santa_clara_zoning/static/app.js` syntax, and `git diff --check` passes; and
- hosted clean-checkout run `29707903970` passes every configured step on the report-polish head before this status-only release-evidence update.

PR #2 passed both exact-head clean-checkout jobs with no unresolved review thread or conflict. After the project owner confirmed the canonical guarded landing plan for head `98c6907edc86cecf5057cf097dd4352db8c1811f`, GitHub merged it through merge commit `9fb112066420e40390a50380d1220d4100a57b66` on July 19, 2026. Post-merge `main` run `29708903702` then passed the complete clean-checkout workflow against that merge commit.

### Tranche 6.6 post-merge release finalization

The final release-only record assigns semantic version `v0.2.0` and title **Santa Clara Zoning Explorer v0.2.0 — Residential Expansion** to the validated product. The tag points to the `main` commit containing this record, after its own pull-request checks and guarded merge. The GitHub release is a normal release rather than a draft or prerelease.

The release uploads no redundant binary assets. The checksum-pinned R1 and residential runtime ZIPs remain versioned repository artifacts and are included in GitHub's tagged source archives; fresh clones install them through the documented bootstrap command.

This tranche updates release status in the progress ledger, README, and whole-project report only. It does not change production code, regulatory values, rulesets, schemas, contracts, source snapshots, runtime packages, dependencies, tests, application behavior, or the preserved `v0.1.0-r1-prototype` release.

## Block 7 local address autocomplete implementation

Block 7 adds address discovery over the existing exact lookup without changing the final analysis boundary. The application now prepares a suggestion view of all 67,243 active City address records when the local address index is loaded at startup. Exact normalized matches rank first, full-address prefixes second, and ordered token-prefix matches third; identical canonical strings collapse with their source-record count, natural ordering is deterministic, and every response is capped at eight choices with the full unique-match count retained.

The same-origin `GET /api/address-suggestions?q=...` endpoint delegates through the already loaded residential pipeline. Its strict public projection exposes only the query, normalized query, address snapshot, counts, canonical display/value, locality and ZIP, and duplicate count. It rejects overlong queries with a controlled 400, returns short queries as a controlled 200, fails closed with a controlled 503 when an injected legacy pipeline has no suggester, and strips coordinates, source IDs, parcel facts, zoning facts, regulations, and unknown provider fields.

The server-rendered GET form remains the functional fallback. Local vanilla JavaScript adds a 150-millisecond debounce, request cancellation and stale-response checks, DOM-only option construction, live result announcements, duplicate and truncation guidance, pointer selection, Down/Up/Home/End/Enter/Escape/Tab handling, and immediate `requestSubmit()` after an explicit selection. The visible label, combobox/listbox relationships, active-descendant state, selected options, and live region follow the editable ARIA combobox pattern. CSS extends the existing green system for hover, selected, loading, no-result, unavailable, truncated, mobile, forced-colors, and reduced-motion states.

Documentation changes are limited to the active product plan, this ledger, `UX-002` in the cross-cutting backlog, the README runbook description, and the manual test sheet. No dependency, setup command, raw snapshot, ruleset, regulatory schema, result contract, capability catalog, source-verification conclusion, or zoning-analysis behavior changed.

Validation evidence:

- two consecutive bootstrap runs in the working repository report all 22 runtime files matching; the residential runtime add-on reproduces at 25,213,418 bytes and SHA-256 `17ccccba8714c3a09d85e18db3dbfedc21a4b79c701ac8f7a1a6cdd4a264d0f0`;
- `pip check`, the approved R1 v2 runtime gate, the complete approved residential lineage and source-checksum gate, and both eight-case residential result-contract validators pass;
- the six-test residential release harness passes in 22.700 seconds;
- `.venv/bin/python -B -m unittest discover -s tests -v` passes all 371 tests in 156.947 seconds with no failures, errors, skips, or unexpected successes;
- JavaScript parsing succeeds in the bundled Node-backed runtime, and `git diff --check` passes;
- a temporary clean checkout plus the Block 7 patch installs all 22 runtime files, reports all 22 already matched on the second bootstrap, and passes 20 focused address-index and residential-web tests;
- real-snapshot endpoint tests prove `1240 whi` selects the existing R2 result, `1500 warburton` retains the outside-snapshot outcome, `324 los padres` remains a two-record ambiguity, and `3710 el camino real` reports 577 unique matches while returning eight;
- in-app browser testing proves pointer and keyboard auto-submit, duplicate warning and controlled ambiguity, Down/Up/Home/End/Escape/Tab behavior, live announcements, stale-request cancellation, zero-result state, and no console warnings or errors; and
- a 375-pixel viewport check shows one-column form controls, an in-bounds popup, no horizontal overflow, eight unit-heavy choices, and the truncated-result instruction in the established visual system.

This evidence establishes implementation readiness only. The current released product remains `v0.2.0`; no branch, commit, pull request, merge, tag, or `v0.3.0` release was created in this block.

## Block 8 supported parcel context map implementation

Block 8 adds a presentation-only map receipt to successful supported residential results. `LocalResidentialLookup.property_map_context(address)` reuses the already loaded exact address, parcel, and current-zoning indexes; non-success outcomes retain their existing statuses and receive no geometry. Successful map contexts include the selected parcel and complete supported zoning features whose bounds intersect a deterministic neighborhood extent. The extent converts the parcel bounds to meters at its latitude, uses twice the parcel diagonal with a 200-meter minimum buffer, preserves stable source ordering, and fails closed above a 1,500-feature ceiling rather than returning a misleading truncated overlay.

The same-origin `GET /api/property-map?address=...` endpoint exposes map contract `1.0.0`, canonical address/APN/zone identity, address and residential-GIS snapshot versions, named bounds, selected-parcel GeoJSON, supported-zoning GeoJSON, feature count, and exact supported-zone scope. Its independent strict projection validates WGS84 Polygon/MultiPolygon rings, property/bounds agreement, context containment, feature counts, and designation closure while stripping source IDs, unrelated parcel attributes, ruleset and regulatory data, citations, and unknown provider fields. Missing or overlong input returns 400, not-found/outside scope 404, ambiguity/review 409, and absent, invalid, or oversized providers 503. Existing injected pipelines remain compatible through an optional map-provider boundary.

The successful property header is now a 40/60 identity/context grid that gives the map more horizontal context and stacks at 50rem. Repository-vendored Leaflet 1.9.4 renders the local layers without a CDN or frontend package manager, fits the selected parcel with padding and maximum zoom 19, limits panning to the returned context, and permits one additional zoom-out level. The selected parcel has a white halo and dark-green outline. Hovering a supported zoning polygon displays its designation in a concise DOM-built tooltip without exposing additional property data. A compact native **Map legend** disclosure keeps the selected parcel, unshaded-area key, and concise visible zone codes available without permanently consuming card space; the parallel text summary, live loading/error state, keyboard zoom controls, touch interaction, responsive sizing, reduced-motion behavior, forced-color paths, JavaScript fallback, and endpoint failure leave the zoning result independently usable.

Zoning fills use a high-saturation categorical palette with one unique color for each of the 12 supported designations. Citywide R1-6L/R1-8L/R2/R3/R4 use cobalt/orange/green/purple/red; zero-count R5/R6 retain cyan/yellow assignments; and adjacent Patrick Henry PH-R5/UC/UV/VR/HDF use magenta/brown/teal/olive/charcoal. Ordinary fills use 48 percent opacity and the selected designation uses 62 percent, preserving street context while making neighboring zones materially easier to distinguish. This palette is not a regulatory or GIS classification input. The configurable default OpenStreetMap raster layer supplies visual street context only, retains visible attribution and normal browser caching/referrer behavior, and is never proxied, prefetched, bulk-downloaded, or packaged. Tile failure leaves the local geometry visible over a neutral background.

Local automated validation evidence:

- 81 focused geometry, residential lookup, summary delegation, Flask boundary, real endpoint, and rendered-interface tests pass;
- the complete repository suite passes all 389 tests in 178.605 seconds;
- the residential release harness passes all six consolidated acceptance tests;
- the approved 12-zone ruleset and both residential result-contract validators pass with source verification enabled;
- bootstrap installs no files over the populated workspace, reports all 22 files already matched on consecutive runs, and the source-complete residential runtime bundle reproduces byte-for-byte at 25,213,418 bytes and SHA-256 `17ccccba8714c3a09d85e18db3dbfedc21a4b79c701ac8f7a1a6cdd4a264d0f0`;
- a temporary clean reconstruction from `HEAD` plus the Block 8 working changes installs all 22 bundled files, reports all 22 already matched on its second bootstrap, reproduces the manifest and bundle exactly, and passes the 81 focused tests;
- the vendored Leaflet and application JavaScript parse in the system JavaScript runtime, Python compilation succeeds with a temporary bytecode cache, and `git diff --check` passes; and
- real map responses return 174 nearby supported polygons for `2852 Sycamore Way`, 225 for `1240 White Drive`, 40 for `3105 Patrick Henry Drive`, and 45 for `4650 Old Ironsides Drive`; `1500 Warburton Avenue`, `324 Los Padres Boulevard`, and a missing address retain controlled geometry-free outcomes.

The manual test sheet now covers mouse, touch, keyboard, assistive announcements, responsive layout, forced colors, reduced motion, small and large parcels, supported-zone boundaries, blocked tiles, blocked map context, and JavaScript-disabled fallback. The owner accepted the completed Block 8 interface on July 23, 2026; the normal hosted Node syntax, PR, CI, merge, and release gates remain pending.

The owner-requested compact-legend refinement passes 44 focused web/rendering tests and JavaScript parsing. A live `4650 Old Ironsides Drive` browser check confirms that the legend is collapsed by default, opens without overflowing the map, contains the parcel and all five visible zoning entries with concise labels, opens with Enter, closes with Escape, and produces no console warnings or errors.

The follow-up context refinement retains those 44 passing focused tests and JavaScript parsing. Live checks of `2852 Sycamore Way` and `4650 Old Ironsides Drive` confirm the 40/60 desktop split, unchanged stacked breakpoint, narrow single- and mixed-zone legends, interactive zoning paths, and no console warnings or errors. Hover tooltips are bound to each supported zoning feature with DOM `textContent`, display only `Zoning: <designation>`, and do not expand the public map payload.

The high-contrast palette refinement also retains the 44 passing focused web/rendering tests, JavaScript parsing, and whitespace validation. The interface test now enforces 12 distinct configured color values. A live mixed-zone check at `4650 Old Ironsides Drive` confirms that PH-R5, UV, VR, UC, and HDF render with five different fills over the street basemap, the stronger opacity keeps street context legible, the parcel outline remains visually dominant, and the browser console has no errors.

The July 23 selected-parcel refinement increases the white halo from seven to ten pixels and the dark-green outline from three to five pixels, making the lookup target more obvious without changing zoning-layer borders, geometry, or map payloads.

No raw snapshot, runtime data bundle, ruleset, regulatory schema, result contract, capability catalog, approved regulation, lookup conclusion, or zoning-analysis behavior changed in Block 8.

## Block 9 exact regulatory source evidence implementation

Block 9 adds a presentation/provenance sidecar without changing approved ruleset `2026-07-19.5`, any regulatory value, schema, result contract, or immutable raw snapshot. Source-evidence contract `1.0.0` and catalog `2026-07-22.1` bind every one of the 443 citation controls rendered across the 12 supported zones to an exact contextual target. The catalog covers ten checksum-verified source documents: the three approved official PDFs plus seven project audit, verification, and predecessor records. Its 33 referenced PDF pages are rendered at 144 DPI with pinned PDFium tooling; exact table cells, row labels, paragraphs, or headings are stored as normalized overlay rectangles so the source page remains unmodified.

`SourceEvidenceProvider` validates the catalog and evidence manifest, ruleset identity, source and page-image checksums, PDF page counts, region bounds, verified excerpts, immutable Markdown line ranges, JSON Pointers when cataloged, unique contextual bindings, and complete rendered-control coverage before returning defensive copies. Native project evidence remains in its original form and is labeled **Project verification record**. The checksum-pinned JSON predecessor stays in the approved evidence chain, but the hidden unavailable pathway has no staff-facing target. Only approved runtime-chain sources appear; candidate Drive research and inventories remain internal.

The optional provider boundary preserves legacy application-factory injections. `GET /source-evidence/<target_id>` renders a dedicated staff evidence tab, `GET /source-evidence/<target_id>/pages/<location_index>.png` serves an allowlisted rendered page, and `GET /source-documents/<document_id>` serves only checksum-verified source artifacts with inline disposition, byte-range support, immutable caching, CSP, referrer controls, and `nosniff`. Unknown IDs and traversal-like requests return 404; provider, catalog, source, or page-image integrity failures return a controlled 503. These routes are independent of the zoning pipeline, so evidence failure never changes or suppresses the existing result or numbered source appendix.

Each source popover retains its numbered citation list and provides a prominent **View exact source** action that opens the dedicated tab with `noopener`; the redundant fragment link to the bottom appendix is removed. The viewer presents the regulation/zone/result context, source classification and metadata, locator, checksum, human-verification status, full-page image with exact overlay highlights, a parallel text excerpt, fit and zoom controls, multi-page navigation, original-PDF and optional official-source actions, and the controlling-document notice. All pages and text remain available without JavaScript; enhancement adds keyboard navigation, automatic highlight scrolling, status announcements, mobile panning, print output, reduced-motion handling, and forced-color styling without PDF.js or a runtime network dependency.

The immutable source-evidence runtime add-on contains the catalog, manifest, and 33 page images. Its deterministic archive is 11,093,881 bytes with SHA-256 `d9cece041c0dc949de7f3e51e3cd7a555533091b84d05d9b0c10bbc0792c8d38`; bootstrap installs it alongside the unchanged R1 and residential bundles under ignored `data/source_evidence/`. Runtime does not contact Google Drive, City document services, or another evidence service. Approved official URLs are optional outbound provenance links only.

Validation evidence:

- `scripts/build_source_evidence.py --validate-only` closes all 443 contextual targets across 12 zones, while focused catalog/viewer tests prove distinct R1-6L/R2 Title 18 cells, PH-R5 `135` and UC `FAA` Patrick Henry cells, exact density rows, plan classifications, native record anchors, defensive copies, malformed-region rejection, unique rendered IDs, secure 404/503 behavior, PDF ranges and headers, accessible new-tab markup, multi-page fallback, and absence of filesystem paths or Drive research in staff output;
- repeated full evidence generation reproduces the 11,093,881-byte archive at SHA-256 `d9cece041c0dc949de7f3e51e3cd7a555533091b84d05d9b0c10bbc0792c8d38` and its manifest at SHA-256 `acd3a3b036cf56e56c24b505dadfc11e44dd7d41af7ce95e74e43c0a6dde4e3e`;
- two working-tree bootstrap runs report all 56 files already matching the three approved bundles; a temporary clean reconstruction installs all 56 files into an empty data tree, reports all 56 matching on its second run, validates the 443-target catalog, and passes all 72 focused bundle, evidence, residential-web, and legacy-web tests;
- the approved R1 v2 gate, complete approved residential lineage/source-checksum gate, both residential result-contract validators, and `pip check` pass;
- the six-test residential release harness passes in 25.297 seconds, and the complete repository suite passes all 406 tests in 217.758 seconds;
- the unchanged source-complete residential add-on reproduces at 25,213,418 bytes and SHA-256 `17ccccba8714c3a09d85e18db3dbfedc21a4b79c701ac8f7a1a6cdd4a264d0f0`;
- application JavaScript parses in the bundled Node runtime, affected Python modules compile with a temporary bytecode cache, immutable ruleset/contract/raw-source checks show no diff, and `git diff --check` passes; and
- direct visual inspection confirms that the rendered Title 18 page 25 and Patrick Henry page 63 assets preserve complete, readable page context at 144 DPI and contain the representative controlling tables. The in-app browser backend did not attach a controllable local tab in this session, so live interaction, responsive, print, forced-color, and screen-reader owner acceptance remains a stated `v0.3.0` release gate rather than being overstated as passed.

The owner accepted the completed Block 9 evidence experience on July 23, 2026. Block 9 targets the eventual `v0.3.0` release with Blocks 7 and 8. The current released product remains `v0.2.0`; no release or landing action is part of this implementation block.

The owner-approved presentation refinement keeps special pathways and their evidence in backend contracts but hides their unavailable analysis from the staff result. It removes the detached **Important qualifications** section and places conditional, proposal-dependent, and source-conflict notices directly beside the affected standard, with competing conflict evidence retained in collapsed details. Residential-use cards show only the use identity, evidence control, and permission status; repetitive profile labels and permission boilerplate remain preserved in presentation data. A single accessible source-help note near the top of each successful result tells staff that the `i` controls open supporting citations and exact evidence. Source popovers use **View exact source** as their sole action while the complete numbered appendix remains available below and in print. On the evidence page, highlighted source content appears before source-identity metadata so staff reach the controlling excerpt first. The combined residential-web, legacy-web, and source-evidence suites pass all 59 focused tests after these refinements. This is a presentation-only change: no ruleset, regulatory value, result contract, source record, lookup result, or zoning-analysis behavior changed.

## Block 10 source-grounded zone overview implementation

Block 10 replaces the mechanical base-zone summary with a concise, staff-facing **Property Overview** for every supported designation. The descriptions are generated once during authoring, reviewed as project content, and stored in presentation catalog contract `1.0.0`, catalog version `2026-07-23.1`; no model, API, external service, or prompt runs when the application starts or serves a lookup. The exact 12-zone catalog is checksum-bound to approved ruleset `2026-07-19.5` and to the authoring guide, and every entry records the approved rule citations used for its source grounding.

The catalog covers `R1-6L`, `R1-8L`, `R2`, `R3`, `R4`, `R5`, `R6`, `PH-R5`, `UV`, `VR`, `UC`, and `HDF` in deterministic order. Each 55-100-word description names its exact zone, explains its general residential purpose and relative intensity, summarizes housing types without reproducing the detailed use cards, and identifies the general Zoning Clearance and Architectural Review path. Comparative language distinguishes standard and larger-lot R1 areas, the citywide residential intensity progression, and the Patrick Henry designations. Exact heights, setbacks, coverage, density ranges, and other numeric standards remain in their controlled rule presentations rather than in this explanatory prose.

`ZoneDescriptionProvider` validates the catalog, authoring-guide and ruleset checksums, exact supported-zone closure and order, citation references, provenance metadata, prose bounds, required approval language, and safe plain-text content before exposing defensive copies. The default residential application loads the provider once at startup and accepts an optional injected provider for focused tests. Missing, stale, malformed, or unavailable presentation content fails safely to the existing deterministic factual summary; it never changes or suppresses a zoning result. Existing injected pipelines remain compatible.

The successful result now presents the overview in its own accessible region. The scope disclaimer and source-control explanation move into a separate **How to use this result** region so orientation, limitations, and evidence instructions remain visible without interrupting the zone description. The layout uses the established green system, a readable line length, and a two-column guidance grid that stacks at the existing mobile breakpoint.

The versioned `docs/zone-description-authoring-guide.md` defines the future offline Codex authoring workflow, input matrix, comparative review requirement, content and safety constraints, examples, validation command, and human approval boundary. AI-assisted prose remains candidate presentation data until its complete catalog, source references, validation, and review pass; it is never a source for numeric regulations or runtime zoning analysis.

Validation evidence:

- `scripts/validate_zone_descriptions.py` validates catalog `2026-07-23.1` with exact coverage of all 12 supported zones, checksum-bound ruleset and guide identities, valid source references, word bounds, comparative distinctions, and safe plain text;
- focused catalog, provider, presentation, and Flask tests cover exact identity, defensive copies, unknown zones, malformed catalogs, missing provenance, changed guide content, safe fallback, rendered section relationships, and injected-provider compatibility;
- 112 focused geometry, lookup, summary, presentation, evidence, catalog, and Flask tests pass in 81.591 seconds;
- the complete repository suite passes all 414 tests in 236.692 seconds with no failures or errors;
- the six-test residential release harness passes in 25.140 seconds;
- the approved 12-zone ruleset validator, the 443-target source-evidence validator, and both eight-case residential result-contract validators pass;
- two consecutive bootstrap runs report all 56 runtime files already matching; the unchanged residential add-on reproduces at 25,213,418 bytes and SHA-256 `17ccccba8714c3a09d85e18db3dbfedc21a4b79c701ac8f7a1a6cdd4a264d0f0`;
- the exact-evidence add-on reproduces at 11,093,881 bytes and SHA-256 `d9cece041c0dc949de7f3e51e3cd7a555533091b84d05d9b0c10bbc0792c8d38`;
- clean-checkout CI now runs the zone-description validator beside the existing evidence, approved-ruleset, result-contract, release-harness, complete-suite, JavaScript, and whitespace gates;
- application JavaScript parses in the bundled Node runtime, affected Python modules compile with an isolated bytecode cache, and `git diff --check` passes; and
- a live `1240 White Drive` browser check confirms the source-grounded R2 paragraph, distinct **Property Overview** and **How to use this result** regions, clean desktop layout, one-column guidance at a 375-pixel viewport, no horizontal overflow, and no browser-console warnings or errors.

The catalog SHA-256 is `f47d7d591f2b2ab000d075bcd553508c6eafc2aef6b4d4808fca32684c96a107`; its authoring-guide SHA-256 is `c09aaf54cc9101de097d1b165275cdf6d2609b4207cd2a777d1d48d07c8b95fd`; and the bound approved-ruleset SHA-256 remains `ed72cfd24cc43755ddcfbcf566a2c6212592155bb491807cb747748addbb05c4`.

No ruleset, regulatory value, source snapshot, result contract, runtime data bundle, lookup conclusion, or zoning-analysis behavior changed in Block 10. The owner accepted the completed Block 10 overview experience and the combined Blocks 7-10 `v0.3.0` scope on July 23, 2026. The current released product remains `v0.2.0`; the normal `v0.3.0` PR, hosted CI, guarded merge, and release-record gates remain pending.

## Blocks 0-1 validation evidence

- `git diff --check` passes;
- the archived R1 ledger matches the corresponding body of the former active ledger exactly;
- the checksum-pinned `docs/title18-amendment-audit.md` has no working-tree diff;
- the Patrick Henry manifest parses, and its recorded 21,816,482-byte size, 191-page count, and SHA-256 `cefd7df91819c61d26b5cdddd0d395b74445078f2dc6e0d57995dc6992b16b87` match the preserved PDF;
- the approved R1 v2 validator still passes schema, domain, source-file, migration, and runtime-eligibility gates;
- all 410 residential snapshot evidence files match their recorded sizes and checksums;
- the eight focused residential downloader and fixture tests pass; and
- `.venv/bin/python -m unittest discover -s tests -q` passes all 167 tests;
- the optional `node --check santa_clara_zoning/static/app.js` check was unavailable because Node.js is not installed; no JavaScript changed in this work.

## Current source and design observations

- Google Drive residential research is available and useful as candidate input, but it is not approved runtime data.
- The July 18 immutable City GIS snapshot contains exact target R1, R2, R3, R4, and Patrick Henry designations, but no exact `R5` or `R6` features. Future snapshots must preserve their own explicit results and trigger inspection if this changes.
- The R1 two-family permission is a special Chapter 18.24 pathway. It must not inherit ordinary R1 single-family dimensional standards silently.
- Two-family belongs to the multifamily workflow family but retains separate legal-use and primary-structure identities.
- A missing maximum must be presented as no maximum listed in the controlling base table, not as unlimited.
- An FAA-controlled height and a plan-dependent Patrick Henry rear setback require explicit nonnumeric dispositions within the existing regulation families.
- Patrick Henry rear setback must not default to zero without an affirmative verified source value.
- Approved ruleset `2026-07-19.5` discloses Objective Design Standards, the applicable 32-foot R1/R2 proximity transition, Patrick Henry recreation space and encroachments, plan/project review, the UC community-benefits path, and the HDF office option without adding them to the evaluated regulation map.
- PH-R5 has a retained 51-100 versus 51-99 gross-density conflict; the approved ruleset uses Table 1-1 only through explicit project-owner policy and does not claim a City correction.
- Base-zone gross residential density is now an approved encoded capability, but parcel yield, plan reconciliation, density bonus, affordability, development agreements, and state-law adjustments remain not evaluated.

## Blockers

None currently recorded. The clean-checkout source-packaging blocker found by the Block 6 audit is resolved by accepted tranche 6.1.

## Decision log

| Date | Decision | Reason |
|---|---|---|
| 2026-07-18 | Preserve the completed R1 ledger in a dated progress archive and start a new active ledger. | The released prototype's detailed evidence remains inspectable while current status stays concise and phase-specific. |
| 2026-07-18 | Keep R1-named historical plans, source verification, rulesets, schemas, scripts, and tests until their owning behavior is deliberately migrated. | Their names accurately identify release provenance; a broad rename would mix historical evidence with active product refactoring. |
| 2026-07-18 | Expand only selected residential zones and the existing main regulation families. | The immediate goal is multifamily residential data and product generalization, not a complete zoning or entitlement system. |
| 2026-07-18 | Retain separate workflow, legal-use, and structure concepts. | Two-family can reuse multifamily machinery without erasing zone-specific permission or dimensional applicability. |
| 2026-07-18 | Use explicit dispositions for no maximum listed, FAA-controlled, plan-dependent, not evaluated, and review required. | Nonnumeric source meaning must not be converted into an invented number, prohibition, or unlimited claim. |
| 2026-07-18 | Create a new residential ruleset lineage and expect a major schema revision, subject to Block 2 approval. | The approved R1 artifact is immutable, while multiple structures and nonnumeric dispositions change closed data contracts. |
| 2026-07-18 | Use **Santa Clara Zoning Explorer** as the active product name and **Selected residential zoning standards by address** as its scope line. | The identity can survive expansion beyond R1 without implying a complete entitlement determination; historical R1/prototype artifacts retain their provenance names. |
| 2026-07-18 | Keep `R5` and `R6` in legal and synthetic rule scope even while exact live feature counts are zero. | The July 2025 code defines both zones; absence from a current GIS response is not authority to erase their rules or invent real-address fixtures. |
| 2026-07-18 | Treat the Patrick Henry Table 2-4 rear setback as plan-dependent, never zero by default, and treat `UC` height and stories as FAA-controlled. | The base table supplies no rear-setback row and uses the literal value `FAA`; deterministic output must preserve those meanings rather than inventing numbers. |
| 2026-07-18 | Promote structured `not evaluated` topics into expansion Block 2. | Applicable but deferred layers such as the 32-foot transition and Objective Design Standards need stable identities, reasons, citations, and prerequisites before broad presentation. |
| 2026-07-18 | Preserve the checksum-pinned R1 amendment audit and create `docs/residential-title18-amendment-audit.md` as its active successor. | Editing the historical source correctly failed the approved ruleset's checksum gate; a new audit preserves R1 reproducibility while allowing the expansion cutoff and findings to evolve. |
| 2026-07-18 | List the source-verified R1 Chapter 18.24 two-unit pathway but keep its dimensional result `not evaluated`. | The applicable standards branch on site eligibility, attached/detached configuration, the ordinary R1 envelope, existing setbacks, and proposal facts the current product does not collect; ordinary single-family rules cannot be applied universally. |
| 2026-07-18 | Add a separate residential GIS downloader instead of broadening the historical R1 downloader in place. | The released acquisition remains reproducible while the new artifact can enforce the exact 12-designation scope, explicit zeroes, excluded-code preflights, polygon validation, and cross-layer count agreement. |
| 2026-07-18 | Preserve one real fixture per live target designation and use synthetic fixtures for zero-count or deliberately excluded codes. | Routing coverage stays source-backed without inventing R5/R6 addresses or normalizing distinct legacy and combining designations. |
| 2026-07-19 | Approve the complete Block 1 residential verification record, including the explicit `High-Density Flex`/`HD Flex`/`HD-Flex` to `HDF` crosswalk and the Patrick Henry rear-setback treatment as no universal numeric base value, with plan/project review required and no zero default. | The source, GIS, fixture, and disposition evidence passed its technical gates and is authorized to drive Block 2 contract design; this approval does not make new-zone rules runtime eligible. |
| 2026-07-19 | Approve the complete Block 2 residential contract design and begin implementation. | The audited design preserves the immutable v2 baseline, separates legal use from ordinary profiles and special pathways, represents nonnumeric source meanings explicitly, and supplies deterministic migration and result-contract gates before runtime expansion. |
| 2026-07-19 | Permit partial v3 candidates for contract and migration validation, but require the exact complete 12-zone target before runtime eligibility. | Block 2 must prove the contract with migrated R1 data without prematurely authoring or approving R2-R6 and Patrick Henry numeric standards; schema validity must not be confused with runtime completeness. |
| 2026-07-19 | Accept the completed Block 2 implementation and authorize the Block 3 R2-R6 citywide authoring tranche. | The schema, migration, equivalence, GIS-fixture, and result-contract gates passed; citywide data can now be authored without coupling it to Patrick Henry or production runtime changes. |
| 2026-07-19 | Preserve `2026-07-19.1` and create a new versioned candidate for citywide expansion. | The committed R1-only candidate is reproducible migration evidence; adding R2-R6 in place would erase that checkpoint and weaken lineage inspection. |
| 2026-07-19 | Add schema `3.1.0` as a successor while preserving schema `3.0.0` unchanged. | R3 and R4 have separate coverage outcomes below and at/above 10,000 square feet; a typed tier within the existing coverage capability preserves both outcomes without flattening data or broadening the regulation catalog. |
| 2026-07-19 | Keep the completed R1-R6 candidate nonruntime and nonapproved until Patrick Henry and full Block 3 approval. | Technical validity and deterministic source encoding do not satisfy the complete 12-zone matrix, owner approval, or production-loader gates. |
| 2026-07-19 | Add `standard.gross_residential_density` as a typed minimum-to-maximum base-zone range while keeping unit yield and density adjustments out of scope. | The base density range is a key zone standard that can be retrieved deterministically without expanding into acreage, proposal, bonus, affordability, plan, or state-law evaluation. |
| 2026-07-19 | Retain all R5/R6 density assertions and select Table 1-1 values of 51-100 and 60-350 DU/AC through explicit project resolutions. | The project owner supplied a deterministic policy choice; preserving the competing purpose and Table 2-3 values prevents that local choice from being mistaken for an official City correction. |
| 2026-07-19 | Preserve candidate `2026-07-19.2` and its pinned verification sources, then create density-specific source supplements and successor `2026-07-19.3`. | Editing checksum-pinned predecessor evidence or rule data in place would break reproducibility; additive documents, schema, rules, and crosswalk retain an inspectable lineage. |
| 2026-07-19 | Accept nonruntime density candidate `2026-07-19.3` and authorize the Patrick Henry tranche. | Its 11 ranges, R5/R6 conflict records, deterministic lineage, source pins, and mutation tests passed; Patrick Henry can be added without editing the checkpoint. |
| 2026-07-19 | Apply the R5 conflict policy to PH-R5: preserve all 51-100 and 51-99 assertions and select Table 1-1's 51-100 DU/AC range. | The project owner supplied the policy explicitly; retaining the four competing 51-99 assertions prevents the project choice from appearing to be an official correction. |
| 2026-07-19 | Reuse schema `3.2.0` for Patrick Henry candidate `2026-07-19.4` and keep all new records nonapproved. | Existing typed requirements already express numeric, range, no-maximum-listed, FAA-controlled, and plan-dependent outcomes; the tranche adds data and provenance, not schema or runtime authority. |
| 2026-07-19 | Approve complete residential candidate `2026-07-19.4` as the Block 3 regulatory content. | The exact 12-zone matrix, supported regulation families, retained conflicts, source pins, deterministic lineage, and technical validation passed project-owner review. |
| 2026-07-19 | Preserve `.4` and promote it without regulatory-semantic change into immutable runtime-eligible version `2026-07-19.5`. | A separate lifecycle successor records approval transparently, enables all 196 rules and two pathways, and keeps the reviewed candidate and every prior checkpoint reproducible. |
| 2026-07-19 | Complete a read-only Block 4 runtime audit and implementation proposal before changing production code. | The released R1 path remains the regression oracle while loader, filtered-GIS, selection, result-contract, and provenance mismatches are resolved explicitly rather than discovered during coupled implementation. |
| 2026-07-19 | Approve the Block 4 design and implement only tranche 4.1 before residential runtime wiring. | A separate `2.1.0` contract resolves the approved-density, use-permission-evidence, filtered-snapshot, empty-address, and version-identity gaps while preserving accepted `2.0.0` and the released R1 application. |
| 2026-07-19 | Accept result-contract tranche 4.1 and authorize only the approved residential loader tranche 4.2. | The accepted runtime-ready result boundary can now be paired with an exact `.5` loader, while GIS lookup, selection retrieval, pipeline orchestration, and presentation remain independently gated. |
| 2026-07-19 | Accept approved-loader tranche 4.2 and authorize only residential GIS lookup tranche 4.3. | The complete-lineage `.5` loader can now define the exact snapshot identity boundary, while selection retrieval, pipeline orchestration, presentation, and the default Flask application remain separately gated. |
| 2026-07-19 | Accept residential GIS lookup tranche 4.3 and authorize only exact selection retrieval and production-independent pipeline tranche 4.4. | All live supported zone identities already pass the immutable snapshot boundary; the next isolated gate can now attach exact approved branches under contract `2.1.0` without changing presentation or the released application. |
| 2026-07-19 | Accept exact selection retrieval and residential pipeline tranche 4.4 and begin the Block 4.5 full-backend acceptance gate. | The production-independent backend now covers exact approved branches under contract `2.1.0`; the complete matrix and released-path regressions must pass together before any presentation consumer changes. |
| 2026-07-19 | Complete Block 4.5 as a validation-only tranche and retain the default R1 application boundary. | Every approved backend acceptance case and released-path regression passed without a code correction; changing presentation consumers remains a separately reviewed Block 5 concern. |
| 2026-07-19 | Accept the complete Block 4 backend and authorize Block 5 presentation and default-application work. | The exact residential matrix and released R1 regressions passed together, so presentation could become the next deliberate consumer of the approved backend. |
| 2026-07-19 | Present verified common zone standards without a mandatory structure selector and retain exact profile selection as backend and future infrastructure. | Current R2, R3, and R4 ordinary profiles have identical supported regulation semantics; allowed uses and profile-specific limitations can be disclosed separately, while any future standards divergence fails closed and triggers backlog item `UX-001`. |
| 2026-07-19 | Add a separate residential GIS runtime add-on rather than modifying the released R1 demo archive. | The new default application needs the broader filtered snapshot, while the published R1 bundle must remain checksum-reproducible as historical release evidence. |
| 2026-07-19 | Accept the complete Block 5 presentation and interface and authorize a read-only Block 6 release audit. | The owner completed local functional and responsive review, accepted the final interface refinements, and confirmed that the generalized residential product works as intended. |
| 2026-07-19 | Approve the Block 6 release-only implementation proposal and begin with the clean-checkout package repair. | Source-complete startup must pass before additional acceptance automation can provide a trustworthy release gate. |
| 2026-07-19 | Preserve residential GIS-only add-on `.1` and its manifest, and create source-complete successor `.2` with a separate version-specific manifest. | The accepted predecessor remains reproducible while fresh clones receive the Patrick Henry authoritative source required by the unchanged complete-lineage validator. |
| 2026-07-19 | Accept Block 6.1 and proceed to the consolidated residential acceptance harness. | The source-complete successor repairs fresh-clone startup, preserves every earlier artifact, and passes the approved validator and complete suite from committed-only data. |
| 2026-07-19 | Keep Block 6.2 test-only and consolidate release evidence without replacing focused tests. | Focused suites remain better diagnostics, while one product-level gate makes the complete offline, regression, provenance, failure, and determinism claim directly executable. |
| 2026-07-19 | Accept Block 6.2 and proceed to clean-checkout CI. | The consolidated gate passes in working and committed-only trees and makes the release claims executable without changing product behavior. |
| 2026-07-19 | Use one read-only Python 3.9 CI job before considering broader version matrices or deployment automation. | The immediate release risk is clean-checkout reproducibility on the supported baseline; extra runtime matrices and deployment systems would expand scope without strengthening the current regulatory acceptance contract. |
| 2026-07-19 | Accept Block 6.3 and proceed to residential release reporting. | Both the workflow implementation head and the final documentation head passed the complete hosted Python 3.9 clean-checkout gate, so the release claims can now be assembled for a general audience. |
| 2026-07-19 | Preserve the R1 prototype report and create a separate Santa Clara Zoning Explorer whole-project report. | The historical report accurately records the first release, while the new report can tell the complete R1-to-residential story and update the architecture diagram without rewriting release provenance. |
| 2026-07-19 | Accept Block 6.4 and proceed through the final release matrix and pull-request workflow. | The owner accepted the accessible whole-project report after its vertical-flow and visual-routing refinements; release readiness can now be proved against the exact branch. |
| 2026-07-19 | Treat the passing tranche 6.5 matrix as PR readiness, not as a release or landing decision. | Local and hosted evidence closes the agreed acceptance scope, while PR CI, review, explicit landing confirmation, merge verification, and post-merge tag gates remain separate safeguards. |
| 2026-07-19 | Land residential expansion PR #2 through a merge commit at its exact approved head. | Both PR checks passed, the branch was clean and mergeable, the owner confirmed the guarded landing warning for head `98c6907edc86cecf5057cf097dd4352db8c1811f`, and post-merge `main` validation passed at merge commit `9fb112066420e40390a50380d1220d4100a57b66`. |
| 2026-07-19 | Publish `v0.2.0` as the first normal Santa Clara Zoning Explorer residential release. | The broader product is no longer a narrow prototype; the historical `v0.1.0-r1-prototype` prerelease remains preserved, while the accepted 12-zone product has passed local, PR, merge, and post-merge gates. |
| 2026-07-20 | Implement Block 7 address autocomplete only from the validated local City snapshot, with no external geocoder or frontend dependency. | Local deterministic suggestions avoid keys, billing, branding, provider policy, runtime network, and new source-provenance concerns while reusing the exact approved address normalization and immutable snapshot identity. |
| 2026-07-20 | Search every active City address, auto-submit an explicitly selected canonical value, and leave final zoning analysis unchanged. | Users can discover supported and outside-scope City addresses more easily, while duplicates remain ambiguous, unit choices are never guessed, manual GET submission remains available, and all existing fail-closed outcomes continue through the same pipeline. |
| 2026-07-20 | Build Block 8 only from the existing filtered residential GIS snapshot and show maps only for exact supported successes. | The map can provide parcel and nearby supported-zone context without adding a new zoning source; explicit unshaded-area copy prevents absent unsupported polygons from being mistaken for unzoned land. |
| 2026-07-20 | Pin the City public map's live zoning-legend colors locally and keep them separate from analysis data. | Staff receive a familiar visual vocabulary, including Patrick Henry colors, while a later City styling change cannot silently alter deterministic output or regulatory meaning. |
| 2026-07-20 | Vendor Leaflet 1.9.4 locally and use configurable OpenStreetMap tiles only as an optional visual basemap. | Executable map code and authoritative geometry remain local with no key or billing; visible attribution and no-prefetch behavior honor the community tile policy, and tile failure does not suppress the local evidence or zoning result. |
| 2026-07-21 | Supersede the City-derived zoning swatches with a unique high-contrast color for every supported designation. | The earlier palette preserved City familiarity but several pale and related hues were hard to distinguish over street tiles; the owner prioritized categorical separation, so the new presentation-only palette increases saturation and opacity without changing GIS classifications or zoning conclusions. |
| 2026-07-22 | Add exact source evidence as a validated presentation sidecar instead of changing approved ruleset `2026-07-19.5`. | Contextual table-cell and paragraph targets, page renderings, and native project-record anchors strengthen staff traceability while preserving the approved regulatory artifact, raw snapshots, and deterministic zoning conclusion. |
| 2026-07-22 | Package only the approved runtime evidence chain and keep Drive research out of staff-facing controls. | Official documents and explicitly labeled checksum-pinned project verification records support the approved output; candidate research aids are not authority and must not be presented as such. |
| 2026-07-22 | Hide unavailable special-pathway cards, place consequential qualifications beside affected rules, and remove redundant source-receipt fragment links. | Staff should see implemented results and their immediate caveats without detached or duplicative sections; backend pathway data, conflict evidence, exact-source access, and the numbered source appendix remain preserved. |
| 2026-07-23 | Reduce residential-use cards to use identity, evidence, and permission status while retaining profile labels and conditions in presentation data. | The profile label repeats the use heading and the approval-free boilerplate is already conveyed by the adjacent required-approvals section; removing both card lines improves scanability without changing regulatory meaning or stored evidence. |
| 2026-07-23 | Explain the `i` source controls once near the top of every successful result. | City staff should not need to infer an icon’s purpose; a concise, accessible instruction makes supporting citations and exact evidence discoverable without repeating helper copy beside every rule. |
| 2026-07-23 | Increase the selected parcel’s white halo and dark-green map outline. | A stronger boundary makes the exact lookup target easier to distinguish from nearby categorical zoning fills without changing the underlying geometry or implying that neighboring parcels were selected. |
| 2026-07-23 | Store source-grounded zone overviews in a versioned presentation catalog authored offline, with no runtime AI, and retain the deterministic factual summary as a fail-safe fallback. | Staff receive concise comparative context for all 12 zones while the approved ruleset remains the sole regulatory authority; checksum and citation validation make the prose reproducible, and unavailable presentation content cannot suppress or change a zoning result. |
| 2026-07-23 | Accept the combined Blocks 7-10 implementation as the complete `v0.3.0` feature scope and begin normal release gates. | The owner completed iterative functional review of autocomplete, maps, exact evidence, presentation refinements, and zone overviews; the final local matrix passes, so remaining work is branch publication, hosted CI, guarded landing, release recording, and tagging rather than additional product scope. |
