# Title 18 Amendment Audit

**Audit cutoff:** July 16, 2026

**Baseline:** Santa Clara Zoning Code, Title 18 — July 2025

**Purpose:** Determine whether later City legislation changes the small set of R1-6L and R1-8L numeric standards selected for the prototype.

This is a source-control audit for a technical prototype, not a legal opinion or complete entitlement review.

## Baseline preserved

The Google Drive zoning-code PDF is preserved locally at:

```text
data/raw/2026-07-16/santa_clara_zoning_code/SantaClaraZoningCode-July-2025.pdf
```

It is 26,758,463 bytes, contains 497 pages, and has SHA-256:

```text
d6461e366cd214beb5c96ee8abe7498d80464879ac63f216119db7c3af6c9c35
```

Its title page identifies it as the July 2025 Title 18 code. The R1 development standards appear in Chapter 18.10, Section 18.10.030, Table 2-3. The [City's Zoning Code Updates page](https://www.santaclaraca.gov/our-city/departments-a-f/community-development/planning-division/zoning/zoning-code-update) still identifies July 2025 as the latest consolidated version. The local and City copies were not compared byte for byte because the City's PDF endpoint rejected the automated download request.

The snapshot's `manifest.json` records the PDF identity, checksum, preserved amendment files, and machine-readable audit findings.

## Audit method and scope

The audit checked:

- the City's zoning and zoning-update pages;
- the City's [eCode360 new-laws list](https://ecode360.com/SA4626/laws) for adopted legislation not yet incorporated into the consolidated code;
- official Legistar adoption records and final ordinance attachments;
- the July 14, 2026 Cleanup #3 matter and event-item status; and
- proposed Cleanup #3 tables for changes to the selected R1 values.

The audit targets generally applicable Title 18 text adopted after the July 2025 baseline. Parcel-specific rezonings and zoning-map actions are outside this text-amendment ledger unless they change generally applicable R1 rules.

## Findings

| Item | Status at cutoff | Change | Effect on selected R1 rules |
|---|---|---|---|
| Ordinance 2085, File 26-242 | Adopted March 10, 2026; effective April 9, 2026; listed by eCode360 as not yet incorporated | Adds Chapter 18.27 objective design standards for multifamily and residential mixed-use projects | No change identified to R1 Table 2-3 numeric standards; outside the single-family primary-structure MVP |
| Ordinance 2086, File 26-613 | Adopted June 9, 2026; effective July 9, 2026; listed by eCode360 as not yet incorporated | Adds Chapter 18.27 regulations for the El Camino Real Corridor and related Title 17 provisions | No change identified to R1 Table 2-3 numeric standards; geographically and substantively outside the MVP |
| Zoning Code Cleanup #3, File 26-735 | Not treated as adopted law: the matter remained `Agenda Ready` with no passed/enactment date, and the July 14 event item had no action or result | Broad proposed cleanup affecting definitions, cross-references, uses, parking, and selected standards | Proposed tables preserve the selected R1 height, stories, coverage, and setback values; re-audit final text if adopted |

The official ordinance PDFs and proposed Cleanup #3 tables are preserved under:

```text
data/raw/2026-07-16/santa_clara_zoning_code/amendments/
```

## Chapter-number conflict

Ordinances 2085 and 2086 both purport to add different material as Chapter 18.27. The City's eCode360 site lists both as adopted laws that have not yet been incorporated into the code. The project must not guess how the City or codifier will reconcile that collision.

This conflict does not alter the selected R1 Table 2-3 numbers, but it is a material source-integrity warning. Neither new Chapter 18.27 should be used as an R1 prototype rule source without later codification or City clarification.

## R1 conclusion

No adopted post-July-2025 amendment was identified that changes the selected numeric standards for R1-6L or R1-8L in Table 2-3. That clears the amendment-audit portion of Block 4.

It does not by itself approve the ruleset. Each value still needs a rule-level check of definitions, applicability, table notes, exceptions, and cross-references before it becomes approved machine-readable data. Cleanup #3 and the two unincorporated ordinances must be rechecked before a future source refresh or authoritative claim.
