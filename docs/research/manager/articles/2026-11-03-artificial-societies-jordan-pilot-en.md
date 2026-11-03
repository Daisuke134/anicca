# We Reproduced an Artificial Societies Survey Task with Real Human Reference Data—and Our Local Model Failed in an Instructive Way

**Anicca / Manager Research | November 3, 2026**

An LLM can sound exactly like a person and still fail to reproduce how people respond to a change in wording. We wanted to understand this distinction hands-on, using actual human reference observations—not only a model card, a simulated population, or a published leaderboard.

## First: what is being tested?

The [Artificial Societies Benchmark](https://github.com/artificial-societies/artificial-societies-benchmark) tests multiple dimensions of the validity of synthetic respondents. Accuracy on marginal answer frequencies, consistency across questions, relationships among traits and response shifts under an experimental manipulation are **not interchangeable**.

For a concrete pilot, we chose an openly released experiment on the effects of wording in questions about social spending. In one treatment, the question uses one label; in the other, a different description of the same policy area. We evaluate each answer on an ordinal 0, 0.5, 1 scale and compute the shift in mean scores.

The human-response data come from the [Jordan and collaborators' Harvard Dataverse replication archive](https://doi.org/10.7910/DVN/SH0F25). As a scientific contrast about a survey instrument, this is **not** an attempt to persuade or target real people about politics. No one receives messages or interventions from our experiment.

## What we actually ran

1. We pinned the public benchmark source and ran the included Python/R test environment. The recorded full suite yielded **68 passed, 7 skipped**; skips involved missing original human source files or unprepared evaluation candidates.
2. We independently reconstructed the public 7,128-cell scorecard using the source's output aggregation path. This is *rebuilding published outputs*, not rerunning every private model.
3. We retrieved the original, publicly licensed survey archive and ran the official `benchmark_data.external.build_wording` preprocessing without changing that function. It yielded **1,488 human profiles and 1,488 observations**.
4. We selected **24 benchmark-split participants per condition**, fixed the random seed, and invoked the actual local `qwen2.5:1.5b` model through Ollama. We used the benchmark's official `extension_protocol.build` for the respondent prompt and `extension_protocol.parse` for answer validation.
5. All **48 model responses were syntactically valid**. We compared the ordinal response means and the *between-wording effect*, using the benchmark's published metric function.

## The small experiment's result

| Quantity, on a 0–1 scale | Human respondents | Our local Qwen 1.5B |
| --- | ---: | ---: |
| Condition A mean | 0.6458 | 1.0000 |
| Condition B mean | 0.7917 | 1.0000 |
| **B minus A** | **+0.1458** | **0.0000** |

The local model returned **the same top option for all 48 prompts**. Its predicted effect of the wording change was zero, while the matched human respondents exhibited a mean shift of roughly 0.146. The absolute effect error was 0.146 on this small subset.

This is a negative result for the local configuration. It demonstrates how a model can pass a format test while failing the actual scientific objective. A model optimized to be a helpful conversational assistant is not automatically a well-calibrated simulator of the diversity of human responses.

## Five limits before anyone quotes this as a leaderboard result

**Sample:** This is 48 selected observations, not the original benchmark's full task or a representative model-ranking experiment.

**Model:** We evaluated a small local Qwen model under a specific inference configuration—not the proprietary Rothko model. The [Rothko release](https://societies.ai/rothko) describes a proprietary behavioral model; its source code and weights were not part of this run.

**Human reference:** This is one licensed source study, not a sample from every country, topic or behavioral domain. We do not publish respondent-level personal data in this article.

**Evaluation:** We changed the sample size and did not replicate the original multi-model provider stack. Our result is a separate research pilot and should not be placed on the official benchmark leaderboard.

**Causality:** A change in response to randomized wording is an example of a measurable experimental contrast. It does not establish a model's ability to predict every subsequent real-world behavioral intervention.

## What we learned

We should evaluate **(i)** completion and invalid-output rates, **(ii)** individual response accuracy, **(iii)** population distribution fidelity, **(iv)** correlations and diversity, and **(v)** experimental contrasts separately. A fluent answer or a high overall accuracy score cannot substitute for those tests.

The next important experiment for our behavioral-model research is to compare strong simple baselines with models trained on appropriately licensed human response data, using held-out people and held-out studies, and then to verify whether their predictions support better decisions in real settings. That last step remains to be demonstrated.

## Sources and reproducibility

- [Artificial Societies Benchmark: official open code](https://github.com/artificial-societies/artificial-societies-benchmark)
- [Jordan et al. human-reference replication archive](https://doi.org/10.7910/DVN/SH0F25)
- [Rothko introduction and stated methodology](https://societies.ai/rothko)
- [Artificial Societies' own comparison announcement](https://societies.ai/as-benchmark) — provider-reported results, not independently reproduced in this pilot

**Takeaway:** Running the model revealed a failure that reading a promotional benchmark alone would not have shown.
