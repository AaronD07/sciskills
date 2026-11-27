"""Matched handoffs for checking scientific execution coverage.

Only the entries of files are participant material. Each ledger describes a
constructed exercise built around the accompanying source observations.
"""

import csv
import hashlib
import io
import json
from pathlib import Path

DATA = Path(__file__).with_name("coverage_data")
PAIRS = ("intact", "compromised")


def dump(rows):
    return json.dumps(rows, indent=2, sort_keys=True) + "\n"


def table(rows):
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=rows[0], lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def raw(name):
    return (DATA / (name + ".csv")).read_text()


def records(name):
    return list(csv.DictReader(io.StringIO(raw(name))))


def checksum(text):
    return hashlib.sha256(text.encode()).hexdigest()


def packet(study, variant, task, files, expected, outstanding):
    gold = {
        "release": not outstanding,
        "scheduled_units": expected,
        "covered_units": expected - len(outstanding),
        "outstanding": sorted(outstanding),
    }
    instructions = (
        "\n\nFile answer.json with exactly four fields. release (boolean) authorizes the "
        "handoff as covering its full registered scope; scheduled_units and covered_units "
        "are integer counts of required scientific units and evidenced units respectively. "
        "outstanding is a JSON list of unresolved unit IDs as strings in lexical order, "
        "or [] when all are covered. You are auditing the archived run. The scope and "
        "the dispatch records are immutable; new runs are outside this audit.\n"
    )
    return {
        "id": f"coverage-{study}-{variant}",
        "source": study,
        "mode": "coverage",
        "variant": variant,
        "files": {"TASK.md": task + instructions, **files},
        "gold": gold,
        "critical": ["release", "outstanding"],
        "gate_keys": ["release"],
    }


def nist(variant):
    starts = {
        "Misra1a": [[500, 0.0001], [250, 0.0005]],
        "Chwirut1": [[0.1, 0.01, 0.02], [0.15, 0.008, 0.010]],
        "Chwirut2": [[0.1, 0.01, 0.02], [0.15, 0.008, 0.010]],
    }
    units = [
        (name, label, vector)
        for name, vectors in starts.items()
        for label, vector in zip(("far", "near"), vectors)
    ]
    events, queue, bundles = [], [], {}
    files = {f"data/{name}.csv": raw(name) for name in starts}
    for i, (name, start, values) in enumerate(units):
        loaded = (
            starts[name][1]
            if variant == "compromised" and (name, start) == ("Chwirut2", "far")
            else values
        )
        data_hash = checksum(raw(name))
        bundle = dump({"input_sha256": data_hash, "parameters": loaded})
        token = checksum(bundle)
        bundles[token] = json.loads(bundle)
        queue.append(
            {"label": f"{name}/{start}", "worker": f"w{i + 6}", "state": "finished"}
        )
        events.append(
            {
                "worker": f"w{i + 6}",
                "loaded_bundle": token,
                "solver": "LM",
                "terminal": "converged" if i != 2 else "iteration-limit",
                "iterations": [7, 4, 64, 12, 13, 7][i],
            }
        )
    files.update(
        {
            "protocol.md": "Enroll Misra1a, Chwirut1 and Chwirut2. For each series, evaluate LM from "
            "both its registered far and near parameter vectors. A numerical iteration-limit outcome "
            "is a valid completed robustness test. Unit ID is series/start. The iteration record's "
            "loaded_bundle identifies the measured file and vector consumed by the process.\n",
            "initializations.json": dump(starts),
            "queue.csv": table(queue),
            "run_records.json": dump(events),
            "bundle_index.json": dump(bundles),
            "handoff.txt": "Batch NLS-37 closed. The dashboard shows all submitted workers in a terminal state.\n",
        }
    )
    return packet(
        "nist-starts",
        variant,
        "Can we sign off on the registered nonlinear-fit robustness study?",
        files,
        6,
        [] if variant == "intact" else ["Chwirut2/far"],
    )


