---
name: test-fresh-inputs
description: Check that an analysis uses its caller’s data when the example changes.
---

# Test fresh inputs

Use when completing a notebook cell, writing a transformation, or handing off code that ran on a demonstration dataset.

## Workflow

1. List the values the caller supplies and the output it expects. For a code insertion, keep the surrounding cell in mind. Put sample data in a separate test so the analysis receives the caller’s objects.
2. Trace each reported value back to those inputs. Check constants for copied sample sizes, identifiers, array shapes and statistics. Keep constants required by the scientific method.
3. Make a second input that distinguishes a general solution from one that memorizes the example. Change group labels, shuffle records, use unequal lengths or move a point near an edge. Predict the result before running the code.
4. Check which properties should change and which should stay fixed. For example, renaming participant IDs should preserve their estimates under the new labels. A result that still contains the old labels identifies where to start looking.

## Completion

Verify the output contract and one discriminating input. When execution is unavailable, walk through the second case and state that the check was manual if the response format permits.

## Exercise

Replay the [two-sample analysis diagnostic](../../benchmarks/fieldstudy/transfer352.py) on the previous pilot’s submissions.

## Check an insertion locally

Declare the variables the caller owns. For an image task where the host supplies the image and crop bounds, run this command from the SciSkills repository:

```sh
python3 skills/test-fresh-inputs/check_inputs.py solution.py --inputs a low_index high_index
```

The checker parses source and reports direct top-level replacements such as `low_index = -1` or `a = np.ones((3, 3))` following a NumPy import. Put those initializations in an example fixture if the host owns the values. Exit status 0 means no matches, 1 means findings, and 2 means the scan could not run. Continue with a changed-input test: indirect constants, conditional writes, in-place mutations and calls inside functions fall outside this check.
