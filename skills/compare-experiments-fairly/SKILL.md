---
name: compare-experiments-fairly
description: Design and audit a comparison with a common baseline, a fixed metric and a record of failed runs.
---

# Compare experiments fairly

Use when comparing tools, models, prompts or analysis methods.

## Workflow

1. Write down the question, primary metric, direction of improvement, stopping rule and failure policy before looking at scores.
2. Give both conditions the same cases, resources and opportunity to finish. Vary only the factor being tested. Record settings that cannot be held fixed.
3. Record every planned attempt with its case, condition, repetition, outcome and run identifier. Keep crashes, timeouts and missing runs distinguishable. Report how many completed in each condition.
4. For paired runs, match by case and repetition. Calculate the within-pair difference and show how many pairs contributed. Report the chosen failure policy alongside any complete-pair comparison.

## Guardrails and completion

Keep the original log. If a conclusion changes when failures are counted differently, say so. Report the metric, denominator and observed difference with enough detail to reproduce them.

## Exercise

Use the [comparison task](../../benchmarks/tasks/comparison/) and the [benchmark guide](../../benchmarks/README.md).
