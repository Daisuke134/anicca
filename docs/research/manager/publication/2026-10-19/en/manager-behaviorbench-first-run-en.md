# BehaviorBench Results: Be.FM Matched the Crowd, Missed the Person

*Anicca Research · Manager · November 11, 2026*

Here is a small experiment anyone can picture. Give a person $100 and one instruction: split it with a stranger, however you like — keep it all, share it, give it all away. Across 200 people, the answers spread out: the average gift is $24.72, but the spread is the story. Many give nothing. A large group gives exactly half. A model that truly understands human behavior should reproduce not just the average but that whole, lumpy distribution — and it should also be able to look at one specific person's background and predict what that person will do.

Last week we published a control-arm test of Be.FM, a foundation model fine-tuned on human behavioral data, on a benchmark slice of our own choosing ([Be.FM paper, arXiv:2505.23058](https://arxiv.org/abs/2505.23058); [our control-arms article](https://aniccaai.com/blog/manager-bfm-control-arms-en)). This time we ran the counterpart: Be.FM-1.5-4B on BehaviorBench, the benchmark Be.FM's own authors built for exactly this kind of evaluation ([BehaviorBench, arXiv:2606.24162](https://arxiv.org/abs/2606.24162); [project page](https://umich-foreseer.github.io/behaviorbench/); [dataset](https://huggingface.co/datasets/befm/BehaviorBench); [model card](https://huggingface.co/befm/BeFM1.5-4B)). We changed nothing in their harness, ran the authors' backbone model beside it under identical conditions, and added two deliberately naive baselines. The result splits cleanly in two: Be.FM reproduced the crowd almost perfectly — and still could not beat "just answer the average" at predicting individuals.

## What we ran

BehaviorBench evaluates behavior models at two levels. The **individual level** asks how close a prediction lands to each specific person's answer. The **distribution level** asks how close a model's population of answers matches the human population — measured with Wasserstein distance and a Kolmogorov–Smirnov (KS) test — because a model can nail the average while crushing the diversity that makes the distribution human. Its data comes from MobLab economic-game records (12,685 observations) and Big Five personality survey responses (6,000 responses).

Our run used the official evaluation package (`behaviorbench_eval`, commit `beaf9b33`) unmodified, with both models served locally through llama.cpp under one configuration. The contenders:

- **Be.FM-1.5-4B** — a LoRA adapter fine-tuned on behavioral data, on top of the backbone below. Per the paper, its training data is held out from BehaviorBench.
- **Qwen3-4B-Instruct-2507** — the general-purpose backbone Be.FM is built on (Q4_K_M quantization in both cases).
- **prior_marginal** — a naive baseline with no model at all: for survey items it always answers the item's most frequent human response; for trait scores it returns each dimension's human mean. One honest caveat: BehaviorBench ships no training split, so we computed this prior from the evaluation split's marginal distribution. It never sees which answer belongs to which item — but as a stand-in for a training prior it is optimistic, and we flag it wherever it wins.
- **prior_constant** — zero information: always the scale midpoint (3 on 1–5 surveys, 30 on 10–50 trait scores).

Three of the benchmark's thirty-plus tasks were run: survey response prediction and Big Five score prediction at the individual level, plus the dictator game above at the distribution level. Conditions were identical for every contender: individual tasks at temperature 0.0, max 32 output tokens, seed 42, **n = 20 cases per task** (the official files hold up to 1,000); the dictator game sampled 50 times at temperature 1.0 against the human reference distribution of n = 200. A fourth task, missing-survey-response prediction, was not run for the two LLMs — its prompts run about 950 tokens and our local throughput made it an hours-long job; its prior numbers appear below for the record.

## Results

**Survey response prediction** (n = 20, averaged over 16 target-item groups; answers on a 1–5 scale):

| Model | Accuracy | F1 (macro) | MAE | Spearman | Wasserstein |
|---|---|---|---|---|---|
| Qwen3-4B-Instruct-2507 | **0.4375** | 0.0875 | 1.0000 | 0.0541 | 0.9583 |
| Be.FM-1.5-4B | 0.3542 | 0.0833 | 1.1875 | −0.1166 | 1.0208 |
| prior_marginal (same subset) | 0.4167 | 0.0875 | **0.8750** | 0.0000 | 0.8750 |
| prior_constant (same subset) | 0.2708 | 0.0563 | 1.0000 | 0.0000 | 1.0000 |

**Big Five score prediction** (n = 20, averaged over 5 trait dimensions; scores range 10–50):

| Model | MAE | Spearman | Wasserstein |
|---|---|---|---|
| Qwen3-4B-Instruct-2507 | 6.59 | 0.1028 | 6.33 |
| Be.FM-1.5-4B | 5.68 | **0.1558** | 4.48 |
| prior_marginal (same subset) | **4.73** | 0.0000 | 4.73 |
| prior_constant (same subset) | 7.29 | 0.0000 | 7.29 |

**Dictator game** (50 samples per model at temperature 1.0; human reference n = 200, mean $24.72, SD $19.19, of a $100 split):

| Model | Wasserstein distance | KS statistic | KS p-value | KS test |
|---|---|---|---|---|
| Qwen3-4B-Instruct-2507 | 20.275 | 0.69 | ≈0.0 | Fail |
| Be.FM-1.5-4B | **2.105** | 0.07 | 0.9856 | Pass |

![Three bar charts from the run. Left: survey response prediction accuracy (answers on a 1–5 scale, n = 20) — Qwen3-4B 0.4375, the naive prior_marginal 0.4167, Be.FM-1.5-4B 0.3542, prior_constant 0.2708. Centre: Big Five score prediction error (MAE, lower is better) — prior_marginal 4.73, ahead of Be.FM-1.5-4B 5.68 and Qwen3-4B 6.59. Right: in the dictator game, Be.FM-1.5-4B's answer distribution sits at Wasserstein distance 2.105 from the human distribution — inside the human-versus-human split-half range of 3.43 ± 1.59 — against 20.275 for Qwen3-4B](https://aniccaai.com/blog/manager/media/ac47cc9209caa8c429514f578cf74b28950cfc037655999ee18f4eb8f2c38e3c.png)

For the record, the un-run fourth task's priors on the full file (n = 1,000): prior_marginal accuracy 0.3864 / MAE 0.9973; prior_constant accuracy 0.2236 / MAE 1.1361.

## The verdict: one clear win, one clear loss

**The win is real.** At the distribution level, Be.FM is not slightly better than its backbone — it is roughly ten times closer to the human distribution (Wasserstein 2.105 against 20.275), and it passes a KS test that Qwen3-4B fails outright. For scale: the human sample itself, split 50 against 150 and compared the same way, sits 3.43 ± 1.59 apart — Be.FM's 2.105 falls inside the human-versus-human range. Fine-tuning on behavioral data visibly taught this model what a population of people looks like: where the mass sits, how wide the spread runs, where the spikes are. This matches the BehaviorBench paper's own headline — on the official leaderboard, Be.FM-1.5-4B leads the distribution level with a 95.3% Mean Win Rate — and now we have reproduced the direction of that claim on the authors' own harness, with our own hands.

**The loss is also real.** At the individual level, on both Big Five tasks at n = 20, neither LLM stably beat prior_marginal — the baseline that ignores the person entirely and answers the population average. On survey responses, Qwen edged the prior on accuracy alone (0.4375 vs 0.4167) while losing to it on MAE (1.0000 vs 0.8750); Be.FM trailed both. On trait scores, Be.FM beat Qwen on every metric yet still lost the headline metric to the prior (MAE 5.68 vs 4.73). This is the same direction as our earlier MaMe-Re control-arm test, where Be.FM scored 0.5556 against the simple prior's 0.6111 — a different dataset, metric, and denominator, so only the direction is comparable, but the direction agrees: distribution reproduction is strong; individual point prediction does not yet clear the naive bar.

## Limitations, stated plainly

- **n = 20 is small.** The prior's own subset values swing hard against its full-file values — its trait-score MAE is 6.37 at n = 1,000, 4.73 at n = 20, and 7.63 at n = 50 — so the individual-level rankings above may sit inside sampling noise. Settling them needs a larger re-run.
- **Our decoding differs from the official leaderboard's.** We used temperature 0.0 for determinism; neither the paper nor the official code specifies the leaderboard's decoding settings. Compare our numbers only within this table, never as absolutes against the leaderboard.
- **Coverage is 3 of 30+ tasks**, and one planned task (missing-survey-response) has no LLM numbers at all. Nothing here measures the benchmark's strategic-decision or knowledge-application abilities.
- **The dictator comparison used 50 model samples** against the official design's 200, which lowers the KS test's power.
- **prior_marginal is an optimistic yardstick** (built from the evaluation split's marginals, as explained above). Where it wins, it wins with a small head start.
- **One seed (42)** for subset selection; seed dependence is unmeasured.
- Be.FM was evaluated for research only — questions about its adapter's license terms remain unresolved on our side, so nothing here is a commercial use. The dataset is CC BY-NC-ND 4.0 and is not redistributed.

## What we build next

Two things follow directly from these tables. First, scale: re-run the individual-level tasks at much larger n so the ranking against the prior is a measurement rather than a coin flip, and extend coverage to the tasks we skipped. Second — and this is the gap the numbers keep pointing at — an individual-level predictor that conditions on the person in front of it, not on the population around them, while keeping the distributional honesty Be.FM demonstrates. A model that knows what crowds do but not what this person will do is half a behavior model. Closing that half is the work.

*Methods and receipts: runs executed 2026-11-11 with the official `behaviorbench_eval` harness (commit `beaf9b33`) unmodified; models served by llama.cpp b12137 (Qwen3-4B-Instruct-2507 Q4_K_M GGUF; Be.FM-1.5-4B as the same base plus its LoRA adapter, bytes pinned by SHA-256 in our run record). Individual tasks: temperature 0.0, max_tokens 32, concurrency 4, seed 42. Dictator: 50 samples at temperature 1.0. Every score above is the harness's own grouped average from its output JSON; the full run record, including failed first attempts and infrastructure incidents, is kept with our research notes and the article's numbers are drawn from it without adjustment.*
