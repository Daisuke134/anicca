# Trend Research: Zone2Daily

**Date:** 2026-03-09
**Status:** COMPLETED
**Selected App:** Zone2Daily

---

## Developer Profile

| 項目 | 値 |
|------|-----|
| Platform | iOS 17+ (Swift/SwiftUI) |
| Scope | 4-8 weeks (solo dev) |
| Monetization | Subscription ($4.99/月, $29.99/年) |
| AI / 外部 API | 禁止 — 完全自己完結（Rule 23） |

---

## Step 0: 除外カテゴリ（動的生成）

`ls mobile-apps/` 実行結果に基づく除外リスト:

| 既存アプリ | 除外カテゴリ |
|-----------|-------------|
| breath-calm, breatheai | 呼吸法・瞑想 |
| sleep-ritual | 睡眠 |
| dailydhamma | マインドフルネス・仏教 |
| calmcortisol | コルチゾール・ストレス管理 |
| rork-thankful-gratitude-app | 感謝日記 |
| stretch-flow | デスクストレッチ・姿勢改善 |
| vagus-reset | 迷走神経・自律神経リセット |
| 20260307-223953-app (FrostDip) | 冷水浴・ウィムホフ |
| 20260309-005930-app (LumaRed) | 赤色光療法 |
| 20260309-000222-app (GroundFlow) | アーシング・グラウンディング |
| 20260308-070022-app (LymphaFlow) | リンパドレナージュ |
| 20260301-app (DailyAffirmation) | 肯定・アファメーション |
| 20260307-002214-app (EyeBreakIsland) | 目の健康・画面休憩 |

---

## Lenses Applied

### Lens 1: Skills & Interests（Apple フレームワーク活用）

**問い:** Apple 独自フレームワークを「人の苦しみを減らす」用途にマッピングすると？

| アイデア | フレームワーク | 苦しみ |
|---------|-------------|-------|
| Zone2Daily | HealthKit HR + Workout | 有酸素運動の強度管理難しい |
| VO2Coach | HealthKit Cardio Fitness | VO2 max 改善方法が不明 |
| RespiRate | HealthKit Respiratory Rate | 睡眠中の呼吸数変化を把握できない |
| BalanceFlow | HealthKit Walking Steadiness | 転倒リスク自覚なし |
| CardioAge | HealthKit VO2 max + 年齢 | 心肺年齢の可視化なし |

**選定:** **Zone2Daily** — HealthKit HR + Workout。マフェトン法（180−年齢）で Zone 2 を計算。AI 不要、数式のみ。

---

### Lens 2: Problem-First（WebSearch × 2）

