# Follow-up evaluation design

The first pilot left a gap between running the code on an example and answering the question on fresh data. This study tests a different use of SciSkills: auditing a scientific result from several records with conflicting versions, repeated attempts or different denominators. These are original, synthetic cases. They test reasoning about records and protocols rather than the ability to edit a real repository.

## Discovery and confirmation

Use two task families. One asks the reviewer to reconcile an experiment schedule with its attempt logs. The other asks for a scientific claim as it could have been supported at a particular date. Each has one development case and three additional cases. The development baselines are the only model answers used to revise the treatment. All six additional cases stay in the comparison, even when the baseline is perfect or the skill hurts. Freeze task text, the answer keys, the two skill documents, scoring rules and launch order before the first held-out session. Keep the previous pilot and its skill versions reproducible.

Use the first available requested Codex model from Terra, Luna and Sol, in that order, and Claude Code Sonnet. Give both conditions the same tools and time limit within each client. Across six cases, run three fresh paired repetitions per client. Count each attempt once. Keep infrastructure errors separate and disclose any incomplete pairs. Keep model identity, prompt hashes, returned answers and field-level outcomes with the results.

## Outcomes chosen before trials

The primary outcome is the fraction of requested answer fields correct, averaged equally across cases, repetitions and clients. Report the within-pair difference in percentage points. Also report fully correct submissions, better/tied/worse pairs and differences by family and client. For this small pilot, a gain of at least 10 percentage points in primary accuracy with no decline in the number of fully correct submissions will count as practically meaningful. This threshold describes this experiment. It is not a population effect or a significance test. Three repetitions reuse the same case, so report how widely any improvement is distributed across the six cases.

As a separate diagnostic, replay archived DS-1000 problem 352 answers on new input values. Keep those outcomes separate from both the original upstream score and the new paired study. The replay tests an error already suspected from inspecting the old submissions.

## Development decision, before held-out generation

Terra and Sonnet each solved both development packets. We retained both clients in the primary comparison. We separately tried Luna on development cases and saw two errors: it used the wrong relative change despite having the correct before and after counts, and miscounted eligible attempts in a paired method comparison. We revised the two workflows to use an explicit worksheet and a second calculation from independent quantities. We added Luna as a secondary cohort with 36 held-out runs. Its selection was informed by the development errors. Its results are reported separately.

The separate code-transfer experiment uses a third skill and two previously unused public exercises. These were selected for variable inputs and multiple upstream tests. Its pass counts are reported separately from record-audit field accuracy.
