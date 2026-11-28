# Pin the environment: small example

This intentionally dependency-free example demonstrates recording a Python runtime and controlling randomness. It is **not** a substitute for a dependency lockfile in a real scientific project.

## Run

```bash
python3 --version
python3 experiment.py --seed 42
python3 -m unittest discover -s . -p 'test_*.py'
```

Record the exact Python version from the first command. Running the experiment twice with the same seed and environment produces the same result in this example. Different seeds typically produce different samples.

## Ask an agent

> Follow the `pin-the-environment` skill for this example. Identify what is already reproducible, what metadata is missing, and what would change if we introduced NumPy. Do not invent a lockfile or modify dependencies without asking.

## Expected limitation

There are no external dependencies here, so no lockfile is generated. For a real project, add and resolve dependencies with a package manager, commit its generated lockfile, and verify from a clean environment.
