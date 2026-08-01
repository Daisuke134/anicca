# O1C-18 Fundraising Funnel Web Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 検証済み資金調達eventだけから、tenant別のapplication→confirmation→interview→offer/reject→funded funnelを既存Web panelへ表示する。

**Architecture:** PostgreSQL RPCがappend-only source ledgerを単一snapshotでprivacy-safe event列へ変換し、Node coreが順序と矛盾を検証してclosed DTOを作る。Panel API、server presentation、browser validatorの三境界を通し、別のfunnel正本は作らない。

**Tech Stack:** Node.js CommonJS、node:test、PostgreSQL 18、PostgREST/Supabase RPC、server-rendered HTML/CSS/JavaScript、Playwright smoke capture。

## Global Constraints

- 未観測stageを到達扱いにしない。現在のlive claimはapplication 1、confirmation 1、他0だけ。
- judgmentはmodel-owned。deterministic codeはschema、source binding、順序、集計、privacyを扱う。
- provider ID、thread ID、本文、sender、subject、quote、digestをWeb DTOへ出さない。
- RPCはservice roleだけ、tenantはauthenticated panel sessionの`uid`だけを読む。
- source欠落・矛盾・未知field・secret-like値は偽の0件へfallbackせずsection unavailableにする。

---

### Task 1: Funnel stage source contract

**Files:**
- Modify: `apps/life-manager/lib/funder-thread-result.js`
- Modify: `apps/life-manager/lib/outbound-result-store.js`
- Modify: `apps/life-manager/lib/funder-thread-result.test.js`
- Modify: `apps/life-manager/migrations/2026-08-02-lm-outbound-result-ledger.sql`

**Interfaces:**
- Consumes: verified funder reply judgment `{kind,status,rationale,evidence_quotes}`。
- Produces: `offer_received | funded`を含むverified common outbound result。

- [x] **Step 1: RED** — exact quote付き`offer_received`/`funded`が未対応で失敗し、未知statusとplain copyが拒否されるtestを書く。
- [x] **Step 2: RED確認** — `node --test lib/funder-thread-result.test.js`がallowed status不足だけで失敗することを確認する。
- [x] **Step 3: GREEN** — model-owned status allowlistとDB CHECKを5-stage contractへ拡張し、既存provenance/hash契約を維持する。
- [x] **Step 4: GREEN確認** — focused testを通す。

### Task 2: Deterministic funnel projector

**Files:**
- Create: `apps/life-manager/lib/fundraising-funnel.js`
- Create: `apps/life-manager/lib/fundraising-funnel.test.js`

**Interfaces:**
- Consumes: `{schema_version:1,events:[{funder_id,source_id,event_kind,occurred_at}]}`。
- Produces: `buildFundraisingFunnel(candidate)`のclosed Web DTO。

- [x] **Step 1: RED** — current YC literal、complete path、reject branch、emptyをhand-derived DTOでtestする。
- [x] **Step 2: RED確認** — module不存在で失敗することを確認する。
- [x] **Step 3: GREEN** — sourceごとに順序検証し、summary/application railsを構築する最小実装を書く。
- [x] **Step 4: RED** — cross-source result、逆順、funded without offer、offer+reject、duplicate stage、extra/secret fieldを拒否するtestを追加する。
- [x] **Step 5: GREEN** —全mutationをfail closedにし、focused testを通す。

### Task 3: Single-snapshot PostgreSQL RPC

**Files:**
- Create: `apps/life-manager/migrations/2026-08-02-lm-panel-fundraising-funnel.sql`
- Create: `apps/life-manager/test/postgres/fundraising-funnel-postgres.integration.sh`
- Modify: `deploy/local/compose.yaml`
- Modify: `apps/life-manager/package.json`

**Interfaces:**
- Produces: `public.lm_panel_fundraising_funnel(p_uid text) RETURNS jsonb`。

- [x] **Step 1: RED** — migration replay、tenant A/B isolation、event mapping、service execution、anon/authenticated denialを実DBで要求するscriptを書く。
- [x] **Step 2: RED確認** — RPC不存在でintegrationが失敗することを確認する。
- [x] **Step 3: GREEN** — source-bound joinを行うSTABLE RPCとservice-only privilegeを実装しComposeへ追加する。
- [x] **Step 4: GREEN確認** — PostgreSQL integrationを2回通す。

### Task 4: Authenticated Panel API and presentation

**Files:**
- Modify: `apps/life-manager/lib/panel-api.js`
- Modify: `apps/life-manager/lib/panel-presentation.js`
- Modify: `apps/life-manager/lib/panel-api.test.js`
- Modify: `apps/life-manager/lib/panel-privacy-api.test.js`

**Interfaces:**
- Adds: `GET /api/panel/fundraising`。
- Reads: RPC with `{p_uid: scope.uid}`。
- Returns: `buildFundraisingFunnel`のclosed DTOだけ。

- [x] **Step 1: RED** — authenticated exact tenant RPC、401、RPC/source error、hostile/extra payload拒否をAPI testへ追加する。
- [x] **Step 2: RED確認** — endpoint 404で失敗することを確認する。
- [x] **Step 3: GREEN** — reader、endpoint、presentation validatorを追加する。
- [x] **Step 4: GREEN確認** — panel API/privacy testsを通す。

### Task 5: Visual Web funnel

**Files:**
- Modify: `apps/life-manager/lib/panel-ui.js`
- Modify: `apps/life-manager/lib/panel-ui.test.js`
- Modify: `apps/life-manager/eval/panel-privacy-harness.js`
- Modify: `apps/life-manager/eval/panel-privacy-contract.js`

**Interfaces:**
- Adds: `data-panel-section="fundraising"`、browser `validateFundraisingData`、`renderFundraising`。

- [x] **Step 1: RED** — section順序、6 summary counts、branch rail、375px縦layout、browser closed validator、section単独errorをtestする。
- [x] **Step 2: RED確認** — fundraising section不存在で失敗することを確認する。
- [x] **Step 3: GREEN** — accessible HTML/CSS rendererとsame-origin loaderを実装する。
- [x] **Step 4: GREEN確認** — UI、privacy eval、smoke testsを通す。

### Task 6: Live proof and closeout

**Files:**
- Create: `docs/evidence/funding/2026-08-02-o1c18-fundraising-funnel-web.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`
- Modify: this plan

**Interfaces:**
- Proves: live local DB → RPC → projector → rendered panelの同一count。

- [x] **Step 1** — migrationをlive local DBへreplayし、YC application=1/confirmation=1/他=0をreadbackする。
- [x] **Step 2** — authenticated fixtureで実panel HTMLをrenderし、desktop/mobile screenshotとDOM countを検証する。
- [x] **Step 3** — full panel/outbound/runtime regression、syntax、diff checkをfresh実行する。
- [x] **Step 4** — independent reviewのCritical/Importantを0にする。
- [x] **Step 5** — implementation commit、evidence、正本checkbox、残94件、push、local/remote HEAD一致を証拠化する。
