"""Read-only legacy workspace inventory from tree text or a local directory.

Never opens source file contents, never moves/deletes files, never imports secrets.
The output is an advisory staging plan, not a migration or evidence validator.
"""
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

GROUPS = {
    'secret_candidate': 'SECURITY REVIEW ONLY; do not ingest into Git, prompt or memory',
    'git_internal': 'Ignore; original repository history is not a research document',
    'cache_generated': 'Keep local; rebuild/discard only after human review',
    'dataset_candidate': 'Register Dataset/Benchmark asset; payload stays outside Git',
    'run_trace_candidate': 'Link to Experiment Run and external trace artifacts',
    'prediction_evaluation': 'Assign Run ID, evaluator version, dataset split, artifact role',
    'research_document': 'Review for Question/Hypothesis/Analysis/Report or Research Archive',
    'memory_candidate': 'Review summary against primary evidence; do not auto-promote',
    'source_code': 'Keep executable source, tests and environment versions in Git',
    'logs_artifacts': 'Register Run artifact; keep large logs in external store',
    'other_review': 'Human triage needed before classifying or moving',
}
SENSITIVE = re.compile(r'(?:api[_-]?key|password|secret|credential|private[_-]?key|access[_-]?token|\.env)', re.I)
TRACE_DIRS = {'travelplanner', 'swe_bench_pro', 'terminal_bench_2', 'vitabench', 'webarena_verified'}


def classify(path):
    normalized = path.replace('\\', '/')
    name = normalized.rsplit('/', 1)[-1].lower()
    parts = normalized.split('/')
    root = parts[0].lower()
    if SENSITIVE.search(name):
        return 'secret_candidate'
    if '.git' in parts:
        return 'git_internal'
    if '__pycache__' in parts or '.ipynb_checkpoints' in parts or name.endswith(('.pyc', '.pyo')):
        return 'cache_generated'
    if root == 'memory':
        return 'memory_candidate'
    if root in {'data', 'datasets', 'longrca-bench'} or name.endswith('.parquet'):
        return 'dataset_candidate'
    if root in TRACE_DIRS:
        return 'run_trace_candidate'
    if root == 'analysis':
        if name.startswith(('preds_', 'results_', 'eval_')) or name.endswith(('.jsonl', '.log')):
            return 'prediction_evaluation'
        if name.endswith('.py'):
            return 'source_code'
        return 'research_document'
    if root == 'logs' or name.endswith('.log'):
        return 'logs_artifacts'
    if root == 'docs' or name.endswith(('.md', '.pdf')):
        return 'research_document'
    if name.endswith(('.py', '.sh')) or root in {'solver', 'src', 'tests'}:
        return 'source_code'
    if name in {'_pdf_text.txt', '_pdf_text_v4.txt'}:
        return 'cache_generated'
    return 'other_review'


def clean_path(name):
    if not name or name in {'.', '..'} or '\x00' in name or '/' in name or '\\' in name:
        raise ValueError('Unsafe entry name in tree: ' + repr(name[:80]))
    if len(name) > 500:
        raise ValueError('Very long entry name in tree')
    return name


def parse_tree(text):
    """Parse Unicode `tree` output; only path information, not file bytes."""
    entries, stack = [], []
    lines = text.splitlines()
    if len(lines) > 1000000:
        raise ValueError('Tree listing unreasonably large')
    for number, line in enumerate(lines[1:], start=2):
        match = re.fullmatch(r'([\u2502 ]*)(?:\u251c|\u2514)\u2500\u2500 (.*)', line)
        if not match or len(match.group(1)) % 4:
            raise ValueError(f'Invalid tree indentation / line {number}')
        depth = len(match.group(1)) // 4 + 1
        is_directory = match.group(2).endswith('/')
        name = clean_path(match.group(2).rstrip('/'))
        if depth > len(stack) + 1:
            raise ValueError(f'Broken tree depth at line {number}')
        stack = stack[:depth - 1] + [name]
        path = '/'.join(stack)
        entries.append({'path': path, 'type': 'directory' if is_directory else 'file'})
    return entries


