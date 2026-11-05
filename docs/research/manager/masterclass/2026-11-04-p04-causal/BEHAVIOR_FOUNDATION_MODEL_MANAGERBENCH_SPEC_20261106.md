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


## 2026-11-06 adoption decision: BehaviorBench is upstream core, not something to re-implement

The default ManagerBench v0.1 evaluation backend for existing behavioral-science tasks should be official MIT `umich-foreseer/behaviorbench_eval` pinned at `ddd646ed2bbecdb79094eb56763ee7664d2f8e1a`. The public benchmark DATA are separately `CC BY-NC-ND 4.0`; **commercial uses require the correct rights, and test data may never be trained on**. Full benchmark score is not yet claimed. GitHub CPU install/unit-test receipt: https://github.com/Daisuke134/life-manager/actions/runs/42094336374 41 passed, 3 skipped. Avoid duplicating its adapters/metrics/leaderboard unless a demonstrated gap exists. The earlier local `experiments/managerbench_v0.py` is a small *software fixture scorer*, not a replacement for the upstream evaluator; retire overlapping functions when official migration and compatibility are verified.

Actual model candidates in reuse priority: gated Apache2 Qwen3-based Be.FM1.5-4B on 24GB cloud GPU, gated Llama3.1-70B base + public Centaur LoRA on A100 80GB, provider API Ampersand using the pre-existing `manager_core/ampersand_api.py`, sign-in limited Persimmon, and the Listen Labs interview/twin product. External catalog research preflight `products/manager/manager_core/behavior_model_catalog.py` tested 10/10; Be.FM Modal probe script syntax-tested but not GPU-executed. No empirical causal effects, neural mind-wandering GLM-HMM refit, or new trained common BFM in this revision.
