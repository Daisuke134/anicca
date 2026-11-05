# ANICCA / Manager — Latest Handover (2026-11-05 JST)

This is the canonical portable handover prompt for **research + implementation**. At the start of every new chat, read this file and `ROADMAP_STATUS_JA.md`; verify GitHub `main` before making assertions. Update this file whenever moving to the next phase or material project changes.

## Mission and response style

**What-if Machine × Executor**: observe authorized real-world signals, model human behavior and possible interventions, compare policies, act only with valid permission and safety guardrails, independently measure actual user welfare or business benefit. Reuse strong published science, open source and open weights instead of reinventing. **Never equate toy/synthetic data, model predictions, a receipt, or delivery with validated real mental-health improvement or incremental business profit.**

Explain technical work in **Japanese, from the fundamentals** (basic definitions, each mathematical symbol, intuition, examples, code and experiment details). Research papers, model choices, data rights, design limitations and exact current implementation should be explicit. Provide status updates while working. **Presentation slide body English, full speaker script Japanese**, one speech per slide. Public talk 34 slides/approximately 43 minutes + 15 minutes Q&A; detailed research archive was 98 slides after P07-1. Lab and IACS talks forthcoming; original November 5 event was postponed, do not assume exact new date.

## Source of truth / GitHub / Mac

Repository: `Daisuke134/life-manager`
- Single curriculum SSOT: `docs/research/manager/masterclass/2026-11-04-p04-causal/ROADMAP_STATUS_JA.md`
- Research folder: `docs/research/manager/masterclass/2026-11-04-p04-causal/`
- Manager Core: `products/manager/manager_core/`
- Product spec: `products/manager/docs/specs/2026-11-04-manager-ontology-query-evidence-reuse.md`
- Company operational SSOT: `docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md`
- Presentation: `journal_club/AI_BEHAVIOR_JOURNAL_CLUB_60MIN_JA.pptx`, `.pdf`, `journal_club/SPEAKER_SCRIPT_60MIN_JA.md`; detailed archive `journal_club/AI_BEHAVIOR_JOURNAL_CLUB_JA.pptx`, `.pdf`, `SPEAKER_NOTES_JA.md`.
- Remote Mac mini ID `e38f34d7-64a7-4608-85dd-b0ff2c57e109`, prior clone `/Users/anicca/Projects/life-manager-p05-1-research-20261104`. Mac disk recently near full; do not download huge EEG/model weights without checking `df -h`. Never wipe user projects, secrets, or working data.
- Before edits: `git fetch origin main`, inspect `git status --short`, start a separate branch from `origin/main`. Prior P06 unfinished/untracked local artifacts exist; do NOT blindly git add them.
- P07-1 research PR #9230 merged to main commit `da47e929e5649183a525f40717b73a05522c9dc3`.
- Current work: `research/manager-p07-2-handover-anicca-site-20261105` (verify PR/merge; do not assume merged).

## Curriculum state

P00: purpose set, exact real subject/rights/consent outstanding.
P01-3: core lessons done, complete Behavior FM/open-weight release NOT proven.
P04: causal estimands, ATE/CATE and toy harness done; unknown-study public real RCT causal effect holdout remains.
P05: ontology, provenance, authority, outbox/reconciliation and shadow offline tested; **actual business S1 Shadow and authorized S2 limited live operation remain uncompleted**.
P06: lessons and synthetic infra done, real UCI observed behavior 53,518 rows and exploratory Qwen2.5 probe performed on Mac; real company impact, user welfare, rumination benefit not proven. A set of P06 artifacts remain untracked locally pending audit.
**P07-1: completed** using actual Collins human trial records. **P07-2 DONE as educational + real ESM forecasting; NEXT P07-3: COM-B/Behavior Change Wheel.** P07-3 through P07-6, P08-12 pending.

## P07-1 exact empirical evidence

Official MIT repository `https://github.com/AnneCollins/WMH`, five genuine research datasets Expe1/3/5/12/14, 269,603 eligible choices (sum across studies 480 participants). Participant-disjoint Expe1 train47/val16/test16. Training/validation select reward+habit+recent-memory model; Expe1 test logloss 0.4866 vs reward-only 0.5108, bootstrap improvement +0.0242 nats/trial (95%CI +0.0194..+0.0285). Expe3 EEG, Expe5 fMRI, Expe12 development, Expe14 probabilistic feedback examined as external study checks; Expe12/14 added after initial three-study output, disclose as supplementary, not preregistered. A lightweight model inspired by authors, **not full WMH model recreation or mechanistic causality**.
Reward omission repeat (deterministic-ish four tasks): low set size9.27%, high21.40%; probabilistic task Expe14: low50.73%, high48.25%. Reward omitted != erroneous choice under stochastic feedback. Turner 2026 social-media reward/habit published figure params n=1558 studied descriptively; full posting model not refit.
45/45 P07-1 tests successful.
`P07-1_JA.md`, `experiments/p07_1_real_reward_habit_eval.py`, `experiments/p07_1_real_avoidance_descriptive.py`, `evidence/P07-1_REAL_REWARD_HABIT_HELDOUT_RESULTS_20261105.json`.
After P07-2, archive now has **100 English slide pages with Japanese notes**, public 34-page talk unchanged.

## Immediate tasks — P07-2 & website

