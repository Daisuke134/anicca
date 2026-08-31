# Connector Doorkeeper default DOM inspection 19D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and test-driven-development. Luna writes production/tests; Sol reviews and verifies.

**Goal:** default Browser Harness inspectorがDoorkeeperのexact申込triggerと、modal open後のvisible required email／single submitだけを安全controlとして返す。

**Architecture:** existing `inspectPageControls`のselector/DOM normalizerへDoorkeeper固有の厳格条件だけを追加する。action/click、duplicate mutation latch、factory injectionは後続sliceへ残す。このsliceはDOM observationだけで外部作用0。

**Tech Stack:** Node.js CommonJS、`node:test`、Playwright-compatible locator evaluation。

## Measured DOM Contract

2026-08-11にshared `:9222`へ診断pageを一枚だけ作成し、`https://techgym.doorkeeper.jp/events/198719`で実測後closeを確認した。

- exact visible trigger: `a[href="#new_registration_modal"]`, text `申し込む`, count 1。
- modal closed: `input#event_registration_email[type=email][name="event_registration[email]"][required]`と`input[type=submit][name=commit][value="申し込む"]`は同じ`form#new_event_registration`内でhidden。
- modal open: 上記emailとsubmitだけがvisible。emailはrequired、submitはdisabled false。
- 診断ではfill/submit 0、target IDはclose後absent。

## Global Constraints

- 変更は`apps/mr-bot/lib/connector-production-browser-harness.js`とmatching testの2 filesだけ。production約20〜45 LOC、test約40〜80 LOC。
- selector追加はexact `a[href="#new_registration_modal"]`だけ。一般`a`や広いhref selectorを追加しない。
- Doorkeeper page identityはexact provider、lowercase non-www group、positive event ID、context event ID完全一致。
- modal closed時のhidden email/submitはcontrol 0。Doorkeeperでは全controlにancestor/style/box visibilityを要求する。
- triggerはexact page上のvisible exact label/hrefが1件だけの時に`kind: link`, `submittable: false`で返す。duplicate/wrong label/wrong href/wrong pageはtrigger 0。
- exact email inputだけpublic label `Email`, required true。raw field name/id/value/private dataをoutputへ出さない。
- modal submitはrequired emailがrepresentableかつcomplete、same exact form、visible single submitの時だけbutton/submittable true。email未入力時はsubmit不可。
- link activation、final-effect core、factory/router/workflow/native/operations/runner/evidence/schedule/live stateは変更しない。
- official wake 0、4 labels UNLOADED。

---

### Task 1: Normalize the measured Doorkeeper modal DOM

**Files:**
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.js`
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.test.js`

- [x] **Step 1: Write RED inspector tests**

  Use literal fake DOM nodes matching the measured attributes and visibility. Prove:

  1. modal closed returns only one exact trigger; hidden email/submit are absent;
  2. modal open with empty email returns trigger + required `Email`, but no submittable submit;
  3. after email completion, exact same-form single submit becomes `button`, label `申し込む`, submittable true;
  4. duplicate trigger, wrong href/label/provider/page/event ID, www/uppercase/query/fragment/port/credentials, hidden/detached/CSS-hidden/zero-size trigger all expose no trigger;
  5. duplicate submit, wrong form, hidden submit, unlabeled/ambiguous required answer expose no submittable submit;
  6. output contains no raw email/name/value/private fixture.

- [x] **Step 2: Run RED**

  ```bash
  cd apps/mr-bot
  node --test lib/connector-production-browser-harness.test.js
  ```

- [x] **Step 3: Implement the minimal Doorkeeper inspector branch**

  Extend only selector and in-page normalization. Reuse `visibleOf`, `requiredOf`, `completedOf`, form binding, and submit count. Add exact known-page/trigger/email predicates; do not implement link clicks.

- [x] **Step 4: Run GREEN and adjacent checks**

  ```bash
  cd apps/mr-bot
  node --test lib/connector-production-browser-harness.test.js
  node --test lib/connector-browser-harness-adapter.test.js lib/connector-doorkeeper-workflow.test.js lib/connector-minimal-production.test.js
  node --check lib/connector-production-browser-harness.js
  git diff --check
  ```

- [x] **Step 5: Self-review and commit**

  Verify exact 2-file ownership, observation-only, no generic selector expansion, hidden/private output 0, existing providers unchanged. Commit without amend and push.

## Plan Self-Review

- Ponytail: measured DOM and existing inspector primitives only; no new browser/service/state abstraction.
- Scope: DOM observation only. Activation and factory reachability remain later slices.
- Safety: no click/fill/submit or live wake is introduced.

## Result

- Luna added four measured-DOM tests after the 61-test baseline; RED was 61/65 and initial GREEN 65/65. Adjacent remained 33/33.
- Fresh Sol review found three Important evidence/compatibility gaps. Round 1 made the selector provider-specific, preserved the exact non-Doorkeeper selector, isolated wrong-form from duplicate submit, and covered ancestor visibility. Round 2 split trigger/email/submit ancestor cases so no trigger early-return masks field/submit behavior.
- Final focused result is 67/67; adjacent is 33/33. Final fresh Sol re-review returned spec PASS / quality SHIP with no findings. Independent Sol verification repeated all results plus syntax, diff, exact ownership, and four-label UNLOADED checks.
- Reviewed commits `f52333fbd`, `7a072341d`, and test-only `7221adf94` are pushed and fast-forwarded into `feature/connector-native-completion`. The bounded identity/visibility matrix accounts for the larger test delta. No link activation, fill, submit, factory, native, or live behavior changed.
