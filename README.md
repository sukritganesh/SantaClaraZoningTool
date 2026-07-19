# Santa Clara Zoning Explorer

**Selected residential zoning standards by address.**

Active development is expanding the released R1 vertical slice to selected citywide and Patrick Henry residential zones, including single-family, two-family, and multifamily choices where verified. The current runnable release, `v0.1.0-r1-prototype`, still covers only Santa Clara's `R1-6L` and `R1-8L` single-family residential zones. Neither the released baseline nor the planned expansion is a complete entitlement analysis or legal/planning determination.

## Project documents

- [Residential expansion plan](docs/residential-expansion-plan.md) — active scope, architecture, migration strategy, implementation blocks, and completion criteria.
- [Current progress](docs/progress.md) — the authoritative record of the current stage, completed blocks, canonical artifacts, and next step.
- [Residential rule verification](docs/residential-rule-verification.md) — active source trace, candidate dispositions, GIS acquisition contract, and approval gate for the expanded zones.
- [Future improvements](docs/future-improvements.md) — the cross-cutting enhancement burndown; active execution remains tracked in the progress ledger.
- [R1 prototype report](docs/prototype-report.md) — historical plain-language account of the released vertical slice and its validation.
- [R1 prototype plan](docs/r1-prototype-plan.md) — historical scope, architecture, source research, data model, and completion criteria for the released baseline.
- [Supported regulations catalog](docs/regulations/supported-regulations.md) — regulation families, capability stages, current boundaries, and deferred expansion queue.
- [Residential ruleset v3 authoring guide](docs/regulations/residential-ruleset-authoring-guide.md) — active residential representation, migration, and approval contract.
- [Ruleset v2 authoring guide](docs/regulations/ruleset-authoring-guide.md) — preserved approved R1 representation contract and examples for human and AI-assisted authors.
- [Residential Title 18 amendment audit](docs/residential-title18-amendment-audit.md) — active July 2025 baseline, later-legislation effects, and expansion recheck triggers.
- [R1 Title 18 amendment audit](docs/title18-amendment-audit.md) — checksum-pinned historical audit used by the approved R1 rulesets.
- [R1 rule-level verification](docs/r1-rule-verification.md) — historical definitions, measurement rules, exceptions, conflicts, and approval record for the released rules.
- [AGENTS.md](AGENTS.md) — operating instructions for Codex tasks in this workspace.
- [Google Drive source](GOOGLE_DRIVE_SOURCE.txt) — link to the shared planning documents and zoning-code PDF.

The README intentionally does not duplicate detailed milestone status. Consult `docs/progress.md` when returning to the project.

## Quick start from a fresh clone

The GIS downloaders use only the Python standard library. Ruleset validation uses the pinned `jsonschema` package so the published Draft 2020-12 contract is enforced directly. The released local application uses pinned Flask with server-rendered Jinja templates.

- Python 3.9 or newer
- Approximately 135 MB of free space for the committed ZIP and its extracted runtime data

From the repository root, create the environment, install the pinned dependencies, and restore the canonical runtime data:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/bootstrap_demo_data.py
```

On Windows PowerShell, create and activate the environment with `py -3 -m venv .venv` and `.\.venv\Scripts\Activate.ps1`, then run the same `python -m pip` and bootstrap commands.

Then start the current released R1 application:

```bash
python -m flask --app santa_clara_zoning.web run
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). Useful supported fixtures include `636 Barto Street` (R1-6L) and `108 Brookside Avenue` (R1-8L).

The repository includes a 35,499,787-byte compressed bundle at `demo-data/santa-clara-r1-runtime-data-2026-07-18.1.zip`. The bootstrap command verifies the archive and every included file against `demo-data/bundle-manifest.json`, installs the approved snapshots under the ignored `data/raw/` tree, and refuses to overwrite different local files. Rerunning it is safe: matching files are reported and left unchanged.

No database, API key, runtime AI service, or live City GIS request is required to run the released baseline. Internet access is needed only to install Python dependencies if they are not already cached.

Run the automated checks with:

```bash
python -m unittest discover -s tests -v
```

If Node.js is installed, also check the small local JavaScript enhancement:

```bash
node --check santa_clara_zoning/static/app.js
```

## Refresh source snapshots for development

The committed bundle is the quickest and canonical way to run the released R1 baseline. The following commands are for researchers or developers who deliberately want to retrieve a new dated source snapshot from Santa Clara's live ArcGIS services; they are not part of normal setup.

