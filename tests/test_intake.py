"""Legacy inventory must remain read-only and abstain from content inference."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
MODULES = ('rk.py', 'rk_assets.py', 'rk_science.py', 'rk_context.py', 'rk_intake.py')


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)/'project'
        self.root.mkdir()
        for name in MODULES:
            shutil.copyfile(SRC/name, self.root/name)
        self.cmd('init')

    def tearDown(self):
        self.tmp.cleanup()

    def cmd(self, *args, ok=True):
        p = subprocess.run([sys.executable, '-S', 'rk.py', *args], cwd=self.root,
                           capture_output=True, text=True, timeout=20)
        self.assertEqual(p.returncode == 0, ok, p.stdout + p.stderr)
        return p.stdout, p.stderr

    def test_tree_filenames_only_and_security(self):
        listing = '''./Workspace
├── .git/
│   └── objects/
│       └── pack/
│           └── huge.pack
├── api_key.txt
├── data/
│   └── private.parquet
├── analysis/
│   ├── preds_trial.jsonl
│   └── results_trial.json
├── memory/
│   └── compact.md
└── solver/
    └── main.py
'''
        path = Path(self.tmp.name)/'tree.txt'
        path.write_text(listing, encoding='utf-8')
        out, _ = self.cmd('intake', 'tree', str(path))
        obj = json.loads((self.root/'.rk/intake/latest/inventory.json').read_text())
        self.assertEqual(obj['file_count'], 7)
        self.assertEqual(obj['groups']['secret_candidate']['count'], 1)
        self.assertIn('api_key.txt', obj['risk_paths'])
        self.assertEqual(obj['groups']['prediction_evaluation']['count'], 2)
        self.assertEqual(obj['groups']['dataset_candidate']['count'], 1)
        self.assertEqual(obj['inventory_type'], 'path_only')
        self.assertIn('READ-ONLY', out)
        self.assertFalse((self.root/'api_key.txt').exists())
        self.assertFalse((self.root/'data').exists())

    def test_tree_path_traversal_rejected(self):
        t = Path(self.tmp.name)/'evil.txt'
        t.write_text('./root\n└── ../escape.txt\n', encoding='utf-8')
        self.cmd('intake', 'tree', str(t), ok=False)

    def test_directory_scan_does_not_read_secret(self):
        target = Path(self.tmp.name)/'legacy'
        (target/'data').mkdir(parents=True)
        (target/'data/raw.parquet').write_bytes(b'NOT-AN-EXPERIMENT')
        (target/'api_key.txt').write_text('FAKE-SECRET-DO-NOT-STORE', encoding='utf-8')
        self.cmd('intake', 'directory', str(target))
        obj = json.loads((self.root/'.rk/intake/latest/inventory.json').read_text())
        self.assertEqual(obj['file_count'], 2)
        self.assertNotIn('FAKE-SECRET', json.dumps(obj))
        self.assertIn('api_key.txt', obj['risk_paths'])
        self.assertEqual((target/'api_key.txt').read_text(), 'FAKE-SECRET-DO-NOT-STORE')


if __name__ == '__main__':
    unittest.main()
