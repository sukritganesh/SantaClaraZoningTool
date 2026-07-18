# Santa Clara Zoning Portal

A block-by-block prototype for answering a narrow version of: **What residential development standards apply at this Santa Clara address?**

The first vertical slice covers Santa Clara's `R1-6L` and `R1-8L` single-family residential zones. This is an early technical prototype, not a complete entitlement analysis or legal/planning determination.

## Project documents

- [Current progress](docs/progress.md) — the authoritative record of the current stage, completed blocks, canonical artifacts, and next step.
- [Future improvements](docs/future-improvements.md) — the cross-cutting enhancement burndown; active execution remains tracked in the progress ledger.
- [R1 prototype plan](docs/r1-prototype-plan.md) — scope, architecture, source research, proposed data model, and completion criteria.
- [Supported regulations catalog](docs/regulations/supported-regulations.md) — regulation families, capability stages, current boundaries, and deferred expansion queue.
- [Ruleset v2 authoring guide](docs/regulations/ruleset-authoring-guide.md) — approved zone-first representation contract and examples for human and AI-assisted authors.
- [Title 18 amendment audit](docs/title18-amendment-audit.md) — the July 2025 baseline, later legislation ledger, R1 impact findings, and recheck triggers.
- [R1 rule-level verification](docs/r1-rule-verification.md) — definitions, measurement rules, exceptions, conflicts, and the machine-readable rule contract.
- [AGENTS.md](AGENTS.md) — operating instructions for Codex tasks in this workspace.
- [Google Drive source](GOOGLE_DRIVE_SOURCE.txt) — link to the shared planning documents and zoning-code PDF.

The README intentionally does not duplicate detailed milestone status. Consult `docs/progress.md` when returning to the project.

## Requirements

The GIS downloaders use only the Python standard library. Ruleset validation uses the pinned `jsonschema` package so the published Draft 2020-12 contract is enforced directly. The local web prototype uses pinned Flask with server-rendered Jinja templates.

- Python 3.9 or newer
- Internet access to `map.santaclaraca.gov`
- Approximately 60 MB for an R1 snapshot and 80 MB for a citywide address snapshot

Create the local environment and install the validation dependency:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

No database, API key, or runtime AI service is currently required.

## Download an R1 GIS snapshot

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

Downloaded GIS snapshots are intentionally excluded from Git because they are generated, potentially large artifacts. Recreate them locally with the downloader; each snapshot retains its own manifest and validation evidence.

## Download a citywide address-point snapshot

```bash
python3 scripts/download_address_points.py
```

Use `--snapshot-date YYYY-MM-DD` to choose the dated destination. This downloader preserves the source metadata, object IDs, and raw POST batches, then writes a consolidated EPSG:4326 GeoJSON file, a schema report, and a validated manifest. It downloads the complete citywide layer because zoning classification happens after address-to-parcel resolution.

## Inspect a snapshot

Find the canonical snapshot path in [docs/progress.md](docs/progress.md). To inspect the newest dated R1 manifest currently on disk:

```bash
MANIFEST="$(find data/raw -path '*/santa_clara_r1_gis/manifest.json' -print | sort | tail -n 1)"
python3 -m json.tool "$MANIFEST"
```

Check the downloader without contacting the City server:

```bash
python3 scripts/download_r1_gis.py --help
python3 scripts/download_address_points.py --help
python3 -c "import ast, pathlib; ast.parse(pathlib.Path('scripts/download_r1_gis.py').read_text()); print('syntax ok')"
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

## Run the local web prototype

After installing `requirements.txt` and restoring the canonical local snapshots, start the development server from the repository root:

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
├── data/
│   └── raw/                          Immutable dated source snapshots
├── docs/
│   ├── progress.md                   Current status and milestone ledger
│   ├── future-improvements.md        Deferred enhancement burndown
│   ├── regulations/
│   │   ├── ruleset-authoring-guide.md Approved ruleset v2 authoring contract
│   │   └── supported-regulations.md   Regulatory capability catalog
│   ├── r1-prototype-plan.md          Detailed prototype specification
│   ├── r1-rule-verification.md       Verified source trace and rule contract
│   └── title18-amendment-audit.md    Post-July-2025 source audit
├── rulesets/
│   ├── schema/r1-ruleset.schema.json Current v1 ruleset contract
│   ├── schema/ruleset-v2.schema.json  Approved zone-first v2 contract
│   └── santa_clara/r1/
│       ├── 2026-07-16/                Versioned approved v1 R1 rules
│       ├── 2026-07-17/                Preserved reviewed v2 candidate
│       └── 2026-07-17.2/              Approved runtime-eligible v2 rules
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
│   ├── download_address_points.py     Citywide address-point downloader
│   ├── download_r1_gis.py             R1 parcel and zoning downloader
│   ├── lookup_r1_zone.py              Offline address-to-zone command
│   ├── migrate_r1_rules_v2.py         Non-overwriting v1-to-v2 migration
│   ├── promote_r1_rules_v2.py         Non-overwriting v2 approval promotion
│   ├── validate_r1_rules.py           Approved v1 ruleset validator
│   └── validate_r1_rules_v2.py        V2 domain, migration, and runtime gate
└── tests/
    └── test_*.py                       Rule, address, geometry, and lookup tests
```

The existing `blender-mcp-test/` directory is unrelated experimental work and is not part of the zoning prototype.
