"""Private workspace entry points shared by the local CLI and acceptance tests."""

import hashlib
import json
import tempfile
from pathlib import Path

from grading.common import file_lock, read_json, sha256_file, write_json
from grading.intake import _resolve, scan


REPO = Path(__file__).resolve().parents[1]
DEFAULT_WORKSPACE = REPO / "grading" / "private"
INVENTORY_FORMAT = "jsik-inventory-v1"
DEFAULT_RUBRIC = "toets_3-legacy-741bede-v1.yaml"


def workspace_path(path):
    base = Path(path).resolve()
    if base.is_relative_to(REPO) and not base.is_relative_to(DEFAULT_WORKSPACE):
        raise ValueError("Gebruik grading/private of een afzonderlijke privémap.")
    return base


def private_path(workspace, relative):
    return _resolve(workspace_path(workspace), relative)


def intake(workspace):
    source_root = private_path(workspace, "submissions")
    manifest_path = private_path(workspace, "intake/manifest.json")
    path = private_path(workspace, "intake/inventory.json")
    with file_lock(private_path(workspace, "intake/.lock")):
        if path.exists() and read_json(path).get("format") != INVENTORY_FORMAT:
            raise ValueError("Inventaris heeft een onbekend formaat.")
        manifest = read_json(manifest_path)
        result = scan(source_root, manifest)
        result["format"] = INVENTORY_FORMAT
        for entry, row in zip(manifest["entries"], result["results"]):
            if row["disposition"] == "accepted":
                row["learner"] = {"name": entry["name"], "class_name": entry["class_name"]}
        write_json(path, result)
    return result["results"]


def accepted_submission(workspace, submission_id):
    inventory = read_json(private_path(workspace, "intake/inventory.json"))
    if inventory.get("format") != INVENTORY_FORMAT:
        raise ValueError("Inventaris heeft een onbekend formaat.")
    accepted = [
        row for row in inventory["results"]
        if row.get("submission_id") == submission_id and row["disposition"] == "accepted"
    ]
    if len(accepted) != 1:
        raise ValueError("Geen unieke aanvaarde inzending. Kijk de inventaris na.")
    row = accepted[0]
    source = _resolve(private_path(workspace, "submissions"), row["source"])
    return row, source