### Download a selected residential GIS snapshot

Use the expansion downloader to retrieve the parcel and current-zoning polygons for the exact selected residential designations:

```bash
python3 scripts/download_residential_gis.py
```

Or choose a date explicitly:

```bash
python3 scripts/download_residential_gis.py --snapshot-date 2026-07-18
```

This is the multi-zone successor to the R1 research download. It does not download a second address directory: the separate citywide address-point snapshot remains the source for address matching. The residential downloader retrieves the zoning-bearing parcel and current-zoning layers for `R1-6L`, `R1-8L`, `R2` through `R6`, `PH-R5`, `UV`, `VR`, `UC`, and `HDF`.

The command refuses to overwrite an existing dated destination and keeps GET feature batches at 100 IDs or fewer. It preserves metadata, complete object-ID responses, per-designation source counts, excluded-designation preflight counts, raw GeoJSON batches, consolidated EPSG:4326 files, and checksums. It rejects unexpected designations, missing or duplicate IDs, invalid polygon geometry, count drift, and parcel/current-zoning disagreement. A failed acquisition writes `manifest.failed.json`; a complete one writes `manifest.json` under:

```text
data/raw/<snapshot-date>/santa_clara_residential_gis/
```

### Download an R1 GIS snapshot

From the repository root, use the current UTC date automatically:

```bash
python3 scripts/download_r1_gis.py
```

Or choose a date explicitly:

```bash
python3 scripts/download_r1_gis.py --snapshot-date 2026-07-15
```

The downloader:

1. requests every ArcGIS object ID matching `R1-6L` or `R1-8L`;
2. downloads source features in URL-safe batches;
3. preserves layer metadata, object IDs, and raw GeoJSON batches;
4. creates consolidated EPSG:4326 GeoJSON files;
5. validates feature counts and unique object IDs; and
6. writes checksums and validation evidence to `manifest.json`.

Snapshots are immutable. The command fails if its dated destination already exists; use a new date rather than overwriting raw source data.

Newly downloaded snapshot directories are intentionally excluded from Git because they are generated, potentially large artifacts. Each snapshot retains its own manifest and validation evidence. The committed runtime ZIP contains the selected canonical consolidated files and provenance records, but not the much larger raw ArcGIS response chunks.

### Download a citywide address-point snapshot

```bash
python3 scripts/download_address_points.py
```

Use `--snapshot-date YYYY-MM-DD` to choose the dated destination. This downloader preserves the source metadata, object IDs, and raw POST batches, then writes a consolidated EPSG:4326 GeoJSON file, a schema report, and a validated manifest. It downloads the complete citywide layer because zoning classification happens after address-to-parcel resolution.

### Inspect a snapshot

Find the canonical snapshot path in [docs/progress.md](docs/progress.md). To inspect the newest dated residential manifest currently on disk:

```bash
MANIFEST="$(find data/raw -path '*/santa_clara_residential_gis/manifest.json' -print | sort | tail -n 1)"
python3 -m json.tool "$MANIFEST"
```

To inspect the newest dated historical R1-only manifest:

```bash
MANIFEST="$(find data/raw -path '*/santa_clara_r1_gis/manifest.json' -print | sort | tail -n 1)"
python3 -m json.tool "$MANIFEST"
```

Check the downloader without contacting the City server:

```bash
python3 scripts/download_residential_gis.py --help
python3 scripts/download_r1_gis.py --help
python3 scripts/download_address_points.py --help
python3 -c "import ast, pathlib; ast.parse(pathlib.Path('scripts/download_residential_gis.py').read_text()); print('syntax ok')"
```

## Resolve an address to an R1 parcel and zone

After the canonical address and R1 snapshots are present, run the offline lookup:

```bash
python3 scripts/lookup_r1_zone.py "636 Barto Street, Santa Clara, CA"
```

The command verifies snapshot checksums, normalizes the address, preserves duplicate matches, intersects the address point with the local parcel and current-zoning polygons, and cross-checks both zoning attributes. It returns controlled statuses for supported R1 matches, ambiguous or unmatched addresses, GIS conflicts, and addresses outside the filtered R1 snapshot.

This command identifies the parcel and zone only. Use the combined standards pipeline below to attach the approved regulatory ruleset. Neither path produces a complete buildability determination.

## Validate the R1 regulatory ruleset

The first approved prototype ruleset is:

