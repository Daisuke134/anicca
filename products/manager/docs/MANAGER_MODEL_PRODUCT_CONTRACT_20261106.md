# Introducing Manager — model and product contract v0.1 (2026-11-06)

**Manager is a startup product and behavioral intelligence MODEL, not merely a research project.** We build usable software now while learning and improving its models with real evidence. The general shared-weight Behavior Foundation Model is an aspirational future release; existing task-specific model evaluations, execution safeguards and evaluation harnesses do not amount to a released BFM.

## Product value
For a user-defined goal, Manager estimates relevant behavioral context, proposes a low-burden action at the right time, uses existing proven mechanisms, and compares independently observed results and harms against NO_ACTION or standard alternatives. Respect autonomy, consent, stop/revoke, privacy, and potential harm. Minimize friction and interruptions. Not a diagnosis, psychotherapy or clinical treatment without separately demonstrated safety and efficacy.

## Product model interface (logical contract, not all endpoints deployed)
- PREDICT: history up to cutoff, task, action set -> calibrated response distribution, uncertainty, model revision, provenance, abstention.
- PLAN: authorized goal and observed context -> bounded intervention candidates including NO_ACTION, benefit and burden hypotheses. Unknown causal effects remain explicitly unknown.
- EXECUTE: existing Manager Core permissioned state machine, not model-generated permission; independent effect receipts.
- EVALUATE: observed user-chosen outcome, comparator, follow-up duration, burden, dropout, harm; a provider receipt is not a welfare result.
- LEARN: offline versioned model training with public held-out data plus actual randomized outcomes where rights allow. Do not silently update production policy.

## Stand on giants, never duplicate their validated code
Model backends: Be.FM 1.5 4B, Centaur, task-specific Collins WMH reward/habit, openESM next-state, Ampersand Agents API, simple classical baselines.
External evaluation: BehaviorBench official MIT evaluator, Psych-101, HBCP, HeartSteps MRT, RCT Bench, UpliftBench, original model cards. Separate software licenses from dataset licenses; no commercial training on CC BY-NC-ND test examples without rights.
Behavior change: COM-B, BCIO/BCTTv1, published randomized behavior-change evidence; do not call an annotation a verified individual diagnosis.

## Implementation increments: real outcome evaluation
HeartSteps V1 from original CC BY 4.0 published study: original 37 participants and 8,274 decision points, available-time randomized notification vs no notification, Jawbone and Google Fit next-30-minute steps, 2,000 participant-cluster bootstrap repeats, arm-specific missingness. This is an exploratory complete-case contrast, not the authors' adjusted causal estimand or a Manager product intervention.
Public RCT Bench: three original randomized studies, including walking adherence (trial 20), 90-day QALY (trial 103), and FACT-G wellbeing and DASS distress (trial 116). Study-specific arm coding and individual data rights require primary-paper validation; no cross-trial pooling.
HBCP official smoking cessation study-arm dataset: 971 RCT arms from 405 reports; study-disjoint prediction baselines mean/Ridge/RF. This reuses the authors' real ontology-annotated intervention data, but does not reproduce their published RuleNN or prove causal impacts of individual BCTs.

All data downloaded at run time to ephemeral free GitHub cloud runner. Only aggregate JSON is uploaded; no participant-level rows or confidential keys enter repo.

## Product acceptance (NO confusing model accuracy and utility)
1. Real user-opted task, constrained scope, reliable observation, safe choice and stop mechanism; technical shadow/live action only when authorized.
2. Model predicts better than held-out baselines with calibration and uncertainty, on subject-/study-/domain-disjoint test sets.
3. Relative to NO_ACTION and usual support, measured increment in users' self-chosen behavior, with followup and independent assessment.
4. Harm guardrails: autonomy, notification burden, privacy, guilt, dropouts. Stop if negative effects exceed pre-registered thresholds.
5. Publish model/eval cards on Hugging Face and GitHub with exact rights, real-world results, independent reproductions and failures.

Business objective: verified additional user benefit per unit cost, not vanity metrics such as app-open counts or flattering leaderboard wins.

## Names and media
Introducing Manager — Behavioral Intelligence, Built for Real Life.
Introducing ManagerBench — Measure What Changes, Not Just What Models Say.
Anicca's company and product should be presented as startup products with an evidence-generating pipeline, not as an unshipped academic study. Never advertise a trained general BFM, proven RNT reduction, or clinical benefit before evidence.

## Sources and operational truth
https://humanbehaviourchange.org/prediction-tool
https://github.com/klasnja/HeartStepsV1
https://bingkaiwang.github.io/RCT_Bench-main/
https://github.com/binshuangli/uplift-bench
https://github.com/umich-foreseer/behaviorbench_eval

Curriculum source of truth: docs/research/manager/masterclass/2026-11-04-p04-causal/ROADMAP_STATUS_JA.md .
Company operational source of truth: docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md .
