# What the first drafts got wrong

Across twelve development tasks and two attempts per model, Luna passed 22/24, Terra 23/24 and Sonnet 24/24. All 72 sessions returned successfully. The four source studies are reused across three task types within development.

| Draft | Observation | Reproduction |
| --- | --- | --- |
| airquality-ozone, Luna, attempt 1 | The fit gave the expected slope and intercept. The answer returned a list of the 111 pairs where the grader expected their count. The wording requested “pairs” without explicitly giving its type, so this is a contract ambiguity. | Load the archived answer and take the length of its pairs field. |
| chickweight-growth, Luna, attempt 2 | The Diet 1 entry contains the correct 20 birds, pooled rate 5.984375 and jackknife SE 0.667091. The answer is keyed by diet and includes three other diets. The request asks for the Diet 1 fields directly. | Compare the fields of the nested Diet 1 entry with the flat reference. |
| airquality-episodes, Terra, attempt 1 | Terra read the task and source data. Its final chat message contained a function, while the submitted workspace had no solution.py. Its two Python calls only read files. | Reconstruct the draft artifacts and inspect the recorded calls. All five file-based checks fail. |

These misses motivated checking the actual deliverable through the caller's interface. The previous record and payment audits motivated independent reconstruction and source-based decisions. We kept the workflows general. The target task names, values, grading references and failing fields never enter review instructions. Drafts and submitted code are in the [development archive](results/dev/sessions.jsonl).
