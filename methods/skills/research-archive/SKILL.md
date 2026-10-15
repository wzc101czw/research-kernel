---
name: research-archive
description: Preserve previous research outputs, source papers and human-facing reports with provenance, publication metadata and stable asset references. Use when migrating old notebooks, reports or literature into the Kernel.
---
# Research archive and publications

1. Identify whether an item is an old result (`legacy`), third-party scholarly work (`paper`), or a human-facing research output (`report`). Avoid rewriting original files during ingest.
2. Place small readable source Markdown/LaTeX/notes in `research/archive/` or `research/publications/`. Large PDFs and media may use an external store; preserve access rights and citation details.
3. Register as `python rk.py asset new KIND --slug SLUG --version v1 --title TITLE --owner OWNER --license LICENSE --source PATH` (or `--uri URI --sha256 HASH`).
4. Add DOI, publication venue, authors, uncertainty and original dates via the metadata editor (`citation` / `extra`). Use unknown placeholders only when verified details cannot be established.
5. Link archival work to source papers, evidence or datasets through `python rk.py asset link REF --relation cites|derived_from --to OTHER_REF --reason '...'`.
6. Present draft and source list to a human reviewer. Preserve original claims as historical claims, not updated consensus. A new interpretation requires its own analysis or Claim.
7. Publish only after review, commit metadata, and preserve a pointer to the original artifacts and their rights.

A publication/report is for human readers; evidence and Claims remain distinct records. The publication's PDF is not a replacement for source data.
