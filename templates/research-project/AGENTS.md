# Agent instructions for <PROJECT NAME>

<!--
Copy this file to the root of your research project and fill in each section.
Delete any section that does not apply, but write "none" rather than leaving
a placeholder: an agent cannot tell an empty section from a forgotten one.
Keep it short; agents read it at the start of every session.
-->

## The science

<!-- Two to four sentences an outsider could follow. What does this code compute, and why? -->

## Quantities and units

<!-- One row per physical quantity that crosses a function or file boundary. -->

| Quantity | Name in code | Unit | Valid range | Notes |
| --- | --- | --- | --- | --- |
| e.g. concentration | `conc` | mol/L | >= 0 | measured; None means missing |
| e.g. time | `t_ms` | ms | >= 0 | instrument logs milliseconds |

Convert units at one boundary: <!-- e.g. "in io.py on load; everything inside is SI" -->

## Conventions

<!-- Delete lines that do not apply; add any your field uses. -->

- Indexing: <!-- 0-based / 1-based; genome coordinates half-open or closed -->
- Angles: <!-- radians / degrees -->
- Logarithms: <!-- natural / base 10 / base 2 -->
- Time and dates: <!-- time zone, calendar -->
- Coordinate frames or reference builds: <!-- e.g. ICRS J2000, hg38 -->
- Statistics: <!-- sample (ddof=1) or population std; how error bars are defined -->

## Data

- Raw data lives in: <!-- path --> . It is read-only; never modify or overwrite it.
- Missing values are encoded as: <!-- None / NaN / -999 / empty cell --> . Zero is a real measurement.
- Data that must never be committed: <!-- large files, patient data, unpublished results -->

## Environment

- Python version used for results: <!-- e.g. 3.12.3 -->
- Dependency manager and lockfile: <!-- e.g. uv + uv.lock -->
- Create the environment: `<!-- command -->`
- Random seeds are set in: <!-- file or config -->

## Checks

- Run the tests: `<!-- command -->`
- Known answers the code must reproduce: <!-- e.g. "decay of 8 with k=ln2 per s gives 4 at t=1000 ms"; or a reference output file and its source -->
- Tolerances and why: <!-- e.g. rel 1e-9 for float64 closed-form results -->

## Rules for the agent

- Ask before changing any scientific result, method, parameter default or protocol step.
- Never edit reference values, loosen tolerances, drop or impute data, or skip tests to make checks pass.
- Report every check as run (with its output) or not run. Do not say "should work".
- Explain changes in terms of the science, not only the code.
- When unsure which check applies, follow `sciskills-start-here` from SciSkills.
