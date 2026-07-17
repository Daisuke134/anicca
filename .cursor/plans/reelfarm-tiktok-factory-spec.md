# Spec: Anicca Automation Factory — SSOT

**Status:** LIVE（LOOP A/B cron 一時無効化中）+ iOS イテレーション設計中
**Date:** 2026-03-31（初版 2026-03-28）
**Author:** Claude Code + ダイス
**ファイルパス:** `.cursor/plans/reelfarm-tiktok-factory-spec.md`

---

## 1. web-app-factory（P1）

### 確定事項

| 項目 | 値 |
|------|-----|
| スキル | `~/.openclaw/skills/web-app-factory/` |
| ランナー | `web-apps/20260303-150000-app/ralph.sh` |
| 失敗原因 | **OAuth token expired (401)** — 全20イテレーション同一エラー |
| テストアプリ | `web-apps/20260303-150000-app/` — US-001〜007 全て passes: false |

### ralph.sh OAuth 修正パッチ

**ファイル:** `web-apps/20260303-150000-app/ralph.sh` **行65**

```diff
- OUTPUT=$(claude --dangerously-skip-permissions --print --mcp-config ~/.claude/mcp.json < "$SCRIPT_DIR/CLAUDE.md" 2>&1 | tee "$LOG_FILE") || true
+ OUTPUT=$(ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:?ANTHROPIC_API_KEY required}" claude --dangerously-skip-permissions --print --mcp-config ~/.claude/mcp.json < "$SCRIPT_DIR/CLAUDE.md" 2>&1 | tee "$LOG_FILE") || true
```

**追加必須:** `web-apps/.env` に追記:
```bash
ANTHROPIC_API_KEY=sk-ant-...  # Claude API key
```

**ralph.sh pre-flight にも追加:**
```diff
- REQUIRED_VARS="VERCEL_TOKEN STRIPE_SECRET_KEY POSTIZ_API_KEY POSTIZ_X_INTEGRATION_ID SLACK_WEBHOOK_AGENTS"
+ REQUIRED_VARS="VERCEL_TOKEN STRIPE_SECRET_KEY POSTIZ_API_KEY POSTIZ_X_INTEGRATION_ID SLACK_WEBHOOK_AGENTS ANTHROPIC_API_KEY"
```

**原因:** `claude --print` は OAuth トークン（`~/.claude/credentials.json`）を使う。Mac Mini の OAuth がexpire → 全20回失敗。API キー直指定で OAuth バイパス。

---

## 2. ReelFarm TikTok Factory（P2）

### 確定事項

| 項目 | 値 |
|------|-----|
| API Base | `https://reel.farm/api/v1` |
| API Key | `[REDACTED-USE-REELFARM_API_KEY-ENV]` |
| プラン | Max Plan（150 automations、無制限生成） |
| スキル | `~/.openclaw/skills/reelfarm/SKILL.md` |
| Cron LOOP A | `0 4 * * *` JST（毎日 04:00）— **現在 enabled: false** |
| Cron LOOP B | `30 4 * * 0` JST（毎週日曜 04:30）— **現在 enabled: false** |
| jobs.json | `/Users/anicca/anicca-project/openclaw-skills/jobs.json` |

### アクティブ Automation（9個）

| ID（短縮） | 名前 | アカウント | hooks数 | crons(PST) |
|-----------|------|----------|---------|------------|
| `37e26301` | 本音翻訳 | honnejp1 | 6 | 04/17/21 |
| `b91325c4` | anicca ja 2 | anicca.jp5 | 6 | 04/16/22 |
| `a17b9467` | デイリーダンマ | anicca.jp3 | 5 | 04/16/20 |
| `c64a09f6` | Anicca ES | anicca.es | 23 | 04/16/20 |
| `3143be7b` | Anicca en 1 | anicca.en | **15（更新済）** | 04/16/22 |
| `4a7912e1` | anicca en 2 | anicca57 | 10 | 05/16/23 |
| `3400d885` | anicca ja 1 | anicca.jp | 6 | 04/16/22 |
| `363ccc5e` | Anicca EN4 | anicca.en4 | **10（新規）** | 07/13/19 |
| `82056504` | Anicca JP4 | anicca.jp4 | **10（新規）** | 07/13/19 |

