# app-metrics-fix-spec.md
## App Metrics Cron修正 + オンボーディング計測追加

**日付**: 2026-03-20
**対象**: app-metrics-morning cron (`8db042f0-014d-466c-92e5-8a85da188491`)
**対象アプリ**: aniccaios v1.7.0

---

## 背景

app-metrics-morning cron が10連続エラー。調査の結果、4つの独立した問題を特定:

| # | 問題 | 根本原因 |
|---|------|---------|
| 1 | ASC CLIハング | `asc` CLIが毎回30秒+タイムアウト。JWT認証は正常（直接curlで取得成功） |
| 2 | Mixpanelイベント名不一致 | SKILL.mdが `onboarding_paywall_viewed` を取得するが、このイベントは `completeOnboarding()` で発火されていない。Paywall表示時に発火されるのは `paywall_primer_viewed`（PaywallPrimerStepView L64 onAppear）。SKILL.mdが見ていた `paywall_viewed` (8件) は別のイベント |
| 3 | SKILL.mdのイベントリスト不足 | iOSコードでは全ステップのtrack()が既に実装済み（下表参照）。SKILL.mdが3イベントしかクエリしていないため中間ステップが不可視 |
| 4 | cron delivery二重投稿 | agentがmessageツールでSlack投稿 + cronのannounce deliveryで二重投稿。agent側が失敗して `⚠️ ✉️ Message failed` エラーに |

### ⚠️ 前版Specの重大な誤り（修正済み）

前版は「4ステップ（struggleDepth, goals, personalizedInsight, valueProp）のtrack()が未実装」と記載していたが、**これは誤り**。実際には各ステップViewの内部で既にtrack()が呼ばれている:

| ステップ | トラッキング場所 | 行 | トリガー |
|----------|-----------------|-----|---------|
| StruggleDepth | `StruggleDepthStepView.swift` | L54 | `selectFrequency()` コールバック |
| Goals | `GoalsStepView.swift` | L97 | `saveAndAdvance()` |
| PersonalizedInsight | `PersonalizedInsightStepView.swift` | L39 | CTAボタンタップ |
| ValueProp | `ValuePropStepView.swift` | L64 | CTAボタンタップ |

`advance()` にtrack()を追加すると**二重トラッキング**になるため、**iOSコード修正は不要**。

---

## 全トラッキングイベント一覧（実装済み・検証済み）

**ファイル**: `aniccaios/aniccaios/Services/AnalyticsManager.swift`

| イベント | AnalyticsEvent case | 行 | 発火場所 |
|----------|--------------------|----|---------|
| `onboarding_started` | `.onboardingStarted` | — | OnboardingFlowView L83 (onAppear) |
| `onboarding_welcome_completed` | `.onboardingWelcomeCompleted` | — | OnboardingFlowView L155 (advance) |
| `onboarding_struggles_completed` | `.onboardingStrugglesCompleted` | — | OnboardingFlowView L158 (advance) |
| `onboarding_struggle_depth_completed` | `.onboardingStruggleDepthCompleted` | L161 | StruggleDepthStepView L54 |
| `onboarding_goals_completed` | `.onboardingGoalsCompleted` | L162 | GoalsStepView L97 |
| `onboarding_insight_completed` | `.onboardingInsightCompleted` | L163 | PersonalizedInsightStepView L39 |
| `onboarding_valueprop_completed` | `.onboardingValuePropCompleted` | L164 | ValuePropStepView L64 |
| `onboarding_live_demo_completed` | `.onboardingLiveDemoCompleted` | — | OnboardingFlowView L169 (advance) |
| `onboarding_notifications_completed` | `.onboardingNotificationsCompleted` | — | OnboardingFlowView L172 (advance) |
| `onboarding_completed` | `.onboardingCompleted` | — | OnboardingFlowView L180 (completeOnboarding) |
| `onboarding_paywall_viewed` | `.onboardingPaywallViewed` | L157 | **❌ 未発火（後述）** |
| `paywall_primer_viewed` | `.paywallPrimerViewed` | L165 | PaywallPrimerStepView L64 (onAppear) |
| `paywall_timeline_viewed` | `.paywallTimelineViewed` | L166 | TrialTimelineStepView L75 (onAppear) |
| `paywall_plan_selection_viewed` | `.paywallPlanSelectionViewed` | L167 | PlanSelectionStepView L129 (onAppear) |
| `paywall_drawer_viewed` | `.paywallDrawerViewed` | — | DrawerOfferView L59 (onAppear) |
| `paywall_drawer_converted` | `.paywallDrawerConverted` | — | DrawerOfferView L30 |
| `onboarding_paywall_purchased` | `.onboardingPaywallPurchased` | — | PlanSelectionStepView L208 |
| `onboarding_paywall_dismissed_free` | `.onboardingPaywallDismissedFree` | — | OnboardingFlowView L216 |

