---
name: legacy-workspace-intake
description: Inspect an unstructured research directory tree without copying, moving, reading or deleting data; propose safe scientific object and asset classification with security review.
---
# Legacy workspace intake
1. Identify whether input is a `tree` text listing or a local directory. If a text tree, inspect *paths only* with `python rk.py intake tree EXAMPLE.txt`; if a real directory, use `intake directory PATH` (no source bytes read).
2. Inspect `.rk/intake/latest/PLAN.md` and `inventory.json`; these remain untracked. Do not auto-move data, auto-classify content as verified, or infer real experiment links from filenames.
3. Escalate filenames resembling credentials first; check Git history locally. If secrets were committed, rotate them and follow approved history-cleanup procedure.
4. Map candidate Dataset/Benchmark versions to Asset Registry, trials and predictions to Run records, drafts to reports/analyses, and notes to unapproved memory proposals.
5. Preserve historical paths and relationships. Require human confirmation before rename/migration.
6. For historical research, mark proposed Protocol as retrospective; never invent when evidence was produced.
7. Run `python rk.py doctor` after approved metadata changes and save decisions in a versioned note.
