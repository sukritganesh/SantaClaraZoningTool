# Manual Testing Addresses

Start the application from the repository root:

```bash
.venv/bin/python -m flask --app santa_clara_zoning.web run
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) and try these addresses.

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
