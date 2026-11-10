"""Lokale, expliciete lerarenbeoordeling; ingezonden code wordt nooit uitgevoerd."""
import json

from grading import review_store, workflow
from grading.common import file_lock, read_json
from grading.scoring import score


def add_commands(subparsers):
    show = subparsers.add_parser('show', help='toon het nakijkdossier')
    show.add_argument('submission')
    show.add_argument('--question', help='toon enkel deze oefening')
    show.set_defaults(handler=_show)
    for action in ('attest', 'marks', 'feedback', 'approve'):
        parser = subparsers.add_parser(action, help=f'leg {action} vast')
        parser.add_argument('submission')
        parser.add_argument('--revision', type=int, required=True)
        parser.add_argument('--actor', required=True)
        parser.add_argument('--reason', required=True)
        if action in ('marks', 'feedback'):
            parser.add_argument('--file', required=True, help='JSON-invoerbestand')
        if action == 'marks':
            parser.add_argument('--checked', required=True, help='all, none of kommagescheiden criterium-ID’s')
        parser.set_defaults(handler=_mutate, action=action)


def _show(workspace, args):
    with file_lock(workflow.private_path(workspace, 'intake/.lock')):
        context = workflow.review_context(workspace, args.submission, args.rubric)
        state = review_store.load_review(context['state_path'], context['baseline'], context['rubric'])
    question = args.question
    criteria = state['score']['criteria']
    evidence = context['baseline']['evidence']
    if question:
        criteria = [item for item in criteria if item['question_id'] == question]
        evidence = [item for item in evidence if item['question_id'] == question]
        if not criteria:
            raise ValueError('Onbekende oefening.')
    # All evidence records include their original page regions and inert extracted text.
    result = {'bron': str(context['source']), 'oefening': question,
              'bewijs': evidence, 'rubriek': context['rubric']['criteria'],
              'oefeningsspecificaties': ({question: context['rubric']['questions'][question]} if question else context['rubric']['questions']),
              'criteria': criteria, 'totalen': state['score']['totals'],
              'beoordelingen': [m for m in state['marks'] if not question or m['criterion_id'].startswith(question + '.')],
              'nagekeken': state['checked_ids'], 'bronverklaring': state['source_attestation'],
              'feedback': state['feedback'], 'revisie': state['revision'], 'goedkeuring': state['approval']}
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _mutate(workspace, args):
    with file_lock(workflow.private_path(workspace, 'intake/.lock')):
        context = workflow.review_context(workspace, args.submission, args.rubric)
        baseline, rubric, path = context['baseline'], context['rubric'], context['state_path']
        payload = {}
        if args.action == 'feedback':
            payload = read_json(args.file)
        elif args.action == 'marks':
            patches = read_json(args.file)
            if not isinstance(patches, list):
                raise ValueError('Beoordelingen moeten een JSON-lijst zijn.')
            ids = [item.get('criterion_id') if isinstance(item, dict) else None for item in patches]
            if any(not isinstance(cid, str) or not cid for cid in ids) or len(set(ids)) != len(ids):
                raise ValueError('Ongeldige of dubbele criterium-ID in invoer.')
            state = review_store.load_review(path, baseline, rubric)
            existing = {item['criterion_id']: item for item in state['marks']}
            # Patches may update individual fields; the scoring engine validates the result.
            for item in patches:
                cid = item['criterion_id']
                existing[cid] = {**existing.get(cid, {}), **item}
            marks = list(existing.values())
            calculated = score(rubric, baseline['evidence'], marks, bool(state['source_attestation']))
            if args.checked == 'all':
                checked = [item['criterion_id'] for item in calculated['criteria']
                           if item['criterion_id'] in ids and item['effective_points'] is not None]
            elif args.checked == 'none':
                checked = []
            else:
                checked = [part.strip() for part in args.checked.split(',')]
                if any(not part for part in checked) or len(set(checked)) != len(checked):
                    raise ValueError('Ongeldige of dubbele nagekeken ID.')
            payload = {'marks': marks, 'checked_ids': checked}
        state = review_store.mutate(path, baseline, rubric, args.revision, args.actor, args.reason, args.action, payload)
    print(f"Opgeslagen · revisie {state['revision']}")
