import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from grading.__main__ import main
from grading.intake import CONFIG
from grading.proposals import register_baseline
from grading.review_store import load_review
from tests.grading.proposals.test_proposals import inputs


class ReviewerCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        binding, self.rubric, extracted, marks = inputs()
        extracted['evidence'][0].update(quote='synthetic code', regions=[{'page': 2, 'box': [0, 0, 1, 1]}], reason='synthetic')
        self.rubric['questions'] = {q['id']: {'programmeerankers': ['a', 'b'], 'functioneel': 'f', 'wiskundeconcept': 'w', 'probes': []} for q in CONFIG['questions']}
        self.baseline = register_baseline(self.root / 'baseline.json', binding, self.rubric, extracted, marks)
        self.state = self.root / 'review.json'
        self.context = {'row': {}, 'source': self.root / 'original.pdf', 'rubric': self.rubric,
                        'baseline': self.baseline, 'state_path': self.state}
        self.lookup = patch('grading.workflow.review_context', return_value=self.context)
        self.lookup.start()
        self.addCleanup(self.lookup.stop)
        self.addCleanup(self.tmp.cleanup)

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(['--workspace', str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def file(self, value):
        path = self.root / 'input.json'
        path.write_text(json.dumps(value), encoding='utf8')
        return str(path)

    def test_show_and_question_filter(self):
        code, out, _ = self.run_cli('show', 'synthetic', '--question', CONFIG['questions'][0]['id'])
        self.assertEqual(code, 0)
        shown = json.loads(out)
        self.assertEqual(shown['bron'], str(self.root / 'original.pdf'))
        self.assertEqual(shown['bewijs'][0]['regions'][0]['page'], 2)
        self.assertEqual(len(shown['criteria']), 4)
        self.assertEqual(len(shown['oefeningsspecificaties']), 1)
        self.assertIn('pending_reason', shown['criteria'][0])
        self.assertEqual(self.run_cli('show', 'synthetic', '--question', 'unknown')[0], 1)

    def test_patch_checked_all_and_duplicates(self):
        cid = self.baseline['raw_marks'][0]['criterion_id']
        args = ['marks', 'synthetic', '--revision', '0', '--actor', 'Leraar', '--reason', 'Nakijken']
        self.assertEqual(self.run_cli(*args, '--file', self.file([{'criterion_id': cid, 'points': 0}]), '--checked', 'all')[0], 0)
        state = load_review(self.state, self.baseline, self.rubric)
        self.assertEqual(state['marks'][0]['points'], 0)
        self.assertEqual(state['marks'][0]['rationale'], 'observed')
        self.assertEqual(state['checked_ids'], [cid])
        self.assertEqual(self.run_cli(*args, '--file', self.file([{'criterion_id': cid}, {'criterion_id': cid}]), '--checked', 'all')[0], 1)
        self.assertEqual(load_review(self.state, self.baseline, self.rubric)['revision'], 1)
        self.assertEqual(self.run_cli(*args, '--file', self.file([]), '--checked', cid)[0], 1)

    def test_attest_feedback_and_approval_gate(self):
        common = ['--actor', 'Leraar', '--reason', 'Controle']
        self.assertEqual(self.run_cli('attest', 'synthetic', '--revision', '0', *common)[0], 0)
        self.assertEqual(self.run_cli('feedback', 'synthetic', '--revision', '1', *common, '--file', self.file({'strength': None, 'priorities': []}))[0], 0)
        self.assertEqual(self.run_cli('approve', 'synthetic', '--revision', '2', *common)[0], 1)
        self.assertEqual(load_review(self.state, self.baseline, self.rubric)['revision'], 2)


if __name__ == '__main__':
    unittest.main()
