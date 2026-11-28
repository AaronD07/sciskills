# Scientific repair holdout

Target **pending**. Complete three-arm comparisons **10/24**.

| | First draft | Ordinary review | Repair skill |
| --- | ---: | ---: | ---: |
| Scored assignments | 11 | 10 | 10 |
| Full passes among complete comparisons | 3 | 3 | 3 |

The skill earned +0 net full passes over ordinary review. It repaired 0 distinct tasks on which both the draft and ordinary review failed.

- Skill-only repairs of wrong drafts — None.
- Ordinary-only full passes — None.
- Correct drafts broken by the skill — None.

## Outcomes by task

Scores below are upstream rewards. A full pass earns 1. Where the verifier reports individual checks, the table gives passed and failed counts. Differences in check counts can reveal partial repairs or regressions even when both rewards are zero.

| Task | Model | First draft | Ordinary review | Repair skill |
| --- | --- | --- | --- | --- |
| certified-sparse-regression | terra | 0 (1 failed, 2 passed, 1 skipped) | 0 (1 failed, 2 passed, 1 skipped) | 0 (1 failed, 2 passed, 1 skipped) |
| certified-sparse-regression | sonnet | missing | missing | missing |
| finite-free-stam | terra | 0 (3 failed, 6 passed) | 0 (3 failed, 6 passed) | 0 (3 failed, 6 passed) |
| finite-free-stam | sonnet | 0 (3 failed, 6 passed) | missing | missing |
| frustrated-heisenberg-nqs | terra | missing | missing | missing |
| frustrated-heisenberg-nqs | sonnet | missing | missing | missing |
| hbv-calibration-1 | terra | missing | missing | missing |
| hbv-calibration-1 | sonnet | missing | missing | missing |
| hysteretic-aquifer-control | terra | missing | missing | missing |
| hysteretic-aquifer-control | sonnet | missing | missing | missing |
| nanoindentation-property-extraction | terra | 0 (1 failed, 2 passed) | 0 (1 failed, 2 passed) | 0 (1 failed, 2 passed) |
| nanoindentation-property-extraction | sonnet | 0 (1 failed, 2 passed) | 0 (1 failed, 2 passed) | 0 (1 failed, 2 passed) |
| ode-law-discovery | terra | missing | missing | missing |
| ode-law-discovery | sonnet | missing | missing | missing |
| rolling-shutter-oma | terra | 1 (50 passed) | 1 (50 passed) | 1 (50 passed) |
| rolling-shutter-oma | sonnet | 1 (50 passed) | 1 (50 passed) | 1 (50 passed) |
| si-fracture-fbc | terra | missing | missing | missing |
| si-fracture-fbc | sonnet | missing | missing | missing |
| small-area-equivalence | terra | missing | missing | missing |
| small-area-equivalence | sonnet | missing | missing | missing |
| stacking-disorder-diffraction | terra | 0 (3 failed, 2 passed) | 0 (3 failed, 2 passed) | 0 (3 failed, 2 passed) |
| stacking-disorder-diffraction | sonnet | 1 (5 passed) | 1 (5 passed) | 1 (5 passed) |
| xrd-multiphase-qpa | terra | 0 (1 failed, 3 passed) | 0 (1 failed, 3 passed) | 0 (1 failed, 3 passed) |
| xrd-multiphase-qpa | sonnet | 0 (2 failed, 2 passed) | 0 (2 failed, 2 passed) | 0 (2 failed, 2 passed) |

## Individual scientific checks

Each change below compares the same upstream check across all three arms. A fix changes a failed draft check to a pass. A regression changes a passing draft check to a failure. These component changes do not count toward the full-task target.

| Task and model | Comparable | Both fixed | Ordinary alone fixed | Skill alone fixed | Both broke | Ordinary alone broke | Skill alone broke | Skipped or other |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| certified-sparse-regression (terra) | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| finite-free-stam (terra) | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| nanoindentation-property-extraction (terra) | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| nanoindentation-property-extraction (sonnet) | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling-shutter-oma (terra) | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rolling-shutter-oma (sonnet) | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stacking-disorder-diffraction (terra) | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stacking-disorder-diffraction (sonnet) | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| xrd-multiphase-qpa (terra) | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| xrd-multiphase-qpa (sonnet) | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Review time and tool use

Both review sessions have recorded wall time and shell requests for 10 of 10 complete comparisons. Wall time includes staging and cleanup. Each logged shell request counts once, including requests that returned an error.

| Task and model | Ordinary seconds | Skill seconds | Ordinary shell requests | Skill shell requests |
| --- | ---: | ---: | ---: | ---: |
| certified-sparse-regression (terra) | 298.21 | 329.36 | 9 | 18 |
| finite-free-stam (terra) | 69.82 | 158.49 | 5 | 9 |
| nanoindentation-property-extraction (terra) | 72.16 | 114.84 | 10 | 8 |
| nanoindentation-property-extraction (sonnet) | 89.54 | 706.46 | 12 | 21 |
| rolling-shutter-oma (terra) | 45.23 | 115.52 | 7 | 10 |
| rolling-shutter-oma (sonnet) | 527.59 | 620.96 | 17 | 17 |
| stacking-disorder-diffraction (terra) | 68.80 | 427.69 | 5 | 8 |
| stacking-disorder-diffraction (sonnet) | 215.25 | 573.39 | 8 | 10 |
| xrd-multiphase-qpa (terra) | 66.43 | 111.84 | 7 | 11 |
| xrd-multiphase-qpa (sonnet) | 91.13 | 222.03 | 8 | 19 |
| **Total** | 1544.16 | 3380.58 | 88 | 131 |

[Protocol and interpretation](../repair-study.md)
