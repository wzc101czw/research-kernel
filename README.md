# Research Kernel v0.3 — Scientific Workspace

A local-first, Git-native, dependency-free research record system with versioned scientific objects, source-linked memory, Context packets and safe legacy intake.

## Quick start

Requirements: Python >= 3.10 and Git (optional for initial CLI tests). No LLM API, Vector DB, or background worker required.

```bash
python rk.py init
python rk.py doctor
python -m unittest discover -s tests -v
python rk.py science list
python rk.py asset list
```

## Key commands

```bash
python rk.py science new question --title "Does context strategy improve reliability?"
python rk.py science new study --title "Study A" --mode empirical --link addresses RQ_ID
python rk.py science new protocol --title "Evaluation protocol" --phase exploratory --link for_study STUDY_ID
python rk.py science freeze PROTOCOL_ID --reviewed-by "Human researcher"
python rk.py context --study STUDY_ID --profile research --max-chars 12000 --manifest-out .rk/context/selection.json
python rk.py intake tree /path/to/legacy-tree.txt
python rk.py doctor
```

`science freeze` records a textual reviewer identifier but does not authenticate it. Do not equate this with formal scientific approval. A final Review also does not automatically verify any Claim.

## Documentation

- [Scientific workflow](docs/SCIENTIFIC-WORKFLOW.zh-CN.md) — Question, Hypothesis, Study, Protocol, Run, Observation, Analysis, Review
- [Context Engineering](docs/CONTEXT-ENGINEERING.zh-CN.md) — layered progressive loading, explicit memory, context manifest
- [Legacy directory intake](docs/LEGACY-INTAKE.zh-CN.md) — read-only triage of messy research workspaces
- [Large data and metadata storage](docs/DATA-STORAGE.zh-CN.md) — asset registry, external raw payload, published versions
- [Upgrade v0.2 → v0.3](docs/UPGRADE-v0.2-to-v0.3.zh-CN.md)
- [English architecture overview](ARCHITECTURE.md)

## Trust boundaries

The provided example tree is a text listing, not original data or a Git history. `intake` reads names only and never relocates files. It cannot know actual file sizes, true source SHA, result correctness or whether suspicious paths contain active secrets. Metadata, summaries and model responses are never accepted as proof merely because they are stored in the Kernel.

Use `methods/skills/` for progressive procedural guidance; the actual validation is enforced in the Python CLI where possible. Always protect secrets, restricted research data and native Git history separately.
