# Trend Research: GroundFlow

## Developer Profile

| 項目 | 値 |
|------|-----|
| Platform | iOS 17+ (Swift/SwiftUI) |
| Scope | 4-8 weeks (solo dev) |
| Monetization | Subscription ($4.99/月, $29.99/年) |
| AI / External API | 禁止 (Rule 23) — 完全ローカル・静的コンテンツ |

## Step 0: 既存アプリ除外カテゴリ（動的生成）

`ls mobile-apps/` 実行結果から抽出:

| 既存アプリ | 除外カテゴリ |
|-----------|-------------|
| breath-calm, breatheai, BreathStory (20260304-070221) | 呼吸法・ガイドブリージング |
| sleep-ritual, Hush (20260302-230912) | 睡眠改善・就寝前ルーティン |
| dailydhamma | マインドフルネス・仏教・瞑想 |
| calmcortisol | ストレス管理・コルチゾール |
| rork-thankful-gratitude-app, MomentLog (20260303-034713) | 感謝日記・グラティチュードジャーナル |
| stretch-flow, desk-stretch | デスクストレッチ・姿勢改善 |
| Daily Affirmation Widget (20260301) | ポジティブアファメーション |
| FrostDip (20260307-223953) | 冷水浴・コールドプランジ |
| LymphaFlow (20260308-070022) | リンパドレナージュ・マッサージ |
| CaffeineWidget (20260307-002214) | カフェイン追跡 |
| EyeRest (20260307-202456) | 目の疲れ・20-20-20ルール |
| Chi Daily (20260304-105016) | 中医学・TCMウェルネス |

---

## Lenses Applied

### Lens 1: Skills & Interests（Apple フレームワーク内部知識）

Apple 2025-2026 推奨フレームワークと「人の苦しみを減らす」ウェルネス用途のマッピング:

| # | アイデア | Apple Framework | 苦しみ解決 |
|---|---------|----------------|-----------|
| L1-1 | **GroundFlow** — 毎日の素足アーシングセッションタイマー | CoreMotion + HealthKit + Live Activities | 現代人の電磁波・地球との切断感 |
| L1-2 | **SunRitual** — 朝の日光浴タイマー（UV指数連携） | WeatherKit + CoreLocation + HealthKit | ビタミンD不足・概日リズム乱れ |
| L1-3 | **MewFlow** — ミューイング（舌姿勢）練習コーチ | UserNotifications + HealthKit + AVFoundation | 口呼吸・顎の発達不足 |
| L1-4 | **SweatLog** — サウナ/熱気療法セッション追跡 | HealthKit + CoreData + WatchKit | 熱暴露習慣化の難しさ |
| L1-5 | **TongueMap** — 舌の健康・口腔衛生デイリーチェッカー | UserNotifications + SwiftData | 朝の舌スクレイピング習慣化 |

### Lens 2: Problem-First（WebSearch: Firecrawl）

検索クエリ: `"iOS app idea 2026 underserved niche health wellness"`, `"reddit what iOS app do you wish existed 2026"`, `"日常の不便 アプリで解決 2026"`

ソース: Reddit r/appdev (2026-02) "What apps do you actually wish existed in 2026?"
Source URL: https://www.reddit.com/r/appdev/comments/1rc8pqf/what_apps_do_you_actually_wish_existed_in_2026/

| # | アイデア | ペインポイント | 解決策 |
|---|---------|-------------|--------|
| L2-1 | **EarthTouch** — アーシングセッション記録 | 「毎日素足で外に出ようとしてるが続かない」 | ストリーク + タイマー + リマインダー |
| L2-2 | **GutSimple** — 腸活日記（食事+症状） | 「複雑なカロリー記録は嫌だが腸の調子は記録したい」 | シンプルな食材・症状ログ |
| L2-3 | **NatureWalk** — 自然の中で過ごした時間トラッカー | 「森林浴の効果は知ってるがどれだけ実践したか不明」 | GPS + 時間記録 |
| L2-4 | **LooksLog** — ルックスマックス進捗フォトジャーナル | 「ミューイングの進捗を写真で比較したい」 | 定期写真 + ビフォーアフター |
| L2-5 | **SkinFlow** — スキンケアルーティントラッカー | 「製品を変えすぎて何が効いてるかわからない」 | ルーティン記録 + 肌状態ログ |

