import copy
import tempfile
import unittest
from pathlib import Path

from grading.intake import BINDING, CONFIG, FINGERPRINT
from grading.proposals import register_baseline


def inputs():
    rubric = {'assessment_id': BINDING['assessment_id'], 'variant': BINDING['variant'], 'revision': BINDING['revision'],
              'rubric_id': 'synthetic', 'rubric_sha256': 'b' * 64, 'caps': [],
              'criteria': {'functioneel': {'max': 1, 'levels': [0, 1]}, 'leesbaar': {'max': 1, 'levels': [0, .5, 1]},
                           'programmeerconcept': {'max': 2, 'levels': [0, 1, 2]}, 'wiskundeconcept': {'max': 1, 'levels': [0, .5, 1]}}}
    binding = {**BINDING, 'submission_id': 'synthetic', 'source_sha256': 'a' * 64, 'config_fingerprint': FINGERPRINT,
               'identity_fingerprint': 'c' * 64,
               'rubric_id': rubric['rubric_id'], 'rubric_sha256': rubric['rubric_sha256']}
    qid = CONFIG['questions'][0]['id']
    extracted = {'submission_id': 'synthetic', 'source_sha256': 'a' * 64, 'verification_regions': [], 'verification_safe': True,
                 'evidence': [{'evidence_id': qid + ':code', 'question_id': qid, 'kind': 'code', 'state': 'present'}]}
    mark = {'criterion_id': qid + '.functioneel', 'points': 1, 'evidence_ids': [qid + ':code'], 'rationale': 'observed'}
    return binding, rubric, extracted, [mark]


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'baseline.json'
    def tearDown(self): self.tmp.cleanup()

    def test_idempotency_conflict_and_immutable_file(self):
        args = inputs()
        baseline = register_baseline(self.path, *args)
        self.assertEqual(register_baseline(self.path, *copy.deepcopy(args)), baseline)
        original = self.path.read_bytes()
        changed = list(copy.deepcopy(args)); changed[1]['extra'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'conflict'): register_baseline(self.path, *changed)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(baseline['raw_marks'], args[3])
        self.assertEqual(baseline['score']['totals']['earned'], 1)

    def test_pending_and_required_justification(self):
        binding, rubric, extracted, marks = inputs()
        baseline = register_baseline(self.path, binding, rubric, extracted)
        self.assertEqual(baseline['score']['totals']['pending'], 45)
        for change in ({'rationale': '  '}, {'evidence_ids': []}, {'evidence_ids': ['missing']}):
            candidate = dict(marks[0], **change)
            with self.assertRaises(ValueError): register_baseline(self.path, binding, rubric, extracted, [candidate])

    def test_binding_and_source_conflicts(self):
        args = inputs()
        for index, key in [(0, 'revision'), (0, 'config_fingerprint'), (0, 'rubric_sha256'), (2, 'source_sha256'), (2, 'submission_id')]:
            changed = list(copy.deepcopy(args)); changed[index][key] = 'c' * 64
            with self.assertRaises(ValueError): register_baseline(self.path, *changed)
        changed = list(copy.deepcopy(args)); changed[0]['extra'] = 'unexpected'
        with self.assertRaises(ValueError): register_baseline(self.path, *changed)
        self.assertFalse(self.path.exists())

if __name__ == '__main__': unittest.main()
