# 07 — VPS Worker + Cron統合 + 既存Skill移行パス

> **元ファイル**: `../closed-loop-ops.md` Section 8, 18
> **ナビ**: [← Slack Approval](./06-slack-approval.md) | [README](./README.md) | [次: Event System →](./08-event-trigger-system.md)

---

## 8. VPS Worker（OpenClaw スキル側）

### 8.1 Mission Worker スキル

> **VPSのOpenClawから5分毎に呼ばれる。次の queued ステップを取得→実行→完了報告**

```yaml
---
name: mission-worker
description: Ops閉ループの実行エンジン。queued ステップを取得して実行する
metadata: { "openclaw": { "emoji": "⚙️", "requires": { "env": ["ANICCA_AGENT_TOKEN"] } } }
---

# mission-worker

## Instructions

1. `GET /api/ops/step/next` で次の実行待ちステップを取得
2. ステップがなければ正常終了（何もしない）
3. ステップがあれば、step_kind に応じた処理を実行:
   - `draft_content`: hookSelector.js でhook選択 → LLMでコンテンツ生成
   - `verify_content`: verifier.js でコンテンツ検証（3/5以上で合格）
   - `post_x`: X API で投稿
   - `post_tiktok`: TikTok API で投稿
   - `detect_suffering`: 苦しみキーワード検索
   - `send_nudge`: app-nudge-sender 経由でNudge送信
   - `fetch_metrics`: X/TikTok のエンゲージメントデータ取得
   - `analyze_engagement`: メトリクスを分析し shared-learnings に記録
   - `diagnose`: ミッション失敗の原因分析
4. 実行結果を `PATCH /api/ops/step/:id/complete` で報告
5. イベントを発行（投稿成功、苦しみ検出等）

## Required Tools

- `exec` (API呼び出し、コンテンツ生成)
- `web_search` (トレンド検出)
- `slack` (通知)
- `read` / `write` (shared-learnings)

## Error Handling

| エラー | 対応 |
|--------|------|
| API呼び出し失敗 | リトライ3回後、step を failed で報告 |
| LLM生成失敗 | フォールバックチェーン（OpenAI → Anthropic → Groq） |
| X API rate limit | step を failed で報告（次回Heartbeat で再スケジュール可能） |
```

### 8.2 Cron 統合

> **既存の個別Cronを mission-worker + heartbeat に集約**
> **注**: 実際のVPSでは `~/.openclaw/cron/jobs.json`（JSON形式）を使用。
> 以下はYAML形式で設計意図を記述（可読性のため）。実装時はJSON形式に変換すること。
> 変換例: CLAUDE.md「OpenClaw VPS Quick Reference」セクション参照。

