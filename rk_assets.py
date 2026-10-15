"""Versioned research asset metadata. Never transfers data over the network.

Public API: add_cli(parser), dispatch(args, root, source_ref, load_json, save_json),
            audit(root, source_ref), require_published(root, ref).

A dataset manifest is a pointer, not a dataset downloader or a proof of ownership.
"""
import copy
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

KINDS = ("dataset", "benchmark", "legacy", "paper", "report")
ACCESS = ("public", "restricted", "confidential")
STATUS = ("draft", "published")
RELATIONS = ("uses_dataset", "benchmarked_with", "derived_from", "supersedes", "cites", "related_to")
REF_RE = re.compile(r"^(dataset|benchmark|legacy|paper|report):([a-z][a-z0-9-]{1,62})@([a-z0-9][a-z0-9._-]{0,63})$")
ALIAS_RE = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
HASH_RE = re.compile(r"^[a-f0-9]{64}$")
ALLOWED_URI_SCHEMES = {"store", "s3", "gs", "oss", "ssh", "https"}
STRUCTURAL_FIELDS = {"schema_version", "ref", "kind", "slug", "version", "status", "revision", "created_at", "updated_at", "history"}
FIELDS = STRUCTURAL_FIELDS | {
    "title", "summary", "owner", "license", "access", "citation", "tags",
    "storage", "sources", "relations", "extra",
}
EDITORIAL_FIELDS = {"title", "summary", "tags", "citation"}
SET_FIELDS = {"title", "summary", "owner", "license", "access", "citation"}


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def error(message):
    raise ValueError(message)


def parse_ref(ref):
    match = REF_RE.fullmatch(ref)
    if not match or ".." in match.group(3):
        error("Invalid asset ref; expected kind:slug@version (lowercase, no spaces)")
    return match.groups()


def asset_path(root, ref):
    kind, slug, version = parse_ref(ref)
    path = root / "assets" / "registry" / kind / slug / f"{version}.json"
    if not path.resolve().is_relative_to(root.resolve()):
        error("Asset path escapes repository")
    return path