def scan_directory(base):
    """Read path metadata only, never follow symlinked directories or open files."""
    import os
    root = Path(base).expanduser().resolve()
    if not root.is_dir():
        raise ValueError('Directory does not exist')
    entries = []
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        # Deliberately avoid descending into .git, caches, raw stores; include directory names.
        here = Path(current)
        for name in sorted(dirs):
            if name in {'.', '..'}:
                continue
            relative = (here / name).relative_to(root).as_posix()
            entries.append({'path': relative, 'type': 'directory'})
        dirs[:] = [x for x in dirs if x not in {'.git', '.cache', '.rk', '.venv', 'node_modules'}
                   and not (here / x).is_symlink()]
        for name in sorted(files):
            relative = (here / name).relative_to(root).as_posix()
            entries.append({'path': relative, 'type': 'file'})
            if len(entries) > 1000000:
                raise ValueError('Inventory exceeds 1 million entries')
    return entries


def summarize(entries):
    files = [x['path'] for x in entries if x['type'] == 'file']
    groups = {name: [] for name in GROUPS}
    for path in files:
        groups[classify(path)].append(path)
    top = Counter(p.split('/')[0] for p in files)
    result = {
        'schema_version': 1,
        'inventory_type': 'path_only',
        'warning': 'No file bytes, file sizes, SHA-256, Git-tracked state or scientific conclusions verified',
        'file_count': len(files), 'directory_count': sum(x['type'] == 'directory' for x in entries),
        'top_level': dict(sorted(top.items(), key=lambda x: (-x[1], x[0]))),
        'groups': {name: {'count': len(paths), 'examples': paths[:8], 'action': GROUPS[name]}
                   for name, paths in groups.items()},
        'risk_paths': groups['secret_candidate'],
        'next_steps': [
            'Security-first: inspect candidate secret paths and Git history locally; rotate real exposed credentials',
            'Snapshot/backup original repository; do not delete, overwrite or rename based on this plan',
            'Human review establishes canonical Study, Protocol, Benchmark and Run identities',
            'Register small paper/report/source metadata; keep raw payload out of Git',
            'Validate source content, metric semantics and real hashes before linking analyses to claims',
        ],
    }
    return result


def markdown(report):
    lines = [
        '# Legacy Workspace Intake — Preview Only', '',
        'This is a **path-only, read-only** inventory. It has not inspected file contents, Git history,',
        'dataset integrity, experiment validity or actual file sizes.', '',
        f"- Files: {report['file_count']}",
        f"- Directories: {report['directory_count']}", '',
        '## Proposed handling', '',
        '| Category | Files | Decision |', '|---|---:|---|',
    ]
    for name, info in report['groups'].items():
        lines.append(f"| `{name}` | {info['count']} | {info['action']} |")
    lines += ['', '## Security review candidates', '']
    lines += [f'- `{name}` (filename only, contents not examined)' for name in report['risk_paths']]
    if not report['risk_paths']:
        lines.append('- None from path heuristics; this is NOT a secret scan.')
    lines += ['', '## Human review checklist', '']
    lines += ['- ' + text for text in report['next_steps']]
    lines += ['', '## Scope of this plan', '',
              'No original file was copied, opened, moved, deleted, executed, or automatically classified as validated evidence.', '']
    return '\n'.join(lines)


def add_cli(sub):
    intake = sub.add_parser('intake', help='read-only legacy workspace inventory')
    commands = intake.add_subparsers(dest='action', required=True)
    for action in ('tree', 'directory'):
        p = commands.add_parser(action)
        p.add_argument('source', help='tree listing TXT or existing directory')
        p.add_argument('--out-dir', help='default .rk/intake/latest (gitignored)')


def dispatch(args, root):
    if args.action == 'tree':
        path = Path(args.source)
        if not path.is_file() or path.stat().st_size > 10 * 1024 * 1024:
            raise ValueError('Tree source must be a <= 10 MiB text file')
        entries = parse_tree(path.read_text(encoding='utf-8'))
    else:
        entries = scan_directory(args.source)
    report = summarize(entries)
    destination = Path(args.out_dir) if args.out_dir else root / '.rk/intake/latest'
    destination = destination.resolve()
    # Prefer private, untracked local reports. Explicit paths allowed for reviewed export.
    if destination.is_symlink():
        raise ValueError('Refusing symlink output directory')
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'inventory.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (destination / 'PLAN.md').write_text(markdown(report), encoding='utf-8')
    print(f"READ-ONLY INTAKE: {report['file_count']} files, {report['directory_count']} dirs")
    print('Manifest:', destination / 'inventory.json')
    print('Plan:', destination / 'PLAN.md')
    if report['risk_paths']:
        print('SECURITY REVIEW: candidate secret-bearing filenames detected (contents not inspected)')
