# Reproduce the record audits

From the repository root, check the saved answers without calling a model:

```sh
python3 benchmarks/fieldstudy/verify.py benchmarks/fieldstudy/results/dev benchmarks/fieldstudy/results/dev-luna benchmarks/fieldstudy/results/heldout benchmarks/fieldstudy/results/heldout-luna
python3 benchmarks/fieldstudy/analyze.py benchmarks/fieldstudy/results/heldout
python3 benchmarks/fieldstudy/analyze.py benchmarks/fieldstudy/results/heldout-luna
```

Each trial records the requested model, raw final reply, field scores and full-pass result. The verifier regenerates each prompt and answer key, checks hashes and schedule membership, and grades the reply again. The analyzer pairs trials by model, family, case and repetition. Its accuracy is the mean fraction of requested fields correct per answer. A full pass also requires exactly the requested keys. Duplicate keys or unparseable output receive no correct fields. Scheduled timeouts or failed calls receive zero, with their status and pair count reported separately.

## Collect a new sample

Use a Codex CLI signed into ChatGPT and a Claude Code CLI signed into a first-party paid Claude account with extra usage off. The runner supplies a short environment allowlist so provider credentials and gateway overrides from the parent shell cannot select an API-billed service. It verifies the native login and quota controls. It starts fresh temporary directories and independent sessions, requests low effort, limits each response to 240 seconds, and schedules at most four processes at once. Each participant receives one user message and returns one answer. Claude tools are disabled. Codex has shell and app tools disabled, a read-only sandbox, and an event check for unexpected tool use. Keep the same models and tools across both arms.

Use fresh output paths. These commands consume subscription quota:

```sh
python3 benchmarks/fieldstudy/runner.py heldout --out /tmp/sciskills-primary-new
python3 benchmarks/fieldstudy/runner.py heldout --luna --out /tmp/sciskills-luna-new
```

Each run freezes the prompt, answer-key and scorer hashes and the balanced randomized schedule before launching the first participant. The primary cohort consists of Codex Terra and Claude Sonnet. Luna is a separate secondary cohort selected after its development results and before its held-out results. The six repeated cases limit generalization across new scientific settings. See the [predeclared outcomes](design.md).
