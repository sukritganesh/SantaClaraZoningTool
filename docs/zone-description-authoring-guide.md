# Zone Description Authoring Guide

**Contract:** Santa Clara residential zone-description catalog `1.0.0`

**Audience:** City staff and other readers who need a concise, plain-language orientation before reviewing detailed standards

**Authoring method:** Offline, source-grounded Codex drafting followed by source review and project-owner acceptance

## Purpose and boundary

The zone-description catalog supplies the short **Property Overview** shown for a successful supported lookup. It is presentation copy, not regulatory data. It does not alter the approved ruleset, replace the detailed standards below it, or determine whether a particular proposal is entitled to approval.

Codex authors descriptions during a maintenance or zone-ingestion task. The running application never calls an AI service and never generates, completes, or rewrites this copy. A reviewed catalog is committed as a versioned input, and identical catalog and zoning inputs produce identical rendered text.

## Required inputs

Before drafting, load the complete supported-zone set rather than considering one zone in isolation:

1. the approved runtime ruleset and its exact zone labels;
2. the official zone-purpose provisions referenced by the ruleset;
3. approved residential use permissions;
4. approved Zoning Clearance and Architectural Review requirements; and
5. any adopted specific-plan classification text referenced for a supported designation.

Candidate research may help locate an official source but must not supply a staff-facing conclusion. Existing accepted descriptions should change only when their sources or comparative context are affected.

## Description contract

Every description must:

- use one paragraph of roughly 55 to 100 words and three or four sentences;
- begin with the exact supported designation and state its human-readable identity;
- explain the zone's general residential character or intensity in ordinary language;
- summarize characteristic housing types without reproducing the full use table;
- name Zoning Clearance and Architectural Review when the approved ruleset requires them;
- use comparative context when it makes a real distinction clearer, such as standard versus larger-lot R1 neighborhoods; and
- remain accurate when read before the parcel-specific standards and qualifications below it.

Prefer phrases such as “is intended for,” “generally accommodates,” and “supports.” Avoid suggesting that a listed use is automatically buildable on a particular parcel.

Descriptions must not:

- repeat exact density, height, setback, coverage, or story values;
- list every permitted or unlisted use;
- infer a use, approval, or development form absent from the cited sources;
- describe a parcel, project, applicant, or likely approval outcome;
- call a missing maximum “unlimited”;
- hide an airport, specific-plan, or other source-defined characteristic that is central to the zone's identity; or
- describe the Explorer as a complete entitlement analysis or legal or planning determination.

## Comparative drafting

Draft the complete set together so adjacent descriptions use consistent distinctions:

- `R1-6L` is the standard single-family neighborhood designation; `R1-8L` is its larger-lot counterpart.
- `R2` introduces greater housing variety while retaining a low-density neighborhood character.
- `R3` and `R4` move through medium- and high-density residential forms.
- `R5` is very-high-density residential, while `R6` emphasizes high-intensity, transit-oriented neighborhoods.
- `PH-R5`, `UV`, `VR`, `UC`, and `HDF` retain their Patrick Henry plan identities and should not be flattened into their nearest citywide density category.

Comparisons are orientation aids, not independent rules. They must remain traceable to official purpose language or approved source-backed distinctions.

## Examples

Acceptable standard/larger-lot distinction:

> R1-8L is Santa Clara's larger-lot single-family residential zone, intended to preserve established neighborhoods with more spacious parcels than the standard R1-6L zone. It generally accommodates detached single-family homes and related residential improvements in a lower-intensity setting. New construction and substantial changes generally require Zoning Clearance and Architectural Review.

Acceptable low-density transition:

> R2 is Santa Clara's low-density residential zone, designed to maintain a neighborhood-scale character while allowing more housing variety than the R1 zones. It generally accommodates single-family, two-family, and smaller multifamily residential development without taking on the scale of higher-density zones. New construction and substantial changes generally require Zoning Clearance and Architectural Review.

Unacceptable:

> You can build up to 19 units per acre here and your project will be approved after design review.

The rejected example repeats a detailed number, addresses the reader's unverified proposal, and promises an outcome the zone description cannot establish.

## Maintenance workflow

1. Produce a complete source-grounded comparison matrix from the current approved ruleset and official purpose provisions.
2. Give Codex this guide, the complete matrix, and the existing catalog.
3. Generate descriptions only for new or materially affected zones.
4. Review every changed sentence against its recorded source references.
5. Run `python -B scripts/validate_zone_descriptions.py`.
6. Review the rendered desktop and mobile overviews before project-owner acceptance.

Validation detects structural and provenance errors, but human review remains responsible for meaning, tone, and source fidelity.
