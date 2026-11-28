---
name: check-a-local-optimum
description: Review a numerical fit or search whose result may depend on its initial state or the moves its solver can make.
---

# Check a local optimum

Use this when the work selects a candidate by search. If the work makes no such choice, verify the requested deliverable directly. A proof or exhaustive check can settle a claim of optimality.

1. Recover the saved candidate, the objective in the requested units, and the feasibility constraints. Recompute its score. Identify which changes the solver can make in one step.
2. Reserve part of the available budget for a competing run. Start from a meaningfully different feasible state, or change coupled variables together if one-at-a-time moves can trap the search. Refine the alternative with the same solver when it can represent that alternative. Otherwise use a method that can. Keep the data, objective and evaluation budget comparable.
3. Score both candidates by the original criterion. Check feasibility and the predicted quantity someone will use. For noisy measurements, repeat enough of the comparison under matched conditions to distinguish an improvement from ordinary variation.
4. If the alternative wins, use that evidence to improve the delivered method and rerun it from its normal entry point. If the candidates tie, report the scope of the search. A global claim needs a bound or certificate that covers the unexplored possibilities.

## Exercise

Place two collection points on a line to minimize the total distance each household travels to its nearest point. Put households in three separated clusters. Compare local refinement from two different pairs of starting locations against the best pair from enumerating the household locations.