def sleep(variant):
    rows = records("sleepstudy")
    subjects = sorted({r["Subject"] for r in rows})
    index, extractions, queue = {}, [], []
    for i, subject in enumerate(subjects):
        for phase, lo, hi in [("baseline", 2, 2), ("restricted", 3, 9)]:
            selected = [
                r
                for r in rows
                if r["Subject"] == subject and lo <= int(r["Days"]) <= hi
            ]
            if variant == "compromised" and subject == "350" and phase == "restricted":
                selected = [
                    r
                    for r in rows
                    if r["Subject"] == subject and 2 <= int(r["Days"]) < 9
                ]
            members = [r["rownames"] for r in selected]
            digest = checksum(",".join(members))
            index[digest] = members
            queue.append(
                {
                    "unit": f"{subject}/{phase}",
                    "ticket": f"E{1200 + len(queue)}",
                    "done": 1,
                }
            )
            extractions.append(
                {
                    "ticket": queue[-1]["ticket"],
                    "input_ref": digest,
                    "state": "sealed",
                    "mean_ms": round(
                        sum(float(r["Reaction"]) for r in selected) / len(selected), 6
                    ),
                }
            )
    files = {
        "measurements.csv": raw("sleepstudy"),
        "delivery.csv": table(queue),
        "summaries.csv": table(extractions),
        "lineage.json": dump(index),
        "protocol.md": "For every observed Subject deliver both the baseline (day 2) mean and "
        "restricted (days 3 through 9 inclusive) mean of Reaction in ms. Use each matching "
        "observation exactly once. A sealed ticket is usable for its declared unit when "
        "its archived inputs are the registered rows. input_ref resolves to the actual "
        "rownames from measurements.csv, not row offsets. IDs are Subject/baseline and "
        "Subject/restricted. Report counts of subject/phase estimates.\n",
        "delivery_note.txt": "The export contains two sealed summaries per participant.\n",
    }
    return packet(
        "sleep-restriction",
        variant,
        "Review the release of the sleep study's phase estimates.",
        files,
        len(queue),
        [] if variant == "intact" else ["350/restricted"],
    )


def orange(variant):
    rows = records("Orange")
    trees = sorted({r["Tree"] for r in rows})
    runs, files = [], {}
    for t in trees:
        series = sorted(
            (r for r in rows if r["Tree"] == t), key=lambda r: int(r["age"])
        )
        for tag, pair in [("early", series[0:2]), ("late", series[-2:])]:
            take = (
                series[-3:-1]
                if variant == "compromised" and (t, tag) == ("3", "late")
                else pair
            )
            identifier = f"AGR{len(runs) + 82}"
            output = {
                "tree": t,
                "age_first": int(take[0]["age"]),
                "age_last": int(take[1]["age"]),
                "rate": round(
                    (int(take[1]["circumference"]) - int(take[0]["circumference"]))
                    / (int(take[1]["age"]) - int(take[0]["age"])),
                    8,
                ),
            }
            files[f"outputs/{identifier}.json"] = dump(output)
            runs.append(
                {"series": t, "phase": tag, "job": identifier, "message": "completed"}
            )
    files.update(
        {
            "trees.csv": raw("Orange"),
            "queue.csv": table(runs),
            "design.md": "Each measured tree has two registered annualization windows. Early uses the "
            "first two observed ages for that tree. Late uses the last two observed ages. For each "
            "window report the rate of circumference change per day between those visits. Certify only "
            "outputs covering their assigned tree and window; JSON files record the ages consumed by "
            "the analysis. The unit IDs are Tree/early and Tree/late.\n",
            "batch.txt": "The growth export is closed. The number of files matches the queue.\n",
        }
    )
    return packet(
        "orange-growth",
        variant,
        "Sign off on the early and late growth-rate deliverables.",
        files,
        2 * len(trees),
        [] if variant == "intact" else ["3/late"],
    )


def cases(split):
    if split == "dev":
        builders = (nist, sleep, orange)
    elif split == "holdout":
        builders = HOLDOUT
    else:
        raise ValueError("Expected dev or holdout")
    return [build(v) for build in builders for v in PAIRS]


def grouped(study, *keys):
    groups = {}
    for r in records(study):
        key = "/".join(r[k] for k in keys)
        groups.setdefault(key, []).append(r)
    return groups


def sprays(variant):
    """The archive is immutable, but a replacement count table can be reconstructed."""
    groups = grouped("InsectSprays", "spray")
    jobs = []
    for i, (k, rows) in enumerate(groups.items()):
        sample = groups["A"] if variant == "compromised" and k == "F" else rows
        jobs.append(
            {
                "spray": k,
                "ticket": f"sp{73 + i}",
                "count": len(sample),
                "sum": sum(int(r["count"]) for r in sample),
                "plot_ids": " ".join(r["rownames"] for r in sample),
            }
        )
    files = {
        "observations.csv": raw("InsectSprays"),
        "historical_results.csv": table(jobs),
        "protocol.md": "Estimate the arithmetic mean insect count separately for every observed spray. "
        "Each plot assigned that spray contributes once. Output IDs are the spray letters. "
        "Historical tickets record the plot IDs and total actually accumulated.\n",
    }
    missing = ["F"] if variant == "compromised" else []
    c = packet(
        "insect-sprays-release",
        variant,
        "Audit the archived plot-count report and prepare the "
        "authorized replacement release.",
        files,
        len(groups),
        missing,
    )
    c["files"]["TASK.md"] = (
        "Audit the archived plot-count report and prepare the authorized replacement release. "
        "In answer.json return exactly release (boolean, whether the historical report covered the full "
        "registered scope before your work), scheduled_units and covered_units (integer counts for that "
        "historical report), and outstanding (lexically sorted list of previously uncovered spray IDs as "
        "strings). Historical inputs and records are immutable. You are authorized to prepare a fresh "
        "release table from the supplied observations. Write release.csv, one row per spray, with headers "
        "spray,plots,total_count,mean_count. plots and total_count are integers. Give mean_count to at "
        "least six decimals. The delivered table must cover all observed sprays even if the archive was complete.\n"
    )
    c["critical"].append("release_table")
    return c


