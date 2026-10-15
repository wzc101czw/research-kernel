# Research Asset Registry

The catalog lives in `assets/registry/{kind}/{slug}/{version}.json` and is managed by `python rk.py asset`.

- **dataset**: raw datasets; external storage URI and immutable payload hash.
- **benchmark**: globally or project-scoped evaluation protocol with a hashed definition file and version-pinned datasets.
- **legacy**: historical research artifacts and outcomes; originals must remain identifiable.
- **paper**: third-party scholarly literature with citation/DOI/rights metadata.
- **report**: human-facing research reports, publications and manuscripts.

A record starts `draft`; `publish` freezes storage, source hash references, ownership, access expansion, license and relations. Editorial corrections (title, summary, tags and citation) increase the metadata revision. Access can also be tightened immediately (public -> restricted -> confidential); relaxing restrictions requires a new version and review. **Dataset or benchmark semantics changing means a new asset version**, not an in-place edit.

Use `python rk.py asset list`, `asset show REF`, `asset edit REF --reason ...`, `asset check`, and `python rk.py doctor`.

Large files are never fetched by this registry. Keep location credentials outside Git. See `docs/DATA-STORAGE.zh-CN.md`.

Human intake: `python rk.py asset wizard` or `asset new`. For human revision, use `asset edit REF --reason ...` (EDITOR) or `asset edit REF --from-json FILE --reason ...`.