def read_record(root, ref):
    path = asset_path(root, ref)
    if not path.is_file():
        error(f"Unknown asset: {ref}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("ref") != ref:
        error(f"Corrupt asset metadata: {ref}")
    return data


def require_published(root, ref):
    record = read_record(root, ref)
    if record.get("status") != "published":
        error(f"Asset is not published: {ref}")
    return record


def check_uri(uri):
    if not isinstance(uri, str) or len(uri) > 2048 or not uri.strip():
        error("Storage URI must be a non-empty string <= 2048 characters")
    p = urlsplit(uri)
    if p.scheme not in ALLOWED_URI_SCHEMES or not p.netloc or not p.path or p.path == "/":
        error("Storage URI must use store://, s3://, gs://, oss://, ssh:// or https:// with a path")
    if p.username or p.password or p.query or p.fragment or any(c.isspace() for c in uri):
        error("Storage URI must not contain credentials, query, fragment or spaces")
    if (not re.fullmatch(r"[a-zA-Z0-9.-]+", p.netloc)
            or p.netloc in {".", ".."}):
        error("Storage URI host/bucket/alias is invalid; keep credentials outside Git")
    if any(segment in {".", ".."} for segment in unquote(p.path).split("/")):
        error("Storage URI contains unsafe path traversal")
    if p.scheme == "store" and not ALIAS_RE.fullmatch(p.netloc):
        error("store:// URI must start with a valid local store alias")


def normalize_storage(record):
    storage = record["storage"]
    if storage is None:
        return
    if not isinstance(storage, dict) or set(storage) != {"uri", "sha256", "size_bytes", "object_version"}:
        error("storage must have uri, sha256, size_bytes and object_version")
    check_uri(storage["uri"])
    checksum = storage["sha256"]
    if checksum is not None and (not isinstance(checksum, str) or not HASH_RE.fullmatch(checksum)):
        error("storage.sha256 must be 64 lowercase hex characters or null")
    size = storage["size_bytes"]
    if size is not None and (type(size) is not int or size < 0):
        error("storage.size_bytes must be a non-negative integer or null")
    version_id = storage["object_version"]
    if version_id is not None and (not isinstance(version_id, str) or not version_id.strip() or len(version_id) > 256):
        error("storage.object_version must be a short non-empty string or null")


def validate(root, record, *, source_ref, require_dependencies=True):
    if not isinstance(record, dict) or set(record) != FIELDS:
        error("Asset JSON fields do not match the v0.2 schema")
    kind, slug, version = parse_ref(record["ref"])
    if (record["schema_version"] != 2 or record["kind"] != kind
            or record["slug"] != slug or record["version"] != version):
        error("Asset identity/schema mismatch")
    if type(record["revision"]) is not int or record["revision"] < 1:
        error("revision must be a positive integer")
    if record["status"] not in STATUS:
        error("Asset status must be draft or published")
    for key in ("title", "owner", "license", "summary", "citation"):
        if not isinstance(record[key], str) or len(record[key]) > 10000:
            error(f"{key} must be a string of <= 10000 characters")
    if not record["title"].strip():
        error("Asset title cannot be empty")
    if record["access"] not in ACCESS:
        error("access must be public/restricted/confidential")
    tags = record["tags"]
    if not isinstance(tags, list) or len(tags) > 100 or any(not isinstance(t, str) or not t.strip() or len(t) > 100 for t in tags):
        error("tags must be an array of short nonempty strings")
    if not isinstance(record["extra"], dict):
        error("extra must be a JSON object")
    if kind == "benchmark" and record["extra"].get("scope") not in {"global", "project"}:
        error("benchmark.extra.scope must be 'global' or 'project'")
    for key in ("created_at", "updated_at"):
        if not isinstance(record[key], str) or not record[key]:
            error(f"{key} must be an ISO timestamp string")
    history = record["history"]
    if not isinstance(history, list) or not history or history[-1].get("revision") != record["revision"]:
        error("Asset history must end at the current revision")
    if any(not isinstance(x, dict) for x in history):
        error("Asset history must contain objects")
    normalize_storage(record)
    sources = record["sources"]
    if not isinstance(sources, list):
        error("sources must be a list")
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"path", "sha256"}:
            error("sources entries must have path and sha256")
        if not isinstance(source["path"], str) or not isinstance(source["sha256"], str):
            error("source path/hash must be strings")
        if not HASH_RE.fullmatch(source["sha256"]):
            error("source.sha256 must be 64 lowercase hex characters")
        path = (root / source["path"]).resolve()
        if not path.is_relative_to(root.resolve()):
            error(f"Source path escapes repository: {source['path']}")
        if path != root / source["path"] or source["path"].startswith("/"):
            error(f"Source path must be canonical relative path: {source['path']}")
        # A missing/changed original is an error even if metadata is syntactically valid.
        if require_dependencies:
            fresh = source_small(source["path"], source_ref, root)
            if fresh["sha256"] != source["sha256"]:
                error(f"STALE source: {source['path']}")
    relations = record["relations"]
    if not isinstance(relations, list):
        error("relations must be a list")
    for rel in relations:
        if not isinstance(rel, dict) or set(rel) != {"type", "target"}:
            error("relations entries must have type and target")
        if rel["type"] not in RELATIONS:
            error("Unsupported relation type")
        parse_ref(rel["target"])
        if rel["target"] == record["ref"]:
            error("Cannot link an asset to itself")
        if require_dependencies:
            target = read_record(root, rel["target"])
            if record["status"] == "published" and target["status"] != "published":
                error("Published asset cannot reference an unpublished asset")
    if record["status"] == "published":
        if not record["owner"].strip() or not record["license"].strip():
            error("Published asset must declare owner and license (use 'unknown' only when justified)")
        if kind == "dataset" and (record["storage"] is None or record["storage"]["sha256"] is None):
            error("Published dataset needs a storage URI and SHA-256 (for directory datasets, use a frozen archive or hashed manifest)")
        if kind == "benchmark" and not record["sources"]:
            error("Published benchmark requires at least one hashed definition/protocol file")
        if kind in ("paper", "report", "legacy") and not record["sources"] and not record["storage"]:
            error("Published paper/report/legacy asset requires source files or external storage URI")


