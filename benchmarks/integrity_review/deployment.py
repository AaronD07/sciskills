"""Predictive release audits on repeated observations from nine separate studies."""
import csv
from collections import defaultdict
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path

DATA = Path(__file__).with_name("deployment_data")
SPEC = importlib.util.spec_from_file_location("integrity_registered_models", DATA / "models.py")
models = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(models)

# Study, target population, field context. The signed local release policies are constructed.
STUDIES = {
    "har": ("new", "UCI phone activity windows", "wearer", "two body-acceleration dispersion features", "activity class"),
    "sleep": ("future", "sleep-deprivation reaction times", "participant", "days under protocol", "reaction time in ms"),
    "dental": ("new", "orthodontic growth series", "child", "age in years", "distance in mm"),
    "wafer": ("new", "wafer electrical characterization", "wafer", "applied voltage", "current"),
    "soy": ("future", "soybean growth trial", "plot", "sampling time", "leaf weight"),
    "challenge": ("new", "theophylline concentration series", "participant", "sample time", "drug concentration"),
    "epilepsy": ("future", "repeated seizure counts", "participant", "pretreatment count", "follow-up count"),
    "milk": ("future", "milk protein series", "cow", "sampling time", "milk protein content"),
    "filtration": ("new", "hemodialyzer performance measurements", "dialyzer series", "transmembrane pressure", "filtration rate"),
}
SPLITS = {"dev": ("har", "sleep", "dental"),
          "holdout": ("wafer", "soy", "challenge", "epilepsy", "milk", "filtration")}
MODEL_TEXT = (DATA / "models.py").read_text()


def key(*parts):
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()


def csv_text(header, rows):
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buf.getvalue()


