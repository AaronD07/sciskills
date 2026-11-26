# Why these skills are here

ScienceAgentBench researchers examined 50 failed Claude 3.5 Sonnet runs from each of two agent setups. Code ran but answered the task incorrectly in 29 of the 50 OpenHands runs and 30 of the 50 Self-Debug runs. Some agents generated artificial data when loading the real data failed. Others quietly replaced the requested model with one they could implement. Environment setup accounted for 10 and 9 failures respectively. These counts describe failed runs in that study. Estimating frequencies for current agents requires a new sample with the model, tasks and denominator recorded. [ScienceAgentBench, Appendix E.2](https://arxiv.org/html/2410.05080v3#A5.SS2)

## Where the workflow can break

| What goes wrong | What to ask before or after coding | Evidence and skill |
| --- | --- | --- |
| An agent chooses one interpretation of an ambiguous request and carries it through to a plausible result. | Before coding, have it identify the data, population and method. If two interpretations would change the result, resolve that specific choice. Afterward, trace the output back to those inputs. | [ClarifyGPT](https://doi.org/10.1145/3660810) studied targeted questions for ambiguous code requirements. [Preserve the research question](../skills/preserve-the-research-question/SKILL.md) applies this idea to analysis. |
| Repeated measurements give one participant excess weight and make the apparent sample size too large. | Ask what was independently sampled. Request counts of both rows and independent units, then inspect pairing and missing subjects. | The [K-Dense statistical analysis skill](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/statistical-analysis/SKILL.md) uses the study design to select a method. [Identify the independent unit](../skills/identify-the-independent-unit/SKILL.md) focuses on repeated observations. |
| A comparison looks favorable because it omits failed trials or gives one condition easier inputs. | Agree on the metric, budget and treatment of failures. Inspect each planned pair, including unfinished attempts, before writing the comparison. | [Karpathy's experiment instructions](https://github.com/karpathy/autoresearch/blob/master/program.md) establish a baseline and log each experiment. [Anthropic's skill creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) compares skill and baseline runs on the same prompt. [Compare experiments fairly](../skills/compare-experiments-fairly/SKILL.md) covers both steps. |
| A finished report confidently states a number that the cited source cannot support. | Read the original table, match its population and period, and recompute the figure using the stated denominator. Revise the sentence to match the result. | [Trace claims to evidence](../skills/trace-claims-to-evidence/SKILL.md) combines source location with calculation checks. [FinQA](https://aclanthology.org/2021.emnlp-main.300/) provides examples of the arithmetic required to answer questions about financial reports. |

The last three rows describe methodological risks and practical checks. The source workflows motivated the skill design. To measure whether the instructions help an agent, compare its work on the same tasks under the same conditions and keep a record of its actual mistakes.

## What financial research agents can teach us

Anthropic's earnings reviewer asks for the filing date, a link to the filing and the source and date of any consensus estimate. A report can be arithmetically correct yet answer the wrong question if it cites the wrong quarter or uses information released after the requested cutoff. Those checks carry over to scientific reports using revised datasets. [Earnings reviewer workflow](https://github.com/anthropics/financial-services/blob/main/plugins/agent-plugins/earnings-reviewer/skills/earnings-analysis/SKILL.md)

Dexter records the inputs and raw tool return for each retrieval alongside an agent summary. That design makes it possible to inspect the specific point where a research note diverged from the source. To audit a claim, follow it back through the summary to the returned record and check the requested reporting period. [Dexter's research log](https://github.com/virattt/dexter#-how-to-debug)

FinanceBench paired questions with evidence from filings and had researchers inspect 2,400 answers from 16 configurations on a 150-question sample. The authors found unsupported answers even when models could use source documents. FinQA supplies expert calculations that connect an answer to the operations used to derive it. Together these studies suggest locating the right record and recalculating the claim as separate checks for a research note. [FinanceBench study](https://arxiv.org/abs/2311.11944) · [FinQA study](https://aclanthology.org/2021.emnlp-main.300/)

The Finance Agent Benchmark pairs analyst-authored questions with tools for finding and interpreting SEC filings. In its 537-question collection, retrieval and calculation can both affect the final answer. This motivated recording the source, reporting period and calculation for a claim so a reviewer can check each step independently. [Finance Agent Benchmark](https://arxiv.org/abs/2508.00828)

For example, suppose a draft says a margin “grew 5%” while its source gives 20% last year and 25% this year. The change is 5 percentage points, or 25% relative growth. The author can choose which measure answers the question and show the arithmetic. The same check works for an accuracy improvement in a research paper.

## Using the skills in a prompt

For a repeated-measures study, “compare the two groups” leaves the agent to decide how much weight each visit carries. A more useful request is “Estimate the average participant's change from their first visit to follow-up. Identify participants who lack either visit and report how many complete pairs remain.” The report then gives the scientist something specific to verify.

After drafting results, ask “For each number in the conclusion, identify the source row or run and reproduce the calculation. Revise any claim the source cannot support.” Keep the source notes alongside the draft so another reader can repeat those checks.