```text
rulesets/santa_clara/r1/2026-07-16/ruleset.json
```

Validate its structure, references, and regulatory invariants:

```bash
python3 scripts/validate_r1_rules.py
```

When the local raw zoning-code snapshot is available, also verify recorded source-file checksums:

```bash
python3 scripts/validate_r1_rules.py --verify-source-files
```

Run the regression tests:

```bash
python3 -m unittest discover -s tests -v
```

The ruleset reports selected base-zone standards only. It preserves citations, deferred exception families, validation states, and the documented R1-8L corner-side conflict separately from the selected 15-foot value.

The approved zone-first v2 structural contract is `rulesets/schema/ruleset-v2.schema.json`. The reviewed candidate remains preserved at:

```text
rulesets/santa_clara/r1/2026-07-17/ruleset.json
rulesets/santa_clara/r1/2026-07-17/migration-crosswalk.json
```

The separately approved v2 artifact is:

```text
rulesets/santa_clara/r1/2026-07-17.2/ruleset.json
rulesets/santa_clara/r1/2026-07-17.2/migration-crosswalk.json
```

Version `2026-07-17.2` contains the same 20 zone-owned regulations and complete 16-rule v1 crosswalk as the reviewed candidate. Only its version and approval metadata differ. It is the canonical regulatory source for deterministic standards retrieval; the approved v1 artifact remains preserved for traceability.

Validate the approved ruleset, its local source checksums, migration replay, and runtime eligibility:

```bash
python3 scripts/validate_r1_rules_v2.py \
  --ruleset rulesets/santa_clara/r1/2026-07-17.2/ruleset.json \
  --crosswalk rulesets/santa_clara/r1/2026-07-17.2/migration-crosswalk.json \
  --verify-source-files \
  --require-runtime-eligible
```

The original candidate can still be validated without the runtime requirement by using the validator defaults.

## Validate the residential expansion contracts

Residential schemas `3.0.0`, `3.1.0`, and `3.2.0` and result contract `2.0.0` are implemented as development contracts without changing the released R1 application. The accepted v3.0 R1 migration checkpoint remains preserved at:

```text
rulesets/santa_clara/residential/2026-07-19.1/ruleset.json
rulesets/santa_clara/residential/2026-07-19.1/migration-crosswalk.json
```

Validate that checkpoint's schema, residential domain invariants, GIS fixture contract, local source checksums, complete crosswalk, deterministic replay, and R1 semantic equivalence:

```bash
python3 scripts/validate_residential_rules_v3.py --verify-source-files
```

The current citywide successor adds the owner-approved R2-R6 matrix in a new nonruntime candidate. Schema `3.1.0` adds only a typed lot-area-tiered maximum shape within structure coverage so the R3/R4 source-table tiers are not flattened:

```text
rulesets/santa_clara/residential/2026-07-19.2/ruleset.json
rulesets/santa_clara/residential/2026-07-19.2/citywide-expansion-crosswalk.json
```

Validate the full approved-v2 → accepted-v3.0 → citywide-v3.1 lineage, source checksums, exact R1 preservation, R2-R6 matrix, deterministic replay, and GIS fixture contract:

```bash
python3 scripts/validate_citywide_residential_rules.py --verify-source-files
```

Candidate `2026-07-19.2` deliberately remains nonruntime: it lacks the five Patrick Henry target designations, carries candidate status, and contains no residential-lineage approvals. Supplying `--require-runtime-eligible` to the citywide validator must fail closed until Patrick Henry authoring and complete ruleset approval are finished.

The gross-density successor preserves candidate `2026-07-19.2` and adds one typed minimum-to-maximum range in dwelling units per acre to each of the 11 R1-R6 ordinary profiles. R5 and R6 retain their conflicting Table 1-1, zone-purpose, and Table 2-3 assertions while using the project-owner-selected Table 1-1 values:

```text
rulesets/santa_clara/residential/2026-07-19.3/ruleset.json
rulesets/santa_clara/residential/2026-07-19.3/density-expansion-crosswalk.json
```

Validate the complete approved-v2 → v3.0 → v3.1 → density-v3.2 lineage, source checksums, conflict consistency, exact predecessor preservation, deterministic replay, and GIS fixture contract:

```bash
python3 scripts/validate_density_residential_rules.py --verify-source-files
```

