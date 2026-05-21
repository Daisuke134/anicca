# Mobile App Factory — 仕様書

**作成日:** 2026-02-21
**更新日:** 2026-02-23
**ステータス:** 計画中（実装未開始）
**目的:** AIエージェントが自律的にアプリをビルド・提出・イテレーションし、人々の苦しみを減らしながら収益を最大化するパイプラインを構築する。

---

## ビジョン

- **Anicca（OpenClaw, Mac Mini）** = プランナー。データを見て何をテストするか決める。cron持ち。
- **Claude Code** = ワーカー。Aniccaに呼ばれて実際に実行する。
- **トリガー方式:** Anicca → `exec` → `claude --print "skill-name: ..."` → Claude Codeが実行
- **全アプリが毎日イテレーション。** 人間は何もしなくてよい。

---

## 全Cron + Skill 一覧

| # | 名前 | 種別 | 担当 | 時刻 | 目的 |
|---|------|------|------|------|------|
| C1 | `screenshot-ab` | Cron + Skill | **Anicca** | 毎朝 06:00 JST | スクショA/B実験の監視・判断・実行（自己完結） |
| C2 | `paywall-ab` | Cron + Skill | **Anicca** | 毎朝 06:01 JST | PaywallA/B実験の監視・判断・実行（自己完結） |
| C3 | `app-factory` | Cron + Skill | **Anicca** | 毎晩 23:00 JST | トレンド検索 → spec生成 → Claude app-shipをトリガー |
| C4 | `larry` | Cron + Skill | **Anicca**（既存） | 毎日 19:00 JST | TikTok投稿（詳細は既存skill参照） |
| S1 | `app-ship` | Skill | **Claude Code** | on-demand（C3から呼ばれる） | コード生成 → greenlight → fastlane submit |
| S2 | `onboarding-ab-execute` | Skill | **Claude Code** | on-demand（later scope） | feature flag → TestFlight |

---

## 接続図

```
06:00 JST  Anicca [screenshot-ab] → 自己完結（asc analytics download + process_screenshots.py + ASC API）
06:01 JST  Anicca [paywall-ab]    → 自己完結（Mixpanel segmentation + RC API）

19:00 JST  Anicca [larry] → TikTok投稿（既存）

23:00 JST  Anicca [app-factory]
               ├─ トレンド検索 → spec生成
               ├─ exec → Claude [app-ship] × N アプリ（順次）
               └─ larry呼び出し（Day 1 TikTok）
```

---

## C1: `screenshot-ab`（Anicca Cron + Skill、自己完結）

### 概要

- 毎朝06:00 JSTに自動起動
- 実験は常に走っている（空白期間なし）
- スクショ生成: **Phase 1 = process_screenshots.py（l.md Bible PIL）**（実画面 + ヘッドライン差し替え）、**Phase 2 = Pencil MCP**（Phase 1で改善しない場合、全体デザイン刷新）
- CVR計測: `asc analytics download` で Impression / Tap を毎日自動取得。手動判断不要。
- 停止基準: Treatment CVR が Control CVR より20%以上高い状態が7日継続 → 自動 winner 判定

### スキル構成

| スキル | 役割 | 参照 |
|--------|------|------|
| `xcrun simctl io booted screenshot` | RAW PNG取得のみ | macOS標準 |
| `process_screenshots.py` + `screenshots.yaml` | PIL合成（キャンバス+テキスト+ベゼル）— l.md Bible 100% | `docs/screenshots/scripts/` |
| `asc analytics download` | Impression / Tap のCSV自動取得 | 実稼働確認済み（2026-02-22） |
| Pencil MCP | Phase 2: 全体デザイン刷新 | MCP内蔵 |

### CVR計算式（確定）

```
install CVR = Tap / Impression × 100

ベースライン（実験開始前 / 2026-02-22 全体）:
  Impression: 5,760
  Page view:  5,361
  Tap:          119
  before_CVR: 119 / 5760 = 2.1%

PPO実験中（Control vs Treatment の分割）:
  → asc analytics download では取れない（Overall のみ）
  → asc product-pages experiments treatments list --experiment-id "..." で取得する
  → experiments list でExperiment ID を確認してから取得

判定ロジック:
  Treatment CVR / Control CVR > 1.2（20%以上向上） かつ 7日以上継続 → 自動 winner
```

### スクショ生成方式（確定: PIL）

