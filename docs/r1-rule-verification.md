# R1 Rule-Level Verification

**Verified through:** July 16, 2026

**Source baseline:** Santa Clara Zoning Code, Title 18 - July 2025

**Scope:** Single-family primary structures in the R1-6L and R1-8L zones. This document verifies source meaning before machine-readable rules are created. It is not a ruleset, entitlement analysis, or legal opinion.

## Verification states

- **Verified base value:** The source value and controlling definition are clear enough to store as a base-zone fact.
- **Verified with conditions:** The base value is clear, but identified parcel facts or exceptions can change its application. Those conditions must travel with the value.
- **Review required:** Source provisions conflict or require a Director/staff determination. The application must not silently select an answer.
- **Deferred:** The subject is outside the first ruleset even if a source value exists.

The source document does not state a precise effective date for the consolidated July 2025 edition. A future ruleset may use `July 2025` as the source version, but it must not invent an effective date.

## Use permission and approval path

### Single-family dwelling

**Finding:** A single-family dwelling is marked `P` for both R1-6L and R1-8L in Section 18.10.020, Table 2-1. `P` means allowed by right. Article 8 defines a single-family dwelling as one dwelling unit on one parcel for one single household; manufactured housing and mobile homes on permanent foundations are included.

**Required qualifications:**

- Section 18.10.020(D) requires Zoning Clearance for a permitted-by-right use involving construction.
- Chapter 18.126 governs Zoning Clearance.
- Section 18.120.020 requires Architectural Review before permits for buildings, structures, and exterior alterations. A Development Review Hearing is required for listed single-family projects, including a new or expanded second story and homes resulting in five or more bedrooms or bathrooms.
- Table 2-1 also lists two-family dwellings and ADUs in R1, subject to separate chapters. They remain explicitly outside this single-family MVP.

**Disposition:** **Verified base permission.** Store the use status as `permitted_by_right`, never as `no_approval_required`. Attach Zoning Clearance and Architectural Review as separate approval-path facts.

## Dimensional standards

### Structure coverage

**Base value:** 40 percent in R1-6L and R1-8L, for parcels both below and at or above 10,000 square feet. Source: Section 18.10.030, Table 2-3.

**Meaning and exclusions:**

- Article 8 defines structure coverage as the portion of a parcel covered by structures, whether or not intended for occupancy.
- The definition excludes structure overhangs, paved areas, walks, and swimming pools.
- The separate definition of `Structure` includes covered patios but excludes outdoor paved and similar recreation areas. Coverage therefore is not merely the primary house footprint; other covered structures can count.
- Section 18.30.020 additionally states that its permitted projections are not included in parcel coverage.
- The City's Planning FAQ independently describes the 40-percent limit as covering buildings and directs users to Planning for a site-specific calculation.

**Disposition:** **Verified base value.** It is safe to store and display `40% maximum structure coverage`. Calculating remaining buildable square footage is deferred until reliable existing-structure footprints and all included/excluded structure facts are available.

### Height

**Base value:** 25 feet in R1-6L and R1-8L. Source: Section 18.10.030, Table 2-3.

**Measurement and exceptions:**

- Section 18.30.040 measures height vertically from `grade` to the roof point specified for flat, mansard, pitched, or hipped roofs.
- Article 8 defines adjacent grade using the lowest finished ground elevation within five feet of the exterior wall, with a property-line or public-way rule where the available distance is less than five feet.
- Section 18.30.040(C) allows listed nonhabitable appurtenances, such as chimneys, antennas, cupolas, elevators, and mechanical appurtenances, to exceed the maximum by no more than 25 percent. A discretionary permit may impose a lower height.
- Section 18.10.040(B)(3) separately limits exposed basement wall height for primary structures to four feet above finished grade.
- Accessory structures and ADUs have separate standards and are not governed solely by this primary-structure value.

**Disposition:** **Verified base value.** Store `25 ft` as the base maximum, together with the measurement method and an exception-family flag. Do not describe 25 feet as an absolute cap on every rooftop element.

### Number of stories

**Base value:** Two stories in R1-6L and R1-8L. Source: Section 18.10.030, Table 2-3.

**Definition limitation:** Article 8 defines a half-story but does not provide a general definition or counting method for `Story`. Accessory structures also have a separate one-and-one-half-story provision.

**Disposition:** **Verified base value for retrieval.** Store and display `2 stories maximum`. Automated proposal-level story counting is deferred until the governing counting convention is confirmed.

### Setback measurement shared conditions

Table 2-3 supplies the base setback values, while Sections 18.10.040, 18.30.020, and 18.30.050 control their application.

Mandatory conditions include:

- Section 18.30.050 generally measures setbacks from parcel lines and warns that parcel lines do not necessarily coincide with the back of the sidewalk.
- Table 2-3 says street-adjacent measurements use the curb face, adopted plan line, or edge of right-of-way. Section 18.30.050 separately requires measurement from an official plan line where one exists. These provisions are not sufficiently self-executing for a parcel-geometry-only calculation.
- On a corner parcel, the narrower street frontage is the front; the other street frontage is the corner side. Irregular and flag parcels have additional rules.
- If at least four parcels on a block face are legally improved, Section 18.30.050 permits an average front setback when that average is less than the current requirement. The downloaded GIS does not contain the facts required to calculate this reliably.
- A qualifying pre-1955 parcel averaging less than 50 feet wide may reduce each interior side setback to 10 percent of parcel width, but not below three feet.
- One-half of an alley may count toward a rear setback.
- Residential encroachments in Table 2-6 allow specified bay windows, chimneys, porches, stairs, eaves, and other features to project into setbacks. General projections also appear in Section 18.30.020; zone-specific residential standards control when they conflict with the general standards.
- Official plan lines, rights-of-way, and public-use easements can prevent an otherwise listed encroachment. Those layers are not part of the current GIS snapshot.
- Legal nonconforming structures may retain or extend some existing conditions under Chapters 18.90 and 18.92. In particular, qualifying one-story residential expansions may extend an existing nonconforming side setback of at least three feet toward the rear.
- Section 18.10.040(B)(3) allows certain disaster reconstruction to reuse a prior footprint and setbacks.

