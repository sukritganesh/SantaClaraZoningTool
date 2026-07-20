# Residential Density Title 18 Amendment Audit Supplement

**Audit cutoff:** July 18, 2026

**Baseline:** Santa Clara Zoning Code, Title 18 - July 2025

**Capability:** `standard.gross_residential_density` for R1-6L, R1-8L, and R2-R6

This checksum-pinned supplement determines whether the post-baseline sources already reviewed for the residential expansion alter the base-zone gross residential density ranges. It does not replace `docs/residential-title18-amendment-audit.md` and is not a legal opinion.

## Finding

No adopted post-July-2025 amendment identified through the cutoff changes the R1-R6 base density ranges in Table 1-1, the zone-purpose text, or Table 2-3:

- Ordinance 2085 adds Objective Design Standards but does not amend these density ranges.
- Ordinance 2086 concerns the El Camino Real Corridor and does not amend these selected base-zone ranges.
- Cleanup #3 was not treated as adopted law at the cutoff. Its proposed `TN`-to-`R6` mapping remains a source/GIS refresh trigger, not authority to alter or operationalize an R6 range.

This finding does not resolve the R5 or R6 inconsistencies already present inside the July 2025 baseline. Those assertions and the project-owner selection policy are recorded in `docs/residential-density-rule-verification.md`.

## Recheck triggers

Re-run this audit before approval or runtime integration if any of the following occurs:

- the City publishes a consolidated code newer than July 2025;
- Cleanup #3 or another ordinance affecting R1-R6 density becomes effective;
- the City issues a correction or interpretation for Table 1-1, Section 18.10.010, or Table 2-3;
- an exact parcel's General Plan, Master Plan, Specific Plan, Area Plan, development agreement, or other controlling layer is introduced into the evaluator; or
- the project begins density-bonus, state-law override, acreage, or unit-yield evaluation.
