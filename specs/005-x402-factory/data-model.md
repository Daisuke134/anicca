# Data Model: x402 Factory Skill

**Date**: 2026-02-24 | **Branch**: `005-x402-factory`

---

## Entities

### 1. SkillRequest（入力）

工場への入力ペイロード。

| Field | Type | Required | Validation |
|-------|------|----------|-----------|
| `skill_name` | string | MUST | kebab-case, 小文字, ハイフン区切り（例: `emotion-detector`） |
| `description` | string | MUST | 1文以上。エンドユーザー向け説明 |
| `usecase` | string | MUST | エージェントがこのスキルを使う場面 |
| `mode` | string | optional | `produce` / `discover` / `measure`（省略時: `produce`） |

**State transitions**:
```
SkillRequest received
  → mode=produce: ProductionPipeline 実行
  → mode=discover: ProposalRecord 作成 → Slack 投稿 → 承認待ち
  → mode=measure: CallMetrics 取得 → DiagnosisReport 作成
```

---

### 2. ProductionResult（出力）

`produce` モード完了時の結果。

| Field | Type | Description |
|-------|------|-------------|
| `skill_name` | string | 生成されたスキル名 |
| `endpoint_url` | string | Railway URL（例: `https://anicca-proxy-production.up.railway.app/api/x402/emotion-detector`） |
| `awal_status` | number | awal テスト HTTP ステータス（200 のみ成功） |
| `clawhub_id` | string | ClawHub 公開後のスキルID |
| `moltbook_post_id` | string | Moltbook 投稿ID |
| `learning_entry_added` | boolean | to-agents-learning.md への追記成否 |
| `slack_report_sent` | boolean | #metrics への完了報告送信成否 |
| `completed_at` | string | ISO8601 タイムスタンプ |
| `error` | string \| null | エラーメッセージ（失敗時のみ） |

---

### 3. LearningEntry（to-agents-learning.md 追記形式）

`to-agents-learning.md` に追記する1レコード。

```markdown
## Run: <skill_name> (<date>)

| Field | Value |
|-------|-------|
| skill_name | emotion-detector |
| endpoint_url | https://anicca-proxy-production.up.railway.app/api/x402/emotion-detector |
| clawhub_id | <id> |
| moltbook_post_id | <id> |
| awal_result | 200 OK |
| notes | <learnings from this run> |
```

**Append rule**: 既存内容の末尾に追記。上書き禁止。

---

### 4. ProposalRecord（proposals.json エントリ）

`discover` モード時に Slack 承認を待つ提案記録。

| Field | Type | Description |
|-------|------|-------------|
| `proposal_id` | string | UUID |
| `skill_name` | string | 提案するスキル名 |
| `description` | string | スキル説明 |
| `rationale` | string | なぜ今このスキルを提案するか |
| `slack_ts` | string | Slack メッセージ timestamp |
| `status` | string | `pending` / `approved` / `rejected` / `expired` |
| `proposed_at` | string | ISO8601 |
| `expires_at` | string | ISO8601（proposed_at + 48h） |

**State transitions**:
```
pending → approved（✅ reaction 受信）→ produce 実行
pending → rejected（❌ reaction 受信）→ 次のスキルを次回 discover で提案
pending → expired（48h 経過）→ 次のスキルを次回 discover で提案
```

---

### 5. CallMetrics（measure モード用）

`measure` モードで取得する週次メトリクス。

| Field | Type | Description |
|-------|------|-------------|
| `skill_name` | string | スキル名 |
| `week_calls` | number | 直近7日の呼び出し数 |
| `prev_week_calls` | number | 前週7日の呼び出し数 |
| `moving_avg_change_pct` | number | 変化率（%）。-20以下でトリガー |
| `days_since_last_call` | number | 最終呼び出しからの日数 |
| `measured_at` | string | ISO8601 |

**Trigger rules**:
- `moving_avg_change_pct <= -20` → 改善提案を #metrics に送信
- `days_since_last_call >= 14`（改善試行後）→ 廃止提案を #metrics に送信

---

### 6. x402EndpointConfig（Railway エンドポイント追加設定）

`apps/api/src/routes/x402/index.js` に追加する paymentMiddleware エントリ。

| Field | Type | Description |
|-------|------|-------------|
| `route` | string | `POST /<skill_name>` |
| `scheme` | string | `"exact"`（固定） |
| `price` | string | `"$0.01"`（固定） |
| `network` | string | `process.env.X402_NETWORK`（固定） |
| `payTo` | string | `process.env.X402_WALLET_ADDRESS`（固定） |
| `description` | string | スキル固有の説明文 |
| `output.example` | object | レスポンスの具体例 |
| `output.schema` | object | レスポンスの JSON Schema |

---

## File Locations（全パス）

| Entity | File Path |
|--------|-----------|
| SkillRequest（入力） | Anicca への Slack DM または cron payload |
| ProductionResult（出力） | Slack #metrics 完了報告 + workspace/to-agents/results/ |
| LearningEntry | `/Users/anicca/.openclaw/workspace/to-agents/to-agents-learning.md` |
| ProposalRecord | `/Users/anicca/.openclaw/workspace/to-agents/proposals.json` |
| CallMetrics | `/Users/anicca/.openclaw/workspace/to-agents/metrics.json` |
| SKILL.md（生成物） | `/Users/anicca/.openclaw/skills/<skill_name>/SKILL.md` |
| Endpoint handler（生成物） | `apps/api/src/routes/x402/<skillName>.js` |
