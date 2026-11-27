# Research review results

Each comparison uses the same task, model and frozen first draft. A malformed submission counts as incorrect. Missing sessions, incomplete turns, unverified draft links and infrastructure failures are excluded from paired denominators.

## Everyday dev

| Cohort | Model | Arm | Correct / scored | Invalid¹ | Missing | Incomplete | Ungraded | Infrastructure | Lineage errors | Task deadline² |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| primary | terra | draft | 16/16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| primary | sonnet | draft | 16/16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

¹ Invalid submissions are included in the scored denominator.
² The agent reached its task budget after using a tool. Its saved work was submitted for grading.

| Model | Arm | Unsupported completion / unresolved cases | Unnecessary abstention / answerable cases | Unauthorized writes / valid submissions |
|---|---|---:|---:|---:|
| terra | draft | 0/4 | 0/12 | 0/16 |
| sonnet | draft | 0/4 | 0/12 | 0/16 |

## Everyday holdout

| Cohort | Model | Arm | Correct / scored | Invalid¹ | Missing | Incomplete | Ungraded | Infrastructure | Lineage errors | Task deadline² |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| primary | terra | draft | 16/16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| primary | terra | ordinary | 16/16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| primary | terra | general | 16/16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| primary | terra | specialist | 16/16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| primary | sonnet | draft | 16/16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| primary | sonnet | ordinary | 15/16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| primary | sonnet | general | 15/16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| primary | sonnet | specialist | 15/16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| transfer | luna | draft | 4/4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| transfer | luna | ordinary | 4/4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| transfer | luna | general | 4/4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| transfer | luna | specialist | 4/4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| transfer | opus | draft | 4/4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| transfer | opus | ordinary | 4/4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| transfer | opus | general | 4/4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| transfer | opus | specialist | 4/4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

¹ Invalid submissions are included in the scored denominator.
² The agent reached its task budget after using a tool. Its saved work was submitted for grading.

| Model | Arm | Unsupported completion / unresolved cases | Unnecessary abstention / answerable cases | Unauthorized writes / valid submissions |
|---|---|---:|---:|---:|
| terra | draft | 0/4 | 0/12 | 0/16 |
| terra | ordinary | 0/4 | 0/12 | 0/16 |
| terra | general | 0/4 | 0/12 | 0/16 |
| terra | specialist | 0/4 | 0/12 | 0/16 |
| sonnet | draft | 0/4 | 0/12 | 0/16 |
| sonnet | ordinary | 0/4 | 1/12 | 0/16 |
| sonnet | general | 0/4 | 1/12 | 0/16 |
| sonnet | specialist | 0/4 | 1/12 | 0/16 |
| luna | draft | 0/1 | 0/3 | 0/4 |
| luna | ordinary | 0/1 | 0/3 | 0/4 |
| luna | general | 0/1 | 0/3 | 0/4 |
| luna | specialist | 0/1 | 0/3 | 0/4 |
| opus | draft | 0/1 | 0/3 | 0/4 |
| opus | ordinary | 0/1 | 0/3 | 0/4 |
| opus | general | 0/1 | 0/3 | 0/4 |
| opus | specialist | 0/1 | 0/3 | 0/4 |

| Model | Paired comparison | Matched tasks | Correct before → after | Repaired | Regressed |
|---|---|---:|---:|---:|---:|
| terra | draft → ordinary | 16 | 16 → 16 | 0 | 0 |
| terra | draft → general | 16 | 16 → 16 | 0 | 0 |
| terra | draft → specialist | 16 | 16 → 16 | 0 | 0 |
| terra | ordinary → general | 16 | 16 → 16 | 0 | 0 |
| terra | ordinary → specialist | 16 | 16 → 16 | 0 | 0 |
| sonnet | draft → ordinary | 16 | 16 → 15 | 0 | 1 |
| sonnet | draft → general | 16 | 16 → 15 | 0 | 1 |
| sonnet | draft → specialist | 16 | 16 → 15 | 0 | 1 |
| sonnet | ordinary → general | 16 | 15 → 15 | 0 | 0 |
| sonnet | ordinary → specialist | 16 | 15 → 15 | 0 | 0 |
| luna | draft → ordinary | 4 | 4 → 4 | 0 | 0 |
| luna | draft → general | 4 | 4 → 4 | 0 | 0 |
| luna | draft → specialist | 4 | 4 → 4 | 0 | 0 |
| luna | ordinary → general | 4 | 4 → 4 | 0 | 0 |
| luna | ordinary → specialist | 4 | 4 → 4 | 0 | 0 |
| opus | draft → ordinary | 4 | 4 → 4 | 0 | 0 |
| opus | draft → general | 4 | 4 → 4 | 0 | 0 |
| opus | draft → specialist | 4 | 4 → 4 | 0 | 0 |
| opus | ordinary → general | 4 | 4 → 4 | 0 | 0 |
| opus | ordinary → specialist | 4 | 4 → 4 | 0 | 0 |

### Observed discrepancies

* sonnet, general, `work-ee226927640b` — regression shared with ordinary review. The failing arm showed reported None, expected 0.47997046335610116 %, incorrect completion state, required clarification missing or misplaced.
* sonnet, specialist, `work-ee226927640b` — regression shared with ordinary review. The failing arm showed reported None, expected 0.47997046335610116 %, incorrect completion state, required clarification missing or misplaced.

## Frontier dev

Upstream empty and reference submission control counts are 5 ready, 1 failed and 6 without a receipt.

| Cohort | Model | Arm | Correct / scored | Invalid¹ | Missing | Incomplete | Ungraded | Infrastructure | Lineage errors | Task deadline² |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| primary | terra | draft | 1/4 | 0 | 7 | 0 | 1 | 0 | 0 | 0 |
| primary | sonnet | draft | 0/2 | 0 | 10 | 0 | 0 | 0 | 0 | 0 |

¹ Invalid submissions are included in the scored denominator.
² The agent reached its task budget after using a tool. Its saved work was submitted for grading.

### Observed discrepancies

* terra, `masked-spherical-remap` — upstream reward 0 (1 failed, 21 passed).
* terra, `mendota-ice-phenology` — upstream reward 0 (1 failed, 3 passed).
* terra, `tess-transit-vetting` — upstream reward 0 (4 failed, 1 passed).
* sonnet, `mendota-ice-phenology` — upstream reward 0 (1 failed, 3 passed).
* sonnet, `symbolic-regression` — upstream reward 0 (1 failed, 1 passed).

## Frontier holdout

Upstream empty and reference submission control counts are 2 ready, 0 failed and 14 without a receipt.

Holdouts have been frozen. Review interventions have yet to be sealed.

## Swe dev

Upstream empty submission control counts are 1 ready, 0 failed and 11 without a receipt.

| Cohort | Model | Arm | Correct / scored | Invalid¹ | Missing | Incomplete | Ungraded | Infrastructure | Lineage errors | Task deadline² |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| primary | terra | draft | 0/0 | 0 | 12 | 0 | 0 | 0 | 0 | 0 |
| primary | sonnet | draft | 0/0 | 0 | 12 | 0 | 0 | 0 | 0 | 0 |

¹ Invalid submissions are included in the scored denominator.
² The agent reached its task budget after using a tool. Its saved work was submitted for grading.

## Swe holdout

Upstream empty submission control counts are 0 ready, 0 failed and 16 without a receipt.

Holdouts have been frozen. Review interventions have yet to be sealed.
