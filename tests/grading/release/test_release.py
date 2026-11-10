import csv
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from grading.common import read_json
from grading.release import promote, release_status, write_overview
from grading.reports import REPORT_FILES


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.pdf'
        self.source.write_bytes(b'synthetic source')
        digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        binding = {'submission_id': 'synthetic', 'identity_fingerprint': 'identity',
                   'source_sha256': digest, 'rubric_sha256': 'rubric'}
        self.baseline = {'binding': binding}
        self.snapshot = {'binding': binding, 'revision': 1,
                         'approval': {'revision': 1, 'source_sha256': digest, 'rubric_sha256': 'rubric'},
                         'source_attestation': {'source_sha256': digest},
                         'score': {'totals': {'pending': 0}, 'criteria': []}, 'checked_ids': []}
        self.reports = self.root / 'reports'

    def render(self, folder, *args, **kwargs):
        for name in REPORT_FILES:
            (folder / name).write_bytes(name.encode())

    def promote(self, validate=lambda: True):
        return promote(self.reports, self.source, {}, self.baseline, self.snapshot, validate)

    @patch('grading.release.render_reports')
    def test_retry_failure_and_stale(self, render):
        render.side_effect = self.render
        target = self.promote()
        self.assertEqual(set(p.name for p in target.iterdir()), set(REPORT_FILES))
        self.assertEqual(release_status(self.reports, 'synthetic', self.snapshot), 'current')
        self.assertEqual(self.promote(), target)
        self.assertEqual(render.call_count, 1)
        self.snapshot['revision'] = 2
        self.snapshot['approval']['revision'] = 2
        render.side_effect = OSError('write failure')
        with self.assertRaises(OSError): self.promote()
        self.assertEqual(release_status(self.reports, 'synthetic', self.snapshot), 'stale')
        self.snapshot['revision'] = 1
        self.snapshot['approval']['revision'] = 1
        self.assertEqual(release_status(self.reports, 'synthetic', self.snapshot), 'current')
        (target / REPORT_FILES[0]).unlink()
        self.assertEqual(release_status(self.reports, 'synthetic', self.snapshot), 'stale')
        with self.assertRaises(ValueError): self.promote()

    @patch('grading.release.render_reports')
    def test_changed_source_and_validation(self, render):
        def changed(folder, *args, **kwargs):
            self.render(folder)
            self.source.write_bytes(b'changed')
        render.side_effect = changed
        with self.assertRaises(ValueError): self.promote()
        self.assertEqual(release_status(self.reports, 'synthetic', self.snapshot), 'unreleased')
        self.source.write_bytes(b'synthetic source')
        render.side_effect = self.render
        with self.assertRaises(ValueError): self.promote(lambda: False)
        self.assertEqual(release_status(self.reports, 'synthetic', self.snapshot), 'unreleased')
        self.promote()
        self.assertEqual(release_status(self.reports, 'synthetic', self.snapshot), 'current')
        self.snapshot['binding']['identity_fingerprint'] = 'reassigned'
        self.assertEqual(release_status(self.reports, 'synthetic', self.snapshot), 'stale')

    def test_overview_formula_cells(self):
        path = write_overview(self.reports, [{'name': ' =1+1', 'source': '\tcmd', 'status': 'accepted', 'release_status': 'unreleased'}])
        with path.open(encoding='utf-8-sig', newline='') as f: row = next(csv.DictReader(f))
        self.assertEqual(row['name'], "' =1+1")
        self.assertEqual(row['source'], "'\tcmd")
        self.assertEqual(row['release_status'], 'unreleased')
        pointer = read_json(path.parent.parent / 'leerkrachtoverzicht-current.json')
        self.assertEqual(pointer['file'], str(path.relative_to(path.parent.parent)))

    @patch('grading.release.render_reports')
    def test_layout_upgrade_creates_a_new_release_for_the_same_approval(self, render):
        render.side_effect = self.render
        with patch('grading.release.REPORT_LAYOUT', 'feedback-v1'):
            previous = self.promote()
        self.assertEqual(release_status(self.reports, 'synthetic', self.snapshot), 'stale')
        current = self.promote()
        self.assertNotEqual(current, previous)
        self.assertEqual(release_status(self.reports, 'synthetic', self.snapshot), 'current')
        self.assertTrue((previous / 'feedbackkaart.pdf').is_file())


if __name__ == '__main__': unittest.main()
