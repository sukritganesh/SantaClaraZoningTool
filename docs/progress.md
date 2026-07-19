# Residential Zoning Expansion Progress

**Last updated:** July 18, 2026

**Current position:** Block 1 technical evidence is complete on `codex/residential-zone-expansion`; the source matrix, Patrick Henry source, residential GIS snapshot, and fixture inventory are ready for project-owner approval, while new-zone runtime implementation remains intentionally pending

**Next action:** Obtain project-owner approval of the completed source matrix, the explicit HDF crosswalk, and the Patrick Henry rear-setback disposition; then begin Block 2 contract design without authoring runtime rules prematurely

This is the sole active project-status ledger. Scope, architecture, and block exit conditions live in `docs/residential-expansion-plan.md`. The completed R1 ledger is preserved at `docs/progress-archive/2026-07-18-r1-prototype-progress.md`.

## Baseline and active scope

- Released baseline: `v0.1.0-r1-prototype`, merged through PR #1.
- Development branch: `codex/residential-zone-expansion`.
- Target citywide zones: `R1-6L`, `R1-8L`, `R2`, `R3`, `R4`, `R5`, and `R6`.
- Target Patrick Henry designations: `PH-R5`, `UV`, `VR`, `UC`, and GIS designation `HDF`.
- Target structure identities: single-family, two-family, and multifamily primary structures.
- Target regulations: the existing use, approval, height, stories, coverage, and four setback families, with only the minimum additional dispositions needed for no maximum listed, FAA-controlled, plan-dependent, not evaluated, and review-required results.
- Commercial analysis and additional regulation families remain outside the phase.

## Canonical artifacts

- Citywide address snapshot: `data/raw/2026-07-16/santa_clara_address_points/manifest.json`
- Released R1 parcel and zoning snapshot: `data/raw/2026-07-14/santa_clara_r1_gis/manifest.json`
- Residential parcel and zoning snapshot: `data/raw/2026-07-18/santa_clara_residential_gis/manifest.json`
- Released zoning-code and amendment snapshot: `data/raw/2026-07-16/santa_clara_zoning_code/manifest.json`
- Adopted Patrick Henry plan snapshot: `data/raw/2026-07-18/patrick_henry_drive_specific_plan/manifest.json`
- Approved R1 ruleset: `rulesets/santa_clara/r1/2026-07-17.2/ruleset.json`
- Reproducible runtime bundle: `demo-data/santa-clara-r1-runtime-data-2026-07-18.1.zip`
- Full R1 validation and decision record: `docs/progress-archive/2026-07-18-r1-prototype-progress.md`

The released R1 artifacts remain the immutable inherited baseline. The Patrick Henry and residential GIS snapshots are Block 1 expansion artifacts and must likewise remain immutable.

## Milestone tracker

| Block | Status | Exit evidence or next result |
|---|---|---|
| 0. Establish the transition contract | Complete | The R1 ledger is archived; the expansion plan, fresh active ledger, and durable instructions establish the new phase without code or runtime-data changes. |
| 1. Verify sources and acquire residential GIS | Ready for owner approval | The checked source matrix, Patrick Henry source, immutable 18,677-feature-per-layer GIS snapshot, and real/synthetic fixture inventory pass their technical gates. The HDF crosswalk, Patrick Henry rear disposition, and full verification record still require explicit owner approval. |
| 2. Generalize the data and result contracts | Not started | New schema, applicability/disposition semantics, crosswalk, and contract versions are approved and mutation-tested. |
| 3. Author and approve residential rules | Not started | All target zone/use/structure cells receive explicit verified dispositions and the new ruleset becomes runtime-eligible. |
| 4. Expand lookup and retrieval | Not started | Exact residential zones and valid use/structure selections return deterministic standards; invalid combinations fail closed. |
| 5. Generalize presentation and interface | Not started | Active R1/prototype wording and implicit single-family assumptions are removed from the product experience. |
| 6. Validate and release | Not started | The expanded acceptance matrix and preserved R1 regressions pass; limitations and release identity are recorded. |

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

## Block 1 evidence ready for approval

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

The source and acquisition work added developer tooling and fixture data, but did not change application runtime code, schemas, rulesets, dependencies, or user-visible behavior. New-zone assertions remain candidate data until the Block 1 evidence and dispositions receive owner approval.

Validation evidence:

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
- Objective Design Standards, 32-foot transitions, and recreation-space rules may be disclosed as applicable but are not evaluated in this phase.

## Blockers

None currently recorded.

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
