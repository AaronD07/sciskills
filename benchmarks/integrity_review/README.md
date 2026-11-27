# Can a review skill prevent a false scientific sign-off?

The three task families check whether an agent certifies incomplete experiments, reports a measurement the instruments do not support, or recommends a model using evidence from the wrong population. Each source has two independently staged versions. Both versions ask the same question. The published packets and submission archives are for offline replay and exploratory use once released.

## Reproduce

The participant and grading harness uses Python's standard library. Run the measured sessions on macOS with the native Codex and Claude Code clients and the local sandbox. The runner verifies subscription login and available included Codex usage, checks that Claude extra usage is off, and strips provider keys and overrides from the model environment. Only the staged scientific files and local Python tool are provided. Reviewers receive the same draft, prior code and final message. They never receive hidden grades. [Study design](design.md)

From the repository root:

```sh
python3 -m unittest discover -s benchmarks/integrity_review -v
python3 benchmarks/integrity_review/experiment.py replay dev coverage
python3 benchmarks/integrity_review/experiment.py replay dev measurement
python3 benchmarks/integrity_review/experiment.py replay dev deployment
python3 benchmarks/integrity_review/analysis.py
```

For a fresh run, specify a new results root and private transcript directory. Replace the family name for the other two families. Run the holdout only for qualifying families. It verifies the development archive and source gate before launching. Use the same paths and settings to resume unfinished work. Completed archives cannot be overwritten.

```sh
python3 benchmarks/integrity_review/experiment.py run dev coverage --results /tmp/integrity-results --private /tmp/integrity-private
python3 benchmarks/integrity_review/experiment.py run holdout coverage --results /tmp/integrity-results --private /tmp/integrity-private
```

The archive includes packet digests, client versions, randomized arms, frozen treatment text, inherited-draft and input hashes, changed artifacts, Python-call evidence, case-level checks, and time spent. Replaying verifies all scheduled identities, reconstitutes the review forks, and regrades the stored answers. The analysis computes the main comparison over matched source/model twins and resamples whole sources.

## Inspect the study

The [development gate and selected mistakes](development.md) identify which families entered holdout. The [coverage](coverage_data/README.md), [measurement](measurement_data/README.md) and [deployment](deployment_data/README.md) notes describe the real observations, the constructed conditions, and the independent checks. To verify source hashes and all reference decisions:

```sh
python3 benchmarks/integrity_review/coverage_data/check.py
python3 benchmarks/integrity_review/measurement_data/validate.py
python3 benchmarks/integrity_review/deployment_data/verify.py
```

The last command additionally uses NumPy for an independent implementation. The participant task implementations and the scored replay use the standard library. In the deployment family, reviewers select a registered candidate or reference recipe and submit exact fit/test memberships. The grader executes the selected recipe on reserved observations. These tasks measure validation and release decisions for supplied models.

The supplementary development diagnostic uses both twins from each source/model combination with a verified original error. Each receives all three review arms. It measures repair of known development mistakes and preservation of their correct counterparts. Run `python3 benchmarks/integrity_review/development_review.py replay deployment` to verify its 12 reviews.
