# Ruleset v2 Authoring Guide

**Status:** Approved authoring contract; schema implemented, data migration pending

**Last updated:** July 16, 2026

**Approved by:** Project owner on July 16, 2026

This guide defines how humans and AI-assisted extraction workflows must represent supported regulations in the deterministic ruleset. `rulesets/schema/ruleset-v2.schema.json` implements the local structural parts of this contract.

The current v1 schema and approved Santa Clara ruleset remain authoritative until this design is approved, implemented, migrated, and validated.

## Relationship to other project artifacts

- `supported-regulations.md` defines **what** the product supports and where support stops.
- This guide defines **how** supported capabilities should be authored in ruleset v2.
- JSON Schema v2 enforces the local structural parts of this guide.
- Domain validation will enforce cross-record references, identities, conflict integrity, and deterministic semantics that JSON Schema cannot fully express.
- `docs/r1-rule-verification.md` remains the legal-source trace for Santa Clara values.
- `docs/progress.md` records whether this draft has been reviewed and implemented.

Examples in this guide illustrate the proposed representation. They do not replace the approved ruleset or authorize runtime use.

## Normative language

`MUST`, `MUST NOT`, `SHOULD`, and `MAY` describe authoring requirements. An AI-assisted workflow must follow the same requirements as a human author. AI-produced records remain candidate data until their sources and values are verified and approved.

## Design goals

Ruleset v2 should make these operations simple and deterministic:

1. Use the GIS designation as an exact zone key.
2. Retrieve all supported regulations owned by that zone.
3. Retrieve one regulation by its stable capability ID.
4. Preserve a separate legal identity and amendment path for each zone's regulation.
5. Reuse source documents, citations, definitions, exceptions, and conflicts by reference.
6. Represent setbacks as a base requirement plus explicit vertical adjustments.
7. Reject ambiguous or incomplete semantics instead of relying on runtime interpretation.

The JSON ruleset is a versioned legal-data artifact, not a UI response and not a database-specific storage model.

## Approved top-level hierarchy

The canonical hierarchy is zone-first:

```text
ruleset
├── metadata
├── shared
│   ├── source_documents
│   ├── citations
│   ├── definitions
│   └── exception_families
├── zones
│   ├── R1-6L
│   │   └── regulations
│   └── R1-8L
│       └── regulations
├── conflicts
├── not_evaluated
└── disclaimer
```

`zones` MUST be an object keyed by the exact canonical designation returned by the validated GIS pipeline. The zone key is the zone's identity; a duplicate `zone_code` field inside the object is unnecessary.

Each zone MUST contain a `regulations` object keyed by capability ID from the supported-regulations catalog. A runtime lookup should therefore follow this path:

```text
zones[zone_code].regulations[capability_id]
```

The ruleset MUST NOT use one top-level rule array that requires scanning every record's zone applicability.

## Zone ownership and rule identity

Each zone owns its regulation records. Equal current values do not make two zone regulations the same legal rule.

For example, R1-6L and R1-8L each receive their own maximum-height record even when both currently specify 25 feet. This intentional duplication permits one zone to be amended, re-verified, superseded, or placed in conflict without changing the other.

### Capability IDs

A capability ID identifies the meaning of a supported regulation across jurisdictions and zones. It MUST match the catalog, such as:

- `use.single_family_dwelling`
- `approval.zoning_clearance`
- `standard.maximum_primary_structure_height`
- `setback.front`

The capability ID is the key inside the zone's `regulations` object. Authors MUST NOT invent a near-synonym when a cataloged capability already exists.

### Rule IDs

A rule ID identifies one zone-owned regulation record. The convention is:

```text
us.ca.<jurisdiction-slug>.<zone-slug>.<capability-id>
```

Examples:

```text
us.ca.santa_clara.r1-6l.standard.maximum_primary_structure_height
us.ca.santa_clara.r1-8l.standard.maximum_primary_structure_height
us.ca.santa_clara.r1-8l.setback.interior_side
```

Rule IDs MUST be unique across the ruleset, stable across value-only amendments, and separate for every zone. A rule ID MUST NOT contain a current value, effective date, array position, or source page number.

Zone membership is established by containment under `zones`; it MUST NOT be repeated as a multi-zone applicability list on the rule.

## Shared reference data

The following data belongs under the top-level `shared` object rather than inside every zone:

- Source-document identity, version, effective date, local path, and checksum
- Citation locators and topics
- Defined terms and their source locations
- Exception-family descriptions and treatment

