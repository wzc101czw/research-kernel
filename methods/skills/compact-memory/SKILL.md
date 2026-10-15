---
name: compact-memory
description: Propose traceable durable memory for long-running research sessions and cross-agent handoff, preserving original evidence, uncertainty, failures and study/protocol identifiers.
---
# Compact research memory

1. Read the specific Task JSON and its latest Handoff, then optionally use `python rk.py context --study STUDY_ID --profile handoff --max-chars 12000`.
2. Identify small atomic items worth retaining: decisions, failures, open questions or observations. Keep bounded conditions, scientific status and negative results.
3. Before summarizing, verify associated raw evidence and whether its claim is provisional, disputed, replicated or unreviewed. An LLM's previous summary is not proof.
4. Generate candidate proposals using `python rk.py memory propose --kind KIND --summary "..." --source TRACKED_FILE` where TRACKED_FILE is a real small, allowed source. If the only source is a large external artifact, first create a small manifest with its stable versioned asset reference; do not invent a source.
5. Keep candidate IDs in `memory/inbox/` for human review. **Never** autonomously call `memory accept`.
6. Test recoverability with `python rk.py context --study STUDY_ID --memory MEMORY_ID --profile research --max-chars 12000` only after the proposal has been accepted.
7. Run `python rk.py doctor`; stale memories must not be silently refreshed.

Do not repeatedly summarize summaries when the original evidence is available. Do not store secrets or full private transcripts.
