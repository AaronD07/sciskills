---
name: compare-experiments-fairly
description: Reconcile a comparison with its planned units, assigned conditions and failure policy.
---

# Compare experiments fairly

Use before interpreting differences between two methods, especially when either side retried or lost runs.

## Workflow

1. Identify the governing protocol, eligibility date, metric, sign and weighting. If a dashboard or earlier draft differs, resolve which rule applies to this analysis.
2. Build a worksheet from the planned units. Give each unit one row with its group and a column for each condition. Join attempts by identifier. Decide eligibility before computing a score. Record why a replacement supersedes an attempt, or why the cell remains missing.
3. Mark success separately from the numeric score. A completed zero and an absent result may contribute the same number under the failure policy while counting differently toward completion.
4. Add each condition’s counts and scores within each group. For the primary estimate apply the protocol’s denominator and group weights. Rebuild the supplementary paired estimate from the intersection of eligible successes.
5. Cross-check every difference twice: subtract the two condition means, then average the row differences over the same units. Account for every planned row. Return counts as counts and round only final results.

## Exercise

Reconcile the [experiment logs](../../benchmarks/tasks/comparison/TASK.md). Retain the worksheet so another reviewer can trace a change in a reported result.
