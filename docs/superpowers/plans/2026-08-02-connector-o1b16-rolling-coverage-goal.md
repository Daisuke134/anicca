# O1B-16 Rolling 21-Day Event Coverage Goal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ユーザーtimezoneの今日〜20日後を毎run再計算し、日別coverageをimmutable snapshotとして保存する。

**Architecture:** Pure builderがlocal calendar datesとtrusted resolved-day evidenceからexactly 21日のsnapshotを作る。PostgreSQL storeはsnapshotをappend-only保存しcurrent viewを提供する。event探索・意味評価・free intervalは後続O1B-17〜24に残す。

**Tech Stack:** Node.js CommonJS、Intl IANA timezone、PostgreSQL 18、`node:test`、既存`gog` Google Calendar OAuth。

## Global Constraints

- Windowは今日を含む21日、つまりtoday〜today+20 local calendar days。
- `now + 24h * n`でlocal dateを生成しない。
- Calendar eventがあるだけで`covered_existing`にしない。
- 「候補がない」を`unavailable`にしない。
- raw Calendar title、location、attendee、emailをsnapshot/evidenceへ保存しない。
- userの既存dirty crypto/handoff filesへ触れない。

---

### Task 1: Pure rolling coverage snapshot

**Files:**
- Create: `apps/life-manager/lib/rolling-event-coverage.js`
- Create: `apps/life-manager/lib/rolling-event-coverage.test.js`
- Modify: `apps/life-manager/package.json`

**Interfaces:**
- Consumes: `{tenantId,timeZone,now,resolvedDays}`
- Produces: `buildRollingEventCoverage(input)`

- [x] **Step 1: RED testを書く**

JST today〜+20、New York DST、翌日slide、default open、resolved evidence、conflict/out-of-window/secret拒否をliteral fixtureで固定する。

- [x] **Step 2: REDを確認する**

Run: `node --test lib/rolling-event-coverage.test.js`
Expected: module path不存在でFAIL。

- [x] **Step 3: minimal implementationを書く**

Intlでlocal todayを得て、date keyをUTC上の暦演算へ写して0〜20日を生成する。snapshot IDはcanonical content hash。

- [x] **Step 4: GREENとoutbound全回帰を確認する**

Run: `node --test lib/rolling-event-coverage.test.js && npm run test:outbound`
Expected: 全件PASS。

- [x] **Step 5: commitする**

```bash
git add apps/life-manager/lib/rolling-event-coverage.js apps/life-manager/lib/rolling-event-coverage.test.js apps/life-manager/package.json
git commit -m "feat(connector): build rolling event coverage"
```

### Task 2: Immutable snapshot store

**Files:**
- Create: `apps/life-manager/lib/rolling-event-coverage-store.js`
- Create: `apps/life-manager/lib/rolling-event-coverage-store.test.js`
- Create: `apps/life-manager/migrations/2026-08-02-lm-event-coverage-snapshots.sql`
- Modify: `apps/life-manager/package.json`

**Interfaces:**
- Consumes: in-process verified coverage snapshot
- Produces: `createRollingEventCoverageStore({connect}).save(snapshot)`

- [ ] **Step 1: RED testを書く**

verified provenance、tenant-bound insert、idempotent retry、collision rollback、immutable trigger、current viewを固定する。

- [ ] **Step 2: REDを確認する**

Run: `node --test lib/rolling-event-coverage-store.test.js`
Expected: module path不存在でFAIL。

- [ ] **Step 3: storeとmigrationを書く**

reference-only JSON、date/count constraints、UPDATE/DELETE拒否、tenant latest viewを実装する。

- [ ] **Step 4: GREENとoutbound全回帰を確認する**

Run: `node --test lib/rolling-event-coverage-store.test.js && npm run test:outbound`
Expected: 全件PASS。

- [ ] **Step 5: commitする**

```bash
git add apps/life-manager/lib/rolling-event-coverage-store.js apps/life-manager/lib/rolling-event-coverage-store.test.js apps/life-manager/migrations/2026-08-02-lm-event-coverage-snapshots.sql apps/life-manager/package.json
git commit -m "feat(connector): persist rolling event coverage"
```

### Task 3: Live Calendar read, DB proof, evidence, master spec

**Files:**
- Create: `docs/evidence/outbound/2026-08-02-o1b16-live-rolling-coverage.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

**Interfaces:**
- Consumes: current `gog` OAuth、production migration/store contract
- Produces: PII-free Calendar count、live coverage snapshot readback、O1B17 open dates

- [ ] **Step 1: migrationを実runtime DBへ適用する**

Run migration against fixed `life-manager-local-postgres-1/life_manager` with `ON_ERROR_STOP=1`。

- [ ] **Step 2: Google Calendarをread-only取得する**

今日〜20日後を`--all --all-pages`で取得し、stdoutへraw eventを出さず、countだけ保持する。

- [ ] **Step 3: initial open snapshotを保存・再読出しする**

O1B23前なのでCalendar eventをresolvedへ推測せず、21 open daysを実storeへ保存しcurrent view/hashを確認する。

- [ ] **Step 4: evidence/specを更新する**

O1B-16を完了し、次をO1B-17へ更新する。

- [ ] **Step 5: final verification、commit、push**

Run: focused tests、`npm run test:outbound`、DB readback、`git diff --check`。
Expected: origin/mainとHEAD一致、unrelated dirty 2件だけ残る。
