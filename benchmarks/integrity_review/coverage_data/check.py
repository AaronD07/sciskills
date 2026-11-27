"""Reconstruct all coverage decisions from participant packets, independently of the key."""

import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "integrity_coverage", HERE.parent / "coverage.py"
)
coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)


def rows(files, name):
    return list(csv.DictReader(io.StringIO(files[name])))


def sums_by_group(data, group, field):
    totals = {}
    for row in data:
        totals.setdefault(row[group], []).append(int(row[field]))
    return totals


def expected_units(source, f):
    """Return a unit -> covered mapping determined solely from the staged records."""
    if source == "nist-starts":
        registry = json.loads(f["initializations.json"])
        bundles = json.loads(f["bundle_index.json"])
        used = [
            bundles[j["loaded_bundle"]]
            for j in json.loads(f["run_records.json"])
            if j["terminal"] in ("converged", "iteration-limit")
        ]
        return {
            f"{name}/{level}": {
                "input_sha256": hashlib.sha256(
                    f[f"data/{name}.csv"].encode()
                ).hexdigest(),
                "parameters": vector,
            }
            in used
            for name, v in registry.items()
            for level, vector in zip(("far", "near"), v)
        }

    if source == "sleep-restriction":
        lineage = json.loads(f["lineage.json"])
        outcomes = {
            r["ticket"]: lineage[r["input_ref"]] for r in rows(f, "summaries.csv")
        }
        delivered = {r["unit"]: outcomes[r["ticket"]] for r in rows(f, "delivery.csv")}
        expected = {}
        for r in rows(f, "measurements.csv"):
            day = int(r["Days"])
            if 2 <= day <= 9:
                phase = "restricted" if day > 2 else "baseline"
                expected.setdefault(r["Subject"] + "/" + phase, []).append(
                    r["rownames"]
                )
        return {k: sorted(v) == sorted(delivered[k]) for k, v in expected.items()}

    if source == "orange-growth":
        data = rows(f, "trees.csv")
        result = {}
        for r in rows(f, "queue.csv"):
            age = sorted(int(x["age"]) for x in data if x["Tree"] == r["series"])
            desired = age[:2] if r["phase"] == "early" else age[-2:]
            item = json.loads(f["outputs/" + r["job"] + ".json"])
            result[r["series"] + "/" + r["phase"]] = [
                item["age_first"],
                item["age_last"],
            ] == desired
        return result

    if source == "insect-sprays-release":
        units = {}
        for r in rows(f, "observations.csv"):
            units.setdefault(r["spray"], set()).add(r["rownames"])
        out = {
            r["spray"]: set(r["plot_ids"].split())
            for r in rows(f, "historical_results.csv")
        }
        return {k: members == out[k] for k, members in units.items()}

    if source == "enzyme-rate-panels":
        expected = {}
        for r in rows(f, "kinetics.csv"):
            expected.setdefault(r["state"] + "/" + r["conc"], []).append(r["rownames"])
        index = dict(line.split("\t") for line in f["tube_key.tsv"].splitlines()[1:])
        delivered = {
            r["trace"]: r["included_observations"].split(",")
            for r in rows(f, "archive.csv")
        }
        return {
            u: sorted(m) == sorted(delivered[index[u]]) for u, m in expected.items()
        }

    if source == "indometh-release-vintage":
        data = rows(f, "samples.csv")
        events = json.loads(f["changes.json"])
        jobs = {
            r["subject"] + "/" + r["last_hour"]: r["job"]
            for r in rows(f, "endpoint_index.csv")
        }
        result = {}
        for sub in {r["Subject"] for r in data}:
            for end in (4, 8):
                key = f"{sub}/{end}"
                event = max(
                    (
                        r
                        for r in events
                        if r["job"] == jobs[key] and r["archive_minute"] <= 150
                    ),
                    key=lambda r: r["archive_minute"],
                )
                count = sum(
                    r["Subject"] == sub and float(r["time"]) <= end for r in data
                )
                result[key] = (
                    event["event"] == "published"
                    and event["actual_subject"] == sub
                    and event["data_until"] == end
                    and event["n_draws"] == count
                )
        return result

    if source == "toothgrowth-method-comparison":
        data = rows(f, "lengths.csv")
        jobs = {j["endpoint"]: j for j in json.loads(f["jobs.json"])}
        valid = {}
        for d in {r["dose"] for r in data}:
            for func in ("mean", "median"):
                key = d + "/" + func
                j = jobs[key]
                valid[key] = j["function"] == func and all(
                    sorted(j[field])
                    == sorted(
                        r["rownames"]
                        for r in data
                        if r["dose"] == d and r["supp"] == supp
                    )
                    for field, supp in (("left_rows", "OJ"), ("right_rows", "VC"))
                )
        return valid

    if source == "rock-tile-manifest":
        receipts = {r["sample"]: r for r in rows(f, "submissions.csv")}
        expected = {}
        main = rows(f, "rock.csv")
        for offset in range(0, len(main), 4):
            key = f"R{offset // 4 + 1:02d}"
            fname = f"tiles/{key}.csv"
            digest = hashlib.sha256(f[fname].encode()).hexdigest()
            expected[key] = (
                rows(f, fname) == main[offset : offset + 4]
                and digest == receipts[key]["stream_sha256"]
            )
        return expected

    if source == "feed-robustness-tests":
        jobs = {r["unit"]: r["job"] for r in rows(f, "registry.csv")}
        events = json.loads(f["event_log.json"])
        expected = {}
        for feed in {r["feed"] for r in rows(f, "weights.csv")}:
            for method in ("average", "spread"):
                unit = feed + "/" + method
                path = sorted(
                    (r for r in events if r["job"] == jobs[unit]),
                    key=lambda r: r["step"],
                )
                expected[unit] = path[0].get("exec_mode") == "calculate" and path[-1][
                    "control"
                ] in ("OK", "NUMERICAL_FAILURE")
        return expected

    raise ValueError(source)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    manifest = json.loads((HERE / "sources.json").read_text())
    for name, entry in manifest.items():
        require(
            hashlib.sha256((HERE / name).read_bytes()).hexdigest() == entry["sha256"],
            name,
        )
    cases = coverage.cases("dev") + coverage.cases("holdout")
    for case in cases:
        units = expected_units(case["source"], case["files"])
        missing = sorted(k for k, valid in units.items() if not valid)
        gold = {
            "release": not missing,
            "outstanding": missing,
            "scheduled_units": len(units),
            "covered_units": len(units) - len(missing),
        }
        require(gold == case["gold"], case["id"])
        if case["source"] == "insect-sprays-release":
            counts = sums_by_group(
                rows(case["files"], "observations.csv"), "spray", "count"
            )
            table = "spray,plots,total_count,mean_count\n" + "".join(
                f"{k},{len(vals)},{sum(vals)},{sum(vals) / len(vals):.6f}\n"
                for k, vals in counts.items()
            )
            require(
                coverage.validate(case, {"release.csv": table})
                == {"release_table": True},
                "reference release",
            )
            require(
                coverage.validate(case, {"release.csv": table.splitlines()[0]})
                == {"release_table": False},
                "incomplete release",
            )
    print(f"Verified {len(manifest)} source files and {len(cases)} audit decisions.")


if __name__ == "__main__":
    main()
