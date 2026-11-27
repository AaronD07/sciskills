"""Exploratory repair and preservation checks on known development errors and their twins."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile

from experiment import (
    ARMS,
    CARDS,
    FAMILIES,
    HERE,
    REPO,
    SEED,
    authenticate,
    checksum,
    digest,
    grade,
    inputs,
    load_cases,
    materialize,
    packed,
    replay,
    result_dir,
    run_session,
    write_atomic,
)
import random


def selected(root, mode):
    rows = replay(root, mode, "dev")
    errors = {(r["source"], r["model_key"]) for r in rows if r["grade"]["gate_errors"]}
    return [r for r in rows if (r["source"], r["model_key"]) in errors]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["run", "replay"])
    ap.add_argument("mode", choices=FAMILIES)
    ap.add_argument("--results", type=Path, default=HERE / "results")
    ap.add_argument("--private", type=Path)
    args = ap.parse_args()
    cases = load_cases(args.mode, "dev")
    drafts = selected(args.results, args.mode)
    if not drafts:
        raise ValueError("No confirmed development errors")
    out = result_dir(args.results, args.mode, "development_review")
    archive = out / "sessions.jsonl"
    manifest = out / "protocol.json"
    rng = random.Random(SEED)
    schedule = [(d, arm) for d in drafts for arm in ARMS]
    rng.shuffle(schedule)
    ids = [d["id"] + "_" + arm for d, arm in schedule]
    if args.action == "run":
        if (
            manifest.exists()
            or args.private is None
            or args.private.resolve().is_relative_to(REPO)
        ):
            raise ValueError("Specify a fresh cohort and an external private directory")
        out.mkdir(parents=True, exist_ok=True)
        private = args.private.resolve() / "development_review" / args.mode
        private.mkdir(parents=True, exist_ok=True)
        cards = {
            a: (
                REPO
                / "skills"
                / CARDS["general" if a == "general" else args.mode]
                / "SKILL.md"
            ).read_text()
            for a in ("general", "specialist")
        }
        write_atomic(
            manifest,
            {
                "clients": authenticate(),
                "order": ids,
                "skills": cards,
                "dev_archive_hash": checksum(
                    result_dir(args.results, args.mode, "dev") / "sessions.jsonl"
                ),
            },
        )

        def run(job):
            draft, arm = job
            case = cases[draft["case"]]
            f = inputs(case, arm, draft, cards)
            row = run_session(
                draft["model_key"],
                f,
                "review",
                Path(tempfile.mkdtemp(dir=private)) / "private",
            )
            row.update(
                id=draft["id"] + "_" + arm,
                parent=digest(draft),
                arm=arm,
                case=case["id"],
                model_key=draft["model_key"],
                input_hash=digest(f),
            )
            row["grade"] = grade(case, materialize(f, row), row["status"])
            return row

        with ThreadPoolExecutor(max_workers=6) as pool:
            rows = list(pool.map(run, schedule))
        archive.write_text("".join(packed(r) + "\n" for r in rows))
        write_atomic(out / "archive.json", {"sha256": checksum(archive)})
    proto = json.loads(manifest.read_text())
    rows = [json.loads(line) for line in archive.read_text().splitlines()]
    if (
        json.loads((out / "archive.json").read_text())["sha256"] != checksum(archive)
        or ids != [r["id"] for r in rows]
        or ids != proto["order"]
        or proto["dev_archive_hash"]
        != checksum(result_dir(args.results, args.mode, "dev") / "sessions.jsonl")
    ):
        raise ValueError("Archive or schedule mismatch")
    for (draft, arm), r in zip(schedule, rows):
        case = cases[draft["case"]]
        f = inputs(case, arm, draft, proto["skills"])
        if (
            digest(draft) != r["parent"]
            or digest(f) != r["input_hash"]
            or grade(case, materialize(f, r), r["status"]) != r["grade"]
        ):
            raise ValueError(r["id"])
    print(
        f"Verified {len(rows)} diagnostic reviews of {len(drafts)} development drafts."
    )


if __name__ == "__main__":
    main()
