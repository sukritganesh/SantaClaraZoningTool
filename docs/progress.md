# R1 Prototype Progress

**Last updated:** July 15, 2026

**Current position:** Block 2 complete; Block 3 not started

**Next block:** Download and inspect the City's address-point data

This is the authoritative project-status ledger. The design and scope remain in `docs/r1-prototype-plan.md`; setup and commands remain in `README.md`.

## Milestone tracker

| Block | Status | Exit evidence |
|---|---|---|
| 0. Define the R1 vertical slice | Complete | Scope and completion criteria recorded in the prototype plan. |
| 1. Verify authoritative sources | Complete | Zoning-code and live ArcGIS findings recorded in the prototype plan. |
| 2. Download R1 parcel and zoning GIS | Complete | Two validated 16,193-feature layers and a complete manifest exist. |
| 3. Download and inspect address-point data | Not started | Requires a validated raw snapshot and schema notes. |
| 4. Approve and structure initial R1 rules | Not started | Requires amendment audit, source verification, and machine-readable candidate rules. |
| 5. Implement address-to-parcel-to-zone lookup | Not started | Requires tested local address and spatial resolution. |
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

No database, address snapshot, normalization, spatial join, rules engine, API, or UI exists yet.

## Next block: address-point acquisition

Proposed exit conditions:

1. Download the public city address-point layer into a separate immutable dated snapshot.
2. Preserve metadata, object IDs, raw batches, consolidated output, checksums, and validation counts.
3. Record the actual field schema and inspect representative unit, street-suffix, and missing-value cases.
4. Determine whether all city address points or only R1-intersecting points should become the first canonical lookup input.
5. Identify a small R1-6L, R1-8L, unsupported-zone, ambiguous, and unmatched test-address set.

Storage and lookup-engine choices remain undecided; downloading this raw source does not require choosing a database.

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
