---
name: audit-research-execution
description: Inspect a Research Kernel typed Plan, its frozen Protocol and execution artifact hashes, detect mismatched assumptions or stale Context authority, and distinguish computation integrity from scientific validity. Use before comparing benchmark runs or trusting exported execution results.
---
# Audit Research Execution

1. Identify Plan and Execution IDs. Read the **tracked** `plans/specs/PLAN_ID.json` and `plans/locks/PLAN_ID.json`; treat them as statements and hashes, not authenticated approvals.
2. Run `python rk.py plan check PLAN_ID`, `python rk.py plan dry-run PLAN_ID` and `python rk.py plan status EXECUTION_ID`. A changed Plan, changed frozen Protocol, changed Agent policy or modified executor invalidates reproducible replay; inspect instead of bypassing the check.
3. Inspect `.rk/executions/PLAN_ID/EXECUTION_ID/steps/*.json` only in trusted working environments. Check recorded input digests, per-step context hashes, operation type, resource/environment summary and completeness; never copy secrets, raw private data or long transcripts into Memory.
4. If both scientific Runs exist, apply `python rk.py compose check RUN_A RUN_B --contract science/contracts/benchmark-comparison.v1.json`. Metadata equality does not prove dataset equivalence, statistical significance or absence of confounding.
5. Inspect missing negative cases, data split, scorer, sample size, stopping conditions, exclusions, seed/model/environment nondeterminism. Escalate to `scientific-review` if a claim is requested.
6. Do not rewrite a frozen Plan or historical output. Create a new Plan/Protocol amendment for changed conditions and preserve disagreements.
7. Record audit findings with linked source hashes and explicit limitations. An exported small manifest proves what was recorded, not that the measurements are genuine or the scientific inference is warranted.
