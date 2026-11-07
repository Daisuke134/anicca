# A Leaderboard Win Is Not a Scientific Result Until Someone Else Can Check It

*Anicca Research / Manager Masterclass P12-1 / November 7, 2026*

A paper announces 90% accuracy. A product page claims a 20% improvement. A new model supposedly generalizes to people it has never met. The numbers may be correct—but here is a harder question: **what happens when an unrelated researcher tries to verify them?**

And an even harder one: if another person reproduces the same number using the same dataset, does that establish generalization to a new population or an intervention that improves human wellbeing?

Those are separate claims. Phase 12 of our work on Manager, a behavioral intelligence model and product, starts by making their evidence boundaries explicit.

![Original Anicca illustration separating repeatability, alternate computation, external reproduction and independent replication](https://aniccaai.com/blog/manager/media/859f486ad1bd4f416ed120a09601f29adea1b99ef7651f1e139b2609a8933174.png)

## A result can be executable without being independently verified

Running an experiment again with the same code and fixed random seed is useful. It demonstrates repeatability under specified conditions.

But independently reproducing the published result means something different. Under the ACM artifact-evaluation terminology, **Results Reproduced** refers to an external team obtaining the main result using author-provided artifacts, at least in part. **Results Replicated** refers to an independent study without relying on the authors' supplied artifacts.

The names vary between scientific traditions; what matters is to report precisely which people, data, code, and environments were independent.

ACM also separates merely available artifacts from those judged functional or reusable. A GitHub link is not an official badge, a proof of correctness, or a research ethics approval.

## A surprisingly easy way to overstate generalization

Imagine 100 people who each make 100 decisions. That gives 10,000 observations. Randomly splitting the rows into 75% training and 25% testing may place observations from the same person in both sets.

The model can then memorize a person's idiosyncrasies. An impressive test score might answer the question, "Can this model predict another decision by someone it has already seen?" It does not answer, "Can this model predict a previously unseen person?"

For unseen-person claims, split by person. For unseen-study claims, split by study. For future predictions, preserve the time cutoff. For cross-cultural generalization, consider languages, sites, translation provenance, and shared study material.

The official scikit-learn GroupKFold documentation is explicit: a group must not appear in both training and evaluation folds.

## We checked our own claims using different arithmetic

During Phase 11, we created a small **fully synthetic** contextual-bandit experiment with two states, two actions, and 20,000 simulated decisions. The data-generating process makes the theoretical target-policy value exactly 0.435.

In P12-1, we implemented the inverse-propensity and doubly robust calculations a second way—**without calling the original P11 evaluation function**. The original DR estimate was approximately 0.4353910556. The alternate calculation returned the same value to numerical precision.

We also verified a second toy result with a different estimator. The Phase 11 negative-transfer example fitted logistic models by gradient descent. The new cross-check derives coefficients directly from smoothed log odds of the two observed feature groups. As designed, task-specific models still outperform a pooled one on two synthetic domains with conflicting rules.

We added checks that reject training/evaluation splits sharing person or study identities. And we repeated the toy offline-policy estimate across multiple random seeds to expose simulation variability rather than presenting one seed as a universal result.

The software suite passed 37 checks.

**None of this is an independent third-party reproduction.** It is an internal alternate-method verification of artificial data. We have not reproduced a real clinical outcome, trained a new general behavioral foundation model, or demonstrated a real-world improvement from Manager.

## What a real behavioral benchmark release must contain

The Nature paper introducing Centaur reports training on Psych-101: 160 psychological experiments, 60,092 participants, and 10,681,650 choices. It also documents how to obtain the model and associated code. Yet the official test set is gated under its own access conditions. A publicly visible model repository does not grant unrestricted rights over all evaluation data.

BehaviorBench provides task identifiers, parsers, individual- and distribution-level metrics, and a public evaluator. This is precisely the kind of infrastructure that can help researchers compare models. But the evaluator's software license must not be mistaken for blanket permission to redistribute every dataset or adapter used with it.

A credible release should identify the exact data and model revisions, relevant SHA-256 hashes, training and test split boundaries, output parser, invalid-answer policy, metric denominators, baselines, random seeds, hardware and cost, uncertainty intervals, and documented failure cases.

Model Cards and Dataset Cards help make intended uses, limitations, provenance, sampling biases, and usage rights legible. GitHub's signed artifact attestations can help verify build provenance, but they do not establish scientific correctness or model safety.

## Being transparent about losing is part of the result

A model may be better at predicting individuals than reproducing population distributions. It may work in familiar studies but fail when evaluated on a new culture. It may predict a behavioral response without identifying the causal benefit of an intervention.

These are not details to hide in a footnote. They are what a serious behavior-science benchmark is supposed to measure.

For Manager, the goal is not to publish the most flattering leaderboard number. It is to build a research record in which competitors and independent researchers can discover **exactly where a model works, where it breaks, and which claims remain unproven**.

A benchmark becomes more valuable when someone else can reproduce the winner—and audit the losses.

### Primary sources
- [ACM Artifact Evaluation (2026)](https://sigsim.acm.org/conf/pads/2026/blog/artifact-evaluation/)
- [NeurIPS Reproducibility Checklist](https://neurips.cc/public/guides/PaperChecklist)
- [Centaur, Nature (2025)](https://www.nature.com/articles/s41586-025-09215-4)
- [BehaviorBench official evaluation code](https://github.com/umich-foreseer/behaviorbench_eval)
- [scikit-learn, GroupKFold and group-wise validation](https://scikit-learn.org/stable/modules/cross_validation.html)
- [Hugging Face Model Cards](https://huggingface.co/docs/hub/model-cards)
- [GitHub Artifact Attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations)

*Evidence boundary: the numerical values and 37 software tests reported above come exclusively from self-authored synthetic examples. No external independent replication, real human behavioral effect, real Manager shared-model advantage, or commercial return is established here.*
