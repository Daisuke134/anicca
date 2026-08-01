# Connector O1B-02 Canonical Event URL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> Status: 実行中。

**Goal:** Calendar、応募証拠、Telegramに載せるイベントURLを、再訪可能なcanonical URLへ統一し、connpassのgroup subdomainを失わない。

**Architecture:** `life-manager`にprovider非依存のcanonical event URL境界を置く。HTTPSだけを許可し、一回性`/join/complete/`を拒否する。connpassは検索結果で得たhostとevent IDをそのまま保持し、root domainへ再構築しない。E3 verifierも同じ境界を使う。旧OpenClaw配備版とvendor copyの差は回帰監査で可視化する。

**Tech Stack:** Node.js 20、node:test、既存outbound evidence contract、実URLへのredirectなしHEAD検証。

## Global Constraints

- O1B-02だけを実装し、Luma browser RSVP adapterはO1B-03へ残す。
- URLはcallerのsuccess自己申告ではなく、共通canonicalizerと実HEAD 200で検証する。
- event URLからcredential、fragment、一回性POST結果URLを除外する。
- 正本specをRED、GREEN、commit、pushごとに更新する。
- unrelated dirty filesをstageしない。

---

### Task 1: Canonical URL contract

**Files:**
- Create: `apps/life-manager/lib/canonical-event-url.js`
- Create: `apps/life-manager/lib/canonical-event-url.test.js`
- Modify: `apps/life-manager/lib/outbound-evidence.js`
- Modify: `apps/life-manager/package.json`

- [ ] connpass group subdomain保持、末尾slash、fragment除去、一回性URL拒否のRED testを書く。
- [ ] 最小canonicalizerを実装しGREENにする。
- [ ] E3 verifierを同じcanonicalizerへ接続しoutbound回帰testを通す。
- [ ] Commit and push.

### Task 2: Deployed legacy regression audit

**Files:**
- Create: `apps/life-manager/scripts/audit-legacy-event-urls.js`
- Create: `apps/life-manager/scripts/audit-legacy-event-urls.test.js`

- [ ] 配備版が検索結果URLを保持し、root connpass URLを再構築しないことを検査するRED testを書く。
- [ ] 古いvendor copyの退行を明示し、正本への移植対象として報告するauditを実装する。
- [ ] 配備版と正本contractの回帰testを通す。
- [ ] Commit and push.

### Task 3: Ten live URL proofs and canonical spec

**Files:**
- Create: `docs/evidence/outbound/2026-08-01-o1b02-canonical-event-urls.json`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

- [ ] 現在の実イベントcanonical URLを10件収集する。
- [ ] redirectなしHEAD 200、subdomain保持、一回性URLなしを全10件で確認する。
- [ ] evidence JSONへURL、status、検証時刻、claim boundaryを保存する。
- [ ] fresh tests、JSON検証、git diff、local/remote一致を確認する。
- [ ] O1B-02を完了にし、O1B-03を次にする。
- [ ] Commit and push.
