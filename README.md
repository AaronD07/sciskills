# SciSkills

Reusable agent instructions for more reliable scientific software, developed for the Caltech CS 143 special project.

SciSkills gives a coding assistant specific checks to run when a scientific result depends on how the code handles data. Each skill includes an exercise. The benchmark tests whether the assistant can apply the same checks to a repair.

## Use a skill

Ask your coding agent to follow the relevant `SKILL.md` while working in your research project. Loading conventions vary across tools; explicit file references work without claiming a universal plugin installation.

| Skill | What it checks | Exercise |
| --- | --- | --- |
| [Pin the environment](skills/pin-the-environment/SKILL.md) | Interpreter, dependencies and randomness | [Seeded simulation](examples/pin-the-environment/) |
| [Known answers first](skills/known-answers-first/SKILL.md) | Independent expected results | Decay analysis |
| [Check the numbers](skills/check-the-numbers/SKILL.md) | Units, missing data and finite values | Assay summary |
| [Adversarial review](skills/adversarial-review/SKILL.md) | Counterexamples and data leakage | Held-out prediction |
| [OOM testing](skills/oom-testing/SKILL.md) | Memory estimates and bounded stress tests | Worked matrix sizing in the skill |
| [Paper to code consistency](skills/paper-to-code-consistency/SKILL.md) | Equations, conventions and implementation | Decay protocol mapping |
| [Preserve the research question](skills/preserve-the-research-question/SKILL.md) | Dataset, cohort and endpoint | [Missing field data](benchmarks/tasks/contract/TASK.md) |
| [Identify the independent unit](skills/identify-the-independent-unit/SKILL.md) | Pairing, repeated measurements and uncertainty | [Paired subjects](benchmarks/tasks/subjects/TASK.md) |
| [Compare experiments fairly](skills/compare-experiments-fairly/SKILL.md) | Planned comparisons, failed runs and denominators | [Experiment logs](benchmarks/tasks/comparison/TASK.md) |
| [Trace claims to evidence](skills/trace-claims-to-evidence/SKILL.md) | Source version, arithmetic and interpretation | [Edit a results paragraph](benchmarks/tasks/claims/TASK.md) |
| [Test fresh inputs](skills/test-fresh-inputs/SKILL.md) | Whether a completion consumes caller-supplied data | [External coding problems](benchmarks/input-transfer/README.md) |
| [Reconstruct a data vintage](skills/reconstruct-a-vintage/SKILL.md) | Which revision of each record was available on a reporting date | [Calibration ledgers](benchmarks/ledger-replay/README.md) |
| [Review a numerical result](skills/review-a-numerical-result/SKILL.md) | Independently reconstruct a saved result | [Assay summary](benchmarks/tasks/assay/) |
| [Review an analysis program](skills/review-an-analysis-program/SKILL.md) | Verify a saved program through its caller's interface | [Seeded simulation](examples/pin-the-environment/) |
| [Test a competing explanation](skills/test-a-competing-explanation/SKILL.md) | Compare a research result with an alternative the original procedure could miss | Instrument drift |
| [Check a local optimum](skills/check-a-local-optimum/SKILL.md) | Test whether a numerical search settled on an inferior feasible solution | Collection-point placement |
| [Repair the delivered result](skills/repair-the-delivered-result/SKILL.md) | Test the saved scientific result independently and verify a repair against prior successes | Sensor calibration |
| [Review a protocol decision](skills/review-a-protocol-decision/SKILL.md) | Trace included and excluded records to a governing rule | [Research contract](benchmarks/tasks/contract/) |
| [Audit a scientific claim](skills/audit-a-scientific-claim/SKILL.md) | Derive the expected evidence for a domain-specific decision | [Integrity review study](benchmarks/integrity_review/) |
| [Verify experimental coverage](skills/verify-experimental-coverage/SKILL.md) | Reconcile protocol obligations and actual results | [Coverage cases](benchmarks/integrity_review/coverage_data/) |
| [Verify measurement provenance](skills/verify-measurement-provenance/SKILL.md) | Determine which observations and decisions a source supports | [Measurement cases](benchmarks/integrity_review/measurement_data/) |
| [Test the deployment claim](skills/test-the-deployment-claim/SKILL.md) | Validate a predictive release on the intended units or future visits | [Deployment cases](benchmarks/integrity_review/deployment_data/) |

For example, if one participant has six follow-up measurements and another has one, averaging every row gives the first participant more weight. Ask the assistant to follow **Identify the independent unit**, calculate each participant’s change, and report how many participants have paired measurements. The [research notes](docs/research-notes.md) explain the evidence behind each new workflow.

## Run locally

