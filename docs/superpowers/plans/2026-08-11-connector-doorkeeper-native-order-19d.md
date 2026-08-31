# Connector Doorkeeper native provider order 19D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and test-driven-development. Luna writes production/tests; Sol reviews and verifies.

**Goal:** official bounded native wakeのprovider順を`Luma → Connpass → Peatix → Meetup → Doorkeeper`へ拡張する。

**Architecture:** `skills/connector/native-pass.js`の既存frozen provider arrayへexact `doorkeeper`を末尾追加するだけ。factory/router/workflow/auditはreview済み既存実装を使用する。Harness allowlistは次B4まで変更せず、scheduleはunloadedを維持する。

**Tech Stack:** Node.js CommonJS、`node:test`、既存native entrypoint contract。

## Global Constraints

- 変更は`skills/connector/native-pass.js`と`skills/connector/test/native-entrypoint.test.js`の2 filesだけ。production 1 LOC、test 2〜10 LOC。
- provider orderはexact `['luma','connpass','peatix','meetup','doorkeeper']`。既存順序を変更せず末尾追加のみ。
- max failures 3、max wake 600000、max agent steps 10、state/provider cursor/privacy境界は変更しない。
- Harness allowlist、router/factory/workflow/audit/operations/runner/evidence/schedule/browser/live stateは変更しない。
- scheduleは4 labels UNLOADED。official wakeはこのslice中に起動しない。
- private identity/profile値をwake inputへ追加しない。

---

### Task 1: Append Doorkeeper to the official provider list

**Files:**
- Modify: `skills/connector/native-pass.js`
- Modify: `skills/connector/test/native-entrypoint.test.js`

- [x] **Step 1: Write RED assertions**

  Update the existing observable native-pass tests to require exact five-provider order both for injected dependencies and production factory boundary. Preserve assertions that private profile values do not enter wake input.

- [x] **Step 2: Run RED**

  ```bash
  cd apps/mr-bot
  node --test ../../skills/connector/test/native-entrypoint.test.js
  ```

  Expected: only exact provider-order assertions fail because Doorkeeper is absent.

- [x] **Step 3: Implement one-line provider append**

  Append exact string `doorkeeper` after `meetup` in `DEFAULT_PROVIDERS`. Do not change any other production symbol.

- [x] **Step 4: Run GREEN and adjacent checks**

  ```bash
  cd apps/mr-bot
  node --test ../../skills/connector/test/native-entrypoint.test.js
  node --test lib/connector-minimal-production.test.js lib/connector-minimal-runner.test.js
  node --check ../../skills/connector/native-pass.js
  git diff --check
  ```

- [x] **Step 5: Self-review and commit**

  Verify exact 2-file ownership, exact order, unchanged safety budgets/private boundary, and no live/schedule effects. Commit without amending and push the task branch.

## Plan Self-Review

- Ponytail: one existing frozen array and existing assertions only; no new abstraction.
- Scope: 2 files, production 1 LOC.
- Safety: schedule remains unloaded and Harness B4 is still pending, so no official wake is executed until the next slice is reviewed.

## Result

- Luna changed the three observable exact-order assertions first: RED was 5/8 with only old four-provider order mismatches. Appending one `doorkeeper` element produced GREEN 8/8; production plus runner stayed 55/55 PASS.
- Production behavior changed by one provider-array element only. Budgets `3 / 600000 / 10` and the factory-only private profile boundary remain unchanged.
- Fresh Sol review returned spec PASS / quality SHIP with no findings. Independent Sol verification repeated 8/8 and 55/55 plus exact order/budgets, syntax, diff, ownership, and four-label UNLOADED checks.
- Reviewed commit `75d48f2e3` is pushed and fast-forwarded into `feature/connector-native-completion`. No official wake ran; Harness support remains the next slice.
