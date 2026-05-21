# 01 — Overview & Architecture Decision Records

> **元ファイル**: `../closed-loop-ops.md` Section 0-1
> **ナビ**: [← README](./README.md) | [次: Data Layer →](./02-data-layer.md)

---

## 0. Executive Summary

| 項目 | 内容 |
|------|------|
| **何を解決するか** | 現行のCron一方通行（実行→終了）を、閉ループ（提案→承認→実行→イベント→トリガー→提案...）に変える |
| **なぜ必要か** | 「x-posterが投稿した結果を次のx-posterが知らない」「trend-hunterの検出をapp-nudge-senderが知らない」というスキル間断絶を解消する |
| **VoxYZの教訓** | 3つの落とし穴（二重実行者、トリガー→提案の断絶、キュー肥大）を事前に回避する |
| **変更規模** | 新規7テーブル + 新規4エンドポイント + 既存Skill改修5本 + Cron統合 |
| **変更しないもの** | Thompson Sampling (hookSelector.js)、content-verifier (verifier.js)、memU テーブル、iOS向けAPI全て |

---

## 1. アーキテクチャ決定記録

### ADR-004: Closed-Loop Ops Layer

**決定**: VoxYZ 方式の Proposal→Mission→Step 閉ループを Railway PostgreSQL + Railway API + OpenClaw VPS で実装する

| 選択肢 | 評価 | 理由 |
|--------|------|------|
| **A: Railway PostgreSQL（採用）** | ✅ | 既存DB活用、Prisma互換、移行不要 |
| B: Supabase 追加 | ❌ | 2DB管理、移行コスト大、リアルタイムsubscription不要（5分ポーリングで十分） |
| C: OpenClaw Memory のみ | ❌ | ファイルベース、ACID保証なし、クエリ能力不足 |

**VoxYZとの差分**:

| VoxYZ | Anicca | 理由 |
|-------|--------|------|
| Supabase（状態管理） | Railway PostgreSQL | 既存DB活用。リアルタイムsubscription不要 |
| Vercel（制御プレーン） | Railway API | 既存APIサーバー活用。Vercelの追加コスト不要 |
| OpenClaw VPS（実行） | OpenClaw VPS（同一） | 完全一致 |

### ADR-005: 実行者の一元化（Pitfall 1 回避）

**決定**: VPS を唯一の実行者（Executor）とする。Railway API は制御プレーン（Control Plane）のみ

**根拠**: VoxYZの Pitfall 1 — VPSとVercel両方がタスクを実行し、race conditionが発生した。修正: 実行者を1つに絞る

```
VPS (OpenClaw)  = Think + Execute（唯一の実行者）
Railway API     = Approve + Monitor（制御プレーンのみ）
Railway PostgreSQL = All State（共有記憶）
```

### ADR-006: 提案サービスの単一エントリポイント（Pitfall 2 回避）

**決定**: 全ての提案作成は `createProposalAndMaybeAutoApprove()` を通す。直接 INSERT 禁止

**根拠**: VoxYZの Pitfall 2 — トリガーが直接 proposals テーブルに INSERT し、auto-approve と mission 生成がスキップされた

### ADR-007: Cap Gate による事前リジェクト（Pitfall 3 回避）

**決定**: クォータ超過は提案段階でリジェクト。Mission/Step を生成しない

**根拠**: VoxYZの Pitfall 3 — クォータ超過でもMission/Stepが生成され続け、キューが肥大化した
