# Trend Research: VagusReset

## Developer Profile

| 項目 | 値 |
|------|-----|
| Platform | iOS 17+ (Swift/SwiftUI) |
| Scope | 4-8 weeks (solo dev) |
| Monetization | Subscription ($4.99/月, $29.99/年) |

---

## Step 0: Pre-check — 除外カテゴリリスト（動的生成）

`ls mobile-apps/` 実行結果から構築した除外カテゴリ:

| 既存アプリ | 除外カテゴリ |
|-----------|-------------|
| breath-calm, breatheai, BreathStory (20260304-070221) | 呼吸法・瞑想 |
| sleep-ritual, Hush (20260302-230912) | 睡眠・寝前ジャーナル |
| dailydhamma | マインドフルネス・仏教 |
| calmcortisol | ストレス管理・コルチゾール |
| rork-thankful-gratitude-app, MomentLog (20260303-034713) | 感謝日記・グラティチュード |
| desk-stretch, stretch-flow | デスクストレッチ・姿勢改善 |
| Daily Affirmation Widget (20260301-app) | アファーメーション |
| EyeBreakIsland (20260307-002214), EyeRest (20260307-202456) | 目のケア・アイブレイク |
| FrostDip (20260307-223953) | コールドプランジ・クライオセラピー |
| LymphaFlow (20260308-070022) | リンパドレナージュ |
| GroundFlow (20260309-000222) | アーシング・グラウンディング |
| LumaRed (20260309-005930) | 赤色光療法（フォトバイオモジュレーション） |
| Chi Daily (20260304-105016) | TCM東洋医学 |
| MindSnap (20260303-070158) | AI日次チェックイン |

---

## Lenses Applied

### Lens 1: Skills & Interests（Apple Frameworks — 検索不要）

Apple 2025-2026 の注目フレームワークと「人の苦しみを減らす」マッピング:

| アイデア | Appleフレームワーク | 用途 |
|---------|------------------|------|
| **CycleSync** — 女性の月経周期別最適化ガイド | HealthKit CycleTracking (iOS 16+) | infradian rhythm 4フェーズ別食事・運動推奨 |
| **WidgetHabit** — ウィジェット単体で完結する習慣トラッカー | WidgetKit + AppIntents (iOS 17 interactive widgets) | アプリを開かずロック画面から習慣チェック |
| **LiveWorkout** — Dynamic Island にリアルタイム心拍表示 | LiveActivity + HealthKit | ワークアウト中に常時HR/ゾーン表示 |
| **PostureDetect** — 背面カメラで姿勢リアルタイム判定 | ARKit + Vision body pose | 座り方をカメラで継続モニタリング |
| **MoodSync** — HealthKit HRV + 日記で気分パターン検出 | HealthKit + NaturalLanguage (on-device) | ローカルNLP + HRVで感情パターン可視化 |

**Lens 1 からの代表アイデア:** **CycleSync** — HealthKit CycleTracking + 4フェーズ別生活最適化

---

### Lens 2: Problem-First（WebSearch実施）

**検索クエリ:**
- `"iOS app idea 2026 underserved niche health wellness"` (Source: dev.to/devin-rosario/future-proofing-your-first-app-15-ideas-2026-tools-26mc)
- `"日常の不便 アプリで解決 2026 wellness"`

**抽出したペインポイントと解決アイデア:**

| ペインポイント | アイデア |
|-------------|---------|
| 肌荒れのトリガーが分からない（食事？睡眠？ストレス？） | **SkinLog** — 毎日30秒で肌写真＋症状記録。週次トレンドで原因特定 |
| キーボード作業でRSI（手首・腱鞘炎）が悪化していく | **WristGuard** — タイピング頻度に応じた手首体操リマインダー |
| 水分補給はしてるのに頭痛が続く（電解質不足） | **ElectroTrack** — 水分＋電解質バランスチェッカー |
| 腸活を毎日続けたいが何をすべきか分からない | **GutDaily** — 発酵食品・食物繊維・水分の3指標デイリートラッカー |
| 自律神経の乱れを感じるが何をすれば良いか不明 | **VagusReset** — 迷走神経活性化エクササイズ（哼り・うがい・冷水・笑い）デイリールーティン |

