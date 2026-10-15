---
name: session-handoff
description: Capture the minimum evidence-grounded task state and handoff to another agent or session when ending, pausing or switching platforms.
---
# Session handoff

1. Find the active task ID in `workspace/tasks/`.
2. Update status, next action and progress using `python rk.py task set`.
3. Explicitly list unresolved questions, reproducibility instructions and evidence locations.
4. Run `python rk.py handoff TASK_ID --note "..."`.
5. Run `python rk.py doctor`.
6. Tell the next agent to read `AGENTS.md`, the task record, the latest handoff and original evidence.

Never claim that a handoff transfers hidden model state or chat history.
