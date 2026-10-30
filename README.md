# SciSkills

Reusable AI-agent skills for reliable scientific software development.

## Why

AI makes it easier for researchers to write code, but working code is not necessarily correct, reproducible, secure, or maintainable. SciSkills provides task-specific instructions that researchers can give to coding agents, with practical examples and eventually benchmarks to test whether the instructions help.

## Who it's for

Graduate students, postdocs, faculty, and other researchers who use AI coding tools without extensive software-engineering training.

## Repository layout

```text
skills/                 Reusable agent instructions
  pin-the-environment/  First implemented skill
examples/               Small, runnable demonstrations
benchmarks/             Future controlled evaluations with planted issues
docs/                   Roadmap and contribution guidance
```

## Try the first skill

1. Open [`skills/pin-the-environment/SKILL.md`](skills/pin-the-environment/SKILL.md).
2. Ask your coding agent to follow that file while preparing a Python research project for reproducible execution.
3. Try the demonstration in [`examples/pin-the-environment/`](examples/pin-the-environment/README.md).
4. Review proposed changes before accepting them. The skill must not silently upgrade dependencies or claim bit-for-bit reproducibility.

Some agents support loading skills directly from a skills directory; others require you to paste or reference the instructions. Integration varies by tool.

## Planned skills

- **Pin the environment** — record and lock dependencies, document runtime, control randomness.
- **Known answers first** — test against simple cases with independently known results.
- **Check the numbers** — validate units, finite values, and scientific constraints.
- **Adversarial review** — challenge assumptions and inspect AI-generated code.
- **OOM testing** — test memory limits and failure behavior.
- **Paper-to-code consistency** — compare implementations with methodological specifications.

Only **Pin the environment** is implemented in this starter repository. The remaining skills are proposals, not completed features.

## Evaluation plan

Develop research tasks with planted mistakes and compare agent behavior **with vs. without** SciSkills. Record correctness, reproducibility, detected failures, runtime, and limitations. Avoid claiming effectiveness until the benchmark has been run.

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). Contributions should include an actionable skill, an example, and a way to check whether it worked.

## Status

Early project scaffold for the Caltech CS 143 special project. Not a security or correctness guarantee.
