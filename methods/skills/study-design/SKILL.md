---
name: study-design
description: Plan and register a research question, competing hypotheses, and a rigorous exploratory or confirmatory study protocol. Use before experiment design or when reconstructing an older research study.
---
# Study design
1. Clarify the research question, competing explanations, prior work, scope and meaningful outcome.
2. Use `python rk.py science new question --title "..." --summary "..."` and note the returned RQ ID.
3. Create alternatives with `science new hypothesis --title "..." --link addresses RQ_ID`; use `science link HYP2 --relation competes_with --to HYP1 --reason "..."` when appropriate.
4. Create `science new study --title "..." --mode empirical --link addresses RQ_ID` (change mode as needed).
5. Create `science new protocol --title "..." --phase confirmatory --link for_study STUDY_ID --link tests HYP_ID`.
6. For confirmatory designs, populate `design.variables`, `design.controls`, `design.outcomes`, `design.analysis_plan`, `design.stopping_rule` with `science set PROTOCOL_ID --key design.NAME --value "..." --reason "..."`.
7. Have the human review the actual design **before** execution. Then `science freeze PROTOCOL_ID --reviewed-by "Researcher"` (not an authentication mechanism).
8. If prior results exist, label the reconstruction retrospective: do not claim preregistration.
9. Run `python rk.py doctor`. Keep protocol revisions via `science amend FROZEN_ID --reason "..."`.
