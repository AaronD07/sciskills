# Small controlled benchmark

Three synthetic repair tasks: decay analysis, assay summary and held-out prediction. Each has a written scientific contract and deliberately faulty code. These are teaching fixtures, not real observed AI failures. The evaluator supplies eight independent checks per task, including boundary and invalid-input behavior. Numeric tolerances are 1e-10 relative and 1e-12 absolute for these small float64 calculations.

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

Replace the example elapsed times and identifiers with actual measurements. Save each JSON line with the corresponding prompt/transcript and code. The scorer records an output-code hash and scoring runtime. Exit 0 means every check passed; exit 1 includes partial correctness or execution failure. Do not rerun an agent against revealed answers and count it as an independent trial.

Suggested pairings: kinetics / known-answers-first or paper-to-code-consistency; assay / check-the-numbers; prediction / adversarial-review. Evaluate one named skill per condition. Environment reconstruction and bounded memory stress need separate experiments; these tasks do not measure them.

## Interpreting results

Report fully correct submissions / total trials as the primary outcome, with per-check scores and elapsed time as secondary outcomes. Compare within each task and tool before pooling. Include failed or timed-out trials. Keep bug detection in written reviews separate from actually repaired code; manually score review claims against concrete evidence. Record limitations and negative results.

The grader launches submitted Python in a separate process with a five-second default timeout. It is **not a security sandbox or memory cap**: only execute trusted local submissions. An infinite allocation can still exhaust memory. The preparation command refuses existing destinations and copies only the task, faulty code and optional skill. Evaluator checks are hidden from that workspace, not immune to deliberate access.

## Verified status

`python3 -m unittest discover -s tests -v` checks that every planted implementation fails, reference repairs pass all 24 checks, participant preparation excludes answers, and crashing or hanging submissions fail. This validates the harness only. No controlled agent comparisons or user study have been completed in this repository.

For a failure gallery, retain actual trial excerpts, expected versus observed behavior and the regression check, with permission and sensitive content removed. Do not label synthetic tasks as real agent failures.
