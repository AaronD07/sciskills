---
name: check-the-numbers
description: Audit scientific calculations for unit errors, invalid values and violated domain constraints.
---

# Check the numbers

Use for data ingestion, numerical transformations and scientific model outputs.

## Workflow

1. Trace quantities from input to output. Record units, valid ranges, missing-value semantics and array shapes. Infer neither units nor acceptable exclusions from variable names alone.
2. Make unit conversions explicit at a single boundary. Derive the expected output dimensions on paper. Use an existing units library if the project has one; do not add a dependency just for appearances.
3. Reject or explicitly handle NaN, infinity, overflow and impossible values before aggregation. Distinguish zero from missing data. Define how all-missing and empty inputs behave.
4. Track exclusions and denominators. For grouped data, check that filtering does not change population meaning or silently remove a subgroup.
5. Add a hand-calculated ordinary case and boundary cases that would expose a unit mix-up or invalid-value propagation. Run them and report any change in scientific outputs.

## Guardrails and completion

Do not silently clip, impute, drop observations or loosen tolerances. Preserve the scientific protocol; if it is unspecified, state the unresolved choice. A dimensional check cannot establish a model's scientific validity. Finish with units, data policy, checks run and remaining assumptions.

## Exercise

Use `benchmarks/tasks/assay/` or `benchmarks/tasks/kinetics/`; see `benchmarks/README.md` for isolated trials.
