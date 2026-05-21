# Paywall Experiment Loop Spec

Version: 1.0
Created: 2026-02-12
Status: Draft

---

## 概要

RevenueCat Experiments を使った Paywall コピーの自動 A/B テストループ。
週次で結果を評価し、勝者を昇格、次の実験を自動開始する。

## 目的

1. Paywall CVR を継続的に改善
2. 人間の介入なしで実験サイクルを回す
3. Candle 原則に基づくコピー生成

---

## As-Is (現状)

```
- Paywall コピー固定
- A/B テストなし
- 変更は手動デプロイのみ
- データに基づく改善なし
```

## To-Be (目標)

```
┌──────────────────────────────────────────────────────────────────┐
│                   PAYWALL EXPERIMENT LOOP                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [paywall-experiment-loop]                                       │
│   cron: 0 9 * * 1 (毎週月曜9時 JST)                              │
│                                                                  │
│   1. RevenueCat API → 現在の Experiment 結果取得                 │
│   2. 統計的有意差チェック (p < 0.05, 最低 N=200)                 │
│   3. 有意差あり → 勝者を default に昇格                          │
│   4. 次のコピー案を LLM で生成 (Candle原則)                      │
│   5. 新 Offering 作成 → 新 Experiment 開始                       │
│   6. Slack #metrics に報告                                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Candle 原則（コピー生成ルール）

### ❌ 訴求しない: コアバリュー
ユーザーは 7日間トライアルで体験済み。

- "Personalized nudges for your pain"
- "Exact-time reminders at difficult times"
- "Daily reminders"
- "Get full access to all features"

### ✅ 訴求する: 深さ・進捗・カスタマイズ
トライアル後に価値が積み重なるもの。

| カテゴリ | 例 |
|---------|-----|
| 深さ | 行動パターン分析、30日インサイト、詳細レポート |
| 進捗 | 成長グラフ、ストリーク、目標達成率 |
| カスタマイズ | Nudge タイミング変更、頻度調整、テーマ |

---

## 技術仕様

### 必要な環境変数

| Key | Description |
|-----|-------------|
| `REVENUECAT_V2_SECRET_KEY` | RevenueCat API v2 シークレット |
| `REVENUECAT_PROJECT_ID` | プロジェクト ID (projbb7b9d1b) |
| `OPENAI_API_KEY` | LLM コピー生成用 |
| `SLACK_BOT_TOKEN` | #metrics 投稿用 |

### RevenueCat API エンドポイント

```bash
# 実験結果取得
GET https://api.revenuecat.com/v2/projects/{project_id}/experiments/{experiment_id}
Authorization: Bearer $REVENUECAT_V2_SECRET_KEY

# Offering 一覧
GET https://api.revenuecat.com/v2/projects/{project_id}/offerings

# Offering 作成
POST https://api.revenuecat.com/v2/projects/{project_id}/offerings

# 実験作成
POST https://api.revenuecat.com/v2/projects/{project_id}/experiments
```

### 判定ロジック

```typescript
interface ExperimentResult {
  variantA: { users: number; conversions: number };
  variantB: { users: number; conversions: number };
}

function evaluate(result: ExperimentResult): Decision {
  const totalUsers = result.variantA.users + result.variantB.users;
  
  // 1. サンプル数チェック
  if (totalUsers < 200) {
    return { action: "continue", reason: "insufficient_sample" };
  }
  
  // 2. CVR 計算
  const cvrA = result.variantA.conversions / result.variantA.users;
  const cvrB = result.variantB.conversions / result.variantB.users;
  
  // 3. 統計的有意差 (chi-squared test)
  const pValue = chiSquaredTest(result);
  
  if (pValue >= 0.05) {
    return { action: "continue", reason: "not_significant", pValue };
  }
  
  // 4. 勝者決定
  const winner = cvrB > cvrA ? "B" : "A";
  return { 
    action: "promote_and_start_new", 
    winner,
    cvrA,
    cvrB,
    pValue,
    confidence: (1 - pValue) * 100
  };
}
```

### LLM Prompt (次の Variant 生成)

```
あなたは Paywall コピーライターです。

## 背景
- アプリ: Anicca (習慣化・行動変容)
- 7日間無料トライアル → 月額 $9.99