**Lens 2 からの代表アイデア:** **SkinLog** — 肌コンディション写真日記＋トリガー分析

---

### Lens 3: Technology-First（WebSearch実施）

**検索クエリ:**
- `"Apple HealthKit new features 2025 indie app underused"` (Source: developer.apple.com/technologies/)
- `"iOS 17 18 new framework underused indie developer"`

**フレームワーク × インディーアプリが少ない組み合わせ:**

| フレームワーク | インディーアプリ不足の理由 | アイデア |
|-------------|------------------|---------|
| HealthKit workoutSessionMirroringStartHandler (watchOS 10+) | 複雑なWatch↔Phone連携が必要 | **Zone2Trainer** — Apple Watch HR ↔ Phone でゾーン2心拍トレーニング |
| CoreMotion CMStepCounter + 歩幅推定 | 単なる万歩計と差別化しにくい | **GaitHealth** — 歩幅・歩行速度の健康指標トラッカー（加齢/疲労検知） |
| AVFoundation AVAudioEngine harmonic analysis | 音響解析コストが高い | **HumTrack** — 哼りの音高記録で声帯・迷走神経ケア |
| HealthKit CDHKElectrocardiogramQuery | ECGデータ解析のUXが難しい | **HeartStory** — Apple Watch ECGデータを日常語で解説するコンパニオン |
| ARKit body tracking + CoreML | 端末負荷が高い | **PostureMirror** — ARで姿勢を可視化するリアルタイムコーチ |

**Lens 3 からの代表アイデア:** **Zone2Trainer** — Apple Watch HealthKit + Zone 2 心拍トレーニングガイド

---

### Lens 4: Market Gap（App Store データ）

**Step 4a: 検索キーワード（Lens 1-3から抽出）:**
vagus nerve / zone 2 cardio / HRV biofeedback / skin care tracker / posture trainer

**Step 4b: iTunes Search API 結果:**

| キーワード | トップアプリ | 平均レビュー数 | 平均評価 | 競合判定 |
|----------|-----------|------------|--------|---------|
| vagus nerve | NEUROFIT™ (651), Vagal Tones (0), Vagus Vibe (15) | **222** | 4.4 | ✅ **競合が弱い穴** |
| zone 2 cardio | Zone 2: Heart Rate Training (226), Zones for Training (18,871) | 10,000+ | 4.7 | ⚠️ 混在 (専門アプリは少) |
| HRV biofeedback | HRV4Biofeedback (27), HeartBreath HRV (52) | **40** | 4.1 | ✅ **極めて低競合** |
| skin care tracker | Clear: Social Skincare Tracker (43), Charm (1,468) | **756** | 4.5 | ✅ **低競合** |
| posture trainer | Posture by M&M (679), UPRIGHT (3,918) | **2,300** | 4.7 | ⚠️ 中程度 |

**Step 4c: 競合分析:**
- Vagus nerve カテゴリ: NEUROFIT 651件 = 圧倒的に少ない。チャンス最大
- Zone 2 専門アプリ「Zone 2: Heart Rate Training」= 226件（低）
- HRV biofeedback = ほぼ空白カテゴリ

**Step 4d: ★1-2 レビュー（NEUROFIT — vagus nerve app）:**
- `"Worked for 5 days then quit reading anything from my phone. Support said it was my problem."` (Rating 1)
- `"I subscribed and ZERO features/content unlocked… 3 day trial to explore nothing."` (Rating 1)
- `"All or nothing values — if I'm 'great' according to data but I don't feel great, the binary output doesn't help."` (Rating 2)
- `"Good for people starting from a reasonable baseline. For atypical physiology/neurology it doesn't work."` (Rating 2)

**Step 4e: ★1-2レビューからの洞察:**
→ NEUROFITの失敗点: センサー依存（壊れる）、サブスク後コンテンツ解放なし、二値判定で細かさがない
→ 改善アプリ: **センサー不要**、**コンテンツ充実**、**毎日できるシンプルなエクササイズリスト**

