---
name: preserve-the-research-question
description: Check an analysis prompt against its protocol and inputs before accepting a scientific result.
---

# Preserve the research question

Use when a prompt leaves room for two analyses that would answer different questions.

## Workflow

1. State the question in one sentence. Identify the population, outcome, required inputs, method and deliverable. Cite the instruction or protocol that settles each material choice.
2. Inspect the available data. Check that it covers the requested population and period and contains the measurements needed for the method.
3. If two readings change the answer, ask the researcher one specific question. When the protocol already settles it, use that decision. If an essential input is missing, name it and explain which result depends on it.
4. Compare the final output against the original request. Trace one result to the actual input and confirm the code ran the agreed method.

## Guardrails and completion

Keep simulated examples explicitly labeled. Report any substitution separately and get agreement before using it to answer the research question. Finish with the result or the precise reason it cannot yet be produced.

## Exercise

Use the [contract task](../../benchmarks/tasks/contract/) and the [benchmark guide](../../benchmarks/README.md).
