# Two data-analysis tasks from DS-1000

Problem 166 asks for group means and sample standard deviations in pandas. Problem 352 asks for a two-sided comparison based on sample means, variances and sizes. Both fit the project's focus on interpreting a scientific question and checking the implementation against the stated units of analysis.

## Run a task

From the repository root, create an evaluator environment with Python 3.10. The lockfile records the package versions used locally, including dependencies of the three scientific libraries.

```sh
python3.10 -m venv /tmp/sciskills-ds1000-env
/tmp/sciskills-ds1000-env/bin/python -m pip install -r benchmarks/external/requirements-lock.txt
/tmp/sciskills-ds1000-env/bin/python benchmarks/external/ds1000.py self-test
python3 benchmarks/external/ds1000.py prepare 166 /tmp/sciskills-166
```

Give the agent access to the prepared task directory. The prompt is in TASK.md and the agent writes its completion to solution.py. Keep the evaluator, its cache and the reference solutions outside the agent's accessible workspace. Grade the resulting script in an isolated environment suitable for executing generated Python. The subprocess timeout bounds the duration of an ordinary attempt and the isolated interpreter setting ignores the local Python path. The operating system still determines filesystem and network access.

```sh
/tmp/sciskills-ds1000-env/bin/python benchmarks/external/ds1000.py score 166 /tmp/sciskills-166
```

Use 352 with a fresh directory for the second task. Each problem earns one point when the completion passes all of its original execution tests. Problem 166 has two cases. Problem 352 has one fixed case, so a passing answer warrants inspection for hard-coded output. Report each task's pass count separately from SciSkills repair scores. This small, selected sample addresses two statistical tasks and has limited power to distinguish conditions.

## Source and attribution

Yuhang Lai and colleagues developed [DS-1000 (ICML 2023)](https://proceedings.mlr.press/v202/lai23b.html). Its authors release the [source artifact](https://github.com/xlang-ai/DS-1000/tree/cddd24520f374c6cdf3497adf058467394f3cf0b) under [CC BY-SA 4.0](https://github.com/xlang-ai/DS-1000/blob/cddd24520f374c6cdf3497adf058467394f3cf0b/LICENSE). The adapter selects two original prompts and executes the original tests. SciSkills adds a submission instruction, workspace layout and scoring wrapper. The upstream problem text and grader remain unchanged. Keep upstream attribution and license information with any redistributed material.

The first invocation fetches the pinned gzip into the evaluator's user cache and verifies its SHA-256 digest. Later runs reuse the same verified archive offline. The digest is `ecc827ac1a9d295cd0acf8f765b4c80592d0d749d18871e33030c7dd06d5a10c`.
