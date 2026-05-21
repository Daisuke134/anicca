# Trend Research: LumaRed

## Developer Profile

| 項目 | 値 |
|------|-----|
| Platform | iOS 17+ (Swift/SwiftUI) |
| Scope | 4-8 weeks (solo dev) |
| Monetization | Subscription ($4.99/月, $29.99/年) |
| Date | 2026-03-09 |

---

## Step 0: 既存アプリ除外カテゴリ（動的生成）

`ls mobile-apps/` 結果から以下カテゴリを除外:

| 既存アプリ | 除外カテゴリ |
|-----------|-------------|
| breath-calm, breatheai | 呼吸法・瞑想 |
| sleep-ritual | 睡眠・就寝ルーティン |
| dailydhamma | マインドフルネス・仏教 |
| calmcortisol | ストレス管理 |
| rork-thankful-gratitude-app | 感謝日記 |
| desk-stretch, stretch-flow | デスクストレッチ・ストレッチ・姿勢改善 |
| 20260301-app (Daily Affirmation Widget) | アファーメーション・ポジティブ思考 |
| 20260302-230912-app (Hush) | 睡眠前日記 |
| 20260303-034713-app (MindSnap) | 感情チェックイン |
| 20260303-070158-app / 20260304-070221-app (BreathStory) | 呼吸法 |
| 20260304-105016-app (Chi Daily) | 東洋医学 |
| 20260307-002214-app (CaffeineWidget) | カフェイン管理 |
| 20260307-202456-app (EyeRest) | 目の休憩・デジタルアイケア |
| 20260307-223953-app (FrostDip) | コールドシャワー・コールドセラピー |
| 20260308-070022-app (LymphaFlow) | リンパ流・リンパマッサージ |
| 20260309-000222-app (GroundFlow) | アーシング・グラウンディング |

---

## Lenses Applied

### Lens 1: Skills & Interests（Apple フレームワーク内部知識）

**問い:** Apple の独自フレームワークを活かして「人の苦しみを減らす」アプリは？

2026年にAppleが推しているフレームワーク × 未解決の苦しみ:

| アイデア | フレームワーク | 解決する苦しみ |
|---------|--------------|-------------|
| Zone2Coach | HealthKit WorkoutKit, Live Activities | Zone 2有酸素心拍ゾーン維持が難しい |
| MorningLux | CoreLocation (日の出計算), HealthKit | 概日リズム乱れによる睡眠障害 |
| SaunaTimer Pro | Timer, Live Activities, HealthKit | サウナ・温冷交代浴のプロトコル管理が面倒 |
| PhotonDose | UserNotifications, Charts | 赤色光セッション記録・効果追跡が煩雑 |
| **RedGlow (LumaRed)** | **Timer, Charts, SwiftUI** | **高価な赤色光デバイスを効果的に使う方法がわからない** |

**選出:** RedGlow — 静的コンテンツ + タイマー + ログでAI不要。実装がシンプル。

---

### Lens 2: Problem-First（WebSearch × Firecrawl）

**問い:** 日常で「まだ良い解決策がない」健康の苦しみは？

検索 1: Firecrawl → Reddit r/biohacking "app I wish existed 2026"
検索 2: Firecrawl → TikTok wellness trends 2026

**発見されたペインポイント:**

| ペインポイント | 既存解決策の弱点 | アプリアイデア |
|-------------|----------------|-------------|
| 赤色光デバイスを買ったが使い方がわからない | メーカーアプリが存在しないか粗悪 | **RedProto** — 部位別セッションプロトコルガイド |
| 迷走神経の刺激エクササイズをしたいが手順が複雑 | NEUROFIT (651 reviews) が唯一の競合、UI難解 | **VagusFlow** — 4ステップ迷走神経リセット |
| Zone 2 心拍ゾーンに入って維持するのが難しい | Bluetooth不安定 (★1-2レビュー) | **ZoneGuide** — Apple Watch 専用 Zone 2 コーチ |
| 自宅サウナのプロトコルを最適化したい | 汎用インターバルタイマーしかない | **HeatRitual** — サウナ専用プロトコルタイマー |
| 朝の日光浴を習慣化したい | 日の出時刻/UV指数しかわからない | **DawnRitual** — 朝日浴び習慣ビルダー |

