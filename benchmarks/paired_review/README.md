# Can a skill help an agent repair its own scientific analysis?

The unit of comparison is a first draft. Two reviewers receive that draft, its Python calls, its files, final chat message and the original assignment. The skill reviewer also receives the workflow for that type of deliverable. Both have access to the same Python interpreter. The [study design](design.md) defines the primary measure and the criterion for a meaningful improvement.

## What happened

The program-review skill repaired one scientific error that ordinary review missed. The protocol-review skill changed a correct scientific value on another task. Across the 71 science drafts with three valid sessions, both review conditions passed 69. The study did not meet its predeclared 10-point improvement criterion.

| Sample | Drafts correct | Ordinary review correct | Skill review correct | Difference in points | 95% source-cluster interval |
| --- | ---: | ---: | ---: | ---: | ---: |
| Science, all 72 drafts | 70/72 | 69/72 | 70/72 | +1.39 | −2.78 to +5.56 |
| Science, 71 fully submitted pairs | 69/71 | 69/71 | 69/71 | 0.00 | −4.17 to +4.17 |
| Finance transfer | 21/24 | 20/24 | 21/24 | +4.17 | 0.00 to +12.50 |

The primary analysis scores one ordinary Luna review as failed because Codex emitted an empty web-search event outside the permitted Python tool. The event returned no search results. Its saved answer matched the reference. All other 287 holdout sessions used the permitted tool and submitted normally. The complete-pair sensitivity removes the entire affected triple. The science interval resamples eight studies, each with three tasks attempted by each model. The finance interval resamples eight issuers. Repetitions on one data source share a cluster.

| Science breakdown | First draft | Ordinary review | Skill review |
| --- | ---: | ---: | ---: |
| Luna | 22/24 | 21/24 | 23/24 |
| Terra | 24/24 | 24/24 | 23/24 |
| Sonnet | 24/24 | 24/24 | 24/24 |
| Numerical reports | 24/24 | 24/24 | 24/24 |
| Analysis programs | 23/24 | 23/24 | 24/24 |
| Protocol decisions | 23/24 | 22/24 | 22/24 |

Only two of the 72 science drafts failed initially. Even repairing both could improve on the first draft by at most 2.78 percentage points. Counts collected on this benchmark cannot establish how common the same mistakes are in a broader range of research.

### Where a review changed the answer

* **A genuine repair.** In the grouped oesophageal cancer data, Luna's program gave a score of 0.313043 for ages 25–34. It rewarded a higher exposure in the control. The specification rewards a higher exposure in the case and gives half credit for ties. Ordinary review retained the implementation. Skill review reversed the comparison and obtained 0.686957. Its program passed all five inputs, up from one. The skill supplied no exposure labels, numbers, comparison direction or hidden cases.
* **A scientific regression.** On the tooth-growth release, Terra's first draft and ordinary review used the highest eligible revision number. Revision 2 set bin A's threshold to 11. Skill review instead chose the largest threshold value, 12 from revision 1. It changed the weighted response for ascorbic acid from 0.32 to 0.23. The packet calls this the “highest threshold revision” and includes a separate revision column. The wording helps explain the alternative reading.
* **A format failure.** Luna correctly returned 80 retained runs and a calibrated speed of 299853.275 km/s on the Morley study. Its series IDs were integers, where the methods requested strings. Both reviewers retained them.
* **Financial transfer.** Neither reviewer repaired any of the three incorrect finance drafts. Ordinary review changed a correct Netflix maturity share from 11.9748% to 52.4305%. Skill review preserved the correct share. For Ford, both reviewers computed a funded-status change of −1973 million dollars against a verified −2093 million. The finance margin comes entirely from preserving the Netflix draft. [Filing calculations](finance_data/README.md)

Across all science pairs the skill exclusively repaired one wrong draft and ordinary review exclusively repaired zero. Each review broke one correct draft under the frozen scoring rule, including the tool-rule failure above. On finance, ordinary review broke one and skill review broke zero. Science skill reviews made 243 Python calls with a median elapsed time of 23.27 seconds, versus 222 calls and 15.79 seconds for ordinary review. Finance used 67 calls in each arm, with medians of 19.63 and 13.78 seconds. Concurrent launches and provider latency affect elapsed time.

The [frozen protocol](results/holdout/protocol.json), [trial archive](results/holdout/sessions.jsonl), and [development errors](development.md) support inspection at the individual-draft level. The three models used ordinary subscription sessions throughout collection. No model served as a judge.

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