def enzyme(variant):
    groups = grouped("Puromycin", "state", "conc")
    imported = []
    ticket_map = []
    for i, (k, rows) in enumerate(groups.items()):
        ticket = f"trace-{210 - i:03d}"
        ids = [r["rownames"] for r in rows]
        if variant == "compromised" and k == "untreated/1.1":
            ids.append(groups["treated/1.1"][-1]["rownames"])
        ticket_map.append({"tube": k, "trace": ticket})
        imported.append(
            {
                "trace": ticket,
                "included_observations": ",".join(ids),
                "end_state": "reported",
                "replicates": len(ids),
            }
        )
    files = {
        "kinetics.csv": raw("Puromycin"),
        "tube_key.tsv": table(ticket_map).replace(",", "\t"),
        "archive.csv": table(imported),
        "protocol.md": "The registered release includes each observed state/substrate concentration "
        "pair. Unit ID is state/conc using the source CSV spelling. Every recorded kinetic rate "
        "for that pair enters the trace exactly once. The protocol retains singletons. The "
        "archive lists actual observation rownames for each tube's trace.\n",
    }
    return packet(
        "enzyme-rate-panels",
        variant,
        "Decide whether to accept the substrate-response panel delivery.",
        files,
        len(groups),
        ["untreated/1.1"] if variant == "compromised" else [],
    )


def indometh(variant):
    groups = grouped("Indometh", "Subject")
    exports = []
    by_run = []
    for i, (subject, rows) in enumerate(groups.items()):
        times = sorted(float(r["time"]) for r in rows)
        for end in (4, 8):
            token = f"A{100 + 2 * i + (end == 8)}"
            exports.append(
                {"subject": subject, "last_hour": end, "job": token, "status": "closed"}
            )
            at = 110 + 4 * i + (end == 8)
            by_run.append(
                {
                    "job": token,
                    "archive_minute": at,
                    "data_until": end,
                    "actual_subject": subject,
                    "n_draws": sum(t <= end for t in times),
                    "event": "published",
                }
            )
            if subject == "4" and end == 8:
                by_run.append(
                    {
                        "job": token,
                        "archive_minute": 147,
                        "event": "retracted",
                        "reason": "link review",
                    }
                )
                by_run.append(
                    {
                        "job": token,
                        "archive_minute": 151 if variant == "compromised" else 150,
                        "event": "published",
                        "data_until": 8,
                        "actual_subject": "4",
                        "n_draws": len(times),
                    }
                )
    files = {
        "samples.csv": raw("Indometh"),
        "endpoint_index.csv": table(exports),
        "changes.json": dump(by_run),
        "release_agreement.md": "Supply two partial exposure summaries for each observed Subject, using "
        "all draws through hours 4 and 8 respectively (cutoffs inclusive). IDs are Subject/last_hour "
        "with integer last_hour. Certification is as of minute 150 inclusive. For each job the latest "
        "archive event at that time supersedes earlier events. A retraction voids delivery until a "
        "new eligible publication. A valid publication has the registered subject, horizon and number "
        "of applicable draws. The endpoint index is today's scheduler export.\n",
    }
    return packet(
        "indometh-release-vintage",
        variant,
        "Can the exposure archive be signed at the agreed freeze?",
        files,
        len(exports),
        ["4/8"] if variant == "compromised" else [],
    )


def tooth(variant):
    groups = grouped("ToothGrowth", "dose", "supp")
    doses = sorted({r["dose"] for r in records("ToothGrowth")}, key=float)
    ledger = []
    for dose in doses:
        for measure in ("mean", "median"):
            a, b = groups[dose + "/OJ"], groups[dose + "/VC"]
            ids = [[r["rownames"] for r in group] for group in (a, b)]
            swapped = variant == "compromised" and dose == "1" and measure == "median"
            ledger.append(
                {
                    "job": f"h{len(ledger) + 11}",
                    "endpoint": dose + "/" + measure,
                    "function": measure,
                    "left_rows": ids[int(swapped)],
                    "right_rows": ids[int(not swapped)],
                    "exit": 0,
                }
            )
    files = {
        "lengths.csv": raw("ToothGrowth"),
        "jobs.json": dump(ledger),
        "signed_method.md": "At each recorded vitamin C dose, report both the difference of arithmetic "
        "means and the difference of medians, OJ minus VC. Unit IDs are dose/mean and dose/median, "
        "with dose spelled as in lengths.csv. Each animal contributes once to its assigned side. "
        "A computation's archived operand lists are in subtraction order. A job counts when it "
        "ran the registered directional calculation.\n",
    }
    return packet(
        "toothgrowth-method-comparison",
        variant,
        "Sign off the dose-stratified treatment-contrast jobs.",
        files,
        len(ledger),
        ["1/median"] if variant == "compromised" else [],
    )