---

## 修正1: iOSコード（最小変更）

### 1a. completeOnboarding() に `onboarding_paywall_viewed` 追加

**ファイル**: `aniccaios/aniccaios/Onboarding/OnboardingFlowView.swift`

`completeOnboarding()` (L179-192) で `paywallStep = .primer` に遷移する直前（L190付近）に:

```swift
// 修正前（L188-190）
} else {
    // Not subscribed — show paywall
    paywallStep = .primer

// 修正後
} else {
    // Not subscribed — show paywall
    AnalyticsManager.shared.track(.onboardingPaywallViewed)
    paywallStep = .primer
```

**理由**: `onboardingPaywallViewed` はenum定義(L157)は存在するが、どこからもtrack()が呼ばれていない唯一のイベント。Paywall全体の入口を示すメタイベントとして有用。

### 1b. advance() への追加は不要（二重トラッキング防止）

前版Specの修正1aは**実装しない**。各ステップViewで既にtrack()済み。

### 1c. Paywall中間ステップへの追加は不要

前版Specの修正1cは**実装しない**。PaywallPrimerStepView/TrialTimelineStepView/PlanSelectionStepViewの各onAppearで既にtrack()済み。

---

## 修正2: SKILL.md（app-metrics）

**ファイル**: `~/.openclaw/skills/app-metrics/SKILL.md`

### 2a. Step 2（Mixpanel）のイベントリスト拡張

| 現状 | 修正後 |
|------|--------|
| `onboarding_started` | `onboarding_started` |
| ❌ なし | `onboarding_welcome_completed` |
| ❌ なし | `onboarding_struggles_completed` |
| ❌ なし | `onboarding_struggle_depth_completed` |
| ❌ なし | `onboarding_goals_completed` |
| ❌ なし | `onboarding_insight_completed` |
| ❌ なし | `onboarding_valueprop_completed` |
| ❌ なし | `onboarding_live_demo_completed` |
| ❌ なし | `onboarding_notifications_completed` |
| ❌ なし | `onboarding_completed` |
| `onboarding_paywall_viewed` | `onboarding_paywall_viewed` ← 修正1aで発火開始 |
| ❌ なし | `paywall_primer_viewed` |
| ❌ なし | `paywall_timeline_viewed` |
| ❌ なし | `paywall_plan_selection_viewed` |
| ❌ なし | `paywall_viewed` ← 既存（別コンテキスト？要確認） |
| `rc_trial_started_event` | `rc_trial_started_event` |
| ❌ なし | `trial_started` |
| ❌ なし | `onboarding_paywall_purchased` |
| ❌ なし | `onboarding_paywall_dismissed_free` |

**注意**: `paywall_viewed` (8件) は `onboarding_paywall_viewed` とは別イベント。Settings画面等からのPaywall表示の可能性あり。両方取得して区別する。

### 2b. Step 3（ASC）を直接curl+JWTに置換

現状: `asc analytics sales ...` → タイムアウト

**修正後**: Python JWTでトークン生成 → curl直接API

```bash
source ~/.openclaw/.env
TOKEN=$(python3 -c "
import json, time, jwt
config = json.load(open('$HOME/.asc/config.json'))
with open(config['private_key_path']) as f:
    pk = f.read()
now = int(time.time())
print(jwt.encode({'iss': config['issuer_id'], 'iat': now, 'exp': now+1200, 'aud': 'appstoreconnect-v1'}, pk, algorithm='ES256', headers={'kid': config['key_id']}))
")

# 7日分のSales Report取得（2日前から。当日・前日はApple未生成）
for i in $(seq 2 8); do
  DATE=$(date -v-${i}d +%Y-%m-%d)
  curl -s "https://api.appstoreconnect.apple.com/v1/salesReports?filter%5BvendorNumber%5D=93486075&filter%5BreportType%5D=SALES&filter%5BreportSubType%5D=SUMMARY&filter%5Bfrequency%5D=DAILY&filter%5BreportDate%5D=${DATE}" \
    -H "Authorization: Bearer $TOKEN" --compressed | gunzip 2>/dev/null | grep "6755129214"
done
```

集計: awk で country($13), units($8), type($7) をパース。type=1が新規DL。

**前提条件**:
- `pip3 install pyjwt cryptography` が必要（PyJWTパッケージ）
- `~/.asc/config.json` に `issuer_id`, `key_id`, `private_key_path` が設定済み
- Sales Reportは2日遅延（当日・前日は404）。`seq 2 8` で2〜8日前を取得

**エラーハンドリング**:
- 404: レポート未生成 → スキップ（`2>/dev/null`で抑制済み）
- 401: JWT期限切れ → 1200秒(20分)で十分だが、cronが長時間かかる場合は再生成必要
- gunzip失敗: 空レスポンス → `2>/dev/null`で抑制

