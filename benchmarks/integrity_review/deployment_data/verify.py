"""Offline independent checks for the released datasets, two scorers and serving manifests."""

import csv
import hashlib
import io
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import deployment  # noqa: E402


def check(predicate, message):
    if not predicate:
        raise ValueError(message)


def reference(model, fit, test, categorical):
    fit = sorted(fit, key=lambda row: row["id"])
    xs = np.array([[r["x"], r["z"]] for r in fit])
    ys = np.array([r["y"] for r in fit])
    groups = np.array([r["unit"] for r in fit])
    targets = np.array([[r["x"], r["z"]] for r in test])
    if categorical:
        labels = np.unique(ys)
        centers = np.array([xs[ys == k].mean(axis=0) for k in labels])
        result = []
        for q, raw in zip(test, targets):
            if model == "reference":
                result.append(labels[np.linalg.norm(centers - raw, axis=1).argmin()])
            else:
                eligible = np.flatnonzero(groups == q["unit"])
                if not len(eligible):
                    eligible = np.arange(len(xs))
                distances = np.linalg.norm(xs[eligible] - raw, axis=1)
                nearest = ys[eligible[np.argsort(distances, kind="stable")[:3]]]
                counts = np.array([sum(nearest == label) for label in labels])
                result.append(labels[counts.argmax()])
        return np.array(result)
    design = np.column_stack([np.ones(len(xs)), xs[:, 0]])
    params = np.linalg.lstsq(design, ys, rcond=None)[0]
    base = params[0] + params[1] * targets[:, 0]
    if model == "reference":
        return base
    residual = ys - design @ params
    offsets = {g: residual[groups == g].mean() for g in set(groups)}
    return base + np.array(
        [offsets.get(q["unit"], np.mean(list(offsets.values()))) for q in test]
    )


def staged(case, filename):
    return list(csv.DictReader(io.StringIO(case["files"][filename])))


def verify(case):
    slug = case["source"]
    policy = deployment.STUDIES[slug][0]
    cross = {r["acquisition"]: r["unit"] for r in staged(case, "assignments.csv")}
    book = {r["unit"]: r for r in staged(case, "registry.csv")}
    fit, test = [], []
    for row in staged(case, "observations.csv"):
        unit = cross[row["acquisition"]]
        enrolled = book[unit]
        in_fit = (
            enrolled["cohort"] == "H"
            if policy == "new"
            else float(row["visit"]) <= float(enrolled["lock_visit"])
        )
        (fit if in_fit else test).append(
            {
                "unit": unit,
                "id": row["id"],
                **{k: float(row[k]) for k in ("visit", "x", "z", "y")},
            }
        )
    provenance = sorted((r["id"], "fit") for r in fit) + sorted(
        (r["id"], "test") for r in test
    )
    as_filed = [(r["id"], r["split"]) for r in staged(case, "run_index.csv")]
    expect_approval = set(provenance) == set(as_filed)
    check(
        expect_approval == (case["gold"]["published_run"] == "certify"),
        case["id"] + " certification",
    )
    check(expect_approval == (case["variant"] == "intact"), "Twins not distinct")
    _, hidden, *_ = deployment.partition(slug)
    if policy == "new":
        check(
            not ({r["unit"] for r in fit + test} & {r["unit"] for r in hidden}),
            "Reserved unit seen",
        )
    else:
        for r in hidden:
            previous = [q["visit"] for q in fit + test if q["unit"] == r["unit"]]
            check(previous and max(previous) < r["visit"], "Reserved visit seen")
    for target, name in ((test, "public"), (hidden, "private")):
        for model in ("candidate", "reference"):
            predictions = reference(model, fit, target, slug == "har")
            ys = np.array([r["y"] for r in target])
            loss = (
                (predictions != ys).mean()
                if slug == "har"
                else np.abs(predictions - ys).mean()
            )
            expected = (
                case["gold"][model + "_loss"]
                if name == "public"
                else case["reference"]["private_losses"][model]
            )
            check(abs(loss - expected) < 1.01e-6, case["id"] + "/" + name + "/" + model)
    release = {
        "fit_ids": [r["id"] for r in fit],
        "test_ids": [r["id"] for r in test],
        "recipe": case["gold"]["service_recipe"],
    }
    check(
        all(deployment.validate(case, {"release.json": json.dumps(release)}).values()),
        "Valid release rejected",
    )
    release["fit_ids"].append(release["test_ids"][0])
    check(
        not any(
            deployment.validate(case, {"release.json": json.dumps(release)}).values()
        ),
        "Contaminated release accepted",
    )


if __name__ == "__main__":
    sources = json.loads((HERE / "sources.json").read_text())
    for name, record in sources.items():
        check(
            hashlib.sha256((HERE / (name + ".csv")).read_bytes()).hexdigest()
            == record["extract_sha256"],
            name,
        )
    cases = deployment.cases("dev") + deployment.cases("holdout")
    for case in cases:
        verify(case)
    print(
        f"Checked {len(sources)} pinned observational extracts and {len(cases)} public and private prediction audits."
    )
