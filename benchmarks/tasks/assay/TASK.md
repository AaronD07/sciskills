# Assay summary

Repair `analysis.py` while preserving `summarize(values)`.

Each input is a finite number or None. None means a missing measurement; zero is a measured zero. Return a dict with `mean` (arithmetic mean of observed values, or None if none are observed), `observed` (number observed), and `missing` (number missing). Reject NaN and infinity with ValueError. Empty input has mean None and both counts zero. Use Python's standard library.

Explain the change and run a small independent check. Do not change this contract.