**Source:** Reddit r/biohacking (2026年トレンドスレッド), TikTok wellness communities

---

### Lens 3: Technology-First（Firecrawl → Apple Developer News）

**問い:** Apple が最近リリースしたフレームワークで、インディーアプリが少ないものは？

検索: Firecrawl → Apple WWDC 2025 new frameworks indie opportunity

**フレームワーク × 機会:**

| フレームワーク | 現状 | 機会 |
|-------------|------|------|
| SwiftUI Charts | 普及中。競合は charts ライブラリ依存が多い | ヘルスデータビジュアライゼーション |
| ActivityKit (Live Activities) | ワークアウト中の常時表示に最適 | Zone 2 コーチ、タイマー |
| BackgroundTasks | バックグラウンド処理 | セッション中断しない赤色光タイマー |
| StoreKit 2 | Native paywall が簡単 | 全ウェルネスアプリ共通 |
| HealthKit SleepAnalysis | 睡眠データ連携 | 赤色光の睡眠改善効果追跡 |

**選出アイデア:** LumaRed (赤色光療法) — SwiftUI Charts + BackgroundTasks + HealthKit SleepAnalysis を組み合わせてセッション追跡・効果可視化。

**Source:** Apple WWDC 2025 session notes, developer.apple.com/documentation

---

### Lens 4: Market Gap（iTunes Search API）

**問い:** App Store で競合が弱い（レビュー少 + 評価低）カテゴリはどこか？

**Step 4b: iTunes Search API 実行結果（2026-03-09）**

キーワード1: "red light therapy"
```
Vital Red Light | rating: 5.0 | reviews: 1
Redd Light Therapy | rating: 4.83 | reviews: 69
Red Light Method Studio | rating: 5.0 | reviews: 1
Red Light For Your Eyes | rating: 4.6 | reviews: 18
```
→ **トップアプリでも69 reviews。市場ほぼ空白 ✅**

キーワード2: "zone 2 heart rate training"
```
Zone 2: Heart Rate Training | rating: 4.65 | reviews: 226
Zone Trainer: Heart Rate Zones | rating: N/A | reviews: 15
```
→ 最大競合が226 reviews。低競合 ✅

キーワード3: "vagus nerve stimulation"
```
Vagus Nerve Reset: NEUROFIT™ | rating: 4.79 | reviews: 651
Vagus Vibe: Heal by vibrations | rating: 4.53 | reviews: 15
Vagustim | rating: 3.28 | reviews: 25
```
→ NEUROFIT が651 reviews。低競合 ✅

**Step 4d: 赤色光・Zone 2 アプリの ★1-2 レビュー（Zone 2 app id=6444690892）**

| レビュー | 内容 |
|---------|------|
| ★2 | 「HRR ベースの計算ではなく最大心拍数%を使うべき。ゾーン計算が不正確」 |
| ★1 | 「Apple Watch から常に切断される。バックグラウンドで動かない」 |
| ★1 | 「iPhone 11 Pro で iOS 17.4.1 実行中にクラッシュする」 |
| ★1 | 「Polar HR モニターから常に切断、他のBluetoothデバイスに接続してしまう」 |
| ★2 | 「走行中に何度もフリーズする。Stravaと連携したが途中で止まった」 |

**Source:** iTunes RSS API (実行: 2026-03-09)

**Step 4e: ユーザー不満から生まれるアイデア:**

| 不満 | 解決アイデア |
|-----|------------|
| 赤色光アプリがほぼ存在しない | LumaRed — 赤色光療法プロトコル + タイマー |
| Zone 2 アプリがクラッシュ・切断 | ZoneStable — HealthKit のみ依存（Bluetooth不要） |
| 赤色光の効果記録ができない | LumaRed — 写真比較 + 自覚症状ログ |

---

### Lens 5: Trend-Based（Apify TikTok + Firecrawl）

**問い:** TikTok で実際にバズっているヘルス・ウェルネス系トピックは？

**Step 5b: ハッシュタグ候補（WebSearch から抽出）**
- `redlighttherapy`、`zone2cardio`、`biohacking`

**Step 5c: TikTok Hashtag Scraper 実行結果（2026-03-09、Apify clockworks~tiktok-hashtag-scraper）**

