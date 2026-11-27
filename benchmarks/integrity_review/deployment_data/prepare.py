"""Create bounded real-data extracts. Local row and unit names are assigned by the packet generator."""

import csv
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
COMMIT = "1dcc2bf5f955cc1224a3e1307256e1fe86b68dae"
# dataset, subject, acquisition ordering (within subject), signal, response
SOURCES = {
    "sleep": ("lme4/sleepstudy", "Subject", "Days", "Days", "Reaction"),
    "dental": ("nlme/Orthodont", "Subject", "age", "age", "distance"),
    "wafer": ("nlme/Wafer", "Wafer", "Site", "voltage", "current"),
    "soy": ("nlme/Soybean", "Plot", "Time", "Time", "weight"),
    "challenge": ("datasets/Theoph", "Subject", "Time", "Time", "conc"),
    "epilepsy": ("MASS/epil", "subject", "period", "base", "y"),
    "milk": ("nlme/Milk", "Cow", "Time", "Time", "protein"),
    "filtration": ("nlme/Dialyzer", "Subject", "index", "pressure", "rate"),
}


def download(url):
    with urllib.request.urlopen(url, timeout=150) as response:
        return response.read()


def archive_source():
    url = "https://archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip"
    raw = download(url)
    with zipfile.ZipFile(io.BytesIO(raw)) as outer:
        inner = zipfile.ZipFile(io.BytesIO(outer.read("UCI HAR Dataset.zip")))
    rows = []
    for part in ("train", "test"):

        def lines(name):
            return (
                inner.read(f"UCI HAR Dataset/{part}/{name}_{part}.txt")
                .decode()
                .splitlines()
            )

        groups, labels, features = lines("subject"), lines("y"), lines("X")
        # Two windows per subject/activity from the original public row order.
        seen = {}
        for i, (g, y, x) in enumerate(zip(groups, labels, features)):
            key = (g.strip(), y.strip())
            n = seen.get(key, 0)
            seen[key] = n + 1
            if n not in (0, 4):
                continue
            vals = x.split()
            rows.append((f"{part}-{i + 1}", key[0], i + 1, vals[3], vals[4], key[1]))
    return url, raw, rows


def export(slug, rows):
    with (ROOT / (slug + ".csv")).open("w") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["source_id", "unit", "visit", "x", "z", "y"])
        w.writerows(rows)


def main():
    manifest = {}
    for slug, (dataset, unit, visit, signal, resp) in SOURCES.items():
        url = f"https://raw.githubusercontent.com/vincentarelbundock/Rdatasets/{COMMIT}/csv/{dataset}.csv"
        raw = download(url)
        data = list(csv.DictReader(io.StringIO(raw.decode())))
        rows = [
            (r["rownames"], r[unit], r[visit], r[signal], "0", r[resp]) for r in data
        ]
        export(slug, rows)
        manifest[slug] = {
            "url": url,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "columns": [unit, visit, signal, resp],
            "observations": len(rows),
        }
    url, raw, rows = archive_source()
    export("har", rows)
    manifest["har"] = {
        "url": url,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "observations": len(rows),
        "features": ["tBodyAcc-std()-X", "tBodyAcc-std()-Y"],
    }
    for slug, entry in manifest.items():
        entry["extract_sha256"] = hashlib.sha256(
            (ROOT / (slug + ".csv")).read_bytes()
        ).hexdigest()
    (ROOT / "sources.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