**P07-2 foundations:** observed vs latent states, cognition, valence/arousal, focused vs intentional/unintentional mind wandering, meta-awareness, rumination/RNT/worry, state vs trait; experience-sampling response bias, action/RT/EEG/eye tracking, probe-induced effects, GLM-HMM temporal inference, proper cross-participant/train-time/heldout validation, calibrated probabilities and limits. **MW != rumination and neither is by definition clinical harm.** Do not claim to have reduced human rumination from observational data.

Primary sources identified:
- Nazari et al. 2025 *Brain and Behavior* systematic review of 555 MW studies https://doi.org/10.1002/brb3.70764
- Zhang & Kool 2026 *Communications Psychology* GLM-HMM, N=93 real human behavior/probes https://doi.org/10.1038/s44271-026-00424-9 (OSF data/code linked in paper).
- Moulds & McEvoy 2025 *Nature Reviews Psychology* repetitive negative thinking https://doi.org/10.1038/s44159-024-00399-6
- Hoebeke 2022 human real-life rumination ESM: **40 people, 2102 scheduled rows**, 14 days, 4 beeps/day, harmonized CC BY4.0 public Zenodo `https://openesmdata.org/datasets/0013_hoebeke/`; official TSV has brooding, self-criticism, negativity, replaying, perseveration, attention control. Data URL `https://zenodo.org/api/records/22952951/files/0013_hoebeke_ts.tsv/content`, SHA256 `85593640b46cc3ab80115ad7e0b1ae5c5ed2ad29ca1ec56d338c45654a17cb58`. Be careful that coding for `att_control` and `activity` is marked unclear.
- Dejonckheere 2019 real affect ESM 100 people, 9800 rows, CC BY4.0 `https://openesmdata.org/datasets/0012_dejonckheere/`; official TSV URL `https://zenodo.org/api/records/17347570/files/0012_dejonckheere_ts.tsv/content`, SHA256 `2cabd3f416f2dd5707b1623de5ac8cdba5de2834616e2a8df2a52e8c5473bf53`. IMPORTANT **no direct rumination field** in released harmonized TSV; only emotion ratings happy/relaxed/sad/angry/stressed. Do not label this a rumination dataset for model training.
- OpenNeuro meditation EEG ds001787 24 subjects, mind-wandering probes, large files; ROAMM ds007629 EEG+eye 44 people; BCIT ds004121 public EEG. Consider download size and actual label availability.

Build a real licensed-data benchmark for next-step brooding or affect, with subject-disjoint (and separately within-person forecasting) train/validation/test, a strong last-value baseline, Ridge/RandomForest and genuine uncertainty; never treat same-time predictor variables as available earlier. Do not mix the two datasets' incompatible labels. Prefer existing `openesm`, `sklearn`, `statsmodels`, `hmmlearn` rather than custom fit engines.

**Anicca website** `https://aniccaai.com/`: live copy already says Anicca builds Life Manager, proactive general agent for body/mind/money, with an ambitious zero-human company vision. User requests updating outdated wording; verify production source in `Daisuke134/anicca-products` (Mac `/Users/anicca/Projects/anicca-products`) or exact deployed repo. Modify only verifiable owned source; do not claim planned features or clinical efficacy are released. Inspect deployment and perform appropriate review/readback before declaring live.

**Handover maintenance:** keep this file committed and updated on each curriculum step, latest commit and actual status. If asked for handover now, output a copy-paste prompt immediately and link this file. Slides English + Japanese notes; preserve 34-slide ~60-minute main talk, append scholarly evidence to optional archive if helpful.

## Handoff next commands

1. `git status --short && git fetch origin main && git log -1 origin/main --oneline`.
2. Read `ROADMAP_STATUS_JA.md`, `P07-1_JA.md`, and this handover.
3. Download/pin Hoebeke openESM TSV from its official Zenodo record and evaluate real per-person repeated states with no lookahead or leakage.
4. Inspect Anicca live/source, draft grounded copy, update correct repo via isolated PR if safe.
5. Add P07-2 lecture, results, tests, research-slide appendix as appropriate, update curriculum SSOT, validate/merge PR and update this handover.


## P07-2 incremental update, 2026-11-05

**P07-2 lecture + real observational ESM forecasting performed**. Official openESM/Zenodo CC BY4.0, not fake subjects: Hoebeke2022 40 participants/2102 original records, 1450 consecutive within-day transitions, last Brooding RMSE30.804 vs validation-chosen Ridge25.979 on held-out 8 participants (bootstrap improvement CI +1.566..+7.807). Dejonckheere2019 100 people/9800 original records, 6890 transitions, next Stress (NOT rumination) persistence RMSE27.302 vs selected RandomForest24.543 on held-out 20 participants (CI +0.471..+4.439). Current observation only predicts later self-report: no EEG, GLM-HMM empirical reproduction, direct mind-wandering probe, treatment, real rumination reduction, or company profit. 30 P07-2 tests + 45 prior P07-1 tests = 75/75 reviewed current real-data tests successful. Details in `P07-2_JA.md` and `evidence/P07-2_REAL_ESM_HOEBEKE_AFFECT_RESULTS_20261105.json`.

Research archive expanded **98→100 slides** (new English appendix 99/100, Japanese notes), public presentation 34-slide PDF/PPTX unchanged. Website homepage currently has stale evidence status text; bilingual proposed copy in `ANICCA_SITE_COPY_UPDATE_PROPOSAL_20261105.md`. **Actual aniccaai.com source update was blocked by host safety and NOT published**; do not claim it is live.

**Next curriculum step P07-3 COM-B; official GLM-HMM + EEG/ESM cross-modal real datasets are pending optional deep research.** Always update this file before closing a phase.
