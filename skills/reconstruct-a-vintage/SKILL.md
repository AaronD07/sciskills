---
name: reconstruct-a-vintage
description: Use Python to reconstruct a scientific dataset as it was available on a reporting date before calculating results.
---

# Reconstruct a data vintage

Use when records can be revised or withdrawn and a report depends on what was available at a particular cutoff.

1. Identify the unit, the fields that identify it, the availability clock and the rule for choosing between competing revisions. Write down the reporting population, comparison dates and denominator. Keep the source files intact.
2. Run the supplied `asof.py` or implement the same operations in Python. Select eligible versions using the availability cutoff first. Within each key take the winning revision using the documented order. Apply withdrawals to those winning rows. If periods have different cutoffs, reconstruct them separately.
3. Inspect one revised key and one excluded key. Then apply the study’s inclusion rules and join the reporting populations. Record the number of keys before and after the join. Compute in Python with full precision. Pool counts for a pooled rate. For an average of unit rates, compute each unit’s rate first and combine them using the stated weights. Audit totals can differ from the quantities that define the endpoint.
4. Check the output on a different cutoff or a small hand-worked example. If the selection rule leaves conflicting versions tied, resolve the rule before using the totals.

For a CSV where public release controls availability and the highest revision number wins, a command might look like this:

```sh
python3 asof.py observations.csv --key instrument --key month --available released --cutoff 2025-12-31 --order revision:int --withdrawn state=withdrawn
```

The output keeps the selected source rows and column names. Use the actual file’s columns and policy. The default clock accepts ISO dates or timestamps with an offset. For integer periods, use `--clock int`. A Python session can import the helper directly:

```python
import csv
import asof

with open("observations.csv", newline="") as source:
    selected = list(asof.select(csv.DictReader(source), ["instrument", "month"],
                         "release_week", 12, [("revision", int)],
                         withdrawn=("state", "withdrawn"), clock=int))
```
