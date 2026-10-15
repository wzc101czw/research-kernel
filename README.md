# Research Kernel Starter (v0.1)

[中文上手指南](QUICKSTART.zh-CN.md)

A Git-native, local-first kernel for agent-assisted research. Python standard library only.

## Quick start

```bash
python rk.py init
python rk.py doctor
python -m unittest discover -s tests -v
git init
git add .
git commit -m "Initialize Research Kernel"
```

`uv` is optional for this starter. If you use uv for your experiments, add a `pyproject.toml` and commit the generated `uv.lock`.

## Your first end-to-end workflow

1. Create a task:

```bash
python rk.py task new --title "Reproduce a result" --next "Read the methods section"
```

2. Record real progress (replace TASK_ID with the output):

```bash
python rk.py task set TASK_ID --status active --next "Run baseline" --note "Recorded the setup"
```

3. Prepare a source file (example):

```bash
echo "Baseline observations; not yet verified" > knowledge/evidence/baseline.txt
python rk.py claim new --statement "Candidate speedup in setting X" --source knowledge/evidence/baseline.txt --scope "Hardware A, dataset X"
```

4. Generate handoff and bootstrap context:

```bash
python rk.py handoff TASK_ID --note "Repeat experiment with another agent"
python rk.py context --task TASK_ID --max-chars 12000
```

5. Propose a memory linked to an existing evidence file:

```bash
python rk.py memory propose --kind open_question --summary "Need to repeat the benchmark" --source knowledge/evidence/baseline.txt
python rk.py memory accept MEMORY_ID
```

The last command requires an explicit interactive `ACCEPT`. This is a lightweight review gate, not an authentication mechanism.

6. Validate and commit:

```bash
python rk.py doctor
git add .
git commit -m "Record research progress"
```

## Cross-agent use

- Codex and Cursor may use root `AGENTS.md` when the project is opened as a repository.
- Claude Code loads `CLAUDE.md`, which directs it to `AGENTS.md`.
- Gemini CLI loads `GEMINI.md`, including the `@./AGENTS.md` import.
- For an API agent or web-only model without filesystem access, pass a bootstrap packet made by `python rk.py context` plus the necessary evidence explicitly. A Git remote alone does not grant a model filesystem access.

These adapters require actual client capability and permission configuration. They are not guaranteed to be behaviorally equivalent.

## Important limitations

- No automatic LLM memory summarization yet: `memory propose` is the review/write interface; Skill instructions guide the model.
- No formal claim verification command: claims start `provisional`, and `challenge` changes the state to `disputed`. Promotion should follow a recorded experiment and human review (future version).
- Source hashes detect **current-file drift** but do not preserve the old bytes. Commit source evidence or store immutable artifacts separately.
- `context --max-chars` uses characters, not model tokens. It may omit optional sections that exceed the cap.
- Do not commit secrets, private datasets or raw user conversations. Use `.gitignore` and separate secure storage.
