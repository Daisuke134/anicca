# O1B-15 Talk Application Transition Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 登壇応募の状態変更をsource-bound immutable ledgerへappendし、同一transactionでcurrent stateへ投影する。

**Architecture:** Geminiはuntrusted sourceから状態観測を判断する。deterministic validatorとPostgreSQL triggerはstate graph、tenant、時刻、証拠参照、原子性、不変性だけを強制する。

**Tech Stack:** Node.js CommonJS、Gemini structured output、PostgreSQL 18、`node:test`。

## Global Constraints

- 一般参加entityへtalk transitionを接続しない。
- 意味判断をregex、keyword、固定if-else fallbackで実装しない。
- raw mail body、氏名、email、電話、secret、ticket URL、QR bytesをledgerへ保存しない。
- 現在の実talk stateをfixture検証のために変更しない。
- userの既存dirty crypto/handoff filesへ触れない。

---

### Task 1: Source-bound transition observation

**Files:**
- Create: `apps/life-manager/lib/talk-application-transition.js`
- Create: `apps/life-manager/lib/talk-application-transition.test.js`
- Modify: `apps/life-manager/package.json`

**Interfaces:**
- Consumes: `{currentState,observedAt,now,sourceText,sourceRefs}`とGemini decision
- Produces: `inferTalkApplicationTransition(input,deps)`、`validateTalkApplicationTransition(value,input)`

- [ ] **Step 1: RED testを書く**

canonical graph、source excerpt、future timestamp、source ref subset、secret拒否、model failure no-fallbackを固定する。

- [ ] **Step 2: REDを確認する**

Run: `node --test lib/talk-application-transition.test.js`
Expected: module path不存在でFAIL。

- [ ] **Step 3: minimal implementationを書く**

Gemini response schemaは`to_state/evidence_excerpt/reason/source_refs`。validatorはtrusted current stateとobserved timeを合成し、in-process provenanceを付ける。

- [ ] **Step 4: GREENを確認する**

Run: `node --test lib/talk-application-transition.test.js`
Expected: 全件PASS。

- [ ] **Step 5: commitする**

```bash
git add apps/life-manager/lib/talk-application-transition.js apps/life-manager/lib/talk-application-transition.test.js apps/life-manager/package.json
git commit -m "feat(connector): validate talk application transitions"
```

### Task 2: Immutable transition store and migration

**Files:**
- Create: `apps/life-manager/lib/talk-application-transition-store.js`
- Create: `apps/life-manager/lib/talk-application-transition-store.test.js`
- Create: `apps/life-manager/migrations/2026-08-02-lm-talk-application-transitions.sql`
- Modify: `apps/life-manager/package.json`

**Interfaces:**
- Consumes: verified transition、`tenantId`、`participationId`
- Produces: `buildTalkApplicationTransitionRecord(...)`、`createTalkApplicationTransitionStore({connect}).append(record)`

- [ ] **Step 1: RED testを書く**

stable ID、reference-only row、accepted graph、same-client lock、idempotent retry、collision rollback、migration trigger contractを固定する。

- [ ] **Step 2: REDを確認する**

Run: `node --test lib/talk-application-transition-store.test.js`
Expected: module path不存在でFAIL。

- [ ] **Step 3: storeとmigrationを書く**

composite FK、pair CHECK、BEFORE current-state gate、AFTER projection、UPDATE/DELETE拒否、tenant indexを実装する。

- [ ] **Step 4: GREENと全outboundを確認する**

Run: `node --test lib/talk-application-transition-store.test.js && npm run test:outbound`
Expected: 全件PASS。

- [ ] **Step 5: commitする**

```bash
git add apps/life-manager/lib/talk-application-transition-store.js apps/life-manager/lib/talk-application-transition-store.test.js apps/life-manager/migrations/2026-08-02-lm-talk-application-transitions.sql apps/life-manager/package.json
git commit -m "feat(connector): persist talk application transitions"
```

### Task 3: Runtime DB proof, evidence, and master spec

**Files:**
- Create: `docs/evidence/outbound/2026-08-02-o1b15-live-talk-transition-ledger.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

**Interfaces:**
- Consumes: production migration/store contract
- Produces: rollback済みlive DB evidenceと未変更real talk evidence

- [ ] **Step 1: migrationを実runtime DBへ適用する**

Run: `docker exec -i life-manager-local-postgres-1 psql -v ON_ERROR_STOP=1 -U life_manager -d life_manager < apps/life-manager/migrations/2026-08-02-lm-talk-application-transitions.sql`

- [ ] **Step 2: transaction fixtureを実行する**

5段階append、parent projection、terminal transition拒否、UPDATE拒否を確認しROLLBACKする。

- [ ] **Step 3: real talk非変更を確認する**

`https://luma.com/p9kfepcf`のstateとtransition countを件数だけreadbackする。

- [ ] **Step 4: evidenceとmaster specを更新する**

O1B-15を完了し、次をO1B-16へ更新する。raw ID、本文、secretは書かない。

- [ ] **Step 5: final verification、commit、push**

Run: `npm run test:outbound && git diff --check`
Expected: 全件PASS、origin/mainとHEAD一致、unrelated dirty 2件だけ残る。
