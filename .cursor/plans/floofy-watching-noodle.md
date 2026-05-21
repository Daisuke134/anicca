# Paywall A/B クローズドループ v2 — 3日ごと人間確認フロー

> **Spec-Driven Development (SDD) — GATE 1 Spec**
> 対象スキル: `.cursor/skills/paywall-ab/SKILL.md`（Mac Mini 稼働中）

---

## 概要（What & Why）

### なぜ変えるか

| 現在の問題 | 新しいアプローチ |
|-----------|----------------|
| 週1回（月曜 9am）の自動評価 — 3日でトレンドが見えても何もしない | **3日ごと**に Anicca が「結果確認してください」と Slack で聞く |
| RC Experiments API が未公開 → 自動取得不可 | ユーザーが RC Dashboard で確認 → Anicca に報告（Human-in-the-loop） |
| 勝者が決まっても新バリアントは手動で作っていた | 勝者分析 → コピー生成 → Pencil MCP でペイウォール更新 → 全自動 |
| Railway 依存（OSS展開不可） | **Railway 不使用** — RC MCP + Pencil MCP のみ |

### フロー全体像

```
実験開始（paywall-ab setup）
  ↓
3日後 7am: Anicca → Slack
  "📊 Day 3 of experiment prexpXXX
   A: anicca offering (現行)
   B: anicca_paywall_ai_v2 (新しいコピー)
   ━━━━━━━━━━━━━━━━━━━
   RC Dashboard で確認してください:
   https://app.revenuecat.com/...
   ━━━━━━━━━━━━━━━━━━━
   結果を教えてください:
   - 「A勝ち」「B勝ち」「まだ早い」"
  ↓
ユーザーが Slack で返信
  ↓
パターン1: 「まだ早い」→ 3日後にまた聞く（Day 6 / Day 9 ...）
パターン2: 「A勝ち」or「B勝ち」→ 勝者分析フェーズへ
  ↓
勝者分析（Anicca が自動）
  RC MCP で勝者 Offering の Paywall 詳細を取得
  → 「Aが勝った理由: タイトルのシンプルさ + 具体的な数字（3本固定）」
  → 次のバリアント仮説を生成
  ↓
新バリアント生成
  Pencil MCP で既存ペイウォールのテキストだけ変更
  ビジュアル（色・レイアウト・アイコン）は維持
  ↓
Slack 承認ゲート
  「新しいバリアント C を作りました。[プレビュー] 実験を開始しますか？」
  ↓
ユーザー「はい」→ RC に新 Offering + Experiment 作成 → Day 1 リセット
```

---

## 受け入れ条件

| # | 条件 | 確認方法 |
|---|------|---------|
| 1 | 実験開始から 3 日後 7am に Slack メッセージが届く | Mac Mini cron 手動トリガーでテスト |
| 2 | メッセージに実験ID・Variant A/B の内容・RC URL が含まれる | Slack メッセージ目視 |
| 3 | 「まだ早い」返信 → 3日後にまた同じメッセージが届く | 返信後にcron手動実行 |
| 4 | 「A勝ち」返信 → 勝者分析テキストが Slack に流れる | 返信後に自動実行される |
| 5 | 新バリアントのテキスト案（3パターン）が Slack に届く | 同上 |
| 6 | ユーザーが「はい」→ RC に新 Offering 作成される | RC MCP で確認 |
| 7 | 新しい実験が RC に作成される | RC Dashboard または MCP で確認 |

---

## As-Is / To-Be

### cron スケジュール

| | 現在 (As-Is) | 変更後 (To-Be) |
|--|-------------|--------------|
| タイミング | 毎週月曜 9:00 JST | 実験開始日から **3日ごと 7:00 JST** |
| 動作モード | `evaluate`（自動判定） | `check_in`（ユーザーに確認を促す） |
| Mac Mini 登録場所 | `/Users/anicca/.openclaw/cron/jobs.json` | 同じファイル、スケジュール変更のみ |

### paywall-ab スキルのモード追加

| モード | 現在 | 変更後 |
|--------|------|--------|
| `setup` | ✅ 実験セットアップ | ✅ 変更なし |
| `evaluate` | 自動判定 + 次バリアント生成 | **削除**（3日チェックインに置き換え） |
| `check_in` | ❌ なし | ✅ **新規追加** — 3日ごとに Slack 確認を送る |
| `analyze` | ❌ なし | ✅ **新規追加** — 勝者分析 + 新コピー生成 |
| `create_variant` | ❌ なし | ✅ **新規追加** — Pencil MCP でテキスト更新 + RC 新 Offering 作成 |

### 新モード `check_in` のロジック

```
1. RC MCP で現在の実験情報を取得
   mcp_RC_get_chart_data(experiment_id) → conversion rate A vs B
2. 実験開始からの経過日数を計算
3. Slack に Day X メッセージを送信（テンプレート下記）
4. Anicca は返信を待つ（reactive モード）
```

### 新モード `analyze` のロジック（ユーザー返信後に実行）