The native tasks and checker use Python 3.10+ and the standard library.

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s examples/pin-the-environment -p 'test_*.py' -v
python3 scripts/check_repo.py . --format text
```

The [checker](docs/checker.md) reports evidence, locations, and suggested fixes. Run it on a research repository before handing the analysis to another scientist.

## Evaluate a skill

The [native benchmark](benchmarks/README.md) has seven repair tasks with eight scored checks apiece. The [DS-1000 adapter](benchmarks/external/README.md) adds two published statistical programming problems with their original graders and a separate pinned environment. Keep evaluator files outside the participant workspace. The scoring tools execute the submitted Python.

## Do skills fix mistakes on published hard benchmarks?

We tested the same drafts with ordinary and skill-assisted review on original LiveCodeBench, DABstep, P-Bench and FrontierScience tasks. Three suites qualified for fresh holdouts. Ordinary, general and specialist reviews repaired 3, 2 and 3 of six wrong drafts on the first review. On an independent repeat the counts were 1, 3 and 1. All six wrong holdout drafts came from Luna. [Results and concrete mistakes](benchmarks/external_review/RESULTS.md) · [Protocol and sources](benchmarks/external_review/README.md)

## Which scientific sign-offs did a skill fix?

The [integrity review study](benchmarks/integrity_review/README.md) tested experimental coverage, measurement provenance and deployment validity. Only deployment qualified for a holdout. The specialist verified that every fitting and assessment record in a theophylline study matched the registered split and restored a valid release that ordinary review had withdrawn. Ordinary review found a different repair that the specialist missed. Both finished with 16 of 18 study/model pairs correct. General review finished with 15.

## Reviewing frontier and everyday research

A researcher can use the skills to review a numerical method that will be run on unfamiliar data. They can also use them for everyday decisions where a unit, a missing calibration or a change to the wrong record would alter the result. We test the first use on published scientific computing tasks and the second on paired research handoffs. All 40 everyday first drafts passed. Ordinary, general and specialist review each finished at 39/40 after withdrawing the same +0.48% cash-flow result. [What changed under review](benchmarks/research_review/RESULTS.md) · [Study design and reproduction](benchmarks/research_review/README.md)

A separate study compares Terra and Sonnet on twelve fresh frontier science tasks. In the first ten completed comparisons, seven first drafts failed. The skill left five of those failed deliverables unchanged and edited numerical estimates in the other two. Three estimates moved closer to their references and one moved farther away. All four stayed on the same side of their acceptance thresholds. First drafts, ordinary review and skill-assisted review each passed the same three assignments. Ordinary review also slightly improved Sonnet’s damping estimates on an already passing vibration task. [Paired results](benchmarks/research_review/results/repair-results.md) · [Evidence for the edits](benchmarks/research_review/RESULTS.md#frozen-repair-skill) · [Frozen protocol](benchmarks/research_review/repair-study.md)

## Does a skill improve a second review?

We gave ordinary and skill-assisted reviewers the same first draft on 24 scientific tasks and eight financial investigations. Luna's program-review skill corrected a reversed comparison on real exposure data. Another skill changed a correct response fraction from 0.32 to 0.23. On the 71 science pairs that completed under the tool rules, both reviewers passed 69. The study found no meaningful overall gain. [Results, task packets and replay](benchmarks/paired_review/README.md)

## What happened in the pilot

Codex CLI and Claude Code each completed 36 fresh, tool-free sessions. Each agent attempted the same six tasks three times with the assigned skill and three times without it. The scorer recorded **30 of 36 full passes with a skill and 30 of 36 at baseline**. Each agent scored 15 of 18 in each condition.

| Task group | Baseline | With skill |
| --- | ---: | ---: |
| Four SciSkills repair tasks | 24/24 | 24/24 |
| DS-1000 166, group statistics | 0/6 | 0/6 |
| DS-1000 352, two-sample test | 6/6 | 6/6 |

On problem 166, both agents wrote code that rebuilt the example table. The grouping calculation then used those example rows even when the grader supplied different data. The shared request for complete Python source may have encouraged that choice. On problem 352, seven passing submissions also copied the example inputs. Its single test case could not distinguish those programs from ones that work on fresh values.

The pilot found no change in full-pass counts. The native tasks were already saturated at baseline, and the external results were sensitive to how the task and grader supplied inputs. [Study protocol and analysis](benchmarks/study/README.md) · [Trial-level scores](benchmarks/study/results/trials.jsonl)

## Where the agents struggled

Seven of twelve passing two-sample analyses in the original pilot failed when the evaluator supplied fresh summary statistics. The follow-up coding study tested two different public problems. On the file-edit replication, Sonnet twice replaced the caller’s image and window bounds with the example values, once in each condition. The fresh-input instructions produced no net change in full passes. A later static preflight flagged all nine previously identified examples of input overwriting in 36 archived submissions. The other 27 drew no flag. This was a retrospective detector check. [Diagnostic and usage](benchmarks/input-transfer/diagnostic.md) [Fresh-data replay](benchmarks/fieldstudy/transfer352.jsonl) · [Code-transfer study](benchmarks/input-transfer/README.md)

In the record audit, Terra and Sonnet returned every field correctly with or without the worksheet. Luna made errors selecting eligible records and calculating changes. Its mean field accuracy was 13.43% at baseline and 9.95% with the worksheet. [Record-audit study](benchmarks/fieldstudy/README.md)

A follow-up gave both agents a local Python tool and three new datasets of 418 calibration certificates each. Luna and Sonnet each returned all 11 requested fields correctly in all nine baseline runs and all nine skill runs. The supplied helper executed in three of the 18 treatment runs. These were different datasets from the text-only study, so the experiments cannot isolate the effect of Python access itself. [Tool-assisted reconstruction study](benchmarks/ledger-replay/README.md)

Read the [contribution guide](docs/CONTRIBUTING.md) when adding a skill or exercise.
