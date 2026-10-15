# Durable Memory

- `memory/inbox/`: candidate memories; not yet approved.
- `memory/compacted/`: reviewed compacted memories.
- `workspace/handoffs/`: ephemeral task continuation notes.

Read durable memories only when relevant to the current task. Verify substantive statements against their source hashes and raw evidence.

To compact: use the `compact-memory` Skill to extract only decisions, failures, open questions or durable observations; call `python rk.py memory propose ...`; review; then `python rk.py memory accept MEMORY_ID`.
