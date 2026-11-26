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

Read the [contribution guide](docs/CONTRIBUTING.md) when adding a skill or exercise.