```
Reve（text-to-image）→ 実アプリUIを捏造する → Apple審査NG → 使わない
PIL → 実simctlスクショのヘッドライン部分だけ書き換える → 実画面保持 → 正解

フロー:
  xcrun simctl io booted screenshot raw.png
  → asc screenshots frame（Koubou: デバイスフレーム追加）
  → PIL: ヘッドラインエリアを背景色で塗り潰し → 新ヘッドラインを描画
  → asc screenshots upload
```

### ヘッドライン生成方式（改善案）

```
現状: Queue テーブルにハードコード（ダイスが手書き）
改善: Anicca が Claude で毎回生成
  入力: before_CVR / 前回負けたヘッドライン / ペルソナ定義 / AppRadar BP
  出力: 新しいヘッドライン3本
```

### memory 構造（Anicca memory）

```json
{
  "experiment_id": "ppo_abc123",
  "start_date": "2026-02-21",
  "queue_position": 0,
  "phase": "PIL",
  "control_label": "現在のデフォルトスクショ3枚",
  "treatment_label": "Queue 0: ペイン直撃ヘッドライン",
  "before_cvr": 2.1,
  "analytics_request_id": "04c74879-547f-4e35-b231-1fafd485801d"
}
```

### フロー

```
06:00 起動
 │
 ├─ Anicca memory 読む
 │    └─ experiment_id / start_date / queue_position / phase / analytics_request_id
 │
 ├─ asc analytics download → 最新のImression/Tap CSVを取得
 │    Control CVR  = Tap(control) / Impression(control) × 100
 │    Treatment CVR = Tap(treatment) / Impression(treatment) × 100
 │
 ├─ ASC API で実験状態確認
 │    GET /v2/appStoreVersionExperiments/{id}
 │    └─ state: RUNNING / STOPPED / なし
 │
 ├─ 経過日数計算（today - start_date）
 │
 ├─ 判断
 │    experiment_id なし                           → START
 │    7日未満                                      → skip
 │    Treatment CVR > Control CVR × 1.2 かつ 7日+ → 自動 WINNER
 │    Treatment CVR <= Control CVR かつ 14日+      → 自動 NULL
 │    90日経過（Apple上限）                         → 自動 NULL → 次へ
 │
 ├─ [WINNER]
 │    勝者をASCのdefaultスクショに適用 → PPO実験停止
 │    → queue_position +1 → START
 │
 ├─ [NULL]
 │    PPO実験停止 → queue_position +1 → START
 │
 ├─ [START]
 │    Phase PIL: ベーススクショ3枚 + ヘッドライン差し替え（process_screenshots.py / l.md Bible）
 │    Phase Pencil: 全体デザイン刷新（Pencil MCP）
 │    → asc screenshots upload → PPO実験作成（50/50）→ memory更新
 │
 └─ Slack サマリ投稿（CVR数字付き）
```

### Slack 日次レポート（output）

```
[screenshot-ab] Day 14 🔬
Queue 0 / Phase PIL: "6 Years. 10 Apps. Still Nothing Changed."
実験ID: ppo_abc123 | 開始: 2026-02-21
Control CVR: 1.2% | Treatment CVR: 1.8% | +50% ↑
→ まだ7日。継続中。
```

### Phase 1: process_screenshots.py（l.md Bible PIL）でスクショ3枚を生成する流れ

ソース: l.md（KOE app日本人開発者） / 核心の引用: 「撮影からストア提出用の画像生成まで、全部自動でやってくれたら楽なのに... XCUITest + Python Pillowを使って、撮影から加工まで完全自動化」

**考え方: ベーススクショ（XCUITest撮影の実画面）に対して process_screenshots.py でヘッドライン差し替え。Reve（text-to-image）禁止 — 実アプリUIを捏造するためApple審査NG。**

```
1. xcrun simctl io booted screenshot docs/screenshots/raw/{screen_id}.png
   └─ シミュレータからアプリの実画面を取得（raw PNG）
   ※ または XCUITest + xcresulttool extract（l.md Step 2-3と同等）

2. screenshots.yamlのcaption.titleを実験ヘッドラインに更新
   例: "6 Years.\n10 Apps.\nStill Nothing Changed."

3. python3 docs/screenshots/scripts/process_screenshots.py
   └─ l.md process_screenshots.py がキャンバス+テキスト+ベゼル合成
   └─ 出力: docs/screenshots/processed/{screen_id}.png（1290×2796）
   ※ Koubou（asc screenshots frame）禁止。ベゼルはl.md内部で処理。
   ※ Reve（infsh app run falai/reve）禁止。PIL で実画面にテキスト描画。

4. スクショ1・2・3を同様に生成（ヘッドラインだけ変える）

5. asc screenshots upload → PPO実験作成（50/50）

6. Anicca memory 更新（experiment_id / start_date / before_cvr）
```

