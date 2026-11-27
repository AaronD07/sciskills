# Reviewing research work

A researcher might ask an agent to finish an unfamiliar numerical method, then use it on a new dataset. Another researcher might ask it to update a routine analysis where a wrong unit, denominator or assumption would change the conclusion. This experiment measures both uses separately.

The published 0.1 release gave its strongest evaluated agent, Claude Opus 5, a 30% resolution rate. That launch result motivates trying the suite. The score of today's Terra or Sonnet on our selection has to be measured with the actual clients and machine. [Benchmark authors’ announcement](https://www.terminal-bench-science.ai/announcement)

## Development and holdout design

Freeze the development and holdout manifests before model sessions. The primary models are GPT-6.1 Terra in Codex and Claude Sonnet 5.5 in Claude Code, both at high effort and using included subscription usage. GPT-6 Luna and Claude Opus 5.5 receive the same four preselected holdout tasks in each track. Each model produces its own draft. Grades and other models’ work are kept outside the participant environment.

* **Frontier science.** Run 12 original Terminal-Bench-Science 0.1 development tasks with their published instructions, data, dependencies, time budgets and verifiers. Advance to 16 frozen tasks only if each primary model makes consequential errors on at least five development questions and a mechanism recurs on two different questions for that model. Inspect task-level records and record a witness for each claimed error. Infrastructure and disputed labels cannot qualify a suite. If the fully measured screen misses the threshold, apply the same screen to SWE-bench Science on distinct scientific repositories. [Original release](https://github.com/harbor-framework/terminal-bench-science/tree/v0.1.0) · [SWE-bench Science](https://github.com/OpenMOSS/SWE-bench-Science)
* **Everyday work.** Use two development pairs and two new holdout pairs in each of four families. Change a condition requiring a different decision within each pair. Check the numeric value, supporting measurements, whether the result is determinable, the usefulness of any request for clarification and the actual effect of proposed writes on a simulated register. Both members are tested. A reviewer who always abstains should miss answerable controls.
* **Alignment measures.** Blocker cases measure whether a submitted result acknowledges an obstacle that prevents completion. Action-scope cases stage proposed writes and inspect their effects before executing anything outside the task. These are local research adaptations of two internal system-card evaluations. [OpenAI blocker evaluation](https://deploymentsafety.openai.com/gpt-6-2-astra-sol/blocker-deception) · [Improper actions evaluation](https://deploymentsafety.openai.com/gpt-6-2-astra-sol/improper-actions-in-workplace-tasks)

After development, choose changes to the skill only from documented recurring behavior. Freeze the general and specialist text before the first holdout. Randomize review scheduling, fork every submitted first draft, and give each reviewer the same task, work, tools and budget. Ordinary review gets no skill file. The other reviewers get the appropriate skill with its unrelated repository exercise removed.

The primary result for each model and use case is the change from its first draft to its skill-assisted deliverable. Compare those same pairs against ordinary review, reporting uniquely repaired and newly broken tasks, incomplete sessions, unsupported answers and unnecessary abstention. Small transfer samples are descriptive. When grading a program, record the upstream task result and expose component checks only if the verifier provides them.

## Reproducing the comparison

From the repository root, use Python 3.11 or newer. The everyday Python tool uses the macOS sandbox. Frontier environments and verifiers need Docker. Both the Codex CLI and Claude Code need an active subscription login. The runner checks authentication and included usage before dispatch. Prompts, transcripts, artifacts and grader receipts live under the ignored `benchmark-runs/research-review` directory.

```sh
python3 -m benchmarks.research_review.study freeze everyday
python3 -m benchmarks.research_review.study dev everyday --workers 2
python3 -m benchmarks.research_review.study seal everyday --skill-map benchmarks/research_review/everyday-skills.json
python3 -m benchmarks.research_review.study holdout everyday --workers 2
python3 -m benchmarks.research_review.study reviews everyday --workers 2
```

For frontier work, follow the [container setup](frontier.md), freeze the `frontier` design and run `dev frontier` once the environment controls pass. Supply `--tasks` to dispatch verified tasks individually. The gate expects `frontier/development-audit.json` under the run directory. For each primary model and task ID, record the broad error class, a specific recurring mechanism in `pattern`, and the scientific consequence and evidence in `evidence`. Use null for unsupported mechanisms. A grader failure alone is insufficient to identify a mechanism. Then use `seal`, `holdout` and `reviews` for that track with the chosen skill map. Re-running a phase resumes from saved submissions. Grading can be retried on a saved Docker snapshot without asking the model to redo the task.

The fallback uses the same study commands with `swe` and has its own manifest. Its upstream publisher withholds gold patches. Its infrastructure control establishes that the official scorer rejects a clean checkout. Results carry this weaker validation.

Export the anonymized outcomes and regenerate the comparisons with `python3 -m benchmarks.research_review.report export --archive /tmp/sciskills-archive.json --report /tmp/sciskills-results.md`. For an offline replay of the summary, use the same command with `render` in place of `export`. A model may have encountered a published task during training. The holdout split protects against updating the skills on evaluated cases.

## Grader and runner decisions

Everyday development produced 16 correct first drafts for each primary model, including all eight cases with a missing decision or certificate across the two models. All eight disclosures named the missing source or decision. We froze existing skills for the everyday holdout. Case families determine specialist routing before the first draft is seen. For numeric outputs, we accept correctly rounded values at three or more significant figures and percent or basis-point values rounded to two decimal places. Integer references and intermediate evidence use the tighter reference comparison. The original implementation mistakenly rejected valid rounding, including a four-decimal pressure value on a holdout. The precision correction applies equally to every model and arm.

The first three frontier Codex drafts used a client whose host sandbox was advertised as read-only even though the task container was writable. One model explicitly cited this conflict. We set the disposable client workspace to writable and replaced all three frontier Codex trials started under the conflicting instruction regardless of their score. The containers remain offline and the built-in host shell is disabled.

During development, two completed Codex sessions emitted the normal feature warning as an error-typed event. The evaluator initially discarded the containers. For symbolic regression, the last successful tool call contained the entire required program as a literal. We restored it in the original image, verified the bytes and obtained a full pass from the upstream grader. For traffic-flux inversion we recovered the original program by replaying its literal writes and deterministic edits. We discarded an automatically started retry and graded the original program. The client now distinguishes that informational message from an actual failed turn. We also regraded the original Sonnet lake-ice snapshot after a file-transfer issue in an early verifier worker. Its corrected result was 39 of 40 pytest cases. Neither recovery required another model answer.

For frontier development, we excluded model sessions whose Linux cgroup showed a process killed under host-wide memory pressure while its own memory limit had never been reached. This decision applies before examining any resulting grade. We retained the original receipts and required fresh participant controls on a larger local VM for those reruns. A process exceeding its published per-task limit is recorded separately from a host-wide kill.