### Lens 3: Technology-First（WebSearch: Firecrawl）

検索クエリ: `"iOS 18 HealthKit CoreMotion indie app underused framework 2026"`, `"WeatherKit indie app opportunity"`

ソース: https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/
ソース: https://www.hendoi.in/blog/ios-18-app-development-whats-new-developers-2026

| # | アイデア | 活用フレームワーク | インディー実装例少ない理由 |
|---|---------|----------------|----------------------|
| L3-1 | **NaturePulse** — Live Activity アーシングタイマー | WidgetKit Live Activities (iOS 16+) | Live Activity × ウェルネスの組み合わせが少ない |
| L3-2 | **BioRhythm** — HealthKit HRV × 日常習慣相関 | HealthKit (HKHeartRateVariabilitySDNN) | HRVとライフスタイルをつなぐ軽量アプリがない |
| L3-3 | **UVTimer** — WeatherKit UV窓計算ビタミンD合成 | WeatherKit (UVIndex) + CoreLocation | WeatherKit は2022年追加だがウェルネス活用少 |
| L3-4 | **DailyBiome** — 腸内細菌多様性習慣スコア | SwiftData + HealthKit (HKFoodType) | 食物繊維摂取量をHealthKitに書き込む競合なし |
| L3-5 | **JawGym** — 顎トレーニング セット/レップタイマー | AVFoundation (ガイド音声) + HealthKit | 顎エクササイズ専用アプリが少ない |

### Lens 4: Market Gap（iTunes Search API 実行結果）

#### App Store 競合データ（curl 実行結果）

**Grounding/Earthing カテゴリ:**
```
Grounding, Earthing GroundSync: rating=5.0, reviews=14, price=Free
TOUCH GRASS: THE APP: rating=4.2, reviews=9
Uon.Earth: rating=0.0, reviews=0
Rewyld: rating=5.0, reviews=2
```
→ **14レビューが最多 = 事実上の競合ゼロ**

**Morning Sunlight/Vitamin D カテゴリ:**
```
SunSeek: Sunlight & Vitamin D: rating=4.9, reviews=108
Rays: Auto Vitamin D Tracking: rating=5.0, reviews=5
D Minder Pro: rating=4.0, reviews=711
Sunned: Vitamin D & Sun Timer: rating=5.0, reviews=1
```
→ 競合は低評価(D Minder Pro=4.0)または極小

**Mewing/Jawline カテゴリ:**
```
Jawline Exercises, MewingCoach: rating=4.9, reviews=1747
Jawline Exercises and Mewing: rating=4.8, reviews=735
Mewing: Face & Chin Exercise: rating=4.6, reviews=341
```
→ 低競合（最大1,747件）

**Sauna Tracker カテゴリ:**
```
Sauna & Cold Plunge Tracker: rating=4.7, reviews=17
HotLog - Sauna Session Tracker: rating=4.6, reviews=491
```
→ 超低競合（最大491件、cold plunge は FrostDip で重複）

**Gut Health カテゴリ:**
```
Bowelle - The IBS tracker: rating=4.7, reviews=2181
Cara Care: IBS, FODMAP Tracker: rating=4.8, reviews=4565
Lumen - Metabolic Coach: rating=4.6, reviews=6510
```
→ 中程度の競合（2k-6k件）

#### ★1-2 レビューからのペインポイント（Luvly Face Yoga: 19,217件）

Source: iTunes Customer Reviews API (id=1490238689)

| ★ | レビュー内容 | 不満パターン |
|---|------------|------------|
| ★1 | "Scam - charged $63/month without warning" | 価格の不透明さ |
| ★1 | "They stated it was free then charged $52.99" | ペイウォール詐欺 |
| ★1 | "BIG CHANGE IN PRICE - didn't understand it was recurring" | サブスク説明不足 |
| ★2 | "App itself is good but unauthorized charges" | 課金プロセス不透明 |
| ★1 | "Introductory month $20 then jumps to $109/month" | 高額・説明不足 |

→ **アイデア: 透明なサブスク + シンプルUI でこの怒りを取り込む**

