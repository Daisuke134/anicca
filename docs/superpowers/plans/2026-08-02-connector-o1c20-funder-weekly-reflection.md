# O1C-20 Funder Weekly Reflection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans and TDD. Human approval checkpoints are disabled by the user's no-HITL instruction.

**Goal:** verifiedな返信・面談・採否結果を週次で振り返り、次回funding outreachのtarget rankingとpitchへ強制的に反映する。

**Architecture:** 既存append-only台帳の単一週次snapshotからagent-owned strategy revisionを作り、closed validation後にappend-only保存する。次回plannerは検証済みrevisionの順位・pitch directive・result lineageを照合する。

## Task 1: Weekly snapshot and closed reflection

**Files:** create `lib/funder-weekly-reflection.js`; create `lib/funder-weekly-reflection.test.js`。

- [x] RED: Tokyo半開週、look-ahead、confirmation除外、結果0件hold、meeting/reject/offerを根拠にしたchange、偽result、候補欠落・重複をtestする。
- [x] GREEN: deterministic snapshot projection、agent judgment validation、content-addressed verified revisionを実装する。

## Task 2: Append-only store and weekly cadence

**Files:** create migration `migrations/2026-08-02-lm-funder-weekly-reflection-ledger.sql`; create store/runtime/runner modules and tests; add PostgreSQL integration test。

- [x] RED: tenant/week uniqueness、exact replay、collision、UPDATE/DELETE/TRUNCATE、RLS/roles、日曜20:15 JST due、並列二重実行をtestする。
- [x] GREEN: single-snapshot reader、append-only ledger、no-HITL weekly runner、fail-closed provider boundaryを実装する。

## Task 3: Enforce reflection in the next outreach

**Files:** modify `lib/funder-investor-outreach.js` and tests。

- [x] RED: verified revisionの順位とdirectiveがselection/bodyへ反映され、偽造・古いrevision・candidate mismatch・directive未反映を拒否するtestを追加する。
- [x] GREEN: verified revision overlayをplannerへ接続し、hold revisionは正直なno-opとして既存動作を維持する。

## Task 4: Live truthful weekly run

- [x] 実ledger migrationを適用し、tenant `dais-local`の週次snapshotをfresh readする。
- [x] 実結果が0件であることを確認し、`hold / insufficient_outcomes` reflectionを一度だけ保存してexact replayを確認する。
- [x] 生本文・recipient・provider IDを含まないreadback evidenceを生成する。

## Task 5: Verification and closeout

- [x] focused/full/PostgreSQL/runtime/outbound regressionとmigration replayをfresh実行する。
- [x] independent reviewでCritical/Importantを0にする。
- [ ] evidence JSON、正本spec、残件数を更新し、commit/push/local-remote HEAD一致を確認する。