The base values below are therefore retrievable standards, not a computed buildable envelope.

### Front setback

| Standard | R1-6L | R1-8L | Verification |
|---|---:|---:|---|
| First story | 20 ft | 20 ft | Verified with conditions |
| Second story | 25 ft | 25 ft | Verified with conditions |

The block-face averaging provision can reduce the required front yard. The code does not clearly state in this provision whether averaging changes both first- and second-story lines. A future ruleset must preserve that ambiguity instead of applying the average automatically to the second story.

### Interior side setback

| Standard | R1-6L | R1-8L | Verification |
|---|---:|---:|---|
| First story | 5 ft | Paired yards of 6 ft and 9 ft | Verified with conditions |
| Second story | 10 ft | Paired yards of 11 ft and 14 ft | Verified with conditions |

For R1-8L, the paired values cannot be reduced to one symmetric number. The narrow-parcel exception, residential encroachments, and nonconforming-structure rules require additional facts before parcel-specific application.

### Corner-side setback

| Standard | R1-6L | R1-8L | Verification |
|---|---:|---:|---|
| First story | 10 ft | Conflict: Table 2-3 says 10 ft; Section 18.10.040(B)(1) says at least 15 ft | R1-6L conditional; R1-8L review required |
| Second story | 15 ft | 15 ft | Verified with conditions |

Section 18.04.020(G) says the more restrictive provision applies when requirements conflict, which supports 15 feet for the R1-8L first-story street side. Because the same consolidated code still presents an explicit 10-foot table cell, the first machine-readable ruleset must not silently overwrite the conflict. It should mark the R1-8L first-story corner-side standard `requires_staff_confirmation` until the City confirms the intended codification.

Section 18.10.040(B)(1) also requires at least 35 percent of the R1-8L street-side setback to remain landscaped. Landscaping is outside the first ruleset but should remain attached as a future cross-reference.

### Rear setback

**Base value:** 20 feet for both single- and multi-story elements in R1-6L and R1-8L.

**Disposition:** **Verified with conditions.** Alley credit, permitted encroachments, accessory-structure standards, and legal nonconformities can change parcel- or feature-specific application.

## Deferred Table 2-3 subjects

| Subject | Source value | Reason deferred |
|---|---|---|
| Minimum parcel area | 6,000 sq ft R1-6L; 8,000 sq ft R1-8L | Applies to newly created parcels. Section 18.10.040(A)(1) preserves some smaller parcels shown on pre-code maps. It is not a test that an existing parcel is unbuildable. |
| Minimum street frontage | 60 ft R1-6L; 70 ft R1-8L | Primarily a parcel-creation standard with a pre-code-map exception down to 45 feet. |
| Driveway approach length | 20 ft | Section 18.10.040(A)(3) limits applicability to a driveway from a public street to a garage serving one or two dwelling units. |
| Density | 0.1-10 dwelling units per acre | Section 18.10.030(B) makes maximum density subject to the General Plan or an applicable plan. State-law and two-unit interactions are outside scope. |
| Daylight plane | 45-degree statement in Table 2-3 | The text is broadly phrased for structures adjacent to R1/R2 and is not needed for the first base-value retrieval. It requires separate interpretation and geometry. |
| Setback encroachments | Table 2-6 and Section 18.30.020 | Proposal-feature evaluation is deferred; the first result should report base setbacks and disclose that allowed encroachments are not evaluated. |

## Gate for the first machine-readable ruleset

The next ruleset may include:

- single-family dwelling use status, with approval-path cross-references;
- maximum structure coverage percentage;
- base maximum height and maximum stories;
- base first- and second-story setbacks;
- structured exception-family references and validation status; and
- exact source citations and source-version identifiers.

It must not yet:

- calculate a buildable envelope from GIS parcel geometry;
- calculate remaining structure-coverage capacity;
- evaluate setback averaging, legal nonconformity, projections, official plan lines, or alley credit;
- treat the R1-8L first-story corner-side conflict as resolved;
- evaluate accessory structures, ADUs, two-unit projects, or density; or
- imply that permitted-by-right construction requires no City review.

Every displayed number should be labeled a **base-zone standard**. The result must list unevaluated exception families and preserve `review required` outcomes where the source is conflicting or incomplete.

## Source trace

| Topic | Controlling or supporting source |
|---|---|
| Interpretation and conflicts | Sections 18.04.020 and 18.04.030 |
| Use permission and Zoning Clearance trigger | Section 18.10.020, Table 2-1; Chapter 18.126 |
| Numeric development standards | Section 18.10.030, Table 2-3 |
| Residential exceptions and R1-8L side yards | Section 18.10.040; Table 2-6 |
| General projections | Sections 18.30.010 and 18.30.020 |
| Height measurement and exceptions | Section 18.30.040 |
| Setback measurement and exceptions | Section 18.30.050 |
| Nonconforming structures | Chapters 18.90 and 18.92 |
| Architectural Review | Section 18.120.020 |
| Definitions | Article 8: `Dwelling, Single-Family`, `Grade`, `Parcel`, `Setback`, `Story, Half`, `Structure`, `Structure Coverage`, and `Structure, Primary` |
| Post-baseline amendment status | `docs/title18-amendment-audit.md` |
