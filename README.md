# Research Kernel v0.4 — Typed Scientific Research Execution

A Git-native, local-first, dependency-free scientific workspace with a typed, fail-closed execution DAG, node-local Context, immutable Plan locks, resumable local runs, source-linked records, and human-controlled research review.

## Quick start

Requirements: Python >= 3.10 and Git (optional for initial CLI tests). No LLM API, Vector DB, or background worker required.

```bash
python rk.py init
python rk.py doctor
python -m unittest discover -s tests -v
python rk.py science list
python rk.py asset list
```

## v0.4 executable Research Plan

```bash
# Create/Freeze Study + Protocol first (see Key commands below).
python rk.py plan create --title "Controlled toy comparison" \
  --study STUDY_ID --protocol PROTOCOL_ID \
  --left examples/fixtures/baseline.jsonl \
  --right examples/fixtures/candidate.jsonl --field success
python rk.py plan check PLAN_ID
python rk.py plan freeze PLAN_ID --reviewed-by "Researcher"
python rk.py plan dry-run PLAN_ID
python rk.py plan context PLAN_ID --step baseline
python rk.py plan run PLAN_ID --max-steps 1
python rk.py plan resume EXEC_ID
python rk.py plan export EXEC_ID --recorded-by "Researcher"
```

This is a tiny **synthetic fixture** workflow: computation success is not scientific support. The builtin executor has no arbitrary Shell, LLM API, data fetch or subprocess operation. It is **not** a container/OS sandbox. `.rk/` execution logs stay local; explicitly exported small manifests go to Git. Read [v0.4 Chinese execution guide](docs/EXECUTION-v0.4.zh-CN.md).

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

## Experimental composition checks (v0.3.1)

Run metadata compatibility only (does not establish scientific validity):

```bash
python rk.py compose check RUN_A RUN_B \
  --contract science/contracts/benchmark-comparison.v1.json
python rk.py context --study STUDY_ID --protocol FROZEN_PROTOCOL_ID \
  --profile audit --max-chars 14000
```

Returns 0 = compatible on declared fields, 2 = incompatible, 3 = insufficient evidence.
For science decisions, pin the required frozen Protocol rather than relying on
optional Context sections. See [composition contract guide](docs/COMPOSITION-CONTRACTS.zh-CN.md).

## Documentation

- [Execution and local Context (v0.4)](docs/EXECUTION-v0.4.zh-CN.md) — typed Plan, preflight, run, resume, Git export, trust limits
- [Scientific workflow](docs/SCIENTIFIC-WORKFLOW.zh-CN.md) — Question, Hypothesis, Study, Protocol, Run, Observation, Analysis, Review
- [Context Engineering](docs/CONTEXT-ENGINEERING.zh-CN.md) — layered progressive loading, explicit memory, context manifest
- [Legacy directory intake](docs/LEGACY-INTAKE.zh-CN.md) — read-only triage of messy research workspaces
- [Large data and metadata storage](docs/DATA-STORAGE.zh-CN.md) — asset registry, external raw payload, published versions
- [Upgrade v0.2 → v0.3](docs/UPGRADE-v0.2-to-v0.3.zh-CN.md)
- [English architecture overview](ARCHITECTURE.md)

## Trust boundaries

The provided example tree is a text listing, not original data or a Git history. `intake` reads names only and never relocates files. It cannot know actual file sizes, true source SHA, result correctness or whether suspicious paths contain active secrets. Metadata, summaries and model responses are never accepted as proof merely because they are stored in the Kernel.

Use `methods/skills/` for progressive procedural guidance; the actual validation is enforced in the Python CLI where possible. Always protect secrets, restricted research data and native Git history separately.
