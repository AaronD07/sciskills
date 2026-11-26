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

Seven of twelve passing two-sample analyses in the original pilot failed when the evaluator supplied fresh summary statistics. The follow-up coding study tested two different public problems. On the file-edit replication, Sonnet twice replaced the caller’s image and window bounds with the example values, once in each condition. The fresh-input instructions produced no net change in full passes. [Fresh-data replay](benchmarks/fieldstudy/transfer352.jsonl) · [Code-transfer study](benchmarks/input-transfer/README.md)

In the record audit, Terra and Sonnet returned every field correctly with or without the worksheet. Luna made errors selecting eligible records and calculating changes. Its mean field accuracy was 13.43% at baseline and 9.95% with the worksheet. [Record-audit study](benchmarks/fieldstudy/README.md)

A follow-up gave both agents a local Python tool and three new datasets of 418 calibration certificates each. Luna and Sonnet each returned all 11 requested fields correctly in all nine baseline runs and all nine skill runs. The supplied helper executed in three of the 18 treatment runs. These were different datasets from the text-only study, so the experiments cannot isolate the effect of Python access itself. [Tool-assisted reconstruction study](benchmarks/ledger-replay/README.md)

Read the [contribution guide](docs/CONTRIBUTING.md) when adding a skill or exercise.
