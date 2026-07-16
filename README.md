# Santa Clara Zoning Portal

A block-by-block prototype for answering a narrow version of: **What residential development standards apply at this Santa Clara address?**

The first vertical slice covers Santa Clara's `R1-6L` and `R1-8L` single-family residential zones. This is an early technical prototype, not a complete entitlement analysis or legal/planning determination.

## Project documents

- [Current progress](docs/progress.md) — the authoritative record of the current stage, completed blocks, canonical artifacts, and next step.
- [R1 prototype plan](docs/r1-prototype-plan.md) — scope, architecture, source research, proposed data model, and completion criteria.
- [Title 18 amendment audit](docs/title18-amendment-audit.md) — the July 2025 baseline, later legislation ledger, R1 impact findings, and recheck triggers.
- [R1 rule-level verification](docs/r1-rule-verification.md) — definitions, measurement rules, exceptions, conflicts, and the gate for machine-readable rules.
- [AGENTS.md](AGENTS.md) — operating instructions for Codex tasks in this workspace.
- [Google Drive source](GOOGLE_DRIVE_SOURCE.txt) — link to the shared planning documents and zoning-code PDF.

The README intentionally does not duplicate detailed milestone status. Consult `docs/progress.md` when returning to the project.

## Requirements

The current GIS downloaders use only the Python standard library.

- Python 3.9 or newer
- Internet access to `map.santaclaraca.gov`
- Approximately 60 MB for an R1 snapshot and 80 MB for a citywide address snapshot

No database, package installation, API key, or runtime AI service is currently required to run the downloader.

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

## Repository map

```text
.
├── AGENTS.md                         Codex operating instructions
├── GOOGLE_DRIVE_SOURCE.txt           Shared project-source link
├── README.md                         Human-facing setup and runbook
├── data/
│   └── raw/                          Immutable dated source snapshots
├── docs/
│   ├── progress.md                   Current status and milestone ledger
│   ├── r1-prototype-plan.md          Detailed prototype specification
│   ├── r1-rule-verification.md       Verified source trace and ruleset gate
│   └── title18-amendment-audit.md    Post-July-2025 source audit
└── scripts/
    ├── arcgis_snapshot.py             Shared ArcGIS snapshot utilities
    ├── download_address_points.py     Citywide address-point downloader
    └── download_r1_gis.py             R1 parcel and zoning downloader
```

The existing `blender-mcp-test/` directory is unrelated experimental work and is not part of the zoning prototype.
