# O1C-17 Common Outbound Result Tracker Implementation Plan

> **Execution:** `building-agents` と strict TDD を使い、人への確認待ちなしで番号順に完了する。

**Goal:** exact Gmail thread から confirmation/reply を取得し、Job Hunter互換の共通result ledgerへ安全に保存する。

## Task 1: Exact read-only Gmail boundary

- [x] malformed/cross-thread/duplicate/pre-submission/outbound message を拒否するRED testを書く。
- [x] `gog --gmail-no-send --no-input ... thread get <exact-id>` adapter とnormalizerを実装する。
- [x] focused testをGREENにする。

## Task 2: Model-owned reply semantics

- [x] deterministic confirmation と agent-owned reply のRED testを書く。
- [x] exact quote proof、allowed status、raw-data-free result builderを実装する。
- [x] mutation casesを追加してfocused testをGREENにする。

## Task 3: Common append-only ledger

- [x] source revalidation、fence、tenant、dedup、conflict、RLS、derived current viewのRED testを書く。
- [x] migration/storeを実装しlocal Compose migration listへ追加する。
- [x] focused/outbound/runtime regressionをGREENにする。

## Task 4: Live proof and closeout

- [x] 実YC threadをread-only fresh readし、存在するresultだけを生成する。
- [x] migration適用、insert、exact replay、DB readbackを行う。
- [x] 非secret evidence、正本spec、remaining countを更新する。
- [x] independent reviewを解消し、commit/push、local/remote HEAD一致を確認する。
