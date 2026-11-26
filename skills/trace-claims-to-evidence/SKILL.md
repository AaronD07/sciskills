---
name: trace-claims-to-evidence
description: Reconstruct a quantitative claim using the records available at the relevant date.
---

# Trace claims to evidence

Use when checking a results section, a revised dataset or a research note.

## Workflow

1. Write down the population, time period, unit, denominator and source cutoff for each claim. A measurement date and the date its result became available can differ.
2. Build a ledger with one row per entity and period. Select the applicable version as of that period’s cutoff. Keep its source identifier and disposition. A withdrawal can invalidate an earlier value. If the question asks for matched populations, reconcile membership before totaling either period.
3. For each rate, retain its numerator and denominator. Pool counts or average group rates according to the stated estimand. Recompute from those counts before rounding.
4. Check the type of change. For rates expressed as fractions, the percentage-point change is 100 × (new − old). The relative change is 100 × (new / old − 1). Verify that multiplying the old rate by one plus the fractional relative change reconstructs the new rate. Flag an undefined ratio if the old rate is zero.
5. Compare the final sentence to the supported population, period and strength of evidence. Preserve supported wording, correct unsupported figures and cite the selected record.

## Exercise

Audit the [survey claims](../../benchmarks/tasks/claims/TASK.md) and trace each revision to its source.
