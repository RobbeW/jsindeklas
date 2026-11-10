import tempfile
import unittest
from pathlib import Path

import yaml
from grading.intake import BINDING, CONFIG, FINGERPRINT
from grading.rubrics import load_rubric
from grading.scoring import score


def fixture():
    return dict(schema_version='1.0', rubric_id='synthetic', **{k: BINDING[k] for k in ('assessment_id', 'variant', 'revision')},
        prompt_source_blob=CONFIG['source_blob'], status='draft', teacher_calibration_gate='pending', total_max=45,
        question_max=5, score_step=.5, caps=[], criteria={'functioneel': {'max': 1, 'levels': [0, 1]},
        'leesbaar': {'max': 1, 'levels': [0, .5, 1]}, 'programmeerconcept': {'max': 2, 'levels': [0, 1, 2]},
        'wiskundeconcept': {'max': 1, 'levels': [0, .5, 1]}}, questions={q['id']: {'functioneel': 'synthetic',
        'programmeerankers': ['a', 'b'], 'wiskundeconcept': 'synthetic', 'probes': []} for q in CONFIG['questions']})


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'rubric.yaml'
        self.registration = {'disposition': 'accepted', 'binding': BINDING, 'route_fingerprint': FINGERPRINT}
        self.qid = CONFIG['questions'][0]['id']
    def tearDown(self): self.tmp.cleanup()
    def load(self, rubric):
        self.path.write_text(yaml.safe_dump(rubric))
        return load_rubric(self.path, self.registration)
    def test_binding_and_schema(self):
        rubric = self.load(fixture())
        self.assertEqual(len(rubric['rubric_sha256']), 64)
        for key, value in [('revision', 'wrong'), ('caps', ['cap']), ('total_max', 44)]:
            bad = fixture(); bad[key] = value
            with self.assertRaises(ValueError): self.load(bad)
        with self.assertRaises(ValueError): load_rubric(self.path, {})
    def test_reconciliation_and_invalid_marks(self):
        rubric = self.load(fixture())
        evidence = [{'evidence_id': self.qid + ':code', 'question_id': self.qid, 'kind': 'code', 'state': 'present'}]
        def mark(suffix, points): return {'criterion_id': self.qid + '.' + suffix, 'points': points, 'evidence_ids': [self.qid + ':code'], 'rationale': 'synthetic'}
        result = score(rubric, evidence, [mark('functioneel', 1), mark('programmeerconcept', 1)])
        self.assertEqual(result['totals'], {'earned': 2, 'loss': 1, 'pending': 42, 'maximum': 45, 'range': [2, 44]})
        self.assertEqual(len(result['criteria']), 36)
        for marks in ([mark('functioneel', .5)], [mark('functioneel', 1), mark('functioneel', 1)], [mark('z', 1)], [dict(mark('functioneel', 1), evidence_ids=['missing'])]):
            with self.assertRaises(ValueError): score(rubric, evidence, marks)
    def test_blank_and_unknown(self):
        rubric = self.load(fixture())
        evidence = [{'evidence_id': self.qid + ':code', 'question_id': self.qid, 'kind': 'code', 'state': 'proven_blank'}]
        mark = {'criterion_id': self.qid + '.functioneel', 'points': 0, 'evidence_ids': [self.qid + ':code'], 'rationale': 'synthetic blank'}
        self.assertEqual(score(rubric, evidence, [mark])['criteria'][0]['pending_reason'], 'blank_requires_attestation')
        self.assertEqual(score(rubric, evidence, [mark], True)['totals']['loss'], 1)
        with self.assertRaises(ValueError): score(rubric, evidence, [dict(mark, points=1)], True)
        evidence[0]['state'] = 'ambiguous'
        with self.assertRaises(ValueError): score(rubric, evidence, [mark])
        self.assertEqual(score(rubric, evidence, [])['totals']['pending'], 45)

if __name__ == '__main__': unittest.main()
