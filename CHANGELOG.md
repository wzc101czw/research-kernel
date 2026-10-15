# Changelog

## v0.3 — Scientific Kernel, Context Packs and Legacy Intake

- Retained v0.2 Asset Registry and existing Task, Claim, Memory and Handoff data model.
- Added eight scientific object kinds: Question, Hypothesis, Study, Protocol, Run, Observation, Analysis and Review.
- Added typed cross-references, source SHA validation, metadata revisions, confirmatory protocol completeness checks, freeze/amend semantics and review finalization without automatic claim promotion.
- Added explicit budgeted Context packets for a Study/Task, optional accepted-memory references and reproducible selection manifests under gitignored `.rk/`.
- Added read-only legacy tree/directory intake that classifies *candidate* paths and flags suspicious secret filenames without opening any original source file contents or migrating data.
- Added five procedural Agent Skills and updated `AGENTS.md`, `audit-claim` and `compact-memory`.
- Added Chinese operational docs, migration guide and regression tests.
- Deliberate limitations: no semantic verification, no LLM scheduler, no automatic memory acceptance, no true access-control system, no dataset payload downloads, no full RO-Crate exporter.

## v0.2

Added a versioned research Asset Registry, detached raw data locations and human metadata revision workflow.
