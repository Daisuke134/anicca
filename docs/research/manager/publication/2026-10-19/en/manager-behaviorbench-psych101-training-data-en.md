# What Does a Foundation Model of Human Behavior Actually Learn?

*Anicca Research / November 8, 2026 / Deep Dive: BehaviorBench and Psych-101*

"Build a foundation model that predicts human behavior" sounds ambitious. It also leaves the most important part unspecified: **what exactly should count as the correct answer?**

A person's choice in a psychology experiment? A survey response? A click on a headline? A change caused by an intervention? These are different observations, different learning targets, and different products.

![Original Anicca diagram separating behavioral training data, held-out evaluation, and real customer outcomes](https://aniccaai.com/blog/manager/media/e811a70f90fd49c2810e35ee93ec7f940fa5c0aab9547a6003afb46b1e48b505.png)

## BehaviorBench's public data are not its training set

Huang and colleagues' 2026 [BehaviorBench](https://arxiv.org/html/2606.24162v3) evaluates twelve tasks across behavior prediction, strategic decision-making, subject-trait inference, and behavioral-science knowledge.

The key distinction is between the authors' **649,394 training examples** across eleven fine-tuning tasks and the **19,893 evaluation instances** reported in Table 5. Training and evaluation subjects or papers were separated. The publicly distributed [Hugging Face dataset](https://huggingface.co/datasets/befm/BehaviorBench) is an **evaluation bundle**. Its separate [official evaluator](https://github.com/umich-foreseer/behaviorbench_eval) explicitly does not include model training code.

Fine-tuning a model on the benchmark's final evaluation answers would undermine the resulting scores. It would not demonstrate generalization to unseen behavior.

## What are the actual labels?

The original sources differ sharply.

**MobLab** contributes observed decisions by real participants playing economic games, including Dictator, Ultimatum, Trust, Public Goods and Beauty Contest. The authors retained 379,754 cleaned move records from 76,035 participants.

**Big Five** contributes 981,500 self-reported survey responses from 19,630 retained participants. These labels measure answers to specific survey items, not the person's response to an intervention. The source includes demographic attributes that warrant careful privacy and fairness review.

**Scientific workflows** come from scholarly titles and abstracts, transformed into structured descriptions of research ideas, methods, outcomes, and potential impact. They teach a model a kind of research-text prediction—not observed trial-by-trial human choice.

**Economics Olympiad** supplies 124 questions with official answers, used for evaluation only. Being good at these questions does not mean accurately predicting how people will answer.

For these reasons, BehaviorBench uses several different metrics: MAE, classification accuracy, game win rates, BLEURT for open-ended research text, and Wasserstein distance for population-level distributions.

An overall leaderboard score cannot be read as the percentage of human actions correctly predicted.

## How did Be.FM 1.5 learn?

The paper fine-tunes Qwen3-4B and Llama-3.3-70B using low-rank adaptation (LoRA). Its Appendix D specifies rank eight, alpha 32, adapters across linear layers, one training epoch, peak learning rate 1e-4, a 2,048-token sequence length, and an effective batch size of 128 on four A100 80GB GPUs.

The authors report approximately 60 A100-GPU hours for the 4B backbone and 600 A100-GPU hours for the 70B backbone. Those are compute quantities, not the cost of running an entire business.

The training mixture has eleven tasks. Certain tasks are upsampled, and the Beauty Contest data are expanded into multiple winning choices in some cases. Such choices shape what a foundation model learns—and they should be measured through dedicated ablations rather than assumed to be universally helpful.

An additional subtlety matters: **generating many individual responses to form a simulated population distribution is not the same as asking the model to state the distribution explicitly**. BehaviorBench evaluates these separately and finds that rankings can change.

## Psych-101's more direct route: supervise actual choices

[Centaur](https://doi.org/10.1038/s41586-025-09215-4), described in Nature in 2025, is trained on the [Psych-101 dataset](https://huggingface.co/datasets/marcelbinz/Psych-101): 160 experiments, 60,092 participants, and 10,681,650 human decisions.

A record is primarily a participant's natural-language experimental session, often containing many trials. The participant's responses are enclosed within distinctive double-angle markers. The [official training implementation](https://github.com/marcelbinz/Llama-3.1-Centaur-70B/blob/main/finetune.py) masks the loss so that the model learns **human response tokens**, rather than being rewarded for predicting the experiment's instructions.

That is the practical distinction between a language model that can discuss psychology and one adapted to assign probabilities to actual human choices.

Centaur uses quantized Llama 3.1 70B with rank-eight adapters; the paper reports one epoch and approximately five days on an A100 80GB GPU. The public training dataset card lists Apache 2.0, but the test dataset is separately gated under CC BY-ND 4.0. The adapter also inherits Llama-specific terms. Licensing must be reviewed separately for data, code, model weights, and commercial use.

## We tested the mechanics without using restricted data

To illustrate the mechanics, we generated 128 entirely fictional participant sessions, totaling 1,152 binary decisions. We separated training, validation and test participants, created strictly past-only prompts, identified response-only supervision spans, and fitted a small logistic model by gradient descent.

On held-out fictional participants, the constant-prediction baseline achieved a negative log-likelihood of about 0.691, versus about 0.536 for the trained toy model. Thirty-seven software tests check data leakage, label parsing, metric definitions, and conservative usage gates.

This is not a new trained language model. No real human-response data, gated benchmark test answers, or Centaur/Be.FM weights entered the exercise.

## What should Anicca train on first?

We should separate a **research track**, testing whether behavioral representations generalize across people and studies, from a **product track**, focused on a specific paid customer decision.

A plausible early product hypothesis is to rank permissioned Japanese message variants before a customer decides which ones to test. It requires legitimate historical observations, a clearly defined response window, pre-decision context, independent outcome records, careful splits across campaigns and customers, and a comparison against simple baselines.

It does **not** justify claiming that a message caused an incremental response. That requires randomized assignment or a defensible causal identification strategy.

The central lesson is simple: **do not collect data in search of something a large model might learn. Define the decision that must improve, then obtain the legitimately usable observations needed to test it.**

### Primary sources
- [BehaviorBench paper (2026)](https://arxiv.org/html/2606.24162v3)
- [Official evaluator](https://github.com/umich-foreseer/behaviorbench_eval)
- [Evaluation dataset and license](https://huggingface.co/datasets/befm/BehaviorBench)
- [Centaur, Nature (2025)](https://doi.org/10.1038/s41586-025-09215-4)
- [Psych-101](https://huggingface.co/datasets/marcelbinz/Psych-101)
- [Centaur training implementation](https://github.com/marcelbinz/Llama-3.1-Centaur-70B/blob/main/finetune.py)
- [Be.FM 1.5 adapter and terms](https://huggingface.co/befm/BeFM1.5-4B)

*Evidence boundary: published model and dataset figures are attributed to their original research. Anicca's toy training statistics are entirely synthetic, not a benchmark score, real-world benefit, or commercial product result. This research article was drafted with AI assistance.*
