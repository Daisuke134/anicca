# Manager Behavior Foundation Model × ManagerBench (research specification v0.1)

Date 2026-11-06. Status: IMPLEMENTATION STARTED AS EVALUATION SCAFFOLD. No unified foundation model trained or published; no newly demonstrated real treatment effects.

## Problem / architectural contract
Manager should estimate reusable state from time-ordered history and compare intervention outcomes, not merely generate persuasive text. Five separate capabilities:
1. Behavioral representation across people, tasks, studies, time, reward, habit and attention.
2. Calibrated predictive head: choice probabilities, state forecasts and uncertainty, with abstention.
3. Causal-response head only when intervention identification is defensible (e.g. genuine randomized trials).
4. Authorized policy constrained by consent, stop/revoke, costs and NO_ACTION.
5. External outcome evaluator that independently measures behavior, burden, agency and long-term harm.

Prediction P(Y|X) is not intervention effect P(Y|do(A),X). The model may share features while runtime execution rights remain outside the model weights.

## Benchmark architecture: six distinct tracks
A. Choice / reward / habit / memory: participant-disjoint choice LogLoss, Brier, ECE, strong pooled and participant baselines. Source: Collins WMH actual P07-1 analysis. Currently only prior single-task result; unified scorer not previously run.
B. Time-indexed state / affect: next-step RMSE, MAE, calibration if distributional prediction; persistence and Ridge/RF; by person bootstrap. Source: openESM Hoebeke Brooding and Dejonckheere Stress, P07-2. Labels MUST remain separate.
C. Distributional human response: TVD/EMD, subgroup and study-level drift; expose separate cohort uncertainty. No real unified run.
D. Causal external study forecast: randomised-study holdout, ITT/ATE error, calibration/coverage, partial identification; zero-effect and trial averages as baseline. Real external RCT out-of-study holdout NOT DONE.
E. Safe policy & abstention: uncertainty-based NO_ACTION, unnecessary interruption count, policy regret when valid logged propensities and outcomes exist, override handling. Software harness ONLY.
F. Actual human benefit: opt-in longitudinal randomized evaluation of self-chosen behavior, distress and daily function with burden, withdrawal and adverse consequences. NOT DONE.

No single leaderboard score blending incompatible endpoints until all weights and source licenses are fixed in a pre-registered protocol. Publish negative results too.

## Existing projects to reproduce/compare
Centaur (2025 Nature human cognition foundation model): https://www.nature.com/articles/s41586-025-09215-4 ; source https://github.com/marcelbinz/Llama-3.1-Centaur-70B ; verify source rights.
BehaviorBench (2026): https://github.com/umich-foreseer/behaviorbench_eval ; check each dataset and CC BY-NC-ND restrictions, do not assume rights for commercial training.
BCIO: https://github.com/HumanBehaviourChangeProject/ontologies .
WMH human trials: https://github.com/AnneCollins/WMH .
openESM: https://openesmdata.org/ .
Zhang & Kool official GLM-HMM OSF https://osf.io/jbp6h/ : official reproduction pending.

## Minimal data contract
Record fields: source_dataset, study_id, participant_id (pseudonym), event_id, timestamp, feature_cutoff, task, target_type, observed_label, observed_at, prediction, model_revision, rights_manifest_sha256. For intervention metrics additionally intervention_candidates, randomized_assignment, propensity, delivery_confirmed, independently observed outcomes, safety and withdrawal. Exclude individual raw sensitive histories from public repos.
Three evaluation splits: (1) participant holdout in the same study; (2) full unseen study holdout; (3) time-forward/adaptation split within person. Report each separately, prevent preprocessing/overlap leakage and align the prediction horizon.
License/data cards pinned by hash, origin, copyright, commercial reuse and publication restrictions; private holdout kept contamination-resistant. Report per-person clustered bootstrap intervals, seed, compute, baselines, failure categories. Never market a score calculated on artificial unit-test fixtures as human performance.

## Build gates: START NOW, no fake launch dates
B0 CURRENT: reproduce published P07 baselines and implement stdlib ManagerBench v0 evaluation and tests (unit tests explicitly synthetic).
B1: integrate existing published participant-heldout real data and check reproducibility + license provenance against known P07-1/2.
B2: simple shared temporal encoder/head, compare against GLM, reward/habit, persistence and single-task deep learning on subject/study/domain holdout.
B3: legally available open-weight baseline comparisons incl Centaur/BeFM and a language-model baseline, identical input & budgets; model card and heldout calibration.
B4: independent randomized intervention corpus, logged propensities, verified causal effect forecasts and abstention. NEVER train causal head on observational response labels alone.
B5: limited opt-in real-world MRT/RCT after suitable permissions/review, independent behavior and harm outcomes; stop/revoke and unexpected effects.
B6: community OSS benchmark (evaluator, manifests, dataset cards, train/dev data where licensed, protected unbiased test, leaderboard, model submissions, errata, independent replications).

Acquisition and publicity are *potential consequences*, not benchmark goals. The compelling scientific artifact is a credible model plus independent reproducibility, well-defined causal endpoints and an honest safety report.

## Separation from other documents
This is a model/eval design document; ROADMAP_STATUS_JA.md remains the ONE curriculum status authority. Executable v0 scoring harness: experiments/managerbench_v0.py, test file with small software-fixture examples only. No human examples invented.


## 2026-11-06｜Phase 8 P08-3〜P08-5 policy / sequential / human-research extension (DESIGN ONLY)

