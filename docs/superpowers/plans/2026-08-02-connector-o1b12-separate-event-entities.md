# Connector O1B-12 Separate Event Entities Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 一つのeventに対する一般参加registrationとLT/CFP/demo登壇applicationを、別ID・別status machine・同一event refとしてdiscover・追跡する。

**Architecture:** O1B-08のvalidated decisionからreference-only entityを作る。`audience_registration`と`talk_application`はstable hash IDを別々に持ち、共通のcanonical event refだけを共有する。PostgreSQLはcurrent entityとappend-only transitionをtenant-boundで保存し、entity kindを跨ぐstatus遷移を拒否する。

## Constraints

- audienceの登録済みをtalk応募済みに読み替えない。
- openな公開登壇URLがある場合だけtalk application entityを作る。
- raw identity、本文、prompt、credentialをentity payloadへ保存しない。
- submitted/registered/accepted/presentedは外部receipt ref必須。
- discovery再実行は同じentity IDへdedupする。

### Task 1: Entity contract (TDD)

- [x] audience-only、talk-only、bothから正しい別entityを作るREDを追加。
- [x] stable ID、reference-only payload、closed/invite-only非生成を固定する。
- [x] kind別status machineとreceipt必須遷移を実装する。

### Task 2: Durable tracking

- [x] tenant-bound current tableとappend-only transition table migrationを追加する。
- [x] discover upsertとcompare-and-set transition storeをTDDで追加する。
- [x] local PostgreSQLへmigrationを適用し、同一eventの2 entityを実readbackする。

### Task 3: SSOT and delivery

- [x] outbound/runtime回帰、diff checkを通す。
- [x] O1B-12完了、残数125件へspecを更新する。
- [x] evidence、commit、pushを完了する。