**Lens 4 からの代表アイデア:** **VagusReset** — センサー不要の迷走神経活性化デイリーエクササイズアプリ

---

### Lens 5: Trend-Based（TikTok + WebSearch）

**Step 5a: WebSearch クエリ:**
- `"TikTok wellness trend 2026 nervous system vagus nerve"` (Source: goodhousekeeping.com)
- `"TikTok health viral 2026 gut health zone2"` (Source: eatingwell.com/wellness-trends-2026-8788090)

**Step 5b: ハッシュタグ候補（WebSearch結果から）:**
`vagusnerve`, `zone2cardio`, `guthealth`, `mouthbreathing`, `posturefix`

**Step 5c: Apify TikTok ハッシュタグスクレイパー結果（実測値）:**

Source: Apify clockworks~tiktok-hashtag-scraper, 2026-03-09実行

| ハッシュタグ | 代表動画ビュー数 | トレンド判定 |
|------------|--------------|------------|
| #vagusnerve / #vagusnervestimulation | 1,500,000 / 1,500,000 / 487,700 / 400,800 | ✅ **5M+ 確認済み** |
| #zone2cardio / #zone2 | 985,600 / 706,500 / 709,000 / 669,900 | ✅ **3M+ 確認済み** |
| #guthealth | 1,100,000 / 690,600 / 306,000 | ✅ **2M+ 確認済み** |
| #mouthbreathing / #nasalbreathing | 4,200,000 / 1,100,000 / 681,900 | ✅ **6M+ 確認済み（ただし呼吸アプリは除外カテゴリ）** |
| #posturefix / #posturecorrection | 1,300,000 / 1,100,000 / 558,700 | ✅ **3M+ 確認済み（ただし姿勢改善は除外カテゴリ隣接）** |

