import contextlib
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pypdf import PdfReader
from grading.__main__ import main
from grading.common import read_json, sha256_file, write_json
from grading.review_store import current_approval, load_review
from grading.workflow import review_context
from tests.grading.demo import create_demo


def cli(workspace, *args):
    stdout, stderr = StringIO(), StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        status = main(["--workspace", str(workspace), "--rubric", "demo.yaml", *args])
    return status, stdout.getvalue().strip(), stderr.getvalue().strip()


def demo_feedback():
    return {
        "strength": {"text": "Bij gratis verzending gebruik je twee duidelijke takken.",
                     "evidence_id": "toets_3-ex02:code"},
        "priorities": [
            {"criterion_id": "toets_3-ex01.wiskundeconcept", "title": "Drempel van 60",
             "observation": "Bij exact 60 geeft je code geen korting.",
             "correction": "Gebruik >= en denk de bedragen 59 en 60 door.", "practice_id": "ch03-ex06"},
            {"criterion_id": "toets_3-ex03.wiskundeconcept", "title": "Vijf procent",
             "observation": "In de tweede tak tel je een vast bedrag op.",
             "correction": "Vermenigvuldig het bedrag met 1,05."},
            {"criterion_id": "toets_3-ex06.programmeerconcept", "title": "Strikte gelijkheid",
             "observation": "Je vergelijking gebruikt twee gelijktekens.",
             "correction": "Gebruik === om de snelheid met nul te vergelijken.", "practice_id": "ch03-ex04"},
        ],
    }


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "demo"
        self.source = create_demo(self.workspace)
        self.original_hash = sha256_file(self.source)

    def run_ok(self, *args):
        status, stdout, stderr = cli(self.workspace, *args)
        self.assertEqual(status, 0, stderr)
        return stdout

    def edit(self, action, revision, *args):
        return self.run_ok(action, self.submission, "--revision", str(revision),
                           "--actor", "Demo Leerkracht", "--reason", "Synthetische proef", *args)

    def state(self):
        context = review_context(self.workspace, self.submission, "demo.yaml")
        return load_review(context["state_path"], context["baseline"], context["rubric"])

    def prepare_demo(self):
        self.assertIn("accepted", self.run_ok("intake"))
        inventory = read_json(self.workspace / "intake/inventory.json")
        self.submission = inventory["results"][0]["submission_id"]
        self.run_ok("prepare", self.submission)
        self.assertEqual(self.state()["score"]["totals"]["range"], [0, 45])
        self.assertIn("console.log", self.run_ok("show", self.submission, "--question", "toets_3-ex01"))
        self.edit("attest", 0)
        marks = self.workspace / "intake/demo-marks.json"
        self.edit("marks", 1, "--file", str(marks), "--checked", "all")
        self.assertEqual(self.state()["score"]["totals"]["range"], [31.5, 31.5])
        feedback = self.workspace / "intake/demo-feedback.json"
        write_json(feedback, demo_feedback())
        self.edit("feedback", 2, "--file", str(feedback))
        self.edit("approve", 3)
        self.assertTrue(current_approval(self.state()))

    def test_review_round_trip_and_edit_invalidates_approval(self):
        self.prepare_demo()
        preview = Path(self.run_ok("preview", self.submission))
        self.assertTrue((preview / "feedbackkaart.pdf").is_file())
        self.assertEqual(Path(self.run_ok("preview", self.submission)), preview)
        correction = self.workspace / "intake/correctie.json"
        write_json(correction, [{"criterion_id": "toets_3-ex02.leesbaar", "points": 0.5,
                                 "rationale": "Hercontrole van de leesbaarheid."}])
        self.edit("marks", 4, "--file", str(correction), "--checked", "all")
        current = self.state()
        self.assertEqual(current["revision"], 5)
        self.assertEqual(current["score"]["totals"]["range"], [31, 31])
        self.assertFalse(current_approval(current))
        self.assertTrue(preview.is_dir())
        self.assertEqual(sha256_file(self.source), self.original_hash)

    def test_new_attempt_cannot_reuse_old_approval(self):
        self.prepare_demo()
        original_binding = self.state()["binding"]
        manifest = self.workspace / "intake/manifest.json"
        contents = read_json(manifest)
        contents["entries"][0]["attempt_slot"] = "andere-poging"
        write_json(manifest, contents)
        self.run_ok("intake")
        result, _, error = cli(self.workspace, "show", self.submission)
        self.assertEqual(result, 1)
        self.assertIn("prepare", error)
        self.run_ok("prepare", self.submission)
        self.assertNotEqual(self.state()["binding"], original_binding)
        self.assertFalse(current_approval(self.state()))

    def test_local_release_and_staleness(self):
        self.prepare_demo()
        status, _, _ = cli(self.workspace, "release", self.submission, "--revision", "3")
        self.assertEqual(status, 1)
        version = Path(self.run_ok("release", self.submission, "--revision", "4"))
        self.assertEqual({p.name for p in version.iterdir()}, {
            "feedbackkaart.pdf", "puntenoverzicht.pdf", "toets-met-feedback.pdf",
        })
        hashes = {path.name: sha256_file(path) for path in version.iterdir()}
        card = PdfReader(version / "feedbackkaart.pdf")
        text = "".join(page.extract_text() for page in card.pages)
        self.assertIn("Nagekeken door je leerkracht", text)
        self.assertIn("31,5 / 45", text)
        self.assertIn("Stemrecht", text)
        self.assertEqual(Path(self.run_ok("release", self.submission, "--revision", "4")), version)
        before_rescan = read_json(self.workspace / "intake/inventory.json")
        self.run_ok("intake")
        self.assertEqual(read_json(self.workspace / "intake/inventory.json"), before_rescan)
        self.assertIn("current", Path(self.run_ok("overview")).read_text(encoding="utf-8-sig"))
        self.source.write_bytes(self.source.read_bytes() + b"\n% gewijzigde bron")
        status, _, _ = cli(self.workspace, "release", self.submission, "--revision", "4")
        self.assertEqual(status, 1)
        self.assertIn("stale", Path(self.run_ok("overview")).read_text(encoding="utf-8-sig"))
        self.assertEqual({path.name: sha256_file(path) for path in version.iterdir()}, hashes)