## Candle 原則
- コアバリュー（Nudge、リマインダー）は訴求しない
  → ユーザーはトライアルで体験済み
- 深さ・進捗・カスタマイズを訴求する
  → トライアル後に価値が積み重なるもの

## 現在の実験結果
- Variant A (現行): CVR {a_cvr}%
- Variant B: CVR {b_cvr}% {winner_mark}

## 勝者の良い要素
{winner_copy}

## タスク
次の Variant C を作成してください。

要件:
1. 勝者の良い要素を保持
2. 新しい「深さ/進捗/カスタマイズ」の切り口を追加
3. フォーマット:
   - タイトル (5語以内)
   - 3つの bullet point (各20文字以内)
   - CTA は "Try Free For 1 Week" 固定

出力形式:
```json
{
  "title": "...",
  "bullets": ["...", "...", "..."],
  "cta": "Try Free For 1 Week"
}
```
```

---

## Cron 設定

```json
{
  "name": "paywall-experiment-loop",
  "schedule": {
    "kind": "cron",
    "expr": "0 9 * * 1",
    "tz": "Asia/Tokyo"
  },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "Run paywall-experiment-loop skill."
  },
  "delivery": {
    "mode": "announce",
    "channel": "C091G3PKHL2"
  }
}
```

---

## Slack 投稿フォーマット

### パターン A: サンプル不足

```
📊 Paywall A/B テスト週次レポート

実験: {experiment_name}
期間: {start_date} - {end_date} ({days}日間)
ステータス: 🟡 継続中

サンプル数:
  Variant A (現行): {a_users} users
  Variant B ({b_label}): {b_users} users
  合計: {total} / 最低200 必要

CVR (参考値):
  A: {a_cvr}% ({a_conv}/{a_users})
  B: {b_cvr}% ({b_conv}/{b_users})

判定: サンプル不足のため継続
次回チェック: {next_check_date}
```

### パターン B: 有意差なし

```
📊 Paywall A/B テスト週次レポート

実験: {experiment_name}
期間: {start_date} - {end_date} ({days}日間)
ステータス: 🟡 継続中

サンプル数:
  Variant A (現行): {a_users} users
  Variant B ({b_label}): {b_users} users
  合計: {total} ✅

CVR:
  A: {a_cvr}% ({a_conv}/{a_users})
  B: {b_cvr}% ({b_conv}/{b_users})

統計検定:
  差分: {diff}%
  p-value: {p_value} (有意水準 0.05)
  結果: ❌ 有意差なし

判定: 継続、{weeks}週後に再評価
次回チェック: {next_check_date}
```

### パターン C: 勝者決定

```
📊 Paywall A/B テスト週次レポート

実験: {experiment_name}
期間: {start_date} - {end_date} ({days}日間)
ステータス: ✅ 完了

サンプル数:
  Variant A (現行): {a_users} users
  Variant B ({b_label}): {b_users} users
  合計: {total} ✅

CVR:
  A: {a_cvr}% ({a_conv}/{a_users})
  B: {b_cvr}% ({b_conv}/{b_users}) ⭐ 勝者

統計検定:
  差分: +{diff}%
  p-value: {p_value} ✅ (< 0.05)
  信頼度: {confidence}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎉 アクション実行:

1. ✅ Variant B を default に昇格
   RevenueCat Offering "{winner_offering}" → default

2. 🆕 新実験 {new_experiment_name} を開始
   Variant A: 現勝者 ({b_label})
   Variant B: {c_label} (新)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 新 Variant B コピー:

タイトル: "{c_title}"

{c_bullets}

