# Coverage sources and reference audit

The CSVs contain published observations. The release agreements, dispatch queues, receipts and archival events are constructed handoffs for this benchmark. Their timestamps, solver stop states and queue identities describe the simulation. They are not historical claims about the people who collected the source data.

Each task has an intact and compromised archive under the same instructions. The source of obligations is the release agreement and observations. The source of outcomes is the worker or artifact record. Scientific units, including accepted numerical failures in robustness tests, are defined before either archive is scored.

| Split | Source study | Unit and independent evidence |
| --- | --- | --- |
| Development | [NIST nonlinear regression](https://itl.nist.gov/div898/strd/nls/nls_main.shtml) | Three datasets at two initializations. Compare each consumed input digest and parameter vector with the registered pair. |
| Development | [Sleep restriction](https://lme4.github.io/lme4/reference/sleepstudy.html) | For 18 subjects, recover the baseline and restricted observation IDs independently from the day column. Check the rows supporting each delivered summary. |
| Development | [Orange growth](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/Orange.html) | Check the actual endpoint ages in each exported rate against the first or last two visits on its tree. |
| Holdout | [Insect count experiment](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/InsectSprays.html) | Reconcile six spray groups with their actual plot identities. Then rebuild the release table and check every group's count, total and mean against the observed plots. |
| Holdout | [Enzyme kinetics](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/Puromycin.html) | Reconcile the trace membership for 12 concentration and treatment pairs. Valid singleton cells still count. |
| Holdout | [Indomethacin](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/Indometh.html) | Reconstruct the publication state of both exposure horizons for six subjects at the release cutoff, including retraction and republication. |
| Holdout | [Tooth growth](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/ToothGrowth.html) | Compare the left and right input IDs of six registered directional contrasts with the treatment groups in the source. |
| Holdout | [Petroleum rock](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/rock.html) | Validate the twelve quartets of measurement rows against the split files and compare the worker's consumed byte-stream hash with the mandated tile. |
| Holdout | [Chicken feed](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/chickwts.html) | Check calculation entry and terminal events for twelve trial units. An input-only preflight and a numerical failure have different implications for coverage. |

In the NIST development case, the local inputs contain only the original numeric observation pairs, with a CSV header. The three original files contain certified fit values, which are excluded from participant materials. NIST supplies far and near initializations as well as a certified solution. This exercise uses the first two initializations only. [NIST starting values](https://www.nist.gov/itl/sed/statistical-reference-datasets/strd-background-information/nonlinear-regression)

The R CSVs are pinned exports from Rdatasets. The [source manifest](sources.json) records URLs and SHA-256 digests. The [R package copying terms](../../paired_review/science_data/COPYING), [lme4 package description](https://github.com/lme4/lme4/blob/master/DESCRIPTION), and original dataset manuals give attribution and distribution details. The holdout datasets are distinct from this benchmark's development studies. ToothGrowth has appeared in other SciSkills tasks with different questions.

From the repository root, run the independent reference audit:

```sh
python3 benchmarks/integrity_review/coverage_data/check.py
```

The audit reconstructs all 18 decisions from the staged packet contents, checks all eleven input hashes, and exercises the recovered-table scorer with a correct and incomplete release. It makes no model calls.
