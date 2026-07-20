# Residential Title 18 Amendment Audit

**Audit cutoff:** July 18, 2026

**Baseline:** Santa Clara Zoning Code, Title 18 — July 2025

**Purpose:** Determine how later City legislation affects the released R1 baseline and the selected citywide and Patrick Henry residential-zone expansion.

This is a source-control audit for Santa Clara Zoning Explorer, not a legal opinion or complete entitlement review.

## Baseline preserved

The Google Drive zoning-code PDF is preserved locally at:

```text
data/raw/2026-07-16/santa_clara_zoning_code/SantaClaraZoningCode-July-2025.pdf
```

It is 26,758,463 bytes, contains 497 pages, and has SHA-256:

```text
d6461e366cd214beb5c96ee8abe7498d80464879ac63f216119db7c3af6c9c35
```

Its title page identifies it as the July 2025 Title 18 code. The selected citywide and Patrick Henry development standards appear in Chapter 18.10, Section 18.10.030, Tables 2-3 and 2-4. The [City's Zoning Code Updates page](https://www.santaclaraca.gov/our-city/departments-a-f/community-development/planning-division/zoning/zoning-code-update) still identifies July 2025 as the latest consolidated version. The local and City copies were not compared byte for byte because the City's PDF endpoint rejected the automated download request.

The existing snapshot's `manifest.json` records the PDF identity, checksum, preserved amendment files, and machine-readable findings through its immutable July 16 cutoff. Live City and Legistar status was rechecked through July 18 for this successor audit; that recheck does not silently mutate or extend the earlier raw snapshot.

The approved R1 rulesets checksum-pin `docs/title18-amendment-audit.md`. That document remains the immutable July 16 R1 audit. This successor owns the broader expansion finding until a future raw source snapshot and manifest supersede it explicitly.

## Audit method and scope

The audit checked:

- the City's zoning and zoning-update pages;
- the City's [eCode360 new-laws list](https://ecode360.com/SA4626/laws) for adopted legislation not yet incorporated into the consolidated code;
- official Legistar adoption records and final ordinance attachments;
- the July 14, 2026 Cleanup #3 matter and event-item status; and
- proposed Cleanup #3 tables for changes to selected residential values and zone availability.

The audit targets generally applicable Title 18 text adopted after the July 2025 baseline. Parcel-specific rezonings and zoning-map actions are normally outside this text-amendment ledger, but a proposed action that creates an exact target-zone designation is retained as a GIS and source-refresh trigger.

## Findings

| Item | Status at cutoff | Change | Effect on the released R1 rules | Effect on the residential expansion |
|---|---|---|---|---|
| Ordinance 2085, File 26-242 | Adopted March 10, 2026; effective April 9, 2026; listed by eCode360 as not yet incorporated | Adds Chapter 18.27 Objective Design Standards for multifamily and residential mixed-use projects | No change identified to the selected R1 Table 2-3 numeric standards | Material applicable layer for new multifamily and residential mixed-use development and additions. It is additive to Chapters 18.10 and 18.14; specific-plan standards control conflicts. Applicability must be disclosed, while detailed standards remain `not evaluated`. |
| Ordinance 2086, File 26-613 | Adopted June 9, 2026; effective July 9, 2026; listed by eCode360 as not yet incorporated | Adds Chapter 18.27 regulations for the El Camino Real Corridor and related Title 17 provisions | No change identified to the selected R1 Table 2-3 numeric standards | The corridor geography and mixed-use program are outside the selected residential base-zone scope, but the Chapter 18.27 collision remains a source-integrity issue. |
| Zoning Code Cleanup #3, File 26-735 | Not treated as adopted law: the matter remained `Agenda Ready` with no passed/enactment date, and the July 14 event item still had no action or result | Broad proposed cleanup affecting definitions, cross-references, uses, parking, selected standards, and a proposed rezoning of `TN` parcels to `R6` | Proposed tables preserve the selected R1 height, stories, coverage, and setback values | Re-audit final text if adopted. The proposed `TN`-to-`R6` map action is a direct trigger to recheck whether exact live `R6` features now exist; the product must not anticipate them before an effective ordinance and updated GIS. |

The official ordinance PDFs and proposed Cleanup #3 tables are preserved under:

```text
data/raw/2026-07-16/santa_clara_zoning_code/amendments/
```

## Chapter-number conflict

Ordinances 2085 and 2086 both purport to add different material as Chapter 18.27. The City's eCode360 site lists both as adopted laws that have not yet been incorporated into the code. The project must not guess how the City or codifier will reconcile that collision.

This conflict does not alter the selected base values in Tables 2-3 or 2-4, but it is a material source-integrity warning. Preserve the two enactments separately and do not guess their eventual codification. Ordinance 2085's verified multifamily applicability may be disclosed from the preserved enactment, while its detailed Objective Design Standards remain outside the current evaluator.

## Residential expansion conclusion

No adopted post-July-2025 amendment was identified that changes the selected base values in Tables 2-3 or 2-4 for the target zones. The released R1 conclusion remains unchanged. Ordinance 2085 nevertheless adds a material multifamily rule layer, so an expanded result must disclose its applicability rather than treating the July 2025 base table as the complete analysis.

This audit does not approve any new ruleset. Each value still needs a rule-level check of definitions, applicability, table notes, exceptions, and cross-references. Cleanup #3 and the two unincorporated ordinances must be rechecked before a future source refresh, and the proposed `R6` map action must trigger a new exact-designation GIS inspection if it becomes effective.