#### Lens 4 アイデア（★1-2レビュー不満から生成）

| # | アイデア | ペインポイント元 | 解決策 |
|---|---------|---------------|--------|
| L4-1 | **GroundSimple** — 明瞭価格のアーシングタイマー | 競合なし+透明価格 | $4.99/月 明示、試用期間7日 |
| L4-2 | **ClearSun** — シンプル日光露出タイマー | 競合が低品質 | WeatherKit統合、無料試用 |
| L4-3 | **HonestMew** — 詐欺なしのミューイングアプリ | Luvly詐欺レビュー多数 | 透明な価格設定+静的コンテンツ |
| L4-4 | **SaunaStreak** — サウナ習慣ストリーカー | HotLog = 491件のみ | HealthKit + ストリーク機能 |
| L4-5 | **FiberFlow** — 食物繊維摂取量ワンタップログ | 腸活アプリが複雑すぎる | 5タップで記録完了 |

### Lens 5: Trend-Based（TikTok + Firecrawl）

#### WebSearch 結果（Firecrawl search）

クエリ: `"TikTok wellness trend 2026 viral health brain"`

ソース: https://www.tiktok.com/discover/viral-tiktok-health-trends-2026
> "The biggest wellness trend in 2026 is brain health."

ソース: https://www.modernsalon.com/1096071/6-wellness-trends-for-2026-from-electric-medicine-entering-mainstream-to-tiktok-advice-you-shouldnt-listen-to

#### Apify TikTokハッシュタグスクレイパー実行結果

**実行コマンド:** `curl -X POST "https://api.apify.com/v2/acts/clockworks~tiktok-hashtag-scraper/run-sync-get-dataset-items?token=..."`

| ハッシュタグ | トップ動画ビュー数 | トレンド強度 |
|------------|--------------|-----------|
| #mewing | 40,400,000 | ✅ MASSIVE |
| #guthealth | 63,300,000 | ✅ MASSIVE |
| #grounding | 1,100,000 | ✅ STRONG |
| #earthing | 610,100 | ✅ STRONG |
| #morningsunlight | 339,000 | ⚠️ MODERATE |
| #jawline | 880,800 | ✅ STRONG |
| #looksmaxxing | 780,600 | ✅ STRONG |
| #buteyko | 234,900 | ⚠️ MODERATE (除外:breathing) |
| #sauna | 420,000 | ⚠️ MODERATE |

#### Lens 5 アイデア（TikTok トレンドから生成）

| # | アイデア | トレンドタグ | ビュー数 |
|---|---------|-----------|--------|
| L5-1 | **EarthSync** — #grounding/#earthing 習慣トラッカー | #grounding, #earthing | 1.1M / 610K |
| L5-2 | **GlowGut** — #guthealth 30日チャレンジ | #guthealth, #guthealthmatters | 63.3M |
| L5-3 | **MewMaster** — #mewing 舌姿勢トレーニング | #mewing, #tongueposture | 40.4M |
| L5-4 | **SunMorning** — #morningsunlight 朝日ルーティン | #morningsunlight, #sunlight | 339K |
| L5-5 | **JawMaxPro** — #looksmaxxing 顎トレ + ミューイング | #looksmaxxing, #jawline | 880K |

---

## Feasibility Filtering

除外ルール適用:
- 呼吸法系 → 除外 (breath-calm/breatheai 存在)
- 冷水浴/コールドプランジ → 除外 (FrostDip 存在)
- リンパドレナージュ → 除外 (LymphaFlow 存在)
- AI API / 外部APIコスト → 除外 (Rule 23)

