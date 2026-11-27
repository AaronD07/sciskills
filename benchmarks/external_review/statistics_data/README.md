# P-Bench Hard

The ten question texts and CSV files come from *Fisher-R1: Training LLM Agents for Reliable Hypothesis Testing* by Jiacheng Miao, Jin Mu, Guanhua Chen and James Zou (2026). The paper reports GPT-5.4 pass@1 of 58.3% for the decision alone and 30.5% for the strict decision-and-p-value metric across the full Hard split. Those numbers concern the paper's models, harness and split. [Paper and results](https://arxiv.org/html/2608.07437v1)

The authors released P-Bench under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The question and CSV bytes here are copied intact. The evaluator manifest contains the upstream task ID, data source, SHA-256 digests and published answer key for each task. Resolve `tasks/<task_id>/` at the pinned revision to find its original files. [Pinned P-Bench release](https://huggingface.co/datasets/May2222/P-Bench/tree/402205db5904b45b3f1f0aca895980f712fd61d3)

## Selection

From the upstream manifest, retain Hard rows marked non-synthetic with null `variant` and `dataset_bytes < 500000`. Rank eligible task IDs by the lowercase hex digest of SHA-256 over the UTF-8 string `sciskills-pbench-v1:` followed by `task_id`. For dev, take one task per category in the order `iv_2sls`, `ols_coefficient_test`, `f_test`, `logistic_regression`, `cox_regression`. For each category take the lowest-ranked eligible task from a previously unused `source_id`. Repeat for holdout, carrying forward the set of used sources. This samples five types of analysis in each split with a different paper or cohort for every task. Source separation is local to this experiment. The original data and answers are publicly accessible and could have appeared in training.

## What participants and graders see

The participant workspace receives `dataset.csv` and the original question, followed by an answer-format instruction. The original questions already identify variables and state hypotheses. The adapter adds alpha and a JSON schema. Only the evaluator receives the key, task category, upstream path and digest manifest. The runner supplies the same Python environment to all conditions.

The primary metric reproduces the published strict rule. The decision at alpha 0.05 must match and the absolute difference between the two-sided normal-equivalent z values must be less than 0.5. The grader also records decision correctness on its own. It follows the authors' p-value floor of 2.2e-16 and z cap of 10. The adapter accepts numeric JSON and canonical decision labels in place of the upstream free-text conclusion. A discrepancy from an upstream key establishes a benchmark error by the model. Some questions leave analytical choices open, so a mismatch alone does not establish that a scientific conclusion is indefensible. [Official scorer at the pinned revision](https://github.com/jmu27/FisherR1/blob/968dd38bea50102a313d7d36843aba564eabc33f/evaluation/evaluate.py)

## Independent key audit

Before inspecting participant outcomes, we fitted at least two plausible specifications per question using the supplied CSV. The executable `audit_keys.py` prints the values in `key_audit.json`. After installing the parent directory's requirements, run `python3 audit_keys.py` from this directory. The audited strict subset requires every audited specification to pass the upstream strict rule. The audited decision subset requires agreement on rejection at 0.05 across all audited specifications and the key. The primary scientific interpretation should use these subsets, with full official scores reported alongside them. This finite sensitivity check cannot resolve every modeling choice.

| ID | Published p | Independently fitted p, approximately | Eligible strict / decision |
| --- | ---: | --- | --- |
| 01 | .014 | .0108 with stated controls, .0782 with branch and income indicators | no / no |
| 02 | .112 | .00878 with village-clustered arm estimates, .00882 also adjusting for age | no / no |
| 03 | .029 | .0493 for the paired race-by-treatment contrast, .0323 also adjusting for demographics | yes / yes |
| 04 | .0025 | 4.16e-45 for age, 1.89e-25 adjusting for sex, disease duration and cholesterol | no / yes |
| 05 | .0004 | .000332 with recurrent intervals clustered by patient, .00108 for first infections | yes / yes |
| 06 | .000156 | .00000595 with the incentive instrument, .000308 adding subdistrict indicators, .000300 using separate assignments | no / yes |
| 07 | 2.13e-15 | 1.86e-8 unadjusted, 2.13e-15 with ward indicators, road and village size | no / yes |
| 08 | .7929 | .735 for the linear contrast with couple clustering, .840 adding cash-prize interactions | yes / yes |
| 09 | .005 | .00552 with age, weight and race, .0196 also adjusting for obstetric history and healthcare use | yes / yes |
| 10 | .4988 | .750 in randomized patients, .827 adding the baseline characteristics named in the question | yes / yes |

The table reports two-sided tests. The direction of the alternative in the loan question also admits a one-sided interpretation. For the village immunisation case the independently fitted effects reverse the upstream significance decision. Use that case as evidence about reference sensitivity, and exclude it from claims about consequential agent errors. Cases 04 and 07 illustrate how model choices or unreproduced keys can change the strict score while preserving the substantive decision.