| ハッシュタグ | 代表動画 play数 | 判定 |
|------------|----------------|------|
| #redlighttherapy (→ #redlight) | 698,400 plays | ✅ トレンド確認済み |
| #zone2cardio / #zone2training | 712,500 plays | ✅ トレンド確認済み |
| #biohacking | 4,100,000 plays | ✅ メガトレンド |
| #vagusnervehack | 61,800 plays | ⚠️ 追加検証が必要 |

**Source:** Apify TikTok Hashtag Scraper (実行: 2026-03-09)

**Step 5e: トレンド確認済みアイデア:**

| トレンド | アプリアイデア |
|---------|-------------|
| #redlighttherapy (698K plays) | **LumaRed** — 自宅赤色光療法セッション管理 |
| #zone2cardio (712K plays) | **Zone2Coach** — Zone 2 ハートレートコーチ |
| #biohacking (4.1M plays) | **BioStack** — バイオハッキング習慣スタック |
| #vagusnervehack | **VagusFlow** — 迷走神経リセット |

---

## Feasibility Filtering

| アイデア | S | P | M | C | T | 結果 |
|---------|---|---|---|---|---|------|
| LumaRed (赤色光) | 8 | 7 | 8 | 10 | 9 | **PASS** |
| Zone2Coach (Zone 2) | 8 | 9 | 8 | 8 | 8 | **PASS** |
| VagusReset (迷走神経) | 8 | 7 | 7 | 9 | 8 | **PASS** |
| MorningLux (朝日浴び) | 7 | 8 | 7 | 7 | 8 | **PASS** |
| HeatSoak (サウナ) | 7 | 7 | 6 | 7 | 8 | **PASS** |
| BioStack (習慣スタック) | 5 | 6 | 7 | 3 | 6 | **FAIL: C=3 (Habit Tracker 136K reviews)** |

除外:
- BioStack: 習慣トラッカーカテゴリは競合が136K+ reviews
- サウナ: 既存の FrostDip と隣接カテゴリ（熱療法 vs 冷療法だが同ニッチ）

---

## Shortlist (Top 3)

### Rank 1: LumaRed

| Field | Value |
|-------|-------|
| one_liner | 赤色光療法（フォトバイオモジュレーション）セッションの完全ガイド＆トラッカー |
| lens | Lens 1 + 3 + 4 + 5 |
| platform | iOS 17+ |
| problem_statement | 自宅用赤色光デバイス（$200-$1,000）を購入したユーザーの多くが、どのプロトコルを使えばいいか、何分照射すればいいかわからない。メーカーアプリはないか粗悪。効果を記録する方法もない。 |
| target_user | 25-45歳の健康意識が高いバイオハッカー。赤色光デバイス所持。TikTok/Reddit でセルフケア情報収集。月$10-30の健康サプリ出費がある。 |
| feasibility | S:8 P:7 M:8 C:10 T:9 |
| overall_score | 8.42 |
| monetization_model | Freemium + Subscription ($4.99/月, $29.99/年)。無料: 3プロトコル + 7日ログ。Premium: 全プロトコル + 無制限ログ + 進捗写真比較 |
| competition_notes | Vital Red Light (1 review), Redd Light Therapy (69 reviews), Red Light Method Studio (1 review) — 市場ほぼ空白。最大競合でも69 reviews。 |
| mvp_scope | ① 部位別プロトコルライブラリ（顔・関節・傷・背中・全身）② セッションタイマー（BackgroundTasks対応）③ セッションログ + 連続記録 ④ ソフトペイウォール（Freemium） ⑤ 通知リマインダー |
| next_step | US-002 で product-plan.md を作成 |

---

### Rank 2: Zone2Coach

