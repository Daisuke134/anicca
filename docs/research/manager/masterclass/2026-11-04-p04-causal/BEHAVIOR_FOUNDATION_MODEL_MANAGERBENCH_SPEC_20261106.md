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

## 2026-11-07｜P09-1 real-data figure-level audit (NOT original RDS reproduction)

Official Nature 2026 Fig1 panelA (published aggregate directed contrasts) independent Python reanalysis completed using 70 studies / 3356 directed contrasts, 1678 mirror pairs. Pooled descriptive Pearson=.8051489, RMSE=.1183468; 2000 study-cluster bootstrap percentile r CI .5973–.9093; LOSO linear calibration trained on 69 and tested on the 70th yields micro RMSE .1183468→.0814526, with 56/70 studies improved and 14 harmed. All statistics are **exploratory source-figure reanalyses**, not the authors exact adjusted model, whose panelB reports GPT-4 raw=.8507895, adjusted=.9151266. Code Ocean source RDS export requires authentication; original Rscript absent and NOT_RUN. Use P09-1_JA.md, evidence/P09-1_NATURE_FIG1_RESULT_20261107.json, experiments/p09_1_nature_fig1_reanalysis.py and linked synthetic software tests (9 PASS). Original input normalized CSV was excluded from Git. No commercial training rights inferred from public browser availability. Unseen-study split for a calibration head does not establish lack of base LLM pretraining contamination.


## 2026-11-07｜Phase 9 real-data lightweight model evaluation, not BFM-training

Source-backed [P09-2..5 report](P09-2_TO_P09-5_REAL_EVAL_20261107_JA.md), [fixed metrics/sha manifest](evidence/P09-2_TO_P09-5_REAL_TWO_DOMAIN_EVAL_20261107.json), [executed NumPy model script](experiments/p09_2_5_empirical_bench.py), [10 unit tests](experiments/test_p09_2_5_empirical_bench.py), Japanese [P09-2](P09-2_JA.md) [P09-3](P09-3_JA.md) [P09-4](P09-4_JA.md) [P09-5](P09-5_JA.md). Nature 2026 official published effect pairs 70 studies/1678 de-mirrored aggregate contrasts; MaMe-Re human aggregate rating 250 contexts x 400 memes/100000 pairs, 160 train /40 validation/50 heldout contexts. Sources and file-specific rights pinned, no copyrighted manga images/dialogue trained.

P09-2: 36 eligible heldout studies, original saved predictions RMSE .12008, global linear calibrated .08154, partial-pooling k5 .08026 vs unpooled k5 .08478; 19/36 studies improved, 17 harmed, exploratory paired-study 95% interval for macro gain [.000505,.003788]. **Research-level effects, not individual personal-twin accuracy**.
P09-3: 24 published train, 8 published calibration, 8 published test, 30 unpublished comparison studies (publication status is not true culture/domain OOD). RMSE .05244 vs .08334; empirical coverage 100% vs 98.54% from extremely wide ±.24248 intervals. No unconditional exchangeability/conditional conformal guarantee, no real-world intervention authority.
P09-4: intentionally undercapacity shared scalar calibration transfers between Nature effect and MaMe-Re funniness: old Nature RMSE .04541→.08452 after target-only training; balanced average .06023; separate domain heads avoid interference. NOT catastrophic forgetting shown in a neural BFM or evaluation of EWC/PCGrad.
P09-5: 50 unseen Japanese contexts/20000 contextual meme scores: global mean RMSE .186687; meme-item historical mean .184605; text+description ridge .184694 (not better). Exploratory context-level bootstrap on difference includes 0. Cannot pool incompatible metrics into a universal leaderboard.

The standalone 16-slide supplement PPTX/PDF was generated and visually QA'd as a separate conversation artifact; Mac generated an archival 134-slide PPTX retaining original 118 slides and adding 16 Japanese speaker-note slides, but **canonical binary Git upload and PDF134 export did not complete** because of shared disk pressure and absent local LibreOffice. Repo retains the slide generator + source outline. Original 34-slide main presentation unchanged. No public article deployment, no new 7B inference, no original Nature RDS replay, no human outcome trial; BFM-01/INT-02 remain separate product implementation gates within the ONE existing roadmap.
