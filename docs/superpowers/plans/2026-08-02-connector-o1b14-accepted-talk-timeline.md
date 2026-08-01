# Accepted Talk Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** accepted talkのslide deadline、appearance、venue、QR、organizer follow-upをsource-bound immutable timelineとして追跡する。

**Architecture:** Geminiはuntrusted acceptance/event textから不足情報とfollow-upを判断する。deterministic validatorはverified accepted state、timestamp ordering、reference subset、secret境界を検証し、PostgreSQLへimmutable snapshotを保存する。

**Tech Stack:** Node.js CommonJS、Gemini structured output、PostgreSQL、`node:test`、既存`lm_event_participations`。

## Global Constraints

- 一般参加entityへtalk timelineを接続しない。
- DBへraw mail body、氏名、email、QR bytes、cookie、API keyを保存しない。
- 意味判断をregex/keyword fallbackで実装しない。
- 現在の実talkは未採択なのでacceptedを捏造しない。
- userの既存dirty crypto/handoff filesへ触れない。

---

### Task 1: Timeline decisionとvalidator

**Files:**
- Create: `apps/life-manager/lib/accepted-talk-timeline.js`
- Create: `apps/life-manager/lib/accepted-talk-timeline.test.js`
- Modify: `apps/life-manager/package.json`

**Interfaces:**
- Consumes: `{acceptedAt,eventStartAt,eventEndAt,ticketRef,sourceRefs,sourceText,now}`
- Produces: `inferAcceptedTalkTimeline(input, deps)`、`validateAcceptedTalkTimeline(value, input)`

- [x] **Step 1: RED testを書く**

`known/pending`、timestamp ordering、source ref subset、ticket ref、secret拒否、model failure no-fallbackをliteral fixtureで固定する。

- [x] **Step 2: REDを確認する**

Run: `node --test lib/accepted-talk-timeline.test.js`
Expected: `Cannot find module './accepted-talk-timeline.js'`

- [x] **Step 3: minimal implementationを書く**

Gemini response schemaはslide、venue、follow-upだけをmodel出力にし、accepted/event/ticketはtrusted inputから合成する。

- [x] **Step 4: GREENを確認する**

Run: `node --test lib/accepted-talk-timeline.test.js`
Expected: 全件PASS。

- [x] **Step 5: commitする**

```bash
git add apps/life-manager/lib/accepted-talk-timeline.js apps/life-manager/lib/accepted-talk-timeline.test.js apps/life-manager/package.json
git commit -m "feat(connector): validate accepted talk timeline"
```

### Task 2: Immutable PostgreSQL snapshot store

**Files:**
- Create: `apps/life-manager/migrations/2026-08-02-lm-talk-timeline-snapshots.sql`
- Create: `apps/life-manager/lib/accepted-talk-timeline-store.js`
- Create: `apps/life-manager/lib/accepted-talk-timeline-store.test.js`

**Interfaces:**
- Consumes: validated timeline object、`tenantId`、`participationId`
- Produces: `buildTalkTimelineSnapshot(...)`、`createAcceptedTalkTimelineStore({connect}).save(snapshot)`

- [x] **Step 1: RED testを書く**

stable hash、reference-only row、accepted talk gate、idempotent insert、cross-tenant failure、immutable migration contractを固定する。

- [x] **Step 2: REDを確認する**

Run: `node --test lib/accepted-talk-timeline-store.test.js`
Expected: module不存在でFAIL。

- [ ] **Step 3: migrationとminimal storeを書く**

snapshot table、UPDATE/DELETE拒否trigger、current view、同一client transactionを実装する。

- [ ] **Step 4: GREENと全outboundを確認する**

Run: `node --test lib/accepted-talk-timeline-store.test.js && npm run test:outbound`
Expected: 全件PASS。

- [ ] **Step 5: commitする**

```bash
git add apps/life-manager/migrations/2026-08-02-lm-talk-timeline-snapshots.sql apps/life-manager/lib/accepted-talk-timeline-store.js apps/life-manager/lib/accepted-talk-timeline-store.test.js
git commit -m "feat(connector): persist immutable talk timelines"
```

### Task 3: Runtime DB実測、spec、evidence

**Files:**
- Create: `docs/evidence/outbound/2026-08-02-o1b14-live-talk-timeline.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

**Interfaces:**
- Consumes: production migrationとstore
- Produces: rollback済みaccepted fixtureのDB証拠、未採択real talk非変更証拠

- [ ] **Step 1: migrationを実runtime DBへ適用する**

固定container `life-manager-local-postgres-1`へ`psql -v ON_ERROR_STOP=1`で適用する。

- [ ] **Step 2: transaction fixtureを実行する**

同一transactionでaccepted talk fixtureを作り、snapshot保存、current view readback、UPDATE拒否を確認してROLLBACKする。

- [ ] **Step 3: real talk非捏造を確認する**

`https://luma.com/p9kfepcf`のtalk entityが未採択でtimeline row 0であることをcountだけreadbackする。

- [ ] **Step 4: evidence/specを更新する**

O1B14を完了にし、次をO1B15へ更新する。raw ID、mail body、secretは記録しない。

- [ ] **Step 5: final verificationとpush**

```bash
npm run test:outbound
git diff --check
git add <O1B14 files only>
git commit -m "feat(connector): complete accepted talk timeline"
git push origin main
```

Expected: origin/mainが新commitを指し、unrelated dirty filesだけが残る。