These collections SHOULD be objects keyed by stable IDs. Zone rules refer to them by ID. Reusing a citation does not merge the zone rules that cite it.

Conflicts remain top-level records because one conflict can preserve multiple assertions and reference one or more affected zone-owned rule IDs. The selected value still belongs in the affected zone rule, while the conflict record preserves all assertions and the approved resolution.

Cross-reference validation MUST confirm that every referenced ID exists and that no shared record is duplicated under conflicting IDs without an explicit reason.

## Common zone-regulation record

Every zone-owned regulation should use a common envelope:

| Field | Purpose |
|---|---|
| `rule_id` | Globally unique identity for this zone's regulation |
| `label` | Concise human-readable name |
| `requirement` | Capability-specific deterministic payload |
| `applicability` | Non-zone context such as structure type or corner-lot status |
| `conditions` | Verified qualifications that do not fit the typed payload |
| `exception_family_ids` | Known exception families, including those not evaluated |
| `validation_status` | Verification or project-resolution state |
| `conflict_id` | Referenced conflict record, or `null` |
| `approved_for_ruleset` | Explicit approval gate |

Zone applicability MUST NOT appear in this envelope because the containing zone already establishes it.

The `requirement` payload MUST use a type defined for the capability family. Numeric quantities MUST contain an explicit unit. Consequential assertions MUST retain exact source references at the narrowest practical level.

Conditions are not a substitute for structured data. If a condition changes a number, trigger, applicability decision, or operation that the engine must evaluate, it MUST be represented in typed fields once that behavior is supported.

## Setback representation

A setback regulation is one zone-owned capability record with:

1. one `base` requirement; and
2. zero or more `adjustments`.

First- and second-story requirements MUST NOT be modeled as unrelated regulations. The base expresses the ordinary setback; an adjustment expresses when and how that setback changes vertically.

### Base requirements

A base setback value may be:

- `distance` — one minimum distance; or
- `paired_distances` — two coordinated minimum side-yard distances.

A paired value MUST preserve both requirements and MUST NOT be averaged or converted into a symmetric value. Unless the controlling source assigns physical sides, members should use semantic roles such as `smaller_setback` and `larger_setback`, with physical assignment marked `proposal_dependent`.

### Adjustment triggers

The schema trigger types are:

| Trigger | Meaning |
|---|---|
| `story_at_or_above` | Applies beginning with the specified story number |
| `height_above` | Applies above an explicit height threshold |

Trigger boundaries MUST be unambiguous. “At or above” and “above” are different legal tests and must not be silently interchanged.

The initial Santa Clara data uses story-based triggers. The v2 schema can represent a height-triggered shape for future jurisdictions, but it remains unsupported operationally until cataloged, sourced, validated, and evaluated.

### Adjustment effects

The schema effect types are:

| Effect | Meaning |
|---|---|
| `replace_total_minimum` | The supplied value is the complete setback required when the trigger applies |
| `add_to_base` | The supplied value is added to the base requirement |

Authors MUST determine which meaning the controlling text states. They MUST NOT convert between the two merely because the arithmetic happens to produce the same number.

An adjustment MUST include its own ID, trigger, effect, and source references. If a setback contains multiple adjustments, `adjustment_resolution` MUST list their IDs in highest-to-lowest precedence order using `highest_precedence_applicable`. The evaluator selects the first applicable adjustment. Validation must reject multiple adjustments without this resolution or with missing, duplicated, or extraneous IDs.

### Setback applicability

The rule envelope should identify relevant context, including:

- `structure_type`
- `lot_context`, such as `all` or `corner`

Parcel orientation, averaging, official plan lines, encroachments, alley credit, historical-lot exceptions, and legal nonconformities remain exception families unless and until their deterministic inputs and evaluators are supported.

## Representative zone-first examples

The examples below are intentionally partial. Ellipses indicate unrelated top-level metadata or shared records, not omitted fields inside a production rule.

### Independent records for an equal height value

