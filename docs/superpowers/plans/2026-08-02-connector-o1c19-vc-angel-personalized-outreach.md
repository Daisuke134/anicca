# O1C-19 VC / Angel Personalized Outreach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans and TDD. Human approval checkpoints are disabled by the user's no-HITL instruction.

**Goal:** acceleratorを除外し、公式thesis一致時だけVC/angelへ、東京日付の全送信合計3〜5件でpersonalized outreachする。

**Architecture:** agent-owned assessmentを公式target本文とcurrent application-kit exact quoteへ束縛する。既存送信ledgerを拡張し、append-only DB reservationで同日slotを外部送信前に直列化する。

## Task 1: Investor assessment and daily-total planner

**Files:** create `lib/funder-investor-outreach.js`; create `lib/funder-investor-outreach.test.js`。

- [x] RED: VC/angel一致、accelerator、不一致、偽quote、偽company quote、非個別化、既送信3→1通、既送信5→no-opをtestする。
- [x] GREEN: closed assessment、exact evidence binding、current kit binding、DB day-stateからplanを作る。

## Task 2: Pre-send daily slot fence

**Files:** create migration `2026-08-02-lm-funder-investor-outreach.sql`; create PostgreSQL integration test; modify Compose/package scripts。

- [x] RED: migration replay、slot 1〜5、同時/反復reservation、tenant/date isolation、service-only権限を実DBで要求する。
- [x] GREEN: append-only reservation tableとadvisory-lock functionを実装する。

## Task 3: Delivery and existing ledger extension

**Files:** modify outreach Gmail/store modules and tests; modify O1C-09 ledger migration。

- [x] RED: reservation無し拒否、1通delivery、proof columns、exact replay/collisionをtestする。
- [x] GREEN: schema v2 deliveryと既存ledger all-or-none proof保存を実装する。

## Task 4: Live Scion run

- [x] official pageとcurrent application-kitをfresh readし、agent assessmentと1通のcopyを生成する。
- [x] live DBの同日3件をreadし、slot 4をreserve、Gmail送信、provider ID/thread IDを既存ledgerへ保存する。
- [x] Gmail Sent readbackとDB合計4件、proof/reservation整合を確認する。

## Task 5: Verification and closeout

- [x] focused/full/PostgreSQL regression、migration replayをfresh実行する。
- [x] independent reviewのCritical/Importantを0にする。
- [x] evidence JSON、正本spec、残件数を更新し、commit/push/local-remote HEAD一致を確認する。