### Phase 2: Pencil MCP でスクショ3枚を生成する流れ（Phase 1で改善しない場合）

```
1. Pencil MCP open_document("new")
2. Pencil MCP get_guidelines("mobile")
3. Pencil MCP batch_design → スクショ1・2・3のレイアウトをゼロからデザイン
4. Pencil MCP get_screenshot → PNG export（1290×2796）× 3枚
5. asc screenshots upload → PPO実験作成（50/50）
6. Anicca memory 更新（phase: "Pencil"）
```

### テストQueue

ソース: AppRadar / 「Lead with clear benefit/result → social proof → core flow」（AIDA フレームワーク）

| Queue # | Phase | 変えるもの | スクショ1（benefit） | スクショ2（social proof） | スクショ3（core flow） |
|---------|-------|-----------|---------------------|------------------------|----------------------|
| 0 | PIL | ヘッドラインのみ | "6 Years. 10 Apps. Still Nothing Changed." | "3,000+ People Finally Broke The Loop" | アプリのメイン画面 |
| 1 | PIL | ヘッドラインのみ | "Why Do You Keep Failing The Same Habit?" | "Your Brain Isn't Broken. Your App Is." | アプリのメイン画面 |
| 2 | PIL | ヘッドライン + 背景色 | "What If Day 1 Didn't Feel Like Day 1 Again?" | "AI That Texts You Before You Give Up" | アプリのメイン画面 |
| 3 | Pencil MCP | 全体デザイン刷新 | 新レイアウト・新配色 | 新レイアウト | 新レイアウト |

---

## C2: `paywall-ab`（Anicca Cron + Skill、自己完結）

### 概要

- 毎朝06:01 JSTに自動起動
- 実験は常に走っている（空白期間なし）
- RevenueCat Experiment で Offering を差し替える
- CVR計測: Mixpanel で `onboarding_paywall_viewed` → `rc_trial_started_event` を RC実験プロパティでセグメント分け → Trial CVR 自動計算。手動判断不要。
- 停止基準: Treatment Trial CVR が Control Trial CVR より20%以上高い状態が7日継続 → 自動 winner 判定

### Paywall デザイン生成方式（2 アプローチ）

**現在採用: Approach B（Pencil MCP）**

| | **Approach A: RC AI 生成** | **Approach B: Pencil MCP（採用）** |
|---|---|---|
| **生成方法** | `mcp_RC_create_design_system_paywall_generation_job` | Pencil MCP（screenshot-creator スキルパターン） |
| **デザイン制御** | RC サーバー任せ（JSON ヒントのみ） | エージェントが完全制御（色・コピー・レイアウト） |
| **出力** | RC Dashboard 上の Draft Paywall | ローカル PNG（`/workspace/screenshots/`）|
| **RC Publish** | **手動必須（API なし）** | **手動必須（API なし）** |
| **Experiment 開始** | **手動必須（API なし）** | **手動必須（API なし）** |
| **Dais の作業** | RC Dashboard で Publish + Experiment 開始 | RC Dashboard で PNG アップロード + Publish + Experiment 開始 |
| **参考** | — | `screenshot-creator` SKILL.md（5エージェント構造） |

**RC API の制約（確定調査済み）:**
- RC API v2 Paywall エンドポイント: list / create / get / delete の4つのみ。**Publish エンドポイント存在しない。**
- RC API v2 に Experiment 管理エンドポイント存在しない（レスポンスフィールドとして出るのみ）。
- **→ Paywall Publish と Experiment 開始は毎回 Dais が RC Dashboard で手動実行（約2分の作業）。**

### Approach B: Pencil MCP エージェント構成（採用）

screenshot-creator スキル（`/tmp/claude-code-plugin/screenshot-creator/skills/screenshot-creator/SKILL.md`）を参考に、paywall 用に3エージェント構成で実装する。

| エージェント | 役割 | 手段 |
|-------------|------|------|
| `paywall-director` | デザイン戦略・abtest.design 参照・Queue コピー決定 | WebSearch（abtest.design） |
| `paywall-designer` | Pencil MCP でPaywall UI 構築 → PNG 保存 | Pencil MCP (batch_design, get_screenshot) |
| `paywall-reviewer` | 品質レビュー・CRO チェック・スコアリング | Pencil MCP (get_screenshot) |

