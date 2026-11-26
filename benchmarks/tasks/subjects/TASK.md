# Change within participants

Repair `paired_change(readings)` in `analysis.py`. The experiment samples participants independently. A participant can have several technical readings at each visit. Each input tuple contains a participant ID, a visit ("before" or "after"), and a finite numeric reading. Input order is arbitrary.

For each participant, average the readings at each visit and subtract the before mean from the after mean. Give each participant with both visits equal weight. Report the arithmetic mean of these changes and its standard error (sample standard deviation of the participant changes divided by the square root of their count). Report the number of complete participants and the number of distinct participants excluded for a missing visit.

Return a dictionary with keys `mean_change`, `standard_error`, `n`, and `excluded`. Return None for the mean when no pairs exist and None for the standard error when fewer than two pairs exist. Use Python's standard library. Explain the repair and run a small independent check.