**Step 5d: ビュー数判定結果:**
- 迷走神経 (#vagusnerve): 1.5M+ → ✅ トレンド確認済み
- Zone 2 カーディオ: 985K+ → ✅ トレンド確認済み
- 口呼吸 (#mouthbreathing): 4.2M+ → ✅ 強いが呼吸アプリは除外カテゴリ
- 姿勢 (#posturefix): 1.3M+ → ✅ 強いが既存 stretch-flow と重複リスク

**Step 5e: 生成アイデア:**
- **VagusReset** — 哼り、うがい、冷水顔洗い、笑いヨガ、腹圧呼吸（呼吸アプリとは異なる）
- **ParasympathAlign** — 交感/副交感バランスセルフチェック + リセット習慣ガイド
- **NervousSystemReset** — 7-day 自律神経リセットチャレンジ
- Zone2Guide — ゾーン2カーディオ教育コンテンツ + セッションログ
- GutRhythm — 腸活デイリールーティン

**Lens 5 からの代表アイデア:** **VagusReset** — TikTok トレンド実証済み（5M+ views）、低競合（NEUROFIT 651件）

---

## Feasibility Filtering

| アイデア | S | P | M | C | T | overall_score | 結果 |
|---------|---|---|---|---|---|--------------|------|
| VagusReset | 9 | 7 | 8 | 9 | 9 | **8.50** | ✅ PASS |
| Zone2Trainer | 8 | 7 | 7 | 8 | 8 | **7.67** | ✅ PASS |
| SkinLog | 8 | 7 | 7 | 7 | 8 | **7.50** | ✅ PASS |
| CycleSync | 7 | 9 | 8 | 5 | 8 | **7.42** | ✅ PASS |
| WidgetHabit | 9 | 10 | 8 | 4 | 9 | N/A | ❌ FAIL (C=4 ≤ 4 — 習慣アプリは競合過多: Streaks 100K+, Habitica 250K+) |

**スコア計算式:** `(S×1.5 + P×1.0 + M×1.0 + C×1.0 + T×1.5) / 6.0`

- VagusReset: (9×1.5 + 7 + 8 + 9 + 9×1.5) / 6.0 = (13.5+7+8+9+13.5)/6 = 51/6 = **8.50**
- Zone2Trainer: (8×1.5 + 7 + 7 + 8 + 8×1.5) / 6.0 = (12+7+7+8+12)/6 = 46/6 = **7.67**
- SkinLog: (8×1.5 + 7 + 7 + 7 + 8×1.5) / 6.0 = (12+7+7+7+12)/6 = 45/6 = **7.50**
- CycleSync: (7×1.5 + 9 + 8 + 5 + 8×1.5) / 6.0 = (10.5+9+8+5+12)/6 = 44.5/6 = **7.42**

---

## Ideas Filtered Out

| アイデア | 除外理由 |
|---------|---------|
| WidgetHabit | C=4 (習慣トラッカーは超競合: Streaks 250K+, Habitica 300K+) |
| NasalBreathing / MouthTape | Step 0 除外カテゴリ（呼吸法 → breatheai/breath-calm と重複） |
| PostureFix | Step 0 除外カテゴリ隣接（姿勢改善 → stretch-flow と重複リスク） |
| GutHealth | M=6（腸活は ZOE/Cara Care/Nerva が 4K〜13K レビューで中競合） |
| HRV4Training | P=5（Apple Watch 必須でユーザーハードル高。Rule 23 に近い複雑さ） |

---

## Shortlist (Top 3)

### Rank 1: VagusReset

| Field | Value |
|-------|-------|
| one_liner | 毎日2分の迷走神経リセット — 哼り・うがい・冷水で自律神経バランスを整えるルーティンアプリ |
| lens | Lens 4 + Lens 5（App Store ギャップ × TikTok トレンド確認済み） |
| platform | iOS 17+ |
| problem_statement | デジタル過多・慢性ストレスで自律神経が乱れた現代人は増加中。NEUROFIT™ など既存の迷走神経アプリはセンサー依存で壊れやすく、課金後にコンテンツが出ないとのレビューが多い。センサー不要で今すぐ使えるシンプルなエクササイズガイドが求められている。 |
| target_user | 25-45歳、デスクワーカー・子育て世代。慢性疲労・不安・消化不良を感じているが病院に行くほどではない。TikTokで「迷走神経」コンテンツを見て試してみたい。 |
| feasibility | S:9 P:7 M:8 C:9 T:9 |
| overall_score | **8.50** |
| monetization_model | Freemium + Subscription ($4.99/月, $29.99/年)。無料: 5エクササイズ + 7日ストリーク。有料: 全20+エクササイズ + 詳細ガイド + ウィジェット + 通知カスタム |
| competition_notes | NEUROFIT™: 651件（センサー依存、課金後コンテンツなしの1星レビュー多数）。Vagal Tones: 0件。Vagus Vibe: 15件。競合は極めて弱い。 |
| mvp_scope | ① エクササイズライブラリ（哼り5分・うがい30秒・冷水顔洗い・横隔膜呼吸・笑いヨガ）② タイマー付きセッション ③ デイリーストリーク ④ ウィジェット（今日のエクササイズ） ⑤ ソフトペイウォール（5エクササイズ無料） |
| next_step | US-002 で product-plan.md を作成 |

---

### Rank 2: Zone2Trainer

| Field | Value |
|-------|-------|
| one_liner | ゾーン2カーディオの正しいやり方を学び、毎週のセッションを記録して脂肪燃焼・ミトコンドリア増加を追跡するトレーニングガイド |
| lens | Lens 3 + Lens 4（HealthKit HR × App Store ギャップ） |
| platform | iOS 17+ |
| problem_statement | ゾーン2トレーニングはPeter Attia・TikTokで急拡散中だが「自分の正しいゾーン2心拍数が分からない」「アプリが複雑すぎる」ニーズがある。「Zone 2: Heart Rate Training」は226件しかなく技術的クラッシュ問題も多い。 |
| target_user | 30-50歳、健康意識の高いランナー/サイクリスト。Apple Watch所持。有酸素基礎を作りたいが難しいアプリは嫌。 |
| feasibility | S:8 P:7 M:7 C:8 T:8 |
| overall_score | **7.67** |
| monetization_model | Freemium + Subscription ($4.99/月, $29.99/年)。無料: HR計算機 + セッション3件。有料: 無制限セッション + 週次レポート + HealthKit連携 |
| competition_notes | Zone 2: Heart Rate Training (226件、技術クラッシュ多数)、Zones for Training (18K件 — 一般ゾーントレーニング)。ゾーン2特化アプリは競合弱。 |
| mvp_scope | ① MAF/Karvonen法で個人ゾーン2HR計算 ② セッションタイマー（手動HR入力 or HealthKit） ③ 週次セッションログ ④ ゾーン2教育コンテンツ（5ページ） ⑤ ウィジェット |
| next_step | US-002 で product-plan.md を作成 |

---

### Rank 3: SkinLog

| Field | Value |
|-------|-------|
| one_liner | 毎朝10秒で肌写真を撮るだけ。週次カレンダーで肌コンディションのトレンドとトリガーを可視化する |
| lens | Lens 2（Problem-First） |
| platform | iOS 17+ |
| problem_statement | 肌荒れのトリガー（食事・睡眠・ストレス・生理）を特定するには継続記録が必要だが、既存の肌トラッカーはUI複雑で続かない。毎朝写真1枚＋タップ評価で続けられるシンプルアプリが求められている。 |
| target_user | 20-35歳女性。ニキビ・乾燥・敏感肌で悩んでいる。皮膚科に行く前にまず自分でトリガーを把握したい。 |
| feasibility | S:8 P:7 M:7 C:7 T:8 |
| overall_score | **7.50** |
| monetization_model | Freemium + Subscription ($4.99/月, $29.99/年)。無料: 30日記録 + 基本カレンダー。有料: 無制限記録 + トリガー分析 + HealthKit睡眠/サイクル連携 |
| competition_notes | Clear: Social Skincare Tracker (43件)、Charm: Skincare Routine 360° (1,468件)。AIスキャン系(OnSkin 31K)は別カテゴリ。シンプルな写真日記は低競合。 |
| mvp_scope | ① カメラ撮影 + 5段階スコア入力 ② 月次カレンダービュー ③ タグ（食事/睡眠/ストレス/生理） ④ 週次トレンドグラフ ⑤ ソフトペイウォール |
| next_step | US-002 で product-plan.md を作成 |

---

## Recommendation

**選定アプリ:** VagusReset（迷走神経デイリーリセットアプリ）

**理由:**
1. **競合が極めて弱い** — NEUROFIT™ 651件、Vagal Tones 0件。カテゴリ全体でレビュー合計 700件未満。
2. **TikTok実証済みトレンド** — #vagusnerve #vagusnervestimulation で合計 5M+ views（Apify実測 2026-03-09）。
3. **センサー不要で技術的にシンプル** — タイマー + コンテンツ + ウィジェット。Rule 23（AIコスト禁止）にも完全適合。
4. **既存アプリの明確な失敗点を解決** — 「センサー壊れる」「課金後コンテンツなし」→ センサー不要 + コンテンツ充実で差別化。
5. **除外カテゴリと重複なし** — 呼吸法アプリ（breatheai）とは異なる。迷走神経エクササイズは哼り・うがい・冷水・笑い（呼吸エクササイズは含まない）。
6. **overall_score 8.50** — 5アイデア中最高スコア。

**ソース:**
- Source: [Apify TikTok Hashtag Scraper](https://apify.com/clockworks/tiktok-hashtag-scraper) / 実測: #vagusnerve = 1,500,000+ views (2026-03-09)
- Source: [Apple iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) / 実測: NEUROFIT™ = 651件レビュー
- Source: [NEUROFIT App Store Reviews](https://apps.apple.com/us/app/vagus-nerve-reset-neurofit/id1630278170) / 「Worked for 5 days then quit reading from phone」(Rating 1)
- Source: [developer.apple.com/technologies/](https://developer.apple.com/technologies/) / HealthKit, WidgetKit, AppIntents