**参照リソース:**
- `abtest.design/patterns/paywall-free-trial` — 実際に勝ったA/Bテスト Before/After（Blinkist +23%, Moonly +39%, Headspace +10%等）
- `screenshot-creator` agents/ — Pencil MCP 操作パターン（screenshot-designer.md）

### スキル構成

| スキル | 役割 | インストール先 |
|--------|------|-------------|
| `ab-test-setup` | A/Bテスト設計原則（95%信頼区間・サンプルサイズ計算・no-peeking） | `.agents/skills/ab-test-setup/`（skill.sh 7,600 installs） |
| `paywall-upgrade-cro` | Paywall CRO ベストプラクティス（トリガー設計・コピー・CTA改善） | `.agents/skills/paywall-upgrade-cro/`（skill.sh 212 installs） |
| `growth-experimenter` | ICEスコア優先度・AARRRフレームワーク・仮説テンプレート | `.agents/skills/growth-experimenter/`（skill.sh 52 installs） |
| `mcp__revenuecat__*` | Offering 作成・Package 作成・Product 紐付け（Experiment 管理ツールなし） | MCP内蔵 |
| Pencil MCP | Treatment Paywall UI をローカルでデザイン → PNG 出力 | MCP内蔵 |
| Mixpanel MCP | Trial CVR per variant 取得（RC→Mixpanel integration が有効な場合） | MCP内蔵 |

**RC MCPギャップ（確定）:** Experiment 開始・停止・一覧取得ツールは RC MCP に存在しない。Experiment 管理は Dais が RC Dashboard で手動実行。

### CVR計算式（確定）

```
Trial CVR = rc_trial_started_event / onboarding_paywall_viewed × 100

データソース（確定）:
  RC Dashboard: Experiment Results ページでバリアント別 Trial CVR を目視確認可能
  RC v2 API:    aggregate（バリアント別集計）エンドポイントなし → 自動取得不可
  Mixpanel MCP: RC→Mixpanel integration が有効な場合、$rc_experiment_id / $rc_variant
                プロパティでセグメント分け → Trial CVR per variant 自動計算可能

自動化方式（確定: Mixpanel MCP）:
  前提: RC→Mixpanel integration が有効（`.openclaw/.env` の RC_MIXPANEL_SECRET で確認）
  セグメントキー: $rc_experiment_variant_assigned → "control" / "treatment"
  Control Trial CVR  = rc_trial_started_event(control) / paywall_viewed(control) × 100
  Treatment Trial CVR = rc_trial_started_event(treatment) / paywall_viewed(treatment) × 100

実測値（Anicca 2026-02-22, integration前ベースライン）:
  onboarding_paywall_viewed: 92
  rc_trial_started_event:      1
  Trial CVR: 1 / 92 = 1.1%

A/Bテストの判定（ab-test-setup BP準拠）:
  Treatment Trial CVR / Control Trial CVR > 1.2（20%以上向上） かつ 7日以上 → WINNER
  Treatment Trial CVR <= Control Trial CVR かつ 14日+                        → NULL
  最低サンプルサイズ: 各バリアント 500 paywall_viewed 以上（95%信頼区間）
```

### ストレージ構造（全パス確定）

```
/Users/anicca/.openclaw/workspace/
│
├── paywall-ab-state.json          ← 今何をテストしているか（遷移時に上書き）
├── paywall-ab-history.jsonl       ← 全テスト記録（append-only、消えない）
│
└── screenshots/
    ├── paywall_control_latest.png      ← Control の最新スクショ（毎回上書き）
    ├── paywall_treatment_latest.png    ← Treatment の最新スクショ（毎回上書き）
    ├── paywall_control_2026-02-23.png  ← 日付付きアーカイブ
    └── paywall_treatment_2026-02-23.png
```

読み書き: OpenClaw `exec` + `cat`/`jq` で直接 read/write。スクショは Maestro が保存。