def scoring_context(workspace, submission_id, rubric_name=DEFAULT_RUBRIC):
    from grading.rubrics import load_rubric

    if Path(rubric_name).name != rubric_name or not rubric_name.endswith(".yaml"):
        raise ValueError("Geef een bestandsnaam uit de privémap rubrics op.")
    row, source = accepted_submission(workspace, submission_id)
    if sha256_file(source) != row["sha256"]:
        raise ValueError("Het bronbestand is gewijzigd. Voer de intake opnieuw uit.")
    rubric_file = private_path(workspace, f"rubrics/{rubric_name}")
    rubric = load_rubric(rubric_file, row)
    calibration_path = private_path(workspace, f"rubrics/{rubric_name}.calibration.json")
    if not calibration_path.is_file():
        raise ValueError("Voor deze correctiesleutel ontbreekt de D02-kalibratie.")
    calibration = read_json(calibration_path)
    if (
        calibration.get("status") != "accepted"
        or calibration.get("rubric_sha256") != rubric["rubric_sha256"]
        or calibration.get("gate") != "D02"
    ):
        raise ValueError("De D02-kalibratie hoort bij een andere correctiesleutel.")
    identity_fingerprint = hashlib.sha256(json.dumps(
        [row["roster_id"], row["class_id"], row["attempt_slot"]],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    binding = {
        **row["binding"],
        "submission_id": row["submission_id"],
        "source_sha256": row["sha256"],
        "config_fingerprint": row["route_fingerprint"],
        "identity_fingerprint": identity_fingerprint,
        "rubric_id": rubric["rubric_id"],
        "rubric_sha256": rubric["rubric_sha256"],
    }
    review_path = private_path(workspace, f"review/{submission_id}/{rubric['rubric_sha256']}/{identity_fingerprint}")
    return row, source, rubric, binding, review_path


def prepare(workspace, submission_id, rubric_name=DEFAULT_RUBRIC):
    from grading.adapters import extract
    from grading.proposals import register_baseline

    workspace = workspace_path(workspace)
    with file_lock(private_path(workspace, "intake/.lock")):
        row, source, rubric, binding, folder = scoring_context(workspace, submission_id, rubric_name)
        extracted = extract(source, row)
        baseline_file = private_path(workspace, (folder / "baseline.json").relative_to(workspace).as_posix())
        return register_baseline(baseline_file, binding, rubric, extracted)


def review_context(workspace, submission_id, rubric_name=DEFAULT_RUBRIC):
    from grading.proposals import FORMAT

    workspace = workspace_path(workspace)
    row, source, rubric, binding, folder = scoring_context(workspace, submission_id, rubric_name)
    relative = folder.relative_to(workspace)
    baseline_path = private_path(workspace, (relative / "baseline.json").as_posix())
    if not baseline_path.is_file():
        raise ValueError("Maak het nakijkdossier eerst met prepare.")
    baseline = read_json(baseline_path)
    if baseline.get("format") != FORMAT or baseline.get("binding") != binding:
        raise ValueError("Het nakijkdossier hoort bij een andere inzending of sleutel.")
    return {
        "row": row, "source": source, "rubric": rubric, "baseline": baseline,
        "state_path": private_path(workspace, (relative / "review.json").as_posix()),
    }


def preview(workspace, submission_id, rubric_name=DEFAULT_RUBRIC):
    from grading.reports import REPORT_FILES, REPORT_LAYOUT, render_reports
    from grading.review_store import load_review

    with file_lock(private_path(workspace, "intake/.lock")):
        context = review_context(workspace, submission_id, rubric_name)
        state_path = context["state_path"]
        with file_lock(state_path.with_name(state_path.name + ".lock")):
            snapshot = load_review(state_path, context["baseline"], context["rubric"])
            key = snapshot["binding"]["rubric_sha256"]
            revision = snapshot["revision"]
            identity_key = snapshot["binding"]["identity_fingerprint"]
            parent = private_path(workspace, f"reports/preview/{submission_id}/{key}/{identity_key}")
            target = parent / f"r{revision}-{REPORT_LAYOUT}"
            parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            identity = {"format": "jsik-preview-v1", "binding": snapshot["binding"],
                        "revision": revision, "report_layout": REPORT_LAYOUT}
            if target.exists() or target.is_symlink():
                manifest = read_json(target / "manifest.json") if not target.is_symlink() else {}
                if (
                    any(manifest.get(k) != v for k, v in identity.items())
                    or set(manifest.get("files", {})) != set(REPORT_FILES)
                    or any(sha256_file(target / name) != manifest["files"][name] for name in REPORT_FILES)
                ):
                    raise ValueError("Voorvertoning bestaat al maar kan niet worden geverifieerd.")
                return target
            with tempfile.TemporaryDirectory(prefix=".preview-", dir=parent) as stage:
                staged = Path(stage) / "render"
                staged.mkdir(mode=0o700)
                render_reports(staged, context["source"], context["row"]["learner"],
                               context["baseline"], snapshot, final=False)
                manifest = {**identity, "files": {name: sha256_file(staged / name) for name in REPORT_FILES}}
                write_json(staged / "manifest.json", manifest)
                staged.rename(target)
            return target


def release(workspace, submission_id, expected_revision, rubric_name=DEFAULT_RUBRIC):
    from grading.release import promote
    from grading.review_store import load_review

    with file_lock(private_path(workspace, "intake/.lock")):
        context = review_context(workspace, submission_id, rubric_name)
        state_path = context["state_path"]
        with file_lock(state_path.with_name(state_path.name + ".lock")):
            snapshot = load_review(state_path, context["baseline"], context["rubric"])
            if snapshot["revision"] != expected_revision:
                raise ValueError("De revisie is gewijzigd. Kijk de huidige versie na.")

            def validate_current():
                current = review_context(workspace, submission_id, rubric_name)
                if current["state_path"] != state_path:
                    raise ValueError("De binding van de inzending is gewijzigd.")
                checked = load_review(state_path, current["baseline"], current["rubric"])
                if checked != snapshot:
                    raise ValueError("De huidige beoordeling is gewijzigd.")
                return True

            return promote(private_path(workspace, "reports"), context["source"],
                           context["row"]["learner"], context["baseline"], snapshot, validate_current)


def overview(workspace, rubric_name=DEFAULT_RUBRIC):
    from grading.release import release_status, write_overview
    from grading.review_store import current_approval, load_review

    with file_lock(private_path(workspace, "intake/.lock")):
        inventory = read_json(private_path(workspace, "intake/inventory.json"))
        if inventory.get("format") != INVENTORY_FORMAT:
            raise ValueError("Inventaris heeft een onbekend formaat.")
        reports = private_path(workspace, "reports")
        rows = []
        for registration in inventory["results"]:
            submission = registration.get("submission_id")
            row = {
                key: registration.get(key)
                for key in ("roster_id", "class_id", "source")
            }
            row.update(registration.get("learner", {}))
            row.update(assessment_id=registration["binding"]["assessment_id"],
                       revision=registration["binding"]["revision"], status=registration["disposition"])
            snapshot = None
            if row["status"] == "accepted":
                try:
                    context = review_context(workspace, submission, rubric_name)
                    snapshot = load_review(context["state_path"], context["baseline"], context["rubric"])
                except (ValueError, OSError):
                    row["status"] = "dossier-te-controleren"
                else:
                    totals = snapshot["score"]["totals"]
                    row.update(
                        status="goedgekeurd" if current_approval(snapshot) else "na-te-kijken",
                        range=totals["range"], maximum=totals["maximum"],
                    )
            row["release_status"] = release_status(reports, submission, snapshot) if submission else "unreleased"
            rows.append(row)
        return write_overview(reports, rows)
