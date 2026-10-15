# Scientific Research Map

A durable research Study is an epistemic object, not just a Task.
Use `python rk.py science list` and `python rk.py science show ID`.

## Object graph
- Research Question (`rq-...`) defines what is being asked.
- Hypothesis (`hyp-...`) addresses a Question and may compete with other hypotheses.
- Study (`study-...`) addresses Questions; its `mode` is empirical/theoretical/systems/simulation/exploratory.
- Protocol (`protocol-...`) is for a Study, may test Hypotheses, and has exploratory/confirmatory phase.
- Run (`run-...`) follows a *frozen* Protocol (execution evidence needs separate files).
- Observation (`obs-...`) is produced by a Run (measurement, not interpretation).
- Analysis (`analysis-...`) uses Observations (interpretation, not a verified Claim).
- Review (`review-...`) reviews a scientific object or existing `claim-...`.

## Core invariants
- **Confirmatory Protocol**: draft until design has variables, controls, outcomes, analysis_plan and stopping_rule. Freeze before formal execution. Any material change means a new amendment ID, not an edit to the frozen record.
- **Retrospective historical reconstruction**: do NOT backdate or claim preregistration. Mark the design as retrospective in summary/metadata.
- **Evidence Sealing**: Run, Observation and Analysis can be sealed only when source-linked; upstream evidence must also be sealed. This protects CLI-level immutability, not scientific truth.
- **Scientific Review**: record a decision and reviewer ID, but CLI does not authenticate or independently prove the reviewer.
- **No leap from Observation to truth**: analysis, independent replication and human judgment remain separate.
- Sources are small tracked files with SHA-256; larger raw data use versioned Asset Registry references.

## Human research and Agent Skills
- `methods/skills/study-design/SKILL.md` — study planning, hypotheses, frozen protocols.
- `methods/skills/experiment-evidence/SKILL.md` — run, observation, analysis and caveats.
- `methods/skills/scientific-review/SKILL.md` — check claims and protocols without fabricated verification.
- `methods/skills/legacy-workspace-intake/SKILL.md` — safely propose migration from legacy folders.
- `methods/skills/context-recovery/SKILL.md` — task/study scoped context packet.
- `methods/skills/compact-memory/SKILL.md` — source-linked memory proposals.

## Navigation
See `docs/SCIENTIFIC-WORKFLOW.zh-CN.md` for commands, scientific responsibilities and limitations.
