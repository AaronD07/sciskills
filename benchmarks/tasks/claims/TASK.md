# Edit a results paragraph

A draft describes an observational survey. Each sentence carries a structured claim so the editor can verify it against a particular figure. Repair `audit_claims(draft, figures, version)` in `analysis.py`. Inputs are lists of dictionaries. A draft entry contains `id`, `group`, `kind` ("rate" or "cause"), `percent` (integer), `figure` (figure ID), and `text`. A figure contains `id`, `version`, `group`, `positive`, and `observed`. IDs are strings. At most one figure matches a group and version. Only respondents with an observed outcome count in the denominator.

Return a list in draft order. Each result has `id`, `status`, `figure`, `percent`, and `text`. Use the current version's matching figure. Recalculate 100 times positive divided by observed and round to the nearest integer with Python's round. A "rate" claim citing the correct figure and percentage keeps its original text verbatim and gets status "keep". A wrong percentage, stale figure, or causal claim requires status "revise". For revisions, use the publication's sentence template, replacing bracketed fields:

[Group]: [positive] of [observed] respondents ([percent]%) reported improvement.

Omit the causal interpretation. If the current figure is absent or has no observed outcomes, return status "unsupported", figure and percent None, and the sentence "The current survey does not establish this result." Otherwise return the current figure ID and recomputed percent. Use Python's standard library. Explain the repair and check it independently.
