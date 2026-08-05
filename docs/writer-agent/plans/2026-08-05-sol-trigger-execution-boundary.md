# Sol Trigger Execution Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ordinary Writer calls incapable of selecting Sol, and permit one Sol medium/high invocation only when a valid run-bound trigger receipt is atomically claimed.

**Architecture:** Extend the sole `model-runner.sh` boundary with a default `terra` role and an explicit `sol-audit` role. `sol-audit` validates a JSON receipt, matches its run ID, validates its allowed trigger/effort/artifact hash, and atomically creates a claim directory before provider execution. The claimed route is Codex-only and cannot fall back to Claude or run twice.

**Tech Stack:** Bash, jq, Python standard-library unittest, fake Codex command capture.

## Global Constraints

- Missing `ARTICLE_MODEL_ROLE` means `terra` and selects `gpt-5.6-terra`.
- Only `ARTICLE_MODEL_ROLE=sol-audit` can select `gpt-5.6-sol`.
- Sol requires `ARTICLE_SOL_TRIGGER_RECEIPT` with schema version 1, matching `run_id`, nonempty `artifact_id`, 64-hex `article_sha256`, allowed trigger, and effort `medium|high`.
- Allowed triggers are `medical`, `legal`, `financial`, `high_value_submission`, `new_topic_class`, `quality_sample`, and `strategy_promotion`.
- The receipt is atomically claimed before the provider call; a second call exits `78` without invoking a provider.
- Sol uses Codex only and never falls back to Claude.
- This slice does not create trigger receipts; deterministic trigger producers are the next slice.

---

### Task 1: Fail-closed one-use Sol route

**Files:**
- Modify: `skills/writer-agent/tests/test_model_runner_contract.py`
- Modify: `skills/writer-agent/runtime/model-runner.sh`
- Modify: `skills/writer-agent/runtime/README.md`
- Modify after verification: `docs/writer-agent/WRITER-AGENT-SSOT.md`

**Interfaces:**
- Consumes: `ARTICLE_MODEL_ROLE=terra|sol-audit`, `ARTICLE_SOL_TRIGGER_RECEIPT=<path>`, `ARTICLE_RUN_ID`.
- Produces: Codex `--model gpt-5.6-sol` with receipt-selected `medium|high`, `<receipt>.claim/receipt.sha256`, and no second provider call.

- [x] **Step 1: Add failing model-runner contracts**

Extend the unittest with valid Sol receipt, missing receipt, invalid trigger, run mismatch, and replay cases. Verify RED because the current runner ignores the role and still captures Terra.

- [x] **Step 2: Implement minimal role/receipt validation and atomic claim**

Default role to Terra. For Sol, validate with jq, create the claim directory using atomic `mkdir`, store the receipt SHA-256, set model/effort, and force candidates to Codex only. Exit `64` for invalid receipt and `78` for an already claimed receipt.

- [x] **Step 3: Run focused GREEN and shell syntax**

Run the model-runner unittest and `bash -n`. Verify ordinary calls capture Terra, valid Sol captures Sol once, and replay does not increase fake provider calls.

- [x] **Step 4: Run real non-publishing Sol E2E**

Create one temporary valid `quality_sample` receipt and call the real runner in judge mode. Require output, provider success, claim hash, and a replay exit `78` without a second success log.

- [x] **Step 5: Run full regression delta**

Run the full repository suite and prove the existing unrelated 32-file failure set does not grow.

- [x] **Step 6: Promote, update receipts, and push**

Commit/push feature runtime, promote the exact commit to the live checkout, rerun focused contracts, update the Writer SSOT privately, commit/push both SSOT remotes, and report only a natural-language brief to the user.
