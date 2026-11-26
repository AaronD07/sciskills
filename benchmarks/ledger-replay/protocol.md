# Reconstructing two scientific releases with a local Python tool

The earlier record audit found that Luna frequently chose the wrong records and denominators when working directly from prose. This follow-up asks what happens when both participants can inspect CSV files and execute Python. It introduces three new calibration datasets, each with a different revision rule, release cutoff or estimand. The records, answer keys and methods amendments are synthetic. They were written for this study.

## Matched conditions

Each of Codex Luna and Claude Code Sonnet attempts each of the three cases three times in each condition, for 36 independent sessions. The baseline receives the task, station roster, schedule and certificate records. The treatment adds the workflow for reconstructing a data vintage and its generic Python helper. Both clients may write their own selection code. The treatment also permits importing the helper or running it in-process. During preflight the helper gained support for integer availability clocks as well as ISO dates, and the instructions gained an importable example. Those changes preceded the measured runs.

The same wrapper asks both clients to use the local tool and write their result to answer.json. The field-study runner authenticates both subscription accounts and checks included usage before launch. Both models use low effort, a 240-second time budget and fresh temporary directories. Four sessions can run concurrently. Python processes have a 12-second wall limit per call. They can read the staged files, calculate, and write files in their own work directory. The macOS sandbox blocks outbound connections, access to user home files and writes outside the work directory. An unrelated CSV sum tested both clients' ability to invoke the calculator and write the requested file before data collection.

All scheduled sessions count once. Report full JSON passes, individual fields correct, and total tool invocations by condition and client. Per-call logs also record entry to functions in the supplied helper based on the executing filename. Reading a helper or reproducing its algorithm independently will leave a different trace from calling its select function. Interpreting scores alongside that trace helps separate access to a skill from use of its implementation. Differences from the earlier text-only experiment can also reflect the changed tasks and model behavior; its scores do not serve as a randomized no-Python control.

## Running and checking

The published protocol lists the randomized job order, client versions, model names, artifact hashes, and authentication checks. The evidence retains the agent-written Python, calculator exit status, helper function names, output answer, and field-level grades. Provider transcripts are kept outside the repository.

On macOS, from the repository root:

```sh
python3 benchmarks/ledger-replay/audit.py benchmarks/ledger-replay/results --replay
```

This re-executes the archived model-written Python in isolated workspaces and checks each final answer. Omitting the replay flag checks the saved answers and source hashes offline without executing participant code. For a fresh study, install both native CLIs with subscription authentication and choose empty result and private log paths.

```sh
python3 benchmarks/ledger-replay/study.py smoke --out /tmp/ledger-smoke-results --private /tmp/ledger-smoke-logs
python3 benchmarks/ledger-replay/study.py run --out /tmp/ledger-new-results --private /tmp/ledger-new-logs
python3 benchmarks/ledger-replay/audit.py /tmp/ledger-new-results --archive-private /tmp/ledger-new-logs --replay
```
