"""Re-create compact source tables, including UCI daily sums of actual analyzer values."""

import csv
import hashlib
import io
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent
SOURCES = json.loads((ROOT / "sources.json").read_text())


def check_digest(content, expected):
    if hashlib.sha256(content).hexdigest() != expected:
        raise ValueError("The fetched source differs from the frozen manifest")


def source_entry(name):
    source = SOURCES[name]
    content = urlopen(source["url"], timeout=45).read()
    check_digest(content, source["sha256"])
    (ROOT / f"{name}.csv").write_bytes(content)


def air_quality():
    source = SOURCES["air"]
    data = urlopen(source["url"], timeout=45).read()
    raw = ZipFile(io.BytesIO(data)).read(source["file_in_zip"])
    check_digest(raw, source["sha256"])
    groups = defaultdict(list)
    for row in csv.DictReader(io.StringIO(raw.decode("latin1")), delimiter=";"):
        if row["Date"] and row["Date"].endswith(("/04/2004", "/06/2004")):
            groups[row["Date"]].append(row)
    dst = io.StringIO()
    writer = csv.writer(dst, lineterminator="\n")
    writer.writerow(["date", "channel", "sample_slots", "available", "value_sum"])
    for date, rows in sorted(groups.items()):
        for channel in ("NMHC(GT)", "NO2(GT)", "PT08.S2(NMHC)"):
            values = [int(r[channel]) for r in rows if r[channel] != "-200"]
            writer.writerow([date, channel, len(rows), len(values), sum(values)])
    content = dst.getvalue().encode()
    check_digest(content, source["daily_sha256"])
    (ROOT / "air_days.csv").write_bytes(content)


if __name__ == "__main__":
    with ThreadPoolExecutor(5) as pool:
        list(pool.map(source_entry, sorted(set(SOURCES) - {"air"})))
    air_quality()
