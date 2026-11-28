# SciSkills

SciSkills is a set of skills for AI coding agents, aimed at the mistakes that hurt research code: a unit converted twice, zeros silently dropped as missing data, test data leaking into a fit, an environment nobody else can rebuild. We're building it for a Caltech CS 143 project.

Most scientists who write code with an AI agent aren't software engineers, and agent-written code usually looks right. The dangerous bugs are the ones that still print a reasonable number. Each skill is a short workflow the agent follows when it's relevant. For example: test against a hand-calculated answer before trusting a new method, trace units from input to output, or reproduce a suspected bug before reporting it. Where we can, a skill ends in a check you can rerun yourself without the agent.

## How it's organized

- **Skill**: a folder with a `SKILL.md` that says when to use it and what to do, plus optional `scripts/` and `references/`. Until a task matches, the agent only sees the skill's one-line description, so an installed skill costs very little context.
- **Pack**: a group of related skills that install together, described by `packs/<pack>/pack.json`.
- **Profile**: a named set of packs in `packs/profiles.json`. Profiles let someone install what fits their work (a biologist doesn't need the Lean skills).
- **Router**: `sciskills-start-here` is always installed. It asks the researcher a few plain questions and picks which skills to follow. Its routing table is generated at install time and lists only the skills you installed.

## Skills available now

| Pack | Skill | Use it when |
| --- | --- | --- |
| core | [sciskills-start-here](packs/core/skills/sciskills-start-here/SKILL.md) | You're not sure which check a task needs |
| core | [known-answers-first](packs/core/skills/known-answers-first/SKILL.md) | Writing tests, or about to trust a new numerical method |
| core | [check-the-numbers](packs/core/skills/check-the-numbers/SKILL.md) | Handling measurements, units, missing values or NaN |
| core | [paper-to-code-consistency](packs/core/skills/paper-to-code-consistency/SKILL.md) | Implementing or checking a method from a paper or protocol |
| core | [adversarial-review](packs/core/skills/adversarial-review/SKILL.md) | Reviewing an analysis or AI-written code; results look too good |
| compute-env | [pin-the-environment](packs/compute-env/skills/pin-the-environment/SKILL.md) | Sharing a project, or results differ between machines |
| compute-env | [memory-budget](packs/compute-env/skills/memory-budget/SKILL.md) | Running out of RAM or GPU memory, or scaling up |

## Install into a project

From a clone of this repo (Python 3.10+, no dependencies):

```bash
python3 scripts/install.py list
python3 scripts/install.py install --into ~/my-project --profile general
```

This copies the skills into `~/my-project/.claude/skills`, where Claude Code finds them. For another agent, pass `--skills-dir` with the folder it reads skills from. Other useful options:

- `--packs core,compute-env` installs specific packs instead of a profile.
- `--link` symlinks instead of copying, so edits in this repo show up in the project immediately.
- `--dry-run` shows what would be installed without writing anything.

Running `install` again replaces the previous install. `uninstall --into ~/my-project` removes it. Both only touch skills that SciSkills installed, which are tracked in `.sciskills.json`.

Also copy [templates/research-project/AGENTS.md](templates/research-project/) into your project and fill it in. It records the facts an agent shouldn't guess: units, conventions, where raw data lives and how to run the checks.

## Working on this repo

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s examples/pin-the-environment -p 'test_*.py' -v
python3 scripts/lint_skills.py .
python3 scripts/install.py sync-router    # after editing any pack.json
```

The linter checks each skill's frontmatter and required sections and validates the paths it mentions. It also checks that every skill directory is listed in its pack's manifest and that the committed router table is up to date. CI runs all of this on Python 3.10 and 3.12. `scripts/check_repo.py <path>` is a separate helper that reports whether a project has tests, lockfiles and seed calls; it doesn't judge whether they're any good.

To add a skill, see [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

## Benchmarks

`benchmarks/` has three small synthetic repair tasks (decay kinetics, an assay summary, a held-out prediction) and a scorer with 24 hidden checks. You can prepare an isolated workspace with or without a skill, have an agent repair the code, then score the result. The tests confirm the harness works: planted bugs fail, reference fixes pass, and answers never reach the agent's workspace. **We haven't measured whether the skills help a real agent yet.** The tasks are also probably too easy to show a difference. The protocol is in [benchmarks/README.md](benchmarks/README.md); the larger benchmark we plan to build is under Planned below.

## Status

### Done

- [x] Seven skills in two packs (core, compute-env), including the router
- [x] Pack manifests, profiles, and an installer that generates the router per install
- [x] Skill linter, tests for the installer and benchmark harness, CI
- [x] `AGENTS.md` template for research projects
- [x] Synthetic benchmark tasks and scorer (harness validated, no agent trials yet)

### Planned

- [ ] **lean**: `lean-formalization` (does the Lean statement say what you mean?), `lean-proving` (proof loop, tactics, Mathlib search), `lean-trust-audit` (no `sorry`, axioms checked, statement unchanged, independent kernel re-check). Includes a `lean_audit.py` script and a hook that blocks "proved" claims until the audit passes.
- [ ] **numerics**: units and dimensions, order-of-magnitude estimates, floating-point pitfalls, convergence testing
- [ ] **data-stats**: statistics sanity checks, notebook hygiene, data provenance
- [ ] **testing**: property-based tests, golden-file regression tests, characterizing legacy code before changing it
- [ ] **compute-env** additions: dependency diagnosis, HPC and SLURM jobs
- [ ] Field packs with catalogs of common bugs: bio, astro, chem, climate
- [ ] Field profiles (biology, physics, math, ML for science) once those packs exist
- [ ] Optional Claude Code extras per pack: hooks for enforcement, a fresh-context reviewer subagent
- [ ] Benchmark v2:
  - real bug fixes from well-tested scientific repos, graded by the maintainers' own tests
  - new bugs planted in well-tested libraries
  - Lean proofs judged by the kernel rather than by the agent's claim
  - review tasks that include clean controls
  - a same-length "be careful" placebo prompt as a control condition
  - an interference test: do extra installed packs make results worse?
  - automated headless runs, with the hypotheses committed before the runs

### Still to do for the final presentation

- [ ] Run the benchmark trials and report every result, including failures
- [ ] Optional small pilot with classmates who don't use AI tools much
- [ ] Verify any citations and statistics we reuse in the slides against their original sources
- [ ] Slides and report
- [ ] Publish the packs as Claude Code plugins (on hold until the project is ready)