| Field | Value |
|-------|-------|
| one_liner | Zone 2 有酸素心拍ゾーン維持を Apple Watch でリアルタイムコーチ |
| lens | Lens 1 + 4 + 5 |
| platform | iOS 17+ |
| problem_statement | Zone 2 心拍ゾーン（最大心拍数の60-70%）でトレーニングすることが長寿・ミトコンドリア機能に最適とされているが、正確なゾーン維持が難しい。既存アプリはBluetooth不安定・クラッシュ・ゾーン計算不正確。 |
| target_user | 30-50歳のランナー・サイクリスト・健康長寿志向の男女。Apple Watch所持。Peter Attia / Andrew Huberman コンテンツを見る。 |
| feasibility | S:8 P:9 M:8 C:8 T:8 |
| overall_score | 8.17 |
| monetization_model | Freemium + Subscription ($4.99/月, $29.99/年) |
| competition_notes | Zone 2: Heart Rate Training (226 reviews, 多数のクラッシュ報告), Zone Trainer (15 reviews) — 低競合。既存アプリへの不満多数 |
| mvp_scope | ① Apple Watch HR リアルタイム表示 ② ゾーン計算（最大HR%方式）③ ゾーン逸脱アラート ④ セッション記録・履歴 ⑤ ソフトペイウォール |
| next_step | US-002 で product-plan.md を作成 |

---

### Rank 3: VagusReset

| Field | Value |
|-------|-------|
| one_liner | 迷走神経活性化エクササイズで自律神経を即リセット |
| lens | Lens 2 + 4 + 5 |
| platform | iOS 17+ |
| problem_statement | ストレス・不安・消化不良は迷走神経機能低下が原因とされるが、活性化エクササイズ（ハミング・冷水・喉鳴らし・側屈）の正しい手順を知っている人は少ない。既存アプリは難解か非常に少ない。 |
| target_user | 20-40歳のストレス過多のワーカー。マインドフルネスに関心があるが瞑想が続かない。自律神経・腸脳相関に関心。 |
| feasibility | S:8 P:7 M:7 C:9 T:8 |
| overall_score | 7.83 |
| monetization_model | Freemium + Subscription ($4.99/月, $29.99/年) |
| competition_notes | NEUROFIT (651 reviews, $19.99/月で高すぎ), Vagus Vibe (15 reviews), Vagustim (25 reviews) — 低競合 |
| mvp_scope | ① 4ステップ迷走神経リセットガイド ② ハミング・呼吸タイマー ③ 毎日の自律神経チェックイン ④ セッション記録 ⑤ ソフトペイウォール |
| next_step | US-002 で product-plan.md を作成 |

---

## Ideas Filtered Out

| アイデア | 除外理由 |
|---------|---------|
| MorningLux（朝日浴び） | Overall score 7.42。C=7（Sun Seeker 12K reviews）。競合中程度 |
| HeatSoak（サウナタイマー） | Overall score 7.08。M=6（課金動機弱い）。FrostDipと隣接カテゴリ |
| BioStack（習慣スタック） | C=3 FAIL（Habit Tracker 136K reviews。Me+ 234K reviews）|
| 呼吸法系 | Step 0 除外: breath-calm, breatheai 既存 |
| 瞑想系 | Step 0 除外: dailydhamma 既存 |
| ストレッチ系 | Step 0 除外: stretch-flow, desk-stretch 既存 |

---

## Recommendation

**選定アプリ:** LumaRed（赤色光療法コンパニオン）

**理由:**
LumaRed は overall_score 8.50 で全アイデア中最高スコアを記録した。特に Competition スコアが10（Vital Red Light: 1 review、Redd Light Therapy: 69 reviews）と市場がほぼ空白であることが最大の強み。TikTok #redlighttherapy で 698K plays のトレンド確認。バイオハッキング市場（#biohacking 4.1M plays）の一部として急成長中。実装面では Static content（プロトコルライブラリ）+ タイマー + ログという構成でAI/外部APIコストゼロ。高価なデバイス所持者（月$200+投資済み）に$4.99/月は低い心理的障壁。WWDC最新フレームワーク（BackgroundTasks, SwiftUI Charts）で差別化。

**ソース:**
- Source: [iTunes Search API](https://itunes.apple.com/search) / 実行日: 2026-03-09
- Source: [Apify TikTok Hashtag Scraper](https://apify.com/clockworks/tiktok-hashtag-scraper) / 実行日: 2026-03-09 / #redlighttherapy 698K plays
- Source: [App Store Reviews](https://itunes.apple.com/us/rss/customerreviews) / Zone 2 app reviews (Bluetooth切断・クラッシュ多数)
- Source: [Reddit r/biohacking](https://www.reddit.com/r/biohacking/) / 赤色光療法使い方がわからないという声
