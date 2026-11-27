---
name: review-an-analysis-program
description: Test a drafted scientific program on fresh inputs through the caller's actual entry point.
---

# Review an analysis program

Use when another scientist will run the delivered code on their own data.

1. Find the promised file and entry point. Load the saved implementation as a caller would. A code block in a conversation cannot satisfy a file-based interface.
2. Construct a small valid input with a result you can calculate independently. Predict the result before running the program. Follow what it reads from its arguments, files or configuration.
3. Change one meaningful input. Predict what should change and what should stay the same. Run both cases against the saved code and compare actual outputs with those predictions.
4. If a case fails, trace the first disagreement, make the smallest justified repair and rerun both cases. Deliver the implementation at the requested location.

Choose input changes the scientific method permits. Reordering observations is meaningful for some analyses. Record the test in working notes when the requested output is code only.

## Exercise

Use the [seeded simulation](../../examples/pin-the-environment/). Run its existing entry point with a fixed seed, then change a caller-supplied parameter and check the expected behavior.
