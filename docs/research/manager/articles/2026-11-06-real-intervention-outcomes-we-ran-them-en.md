# The Best Behavior-Change Benchmark Was Already Out There. We Ran It.

*Introducing Manager · November 6, 2026 · Real experiments, real outcomes, no invented humans.*

Imagine an AI telling someone to take a walk. The message might be beautifully worded. It might appear at exactly the right time. It might generate a click, a thank-you, or a perfect five-star rating.

But did the person actually walk?

That is the question we care about at Anicca. Manager is an AI model and product designed to understand human behavior and support outcomes people genuinely want. A model that predicts choices is useful. A model that recommends an intervention, observes what happens, and learns which interventions are worth making could be far more useful—but only if we can test it against the world.

For weeks, we wondered whether we needed to invent a new benchmark for behavioral interventions. Then we searched the literature. The answer was hiding in plain sight.

![Original evidence diagram comparing HeartSteps, RCT Bench and HBCP research results](MANAGER_EVIDENCE_IMAGE_PLACEHOLDER)

## The walking experiment that already measured the answer

In HeartSteps V1, 37 people participated in a six-week mobile-health experiment. Up to five times per day, when it was safe and feasible to intervene, the research software randomized among three options: no message (40%), a walking suggestion (30%), and a suggestion to break up sedentary behavior (30%). Wrist-worn and phone sensors recorded steps following the decision.

The authors made the data public, together with a description of the randomization, the observations and known missingness. No synthetic respondents were needed.

We re-ran a narrow analysis on a free GitHub-hosted computer: 8,274 recorded decisions, 6,590 marked as available, with an unadjusted comparison of notification versus no notification using observed Jawbone steps in the next 30 minutes.

The observed difference was **+12.95 steps**, with a participant-cluster bootstrap 95% interval of **−16.99 to +39.43**. Approximately 11.6% of the no-notification arm and 12.2% of the notification arm lacked the primary step measurement under our eligibility rule.

This does *not* reproduce the authors’ prespecified, adjusted causal excursion-effect analysis. Our crude complete-case interval contains zero, and missing tracker readings can distort results. We did not conclude that reminders work, that they fail, or that Manager helped anyone. What mattered for engineering was running an actual randomized intervention analysis on real measured behavior rather than evaluating how persuasive a message sounds.

Source: [HeartSteps V1 public data](https://github.com/klasnja/HeartStepsV1), [original trial](https://doi.org/10.1093/abm/kay067), [our reproducible cloud run](https://github.com/Daisuke134/life-manager/actions/runs/42099736589).

## A second giant: 125 randomized trials, not fifty

RCT Bench began as a standardized collection of 50 clinical trials. Its expanded public website now lists **125 individually randomized trials**, with common fields for treatment assignment, outcomes, baseline covariates and publication metadata.

We used three existing trials to test the ability to evaluate *different kinds of real outcomes*.

In **Trial 20**, adding support to an interval-walking program produced an observed difference of **+345.3 minutes** of training during 12 weeks (exploratory bootstrap interval +17.1 to +687.8). In **Trial 103**, an older-adult hospital-care intervention had a **+0.0110** observed difference in 90-day quality-adjusted life years (interval −0.0054 to +0.0289). **Trial 116** contained both a cancer-treatment quality-of-life scale and a psychological-distress measure; we calculated arm differences, but did not identify the intervention/control meaning of its Group 1 and Group 2 codes, so we do not assign a treatment-benefit direction.

These are different populations, interventions, outcome scales and original trial designs. The numbers must not be added together, interpreted as Manager's performance, or used to give medical advice. Their value is that an evaluation engine can be tested on more than clicks.

Source: [RCT Bench expanded public collection](https://bingkaiwang.github.io/RCT_Bench-main/) and [our cloud execution](https://github.com/Daisuke134/life-manager/actions/runs/42099736589).

## A third giant: an AI already predicting behavior-change outcomes

The Human Behaviour-Change Project, led by researchers including Susan Michie, did not wait for modern chatbots. It organized reports of smoking-cessation randomized trials using a formal ontology of interventions, populations and conditions.

The original model learned from **971 intervention arms across 405 studies**. Its published ontology-informed rule-based model reported a mean absolute error of 9.15 percentage points for cessation rates under its cross-validation procedure. This is a study-arm outcome forecast, not an identified effect of adding a particular behavior-change technique.

Using its public annotated arm data, we trained three small baselines on a free cloud runner. We kept all arms from the same study together in a held-out fold. Our five-fold results were:

| Study-disjoint model | Mean absolute error |
|---|---:|
| Train-fold mean | 9.99 percentage points |
| Ridge regression | 9.65 percentage points |
| Random forest | **9.45 percentage points** |

These results are **not** a head-to-head reproduction of the original RuleNN's 9.15: model, grouping and evaluation procedures differ. They demonstrate that the existing data format can serve a reproducible model-comparison pipeline immediately.

Sources: [HBCP prediction tool](https://humanbehaviourchange.org/prediction-tool), [original outcome prediction study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12603517/), [our cloud results](https://github.com/Daisuke134/life-manager/actions/runs/42100293105).

## The lesson for building a model company

We used to phrase ManagerBench as a benchmark we would need to build. That was too narrow a search.

[BehaviorBench](https://github.com/umich-foreseer/behaviorbench_eval) already covers broad human response prediction. [UpliftBench](https://github.com/binshuangli/uplift-bench) already implements multiple treatment-effect estimators and explains why different metrics can rank them differently. HBCP already makes intervention evidence machine-readable. HeartSteps already gives us randomized decisions and next-30-minute behavior. RCT Bench already supplies dozens of health and quality-of-life endpoints.

So we will **connect these components before writing a new one**.

Manager must be a useful model and product—not an eternal research presentation. The immediate stack is an existing behavior model, an established evidence catalog, a safe intervention selector including no action, a permissioned executor, and an evaluator that checks what really happened.

The missing work is narrower and harder: testing whether this integrated product improves the *self-chosen outcomes of its own users*, over time, without unwanted pressure or harm. That requires separate product trials with real consent and independent measurement.

We have not achieved that yet. Our public results are the baselines and infrastructure that will help us discover whether we do.

## Follow the work

The code is in the [Manager repository](https://github.com/Daisuke134/life-manager). Our [real intervention outcomes runner](https://github.com/Daisuke134/life-manager/actions/runs/42100293105) uses free cloud CPU, pins its sources and stores aggregate-only receipts. We will report unexpected failures and negative results with the same care as improvements.

**Manager is the model. ManagerBench is the measurement. The product succeeds only when life outside the benchmark actually gets better.**

*Editorial and research limitation: existing RCT outcomes are not a randomized trial of Manager. No new users received interventions during these runs; no individual treatment response or clinical benefit has been verified.*
