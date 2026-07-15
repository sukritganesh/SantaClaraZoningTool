# AGENTS.md

These instructions apply to the entire `SantaClaraZoningPortal` workspace unless a more specific nested `AGENTS.md` says otherwise.

## Objective

Build the Santa Clara R1 zoning prototype in small, deterministic, evidence-backed blocks. The detailed scope and architecture live in `docs/r1-prototype-plan.md`; do not reproduce them here.

Do not describe prototype output as a complete entitlement analysis or legal/planning determination.

## Document ownership

Each project document has one job:

- `README.md` is the human-facing setup and runbook. Put dependencies, runnable commands, and repository orientation there.
- `AGENTS.md` contains durable Codex operating instructions. Do not put changing milestone status or duplicate run commands here.
- `docs/progress.md` is the sole status ledger. Put the current stage, completed blocks, validation evidence, canonical artifacts, next block, blockers, and implementation decision log there.
- `docs/r1-prototype-plan.md` is the design reference. Put scope, architecture, authoritative-source research, schemas, rules, and completion criteria there.
- Each raw snapshot's `manifest.json` is the authoritative record of that download's sources, filters, counts, files, and checksums.

When something changes, update only its owning document unless the change genuinely affects another document's role. In particular, a milestone change normally updates `docs/progress.md` only.

## Starting a task

1. Read `docs/progress.md` to learn the current stage and next block.
2. Read the relevant portions of `docs/r1-prototype-plan.md` before making design or scope decisions.
3. Read `README.md` when running, changing, or documenting repository commands or dependencies.
4. Read the relevant `manifest.json` before using or transforming a GIS snapshot.
5. Use `GOOGLE_DRIVE_SOURCE.txt` when project source documents in Google Drive are needed.

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

## Code quality and documentation

- Prefer clear names, cohesive functions, explicit types or schemas, and straightforward control flow so the code explains itself.
- Document modules, public interfaces, data contracts, important assumptions, provenance requirements, and non-obvious edge cases.
- Use comments to explain **why**, constraints, or invariants; do not narrate obvious syntax or repeat what the code already states.
- Keep docstrings and comments concise and information-dense. Do not comment every function, branch, or line by default.
- Update nearby documentation whenever behavior or assumptions change, and remove stale comments promptly.

## Respect scope and uncertainty

- Follow the included and deferred scope in `docs/r1-prototype-plan.md`.
- Treat unsupported zones and deferred topics explicitly; do not silently infer applicability.
- Label unevaluated subjects `not evaluated` rather than implying they are prohibited or irrelevant.
- Do not treat the July 2025 consolidated PDF as a complete current-law snapshot without auditing later Title 18 amendments.

## Keep progress reliable

- Update `docs/progress.md` when a block starts, completes, changes direction, or becomes blocked.
- Record artifacts, source versions, commands needed for reproduction, and validation evidence for completed work.
- Record material implementation choices in its decision log.
- Do not mark a block complete merely because files exist; its validation criteria must pass.
- Update `README.md` only if setup, dependencies, runnable commands, or repository orientation changed.
- Update the prototype plan only if design, scope, source research, or completion criteria changed.

## Protect the workspace

- Existing files and changes belong to the user unless clearly created for this project.
- `blender-mcp-test/` is unrelated experimental work; do not modify or delete it during zoning tasks.
- Avoid destructive Git and filesystem commands.
