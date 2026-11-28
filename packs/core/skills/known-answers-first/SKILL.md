---
name: known-answers-first
description: Test scientific code against independently known results before trusting realistic outputs. Use when writing tests for numerical or scientific code, before accepting a new implementation, or when changing an analysis method; anchor tests to hand calculations, analytic solutions or conservation laws, never to the code's own output.
---

# Known answers first

Use before accepting a numerical implementation or changing an analysis method.

## Workflow

1. Identify the mathematical contract: inputs, outputs, units, valid domain, tolerances and limiting cases. Resolve ambiguity before choosing an expected result.
2. Choose a small case whose answer comes from hand calculation, an analytic solution, a conservation law or a separately derived reference. Do not generate the expected answer with the implementation under test.
3. Check an ordinary case, a boundary and a case that distinguishes plausible wrong implementations. Examples: a constant integral, zero noise, a one-element sample, or unequal time steps.
4. Encode these as executable assertions. Set absolute and relative tolerances from scale, precision and scientific needs; explain them. Check shape and finiteness before numerical closeness.
5. Run the tests before and after the fix. Confirm at least one discriminating test fails on the original bug. Preserve valid behavior outside the example.

## Guardrails and completion

Do not change reference values to match current output. Passing simple cases supports only the tested contract, not the full scientific claim. Report the source of each known answer, commands, outcomes and untested regimes.

## Exercise

Use `benchmarks/tasks/kinetics/` and the workflow in `benchmarks/README.md`. The evaluator has independent cases; keep its code out of the agent workspace during a measured trial.
