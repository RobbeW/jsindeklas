"""Load and validate revision-bound, teacher-authored private rubrics."""
import hashlib
import math
from pathlib import Path

from grading.intake import BINDING, CONFIG, FINGERPRINT


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def load_rubric(path, registration):
    """Return a validated rubric and the SHA-256 of its exact YAML bytes."""
    if (not isinstance(registration, dict) or registration.get('disposition') != 'accepted'
            or registration.get('binding') != BINDING or registration.get('route_fingerprint') != FINGERPRINT):
        raise ValueError('accepted matching registration required')
    import yaml  # Optional until a rubric is actually loaded.
    data = Path(path).read_bytes()
    try:
        rubric = yaml.safe_load(data)
    except yaml.YAMLError as exc:
        raise ValueError('invalid rubric YAML') from exc
    if not isinstance(rubric, dict):
        raise ValueError('rubric must be a mapping')
    for key in ('schema_version', 'rubric_id', 'assessment_id', 'variant', 'revision',
                'prompt_source_blob', 'status', 'teacher_calibration_gate', 'total_max',
                'question_max', 'score_step', 'caps', 'criteria', 'questions'):
        if key not in rubric:
            raise ValueError('missing rubric field: ' + key)
    if rubric['schema_version'] != '1.0' or any(not isinstance(rubric[k], str) or not rubric[k].strip() for k in ('rubric_id', 'status')):
        raise ValueError('invalid rubric identity')
    if any(rubric[k] != BINDING[k] for k in ('assessment_id', 'variant', 'revision')) or rubric['prompt_source_blob'] != CONFIG['source_blob']:
        raise ValueError('rubric binding mismatch')
    if rubric['caps'] not in ([], {}):
        raise ValueError('caps are out of scope')
    if rubric['total_max'] != 45 or rubric['question_max'] != 5 or rubric['score_step'] != 0.5:
        raise ValueError('invalid score budget')
    criteria = rubric['criteria']
    if not isinstance(criteria, dict) or len(criteria) != 4:
        raise ValueError('four criteria required')
    for suffix, item in criteria.items():
        if not isinstance(suffix, str) or not suffix or ':' in suffix or not isinstance(item, dict):
            raise ValueError('invalid criterion')
        levels = item.get('levels')
        if not isinstance(levels, list) or any(not _number(x) for x in levels):
            raise ValueError('invalid levels')
    required_levels = {
        'functioneel': (1, (0, 1)),
        'leesbaar': (1, (0, .5, 1)),
        'programmeerconcept': (2, (0, 1, 2)),
        'wiskundeconcept': (1, (0, .5, 1)),
    }
    if {k: (v.get('max'), tuple(v['levels'])) for k, v in criteria.items()} != required_levels:
        raise ValueError('invalid criterion maxima or levels')
    questions = rubric['questions']
    if not isinstance(questions, dict) or set(questions) != {q['id'] for q in CONFIG['questions']}:
        raise ValueError('question IDs mismatch')
    for question in questions.values():
        if not isinstance(question, dict) or any(k not in question for k in ('functioneel', 'programmeerankers', 'wiskundeconcept', 'probes')) or not isinstance(question['programmeerankers'], list) or len(question['programmeerankers']) != 2:
            raise ValueError('invalid question specification')
    rubric['rubric_sha256'] = hashlib.sha256(data).hexdigest()
    return rubric
