# Paired benchmark runs

Repair `compare(schedule, log)` in `analysis.py`. The schedule lists unique (case, repetition) tuples. Each pair has two planned runs, "baseline" and "skill". Log entries are (case, repetition, condition, status, score) tuples. A completed run has status "ok" and a finite score from zero to one. A "timeout" or "crash" has score None. An absent log entry means the run is missing.

The primary metric is the mean skill score minus the mean baseline score over all planned pairs. Assign a zero score to each timeout, crash or missing run. Also compute the mean paired difference restricted to pairs where both runs completed. Return `delta_all`, `delta_complete`, `planned_pairs` and `complete_pairs` in a dictionary. An average with an empty denominator is None.

Match runs by case and repetition. Raise ValueError for duplicate entries for the same planned run or entries outside the schedule. Use Python's standard library, explain the repair and check it independently.
