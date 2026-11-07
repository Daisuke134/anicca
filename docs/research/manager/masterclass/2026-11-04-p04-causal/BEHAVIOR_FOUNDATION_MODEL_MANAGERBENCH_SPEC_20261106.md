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


## 2026-11-06｜文化伝達・笑いの領域横断拡張（設計のみ）

[文化・笑いのモデル/評価契約](CULTURE_HUMOR_MODEL_BENCH_SPEC_20261106.md)と[一次資料/版/権利台帳](CULTURE_HUMOR_SOURCES_20261106.md)を追加。A–Fの既存トラック内で、模倣・信念・伝達・笑い・好み・採点・通過・投票・便益を別々に評価する。共有モデルは仮説であり、人物と刺激familyの二重holdout、演者/会場/年/文化holdout、情報cutoff、ネットワーク干渉、生成の評価器過適合を必須監査にする。既存SOCRATES/Oogiri/UR-FUNNY/New Yorkerを権利確認後に再利用する。書誌上の「柴田さん」は未同定。

学習接続は元のP09-1〜P09-5。人間試験・共有モデルの学習・大会出場・新しい勝率の実測はいずれも未実施。会社の統合SSOT cursorを変更しない。P08-3〜5の教材は未マージPR #9291を参照し、mainに統合済みと仮定しない。新規[18枚補足スライド原稿](journal_club/CULTURE_HUMOR_PHASE9_SLIDES_20261106.md)を作成し、既存34枚本番版と118枚研究保存版は変更しない。
