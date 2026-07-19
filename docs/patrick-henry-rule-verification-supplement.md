# Patrick Henry Residential Rule Verification Supplement

**Status:** Source verified and project-owner approved for nonruntime Block 3 authoring

**Verified through:** July 18, 2026

**Project-owner decision:** July 19, 2026

**Ruleset scope:** `PH-R5`, `UV`, `VR`, `UC`, and exact GIS designation `HDF`

This checksum-pinned supplement records the final Patrick Henry source check and the project decision needed to author the five plan designations after residential candidate `2026-07-19.3`. It does not approve a runtime ruleset, evaluate commercial or office uses, add regulation families, calculate parcel yield, or provide an entitlement determination.

The predecessor-pinned `docs/residential-rule-verification.md` remains authoritative for the approved use/profile matrix and the original Patrick Henry base-standard verification. This supplement preserves that file unchanged while adding the gross-density conflict record and a final visual source reconciliation for the successor candidate.

## Preserved authoritative sources

The source checks used:

- `data/raw/2026-07-16/santa_clara_zoning_code/SantaClaraZoningCode-July-2025.pdf`, SHA-256 `d6461e366cd214beb5c96ee8abe7498d80464879ac63f216119db7c3af6c9c35`; and
- `data/raw/2026-07-18/patrick_henry_drive_specific_plan/PatrickHenryPlan.pdf`, SHA-256 `cefd7df91819c61d26b5cdddd0d395b74445078f2dc6e0d57995dc6992b16b87`.

The following locations were visually rechecked for this authoring gate:

| Subject | Source location | PDF page | Printed page |
|---|---|---:|---:|
| Allowable density across all target residential zones | Title 18 Table 1-1 | 12 | 1-10 |
| Patrick Henry zone purposes and density ranges | Title 18 Section 18.10.010 | 20 | 2-2 |
| Patrick Henry residential uses | Title 18 Table 2-2 | 23 | 2-5 |
| Patrick Henry development standards | Title 18 Table 2-4 | 27 | 2-9 |
| Plan land-use classifications and density narratives | Specific Plan Section 4.3.2 | 58, 60, 62 | 52, 54, 56 |
| Plan development standards | Specific Plan Table 4.2 | 63 | 57 |
| Plan residential use permissions | Specific Plan Table 4.3 | 64-65 | 58-59 |
| Plan setback and frontage guidance | Specific Plan Section 5.5.3 | 148-150 | 142-144 |
| Plan implementation and project review | Specific Plan Section 7.1 | 179-180 | 173-174 |

The July 18 residential amendment audit found no adopted post-baseline amendment that changes the selected Table 2-4 values. Ordinance 2085's Objective Design Standards remain an applicable but unevaluated layer for multifamily development.

## Approved use and profile treatment

Each of the five designations has three explicit use-permission records:

| Use capability | Candidate status | Product treatment |
|---|---|---|
| `use.single_family_dwelling` | `not_listed` | No ordinary single-family profile. The result does not convert this conservative table status into a complete prohibition conclusion. |
| `use.two_family_dwelling` | `not_listed` | No separate two-family profile. This does not change the project's general rule that a two-unit proposal may fall within multifamily treatment where the controlling source does not separately list a two-family category. |
| `use.multifamily_dwelling` | `permitted_by_right` | One ordinary `multifamily` analysis profile using `multifamily_primary_structure`. Permission remains separate from Zoning Clearance, Architectural Review, hearing, and plan-conformance requirements. |

Only the residential multifamily path is authored. The optional office path described for HD Flex and other nonresidential uses in Specific Plan Table 4.3 remain outside this product phase.

## Supported base-standard matrix

The successor retains exactly the ten already-supported profile capabilities: Zoning Clearance, Architectural Review, height, stories, structure coverage, gross residential density, and the four setback families.

| GIS key | Height | Stories | Coverage | Density | Front, street-side, and interior-side setbacks | Rear setback |
|---|---:|---:|---|---:|---|---|
| `PH-R5` | 135 ft | 10 | No maximum listed | 51-100 DU/AC selected with conflict retained | 10 ft from back of walk | Plan-dependent; no universal numeric value |
| `UV` | 160 ft | 12 | No maximum listed | 100-149 DU/AC | 10 ft from back of walk | Plan-dependent; no universal numeric value |
| `VR` | 160 ft | 12 | No maximum listed | 60-149 DU/AC | 10 ft from back of walk | Plan-dependent; no universal numeric value |
| `UC` | FAA-controlled | FAA-controlled | No maximum listed | 120-250 DU/AC | 10 ft from back of walk | Plan-dependent; no universal numeric value |
| `HDF` | 160 ft | 12 | No maximum listed | 60-149 DU/AC | 10 ft from back of walk | Plan-dependent; no universal numeric value |

`No maximum listed` records the source table's `None` value; it does not mean unlimited development. The literal `FAA` values for UC height and stories remain nonnumeric. The tables contain no rear-setback row, and the plan does not supply a universal rear-yard number elsewhere, so the successor must not substitute zero.

## PH-R5 gross-density conflict and project resolution

The authoritative source stack disagrees for PH-R5:

| Assertion | Range |
|---|---:|
| Title 18 Table 1-1 | 51-100 DU/AC |
| Title 18 Section 18.10.010 zone-purpose text | 51-99 DU/AC |
| Title 18 Table 2-4 | 51-99 DU/AC |
| Specific Plan Section 4.3.2.1 | 51-99 DU/AC |
| Specific Plan Table 4.2 | 51-99 DU/AC |

The project owner accepted candidate `2026-07-19.3` and approved applying the established R5 policy to PH-R5 on July 19, 2026: retain every assertion and select Title 18 Table 1-1's 51-100 DU/AC range in the candidate ruleset. The selected rule must use `project_resolved_with_conditions`. This is a project resolution pending official clarification, not a City correction or a conclusion about a particular parcel.

Re-review is required if the City or codifier clarifies the discrepancy, publishes a newer consolidated code, adopts a relevant amendment, or introduces controlling parcel-specific General Plan, specific-plan, development-agreement, or approval information.

## Explicitly unevaluated qualifications

The successor discloses but does not evaluate:

- the 32-foot height maximum within 20 feet of R1-6L, R1-8L, or R2;
- recreation-space and detailed setback-encroachment standards;
- Specific Plan design guidelines, substantial-conformance review, PDO or project conditions, and proposal-specific measurements;
- Objective Design Standards under Ordinance 2085;
- UC densities above 250 DU/AC that may be allowed through community benefits formalized in a development agreement;
- the HD Flex nonresidential option;
- General Plan or other plan reconciliation, density bonus, affordable-housing adjustments, state-law effects, acreage, parcel unit yield, and proposal compliance.

These topics are not additional supported regulation families. They remain structured qualifications on the ordinary multifamily profiles.

## Approval boundary

This source and policy record authorizes deterministic nonruntime authoring of a direct successor to `2026-07-19.3`. Every new rule remains `approved_for_ruleset: false`, the successor remains `candidate`, and production loading remains prohibited until the complete Block 3 candidate is separately reviewed and approved.
