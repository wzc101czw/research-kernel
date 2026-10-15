"""Scientific study objects; small typed JSON registry. No LLM calls or scientific truth claims.

This module enforces relationships, provenance, protocol freeze/amendment, and review
record integrity. It deliberately does NOT decide whether a scientific claim is true.
"""
import argparse
import copy
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

KINDS = {
    'question': ('rq', 'questions'),
    'hypothesis': ('hyp', 'hypotheses'),
    'study': ('study', 'studies'),
    'protocol': ('protocol', 'protocols'),
    'run': ('run', 'runs'),
    'observation': ('obs', 'observations'),
    'analysis': ('analysis', 'analyses'),
    'review': ('review', 'reviews'),
}
MODE = {'empirical', 'theoretical', 'systems', 'simulation', 'exploratory'}
PHASE = {'exploratory', 'confirmatory'}
REVIEW_DECISION = {'accepted', 'changes_requested', 'rejected', 'inconclusive'}
RELATIONS = {
    'addresses': {'question'},
    'competes_with': {'hypothesis'},
    'for_study': {'study'},
    'tests': {'hypothesis'},
    'follows': {'protocol'},
    'produced_by': {'run'},
    'uses_observation': {'observation'},
    'interprets': {'hypothesis'},
    'reviews': {'protocol', 'analysis', 'hypothesis', 'observation', 'run', 'claim'},
    'amends': {'protocol'},
    'related_to': set(KINDS) | {'claim'},
}
ALLOWED_FOR = {
    'question': {'related_to'},
    'hypothesis': {'addresses', 'competes_with', 'related_to'},
    'study': {'addresses', 'related_to'},
    'protocol': {'for_study', 'tests', 'amends', 'related_to'},
    'run': {'follows', 'related_to'},
    'observation': {'produced_by', 'related_to'},
    'analysis': {'uses_observation', 'interprets', 'related_to'},
    'review': {'reviews', 'related_to'},
}
FIELDS = {
    'schema_version', 'id', 'kind', 'title', 'summary', 'status', 'mode', 'phase',
    'design', 'links', 'sources', 'asset_refs', 'reviewer', 'decision',
    'created_at', 'updated_at', 'revision', 'history',
}
CONFIRMATORY_DESIGN = (
    'variables', 'controls', 'outcomes', 'analysis_plan', 'stopping_rule',
)


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def fail(msg):
    raise ValueError(msg)


def id_kind(ident):
    if not isinstance(ident, str):
        fail('Scientific ID must be a string')
    for kind, (prefix, _folder) in KINDS.items():
        if re.fullmatch(rf'{prefix}-[a-f0-9]{{12}}', ident):
            return kind
    if re.fullmatch(r'claim-[a-f0-9]{12}', ident):
        return 'claim'
    fail(f'Invalid scientific ID: {ident}')


def path_for(root, ident):
    kind = id_kind(ident)
    if kind == 'claim':
        return root / 'knowledge/claims' / (ident + '.json')
    return root / 'science' / KINDS[kind][1] / (ident + '.json')


def load(root, ident):
    path = path_for(root, ident)
    if not path.resolve().is_relative_to(root.resolve()):
        fail('Scientific path escapes repository')
    if not path.is_file():
        fail('Unknown scientific object: ' + ident)
    obj = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj, dict) or obj.get('id') != ident:
        fail('Scientific object identity mismatch: ' + ident)
    return obj


def object_source(root, name, source_ref):
    p = (root / name).resolve()
    if not p.is_relative_to(root.resolve()):
        fail('Scientific source outside repository')
    if (any(x in {'.git', '.rk', 'data', 'secrets', '.cache', '.ipynb_checkpoints'}
            for x in p.relative_to(root).parts)
            or re.search(r'(api[_-]?key|password|secret|credential|private[_-]?key|access[_-]?token|\.env)',
                         p.name, flags=re.I)):
        fail('Source path is not an approved tracked research source')
    if not p.is_file() or p.stat().st_size > 5 * 1024 * 1024:
        fail('Scientific source must be a small file inside repository (<= 5 MiB)')
    return source_ref(name)


