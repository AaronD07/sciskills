---
name: identify-the-independent-unit
description: Check which observations count as independent before estimating effects or uncertainty.
---

# Identify the independent unit

Use for repeated measurements, matched observations or data collected in clusters.

## Workflow

1. Read the study design. Identify what was sampled or assigned independently. One row might represent a reading, visit or replicate from the same participant.
2. Count rows and distinct units per group. Check which units appear in multiple conditions and how many measurements each contributes. Ask for the grouping key if the design needs one.
3. Match the calculation to the question. For an average participant change, align conditions by participant ID, summarize technical replicates within each condition and compute a change per participant. Account for dependence when calculating uncertainty.
4. Check a small case by hand. Shuffle the rows and confirm ID pairing survives. Duplicate an identical technical reading and confirm it adds no independent participant.

## Guardrails and completion

Explain how incomplete pairs and unequal replication affect the estimate. Report the effect, the independent unit, the number of units analyzed and the number excluded.

## Exercise

Use the [subjects task](../../benchmarks/tasks/subjects/) and the [benchmark guide](../../benchmarks/README.md).
