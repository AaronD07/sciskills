# Contributing a skill

A skill should be narrowly scoped, actionable, and auditable.

1. Create `skills/<skill-name>/SKILL.md` with single-line `name` (matching the directory, kebab-case) and `description` frontmatter. The description says what the skill does and includes "Use when ..." so agents know when to load it.
2. Explain **when to use it**, a step-by-step agent workflow, guardrails, and a completion checklist.
3. Add a small example under `examples/<skill-name>/` with instructions and checks.
4. Describe any assumptions, tool limitations, or failure modes.
5. Prefer verification commands over unsupported claims that an agent has completed a task.
6. Add a row for the skill to the routing table in `skills/sciskills-start-here/SKILL.md` and to the README table.
7. Run `python3 scripts/lint_skills.py .` and the tests; CI runs both.

Before merging, have a second contributor review whether the instructions could cause destructive changes or false confidence.
