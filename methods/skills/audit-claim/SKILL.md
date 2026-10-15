---
name: audit-claim
description: Challenge research conclusions against primary evidence, source hashes, assumptions, counterexamples and reproducible tests when asked to reevaluate prior findings.
---
# Claim audit

1. Read the target Claim JSON and each source file. Check source digests with `python rk.py doctor`.
2. Separate raw observation, inferential interpretation and assumptions.
3. Search for invalid baseline, confounders, missing replications or contradictory evidence.
4. If challenged, run `python rk.py claim challenge CLAIM_ID --reason "..."`.
5. Propose an independent experiment and save its config and results in `experiments/runs/`.
6. Do not silently edit old evidence or mark the conclusion verified. Record a review decision separately.

This skill supplies a review procedure, not automatic scientific truth.
