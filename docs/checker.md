# Inspect a research repository

Run `python3 scripts/check_repo.py . --format text` from the project root. To save a machine-readable report, use `python3 scripts/check_repo.py .`. The checker reads files locally and presents the evidence for each observation. You decide whether a change is appropriate for the scientific workflow.

| Finding | What triggers it | What to check |
| --- | --- | --- |
| Missing dependency lock | A recognized Python or Node manifest declares packages and there is no matching lockfile in that directory. | Find the environment used for the published run. A shared workspace lock, container, or fully pinned requirements file may already cover it. |
| Missing script | A literal Python script command in a README or Markdown under `docs/` points to a missing file. | Verify the intended working directory and how readers obtain the script. |
| Entropy-seeded RNG | A recognized Python or NumPy constructor or seed call omits the seed or passes literal `None`. | Determine whether that experiment needs exact replay. If it does, record and pass its seed. |
| Undocumented test command | There are Python test files but no recognized test invocation in the scanned documentation. | Write down the command used to run the suite and the directory in which to run it. |

The JSON output keeps `root`, `evidence`, and `limitations`. Each entry in `findings` has a rule, location, observation, suggested action, and limitation. Check `incomplete_coverage` for unreadable text, invalid syntax, or unparseable manifests. Findings are advisory and a successful scan exits with status zero.

The checker looks at PEP 621 and Poetry dependency declarations, ordinary named requirement lines in `requirements.txt`, and npm dependency declarations. Reading TOML requires Python 3.11+ or the optional `tomli` package on Python 3.10. It recognizes common pytest and unittest commands and direct Python test script invocations. Shell examples may use either the repository root or the document directory. Literal `cd` commands inside fenced examples change the assumed working directory. Import resolution recognizes common aliases and cannot establish runtime behavior. Symlinks, virtual environments, and benchmark run directories are excluded. Run the actual tests and reproduce the analysis to verify its results.