This section extends the original A–F benchmark tracks, not a new benchmark or model workstream. Detailed source-grounded Japanese lessons: [P08-3](P08-3_JA.md), [P08-4](P08-4_JA.md), [P08-5](P08-5_JA.md). The 12-slide research appendix is **source text only**, not a regenerated PPTX/PDF: [Slide source](journal_club/PHASE8_P08-3_TO_P08-5_RESEARCH_SLIDES_SOURCE_JA.md). Publication-ready JA/EN articles are **drafts**, not live pages: ../../articles/2026-11-06-learn-bandits-mdp-and-safe-interventions-{ja,en}.md.

### P08-3 policy contract
1. BFM.predict can estimate states, behavior and uncertainty. It does not identify causal response without a defensible research design.
2. causal_response supplies study-identified effect estimates, CI, source population, feature cutoff, transport limitations and an explicit NOT_IDENTIFIED state.
3. policy.propose chooses only from externally validated A_safe(context) and includes NO_ACTION as a normal option. Revocation / STOP is enforced by the permission layer and is **not** a learnable arm.
4. The initial policy comparators are NO_ACTION, fixed time, deterministic rules/JITAI, epsilon-greedy, LinUCB and linear Thompson Sampling. Reuse MABWiser instead of writing an unvalidated bandit solver. All new actions are DRAFT_ONLY in offline mode.
5. OPE must have a verified historical assignment probability, positivity/support, consistent definitions of reward and availability, pre-action covariates, treatment/delivery separation, missingness, participant dependence and policy versioning. Report DM / IPS / DR, weight-distribution, ESS, CIs and sensitivity analysis; suppress unsupported value claims. MABWiser library docs: https://fidelity.github.io/mabwiser/ ; OBP: https://github.com/st-tech/zr-obp ; DR: https://www.microsoft.com/en-us/research/publication/doubly-robust-policy-evaluation-and-learning-2/

### P08-4 sequential decision contract
An MDP models (S,A,P,R,gamma); transition P(next_state|state,action) is a hypothesis and requires heldout validation. POMDP adds permitted observations and a probabilistic belief, not an asserted psychological diagnosis. Bellman evaluation, finite artificial worlds and belief updating come **before** deep or online RL. Long-horizon value cannot be empirically identified merely by applying one-step IPS to ordinary outcome logs; sequential support, unmeasured confounding, delayed effects and simulator error need their own audit. Compare simple policies under the same objective, constraints, observation budget and horizon. If the complexity has no independently measured incremental benefit, prefer the simpler policy. References: Sutton & Barto 2018 https://mitpress.mit.edu/9780262039246/reinforcement-learning/ ; POMDP belief filter https://search.r-project.org/CRAN/refmans/pomdp/html/update_belief.html

### P08-5 permission, research and monitoring contract
Separate consents for (a) user-chosen goal, (b) data processing, (c) delivery channel and (d) research participation/randomization. Recording consent does not create universal authorization to test arbitrary interventions. Stop/revoke before policy action. Track both proximal and distal outcomes, burden, functioning, autonomy, harms, missingness, attrition and fidelity (assignment→delivery→receipt→outcome) independently of engagement.
Use a monitoring incident taxonomy: GREEN normal; YELLOW freeze adaptation and fall back to NO_ACTION on uncertainty/drift; RED stop unsafe action and follow incident/escalation plan. Human-subjects protection, legally necessary ethics review, trial governance, and protection/recourse are **not** optional because the company automates software. Oralytics 2025 online decision making: https://pmc.ncbi.nlm.nih.gov/articles/PMC12122013/ ; 2026 monitoring: https://www.nature.com/articles/s41746-026-02669-4 . The Oralytics one-arm 79-enrolled/72-analyzed case study is **not a causal proof of superiority to a no-intervention group**.
Jurisdiction rules require individual assessment. Japan's biomedical human-subjects guidelines amendment publicized August 2026 takes effect **2026-12-01**, which is after this document date: https://www.mhlw.go.jp/stf/newpage_75864.html . Also consult US OHRP https://www.hhs.gov/ohrp/regulations-and-policy/guidance/faq/informed-consent/index.html , EU AI Act Article 5 https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-5 , GDPR guidance https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/legal-grounds-processing-data_en , and FDA CDS intended-use guidance https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software . Do not assert across-the-board medical device status or exemption.

### Minimal decision/evaluation schema (conceptual, not deployed)
decision_id, pseudonymous participant_id, study_id, decision_ts, feature_cutoff, context_provenance, availability, eligible_actions, consent_scope_version, revoked_at, assigned_action, original_propensity, randomization_verified, delivered_action, received_at, outcome_at, proximal_outcome, distal_outcome, missing_reason, intervention_burden, harm_flag, model_version, policy_version, policy_probability_vector, decision_reason, safety_fallback, rights_manifest_hash. Store person-level data only in appropriately permitted systems; never commit participant rows to Git.

### Acceptance gates and implementation handoff
- **Research literacy DONE:** sourced lessons P08-3/4/5, algorithm equations, careful causal distinctions, JA/EN article drafts, slide source; this does not mean any original human result.
- **Implementation NOT_DONE:** no new bandit runtime, no MDP/POMDP training, no fresh OPE score, no participant randomization, no regenerated research PPTX/PDF, no public article deployment.
- **Next Codex sequence:** verify P08-1 PR merge and HeartSteps original randomization (P08-2); reuse MABWiser/OBP; test synthetic policy+OPE including negative cases; add limited finite MDP/POMDP simulator; check the rights and study gates; only then consider read-only integration. BFM-01 remains the integrated model product goal, INT-02 is the causal evaluation increment; don't create multiple competing master roadmaps.
- **Benchmark truth:** A/B/C behavior forecast; D identified causal effect; E safe policy and OPE under logged support; F independent human welfare. Never publish a synthetic or unaudited OPE score as verified real human benefit.
