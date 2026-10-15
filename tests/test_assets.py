"""Integration and abuse-case tests for Asset Registry v0.2."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
DIGEST = hashlib.sha256(b"example data, not a real dataset\n").hexdigest()
DATA = b"example data, not a real dataset\n"


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.root = self.dir / "project"
        self.root.mkdir()
        for name in ("rk.py", "rk_assets.py", "rk_science.py", "rk_context.py", "rk_intake.py", ".gitignore"):
            shutil.copyfile(SOURCE / name, self.root / name)
        self.runcli("init")

    def tearDown(self):
        self.tmp.cleanup()

    def runcli(self, *args, ok=True, stdin=""):
        p = subprocess.run([sys.executable, "-S", "rk.py", *args], cwd=self.root,
                           input=stdin, capture_output=True, text=True, timeout=12)
        if ok:
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        else:
            self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        return p

    def dataset(self, published=False, name="test-corpus", sha=DIGEST, uri="s3://my-bucket/corpus-v1.tar.zst", version="v1"):
        ref = self.runcli("asset", "new", "dataset", "--slug", name,
                          "--version", version, "--title", "测试数据集",
                          "--owner", "Example Lab", "--license", "CC-BY-4.0",
                          "--uri", uri, "--sha256", sha,
                          "--size-bytes", str(len(DATA))).stdout.strip()
        if published:
            self.runcli("asset", "publish", ref, "--reviewed-by", "Lab Member")
        return ref

    def record(self, ref):
        kind, rest = ref.split(":", 1)
        slug, version = rest.split("@", 1)
        return self.root / "assets" / "registry" / kind / slug / (version + ".json")

    def protocol(self):
        path = self.root / "benchmarks/definitions/protocol.md"
        path.write_text("# Eval v1\nMetric: accuracy.\n", encoding="utf-8")
        return path

    def test_emergency_restrict_access_on_published_asset(self):
        ref = self.runcli("asset", "new", "dataset", "--slug", "public-data",
                          "--version", "v1", "--title", "Public set",
                          "--owner", "Lab", "--license", "CC0", "--access", "public",
                          "--uri", "s3://bucket/public-v1.bin", "--sha256", DIGEST).stdout.strip()
        self.runcli("asset", "publish", ref, "--reviewed-by", "Data Custodian")
        self.runcli("asset", "set", ref, "--field", "access", "--value", "confidential",
                    "--reason", "New privacy finding")
        self.assertEqual(json.loads(self.record(ref).read_text())["access"], "confidential")
        self.runcli("asset", "set", ref, "--field", "access", "--value", "public",
                    "--reason", "Unsafe reopening", ok=False)
        self.runcli("doctor")

    def test_editor_integration_and_atomic_validation(self):
        ref = self.dataset()
        editor = self.dir / "research_editor.py"
        editor.write_text("#!/usr/bin/env python3\nimport json, sys\nfrom pathlib import Path\n"
                          "p = Path(sys.argv[1])\nx = json.loads(p.read_text())\n"
                          "x['summary'] = 'Edited in a GUI-like workflow'\n"
                          "p.write_text(json.dumps(x))\n", encoding="utf-8")
        editor.chmod(0o755)
        self.runcli("asset", "edit", ref, "--editor", str(editor),
                    "--reason", "manual editor")
        record = json.loads(self.record(ref).read_text())
        self.assertEqual(record["revision"], 2)
        self.assertIn("GUI-like", record["summary"])
        bad = self.dir / "invalid.json"
        bad.write_text("not json", encoding="utf-8")
        self.runcli("asset", "edit", ref, "--from-json", str(bad),
                    "--reason", "bad JSON", ok=False)
        self.assertEqual(json.loads(self.record(ref).read_text())["revision"], 2)

    def test_large_source_is_rejected(self):
        big = self.root / "research/archive/oversize.md"
        big.parent.mkdir(parents=True, exist_ok=True)
        big.write_bytes(b"x" * (5 * 1024 * 1024 + 1))
        self.runcli("asset", "new", "legacy", "--slug", "big-file", "--version", "v1",
                    "--title", "Forbidden large Git source", "--source",
                    "research/archive/oversize.md", ok=False)

    def test_interactive_registration_wizard(self):
        fields = ["dataset", "wizard-sample", "v3", "Human study", "Research Team",
                  "restricted-use", "restricted", "A manually added dataset", "", "", 
                  "store://lab/manual-v3.bin", DIGEST, str(len(DATA))]
        p = self.runcli("asset", "wizard", stdin="\n".join(fields) + "\n")
        self.assertIn("dataset:wizard-sample@v3", p.stdout)
        manifest = self.record("dataset:wizard-sample@v3")
        data = json.loads(manifest.read_text())
        self.assertEqual(data["status"], "draft")
        self.assertEqual(data["summary"], "A manually added dataset")
        self.runcli("doctor")

    def test_dataset_no_payload_download(self):
        ref = self.dataset()
        self.assertEqual(self.runcli("asset", "show", ref).returncode, 0)
        self.assertFalse((self.root / "data").exists())
        self.assertEqual(json.loads(self.record(ref).read_text())["status"], "draft")
        self.runcli("asset", "check")
        self.runcli("doctor")

    def test_dataset_requires_checksum_to_publish(self):
        ref = self.runcli(
            "asset", "new", "dataset", "--slug", "no-checksum", "--version", "v1",
            "--title", "Missing", "--owner", "Researcher", "--license", "unknown",
            "--uri", "s3://bucket/snapshot.bin").stdout.strip()
        self.runcli("asset", "publish", ref, "--reviewed-by", "Human", ok=False)
        self.assertEqual(json.loads(self.record(ref).read_text())["status"], "draft")

    def test_benchmark_relation_freezes(self):
        ds = self.dataset(published=True)
        self.protocol()
        bm = self.runcli("asset", "new", "benchmark", "--slug", "global-task",
                         "--version", "v1", "--title", "Global Benchmark",
                         "--owner", "Researcher", "--license", "MIT", "--scope", "global",
                         "--source", "benchmarks/definitions/protocol.md").stdout.strip()
        self.runcli("asset", "link", bm, "--relation", "uses_dataset",
                    "--to", ds, "--reason", "pin this data revision")
        self.runcli("asset", "publish", bm, "--reviewed-by", "Committee")
        self.runcli("asset", "link", bm, "--relation", "related_to",
                    "--to", ds, "--reason", "late change", ok=False)
        data = json.loads(self.record(bm).read_text())
        self.assertEqual(data["extra"]["scope"], "global")
        self.assertEqual(data["relations"], [{"type": "uses_dataset", "target": ds}])
        self.runcli("doctor")

    def test_unpublished_dependency_cannot_publish(self):
        ds = self.dataset()
        self.protocol()
        bm = self.runcli("asset", "new", "benchmark", "--slug", "task-v1",
                         "--version", "v1", "--title", "Scoring",
                         "--owner", "Lab", "--license", "MIT",
                         "--source", "benchmarks/definitions/protocol.md").stdout.strip()
        self.runcli("asset", "link", bm, "--relation", "uses_dataset", "--to", ds,
                    "--reason", "link draft dependency")
        self.runcli("asset", "publish", bm, "--reviewed-by", "Human", ok=False)
        self.dataset(published=False, name="other-data")
        self.runcli("doctor")

    def test_metadata_set_and_history(self):
        ref = self.dataset()
        self.runcli("asset", "set", ref, "--field", "summary", "--value", "Updated notes",
                    "--reason", "human corrected description", "--expected-revision", "1")
        data = json.loads(self.record(ref).read_text())
        self.assertEqual(data["revision"], 2)
        self.assertEqual(data["summary"], "Updated notes")
        self.assertEqual(data["history"][-1]["reason"], "human corrected description")
        self.runcli("asset", "set", ref, "--field", "title", "--value", "Wrong revision",
                    "--reason", "stale edit", "--expected-revision", "1", ok=False)
        self.runcli("doctor")

    def test_json_editor_and_immutable_fields(self):
        ref = self.dataset()
        record = json.loads(self.record(ref).read_text())
        inputfile = self.dir / "human-changes.json"
        record["tags"] = ["classification", "image"]
        record["extra"] = {"doi": "10.1234/example", "collection": "demo"}
        inputfile.write_text(json.dumps(record), encoding="utf-8")
        self.runcli("asset", "edit", ref, "--from-json", str(inputfile), "--reason", "human curator")
        edited = json.loads(self.record(ref).read_text())
        self.assertEqual(edited["revision"], 2)
        self.assertEqual(edited["tags"], ["classification", "image"])
        edited["version"] = "v2"
        inputfile.write_text(json.dumps(edited), encoding="utf-8")
        self.runcli("asset", "edit", ref, "--from-json", str(inputfile),
                    "--reason", "trying to rewrite identity", ok=False)
        self.assertEqual(json.loads(self.record(ref).read_text())["version"], "v1")

    def test_publish_editorial_and_semantic_freeze(self):
        ref = self.dataset(published=True)
        self.runcli("asset", "set", ref, "--field", "summary", "--value", "Fixed typo",
                    "--reason", "editorial correction")
        self.runcli("asset", "set", ref, "--field", "access", "--value", "public",
                    "--reason", "unsafe permission change", ok=False)
        edited = json.loads(self.record(ref).read_text())
        edited["storage"]["uri"] = "s3://my-bucket/another-version.bin"
        inputfile = self.dir / "metadata.json"
        inputfile.write_text(json.dumps(edited), encoding="utf-8")
        self.runcli("asset", "edit", ref, "--from-json", str(inputfile),
                    "--reason", "hidden storage change", ok=False)
        self.runcli("doctor")

    def test_fork_preserves_history(self):
        ref = self.dataset(published=True)
        new_ref = self.runcli("asset", "fork", ref, "--version", "v2",
                              "--reason", "New data release").stdout.strip()
        self.assertEqual(new_ref, "dataset:test-corpus@v2")
        self.assertEqual(json.loads(self.record(new_ref).read_text())["status"], "draft")
        self.assertEqual(json.loads(self.record(ref).read_text())["status"], "published")
        self.assertEqual(json.loads(self.record(new_ref).read_text())["history"][0]["parent"], ref)
        self.runcli("doctor")

    def test_store_bind_verify_and_bad_hash(self):
        location = self.dir / "external-storage"
        location.mkdir()
        (location / "frozen.dat").write_bytes(DATA)
        ref = self.dataset(published=True, uri="store://lab/frozen.dat")
        self.runcli("store", "bind", "lab", "--path", str(location))
        self.assertTrue((self.root / ".rk/stores.local.json").exists())
        self.assertIn("VERIFIED LOCAL SHA-256", self.runcli("asset", "verify", ref).stdout)
        (location / "frozen.dat").write_bytes(b"mutated payload")
        self.runcli("asset", "verify", ref, ok=False)
        self.runcli("doctor")  # Metadata remains valid; physical source must be re-verified on demand.

    def test_remote_file_verify_without_fetch(self):
        file = self.dir / "downloaded-on-purpose.bin"
        file.write_bytes(DATA)
        ref = self.dataset(published=True)
        self.runcli("asset", "verify", ref, "--file", str(file))
        file.write_bytes(DATA + b"changed")
        self.runcli("asset", "verify", ref, "--file", str(file), ok=False)

    def test_reject_secret_and_path_traversal_uris(self):
        for bad in (
            "https://host/file?token=secret", "s3://bucket/../private.csv",
            "s3://user:pass@bucket/private.csv", "file:///home/me/private.csv",
            "store://alias/../../etc/passwd",
        ):
            with self.subTest(bad=bad):
                self.runcli("asset", "new", "dataset", "--slug", "bad-location",
                            "--version", "v1", "--title", "Bad",
                            "--uri", bad, "--sha256", DIGEST, ok=False)
        self.runcli("asset", "list")

    def test_source_modified_flags_stale(self):
        protocol = self.protocol()
        self.runcli("asset", "new", "benchmark", "--slug", "test-task",
                    "--version", "v1", "--title", "Protocol",
                    "--owner", "Lab", "--license", "MIT", "--source",
                    "benchmarks/definitions/protocol.md")
        protocol.write_text("Changed metric to ROC-AUC\n", encoding="utf-8")
        self.assertIn("STALE source", self.runcli("doctor", ok=False).stdout)

    def test_invalid_untracked_source_location_and_size(self):
        outside = self.dir / "remote.txt"
        outside.write_text("Hello", encoding="utf-8")
        self.runcli("asset", "new", "paper", "--slug", "external-source",
                    "--version", "v1", "--title", "Outside",
                    "--source", str(outside), ok=False)
        raw = self.root / "data"
        raw.mkdir()
        (raw / "hidden.txt").write_text("Private payload", encoding="utf-8")
        self.runcli("asset", "new", "paper", "--slug", "raw-source",
                    "--version", "v1", "--title", "Ignored",
                    "--source", "data/hidden.txt", ok=False)

    def test_claim_can_pin_a_published_dataset(self):
        ref = self.dataset(published=True)
        source = self.root / "knowledge/evidence/base.md"
        source.write_text("Observation only", encoding="utf-8")
        p = self.runcli("claim", "new", "--statement", "Candidate result",
                        "--source", "knowledge/evidence/base.md", "--asset-ref", ref)
        cid = p.stdout.strip()
        obj = json.loads((self.root / "knowledge/claims" / f"{cid}.json").read_text())
        self.assertEqual(obj["asset_refs"], [ref])
        self.runcli("doctor")
        self.record(ref).unlink()
        self.assertIn("invalid asset ref", self.runcli("doctor", ok=False).stdout)

    def test_git_clone_does_not_download_payload(self):
        if not shutil.which("git"):
            self.skipTest("Git is unavailable")
        raw = self.root / "data"
        raw.mkdir()
        (raw / "large-payload.bin").write_bytes(b"x" * 4096)
        self.dataset(published=True)
        commands = [
            ["git", "init", "-q"], ["git", "add", "."],
            ["git", "-c", "user.name=Researcher", "-c", "user.email=local@example.test",
             "commit", "-q", "-m", "Catalog metadata"],
        ]
        for c in commands:
            p = subprocess.run(c, cwd=self.root, capture_output=True, text=True, timeout=10)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        tracked = subprocess.check_output(["git", "ls-files"], cwd=self.root, text=True)
        self.assertIn("assets/registry/dataset/test-corpus/v1.json", tracked)
        self.assertNotIn("large-payload.bin", tracked)
        clone = self.dir / "fresh-clone"
        p = subprocess.run(["git", "clone", "--quiet", str(self.root), str(clone)],
                           capture_output=True, text=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue((clone / "assets/registry/dataset/test-corpus/v1.json").is_file())
        self.assertFalse((clone / "data/large-payload.bin").exists())
        self.assertEqual(subprocess.run([sys.executable, "-S", "rk.py", "doctor"],
                                        cwd=clone, capture_output=True, timeout=10).returncode, 0)


if __name__ == "__main__":
    unittest.main()
