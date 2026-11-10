import hashlib
import importlib.util
from io import BytesIO
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.pdfgen.textobject import PDFTextObject
from pypdf import PdfReader, PdfWriter
from pathlib import Path

from grading.adapters import extract
from grading.intake import scan

spec = importlib.util.spec_from_file_location('intake_fixture', Path(__file__).parents[1] / 'intake' / 'test_intake.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / 'a.pdf'
        self.make_pdf()
        self.registration = scan(self.root, {'entries': [fixture.entry()]})['results'][0]

    def make_pdf(self):
        original = PDFTextObject.textLine
        def add_header(obj, text=''):
            if text == 'Pagina-URL: https://example.org/evaluaties/toets_4.html':
                original(obj, 'Verificatiegegevens:')
            return original(obj, text)
        with patch.object(PDFTextObject, 'textLine', add_header):
            fixture.pdf(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_code_and_regions(self):
        result = extract(self.path, self.registration)
        self.assertEqual(result['source_sha256'], hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(len(result['evidence']), 27)
        code = result['evidence'][0]
        self.assertEqual(code['state'], 'present')
        self.assertEqual(code['quote'], 'let fictief = 1;')
        self.assertEqual(code['regions'][0]['page'], 2)
        self.assertEqual(result['evidence'][1]['state'], 'unavailable')
        self.assertEqual(len(result['verification_regions']), 9)
        self.assertTrue(all(len(x['box']) == 4 for x in result['verification_regions']))

    def test_blank_requires_attestation(self):
        original = PDFTextObject.textLine
        def blank(obj, text=''):
            return original(obj, '' if text == 'let fictief = 1;' else text)
        with patch.object(PDFTextObject, 'textLine', blank):
            self.make_pdf()
        registration = scan(self.root, {'entries': [fixture.entry()]})['results'][0]
        code = extract(self.path, registration)['evidence'][0]
        self.assertEqual(code['state'], 'proven_blank')
        self.assertIn('attestation', code['reason'])

    def test_rotation_is_open(self):
        reader = PdfReader(self.path)
        writer = PdfWriter()
        for index, page in enumerate(reader.pages):
            if index == 1: page.rotate(90)
            writer.add_page(page)
        with self.path.open('wb') as out: writer.write(out)
        registration = scan(self.root, {'entries': [fixture.entry()]})['results'][0]
        if registration['disposition'] == 'accepted':
            result = extract(self.path, registration)
            self.assertEqual(result['evidence'][0]['state'], 'ambiguous')
            self.assertFalse(result['verification_safe'])
        else:
            self.assertIn(registration['disposition'], ('triage', 'unsupported'))

    def test_image_only_answer_is_never_a_blank(self):
        original = PDFTextObject.textLine
        def erase_answer(obj, text=''):
            return original(obj, '' if text == 'let fictief = 1;' else text)
        with patch.object(PDFTextObject, 'textLine', erase_answer):
            self.make_pdf()
        writer = PdfWriter(clone_from=PdfReader(self.path))
        overlay = BytesIO()
        art = canvas.Canvas(overlay)
        art.drawImage(ImageReader(Image.new('RGB', (40, 10), 'black')), 30, 636, width=40, height=10)
        art.save()
        writer.pages[1].merge_page(PdfReader(overlay).pages[0])
        with self.path.open('wb') as out:
            writer.write(out)
        registration = scan(self.root, {'entries': [fixture.entry()]})['results'][0]
        code = extract(self.path, registration)['evidence'][0]
        self.assertEqual(code['state'], 'ambiguous')

    def test_changed_or_unaccepted_source_refused(self):
        self.path.write_bytes(self.path.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'hash'): extract(self.path, self.registration)
        with self.assertRaisesRegex(ValueError, 'registration'): extract(self.path, {})

if __name__ == '__main__': unittest.main()
