# Santa Clara Zoning Explorer

**Selected residential zoning standards by address.**

Release `v0.3.0` adds local address autocomplete, selected-parcel and supported-zoning maps, exact checksummed source evidence, and reviewed plain-language zone overviews to the 12-designation residential product. Release `v0.2.0` remains the residential-expansion baseline, and `v0.1.0-r1-prototype` remains the historical two-zone release. None of these releases is a complete entitlement analysis or legal/planning determination.

## Project documents

- [Residential expansion plan](docs/residential-expansion-plan.md) — active scope, architecture, migration strategy, implementation blocks, and completion criteria.
- [Current progress](docs/progress.md) — the authoritative record of the current stage, completed blocks, canonical artifacts, and next step.
- [Santa Clara Zoning Explorer report](docs/santa-clara-zoning-explorer-report.md) — the accessible, whole-project account from the first R1 release through the residential expansion and its validation.
- [Manual testing addresses](docs/manual-testing-addresses.md) — concise live-address and controlled-outcome checks for the local application.
- [Residential rule verification](docs/residential-rule-verification.md) — active source trace, candidate dispositions, GIS acquisition contract, and approval gate for the expanded zones.
- [Future improvements](docs/future-improvements.md) — the cross-cutting enhancement burndown; active execution remains tracked in the progress ledger.
- [R1 prototype report](docs/prototype-report.md) — historical plain-language account of the released vertical slice and its validation.
- [R1 prototype plan](docs/r1-prototype-plan.md) — historical scope, architecture, source research, data model, and completion criteria for the released baseline.
- [Supported regulations catalog](docs/regulations/supported-regulations.md) — regulation families, capability stages, current boundaries, and deferred expansion queue.
- [Residential ruleset v3 authoring guide](docs/regulations/residential-ruleset-authoring-guide.md) — active residential representation, migration, and approval contract.
- [Zone description authoring guide](docs/zone-description-authoring-guide.md) — source-grounded offline Codex workflow and copy contract for plain-language property overviews.
- [Ruleset v2 authoring guide](docs/regulations/ruleset-authoring-guide.md) — preserved approved R1 representation contract and examples for human and AI-assisted authors.
- [Residential Title 18 amendment audit](docs/residential-title18-amendment-audit.md) — active July 2025 baseline, later-legislation effects, and expansion recheck triggers.
- [R1 Title 18 amendment audit](docs/title18-amendment-audit.md) — checksum-pinned historical audit used by the approved R1 rulesets.
- [R1 rule-level verification](docs/r1-rule-verification.md) — historical definitions, measurement rules, exceptions, conflicts, and approval record for the released rules.
- [AGENTS.md](AGENTS.md) — operating instructions for Codex tasks in this workspace.
- [Google Drive source](GOOGLE_DRIVE_SOURCE.txt) — link to the shared planning documents and zoning-code PDF.

The README intentionally does not duplicate detailed milestone status. Consult `docs/progress.md` when returning to the project.

## Quick start from a fresh clone

The GIS downloaders use only the Python standard library. Ruleset validation uses the pinned `jsonschema` package so the published Draft 2020-12 contract is enforced directly. The local application uses pinned Flask with server-rendered Jinja templates and a repository-vendored copy of Leaflet 1.9.4 for its successful-result map. Leaflet's BSD-2-Clause license is preserved beside the static assets; no frontend package manager or CDN script is required.

- Python 3.9 or newer
- Approximately 250 MB of free space for the committed ZIPs and their extracted runtime data

From the repository root, create the environment, install the pinned dependencies, and restore the canonical runtime data:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/bootstrap_demo_data.py
```

On Windows PowerShell, create and activate the environment with `py -3 -m venv .venv` and `.\.venv\Scripts\Activate.ps1`, then run the same `python -m pip` and bootstrap commands.

Then start the residential development application:

```bash
python -m flask --app santa_clara_zoning.web run
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). Start typing at least three address characters to choose a canonical City address and run the lookup immediately, or enter a full address and use the ordinary lookup button. Suggestions come only from the bundled Santa Clara snapshot; they require no API key or network request. A successful supported result includes a reviewed plain-language zone overview, the selected parcel and nearby supported zoning polygons from the pinned local GIS snapshot, and source popovers that open a dedicated tab at the exact checksummed PDF cell or native project verification record behind the displayed regulation. The [manual testing address sheet](docs/manual-testing-addresses.md) covers overviews, autocomplete, maps, exact evidence, one verified address for every live supported designation, and useful controlled-failure cases.

