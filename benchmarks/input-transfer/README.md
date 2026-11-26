# Do assistants use fresh inputs?

In the previous study, seven of twelve passing DS-1000 problem 352 submissions copied the example values. For this follow-up, we selected two different problems whose official graders supply multiple inputs and gave the assistants explicit insertion instructions. We froze the questions and the [measured fresh-input skill](measured-skill.md) before the first measured run. The [design](design.md) records our rationale and decision criterion.

| Agent | 108 baseline | 108 with skill | 411 baseline | 411 with skill |
| --- | ---: | ---: | ---: | ---: |
| Codex CLI, GPT-6.1 Terra | 3/3 | 3/3 | 3/3 | 3/3 |
| Claude Code, Sonnet 5.5 | 0/3 | 1/3 | 1/3 | 0/3 |

**Each condition passed 7 of 12 runs.** Across twelve matched pairs there was one gain, one regression and ten ties. On these tasks Terra reached the ceiling at baseline. Sonnet gained a pass on the dataframe join and lost a pass on the image-window task. The observed result fell short of the prespecified improvement criterion.

## What actually failed

All ten failures came from Sonnet. Eight graded insertions failed Python compilation. They contained XML code tags, explanatory prose, extra Markdown fences, or indentation inconsistent with insertion at top level. On the join task the five rejected submissions each contained a recognizable forward as-of merge. Embedded in prose or tags, those snippets did not run. Treatment replies sometimes explained their manual check despite the common request for Python only. Scoring removed a single enclosing Markdown fence and stripped outer whitespace, which can affect the first line of an indented answer.

The other two failures were specific to the image task. One baseline reply extended the upper crop bound by one pixel. One treatment reply referred to undefined variables named `high` and `low`; the supplied variables were `high_index` and `low_index`. The graded submissions provide no evidence that copying the fixed example inputs caused a failure in this study. These two public questions and repeated samples from each model give limited evidence about other workflows.

## Reproduce the grades

The [protocol](results/protocol.json) records the ordered pairs, models, prompt digests, CLI versions and authentication checks. The [trial records](results/trials.jsonl) include the graded source and its digest, elapsed time, and verdict for every attempt. All 24 returned submissions within 180 seconds. Participants received only their prompt in independent, tool-free sessions. Low reasoning effort, task text and output contract were fixed across conditions. The launch environment excluded API keys and model/provider overrides. The Codex account had included ChatGPT usage available, and Claude Code used a first-party Max subscription with extra usage disabled.

Install and cache the pinned [DS-1000 evaluator](../external/README.md). From the repository root on macOS, the following command reruns all five original test cases across the stored completions for their respective tasks, using the same sandbox as the earlier pilot. Replay requires no model calls.

```sh
python3 benchmarks/input-transfer/study.py replay \
  --external-python /tmp/sciskills-ds1000-env/bin/python \
  --out benchmarks/input-transfer/results
```

Use the `run` subcommand and a new output directory to collect another sample. It checks subscription access, verifies that upstream reference answers pass and empty submissions fail, and preflights both clients. Use `python3 -m unittest discover -s benchmarks/input-transfer -v` for the offline protocol tests.

## File-edit replication on the same questions

Eight response-only failures contained invalid Python. To isolate the contribution of answer formatting, we repeated the comparison in fresh workspaces. Each assistant read TASK.md, could read SKILL.md in treatment, and wrote solution.py. The final chat reply was never scored. This reused the same questions after observing the first study. See the [prospective follow-up design](file-design.md), [protocol](file-results/protocol.json), and [24 scored files and tool observations](file-results/trials.jsonl).

| Agent | 108 baseline | 108 with skill | 411 baseline | 411 with skill |
| --- | ---: | ---: | ---: | ---: |
| Codex CLI, GPT-6.1 Terra | 0/3 | 0/3 | 3/3 | 3/3 |
| Claude Code, Sonnet 5.5 | 3/3 | 3/3 | 2/3 | 2/3 |

**Each condition passed 8/12.** There was one matched gain, one regression and ten ties. All 24 returned files that compiled as Python. Claude used its restricted file tools. Codex used workspace shell commands to locate, read and write files. Its recorded commands show no execution of a submitted analysis. Both tools completed all sessions before the limit.

The six rejected Codex joins used a `while` loop to choose a temporary column name that did not already exist. The upstream source-form test rejects any `for` or `while` token. The public problem asks to avoid looping through dataframe rows. None of these six loops iterates over rows. In a secondary diagnostic, all six submissions passed both original dataframe value checks when the source-form test alone was omitted. The table retains all six upstream failures.

The two rejected Sonnet image crops each replaced the caller’s array with the displayed three-by-three array of ones and reset the bounds to −1 and 2. They reproduced the example even when the grader supplied a five-by-five array and different bounds. One mistake occurred at baseline and one with the skill, in different repetitions. This reproduces the original failure mechanism in a real edit, with no measured reduction in its frequency in this small sample.

Replay the graded files and, separately, rerun the secondary source-form diagnostic:

```sh
python3 benchmarks/input-transfer/files.py replay \
  --external-python /tmp/sciskills-ds1000-env/bin/python \
  --out benchmarks/input-transfer/file-results
python3 benchmarks/input-transfer/diagnose.py \
  --external-python /tmp/sciskills-ds1000-env/bin/python \
  --out benchmarks/input-transfer/file-results
```

The [post hoc checker diagnostic](diagnostic.md) reviews a separately implemented source check against the archived input-overwrite failures.
