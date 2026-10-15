#!/usr/bin/env python3
"""Research Kernel v0.4: scientific plans, controlled execution and records."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid

import rk_assets
import rk_science
import rk_context
import rk_intake
import rk_execution
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIRS = (
    "workspace/tasks", "workspace/handoffs",
    "knowledge/claims", "knowledge/evidence",
    "memory/inbox", "memory/compacted",
    "methods/skills", "experiments/runs", "src", "tests",
    "assets/registry", "benchmarks/definitions", "research/archive",
    "research/publications",
    "science/questions", "science/hypotheses", "science/studies",
    "science/protocols", "science/runs", "science/observations",
    "science/analyses", "science/reviews",
    "plans/specs", "plans/locks",
)
STARTER = {
    "AGENTS.md": "# Research Kernel\nRead workspace/policies.md and knowledge/INDEX.md before work.\n",
    "workspace/policies.md": "# Policies\nTreat model output as unverified. Preserve evidence.\n",
    "knowledge/INDEX.md": "# Knowledge Map\nAdd links to research documents here.\n",
    "memory/INDEX.md": "# Memory Map\nCompacted memory is a pointer, not authoritative evidence.\n",
    "assets/INDEX.md": "# Research Assets\nUse `python rk.py asset list` for versioned assets.\n",
    "science/INDEX.md": "# Scientific Research Map\nUse `python rk.py science list` and trace Question -> Study -> Protocol -> Run -> Observation -> Analysis -> Review.\n",
}
TASK_STATES = {"active", "blocked", "done"}
CLAIM_STATES = {"provisional", "disputed", "verified", "refuted", "superseded"}
MEMORY_KINDS = {"decision", "observation", "open_question", "failure"}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def uid(kind):
    return f"{kind}-{uuid.uuid4().hex[:12]}"


def fail(message):
    raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data, new=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if new:
        with path.open("x", encoding="utf-8") as f:
            f.write(payload)
        return
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temp.write_text(payload, encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def source_ref(name):
    path = (ROOT / name).resolve()
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        fail("Source must be inside this repository")
    if (not rel.parts
            or any(x in {".git", ".rk", ".cache", ".venv", "data", "secrets",
                         ".ipynb_checkpoints"} for x in rel.parts)
            or re.search(r"(api[_-]?key|password|secret|credential|private[_-]?key|access[_-]?token|\.env)",
                         path.name, flags=re.I)):
        fail("Source is in a forbidden directory or resembles sensitive credentials")
    if not path.is_file():
        fail(f"Source does not exist: {name}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": rel.as_posix(), "sha256": digest.hexdigest()}


def record_path(kind, record_id, folder):
    if not re.fullmatch(rf"{kind}-[0-9a-f]{{12}}", record_id):
        fail(f"Invalid {kind} ID: {record_id}")
    target = (ROOT / folder / f"{record_id}.json").resolve()
    try:
        target.relative_to(ROOT)
    except ValueError:
        fail("Record path escapes the repository")
    return target


def git_info(*args):
    try:
        p = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True,
            text=True, timeout=3, check=False,
        )
        return p.stdout.strip() if p.returncode == 0 else "unavailable"
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"


def init():
    for folder in DIRS:
        directory = ROOT / folder
        directory.mkdir(parents=True, exist_ok=True)
        # Empty directories are not tracked by Git; keep structure clonable.
        marker = directory / ".gitkeep"
        if not marker.exists():
            marker.touch()
    for name, content in STARTER.items():
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content, encoding="utf-8")
    print(f"Initialized: {ROOT}")


def task_new(args):
    if not args.title.strip() or not args.next.strip():
        fail("Task title and next action must not be blank")
    ident = uid("task")
    save_json(record_path("task", ident, "workspace/tasks"), {
        "schema_version": 1, "id": ident, "title": args.title,
        "status": "active", "next_action": args.next,
        "created_at": now(), "updated_at": now(), "log": [],
    }, new=True)
    print(ident)


def task_set(args):
    path = record_path("task", args.id, "workspace/tasks")
    data = read_json(path)
    if not any((args.status, args.next is not None, args.note)):
        fail("Specify --status, --next or --note")
    if args.status:
        data["status"] = args.status
    if args.next is not None:
        data["next_action"] = args.next
    if args.note:
        data.setdefault("log", []).append({"at": now(), "note": args.note})
    data["updated_at"] = now()
    save_json(path, data)
    print(path.relative_to(ROOT))


def handoff(args):
    task = read_json(record_path("task", args.id, "workspace/tasks"))
    notes = "\n".join(
        f"- {entry['at']}: {entry['note']}"
        for entry in task.get("log", [])[-5:]
    ) or "- None"
    body = f"""# Handoff: {task['id']}