```json
{
  "zones": {
    "R1-6L": {
      "regulations": {
        "standard.maximum_primary_structure_height": {
          "rule_id": "us.ca.santa_clara.r1-6l.standard.maximum_primary_structure_height",
          "label": "Maximum primary-structure height",
          "requirement": {
            "kind": "maximum_quantity",
            "value": {"number": 25, "unit": "ft"},
            "source_refs": ["r1-standards-table", "height-method"]
          },
          "applicability": {
            "structure_type": "single_family_primary_structure",
            "lot_context": "all"
          },
          "conditions": [
            "Base maximum; listed nonhabitable appurtenances are not evaluated."
          ],
          "exception_family_ids": ["height-measurement-and-appurtenances"],
          "validation_status": "verified_with_conditions",
          "conflict_id": null,
          "approved_for_ruleset": true
        }
      }
    },
    "R1-8L": {
      "regulations": {
        "standard.maximum_primary_structure_height": {
          "rule_id": "us.ca.santa_clara.r1-8l.standard.maximum_primary_structure_height",
          "label": "Maximum primary-structure height",
          "requirement": {
            "kind": "maximum_quantity",
            "value": {"number": 25, "unit": "ft"},
            "source_refs": ["r1-standards-table", "height-method"]
          },
          "applicability": {
            "structure_type": "single_family_primary_structure",
            "lot_context": "all"
          },
          "conditions": [
            "Base maximum; listed nonhabitable appurtenances are not evaluated."
          ],
          "exception_family_ids": ["height-measurement-and-appurtenances"],
          "validation_status": "verified_with_conditions",
          "conflict_id": null,
          "approved_for_ruleset": true
        }
      }
    }
  }
}
```

The two values match, but the rule IDs and records remain independent. Both may reference the same shared citations and exception family.

### Scalar base setback with a story-based total minimum

This proposed R1-6L representation treats 20 feet as the base front setback and 25 feet as the total minimum beginning at the second story:

```json
{
  "zones": {
    "R1-6L": {
      "regulations": {
        "setback.front": {
          "rule_id": "us.ca.santa_clara.r1-6l.setback.front",
          "label": "Front setback",
          "requirement": {
            "kind": "setback",
            "base": {
              "value": {"kind": "distance", "number": 20, "unit": "ft"},
              "source_refs": ["r1-standards-table"]
            },
            "adjustments": [
              {
                "adjustment_id": "second-story-total",
                "trigger": {"kind": "story_at_or_above", "story": 2},
                "effect": {
                  "kind": "replace_total_minimum",
                  "value": {"kind": "distance", "number": 25, "unit": "ft"}
                },
                "source_refs": ["r1-standards-table"]
              }
            ]
          },
          "applicability": {
            "structure_type": "single_family_primary_structure",
            "lot_context": "all"
          },
          "conditions": [
            "Block-face averaging and parcel-specific measurement controls are not evaluated."
          ],
          "exception_family_ids": [
            "setback-measurement-and-plan-lines",
            "front-setback-block-average",
            "setback-encroachments",
            "legal-nonconformities",
            "disaster-reconstruction"
          ],
          "validation_status": "verified_with_conditions",
          "conflict_id": null,
          "approved_for_ruleset": true
        }
      }
    }
  }
}
```

### Paired base setbacks with a paired story adjustment

This proposed R1-8L representation preserves the coordinated 6/9-foot base pair and the 11/14-foot total pair beginning at the second story:

```json
{
  "zones": {
    "R1-8L": {
      "regulations": {
        "setback.interior_side": {
          "rule_id": "us.ca.santa_clara.r1-8l.setback.interior_side",
          "label": "Interior-side setbacks",
          "requirement": {
            "kind": "setback",
            "base": {
              "value": {
                "kind": "paired_distances",
                "members": [
                  {"role": "smaller_setback", "number": 6, "unit": "ft"},
                  {"role": "larger_setback", "number": 9, "unit": "ft"}
                ],
                "relationship": "coordinated_pair",
                "physical_assignment": "proposal_dependent"
              },
              "source_refs": ["r1-standards-table"]
            },
            "adjustments": [
              {
                "adjustment_id": "second-story-total-pair",
                "trigger": {"kind": "story_at_or_above", "story": 2},
                "effect": {
                  "kind": "replace_total_minimum",
                  "value": {
                    "kind": "paired_distances",
                    "members": [
                      {"role": "smaller_setback", "number": 11, "unit": "ft"},
                      {"role": "larger_setback", "number": 14, "unit": "ft"}
                    ],
                    "relationship": "coordinated_pair",
                    "physical_assignment": "proposal_dependent"
                  }
                },
                "source_refs": ["r1-standards-table"]
              }
            ]
          },
          "applicability": {
            "structure_type": "single_family_primary_structure",
            "lot_context": "all"
          },
          "conditions": [
            "The paired yards must not be reduced to one symmetric value."
          ],
          "exception_family_ids": [
            "setback-measurement-and-plan-lines",
            "narrow-pre-1955-parcel-side-setback",
            "setback-encroachments",
            "legal-nonconformities",
            "disaster-reconstruction"
          ],
          "validation_status": "verified_with_conditions",
          "conflict_id": null,
          "approved_for_ruleset": true
        }
      }
    }
  }
}
```

