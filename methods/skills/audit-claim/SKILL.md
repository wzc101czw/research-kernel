---
name: audit-claim
description: Recheck an existing scientific Claim against original evidence, assumptions, experimental controls, protocol versions and contradictory observations, without fabricating validation.
---
# Audit a research Claim

1. Inspect the Claim and original sources; run `python rk.py doctor` to check source SHA drift.
2. Find any linked Study and Protocol. A retrospectively inferred protocol is not preregistered.
3. Separate raw Observation, Analysis, hypothesis and Claim. Check data splits, metric validity, selection bias, confounding variables, replication and scope.
4. Use `python rk.py claim challenge CLAIM_ID --reason "..."` when evidence is contradicted or insufficient.
5. For formal independent review, create `python rk.py science new review --title "..." --link reviews CLAIM_ID` and record rationale/source evidence.
6. A reviewer may finalize with `science finalize` but it **does not** change the Claim's scientific validity or `verified` status automatically.
7. Preserve negative results and propose new experiments without rewriting original logs.
