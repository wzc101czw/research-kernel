---
name: compact-memory
description: Extract durable decisions, failures, open questions and reusable observations from task journals and handoffs into reviewable memory proposals.
---
# Memory compaction

1. Read only relevant task records and handoffs. Identify provenance files that exist.
2. Extract atomic items of kind `decision`, `observation`, `failure` or `open_question`.
3. Preserve scope, conditions, negative results and uncertainty. Never turn a hypothesis into an established fact.
4. For each candidate, call `python rk.py memory propose --kind KIND --summary "..." --source PATH`.
5. Do not call `memory accept` autonomously. Present the proposed memory IDs for review.
6. After human review, run `python rk.py doctor`.

Do not repeatedly summarize old summaries if the underlying source is available.
