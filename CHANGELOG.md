# Changelog

## v0.4.0 — Typed Research Execution

- Adds `rk_execution.py`: Plan/Step DAG registry, strict schema and operation allowlist, Study/Protocol integration and input SHA-256 pinning.
- Adds reviewer-labeled, Git-trackable frozen Plan locks with Plan, Protocol, Study, policy, extra context and executor SHA-256 hashes.
- Adds `plan dry-run` and `plan context` with mandatory per-step budgeted Context (no raw data in LLM prompt).
- Adds builtin deterministic `jsonl_rate`, `compare_rates`, `sha256_file`, `validate_json`; no arbitrary host commands or network fetch.
- Adds local execution ledger, pause/resume with output integrity checks and explicit versioned Git export.
- Adds synthetic benchmark fixtures and new Agent Skills, docs, and regression tests.
- Retains v0.3.1 scientific objects, contracts, assets, source-linked memory and legacy intake without data migration.



## v0.3.1 — Compositional Research Pilot

- Added advisory, read-only `compose check` for sealed Run metadata.
- Explicit contract dimensions and tri-state results with limitations.
- Added opt-in, fail-closed frozen Protocol pinning for scientific Context packets.
- Kept all v0.3 object schemas and existing files unchanged.



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
