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

## Property overviews and result guidance

Every successful supported lookup should show a **Property Overview** with one concise source-grounded paragraph. Exact numeric standards remain in the detailed cards and table below it. The scope notice and `i` source-control explanation belong in a separate **How to use this result** section.

| Address | Expected overview distinction |
|---|---|
| `636 Barto Street` | R1-6L is identified as Santa Clara's standard single-family residential zone. |
| `108 Brookside Avenue` | R1-8L is clearly distinguished as the larger-lot single-family counterpart. |
| `1240 White Drive` | R2 is described as low-density residential with more housing variety than R1. |
| `1577 Pomeroy Avenue` | R3 is described as a medium-density transition to more intensive multifamily areas. |
| `1400 Coleman Avenue` | R4 is described as high-density multifamily housing below the R5/R6 intensity. |
| `3105 Patrick Henry Drive` | PH-R5 retains its Patrick Henry Very-High-Density Residential identity. |
| `3200 Patrick Henry Drive` | UV retains its transit-oriented Urban Village identity. |
| `4701 Patrick Henry Drive` | VR retains its primarily residential Village Residential identity. |
| `4650 Old Ironsides Drive` | UC identifies its urban transit setting and airport flight-path context. |
| `4633 Old Ironsides Drive` | HDF explains its flexible residential/employment transition while identifying the Explorer's residential scope. |

Overview checklist:

- confirm every paragraph begins with the exact displayed zoning designation;
- confirm the paragraph gives a general zone orientation rather than repeating density, height, coverage, story, or setback numbers;
- confirm Zoning Clearance and Architectural Review are named without promising project approval;
- confirm **Scope notice** and **Source details** do not appear inside the overview panel and instead appear under **How to use this result**;
- review wide desktop and 375-pixel mobile layouts, including heading order and screen-reader navigation; and
- confirm lookup-failure and review-required outcomes do not receive a zone overview or staff-guidance section.

R5 and R6 have reviewed descriptions in the catalog but no live-address fixture in the July 18 GIS snapshot. Their overview copy is covered by synthetic automated presentation tests.

## Parcel and zoning context maps

Successful supported lookups place the property identity and local context map side by side on wider screens and stack the map below the identity on narrow screens. Parcel and zoning geometry comes from the pinned July 18 City snapshot; the OpenStreetMap street layer is optional visual context and does not affect the result.

| Address | Expected map behavior |
|---|---|
| `2852 Sycamore Way` | Small R1-6L parcel fits closely; the parcel has a white halo and dark-green outline, and nearby R1-6L zoning uses cobalt blue. |
| `1240 White Drive` | R2 parcel and nearby supported polygons load; R2 uses emerald green and any visible R1/R3 polygons retain their distinct blue/purple assignments. |
| `1577 Pomeroy Avenue` | R3 zoning uses purple without obscuring the selected-parcel outline. |
| `3105 Patrick Henry Drive` | The larger PH-R5 parcel produces a wider automatic view and uses magenta. |
| `4650 Old Ironsides Drive` | UC uses brown; nearby PH-R5, UV, VR, and HDF polygons remain distinguishable as magenta, teal, olive, and charcoal. |
| `4633 Old Ironsides Drive` | HDF uses charcoal and remains distinct from every colored Patrick Henry designation. |
| `1500 Warburton Avenue` | Controlled outside-snapshot result with no map shell or geometry response. |
| `324 Los Padres Boulevard` | Controlled ambiguity with no map shell or automatically selected parcel. |

Map interaction checklist:

- confirm the initial view fits the selected parcel without zooming out to the entire city;
- confirm the selected parcel has a clearly dominant thick white-and-dark-green outline over every supported zoning color;
- move the pointer across differently colored supported zoning polygons and confirm a compact `Zoning: <designation>` tooltip follows the hovered polygon without exposing an address, APN, object ID, or regulatory data;
- use the keyboard-accessible plus/minus controls, touch pinch, and drag while confirming panning remains within the returned local context and zoom-out stops one level beyond the initial view;
- verify the narrow collapsed **Map legend** disclosure opens with pointer, touch, and keyboard input and contains the selected parcel, concise outside-overlay key, and every supported zone code currently shown using the distinct categorical palette;
- confirm the text states that unshaded land is outside the Explorer's supported overlay and is not necessarily unzoned;
- block `tile.openstreetmap.org` or set an invalid `MAP_TILE_URL`, then confirm the local colored polygons and parcel outline remain visible with a street-basemap warning;
- make `/api/property-map` unavailable and confirm the standards remain usable with a controlled map message;
- disable JavaScript and confirm the ordinary zoning result and explanatory map fallback remain readable;
- check the map at wide desktop and 375-pixel mobile widths, with keyboard-only navigation, a screen reader, forced colors/high contrast, and reduced motion; and
- confirm visible OpenStreetMap attribution remains on the map whenever the default street tiles are configured.

## Exact regulatory source evidence

Open the `i` source popover on a supported result. Every numbered citation should offer **View exact source**, which opens a dedicated tab without replacing the zoning result. The popover should not include a redundant **Source receipt** link; the complete numbered source appendix remains available at the bottom of the result and in print.

Confirm every successful result includes one concise **Source details** note inside **How to use this result**, explaining that the `i` controls open supporting citations and exact sources. Landing, lookup-failure, and review-required states should not show that note.

| Result and control | Expected exact evidence |
|---|---|
| `636 Barto Street`, R1-6L height | Title 18 PDF page 25 / printed page 2-7, with the height row label and R1-6L `25` cell highlighted. |
| `1240 White Drive`, R2 height | The same Title 18 table page, but the distinct R2 `32` cell is highlighted. |
| `3105 Patrick Henry Drive`, PH-R5 height | Patrick Henry plan PDF page 63 / printed page 57, with Table 4.2 height row and `135` cell highlighted. |
| `4650 Old Ironsides Drive`, UC height | Patrick Henry Table 4.2 height row and the UC `FAA` cell highlighted. |
| R1-8L corner-side setback conflict | Each source in the multi-source receipt opens its own exact table, code paragraph, audit, or verification target without presenting the rejected assertion as the selected value. |
| Any density source | Table 1-1 opens at the exact zone row and density cell; supporting project decisions open as native, escaped verification records. |

Evidence-viewer checklist:

- confirm the page shows regulation, zone, displayed result, source classification, title/version/effective date, locator, checksum, and human-verification status;
- compare the highlighted excerpt with the parallel DOM text and the checksummed original PDF; confirm the notice says the highlight is only a navigation aid;
- use Fit width, zoom in/out, Previous/Next, Page Up/Page Down, arrow, Home/End, plus/minus, and ordinary browser printing with keyboard-only input;
- test a multi-page citation and confirm every referenced page remains available when JavaScript is disabled;
- check automatic highlight scrolling, mobile horizontal panning, screen-reader announcements and excerpts, forced colors/high contrast, reduced motion, and print layout;
- make the evidence provider or page asset unavailable and confirm the numbered source appendix and zoning result remain present while evidence returns a controlled unavailable response;
- alter no catalog IDs by hand: unknown targets, page indexes, document IDs, and traversal-like paths should return 404 without exposing a local filesystem path; and
- confirm candidate Drive research, inventories, and live Drive/City document requests never appear in staff-facing source controls.

## Supported residential results

| Address | Expected zone | Useful check |
|---|---|---|
| `636 Barto Street` | `R1-6L` | Single-family standards; the unevaluated Chapter 18.24 pathway and standalone qualifications section are not displayed, while the corner-lot qualification appears beside the street-side setback |
| `108 Brookside Avenue` | `R1-8L` | R1 standards with the retained corner-side conflict beside the affected setback and competing source values available in its collapsed details |
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