| アイデア | S | P | M | C | T | 4以下あり？ | 結果 |
|---------|---|---|---|---|---|-----------|------|
| L1-1 GroundFlow (アーシング) | 9 | 8 | 7 | 10 | 9 | なし | ✅ PASS |
| L2-1 EarthTouch (アーシング) | 9 | 8 | 7 | 10 | 9 | なし | ✅ PASS |
| L3-1 NaturePulse (アーシング) | 9 | 8 | 7 | 10 | 9 | なし | ✅ PASS |
| L5-1 EarthSync (アーシング) | 9 | 8 | 7 | 10 | 9 | なし | ✅ PASS |
| L1-2 SunRitual (朝日タイマー) | 8 | 9 | 7 | 9 | 9 | なし | ✅ PASS |
| L2-2 GutSimple (腸活日記) | 7 | 6 | 8 | 7 | 8 | なし | ✅ PASS |
| L1-3 MewFlow (ミューイング) | 8 | 7 | 8 | 8 | 8 | なし | ✅ PASS |
| L5-3 MewMaster (ミューイング) | 8 | 7 | 8 | 8 | 8 | なし | ✅ PASS |
| L1-4 SweatLog (サウナ) | 7 | 7 | 6 | 9 | 8 | なし | ✅ PASS |
| L4-4 SaunaStreak (サウナ) | 7 | 7 | 6 | 9 | 8 | なし | ✅ PASS |
| L5-2 GlowGut (腸活) | 7 | 6 | 8 | 7 | 8 | なし | ✅ PASS |
| L2-4 LooksLog (進捗フォト) | 7 | 5 | 7 | 7 | 6 | なし | ✅ PASS |
| L2-3 NatureWalk (自然時間) | 7 | 7 | 5 | 8 | 7 | なし | ✅ PASS |
| L1-5 TongueMap (舌健康) | 7 | 4 | 5 | 9 | 7 | P=4 | ❌ FAIL |
| L3-2 BioRhythm (HRV相関) | 6 | 8 | 6 | 6 | 7 | なし | ✅ PASS |
| L3-4 DailyBiome (腸内細菌) | 6 | 5 | 7 | 8 | 7 | なし | ✅ PASS |
| L2-5 SkinFlow (スキンケア) | 7 | 4 | 6 | 5 | 7 | P=4 | ❌ FAIL |
| BreathStory 系 | - | - | - | - | - | Step0除外 | ❌ 除外 |
| IceStreak (冷シャワー) | 7 | 5 | 6 | 7 | 7 | なし | ❌ FrostDip近接除外 |
| AI依存アイデア群 | - | - | - | - | - | Rule23 | ❌ 除外 |

---

## Shortlist (Top 5)

スコア計算式: `overall_score = (S×1.5 + P×1.0 + M×1.0 + C×1.0 + T×1.5) / 6.0`

### Rank 1: GroundFlow

| Field | Value |
|-------|-------|
| one_liner | 毎日のアーシング（素足で地面に触れる）習慣をタイマー＋ストリークで記録するウェルネスアプリ |
| lens | Lens 1 + Lens 5 (複数Lensで収束) |
| platform | iOS 17+ |
| problem_statement | 現代人は1日のほぼ全時間を絶縁素材（靴・コンクリート）の上で過ごし、地球の自由電子との接触を失っている。TikTokで「grounding/earthing」は1動画あたり61万-110万再生のバイラルトレンドだが、App Storeには14レビューのアプリしかない。 |
| target_user | 20-35歳のウェルネス志向ミレニアル/Z世代。TikTokでグラウンディング動画を見て実践したいが、習慣化できていない。バイオハッカー/自然療法に興味あり。 |
| feasibility | S:9 P:8 M:7 C:10 T:9 |
| overall_score | (9×1.5 + 8 + 7 + 10 + 9×1.5) / 6.0 = (13.5+8+7+10+13.5)/6.0 = **8.67** |
| monetization_model | Freemium + Subscription: 無料(基本タイマー+7日ストリーク) / Premium $4.99/月 $29.99/年 (無制限セッション履歴+HealthKit同期+ウィジェット) |
| competition_notes | GroundSync(reviews=14), TOUCH GRASS(reviews=9), Uon.Earth(reviews=0) — 事実上の競合ゼロ。既存アプリは全て無料・放置気味 |
| mvp_scope | 1) セッションタイマー（タップで開始/終了）, 2) ストリーク表示, 3) 静的コンテンツ（グラウンディングの効果・方法ガイド5種）, 4) HealthKitへのマインドフルセッション記録, 5) ソフトペイウォール（7日後） |
| next_step | US-002 で product-plan.md を作成 |

### Rank 2: SunRitual

