# Small controlled benchmark

The native suite contains seven short Python repair tasks with 56 checks. Each task gives the participant a scientific contract and a faulty implementation. The mistakes were planted for teaching and evaluation. The scorer uses relative tolerance 1e-10 and absolute tolerance 1e-12 for numbers, and exact agreement for text and dictionary keys.

| Case | What the repair must preserve | Skill to try |
| --- | --- | --- |
| `kinetics` | Time units and the decay equation | Known answers first |
| `assay` | Real zeros and missing measurements | Check the numbers |
| `prediction` | Train and test separation | Adversarial review |
| `contract` | Requested cohort and endpoint, including unavailable data | Preserve the research question |
| `subjects` | Independent participant count and standard error of paired changes | Identify the independent unit |
| `comparison` | Planned trial denominator and matched complete pairs | Compare experiments fairly |
| `claims` | Current source, denominator and wording in a survey results paragraph | Trace claims to evidence |

The [external benchmark](external/README.md) evaluates two DS-1000 completions with their published graders. Report external full passes separately from native check totals.

## Run a paired trial

From the repository root, prepare two fresh directories outside the repo:

```bash
python3 benchmarks/benchmark.py prepare --case assay --dest /tmp/assay-baseline-01
python3 benchmarks/benchmark.py prepare --case assay --skill check-the-numbers --dest /tmp/assay-skill-01
```

Open only the prepared directory in a fresh agent session. Do not expose this repo, evaluator or reference repairs to the agent. Agent-facing prompt in both conditions:

> Complete TASK.md by repairing analysis.py. If SKILL.md exists, follow it. Explain the repair and run your checks.

Keep the model, tool version, resource limits and prompt constant. Record the exact model identifier, tool version, prompt, original and revised code, date, elapsed time, trial order and any human intervention. Use fresh sessions, randomize which condition runs first, and repeat each pair at least three times. Three trials are a small pilot, not strong statistical evidence. The person running the sessions will know the condition; blind outcome review where practical.

Score each final submission outside the agent workspace:

```bash
python3 benchmarks/benchmark.py score --case assay --submission /tmp/assay-baseline-01/analysis.py --condition baseline --agent 'tool/version' --model 'exact-model-id' --trial 1 --elapsed-seconds 120
python3 benchmarks/benchmark.py score --case assay --submission /tmp/assay-skill-01/analysis.py --condition skill --skill check-the-numbers --agent 'tool/version' --model 'exact-model-id' --trial 1 --elapsed-seconds 120
```

Replace the example elapsed times and identifiers with actual measurements. Save each JSON line with the corresponding prompt/transcript and code. The scorer records an output-code hash and the elapsed time supplied by the trial operator. Exit 0 means every check passed; exit 1 includes partial correctness or execution failure. Do not rerun an agent against revealed answers and count it as an independent trial.

Evaluate one named skill per treatment condition. The kinetics task also supports the paper-to-code consistency skill. Environment reconstruction and memory stress require separate experiments.

## Interpreting results

Report fully correct submissions / total trials as the primary outcome, with per-check scores and elapsed time as secondary outcomes. Compare within each task and tool before pooling. Include failed or timed-out trials. Keep bug detection in written reviews separate from actually repaired code; manually score review claims against concrete evidence. Record limitations and negative results.

The grader launches submitted Python in a separate process with a five-second default timeout. It imports the source into the worker and passes fresh inputs to each check. Use an isolated environment with resource limits when grading generated Python. A subprocess inherits the operating system permissions of its user. The preparation command creates a fresh workspace containing the task, starter code, and optional skill.

## Verified status

`python3 -m unittest discover -s tests -v` checks that every starter fails at least one check, that reference repairs pass all 56 native checks, and that participant preparation excludes evaluator answers. Regression tests also cover imports that crash, hanging submissions, stale bytecode, and candidate functions that modify their inputs. These checks measure the behavior of the scorer. Paired trials measure how agents perform.

For a failure gallery, retain actual trial excerpts, expected versus observed behavior and the regression check, with permission and sensitive content removed. Do not label synthetic tasks as real agent failures.
