"""Revisioned, local teacher review of an immutable scoring baseline."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from grading.common import file_lock, read_json, write_json
from grading.practice import PRACTICE
from grading.proposals import FORMAT as BASELINE_FORMAT
from grading.scoring import score

FORMAT = 'jsik-review-v1'


def _copy(value):
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError('inputs must be JSON-compatible') from exc


def _fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _initial(baseline, rubric):
    if not isinstance(baseline, dict) or baseline.get('format') != BASELINE_FORMAT:
        raise ValueError('invalid baseline')
    binding = baseline['binding']
    if any(binding.get(k) != rubric.get(k) for k in ('assessment_id', 'variant', 'revision', 'rubric_id', 'rubric_sha256')):
        raise ValueError('rubric binding mismatch')
    return {'format': FORMAT, 'baseline_sha256': _fingerprint(baseline), 'rubric_fingerprint': _fingerprint(rubric),
            'binding': binding, 'revision': 0, 'marks': baseline['raw_marks'], 'checked_ids': [],
            'source_attestation': None, 'feedback': {'strength': None, 'priorities': []},
            'approval': None, 'history': []}


def _snapshot(state, baseline, rubric):
    expected = _initial(baseline, rubric)
    if any(state.get(k) != expected[k] for k in ('format', 'baseline_sha256', 'rubric_fingerprint', 'binding')):
        raise ValueError('baseline or rubric conflict')
    result = _copy(state)
    result['score'] = score(rubric, baseline['evidence'], state['marks'], bool(state['source_attestation']))
    return result


def load_review(path, baseline, rubric):
    """Load decisions and recompute the effective score; absent files start at revision zero."""
    baseline, rubric = _copy([baseline, rubric])
    path = Path(path)
    state = read_json(path) if path.exists() else _initial(baseline, rubric)
    return _snapshot(state, baseline, rubric)


def current_approval(snapshot):
    approval = snapshot["approval"]
    binding = snapshot["binding"]
    attestation = snapshot["source_attestation"]
    return bool(
        approval and attestation
        and approval["revision"] == snapshot["revision"]
        and approval["source_sha256"] == binding["source_sha256"] == attestation["source_sha256"]
        and approval["rubric_sha256"] == binding["rubric_sha256"]
        and not snapshot["score"]["totals"]["pending"]
        and set(snapshot["checked_ids"]) == {item["criterion_id"] for item in snapshot["score"]["criteria"]}
    )


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _validate_feedback(feedback, snapshot, baseline):
    if not isinstance(feedback, dict) or set(feedback) != {'strength', 'priorities'}:
        raise ValueError('invalid feedback')
    strength, priorities = feedback['strength'], feedback['priorities']
    evidence = {item['evidence_id']: item for item in baseline['evidence']}
    if strength is not None:
        if (not isinstance(strength, dict) or set(strength) != {'text', 'evidence_id'}
                or not _text(strength['text']) or strength['evidence_id'] not in evidence
                or evidence[strength['evidence_id']].get('state') != 'present'):
            raise ValueError('strength requires verified evidence')
    criteria = {item['criterion_id']: item for item in snapshot['score']['criteria']}
    if not isinstance(priorities, list) or len(priorities) > 3:
        raise ValueError('invalid priorities')
    seen = set()
    for item in priorities:
        required = {'criterion_id', 'title', 'observation', 'correction'}
        if not isinstance(item, dict) or not required <= set(item) <= required | {'practice_id'}:
            raise ValueError('invalid priority')
        cid = item['criterion_id']
        if cid in seen or cid not in criteria or any(not _text(item[k]) for k in ('title', 'observation', 'correction')):
            raise ValueError('invalid priority')
        criterion = criteria[cid]
        if criterion['effective_points'] is None or criterion['effective_points'] >= criterion['effective_max'] or not criterion['evidence_ids']:
            raise ValueError('priority requires verified deduction')
        if 'practice_id' in item:
            practice_id = item['practice_id']
            if (not isinstance(practice_id, str)
                    or criterion['question_id'] not in PRACTICE.get(practice_id, {}).get('questions', ())):
                raise ValueError('unknown practice reference for the question')
        seen.add(cid)


def mutate(path, baseline, rubric, expected_revision, actor, reason, action, payload):
    """Atomically apply one reviewed decision if the caller has the current revision."""
    if type(expected_revision) is not int or expected_revision < 0 or not _text(actor) or not _text(reason):
        raise ValueError('revision, actor and reason are required')
    baseline, rubric, payload = _copy([baseline, rubric, payload])
    path = Path(path)
    with file_lock(path.with_name(path.name + '.lock')):
        state = read_json(path) if path.exists() else _initial(baseline, rubric)
        current = _snapshot(state, baseline, rubric)
        if state['revision'] != expected_revision:
            raise ValueError('stale revision')
        if not isinstance(payload, dict):
            raise ValueError('invalid payload')
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        invalidated = []
        if action == 'attest':
            if payload: raise ValueError('attestation payload must be empty')
            state['source_attestation'] = {'actor': actor, 'reason': reason, 'source_sha256': state['binding']['source_sha256'], 'revision': expected_revision + 1, 'timestamp': timestamp}
        elif action == 'marks':
            if set(payload) != {'marks', 'checked_ids'} or not isinstance(payload['marks'], list) or not isinstance(payload['checked_ids'], list):
                raise ValueError('invalid marks payload')
            updated = score(rubric, baseline['evidence'], payload['marks'], bool(state['source_attestation']))
            ids = {x['criterion_id'] for x in updated['criteria']}
            checked = payload['checked_ids']
            if any(not isinstance(x, str) or x not in ids for x in checked) or len(set(checked)) != len(checked):
                raise ValueError('invalid checked IDs')
            old = {x['criterion_id']: x for x in state['marks']}
            new = {x['criterion_id']: x for x in payload['marks']}
            changed = {cid for cid in ids if old.get(cid) != new.get(cid)}
            state['marks'] = payload['marks']
            state['checked_ids'] = sorted((set(state['checked_ids']) - changed) | set(checked))
            criteria = {x['criterion_id']: x for x in updated['criteria']}
            kept = []
            for priority in state['feedback']['priorities']:
                criterion = criteria[priority['criterion_id']]
                if criterion['effective_points'] is None or criterion['effective_points'] >= criterion['effective_max'] or not criterion['evidence_ids']:
                    invalidated.append(priority['criterion_id'])
                else:
                    kept.append(priority)
            state['feedback']['priorities'] = kept
        elif action == 'feedback':
            _validate_feedback(payload, current, baseline)
            state['feedback'] = payload
        elif action == 'approve':
            if payload: raise ValueError('approval payload must be empty')
            ids = {x['criterion_id'] for x in current['score']['criteria']}
            attestation = state['source_attestation']
            if (set(state['checked_ids']) != ids or not attestation or attestation['source_sha256'] != state['binding']['source_sha256']
                    or current['score']['totals']['pending'] != 0 or not baseline['verification_safe']):
                raise ValueError('review is not ready for approval')
            _validate_feedback(state['feedback'], current, baseline)
        else:
            raise ValueError('unknown action')
        state['revision'] += 1
        state['approval'] = ({'actor': actor, 'reason': reason, 'revision': state['revision'],
                              'source_sha256': state['binding']['source_sha256'], 'rubric_sha256': state['binding']['rubric_sha256'], 'timestamp': timestamp}
                             if action == 'approve' else None)
        state['history'].append({'revision': state['revision'], 'actor': actor, 'reason': reason, 'action': action, 'payload': payload, 'timestamp': timestamp, 'invalidated_priorities': invalidated})
        result = _snapshot(state, baseline, rubric)
        write_json(path, state)
        return result
