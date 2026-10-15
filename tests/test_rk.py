import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "rk.py"


class KernelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "project"
        self.root.mkdir()
        shutil.copyfile(SRC, self.root / "rk.py")
        shutil.copyfile(SRC.with_name("rk_assets.py"), self.root / "rk_assets.py")
        self.call("init", ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, *args, ok=True, stdin=""):
        p = subprocess.run(
            [sys.executable, "-S", "rk.py", *args], cwd=self.root,
            input=stdin, text=True, capture_output=True, timeout=15
        )
        if ok:
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        else:
            self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        return p

    def evidence(self):
        p = self.root / "knowledge/evidence/实验结论.txt"
        p.write_text("Observed 42 in a synthetic example.\n", encoding="utf-8")
        return p

    def test_bootstrap_idempotent(self):
        self.call("doctor")
        target = self.root / "AGENTS.md"
        target.write_text("custom rules", encoding="utf-8")
        self.call("init")
        self.assertEqual(target.read_text(encoding="utf-8"), "custom rules")

    def test_task_handoff_context(self):
        tid = self.call("task", "new", "--title", "模型评测", "--next", "复查基线").stdout.strip()
        self.call("task", "set", tid, "--status", "blocked",
                  "--next", "等待证据", "--note", "实验日志未上传")
        path = self.call("handoff", tid, "--note", "cross-platform handoff").stdout.strip()
        text = (self.root / path).read_text(encoding="utf-8")
        self.assertIn("等待证据", text)
        self.assertIn("cross-platform handoff", text)
        result = self.call("context", "--task", tid, "--max-chars", "12000")
        self.assertIn("模型评测", result.stdout)
        self.assertTrue(result.stdout.startswith("### AGENTS.md\n"))
        self.assertLessEqual(len(result.stdout.rstrip("\n")), 12000)
        self.call("context", "--task", tid, "--max-chars", "100", ok=False)

    def test_cross_directory_handoff_restore(self):
        tid = self.call("task", "new", "--title", "Persistent experiment",
                        "--next", "Independent review").stdout.strip()
        self.call("handoff", tid, "--note", "Keep this checkpoint")
        clone = Path(self.tmp.name) / "fresh-copy"
        shutil.copytree(self.root, clone)
        restored = subprocess.run(
            [sys.executable, "-S", "rk.py", "context", "--task", tid],
            cwd=clone, text=True, capture_output=True, timeout=15
        )
        self.assertEqual(restored.returncode, 0, restored.stderr)
        self.assertIn("Persistent experiment", restored.stdout)
        self.assertIn("Keep this checkpoint", restored.stdout)

    def test_task_blank_rejected(self):
        self.call("task", "new", "--title", "   ", "--next", "run", ok=False)
        self.call("task", "new", "--title", "hi", "--next", " ", ok=False)

    def test_claim_provenance_detects_stale(self):
        path = self.evidence()
        cid = self.call("claim", "new", "--statement", "Unverified speedup",
                        "--source", "knowledge/evidence/实验结论.txt").stdout.strip()
        self.call("doctor")
        self.call("claim", "challenge", cid, "--reason", "Potential confounder")
        obj = json.loads((self.root / "knowledge/claims" / f"{cid}.json").read_text())
        self.assertEqual(obj["status"], "disputed")
        path.write_text("Changed after citation", encoding="utf-8")
        result = self.call("doctor", ok=False)
        self.assertIn("STALE source", result.stdout)

    def test_missing_source_rejected(self):
        self.call("claim", "new", "--statement", "Claim",
                  "--source", "knowledge/evidence/not-found.txt", ok=False)

    def test_path_traversal_rejected(self):
        outside = Path(self.tmp.name) / "private.txt"
        outside.write_text("secret", encoding="utf-8")
        self.call("claim", "new", "--statement", "Leak",
                  "--source", "../private.txt", ok=False)
        self.call("handoff", "../private", ok=False)

    def test_symlink_escape_rejected(self):
        outside = Path(self.tmp.name) / "private.txt"
        outside.write_text("secret", encoding="utf-8")
        link = self.root / "knowledge/evidence/link.txt"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        self.call("claim", "new", "--statement", "Symlink",
                  "--source", "knowledge/evidence/link.txt", ok=False)

    def test_memory_review_flow(self):
        self.evidence()
        mid = self.call("memory", "propose", "--kind", "failure",
                        "--summary", "Missing baseline repetition",
                        "--source", "knowledge/evidence/实验结论.txt").stdout.strip()
        self.assertTrue((self.root / "memory/inbox" / f"{mid}.json").is_file())
        self.call("memory", "accept", mid, stdin="NO\n", ok=False)
        self.assertTrue((self.root / "memory/inbox" / f"{mid}.json").exists())
        self.call("memory", "accept", mid, stdin="ACCEPT\n")
        self.assertFalse((self.root / "memory/inbox" / f"{mid}.json").exists())
        accepted = json.loads((self.root / "memory/compacted" / f"{mid}.json").read_text())
        self.assertEqual(accepted["status"], "accepted")
        self.call("doctor")

    def test_doctor_handles_bad_records(self):
        path = self.root / "memory/inbox" / "memory-123456789abc.json"
        path.write_text("[]", encoding="utf-8")
        p = self.call("doctor", ok=False)
        self.assertIn("Record must contain a JSON object", p.stdout)
        path.write_text("{not json", encoding="utf-8")
        self.call("doctor", ok=False)

    def test_no_false_verified(self):
        self.evidence()
        cid = self.call("claim", "new", "--statement", "Model is better",
                        "--source", "knowledge/evidence/实验结论.txt").stdout.strip()
        record = json.loads((self.root / "knowledge/claims" / f"{cid}.json").read_text())
        self.assertEqual(record["status"], "provisional")
        self.assertIn("sha256", record["sources"][0])

    def test_doctor_rejects_malformed_skill(self):
        folder = self.root / "methods/skills/example"
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text(
            "---\nname: wrong\ndescription: Test\n---\n# Body\n",
            encoding="utf-8",
        )
        p = self.call("doctor", ok=False)
        self.assertIn("Invalid Skill name", p.stdout)

    def test_missing_evidence_after_memory_proposal(self):
        path = self.evidence()
        mid = self.call("memory", "propose", "--summary", "Check",
                        "--source", "knowledge/evidence/实验结论.txt").stdout.strip()
        path.unlink()
        self.call("memory", "accept", mid, stdin="ACCEPT\n", ok=False)
        self.assertIn("Invalid source", self.call("doctor", ok=False).stdout)


if __name__ == "__main__":
    unittest.main()
