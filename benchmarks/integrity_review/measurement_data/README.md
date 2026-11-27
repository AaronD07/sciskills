# Measurement evidence

The packets combine published observations with explicitly constructed reporting situations. The cutoff dates, certification decisions, register names, custody records, estimates and authorization policies were designed for this study. Study-specific thresholds describe a simulated archive decision. Each pair uses the same request and case-specific policy. Agents receive only the packet files. The generator, answer key and independent verifier remain outside the workspace.

## Sources

| Source | Observations used | Development or transfer question |
| --- | --- | --- |
| [De Vito, UCI Air Quality](https://archive.ics.uci.edu/dataset/360/air%2Bquality) | Available-hour counts and sums aggregated from the original hourly series in April and June 2004 | A reference analyzer and a similarly named process-sensor channel measure different quantities. |
| [Kwan et al., indomethacin pharmacokinetics](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/Indometh.html) | Concentration series for subjects 1 and 2 | The instrument readout and the releasable specimen series can differ at the cutoff. |
| [NPK field experiment](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/npk.html) | Twenty-four plot yields and treatment assignments | A complete point estimate and a decision identified by bounds have distinct evidence requirements. |
| [Mercury pressure series](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/pressure.html) | Nineteen reference table entries | The planning process accepts interpolated pressure; reference-table qualification has a separate rule. |
| [Black cherry trees](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/trees.html) | Census of 31 trees, their heights and volumes | A sublot can be exactly reconciled across a missing reading only when the available balance identifies its contribution. |
| [Rawlings et al., cabbage experiment](https://stat.ethz.ch/R-manual/R-devel/library/MASS/html/cabbages.html) | Ten measured heads in the C39/D16 group | Losing linkage can preserve both marginal results while making an individual-head association unidentifiable. |
| [Ezekiel, stopping distances](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/cars.html) | Fifty observations, with high-speed outcomes represented by exact integer bin sums and counts | A threshold event count can be unidentified even when the mean remains exactly recoverable. |
| [Sandstone specimen measurements](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/rock.html) | Twelve sandstone specimens, each with four cross-sections | Repeated image labels and a planning estimate carry different provenance from a retained core-level assay. |
| [Beall, insect spray experiment](https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/InsectSprays.html) | Counts from spray groups C and D | An unverified area denominator can invalidate one density endpoint while both count totals remain available. |

The air-quality packet contains derived daily summaries. The download helper fetches the original UCI archive to regenerate them. It excludes the documented missing sentinel of −200 and treats a day with no available readings as having zero valid observations. The R observations are unmodified exports from the pinned Rdatasets revision in [the source manifest](sources.json). See the [R datasets redistribution terms](../../paired_review/science_data/COPYING) and [MASS package record](https://cran.r-project.org/package=MASS).

Run the following from the repository root. The first command verifies every frozen packet offline against a second implementation, including the bounds and missing values. The second downloads the cited sources and rebuilds the tabular files.

```sh
python3 benchmarks/integrity_review/measurement_data/validate.py
python3 benchmarks/integrity_review/measurement_data/fetch.py
```
