# Do skills repair wrong answers on published hard tasks?

We use the hard subsets of P-Bench for statistical inference, LiveCodeBench for code and DABstep for financial transfer. A second science screen uses original physics problems from OpenAI’s FrontierScience Olympiad, with numerical answers checked against the published solutions. Each adapter fixes its development and holdout split before its first model session. The participant sees the original question, data or starter code and a submission format. Graders, reference values, other attempts and hidden tests stay outside the workspace. These are public releases, so prior model exposure is possible.

## Why these tasks

| Source | Why it was worth testing | Local selection |
| --- | --- | --- |
| P-Bench Hard | GPT-5.4 scored 58.3% on the decision and 30.5% when the p-value also had to agree. [Fisher-R1 paper](https://arxiv.org/html/2608.07437v1) | Original questions and study data, with audited references from independent specifications. [Selection and audit](statistics_data/README.md) |
| FrontierScience Olympiad | OpenAI reported 77% for GPT-5.2 on its full Olympiad set. [OpenAI evaluation](https://openai.com/index/frontierscience/) | Physics questions with original numerical answers or a specified numerical evaluation of a published expression. [Derivations](physics_data/README.md) |
| LiveCodeBench | A functional programming benchmark published at ICLR and used in Google DeepMind model cards. [ICLR paper](https://proceedings.iclr.cc/paper_files/paper/2025/file/94074dd5a072d28ff75a76dabed43767-Paper-Conference.pdf) · [DeepMind model card](https://deepmind.google/models/model-cards/gemini-3-1-flash-lite/) | Two cohorts using published tests and independently verified reference implementations. [LeetCode](programming_data/README.md) · [AtCoder](contest_data/README.md) |
| DABstep | The best baseline in the original paper, o4-mini, solved 14.55% of the hidden hard split. [DABstep paper](https://arxiv.org/html/2506.23719v1) | Labeled public development questions with the full 138,236-transaction dataset. Both local holdouts concern the same merchant and fee-rule family. [Labels and exclusions](payments_data/README.md) |

## Protocol

Use a fresh draft from each of GPT-6 Luna, GPT-6.1 Terra and Claude Sonnet 5.5. Qualify each suite for review when at least two distinct development questions produce a submitted, substantively incorrect draft across the three models. A disputed reference, infrastructure problem or missing answer alone cannot qualify a suite. Check questionable references independently and record exclusions. Group financial results by task family.

On each qualifying suite run all held-out questions for all three models, including items on which the draft was correct. Fork each submitted draft three ways. Ordinary review receives the original question, full draft workspace, prior tool calls and reply. The other two reviewers receive identical materials plus the existing general audit or domain review skill with its unrelated repository exercise removed. No reviewer receives scores, hints about errors or the answer key. All arms use medium effort, an eight-minute session limit and the same isolated Python tool, with local scientific libraries. Review order is seeded. The online releases and this specific harness have different model populations, resource limits and grading rules.

The P-Bench key audit is independent of the model outputs. Only independently reproducible strict labels support p-value comparisons. A decision can be counted separately when independently supported.

The primary comparison is binary repair of valid wrong drafts, paired against ordinary review on the same work. Also report regressions from correct drafts, invalid or unavailable results and the number of questions contributing. For statistics, distinguish an incorrect decision from a strict p-value discrepancy, and for programming, distinguish partial test improvement from passing all tests. A difference on one question is descriptive. Shared tasks across models are correlated.

To measure repair where an error actually occurred, a separate exploratory experiment forks every valid wrong development draft with an independently accepted key into the same three reviews. This decision was made after seeing initial development and partial holdout drafts, before conducting any development reviews. Reviewers receive no feedback from the grader. These selected mistakes are reported separately from the holdout and cannot establish an out-of-sample gain.

While the first holdout was running, we added a harder, separately reported LiveCodeBench contest cohort from AtCoder. The split and skill texts were fixed before its first draft. Use the same development gate and paired comparisons. We also scheduled a second independent review of each valid wrong holdout draft across qualified suites, irrespective of the initial review outcomes. This checks repeatability on the same artifact. A second review does not create another independent question.

## Reproduction on macOS

Install the pinned scientific wheels for Homebrew Python 3.14 with `python3 -m pip install --only-binary=:all: --target /private/tmp/sciskills-external-python-314-v1 -r benchmarks/external_review/requirements.txt`. Authenticate the Codex and Claude Code subscription clients. Included usage and Claude's extra-usage setting are checked on launch. Run `python3 benchmarks/external_review/trial.py dev --out benchmark-runs/public-hard`. Use the same command with `holdout` and then `reviews` and pass the qualifying suites via `--modes`. The local output contains tool transcripts, work products and frozen protocols. Run first drafts before scheduling reviews. Grading scripts check for two qualifying development questions before launching a holdout.

For the conditional development and repeat experiments, use `dev-repairs` on all five suites and `repeat` on the qualifying suites. The original task files, draft working files, prior tool code and final draft reply can be reconstructed from the release. Run `python3 benchmarks/external_review/report.py export` on a completed local study or `python3 benchmarks/external_review/report.py replay` to grade the published submissions without a model call. Grading runs submitted Python inside the same restricted macOS environment. The evaluator also needs SciPy available in the host Python installation.

A client or transport failure with no usable session may be retried once on the same inputs. Preserve the failed attempt and identify it in the published row. A submitted omission or wrong answer is retained as observed.
