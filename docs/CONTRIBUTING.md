# Contributing

## Adding a skill

1. Pick the pack it belongs to, or create `packs/<pack>/` with a `pack.json` if none fits.
2. Create `packs/<pack>/skills/<skill-name>/SKILL.md`. The frontmatter needs a single-line `name` (kebab-case, matching the folder) and a `description`. The description says what the skill does and includes "Use when ..."; that line is all the agent sees before deciding to load the skill, so make it specific.
3. In the body, write a `## Workflow` the agent can follow step by step, `## Guardrails`, and a completion section or checklist. Keep it under about 150 lines. Put long material (bug catalogs, cheat sheets) in `references/` and link to it, and put runnable checks in `scripts/`. Keep everything inside the skill folder, because the installer copies that folder on its own.
4. Add the skill to its pack's `pack.json` with a `route`: one short line describing the situation it's for. Then run `python3 scripts/install.py sync-router` to update the router's table.
5. Add an example or benchmark task that shows the skill catching something, and a way to check the result.
6. Add a row to the table in the README.
7. Run `python3 scripts/lint_skills.py .` and the tests. CI runs both.

## Adding a profile

Add an entry to `packs/profiles.json` listing existing packs. The linter rejects profiles that name packs that don't exist.

## Review

Before merging, have someone else read the skill and ask two questions. Could following it cause destructive changes, such as deleted data, rewritten results or loosened tolerances? Could it give the user false confidence, by claiming a check ran when it didn't or overstating what a check proves?