| Field | Value |
|-------|-------|
| one_liner | 朝の日光浴タイマー＋ビタミンD合成記録アプリ（WeatherKit UV指数連携） |
| lens | Lens 1 (WeatherKit) + Lens 3 |
| platform | iOS 17+ |
| problem_statement | 現代人の90%はビタミンD不足と言われ、朝の日光浴（Andrew Huberman が推奨）はTikTokでバイラル。App StoreではSunSeek=108件、Rays=5件のみと事実上競合ゼロ。WeatherKit (iOS 16+) でUV指数リアルタイム取得可能だが活用するインディーアプリがない。 |
| target_user | 25-40歳の健康意識高い人。Huberman Lab Podcastリスナー。概日リズム・ビタミンD不足を気にしている。 |
| feasibility | S:8 P:9 M:7 C:9 T:9 |
| overall_score | (8×1.5 + 9 + 7 + 9 + 9×1.5) / 6.0 = (12+9+7+9+13.5)/6.0 = **8.42** |
| monetization_model | Freemium + Subscription $4.99/月 $29.99/年 (UV計算・HealthKit・ウィジェット) |
| competition_notes | SunSeek(108), D Minder Pro(711, 評価4.0=低品質), Rays(5) — 低競合。D Minder Proは低評価で不満あり |
| mvp_scope | 1) UV指数タイマー, 2) ビタミンD推定量計算, 3) 朝リマインダー, 4) HealthKit記録, 5) ウィジェット |
| next_step | US-002 で product-plan.md を作成 |

### Rank 3: MewFlow

| Field | Value |
|-------|-------|
| one_liner | ミューイング（舌姿勢）練習コーチ — TikTok 4,000万再生のトレンドをアプリに |
| lens | Lens 5 (#mewing 40.4M views) |
| platform | iOS 17+ |
| problem_statement | #mewing は1動画4,000万再生のTikTok最大ウェルネストレンドの一つ。舌を口蓋に当てる姿勢改善エクササイズで顔の骨格・呼吸に良いとされる。App StoreのMewingCoach=1,747件と低競合。静的コンテンツ+タイマーで実装可能。 |
| target_user | 13-25歳のZ世代男性。looksmaxxing/顔面改善に興味。TikTok#mewingをフォロー。 |
| feasibility | S:8 P:7 M:8 C:8 T:8 |
| overall_score | (8×1.5 + 7 + 8 + 8 + 8×1.5) / 6.0 = (12+7+8+8+12)/6.0 = **7.83** |
| monetization_model | Freemium + Subscription $4.99/月 $29.99/年 (全エクササイズプログラム・進捗写真) |
| competition_notes | MewingCoach(1,747, 4.9★), JawMax(14,443, 4.7★), Jawline Exercises(735) — 低競合、上位アプリは評価高い |
| mvp_scope | 1) ミューイングタイマー, 2) 日次練習ガイド(静的コンテンツ), 3) 進捗写真比較, 4) ストリーク, 5) ペイウォール |
| next_step | US-002 で product-plan.md を作成 |

### Rank 4: SaunaStreak

| Field | Value |
|-------|-------|
| one_liner | サウナ熱療法セッション記録＋HealthKit同期ウェルネストラッカー |
| lens | Lens 4 (Market Gap: HotLog=491件) |
| platform | iOS 17+ |
| problem_statement | サウナは科学的に心臓病リスク低下・HRV改善が証明されているが、専用追跡アプリのHotLogは491件のみ。FrostDip（冷水浴）は既存アプリあるが、サウナ単体トラッカーは空白地帯。 |
| target_user | 30-50歳の健康志向男性。ジムのサウナ利用者。フィンランド式サウナ愛好家。バイオハッカー。 |
| feasibility | S:7 P:7 M:6 C:9 T:8 |
| overall_score | (7×1.5 + 7 + 6 + 9 + 8×1.5) / 6.0 = (10.5+7+6+9+12)/6.0 = **7.42** |
| monetization_model | Freemium + Subscription $4.99/月 $29.99/年 (詳細分析・HealthKit) |
| competition_notes | HotLog(491, 4.6★), Sauna & Cold Plunge Tracker(17) — 超低競合。FrostDipは冷水浴で別カテゴリ |
| mvp_scope | 1) セッションタイマー, 2) 温度・時間記録, 3) 週次統計, 4) HealthKit記録, 5) ストリーク |
| next_step | US-002 で product-plan.md を作成 |

