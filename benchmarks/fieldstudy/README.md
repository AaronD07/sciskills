# Does a worksheet improve a scientific record audit?

**Terra and Sonnet answered every held-out question correctly with and without a SciSkills worksheet. Luna made substantive errors, and its mean field accuracy fell from 13.43% to 9.95% with a worksheet.** Neither cohort reached the predeclared threshold of a 10 percentage point gain with at least as many fully correct answers. [Study design](design.md)

## What we asked the agents to do

The **method comparison** packet contains a registered specimen roster, two sites, a withdrawal register, recovery tickets, instrument runs and an older dashboard description. The answer depends on which attempts belong in the experiment, how failures enter its denominator and how the sites are weighted. Each response requests eight fields, including two site estimates and the complete-case estimate.

The **surveillance records** packet asks the agent to reconstruct what a report could have said at a cutoff date. Amendments, competing versions, withdrawals and incomplete coverage affect which sites and records are eligible. The nine fields trace site selection through source IDs, counts, denominators, percentage point change and relative percentage change.

In development, Terra and Sonnet each solved one packet from each family. On the surveillance development case Luna recovered the counts and denominators correctly but reported a 40% relative increase. The two rates, 14/60 and 21/70, imply **28.57%**. On the method comparison it reported a primary difference of **+9.583** when the signed estimate was **−3.750**. We used only development answers to revise the workflows. The comparison worksheet asks for eligible attempts slot by slot. The records worksheet asks for an evidence table and a second calculation. We added Luna as a separate cohort after seeing its development errors. [Development runs](results/dev/trials.jsonl) · [Luna development runs](results/dev-luna/trials.jsonl) · [Frozen Luna schedule](results/luna-preregistration.json)

## Held-out results

Each agent received three new cases per family, with three paired repetitions per case. Within a pair, the baseline and skill runs used fresh sessions and the same task text. The treatment appended the assigned worksheet. Codex CLI used ChatGPT authentication for Terra and Luna. Claude Code used the Max subscription for Sonnet. Both clients used low effort and a 240-second limit. The packets were supplied as text and the agents returned flat JSON without tools. These trials measure audit reasoning from supplied records.

The primary measure gives equal weight to each answer's fraction of correct fields. Full passes require all fields and the correct set of keys. The last column counts paired repetitions where the skill earned a higher, equal or lower field score. Positive differences favor the skill.

| Cohort and family | Pairs | Baseline fields correct | With skill | Difference (pp) | Full passes, baseline → skill | Better / tied / worse |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Terra, method comparison | 9 | 100% | 100% | 0.00 | 9 → 9 | 0 / 9 / 0 |
| Terra, surveillance records | 9 | 100% | 100% | 0.00 | 9 → 9 | 0 / 9 / 0 |
| Sonnet, method comparison | 9 | 100% | 100% | 0.00 | 9 → 9 | 0 / 9 / 0 |
| Sonnet, surveillance records | 9 | 100% | 100% | 0.00 | 9 → 9 | 0 / 9 / 0 |
| **Primary cohort, Terra and Sonnet** | **36** | **100%** | **100%** | **0.00** | **36 → 36** | **0 / 36 / 0** |
| Luna, method comparison | 9 | 19.44% | 12.50% | −6.94 | 0 → 0 | 2 / 1 / 6 |
| Luna, surveillance records | 9 | 7.41% | 7.41% | 0.00 | 0 → 0 | 2 / 5 / 2 |
| **Secondary cohort, Luna** | **18** | **13.43%** | **9.95%** | **−3.47** | **0 → 0** | **4 / 6 / 8** |

All 108 held-out sessions submitted answers with the exact set of requested keys. There were zero missing pairs, timeouts or infrastructure errors. The comparison does not pool the selected Luna cohort with the primary cohort. [Primary trial records](results/heldout/trials.jsonl) · [Luna trial records](results/heldout-luna/trials.jsonl)

## Where the worksheets helped or hurt

- **Counting eligible specimens.** On comparison case A the roster started with ten specimens. Two withdrawals were recorded by the lock, including one recorded at the lock minute itself. In all three repetitions the Luna baseline reported the correct eight planned specimens. All three worksheet runs reported ten. Across its eight requested fields, this case lost 12.50 percentage points with the worksheet. [Comparison packets](comparisons.py)
- **Preserving the site panel.** For surveillance case C, W's first-round data had been withdrawn by the freeze. In repetition one the Luna baseline included W and returned a first-round count of 22/88. The worksheet run correctly retained only A and J, giving 15/70. On repetition two the baseline returned the correct panel, while the worksheet run added E despite its second-round withdrawal. The first-round numerator then rose incorrectly to 23. [Surveillance packets](records.py)
- **Distribution across cases.** The primary cohort tied on every case. Luna's case-level differences were −12.50, −4.17 and −4.17 percentage points for comparison A, B and C. For surveillance A, B and C they were +3.70, 0.00 and −3.70. The worksheets improved one of six case averages, tied one and lowered four.

The results support two narrower conclusions. The explicit protocol sheets already supplied Terra and Sonnet with enough detail to solve these six cases at baseline. Luna had room to improve, yet adding instructions did not reliably stabilize its choice of records or denominator. Three repetitions of the same packet measure response variability on that packet. There are six distinct held-out packets here, and their cases and fields should not be counted as independent evidence about all scientific audits.

## Reproduce the analysis

From the repository root, run:

```sh
python3 benchmarks/fieldstudy/analyze.py benchmarks/fieldstudy/results/heldout
python3 benchmarks/fieldstudy/analyze.py benchmarks/fieldstudy/results/heldout-luna
```

The analysis checks the saved schedule, prompt and answer-key hashes, grades the archived replies again, and emits the paired summaries for each model, family and case. The command works offline. [Primary protocol](results/heldout/protocol.json) · [Luna protocol](results/heldout-luna/protocol.json)

The archived DS-1000 diagnostic and the new transfer experiment use different outcomes. Five of twelve previously passing problem 352 submissions passed all the diagnostic input changes. Those were five Codex submissions. The separate code-transfer study tests whether an input-preservation skill helps on additional tasks. [Archived replay](transfer352.jsonl) · [Code-transfer study](../input-transfer/README.md)
