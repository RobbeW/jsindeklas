import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pypdf import PdfReader
from grading.common import read_json, sha256_file, write_json
from grading.reports import REPORT_FILES, _feedback_card, render_reports
from grading.review_store import load_review
from grading.workflow import review_context
from tests.grading.demo import create_demo
from tests.grading.test_workflow import cli, demo_feedback


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.workspace = self.root / 'demo'
        self.source = create_demo(self.workspace); self.digest = sha256_file(self.source)
        self.run_cli('intake')
        self.submission = read_json(self.workspace / 'intake/inventory.json')['results'][0]['submission_id']
        self.run_cli('prepare', self.submission)
        self.context = review_context(self.workspace, self.submission, 'demo.yaml')
        self.learner = {'name': 'Demo Leerling', 'class_name': 'TEST'}

    def run_cli(self, *args):
        status, _, error = cli(self.workspace, *args)
        self.assertEqual(status, 0, error)

    def state(self):
        return load_review(self.context['state_path'], self.context['baseline'], self.context['rubric'])

    def edit(self, action, revision, *args):
        self.run_cli(action, self.submission, '--revision', str(revision), '--actor', 'Leraar', '--reason', 'Demo', *args)

    def output(self, name, state, final=False):
        folder = self.root / name; folder.mkdir()
        return render_reports(folder, self.source, self.learner, self.context['baseline'], state, final)

    def test_draft_final_feedback_and_sanitization(self):
        paths = self.output('draft', self.state())
        self.assertEqual(tuple(p.name for p in paths), REPORT_FILES)
        for path in paths:
            preview_text = ''.join(page.extract_text() for page in PdfReader(path).pages)
            self.assertNotIn('Voorlopig – na te kijken', preview_text)
            self.assertNotIn('Nagekeken door je leerkracht', preview_text)
        text = ''.join(p.extract_text() for p in PdfReader(paths[0]).pages)
        self.assertIn('45', text); self.assertIn('open', text.lower())
        draft = PdfReader(paths[1])
        first_page = draft.pages[0].extract_text()
        for label in ('Functioneel', 'Leesbaar', 'Programmeerconcept', 'Wiskundeconcept'):
            self.assertIn(label, first_page)
            self.assertIn(label, text)
        self.assertIn('0–18 / 18', first_page)
        draft_detail = ''.join(p.extract_text() for p in draft.pages[1:])
        self.assertIn('Nog na te kijken', draft_detail)
        self.assertNotIn('Waar verloor je punten?', draft_detail)
        self.edit('attest', 0)
        self.edit('marks', 1, '--file', str(self.workspace / 'intake/demo-marks.json'), '--checked', 'all')
        feedback = demo_feedback()
        for n in (1, 3):
            f = self.workspace / f'intake/feedback{n}.json'; write_json(f, {**feedback, 'priorities': feedback['priorities'][:n]})
            self.edit('feedback', 2 if n == 1 else 3, '--file', str(f))
            paths = self.output(f'feedback{n}', self.state())
            text = ''.join(p.extract_text() for p in PdfReader(paths[1]).pages)
            self.assertIn(feedback['priorities'][n-1]['title'], text)
        self.edit('approve', 4)
        paths = self.output('final', self.state(), True)
        card = PdfReader(paths[1])
        self.assertEqual(len(card.pages), 2)
        self.assertIn('Nagekeken door je leerkracht', card.pages[0].extract_text())
        detail = card.pages[1].extract_text()
        self.assertIn('Je punten per vraag', detail)
        self.assertIn('5. Batterijstatus · Functioneel', detail)
        self.assertIn('45 - 13,5 puntenverlies = 31,5 / 45.', detail)
        self.assertNotIn('Fictief voorbeeld voor de demonstratie', detail)
        copy_pdf = PdfReader(paths[2]); source = PdfReader(self.source)
        self.assertGreater(len(copy_pdf.pages), len(source.pages))
        self.assertTrue(all(set((p.extract_text() or '').strip()) <= set('123\n ') for p in copy_pdf.pages[:len(source.pages)]))
        self.assertNotIn('TECHNISCH-ALLEEN-DEMO', ''.join(p.extract_text() or '' for p in copy_pdf.pages))
        self.assertEqual(sha256_file(self.source), self.digest)

    def test_clean_card_needs_no_detail_page(self):
        criteria = self.state()['score']['criteria']
        for criterion in criteria:
            criterion['effective_points'] = criterion['effective_max']
        path = self.root / 'clean.pdf'
        _feedback_card(path, self.learner, {'strength': None, 'priorities': []}, criteria,
                       {'earned': 45, 'loss': 0, 'pending': 0, 'maximum': 45}, 'Nagekeken door je leerkracht')
        card = PdfReader(path)
        self.assertEqual(len(card.pages), 1)
        self.assertIn('Je behaalde alle punten.', card.pages[0].extract_text())

    def test_mixed_card_distinguishes_loss_from_pending(self):
        criteria = self.state()['score']['criteria']
        for criterion in criteria:
            criterion['effective_points'] = criterion['effective_max']
        by_id = {criterion['criterion_id']: criterion for criterion in criteria}
        by_id['toets_3-ex01.functioneel']['effective_points'] = 0
        by_id['toets_3-ex03.functioneel']['effective_points'] = None
        path = self.root / 'mixed.pdf'
        _feedback_card(path, self.learner, {'strength': None, 'priorities': []}, criteria,
                       {'earned': 43, 'loss': 1, 'pending': 1, 'maximum': 45}, '')
        card = PdfReader(path)
        self.assertIn('7–8 / 9', card.pages[0].extract_text())
        detail = card.pages[1].extract_text()
        self.assertIn('Korting vanaf ... · Functioneel', detail)
        self.assertNotIn('Kassa: pas bedrag aan · Functioneel', detail)
        self.assertIn('45 - 1 puntenverlies = 44 maximaal.', detail)
        self.assertIn('43–44 / 45', detail)

    def test_long_work_point_flows_without_losing_text(self):
        state = self.state()['score']
        feedback = demo_feedback()
        feedback['priorities'][0]['observation'] = (
            'Bij deze grens kan je de voorwaarde stap voor stap volgen. '*135 + 'Eindcontrole zichtbaar.'
        )
        path = self.root / 'long.pdf'
        learner = {'name': 'Zoë van den Oever '*24, 'class_name': 'TEST'}
        _feedback_card(path, learner, feedback, state['criteria'], state['totals'], '')
        card = PdfReader(path)
        text = ' '.join(page.extract_text() for page in card.pages)
        self.assertLess(len(card.pages), 8)
        self.assertIn('Eindcontrole zichtbaar.', text)
        self.assertIn('Je punten per vraag', text)

    def test_rejects_unsafe_stale_and_changed_source(self):
        with self.assertRaises(ValueError): self.output('unapproved', self.state(), True)
        bad = copy.deepcopy(self.context['baseline']); bad['verification_safe'] = False
        folder = self.root / 'unsafe'; folder.mkdir()
        with self.assertRaises(ValueError): render_reports(folder, self.source, self.learner, bad, self.state())
        self.source.write_bytes(self.source.read_bytes() + b'changed')
        with self.assertRaises(ValueError): self.output('changed', self.state())

if __name__ == '__main__': unittest.main()