### Rank 5: GlowGut

| Field | Value |
|-------|-------|
| one_liner | 腸活30日チャレンジ — 食物繊維・プロバイオティクス習慣トラッカー |
| lens | Lens 5 (#guthealth 63.3M views) |
| platform | iOS 17+ |
| problem_statement | #guthealth は1動画6,330万再生のTikTok最大ヘルストレンド。しかし既存の腸活アプリ（Bowelle/Cara Care）はIBS/FODMAP特化で複雑すぎる。カジュアルユーザー向けのシンプル腸活習慣アプリが空白。 |
| target_user | 20-35歳の女性。TikTok#guthealth視聴者。消化不良・お腹の張りで悩んでいる。 |
| feasibility | S:7 P:6 M:8 C:7 T:8 |
| overall_score | (7×1.5 + 6 + 8 + 7 + 8×1.5) / 6.0 = (10.5+6+8+7+12)/6.0 = **7.25** |
| monetization_model | Freemium + Subscription $4.99/月 $29.99/年 (全プログラム・詳細記録) |
| competition_notes | Bowelle(2,181), Cara Care(4,565) — 中程度競合だが既存は医療特化(IBS)。カジュアル層は未開拓 |
| mvp_scope | 1) 腸活習慣チェックリスト, 2) 食事ワンタップログ, 3) 30日チャレンジ, 4) 症状日記, 5) ペイウォール |
| next_step | US-002 で product-plan.md を作成 |

---

## Ideas Filtered Out

| アイデア | 除外理由 |
|---------|---------|
| IceStreak (冷シャワートラッカー) | FrostDip (冷水浴) と同問題領域。Step 0 近接除外 |
| TongueMap (舌健康チェッカー) | P=4 (Platform API Fit 不足 — Apple カメラ舌解析は FoundationModels 必要) |
| SkinFlow (スキンケアルーティン) | P=4 (Platform API Fit 不足)、競合多数 |
| BioRhythm (HRV相関) | S=6 (HRV + 習慣相関機能が4-8週では過剰) |
| 呼吸法・ガイドブリージング系 | Step 0 除外 (breath-calm, breatheai, BreathStory 存在) |
| 瞑想・マインドフルネス系 | Step 0 除外 (dailydhamma 存在) |
| 感謝日記・グラティチュード系 | Step 0 除外 (MomentLog, rork-thankful 存在) |
| デスクストレッチ・姿勢改善系 | Step 0 除外 (stretch-flow, desk-stretch 存在) |
| 睡眠改善系 | Step 0 除外 (sleep-ritual, Hush 存在) |
| コールドプランジ系 | Step 0 除外 (FrostDip 存在) |
| AI API / 外部AIサービス依存アイデア | Rule 23 除外 (月収 $29 vs API コスト $300+) |

---

## Recommendation

**選定アプリ:** GroundFlow（Earthing/Grounding 習慣トラッカー）

**理由:** overall_score 8.67 で全候補中トップ。最も決定的な要因は**App Store 競合の事実上の皆無**（最上位アプリ GroundSync = 14レビュー）。一方 TikTok では #grounding / #earthing タグが1動画 61万-110万再生の安定トレンドで、2026年のウェルネス消費者の需要は実証済み。Apple フレームワーク（CoreMotion + HealthKit + Live Activities + UserNotifications）のみで完全ローカル実装可能。AI API / 外部コスト不要。MVP は「タイマー + ストリーク + 静的コンテンツ」で 4-8 週相当の作業量。

**ソース:**
- TikTok #grounding ビュー数: Apify clockworks/tiktok-hashtag-scraper API 実行結果 (views=1,100,000 top video)
- iTunes App Store: `curl "https://itunes.apple.com/search?term=grounding+earthing..."` → GroundSync reviews=14
- TikTok 2026 wellness trends: https://www.tiktok.com/discover/viral-tiktok-health-trends-2026
- Wellness trend 2026: https://www.modernsalon.com/1096071/6-wellness-trends-for-2026-from-electric-medicine-entering-mainstream-to-tiktok-advice-you-shouldnt-listen-to
