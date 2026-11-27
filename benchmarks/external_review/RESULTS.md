# What changed when the same draft got a second review?

We ran 243 completed draft and review sessions using the Codex and Claude Code subscriptions. The general skill preserved more correct first drafts on this holdout. Neither skill showed a consistent advantage over ordinary review in repairing wrong answers.

## What happened on fresh problems

The three qualifying suites contributed eleven fresh questions and three models per question. Of 33 first drafts, 26 were correct, six contained a substantive error and one omitted the requested program. All six valid wrong drafts came from Luna on six different questions. Terra submitted the omission, which every review recovered. Sonnet and Terra had substantive failures in development.

| Review | Fixed on first review, out of 6 wrong | Correct drafts broken, out of 26 | Correct after first review, out of 33 | Fixed on independent repeat, same 6 wrong |
| --- | ---: | ---: | ---: | ---: |
| Ordinary review | 3 | 2 | 28 | 1 |
| General audit skill | 2 | 0 | 29 | 3 |
| Domain specialist skill | 3 | 1 | 29 | 1 |

Across both review rounds, the general skill repaired five of twelve opportunities and ordinary review repaired four. In three matched comparisons only the general skill succeeded. In two only ordinary review succeeded. Specialist and ordinary each repaired four, with one win unique to each. These twelve opportunities come from six drafts, all from the same model. The data do not establish a general increase in repair probability.

* **A wrong algorithm that a skill fixed.** On the repeat, the general skill replaced Luna’s exponential square-boundary search with binary search and greedy jumps around the perimeter. It passed 43/43 checks. Ordinary and specialist repeat reviews each passed 35/43, hitting resource limits on eight. On the first review all three fell short. The general reviewer explicitly said it had not run tests, so the observed gain is in the delivered algorithm.
* **A wrong financial decision that ordinary review fixed.** Luna included fee ID 65 in a merchant’s March list. No transaction met that rule’s combined scheme, debit, acquiring-bank and international conditions. The correct list had 34 IDs. Ordinary review removed the extra ID on the repeat. Both skills retained it in both rounds. On the separate January question, ordinary and specialist review shortened an initially correct ten-ID list to two. General review preserved all ten. [Independent checks and sensitivity to rule interpretation](payments_data/README.md)
* **A fix ordinary review could also make.** On the constrained shortest-path problem, the original code tried combinations of edges and exceeded the resource limit on 25/43 cases. First-round ordinary and specialist reviews replaced enumeration with a minimum-cut algorithm and passed 43/43. General review still passed 18. On the repeat all three stayed at 18.
* **A shared failure.** On the lattice-path problem all six reviews kept a solution that passed 36/43. Recognising that the code could exceed the time budget did not produce a faster implementation.

## Where the models failed

Each baseline cell is one first draft from a fresh session. We promoted suites with substantive failures on at least two development questions. Three suites qualified.

| Development screen | Correct first drafts | What the errors established |
| --- | ---: | --- |
| P-Bench Hard | 8/15 on the published strict key | The independently defensible subset had 6/6 correct strict scores and 9/9 correct decisions. Seven published-key misses would have overstated the evidence of model failure. |
| FrontierScience physics | 8/9 | Luna repeatedly endorsed −3.2 × 10⁴¹ J for the energy of a three-star orbit. The independently reconstructed energy was −8.64 × 10³⁹ J, agreeing with the published −8.6 × 10³⁹ J. All three reviewers kept the wrong result. One development question failed. |
| DABstep payments | 6/9 | Luna and Sonnet excluded 21 fee rules whose credit indicator was null. They reported €0.117667 instead of €0.120132. Terra also returned an incorrect eligibility list on a different question. |
| LiveCodeBench LeetCode Hard | 5/9 | Luna’s minimum-cost caption returned an empty string for `aca` where `aaa` was optimal. Its prefix-removal program returned five 3s for a case whose correct prefix lengths were 3, 4, 4, 3, 4. Sonnet missed two cases on that problem as well. |
| LiveCodeBench AtCoder Hard | 3/9 | Every model missed the graph game. Terra and Sonnet failed the same 4,528-vertex, 5,000-edge case. Luna also failed on three vertices with zero edges. On another task Sonnet imported NumPy into a standard-library submission, which failed all 43 checks. |

The published statistics keys warrant particular care. In a village immunisation study the published p-value of .112 implies failure to reject. Two independent village-clustered estimates produced p-values around .0088, reversing the decision. All three models rejected the null hypothesis. We excluded that case from consequential-error claims. [Statistical audit](statistics_data/README.md)

## What the development repairs show

We gave all three reviewers the same 14 valid wrong development drafts. Ordinary review repaired six, general review repaired five and specialist review repaired six. These were selected errors from development. Across the four LeetCode errors, the general and specialist each fixed three and ordinary fixed two, with different gains.

* **A specialist-only repair.** Luna’s caption draft passed 4/43 checks. The specialist called the saved method, compared it against exhaustive short strings and raised the result to 43/43. Ordinary and general review kept the original error.
* **A general-only repair.** Luna’s constrained-subsequence draft discarded smaller products that could become optimal under a later multiplication and product cap. On one failed input it returned −1 when the maximum feasible product was 200. General review retained the competing products and passed 43/43. Ordinary and specialist review fixed a separate zero case and finished at 37/43.
* **An ordinary-only repair.** On the hard graph game, ordinary review of Sonnet’s draft fixed its last wrong outcome and passed 43/43. Both skill reviews still passed 42. On the wheel-orientation problem, ordinary and specialist review repaired Luna’s slow implementation, while general review replaced it with an incomplete program that failed all 42 tests.
* **A repair shared across arms.** Sonnet’s fee calculation initially omitted wildcard rules. All three reviews recovered €0.120132. This is evidence that a second look can help, with no incremental credit attributable to the skills on this draft.

## Interpretation

Lengths and amounts were scored from the submitted artifacts. Scientific p-value and decision outcomes are available separately. Program grading separates incorrect outputs, execution errors and resource limits. In the functional-program grader, adjudication disables an inherited function-call profiler and stages submitted helper modules. The archive preserves the initial and adjudicated scores.

All counted sessions returned a submission or a completed response. One specialist payments review hit a closed tool transport before making a Python call and was retried once. The row records the failed attempt. The seven DABstep context files and upstream contest tests are fetched by pinned revision. Drafts, delivered programs, prior calls, final reviewer messages and file digests accompany the scores.

The measured intervention is assignment of the existing skill. The ordinary reviewer has the same original task, prior code and final answer, verification tools and time budget, and can independently invent any of the same checks. The suite-specific conditions and answer keys were frozen before the associated model runs. The selected development-error follow-up and AtCoder expansion were added during the study. The source tasks are public and possible training exposure is unknown. Timed code failures depend on the hardware and limits, and judge test entries within a question are correlated.

[Protocol and source papers](README.md) · [Trial-level results](results/scores.jsonl) · [Scoring and replay](report.py)
