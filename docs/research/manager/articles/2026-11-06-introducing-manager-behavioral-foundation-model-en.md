# Introducing Manager: The Behavioral Foundation Model, Explained From First Principles

*November 6, 2026 · Anicca · Model / Product / Evaluation · Readable guide and FAQ.*

**Manager is an AI model and a product.** Its goal is to understand human behavior, simulate possible responses, and help people achieve outcomes *they choose*. We intend to release an open-weight Behavioral Foundation Model, but there is **no released general Manager model checkpoint yet**. Open code and real-world trial analyses already exist; Manager-specific improvements in users' lives remain to be verified.

![Original model/evaluation landscape and terminology infographic](https://aniccaai.com/blog/manager/media/db5dfc3a6171eb60235a6131e7a15e5c8e5c72d043df5fa86ea1cd8f96bd218b.png)

## First: what is a Behavioral Foundation Model?

A *model* is a function learned from data. In the simplest possible case, it takes a context such as recent walking, time, and an upcoming schedule, and outputs probabilities for possible next behaviors. A *foundation model* aims to reuse learned representations across many tasks and populations instead of being trained exclusively for one question.

A behavioral foundation model aims to learn shared regularities in how people decide, remember, acquire habits, react to incentives, and respond to context. Models such as **Centaur** and **Be.FM** already exist. We should run them, improve or fine-tune only where needed, and release our own open weights only when independently validated transfer merits it.

**Prediction is not intervention.** Knowing that someone is unlikely to walk tomorrow does not tell us whether a notification will help, or whether it will annoy them. A useful model-company must test predictions, intervention effects, user autonomy, and downstream outcomes separately.

## What we learned from competitors

[Simile](https://www.simile.com/) presents human-behavior simulations as a directly useful enterprise product. It describes continuous real-human data collection, validation, and a confidence model for when simulated answers are trustworthy. Its website reports over **7,000 evaluations**; this is a company-reported claim, not a public head-to-head score we independently reproduced. Simile's headline is concrete: decisions that can be simulated.

[Artificial Societies](https://societies.ai/) leads with consequential decisions and communicates a full mechanism: real-world-grounded personas, social networks, and simulated influence. Its [evaluation](https://societies.ai/eval) and [September 2026 explainer](https://societies.ai/knowledge/what-are-artificial-societies) report **86% distribution accuracy over 1,000 surveys** relative to a **91% self-retest ceiling** using its own definition. This too is a company-reported benchmark. Its simulation platform is not the same as a clinically validated intervention service.

Our lesson is straightforward: present **what the customer can do**, **what is measured**, **how confidence is assessed**, and **how to try it**. Copy the rigor and clarity of the underlying mechanisms, not another company's marketing language or unverified accuracy claims.

## Reuse-first model and evaluation stack

| Existing component | Actual role | Reuse decision |
|---|---|---|
| [Centaur](https://www.nature.com/articles/s41586-025-09215-4) | 70B cognition model fine-tuned on Psych-101 human choices | Run as an external behavior-prediction baseline |
| [Be.FM 1.5-4B](https://huggingface.co/befm/BeFM1.5-4B) | Open-weight LoRA model on Qwen3-4B for human survey/game predictions | First inexpensive GPU model candidate, gated access |
| [BehaviorBench](https://github.com/umich-foreseer/behaviorbench_eval) | Existing MIT-licensed evaluator of behavioral-science modeling | Reuse original code; its dataset is separately CC BY-NC-ND |
| [HBCP](https://humanbehaviourchange.org/prediction-tool) | Ontology-based intervention outcome prediction from smoking-cessation trials | Reuse trial-arm dataset and original methods |
| [HeartSteps V1](https://github.com/klasnja/HeartStepsV1) | Real 6-week micro-randomized activity suggestion study | Reuse randomized decision data and outcomes |
| [RCT Bench](https://bingkaiwang.github.io/RCT_Bench-main/) | 125 standardized real participant-level randomized trials | Reuse real health/behavior/quality-of-life endpoints |
| [UpliftBench](https://github.com/binshuangli/uplift-bench) | Compare heterogeneous treatment-effect estimators and objective mismatches | Reuse metric baselines and policy evaluation tools |

As of November 6, our cloud reproducibility includes **41 passed / 3 skipped** upstream BehaviorBench software tests; a real **971-arm / 405-study HBCP** study-disjoint baseline (Random Forest MAE **9.45 percentage points**, not directly comparable with the paper's RuleNN); a HeartSteps exploratory walking analysis; and three existing RCT Bench trials covering walking adherence, quality-adjusted life years (QALYs), and quality of life or distress. These are **not new Manager intervention trials**.

### A correction from the original HeartSteps paper

Our first exploratory analysis used **6,590** available records from the public source and reported a **+12.95-step** difference between records marked *sent* and *not sent*. On inspecting the original data construction, the variable **send** is a corrected delivery-status field. It is **not a verified, untouched assignment variable for an intention-to-treat comparison**. The paper selected **6,061** decision points for its prespecified analyses and reported an adjusted **35 additional steps** averaged over activity suggestions (p=.06). These differ in eligibility, outcome processing and estimand. **Do not interpret our +12.95 as an identified causal effect.** We retain the number transparently as a descriptive software-and-data audit and use the original paper for its causal analysis. This is how an evaluator should respond when it finds an identification error: correct the claim, not the history.

See the [original trial methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC6401341/), [dataset-construction source](https://github.com/LisaGotzian/HeartSteps/blob/master/build_heartsteps_data.R), and [our original cloud run](https://github.com/Daisuke134/life-manager/actions/runs/42099736589).

## The terminology, one concept at a time

| Term | Meaning from first principles |
|---|---|
| Model | A function that learns patterns from examples, then produces a prediction or response. |
| Foundation Model | A broadly reusable trained model; one representation can support multiple tasks. A claim to evaluate, not a size-based honorific. |
| Open source | Software code can be inspected, reused, and modified under its actual license. Code availability does not mean model weights or datasets are open. |
| Open weights | The model's trained parameters are downloadable under stated terms. It does **not** automatically mean the training data or full training pipeline is open. |
| Inference | Running a trained model on new input without changing its weights. |
| Fine-tuning / LoRA | Adapting an existing model to a task, often by training relatively small added matrices rather than all parameters. |
| Behavior simulation | Producing hypothetical decisions for a person or population. Plausible simulations are not verified real-world outcomes. |
| Agent-based model (ABM) | A simulation containing interacting individual agents; society-level patterns emerge from their interactions. |
| Benchmark | A fixed task, dataset, metrics and procedure that makes model comparisons repeatable. |
| Baseline | A simple existing method (e.g., always predict no change) that a new model should beat. |
| Holdout | Data kept outside training so the model is judged on examples it did not learn from. Entire people or studies may need to be held out. |
| RCT | Randomized controlled trial: participants or decision points are assigned to alternatives by chance, reducing confounding. |
| MRT | Micro-randomized trial: repeated randomization at many small decision points within the same person's daily life. |
| JITAI | Just-in-time adaptive intervention: assistance chosen based on the right moment and context. |
| ITT | Intention-to-treat: compare groups by *random assignment* even when the intervention was not delivered or followed. |
| Treatment / Intervention | An action meant to change an outcome, such as a walking suggestion or action plan. |
| Outcome | What is measured afterwards: for example, steps, habit days, stress or quality of life. Clicks may be a poor outcome. |
| Causal effect | The difference between what would happen under an intervention and without it, under a valid identification design. |
| ATE | Average treatment effect: average causal difference across a population. |
| CATE | Conditional average treatment effect: the average causal difference for people with a given context or characteristic. |
| Uplift | Additional outcome attributable to treatment (or a model's estimate of that increment), not merely raw prediction accuracy. |
| Confounding | Another variable affects both intervention selection and outcome, potentially creating a misleading association. |
| Bootstrap | Repeatedly resample observational units to characterize uncertainty; repeated records from one person require clustering. |
| 95% Confidence Interval | A procedure that covers the true parameter in 95% of hypothetical repetitions under its assumptions; not a 95% probability about an already fixed number. |
| QALY | Quality-adjusted life year: one year of life weighted by health-related quality; used in healthcare evaluation. |
| COM-B | Capability, Opportunity, Motivation → Behavior: an organizing framework for why a person can or cannot act. |
| BCT / BCTTv1 | Behavior Change Technique; the taxonomy v1 catalogues 93 precisely described intervention components. |
| BCIO | Behavior Change Intervention Ontology: a machine-readable vocabulary for interventions, contexts and outcomes. |
| HBCP | Human Behaviour-Change Project: reused published intervention-study evidence and predictive models. |
| HeartSteps | A real mobile-health intervention experiment, not a foundation model itself. |
| RCT Bench | A collection of standardized real randomized-trial datasets, not one treatment or one trained model. |
| RNT / PTQ | Repetitive Negative Thinking; Perseverative Thinking Questionnaire, a validated self-report measure of that pattern. |
| Calibration | Whether events predicted with probability 70% occur about 70% of the time over comparable predictions. |
| Policy | A rule or model selecting what action to take; **NO_ACTION** must be possible. |
| Off-policy evaluation | Estimate a new policy's value using previously logged action/outcome data, with required support and assignment propensities. |

## Frequently asked questions

**Q: Is Manager already a trained general Behavioral Foundation Model?**

No. Manager is the behavioral AI product and model stack. It is **building toward** a general open-weight checkpoint; released baselines and evaluation code are not equivalent to a new trained, cross-domain model.

**Q: Does outperforming BehaviorBench mean Manager improves lives?**

No. A behavioral prediction leaderboard measures predictive fidelity on selected tasks. Real-world utility requires independent intervention and harm outcomes.

**Q: Why should a model care about people who decline help?**

Because respecting autonomy is part of success. A reliable system abstains when the action is unsupported or unwanted, and retains a NO_ACTION option.

**Q: Why not develop our own benchmark from scratch?**

Existing public tooling includes BehaviorBench, UpliftBench, HBCP, HeartSteps and RCT Bench. We adopt them and develop a separate, documented extension only for an empirically demonstrated gap.

**Q: Did the HeartSteps +12.95 mean the notification improved walking by 12.95 steps?**

No. It is a descriptive comparison on corrected delivery records with different inclusion criteria from the paper. The original randomized assignment and analytic protocol must be recovered for a causal result.

**Q: What is the first new model to run?**

Be.FM 1.5-4B against its Qwen3-4B base on an authorized cloud GPU, followed by a properly licensed real-human holdout. The access-controlled LoRA and original dataset licenses remain gates.

**Q: Does more data guarantee accurate predictions of individuals or societies?**

No. Population-level distributions can match even when individual choices are wrong; shifts in culture, time and incentives can break any simulation.

**Q: When will Manager be useful, instead of endlessly publishing studies?**

The product must ship useful user-chosen assistance with reliable permissions and independent outcomes. We learn and build in one cycle: reuse an existing method, run it, compare against a baseline, integrate a bounded improvement, ship, and publish the verified result.

## The one product roadmap

There is **one** operational learning-and-building queue in [Manager's canonical roadmap](https://github.com/Daisuke134/life-manager/blob/main/docs/research/manager/masterclass/2026-11-04-p04-causal/ROADMAP_STATUS_JA.md). The next gate is real Be.FM 4B cloud inference and proper head-to-head evaluation versus Qwen3 with legally accessible holdout data. The website, book, and slides are outputs of the same gate, not separate competing workstreams.

*Research and product disclosure: No independent randomized trial yet demonstrates that Manager itself reduces rumination or improves users' quality of life. We do not market an untrained checkpoint as an already released model.*