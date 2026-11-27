# Can a review skill prevent a false scientific sign-off?

The three task families check whether an agent certifies incomplete experiments, reports a measurement the instruments do not support, or recommends a model using evidence from the wrong population. Each source has two independently staged versions. Both versions ask the same question. The published packets and submission archives are for offline replay and exploratory use once released.

## Results

The deployment specialist corrected one held-out false withdrawal that ordinary and general review both missed. It also missed a different repair that ordinary review made. The general skill produced no additional repair beyond ordinary review. No reviewer broke a correct first draft.

Development used Luna, Terra and Sonnet on intact and compromised versions of three independent source studies per family. Coverage and measurement each passed all 18 drafts and had zero qualifying sources. Their 12 holdout packets per family were implemented and independently verified, with zero model sessions on those packets. Deployment passed 16/18 development drafts. The two errors occurred on different studies, so deployment proceeded to six fresh study pairs. [Development evidence](development.md)

### Deployment holdout

A pair passes only when the model handles both the compromised and intact version of the study correctly, including the release decision, selected recipe and verified fit/test artifact. All 144 holdout sessions submitted using the permitted tool. The 36 first drafts comprised 18 correct compromised decisions and 13 correct intact decisions. Each of the five first-draft failures incorrectly withdrew a valid evaluation. Every first draft chose the correct recipe and submitted memberships that passed independent private prediction replay.

| Condition | Critical passes | Both twins correct | Wrong drafts repaired | Correct drafts broken | Median seconds | Python calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| First draft | 31/36 | 13/18 | — | — | 29.10 | 171 |
| Ordinary review | 34/36 | 16/18 | 3 | 0 | 26.04 | 150 |
| General skill | 33/36 | 15/18 | 2 | 0 | 31.46 | 186 |
| Deployment specialist | 34/36 | 16/18 | 3 | 0 | 28.55 | 164 |

General versus ordinary review changed paired success by −5.56 percentage points (95% source-cluster bootstrap interval −16.67 to 0.00). Specialist versus ordinary changed it by 0.00 points (−16.67 to +16.67). Specialist versus general gained 5.56 points (0.00 to +16.67). There are only six distinct held-out sources. Both the absolute scores and the intervals describe these constructed release audits.

| Model, both twins correct | First draft | Ordinary | General | Specialist |
| --- | ---: | ---: | ---: | ---: |
| Luna | 3/6 | 4/6 | 4/6 | 5/6 |
| Terra | 6/6 | 6/6 | 6/6 | 6/6 |
| Sonnet | 4/6 | 6/6 | 5/6 | 5/6 |

### Which decisions changed?

| Held-out draft | Actual evidence | Reviewers that fixed the false withdrawal |
| --- | --- | --- |
| Luna, theophylline participant study | The filed index matched the enrollment registry on all **77 fitting and 33 assessment observations**. Both recipes gave mean absolute error **2.342862**, so the registered reference recipe remained eligible. The specialist joined the memberships and restored certification. Ordinary and general review retained the withdrawal. | **Specialist only** |
| Sonnet, future seizure counts | The valid chronological evaluation favored the candidate. Its error was **4.415254** versus **5.935430** for the reference. | Ordinary, general and specialist |
| Luna, filtration study | The registered evaluation was valid. Both recipe errors were **10.476930**; the tie rule retained the reference. | Ordinary, general and specialist |
| Sonnet, same filtration study | The observed data and tie were the same as in Luna's case. | **Ordinary only** |
| Luna, future soybean measurements | The filed temporal split was valid. Candidate error **2.864138** was below reference **2.947284**. | None |

Across 18 compromised holdout drafts all models already identified the invalid filed evaluation and delivered the required release artifact. The specialist's unique gain concerns **preserving a valid study**, so this cohort supplies no evidence that a skill caught additional leakage. In the separate development diagnostic, all three reviewers fixed both known false withdrawals and kept both compromised twins correct. These 12 selected reviews are excluded from the holdout totals. [Holdout sessions](results/holdout/deployment/sessions.jsonl) · [Frozen holdout protocol](results/holdout/deployment/protocol.json) · [Development diagnostic](results/development_review/deployment/sessions.jsonl)

Across calibration (54), qualifying holdout (144), and the diagnostic (12), all 210 model sessions used the included Codex and Claude Code subscriptions. The pre-run implementation and skills are recorded in commit 555d1c1. Additional replay linkage checks verify that the holdout still points to the same qualifying development evidence.

## Reproduce

The participant and grading harness uses Python's standard library. Run the measured sessions on macOS with the native Codex and Claude Code clients and the local sandbox. The runner verifies subscription login and available included Codex usage, checks that Claude extra usage is off, and strips provider keys and overrides from the model environment. Only the staged scientific files and local Python tool are provided. Reviewers receive the same draft, prior code and final message. They never receive hidden grades. [Study design](design.md)

From the repository root:

```sh
python3 -m unittest discover -s benchmarks/integrity_review -v
python3 benchmarks/integrity_review/experiment.py replay dev coverage
python3 benchmarks/integrity_review/experiment.py replay dev measurement
python3 benchmarks/integrity_review/experiment.py replay dev deployment
python3 benchmarks/integrity_review/analysis.py
```

For a fresh run, specify a new results root and private transcript directory. Replace the family name for the other two families. Run the holdout only for qualifying families. It verifies the development archive and source gate before launching. Use the same paths and settings to resume unfinished work. Completed archives cannot be overwritten.

```sh
python3 benchmarks/integrity_review/experiment.py run dev coverage --results /tmp/integrity-results --private /tmp/integrity-private
python3 benchmarks/integrity_review/experiment.py run holdout coverage --results /tmp/integrity-results --private /tmp/integrity-private
```

The archive includes packet digests, client versions, randomized arms, frozen treatment text, inherited-draft and input hashes, changed artifacts, Python-call evidence, case-level checks, and time spent. Replaying verifies all scheduled identities, reconstitutes the review forks, and regrades the stored answers. The analysis computes the main comparison over matched source/model twins and resamples whole sources.

## Inspect the study

The [development gate and selected mistakes](development.md) identify which families entered holdout. The [coverage](coverage_data/README.md), [measurement](measurement_data/README.md) and [deployment](deployment_data/README.md) notes describe the real observations, the constructed conditions, and the independent checks. To verify source hashes and all reference decisions:

```sh
python3 benchmarks/integrity_review/coverage_data/check.py
python3 benchmarks/integrity_review/measurement_data/validate.py
python3 benchmarks/integrity_review/deployment_data/verify.py
```

The last command additionally uses NumPy for an independent implementation. The participant task implementations and the scored replay use the standard library. In the deployment family, reviewers select a registered candidate or reference recipe and submit exact fit/test memberships. The grader executes the selected recipe on reserved observations. These tasks measure validation and release decisions for supplied models.

The supplementary development diagnostic uses both twins from each source/model combination with a verified original error. Each receives all three review arms. It measures repair of known development mistakes and preservation of their correct counterparts. Run `python3 benchmarks/integrity_review/development_review.py replay deployment` to verify its 12 reviews.
