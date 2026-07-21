# Manual Testing Addresses

Start the application from the repository root:

```bash
.venv/bin/python -m flask --app santa_clara_zoning.web run
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) and try these addresses.

## Local address autocomplete

The form remains an ordinary GET lookup when JavaScript is unavailable. With JavaScript enabled, verify these discovery cases before submitting the address matrix below.

| Enter | Expected suggestion behavior |
|---|---|
| `12` | No popup choices; the live status asks for at least three address characters. |
| `1240 whi` | One `1240 White Drive` choice; click or press Down then Enter and confirm the R2 lookup runs immediately. |
| `barto` | Eight of 39 naturally ordered Barto Street choices and a prompt to continue typing. |
| `3710 el camino real` | Eight of 577 address and unit choices; the popup reports the full count and asks for a street or unit number instead of choosing a unit. |
| `324 los padres` | One canonical choice with a two-record warning; selecting it retains the controlled ambiguous-address result. |
| `1500 warburton` | A City address choice that retains the controlled outside-supported-residential-snapshot result after selection. |
| `99999 no such street` | A no-results message while the ordinary lookup button remains usable. |

Interaction checklist:

- select with a mouse and touch input;
- use Down/Up, Home/End, Enter, Escape, and Tab without losing ordinary text editing or focus behavior;
- confirm live announcements report loading, result counts, truncation, no results, and suggestion unavailability;
- type one query and quickly replace it with another to confirm stale results never replace the current list;
- inspect the unit-heavy case on a narrow mobile viewport, in forced-colors/high-contrast mode, and with reduced motion enabled; and
- disable JavaScript or make the suggestion endpoint unavailable, then confirm entering a full address and pressing **Look up zoning** still works.

## Supported residential results

| Address | Expected zone | Useful check |
|---|---|---|
| `636 Barto Street` | `R1-6L` | Single-family standards and the separate Chapter 18.24 two-home pathway |
| `108 Brookside Avenue` | `R1-8L` | R1 standards and the retained corner-side setback conflict |
| `1240 White Drive` | `R2` | Single-family, two-family, and multifamily uses with shared standards |
| `1577 Pomeroy Avenue` | `R3` | Two-family and multifamily uses; tiered structure coverage |
| `1400 Coleman Avenue` | `R4` | Two-family and multifamily uses |
| `3105 Patrick Henry Drive` | `PH-R5` | Plan-dependent rear setback and retained density conflict |
| `3200 Patrick Henry Drive` | `UV` | Patrick Henry Urban Village standards |
| `4701 Patrick Henry Drive` | `VR` | Patrick Henry Village Residential standards |
| `4650 Old Ironsides Drive` | `UC` | FAA-controlled height and stories |
| `4633 Old Ironsides Drive` | `HDF` | Patrick Henry High-Density Flex residential standards |

There are no live-address fixtures for `R5` or `R6`: the preserved July 18 GIS snapshot contains zero exact features for both designations. Their rules remain covered by synthetic automated tests.

## Controlled outcomes

| Address | Expected result |
|---|---|
| `1500 Warburton Avenue` | Address found, but outside the supported residential snapshot |
| `324 Los Padres Boulevard` | Ambiguous address; no regulations attached |
| `99999 No Such Street` | Address not found; no regulations attached |

These addresses test deterministic routing against the preserved snapshots. They are not evidence of complete entitlement or buildability analysis.