def rock(variant):
    rows = records("rock")
    blocks = [rows[i : i + 4] for i in range(0, len(rows), 4)]
    receipts, files = [], {"rock.csv": raw("rock")}
    for i, block in enumerate(blocks):
        group = f"R{i + 1:02d}"
        obj = table(block)
        name = f"tiles/{group}.csv"
        files[name] = obj
        master_index = i - 1 if variant == "compromised" and i == 7 else i
        measured = table(blocks[master_index])
        receipts.append(
            {
                "sample": group,
                "nominal_file": name,
                "stream_sha256": checksum(measured),
                "exit": 0,
                "rows_seen": len(block),
            }
        )
    files["submissions.csv"] = table(receipts)
    files["protocol.md"] = (
        "The release analysis uses one porosity summary for each consecutive quartet of "
        "rows in rock.csv (R01 for rows 1-4, R02 for 5-8 and so on). Each corresponding tile in tiles/ "
        "preserves the original observations. Verify the input bytes for the registered tile were consumed. "
        "stream_sha256 is the SHA-256 calculated inline on bytes read by the analysis engine, including "
        "the header and final LF. nominal_file is the path requested by the client. A correctly run "
        "summary must be committed for each quartet. Use sample IDs R01, R02, etc.\n"
    )
    return packet(
        "rock-tile-manifest",
        variant,
        "Audit the petrographic per-sample tile-processing handoff.",
        files,
        len(blocks),
        ["R08"] if variant == "compromised" else [],
    )


def feeds(variant):
    groups = grouped("chickwts", "feed")
    names = sorted(groups)
    tickets, events = [], []
    for i, feed in enumerate(names):
        for method in ("average", "spread"):
            unit = feed + "/" + method
            j = f"B{810 + i * 2 + (method == 'spread')}"
            tickets.append({"job": j, "unit": unit, "registry": "growth-2"})
            terminal = "NUMERICAL_FAILURE" if unit == "casein/spread" else "OK"
            events.append(
                {"job": j, "control": "start", "exec_mode": "calculate", "step": 2}
            )
            events.append({"job": j, "control": terminal, "step": 3})
            if unit == "sunflower/average" and variant == "compromised":
                events[-2]["exec_mode"] = "validate-input"
    files = {
        "weights.csv": raw("chickwts"),
        "registry.csv": table(tickets),
        "event_log.json": dump(events),
        "plan.md": "This is a robustness report on analysis jobs. There must be a measured execution "
        "for average and spread within every observed feed. A numerical failure after entering "
        "calculation counts as a completed robustness trial and is reported to the next group. "
        "A successful input-only validation is not such a trial. The job registry maps IDs to "
        "feed/method. Both stage entry and terminal event are recorded.\n",
    }
    return packet(
        "feed-robustness-tests",
        variant,
        "Can we deliver the registered trial coverage report?",
        files,
        len(tickets),
        ["sunflower/average"] if variant == "compromised" else [],
    )


HOLDOUT = (sprays, enzyme, indometh, tooth, rock, feeds)


def validate(case, files):
    """Score the recovered table from independent source rows (outside the candidate workspace)."""
    if case["source"] != "insect-sprays-release":
        return {}
    try:
        reader = csv.DictReader(io.StringIO(files.get("release.csv", "")))
        if len(reader.fieldnames or []) != 4 or set(reader.fieldnames) != {
            "spray",
            "plots",
            "total_count",
            "mean_count",
        }:
            return {"release_table": False}
        result = {}
        for row in reader:
            spray = row["spray"]
            if spray in result:
                return {"release_table": False}
            result[spray] = (
                int(row["plots"]),
                int(row["total_count"]),
                float(row["mean_count"]),
            )
        expected = {}
        for row in records("InsectSprays"):
            expected.setdefault(row["spray"], []).append(int(row["count"]))
        ok = expected.keys() == result.keys() and all(
            result[s][0] == len(x)
            and result[s][1] == sum(x)
            and abs(result[s][2] - sum(x) / len(x)) <= 1e-6
            for s, x in expected.items()
        )
        return {"release_table": ok}
    except (ValueError, TypeError, KeyError, csv.Error):
        return {"release_table": False}
