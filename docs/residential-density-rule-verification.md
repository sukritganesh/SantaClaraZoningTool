# Santa Clara Residential Density Rule Verification

**Status:** Source verified and project-owner approved for nonruntime Block 3 authoring

**Verified through:** July 18, 2026

**Project-owner decision:** July 19, 2026

**Consolidated-code baseline:** Santa Clara Zoning Code, Title 18 - July 2025

This supplement owns the source trace and project conflict decisions for `standard.gross_residential_density`. It does not approve a runtime ruleset, calculate parcel yield, apply a density bonus, or provide an entitlement determination. The checksum-pinned `docs/residential-rule-verification.md` remains the source gate for the predecessor R1-R6 capabilities and is not edited in place.

## Capability boundary

The supported result is the base-zone gross residential density range, expressed as minimum and maximum dwelling units per acre. It is attached to each ordinary R1-R6 analysis profile because it is a zone-level residential development standard, not a distinction between otherwise valid structure selections.

The capability does not:

- multiply acreage by the range to estimate an allowed unit count;
- determine net, developable, or qualifying acreage;
- apply General Plan, master-plan, specific-plan, area-plan, overlay, development-agreement, affordable-housing, density-bonus, or state-law adjustments; or
- evaluate whether a particular proposal complies.

Section 18.10.030(B) states that maximum density must be consistent with the General Plan or an applicable Master, Specific, or Area Plan. Section 18.02.050(C) states that the greater density range prevails when the Zoning Code and General Plan conflict. Those provisions are recorded as conditions and re-review triggers; this candidate does not perform parcel-specific plan reconciliation.

## Visually verified source assertions

The preserved baseline is `data/raw/2026-07-16/santa_clara_zoning_code/SantaClaraZoningCode-July-2025.pdf`, SHA-256 `d6461e366cd214beb5c96ee8abe7498d80464879ac63f216119db7c3af6c9c35`.

| Location | PDF page | Printed page | R1-6L | R1-8L | R2 | R3 | R4 | R5 | R6 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Table 1-1, Zones Implementing the General Plan | 12 | 1-10 | 0.1-10 | 0.1-10 | 8-19 | 20-36 | 37-50 | 51-100 | 60-350 |
| Zone-purpose text, Section 18.10.010 | 19-20 | 2-1 to 2-2 | 0.1-10 | 0.1-10 | 8-19 | 20-36 | 37-50 | 51-99 | 60-350 |
| Table 2-3, Residential Zone Development Standards | 25 | 2-7 | 0.1-10 | 0.1-10 | 8-19 | 20-36 | 37-50 | 51-99 | 85-350 |

All values are gross residential density in dwelling units per acre. R1 through R4 agree across the cited source locations. R5 and R6 do not.

The project Google Drive research and rule inventory independently identify the same R5/R6 discrepancies. Those materials are corroborating candidate research, not a substitute for the preserved code pages.

## Approved values and conflict dispositions

| Zone | Selected range | Disposition |
|---|---:|---|
| `R1-6L`, `R1-8L` | 0.1-10 DU/AC | Source verified; inherited profiles receive the new capability without changing their existing rules. |
| `R2` | 8-19 DU/AC | Source verified. |
| `R3` | 20-36 DU/AC | Source verified. |
| `R4` | 37-50 DU/AC | Source verified. |
| `R5` | 51-100 DU/AC | Conflict retained; Table 1-1 selected by project-owner policy on July 19, 2026. |
| `R6` | 60-350 DU/AC | Conflict retained; Table 1-1 selected by project-owner policy on July 19, 2026. |

For R5, the conflict record must preserve Table 1-1's 51-100 assertion separately from the 51-99 assertions in the purpose text and Table 2-3. For R6, it must preserve Table 1-1 and purpose text's 60-350 assertions separately from Table 2-3's 85-350 assertion.

The selected R5 and R6 rules use `project_resolved_with_conditions`. The decision source is `Project owner direction in the July 19, 2026 Codex task`, not an official City correction. Re-review is mandatory if the City publishes a corrected or newer consolidated code, clarifies the internal inconsistency, adopts a relevant amendment, or supplies controlling parcel-specific General Plan or plan information.

## Approval gate

The project owner approved adding this capability through the current Block 3 stage and expressly directed the project to retain the R5/R6 conflicts while selecting Table 1-1 values. Candidate records remain nonapproved for the residential ruleset and nonruntime until the complete Block 3 and later integration gates pass.