```yaml
# 設計意図（実装時は ~/.openclaw/cron/jobs.json にJSON形式で記述）
# timezone: Asia/Tokyo

jobs:
  # --- 閉ループ制御 ---

  # Heartbeat: 5分毎にRailway APIの制御プレーンを叩く
  ops-heartbeat:
    cron: "*/5 * * * *"
    session: isolated
    kind: agentTurn
    delivery:
      mode: "none"
    message: |
      curl -s -H "Authorization: Bearer $ANICCA_AGENT_TOKEN" \
        ${API_BASE_URL}/api/ops/heartbeat

  # Mission Worker: 1分毎に次のステップを取得→実行
  ops-worker:
    skill: mission-worker
    cron: "* * * * *"
    session: isolated

  # --- 提案生成（閉ループの入口）---
  # P1 #8 解消: Cron message 形式
  # message フィールドはプレーンテキスト。JSON を含むがテキストとして渡される。
  # OpenClaw エージェントは message を LLM に渡し、LLM が内容を理解して exec で API POST を実行する。
  # JSON.parse() による機械的パースではなく、LLM のプロンプト指示として動作する。

  # x-poster: 朝と夜に投稿提案を生成
  x-poster-morning:
    cron: "0 9 * * *"
    session: isolated
    kind: agentTurn
    delivery:
      mode: "none"
    message: |
      以下のJSONをPOST /api/ops/proposal に送信してください:
      {
        "skillName": "x-poster",
        "source": "cron",
        "title": "X朝投稿",
        "payload": { "slot": "morning" },
        "steps": [
          { "kind": "draft_content", "order": 0 },
          { "kind": "verify_content", "order": 1 },
          { "kind": "post_x", "order": 2 }
        ]
      }

  x-poster-evening:
    cron: "0 21 * * *"
    session: isolated
    kind: agentTurn
    delivery:
      mode: "none"
    message: |
      以下のJSONをPOST /api/ops/proposal に送信してください:
      {
        "skillName": "x-poster",
        "source": "cron",
        "title": "X夜投稿",
        "payload": { "slot": "evening" },
        "steps": [
          { "kind": "draft_content", "order": 0 },
          { "kind": "verify_content", "order": 1 },
          { "kind": "post_x", "order": 2 }
        ]
      }

  tiktok-poster:
    cron: "0 20 * * *"
    session: isolated
    kind: agentTurn
    delivery:
      mode: "none"
    message: |
      以下のJSONをPOST /api/ops/proposal に送信してください:
      {
        "skillName": "tiktok-poster",
        "source": "cron",
        "title": "TikTok日次投稿",
        "payload": {},
        "steps": [
          { "kind": "draft_content", "order": 0 },
          { "kind": "verify_content", "order": 1 },
          { "kind": "post_tiktok", "order": 2 }
        ]
      }

  trend-hunter:
    cron: "0 */4 * * *"
    session: isolated
    kind: agentTurn
    delivery:
      mode: "none"
    message: |
      以下のJSONをPOST /api/ops/proposal に送信してください:
      {
        "skillName": "trend-hunter",
        "source": "cron",
        "title": "トレンド検出 + hook生成",
        "payload": {},
        "steps": [
          { "kind": "run_trend_scan", "order": 0 }
        ]
      }

      # 注意: run_trend_scan は単一ステップだが、VPS SKILL.md 内部で
      # 全パイプライン（4ソース収集→LLMフィルタ→hook生成→Railway保存→hook_saved イベント発行）を実行する。
      # detect_suffering とは別物。detect_suffering は suffering-detector 用。

  # --- 既存（変更なし）---

  daily-metrics-reporter:
    # 既存のまま（ops対象外）
    cron: "0 20 * * *"
    session: isolated

  hookpost-ttl-cleaner:
    skill: hookpost-ttl-cleaner
    cron: "0 3 * * *"
    session: isolated

  sto-weekly-refresh:
    skill: sto-weekly-refresh
    cron: "0 3 * * 0"
    session: isolated
```

---

## 18. 既存 Skill 移行パス

> **Gap P1 #4 解消**: 既存のスキルを閉ループ対応に移行する方法
> **方針**: 既存 SKILL.md を「閉ループ対応版」に書き換え。skill-creator で再作成

### 18.1 移行チェックリスト

| # | スキル | 現行 | 閉ループ対応後 | 移行難易度 |
|---|--------|------|---------------|-----------|
| 1 | x-poster | 直接 X API 呼び出し + Slack 報告 | Proposal → Mission → Steps (draft→verify→post) | 中 |
| 2 | tiktok-poster | 直接 TikTok API 呼び出し + Slack 報告 | Proposal → Mission → Steps (draft→verify→post) | 中 |
| 3 | trend-hunter | web_search → hook_candidates INSERT | Proposal → Mission → Step (run_trend_scan) — 単一ステップ内で4ソース収集→フィルタ→hook生成→保存→イベント発行を全実行 | 低 |
| 4 | suffering-detector | Moltbook 検索 → 返信 | Proposal → Mission → Step (detect_suffering) | 低 |
| 5 | app-nudge-sender | 直接 Push通知 | Proposal → Mission → Steps (draft_nudge→send_nudge) | 中 |

### 18.2 x-poster SKILL.md Before/After

**BEFORE（現行: 直接実行型）:**
```yaml
---
name: x-poster
description: X(Twitter)にAnicca関連の投稿をする
---

# x-poster

1. hook_candidates テーブルから候補を取得
2. Thompson Sampling でhook選択
3. LLMでコンテンツ生成
4. verifier.js で検証（3/5以上で合格）
5. X API で投稿
6. Slackに結果報告
```

**AFTER（閉ループ対応: Proposal 経由）:**
```yaml
---
name: x-poster
description: X(Twitter)にAnicca関連の投稿をする（閉ループ対応）
metadata:
  openclaw:
    emoji: "🐦"
    requires:
      env: ["ANICCA_AGENT_TOKEN"]
---

# x-poster（閉ループ版）

## 概要
Cron から呼ばれた時、直接投稿せずに Proposal を生成する。
実際の実行は mission-worker が行う。

## Instructions

1. Cron メッセージから slot (morning/evening) を受け取る
2. 以下のJSONを POST /api/ops/proposal に送信:
   ```json
   {
     "skillName": "x-poster",
     "source": "cron",
     "title": "X{slot}投稿",
     "payload": { "slot": "{slot}" },
     "steps": [
       { "kind": "draft_content", "order": 0 },
       { "kind": "verify_content", "order": 1 },
       { "kind": "post_x", "order": 2 }
     ]
   }
   ```
3. レスポンスを確認:
   - `status: "accepted"` → ログに記録（mission-worker が実行する）
   - `status: "rejected"` → リジェクト理由をログに記録
   - `status: "pending"` → 人間承認待ち（Slack通知済み）

## 注意
- 直接 X API を呼んではいけない（mission-worker の担当）
- このスキルは「提案を作る」だけ。実行はしない
```

