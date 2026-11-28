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

### Distinct recorded interruptions and exclusions

Each attempt appears once, including exclusions whose replacement has yet to return. A recovered attempt can also have a current result. These counts do not enter the task accuracy denominators.

| Model | Arm | Recorded reason | Distinct recorded attempts | Same attempt as current row | Different current row | No current row |
|---|---|---|---:|---:|---:|---:|
| sonnet | draft | cli_error | 5 | 0 | 1 | 4 |
| sonnet | draft | participant_host_oom | 3 | 0 | 2 | 1 |
| sonnet | draft | tool_unavailable | 1 | 0 | 0 | 1 |
| terra | draft | cli_error | 4 | 1 | 3 | 0 |
| terra | draft | conflicting_client_permissions | 3 | 0 | 3 | 0 |
| terra | draft | participant_host_oom | 2 | 0 | 2 | 0 |

Upstream empty and reference submission control counts are 12 ready, 0 failed and 0 without a receipt.

Control names and engine identifiers are pseudonymous. Each frontier holdout score requires a recorded participant context and engine with successful negative and positive controls. Development scores can include older submissions lacking engine metadata.

| Task | Participant | Verifier | Reference controls | Recorded holdout use |
|---|---|---|---|---|
| `amr-poisson-optimize` | context-0fa668a872909fb9, engine-05e968bc8029b197 | context-0fa668a872909fb9, engine-05e968bc8029b197 | ready | — |
| `amr-poisson-optimize` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-0fa668a872909fb9, engine-05e968bc8029b197 | ready | — |
| `inelastic-constitutive-discovery` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | ready | — |
| `inverse-lithography` | context-0fa668a872909fb9, engine-05e968bc8029b197 | context-0fa668a872909fb9, engine-05e968bc8029b197 | ready | — |
| `inverse-lithography` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | ready | — |
| `masked-spherical-remap` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | ready | — |
| `mendota-ice-phenology` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | ready | — |
| `noisy-blackbox-optimization` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | ready | — |
| `rv-astrometry-fitting` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | ready | — |
| `sparse-network-assimilation` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | ready | — |
| `spin-glass-groundstate` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | ready | — |
| `symbolic-regression` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | ready | — |
| `tess-transit-vetting` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | ready | — |
| `traffic-flux-inversion` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | ready | — |

| Cohort | Model | Arm | Correct / scored | Invalid¹ | Missing | Incomplete | Ungraded | Infrastructure | Lineage errors | Task deadline² |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| primary | terra | draft | 3/12 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| primary | sonnet | draft | 1/7 | 0 | 4 | 0 | 1 | 0 | 0 | 0 |

¹ Invalid submissions are included in the scored denominator.
² The agent reached its task budget after using a tool. Its saved work was submitted for grading.

### Observed discrepancies

* terra, `amr-poisson-optimize` — upstream reward 0 (1 failed, 15 passed).
* terra, `masked-spherical-remap` — upstream reward 0 (1 failed, 21 passed).
* terra, `mendota-ice-phenology` — upstream reward 0 (1 failed, 3 passed).
* terra, `noisy-blackbox-optimization` — upstream reward 0 (1 failed, 25 passed).
* terra, `rv-astrometry-fitting` — upstream reward 0 (1 failed, 1 passed).
* terra, `sparse-network-assimilation` — upstream reward 0 (3 failed, 4 passed).
* terra, `spin-glass-groundstate` — upstream reward 0 (1 failed, 3 passed).
* terra, `tess-transit-vetting` — upstream reward 0 (4 failed, 1 passed).
* terra, `traffic-flux-inversion` — upstream reward 0 (4 failed, 3 passed).
* sonnet, `masked-spherical-remap` — upstream reward 0 (4 failed, 18 passed).
* sonnet, `mendota-ice-phenology` — upstream reward 0 (1 failed, 3 passed).
* sonnet, `rv-astrometry-fitting` — upstream reward 0 (1 failed, 1 passed).
* sonnet, `spin-glass-groundstate` — upstream reward 0 (1 failed, 3 passed).
* sonnet, `symbolic-regression` — upstream reward 0 (1 failed, 1 passed).
* sonnet, `tess-transit-vetting` — upstream reward 0 (4 failed, 1 passed).

## Frontier holdout

Upstream empty and reference submission control counts are 9 ready, 7 failed and 0 without a receipt.

Control names and engine identifiers are pseudonymous. Each frontier holdout score requires a recorded participant context and engine with successful negative and positive controls. Development scores can include older submissions lacking engine metadata.

| Task | Participant | Verifier | Reference controls | Recorded holdout use |
|---|---|---|---|---|
| `certified-sparse-regression` | context-0fa668a872909fb9, engine-05e968bc8029b197 | context-0fa668a872909fb9, engine-05e968bc8029b197 | failed | — |
| `certified-sparse-regression` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-0fa668a872909fb9, engine-05e968bc8029b197 | failed | — |
| `finite-free-stam` | context-0fa668a872909fb9, engine-05e968bc8029b197 | context-0fa668a872909fb9, engine-05e968bc8029b197 | ready | — |
| `frustrated-heisenberg-nqs` | context-0fa668a872909fb9 | context-0fa668a872909fb9 | failed | — |
| `hbv-calibration-1` | context-0fa668a872909fb9, engine-05e968bc8029b197 | context-0fa668a872909fb9, engine-05e968bc8029b197 | failed | — |
| `hysteretic-aquifer-control` | context-0fa668a872909fb9, engine-05e968bc8029b197 | context-0fa668a872909fb9, engine-05e968bc8029b197 | failed | — |
| `hysteretic-aquifer-control` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | failed | — |
| `inverse-waveguide-shape` | context-0fa668a872909fb9 | context-0fa668a872909fb9 | failed | — |
| `linked-cell-suppression` | context-0fa668a872909fb9 | context-0fa668a872909fb9 | failed | — |
| `nanoindentation-property-extraction` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | ready | — |
| `neo-orbit-determination` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | ready | — |
| `ode-law-discovery` | context-0fa668a872909fb9, engine-05e968bc8029b197 | context-0fa668a872909fb9, engine-05e968bc8029b197 | ready | — |
| `ode-law-discovery` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-0fa668a872909fb9, engine-05e968bc8029b197 | failed | — |
| `rolling-shutter-oma` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-0fa668a872909fb9, engine-05e968bc8029b197 | ready | — |
| `si-fracture-fbc` | context-0fa668a872909fb9, engine-05e968bc8029b197 | context-0fa668a872909fb9, engine-05e968bc8029b197 | ready | — |
| `si-fracture-fbc` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-0fa668a872909fb9, engine-05e968bc8029b197 | failed | — |
| `small-area-equivalence` | context-0fa668a872909fb9 | context-0fa668a872909fb9 | failed | — |
| `stacking-disorder-diffraction` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-0fa668a872909fb9, engine-05e968bc8029b197 | ready | — |
| `supraglacial-lake-classification` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-0fa668a872909fb9, engine-05e968bc8029b197 | ready | — |
| `xrd-multiphase-qpa` | context-3e0d78d2dbaf1355, engine-bbea3e0d1e140611 | context-0fa668a872909fb9, engine-05e968bc8029b197 | ready | — |

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
