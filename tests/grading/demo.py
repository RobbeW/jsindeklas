"""Generate an entirely fictional submission for local workflow verification."""

import argparse
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from grading.common import sha256_file, write_json
from grading.intake import BINDING, CONFIG


ANSWERS = [
    ('const bedrag = 64;\nif (bedrag > 60) {\n  console.log("Korting toegepast.");\n}', 'Korting toegepast.'),
    ('const bedrag = 46;\nif (bedrag >= 50) {\n  console.log("Gratis verzending.");\n}'
     '\nelse {\n  console.log("Verzendkosten betalen.");\n}', 'Verzendkosten betalen.'),
    ('let bedrag = 64;\nif (bedrag >= 60) {\n  bedrag *= 0.9;\n}'
     '\nelse {\n  bedrag += 5;\n}\nconsole.log("Nieuw bedrag: " + bedrag);', 'Nieuw bedrag: 57.6'),
    ('const temperatuur = 28;\nif (temperatuur < 18) {\n  console.log("Koud.");\n}'
     '\nelse if (temperatuur < 25) {\n  console.log("Aangenaam.");\n}'
     '\nelse {\n  console.log("Warm.");\n}', 'Warm.'),
    ('console.log("Batterij laag.");', 'Batterij laag.'),
    ('const snelheid = 0;\nif (snelheid == 0) {\n  console.log("Stilstand.");\n}'
     '\nelse {\n  console.log("In beweging.");\n}', 'Stilstand.'),
    ('const postcode = "9000";\nif (postcode === "9000") {\n  console.log("Postcode 9000 is voor Gent (stad).");\n}'
     '\nelse if (postcode === "9080") {\n  console.log("Postcode 9080 is voor Lochristi.");\n}'
     '\nelse if (postcode === "9940") {\n  console.log("Postcode 9940 is voor Evergem.");\n}'
     '\nelse {\n  console.log("Onbekende postcode.");\n}', 'Postcode 9000 is voor Gent (stad).'),
    ('', '(geen uitvoer)'),
    ('const punten = 37;\nconst maximum = 50;\nconst percentage = punten * 100 / maximum;\n'
     'let letter;\nif (percentage >= 85) {\n  letter = "A";\n}'
     '\nelse if (percentage >= 70) {\n  letter = "B";\n}'
     '\nelse if (percentage >= 50) {\n  letter = "C";\n}'
     '\nelse {\n  letter = "D";\n}', '(geen uitvoer)'),
]

DEMO_MARKS = [
    (0, 1, 2, 0.5), (1, 1, 2, 1), (0, 1, 2, 0.5),
    (1, 1, 2, 1), (0, 0.5, 0, 0), (1, 1, 1, 1),
    (1, 1, 2, 1), (0, 0, 0, 0), (1, 1, 2, 1),
]


def demo_rubric():
    return {
        "schema_version": "1.0", "rubric_id": "synthetic-demo-v1",
        "assessment_id": BINDING["assessment_id"], "variant": BINDING["variant"],
        "revision": BINDING["revision"], "prompt_source_blob": CONFIG["source_blob"],
        "status": "synthetic", "teacher_calibration_gate": "D02",
        "total_max": 45, "question_max": 5, "score_step": 0.5, "caps": [],
        "criteria": {
            "functioneel": {"max": 1, "levels": [0, 1]},
            "leesbaar": {"max": 1, "levels": [0, 0.5, 1]},
            "programmeerconcept": {"max": 2, "levels": [0, 1, 2]},
            "wiskundeconcept": {"max": 1, "levels": [0, 0.5, 1]},
        },
        "questions": {
            q["id"]: {
                "functioneel": "Fictieve demonstratie van het nakijken.",
                "programmeerankers": ["Gebruikt selectie.", "Bouwt duidelijke takken op."],
                "wiskundeconcept": "Past de gegeven grenzen toe.",
                "probes": [],
            }
            for q in CONFIG["questions"]
        },
    }


def demo_marks():
    suffixes = tuple(demo_rubric()["criteria"])
    return [
        {
            "criterion_id": f"{question['id']}.{suffix}",
            "points": points,
            "evidence_ids": [f"{question['id']}:code"],
            "rationale": "Fictief voorbeeld voor de demonstratie.",
        }
        for question, scores in zip(CONFIG["questions"], DEMO_MARKS)
        for suffix, points in zip(suffixes, scores)
    ]


def create_demo(workspace):
    workspace = Path(workspace)
    workspace.mkdir(mode=0o700)
    submissions = workspace / "submissions"
    submissions.mkdir(mode=0o700)
    path = submissions / "demo.pdf"
    pdf = canvas.Canvas(str(path), pagesize=A4, invariant=True)

    def lines(items):
        text = pdf.beginText(36, 806)
        text.setFont("Courier", 9)
        text.setLeading(12)
        for line in items:
            text.textLine(line)
        pdf.drawText(text)

    lines([
        "JavaScript in de Klas - Gebundelde export",
        "Naam: Demo Leerling",
        "Klas: TEST",
        "Datum: 01/01/2000",
        "Inhoud:",
        *[q["title"] for q in CONFIG["questions"]],
    ])
    pdf.showPage()
    for number, (question, answer) in enumerate(zip(CONFIG["questions"], ANSWERS), 1):
        code, console = answer
        lines([
            f"Oefening {number} / 9", question["title"], "Opdracht:", "Gegeven",
            "Code:", *question["prompt"].splitlines(), *code.splitlines(),
            "Console-uitvoer:", console,
        ])
        pdf.showPage()
        lines([
            "Beoordeling & feedback leerkracht:", "Verificatiegegevens:",
            "Bewaard op: 01/01/2000", "Pagina-URL: https://example.invalid/evaluaties/toets_4.html",
            "Browser: TECHNISCH-ALLEEN-DEMO",
        ])
        pdf.showPage()
    pdf.save()
    write_json(workspace / "intake" / "manifest.json", {"entries": [{
        "roster_id": "demo-pupil", "class_id": "demo-class",
        "name": "Demo Leerling", "class_name": "TEST",
        "assessment_id": "toets_3", "attempt_slot": "demo", "source": "demo.pdf",
    }]})
    rubric_path = workspace / "rubrics" / "demo.yaml"
    write_json(rubric_path, demo_rubric())
    write_json(workspace / "rubrics" / "demo.yaml.calibration.json", {
        "gate": "D02", "status": "accepted", "rubric_sha256": sha256_file(rubric_path),
        "scope": "synthetic-only",
    })
    write_json(workspace / "intake" / "demo-marks.json", demo_marks())
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("new_workspace", type=Path)
    args = parser.parse_args()
    print(create_demo(args.new_workspace))
