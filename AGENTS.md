# AGENTS.md

These instructions apply to the entire `SantaClaraZoningPortal` workspace unless a more specific nested `AGENTS.md` says otherwise.

## Objective

Expand the released Santa Clara R1 prototype into **Santa Clara Zoning Explorer**, a selected residential zoning product, in small, deterministic, evidence-backed blocks. The active scope and architecture live in `docs/residential-expansion-plan.md`; do not reproduce them here. `docs/r1-prototype-plan.md` remains the historical design reference for the released baseline.

Do not describe product output as a complete entitlement analysis or legal/planning determination.

## Document ownership

Each project document has one job:

- `README.md` is the human-facing setup and runbook. Put dependencies, runnable commands, and repository orientation there.
- `AGENTS.md` contains durable Codex operating instructions. Do not put changing milestone status or duplicate run commands here.
- `docs/progress.md` is the sole active status ledger. Put the current stage, completed blocks, validation evidence, canonical artifacts, next block, blockers, and implementation decision log there.
- `docs/progress-archive/` preserves closed phase ledgers. Treat archived ledgers as historical evidence; never resume active status tracking in them or silently rewrite their technical record.
- `docs/future-improvements.md` is the cross-cutting improvement burndown. Record useful deferred enhancements there; when one becomes active, put execution status in `docs/progress.md` and detailed design in the relevant owning artifact.
- `docs/residential-expansion-plan.md` is the active phase design reference. Put the approved expansion scope, architecture, source boundaries, migration strategy, blocks, and completion criteria there.
- `docs/r1-prototype-plan.md` is the historical design reference for the released R1 vertical slice. Do not retrofit the expansion design into it.
- `docs/prototype-report.md` is the completed plain-language report for the R1 release. Preserve it as historical product context.
- `docs/regulations/supported-regulations.md` is the regulatory capability catalog. Put supported regulation families, their meanings, implementation boundaries, and the deferred capability queue there; do not duplicate zone-specific values or schema field designs.
- `docs/regulations/ruleset-authoring-guide.md` is the preserved human- and AI-facing representation contract for the released R1 ruleset v2 lineage. Change it only when the v2 contract itself changes.
- `docs/regulations/residential-ruleset-authoring-guide.md` is the active human- and AI-facing representation contract for residential ruleset v3. Put the v3 hierarchy, identity conventions, typed regulation semantics, authoring requirements, and representative examples there.
- `contracts/residential-result-contract-2.0.0.schema.json` is the machine-enforced residential pipeline result contract. Put controlled status payload shapes and selection/result cardinality there; keep runtime implementation status in `docs/progress.md`.
- `docs/title18-amendment-audit.md` is the checksum-pinned historical amendment audit used by the approved R1 rulesets. Preserve it byte-for-byte unless intentionally creating a new R1 ruleset version and migration.
- `docs/residential-title18-amendment-audit.md` owns the current expansion cutoff, later-legislation effects, and recheck triggers.
- `docs/residential-density-title18-amendment-audit.md` is the checksum-pinned density-capability audit supplement for residential candidate `2026-07-19.3`; preserve it when creating later successors.
- `docs/r1-rule-verification.md` is the historical source trace and approval gate for the released machine-readable R1 rules. Preserve it except when correcting or re-verifying its own R1 conclusions.
- `docs/residential-rule-verification.md` is the active source trace and approval gate for new-zone use permissions, structure applicability, definitions, exceptions, conflicts, and rule dispositions.
- `docs/residential-density-rule-verification.md` is the checksum-pinned source trace and project-decision record for the gross residential density capability added after candidate `2026-07-19.2`.
- `docs/patrick-henry-rule-verification-supplement.md` is the checksum-pinned final source reconciliation and PH-R5 density decision record for the Patrick Henry successor to candidate `2026-07-19.3`.
- Each raw snapshot's `manifest.json` is the authoritative record of that download's sources, filters, counts, files, and checksums.

When something changes, update only its owning document unless the change genuinely affects another document's role. In particular, a milestone change normally updates `docs/progress.md` only.

## Starting a task

1. Read `docs/progress.md` to learn the current stage and next block.
2. Read the relevant portions of `docs/residential-expansion-plan.md` before making design or scope decisions.
3. Read `docs/residential-rule-verification.md` before approving, authoring, or implementing a new residential-zone rule or disposition.
4. Read `docs/residential-title18-amendment-audit.md` before making a current-law or later-legislation conclusion for the expansion.
5. Read the density-specific verification and audit supplements before changing gross residential density data or its conflict resolutions.
6. Read the Patrick Henry verification supplement before authoring, approving, or changing Patrick Henry rule data or its PH-R5 conflict resolution.
7. Read the relevant portions of `docs/r1-prototype-plan.md` when changing, migrating, or testing a contract inherited from the R1 baseline.
8. Read `docs/regulations/supported-regulations.md` before adding or changing a regulatory capability.
9. Read `docs/regulations/ruleset-authoring-guide.md` before changing or migrating the released R1/v2 contract.
10. Read `docs/regulations/residential-ruleset-authoring-guide.md` before changing residential ruleset v3 schemas, authoring v3 rule data, or building v3 extraction workflows.
11. Read `contracts/residential-result-contract-2.0.0.schema.json` before changing expansion pipeline or presentation result shapes.
12. Read `README.md` when running, changing, or documenting repository commands or dependencies.
13. Read `docs/future-improvements.md` before promoting a deferred enhancement or recording a newly discovered cross-cutting improvement.
14. Read the relevant `manifest.json` before using or transforming a GIS snapshot.
15. Use `GOOGLE_DRIVE_SOURCE.txt` when project source documents in Google Drive are needed.

