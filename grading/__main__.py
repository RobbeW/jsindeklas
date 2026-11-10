"""Command line for the offline JavaScript in de Klas grading workflow."""

import argparse
import sys
from pathlib import Path

from grading import workflow


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workflow.DEFAULT_WORKSPACE, help="privémap")
    parser.add_argument("--rubric", default=workflow.DEFAULT_RUBRIC, help="bestandsnaam in rubrics/")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("intake", help="controleer de inzendingen uit intake/manifest.json")
    prepare = commands.add_parser("prepare", help="maak het nakijkdossier van een aanvaarde inzending")
    prepare.add_argument("submission")
    preview = commands.add_parser("preview", help="maak een privévoorvertoning van de huidige versie")
    preview.add_argument("submission")
    release = commands.add_parser("release", help="plaats een nagekeken set in de privémap voor de leerling")
    release.add_argument("submission")
    release.add_argument("--revision", type=int, required=True)
    commands.add_parser("overview", help="schrijf het privéoverzicht voor de leerkracht")
    from grading.reviewer import add_commands
    add_commands(commands)
    args = parser.parse_args(argv)
    try:
        workspace = workflow.workspace_path(args.workspace)
        if args.command == "intake":
            rows = workflow.intake(workspace)
            for row in rows:
                identifier = row.get("submission_id", "—")
                print(f"{row['disposition']}\t{identifier}\t{', '.join(row['reasons'])}")
            return 0
        if args.command == "prepare":
            baseline = workflow.prepare(workspace, args.submission, args.rubric)
            print(f"Nakijkdossier klaar · {len(baseline['score']['criteria'])} criteria")
            return 0
        if args.command == "preview":
            print(workflow.preview(workspace, args.submission, args.rubric))
            return 0
        if args.command == "release":
            print(workflow.release(workspace, args.submission, args.revision, args.rubric))
            return 0
        if args.command == "overview":
            print(workflow.overview(workspace, args.rubric))
            return 0
        args.handler(workspace, args)
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"Gestopt · {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