def source_small(path, source_ref, root):
    original = (root / path).resolve()
    try:
        relative = original.relative_to(root.resolve())
    except ValueError:
        error("Source must be inside this repository")
    if (not original.is_file() or original.stat().st_size > 5 * 1024 * 1024
            or any(x in (".git", ".rk", "data", "secrets", ".cache") for x in relative.parts)):
        error("Versioned text sources must exist inside Git and be <= 5 MiB, not raw datasets")
    return source_ref(path)


def change(root, ref, proposed, reason, old, source_ref, save_json):
    if not reason or not reason.strip():
        error("A non-empty --reason is required")
    path = asset_path(root, ref)
    fresh = read_record(root, ref)
    if fresh["revision"] != old["revision"]:
        error("Concurrent metadata edit: revision changed; reload before saving")
    if set(proposed) != set(old):
        error("Do not add/remove schema fields; use the 'extra' object for custom metadata")
    forbidden = sorted(k for k in STRUCTURAL_FIELDS if proposed[k] != old[k])
    if forbidden:
        error("Cannot directly edit structural fields: " + ", ".join(forbidden))
    edited = [k for k in proposed if k not in STRUCTURAL_FIELDS and proposed[k] != old[k]]
    if not edited:
        print("No metadata changes")
        return
    if old["status"] == "published":
        non_editorial = set(edited) - EDITORIAL_FIELDS
        # Security emergency: tightening data access never needs a new payload version.
        levels = {"public": 0, "restricted": 1, "confidential": 2}
        access_tightened = (non_editorial == {"access"}
                            and proposed["access"] in levels
                            and levels[proposed["access"]] > levels[old["access"]])
        if non_editorial and not access_tightened:
            error("Published asset is frozen; fork a version for semantic changes. "
                  "Only stricter access restrictions may be edited immediately")
    proposed["revision"] = old["revision"] + 1
    proposed["updated_at"] = timestamp()
    proposed["history"] = old["history"] + [{
        "revision": proposed["revision"], "at": proposed["updated_at"],
        "action": "metadata_edit", "fields": edited, "reason": reason.strip(),
    }]
    validate(root, proposed, source_ref=source_ref)
    save_json(path, proposed)
    print(f"Updated {ref} revision={proposed['revision']}; fields={','.join(edited)}")


def file_store_map(root):
    return root / ".rk" / "stores.local.json"


def store_map(root):
    path = file_store_map(root)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in data.items()):
        error("Local store mapping is invalid")
    return data


def stored_path(root, uri):
    parsed = urlsplit(uri)
    if parsed.scheme != "store":
        error("Not a store:// URI. Supply --file for an externally fetched dataset")
    mapping = store_map(root)
    if parsed.netloc not in mapping:
        error(f"Unknown local store alias: {parsed.netloc}; bind it with `rk.py store bind`")
    base = Path(mapping[parsed.netloc]).expanduser().resolve()
    result = (base / unquote(parsed.path).lstrip("/")).resolve()
    if not result.is_relative_to(base):
        error("Local store path escapes its configured root")
    return result


