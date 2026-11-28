# Scientific repair holdout

Target **pending**. Complete three-arm comparisons **9/24**.

| | First draft | Ordinary review | Repair skill |
| --- | ---: | ---: | ---: |
| Scored assignments | 10 | 9 | 9 |
| Full passes among complete comparisons | 2 | 2 | 2 |

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
| finite-free-stam | sonnet | missing | missing | missing |
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
| rolling-shutter-oma | sonnet | 1 (50 passed) | missing | missing |
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
| stacking-disorder-diffraction (terra) | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| stacking-disorder-diffraction (sonnet) | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| xrd-multiphase-qpa (terra) | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| xrd-multiphase-qpa (sonnet) | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

[Protocol and interpretation](../repair-study.md)
