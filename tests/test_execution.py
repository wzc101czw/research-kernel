"""v0.4 integration: real CLI execution with tiny synthetic JSONL inputs."""
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
MODULES = ('rk.py', 'rk_assets.py', 'rk_science.py', 'rk_context.py',
           'rk_intake.py', 'rk_execution.py', 'rk_composition.py')


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'research-kernel'
        self.root.mkdir()
        for module in MODULES:
            shutil.copy2(SOURCE / module, self.root / module)
        shutil.copytree(SOURCE / 'methods/skills', self.root / 'methods/skills')
        (self.root / 'examples/fixtures').mkdir(parents=True)
        (self.root / 'examples/fixtures/one.jsonl').write_text(
            '{"success": true}\n{"success": false}\n{"success": true}\n', encoding='utf-8')
        (self.root / 'examples/fixtures/two.jsonl').write_text(
            '{"success": true}\n{"success": true}\n{"success": true}\n', encoding='utf-8')
        self.cli('init')
        self.study, _ = self.cli('science', 'new', 'study', '--title', 'Synthetic study',
                                 '--mode', 'empirical')
        self.protocol, _ = self.cli('science', 'new', 'protocol', '--title', 'Test protocol',
                                    '--phase', 'exploratory', '--link', 'for_study', self.study)
        self.cli('science', 'freeze', self.protocol, '--reviewed-by', 'Test author')
        self.plan, _ = self.cli('plan', 'create', '--title', 'Compare two toy results',
                                '--study', self.study, '--protocol', self.protocol,
                                '--left', 'examples/fixtures/one.jsonl',
                                '--right', 'examples/fixtures/two.jsonl')

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args, code=0):
        p = subprocess.run([sys.executable, '-S', 'rk.py', *args], cwd=self.root,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
        self.assertEqual(p.returncode, code, p.stdout + '\n' + p.stderr)
        return p.stdout.strip(), p

    def freeze(self):
        self.cli('plan', 'freeze', self.plan, '--reviewed-by', 'Test author')

    def plan_path(self):
        return self.root / 'plans/specs' / (self.plan + '.json')

    def load_draft(self):
        return json.loads(self.plan_path().read_text(encoding='utf-8'))

    def replace_draft(self, data):
        self.plan_path().write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')

    def test_plan_checks_and_dry_run(self):
        out, _ = self.cli('plan', 'check', self.plan)
        self.assertFalse(json.loads(out)['frozen'])
        self.freeze()
        out, _ = self.cli('plan', 'dry-run', self.plan)
        obj = json.loads(out)
        self.assertEqual([x['step'] for x in obj['would_execute']], ['baseline', 'candidate', 'compare'])
        self.assertTrue(obj['no_side_effects'])
        self.assertFalse((self.root / '.rk/executions').exists())

    def test_run_pause_resume_and_export_to_git(self):
        self.freeze()
        out, _ = self.cli('plan', 'run', self.plan, '--max-steps', '1')
        paused = json.loads(out)
        self.assertEqual(paused['status'], 'paused')
        execution = paused['execution_id']
        out, _ = self.cli('plan', 'resume', execution)
        self.assertEqual(json.loads(out)['status'], 'completed')
        ledger, _ = self.cli('plan', 'status', execution)
        self.assertTrue(all(x['status'] == 'completed' for x in json.loads(ledger)['steps'].values()))
        path, _ = self.cli('plan', 'export', execution, '--recorded-by', 'Lab reviewer')
        exported = json.loads((self.root / path).read_text(encoding='utf-8'))
        results = {x['id']: x['summary'] for x in exported['step_outputs']}
        self.assertEqual(results['baseline']['trials'], 3)
        self.assertAlmostEqual(results['baseline']['success_rate'], 2/3)
        self.assertEqual(results['candidate']['success_rate'], 1.0)
        self.assertAlmostEqual(results['compare']['delta'], 1/3)
        self.assertEqual(exported['scientific_validity'], 'not_assessed')
        self.assertTrue((self.root / '.rk/executions' / self.plan / execution).exists())
        self.cli('doctor')
        run, _ = self.cli('science', 'new', 'run', '--title', 'Linked computation',
                          '--link', 'follows', self.protocol, '--source', path)
        self.cli('science', 'seal', run, '--recorded-by', 'Lab reviewer')
        self.cli('doctor')

    def test_resume_refuses_modified_completed_result(self):
        self.freeze()
        paused, _ = self.cli('plan', 'run', self.plan, '--max-steps', '1')
        execution = json.loads(paused)['execution_id']
        target = self.root / '.rk/executions' / self.plan / execution / 'steps/baseline.json'
        target.write_text('{"tampered": true}', encoding='utf-8')
        _, result = self.cli('plan', 'resume', execution, code=1)
        self.assertIn('altered', result.stderr)

    def test_edit_frozen_plan_is_detected(self):
        self.freeze()
        item = self.load_draft()
        item['need'] = 'Altered after review'
        self.replace_draft(item)
        _, result = self.cli('plan', 'run', self.plan, code=1)
        self.assertIn('changed after review', result.stderr)
        self.cli('doctor', code=1)

    def test_source_mutation_blocks_preflight(self):
        self.freeze()
        (self.root / 'examples/fixtures/one.jsonl').write_text('{"success": true}\n', encoding='utf-8')
        self.cli('plan', 'dry-run', self.plan, code=1)
        self.cli('plan', 'run', self.plan, code=1)

    def test_protocol_change_blocks_execution(self):
        self.freeze()
        protocol = self.root / 'science/protocols' / (self.protocol + '.json')
        content = json.loads(protocol.read_text(encoding='utf-8'))
        content['title'] = 'Modified externally'
        protocol.write_text(json.dumps(content), encoding='utf-8')
        self.cli('plan', 'run', self.plan, code=1)

    def test_policy_change_blocks_execution(self):
        self.freeze()
        with (self.root / 'workspace/policies.md').open('a') as f:
            f.write('\nNew global constraint.\n')
        _, p = self.cli('plan', 'run', self.plan, code=1)
        self.assertIn('authority changed', p.stderr)

    def test_step_context_is_bounded_and_pinned(self):
        self.freeze()
        text, _ = self.cli('plan', 'context', self.plan, '--step', 'baseline',
                           '--manifest-out', '.rk/context/baseline.json')
        self.assertIn(self.protocol, text)
        self.assertIn(self.study, text)
        manifest = json.loads((self.root / '.rk/context/baseline.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['scope'], 'required_dependencies_only')
        self.assertTrue(manifest['context_sha256'])
        self.cli('plan', 'context', self.plan, '--step', 'baseline', '--max-chars', '1200', code=1)
        self.cli('plan', 'context', self.plan, '--step', 'baseline',
                 '--manifest-out', 'memory/my-summary.json', code=1)

    def test_cycle_rejected(self):
        spec = self.load_draft()
        spec['steps'][0]['depends_on'] = ['compare']
        self.replace_draft(spec)
        self.cli('plan', 'check', self.plan, code=1)

    def test_arbitrary_shell_operation_rejected(self):
        spec = self.load_draft()
        spec['steps'][0]['op'] = 'shell'
        self.replace_draft(spec)
        self.cli('plan', 'freeze', self.plan, '--reviewed-by', 'X', code=1)

    def test_comparison_requires_two_distinct_producers(self):
        spec = self.load_draft()
        spec['steps'][2]['inputs']['right']['step'] = 'baseline'
        self.replace_draft(spec)
        self.cli('plan', 'check', self.plan, code=1)

    def test_confidential_path_names_rejected(self):
        path = self.root / 'api_key.txt'
        path.write_text('FAKE_TEST_KEY', encoding='utf-8')
        self.cli('plan', 'create', '--title', 'Secret', '--study', self.study,
                 '--protocol', self.protocol, '--left', 'api_key.txt',
                 '--right', 'examples/fixtures/two.jsonl', code=1)

    def test_symlinked_source_rejected(self):
        link = self.root / 'examples/fixtures/linked.jsonl'
        try:
            link.symlink_to(self.root / 'examples/fixtures/two.jsonl')
        except OSError:
            self.skipTest('Symlink creation unavailable')
        self.cli('plan', 'create', '--title', 'Symlink', '--study', self.study,
                 '--protocol', self.protocol, '--left', 'examples/fixtures/one.jsonl',
                 '--right', 'examples/fixtures/linked.jsonl', code=1)

    def test_unfrozen_plan_cannot_execute_or_export(self):
        self.cli('plan', 'run', self.plan, code=1)
        self.cli('plan', 'dry-run', self.plan, code=1)

    def test_step_context_loads_only_explicit_approved_memory_and_skill(self):
        evidence = self.root / 'knowledge/evidence/approved-note.md'
        evidence.write_text('Synthetic evidence for an explicitly approved note.', encoding='utf-8')
        ident, _ = self.cli('memory', 'propose', '--summary', 'Example reviewed memory',
                            '--kind', 'observation', '--source',
                            'knowledge/evidence/approved-note.md')
        approval = subprocess.run([sys.executable, '-S', 'rk.py', 'memory', 'accept', ident],
                                  cwd=self.root, input='ACCEPT\n', capture_output=True,
                                  text=True, timeout=12)
        self.assertEqual(approval.returncode, 0, approval.stderr)
        spec = self.load_draft()
        spec['steps'][0]['context']['required_refs'] = [ident]
        spec['steps'][0]['context']['required_skills'] = ['execute-research-plan']
        self.replace_draft(spec)
        self.freeze()
        output, _ = self.cli('plan', 'context', self.plan, '--step', 'baseline')
        self.assertIn('Example reviewed memory', output)
        self.assertIn('Selected Procedural Skill', output)
        self.assertIn('execute-research-plan', output)
        self.assertNotIn('Synthetic evidence for', output)  # no source document body
        evidence.write_text('Changed evidence content', encoding='utf-8')
        self.cli('plan', 'check', self.plan, code=1)

    def test_unapproved_memory_cannot_enter_context(self):
        evidence = self.root / 'knowledge/evidence/unreviewed.md'
        evidence.write_text('Raw source note', encoding='utf-8')
        ident, _ = self.cli('memory', 'propose', '--summary', 'Unreviewed memory',
                            '--kind', 'observation', '--source',
                            'knowledge/evidence/unreviewed.md')
        spec = self.load_draft()
        spec['steps'][0]['context']['required_refs'] = [ident]
        self.replace_draft(spec)
        self.cli('plan', 'check', self.plan, code=1)

    def test_edited_selected_skill_invalidates_frozen_plan(self):
        spec = self.load_draft()
        spec['steps'][0]['context']['required_skills'] = ['execute-research-plan']
        self.replace_draft(spec)
        self.freeze()
        skill = self.root / 'methods/skills/execute-research-plan/SKILL.md'
        skill.write_text(skill.read_text(encoding='utf-8') + '\nA changed instruction.\n', encoding='utf-8')
        self.cli('plan', 'dry-run', self.plan, code=1)

    def test_bad_row_fails_without_writing_raw_private_content(self):
        bad = self.root / 'examples/fixtures/invalid.jsonl'
        bad.write_text('{"success": "SENSITIVE_EXAMPLE_STRING"}\n', encoding='utf-8')
        spec = self.load_draft()
        digest = hashlib.sha256(bad.read_bytes()).hexdigest()
        spec['steps'][0]['inputs']['data'] = {
            'type': 'workspace_file', 'path': 'examples/fixtures/invalid.jsonl',
            'sha256': digest,
        }
        self.replace_draft(spec)
        self.freeze()
        result, proc = self.cli('plan', 'run', self.plan, code=1)
        self.assertNotIn('SENSITIVE_EXAMPLE_STRING', result + proc.stderr)
        self.assertIn('FAILED', result)

    def test_original_source_kept_small_and_outside_git_raw(self):
        self.freeze()
        plan = self.load_draft()
        self.assertTrue(all(i['type'] != 'arbitrary_command' for x in plan['steps']
                            for i in x['inputs'].values()))
        self.assertEqual(plan['environment']['network'], 'not_used')
        self.assertIn('data/', (SOURCE / '.gitignore').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