CTA: "Try Free For 1 Week"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 次回チェック: {next_check_date}
```

---

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | サンプル不足 | A:45, B:52 | action: continue, reason: insufficient_sample |
| 2 | 有意差なし | A:112 (5%), B:108 (5.1%), p=0.89 | action: continue, reason: not_significant |
| 3 | B勝利 | A:167 (4.2%), B:171 (6.4%), p=0.032 | action: promote_and_start_new, winner: B |
| 4 | A勝利 | A:180 (7.1%), B:175 (4.8%), p=0.041 | action: promote_and_start_new, winner: A |
| 5 | LLMコピーにコアバリュー | - | コピーに "nudge", "reminder" 含まない |
| 6 | RevenueCat API エラー | 500 | Slack にエラー通知、リトライなし |

---

## 初期セットアップ手順

### 1. RevenueCat で初回 Experiment 作成

1. RevenueCat Dashboard → Experiments
2. "New Experiment" → Type: "Paywall design"
3. Variant A: 現行 Offering
4. Variant B: Candle原則に基づく新 Offering 作成
   - タイトル: "Your Growth Companion"
   - Bullets:
     - 📈 30日間の成長をグラフで確認
     - 🎯 行動パターンから最適なタイミングを提案
     - ⚙️ Nudge の頻度とスタイルをカスタマイズ
5. Traffic split: 50/50
6. Start experiment

### 2. VPS スキル作成

```bash
mkdir -p /home/anicca/.openclaw/workspace/skills/paywall-experiment-loop
# SKILL.md を作成
```

### 3. Cron 登録

```bash
openclaw cron add paywall-experiment-loop
```

---

## 成功指標

| Metric | 目標 |
|--------|------|
| Paywall CVR | 4.2% → 8% (6ヶ月) |
| 実験サイクル | 2-3週/実験 |
| 人間介入 | 月1回のレビューのみ |

---

## リスクと対策

| リスク | 対策 |
|--------|------|
| RevenueCat API 変更 | エラー時 Slack 通知、手動フォールバック |
| LLM がコアバリュー含むコピー生成 | 禁止ワードリストでフィルタ |
| 長期間有意差出ない | 3週間後に別切り口で新実験提案 |
| CVR 悪化 | 前回勝者にロールバック可能な設計 |

---

## Paywall デザイン → RevenueCat 投入フロー（調査結果）

### 調査背景

Treatment A の HTML デザインを RevenueCat に投入する最短経路を調査した。
調査方法: サブエージェント2本を並列実行（RC Figma plugin 深堀り + RC API 代替経路）。

### 確定した事実（ソース付き）

| # | 事実 | ソース |
|---|------|--------|
| 1 | RC Figma Plugin は **Auto Layout 必須** | RC 公式ドキュメント「Your paywall designs must use Figma auto layout to be imported correctly.」 |
| 2 | `html-to-design` は CSS flexbox を Figma Auto Layout に**確実には変換しない** | Figma html-to-design GitHub / コミュニティレポート |
| 3 | RC API v2 `POST /paywalls` は `offering_id` のみ受け付ける。**コンポーネントツリーの書き込みAPIは存在しない** | RC API v2 公式スキーマ `components_config: additionalProperties: true`（スキーマレス） |
| 4 | `mcp_RC_create_design_system_paywall_generation_job` が存在する。**デザインシステム JSON を渡すと AI が Paywall を自動生成**する（非公式エンドポイント） | RC MCP ツール定義 |
| 5 | `figmaselector=.paywall` URL パラメータで DOM 要素だけを Figma にキャプチャできる（430×932 に収まる） | Figma html-to-design ドキュメント |
| 6 | HTML 要素の `id` 属性が Figma レイヤー名になる。RC plugin は `Purchase Button` / `Footer` 等の**特定レイヤー名を認識**する | RC Figma plugin layer naming spec |
| 7 | フレームサイズの公式仕様はない。業界標準は **390×844**。RC はレスポンシブにレンダリングする | RC コミュニティ / 実例調査 |

### なぜ html-to-design → RC plugin が失敗したか

```
問題の連鎖:
1. ブラウザ viewport が 1502px → figmaselector なしでキャプチャ → 1502×932 になる
2. CSS flexbox は html-to-design で Auto Layout に変換されない（フラットなビジュアルレンダー）
3. Auto Layout がない Figma フレームは RC plugin がインポートできない
```

### 解決策（決定）: RC AI自動生成

**`mcp_RC_create_design_system_paywall_generation_job` がプライマリ。エージェントが完全自動実行。Dais の GUI 操作ゼロ。**

| ステップ | 担当 | 所要時間 |
|---------|------|---------|
| 1. 新 Offering 作成 (`mcp_RC_create_offering`) | エージェント | 1分 |
| 2. `$rc_monthly` パッケージ作成・product 紐付け | エージェント | 1分 |
| 3. `mcp_RC_create_design_system_paywall_generation_job` 実行 | エージェント | 非同期（30秒〜2分） |
| 4. `GET /v2/projects/{project_id}/paywalls` でジョブ完了確認 | エージェント | ポーリング |
| 5. RC Dashboard でプレビュー確認 → Experiment 作成 | Dais | 5分 |

**実行済み記録:**
- Offering: `ofrng4c8d1f9d48` (`anicca_paywall_ai_v1`)
- Paywall: `pwd08b47e7c59f464d` ("Anicca Paywall AI v1 — Candle Paywall")
- ジョブ ID: `pwjbeb75b3ed40f24d33af49e7cdc014358c`
- RC Dashboard: `https://app.revenuecat.com/projects/projbb7b9d1b/paywalls/pwd08b47e7c59f464d`