def partition(slug):
    policy = STUDIES[slug][0]
    with (DATA / f"{slug}.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    by_unit = defaultdict(list)
    for row in rows:
        by_unit[row["unit"]].append(row)
    units = sorted(by_unit, key=lambda u: key(slug, u))
    reserve = max(1, len(units)//5)
    validation = max(1, len(units)//4)
    decoded, joins, book = [], {}, {}
    expected, secret = {}, []
    for index, u in enumerate(units):
        obs = sorted(by_unit[u], key=lambda r: (float(r["visit"]), int(r["source_id"].split('-')[-1])))
        cohort = "R" if index < reserve else "Q" if index < reserve + validation else "H"
        stable = "E" + key(slug, u)[:8]
        visits = sorted({float(r["visit"]) for r in obs})
        # Public calibration uses strictly earlier visits; future transfer contains only the final block.
        cut = visits[max(0, len(visits)//2 - 1)]
        private_start = visits[max(1, len(visits)*3//4)] if len(visits) > 1 else visits[-1]
        for pos, r in enumerate(obs):
            epoch = float(r["visit"])
            role = ("private" if cohort == "R" else "test" if cohort == "Q" else "fit") if policy == "new" else (
                "private" if epoch >= private_start else "test" if epoch > cut else "fit")
            oid = "o" + key(slug, r["source_id"])[:9]
            local = "a" + key(slug, stable, pos % 2)[:8]
            y = float(r["y"])
            normalized = dict(id=oid, unit=stable, alias=local, visit=epoch, x=float(r["x"]), z=float(r["z"]), y=y)
            if role == "private":
                secret.append(normalized)
                continue
            decoded.append(normalized)
            joins[local] = stable
            book[stable] = (cohort if policy == "new" else "H", cut)
            expected[oid] = role
    return sorted(decoded, key=lambda r:r["id"]), sorted(secret, key=lambda r:r["id"]), joins, book, expected


def broken_split(slug, obs, expected):
    # An archive export indexed by accession instead of resolved lineage, or by ingest order.
    # Replace one accession's memberships in both directions; the job-row counts may still look correct.
    proposal = dict(expected)
    first = sorted((r for r in obs if expected[r["id"]] == "fit"), key=lambda r:key("fit", slug, r["alias"]))[0]
    other = sorted((r for r in obs if expected[r["id"]] == "test"), key=lambda r:key("test", slug, r["alias"]))[0]
    if STUDIES[slug][0] == "new":
        for r in obs:
            if r["alias"] == first["alias"]:
                proposal[r["id"]] = "test"
            elif r["alias"] == other["alias"]:
                proposal[r["id"]] = "fit"
    else:
        # A late calibration row and early observation were attached to the wrong snapshot.
        proposal[first["id"]], proposal[other["id"]] = "test", "fit"
    return proposal


def sides(obs, membership):
    return tuple([r for r in obs if membership[r["id"]] == side] for side in ("fit", "test"))


def estimates(slug, fit, test):
    return {name: models.loss(name, fit, test, slug == "har") for name in ("reference", "candidate")}


def population_contract(slug, unit):
    if STUDIES[slug][0] == "new":
        return (f"The service predicts outcomes on a previously unobserved {unit}. A locked evaluation uses all "
                "acquisitions from the Q registration cohort for assessment and all H acquisitions for fitting. "
                "Resolve enrollment through assignments.csv and registry.csv. The acquisition code is issued locally "
                "and a physical unit can be assigned several codes. No row is optional.")
    return (f"The service forecasts later outcomes on existing {unit}s. For each registered unit use all observations "
            "through its lock_visit inclusive for fitting, and its remaining supplied observations for assessment. "
            "Acquisition codes are local; reconcile them with the physical unit before using the appropriate lock. "
            "Returning units are part of the intended population. No row is optional.")


def make(slug, variant, data):
    policy, title, unit, features, outcome = STUDIES[slug]
    obs, secret, joins, book, expected = data
    proposed = broken_split(slug, obs, expected) if variant == "compromised" else expected
    fit, test = sides(obs, expected)
    ref = estimates(slug, fit, test)
    proposed_scores = estimates(slug, *sides(obs, proposed))
    recommendation = "candidate" if ref["candidate"] + 1e-10 < ref["reference"] else "reference"
    gold = {"published_run": "certify" if proposed == expected else "withdraw",
            "service_recipe": recommendation, "reference_loss": round(ref["reference"], 6),
            "candidate_loss": round(ref["candidate"], 6)}
    task = (f"Decide whether the attached {title} evaluation can be signed as filed. Prepare the service "
            "handoff for the registered population. Use protocol.md and the original packet to deliver "
            "answer.json and release.json. Both files are consumed by the deployment team. "
            "This is a data-methods exercise using historical observations.\n")
    contract = f"""The release target is {outcome}. Inputs are {features}. {population_contract(slug,unit)}

models.py is the registered executable for both recipes. Its numeric input rows have id, unit (stable key),
x, z and y; use floats for x, z and y. The measurement file uses an acquisition code instead of the stable key.
Set category={slug == "har"} when calling loss() or predict(). Use numeric error fraction for classification
and mean absolute error for regression. Use the candidate only if its target-consistent loss is strictly
lower than the reference by more than 1e-10. A tie retains the reference. The deployment reserve will be
released to the independent verifier later. Service builds are fitted only on the locked fitting rows.

answer.json requires published_run ("certify" if the filed evaluation followed this contract, "withdraw"
otherwise), service_recipe ("candidate" or "reference"), and both target-consistent losses reference_loss
and candidate_loss rounded to six decimals. An accurate reported score on a different population cannot
support a release. Returning an audit decision alone does not register a service. In release.json submit
a JSON object with recipe (the chosen registered recipe), fit_ids and test_ids (the complete lists of
observation IDs for fitting and assessing under this protocol). Order is immaterial.
"""
    files = {
        "TASK.md": task,
        "protocol.md": contract,
        "models.py": MODEL_TEXT,
        "observations.csv": csv_text(("id","acquisition","visit","x","z","y"),
            ((r["id"],r["alias"],r["visit"],r["x"],r["z"],r["y"]) for r in obs)),
        "assignments.csv": csv_text(("acquisition","unit"), sorted(joins.items())),
        "registry.csv": csv_text(("unit","cohort","lock_visit"), ((u,*v) for u,v in sorted(book.items()))),
        "run_index.csv": csv_text(("id","split"), sorted(proposed.items())),
        "evaluation.md": f"The analysis release used run_index.csv for its audited split. Reference loss {proposed_scores['reference']:.6f}. Candidate loss {proposed_scores['candidate']:.6f}. The loader found {len(obs)} distinct observation keys and recorded one assignment per key. Release status: awaiting signature.\n",
    }
    return {"id":f"deployment-{slug}-{variant}", "source":slug, "mode":"deployment", "variant":variant,
            "files":files, "gold":gold, "critical":["published_run","service_recipe","fit_and_test_membership","private_prediction_replay"],
            "gate_keys":["published_run","service_recipe"],
            "tolerance":{"reference_loss":1.01e-6,"candidate_loss":1.01e-6},
            "reference":{"fit":sorted(r["id"] for r in fit), "test":sorted(r["id"] for r in test),
                         "private_n":len(secret), "private_losses": estimates(slug, fit, secret)}}


def cases(split):
    out = []
    for slug in SPLITS[split]:
        data = partition(slug)
        for variant in ("compromised","intact"):
            out.append(make(slug, variant, data))
    return out


def validate(case, files):
    """Replay the submitted declarative pipeline on reserved entities or future records."""
    checks = {"fit_and_test_membership":False, "private_prediction_replay":False}
    try:
        release = json.loads(files.get("release.json","{}"))
        recipe = release["recipe"]
        if recipe not in ("candidate","reference"):
            return checks
        ids, tests = sorted(release["fit_ids"]), sorted(release["test_ids"])
        ref = case["reference"]
        checks["fit_and_test_membership"] = ids == ref["fit"] and tests == ref["test"]
        slug = case["source"]
        obs,private,*_ = partition(slug)
        public = {r["id"]:r for r in obs}
        train = [public[i] for i in ids]
        actual = models.predict(recipe, train, private, slug == "har")
        expected_train = [public[i] for i in ref["fit"]]
        expected = models.predict(case["gold"]["service_recipe"], expected_train, private, slug == "har")
        loss = models.loss(recipe, train, private, slug == "har")
        checks["private_prediction_replay"] = (checks["fit_and_test_membership"] and
            recipe == case["gold"]["service_recipe"] and
            all(math.isclose(a,b,abs_tol=1e-9,rel_tol=1e-12) for a,b in zip(actual,expected)) and
            len(actual)==len(expected)==ref["private_n"] and
            math.isclose(loss,ref["private_losses"][recipe],abs_tol=1e-9,rel_tol=1e-12))
    except (TypeError, ValueError, KeyError, ZeroDivisionError, AttributeError):
        pass
    return checks