def validate(root, obj, source_ref, check_external=True):
    if not isinstance(obj, dict) or set(obj) != FIELDS:
        fail('Scientific object schema keys invalid')
    kind = id_kind(obj.get('id'))
    if kind == 'claim' or kind != obj['kind'] or obj['schema_version'] != 1:
        fail('Scientific object ID, kind or version mismatch')
    if not isinstance(obj['title'], str) or not obj['title'].strip() or len(obj['title']) > 500:
        fail('Scientific title missing/too long')
    if not isinstance(obj['summary'], str) or len(obj['summary']) > 10000:
        fail('Scientific summary invalid')
    if obj['status'] not in ('draft', 'frozen', 'sealed', 'finalized'):
        fail('Unknown scientific status')
    if obj['status'] == 'frozen' and kind != 'protocol':
        fail('Only protocol may be frozen')
    if obj['status'] == 'finalized' and kind != 'review':
        fail('Only review may be finalized')
    if obj['status'] == 'sealed' and kind not in {'run', 'observation', 'analysis'}:
        fail('Only run, observation or analysis may be sealed')
    if obj['mode'] is not None and (kind != 'study' or obj['mode'] not in MODE):
        fail('Research mode only valid on Study')
    if obj['phase'] is not None and (kind != 'protocol' or obj['phase'] not in PHASE):
        fail('Phase only valid on Protocol')
    if kind == 'study' and obj['mode'] not in MODE:
        fail('Study requires valid research mode')
    if kind == 'protocol' and obj['phase'] not in PHASE:
        fail('Protocol requires exploratory/confirmatory phase')
    if not isinstance(obj['design'], dict) or len(obj['design']) > 80:
        fail('Design must be an object')
    if any(not isinstance(k, str) or not isinstance(v, str) or len(v) > 10000
           for k, v in obj['design'].items()):
        fail('Design values must be strings <=10000 chars')
    if not isinstance(obj['links'], list) or len(obj['links']) > 200:
        fail('Invalid links list')
    seen = set()
    for link in obj['links']:
        if not isinstance(link, dict) or set(link) != {'relation', 'target'}:
            fail('Invalid link schema')
        relation, target = link['relation'], link['target']
        target_kind = id_kind(target)
        if (relation not in ALLOWED_FOR[kind]
                or target_kind not in RELATIONS.get(relation, set())
                or target == obj['id']):
            fail('Illegal scientific relationship: ' + str(link))
        pair = (relation, target)
        if pair in seen:
            fail('Duplicate scientific relationship')
        seen.add(pair)
        if check_external:
            linked = load(root, target)
            if relation == 'follows' and linked.get('status') != 'frozen':
                fail('Run must follow a frozen Protocol')
    if not isinstance(obj['asset_refs'], list) or len(obj['asset_refs']) > 100:
        fail('Invalid asset refs')
    if len(obj['asset_refs']) != len(set(obj['asset_refs'])):
        fail('Duplicate asset refs')
    if check_external:
        import rk_assets
        for asset_ref in obj['asset_refs']:
            rk_assets.require_published(root, asset_ref)
    if not isinstance(obj['sources'], list) or len(obj['sources']) > 100:
        fail('Invalid source list')
    for source in obj['sources']:
        if not isinstance(source, dict) or set(source) != {'path', 'sha256'}:
            fail('Invalid source entry')
        if not isinstance(source['path'], str) or not re.fullmatch('[0-9a-f]{64}', source['sha256']):
            fail('Invalid source path/hash')
        if check_external:
            fresh = object_source(root, source['path'], source_ref)
            if fresh != source:
                fail('STALE scientific source: ' + source['path'])
    if not isinstance(obj['reviewer'], str) or not isinstance(obj['decision'], str):
        fail('Review fields must be strings')
    if kind != 'review' and (obj['reviewer'] or obj['decision']):
        fail('Review fields only valid on Review')
    if kind == 'review' and obj['decision'] and obj['decision'] not in REVIEW_DECISION:
        fail('Invalid review decision')
    if type(obj['revision']) is not int or obj['revision'] < 1:
        fail('Revision must be positive integer')
    if (not isinstance(obj['history'], list) or not obj['history']
            or obj['history'][-1].get('revision') != obj['revision']):
        fail('Invalid revision history')
    for key in ('created_at', 'updated_at'):
        if not isinstance(obj[key], str) or not obj[key].strip():
            fail('Missing timestamp')
    if kind == 'protocol' and obj['status'] == 'frozen':
        if not any(l['relation'] == 'for_study' for l in obj['links']):
            fail('Frozen protocol must link to a study')
        if obj['phase'] == 'confirmatory':
            missing = [k for k in CONFIRMATORY_DESIGN if not obj['design'].get(k, '').strip()]
            if missing:
                fail('Frozen confirmatory protocol missing: ' + ', '.join(missing))
    if kind in {'run', 'observation', 'analysis'} and obj['status'] == 'sealed':
        if not obj['sources'] and not obj['asset_refs']:
            fail('Sealed scientific evidence requires source or published Asset reference')
        required_relation = {'run': 'follows', 'observation': 'produced_by',
                             'analysis': 'uses_observation'}[kind]
        # In theoretical research, a source-linked proof/analysis need not fabricate a Run.
        if kind != 'analysis' or not obj['sources']:
            if not any(l['relation'] == required_relation for l in obj['links']):
                fail('Sealed ' + kind + ' missing ' + required_relation + ' relationship')
        if check_external and kind in {'observation', 'analysis'}:
            for link in obj['links']:
                if link['relation'] == required_relation:
                    earlier = load(root, link['target'])
                    if earlier.get('status') != 'sealed':
                        fail('Sealed evidence cannot depend on an unsealed predecessor')
    if kind == 'review' and obj['status'] == 'finalized':
        if (not obj['reviewer'].strip() or obj['decision'] not in REVIEW_DECISION
                or not any(l['relation'] == 'reviews' for l in obj['links'])):
            fail('Finalized review needs reviewer, decision and reviewed target')


