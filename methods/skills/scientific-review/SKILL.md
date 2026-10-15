---
name: scientific-review
description: Perform critical, evidence-grounded study/claim/protocol review and record human-readable approval conditions, rival explanations, uncertainty and reviewer decisions.
---
# Scientific review
1. Identify what object will be reviewed: a frozen Protocol, Hypothesis, Analysis, Observation, Run or existing Claim.
2. Inspect primary evidence, protocol date and revisions, confounders, data splits, statistical or logical assumptions, and validity of the benchmark construct.
3. Search for plausible competing explanations and falsifying observations. Do not treat agreement among language models as independent evidence.
4. Create `science new review --title "..." --link reviews TARGET_ID --summary "..."`. Link supporting small source documents when available.
5. Human reviewer may finalize with `science finalize REVIEW_ID --reviewer "..." --decision changes_requested --reason "..."` (accepted/changes_requested/rejected/inconclusive).
6. This review only records a judgment; CLI does not authenticate the reviewer or automatically mark a Claim as verified.
7. Follow up with human-directed evidence acquisition, independent replication or amended Protocol when appropriate.
