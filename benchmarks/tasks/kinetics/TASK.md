# Decay analysis

Repair `analysis.py` while preserving its public function `decay(initial, rate_per_second, times_ms)`.

Protocol: first-order decay is C(t) = C(0) * exp(-k*t), with k in inverse seconds. Return one float per time, in input order. Times are in milliseconds. Initial concentration and rate must be finite and nonnegative; every time must be finite and nonnegative. Invalid inputs raise ValueError. Empty times return an empty list. Use Python's standard library.

Explain the change and run a small independent check. Do not change this contract.
