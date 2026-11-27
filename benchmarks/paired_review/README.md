# Can a skill help an agent repair its own scientific analysis?

The unit of comparison is a first draft. Two reviewers receive that draft, its Python calls, its files, final chat message and the original assignment. The skill reviewer also receives the workflow for that type of deliverable. Both have access to the same Python interpreter. The [study design](design.md) defines the primary measure and the criterion for a meaningful improvement.

## Reproduce locally

Use Python 3.10 or newer on macOS. The local Python execution tool uses the system sandbox. Offline replay reads archived submissions, reconstructs both review inputs and grades each answer again. It executes the submitted programs in isolated directories on the published test inputs.

From the repository root, run:

```sh
python3 -m unittest discover -s benchmarks/paired_review -v
python3 benchmarks/paired_review/study.py replay dev --out benchmarks/paired_review/results/dev
python3 benchmarks/paired_review/study.py replay holdout --out benchmarks/paired_review/results/holdout
python3 benchmarks/paired_review/analyze.py benchmarks/paired_review/results/holdout
```

For a fresh collection, use new result and private-log directories. Raw client transcripts stay outside the repository. Each completed session is checkpointed there. Reuse the same directories to resume an interrupted cohort with matching inputs. Public inputs and results make these cases suitable for replay and exploratory experiments once the study is released.

```sh
python3 benchmarks/paired_review/study.py run dev --out /tmp/sciskills-dev-results --private /tmp/sciskills-dev-private
python3 benchmarks/paired_review/study.py run holdout --out /tmp/sciskills-review-results --private /tmp/sciskills-review-private
```

The runner verifies ChatGPT subscription login, available included Codex usage, and first-party Claude subscription login with extra usage disabled. It removes API keys and custom providers from the child environment. Each task has a 240-second limit per session. Tool calls cannot reach the network, parent repository, or private transcripts.

The [scientific sources](science_data/README.md) identify the measured observations and distinguish the constructed review policies and input variations. The [financial sources](finance_data/README.md) document the filed tables and independent calculations.

## Reading the records

`protocol.json` maps case IDs to content digests and records the randomized order and frozen skill text. Each line of `sessions.jsonl` contains one participant's changed files, deleted paths, Python calls, elapsed time, status and field or input-level grades. Every review carries the digest of its parent draft and its staged input. A submitted numerical or protocol answer passes when its requested fields and keys match, using absolute tolerance 0.000001 for numbers. A submitted program passes when its return value is correct on every input. The grader accepts alternative implementations and ignores ordinary diagnostic output.
