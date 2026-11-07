# Manager Zero-UI G0–G3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax.

**Goal:** Deliver inspectable cross-task benchmark, real trained arm-outcome prediction head and fail-closed offline Zero-UI Shadow.

**Architecture:** Reuse Nature/MaMe-Re/HBCP pinned aggregate receipts and existing evaluation/test infrastructure. Train an HBCP regularized head on study-disjoint real public data and do not claim it is a BFM. Use existing manager_core.authority for read-only offline public-aggregate Shadow. No new UI or real intervention.

**Tech Stack:** Python 3.14, numpy, existing GitHub actions, unit test, HBCP original pinned public source.

**Spec:** docs/superpowers/specs/2026-11-07-manager-zero-ui-g0-g3-design.md

## Global Constraints
- Existing signed authority/safety gate remains the authority; no real user actions, no covert personal-data access, no production run.
- Strictly hold out studies, pin SHA, never train on test labels, avoid publishing source personal rows.
- No single score across different outcome units, no claims of trained 7B universal BFM.
- Branch from current main in isolated worktree; do not modify other active owners' files. No new company SSOT.

## Review Focus
- Malformed/changed source SHA must cause validation failure (G1/G2 tests).
- Train/validation/test study overlap must fail (G2 test).
- No test-row-dependent preprocessing and model parameter fitting (G2 test).
- Missing/revoked/expired/incorrect scope returns NO_ACTION and causes zero external actions (G3 test).
- No public-aggregate sample below 30, no personal input, no effectful output (G3 test).

---

### Task 1: G0 documented and G1 strict benchmark report
**Files:** create products/manager/evals/managerbench_v1.py and products/manager/evals/test_managerbench_v1.py; update docs/research/manager/verification/G0_G1_ZERO_UI_20261107_JA.md.

**Interfaces:** build_report(nature: dict, hbcp: dict, mame: dict, qwen: dict|None) -> dict, CLI --nature --hbcp --mame --qwen --output; metric units always per-track. Output includes checksums, holdout, per-track winner/not-proven, never global score.

- [ ] Write tests that reject missing SHA, nonfinite values, mismatched dataset identity, incompatible tasks and bogus human metrics; test valid pinned receipts preserve units.
- [ ] Run failing tests.
- [ ] Implement validator, per-track report and CLI; read-only, no web if using saved receipts.
- [ ] Run 100% test pass and actual saved receipt comparison.
- [ ] Commit Task 1.

### Task 2: G2 study-disjoint trained model artifact
**Files:** create products/manager/evals/hbcp_train_v0.py and products/manager/evals/test_hbcp_train_v0.py; attach small JSON model to docs/research/manager/verification/HBCP_TRAINED_HEAD_V0_20261107.json and report.

**Interfaces:** fixed_study_split(groups,seed=20261107) -> train, calibration, test indices; train_artifact(rows) -> artifact; predict_artifact(artifact, input X) -> probabilities/percentage prediction.

- [ ] RED tests: stable group-disjoint 70/10/20, no test-label leakage, no heldout impute leak, corrupt input/model reject, model can predict from reloaded JSON.
- [ ] Implement training-only preprocessing and Ridge alpha30 fitted on real source with calibrated interval; output source SHA, study-ID list hashed splits, train/valid/test metrics, model weights SHA.
- [ ] Run tests and actual public 405-study data training; include train-mean comparison, abstention/holdout guard.
- [ ] Commit Task 2.

### Task 3: G3 no-UI *offline* P0 Shadow
**Files:** create products/manager/manager_core/zero_ui_shadow_v0.py and products/manager/tests/test_zero_ui_shadow_v0.py; add zero-UI run receipt and honest product scope documentation.

**Interfaces:** evaluate_shadow(verifier,grant,signature,aggregate_model_receipt,now,enabled=False) -> limited dict. Uses AuthorityVerifier.authorize for scoped grant domain=manager, action=shadow.observe, target=public_aggregate; public aggregate group_size>=30; no provider or filesystem effects.
- [ ] RED tests: disabled/no grant/expired/revoked/wrong target, personal data rejected, no notifications/writes, approved fixture returns read-only NO_ACTION receipt with prelearned model candidate only.
- [ ] Implement pure offline function, strict types and minimal read-only model candidate.
- [ ] Run tests and one real aggregate trained-head read-only demo without any live user data.
- [ ] Commit Task 3.

### Task 4: integration and review
**Files:** update canonical research roadmap via append-only checkpoint and G0_G1_ZERO_UI report; never replace operational SSOT; optional docs/team/BOARD.md ownership log.
- [ ] Verify G0 official merged PR #9292/#9303 readback.
- [ ] Run dedicated/adjacent Python suites and git diff --check; inspect JSON outputs and no source personal rows.
- [ ] Independent review where available; otherwise self-review limitations.
- [ ] Push dedicated branch and create PR, inspect CI; only guarded merge after all required checks succeed.
