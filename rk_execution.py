"""Research Kernel 0.4: typed, fail-closed, deterministic execution DAG.

No arbitrary command execution, network fetches, LLM invocation, or secret brokerage.
Execution records are local and ignored; explicit small export snapshots live in Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import rk_assets
import rk_context
import rk_science

PLAN_ID = re.compile(r"plan-[0-9a-f]{12}\Z")
EXEC_ID = re.compile(r"exec-[0-9a-f]{12}\Z")
STEP_ID = re.compile(r"[a-z][a-z0-9-]{0,47}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
NAME = re.compile(r"[a-z][a-z0-9_]{0,47}\Z")
SKILL = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
MEMORY = re.compile(r"memory-[0-9a-f]{12}\Z")
FILE_LIMIT = 32 * 1024 * 1024
MAX_STEPS = 64
OPERATIONS = {"jsonl_rate", "compare_rates", "sha256_file", "validate_json"}
INVARIANTS = {"frozen_protocol", "no_secret_content", "artifact_local_only"}
DENY_PARTS = {".git", ".rk", "secrets", ".venv", ".cache", ".ipynb_checkpoints", "data", "raw"}
DENY_NAME = re.compile(r"(api[_-]?key|password|secret|credential|private[_-]?key|access[_-]?token|^\.env($|\.)|\.pem$)", re.I)
PLAN_FIELDS = {"schema_version", "id", "title", "study", "protocol", "need", "spirit", "environment", "steps", "created_at"}
STEP_FIELDS = {"id", "op", "depends_on", "inputs", "params", "context"}


def fail(message):
    raise ValueError(message)


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha_bytes(content):
    return hashlib.sha256(content).hexdigest()


def json_bytes(data):
    return (json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


def read_small_json(path, size_limit=128 * 1024):
    if not path.is_file() or path.stat().st_size > size_limit:
        fail("JSON record missing or oversized: " + path.name)
    return json.loads(path.read_text(encoding="utf-8"))


def atomic(path, data, *, new=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json_bytes(data)
    if new:
        with path.open("xb") as out:
            out.write(payload)
        return
    temp = path.with_name("." + path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temp.write_bytes(payload)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _safe_local_folder(root, name):
    folder = root / name
    if folder.is_symlink() or not folder.resolve().is_relative_to(root.resolve()):
        fail("Refusing symlinked or escaping local directory: " + name)
    return folder


def plan_path(root, ident):
    if not isinstance(ident, str) or not PLAN_ID.fullmatch(ident):
        fail("Invalid Plan ID")
    folder = _safe_local_folder(root, "plans/specs")
    path = folder / (ident + ".json")
    if path.is_symlink():
        fail("Symlinked Plan record forbidden")
    return path


def lock_path(root, ident):
    plan_path(root, ident)
    folder = _safe_local_folder(root, "plans/locks")
    path = folder / (ident + ".json")
    if path.is_symlink():
        fail("Symlinked frozen Plan lock forbidden")
    return path


def execution_path(root, plan_id, execution_id):
    plan_path(root, plan_id)
    if not EXEC_ID.fullmatch(execution_id):
        fail("Invalid Execution ID")
    return _safe_local_folder(root, ".rk/executions") / plan_id / execution_id


def local_source(root, name):
    if (not isinstance(name, str) or not 1 <= len(name) <= 300
            or "\\" in name or "\x00" in name or name.startswith("/")):
        fail("Source must be a short relative workspace path")
    rel = Path(name)
    if (rel.is_absolute() or not rel.parts or any(p in (".", "..") for p in rel.parts)
            or any(p in DENY_PARTS for p in rel.parts)
            or any(DENY_NAME.search(p) for p in rel.parts)):
        fail("Source path is forbidden: " + name)
    target = (root / rel).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        fail("Source outside repository or missing: " + name)
    if target.stat().st_size > FILE_LIMIT:
        fail("Source too large for builtin executor: " + name)
    # Reject symlinked components, even links that remain inside repository.
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            fail("Symlinked input refused: " + name)
    return target


def digest_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_plan(root, ident):
    path = plan_path(root, ident)
    if not path.is_file() or path.is_symlink():
        fail("Plan is missing or symlinked")
    data = read_small_json(path, 1024 * 1024)
    if not isinstance(data, dict) or data.get("id") != ident:
        fail("Plan ID does not match file")
    return data


def accepted_memory(root, ident):
    if not isinstance(ident, str) or not MEMORY.fullmatch(ident):
        fail("Invalid accepted Memory ID")
    path = root / "memory/compacted" / (ident + ".json")
    if not path.is_file() or path.is_symlink():
        fail("Unknown accepted Memory: " + ident)
    data = read_small_json(path)
    if not isinstance(data, dict) or data.get("id") != ident or data.get("status") != "accepted":
        fail("Not an approved Memory: " + ident)
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        fail("Accepted Memory missing provenance")
    for ref in sources:
        if not isinstance(ref, dict) or set(ref) != {"path", "sha256"}:
            fail("Malformed Memory source")
        actual = _source_ref(root, ref["path"])
        if ref != actual:
            fail("Accepted Memory has stale evidence")
    return data


def approved_skill(root, name):
    if not isinstance(name, str) or not SKILL.fullmatch(name) or len(name) > 64:
        fail("Invalid Skill name")
    folder = root / "methods/skills" / name
    target = folder / "SKILL.md"
    if folder.is_symlink() or target.is_symlink() or not target.is_file():
        fail("Missing or symlinked Skill")
    if not target.resolve().is_relative_to(root.resolve()) or target.stat().st_size > 12000:
        fail("Skill is oversized or outside repository")
    content = target.read_text(encoding="utf-8")
    if not content.startswith("---\n") or not re.search(
            r"(?m)^name: " + re.escape(name) + r"\s*$", content.split("---\n", 2)[1]):
        fail("Skill frontmatter identity mismatch")
    return target, content


def _ref_check(root, ref):
    if not isinstance(ref, str) or not ref or len(ref) > 200:
        fail("Invalid context dependency ref")
    if MEMORY.fullmatch(ref):
        accepted_memory(root, ref)
    elif ref.startswith(("dataset:", "benchmark:", "report:", "publication:", "archive:")):
        rk_assets.require_published(root, ref)
    else:
        rk_science.load(root, ref)


def validate_plan(root, plan, *, strict_sources=True):
    if not isinstance(plan, dict) or set(plan) != PLAN_FIELDS or plan.get("schema_version") != 1:
        fail("Invalid Plan schema")
    if not PLAN_ID.fullmatch(str(plan["id"])):
        fail("Invalid Plan ID")
    for k in ("title", "need", "created_at"):
        if not isinstance(plan[k], str) or not plan[k].strip() or len(plan[k]) > 1000:
            fail("Missing or excessive Plan value: " + k)
    study = rk_science.load(root, plan["study"])
    protocol = rk_science.load(root, plan["protocol"])
    if study["kind"] != "study" or protocol["kind"] != "protocol" or protocol["status"] != "frozen":
        fail("Plan requires valid Study and frozen Protocol")
    if not any(l["relation"] == "for_study" and l["target"] == plan["study"]
               for l in protocol["links"]):
        fail("Frozen Protocol does not belong to Plan Study")
    rk_science.validate(root, study, lambda n: _source_ref(root, n))
    rk_science.validate(root, protocol, lambda n: _source_ref(root, n))
    spirit = plan["spirit"]
    if (not isinstance(spirit, dict) or set(spirit) != {"invariants", "review_required"}
            or not isinstance(spirit["invariants"], list) or set(spirit["invariants"]) != INVARIANTS
            or not isinstance(spirit["review_required"], list)
            or "scientific_interpretation_and_comparability" not in spirit["review_required"]
            or len(spirit["review_required"]) > 20
            or any(not isinstance(x, str) or not x.strip() or len(x) > 80
                   for x in spirit["review_required"])):
        fail("Plan must preserve mandatory invariants and external scientific review")
    env = plan["environment"]
    if env != {"executor": "builtin-v1", "network": "not_used", "process_isolation": "none"}:
        fail("Unsupported execution environment; no custom shell/network executors")
    steps = plan["steps"]
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        fail("Plan must contain 1..64 steps")
    order, graph, by_id = [], {}, {}
    for step in steps:
        if not isinstance(step, dict) or set(step) != STEP_FIELDS:
            fail("Invalid Step fields")
        ident = step["id"]
        if not isinstance(ident, str) or not STEP_ID.fullmatch(ident) or ident in by_id:
            fail("Duplicate or invalid Step ID")
        if step["op"] not in OPERATIONS:
            fail("Operation not in allowlist: " + str(step["op"]))
        deps = step["depends_on"]
        if (not isinstance(deps, list) or len(deps) != len(set(deps))
                or any(not isinstance(d, str) or d == ident for d in deps)):
            fail("Invalid Step dependencies")
        if not isinstance(step["params"], dict) or not isinstance(step["inputs"], dict):
            fail("Step inputs/params must be objects")
        ctx = step["context"]
        if (not isinstance(ctx, dict) or set(ctx) != {"required_refs", "required_skills", "max_chars"}
                or type(ctx["max_chars"]) is not int
                or not 1000 <= ctx["max_chars"] <= 100000
                or not isinstance(ctx["required_refs"], list)
                or len(ctx["required_refs"]) > 20
                or len(ctx["required_refs"]) != len(set(ctx["required_refs"]))
                or not isinstance(ctx["required_skills"], list)
                or len(ctx["required_skills"]) > 8
                or len(ctx["required_skills"]) != len(set(ctx["required_skills"]))):
            fail("Invalid local Context contract")
        for ref in ctx["required_refs"]:
            _ref_check(root, ref)
        for name in ctx["required_skills"]:
            approved_skill(root, name)
        by_id[ident] = step
        graph[ident] = deps
    for ident, deps in graph.items():
        for dep in deps:
            if dep not in graph:
                fail("Unknown Step dependency: " + dep)
    visited, visiting = set(), set()

    def visit(ident):
        if ident in visiting:
            fail("Cyclic Plan dependencies")
        if ident in visited:
            return
        visiting.add(ident)
        for dep in graph[ident]:
            visit(dep)
        visiting.remove(ident)
        visited.add(ident)
        order.append(ident)

    for ident in graph:
        visit(ident)
    for step in steps:
        op, inputs, params, deps = step["op"], step["inputs"], step["params"], set(step["depends_on"])
        expected = {"compare_rates": {"left", "right"}}.get(op, {"data"})
        if set(inputs) != expected:
            fail("Unexpected input interface for " + op)
        if op == "jsonl_rate":
            if set(params) != {"field"} or not isinstance(params["field"], str) or not NAME.fullmatch(params["field"]):
                fail("jsonl_rate expects one short field name")
        elif params:
            fail("Operation does not accept params: " + op)
        for input_name, input_ref in inputs.items():
            if not isinstance(input_ref, dict) or "type" not in input_ref:
                fail("Invalid typed input")
            if input_ref["type"] == "workspace_file":
                if set(input_ref) != {"type", "path", "sha256"} or deps:
                    fail("File-input step cannot depend on another step")
                if not isinstance(input_ref["sha256"], str) or not HASH.fullmatch(input_ref["sha256"]):
                    fail("Input must pin SHA-256")
                if strict_sources and digest_file(local_source(root, input_ref["path"])) != input_ref["sha256"]:
                    fail("Input SHA-256 mismatch: " + input_ref["path"])
            elif input_ref["type"] == "step_output":
                if set(input_ref) != {"type", "step"} or input_ref["step"] not in deps:
                    fail("Step input must reference an explicit dependency")
                if input_ref["step"] == step["id"]:
                    fail("Cannot consume own output")
                if by_id[input_ref["step"]]["op"] != "jsonl_rate" or op != "compare_rates":
                    fail("Incompatible producer/consumer interface")
            else:
                fail("Unknown input type")
        if op == "compare_rates" and (len(deps) != 2
                or any(i["type"] != "step_output" for i in inputs.values())
                or {i["step"] for i in inputs.values()} != deps):
            fail("compare_rates expects exactly two distinct prior rate outputs")
        if op != "compare_rates" and any(i["type"] != "workspace_file" for i in inputs.values()):
            fail("Operation expects a pinned workspace file")
    return order, by_id, study, protocol


def _source_ref(root, name):
    # Reuse existing scientific provenance rules without importing the CLI.
    path = local_source(root, name)
    return {"path": name, "sha256": digest_file(path)}


def _context_dependencies(root, plan):
    """Pin research authority and local policy, not just step file inputs."""
    paths = {
        "AGENTS.md": root / "AGENTS.md",
        "workspace/policies.md": root / "workspace/policies.md",
        "study": rk_science.path_for(root, plan["study"]),
        "protocol": rk_science.path_for(root, plan["protocol"]),
    }
    for step in plan["steps"]:
        for ref in step["context"]["required_refs"]:
            if MEMORY.fullmatch(ref):
                accepted_memory(root, ref)
                path = root / "memory/compacted" / (ref + ".json")
            elif ref.startswith(("dataset:", "benchmark:", "report:", "publication:", "archive:")):
                path = rk_assets.asset_path(root, ref)
            else:
                path = rk_science.path_for(root, ref)
            paths["dependency:" + ref] = path
        for skill in step["context"]["required_skills"]:
            path, _ = approved_skill(root, skill)
            paths["skill:" + skill] = path
    result = {}
    for label, path in paths.items():
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            fail("Context authority file missing or symlinked: " + label)
        result[label] = digest_file(path)
    return result


def load_frozen(root, ident):
    plan = load_plan(root, ident)
    order, by_id, study, protocol = validate_plan(root, plan)
    lock = read_small_json(lock_path(root, ident))
    if not isinstance(lock, dict) or set(lock) != {"schema_version", "plan_id", "plan_sha256", "protocol_sha256", "executor_sha256", "dependency_sha256", "frozen_at", "reviewed_by"}:
        fail("Invalid frozen Plan lock")
    if (lock["schema_version"] != 1 or lock["plan_id"] != ident
            or lock["plan_sha256"] != digest_file(plan_path(root, ident))):
        fail("Frozen Plan changed after review; create a new Plan")
    if lock["protocol_sha256"] != digest_file(rk_science.path_for(root, plan["protocol"])):
        fail("Frozen Protocol changed since Plan freeze")
    if lock["executor_sha256"] != digest_file(Path(__file__).resolve()):
        fail("Builtin executor implementation changed since Plan freeze")
    if lock["dependency_sha256"] != _context_dependencies(root, plan):
        fail("Mandatory Context authority changed since Plan freeze; create new reviewed Plan")
    return plan, lock, order, by_id, study, protocol


def create(args, root):
    if args.left == args.right:
        fail("Provide two distinct evaluation files")
    if not args.title.strip() or not args.need.strip():
        fail("Plan title and need are required")
    if not NAME.fullmatch(args.field):
        fail("Invalid metric field")
    def input_file(name):
        return {"type": "workspace_file", "path": name,
                "sha256": digest_file(local_source(root, name))}
    left, right = input_file(args.left), input_file(args.right)
    def step(ident, op, deps, inputs, params):
        return {"id": ident, "op": op, "depends_on": deps, "inputs": inputs,
                "params": params, "context": {"required_refs": [],
                                                  "required_skills": [], "max_chars": 16000}}
    plan = {
        "schema_version": 1, "id": "plan-" + uuid.uuid4().hex[:12],
        "title": args.title.strip(), "need": args.need.strip(),
        "study": args.study, "protocol": args.protocol,
        "spirit": {"invariants": sorted(INVARIANTS),
                   "review_required": ["scientific_interpretation_and_comparability"]},
        "environment": {"executor": "builtin-v1", "network": "not_used", "process_isolation": "none"},
        "steps": [
            step("baseline", "jsonl_rate", [], {"data": left}, {"field": args.field}),
            step("candidate", "jsonl_rate", [], {"data": right}, {"field": args.field}),
            step("compare", "compare_rates", ["baseline", "candidate"],
                 {"left": {"type": "step_output", "step": "baseline"},
                  "right": {"type": "step_output", "step": "candidate"}}, {}),
        ],
        "created_at": stamp(),
    }
    validate_plan(root, plan)
    atomic(plan_path(root, plan["id"]), plan, new=True)
    print(plan["id"])


def check(args, root):
    plan = load_plan(root, args.id)
    order, _, _, _ = validate_plan(root, plan)
    frozen = lock_path(root, args.id).exists()
    if frozen:
        load_frozen(root, args.id)
    print(json.dumps({"plan": args.id, "frozen": frozen, "order": order,
                      "validation": "structural_and_provenance_only",
                      "scientific_validity": "not_assessed"}, indent=2))


def freeze(args, root):
    plan = load_plan(root, args.id)
    validate_plan(root, plan)
    if not args.reviewed_by.strip():
        fail("Human reviewer identifier required; not authenticated by CLI")
    lock = {"schema_version": 1, "plan_id": args.id,
            "plan_sha256": digest_file(plan_path(root, args.id)),
            "protocol_sha256": digest_file(rk_science.path_for(root, plan["protocol"])),
            "executor_sha256": digest_file(Path(__file__).resolve()),
            "dependency_sha256": _context_dependencies(root, plan),
            "frozen_at": stamp(), "reviewed_by": args.reviewed_by.strip()}
    atomic(lock_path(root, args.id), lock, new=True)
    print("FROZEN", args.id)


def _node_context(plan, lock, step, study, protocol, root, budget):
    required = [
        ("Agent execution policy", "AGENTS.md", rk_context.raw_file(root, "AGENTS.md")),
        ("Workspace policy", "workspace/policies.md", rk_context.raw_file(root, "workspace/policies.md")),
        ("Selected Study", plan["study"], rk_context.render_summary(study)),
        ("Frozen Protocol", plan["protocol"], rk_context.render_summary(protocol)),
        ("Pinned Plan", plan["id"], json.dumps({"id": plan["id"], "title": plan["title"],
                                "need": plan["need"], "spirit": plan["spirit"],
                                "plan_sha256": lock["plan_sha256"]}, indent=2)),
        ("Current Step", step["id"], json.dumps(step, indent=2)),
    ]
    for ref in step["context"]["required_refs"]:
        if MEMORY.fullmatch(ref):
            item = accepted_memory(root, ref)
            content = json.dumps({"id": item["id"], "status": "accepted",
                "scope": item.get("scope"), "summary": item.get("summary"),
                "sources": item.get("sources"), "authority": "memory_pointer_not_scientific_proof"}, indent=2)
        elif ref.startswith(("dataset:", "benchmark:", "report:", "publication:", "archive:")):
            item = rk_assets.require_published(root, ref)
            storage = item.get("storage") or {}
            content = json.dumps({"asset_ref": ref, "kind": item.get("kind"),
                "title": item.get("title"), "status": item.get("status"),
                "access": item.get("access"), "license": item.get("license"),
                "payload_sha256_declared": storage.get("sha256")}, indent=2)
        else:
            item = rk_science.load(root, ref)
            content = rk_context.render_summary(item)
        required.append(("Required Dependency", ref, content))
    for name in step["context"]["required_skills"]:
        _, skill_text = approved_skill(root, name)
        required.append(("Selected Procedural Skill", name, skill_text))
    header = "# Local Research Step Context\nScope: one typed Step; not sufficient for final scientific judgement.\n"
    output = header
    selected = []
    for label, ident, content in required:
        section = f"## {label}: {ident}\n{content}\n\n"
        if len(output) + len(section) > budget:
            fail("Node Context budget insufficient for mandatory dependency: " + ident)
        output += section
        selected.append({"ref": ident, "sha256": sha_bytes(content.encode("utf-8"))})
    return output.rstrip(), {"plan": plan["id"], "step": step["id"],
                             "protocol": plan["protocol"], "scope": "required_dependencies_only",
                             "selected": selected, "budget_chars": budget,
                             "actual_chars": len(output.rstrip()),
                             "context_sha256": sha_bytes(output.rstrip().encode("utf-8"))}


def context(args, root):
    plan, lock, _, steps, study, protocol = load_frozen(root, args.id)
    if args.step not in steps:
        fail("Unknown Step in Plan")
    spec = steps[args.step]
    budget = args.max_chars if args.max_chars is not None else spec["context"]["max_chars"]
    if budget > spec["context"]["max_chars"]:
        fail("Cannot exceed the Step's approved Context budget")
    packet, manifest = _node_context(plan, lock, spec, study, protocol, root, budget)
    if args.manifest_out:
        target = (root / args.manifest_out).resolve()
        allowed = (root / ".rk").resolve()
        if not target.is_relative_to(allowed):
            fail("Context manifest must live beneath .rk")
        atomic(target, manifest)
    print(packet)


def dry_run(args, root):
    plan, lock, order, steps, study, protocol = load_frozen(root, args.id)
    reports = []
    for ident in order:
        step = steps[ident]
        _, manifest = _node_context(plan, lock, step, study, protocol, root,
                                    step["context"]["max_chars"])
        reports.append({"step": ident, "op": step["op"], "depends_on": step["depends_on"],
                        "context_chars": manifest["actual_chars"],
                        "context_sha256": manifest["context_sha256"]})
    print(json.dumps({"plan": args.id, "would_execute": reports,
                      "no_side_effects": True, "scientific_validity": "not_assessed"}, indent=2))


def _read_node_input(root, spec, results):
    if spec["type"] == "workspace_file":
        path = local_source(root, spec["path"])
        digest = digest_file(path)
        if digest != spec["sha256"]:
            fail("Input changed since Plan freeze: " + spec["path"])
        return path, digest
    value = results.get(spec["step"])
    if value is None:
        fail("Missing upstream output: " + spec["step"])
    return value["result"], value["sha256"]


def _run_builtin(root, step, results):
    values = {}
    hashes = {}
    for name, input_ref in step["inputs"].items():
        values[name], hashes[name] = _read_node_input(root, input_ref, results)
    op = step["op"]
    if op == "sha256_file":
        path = values["data"]
        result = {"sha256": hashes["data"], "bytes": path.stat().st_size,
                  "source": step["inputs"]["data"]["path"]}
    elif op == "validate_json":
        path = values["data"]
        with path.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
        result = {"valid": True, "top_level": type(data).__name__, "sha256": hashes["data"],
                  "source": step["inputs"]["data"]["path"]}
    elif op == "jsonl_rate":
        path, field = values["data"], step["params"]["field"]
        n = successes = 0
        with path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                n += 1
                if n > 100000:
                    fail("jsonl_rate maximum rows exceeded")
                record = json.loads(line)
                if not isinstance(record, dict) or field not in record:
                    fail("JSONL row missing required outcome field")
                value = record[field]
                if type(value) is bool:
                    successes += int(value)
                elif type(value) is int and value in {0, 1}:
                    successes += value
                else:
                    fail("Outcome must be boolean or integer 0/1")
        if n == 0:
            fail("Cannot compute success rate from empty sample")
        result = {"trials": n, "successes": successes, "success_rate": successes/n,
                  "source": step["inputs"]["data"]["path"], "source_sha256": hashes["data"],
                  "outcome_field": field}
    elif op == "compare_rates":
        a, b = values["left"], values["right"]
        for item in (a, b):
            if not isinstance(item, dict) or set(("trials", "successes", "success_rate")) - set(item):
                fail("compare_rates requires validated rate outputs")
        result = {"baseline_rate": a["success_rate"], "candidate_rate": b["success_rate"],
                  "delta": b["success_rate"] - a["success_rate"],
                  "baseline_trials": a["trials"], "candidate_trials": b["trials"],
                  "interpretation": "Arithmetic only; no statistical or scientific validity claim"}
    else:
        fail("Unsupported builtin operation")
    return result, hashes


def _step_artifact(root, plan, lock, spec, study, protocol, results):
    context_text, manifest = _node_context(plan, lock, spec, study, protocol, root,
                                           spec["context"]["max_chars"])
    del context_text  # Context is intentionally not injected into a non-LLM builtin.
    result, inputs = _run_builtin(root, spec, results)
    return {"schema_version": 1, "step": spec["id"], "operation": spec["op"],
            "plan_sha256": lock["plan_sha256"], "context_sha256": manifest["context_sha256"],
            "inputs": inputs, "result": result,
            "environment": {"executor": "builtin-v1", "python": platform.python_version(),
                            "platform": platform.system(), "implementation_sha256": lock["executor_sha256"]},
            "completed_at": stamp(), "scientific_validity": "not_assessed"}


def _replay_completed(output_dir, ledger, steps, expected_plan_sha):
    result_objects = {}
    for step_id, record in ledger["steps"].items():
        if record.get("status") != "completed":
            continue
        path = output_dir / "steps" / (step_id + ".json")
        if not path.is_file() or path.is_symlink() or digest_file(path) != record.get("artifact_sha256"):
            fail("Stored completed output was altered: " + step_id)
        output = read_small_json(path)
        if (output.get("step") != step_id or output.get("plan_sha256") != expected_plan_sha
                or output.get("operation") != steps[step_id]["op"]):
            fail("Stored output is not valid for this Plan")
        result_objects[step_id] = {"result": output["result"], "sha256": record["artifact_sha256"]}
    return result_objects


def _find_execution(root, execution_id):
    if not EXEC_ID.fullmatch(execution_id):
        fail("Invalid execution ID")
    matches = list(_safe_local_folder(root, ".rk/executions").glob("plan-*/" + execution_id + "/execution.json"))
    if len(matches) != 1:
        fail("Unknown or ambiguous Execution ID")
    path = matches[0]
    if path.is_symlink() or not path.resolve().is_relative_to((root / ".rk/executions").resolve()):
        fail("Execution manifest path invalid")
    ledger = read_small_json(path)
    return ledger["plan_id"], path.parent, ledger


def execute(root, plan_id, *, resume=None, max_steps=None):
    plan, lock, order, steps, study, protocol = load_frozen(root, plan_id)
    if max_steps is not None and max_steps < 1:
        fail("--max-steps must be at least one")
    # Every mandatory Step Context must fit before any execution side effects.
    for step_id in order:
        step_spec = steps[step_id]
        _node_context(plan, lock, step_spec, study, protocol, root,
                      step_spec["context"]["max_chars"])
    if resume:
        found_plan, output_dir, ledger = _find_execution(root, resume)
        if found_plan != plan_id or ledger.get("plan_sha256") != lock["plan_sha256"]:
            fail("Execution Plan snapshot mismatch")
        if ledger.get("status") == "completed":
            fail("Execution already completed; use plan status or plan export")
        if set(ledger["steps"]) != set(steps):
            fail("Execution node set does not match Plan")
        results = _replay_completed(output_dir, ledger, steps, lock["plan_sha256"])
    else:
        execution_id = "exec-" + uuid.uuid4().hex[:12]
        output_dir = execution_path(root, plan_id, execution_id)
        output_dir.mkdir(parents=True, exist_ok=False)
        ledger = {"schema_version": 1, "execution_id": execution_id, "plan_id": plan_id,
                  "plan_sha256": lock["plan_sha256"], "protocol": plan["protocol"],
                  "started_at": stamp(), "updated_at": stamp(), "status": "running",
                  "steps": {sid: {"status": "pending"} for sid in steps}}
        atomic(output_dir / "execution.json", ledger, new=True)
        results = {}
    count = 0
    for ident in order:
        if ident in results:
            continue
        if max_steps is not None and count >= max_steps:
            ledger["status"] = "paused"
            ledger["updated_at"] = stamp()
            atomic(output_dir / "execution.json", ledger)
            print(json.dumps({"execution_id": ledger["execution_id"], "status": "paused",
                              "completed_steps": list(results)}, indent=2))
            return 0
        # Recheck pinned authorities and input snapshot before each operation.
        # A concurrent mutation will fail closed before scheduling the next Step.
        load_frozen(root, plan_id)
        step = steps[ident]
        if any(dep not in results for dep in step["depends_on"]):
            fail("Missing completed predecessor for Step " + ident)
        ledger["steps"][ident] = {"status": "running"}
        ledger["status"] = "running"
        ledger["updated_at"] = stamp()
        atomic(output_dir / "execution.json", ledger)
        try:
            artifact = _step_artifact(root, plan, lock, step, study, protocol, results)
            path = output_dir / "steps" / (ident + ".json")
            atomic(path, artifact)
            digest = digest_file(path)
            results[ident] = {"result": artifact["result"], "sha256": digest}
            ledger["steps"][ident] = {"status": "completed", "artifact_sha256": digest}
        except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
            # Intentionally do not save raw source content, stacktraces or environment variables.
            ledger["steps"][ident] = {"status": "failed", "error_type": type(exc).__name__}
            ledger["status"] = "failed"
            ledger["updated_at"] = stamp()
            atomic(output_dir / "execution.json", ledger)
            print("FAILED", ledger["execution_id"], "step=", ident, "error=", type(exc).__name__)
            return 1
        ledger["updated_at"] = stamp()
        atomic(output_dir / "execution.json", ledger)
        count += 1
    ledger["status"] = "completed"
    ledger["updated_at"] = stamp()
    atomic(output_dir / "execution.json", ledger)
    print(json.dumps({"execution_id": ledger["execution_id"], "status": "completed",
                      "completed_steps": list(results), "scientific_validity": "not_assessed"}, indent=2))
    return 0


def status(args, root):
    _, output_dir, ledger = _find_execution(root, args.execution_id)
    print(json.dumps(ledger, ensure_ascii=False, indent=2))


def export(args, root):
    plan_id, output_dir, ledger = _find_execution(root, args.execution_id)
    plan, lock, _, steps, _, _ = load_frozen(root, plan_id)
    if ledger.get("status") != "completed" or ledger["plan_sha256"] != lock["plan_sha256"]:
        fail("Only completed, matching, frozen executions can be exported")
    if not args.recorded_by.strip():
        fail("Explicit recorder identifier required; not authenticated")
    outputs = _replay_completed(output_dir, ledger, steps, lock["plan_sha256"])
    if set(outputs) != set(steps):
        fail("Not every step has a verified output")
    metadata = {"schema_version": 1, "kind": "execution_manifest", "execution_id": ledger["execution_id"],
                "plan_id": plan_id, "plan_sha256": lock["plan_sha256"], "study": plan["study"],
                "protocol": plan["protocol"], "protocol_sha256": lock["protocol_sha256"],
                "executor_sha256": lock["executor_sha256"], "recorded_by": args.recorded_by.strip(),
                "recorded_at": stamp(), "step_outputs": [
                    {"id": step, "artifact_sha256": outputs[step]["sha256"],
                     "summary": outputs[step]["result"]} for step in sorted(outputs)
                ], "scientific_validity": "not_assessed",
                "review_required": plan["spirit"]["review_required"]}
    dest = _safe_local_folder(root, "experiments/runs") / (plan_id + "-" + ledger["execution_id"] + ".json")
    atomic(dest, metadata, new=True)
    print(dest.relative_to(root))


def audit(root):
    errors = []
    folder = root / "plans/specs"
    if not folder.is_dir() or not (root / "plans/locks").is_dir():
        errors.append("Missing Plan directories (run rk.py init)")
        return errors
    for file in sorted(folder.glob("*.json")):
        try:
            if file.is_symlink():
                fail("Symlinked Plan forbidden")
            plan = load_plan(root, file.stem)
            validate_plan(root, plan)
            if lock_path(root, file.stem).exists():
                load_frozen(root, file.stem)
        except (ValueError, OSError, KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
            errors.append(str(file.relative_to(root)) + ": " + str(exc))
    for file in sorted((root / "plans/locks").glob("*.json")):
        if not plan_path(root, file.stem).is_file():
            errors.append("Orphaned Plan lock: " + file.name)
    return errors


def add_cli(sub):
    p = sub.add_parser("plan", help="typed research plans and restricted execution")
    cmds = p.add_subparsers(dest="plan_action", required=True)
    q = cmds.add_parser("create", help="create a 3-step JSONL benchmark comparison Plan")
    q.add_argument("--title", required=True)
    q.add_argument("--need", default="Compute two declared success rates and their arithmetic difference; no scientific claim")
    q.add_argument("--study", required=True)
    q.add_argument("--protocol", required=True)
    q.add_argument("--left", required=True)
    q.add_argument("--right", required=True)
    q.add_argument("--field", default="success")
    q = cmds.add_parser("check"); q.add_argument("id")
    q = cmds.add_parser("freeze"); q.add_argument("id"); q.add_argument("--reviewed-by", required=True)
    q = cmds.add_parser("dry-run"); q.add_argument("id")
    q = cmds.add_parser("context"); q.add_argument("id"); q.add_argument("--step", required=True)
    q.add_argument("--max-chars", type=int)
    q.add_argument("--manifest-out")
    q = cmds.add_parser("run"); q.add_argument("id"); q.add_argument("--max-steps", type=int)
    q = cmds.add_parser("resume"); q.add_argument("execution_id"); q.add_argument("--max-steps", type=int)
    q = cmds.add_parser("status"); q.add_argument("execution_id")
    q = cmds.add_parser("export"); q.add_argument("execution_id"); q.add_argument("--recorded-by", required=True)
    cmds.add_parser("audit")


def dispatch(args, root):
    if args.plan_action == "create":
        create(args, root)
    elif args.plan_action == "check":
        check(args, root)
    elif args.plan_action == "freeze":
        freeze(args, root)
    elif args.plan_action == "dry-run":
        dry_run(args, root)
    elif args.plan_action == "context":
        context(args, root)
    elif args.plan_action == "run":
        return execute(root, args.id, max_steps=args.max_steps)
    elif args.plan_action == "resume":
        plan_id, _, _ = _find_execution(root, args.execution_id)
        return execute(root, plan_id, resume=args.execution_id, max_steps=args.max_steps)
    elif args.plan_action == "status":
        status(args, root)
    elif args.plan_action == "export":
        export(args, root)
    elif args.plan_action == "audit":
        errors = audit(root)
        for error in errors:
            print("ERROR:", error)
        print("Plan audit errors:", len(errors))
        return 1 if errors else 0
    return 0