```
入力: winner = "A" or "B"
1. RC MCP で勝者・敗者の Offering 詳細を取得
   mcp_RC_list_offerings + 各 Offering の Paywall ID → テキスト内容
2. LLM 分析: 「なぜ勝者のコピーが響いたか」（3つの仮説）
3. 新コピー仮説を生成（勝者の要素を保持 + 改善点を追加）
4. Slack に分析結果 + 新コピー案 3 パターンを送信
```

### 新モード `create_variant` のロジック（ユーザー「はい」後に実行）

```
入力: copy_pattern = 1 or 2 or 3（ユーザーが選んだパターン）
1. Pencil MCP で現在の Paywall テンプレートを開く
   - ビジュアル（色・アイコン・レイアウト）は変えない
   - タイトル・サブタイトル・CTA テキストのみ差し替え
2. RC MCP で新 Offering 作成 (mcp_RC_create_offering)
3. RC MCP で新 Experiment 作成
4. Slack 承認ゲート（slack-approval スキル）
5. 承認後: cron の Day カウンターをリセット（次の check_in は3日後）
```

---

## テストマトリックス

| # | To-Be | テスト名 | カバー |
|---|-------|----------|--------|
| 1 | 3日後 7am に check_in メッセージ送信 | `test_checkin_message_sent_day3` | OK |
| 2 | 「まだ早い」→ 何もしない | `test_not_yet_response_no_action` | OK |
| 3 | 「A勝ち」→ analyze モードが走る | `test_winner_triggers_analyze` | OK |
| 4 | analyze が勝者/敗者のコピーを取得して比較 | `test_analyze_fetches_offering_texts` | OK |
| 5 | create_variant が Pencil MCP でテキスト差替え | `test_create_variant_updates_paywall_text` | OK |
| 6 | create_variant が RC に新 Offering 作成 | `test_create_variant_creates_rc_offering` | OK |
| 7 | Day カウンターが正しくリセットされる | `test_day_counter_reset_after_new_experiment` | OK |

---

## 境界（触らないもの）

| 触らない | 理由 |
|---------|------|
| `apps/api/` — Railway バックエンド | 今回の変更には不要。OSS 展開のため依存しない |
| `aniccaios/` — iOS アプリ | ペイウォール内容は RC 経由で変わる。Swift コード変更不要 |
| Mixpanel 送信ロジック | 実装済み。`rc_trial_started_event` + `paywall_viewed` で自動収集 |
| Paywall のビジュアルデザイン（色・アイコン・レイアウト） | 勝者の「デザインが勝因」の場合に備えて保持 |
| paywall-ab `setup` モード | 実験セットアップは現行で動いている |

---

## E2E 判定

| 項目 | 値 |
|------|-----|
| UI変更 | なし（iOS アプリ画面変更なし） |
| 新画面 | なし |
| 結論 | Maestro E2E 不要。Slack メッセージ + RC MCP で手動確認 |

---

## 変更ファイル

| # | ファイル | 変更内容 |
|---|---------|---------|
| 1 | `.cursor/skills/paywall-ab/SKILL.md` | `check_in` / `analyze` / `create_variant` モード追加、`evaluate` モード削除 |
| 2 | `/Users/anicca/.openclaw/skills/paywall-ab/SKILL.md`（Mac Mini） | 同上を Mac Mini に反映 |
| 3 | `/Users/anicca/.openclaw/cron/jobs.json`（Mac Mini） | スケジュールを毎週月曜 → 3日ごと 7am に変更 |

---

## 実行手順（実装後）

```bash
# 1. ローカルで SKILL.md を更新
# (SKILL.md 編集)

# 2. Mac Mini に反映
scp .cursor/skills/paywall-ab/SKILL.md anicca@100.99.82.95:/Users/anicca/.openclaw/skills/paywall-ab/SKILL.md

# 3. Mac Mini の cron を更新（3日ごとに変更）
ssh anicca@100.99.82.95 "cat /Users/anicca/.openclaw/cron/jobs.json"
# schedule を "0 7 */3 * *" に変更

# 4. check_in を手動トリガーしてテスト
ssh anicca@100.99.82.95 "export PATH=/opt/homebrew/bin:/opt/homebrew/sbin:\$PATH && \
  openclaw agent --skill paywall-ab --mode check_in --deliver"

# 5. Slack で結果確認 → 「A勝ち」or「B勝ち」で返信してフロー確認
```

---

## Slack メッセージテンプレート（check_in）

```
📊 Paywall 実験 Day {N}

実験ID: {experiment_id}
━━━━━━━━━━━━━━━━━━━━
Variant A（現行）: {offering_a_name}
  タイトル: {title_a}
  CTA: {cta_a}

Variant B（テスト中）: {offering_b_name}
  タイトル: {title_b}
  CTA: {cta_b}
━━━━━━━━━━━━━━━━━━━━
📌 RC Dashboard で CVR を確認してください:
https://app.revenuecat.com/projects/projbb7b9d1b/experiments/{experiment_id}

結果を教えてください:
• 「A勝ち」
• 「B勝ち」
• 「まだ早い」（3日後にまた確認）
```
