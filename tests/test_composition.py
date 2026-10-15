"""Advisory composition and explicit context dependency regression tests."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
MODULES = ("rk.py", "rk_assets.py", "rk_science.py", "rk_context.py",
           "rk_intake.py", "rk_composition.py", "rk_execution.py")
DIMS = {
    "dataset_version": "dataset-a@v1",
    "evaluation_split": "test-128",
    "metric_definition": "task-success-rate-v1",
    "scorer_version": "scorer-1.0",
    "compute_budget": "10000-tokens",
    "context_strategy": "hierarchical-cache",
}


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "project"
        self.root.mkdir()
        for name in MODULES:
            shutil.copyfile(SRC / name, self.root / name)
        self.cli("init", status=0)
        contract_dir = self.root / "science/contracts"
        contract_dir.mkdir(exist_ok=True)
        shutil.copyfile(SRC / "science/contracts/benchmark-comparison.v1.json",
                        contract_dir / "benchmark-comparison.v1.json")
        evidence = self.root / "knowledge/evidence/illustrative-run.txt"
        evidence.write_text("Synthetic fixture. No real experiment was performed.\n", encoding="utf-8")
        self.study, _ = self.cli("science", "new", "study", "--title", "Run compatibility",
                                 "--mode", "empirical")
        self.protocol, _ = self.cli("science", "new", "protocol",
                                    "--title", "Frozen illustrative protocol",
                                    "--phase", "exploratory",
                                    "--link", "for_study", self.study)
        self.cli("science", "freeze", self.protocol, "--reviewed-by", "Synthetic test reviewer")

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args, status=0):
        p = subprocess.run([sys.executable, "-S", "rk.py", *args], cwd=self.root,
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(p.returncode, status, p.stdout + "\n" + p.stderr)
        return p.stdout.strip(), p

    def make_run(self, strategy="hierarchical-cache", replace=None, sealed=True):
        values = dict(DIMS)
        values["context_strategy"] = strategy
        if replace:
            values.update(replace)
        run, _ = self.cli("science", "new", "run", "--title", "Synthetic Run",
                          "--link", "follows", self.protocol,
                          "--source", "knowledge/evidence/illustrative-run.txt")
        source = self.root / "science/runs" / (run + ".json")
        obj = json.loads(source.read_text(encoding="utf-8"))
        obj["design"] = values
        proposal = self.root / "proposal.json"
        proposal.write_text(json.dumps(obj), encoding="utf-8")
        self.cli("science", "edit", run, "--from-json", str(proposal),
                 "--reason", "Attach comparison dimensions")
        if sealed:
            self.cli("science", "seal", run, "--recorded-by", "Synthetic fixture")
        return run

    def test_compatible_metadata_not_scientific_proof(self):
        a = self.make_run()
        b = self.make_run(strategy="full-context")
        text, p = self.cli("compose", "check", a, b)
        report = json.loads(text)
        self.assertEqual(report["status"], "compatible_on_declared_dimensions")
        self.assertFalse(report["safe_to_claim_scientific_validity"])
        self.assertEqual(len(report["matched_dimensions"]), 5)
        self.assertEqual(len(report["snapshot_sha256"]["contract"]), 64)
        self.assertEqual(report["snapshot_sha256"]["left_protocol"],
                         report["snapshot_sha256"]["right_protocol"])
        self.cli("doctor")

    def test_mismatched_scorer_is_incompatible(self):
        a = self.make_run()
        b = self.make_run(replace={"scorer_version": "scorer-2.0"})
        report, _ = self.cli("compose", "check", a, b, status=2)
        self.assertEqual(json.loads(report)["mismatches"][0]["field"], "scorer_version")

    def test_missing_required_dimension_is_unknown(self):
        a = self.make_run()
        b = self.make_run(replace={"compute_budget": ""})
        report, _ = self.cli("compose", "check", a, b, status=3)
        self.assertIn("compute_budget", " ".join(json.loads(report)["unknowns"]))

    def test_unsealed_run_is_unknown(self):
        a = self.make_run()
        b = self.make_run(sealed=False)
        report, _ = self.cli("compose", "check", a, b, status=3)
        self.assertIn("not sealed", " ".join(json.loads(report)["unknowns"]))

    def test_reject_external_contract_path(self):
        a = self.make_run()
        b = self.make_run(strategy="full-context")
        self.cli("compose", "check", a, b, "--contract",
                 "../secret-logic.json", status=1)

    def test_context_pins_frozen_protocol_and_manifest(self):
        text, _ = self.cli("context", "--study", self.study, "--protocol",
                           self.protocol, "--profile", "audit", "--max-chars",
                           "14000", "--manifest-out", ".rk/context/decision.json")
        self.assertIn("PINNED FROZEN PROTOCOL", text)
        self.assertIn(self.protocol, text)
        manifest = json.loads(
            (self.root / ".rk/context/decision.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["protocol"], self.protocol)
        self.assertEqual(manifest["context_scope"],
                         "protocol_pinned_not_scientifically_validated")
        self.assertTrue(any(x["name"] == self.protocol and x["required"]
                            for x in manifest["selected"]))

    def test_context_does_not_silently_omit_required_protocol(self):
        self.cli("context", "--study", self.study, "--protocol", self.protocol,
                 "--max-chars", "150", status=1)

    def test_context_rejects_unrelated_or_missing_study(self):
        self.cli("context", "--protocol", self.protocol, status=1)
        other, _ = self.cli("science", "new", "study", "--title", "Other study",
                            "--mode", "empirical")
        self.cli("context", "--study", other, "--protocol", self.protocol, status=1)

    def test_navigation_mode_is_explicitly_non_decisional(self):
        text, _ = self.cli("context", "--study", self.study, "--profile", "research",
                           "--max-chars", "14000")
        self.assertIn("NAVIGATION ONLY", text)


if __name__ == "__main__":
    unittest.main()
