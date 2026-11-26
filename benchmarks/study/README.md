# Paired study, November 26, 2026

Both agents passed 15 of 18 attempts with the assigned skill and 15 of 18 without it. Each of the 36 paired comparisons tied. The four local tasks were too easy to distinguish the conditions on correctness. One external problem exposed a repeated mistake when agents copied example inputs.

| Task | Assigned skill | Codex baseline | Codex skill | Claude baseline | Claude skill |
| --- | --- | ---: | ---: | ---: | ---: |
| Requested cohort | Preserve the research question | 3/3 | 3/3 | 3/3 | 3/3 |
| Paired observations | Identify the independent unit | 3/3 | 3/3 | 3/3 | 3/3 |
| Paired run logs | Compare experiments fairly | 3/3 | 3/3 | 3/3 | 3/3 |
| Survey claims | Trace claims to evidence | 3/3 | 3/3 | 3/3 | 3/3 |
| DS-1000 166 | Identify the independent unit | 0/3 | 0/3 | 0/3 | 0/3 |
| DS-1000 352 | Known answers first | 3/3 | 3/3 | 3/3 | 3/3 |

Each entry counts submissions that passed every check. All 48 local submissions passed all eight checks for their task. On the selected DS-1000 problems, each condition passed 6 of 12 submissions across both agents.

## What the failures tell us

On problem 166, all 12 submissions recreated the example dataframe before calculating grouped means and standard deviations. The original evaluator supplies a second dataframe with different group labels. Overwriting that input makes the example output look correct while the second case fails. The common study instruction asked for complete Python source, while DS-1000 expects an insertion into existing code. That wording may have encouraged copying the example. This is one observed interaction between the prompt and the evaluation format.

Problem 352 tests only one set of summary statistics. All 12 submissions computed a two-sided Welch p-value. Seven also assigned the exact sample means, variances and sizes from the prompt to the evaluator's input variables. These were the six Claude submissions and Codex's second skill run. Those seven answers would reuse the example values even if the evaluator supplied different inputs. A pass on the single fixed example therefore offers limited evidence of transfer.

The native tasks gave both agents an explicit contract and starter code. With every native answer passing at baseline, these tasks leave no room to measure improvement in the primary outcome. Six tasks, three repetitions, and a public external dataset also limit generalization. Median CLI wall time in seconds was 12.3 baseline and 14.8 with skills for Codex, and 7.1 and 7.7 for Claude. Concurrency and provider load affect these timings.

## Procedure

The pilot used Codex CLI 0.172.0 with gpt-6.2-sol at low reasoning effort and Claude Code 2.1.325 with claude-sonnet-5-5. The original second client, Gemini CLI, rejected the available individual account at preflight. Both selected clients passed a separate smoke check before measurement. Each agent received the same wrapper and task text for both conditions. The skill condition appended the assigned skill in full. Native tasks included faulty starter code. External tasks kept the upstream problem text and the adapter's submission instruction.

The runner shuffled 36 pairs and the condition order within each pair using seed 20261126, submitted the 72 jobs in recorded order, and used six concurrent processes. Fresh temporary working directories and independent CLI sessions kept evaluator inputs out of the prompts. Claude's tools were disabled. Codex used a read-only sandbox and an instruction to use no tools; its JSON event logs were checked for tool activity. Participants returned source in one response. The primary outcome therefore measures one-response code generation. All 72 runs submitted code before the 180-second generation limit. No trial required human edits or a retry.

The runner strips a single enclosing Markdown fence if present and normalizes the final newline. The native grader compares outputs with its predefined checks. The external grader runs the pinned upstream tests. Generated submissions run separately in a temporary macOS sandbox with network access and writes to the repository disabled. Native worker timeout is five seconds. Each upstream solution has a 120-second time limit.

[Trial records](results/trials.jsonl) include model and condition, observed time, prompt and submission hashes, and individual check outcomes. The [protocol](results/protocol.json) records the schedule, versions and grader hashes. The [submission archive](results/submissions.jsonl) stores Python source by SHA-256 and omits private CLI transcripts. External task provenance and licensing, including for example inputs reproduced in completions, are documented in the [DS-1000 adapter guide](../external/README.md).

## Reproduce

Install the pinned DS-1000 evaluator environment and populate its verified cache by following the adapter guide. From the repository root on macOS, replay the published model outputs without contacting either model provider:

```sh
python3 benchmarks/study/replay.py --external-python /tmp/sciskills-ds1000-env/bin/python
```

To collect a new sample, use authenticated Codex and Claude clients with the recorded models. Choose a fresh run directory outside the checkout and a separate output directory. Set CODEX_BIN or CLAUDE_BIN if the binaries are outside the normal search path.

```sh
python3 benchmarks/study/run.py /tmp/sciskills-study-new
python3 benchmarks/study/score.py /tmp/sciskills-study-new \
  --external-python /tmp/sciskills-ds1000-env/bin/python \
  --output /tmp/sciskills-study-new-results
```

Run directories contain private CLI output. The generation command can resume a stopped batch at the same path, retaining an interrupted attempt in the original denominator.
