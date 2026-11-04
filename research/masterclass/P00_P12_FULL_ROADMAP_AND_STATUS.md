# Manager Masterclass — Complete Roadmap P00–P12

Updated: 2026-11-04. Canonical curriculum progress snapshot for this PR. This is a teaching-status document, not a claim that the experimental Manager Behavior Foundation Model or real-world interventions have been validated.

## Current checkpoint
- P00: P00-1 Mission and metrics, P00-2 Manager architecture studied; P00-3 first target and permissions pending.
- P01: P01-1 through P01-7 completed (lessons).
- P02: P02-1 previously covered; P02-2 through P02-5 completed (lessons).
- P03: P03-1 through P03-7 completed (lessons).
- P04: P04-1 observational association vs causal effects covered; P04-2 RCT/ATE covered; P04-3 observational causal inference is CURRENT. P04-4 through P04-6 pending.
- P05 through P12: curriculum/research validation pending. Partial operational prototypes do not imply completion.

## Detailed sequence

### P00 — Mission and research design
- P00-1: Defining suffering, behavior, benefit and outcomes — studied.
- P00-2: Overall Manager / Digital Buddha architecture — studied.
- P00-3: Choose first validation domain, consent and permission boundaries — pending.

### P01 — Human behavior simulation foundations (studied)
- P01-1: Prediction versus intervention.
- P01-2: Types of behavior models.
- P01-3: Probability, conditional probability, Bayes.
- P01-4: Data generation and estimation.
- P01-5: Benchmarks and evaluation design.
- P01-6: Experiment records and reproducibility.
- P01-7: Integration across disciplines.

### P02 — Data and statistical thinking (studied)
- P02-1: Synthetic populations (previously studied).
- P02-2: Units, operationalization, measurement.
- P02-3: Variance, confidence intervals and bootstrap.
- P02-4: Selection bias and missingness.
- P02-5: Data rights, leakage and train/test splits.

### P03 — Learning behavior models (studied, not claimed validated)
- P03-1: Linear regression.
- P03-2: Binary decisions, softmax and probabilities.
- P03-3: Optimization and loss functions.
- P03-4: Transformers and representation learning.
- P03-5: Memory and generative behavior.
- P03-6: SFT and DPO.
- P03-7: Survey and evaluation of behavior-model approaches.

### P04 — Causal inference and interventions (CURRENT)
- P04-1: Confounding, potential outcomes, DAGs, observational vs interventional probabilities — studied.
- P04-2: RCT, ATE, ITT, confidence intervals and sample size — studied with synthetic educational results.
- P04-3: Observational identification, g-formula, propensity scores, IPW, matching, AIPW, DiD — **CURRENT**.
- P04-4: Heterogeneous effects, CATE, ATT, mediation — pending.
- P04-5: Predictions on unseen public experiment outcomes — pending.
- P04-6: Preregistration, study decisions and value-of-information — pending.

### P05 — Link model to execution
- P05-1: Ontology.
- P05-2: Common predictions and evidence schema.
- P05-3: Permissions and agent autonomy.
- P05-4: Verification, rollbacks and stopping.
- P05-5: Shadow mode and bounded deployment.

### P06 — Validate in real business workflows
- P06-1: Choose first real-world domain.
- P06-2: Compare simulation-assisted decisions to strong baselines.
- P06-3: Sample sizes, pre-registered criteria and stopping rules.
- P06-4: Incremental profit and harm.
- P06-5: Replication, audits and observed results.

### P07 — Psychology, behavior and suffering
- P07-1: Habits and learning.
- P07-2: Cognition and emotion.
- P07-3: COM-B and behavior change theory.
- P07-4: CBT and ACT.
- P07-5: Vipassana, suffering and phenomenological constructs.
- P07-6: Validated psychological measures, consent and safety.

### P08 — Adaptive interventions
- P08-1: Just-in-time adaptive interventions (JITAI).
- P08-2: Micro-randomized trials (MRT) and N-of-1 studies.
- P08-3: Contextual bandits.
- P08-4: MDP and POMDP.
- P08-5: Safety-aware personalization.

### P09 — Generalization and transfer
- P09-1: Person, study and temporal holdouts.
- P09-2: Few-shot adaptation.
- P09-3: OOD detection and uncertainty.
- P09-4: Forgetting and negative transfer.
- P09-5: Cross-domain benchmarking.

### P10 — Business and safe operations
- P10-1: Revenue and profit measurement.
- P10-2: Capital allocation.
- P10-3: Auditing, governance and authorization.
- P10-4: Reproducible operations.

### P11 — Advanced model research
- P11-1: Model-based RL.
- P11-2: Multi-agent societies and collective behavior.
- P11-3: Distributed cooperation.
- P11-4: General-purpose behavior model refinement.
- P11-5: Careful transfers including finance.

### P12 — External replication and long-term research
- P12-1: Independent third-party replication.
- P12-2: Longitudinal effects and harms.
- P12-3: Articles, open methodology and book.
- P12-4: Continuing evaluation of general behavior intelligence.

## Next implementation milestone
Using fully synthetic data with known ground truth, benchmark:
1. Naive observational difference.
2. Outcome regression / g-computation.
3. IPW and weight diagnostics.
4. AIPW (with cross-fitting for ML models).
5. Sensitivity to unmeasured confounding, overlap failures and misspecification.
6. Effect estimate error, interval coverage and calibration in repeated simulations.
Keep lesson completion, test execution, model training and real-world efficacy in separate status fields.

See: P04-1_CAUSAL_FOUNDATIONS_JA.md, P04-3_OBSERVATIONAL_IDENTIFICATION_JA.md, P04_SLIDES_APPENDIX_JA.md.