def save(root, obj, save_json, new=False):
    save_json(path_for(root, obj['id']), obj, new=new)


def new(args, root, source_ref, save_json):
    ident = KINDS[args.kind][0] + '-' + uuid.uuid4().hex[:12]
    t = stamp()
    obj = {
        'schema_version': 1, 'id': ident, 'kind': args.kind, 'title': args.title,
        'summary': args.summary or '', 'status': 'draft',
        'mode': args.mode if args.kind == 'study' else None,
        'phase': args.phase if args.kind == 'protocol' else None,
        'design': {},
        'links': [{'relation': relation, 'target': target} for relation, target in (args.link or [])],
        'sources': [object_source(root, s, source_ref) for s in (args.source or [])],
        'asset_refs': args.asset_ref or [],
        'reviewer': '', 'decision': '',
        'created_at': t, 'updated_at': t, 'revision': 1,
        'history': [{'revision': 1, 'at': t, 'action': 'created', 'reason': 'initial record'}],
    }
    validate(root, obj, source_ref)
    save(root, obj, save_json, new=True)
    print(ident)


def mutate(root, ident, updated, original, reason, source_ref, save_json):
    if not reason or not reason.strip():
        fail('Nonempty reason required')
    latest = load(root, ident)
    if latest['revision'] != original['revision']:
        fail('Concurrent revision conflict; reload record')
    if set(updated) != FIELDS:
        fail('Changed schema keys')
    immutable = FIELDS - {'title', 'summary', 'design', 'links', 'sources', 'asset_refs'}
    if any(updated[k] != original[k] for k in immutable):
        fail('Identity/state/history fields are immutable')
    if original['status'] != 'draft':
        fail('Scientific record frozen/finalized: fork amendment or create new record')
    edited = [k for k in FIELDS - immutable if updated[k] != original[k]]
    if not edited:
        print('No changes')
        return
    updated['revision'] = original['revision'] + 1
    updated['updated_at'] = stamp()
    updated['history'] = original['history'] + [{
        'revision': updated['revision'], 'at': updated['updated_at'],
        'action': 'edited', 'fields': sorted(edited), 'reason': reason.strip(),
    }]
    validate(root, updated, source_ref)
    save(root, updated, save_json)
    print(f"Updated {ident} revision={updated['revision']}")


