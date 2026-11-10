"""Teacher-entered scoring; submitted code is treated solely as inert evidence."""
from grading.intake import CONFIG
from grading.rubrics import _number


def score(rubric, evidence, marks, source_attested=False):
    if not isinstance(source_attested, bool) or not isinstance(evidence, list) or not isinstance(marks, list):
        raise ValueError('invalid scoring inputs')
    if rubric.get('caps') not in ([], {}):
        raise ValueError('caps are out of scope')
    expected = {f"{q['id']}.{suffix}": (q['id'], spec) for q in CONFIG['questions'] for suffix, spec in rubric['criteria'].items()}
    if len(expected) != 36:
        raise ValueError('invalid rubric criteria')
    evid = {}
    for item in evidence:
        if not isinstance(item, dict) or not isinstance(item.get('evidence_id'), str) or item['evidence_id'] in evid:
            raise ValueError('invalid or duplicate evidence')
        evid[item['evidence_id']] = item
    entries = {}
    for mark in marks:
        if not isinstance(mark, dict) or mark.get('criterion_id') not in expected or mark['criterion_id'] in entries:
            raise ValueError('unknown or duplicate criterion')
        points = mark.get('points')
        if points is not None and (not _number(points) or points not in expected[mark['criterion_id']][1]['levels']):
            raise ValueError('invalid points')
        ids = mark.get('evidence_ids', [])
        if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids) or len(ids) != len(set(ids)):
            raise ValueError('invalid evidence IDs')
        if not isinstance(mark.get('rationale', ''), str):
            raise ValueError('invalid rationale')
        if points is not None and not mark.get('rationale', '').strip():
            raise ValueError('numeric mark requires a rationale')
        entries[mark['criterion_id']] = mark
    result = []
    for cid, (qid, spec) in expected.items():
        mark = entries.get(cid, {})
        points = mark.get('points')
        ids = mark.get('evidence_ids', [])
        code = [e for e in evid.values() if e.get('question_id') == qid and e.get('kind') == 'code']
        if len(code) > 1:
            raise ValueError('duplicate code evidence')
        state = code[0].get('state') if code else None
        if state == 'proven_blank' and points not in (None, 0):
            raise ValueError('nonzero blank mark')
        reason = None
        if any(i not in evid or evid[i].get('question_id') != qid for i in ids):
            raise ValueError('mark requires relevant evidence')
        if points is None:
            if state == 'proven_blank' and not source_attested:
                reason = 'blank_requires_attestation'
            elif state in ('unreadable', 'ambiguous', 'unavailable') or state is None:
                reason = state or 'unavailable'
            else:
                reason = 'awaiting_teacher_score'
        elif state == 'proven_blank':
            if not source_attested:
                reason = 'blank_requires_attestation'
            elif code[0]['evidence_id'] not in ids:
                raise ValueError('mark requires relevant code evidence')
        elif state != 'present':
            raise ValueError('numeric mark unsupported by code evidence')
        elif code[0]['evidence_id'] not in ids:
            raise ValueError('mark requires relevant code evidence')
        effective = None if reason else points
        result.append({'criterion_id': cid, 'question_id': qid, 'raw_max': spec['max'], 'raw_points': points,
                       'effective_max': spec['max'], 'effective_points': effective, 'levels': list(spec['levels']),
                       'evidence_ids': ids, 'rationale': mark.get('rationale', ''), 'pending_reason': reason})
    earned = sum(x['effective_points'] for x in result if x['effective_points'] is not None)
    pending = sum(x['effective_max'] for x in result if x['effective_points'] is None)
    maximum = sum(x['effective_max'] for x in result)
    loss = maximum - earned - pending
    return {'criteria': result, 'totals': {'earned': earned, 'loss': loss, 'pending': pending,
                                            'maximum': maximum, 'range': [earned, earned + pending]}}
