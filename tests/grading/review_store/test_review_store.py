import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from grading.intake import CONFIG
from grading.proposals import register_baseline
from grading.review_store import load_review, mutate
from tests.grading.proposals.test_proposals import inputs


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'review.json'
        binding, self.rubric, extracted, _ = inputs()
        extracted['evidence'] = [{'evidence_id': q['id'] + ':code', 'question_id': q['id'], 'kind': 'code', 'state': 'present'} for q in CONFIG['questions']]
        self.baseline = register_baseline(Path(self.tmp.name) / 'baseline.json', binding, self.rubric, extracted)
        self.marks = [{'criterion_id': q['id'] + '.' + suffix, 'points': spec['max'], 'evidence_ids': [q['id'] + ':code'], 'rationale': 'observed'} for q in CONFIG['questions'] for suffix, spec in self.rubric['criteria'].items()]
        self.ids = [m['criterion_id'] for m in self.marks]
    def tearDown(self): self.tmp.cleanup()
    def change(self, revision, action, payload):
        return mutate(self.path, self.baseline, self.rubric, revision, 'Teacher', 'Review', action, payload)
    def test_reload_stale_approval_and_invalidation(self):
        self.assertEqual(load_review(self.path, self.baseline, self.rubric)['revision'], 0)
        self.change(0, 'attest', {})
        self.change(1, 'marks', {'marks': self.marks, 'checked_ids': self.ids[:-1]})
        with self.assertRaisesRegex(ValueError, 'ready'): self.change(2, 'approve', {})
        self.change(2, 'marks', {'marks': self.marks, 'checked_ids': [self.ids[-1]]})
        result = self.change(3, 'approve', {})
        self.assertEqual(result['approval']['revision'], 4)
        self.assertEqual(load_review(self.path, self.baseline, self.rubric), result)
        with self.assertRaisesRegex(ValueError, 'stale'): self.change(3, 'attest', {})
        marks = copy.deepcopy(self.marks); marks[0]['points'] = 0
        result = self.change(4, 'marks', {'marks': marks, 'checked_ids': []})
        self.assertIsNone(result['approval'])
        self.assertNotIn(self.ids[0], result['checked_ids'])
        changed = copy.deepcopy(self.baseline); changed['verification_safe'] = False
        with self.assertRaisesRegex(ValueError, 'conflict'): load_review(self.path, changed, self.rubric)
    def test_failed_write_and_feedback(self):
        self.change(0, 'attest', {})
        before = self.path.read_bytes()
        with patch('grading.review_store.write_json', side_effect=OSError('synthetic failure')):
            with self.assertRaises(OSError): self.change(1, 'attest', {})
        self.assertEqual(self.path.read_bytes(), before)
        marks = copy.deepcopy(self.marks); marks[0]['points'] = 0
        self.change(1, 'marks', {'marks': marks, 'checked_ids': self.ids})
        feedback = {'strength': {'text': 'Good', 'evidence_id': marks[0]['evidence_ids'][0]}, 'priorities': [{'criterion_id': self.ids[0], 'title': 'Improve', 'observation': 'Observed', 'correction': 'Correct'}]}
        self.assertEqual(self.change(2, 'feedback', feedback)['feedback'], feedback)
        with self.assertRaises(ValueError): self.change(3, 'feedback', {'strength': None, 'priorities': feedback['priorities'] * 4})
        result = self.change(3, 'marks', {'marks': self.marks, 'checked_ids': []})
        self.assertEqual(result['feedback']['priorities'], [])
        self.assertEqual(result['history'][-1]['invalidated_priorities'], [self.ids[0]])

if __name__ == '__main__': unittest.main()
