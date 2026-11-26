"""Independent reference implementations for the four native v2 exercises."""
from pathlib import Path
import inspect
import os
import py_compile
import tempfile
import unittest

from test_tooling import benchmark


def estimate(protocol, datasets):
    from statistics import mean

    cohort = protocol["cohort"]
    endpoint = protocol["endpoint"]
    result = dict(cohort=cohort, status="missing cohort", mean=None, n=0)
    if cohort not in datasets:
        return result
    records = datasets[cohort]
    if any(endpoint not in row for row in records):
        result["status"] = "missing endpoint"
        return result
    observed = [row[endpoint] for row in records if row[endpoint] is not None]
    if observed:
        result.update(status="ok", mean=mean(observed), n=len(observed))
    else:
        result["status"] = "no observations"
    return result


def paired_change(readings):
    from collections import defaultdict
    from math import sqrt
    from statistics import mean, stdev

    people = defaultdict(lambda: defaultdict(list))
    for person, visit, value in readings:
        people[person][visit].append(value)
    changes = [mean(visits["after"]) - mean(visits["before"])
               for visits in people.values() if "before" in visits and "after" in visits]
    n = len(changes)
    return dict(mean_change=mean(changes) if changes else None,
                standard_error=stdev(changes) / sqrt(n) if n > 1 else None,
                n=n, excluded=len(people) - n)


def compare(schedule, log):
    from statistics import mean

    scores = {key: {} for key in schedule}
    for case, repetition, condition, status, value in log:
        key = (case, repetition)
        if key not in scores or condition in scores[key]:
            raise ValueError("unknown or duplicate run")
        scores[key][condition] = value if status == "ok" else None

    all_deltas = []
    complete_deltas = []
    for pair in scores.values():
        baseline, skill = pair.get("baseline"), pair.get("skill")
        all_deltas.append((skill or 0) - (baseline or 0))
        if baseline is not None and skill is not None:
            complete_deltas.append(skill - baseline)
    return dict(delta_all=mean(all_deltas) if all_deltas else None,
                delta_complete=mean(complete_deltas) if complete_deltas else None,
                planned_pairs=len(schedule), complete_pairs=len(complete_deltas))


def audit_claims(draft, figures, version):
    current = {f["group"]: f for f in figures if f["version"] == version}
    output = []
    for claim in draft:
        group = claim["group"]
        figure = current.get(group)
        result = dict(id=claim["id"], status="unsupported", figure=None, percent=None,
                      text="The current survey does not establish this result.")
        if figure and figure["observed"]:
            observed = figure["observed"]
            positive = figure["positive"]
            percent = round(100 * positive / observed)
            result.update(figure=figure["id"], percent=percent)
            if (claim["kind"] == "rate" and claim["figure"] == figure["id"]
                    and claim["percent"] == percent):
                result.update(status="keep", text=claim["text"])
            else:
                text = f"{group}: {positive} of {observed} respondents ({percent}%) reported improvement."
                result.update(status="revise", text=text)
        output.append(result)
    return output


V2 = {
    "contract": (estimate, "demo_only", "preserve-the-research-question"),
    "subjects": (paired_change, "replicated_visit", "identify-the-independent-unit"),
    "comparison": (compare, "missing", "compare-experiments-fairly"),
    "claims": (audit_claims, "causal_overstatement", "trace-claims-to-evidence"),
}


class NativeV2Tests(unittest.TestCase):
    def test_prepared_tasks_have_expected_fault_and_references_pass(self):
        for case, (reference, expected_fault, skill) in V2.items():
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                dest = Path(directory) / case
                benchmark.prepare(case, dest, skill)
                self.assertEqual({p.name for p in dest.iterdir()}, {"TASK.md", "analysis.py", "SKILL.md"})
                submission = dest / "analysis.py"
                broken = benchmark.score(case, submission)
                self.assertNotIn("error", broken)
                self.assertIn(expected_fault, {r["check"] for r in broken["checks"] if not r["passed"]})
                submission.write_text(inspect.getsource(reference))
                result = benchmark.score(case, submission)
                self.assertEqual(result["passed"], 8, result)
                self.assertEqual(result["total"], 8)

    def test_candidate_can_mutate_its_copy_of_the_input(self):
        code = inspect.getsource(audit_claims).replace("    return output", """    for figure in figures:
        figure.clear()
    return output""")
        with tempfile.TemporaryDirectory() as directory:
            submission = Path(directory) / "analysis.py"
            submission.write_text(code)
            result = benchmark.score("claims", submission)
            self.assertEqual(result["passed"], 8, result)

    def test_same_second_repair_grades_current_bytes(self):
        # A bytecode timestamp stores only whole seconds and source size.
        with tempfile.TemporaryDirectory() as directory:
            submission = Path(directory) / "analysis.py"
            correct = inspect.getsource(estimate)
            submission.write_text(correct.replace('"ok"', '"XX"'))
            stamp = submission.stat().st_mtime
            py_compile.compile(str(submission), doraise=True,
                               invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
            submission.write_text(correct)
            os.utime(submission, (stamp, stamp))
            self.assertEqual(benchmark.score("contract", submission)["passed"], 8)