Candidate `2026-07-19.3` also remains nonruntime and nonapproved. It retrieves base-zone gross density ranges only; it does not calculate unit yield or evaluate applicable plans, density bonus, affordability, development agreements, or state-law adjustments.

Validate all eight nonruntime result-contract fixtures:

```bash
python3 scripts/validate_residential_result_contract.py
```

The fixtures exercise zone-found, standards-found, special-pathway-not-evaluated, unavailable-selection, outside-snapshot, address-not-found, address-ambiguous, and review-required meanings. They do not change the production pipeline or imply that candidate v3 rules are serving users.

Application code loads and validates the approved artifact once before serving lookups:

```bash
python3 -c 'from santa_clara_zoning import ApprovedR1Ruleset; r = ApprovedR1Ruleset.load(); print(r.version, r.supported_zones, r.regulation_count)'
```

`ApprovedR1Ruleset.load()` runs the schema, domain, source-checksum, migration-replay, and runtime-eligibility gates. It retains a recursively read-only in-memory representation and returns defensive copies through `as_dict()`. Address orchestration is handled by `R1StandardsPipeline`.

Retrieve the complete approved regulations and referenced provenance for one exact zone:

```python
from santa_clara_zoning import ApprovedR1Ruleset, retrieve_zone_standards

ruleset = ApprovedR1Ruleset.load()
standards = retrieve_zone_standards("R1-6L", ruleset)
print(standards["regulatory_context"]["ruleset_version"])
print(list(standards["regulations"]))
```

Retrieval is case-sensitive and does not normalize or guess zone codes. It preserves applicability, conditions, setback adjustments, paired yards, conflicts, and `not_evaluated` topics; it does not determine whether a parcel is a corner lot or evaluate a proposal.

## Run the address-to-standards pipeline

Load the validated local GIS snapshots and approved ruleset once, then retrieve a versioned combined result:

```python
from santa_clara_zoning import R1StandardsPipeline

pipeline = R1StandardsPipeline.from_defaults()
result = pipeline.analyze_address("636 Barto Street")
print(result["status"])
print(result["parcel"]["apn"])
print(result["zoning"]["designation"])
print(list(result["regulations"]))
```

A supported address returns `r1_standards_found` with parcel and zoning evidence, all approved zone regulations, their referenced provenance, explicit limitations, and GIS/ruleset versions. Unmatched, ambiguous, unsupported, or spatially inconsistent lookups retain their controlled Block 5 outcome and do not receive regulations. Ruleset integrity failures stop the pipeline rather than being mislabeled as parcel-specific planning review.

## Run the released local R1 application

After completing the quick start, launch the development server from the repository root at any time with:

```bash
python -m flask --app santa_clara_zoning.web run
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) and enter a Santa Clara address. The responsive local interface renders property identity, supported use, approvals, selected standards, setbacks, qualifications, limitations, source receipts, data versions, and controlled non-regulatory outcomes. It uses local server-rendered templates and custom CSS with no frontend build step or external asset dependency.

The built-in server is for local development only. It binds to the local machine by default; do not expose debug mode or the development server as a production deployment.

Create a later candidate in a new, nonexisting version directory with:

```bash
python3 scripts/migrate_r1_rules_v2.py \
  --version YYYY-MM-DD.1 \
  --output-dir rulesets/santa_clara/r1/YYYY-MM-DD
```

The migration verifies the approved v1 ruleset and its source-file checksums, refuses to overwrite an existing destination, validates the v2 schema before writing, and emits the migration crosswalk and checksums.

Promotion is also non-overwriting. For a newly reviewed candidate, use a new version and output directory:

```bash
python3 scripts/promote_r1_rules_v2.py \
  --approved-on YYYY-MM-DD \
  --version YYYY-MM-DD.N \
  --output-dir rulesets/santa_clara/r1/YYYY-MM-DD.N