### 18.3 mission-worker SKILL.md（詳細版）

```yaml
---
name: mission-worker
description: Ops閉ループの実行エンジン。queued ステップを取得→実行→完了報告
metadata:
  openclaw:
    emoji: "⚙️"
    requires:
      env: ["ANICCA_AGENT_TOKEN"]
      tools: ["exec", "web_search", "slack", "read", "write"]
---

# mission-worker

## 概要
1分毎にポーリングし、次の queued ステップを取得→実行→完了報告する。
全ての外部API呼び出し（X API, TikTok API, LLM等）はこのワーカーが担当。

## Instructions

### 1. ステップ取得
```bash
curl -s -H "Authorization: Bearer $ANICCA_AGENT_TOKEN" \
  $API_BASE_URL/api/ops/step/next
```

レスポンス `step: null` の場合 → 正常終了（何もしない）

### 2. ステップ実行（step_kind 別）

| step_kind | 処理内容 | 使用ツール |
|-----------|---------|-----------|
| `draft_content` | hookSelector → LLMでコンテンツ生成 | exec (API呼び出し) |
| `verify_content` | verifier.js でコンテンツ検証 | exec (API呼び出し) |
| `post_x` | X API v2 で投稿 | exec (curl) |
| `post_tiktok` | TikTok API で投稿 | exec (curl) |
| `fetch_metrics` | X/TikTok API でメトリクス取得 | exec (curl) |
| `analyze_engagement` | LLMで分析 + shared-learnings 記録 | exec, write |
| `detect_suffering` | Web検索で苦しみ関連トレンド検出 | web_search |
| `draft_nudge` | LLMでNudge下書き生成 | exec |
| `send_nudge` | Railway API 経由でPush通知 | exec |
| `diagnose` | 失敗ミッションの原因分析（input: `{ eventId }` — mission:failed イベントIDを受け取る。missionIdではない） | exec, read |
| `evaluate_hook` | hook_candidate の投稿適合性評価 | exec |
| `run_trend_scan` | trend-hunterフルパイプライン（4ソース収集→LLMフィルタ→hook生成→Railway保存→イベント発行） | exec, web_search |

### 3. 完了報告
```bash
# events は output の外側で送信する（step/complete は body.events を処理）
curl -s -X PATCH \
  -H "Authorization: Bearer $ANICCA_AGENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "succeeded", "output": {...}, "events": [...]}' \
  $API_BASE_URL/api/ops/step/{stepId}/complete
```

### 4. エラーハンドリング

| エラー | 対応 |
|--------|------|
| API呼び出し失敗 | 3回リトライ（Equal Jitter Backoff）後、status: "failed" で報告 |
| LLM生成失敗 | フォールバックチェーン: OpenAI → Anthropic → Groq |
| X/TikTok rate limit | status: "failed" + error: "rate_limited" で報告 |
| タイムアウト | 5分で強制終了 + status: "failed" で報告 |

### 5. output に含めるべきデータ

step_kind ごとの output スキーマ（次ステップの input になる）:

| step_kind | output 必須フィールド |
|-----------|---------------------|
| `draft_content` | `content`, `hookId`, `hookText`, `platform` |
| `verify_content` | `content`, `verificationScore`, `passed` |
| `post_x` | `postId`, `dbRecordId`, `platform` |
| `post_tiktok` | `postId` |
| `fetch_metrics` | `metrics`, `postId`, `platform` |
| `analyze_engagement` | `analysis`, `isHighEngagement`, `engagementRate` |
| `detect_suffering` | `detections[]` (各: text, severity, problemType) |
| `diagnose` | `diagnosis`, `failedMissionId`, `failedStepKinds`（input: `{ eventId }` — missionIdではなくeventIdを受け取る） |
| `draft_nudge` | `nudgeContent`, `targetProblemType`, `severity` |
| `send_nudge` | `sent`, `nudgeContent`, `targetProblemType`（skipped時: `{ sent: false, skipped: true }`） |
| `evaluate_hook` | `shouldPost` (boolean) |
```