```json
// paywall-ab-state.json
{
  "experiment_id": "rc_exp_abc123",
  "start_date": "2026-02-21",
  "queue_position": 0,
  "control_offering_id": "ofrng78a01eb506",
  "treatment_offering_id": "ofrng_treatment_xxx",
  "treatment_paywall_id": "pw_abc123",
  "control_label": "Start Your Free Week",
  "treatment_label": "Queue 0: Try Free for 7 Days",
  "before_trial_cvr": 1.1,
  "control_screenshot": "/Users/anicca/.openclaw/workspace/screenshots/paywall_control_latest.png",
  "treatment_screenshot": "/Users/anicca/.openclaw/workspace/screenshots/paywall_treatment_latest.png",
  "winning_patterns": []
}

// paywall-ab-history.jsonl（1行=1イベント）
{"ts":"2026-02-21T06:01:00Z","event":"START","queue":0,"experiment_id":"rc_exp_abc123","paywall_id":"pw_abc123","label":"Try Free for 7 Days","screenshot":"/Users/anicca/.openclaw/workspace/screenshots/paywall_treatment_2026-02-21.png"}
{"ts":"2026-03-07T06:01:00Z","event":"WINNER","queue":0,"treatment_cvr":2.3,"control_cvr":1.1,"lift":109,"winning_element":"headline_copy"}
{"ts":"2026-03-07T06:01:05Z","event":"START","queue":1,"experiment_id":"rc_exp_def456","paywall_id":"pw_def456","label":"Begin My Journey","screenshot":"/Users/anicca/.openclaw/workspace/screenshots/paywall_treatment_2026-03-07.png"}
```

### フロー

```
06:01 起動
 │
 ├─ Anicca memory 読む（/Users/anicca/.openclaw/workspace/paywall-ab-state.json）
 │    └─ experiment_id / start_date / queue_position / before_trial_cvr
 │
 ├─ Mixpanel MCP で Trial CVR per variant 取得（直近7日）
 │    セグメントキー: $rc_experiment_variant_assigned → "control" / "treatment"
 │    Control Trial CVR  = rc_trial_started_event(control) / paywall_viewed(control) × 100
 │    Treatment Trial CVR = rc_trial_started_event(treatment) / paywall_viewed(treatment) × 100
 │
 ├─ RC API（rc-api.sh）で実験状態確認
 │    ※ RC MCP に Experiment 管理ツールなし → revenuecat スキルの rc-api.sh を使う
 │    GET /v2/projects/{id}/experiments → 実験一覧取得
 │    GET /v2/experiments/{id} → state: RUNNING / STOPPED / DRAFT
 │
 ├─ 経過日数計算（today - start_date）
 │
 ├─ 判断
 │    experiment_id なし                                    → START
 │    7日未満                                               → skip
 │    Treatment CVR > Control CVR × 1.2 かつ 7日+          → 自動 WINNER
 │    Treatment CVR <= Control CVR かつ 14日+               → 自動 NULL
 │    90日経過（Apple上限）                                  → 自動 NULL → 次へ
 │
 ├─ [WINNER]
 │    勝者OfferingをRC defaultに設定 → 実験停止 → queue +1 → START
 │
 ├─ [NULL]
 │    実験停止 → queue +1 → START
 │
 ├─ [START]
 │
 │    ── ここから Anicca 自動（エージェントが全部やる）──
 │
 │    1. RC MCP で新 Treatment Offering 作成
 │         mcp__revenuecat__mcp_RC_create_offering
 │         └─ lookup_key: "anicca_treatment_q{queue_position}"
 │    2. RC MCP で Package 作成 + 既存商品紐付け
 │         mcp__revenuecat__mcp_RC_create_package（$rc_monthly）
 │         mcp__revenuecat__mcp_RC_attach_products_to_package
 │    3. Pencil MCP で Treatment Paywall デザイン生成（Approach B）
 │         paywall-director: Queue コピーを決定 + abtest.design 参照でデザイン戦略
 │         paywall-designer: Pencil MCP で .pen ファイルを新規作成
 │           → batch_design でPaywall UI 構築（Queue Variant コピーを使用）
 │           → get_screenshot で PNG export
 │           → /workspace/screenshots/paywall_treatment_latest.png に保存
 │           → /workspace/screenshots/paywall_treatment_{date}.png にアーカイブ
 │         paywall-reviewer: 品質スコア 7/10 以上を確認
 │    4. Control スクショ撮影（Maestro）
 │         iOS Simulator 起動 → Control offering 表示 → スクショ
 │           → /workspace/screenshots/paywall_control_latest.png に保存
 │    5. Slack に投稿（スクショ付き）
 │         「Treatment Paywall デザイン完成。RC Dashboard で以下の作業をお願いします。」
 │         [Control スクショ] [Treatment PNG]
 │         Treatment Offering ID: anicca_treatment_q{n}
 │         手順: ① RC Dashboard で Treatment Offering に PNG をアップロード
 │               ② Paywall を Publish
 │               ③ Experiment 作成（Control: anicca / Treatment: anicca_treatment_q{n} / 50:50）
 │               ④ Experiment 開始
 │    6. memory 更新（state 上書き + history append）
 │         treatment_offering_id / treatment_png_path / queue_position / status: "WAITING_DAIS"
 │
 │    ── ここから Dais 手動（RC Dashboard、約2分）──
 │
 │    7. [Dais 手動] RC Dashboard で Treatment PNG アップロード + Paywall Publish
 │         URL: https://app.revenuecat.com/projects/projbb7b9d1b/offerings/{offering_id}/paywall
 │    8. [Dais 手動] RC Dashboard で Experiment 作成 + 開始（50/50）
 │         URL: https://app.revenuecat.com/projects/projbb7b9d1b/experiments
 │    9. Dais が Slack で「実験開始した」と返信 → Anicca が state を "RUNNING" に更新
 │         experiment_id / start_date を state に記録
 │
 └─ [毎日 skip 時も]
      Mixpanel CVR 数字 + 両スクショ を Slack に投稿（日次レポート）
```

