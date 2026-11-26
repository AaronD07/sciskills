# Contributing a skill

A skill should be narrowly scoped, actionable, and auditable.

1. Create `skills/<skill-name>/SKILL.md` with `name` and `description` frontmatter.
2. Explain **when to use it**, a step-by-step agent workflow, guardrails, and a completion checklist.
3. Link a runnable example under `examples/` or a scored exercise under `benchmarks/tasks/`. Include instructions and an independent check.
4. Describe any assumptions, tool limitations, or failure modes.
5. Prefer verification commands over unsupported claims that an agent has completed a task.

Before merging, have a second contributor review whether the instructions could cause destructive changes or false confidence.