**ジョブステータス確認方法（MCPに専用ツールなし → v2 paywalls list で代替）:**

```bash
# paywalls list でジョブ完了を確認（offering_id が一致するエントリが出たら完了）
curl -s "https://api.revenuecat.com/v2/projects/projbb7b9d1b/paywalls" \
  -H "Authorization: Bearer $REVENUECAT_V2_SECRET_KEY" | python3 -m json.tool
```

**Anicca デザインシステム JSON（確定版）:**

```json
{
  "visual_language": {
    "color_palette": {
      "primary_brand_color": "#C9B382",
      "secondary_brand_color": "#2C2A28",
      "accent_cta_color": "#C9B382",
      "background_colors": ["#F5F3ED", "#EDE9E0"],
      "palette_mood": "warm sand, zen rock garden, morning light through rice paper"
    },
    "typography": {
      "headline_font_family": "SF Pro Display",
      "body_font_family": "SF Pro Text",
      "typographic_style": "large confident headline, minimal body, generous whitespace"
    },
    "illustration_and_imagery_style": {
      "primary_style": "zen minimalism — stacked river stones, ripple rings in sand",
      "iconography_style": "thin line icons, subtle and contemplative"
    }
  },
  "tone_of_voice": {
    "primary_tone": "calm and wise",
    "secondary_tone": "warm and encouraging",
    "communication_style_summary": "Ancient wisdom in modern language. Never preachy, never urgent."
  },
  "content_strategy": {
    "premium_feature_highlights": [
      "30-day insight reports — understand your patterns",
      "Progress growth graph — see how far you've come",
      "Nudge frequency & timing customization",
      "AI-personalized wisdom for your specific struggles"
    ]
  }
}
```

**廃止 Approach（参考アーカイブ）: HTML → Figma → Auto Layout → RC plugin**

| 理由 | 詳細 |
|------|------|
| `html-to-design` が Auto Layout を生成しない | CSS flexbox → フラット絶対座標変換。RC plugin がエラー |
| Figma REST API は read-only | Auto Layout を API 経由で追加不可 |
| Figma Plugin API はエディタ内のみ | ヘッドレス実行不可 |
| **→ Dais の手動 GUI 操作が必要 = 採用しない** | AI生成で完全自動化が実現するため廃止 |

### Treatment A デザイン資産

| 項目 | パス / 値 |
|------|----------|
| HTML ソース | `/tmp/anicca-paywall-preview.html`（= v2。QA済み） |
| QA スクリーンショット | `/tmp/paywall-qa-v2.png`（Visual QA 8.5/10） |
| 解像度 | 430×932 px |
| ブランドカラー | bg `#F5F3ED`, gold `#C9B382`, headline `#2C2A28`, subhead `#7a7875` |
| RC project | `projbb7b9d1b` |

### RC Figma Plugin が認識する必須レイヤー名

| レイヤー名 | 役割 | HTML id |
|----------|------|---------|
| `Purchase Button` | 購入ボタン | `id="Purchase Button"` |
| `Footer` | キャンセル・規約テキスト行 | `id="Footer"` |
| `Package` | プランカード（複数プランある場合） | `id="Package"` |

---

## Changelog

- 2026-02-12: v1.0 初版作成
- 2026-02-24: v1.1 Figma/RC 投入フロー調査結果を追記（サブエージェント2本による深堀り調査）
- 2026-02-24: v1.2 RC AI自動生成をプライマリに昇格。Figma approach を廃止・アーカイブ。初回生成実績記録（pwd08b47e7c59f464d）
