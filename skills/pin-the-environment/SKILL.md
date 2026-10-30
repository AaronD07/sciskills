---
name: pin-the-environment
description: Make a scientific Python project more reproducible by recording its interpreter, locking dependencies, documenting setup, and controlling stochastic seeds where appropriate.
---

# Pin the environment

## Purpose

Make a research project's computational environment reconstructable. A dependency list alone is not enough: record the Python version, exact resolved dependency versions, platform assumptions, and randomness configuration.

## When to use

Use when starting a Python research project, preparing to share or publish results, onboarding collaborators, or debugging differences between machines.

## Agent workflow

1. **Inspect before changing.** Identify the Python version, operating system, dependency manager, existing manifests/lockfiles, notebooks, and random-number generators. Ask which dependency manager to use if unclear. Do not overwrite existing environment files without approval.
2. **Record the interpreter.** Specify a supported Python version in project metadata and document the exact interpreter used to generate results. Explain that a version range is not an exact runtime pin.
3. **Resolve and lock dependencies.** Prefer the project's existing dependency manager and its native lockfile (for example, `uv.lock`, `poetry.lock`, or `conda-lock.yml`). Commit the lockfile. If using pip, capture a fully resolved environment (`python -m pip freeze > requirements-lock.txt`) and explain that a freeze is platform-specific and may not reproduce builds on other platforms. Do not present a handwritten top-level requirements list as a complete lockfile.
4. **Use isolation.** Document how to create a clean virtual environment and install from the locked dependencies. Never install packages into an unrelated global environment without approval.
5. **Handle randomness.** Identify all relevant RNGs (e.g., Python `random`, NumPy, ML frameworks). Set explicit seeds in the application entry point or configuration, and record them. Do not reset seeds inside library functions unless that behavior is intentional. Explain that seeds alone do not guarantee deterministic results across devices, threads, or library versions.
6. **Check reconstruction.** In a fresh environment, install the locked dependencies, run the tests or a smoke test, and record the commands and outcomes. If installation or verification cannot be run, mark it **not verified**; never imply success.
7. **Report changes.** Summarize created/modified files, exact commands, recorded versions, test results, and remaining reproducibility risks. Ask before performing disruptive upgrades or changing research results.

## Guardrails

- Never invent dependency versions or generate a fake lockfile.
- Never silently upgrade or remove dependencies.
- Do not commit secrets, local environment variables, proprietary data, or large raw datasets.
- Keep the source of truth for dependency versions unambiguous.
- Distinguish *repeatable randomness on one machine* from *cross-platform numerical reproducibility*.
- If no dependencies are installed or network access is unavailable, document what is missing and how to finish the lock step.

## Completion checklist

- [ ] Interpreter and platform documented
- [ ] Dependency manifest and generated lockfile committed (or gap disclosed)
- [ ] Clean installation instructions written
- [ ] Seeds identified and controlled where relevant
- [ ] Smoke test run in a fresh environment (or explicitly unverified)
- [ ] Remaining nondeterminism and platform assumptions documented

## Example

See `examples/pin-the-environment/` for a small NumPy-free demonstration using Python's standard library. It shows an explicit seed and a reproducibility check, but does **not** demonstrate third-party dependency locking. Apply the workflow above to a real project with dependencies.