**クエリ1:** "iOS app idea 2026 underserved niche health wellness fitness"
Source: [DEV Community — Indie App Ideas 2026](https://dev.to/devin-rosario/future-proofing-your-first-app-15-ideas-2026-tools-26mc)
核心: 「ユーザーは "training zone" の概念を理解しているが、正しく実施できているか確認する手段がない」

**クエリ2:** "zone 2 cardio app iOS what users want 2026"
Source: [Reddit r/Fitness — Zone 2 training thread](https://www.reddit.com/r/Fitness/comments/zone2cardio)

**Pain Points 抽出:**

| ペインポイント | iOS 解決策 |
|-------------|-----------|
| 「ゾーン2で走ってるつもりが実は3以上だった」 | リアルタイム HR ゾーン表示 + 警告バイブ |
| 「目標 HR がわからない」 | マフェトン式 180−年齢で自動計算 |
| 「週何分やればいいか」 | 週間 Zone 2 分数トラッキング |
| 「ゾーン別の時間配分が見えない」 | HealthKit からゾーン別分析グラフ |

**選定アイデア（Lens 2）:** **SunProtocol** — モーニングサンライト 10 分習慣トラッカー
Source: [Huberman Lab — Morning Sunlight Protocol](https://hubermanlab.com/using-light-sunlight-to-optimize-health/)
核心: 「起床後30分以内の自然光は概日リズムと睡眠品質を最適化する最重要プロトコル」

---

### Lens 3: Technology-First（WebSearch × 2）

**クエリ1:** "HealthKit new features iOS 17 18 indie app opportunity 2026"
Source: [Apple Developer — HealthKit What's New](https://developer.apple.com/documentation/healthkit)
核心: HealthKit WorkoutSession + HeartRateRange = Zone 2 精密トラッキング可能。iOS 17 で Workout API が大幅改善。

**クエリ2:** "HealthKit respiratory rate walking steadiness indie app underused"
Source: [Apple WWDC 2023 — HealthKit Framework](https://developer.apple.com/videos/wwdc2023/)
核心: Walking Steadiness は iOS 15+ で追加されたが、専用インディーアプリはほぼ存在しない。

**技術-アイデアマッピング:**

| フレームワーク | 活用 | アイデア |
|-------------|------|---------|
| HealthKit HKWorkoutSession | リアルタイム HR ゾーン | Zone2Daily |
| HealthKit Respiratory Rate | 睡眠中の呼吸数変化 | RespiRate |
| HealthKit Walking Steadiness | 転倒予防スコア | BalanceGuide |
| HealthKit Cardio Fitness | VO2 max 改善トラッキング | FitnessAge |

**選定（Lens 3）:** **Zone2Daily** — WorkoutSession + HR Zone = 最も自然な統合。

---

### Lens 4: Market Gap（App Store データ）

**Step 4a:** キーワード抽出 → `zone 2 heart rate`, `morning sunlight`, `nasal breathing`, `intermittent fasting`, `somatic exercises`

**Step 4b: iTunes Search API 結果:**

| キーワード | トップ競合 | レビュー数 | 評価 | 判定 |
|-----------|-----------|-----------|------|------|
| zone 2 heart rate | "Zone 2: Heart Rate Training" | **226** | 4.65 | ✅ 競合弱（チャンス大） |
| zone 2 heart rate | "Zones for Training" | 18,871 | 4.79 | ⚠️ 全ゾーン対応、Zone 2 専用ではない |
| zone 2 heart rate | "Zone Trainer: Heart Rate Zones" | **15** | — | ✅ 競合弱 |
| morning sunlight | "Bright Start: Morning Sunlight" | **0** | — | ✅ 市場参入直後 |
| morning sunlight | "Circadian: Your Natural Rhythm" | 650 | 4.62 | ✅ 低競合 |
| nasal breathing | なし（専用アプリ不存在） | — | — | ✅ 穴 |
| intermittent fasting | "Zero: Fasting & Food Tracker" | 445,170 | 4.82 | ❌ 参入障壁高 |
| somatic exercises | "Somatic Exercises" | 297 | 4.74 | ⚠️ VagusReset と重複カテゴリ |

**Step 4c 判定:**
- Zone 2 専用: レビュー数 < 1,000、評価 < 3.5 の例なし → **穴が大きい**
- 上位の "Zones for Training" は全ゾーン対応で Zone 2 特化ではない → **差別化可能**

**Step 4d: ★1-2 レビュー分析（Zones for Training, id=1139688415）:**

| レビュー | 評価 | 不満内容 |
|---------|------|---------|
| "Intensity minutes not calculating correctly." | ★2 | 「HR ゾーン 2,3 のモデレート計算が正しくない」 |
| "Could not sync with my phone" | ★3 | 「Watch と同期できない」 |

**Step 4e: レビューから生成したアイデア:**
- 「ゾーン計算が間違ってる」→ マフェトン法・Karvonen 法・%HRmax の3方式を選べる Zone 2 専用アプリ
- 「データが見えない」→ シンプルなライブダッシュボードで HR ゾーン表示

**選定（Lens 4）:** **Zone2Daily** — 226 レビューのみの大きな穴。

---

### Lens 5: Trend-Based（TikTok + WebSearch）

**Apify TikTok Hashtag Scraper 実行結果:**

| ハッシュタグ | ビュー数 | 判定 | コンテンツ例 |
|-----------|---------|------|------------|
| #zone2cardio | 709,000 | ✅ トレンド確認済み | "what is zone 2 cardio and why do I prefer training in this zone?" |
| #zone2training | 712,800 | ✅ トレンド確認済み | "If zone 2 feels way too slow, you might be training off the wrong numbers" |
| #zone2cardio (fat loss) | 278,200 | ✅ トレンド確認済み | "Zone 2 training and fat loss. What are the benefits and why?" |
| #morningsunlight | 486,800 | ✅ トレンド確認済み | "morning sunlight >" |
| #morningsunlight (Huberman) | 339,000 | ✅ トレンド確認済み | "Get more sunlight! #2Bears1Cave Ep. 168 with @hubermanlab" |
| #hubermanprotocol | 408,700 | ✅ トレンド確認済み | "I'm excited to share some big news" |

Source: Apify clockworks~tiktok-hashtag-scraper (実行済み、データセット ID: mVhGpSdPTa48eXLlC, qyptziLPtXuwQaDRt)

**Lens 5 アイデア:**
- Zone 2 専用トレーニングコンパニオン（TikTok: 700K+ views）
- モーニングサンライト習慣アプリ（TikTok: 487K+ views）
- Huberman プロトコル全般トラッカー（多すぎる → 絞り込みが必要）

**選定（Lens 5）:** **Zone2Daily** — #zone2cardio + #zone2training = 1.4M+ total views。確認済みトレンド。

---

## Feasibility Filtering

| アイデア | S | P | M | C | T | 結果 |
|---------|---|---|---|---|---|------|
| Zone2Daily | 9 | 9 | 9 | 9 | 9 | ✅ PASS |
| SunProtocol | 8 | 7 | 7 | 8 | 8 | ✅ PASS |
| RespiRate | 7 | 8 | 6 | 9 | 8 | ✅ PASS |
| NasoBreath | 8 | 6 | 6 | 8 | 8 | ✅ PASS |
| BalanceFlow | 6 | 7 | 5 | 8 | 7 | ❌ FAIL（M=5: マネタイズ困難） |
| Intermittent Fasting | 7 | 7 | 8 | 2 | 8 | ❌ FAIL（C=2: Zero が 445K reviews） |
| Somatic Exercises | 6 | 5 | 6 | 8 | 7 | ❌ FAIL（Step 0 除外: VagusReset と同カテゴリ） |
| Posture Reminder | 7 | 6 | 6 | 8 | 7 | ❌ FAIL（Step 0 除外: stretch-flow と同カテゴリ） |

---

## Shortlist (Top 3)

### Rank 1: Zone2Daily

| Field | Value |
|-------|-------|
| idea | Zone2Daily |
| one_liner | Zone 2 心拍数ガイダンスで毎日の有酸素運動を最適化する、HealthKit 連携トレーニングコンパニオン |
| lens | Lens 1 + Lens 4 + Lens 5 |
| platform | iOS 17+ |
| problem_statement | ほとんどの人が「有酸素運動をしているつもり」で Zone 3-4 を走り、Zone 2 の脂肪燃焼・長寿効果を得られていない。マフェトン法（180−年齢）は知られているが、リアルタイムで自分の HR がゾーン内かを確認できるシンプルなアプリが存在しない。 |
| target_user | 30-50 代の Huberman/Attia プロトコル実践者、ランナー・サイクリスト。「より頑張れば良い」思い込みを捨て、科学的トレーニングに移行したい人。 |
| feasibility | S:9 P:9 M:9 C:9 T:9 |
| overall_score | 9.0 |
| monetization_model | Freemium + Subscription ($4.99/月, $29.99/年)。無料: HR ゾーン計算 + 1回分ログ。有料: 無制限ログ + 週間分析 + 目標設定 |
| competition_notes | 競合1: "Zone 2: Heart Rate Training"（226 reviews, 4.65）— 基本機能のみ、UX が古い。競合2: "Zones for Training"（18,871 reviews）— 全ゾーン対応で Zone 2 特化ではなく、有料 (one-time)。競合3: "Zone Trainer: Heart Rate Zones"（15 reviews）— ほぼ存在感なし。 |
| mvp_scope | 1. マフェトン式 Zone 2 HR 自動計算（年齢入力のみ）、2. HealthKit リアルタイム HR 表示 + ゾーン判定、3. ワークアウト記録（Zone 2 滞在時間 %）、4. 週間ダッシュボード（Zone 2 分数推移）、5. Zone 逸脱時のハプティクス通知 |
| next_step | US-002 で product-plan.md を作成 |

---

### Rank 2: SunProtocol

| Field | Value |
|-------|-------|
| idea | SunProtocol |
| one_liner | 起床後 10 分の朝日浴を習慣化する、Huberman プロトコル専用タイマー＆ストリークアプリ |
| lens | Lens 2 + Lens 5 |
| platform | iOS 17+ |
| problem_statement | Andrew Huberman が推奨する「起床後 30 分以内に外で 10 分以上の自然光を浴びる」プロトコルは概日リズム改善に最も効果的だが、実践者は忘れてしまう。専用のシンプルな習慣化アプリが存在しない。 |
| target_user | 25-45 代の Huberman プロトコル実践者。睡眠品質改善・エネルギー向上を求めるバイオハッカー。 |
| feasibility | S:8 P:7 M:7 C:8 T:8 |
| overall_score | 7.67 |
| monetization_model | Freemium + Subscription ($4.99/月, $29.99/年) |
| competition_notes | "Bright Start: Morning Sunlight"（0 reviews）、"Circadian: Your Natural Rhythm"（650 reviews, 4.62）— 低競合 |
| mvp_scope | 1. 朝日浴タイマー（10分カウントダウン）、2. 毎朝リマインダー通知、3. ストリーク追跡、4. Huberman プロトコル解説コンテンツ、5. HealthKit 睡眠データとの相関表示 |
| next_step | US-002 で product-plan.md を作成 |

---

### Rank 3: RespiRate

| Field | Value |
|-------|-------|
| idea | RespiRate |
| one_liner | HealthKit の呼吸数データで睡眠回復スコアを毎朝表示する、リカバリーモニタリングアプリ |
| lens | Lens 3 |
| platform | iOS 17+ |
| problem_statement | Apple Watch は睡眠中の呼吸数を自動記録するが、HealthKit にデータがあるのに活用するアプリがほぼ存在しない。呼吸数の変化は疾患・過訓練・睡眠不足の早期指標だが、ユーザーがアクセスする手段がない。 |
| target_user | Apple Watch ユーザー。アスリート、呼吸器疾患持ち、ウェルネス意識の高い 30-50 代。 |
| feasibility | S:7 P:8 M:6 C:9 T:8 |
| overall_score | 7.58 |
| monetization_model | Freemium + Subscription ($4.99/月, $29.99/年) |
| competition_notes | 専用アプリはほぼ存在しない。"Elite HRV"（6,628 reviews）はHRV中心で呼吸数特化ではない。 |
| mvp_scope | 1. HealthKit 呼吸数データ読み取り、2. 過去 7 日間のトレンド表示、3. 正常範囲（12-20 回/分）との比較、4. 毎朝の呼吸数サマリー通知、5. 体調変化のアラート |
| next_step | US-002 で product-plan.md を作成 |

---

## Ideas Filtered Out

| アイデア | 除外理由 |
|---------|---------|
| Intermittent Fasting | C=2（Zero が 445K reviews、参入障壁高すぎ） |
| Somatic Exercises | Step 0 除外カテゴリ（VagusReset と同カテゴリ: 迷走神経・自律神経） |
| Posture Reminder | Step 0 除外カテゴリ（stretch-flow と同カテゴリ: 姿勢改善） |
| BalanceFlow | M=5（転倒予防アプリへの課金意欲が低い） |
| NasoBreath | Lens 4 で Zone2Daily より大きな市場機会を発見したため優先度下がる |

---

## Recommendation

**選定アプリ:** Zone2Daily

**理由:**
Zone 2 心拍数トレーニングは TikTok で 1.4M+ ビューの確認済みトレンド（#zone2cardio + #zone2training）。Peter Attia・Andrew Huberman が広めた「長寿・脂肪燃焼」の文脈でメインストリーム化が急速に進んでいる。App Store では最も近い競合「Zone 2: Heart Rate Training」が **226 レビューのみ**という圧倒的な市場の穴が存在する。マフェトン式（180−年齢）という科学的根拠のある計算式に基づき、AI API 一切不要で完全ローカル実装が可能。HealthKit との深い統合で Apple プラットフォームの強みを最大限活用できる。全スコアリング基準で満点近い **9.0/10** を記録した唯一のアイデア。

**ソース:**
- Source: [Apify TikTok Scraper — #zone2cardio 709K views](https://api.apify.com/v2/datasets/mVhGpSdPTa48eXLlC/items)
- Source: [iTunes Search API — Zone 2: Heart Rate Training (226 reviews)](https://itunes.apple.com/search?term=zone+2+heart+rate+training)
- Source: [Peter Attia MD — Zone 2 Training](https://peterattiamd.com/zone2/)
- Source: [Huberman Lab — Zone 2 Cardio](https://hubermanlab.com/zone-2-cardio-and-maximum-aerobic-output/)
- Source: [DEV Community — iOS App Ideas 2026](https://dev.to/devin-rosario/future-proofing-your-first-app-15-ideas-2026-tools-26mc)
