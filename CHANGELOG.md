# Changelog

## v0.2 — Research Assets (2026-10)

- Add versioned `dataset`, `benchmark`, `legacy`, `paper`, and `report` Asset Registry.
- Add human metadata intake wizard, CLI field edits, `$EDITOR` and JSON-file edit workflows.
- Add draft/published lifecycle, human review labels, revision history and semantic freeze.
- Add versioned links between benchmarks and datasets and optional asset references from Claims.
- Add `store://` aliases with per-machine `.rk/stores.local.json` mapping excluded from Git.
- Add local single-file SHA-256 verification, without any automatic dataset download.
- Add three procedural Skills: dataset-curation, benchmark-governance and research-archive.
- Add large-payload `.gitignore` and official DVC/LFS integration guidance.
- Preserve existing v0.1 task, handoff, claim and memory formats.
- Add regression tests for Git Clone not carrying raw data, stale source files, invalid metadata, checksum mismatch, version immutability and human editor integration.

Known limitations: no remote downloader, no multi-file shard verifier, no built-in authorization, and no web UI.
