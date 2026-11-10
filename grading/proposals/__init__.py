"""Immutable, teacher-entered scoring baselines."""
import hashlib
import json
from pathlib import Path

from grading.common import file_lock, read_json, write_json
from grading.intake import BINDING, route_config
from grading.scoring import score

FORMAT = 'jsik-baseline-v1'
_BINDING_KEYS = set(BINDING) | {
    'submission_id', 'source_sha256', 'config_fingerprint', 'identity_fingerprint', 'rubric_id', 'rubric_sha256',
}


def _json_copy(value):
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError('inputs must be JSON-compatible') from exc


def register_baseline(path, binding, rubric, extracted, marks=None):
    """Create a baseline once; repeat only with precisely matching inputs."""
    binding, rubric, extracted, marks = _json_copy([binding, rubric, extracted, [] if marks is None else marks])
    if not isinstance(binding, dict) or set(binding) != _BINDING_KEYS:
        raise ValueError('invalid binding keys')
    if any(not isinstance(v, str) or not v.strip() for v in binding.values()):
        raise ValueError('invalid binding values')
    route = {k: binding[k] for k in BINDING}
    if (route_config(route, binding['config_fingerprint']) is None
            or not isinstance(rubric, dict) or not isinstance(extracted, dict)
            or any(binding[k] != rubric.get(k) for k in ('assessment_id', 'variant', 'revision', 'rubric_id', 'rubric_sha256'))
            or any(binding[k] != extracted.get(k) for k in ('submission_id', 'source_sha256'))):
        raise ValueError('binding mismatch')
    for k in ('source_sha256', 'rubric_sha256', 'identity_fingerprint'):
        if len(binding[k]) != 64 or any(c not in '0123456789abcdef' for c in binding[k]):
            raise ValueError('invalid hash')
    if (not isinstance(extracted.get('evidence'), list) or not isinstance(extracted.get('verification_regions'), list)
            or not isinstance(extracted.get('verification_safe'), bool) or not isinstance(marks, list)):
        raise ValueError('invalid extraction or marks')
    for mark in marks:
        if isinstance(mark, dict) and mark.get('points') is not None:
            if not isinstance(mark.get('rationale'), str) or not mark['rationale'].strip() or not mark.get('evidence_ids'):
                raise ValueError('numeric marks require evidence and rationale')
    digest = hashlib.sha256(json.dumps([binding, rubric, extracted, marks], ensure_ascii=False, sort_keys=True,
                                       separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
    baseline = {'format': FORMAT, 'binding': binding, 'evidence': extracted['evidence'],
                'verification_regions': extracted['verification_regions'], 'verification_safe': extracted['verification_safe'],
                'raw_marks': marks, 'score': score(rubric, extracted['evidence'], marks), 'input_sha256': digest}
    path = Path(path)
    with file_lock(path.with_name(path.name + '.lock')):
        if path.exists():
            existing = read_json(path)
            if existing != baseline:
                raise ValueError('baseline conflict')
            return existing
        write_json(path, baseline)
    return baseline
