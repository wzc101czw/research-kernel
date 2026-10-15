---
name: execute-research-plan
description: Prepare, statically check, freeze, execute and resume a typed Research Kernel execution DAG. Use when a scientific Study requires deterministic benchmark evaluation, local context packing, provenance-preserving steps, or controlled replay under a frozen Protocol.
---
# Execute Research Plan

1. Identify a valid Study and its **frozen** Protocol. If missing, use `study-design`; do not fabricate a scientific approval.
2. Create a draft Plan with `python rk.py plan create --study STUDY_ID --protocol PROTOCOL_ID --title "..." --left examples/fixtures/baseline.jsonl --right examples/fixtures/candidate.jsonl --field success`. Substitute real **small, permitted** evaluation summaries. Raw large data remain external. Other plan variants may be authored as JSON conforming to `docs/EXECUTION-v0.4.zh-CN.md`.
3. Inspect `plans/specs/PLAN_ID.json`: its need, invariant set, declared inputs, source hashes, operation allowlist, node contexts and validation. Confirm no secret, privileged tool, external network or unreviewed Benchmark alteration is requested.
4. Execute `python rk.py plan check PLAN_ID` and `python rk.py plan dry-run PLAN_ID` after a reviewer freezes it with `plan freeze PLAN_ID --reviewed-by "..."`. This is a review label, **not authenticated approval**.
5. For LLM-mediated reasoning adjacent to a Step, load only `python rk.py plan context PLAN_ID --step STEP_ID`. Do not load raw outputs or unrelated historical chats into the context. A valid local Context is not evidence of scientific correctness.
6. Run `python rk.py plan run PLAN_ID`; for interrupted or failed executions `python rk.py plan resume EXECUTION_ID`. Completed steps are reused only when local output hashes still match, and changed Plan/Protocol/context authority blocks replay.
7. Confirm Step outputs in `.rk/executions/` are **local/untracked**. Use `python rk.py plan export EXECUTION_ID --recorded-by "..."` only after inspection, to create a small, Git-trackable manifest.
8. To claim anything beyond arithmetic results, create formal scientific Run/Observation/Analysis and review using `experiment-evidence` and `scientific-review`. Never promote a metric difference into a verified Claim automatically.

The v0.4 built-in runtime is a restricted operation allowlist, **not a Docker sandbox or secret isolation boundary**. Do not give an untrusted Agent unrestricted host terminal access to sensitive environments.