def freeze(args, root, source_ref, save_json):
    obj = load(root, args.id)
    if obj['kind'] != 'protocol' or obj['status'] != 'draft':
        fail('Only draft protocols may be frozen')
    if not args.reviewed_by.strip():
        fail('Provide reviewed-by human identifier; CLI does not authenticate identity')
    t = stamp()
    obj['status'] = 'frozen'
    obj['updated_at'] = t
    obj['revision'] += 1
    obj['history'] += [{
        'revision': obj['revision'], 'at': t, 'action': 'frozen',
        'reviewed_by': args.reviewed_by, 'reason': args.reason,
    }]
    validate(root, obj, source_ref)
    save(root, obj, save_json)
    print('FROZEN', args.id)


def seal(args, root, source_ref, save_json):
    obj = load(root, args.id)
    if obj['kind'] not in {'run', 'observation', 'analysis'} or obj['status'] != 'draft':
        fail('Only draft Runs, Observations and Analyses may be sealed')
    if not args.recorded_by.strip():
        fail('Recorder identifier required (not authenticated by CLI)')
    obj['status'] = 'sealed'
    obj['revision'] += 1
    obj['updated_at'] = stamp()
    obj['history'] += [{
        'revision': obj['revision'], 'at': obj['updated_at'],
        'action': 'sealed', 'recorded_by': args.recorded_by, 'reason': args.reason,
    }]
    validate(root, obj, source_ref)
    save(root, obj, save_json)
    print('SEALED', args.id)


def finalize(args, root, source_ref, save_json):
    obj = load(root, args.id)
    if obj['kind'] != 'review' or obj['status'] != 'draft':
        fail('Only draft reviews may be finalized')
    if not args.reviewer.strip():
        fail('Reviewer identifier required (not authenticated by CLI)')
    obj['reviewer'], obj['decision'] = args.reviewer, args.decision
    obj['revision'] += 1
    obj['status'], obj['updated_at'] = 'finalized', stamp()
    obj['history'] += [{
        'revision': obj['revision'], 'at': obj['updated_at'],
        'action': 'finalized', 'reviewer': args.reviewer, 'reason': args.reason,
    }]
    validate(root, obj, source_ref)
    save(root, obj, save_json)
    print('FINALIZED REVIEW', args.id, args.decision)


def amend(args, root, source_ref, save_json):
    original = load(root, args.id)
    if original['kind'] != 'protocol' or original['status'] != 'frozen':
        fail('Can only amend a frozen protocol')
    if not args.reason.strip():
        fail('Provide an amendment reason')
    new_obj = copy.deepcopy(original)
    ident = 'protocol-' + uuid.uuid4().hex[:12]
    t = stamp()
    new_obj.update({
        'id': ident, 'title': original['title'] + ' (amendment)',
        'status': 'draft', 'created_at': t, 'updated_at': t,
        'revision': 1, 'history': [{
            'revision': 1, 'at': t, 'action': 'amended_from',
            'parent': original['id'], 'reason': args.reason,
        }],
        'links': [l for l in original['links'] if l['relation'] != 'amends']
                 + [{'relation': 'amends', 'target': original['id']}],
    })
    validate(root, new_obj, source_ref)
    save(root, new_obj, save_json, new=True)
    print(ident)


def check(root, source_ref):
    problems = []
    for kind, (_prefix, folder) in KINDS.items():
        directory = root / 'science' / folder
        if not directory.is_dir():
            problems.append('Missing scientific directory: science/' + folder)
            continue
        for path in sorted(directory.glob('*.json')):
            try:
                if not path.resolve().is_relative_to(root.resolve()):
                    fail('Escaping symlink')
                obj = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(obj, dict) or path.stem != obj.get('id') or obj.get('kind') != kind:
                    fail('Scientific object path does not match identity')
                validate(root, obj, source_ref)
            except (OSError, ValueError, TypeError, KeyError, AttributeError) as e:
                problems.append(f'{path.relative_to(root)}: {e}')
    return problems


