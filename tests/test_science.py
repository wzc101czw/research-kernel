"""Scientific-object invariants and abuse/boundary cases."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1]
MODULES = ('rk.py', 'rk_assets.py', 'rk_science.py', 'rk_context.py', 'rk_intake.py')


class ScientificTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)/'project'
        self.root.mkdir()
        for name in MODULES:
            shutil.copyfile(SRC/name, self.root/name)
        self.cli('init')

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args, ok=True, input_text=''):
        p = subprocess.run([sys.executable, '-S', 'rk.py', *args], cwd=self.root,
                           capture_output=True, text=True, input=input_text, timeout=15)
        if ok:
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        else:
            self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        return p.stdout.strip(), p

    def seed(self):
        rq, _ = self.cli('science', 'new', 'question', '--title', 'Does context matter?')
        h1, _ = self.cli('science', 'new', 'hypothesis', '--title', 'Cache reduces errors',
                         '--link', 'addresses', rq)
        h2, _ = self.cli('science', 'new', 'hypothesis', '--title', 'Budget explains errors',
                         '--link', 'addresses', rq, '--link', 'competes_with', h1)
        st, _ = self.cli('science', 'new', 'study', '--title', 'Controlled comparison',
                         '--mode', 'empirical', '--link', 'addresses', rq)
        p, _ = self.cli('science', 'new', 'protocol', '--title', 'Frozen evaluation plan',
                        '--phase', 'confirmatory', '--link', 'for_study', st,
                        '--link', 'tests', h1)
        return rq, h1, h2, st, p

    def fill_protocol(self, protocol):
        for field, content in {
            'variables': 'context loading style', 'controls': 'model, budget, toolkit',
            'outcomes': 'task success and failures', 'analysis_plan': 'paired comparison',
            'stopping_rule': 'all predetermined tasks processed',
        }.items():
            self.cli('science', 'set', protocol, '--key', 'design.'+field,
                     '--value', content, '--reason', 'preregister')

    def test_scientific_lifecycle(self):
        _rq, _h1, _h2, study, protocol = self.seed()
        self.cli('science', 'freeze', protocol, '--reviewed-by', 'Researcher', ok=False)
        self.fill_protocol(protocol)
        self.cli('science', 'freeze', protocol, '--reviewed-by', 'Researcher')
        self.cli('science', 'set', protocol, '--key', 'design.outcomes',
                 '--value', 'post hoc ranking', '--reason', 'change', ok=False)
        amended, _ = self.cli('science', 'amend', protocol, '--reason', 'additional condition')
        self.assertNotEqual(amended, protocol)
        old = json.loads((self.root/'science/protocols'/f'{protocol}.json').read_text())
        new = json.loads((self.root/'science/protocols'/f'{amended}.json').read_text())
        self.assertEqual(old['status'], 'frozen')
        self.assertEqual(new['status'], 'draft')
        self.assertTrue(any(l['target'] == protocol and l['relation'] == 'amends' for l in new['links']))
        self.cli('science', 'new', 'run', '--title', 'Not yet allowed',
                 '--link', 'follows', amended, ok=False)
        run, _ = self.cli('science', 'new', 'run', '--title', 'Run with frozen protocol',
                          '--link', 'follows', protocol)
        obs, _ = self.cli('science', 'new', 'observation', '--title', 'Measurements',
                          '--link', 'produced_by', run)
        analysis, _ = self.cli('science', 'new', 'analysis', '--title', 'Paired estimate',
                               '--link', 'uses_observation', obs)
        rev, _ = self.cli('science', 'new', 'review', '--title', 'Independent review',
                          '--link', 'reviews', analysis)
        self.cli('science', 'finalize', rev, '--reviewer', 'Reviewer',
                 '--decision', 'inconclusive', '--reason', 'Need more independent tasks')
        self.cli('science', 'set', rev, '--key', 'summary', '--value', 'pretend accepted',
                 '--reason', 'unsafe', ok=False)
        self.cli('science', 'check')
        doctor,_ = self.cli('doctor')
        self.assertIn('errors: 0', doctor)
    def test_invalid_relation_rejected(self):
        _rq, h1, _h2, st, p = self.seed()
        self.cli('science', 'new', 'run', '--title', 'Cannot follow a hypothesis',
                 '--link', 'follows', h1, ok=False)
        self.cli('science', 'new', 'hypothesis', '--title', 'Wrong target',
                 '--link', 'addresses', st, ok=False)
        self.cli('science', 'link', p, '--relation', 'tests', '--to', 'hyp-000000000000',
                 '--reason', 'unknown link', ok=False)
        self.cli('science', 'new', 'study', '--title', 'Invalid mode', '--mode', 'science', ok=False)

    def test_draft_mutation_and_revision(self):
        _rq, _, _, _, p = self.seed()
        self.cli('science', 'set', p, '--key', 'design.outcomes', '--value', 'pass rate',
                 '--reason', 'metric plan', '--expected-revision', '99', ok=False)
        self.cli('science', 'set', p, '--key', 'design.outcomes', '--value', 'pass rate',
                 '--reason', 'metric plan', '--expected-revision', '1')
        self.cli('science', 'set', p, '--key', 'id', '--value', 'hijack',
                 '--reason', 'identity change', ok=False)
        obj = json.loads((self.root/'science/protocols'/f'{p}.json').read_text())
        self.assertEqual(obj['revision'], 2)
        self.assertEqual(obj['design']['outcomes'], 'pass rate')

    def test_provenance_stale(self):
        src = self.root/'knowledge/evidence/notes.md'
        src.write_text('First controlled measurement', encoding='utf-8')
        question, _ = self.cli('science', 'new', 'question', '--title', 'Hypothesis',
                               '--source', 'knowledge/evidence/notes.md')
        self.cli('doctor')
        src.write_text('Modified measurement', encoding='utf-8')
        report, _ = self.cli('doctor', ok=False)
        self.assertIn('STALE scientific source', report)
        obj = json.loads((self.root/'science/questions'/f'{question}.json').read_text())
        self.assertIn('sha256', obj['sources'][0])

    def test_seal_evidence_requires_real_source_and_order(self):
        _rq, _h1, _h2, _study, protocol = self.seed()
        self.fill_protocol(protocol)
        self.cli('science', 'freeze', protocol, '--reviewed-by', 'Researcher')
        run, _ = self.cli('science', 'new', 'run', '--title', 'Source pending',
                          '--link', 'follows', protocol)
        self.cli('science', 'seal', run, '--recorded-by', 'Researcher', ok=False)
        src = self.root/'knowledge/evidence/run-manifest.md'
        src.write_text('Trace hash and environment are pending review', encoding='utf-8')
        record_path = self.root/'science/runs'/f'{run}.json'
        obj = json.loads(record_path.read_text())
        import hashlib
        obj['sources'] = [{'path': 'knowledge/evidence/run-manifest.md',
                           'sha256': hashlib.sha256(src.read_bytes()).hexdigest()}]
        proposal = self.root/'proposal.json'
        proposal.write_text(json.dumps(obj))
        self.cli('science', 'edit', run, '--from-json', str(proposal), '--reason', 'Attach source')
        obs_src = self.root/'knowledge/evidence/observation.md'
        obs_src.write_text('An illustrative observation', encoding='utf-8')
        obs, _ = self.cli('science', 'new', 'observation', '--title', 'Observed value',
                          '--link', 'produced_by', run,
                          '--source', 'knowledge/evidence/observation.md')
        self.cli('science', 'seal', obs, '--recorded-by', 'Researcher', ok=False)
        self.cli('science', 'seal', run, '--recorded-by', 'Researcher')
        self.cli('science', 'seal', obs, '--recorded-by', 'Researcher')
        a_src = self.root/'knowledge/evidence/analysis.md'
        a_src.write_text('Illustrative inference; unconfirmed', encoding='utf-8')
        analysis, _ = self.cli('science', 'new', 'analysis', '--title', 'Interpretation',
                               '--link', 'uses_observation', obs,
                               '--source', 'knowledge/evidence/analysis.md')
        self.cli('science', 'seal', analysis, '--recorded-by', 'Researcher')
        self.cli('science', 'set', analysis, '--key', 'summary', '--value', 'Forged',
                 '--reason', 'unsafe', ok=False)
        self.cli('doctor')

    def test_science_escaped_source(self):
        outside = Path(self.tmp.name)/'private.txt'
        outside.write_text('do not open', encoding='utf-8')
        self.cli('science', 'new', 'question', '--title', 'Escape',
                 '--source', '../private.txt', ok=False)
        link = self.root/'knowledge/evidence/bad.txt'
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        self.cli('science', 'new', 'question', '--title', 'Symlink escape',
                 '--source', 'knowledge/evidence/bad.txt', ok=False)

    def test_context_pack_and_budget(self):
        _, _, _, study, protocol = self.seed()
        self.fill_protocol(protocol)
        self.cli('science', 'freeze', protocol, '--reviewed-by', 'Researcher')
        output, _ = self.cli('context', '--study', study, '--profile', 'research',
                             '--max-chars', '12000',
                             '--manifest-out', '.rk/context/selection.json')
        self.assertIn('Research Context Packet', output)
        self.assertIn('Controlled comparison', output)
        self.assertIn('Frozen evaluation plan', output)
        self.assertLessEqual(len(output), 12000)
        manifest = json.loads((self.root/'.rk/context/selection.json').read_text())
        self.assertEqual(manifest['study'], study)
        self.assertTrue(manifest['selected'])
        self.cli('context', '--study', study, '--max-chars', '20', ok=False)
        self.cli('context', '--study', study, '--manifest-out', 'bad-export.json', ok=False)

    def test_context_explicit_approved_memory(self):
        evidence = self.root/'knowledge/evidence/source.txt'
        evidence.write_text('A reproducibility concern', encoding='utf-8')
        mid, _ = self.cli('memory', 'propose', '--kind', 'failure',
                          '--summary', 'Benchmark seed was missing',
                          '--source', 'knowledge/evidence/source.txt')
        self.cli('context', '--memory', mid, ok=False)
        self.cli('memory', 'accept', mid, input_text='ACCEPT\n')
        out, _ = self.cli('context', '--memory', mid, '--max-chars', '12000')
        self.assertIn('Benchmark seed was missing', out)
        evidence.write_text('Changed original', encoding='utf-8')
        out, p = self.cli('context', '--memory', mid, '--max-chars', '12000')
        self.assertNotIn('Benchmark seed was missing', out)
        self.assertIn('SKIP stale memory', p.stderr)


if __name__ == '__main__':
    unittest.main()