```

## Repository map

```text
.
├── AGENTS.md                         Codex operating instructions
├── GOOGLE_DRIVE_SOURCE.txt           Shared project-source link
├── README.md                         Human-facing setup and runbook
├── requirements.txt                  Pinned Python validation dependency
├── demo-data/
│   ├── bundle-manifest.json          Runtime bundle inventory and checksums
│   └── santa-clara-r1-runtime-…zip   Committed canonical runtime data
├── data/
│   └── raw/                          Ignored, installed immutable snapshots
├── contracts/
│   └── residential-result-contract-2.0.0.schema.json  Expansion result contract
├── docs/
│   ├── progress.md                   Current status and milestone ledger
│   ├── future-improvements.md        Deferred enhancement burndown
│   ├── residential-expansion-plan.md Active residential expansion specification
│   ├── residential-density-rule-verification.md Density source matrix and conflict decisions
│   ├── residential-density-title18-amendment-audit.md Density amendment-audit supplement
│   ├── residential-rule-verification.md Active residential source and rule gate
│   ├── residential-title18-amendment-audit.md Active expansion amendment audit
│   ├── regulations/
│   │   ├── residential-ruleset-authoring-guide.md Active ruleset v3 contract
│   │   ├── ruleset-authoring-guide.md Preserved ruleset v2 authoring contract
│   │   └── supported-regulations.md   Regulatory capability catalog
│   ├── r1-prototype-plan.md          Detailed prototype specification
│   ├── r1-rule-verification.md       Verified source trace and rule contract
│   └── title18-amendment-audit.md    Checksum-pinned historical R1 audit
├── rulesets/
│   ├── schema/r1-ruleset.schema.json Current v1 ruleset contract
│   ├── schema/ruleset-v2.schema.json  Approved zone-first v2 contract
│   ├── schema/ruleset-v3.schema.json  Accepted residential v3.0 R1 contract
│   ├── schema/ruleset-v3.1.schema.json Additive citywide coverage-tier contract
│   ├── schema/ruleset-v3.2.schema.json Additive gross-density range contract
│   └── santa_clara/
│       ├── residential/2026-07-19.1/  Nonruntime migrated R1 v3 candidate
│       ├── residential/2026-07-19.2/  Nonruntime R1-R6 v3.1 candidate
│       ├── residential/2026-07-19.3/  Nonruntime R1-R6 density v3.2 candidate
│       └── r1/
│           ├── 2026-07-16/            Versioned approved v1 R1 rules
│           ├── 2026-07-17/            Preserved reviewed v2 candidate
│           └── 2026-07-17.2/          Approved runtime-eligible v2 rules
├── santa_clara_zoning/
│   ├── addressing.py                  Controlled address normalization and matching
│   ├── geometry.py                    GeoJSON point-in-polygon operations
│   ├── lookup.py                      Snapshot loading and lookup outcomes
│   ├── pipeline.py                    Versioned address-to-standards orchestration
│   ├── presentation.py                UI-neutral deterministic presentation model
│   ├── ruleset.py                     Approved v2 runtime ruleset loader
│   ├── standards.py                   Pure exact-zone regulation retrieval
│   ├── templates/                     Server-rendered web templates
│   └── web.py                         Flask application factory and route boundary
├── scripts/
│   ├── arcgis_snapshot.py             Shared ArcGIS snapshot utilities
│   ├── author_citywide_residential_rules.py Non-overwriting R2-R6 authoring replay
│   ├── author_density_residential_rules.py Non-overwriting gross-density authoring replay
│   ├── bootstrap_demo_data.py         Safe fresh-clone data installer
│   ├── build_demo_data_bundle.py      Deterministic release-bundle builder
│   ├── download_address_points.py     Citywide address-point downloader
│   ├── download_residential_gis.py    Selected residential-zone GIS downloader
│   ├── download_r1_gis.py             R1 parcel and zoning downloader
│   ├── lookup_r1_zone.py              Offline address-to-zone command
│   ├── migrate_r1_rules_v3.py         Non-overwriting approved-v2-to-v3 migration
│   ├── migrate_r1_rules_v2.py         Non-overwriting v1-to-v2 migration
│   ├── promote_r1_rules_v2.py         Non-overwriting v2 approval promotion
│   ├── validate_residential_result_contract.py Expansion fixture validator
│   ├── validate_citywide_residential_rules.py R1-R6 lineage and domain validator
│   ├── validate_density_residential_rules.py Density lineage and domain validator
│   ├── validate_residential_rules_v3.py Residential domain and runtime gate
│   ├── validate_r1_rules.py           Approved v1 ruleset validator
│   └── validate_r1_rules_v2.py        V2 domain, migration, and runtime gate
└── tests/
    ├── fixtures/
    │   ├── residential_gis_fixture_inventory.json  Expanded routing fixtures
    │   └── residential_result_contract_cases.json  Nonruntime result cases
    └── test_*.py                       Rule, address, geometry, and lookup tests
```

The existing `blender-mcp-test/` directory is unrelated experimental work and is not part of Santa Clara Zoning Explorer.