def add_cli(sub):
    sc = sub.add_parser('science', help='study, hypotheses, protocols, evidence and reviews')
    cmds = sc.add_subparsers(dest='action', required=True)
    p = cmds.add_parser('new')
    p.add_argument('kind', choices=KINDS)
    p.add_argument('--title', required=True)
    p.add_argument('--summary', default='')
    p.add_argument('--mode', choices=sorted(MODE), default='empirical')
    p.add_argument('--phase', choices=sorted(PHASE), default='exploratory')
    p.add_argument('--link', nargs=2, action='append', metavar=('RELATION', 'ID'))
    p.add_argument('--source', action='append')
    p.add_argument('--asset-ref', action='append')
    p = cmds.add_parser('show')
    p.add_argument('id')
    p = cmds.add_parser('list')
    p.add_argument('--kind', choices=KINDS)
    p = cmds.add_parser('set', help='edit a draft field or design entry')
    p.add_argument('id')
    p.add_argument('--key', required=True, help='title, summary, or design.NAME')
    p.add_argument('--value', required=True)
    p.add_argument('--reason', required=True)
    p.add_argument('--expected-revision', type=int)
    p = cmds.add_parser('link', help='add typed relationship to a draft object')
    p.add_argument('id')
    p.add_argument('--relation', required=True, choices=sorted(RELATIONS))
    p.add_argument('--to', required=True)
    p.add_argument('--reason', required=True)
    p = cmds.add_parser('edit', help='edit a draft object using prepared JSON')
    p.add_argument('id')
    p.add_argument('--from-json', required=True)
    p.add_argument('--reason', required=True)
    p.add_argument('--expected-revision', type=int)
    p = cmds.add_parser('freeze', help='freeze study Protocol; no execution or truth guarantee')
    p.add_argument('id')
    p.add_argument('--reviewed-by', required=True)
    p.add_argument('--reason', default='Human review before evaluation')
    p = cmds.add_parser('amend', help='fork a frozen Protocol, preserving frozen original')
    p.add_argument('id')
    p.add_argument('--reason', required=True)
    p = cmds.add_parser('seal', help='seal a sourced Run, Observation or Analysis')
    p.add_argument('id')
    p.add_argument('--recorded-by', required=True)
    p.add_argument('--reason', default='Completed source-linked evidence record')
    p = cmds.add_parser('finalize', help='finalize scientific Review; does not promote Claim')
    p.add_argument('id')
    p.add_argument('--reviewer', required=True)
    p.add_argument('--decision', choices=sorted(REVIEW_DECISION), required=True)
    p.add_argument('--reason', required=True)
    cmds.add_parser('check')


def dispatch(args, root, source_ref, save_json):
    if args.action == 'new':
        new(args, root, source_ref, save_json)
    elif args.action == 'show':
        print(json.dumps(load(root, args.id), ensure_ascii=False, indent=2))
    elif args.action == 'list':
        for kind, (_prefix, folder) in KINDS.items():
            if args.kind and kind != args.kind:
                continue
            for path in sorted((root / 'science' / folder).glob('*.json')):
                obj = json.loads(path.read_text(encoding='utf-8'))
                print(f"{obj['id']}\t{obj['status']}\t{obj['title']}")
    elif args.action in {'set', 'link', 'edit'}:
        obj = load(root, args.id)
        if getattr(args, 'expected_revision', None) is not None and obj['revision'] != args.expected_revision:
            fail('Expected revision mismatch')
        updated = copy.deepcopy(obj)
        if args.action == 'set':
            if args.key in {'title', 'summary'}:
                updated[args.key] = args.value
            elif re.fullmatch(r'design\.[a-z][a-z0-9_]{0,63}', args.key):
                updated['design'][args.key[7:]] = args.value
            else:
                fail('Can set only title, summary or design.KEY')
        elif args.action == 'link':
            updated['links'].append({'relation': args.relation, 'target': args.to})
        else:
            updated = json.loads(Path(args.from_json).read_text(encoding='utf-8'))
        mutate(root, args.id, updated, obj, args.reason, source_ref, save_json)
    elif args.action == 'freeze':
        freeze(args, root, source_ref, save_json)
    elif args.action == 'finalize':
        finalize(args, root, source_ref, save_json)
    elif args.action == 'seal':
        seal(args, root, source_ref, save_json)
    elif args.action == 'amend':
        amend(args, root, source_ref, save_json)
    elif args.action == 'check':
        failures = check(root, source_ref)
        for error in failures:
            print('ERROR:', error)
        print('Scientific registry errors:', len(failures))
        return 1 if failures else 0
    return 0