No member is labeled left or right because the verified source does not establish a universal physical assignment.

### Illustrative future adjustment shape

The following fragment demonstrates the distinction the schema should eventually be able to express. It is not Santa Clara data and is not currently supported for runtime evaluation:

```json
{
  "adjustment_id": "illustrative-height-stepback",
  "trigger": {
    "kind": "height_above",
    "height": {"number": 20, "unit": "ft"}
  },
  "effect": {
    "kind": "add_to_base",
    "value": {"kind": "distance", "number": 3, "unit": "ft"}
  },
  "source_refs": ["illustrative-source-only"]
}
```

Schema expressiveness alone does not move this capability to encoded, retrievable, or evaluated status.

## Authoring rules for humans and AI

An authoring workflow MUST:

1. Select an existing capability ID from the catalog or propose the capability there first.
2. Use the exact GIS zone designation as the containing key.
3. Create a separate rule record and rule ID for each zone.
4. Verify values, applicability, definitions, exceptions, and amendment status against authoritative sources.
5. Add or reuse shared source and citation records without copying their text into every zone.
6. Use typed requirement fields for every fact needed by deterministic retrieval or evaluation.
7. Preserve unresolved assertions and approved resolutions through conflict records.
8. Mark unsupported or unavailable evaluation paths as `not evaluated`; never translate them into permission or prohibition.
9. Run schema and domain validation.
10. Obtain the required approval before setting `approved_for_ruleset` to true.

AI may extract, normalize, propose IDs, and draft candidate records. It MUST NOT invent missing values, silently choose among conflicts, infer that equal values share one legal identity, or mark its own output approved.

## Invalid patterns

The v2 design should reject or prohibit these patterns:

- One rule with `zones: ["R1-6L", "R1-8L"]`
- A top-level rules array that must be scanned to discover a zone's standards
- A rule ID shared by multiple zones because their present values match
- A zone-specific numeric value stored only in shared reference data
- First- and second-story setbacks encoded as unrelated capabilities
- A second-story number with no indication whether it is a total minimum or an addition
- Paired side yards averaged into one number or assigned left/right without authority
- A height trigger that omits whether the threshold is inclusive
- Material numeric or applicability logic stored only in prose conditions
- Missing source references represented as guessed values
- Unsupported exceptions treated as inapplicable, prohibited, or zero-valued

## Deterministic validation expectations

The v2 schema and eventual domain validator must establish at least:

- Exact top-level structure and allowed fields
- Unique, convention-compliant rule IDs
- Direct correspondence between catalog capability IDs and regulation keys
- One zone-owned record per encoded capability and zone
- No multi-zone applicability fields inside zone records
- Valid typed values and units
- Valid setback base, trigger, effect, and paired-member combinations
- Explicit, complete precedence whenever a setback has multiple adjustments
- Existing shared references and conflict references
- Complete conflict assertions and consistency with the selected rule value
- Migration completeness against every approved v1 rule
- Repeatable zone and capability lookup fixtures

JSON Schema should enforce local structure. A domain validator must enforce identity uniqueness, cross-reference existence, conflict consistency, migration completeness, and other cross-record invariants.

## Approved design decisions

The project owner approved these decisions on July 16, 2026:

1. `zones` is an object keyed by exact GIS zone designation.
2. Each zone has a direct `regulations` map keyed by catalog capability ID.
3. Every zone owns an independent rule record and rule ID, even when values match.
4. Shared legal context is referenced by ID rather than copied into every zone.
5. A setback is one base requirement plus typed adjustments.
6. Story and height triggers are distinct and have explicit boundaries.
7. Total-minimum and additional-distance effects remain distinct.
8. Paired side yards preserve both values without unsupported physical assignment.
9. Multiple adjustments require an explicit highest-to-lowest precedence list.
10. The catalog, authoring guide, JSON Schema, source verification, and runtime engine retain separate responsibilities.

Approval of this guide authorized schema implementation, not automatic migration or runtime use. The approved v1 artifacts remain unchanged until the later migration and validation steps pass.