### 2c. Slack報告テンプレート更新

ファネル部分を全ステップに拡張:

```
📈 オンボーディングファネル（Mixpanel 直近7日）
 1. Started:            XX件 (100%)
 2. Welcome Done:       XX件 (XX.X%)
 3. Struggles:          XX件 (XX.X%)
 4. StruggleDepth:      XX件 (XX.X%)
 5. Goals:              XX件 (XX.X%)
 6. Insight:            XX件 (XX.X%)
 7. ValueProp:          XX件 (XX.X%)
 8. LiveDemo:           XX件 (XX.X%)
 9. Notifications:      XX件 (XX.X%)
10. Completed:          XX件 (XX.X%)

💳 Paywall ファネル（% of Completed）
11. Paywall Entered:     XX件 (XX.X%)
12. Primer Viewed:       XX件 (XX.X%)
13. Timeline Viewed:     XX件 (XX.X%)
14. Plan Selection:      XX件 (XX.X%)
15. Purchased:           XX件 (XX.X%)
16. Dismissed Free:      XX件 (XX.X%)
17. Trial Started (RC):  XX件 (XX.X%)

🔴 最大離脱ポイント: Step X → Step X+1 (XX.X% → XX.X%, -XX件)
```

---

## 修正3: Cron設定パッチ

### 3a. Payload更新（Slack二重投稿修正）

```json
{
  "payload": {
    "kind": "agentTurn",
    "message": "Execute the app-metrics skill at ~/.openclaw/skills/app-metrics/SKILL.md. Follow all steps (RevenueCat, Mixpanel, ASC). Do NOT post to Slack yourself — cron delivery handles Slack posting automatically. Just collect the data, save the JSON file, and return the formatted summary as your final response.",
    "model": "anthropic/claude-sonnet-4-5"
  }
}
```

### 3b. 他3つのcron（midday/afternoon/night）は無効のまま

朝1回で十分（Dais確認済み）。

---

## 実行順序

| # | タスク | 修正 | 即時適用 |
|---|--------|------|---------|
| 1 | SKILL.md更新（イベントリスト拡張 + ASC curl置換 + テンプレート） | 2a, 2b, 2c | ✅ |
| 2 | Cron payload更新（二重投稿修正） | 3a | ✅ |
| 3 | 手動 `cron run` で検証 | — | ✅ |
| 4 | iOSコード修正（`onboardingPaywallViewed` 1箇所のみ） | 1a | ❌ 次回リリース |
| 5 | fastlane でビルド&テスト | — | ❌ 次回リリース |
| 6 | App Store提出（1.7.1 or 次回バージョン） | — | ❌ 次回リリース |

### 優先順位の理由

- 修正2,3（SKILL + cron）は**即時適用可能**で、cron10連続エラーを即座に解消
- 既存のtrack()呼び出しは既に動作中 → SKILL.mdがクエリすれば即座にデータ取得可能
- 修正1（iOS）は1箇所のみで影響小。次回リリースに含めれば十分

### E2E判定

E2E不要。理由:
- iOS修正は `AnalyticsManager.shared.track()` 1行追加のみ（UIロジック変更なし）
- SKILL.md/Cronはバックエンドスクリプト変更（手動 `cron run` で検証可能）

---

## エッジケース・注意事項

| ケース | 対応 |
|--------|------|
| `paywall_viewed` vs `onboarding_paywall_viewed` の違い | `paywall_viewed` はSettings等からの表示を含む可能性。両方取得して区別 |
| 既存Pro用ユーザーの `completeOnboarding()` | `isEntitled` チェック → `completeOnboardingForExistingPro()` → Paywall非表示 → `onboardingPaywallViewed` は発火しない（正しい動作） |
| DrawerOfferView からのコンバージョン | `paywall_drawer_viewed` / `paywall_drawer_converted` も取得してドロワー経由のコンバージョンを可視化 |
| PyJWT未インストール | `pip3 install pyjwt cryptography` を SKILL.md の前提条件に記載するか、事前にMac Miniにインストール |
| Sales Report の2日遅延 | `seq 2 8` で対応済み。当日・前日は404 |
| advance() の二重トラッキング | **絶対にadvance()にtrack()を追加しない**。各ステップViewで既に実装済み |

---

## 期待される成果

修正後のSlack出力で以下が可視化される:

| 項目 | 現状 | 修正後 |
|------|------|--------|
| オンボーディングステップ | 3イベントのみ | 全10ステップ |
| Paywallファネル | `paywall_viewed` のみ | Primer→Timeline→PlanSelection→Purchased/Dismissed |
| 離脱ポイント特定 | 不可能 | 自動検出 |
| ASCダウンロード数 | タイムアウト | curl直接で安定取得 |
| Slack投稿 | 二重投稿+エラー | cron deliveryのみ |