### Slack 日次レポート（output）

```
[paywall-ab] Day 14 🔬
Queue 0: "Try Free for 7 Days" vs "Start Your Free Week"
実験ID: rc_exp_abc123 | 開始: 2026-02-21
Control Trial CVR: 1.0% | Treatment Trial CVR: 1.5% | +50% ↑
→ まだ7日。継続中。

[画像: paywall_control_latest.png]   [画像: paywall_treatment_latest.png]
```

WINNER 時:
```
[paywall-ab] ✅ WINNER 確定
Queue 0: "Try Free for 7 Days" が勝利
lift: +109% (1.1% → 2.3%)  |  7日継続
→ Treatment を default に昇格 → Queue 1 スタート

[画像: 勝者 paywall_treatment_latest.png]
winning_element: headline_copy
次のテスト: Queue 1 "Begin My Journey"
```

### Pencil MCP Paywall デザイン仕様（[START] Step 3 で使う）

paywall-designer が Pencil MCP で構築する Paywall の仕様。screenshot-creator SKILL.md のガイドラインに準拠。

**デバイスサイズ:** iPhone 6.9" (430 × 932pt)

**レイアウト構成:**
```
┌────────────────────────┐
│  HeroArea（上40%）       │ ← アプリ名 + ビジュアル（シンプル）
├────────────────────────┤
│  BenefitArea（中30%）    │ ← Queue Variant コピー（3行: headline + sub×2）
├────────────────────────┤
│  PricingArea（下20%）    │ ← 価格 + CTA ボタン
└────────────────────────┘
```

**カラーパターン（Anicca ブランド準拠）:**
| 要素 | カラー |
|------|--------|
| 背景 | `#0A0A12`（deep navy） |
| ヘッドライン | `#F5E6C8`（warm sand） |
| サブテキスト | `#B8A888`（muted sand） |
| CTA ボタン | `#D4A853`（amber gold）|
| CTA テキスト | `#0A0A12` |

**Queue Variant コピー（BenefitArea に使う）:**

| Queue # | Headline | Sub1 | Sub2 |
|---------|---------|------|------|
| 0 | "Try Free for 7 Days" | "No charge until trial ends" | "Cancel anytime" |
| 1 | "Begin My Journey" | "Start your free week today" | "No commitment" |
| 2 | "Less than $0.33/day" | "That's cheaper than one coffee" | "7-day free trial" |
| 3 | "No Charge for 7 Days" | "Experience the full app free" | "Then $9.99/month" |

**参照（abtest.design Paywall & Free Trial 勝ちパターン）:**
- Blinkist "+23% trial signups": Free trial の仕組みを明確に見せる
- Moonly "+39% conversion": Annual のみ free trial でプレミアム感を演出
- Headspace "+10% conversion": Multi-intent onboarding → paywall 直結

### Approach A: RC AI 生成（参考、現在未採用）

`mcp_RC_create_design_system_paywall_generation_job` の `design_system` フィールドに毎回渡す JSON 定義。未採用理由: Publish API がなく毎回 Dashboard 操作が必要なため、Pencil MCP と手間が同じ。将来 RC が Publish API を公開したら Approach A に切り替える。

Queue ごとに変わるのは `content_strategy.premium_feature_highlights[0]`（= Queue のVariant コピー）のみ。

