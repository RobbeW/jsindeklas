import hashlib
import tempfile
import unittest
from pathlib import Path
from reportlab.pdfgen import canvas
from grading.intake import CONFIG, scan


def pdf(path, *, change=None, identity=('Fictief Leerling', '1A'), incomplete=False, url='https://example.org/evaluaties/toets_4.html', family=False):
    c = canvas.Canvas(str(path))
    def lines(items):
        t = c.beginText(30, 800)
        t.setFont('Helvetica', 9)
        for item in items:
            t.textLine(item)
        c.drawText(t)
    lines(['JavaScript in de Klas - Gebundelde export' if not family else 'Other', 'Naam: '+identity[0], 'Klas: '+identity[1], 'Inhoud:'] + [q['title'] for q in CONFIG['questions']])
    c.showPage()
    for i, q in enumerate(CONFIG['questions']):
        if incomplete and i == 8: break
        prompt = q['prompt']
        if change and i == 8: prompt = prompt.replace('// Schrijf hieronder', '// Voorbeelduitkomst voor de console: Beoordeling: B.\n// Schrijf hieronder')
        lines([f'Oefening {i+1} / 9', q['title'], 'Opdracht:', 'Gegeven', 'Code:'] + prompt.splitlines() + ['let fictief = 1;', 'Console-uitvoer:', ''])
        c.showPage()
        lines(['Beoordeling & feedback leerkracht:', 'Pagina-URL: '+url])
        c.showPage()
    c.save()


def entry(source='a.pdf', **kw):
    result = dict(source=source, roster_id='r1', class_id='c1', name='Fictief Leerling', class_name='1A', assessment_id='toets_3', attempt_slot='first')
    result.update(kw)
    return result

class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        pdf(self.root/'a.pdf')
    def tearDown(self): self.tmp.cleanup()
    def scan(self, *entries, **kwargs): return scan(self.root, {'entries': list(entries), **kwargs})['results']
    def test_clean_repeat_and_continuations(self):
        before = hashlib.sha256((self.root/'a.pdf').read_bytes()).hexdigest()
        a = self.scan(entry())[0]
        self.assertEqual(a['disposition'], 'accepted', a)
        self.assertEqual(a['sections'][0], {'question_id':'toets_3-ex01', 'start_page':2, 'end_page':3})
        self.assertEqual(a, self.scan(entry())[0])
        (self.root/'renamed.pdf').write_bytes((self.root/'a.pdf').read_bytes())
        self.assertEqual(a['submission_id'], self.scan(entry('renamed.pdf'))[0]['submission_id'])
        self.assertEqual(before, hashlib.sha256((self.root/'a.pdf').read_bytes()).hexdigest())
    def test_routes_and_identity(self):
        for options, expected in [({'change':True}, 'unsupported'), ({'incomplete':True}, 'triage'), ({'url':'https://example.org/evaluaties/other.html'}, 'triage'), ({'family':True}, 'unsupported')]:
            pdf(self.root/'b.pdf', **options)
            self.assertEqual(self.scan(entry('b.pdf'))[0]['disposition'], expected)
        self.assertEqual(self.scan(entry(name='Someone else'))[0]['disposition'], 'mismatch')
        self.assertEqual(self.scan(entry('missing.pdf'))[0]['disposition'], 'missing')
        (self.root/'bad.pdf').write_bytes(b'not a pdf')
        self.assertEqual(self.scan(entry('bad.pdf'))[0]['disposition'], 'corrupt')
    def test_conflicts_and_exclusion(self):
        (self.root/'b.pdf').write_bytes((self.root/'a.pdf').read_bytes())
        results = self.scan(entry(), entry('b.pdf'))
        self.assertTrue(all('duplicate_bytes' in x['reasons'] for x in results))
        results = self.scan(entry(), entry('b.pdf', roster_id='r2'))
        self.assertTrue(all('bytes_claimed_by_different_learners' in x['reasons'] for x in results))
        pdf(self.root/'b.pdf', identity=('Other', '1A'))
        results = self.scan(entry(), entry('b.pdf'))
        self.assertTrue(all('competing_hand_ins' in x['reasons'] for x in results))
        (self.root/'out').mkdir()
        (self.root/'out'/'x.pdf').write_bytes((self.root/'a.pdf').read_bytes())
        self.assertEqual(self.scan(entry('out/x.pdf'), managed_outputs=['out'])[0]['disposition'], 'excluded')
        self.assertEqual(self.scan(entry('../outside.pdf'))[0]['disposition'], 'triage')

    def test_homonyms_require_teacher_resolution(self):
        results = self.scan(entry(), entry('missing.pdf', roster_id='r2'))
        self.assertEqual(results[0]['reasons'], ['visible_identity_ambiguous'])
        self.assertEqual(results[1]['disposition'], 'missing')

if __name__ == '__main__': unittest.main()
