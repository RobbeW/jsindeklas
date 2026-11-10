"""Regression for timed exports and their separately bound scoring workflow."""
import math
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pypdfium2 as pdfium
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from grading.adapters import extract
from grading.common import sha256_file, write_json
from grading.intake import TIMED_BINDING, TIMED_CONFIG
from grading.rubrics import load_rubric
from grading.workflow import intake
from tests.grading.demo import ANSWERS, create_demo, demo_rubric
from tests.grading.test_workflow import cli, demo_feedback


def write_timed_pdf(path, revision=TIMED_BINDING['revision'], changed_prompt=False):
    pdf = canvas.Canvas(str(path), pagesize=A4, invariant=True)
    y = 804

    def line(text, font='Helvetica', size=12):
        nonlocal y
        pdf.setFont(font, size)
        pdf.drawString(36, y, text)
        y -= size + 3

    def heading(text, size=13):
        line(text, 'Helvetica-Bold', size)

    def page():
        nonlocal y
        pdf.showPage()
        y = 804

    heading('JavaScript in de Klas - Gebundelde export', 18)
    for text in ('Naam: Demo Leerling', 'Klas: TEST', TIMED_CONFIG['title']):
        line(text)
    heading('Inhoud:')
    for question in TIMED_CONFIG['questions']:
        line(question['title'])
    for number, (question, answer) in enumerate(zip(TIMED_CONFIG['questions'], ANSWERS), 1):
        page()
        heading(f'Oefening {number} / 9', 18)
        line(question['title'])
        prompt = question['prompt']
        if changed_prompt and number == 9:
            prompt = prompt.replace('37 punten', '38 punten')
        if number == 1:
            heading('Opdracht:')
            for text in prompt.splitlines():
                line(text.removeprefix('// ').removeprefix('//'))
        heading('Code:')
        if number != 1:
            for text in prompt.splitlines():
                line(text, 'Courier', 10)
        for text in answer[0].splitlines():
            line(text, 'Courier', 10)
        if number == 2:
            page()
            line('// vervolg op de volgende pagina', 'Courier', 10)
        if number == 1:
            heading('Code van de laatste uitvoering:')
            line('console.log("oude versie");', 'Courier', 10)
            heading('Console-uitvoer van eerdere code:')
            line('oude versie', 'Courier', 10)
        else:
            heading('Console-uitvoer:')
            line('Code:' if number == 3 else answer[1], 'Courier', 10)
        heading('Beoordeling & feedback leerkracht:')
    page()
    heading('Door de browser geregistreerd:')
    for text in (f'Versie: {revision}', 'Poging: synthetisch', 'Afgerond: Zelf ingediend',
                 'Start (UTC): 2026-01-01T12:00:00Z', 'Einde (UTC): 2026-01-01T12:10:00Z',
                 'Pagina-URL: https://example.invalid/een/lange/map/', 'platform.html',
                 'Browser: ALLEEN-VOOR-SYNTHETISCHE-TEST'):
        line(text)
    pdf.save()


class TimedWorkflowTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name) / 'demo'
        self.source = create_demo(self.workspace)

    def command(self, *args):
        status, output, error = cli(self.workspace, *args)
        self.assertEqual(status, 0, error)
        return output

    def test_current_revision_extracts_final_code_and_releases_feedback(self):
        write_timed_pdf(self.source)
        registration, = intake(self.workspace)
        self.assertEqual(registration['disposition'], 'accepted', registration['reasons'])
        self.assertEqual(registration['binding'], TIMED_BINDING)
        result = extract(self.source, registration)
        self.assertTrue(result['verification_safe'])
        evidence = {item['evidence_id']: item for item in result['evidence']}
        self.assertEqual(evidence['toets_3-ex01:code']['quote'], ANSWERS[0][0])
        self.assertEqual(evidence['toets_3-ex01:console']['state'], 'unavailable')
        self.assertIn('vervolg', evidence['toets_3-ex02:code']['quote'])
        self.assertEqual(evidence['toets_3-ex03:console']['quote'], 'Code:')
        self.assertEqual(evidence['toets_3-ex08:code']['state'], 'proven_blank')

        rubric_path = self.workspace / 'rubrics/demo.yaml'
        with self.assertRaisesRegex(ValueError, 'rubric binding mismatch'):
            load_rubric(rubric_path, registration)
        rubric = demo_rubric()
        rubric.update(revision=TIMED_BINDING['revision'], prompt_source_blob=TIMED_CONFIG['source_blob'])
        write_json(rubric_path, rubric)
        write_json(rubric_path.with_suffix('.yaml.calibration.json'), {
            'gate': 'D02', 'status': 'accepted', 'rubric_sha256': sha256_file(rubric_path),
        })

        submission = registration['submission_id']
        self.command('prepare', submission)
        self.assertIn('console.log', self.command('show', submission, '--question', 'toets_3-ex01'))
        feedback = self.workspace / 'intake/feedback.json'
        write_json(feedback, demo_feedback())
        for revision, (action, arguments) in enumerate([
            ('attest', []),
            ('marks', ['--file', str(self.workspace / 'intake/demo-marks.json'), '--checked', 'all']),
            ('feedback', ['--file', str(feedback)]),
            ('approve', []),
        ]):
            self.command(action, submission, '--revision', str(revision),
                         '--actor', 'Demo Leerkracht', '--reason', 'Synthetische proef', *arguments)
        released = Path(self.command('release', submission, '--revision', '4').strip())
        for filename in ('feedbackkaart.pdf', 'puntenoverzicht.pdf', 'toets-met-feedback.pdf'):
            self.assertTrue((released / filename).is_file())
        annotated = pdfium.PdfDocument(released / 'toets-met-feedback.pdf')
        footer, = result['verification_regions']
        image = annotated[footer['page'] - 1].render(scale=1).to_pil().convert('RGB')
        top = math.ceil(footer['box'][1] * image.height) + 3
        self.assertEqual(image.crop((0, top, image.width, image.height)).getextrema(), ((255, 255),) * 3)

    def test_unknown_revision_and_changed_prompt_are_not_accepted(self):
        write_timed_pdf(self.source, revision='toets-3-onbekend')
        unknown, = intake(self.workspace)
        self.assertEqual(unknown['disposition'], 'unsupported')
        write_timed_pdf(self.source, changed_prompt=True)
        changed, = intake(self.workspace)
        self.assertEqual(changed['disposition'], 'triage')
        self.assertIn('starter_missing_or_mismatch', changed['reasons'])
