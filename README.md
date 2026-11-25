# SciSkills

Reusable agent instructions for more reliable scientific software, developed for the Caltech CS 143 special project.

Scientists can use AI to build research tools quickly; plausible output can still hide incorrect assumptions, lost data or irreproducible environments. SciSkills pairs focused review workflows with runnable exercises and a small controlled evaluation harness.

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

Read the [benchmark guide](benchmarks/README.md) before running measured trials; keep evaluator answers out of the agent's workspace. These instructions support review, not a guarantee of correctness or security.

## Run locally

Python 3.10+; all shipped code uses the standard library, so no third-party dependency lockfile is needed. For projects with dependencies, follow the environment skill and generate a real lockfile.

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s examples/pin-the-environment -p 'test_*.py' -v
python3 scripts/check_repo.py .
```

The checker reports evidence of README files, tests, dependency locks, runtime metadata and explicit seed calls. It does not run tests or grade scientific correctness. Empty categories may be appropriate for a particular project.

## What is complete

- Six actionable skills, with exercises or worked examples.
- Three synthetic repair tasks and a scorer with 24 independent checks.
- Regression tests for the evaluator and a read-only repository checker.

The harness has been checked against planted bugs and reference repairs. **Effectiveness with real agents has not yet been measured.** Cross-tool comparisons, a gallery of observed failures, a user study and a separate website remain future work. The README is the current project entry point.

## Finish the class project

1. Run and save repeated baseline/skill trials following the [protocol](benchmarks/README.md). Keep transcripts and actual results; do not turn harness self-tests into effectiveness claims.
2. Present correctness and time per task and tool, including failures. If feasible, run a small consented user pilot and describe its sample size and limitations.
3. Update the final slides/report with observed results, examples and limitations. Correct the proposal's OOM description to memory testing. Verify the review-paper citation and learning-study statistic against their original sources before reusing them; neither is evidence for SciSkills itself.

See [contribution guidance](docs/CONTRIBUTING.md). Keep additions small: a skill needs an actionable workflow, an exercise and a way to check its result.
