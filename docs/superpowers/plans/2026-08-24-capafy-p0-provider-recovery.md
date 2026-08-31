# Capafy P0 Provider Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the Capafy hourly owner through Codex account 2 direct authentication, then prevent a provider quota incident from becoming a five-minute restart storm.

**Architecture:** Keep launchd as the only execution owner. Codex uses the existing private `~/.codex-acct2/auth.json` through the repo-owned runner without the local proxy override. The healthcheck reads the latest runner classification and records a durable quota backoff instead of kickstarting the hourly owner.

**Tech Stack:** Python `unittest`, Bash, launchd, JSON runner receipts, Codex CLI.

**Spec:** `specs/29-CAPAFY-10K-MRR-CLOSED-LOOP.md` P0

## Global Constraints

- Only P0 is active; do not publish a Skill or Instagram post.
- Never commit credentials, tokens, account identifiers, mutable state, or provider output.
- One external side effect owner remains `ai.anicca.capafy-loop-daily`.
- A provider failure must not write the healthy-pass marker.
- Account 2 direct routing is accepted only after a real provider probe and production runner readback.
- Quota backoff acceptance requires Capafy writes `0`, Instagram writes `0`, and five-minute kickstarts `0`.

---

### Task 1: Route Codex through account 2 directly

**Files:**
- Create: `runtime/agent-runner/tests/test_account2_direct_routing.py`
- Modify: `runtime/agent-runner/config.json`

**Interfaces:**
- Consumes: provider config field `auth_file` and `provider_process_env()`.
- Produces: Codex candidate environment whose `CODEX_HOME/auth.json` resolves to `~/.codex-acct2/auth.json`, with no configured `local_proxy` model provider.

- [x] **Step 1: Write the failing routing contract test**

Load `runtime/agent-runner/config.json` and assert that the Codex provider uses `~/.codex-acct2/auth.json` and does not define `model_provider` or `model_providers`.

- [x] **Step 2: Run the test and verify RED**

Run: `python3 runtime/agent-runner/tests/test_account2_direct_routing.py -v`

Expected: FAIL because `model_provider` is `local_proxy`.

- [x] **Step 3: Remove only the local proxy override**

Delete `model_provider` and `model_providers` from the Codex provider row. Preserve `auth_file`, automation isolation, capability declarations, task classes, and Claude fallback.

- [x] **Step 4: Verify GREEN and focused runner regression**

Run:

```bash
python3 runtime/agent-runner/tests/test_account2_direct_routing.py -v
python3 -m unittest discover -s runtime/agent-runner/tests -p 'test_*.py'
```

Expected: all tests PASS.

- [x] **Step 5: Verify a direct account 2 provider probe**

Run one ephemeral, read-only Codex request with `CODEX_HOME=~/.codex-acct2`, no proxy environment, and require exact output `ACCOUNT2_OK`.

- [x] **Step 6: Commit Task 1**

```bash
git add runtime/agent-runner/config.json runtime/agent-runner/tests/test_account2_direct_routing.py
git commit -m "fix(capafy): route Codex through account 2"
```

### Task 2: Stop quota-driven healthcheck kickstarts

**Files:**
- Create: `skills/self/capafy-loop/test_capafy_healthcheck_quota_backoff.py`
- Modify: `skills/self/capafy-loop/capafy-loop-healthcheck.sh`

**Interfaces:**
- Consumes: latest `capafy-marketplace/*/summary.json` and `attempts.jsonl`.
- Produces: private `capafy-provider-backoff.json` with `error_class`, `observed_at`, and `next_eligible_at`; no kickstart while the latest terminal is all `transient_quota`.

- [x] **Step 1: Write the failing stale-marker plus quota test**

Create a temporary Mr.bot state tree, a stale healthy marker, a failed summary with only `transient_quota` attempts, and a fake `launchctl` that records calls. Assert exit `0`, zero `kickstart`, and a future `next_eligible_at`.

- [x] **Step 2: Run the test and verify RED**

Run: `python3 skills/self/capafy-loop/test_capafy_healthcheck_quota_backoff.py -v`

Expected: FAIL because the current healthcheck calls `launchctl kickstart` and writes no backoff receipt.

- [x] **Step 3: Add the minimal quota classification guard**

Before stale-marker kickstart, inspect the latest completed runner receipt. If every failed attempt is `transient_quota`, atomically write a mode-0600 backoff receipt for the next hourly boundary, log the no-write terminal, and exit `0`. Missing, malformed, mixed, or non-quota evidence keeps the existing fail-closed behavior.

- [x] **Step 4: Verify GREEN and Capafy regression**

Run:

```bash
python3 skills/self/capafy-loop/test_capafy_healthcheck_quota_backoff.py -v
bash skills/self/capafy-loop/test-loop.sh
bash -n skills/self/capafy-loop/capafy-loop-healthcheck.sh
```

- [x] **Step 5: Install and read back one production owner transition**

Use `bin/launchctl-safe` for the exact Capafy labels. Verify the hourly owner uses the pushed Mr.bot source, the provider receipt selects Codex account 2 direct, no Capafy/Instagram write occurs during recovery, and three consecutive five-minute healthchecks add zero kickstarts.

- [x] **Step 6: Synchronize the spec and push**

Mark P0 complete only with the production receipts above, move P1 to active, commit the code/test/spec, push `main`, and verify the remote spec readback.
