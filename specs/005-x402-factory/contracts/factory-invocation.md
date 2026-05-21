# Contract: Factory Skill Invocation

**Type**: OpenClaw Skill (agentTurn payload)
**Skill**: `to-agents-skill`

---

## Invocation Interface

### Via Slack DM（手動トリガー）

```
@Anicca to-agents-skill produce skill_name=emotion-detector description="Detects emotional state from text" usecase="When an agent needs to understand user emotion before responding"
```

### Via OpenClaw agentTurn（cron / programmatic）

```json
{
  "kind": "agentTurn",
  "message": "Execute to-agents-skill. mode=discover. Read /Users/anicca/.openclaw/workspace/to-agents/to-agents-learning.md and propose the next unbuilt skill from the catalog to Slack #metrics."
}
```

### モード別メッセージ形式

| Mode | Message Pattern |
|------|----------------|
| `produce` | `Execute to-agents-skill. mode=produce. skill_name=<name>. description=<desc>. usecase=<usecase>.` |
| `discover` | `Execute to-agents-skill. mode=discover.` |
| `measure` | `Execute to-agents-skill. mode=measure.` |

---

## Execution Contract（SKILL.md が保証するもの）

### produce モード

| Step | Input | Output | Failure Behavior |
|------|-------|--------|-----------------|
| 1. learning.md 読み込み | ファイルパス | 最新の型とパターン | ファイル未存在 → テンプレートで代替 |
| 2. エンドポイント追加（git + push） | skill_name | Railway への push 完了 | git エラー → halt + #metrics エラー報告 |
| 3. awal テスト | endpoint_url | HTTP 200 OK | 非200 → halt（publish 禁止） |
| 4. SKILL.md 生成 | skill_name + schema | SKILL.md ファイル | - |
| 5. clawhub publish | SKILL.md | clawhub_id | 失敗 → 1回リトライ → halt |
| 6. Moltbook 宣伝 | skill_name + endpoint | post_id | 失敗 → warning（halt しない） |
| 7. learning.md 追記 | ProductionResult | 追記完了 | 失敗 → warning（halt しない） |
| 8. #metrics 報告 | ProductionResult | Slack メッセージ | MUST（halt しない） |

### discover モード

| Step | Action | Output |
|------|--------|--------|
| 1. カタログ読み込み | to-agents-learning.md の未着手スキルを特定 | next_skill |
| 2. 重複チェック | clawhub search <skill_name> | 既存: スキップ / 未存在: 提案 |
| 3. Slack 提案 | #metrics にブロックKitメッセージ送信 | slack_ts |
| 4. proposals.json 更新 | status=pending で保存 | - |
| **STOP** | 承認まで produce 実行禁止 | - |

### measure モード

| Step | Action | Output |
|------|--------|--------|
| 1. 生きているスキル一覧取得 | clawhub search + workspace/to-agents/ | skill list |
| 2. 週次コール数計算 | to-agents-learning.md の実行記録から推定（v1はシンプルカウント） | CallMetrics[] |
| 3. 閾値判定 | MA変化率 -20% 以下 | underperforming list |
| 4. 診断・改善提案 | underperforming 各スキルに1つの改善提案 | #metrics メッセージ |

---

## 不変条件（Invariants）

1. **awal 200 OK なしに clawhub publish は実行しない**
2. **discover モードで ✅ なしに produce は実行しない**
3. **to-agents-learning.md / jobs.json をファイル全体上書きしない**（append only）
4. **#metrics への完了/エラー報告は最終ステップとして必ず実行する**
