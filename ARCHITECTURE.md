# Research Kernel v0.1

The repository is the authority. Agents are replaceable clients. `rk.py` is a deterministic, local CLI.

## Write paths
- Task: `workspace/tasks/task-*.json`
- Handoff: `workspace/handoffs/handoff-*.md`
- Claim: `knowledge/claims/claim-*.json`
- Candidate memory: `memory/inbox/memory-*.json`
- Accepted memory: `memory/compacted/memory-*.json`

## Trust levels
Raw evidence > direct reproducible tests > reviewed claims > analyses > compacted memories > retrieved snippets.
This is a working heuristic, not a universal scientific hierarchy. Evidence quality always matters.

## L0-L4 information loading
- L0: `AGENTS.md`, `workspace/policies.md`
- L1: `knowledge/INDEX.md`, `memory/INDEX.md`
- L2: task JSON, current handoff and relevant compacted memories
- L3: exact source files, claims and run records
- L4: full archives / external datasets (not necessarily in Git)

`python rk.py context` is a char-bounded bootstrap packer, **not** semantic retrieval and **not** a token counter.

## Roadmap
v0.2: experiment run manifests, source/versioned provenance, optional `rg`/SQLite FTS5.
v0.3: model-independent Skills evaluation, content-addressed cache invalidation, hybrid retrieval.
v0.4: optional MCP adapter and durable agent runtime.