```json
{
  "app_context": {
    "app_name": "Anicca",
    "category": "Health & Fitness / Mental Wellness",
    "one_line_description": "Buddhist-inspired proactive behavior change agent"
  },
  "brand_identity": {
    "brand_mission": "苦しみを減らす（Reduce Suffering）",
    "brand_personality_archetype": "Sage / Caregiver",
    "core_values": ["compassion", "impermanence", "non-judgment"]
  },
  "target_audience": {
    "primary_user_persona": "25-35歳、6-7年間主体性欠如・自己嫌悪ループから抜け出せない人",
    "user_pain_points": ["習慣アプリ10個以上全部3日坊主", "朝起きられない", "自分との約束を破り続けている"],
    "user_needs_and_goals": ["誰かに引っ張ってほしい", "責められない小さな一歩", "変われる感覚"]
  },
  "tone_of_voice": {
    "primary_tone": "compassionate",
    "secondary_tone": "calm and grounded",
    "keywords_and_phrases": ["一緒に", "大丈夫", "小さくていい", "Try Free"],
    "communication_style_summary": "Buddhist gentle guide. Never blame. Short sentences. No pressure."
  },
  "problem_solution_fit": {
    "problem_statement": "意志力では変われない。6-7年間、同じ問題が続いている",
    "solution_statement": "AIが先に気づいて、小さな一歩をプロアクティブに提案する",
    "unique_selling_propositions": ["プロアクティブ（ユーザーが操作不要）", "7日間無料トライアル", "ジャッジなし"]
  },
  "content_strategy": {
    "key_content_themes": ["impermanence = change is possible", "compassion over discipline"],
    "premium_feature_highlights": ["<<Queue Variant コピーをここに入れる>>", "No charge for 7 days"]
  },
  "visual_language": {
    "color_palette": "deep navy, warm sand, soft amber gold",
    "typography": "clean sans-serif, calm and readable",
    "illustration_and_imagery_style": "minimal, breath-like, Japanese wabi-sabi"
  },
  "ui_patterns": {
    "button_style": "rounded corners, full-width, amber/gold CTA",
    "card_style": "soft shadow, generous whitespace",
    "overall_layout_philosophy": "breathing room, nothing cluttered, one clear action"
  }
}
```

### テストQueue（Aniccaのpaywall）

ソース: `paywall-upgrade-cro`（skill.sh 212 installs）+ `ab-test-setup`（skill.sh 7,600 installs）/ CRO原則「見出しコピーのテストが最も高インパクト。次にCTA文言、価格フレーミング。」/ ICEスコア: 見出し=高Impact×高Confidence×高Ease → 最優先

| Queue # | 変えるもの | Control | Variant |
|---------|-----------|---------|---------|
| 0 | 見出しコピー | "Start Your Free Week" | "Try Free for 7 Days" |
| 1 | CTAボタン文言 | "Start Free Trial" | "Begin My Journey" |
| 2 | 価格表示 | "$9.99/month" | "Less than $0.33/day" |
| 3 | trial期間強調 | "7-Day Free Trial" | "No Charge for 7 Days" |

---

## C3: `app-factory`（Anicca Skill）

### 概要

- 毎晩23:00 JSTに実行
- 苦しみを減らすアプリのコンセプトを探し → specを作り → Claude Codeにshipさせる

### フロー

| ステップ | 内容 | ツール |
|---------|------|--------|
| 1 | トレンド検索（TikTok急上昇 + App Storeランキング） | Exa `web_search_exa` |
| 2 | フィルタリング（苦しみを減らすもののみ） | Anicca判断 |
| 3 | コンセプト×5を決定 | Anicca |
| 4 | 各コンセプト → spec.md生成 | Anicca write |
| 5 | spec保存 | `/Users/anicca/.openclaw/workspace/specs/YYYY-MM-DD/{app-name}.md` |
| 6 | exec → Claude `app-ship` × 5（順次実行） | exec |
| 7 | Day 1 TikTok → larry呼び出し | larry skill |

### アプリ選定基準

| OK（苦しみを減らす） | NG（苦しみを増やす） |
|--------------------|---------------------|
| 不安・ストレス軽減 | ルッキズム・外見への執着を増やすもの |
| 睡眠改善 | SNS依存を増やすもの |
| 先延ばし克服 | ギャンブル・課金依存 |
| マインドフルネス | 比較・競争を煽るもの |
| 人間関係改善 | 恐怖・怒りを利用したエンゲージメント設計 |

---

## S1: `app-ship`（Claude Code Skill）

### 概要

