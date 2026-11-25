---
name: paper-to-code-consistency
description: Compare a scientific implementation against supplied equations and methodological specifications.
---

# Paper to code consistency

Use when implementing or auditing a method from a paper or supplied scientific protocol.

## Workflow

1. Read the relevant method, equations, algorithm, supplement and version. If unavailable, request the missing specification; never reconstruct it from a title or abstract alone.
2. Map each required operation to code: equation or section, symbols and units, indexing, initialization, stopping criterion, preprocessing and parameter defaults. A short table in the review is sufficient.
3. Check convention-sensitive details: log base, normalization, inclusive endpoints, axis, sign, time units, population versus sample statistics and order of operations.
4. Derive a tiny example independently from the specification. Compare intermediate quantities as well as final results, with justified tolerances. Distinguish an implementation error from an intentional methodological variant.
5. Report mismatches with precise source locations and code locations. Fix only supported discrepancies within the authorized scope. Label ambiguities and any unavailable supplementary methods.

## Guardrails and completion

Do not invent source passages, bibliographic details or expected values. Agreement with an equation does not reproduce an entire paper. State the source version, checked operations, executed tests and unresolved differences.

## Exercise

Treat the supplied protocol in `benchmarks/tasks/kinetics/TASK.md` as the specification and map it to `analysis.py`. This synthetic protocol exercise does not demonstrate reproduction of a published paper.
