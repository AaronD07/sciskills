---
name: test-the-deployment-claim
description: Verify whether a model comparison measures performance on the intended deployment population.
---

# Test the deployment claim

1. Describe the prediction event. Who or what should be new, what can legitimately have been seen, and what information exists at prediction time?
2. Inspect actual membership and feature provenance for fitting, selection and evaluation. Compare identities, related observations, and time boundaries as the use case requires. Check an example on either side of the boundary.
3. Reconstruct the candidate and baseline on a common admissible evaluation. Keep the metric and eligible inputs comparable. Verify the fitted artifact can produce the predictions being claimed.
4. Preserve gains that survive this test. Repair the comparison or narrow its conclusion when the evidence covers a different deployment setting. Confirm the released artifact reflects that choice.

## Exercise

Review the [prediction task](../../benchmarks/tasks/prediction/). State what the validation population establishes about the proposed use.