### 接続済み TikTok アカウント（13個）

| アカウント | ID |
|----------|-----|
| anicca.en4 | `-000CIIeSXrsgxpeDbThsltKCF-cmnjMbw_h` |
| anicca.jp4 | `-000_iUw_TD236YemHot7I_hYLpIdZ39KMOA` |
| anicca.en | `-000cCZgW_cHLwgDo7sMH_uoBV-Y6VWcCW1Q` |
| anicca57 | `-000A4MiLccP6uCuymBf2AbmfF39bbRMkRkb` |
| anicca.es | `-000WjeHCaqED_5C-nsK4jwxN_L6N1ds8p2Y` |
| anicca.jp5 | `-0005epV48ODOmNEVRsiT9G_cg5yds_iCwuU` |
| anicca.jp3 | `-0006sZ5QxTDytBpMNnIn345Ko5ovLAw_j_K` |
| anicca.jp | `-000j-QZU93W1xKE9XdcBddcC7qnMwZ-nbjD` |
| honnejp1 | `-000TJCXgLCk5C27Xpq6GPggwaCtF01uHxgE` |
| honnejp | `-000RuG1K3zF8vXDGW_pjP5iCoF9CjgrwdxA` |
| anicca.en5 | `-0003VxzF2RBuTNSYy7ynwH9amY3VigJ4aNK` |
| aniccajp6 | `-000VsH2qBN-tFkVoSYjgDG9N_weofhRMJG5` |

### LOOP A パッチ（7個、2026-03-29 適用済み）

**Patch 1: アカウントマッピング追加**
```
SKILL.md LOOP A に Step 2 追加:
GET /tiktok/accounts → ID→username マッピング構築
（API が tiktok_account_username を返さないため）
```

**Patch 2: timeframe 変更**
```
timeframe=3 → timeframe=7
（3日では20件返って不正確。7日で安定）
```

**Patch 3: FOR EACH ループ化**
```
LOOP A Step 4 を FOR EACH automation に変更:
  a. GET /tiktok/posts?automation_id={id}&timeframe=7
  b. engagement score = views*0.4 + likes*0.3 + comments*0.2 + shares*0.1
  c. top 3 / bottom 3 特定
  d. 新 hooks 生成（感情的2人称スタイル）
  e. PATCH /automations/{id}
```

**Patch 4: ニッチ確認**
```
LOOP B Step 1: GET /library/niches で利用可能ニッチ確認
（self-improvement, mindfulness は 0 件だった→スキップ）
```

**Patch 5: 投稿枠チェック**
```
LOOP B Step 4: 各アカウントの投稿枠確認
6/day limit per account。capacity = 6 - today_posts
```

**Patch 6: auto_pull_images**
```
LOOP B Step 5: image_settings に auto_pull_images: true, all_slides: "auto"
（ユーザーコレクション使わない。Pinterest 自動取得）
```

**Patch 7: キュー確認**
```
LOOP B: 作成前に GET /slideshows?status=queued
100件以上キューされてたら作成スキップ → Slack 通知
```

### 勝ちパターン

| パターン | 例 | 平均 views |
|---------|-----|-----------|
| 感情的2人称 | "Nobody talks about..." "You're not..." | 40x |
| 番号リスト | "4 Ways to..." | 1x（ベースライン） |

### Cron payload（jobs.json、2026-03-30 更新済み）

LOOP A: `7-day metrics` + `account mapping` + `per-automation scoring loop`
LOOP B: `niche check` + `posting capacity` + `auto_pull_images` + `queue check`

---

## 3. iOS イテレーションスキル（6個）

### 概要

```
隔週月曜:
  08:00  onboarding-iteration → コード変更 → fastlane → 提出
  10:00  screenshot-iteration → スクショ生成 → PPO Experiment
  12:00  バンドル提出（コード + PPO）

隔週木曜:
  10:00  aso-iteration → メタデータ更新（提出不要）

3日ごと:
  07:00  paywall-ab → Superwall A/B（提出不要）

毎月1日:
  10:00  app-ux-iteration → 分析→改善提案

毎日:
  10:00  app-resubmission → リジェクション自動対応
```

### Skill 1: screenshot-iteration