def hash_file(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def do_new(args, root, source_ref, save_json):
    if not ALIAS_RE.fullmatch(args.slug):
        error("Asset slug must be lowercase kebab-case, 1-32 characters")
    ref = f"{args.kind}:{args.slug}@{args.version}"
    path = asset_path(root, ref)
    if path.exists():
        error(f"Asset already exists: {ref}")
    sources = [source_small(p, source_ref, root) for p in (args.source or [])]
    storage = None
    if args.uri:
        storage = {"uri": args.uri, "sha256": args.sha256,
                   "size_bytes": args.size_bytes, "object_version": args.object_version}
    elif args.sha256 or args.size_bytes is not None or args.object_version:
        error("--sha256/--size-bytes/--object-version require --uri")
    if args.scope and args.kind != "benchmark":
        error("--scope is only valid for benchmarks")
    record = {
        "schema_version": 2, "ref": ref, "kind": args.kind, "slug": args.slug,
        "version": args.version, "status": "draft", "revision": 1,
        "title": args.title, "summary": args.summary, "owner": args.owner,
        "license": args.license, "access": args.access, "citation": args.citation,
        "tags": args.tag or [], "storage": storage, "sources": sources,
        "relations": [], "extra": {"scope": args.scope or "global"} if args.kind == "benchmark" else {},
        "created_at": timestamp(),
        "updated_at": timestamp(), "history": [{
            "revision": 1, "at": timestamp(), "action": "created",
            "fields": [], "reason": "registered by user/agent CLI",
        }],
    }
    validate(root, record, source_ref=source_ref)
    save_json(path, record, new=True)
    print(ref)


def do_edit(args, root, source_ref, save_json):
    old = read_record(root, args.ref)
    if args.expected_revision is not None and args.expected_revision != old["revision"]:
        error("Expected revision mismatch; refresh and retry")
    if args.from_json:
        proposed = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
    else:
        editor = args.editor or os.getenv("VISUAL") or os.getenv("EDITOR") or ("notepad" if os.name == "nt" else "vi")
        cmd = shlex.split(editor)
        if not cmd:
            error("Empty editor command")
        with tempfile.TemporaryDirectory(prefix="rk-edit-") as folder:
            scratch = Path(folder) / "asset.json"
            scratch.write_text(json.dumps(old, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            completed = subprocess.run(cmd + [str(scratch)], check=False)
            if completed.returncode:
                error(f"Editor returned {completed.returncode}; no changes were saved")
            proposed = json.loads(scratch.read_text(encoding="utf-8"))
    if not isinstance(proposed, dict):
        error("Edited metadata must be a JSON object")
    change(root, args.ref, proposed, args.reason, old, source_ref, save_json)


def do_set(args, root, source_ref, save_json):
    old = read_record(root, args.ref)
    if args.expected_revision is not None and args.expected_revision != old["revision"]:
        error("Expected revision mismatch; refresh and retry")
    copy_of_record = copy.deepcopy(old)
    copy_of_record[args.field] = args.value
    change(root, args.ref, copy_of_record, args.reason, old, source_ref, save_json)


def do_link(args, root, source_ref, save_json):
    old = read_record(root, args.ref)
    target = read_record(root, args.to)
    if old["status"] != "draft":
        error("Published asset cannot change relationships; fork a new version")
    if target["ref"] == args.ref:
        error("Self-reference is not allowed")
    proposed = copy.deepcopy(old)
    rel = {"type": args.relation, "target": args.to}
    if rel not in proposed["relations"]:
        proposed["relations"].append(rel)
    change(root, args.ref, proposed, args.reason, old, source_ref, save_json)


def do_publish(args, root, source_ref, save_json):
    old = read_record(root, args.ref)
    if old["status"] != "draft":
        error("Already published")
    if not args.reviewed_by.strip():
        error("Publishing requires a non-empty --reviewed-by (process record, not authentication)")
    new = copy.deepcopy(old)
    new["status"] = "published"
    new["revision"] += 1
    new["updated_at"] = timestamp()
    new["history"].append({"revision": new["revision"], "at": new["updated_at"],
                           "action": "published", "fields": ["status"],
                           "reason": args.reason, "reviewed_by": args.reviewed_by})
    validate(root, new, source_ref=source_ref)
    save_json(asset_path(root, args.ref), new)
    print(f"Published {args.ref}. Declared checksums are not independently verified unless `asset verify` is run.")


def do_fork(args, root, source_ref, save_json):
    old = read_record(root, args.ref)
    if old["status"] != "published":
        error("Only published assets may be forked to a new version")
    kind, slug, _ = parse_ref(args.ref)
    new_ref = f"{kind}:{slug}@{args.version}"
    path = asset_path(root, new_ref)
    if path.exists() or new_ref == args.ref:
        error("New version already exists")
    new = copy.deepcopy(old)
    new.update({"ref": new_ref, "version": args.version, "status": "draft", "revision": 1,
                "created_at": timestamp(), "updated_at": timestamp(),
                "history": [{"revision": 1, "at": timestamp(), "action": "forked",
                             "fields": [], "reason": args.reason, "parent": args.ref}]})
    validate(root, new, source_ref=source_ref)
    save_json(path, new, new=True)
    print(new_ref)


def do_verify(args, root):
    record = read_record(root, args.ref)
    storage = record["storage"]
    if not storage or storage["sha256"] is None:
        error("This asset has no declared storage checksum")
    path = Path(args.file) if args.file else stored_path(root, storage["uri"])
    if not path.is_file():
        error("Data not present as a local file. Obtain it explicitly from your authorized storage provider")
    if storage["size_bytes"] is not None and path.stat().st_size != storage["size_bytes"]:
        error("Size mismatch: local file is not the recorded dataset version")
    if hash_file(path) != storage["sha256"]:
        error("SHA-256 MISMATCH: local data differs from the recorded asset")
    print(f"VERIFIED LOCAL SHA-256: {args.ref} (no metadata changed)")


def do_store(args, root):
    if args.action == "bind":
        if not ALIAS_RE.fullmatch(args.alias):
            error("Store alias must be lowercase kebab-case")
        path = Path(args.path).expanduser().resolve()
        if not path.is_dir():
            error("Local store must be an existing directory")
        stores = store_map(root)
        stores[args.alias] = str(path)
        destination = file_store_map(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(destination.parent, 0o700) if os.name != "nt" else None
        destination.write_text(json.dumps(stores, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if os.name != "nt":
            os.chmod(destination, 0o600)
        print(f"Bound local store '{args.alias}' (mapping is gitignored)")
    elif args.action == "list":
        for alias in sorted(store_map(root)):
            print(f"{alias}: configured locally")


def do_wizard(root, source_ref, save_json):
    """Interactive human metadata intake. Creates a draft, never publishes."""
    def ask(label, default=""):
        suffix = f" [{default}]" if default else ""
        response = input(f"{label}{suffix}: ").strip()
        return response or default

    print("Research Asset Wizard (metadata-only: no dataset is downloaded)")
    kind = ask("Kind (dataset/benchmark/legacy/paper/report)", "dataset")
    if kind not in KINDS:
        error("Unrecognized asset kind")
    slug = ask("Stable slug (lowercase kebab-case)")
    version = ask("Version", "v1")
    title = ask("Human-readable title")
    owner = ask("Responsible owner/lab")
    license_value = ask("License/rights (if uncertain, enter unknown)", "unknown")
    access = ask("Access (public/restricted/confidential)", "restricted")
    summary = ask("Research description (optional)")
    citation = ask("DOI/citation (optional)")
    scope = ask("Benchmark scope (global/project)", "global") if kind == "benchmark" else None
    source = ask("Small repository source file (optional)")
    uri = ask("External data URI (optional; store://, s3://, ...)")
    sha256 = ask("Payload SHA-256 (optional until publishing)") if uri else ""
    byte_count = ask("Payload size in bytes (optional)") if uri else ""
    args = type("WizardArgs", (), {
        "kind": kind, "slug": slug, "version": version, "title": title,
        "summary": summary, "owner": owner, "license": license_value,
        "access": access, "citation": citation, "scope": scope,
        "tag": None, "source": [source] if source else None,
        "uri": uri or None, "sha256": sha256 or None,
        "size_bytes": int(byte_count) if byte_count else None,
        "object_version": None,
    })()
    do_new(args, root, source_ref, save_json)
    print("Draft registered. Review using `asset edit REF --reason ...` before publish.")


def dispatch(args, root, source_ref, load_json, save_json):
    del load_json
    action = args.action
    if action == "new":
        do_new(args, root, source_ref, save_json)
    elif action == "wizard":
        do_wizard(root, source_ref, save_json)
    elif action == "list":
        for path in sorted((root / "assets/registry").glob("*/*/*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            if args.kind is None or record["kind"] == args.kind:
                print(f"{record['ref']}\t{record['status']}\tr{record['revision']}\t{record['title']}")
    elif action == "show":
        print(json.dumps(read_record(root, args.ref), indent=2, ensure_ascii=False))
    elif action == "edit":
        do_edit(args, root, source_ref, save_json)
    elif action == "set":
        do_set(args, root, source_ref, save_json)
    elif action == "link":
        do_link(args, root, source_ref, save_json)
    elif action == "publish":
        do_publish(args, root, source_ref, save_json)
    elif action == "fork":
        do_fork(args, root, source_ref, save_json)
    elif action == "verify":
        do_verify(args, root)
    elif action == "check":
        problems = audit(root, source_ref)
        for p in problems:
            print("ERROR:", p)
        print(f"Asset registry errors: {len(problems)}")
        if problems:
            return 1
    return 0


def audit(root, source_ref):
    failures = []
    folder = root / "assets/registry"
    if not folder.is_dir():
        return ["Missing asset registry: assets/registry"]
    for path in sorted(folder.glob("*/*/*.json")):
        try:
            if not path.resolve().is_relative_to(root.resolve()):
                error("Asset symlink resolves outside repository")
            record = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(record, dict) or asset_path(root, record["ref"]) != path:
                error("Asset ref does not match registry path")
            validate(root, record, source_ref=source_ref)
        except (ValueError, TypeError, KeyError, OSError, AttributeError, RecursionError) as exc:
            failures.append(f"{path.relative_to(root)}: {exc}")
    return failures


def add_cli(sub):
    asset = sub.add_parser("asset", help="versioned scientific asset catalog (metadata only)")
    actions = asset.add_subparsers(dest="action", required=True)

    p = actions.add_parser("new", help="register a human-curated draft asset")
    p.add_argument("kind", choices=KINDS)
    p.add_argument("--slug", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--summary", default="")
    p.add_argument("--scope", choices=("global", "project"), help="benchmark scope")
    p.add_argument("--owner", default="")
    p.add_argument("--license", default="")
    p.add_argument("--access", choices=ACCESS, default="restricted")
    p.add_argument("--citation", default="")
    p.add_argument("--tag", action="append")
    p.add_argument("--source", action="append", help="small tracked source file inside repository")
    p.add_argument("--uri", help="external payload URI; never downloaded by this command")
    p.add_argument("--sha256", help="64-hex digest of frozen payload (declared, not verified)")
    p.add_argument("--size-bytes", type=int)
    p.add_argument("--object-version", help="external provider object version ID")

    actions.add_parser("wizard", help="interactive human metadata registration wizard")

    p = actions.add_parser("list", help="list versioned assets")
    p.add_argument("--kind", choices=KINDS)
    p = actions.add_parser("show", help="print editable JSON metadata")
    p.add_argument("ref")

    p = actions.add_parser("edit", help="edit metadata in your $EDITOR or from JSON file")
    p.add_argument("ref")
    p.add_argument("--reason", required=True)
    p.add_argument("--from-json", help="edited JSON path, useful for GUI/file workflows")
    p.add_argument("--editor", help="editor command, e.g. 'code --wait'")
    p.add_argument("--expected-revision", type=int)

    p = actions.add_parser("set", help="update a simple human-editable metadata field")
    p.add_argument("ref")
    p.add_argument("--field", required=True, choices=sorted(SET_FIELDS))
    p.add_argument("--value", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--expected-revision", type=int)

    p = actions.add_parser("link", help="link draft asset to another versioned asset")
    p.add_argument("ref")
    p.add_argument("--relation", choices=RELATIONS, required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--reason", required=True)

    p = actions.add_parser("publish", help="freeze version-defining metadata after review")
    p.add_argument("ref")
    p.add_argument("--reviewed-by", required=True)
    p.add_argument("--reason", default="human approval")

    p = actions.add_parser("fork", help="create a draft new version; do not rewrite published one")
    p.add_argument("ref")
    p.add_argument("--version", required=True)
    p.add_argument("--reason", required=True)

    p = actions.add_parser("verify", help="SHA-256 check of local payload; never downloads data")
    p.add_argument("ref")
    p.add_argument("--file", help="path to local payload for s3:// / https:// assets")

    actions.add_parser("check", help="validate registry, source hashes and references")

    store = sub.add_parser("store", help="manage local data volume aliases; mapping is ignored by Git")
    store_actions = store.add_subparsers(dest="action", required=True)
    p = store_actions.add_parser("bind", help="bind a store://alias to local directory")
    p.add_argument("alias")
    p.add_argument("--path", required=True)
    store_actions.add_parser("list", help="show configured aliases without exposing paths")
