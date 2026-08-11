# Connector Doorkeeper Browser Harness core 19D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and test-driven-development. Luna writes production/tests; Sol reviews and verifies.

**Goal:** Browser Harnessがexact Doorkeeper candidateの最終`申し込む`submitを一度だけ実行し、parent readbackで`registered`を確認するか`effect_unknown`で停止できるprovider coreを追加する。

**Architecture:** existing Peatix/Connpass final-effect latchをcopy-tweakする。DoorkeeperをHarness registryへ追加し、exact candidate ref/canonical current page、single submittable exact-label buttonを検証してからclickとbounded readbackを結合する。default DOM modal trigger/visibilityは次B4b、factory注入はB4cまで変更しない。

**Tech Stack:** Node.js CommonJS、`node:test`、既存Browser Harness adapter/readback latch。

## Global Constraints

- 変更は`apps/life-manager/lib/connector-production-browser-harness.js`とmatching testの2 filesだけ。production約25〜50 LOC、test約40〜80 LOC。
- exact provider `doorkeeper`、event ref `doorkeeper-event://event/<positive-id>`、canonical current page `https://<lowercase-group>.doorkeeper.jp/events/<same-id>`。
- final controlはvisible observation内のsingle `button`, exact label `申し込む`, `submittable: true`だけ。
- click前にcandidate/current URL/control/readProviderStateが曖昧ならaction 0でfail closed。
- click成功・throw・return failureのいずれでもparent readbackを最大30秒だけpollし、`registered`ならsuccess、未確認なら`effect_unknown`。同candidateのsubmitは1回だけ。
- `pending`はDoorkeeper completionに数えない。Doorkeeper workflowのreadback contractは`registered|absent|unavailable`。
- existing provider behavior、DOM selector/visibility、modal trigger、factory、router、workflow、native、operations、runner、evidence、schedule/live stateは変更しない。
- official wakeは実行しない。4 labels UNLOADEDを維持する。

---

### Task 1: Add Doorkeeper final-effect safety to Browser Harness

**Files:**
- Modify: `apps/life-manager/lib/connector-production-browser-harness.js`
- Modify: `apps/life-manager/lib/connector-production-browser-harness.test.js`

- [ ] **Step 1: Write RED behavior tests**

  With injected controls (not default DOM), prove:

  1. exact candidate/current URL plus one submittable exact `申し込む` button clicks once and completes only after Doorkeeper workflow returns `registered`;
  2. wrong event ref, current URL mismatch, duplicate final buttons, non-button/non-submittable/wrong label, or missing workflow produces action 0 and no registered result;
  3. readback that never settles is bounded at 30 seconds, returns `effect_unknown`, and click count remains one;
  4. an ambiguous thrown/failed click still uses readback and never clicks a second time;
  5. Luma/Connpass/Peatix/Meetup tests remain unchanged.

- [ ] **Step 2: Run RED**

  ```bash
  cd apps/life-manager
  node --test lib/connector-production-browser-harness.test.js
  ```

  Expected: new Doorkeeper tests fail because provider/workflow/final latch are absent; existing tests stay green.

- [ ] **Step 3: Implement the minimal provider/latch**

  Add exact Doorkeeper constants/helpers, provider set entry, optional workflow validation/registry, and a Doorkeeper branch in the existing final-effect wait. Reuse `readStateWithinDeadline` and `settleFinalEffect`. Do not touch `inspectPageControls` selector or generic link behavior in this slice.

- [ ] **Step 4: Run GREEN and adjacent checks**

  ```bash
  cd apps/life-manager
  node --test lib/connector-production-browser-harness.test.js
  node --test lib/connector-browser-harness-adapter.test.js lib/connector-doorkeeper-workflow.test.js lib/connector-minimal-production.test.js
  node --check lib/connector-production-browser-harness.js
  git diff --check
  ```

- [ ] **Step 5: Self-review and commit**

  Verify exact 2-file ownership, submit max1, exact identity/control, bounded unknown effect, no default DOM/factory/native/live changes. Commit without amend and push.

## Plan Self-Review

- Ponytail: existing final-effect latch and adapter are reused; no new service/state/cache.
- Scope: provider safety core only. Modal DOM discovery and factory reachability are explicit later slices.
- Safety: native may list Doorkeeper, but factory still does not inject its workflow into Harness and no official wake runs in this slice.
