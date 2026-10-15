# Knowledge Map

## Topics
- Add each research topic here with its canonical location, e.g. `knowledge/analyses/` or `src/`.

## Claims
- Structured, source-linked claims live in `knowledge/claims/`.
- A claim's source hash can become stale; run `python rk.py doctor`.

## Evidence
- Small, shareable evidence can live in `knowledge/evidence/`.
- Keep immutable raw results or external artifact manifests for large experiments.

## Navigation conventions
Use descriptive filenames. Link to source code, paper sections and experiment run IDs rather than duplicating full content.

## External and global scientific assets
- See `assets/INDEX.md` for papers, reports, historical results, datasets and global benchmark metadata.
- Pin the exact `kind:slug@version` reference in Claims/Run manifests.
- Never treat Dataset location as its stable identity or an old report as independent evidence.
