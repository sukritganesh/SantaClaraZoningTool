# Residential Zoning Expansion Progress

**Last updated:** July 18, 2026

**Current position:** Block 1 in progress on `codex/residential-zone-expansion`; the source matrix and Patrick Henry source snapshot are established, while the residential GIS snapshot and runtime implementation remain pending

**Next action:** Implement and run the exact residential GIS acquisition contract, verify reachable-zone fixtures, and submit the completed source matrix and candidate dispositions for owner approval

This is the sole active project-status ledger. Scope, architecture, and block exit conditions live in `docs/residential-expansion-plan.md`. The completed R1 ledger is preserved at `docs/progress-archive/2026-07-18-r1-prototype-progress.md`.

## Baseline and active scope

- Released baseline: `v0.1.0-r1-prototype`, merged through PR #1.
- Development branch: `codex/residential-zone-expansion`.
- Target citywide zones: `R1-6L`, `R1-8L`, `R2`, `R3`, `R4`, `R5`, and `R6`.
- Target Patrick Henry designations: `PH-R5`, `UV`, `VR`, `UC`, and GIS designation `HDF`.
- Target structure identities: single-family, two-family, and multifamily primary structures.
- Target regulations: the existing use, approval, height, stories, coverage, and four setback families, with only the minimum additional dispositions needed for no maximum listed, FAA-controlled, plan-dependent, not evaluated, and review-required results.
- Commercial analysis and additional regulation families remain outside the phase.

## Inherited canonical artifacts

- Citywide address snapshot: `data/raw/2026-07-16/santa_clara_address_points/manifest.json`
- Released R1 parcel and zoning snapshot: `data/raw/2026-07-14/santa_clara_r1_gis/manifest.json`
- Released zoning-code and amendment snapshot: `data/raw/2026-07-16/santa_clara_zoning_code/manifest.json`
- Adopted Patrick Henry plan snapshot: `data/raw/2026-07-18/patrick_henry_drive_specific_plan/manifest.json`
- Approved R1 ruleset: `rulesets/santa_clara/r1/2026-07-17.2/ruleset.json`
- Reproducible runtime bundle: `demo-data/santa-clara-r1-runtime-data-2026-07-18.1.zip`
- Full R1 validation and decision record: `docs/progress-archive/2026-07-18-r1-prototype-progress.md`

These artifacts remain the immutable inherited baseline until a later block creates and validates an explicit successor.

## Milestone tracker

| Block | Status | Exit evidence or next result |
|---|---|---|
| 0. Establish the transition contract | Complete | The R1 ledger is archived; the expansion plan, fresh active ledger, and durable instructions establish the new phase without code or runtime-data changes. |
| 1. Verify sources and acquire residential GIS | In progress | `docs/residential-rule-verification.md` records the checked source matrix, candidate dispositions, live GIS preflight, acquisition requirements, remaining evidence, and approval gate. The Patrick Henry source is preserved; the immutable residential GIS snapshot and fixtures are still required. |
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

## Block 1 work in progress

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

July 18 ArcGIS preflight evidence:

- both layers returned 18,677 target features and identical per-zone counts;
- exact counts included `R1-6L: 15,757`, `R1-8L: 436`, `R2: 752`, `R3: 1,685`, `R4: 2`, `PH-R5: 2`, `UV: 9`, `VR: 27`, `UC: 2`, and `HDF: 5`;
- exact `R5` and `R6` counts were zero in both layers; they remain legal and synthetic rule targets, not real-address fixtures;
- deliberately excluded exact designations were also observed in both layers: `R1-6LHT: 14`, `R2-7L: 1`, and `R2HT: 2`; and
- these are preflight observations, not hardcoded future acceptance values. The immutable acquisition must preserve and validate whatever the official source returns at retrieval time.

The source checks did not change application code, schemas, rulesets, dependencies, or runtime behavior. New-zone assertions remain candidate data until the Block 1 evidence and dispositions receive owner approval.

Validation evidence:

- `git diff --check` passes;
- the archived R1 ledger matches the corresponding body of the former active ledger exactly;
- the checksum-pinned `docs/title18-amendment-audit.md` has no working-tree diff;
- the Patrick Henry manifest parses, and its recorded 21,816,482-byte size, 191-page count, and SHA-256 `cefd7df91819c61d26b5cdddd0d395b74445078f2dc6e0d57995dc6992b16b87` match the preserved PDF;
- the approved R1 v2 validator still passes schema, domain, source-file, migration, and runtime-eligibility gates;
- `.venv/bin/python -m unittest discover -s tests -v` passes all 159 baseline tests; and
- the optional `node --check santa_clara_zoning/static/app.js` check was unavailable because Node.js is not installed; no JavaScript changed in this work.

## Current source and design observations

- Google Drive residential research is available and useful as candidate input, but it is not approved runtime data.
- The live City GIS inspection on July 18, 2026 returned exact designations for the target R1, R2, R3, R4, and Patrick Henry zones, but no exact `R5` or `R6` features. The immutable snapshot must reproduce or explicitly explain any later change in this finding.
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