The repository preserves the 35,499,787-byte released R1 bundle and the initial 4,186,509-byte residential GIS-only add-on. Fresh-clone bootstrap uses the R1 bundle, the source-complete 25,213,418-byte residential successor, and the 11,093,881-byte source-evidence add-on. The residential successor contains the same three GIS artifacts and the checksum-pinned Patrick Henry adopted-plan snapshot required by approved-ruleset validation. The evidence add-on contains catalog `2026-07-22.1`, its manifest, and only the 33 referenced full-page 144-DPI images. Bootstrap verifies all selected archives and files, installs raw sources under ignored `data/raw/` and evidence assets under ignored `data/source_evidence/`, and refuses to overwrite different local files. Rerunning it is safe: matching files are reported and left unchanged.

No database, API key, runtime AI service, live City GIS request, Google Drive request, or live evidence-document request is required to run the application. The parcel, zoning, and exact evidence chain remain local and checksum-verified. Approved official URLs appear only as optional user-activated provenance links. By default, the browser optionally requests only the currently viewed street tiles from `https://tile.openstreetmap.org/{z}/{x}/{y}.png`; visible OpenStreetMap attribution is retained, no tiles are prefetched or proxied, and a tile failure leaves the local geometry visible over a neutral background. This community service is best-effort and governed by the [OpenStreetMap tile usage policy](https://operations.osmfoundation.org/policies/tiles/). Deployments can change `MAP_TILE_URL`, `MAP_ATTRIBUTION_TEXT`, and `MAP_ATTRIBUTION_URL` together in Flask configuration when using another compliant tile source.

Run the automated checks with:

```bash
python -m unittest discover -s tests -v
```

If Node.js is installed, also check the local JavaScript enhancements:

```bash
node --check santa_clara_zoning/static/app.js
```

## Refresh source snapshots for development

The committed bundles are the quickest and canonical way to run the application. The following commands are for researchers or developers who deliberately want to retrieve a new dated source snapshot from Santa Clara's live ArcGIS services; they are not part of normal setup.

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

The residential lookup boundary can resolve the broader approved scope independently of presentation:

```bash
python3 -c 'from santa_clara_zoning import ApprovedResidentialRuleset, LocalResidentialLookup; r = ApprovedResidentialRuleset.load(); lookup = LocalResidentialLookup.from_snapshots(ruleset=r); print(lookup.lookup("1240 White Drive"))'
```

`LocalResidentialLookup` requires the validated approved ruleset to define its exact 12-zone identity set, verifies the complete address and July 18 residential manifests, output checksums, feature counts, per-zone counts, cross-layer agreement, and exact excluded-designation preflights, then performs local exact-address and point-in-polygon matching. Ten designations have verified live-address fixtures. R5 and R6 remain supported regulatory identities with explicit zero live GIS features; `R1-6LHT`, `R2-7L`, and `R2HT` remain distinct excluded codes and are never normalized. This lower-level backend identifies a residential zone only. `ResidentialStandardsPipeline` adds exact profile retrieval, and `ResidentialZoneSummaryPipeline` verifies and combines semantically shared standards for the default interface.

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

Residential schemas `3.0.0`, `3.1.0`, and `3.2.0`, result-contract checkpoint `2.0.0`, and runtime-ready successor `2.1.0` are implemented. The accepted v3.0 R1 migration checkpoint remains preserved at:

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

Candidate `2026-07-19.2` deliberately remains nonruntime: it lacks the five Patrick Henry target designations, carries candidate status, and contains no residential-lineage approvals. Supplying `--require-runtime-eligible` to the citywide validator must continue to fail closed; later approved successor `.5` does not retroactively alter this checkpoint.

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

The Patrick Henry successor preserves candidate `2026-07-19.3` and adds the five exact plan designations with one multifamily profile apiece. It reuses schema `3.2.0` and the same ten supported capabilities; no commercial or office analysis is added. UC height and stories remain FAA-controlled, every Patrick Henry rear setback remains plan-dependent rather than zero, and structure coverage remains no-maximum-listed rather than unlimited. PH-R5 retains all 51-100 and 51-99 density assertions while using the project-owner-selected Table 1-1 range:

```text
rulesets/santa_clara/residential/2026-07-19.4/ruleset.json
rulesets/santa_clara/residential/2026-07-19.4/patrick-henry-expansion-crosswalk.json
```

Validate the complete approved-v2 → v3.0 → v3.1 → density-v3.2 → 12-zone-v3.2 lineage, source checksums, conflict consistency, exact predecessor preservation, deterministic replay, and GIS fixture contract:

```bash
python3 scripts/validate_patrick_henry_residential_rules.py --verify-source-files
```

Candidate `2026-07-19.4` remains the immutable reviewed checkpoint. Supplying `--require-runtime-eligible` still fails closed for that artifact because it is a candidate, `approved_on` is null, and every record is unapproved.

Project-owner approval is recorded in a separate, semantically identical successor. Version `2026-07-19.5` sets the lifecycle metadata and all 196 rule plus two pathway approval flags, while its approval crosswalk checksum-pins `.4`, `.5`, schema `3.2.0`, and the shared regulatory-semantic projection:

```text
rulesets/santa_clara/residential/2026-07-19.5/ruleset.json
rulesets/santa_clara/residential/2026-07-19.5/approval-crosswalk.json
```

Validate the full approved-v2 → v3.0 → v3.1 → density-v3.2 → 12-zone-v3.2 → approved-v3.2 lineage, local source checksums, deterministic replays, exact semantic preservation, GIS fixtures, per-record approvals, and runtime eligibility:

```bash
python3 scripts/validate_approved_residential_rules.py --verify-source-files
```

The approved `.5` ruleset is consumed by the residential loader, lookup, exact selection retriever, and pipeline. The default Flask application now places a fail-closed common-zone summary and presentation boundary over that backend.

Validate all eight nonruntime result-contract fixtures:

```bash
python3 scripts/validate_residential_result_contract.py
```

The fixtures exercise zone-found, standards-found, special-pathway-not-evaluated, unavailable-selection, outside-snapshot, address-not-found, address-ambiguous, and review-required meanings. They do not change the production pipeline or imply that candidate v3 rules are serving users.

Validate the same eight statuses against the approved `.5` ruleset and runtime-ready result contract `2.1.0`:

```bash
python3 scripts/validate_residential_result_contract_v2_1.py
```

The `2.1.0` fixtures add the selected use-permission record and its exact provenance, require all ten profile capabilities including gross residential density, preserve five independent version identities, allow address-only evidence outside the filtered residential snapshot, and permit an empty query only for `address_not_found`. The exact selection pipeline continues to produce equivalent contract-valid results underneath the common-zone interface.

Load the approved residential artifact through its standalone Block 4 backend boundary:

```bash
python3 -c 'from santa_clara_zoning import ApprovedResidentialRuleset; r = ApprovedResidentialRuleset.load(); print(r.version, r.schema_version, r.supported_zones, r.regulation_count)'
```

`ApprovedResidentialRuleset.load()` reads the complete approved-v2 → v3.0 → v3.1 → density-v3.2 → 12-zone-v3.2 → approved-v3.2 lineage once, runs every source, schema, GIS-fixture, replay, semantic-preservation, per-record approval, and runtime-eligibility gate, then recursively freezes the exact validated `.5` object. `as_dict()` returns defensive mutable copies. The residential lookup, exact selection retriever, selection pipeline, common-zone summary, and default Flask application consume this validated boundary.

The released R1 loader and pipeline remain available as a separately protected historical path:

```bash
python3 -c 'from santa_clara_zoning import ApprovedR1Ruleset; r = ApprovedR1Ruleset.load(); print(r.version, r.supported_zones, r.regulation_count)'
```

`ApprovedR1Ruleset.load()` runs the schema, domain, source-checksum, migration-replay, and runtime-eligibility gates. It retains a recursively read-only in-memory representation and returns defensive copies through `as_dict()`. Released address orchestration remains handled by `R1StandardsPipeline`.

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

The lower-level residential pipeline still lists exact profiles and retrieves a selected branch for tests, future structure-specific behavior, and non-UI consumers:

```python
from santa_clara_zoning import ResidentialStandardsPipeline

pipeline = ResidentialStandardsPipeline.from_defaults()
zone_result = pipeline.analyze_address("1240 White Drive")
print(zone_result["status"])
print(zone_result["available_selections"])

selected_result = pipeline.analyze_address(
    "1240 White Drive",
    selection_id="multifamily",
)
print(selected_result["status"])
print(list(selected_result["regulations"]))
```

Selection IDs are exact and case-sensitive. Ordinary `single_family`, `two_family`, and `multifamily` profiles return their approved ten-rule branch when available. A listed special pathway returns `analysis_not_evaluated`; a known profile recorded as `not_listed` returns `selection_not_available`; an unknown or inexact identity raises an error. The public interface does not require this choice while all ordinary profiles in a zone share the supported standards; it verifies that equality and fails closed if the profiles diverge.

## Run the local residential application

After completing the quick start, launch the development server from the repository root at any time with:

```bash
python -m flask --app santa_clara_zoning.web run
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) and start typing a Santa Clara address. The progressively enhanced field suggests up to eight canonical City addresses from the already loaded local snapshot; choosing one runs the unchanged zoning lookup immediately. The lookup button and ordinary GET form remain available without JavaScript or suggestions. The responsive local interface renders property identity, verified residential uses, common supported standards, approvals, setbacks, consequential qualifications beside the affected rules, limitations, exact source evidence, a numbered source appendix, data versions, and controlled non-regulatory outcomes. Special-pathway records remain available to the deterministic backend but are not shown as staff-facing results until their analysis is implemented. The interface uses local server-rendered templates and custom CSS with no frontend build step, required external asset, geocoder, API key, or billing account. Only the optional street basemap and user-activated official provenance links can make third-party requests; neither affects the zoning result or local evidence viewer.

The built-in server is for local development only. It binds to the local machine by default; do not expose debug mode or the development server as a production deployment.

### Author and validate zone descriptions

The running application never calls an AI service. Plain-language zone descriptions are authored offline with Codex, source-checked, and committed in a versioned presentation catalog. The checked-in [authoring guide](docs/zone-description-authoring-guide.md) requires the complete supported-zone matrix so comparative language remains consistent as zones are added.

Validate the catalog, approved-ruleset binding, authoring-guide checksum, exact 12-zone coverage, source references, and copy boundaries with:

```bash
python -B scripts/validate_zone_descriptions.py
```

When a later approved ruleset adds a zone, give Codex the guide, the complete approved zone/use/approval matrix, the official zone-purpose provisions, and the existing catalog. Generate only new or materially affected descriptions, source-review every changed sentence, and rerun the validator before owner acceptance. The catalog is small and committed, so it requires no bootstrap, database, API key, or runtime-data bundle change.

### Rebuild and validate source evidence

The ordinary application and bootstrap do not need PDF tooling. Maintainers regenerating the immutable evidence add-on need the pinned build environment's `pypdfium2`/PDFium renderer plus Poppler's `pdfinfo` and `pdftotext`:

```bash
python -B scripts/build_source_evidence.py
python -B scripts/build_source_evidence.py --validate-only
```

The builder verifies approved ruleset `2026-07-19.5`, every local source checksum, exact contextual coverage, page counts, region bounds, PDF excerpts, Markdown line ranges, JSON Pointers, rendered-page checksums, and deterministic catalog ordering. It renders only referenced full pages at 144 DPI, keeps highlights as HTML overlays, and reproduces `demo-data/santa-clara-source-evidence-runtime-data-2026-07-22.1.zip` plus its manifest. The viewer never converts native project records into derived PDFs and never contacts Drive or a City document service at runtime.

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
│   ├── bundle-manifest.json          Released R1 bundle inventory and checksums
│   ├── residential-bundle-manifest.json Preserved GIS-only add-on inventory
│   ├── residential-bundle-manifest-2026-07-19.2.json Source-complete successor inventory
│   ├── source-evidence-bundle-manifest-2026-07-22.1.json Exact evidence add-on inventory
│   ├── santa-clara-r1-runtime-…zip   Preserved released runtime data
│   ├── santa-clara-residential-runtime-…19.1.zip Preserved GIS-only add-on
│   ├── santa-clara-residential-runtime-…19.2.zip Default source-complete add-on
│   └── santa-clara-source-evidence-runtime-…22.1.zip Exact evidence add-on
├── data/
│   ├── presentation/                 Checked-in reviewed zone-description catalog
│   ├── raw/                          Ignored, installed immutable snapshots
│   └── source_evidence/              Ignored, installed exact evidence assets
├── contracts/
│   ├── residential-result-contract-2.0.0.schema.json  Accepted expansion checkpoint
│   └── residential-result-contract-2.1.0.schema.json  Runtime-ready successor
├── docs/
│   ├── progress.md                   Current status and milestone ledger
│   ├── santa-clara-zoning-explorer-report.md Accessible whole-project report
│   ├── future-improvements.md        Deferred enhancement burndown
│   ├── residential-expansion-plan.md Active residential expansion specification
│   ├── patrick-henry-rule-verification-supplement.md Patrick Henry source and PH-R5 decision gate
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
│       ├── residential/2026-07-19.4/  Complete nonruntime 12-zone v3.2 candidate
│       ├── residential/2026-07-19.5/  Approved runtime-eligible 12-zone v3.2 rules
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
│   ├── residential_pipeline.py        Contract 2.1 residential orchestration
│   ├── residential_presentation.py    Common-zone presentation contract
│   ├── residential_standards.py       Exact profile and pathway retrieval
│   ├── residential_summary.py         Fail-closed common-profile projection
│   ├── source_evidence.py              Validated exact-evidence provider
│   ├── zone_descriptions.py            Validated zone-overview provider
│   ├── ruleset.py                     Approved v2 and residential v3 loaders
│   ├── standards.py                   Pure exact-zone regulation retrieval
│   ├── templates/                     Server-rendered web templates
│   └── web.py                         Flask application factory and route boundary
├── scripts/
│   ├── arcgis_snapshot.py             Shared ArcGIS snapshot utilities
│   ├── author_citywide_residential_rules.py Non-overwriting R2-R6 authoring replay
│   ├── author_density_residential_rules.py Non-overwriting gross-density authoring replay
│   ├── author_patrick_henry_residential_rules.py Non-overwriting Patrick Henry authoring replay
│   ├── bootstrap_demo_data.py         Safe fresh-clone data installer
│   ├── build_demo_data_bundle.py      Deterministic release-bundle builder
│   ├── build_residential_demo_data_bundle.py Deterministic residential add-on builder
│   ├── build_source_evidence.py       Exact-evidence catalog and bundle builder
│   ├── download_address_points.py     Citywide address-point downloader
│   ├── download_residential_gis.py    Selected residential-zone GIS downloader
│   ├── download_r1_gis.py             R1 parcel and zoning downloader
│   ├── lookup_r1_zone.py              Offline address-to-zone command
│   ├── migrate_r1_rules_v3.py         Non-overwriting approved-v2-to-v3 migration
│   ├── migrate_r1_rules_v2.py         Non-overwriting v1-to-v2 migration
│   ├── promote_r1_rules_v2.py         Non-overwriting v2 approval promotion
│   ├── promote_residential_rules_v3.py Non-overwriting residential approval promotion
│   ├── render_source_evidence_pages.py Pinned full-page PDF renderer helper
│   ├── validate_residential_result_contract.py Expansion fixture validator
│   ├── validate_residential_result_contract_v2_1.py Approved-data result validator
│   ├── validate_approved_residential_rules.py Callable approved-lineage/runtime validator
│   ├── validate_zone_descriptions.py  Zone-overview catalog validator
│   ├── validate_citywide_residential_rules.py R1-R6 lineage and domain validator
│   ├── validate_density_residential_rules.py Density lineage and domain validator
│   ├── validate_patrick_henry_residential_rules.py Complete 12-zone lineage validator
│   ├── validate_residential_rules_v3.py Residential domain and runtime gate
│   ├── validate_r1_rules.py           Approved v1 ruleset validator
│   └── validate_r1_rules_v2.py        V2 domain, migration, and runtime gate
└── tests/
    ├── fixtures/
    │   ├── residential_gis_fixture_inventory.json  Expanded routing fixtures
    │   ├── residential_result_contract_cases.json  Nonruntime 2.0 result cases
    │   └── residential_result_contract_2_1_cases.json Approved-data 2.1 cases
    └── test_*.py                       Rule, address, geometry, and lookup tests
```

The existing `blender-mcp-test/` directory is unrelated experimental work and is not part of Santa Clara Zoning Explorer.
