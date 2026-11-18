---
license: apache-2.0
language:
- en
library_name: transformers
pipeline_tag: text-generation
base_model: HuggingFaceTB/SmolLM2-135M-Instruct
tags:
- behavior-intervention
- uplift-modeling
- managerbench
- causal-inference
- small-language-model
---

# Manager v0 (135M) — research baseline for intervention uplift ranking

A small causal language model fine-tuned to rank **which intervention is most likely to change a person's behavior**.
This is a **research baseline, not a production model**. It **failed its preregistered promotion gate**
(see [Evaluation](#evaluation) below) and must not be presented as the flagship Manager.

- **Base model**: [HuggingFaceTB/SmolLM2-135M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct) (Apache-2.0)
- **License**: Apache-2.0
- **Training**: LoRA SFT (TRL SFTTrainer + PEFT), merged into the base weights
- **Size**: 135M parameters, bf16, 269 MB
- **Language**: English (training and evaluation data are English)

## What it does

Given a context describing a person and a candidate intervention, the model produces text used to score
uplift — the expected change in behavior from applying that intervention versus not applying it.
The intended research question is: *can a small model learn to rank interventions by their causal effect?*
The honest answer from our first run is: **not yet, at this size and recipe**.

## Quick start

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

tok = AutoTokenizer.from_pretrained("ANICCA/manager-v0")
model = AutoModelForCausalLM.from_pretrained("ANICCA/manager-v0")
```

Replace `ANICCA` with the real Hugging Face namespace once the account is created
(see `files/horizon-hf-adoption-2026-11-18.md`).

## Training

- Recipe: TRL SFTTrainer + PEFT LoRA (`r=16`, `alpha=32`, `all-linear`), 1 epoch, lr `1e-3`,
  cosine schedule, warmup 4 steps, batch 16, max length 256, bf16, completion-only loss, merged.
- Data: 29,885 serialized uplift examples (`sft_train_v0.jsonl`), derived from the Hillstrom
  email-marketing experiment dataset (public research data).
- Train loss: 0.1887, 63 steps, ~53 minutes on GPU.
- Full recipe and logs: `manager-v0-work/scripts/train_sft.py`, `manager-v0-work/out/manager-v0/train_log.json`.

## Evaluation

Protocol: **MG-06 prereg** (`files/mg06-prereg-2026-11-14.md`), frozen split, seed 0,
evaluation subsample `n=1000`, stratified by treatment × visit, declared before scoring.

| Arm | Qini | AUUC | Uplift @30% |
|---|---|---|---|
| **manager-v0 (this model)** | 0.0041 | 0.0027 | 0.0746 |
| Population prior | 0.0000 | 0.0000 | 0.0749 |
| T-learner (logistic regression) | **0.1017** | **0.0479** | 0.0671 |
| Random targeting | mean −0.0070, p95 0.0715 | — | — |

**Preregistered gate** — uplift ranking must beat random targeting (lower 95% CI > random p95):
lower CI = −0.0839, random p95 = 0.0715 → **FAIL**.

Read this plainly:

- v0 does not beat a trivial population prior on uplift@30%, and a simple T-learner
  logistic regression beats it clearly on Qini (0.1017 vs 0.0041).
- We publish the weights anyway, with the failed gate on the card, because the bottleneck
  (training data — real intervention → response cases are still 0) is a research fact, and
  a reproducible baseline that fails honestly is more useful than no baseline.
- Do not use this model to decide real interventions for real people. It is a benchmark
  artifact for ManagerBench, not a product.

Evaluation artifacts: `manager-v0-work/results/eval_manager-v0_fp32.json`.

## Intended use and limitations

- Research use only: uplift-modeling baselines, ManagerBench evaluation, failure analysis.
- English only. 256-token training context; not a general chat model.
- The training data is one marketing-experiment dataset; it does not cover the intervention
  types (affirmation, comedy, mindful questions, etc.) that the real Manager targets.
- Known weakness: uplift ranking is statistically indistinguishable from random at n=1000.

## Source

- Training and evaluation code: `manager-v0-work/` (scripts, data builders, eval harness).
- Benchmark: [ManagerBench](https://huggingface.co/datasets/ANICCA/managerbench) (frozen receipts).
- Related record: `files/horizon-hf-adoption-2026-11-18.md`.
