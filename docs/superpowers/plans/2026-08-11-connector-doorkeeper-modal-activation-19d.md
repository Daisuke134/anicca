# Connector Doorkeeper modal activation 19D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and test-driven-development. Luna writes production/tests; Sol reviews and verifies.

**Goal:** Browser Harnessがdefault inspectorのexact Doorkeeper modal triggerを一度だけclickし、required Email fillと最終submitへ同じpage上で進めるようにする。

**Architecture:** reviewed inspectorが返すunique exact trigger `kind: link`をDoorkeeperだけparent-authorized actionとして扱う。既存adapterのmutation dedupeを再利用し、modal trigger signatureとfinal form-submit signatureを明確に分離する。final submitはB4aのexact identity/readback latchをそのまま使う。

**Tech Stack:** Node.js CommonJS、`node:test`、既存Browser Harness adapter/control operator。

## Global Constraints

- 変更は`apps/life-manager/lib/connector-production-browser-harness.js`とmatching testの2 filesだけ。production約20〜40 LOC、test約40〜80 LOC。
- trigger actionはprovider exact `doorkeeper`、valid candidate binding、current URL exact candidate canonical、one control `kind: link`, label exact `申し込む`, submittable false、observation内同条件count 1だけ。
- triggerは既存`ax_click`を使うが外部registration submitではない。signatureはmodal trigger固有で、final `form-submit`と衝突させない。
- same page/pathでtriggerの成功mutationは一度だけ。再選択はDOM action 0。final submit guard/max1と30秒registered-only readbackは維持する。
- arbitrary link、wrong provider/identity/label、duplicate trigger、button pretending triggerはaction 0。
- full injected flowはtrigger click 1、Email fill 1、final submit click 1、registered readbackでcompleted。trigger click後のabsent/unavailableは成功扱いにせず次stepへ進む。
- default inspector、private resolver、factory/router/workflow/native/operations/runner/evidence/schedule/live stateは変更しない。
- official wake 0、4 labels UNLOADED。

---

### Task 1: Activate the exact modal trigger without consuming final submit

**Files:**
- Modify: `apps/life-manager/lib/connector-production-browser-harness.js`
- Modify: `apps/life-manager/lib/connector-production-browser-harness.test.js`

- [x] **Step 1: Write RED action-flow tests**

  With injected observations and parent-owned values, prove:

  1. three-step exact flow: trigger link → required Email fill → single final button; repaired actions preserve all three in order and final state is registered;
  2. trigger and final submit each click exactly once and do not collide in mutation dedupe;
  3. selecting the same successful trigger twice produces no second DOM click, then a valid fill/final submit can still finish within the bounded steps;
  4. arbitrary/wrong-provider/wrong-identity/wrong-label/duplicate trigger/action token fails before link action;
  5. final submit ambiguity remains `effect_unknown` with no retry.

- [x] **Step 2: Run RED**

  ```bash
  cd apps/life-manager
  node --test lib/connector-production-browser-harness.test.js
  ```

- [x] **Step 3: Implement minimal trigger authorization/signature**

  Add a small exact trigger predicate reused by outer `performAction` and adapter signature/latch classification. Do not broaden generic link behavior. Keep final submit identification based on the actual observed button, not merely action purpose.

- [x] **Step 4: Run GREEN and adjacent checks**

  ```bash
  cd apps/life-manager
  node --test lib/connector-production-browser-harness.test.js
  node --test lib/connector-browser-harness-adapter.test.js lib/connector-doorkeeper-workflow.test.js lib/connector-minimal-production.test.js
  node --check lib/connector-production-browser-harness.js
  git diff --check
  ```

- [x] **Step 5: Self-review and commit**

  Verify exact 2-file ownership, generic links unchanged, trigger/final signatures distinct, Submit max1, no factory/native/live effect. Commit without amend and push.

## Plan Self-Review

- Ponytail: no new action engine; one exact predicate and existing dedupe/latch only.
- Scope: modal activation only. Production factory injection remains B4c.
- Safety: no official wake runs and no real provider submit occurs in tests.

## Result

Luna implemented exact Doorkeeper modal-trigger authorization, a distinct modal-trigger mutation signature/latch, and the default proposer path in the two assigned Harness files. The final regression set proves exact trigger → Email fill → one final submit, repeated-trigger action 0, default-proposer selection, semantic duplicate rejection even with an invalid token, and continued generic-link rejection.

Review/self-reviewでdefault proposer omissionとtoken非依存semantic duplicateを検出し、RED後それぞれ`2229bb9b6`、`1b35d4a2f`で修復した。続くfresh Sol reviewは、public `performAction`がcached observationを再利用し、run-local latchを跨いで同page/canonical triggerを2回clickできるImportantを再現した。LunaはDoorkeeperだけをaction直前に再観測し、page＋exact canonical URL単位の成功latchを`bc043cb2c`で追加した。mutation確認用revert `cd82201dd`が一時pushされたため、通常の再適用commit `51656fd5b`で履歴を保ったまま最終状態へ戻した。scoped fresh Sol re-reviewは全finding ADDRESSED、新規breakage 0、SHIP。

Solは最終treeでHarness `74/74`、隣接adapter/workflow/factory `33/33`、syntax、diff、clean worktree、remote equality、変更2 files、4 labels UNLOADEDを独立再検証した。review済み実装はmerge commit `82c36e14d`でstableへ統合した。No official wake、browser action、provider submit、Calendar write、Telegram送信、launchd load。B4c production factory injectionが次slice。
