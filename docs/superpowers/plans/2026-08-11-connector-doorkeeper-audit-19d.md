# Connector Doorkeeper discovery audit 19D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and test-driven-development. Luna writes production/tests; Sol reviews and verifies.

**Goal:** Doorkeeper workflowのprivacy-safe five-count discovery auditを既存operations stateへmode `0600`でappend-only保存する。

**Architecture:** `connector-minimal-operations.js`の既存provider audit writerをcopy-tweakし、Doorkeeper固有の新5キー用validatorと`doorkeeper-discovery-audits.jsonl` writerだけを追加する。既存Luma/Connpass/Peatix/Meetupの旧5キーvalidator・files・rowsは変更しない。

**Tech Stack:** Node.js CommonJS、`node:test`、既存atomic append/mode contract。

## Global Constraints

- 変更は`apps/mr-bot/lib/connector-minimal-operations.js`とmatching testの2 filesだけ。production約15〜30 LOC、test約25〜50 LOC。
- Doorkeeper input keysはexact `discovered_count`, `within_window_count`, `eligible_count`, `calendar_free_count`, `selected_count`。
- 全countはinteger 0〜500、`selected <= calendar_free <= eligible <= within_window <= discovered`。
- persisted rowはschema version、wake ID、exact recorded time、上記5 aggregate countsだけ。URL、event ref、title、profile、ticket、auth、private Calendar dataは0。
- invalid inputはthrowし、file append 0。valid fileはexact mode `0600`。
- existing `safeDiscoveryAudit`と4provider writer/file/outputはbyte behaviorを変えない。
- router、workflow、Harness、native order、runner、evidence、schedule、browser/live state、external servicesは変更しない。

---

### Task 1: Persist Doorkeeper aggregate audits

**Files:**
- Modify: `apps/mr-bot/lib/connector-minimal-operations.js`
- Modify: `apps/mr-bot/lib/connector-minimal-operations.test.js`

- [x] **Step 1: Write RED tests**

  Add one focused test that:

  1. calls `recordDoorkeeperDiscoveryAudit` with `100/12/8/0/0`;
  2. reads exact `doorkeeper-discovery-audits.jsonl` and asserts one row, exact keys, values, wake ID, timestamp, and mode `0600`;
  3. proves serialized row contains no URL/private fixture values;
  4. attempts non-monotonic, extra-key, missing-key, fractional, negative, >500, string, array/null inputs and proves rejection plus line count remains one.

- [x] **Step 2: Run RED**

  ```bash
  cd apps/mr-bot
  node --test lib/connector-minimal-operations.test.js
  ```

  Expected: new test fails because the method/file do not exist; existing operations tests remain green.

- [x] **Step 3: Implement the minimal validator/writer**

  Add a separate Doorkeeper validator, the exact file path, one writer method, and frozen export. Reuse existing `append`, wake ID, exact time, schema, and mode behavior. Do not generalize or migrate existing providers.

- [x] **Step 4: Run GREEN and adjacent checks**

  ```bash
  cd apps/mr-bot
  node --test lib/connector-minimal-operations.test.js
  node --test lib/connector-minimal-production.test.js lib/connector-doorkeeper-workflow.test.js
  node --check lib/connector-minimal-operations.js
  git diff --check
  ```

- [x] **Step 5: Self-review and commit**

  Verify exact 2-file ownership, no private values, invalid append 0, unchanged existing provider behavior, and zero external effects. Commit without amending prior history and push the task branch.

## Plan Self-Review

- Ponytail: reuses the existing append and per-provider file pattern; no schema migration or abstraction.
- Scope: 2 files and one user-observable capability—durable Doorkeeper discovery audit.
- Safety: official native order remains unchanged, so no live wake/provider effect occurs in this slice.

## Result

- Luna observed RED 9/10 because `recordDoorkeeperDiscoveryAudit` was absent, then GREEN 10/10. Production plus Doorkeeper workflow remained 29/29 PASS.
- The exact five-key validator/writer persists only schema, wake, recorded time, and aggregate counts to `doorkeeper-discovery-audits.jsonl` with mode `0600`; invalid matrix appends zero rows.
- Fresh Sol review returned spec PASS / quality SHIP, Critical 0, Important 0, and one non-blocking Minor suggesting optional per-inequality tests. Independent Sol verification repeated 10/10 and 29/29 plus syntax, diff, ownership, and four-label UNLOADED checks.
- Reviewed commit `c7269d886` is pushed and fast-forwarded into `feature/connector-native-completion`. Native order remains unchanged, so this slice has no official-wake reachability or external effect.
