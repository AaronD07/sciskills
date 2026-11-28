# Research project template

`AGENTS.md` tells a coding agent the facts it cannot safely guess about your project: units, conventions, where raw data lives, how to run the checks and what it must never change. Most unit, indexing and data-handling mistakes come from an agent guessing one of these.

## Use it

1. Copy `AGENTS.md` into the root of your research project.
2. Fill in every section, or write "none". Ten minutes here saves debugging later.
3. Tell your agent to read it:
   - Many agents (for example Codex and Cursor) read `AGENTS.md` automatically.
   - Claude Code reads `CLAUDE.md`. Create a `CLAUDE.md` containing the single line `@AGENTS.md` so both stay in sync.
4. Update it when the project changes: a new instrument, a new unit, a new dataset.

The file supports careful work; it does not check anything by itself. Pair it with the skills in `skills/` and real tests.