- `app-factory`（Anicca）からexec経由で呼ばれる
- spec.mdを読んでアプリを完全に自律ビルド・提出する

### INPUT

```
spec: spec.md のファイルパス
```

### フロー

| ステップ | 内容 | ツール |
|---------|------|--------|
| 1 | spec.md読み込み（画面設計・通知・monetization） | Read |
| 2 | コード生成（SwiftUI） | ralph-autonomous-dev |
| 3 | アイコン生成（1024×1024） | `ai-image-generation`（FLUX Dev LoRA） |
| 4 | スクショ3枚生成（simctl → process_screenshots.py PIL合成） | `xcrun simctl` + `process_screenshots.py`（l.md Bible） |
| 5 | メタデータ6言語生成（title, subtitle, description, keywords） | `asc localizations update` |
| 6 | 品質チェック | `greenlight preflight` → CRITICAL=0 |
| 7 | ビルド + App Store提出 | `fastlane full_release` |
| 8 | 完了報告 → Aniccaに返す | exec return |

---

## S2: `onboarding-ab-execute`（Claude Code Skill）— later scope

- オンボーディングフロー（画面順序・コピー）のA/B
- コード変更が必要なためTestFlight経由
- 今は実装しない

---

## データフロー全体図

| データソース | 何を測る | 使うSkill |
|------------|---------|----------|
| `asc analytics download` | install CVR（Impression / Tap）per variant | `screenshot-ab` |
| ASC API `/v2/appStoreVersionExperiments/{id}` | 実験state・開始日 | `screenshot-ab` |
| Mixpanel MCP（$rc_experiment_variant_assignedでセグメント） | Trial CVR（paywall_viewed → trial_started）per variant | `paywall-ab` |
| RC API | Offering一覧・Experiment状態 | `paywall-ab` |
| `xcrun simctl` | アプリ実画面PNG（審査通過済み実画面） | `screenshot-ab`, `app-ship` |
| `process_screenshots.py` + `screenshots.yaml` | ベゼル合成 + テキスト描画（1290×2796 / l.md Bible） | `screenshot-ab`, `app-ship` |
| `ai-image-generation`（FLUX Dev LoRA） | アイコン生成（1024×1024） | `app-ship` |
| Pencil MCP | 全体デザイン刷新（Phase 2） | `screenshot-ab`（Queue 3以降） |
| Anicca memory | 実験記録（id・開始日・queue・before CVR・analytics_request_id） | 全Cron |

---

## 実験管理ルール

| ルール | 内容 | ソース |
|--------|------|--------|
| Track A（スクショ）とTrack B（paywall）は同時実行OK | 異なる指標に影響するため | Apple公式 |
| 1 Track内では1実験のみ | 同時に複数変えると因果が不明 | Apple公式 |
| 停止基準（スクショ） | Treatment install CVR > Control × 1.2 かつ 7日+ → 自動winner。asc analytics downloadで自動取得 | 実装済み |
| 停止基準（paywall） | Treatment Trial CVR > Control × 1.2 かつ 7日+ → 自動winner。Mixpanel MCP segmentで自動取得（RC→Mixpanel integration必須） | - |
| 最短実行期間 | 7日（7日単位で判断） | Apple公式 |
| 最長実行期間 | 90日（Appleのハードリミット） | Apple公式 |
| 常に実験を回す | 実験終了後は即座に次を開始。空白期間なし | - |
| Phase 1 | process_screenshots.py（l.md Bible PIL）でヘッドライン差し替え。実画面必須（Apple審査要件） | - |
| Phase 2 | Phase 1で改善しない場合のみ Pencil MCP で全体デザイン刷新 | - |

---

## スクショ設計原則（Best Practice）

ソース: AppRadar / 「Screenshots are the real decision point. Lead with clear benefit/result → social proof → core flow. No text overlay = instant swipe away.」

| スクショ | 役割 | 内容 |
|---------|------|------|
| 1枚目 | Attention（benefit/result） | ユーザーのペインを直撃するテキスト |
| 2枚目 | Interest + Desire（social proof） | 「○○人が変わった」等の証拠 |
| 3枚目 | Action（core flow） | アプリの実際の画面 |

---

## OSS化方針

- 全skillはapp_idをパラメータ化（どのアプリでも動く）
- spec.mdフォーマットを標準化（誰でも使えるテンプレ）
- README: "AIエージェントがApp Storeアプリを自律的にイテレーションするフレームワーク"
- 公開先: GitHub（別リポジトリ推奨）