| 項目 | 値 |
|------|-----|
| パス | `~/.openclaw/skills/screenshot-iteration/SKILL.md` |
| cron | `0 10 * * 1`（隔週月曜 10:00 JST） |
| 画面数 | 4画面 × 2言語（EN + JA）= 8スクリーン |
| サイズ | 1290x2796 (6.7") + 1242x2688 (6.5") + 1242x2208 (5.5") |
| 依存 | ParthJadhav/app-store-screenshots, ASC CLI |
| 提出 | 必要（PPO Experiment はバージョン提出が前提） |

```
フォルダ:
~/.openclaw/skills/screenshot-iteration/
├── SKILL.md
├── references/
│   ├── ppo-experiment-guide.md
│   ├── screenshot-best-practices.md
│   └── asc-cli-commands.md
├── examples/
│   └── sample-report.json
└── scripts/
    └── generate-screenshots.sh

フロー:
① asc product-pages experiments list → 前回 PPO 結果
② 勝者/敗者判定 → conversion rate 比較
③ ParthJadhav → 新バリアント 4画面 × EN/JA
④ asc screenshots upload → EN + JA locale
⑤ asc product-pages experiments create → PPO
⑥ onboarding とバンドル提出
⑦ Slack #metrics レポート
```

### Skill 2: onboarding-iteration

| 項目 | 値 |
|------|-----|
| パス | `~/.openclaw/skills/onboarding-iteration/SKILL.md` |
| cron | `0 8 * * 1`（隔週月曜 08:00 JST） |
| 依存 | Mixpanel API, fastlane, ASC CLI |
| 提出 | 必要（コード変更あり） |

```
フォルダ:
~/.openclaw/skills/onboarding-iteration/
├── SKILL.md
├── references/
│   ├── onboarding-best-practices.md（ios-app-onboarding から移植）
│   ├── mixpanel-funnel-guide.md
│   └── localization-guide.md
├── examples/
│   └── funnel-analysis.json
└── scripts/
    └── fetch-funnel.sh

フロー:
① Mixpanel → ファネル取得（EN/JA 別）
② ドロップオフ最大ステップ特定
③ BP参照 → 改善コード生成
④ SwiftUI + Localizable.strings 変更（EN/JA）
⑤ fastlane build → IPA
⑥ asc builds upload → versions create → submit（スクショとバンドル）
⑦ Slack #metrics レポート
```

### Skill 3: paywall-ab（Superwall 移行）

| 項目 | 値 |
|------|-----|
| パス | `~/.openclaw/skills/paywall-ab/SKILL.md` |
| cron | `0 7 */3 * *`（3日ごと 07:00 JST） |
| 依存 | **Superwall MCP**（RevenueCat Experiments 廃止） |
| 提出 | **不要**（サーバーサイド切替） |
| 価格テスト | Superwall Campaign で異なる Product 紐付け |

```
フォルダ:
~/.openclaw/skills/paywall-ab/
├── SKILL.md（RevenueCat → Superwall に書き換え）
├── references/
│   ├── superwall-mcp-guide.md
│   ├── pricing-ab-testing.md
│   └── paywall-design-patterns.md
├── examples/
│   └── campaign-config.json
└── scripts/
    └── sw-api.sh

フロー:
① Superwall MCP → Campaign 結果取得（EN/JA 別）
② 勝者判定（revenue/user）
③ LLM → 新ペイウォールデザイン（EN/JA 両方）+ 価格バリエーション
④ Superwall MCP → 新ペイウォール作成 + Product 紐付け
⑤ Superwall MCP → 新 Campaign（A/B + 自動最適化）
⑥ Slack #metrics レポート

Superwall MCP インストール済み:
  claude mcp add superwall --transport http https://superwall-mcp.superwall.com/mcp
  npx skills add superwall/skills -y
```

**RevenueCat → Superwall 移行理由:**
- RevenueCat Experiments はテンプレート縛り。カスタム SwiftUI の A/B 不可
- ペイウォールデザインのプレビュー不可能
- Superwall MCP で全操作自動化（ゼロから作成 + Campaign + 価格テスト）

### Skill 4: app-ux-iteration

| 項目 | 値 |
|------|-----|
| パス | `~/.openclaw/skills/app-ux-iteration/SKILL.md` |
| cron | `0 10 1 * *`（毎月1日 10:00 JST） |
| 依存 | Mixpanel, RevenueCat, Sentry, ASC CLI |
| 提出 | 次の月曜バンドルに含める |

```
フォルダ:
~/.openclaw/skills/app-ux-iteration/
├── SKILL.md
├── references/
│   ├── anicca-app-architecture.md
│   ├── removed-features.md（ee50fd6e の記録）
│   ├── ux-improvement-patterns.md
│   └── localization-checklist.md
├── examples/
│   └── churn-analysis.json
└── scripts/
    └── fetch-metrics.sh

フロー:
① データ収集: Mixpanel + RevenueCat + Sentry + ASC（EN/JA セグメント別）
② パターン分析: チャーン日数 / セッション長 / タブ離脱 / 転換率
③ Impact × Effort → Top 3 改善提案
④ P0→即修正, P1→Slack承認→実装, P2→Spec作成
⑤ Slack #metrics レポート
```

**2026-02-01 削除済み機能（commit ee50fd6e）:**
- DeepDive: 問題カードタップ→質問シート（`DeepDiveQuestionsData.swift` 322行）
- Tell Anicca: 3カード（困ってること/ゴール/覚えておいて）→テキスト入力
- 問題削除: 赤ボタン→確認→削除
- カード chevron: タップ可能→読み取り専用に

### Skill 5: aso-iteration

| 項目 | 値 |
|------|-----|
| パス | `~/.openclaw/skills/aso-iteration/SKILL.md` |
| cron | `0 10 * * 4`（隔週木曜 10:00 JST） |
| 既存スキル統合 | `aso-growth` + `aso-audit` を references/ に |
| 提出 | **不要**（メタデータ変更は審査不要） |

```
フロー:
① ASC API → インプレッション/ダウンロード/conversion（EN/JA 別）
② 競合キーワード分析
③ タイトル/サブタイトル/キーワード/説明文 最適化案（EN/JA）
④ asc metadata update --locale en-US + --locale ja
⑤ Slack #metrics レポート
```

### Skill 6: app-resubmission

| 項目 | 値 |
|------|-----|
| パス | `~/.openclaw/skills/app-resubmission/SKILL.md`（既存） |
| cron | `0 10 * * *`（毎日 10:00 JST）— **追加予定** |

```
E2E フロー（現行スキル）:

① mobile-apps/20*-app 全ディレクトリ走査
   → prd.json から appId 取得
   → asc apps status --id "$APP_ID" --output json
   → REJECTED or DEVELOPER_REJECTED 検出

② リジェクト理由取得
   → asc web review show --app "$APP_ID" --output json
   → rejectionReason + messages 取得
   → $APP_DIR/rejection.json に保存

③ Slack 通知
   → SLACK_WEBHOOK_AGENTS に 🔴 REJECTED 送信

④ CC で修正
   → rejection.json の内容を CLAUDE.md に追記
   → claude --dangerously-skip-permissions で自動修正
   → リジェクト理由に基づきメタデータ/スクショ/コード修正

⑤ fastlane ビルド + 再提出
   → cd $APP_DIR && fastlane build_and_submit
   → asc submit create

⑥ 結果報告
   → Slack #metrics + rejection.json 更新
```

**注意:** 現在 cron なし。jobs.json に追加必須。

---

## 4. Anicca iOS ペイウォール現状 + パッチ

### ペイウォール構成

| 場面 | 実装 |
|------|------|
| オンボーディング | **100% カスタム SwiftUI**（PaywallPrimerStepView → PlanSelectionStepView） |
| アップグレード | RevenueCatUI.PaywallView |
| バックエンド | RevenueCat |
| A/B テスト | **Superwall に移行予定**（RevenueCat Experiments 廃止） |

### ペイウォールファイル

| ファイル | 内容 |
|---------|------|
| `aniccaios/aniccaios/Onboarding/PaywallPrimerStepView.swift` | Primer（タイトル + 3機能 + Continue） |
| `aniccaios/aniccaios/Onboarding/PlanSelectionStepView.swift` | プラン選択（年額/月額カード + CTA） |
| `aniccaios/aniccaios/Views/MyPathTabView.swift` | アップグレードボタン → RevenueCatUI |
| `aniccaios/aniccaios/MainTabView.swift` | Nudge後アップグレード → RevenueCatUI |

### 現行プラン + 価格 A/B テスト

| プラン | 現行価格 | テスト価格 | トライアル |
|--------|---------|-----------|----------|
| Monthly | $9.99/月 | $4.99/月 | ~~7日無料~~ → **廃止** |
| Annual | $49.99/年 | $39.99/年 | 7日無料（維持） |

### PATCH: 月額トライアル廃止

**ファイル:** `aniccaios/aniccaios/Onboarding/PlanSelectionStepView.swift`

**変更1: CTA テキスト（行128-129）**
```diff
- let hasTrialEligibility = selectedPackage?.storeProduct.introductoryDiscount != nil
- Text(String(localized: hasTrialEligibility ? "paywall_plan_cta_trial" : "paywall_plan_cta_subscribe"))
+ let hasTrialEligibility = selectedPackage?.packageType == .annual && selectedPackage?.storeProduct.introductoryDiscount != nil
+ Text(String(localized: hasTrialEligibility ? "paywall_plan_cta_trial" : "paywall_plan_cta_subscribe"))
```

**変更2: analytics guard（行272-274）**
```diff
  if result.customerInfo.entitlements[AppConfig.revenueCatEntitlementId]?.isActive == true {
      AnalyticsManager.shared.track(.onboardingPaywallPurchased)
-     if package.storeProduct.introductoryDiscount != nil {
+     if package.packageType == .annual && package.storeProduct.introductoryDiscount != nil {
          AnalyticsManager.shared.track(.trialStarted, properties: [
              "product_id": package.storeProduct.productIdentifier
          ])
      }
```

**Localizable.strings 変更（EN/JA のみ — 他言語は該当キーなし）:**

`aniccaios/aniccaios/Resources/en.lproj/Localizable.strings`:
```
既存キーそのまま（"paywall_plan_cta_subscribe" = "Subscribe";）
→ 月額選択時に "Subscribe" が表示される。変更不要。
```

`aniccaios/aniccaios/Resources/ja.lproj/Localizable.strings`:
```
既存キーそのまま（"paywall_plan_cta_subscribe" = "登録する";）
→ 月額選択時に "登録する" が表示される。変更不要。
```

**補足:** RevenueCat 側で月額の introductory offer を削除する必要はない。コード側で `.annual` チェックするだけで CTA テキストが "Subscribe"/"登録する" に切り替わる。月額でも Store 側にトライアルが残っていれば Apple が自動表示するが、CTA コピーは制御できる。

### ASC 価格 A/B テスト用プロダクト作成

```bash
# 既存: $9.99/月 + $49.99/年（RevenueCat で作成済み）
# 新規: $4.99/月 + $39.99/年（ASC CLI で作成）

# Step 1: 月額 $4.99 サブスクリプション作成
asc iap create \
  --app 6738663505 \
  --type auto-renewable \
  --product-id "anicca_monthly_499" \
  --reference-name "Anicca Monthly $4.99" \
  --group-id <SUBSCRIPTION_GROUP_ID>

# Step 2: 年額 $39.99 サブスクリプション作成
asc iap create \
  --app 6738663505 \
  --type auto-renewable \
  --product-id "anicca_annual_3999" \
  --reference-name "Anicca Annual $39.99" \
  --group-id <SUBSCRIPTION_GROUP_ID>

# Step 3: availability → pricing の順序（platform-gotchas.md 参照）
asc iap availability set --product "anicca_monthly_499" --territories US JP
asc iap pricing set --product "anicca_monthly_499" --price 4.99

asc iap availability set --product "anicca_annual_3999" --territories US JP
asc iap pricing set --product "anicca_annual_3999" --price 39.99

# Step 4: RevenueCat に Products 追加
# RevenueCat Dashboard → Products → New → anicca_monthly_499, anicca_annual_3999

# Step 5: Superwall Campaign で価格 A/B
# Variant A: $9.99/月 + $49.99/年（現行）
# Variant B: $4.99/月 + $39.99/年（新）
```

---

## 5. TikTok アカウントスケール（P2）

| ツール | 何をするか |
|--------|-----------|
| hendrikbgr/TikTok-Account-Creator | Selenium でアカウント自動作成 |
| l-portet/tiktok-warmup-bot | iOS Voice Control で 7-14日ウォームアップ |
| DansVPN ($2/月) | US IP でコンテンツ配信 |

フロー: 作成→ウォームアップ→ReelFarm接続→LOOP B 自動化

---

## 6. 外部ツール統合（P2）

| ツール | cron適合 | 用途 |
|--------|---------|------|
| AutoResearchClaw | ⭐⭐⭐⭐⭐ | 週次自律リサーチ（CLI、ヘッドレス） |
| Crucix | ⭐⭐⭐⭐ | 6h OSINT 収集（27ソース、Node.js） |
| MiroFish | ⭐⭐（保留） | Web UI 必須、高コスト |
| paperclip | 保留 | コンセプト参考のみ |
| autoresearch | 除外 | LLM 訓練用。Anicca に不適 |
| superpowers | 統合 | 開発手法改善（cron ではない） |

---

## 7. Factory SaaS（P3）

| 項目 | 値 |
|------|-----|
| URL | aniccaai.com/factory |
| Spec | `.cursor/plans/mobileapp-factory-saas-spec.md` |
| フロント | Next.js + Stripe |
| バックエンド | Node.js/Express + Railway |
| TikTok | アカウント自動作成 + ウォームアップ + ReelFarm 接続 |
| 価格 | $49/月 Starter, $149/月 Pro, $499/月 Enterprise |

---

## 8. ASC CLI 自動化能力

| 機能 | コマンド |
|------|---------|
| PPO Experiment | `asc product-pages experiments create` |
| スクショアップロード | `asc screenshots upload` |
| バージョン作成 | `asc versions create` |
| ビルドアタッチ | `asc versions attach-build` |
| 提出 | `asc submit create` |
| 審査状態 | `asc status --app APP_ID` |
| リジェクション詳細 | `asc review details-for-version` |
| メタデータ更新 | `asc metadata update` |
| ワークフロー | `.asc/workflow.json` |
| IPA アップロード | `asc builds upload --app APP_ID --ipa app.ipa` |
| IAP 作成 | `asc iap create --app APP_ID --type auto-renewable` |
| 価格設定 | `asc iap pricing set --product PRODUCT_ID --price X.XX` |

---

## 9. 全 To-Do

| # | 優先度 | タスク | 状態 |
|---|--------|--------|------|
| 1 | P0 | Superwall SDK iOS 統合 | ⬜ |
| 2 | P0 | paywall-ab → Superwall MCP 改修 | ⬜ |
| 3 | P0 | app-resubmission cron 追加 | ⬜ |
| 4 | P0 | 月額トライアル廃止パッチ適用 | ⬜ |
| 5 | P0 | ASC 価格テスト用プロダクト作成 ($4.99/$39.99) | ⬜ |
| 6 | P1 | web-app-factory ralph.sh OAuth 修正 | ⬜ |
| 7 | P1 | web-app-factory テスト実行 | ⬜ |
| 8 | P1 | Web App イテレーションスキル | ⬜ |
| 9 | P1 | screenshot-iteration スキル作成 | ⬜ |
| 10 | P1 | onboarding-iteration スキル作成 | ⬜ |
| 11 | P1 | app-ux-iteration スキル作成 | ⬜ |
| 12 | P1 | aso-iteration スキル作成 | ⬜ |
| 13 | P1 | 6スキル cron jobs.json 追加 | ⬜ |
| 14 | P1 | DeepDive/TellAnicca/問題削除 復活 | ⬜ |
| 15 | P2 | LOOP A/B cron 再有効化 + テスト | ⬜ |
| 16 | P2 | DansVPN + warmup-bot + Account Creator | ⬜ |
| 17 | P2 | 新 TikTok アカウント 4-6個 | ⬜ |
| 18 | P2 | AutoResearchClaw + 週次 cron | ⬜ |
| 19 | P2 | Crucix + 6h OSINT cron | ⬜ |
| 20 | P3 | aniccaai.com/factory フル開発 | ⬜ |

---

最終更新: 2026-03-31
