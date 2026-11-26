# A preflight for examples that overwrite caller inputs

On DS-1000 problem 352, seven submitted programs passed the published example and then failed on all three fresh inputs. Each assigned the example values to the six variables the evaluator had supplied. In the follow-up image-window study, two files similarly reset an image and its crop bounds before computing their answers. A source check can surface this particular error before running the analysis.

The [checker](../../skills/test-fresh-inputs/check_inputs.py) asks the scientist to name the variables already supplied by the calling code. It parses the Python syntax tree, checks unconditional assignments at the module level and reports the first source line of each direct replacement. It recognizes literals, literal containers and selected NumPy or pandas constructors imported in the submission whose arguments are entirely literal. For example, a fresh image or array initialized from the caller's shape falls outside the rule. It does not execute the submission.

| Archived task | Submissions | Confirmed replacements flagged | Other submissions flagged | Confirmed replacements missed |
| --- | ---: | ---: | ---: | ---: |
| Welch test, 352 | 12 | 7 | 0 | 0 |
| Timestamp join, 108 file edits | 12 | 0 | 0 | 0 |
| Image crop, 411 file edits | 12 | 2 | 0 | 0 |

The [fresh-value diagnostic](../fieldstudy/transfer352.jsonl) and inspection of the original 352 code established its comparison labels. For the two file-edit tasks, the labels came from the [previously documented review](README.md#file-edit-replication-on-the-same-questions). The six rejected timestamp joins had a separate source-form issue: they passed both input/output checks. None was flagged for overwriting data. The calculation counts submissions, including repeated attempts on the same tasks.

This is a **post hoc detector check**. We designed the rule after seeing the archived failures. Its agreement on these 36 files describes a known, narrow defect. It provides neither a prospective estimate of false alarms nor evidence that giving an LLM the skill increased its pass rate. Conditional writes, in-place mutation, indirect constants, inputs reassigned inside functions and unrecognized constructors can all evade the check. The declared names matter: a literal initialization can be legitimate when the caller does not supply that variable.

## Reproduce offline

From the repository root, scan the 36 archived, hash-checked submissions and compare findings with the prior diagnoses:

```sh
python3 benchmarks/input-transfer/check_archive.py
```

To use the checker on a new image crop:

```sh
python3 skills/test-fresh-inputs/check_inputs.py solution.py --inputs a low_index high_index
```

The input-transfer study and its file-edit replication use the [frozen measured skill](measured-skill.md) for replay. The [live skill](../../skills/test-fresh-inputs/SKILL.md) now includes instructions for the additional checker.
