"""Read-only declared-metadata compatibility checker for scientific Runs.

The output is an advisory integration check, not causal inference or scientific proof.
"""
import hashlib
import json
import re
from pathlib import Path

import rk_science

DIMENSION = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
RESULT_CODES = {
    "compatible_on_declared_dimensions": 0,
    "incompatible": 2,
    "insufficient_evidence": 3,
}


def fail(message):
    raise ValueError(message)


def contract_from_repo(root, path_str):
    folder = (root / "science/contracts").resolve()
    file = (root / path_str).resolve()
    if not file.is_relative_to(folder) or not file.is_file():
        fail("Contract must be an existing file under science/contracts/")
    if file.stat().st_size > 16 * 1024:
        fail("Contract exceeds the 16 KiB metadata limit")
    data = json.loads(file.read_text(encoding="utf-8"))
    expected = {
        "schema_version", "name", "purpose", "required_equal",
        "allowed_vary", "same_protocol", "limitations",
    }
    if not isinstance(data, dict) or set(data) != expected:
        fail("Contract schema keys invalid")
    if data["schema_version"] != 1:
        fail("Unsupported contract schema version")
    if not isinstance(data["name"], str) or not data["name"].strip():
        fail("Contract must have a name")
    if not isinstance(data["purpose"], str) or not data["purpose"].strip():
        fail("Contract must state its purpose")
    if not isinstance(data["limitations"], str) or not data["limitations"].strip():
        fail("Contract must explicitly state its limitations")
    if type(data["same_protocol"]) is not bool:
        fail("same_protocol must be boolean")
    equal = data["required_equal"]
    vary = data["allowed_vary"]
    if (not isinstance(equal, list) or not 1 <= len(equal) <= 25
            or not isinstance(vary, list) or len(vary) > 25):
        fail("Contract fields must be limited lists")
    for item in equal + vary:
        if not isinstance(item, str) or not DIMENSION.fullmatch(item):
            fail("Invalid comparison dimension")
    if len(set(equal + vary)) != len(equal + vary):
        fail("Duplicate or contradictory comparison dimensions")
    return data, file


def run_context(root, run_id, source_ref):
    issues = []
    obj = rk_science.load(root, run_id)
    if obj["kind"] != "run":
        fail("Comparison accepts two scientific Run IDs only")
    try:
        rk_science.validate(root, obj, source_ref)
    except (ValueError, KeyError, TypeError) as exc:
        issues.append(f"{run_id}: invalid/stale run record: {exc}")
    if obj.get("status") != "sealed":
        issues.append(f"{run_id}: Run is not sealed")
    refs = [
        link["target"] for link in obj.get("links", [])
        if isinstance(link, dict) and link.get("relation") == "follows"
    ]
    protocol_id = None
    if len(refs) != 1:
        issues.append(f"{run_id}: requires exactly one follows Protocol")
    else:
        protocol_id = refs[0]
        try:
            protocol = rk_science.load(root, protocol_id)
            rk_science.validate(root, protocol, source_ref)
            if protocol["status"] != "frozen":
                issues.append(f"{run_id}: Protocol is not frozen")
        except (ValueError, KeyError, TypeError) as exc:
            issues.append(f"{run_id}: invalid/stale Protocol: {exc}")
    return obj, protocol_id, issues


def check(args, root, source_ref):
    contract, path = contract_from_repo(root, args.contract)
    left, lp, left_issues = run_context(root, args.left, source_ref)
    right, rp, right_issues = run_context(root, args.right, source_ref)

    mismatches, unknown = [], left_issues + right_issues
    if args.left == args.right:
        unknown.append("Comparing a Run with itself does not establish a comparative result")
    if contract["same_protocol"]:
        if lp and rp and lp != rp:
            mismatches.append({
                "field": "protocol", "left": lp, "right": rp,
                "reason": "comparison contract requires one shared frozen Protocol",
            })
        elif not lp or not rp:
            unknown.append("Cannot verify shared Protocol")
    else:
        unknown.append(
            "Different Protocols are not shown equivalent by metadata alone; "
            "independent protocol equivalence review is required"
        )

    ldesign, rdesign = left.get("design"), right.get("design")
    if not isinstance(ldesign, dict) or not isinstance(rdesign, dict):
        unknown.append("Both Runs need structured design metadata")
        ldesign = ldesign if isinstance(ldesign, dict) else {}
        rdesign = rdesign if isinstance(rdesign, dict) else {}

    matching = []
    for dim in contract["required_equal"]:
        a, b = ldesign.get(dim), rdesign.get(dim)
        if not isinstance(a, str) or not a.strip() or not isinstance(b, str) or not b.strip():
            unknown.append(f"Missing mandatory comparison dimension: {dim}")
        elif a != b:
            mismatches.append({"field": dim, "left": a, "right": b,
                               "reason": "declared values differ"})
        else:
            matching.append(dim)

    varied = []
    for dim in contract["allowed_vary"]:
        a, b = ldesign.get(dim), rdesign.get(dim)
        if isinstance(a, str) and isinstance(b, str) and a.strip() and b.strip():
            varied.append({"field": dim, "left": a, "right": b})
        else:
            unknown.append(f"Declared variable {dim} is unspecified in one Run")

    status = (
        "incompatible" if mismatches
        else "insufficient_evidence" if unknown
        else "compatible_on_declared_dimensions"
    )
    report = {
        "status": status,
        "contract": str(path.relative_to(root)),
        "contract_name": contract["name"],
        "runs": [args.left, args.right],
        "snapshot_sha256": {
            "contract": hashlib.sha256(path.read_bytes()).hexdigest(),
            "left_run": hashlib.sha256(rk_science.path_for(root, args.left).read_bytes()).hexdigest(),
            "right_run": hashlib.sha256(rk_science.path_for(root, args.right).read_bytes()).hexdigest(),
            "left_protocol": (
                hashlib.sha256(rk_science.path_for(root, lp).read_bytes()).hexdigest()
                if lp and rk_science.path_for(root, lp).is_file() else None
            ),
            "right_protocol": (
                hashlib.sha256(rk_science.path_for(root, rp).read_bytes()).hexdigest()
                if rp and rk_science.path_for(root, rp).is_file() else None
            ),
        },
        "matched_dimensions": matching,
        "varied_dimensions": varied,
        "mismatches": mismatches,
        "unknowns": unknown,
        "safe_to_claim_scientific_validity": False,
        "interpretation": (
            "This checker only compares declared metadata and source-linked "
            "record states. It does not establish causal validity, data "
            "authenticity, correct scoring, or sufficient statistical evidence."
        ),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return RESULT_CODES[status]
