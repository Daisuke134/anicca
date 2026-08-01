# Connector O1B-01 Remove Fake Success Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `outbound.event.apply`がhandlerの自己申告だけでcompletedになれる経路を削除し、実E1/E2/E3 verifier由来のreceiptだけを成功として保存する。

**Architecture:** `verifyOutboundEvidence()`がこのprocessで生成したverified objectをprivate provenance setへ登録する。新しいsuccess receipt builderはそのobject identityだけを受け入れ、runtime workerは`outbound.event.apply`完了前にbuilder由来receiptを検証する。bare success、JSON copy、別attempt、missing tierは完了させず`unknownEffect=true`で既存reconciliationへ渡す。

**Tech Stack:** Node.js 20、node:test、既存runtime job protocol。

## Global Constraints

- O1B-01だけを実装し、URL修正やLuma browser adapterを先取りしない。
- deterministic evidence provenanceとbookkeepingだけをcodeに置き、event選定・page判断はagentに残す。
- external effect後に証拠が成立しない場合はretry可能な通常失敗にしない。
- 正本specをRED、GREEN、commit、pushごとに更新する。

---

### Task 1: Verifier provenance and success receipt

**Files:**
- Modify: `apps/life-manager/lib/outbound-evidence.js`
- Create: `apps/life-manager/lib/outbound-success.js`
- Create: `apps/life-manager/lib/outbound-success.test.js`
- Modify: `apps/life-manager/package.json`

**Interfaces:**
- Consumes: `verifyOutboundEvidence(input, dependencies)` result。
- Produces: `buildVerifiedOutboundReceipt(input, evidence)`、`assertVerifiedOutboundReceipt(receipt, job)`。

- [x] Write tests proving verified evidence is accepted while failed evidence, plain object copies, JSON roundtrips, and mismatched attempts are rejected.
- [x] Run the tests and observe RED because the success module/provenance API does not exist.
- [x] Implement the private provenance set and minimal receipt builder/assertion.
- [x] Run outbound tests and observe GREEN.
- [ ] Commit and push.

### Task 2: Runtime completion gate

**Files:**
- Modify: `apps/life-manager/scripts/runtime-up.js`
- Modify: `apps/life-manager/scripts/runtime-up.test.js`

**Interfaces:**
- Consumes: `assertVerifiedOutboundReceipt(receipt, job)`。
- Produces: completed receipt only for verified outbound application; otherwise failed receipt with `unknownEffect=true`。

- [x] Add a failing test where an outbound handler returns bare `{status:"success"}` and assert `completeJob` is never called.
- [x] Add a passing test using a real verifier-derived receipt for the exact tenant/job/attempt.
- [x] Implement the capability-specific completion gate immediately before `completeJob`.
- [x] Run outbound and runtime worker regression tests.
- [ ] Commit and push.

### Task 3: Evidence and canonical spec

**Files:**
- Create: `docs/evidence/outbound/2026-08-01-o1b01-fake-success-gate.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

- [ ] Record RED/GREEN counts, rejected fake cases, implementation commits, and claim boundary.
- [ ] Run fresh tests, JSON validation, git diff check, and local/remote equality.
- [ ] Mark O1B-01 complete only after every verification succeeds; leave O1B-02 untouched.
- [ ] Commit and push.
