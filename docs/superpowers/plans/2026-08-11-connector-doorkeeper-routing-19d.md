# Connector Doorkeeper production routing 19D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and test-driven-development. Production code and tests are owned by Luna; Sol reviews and verifies.

**Goal:** reviewed Doorkeeper workflowを既存production provider router/factoryへ追加し、同じowned page・Calendar・cache/direct/fallback/readback契約で選択可能にする。

**Architecture:** `connector-minimal-production.js`の既存provider mapだけをcopy-tweakする。新service、API client、DB、queue、browser rail、state schemaは作らない。このsliceではnative provider順、Harness内部provider allowlist、audit writer、schedule、live stateを変更しないため、production wakeはまだDoorkeeperを呼ばない。

**Tech Stack:** Node.js CommonJS、`node:test`、既存provider workflow/router interface。

## Global Constraints

- 変更は次の2 filesだけ。production約15〜30 LOC、test約25〜50 LOCをsoft targetにする。
- Connector endpointはexact `http://127.0.0.1:9222`。browser/session/target/pageを新規作成・closeしない。
- providerはexact `doorkeeper`、workflow versionはexact `doorkeeper_registration_v1`。
- Doorkeeper workflowは既存`createDoorkeeperScriptFirstWorkflow`を直接再利用する。
- audit callbackは後続operations sliceまでoptional no-op。native orderとHarness allowlistは後続sliceまで変更しない。
- credential、cookie、email、氏名、private Calendar dataをfixture/outputへ置かない。
- scheduleはunloaded。browser、Calendar、Telegram、provider、stateへの外部作用0。

## Grounded Contract

- `docs/superpowers/plans/2026-08-11-connector-doorkeeper-discovery-19d.md`のreview済みResultを入力とする。Doorkeeper workflowは`discoverCandidates({ page, calendar })`、`runDirectAction({ page, candidate })`、`readProviderState({ page, candidate })`を提供し、direct actionはこの時点ではsafe failureである。
- 既存`createProductionProviderRouter`はLuma/Connpass/Peatix/Meetupを同じ`selected()`境界からcache/direct/fallback/readbackへ渡す。この既存mapを拡張するだけにする。

---

### Task 1: Route Doorkeeper through the production factory

**Files:**
- Modify: `apps/life-manager/lib/connector-minimal-production.js`
- Modify: `apps/life-manager/lib/connector-minimal-production.test.js`

- [ ] **Step 1: Write RED routing tests**

  Add observable tests proving:

  1. `createProductionProviderRouter` routes exact provider `doorkeeper` to the injected Doorkeeper workflow for discovery, cache replay, direct action, fallback, readback, and repaired action save.
  2. discovery receives the exact same `page` and `calendar` objects.
  3. cache replay/save use exact `doorkeeper_registration_v1`, existing `registration_page_v1`, and `registered_or_pending`.
  4. candidate/private fixture values are not copied into cache metadata beyond the existing router contract.
  5. official factory uses an injected Doorkeeper workflow and passes it to the router without creating a browser/session/target/page.

- [ ] **Step 2: Run RED**

  ```bash
  cd apps/life-manager
  node --test lib/connector-minimal-production.test.js
  ```

  Expected: new Doorkeeper cases fail because provider selection/factory wiring is absent. Existing cases stay green.

- [ ] **Step 3: Implement the minimal route**

  In `connector-minimal-production.js` only:

  - import `createDoorkeeperScriptFirstWorkflow`;
  - add `DOORKEEPER_WORKFLOW_VERSION = "doorkeeper_registration_v1"`;
  - accept optional `doorkeeperWorkflow` with the same three-method validation as optional Peatix/Meetup;
  - extend `selected()` exact allowlist/map/version for `doorkeeper` without changing existing provider ordering or behavior;
  - factory-create the workflow with `now` and `operations.recordDoorkeeperDiscoveryAudit || (() => {})`;
  - pass it to `createProductionProviderRouter` only. Do not pass it into Browser Harness in this slice.

- [ ] **Step 4: Run GREEN and focused adjacent checks**

  ```bash
  cd apps/life-manager
  node --test lib/connector-minimal-production.test.js
  node --test lib/connector-doorkeeper-workflow.test.js lib/connector-minimal-runner.test.js
  node --check lib/connector-minimal-production.js
  git diff --check
  ```

- [ ] **Step 5: Self-review and commit**

  Verify exact 2-file ownership, no Harness/native/operations/schedule changes, no external writes, and no provider behavior regression. Commit without amending prior commits.

## Plan Self-Review

- Ponytail: one existing map/factory seam is reused; no abstraction or dependency is added.
- Scope: 2 files, expected total delta under 80 LOC. Native reachability and form action remain explicitly deferred.
- Safety: this slice cannot run Doorkeeper in an official wake because native order remains unchanged; it only makes the reviewed workflow selectable at the production dependency boundary.