## Preserve authoritative inputs

- Treat `data/raw/<date>/` as immutable source snapshots.
- Never silently overwrite or modify an existing raw snapshot.
- Put a new retrieval in a new dated directory.
- Preserve source metadata, query filters, object IDs, record counts, raw responses, and checksums.
- Do not silently accept ArcGIS record truncation; validate downloaded IDs and counts.
- Keep GET query batches at 100 features or fewer unless a tested alternative removes the URL-length constraint.

## Keep conclusions deterministic

- Do not use an LLM to generate numeric zoning standards at runtime.
- Treat AI-assisted extraction as candidate data until checked against authoritative text.
- Verify consequential rules before marking them approved.
- Preserve source citations, effective dates, ruleset versions, assumptions, and validation status.
- The same versioned inputs and engine version should produce the same result.

## Reuse common semantics without erasing local rules

- Reuse a shared capability only when the local provision is an exact semantic fit; keep jurisdiction values, terminology, citations, conditions, exceptions, conflicts, and precedence in jurisdiction-owned data.
- Do not force a unique local rule into a nearby shared field. Preserve it as a candidate controlled jurisdiction extension until its identity, typed representation, validation, deterministic behavior, and presentation path are approved.
- Never silently drop or guess an unknown capability or requirement shape. Reject it or return an explicit unsupported or `not evaluated` outcome.
- Promote a recurring local pattern into the shared core only through deliberate catalog, authoring-contract, schema, migration, validator, and test changes.
- Treat AI-proposed capability mappings and extensions as candidates until source verification and human approval are complete.

## Preserve and resolve regulatory conflicts

- Never erase or silently normalize conflicting source values. Record each assertion, its location, and its source version.
- Apply a deterministic resolution only when an explicit authority, precedence rule, effective date, or approved project policy supports it.
- Record the selected value separately from the conflicting source values, together with the resolution rationale, reviewer or decision source, date, and status.
- Return `review required` when the conflict cannot be resolved by an approved rule. A local project resolution is not an official correction by the issuing government.

## Code quality and documentation

- Prefer clear names, cohesive functions, explicit types or schemas, and straightforward control flow so the code explains itself.
- Document modules, public interfaces, data contracts, important assumptions, provenance requirements, and non-obvious edge cases.
- Use comments to explain **why**, constraints, or invariants; do not narrate obvious syntax or repeat what the code already states.
- Keep docstrings and comments concise and information-dense. Do not comment every function, branch, or line by default.
- Update nearby documentation whenever behavior or assumptions change, and remove stale comments promptly.

## Respect scope and uncertainty

- Follow the included and deferred scope in `docs/residential-expansion-plan.md`. Use `docs/r1-prototype-plan.md` only for inherited R1 behavior and historical acceptance boundaries.
- Treat unsupported zones and deferred topics explicitly; do not silently infer applicability.
- Label unevaluated subjects `not evaluated` rather than implying they are prohibited or irrelevant.
- Do not treat the July 2025 consolidated PDF as a complete current-law snapshot without auditing later Title 18 amendments.

## Keep progress reliable

- Update `docs/progress.md` when a block starts, completes, changes direction, or becomes blocked.
- Record artifacts, source versions, commands needed for reproduction, and validation evidence for completed work.
- Record material implementation choices in its decision log.
- Do not mark a block complete merely because files exist; its validation criteria must pass.
- Update `README.md` only if setup, dependencies, runnable commands, or repository orientation changed.
- Update the residential expansion plan only if active-phase design, scope, source boundaries, migration strategy, or completion criteria changed. Preserve the R1 prototype plan unless correcting its own historical record.
- Update the supported-regulations catalog when a capability is added, removed, renamed, or its supported behavior changes.
- Update the authoring guide that owns the affected schema lineage when a capability's JSON mapping, identity convention, typed semantics, or maintenance workflow changes; every cataloged capability must have a documented standalone or embedded representation before rule data is authored.
- Update the future-improvements backlog when a cross-cutting enhancement is discovered, promoted, completed, dropped, or superseded; do not use it as a second active-status ledger.

## Protect the workspace

- Existing files and changes belong to the user unless clearly created for this project.
- `blender-mcp-test/` is unrelated experimental work; do not modify or delete it during zoning tasks.
- Avoid destructive Git and filesystem commands.
