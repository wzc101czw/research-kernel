# Research Kernel v0.4 — Scientific Intent, Plan, Context, Execution, Verification

```
Researcher + Study + Frozen Protocol + published Asset versions
                           |
                           v
                  Typed Plan DAG (Git)
                           |
                   Static Preflight
                           |
     +---------------------+--------------------+
     |                     |                    |
 Node-local Context   Builtin Executor    Proof-of-completion
 explicit authority   typed operation     local output hash
     |                     |                    |
     +---------------------+--------------------+
                           |
                  .rk/ execution ledger
                           |
                    Reviewed Export
                           |
              Git small Run Manifest
                           |
                Scientific Evidence
                           |
                Human Scientific Review
```

This is a staged engineering interpretation of compositional research execution; it does **not** implement Free Monad or Grothendieck Topos machinery. The v0.4 builtin executor is not OS-isolated and only permits a few audited operations. See `docs/EXECUTION-v0.4.zh-CN.md` for precise runtime/trust boundaries.

---

# Research Kernel v0.2 Architecture

## Source of truth and roles

- Git: metadata, small research source files, Claims, Tasks, Handoffs, Skills and evaluations.
- External data: Raw datasets, large logs, generated weights and large copyrighted or private PDFs.
- Asset Registry (`rk_assets.py`): versioned metadata records and references. Never downloads or uploads data.
- Local store map (`.rk/stores.local.json`): per-machine mappings from `store://alias/...` to a mounted directory. Excluded from Git.

## Logical map

```text
AGENTS.md             Agent bootstrap rules (intentionally short)
workspace/            Tasks, handoffs, permissions and policies
knowledge/            Research claims and evidence
memory/               Candidate and reviewed memory
methods/skills/        Portable task methods with SKILL.md
assets/registry/       Immutable-versioned records for dataset/benchmark/legacy/paper/report
benchmarks/definitions/   Hash-checked scoring protocols
research/archive/     Historical research outcomes
research/publications/   Human-facing research output source
experiments/runs/     Run manifests (manual in v0.2)
rk.py                 Task / Memory / Claim CLI and general integrity checks
rk_assets.py          Asset CLI, metadata lifecycle and local payload SHA verification
```

## Metadata lifecycle

`new` => draft => `edit` / `set` / `link` => human `publish` => editorial corrections only.

To update Dataset payload, benchmarking rules, sources, license or expand access: `fork` a new version and re-review. A published asset's access may be tightened immediately with an audited `set` update. All mutation commands append a revision and reason. Published-asset freeze is an application-layer rule; Git branch protection/permissions are needed for stronger governance.

Example reference `dataset:my-corpus@v1`: stable identity separate from location. Example storage `store://lab/my-corpus-v1.tar.zst`: logical physical location mapped outside Git. `storage.sha256` is the declared payload digest; `asset verify` checks a local file explicitly.

## The context hierarchy

- L0: AGENTS.md, workspace policies.
- L1: human-written knowledge and asset indexes.
- L2: Task, Handoff and scoped compacted memory.
- L3: Exact Claims, published asset manifests, source files and experiments.
- L4: large datasets/archive payloads (external).

The CLI `context` uses a character budget, not a token budget. No Vector DB or semantic retrieval is included in v0.2.

## Limitations

- Local SHA verification is single-file; folder sharding and shard-level Merkle validation are future work.
- External URIs are metadata only; DVC/remote download is explicitly opt-in via separate tooling.
- JSON history is not cryptographically append-only; direct manual edits can bypass it. Use Git review and CI.
- Concurrent writers are checked by metadata revision, but the standalone CLI has no multi-host lock service.
- No authentication inside this CLI. Human approval labels are procedural, not identity proofs.
- Asset publish is not independent scientific validation or legal licensing clearance.

## v0.3 Scientific Method Layer

`rk_science.py` introduces typed Question, Hypothesis, Study, Protocol, Run, Observation, Analysis and Review records under `science/`, separate from operational Tasks and unverified Claims. A confirmatory Protocol cannot freeze without declared variables, controls, outcomes, analysis plan and stopping rule. Amendments preserve the old record. No scientific validation is inferred from a successful CLI command.

`rk_context.py` implements study-scoped, char-bounded progressive context packaging. Explicit reviewed Memory IDs are source-checked. The `.rk/context/` manifest records what was included/omitted and the source bytes used. The unextended `rk.py context --task` call remains backwards compatible.

`rk_intake.py` accepts a Unicode tree listing or reads live directory *names only* to generate a local untracked advisory triage report. It does not read secrets, move files, download data or infer run provenance from filenames.

New procedures are task-selected Agent Skills under `methods/skills/`, with canonical rules in `AGENTS.md` and `workspace/policies.md`.