- Created (UTC): {now()}
- Task: {task['title']}
- Status: {task['status']}
- Next action: {task['next_action']}
- Git commit: {git_info('rev-parse', 'HEAD')}
- Git branch: {git_info('branch', '--show-current')}

## Recent progress
{notes}

## Session notes
{args.note or 'No additional notes provided.'}

## Navigation
- Read `AGENTS.md`, `workspace/policies.md`, and `knowledge/INDEX.md`.
- Verify claims against original sources rather than this summary.
- Read `workspace/tasks/{task['id']}.json` for the live task state.
"""
    path = ROOT / "workspace/handoffs" / f"{uid('handoff')}-{args.id}.md"
    path.write_text(body, encoding="utf-8")
    print(path.relative_to(ROOT))


def claim_new(args):
    if not args.statement.strip():
        fail("Claim statement must not be blank")
    ident = uid("claim")
    refs = [source_ref(x) for x in args.source]
    for ref in args.asset_ref or []:
        rk_assets.require_published(ROOT, ref)
    path = record_path("claim", ident, "knowledge/claims")
    save_json(path, {
        "schema_version": 1, "id": ident,
        "statement": args.statement, "scope": args.scope,
        "assumptions": args.assumptions, "status": "provisional",
        "sources": refs, "asset_refs": args.asset_ref or [],
        "created_at": now(), "history": [],
    }, new=True)
    print(ident)


def claim_challenge(args):
    if not args.reason.strip():
        fail("Challenge reason must not be blank")
    path = record_path("claim", args.id, "knowledge/claims")
    data = read_json(path)
    data["status"] = "disputed"
    data.setdefault("history", []).append({
        "at": now(), "event": "challenged", "reason": args.reason,
    })
    save_json(path, data)
    print(path.relative_to(ROOT))


def memory_propose(args):
    if not args.summary.strip():
        fail("Memory summary must not be blank")
    ident = uid("memory")
    path = record_path("memory", ident, "memory/inbox")
    save_json(path, {
        "schema_version": 1, "id": ident, "kind": args.kind,
        "scope": args.scope, "summary": args.summary,
        "sources": [source_ref(x) for x in args.source],
        "status": "proposed", "created_at": now(),
    }, new=True)
    print(ident)


def check_sources(document):
    errors = []
    for ref in document.get("sources", []):
        try:
            current = source_ref(ref["path"])
            if current["sha256"] != ref["sha256"]:
                errors.append(f"STALE source: {ref['path']}")
        except (ValueError, KeyError, TypeError) as e:
            errors.append(f"Invalid source: {ref!r} ({e})")
    return errors


def memory_accept(args):
    src = record_path("memory", args.id, "memory/inbox")
    data = read_json(src)
    if check_sources(data):
        fail("Evidence is missing or changed; do not accept this memory")
    answer = input("Human review required. Type ACCEPT to promote: ").strip()
    if answer != "ACCEPT":
        fail("Promotion cancelled")
    data["status"] = "accepted"
    data["accepted_at"] = now()
    dest = record_path("memory", args.id, "memory/compacted")
    save_json(dest, data, new=True)
    src.unlink()
    print(dest.relative_to(ROOT))


def doctor():
    problems = []
    for name in STARTER:
        if not (ROOT / name).is_file():
            problems.append(f"Missing file: {name}")
    for folder in DIRS:
        if not (ROOT / folder).is_dir():
            problems.append(f"Missing directory: {folder}")
    skill_dir = ROOT / "methods/skills"
    if skill_dir.is_dir():
        for folder in sorted(skill_dir.iterdir()):
            if not folder.is_dir():
                continue
            entry = folder / "SKILL.md"
            if not entry.is_file():
                problems.append(f"Missing SKILL.md in {folder.name}")
                continue
            try:
                text = entry.read_text(encoding="utf-8")
                if not text.startswith("---\n"):
                    problems.append(f"Missing Skill frontmatter: {folder.name}")
                    continue
                front = text.split("---\n", 2)[1]
                name = re.search(r"^name:\s*(.*?)\s*$", front, flags=re.M)
                desc = re.search(r"^description:\s*(.*?)\s*$", front, flags=re.M)
                if (not name or name.group(1) != folder.name or
                        not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", folder.name)
                        or len(folder.name) > 64):
                    problems.append(f"Invalid Skill name: {folder.name}")
                if not desc or not 0 < len(desc.group(1).strip()) <= 1024:
                    problems.append(f"Invalid Skill description: {folder.name}")
            except (OSError, IndexError) as e:
                problems.append(f"Invalid Skill: {folder.name} ({e})")
    locations = [
        ("task", "workspace/tasks"),
        ("claim", "knowledge/claims"),
        ("memory", "memory/inbox"),
        ("memory", "memory/compacted"),
    ]
    checked = 0
    for kind, folder in locations:
        for path in sorted((ROOT / folder).glob("*.json")):
            checked += 1
            try:
                if not path.resolve().is_relative_to(ROOT):
                    fail("Record symlink escapes the repository")
                data = read_json(path)
                if not isinstance(data, dict):
                    fail("Record must contain a JSON object")
                if (data.get("schema_version") != 1
                        or data.get("id") != path.stem
                        or not re.fullmatch(rf"{kind}-[0-9a-f]{{12}}", path.stem)):
                    problems.append(f"Invalid ID/schema: {path.relative_to(ROOT)}")
                if kind == "task":
                    if data.get("status") not in TASK_STATES:
                        problems.append(f"Invalid task status: {path.name}")
                    if not data.get("title") or "next_action" not in data:
                        problems.append(f"Incomplete task: {path.name}")
                if kind == "claim":
                    if data.get("status") not in CLAIM_STATES:
                        problems.append(f"Invalid claim status: {path.name}")
                    if not isinstance(data.get("asset_refs", []), list):
                        problems.append(f"Invalid asset_refs: {path.name}")
                    else:
                        for ref in data.get("asset_refs", []):
                            try:
                                rk_assets.require_published(ROOT, ref)
                            except (ValueError, TypeError) as e:
                                problems.append(f"{path.name}: invalid asset ref: {e}")
                if kind == "memory":
                    required = "proposed" if folder.endswith("inbox") else "accepted"
                    if data.get("status") != required or data.get("kind") not in MEMORY_KINDS:
                        problems.append(f"Invalid memory state: {path.name}")
                if kind != "task":
                    if not data.get("sources") or not isinstance(data["sources"], list):
                        problems.append(f"Missing sources: {path.name}")
                    problems.extend(f"{path.name}: {err}" for err in check_sources(data))
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
                problems.append(f"Unreadable record: {path.name} ({e})")
    problems.extend(rk_assets.audit(ROOT, source_ref))
    problems.extend(rk_science.check(ROOT, source_ref))
    problems.extend(rk_execution.audit(ROOT))
    for problem in problems:
        print("ERROR:", problem)
    n_assets = len(list((ROOT / "assets/registry").glob("*/*/*.json")))
    n_science = sum(1 for folder in rk_science.KINDS.values()
                    for _ in (ROOT / "science" / folder[1]).glob("*.json"))
    print(f"Checked {checked} task/claim/memory records, {n_assets} asset versions, "
          f"{n_science} scientific objects; errors: {len(problems)}")
    return 1 if problems else 0


def context(args):
    if args.max_chars < 1:
        fail("--max-chars must be positive")
    # Mandatory: policy and explicitly requested live task state.
    required = [
        ("AGENTS.md", (ROOT / "AGENTS.md").read_text(encoding="utf-8")),
        ("workspace/policies.md", (ROOT / "workspace/policies.md").read_text(encoding="utf-8")),
    ]
    optional = []
    if args.task:
        path = record_path("task", args.task, "workspace/tasks")
        required.append((str(path.relative_to(ROOT)), path.read_text(encoding="utf-8")))
        matches = sorted((ROOT / "workspace/handoffs").glob(f"*-{args.task}.md"))
        if matches:
            path = matches[-1]
            optional.append((str(path.relative_to(ROOT)), path.read_text(encoding="utf-8")))
    optional += [
        ("knowledge/INDEX.md", (ROOT / "knowledge/INDEX.md").read_text(encoding="utf-8")),
        ("memory/INDEX.md", (ROOT / "memory/INDEX.md").read_text(encoding="utf-8")),
        ("assets/INDEX.md", (ROOT / "assets/INDEX.md").read_text(encoding="utf-8")),
    ]
    output, skipped = "", []
    for must, (name, content) in (
        [(True, item) for item in required]
        + [(False, item) for item in optional]
    ):
        section = f"### {name}\n{content.strip()}\n\n"
        if len(output) + len(section) <= args.max_chars:
            output += section
        elif must:
            fail(f"Context budget too small to fit mandatory section: {name}")
        else:
            skipped.append(name)
    print(output.rstrip())
    if skipped:
        print("SKIPPED (context budget): " + ", ".join(skipped), file=sys.stderr)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Research Kernel v0.4")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("doctor")

    tasks = sub.add_parser("task").add_subparsers(dest="action", required=True)
    p = tasks.add_parser("new")
    p.add_argument("--title", required=True)
    p.add_argument("--next", required=True)
    p = tasks.add_parser("set")
    p.add_argument("id")
    p.add_argument("--status", choices=sorted(TASK_STATES))
    p.add_argument("--next")
    p.add_argument("--note")

    p = sub.add_parser("handoff")
    p.add_argument("id")
    p.add_argument("--note", default="")

    claims = sub.add_parser("claim").add_subparsers(dest="action", required=True)
    p = claims.add_parser("new")
    p.add_argument("--statement", required=True)
    p.add_argument("--source", action="append", required=True)
    p.add_argument("--scope", default="unspecified")
    p.add_argument("--assumptions", default="")
    p.add_argument("--asset-ref", action="append", help="published asset ref, e.g. dataset:corpus@v1")
    p = claims.add_parser("challenge")
    p.add_argument("id")
    p.add_argument("--reason", required=True)

    memories = sub.add_parser("memory").add_subparsers(dest="action", required=True)
    p = memories.add_parser("propose")
    p.add_argument("--summary", required=True)
    p.add_argument("--kind", choices=sorted(MEMORY_KINDS), default="observation")
    p.add_argument("--scope", default="project")
    p.add_argument("--source", action="append", required=True)
    p = memories.add_parser("accept")
    p.add_argument("id")

    rk_assets.add_cli(sub)
    rk_science.add_cli(sub)
    rk_intake.add_cli(sub)
    rk_execution.add_cli(sub)

    compose = sub.add_parser("compose", help="read-only scientific result composition checks")
    compose_cmds = compose.add_subparsers(dest="compose_action", required=True)
    check = compose_cmds.add_parser("check", help="compare two sealed Runs under a declared contract")
    check.add_argument("left", help="first Run ID")
    check.add_argument("right", help="second Run ID")
    check.add_argument("--contract", default="science/contracts/benchmark-comparison.v1.json")

    p = sub.add_parser("context")
    rk_context.add_arguments(p)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "init":
            init()
        elif args.cmd == "doctor":
            return doctor()
        elif args.cmd == "task":
            (task_new if args.action == "new" else task_set)(args)
        elif args.cmd == "handoff":
            handoff(args)
        elif args.cmd == "claim":
            (claim_new if args.action == "new" else claim_challenge)(args)
        elif args.cmd == "memory":
            (memory_propose if args.action == "propose" else memory_accept)(args)
        elif args.cmd == "context":
            # Preserve v0.2 default Context output for existing users/scripts.
            if not (args.study or args.protocol or args.memory or args.manifest_out or args.profile != "bootstrap"):
                context(args)
            else:
                rk_context.pack(
                    args, ROOT,
                    lambda tid: read_json(record_path("task", tid, "workspace/tasks")),
                    check_sources,
                )
        elif args.cmd == "asset":
            return rk_assets.dispatch(args, ROOT, source_ref, read_json, save_json)
        elif args.cmd == "store":
            rk_assets.do_store(args, ROOT)
        elif args.cmd == "science":
            return rk_science.dispatch(args, ROOT, source_ref, save_json)
        elif args.cmd == "intake":
            return rk_intake.dispatch(args, ROOT)
        elif args.cmd == "plan":
            return rk_execution.dispatch(args, ROOT)
        elif args.cmd == "compose":
            # Lazy import preserves old per-module testing and v0.3 commands.
            import rk_composition
            return rk_composition.check(args, ROOT, source_ref)
        return 0
    except (OSError, ValueError, EOFError, TypeError, KeyError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
