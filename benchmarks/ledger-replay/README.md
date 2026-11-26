# Paired calibration study with Python access

Luna and Sonnet each solved every calibration case with Python alone and with Python plus the **Reconstruct a data vintage** skill. Both arms returned 18 fully correct submissions and 198 correct fields. Each submission had to identify eligible stations, reconstruct two releases, select a paired panel, and report counts and effect estimates. This small benchmark reached its ceiling in both arms.

| Client | Full passes, baseline | Full passes, with skill | Calls to Python, baseline / skill | Treatment runs calling the helper’s selector |
| --- | ---: | ---: | ---: | ---: |
| Codex CLI, GPT-6 Luna | 9/9 | 9/9 | 39 / 39 | 3/9 |
| Claude Code, Sonnet 5.5 | 9/9 | 9/9 | 45 / 43 | 0/9 |

For example, the estuary dataset included 12 operating stations at the roster date. After revisions and channel coverage were applied, eight remained in the paired panel. The pass rate fell from 399/530 to 364/491, a change of −1.149 percentage points. All 12 attempts on that case recovered the same panel and effect. The other cases required different revision policies or site weighting.

Across 18 matched pairs, all 18 tied on field accuracy and full correctness. Median elapsed CLI time was 21.77 seconds at baseline and 24.23 seconds with the skill. Concurrent execution and provider latency affect timing. Offering the supplied workflow and selector produced no measured gain in accuracy on these three cases. Each client could also implement the procedure directly in the local Python interpreter. Direct helper use was voluntary. The study tested the effect of providing the skill package, rather than isolating what its prose or its code contributes.

Both clients generated the answers using their subscribed CLI sessions. A local replay re-executed all 166 archived Python calls and reproduced every final answer byte for byte, along with all 396 field scores and the recorded selector calls. [Study design and local replay instructions](protocol.md) · [Frozen protocol](results/protocol.json) · [Trial records](results/trials.jsonl) · [Submitted Python](results/python-calls.jsonl)
