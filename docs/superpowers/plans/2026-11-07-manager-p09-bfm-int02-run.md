# Manager P09, BFM-01/02 and INT-02 Experimental Execution Plan

> For agentic workers: execute in isolated worktree with source boundary; TDD and independent evidence checks. This is an execution *plan*, not an alternate company/Manager roadmap.

**Goal:** Execute source-backed, legally permitted, non-production human-response model and intervention evaluation, strengthen existing P09 tests, and truthfully distinguish completed real model inference from blocked foundation model runs.

**Architecture:** Preserve ONE repository and existing product/runtime owner. P09-1..5 source-based evaluations remain in PR #9292; this complementary branch adds 1) HeartSteps binary random-selection effect replication with participant-cluster CI and paper estimand audit; 2) Qwen3-4B real CPU human-labeled text-only MaMe-Re evaluation with frozen holdout, human preference baseline, and no copyrighted visuals; 3) an evidence-labeled status for gated Be.FM / Centaur limitations. Maintain NO_ACTION/consent and no live intervention.

**Tech Stack:** Python 3.11/3.14 stdlib+NumPy+SciPy, GitHub Actions Ubuntu CPU with pinned llama.cpp/GGUF, GitHub official artifacts/receipts, python-pptx.

**Specs:** Existing docs/research/manager/masterclass/2026-11-04-p04-causal/ROADMAP_STATUS_JA.md; BEHAVIOR_FOUNDATION_MODEL_MANAGERBENCH_SPEC_20261106.md; PR #9292 P09-1..5; original HeartSteps V1 2019 paper, repository wiki and source commit; public MaMe-Re CC BY source fields.

## Global constraints
- No user-specific/patient data in Git; only aggregate metrics and source hash.
- No unapproved paid GPU or gated-model download; license conflict on Be.FM is not overridden by Hugging Face card.
- Centaur 70B full weights require 2×80GB GPUs / 150GB+ free disk (model card); no false deployment claim on Mac.
- Changes must not touch production runtime, release, marketing, X posts, credentials, user interventions, or existing owners.
- Source hashes and model file SHA256 pinned; model observations must have exact run ID, model ID, holdout IDs, output and cost scope.
- A successful software test is not a new human-performance experiment.

## Review focus
1. HeartSteps 'is.randomized' random selection vs post-correction 'send' delivery: wrong exposure variable must not produce false ITT.
2. Exact 6061 author cohort vs accessible raw-index 6119: no forced/guessed row exclusions.
3. MaMe-Re training scores or copyrighted images/dialogue must not leak into frozen test prompts or published artifacts.
4. GitHub cloud inference may produce no valid A/B verdict; parse invalid as missing/incorrect, not silently discard.
5. Citation, licensing, permissions, source checksum and model cost attribution must be independently auditable.

### Task 1: HeartSteps INT-02 assignment and WCLS-like audit
**Files:** products/manager/evals/heartsteps_assignment_audit.py, test_heartsteps_assignment_audit.py; docs/research/manager/verification/INT02_20261107.md
**Interfaces:** summarize_public(rows, n_boot=1000) -> aggregate dict; load via existing pinned HeartStepsV1 source. Test expected 8274/37 real rows, strict 6119 vs paper 6061, random-assignment vs delivery mismatch, stable deterministic group bootstrap, no claim of full original GEE replication.
- [ ] First create test and confirm import failure.
- [ ] Implement strict data/assignment/feature cutoff, robust outcome and status records.
- [ ] Run 37-person real cohort, compare day0 and day21 ratios to original.
- [ ] Regression + failure tests, record exact data provenance and missingness.

### Task 2: BFM-01 real free Qwen CPU receipt
**Files:** docs/research/manager/verification/BFM01_20261107.md, pinned JSON receipt; existing workflow unchanged.
- [x] Dispatch original Qwen3-4B workflow main.
- [x] Independently read official run 42365475377 and immutable artifact; success, model GGUF hash, 6s CPU, fictional allocation 0, no human score.
- [ ] Add evidence record and rights/credentials gating. No Be.FM commercial execution without clarified license and approved access.

### Task 3: BFM-02 actual fixed human-preference LLM eval
**Files:** products/manager/evals/qwen3_mame_text_eval.py, tests; .github/workflows/manager-bfm02-qwen3-mame-cpu.yml; docs/research/manager/verification/BFM02_20261107.md
**Interfaces:** deterministic public MaMe-Re dataset builder -> blinded Japanese context and image-description-only A/B prompts; forward via pinned 4B GGUF free CPU runner, compare responses against 5-vote aggregate human preferences and item-history baseline; publish only noncopyrighted metrics.
- [ ] Test red/green on deterministic holdout, rights-safe prompt contents, selection, invalid parse, score.
- [ ] Run cloud workflow on PR; obtain actual workflow/run output, only after source+weight SHA.
- [ ] Compare human win rates, accuracy, invalid rate and cost; label as text-only, not original multimodal nor Centaur.
- [ ] Centaur 70B remains separately gated by resource/license; no fake comparison.

### Task 4: P09 connection + research slides/article + review
**Files:** docs/research/manager/verification/P09_BFM_INT_INTEGRATION_20261107.md, slide appendix source; isolated presentation file/user artifact.
- [ ] Verify P09-1..5 separate PR #9292 source/test/results.
- [ ] Preserve existing ONE roadmap (BFM-01/INT-02) and document gates/status.
- [ ] Render slides, write Japanese detailed research findings and proper source links.
- [ ] Run focused tests + available full relevant suite, clean diff, commit/push, PR; check CI/readback.
- [ ] Record blockers and exact unfinished acceptance, don't merge if checks pending/failed.
