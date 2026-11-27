# Running the frontier science tasks

The manifest selects 12 development tasks and 16 holdouts from Terminal-Bench-Science v0.1.0. Each task belongs to one split. Four holdouts are marked for the smaller transfer sample. The task IDs, upstream Git trees and registry digests were recorded before model evaluation. The original tasks cover different scientific workflows, including estimating a lake's ice season, reconstructing a traffic-flow law, calibrating a watershed model and interpreting orbital measurements. [Upstream release](https://github.com/harbor-framework/terminal-bench-science/tree/v0.1.0)

From the repository root, run these commands with Python 3.11 or newer, Git and Docker.

```sh
python3 -m benchmarks.research_review.frontier list --phase dev
python3 -m benchmarks.research_review.frontier status --phase all
python3 -m benchmarks.research_review.frontier preflight --phase dev --task mendota-ice-phenology
python3 -m benchmarks.research_review.frontier preflight --phase dev
```

Cloning and building images need network access. The participant, reference and grading containers run offline. Set `SCISKILLS_TBS_SOURCE` to change the checkout path or `SCISKILLS_TBS_STATE` to change the control receipt directory. The checkout must match the manifest's commit, and selected task directories must be clean. Both Dockerfiles and all inputs come from those directories. Image builds may take several minutes. Some reference solutions and verifiers are CPU intensive.

The preflight submits the untouched environment to the upstream verifier, then runs the published solution in a separate participant container and grades its artifacts. A task becomes eligible only when the untouched environment fails and the published solution receives the full upstream reward of 1. Building images or obtaining a partial reference score cannot qualify a case. Each receipt records the exact participant and verifier image IDs; the runner reuses those images. The status command prints shareable counts and image IDs, including the grouped CTRF count and the complete pytest result when available. A saved snapshot is in `frontier_controls.json`. Receipts live under `benchmark-runs/research-review/frontier-controls/` by default and contain private verifier diagnostics. The TESS and masked remapping verifiers use native system-call filters or a filesystem jail, so those two tasks use native ARM64 images on ARM64 Docker engines. The remaining tasks use the upstream Dockerfiles built for Linux AMD64.

Participants see the original instructions and the files in the original environment. Reviewers start from separate copies of the same committed first-draft image. After a session ends the adapter transfers only the artifact paths declared in the original task configuration into a clean verifier. It executes the upstream test script there and retains the scalar reward and component counts. None of the hidden tests, oracle files or prior grades are passed to reviewers. A missing required submission is recorded separately from a verifier that could not return a reward. A timed-out verifier or a failed reference control cannot establish a model mistake.

These runs use the published scientific tasks and verifiers with a different agent harness, network policy and machine. In particular, tasks whose original evaluator measures runtime can be sensitive to architecture and concurrent load. Treat the measurements as results for the selected cases and runner. The suite's version and file digests make it possible to repeat the same selection elsewhere.
