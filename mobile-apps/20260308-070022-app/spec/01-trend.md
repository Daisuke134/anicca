# Trend Research: LymphaFlow

## Developer Profile

| 項目 | 値 |
|------|-----|
| Platform | iOS 17+ (Swift/SwiftUI) |
| Scope | 4-8 weeks (solo dev) |
| Monetization | Subscription ($4.99/月, $29.99/年) |
| AI/外部API | 禁止（Rule 21）— 完全自己完結。静的キュレーションコンテンツのみ |

---

## Step 0: 既存アプリ除外カテゴリ（動的生成）

`ls mobile-apps/` 実行結果（2026-03-08）:

| 既存アプリ | 除外カテゴリ |
|-----------|-------------|
| breath-calm, breatheai | 呼吸法・瞑想 |
| sleep-ritual | 睡眠最適化 |
| dailydhamma | マインドフルネス・仏教 |
| calmcortisol | ストレス管理 |
| rork-thankful-gratitude-app (+ 20260303-034713: MomentLog) | 感謝日記・フォトジャーナル |
| stretch-flow, desk-stretch | デスクストレッチ・姿勢改善（一般） |
| 20260307-002214 (EyeBreakIsland), 20260307-202456 (EyeRest) | 目のケア・20-20-20ルール |
| 20260307-223953 (FrostDip) | コールドプランジ・アイスバス |
| 20260301 (Daily Affirmation Widget) | アファメーション・自己啓発 |
| 20260303-070158 (MindSnap) | AIデイリーチェックイン |
| 20260304-105016 (Chi Daily) | TCM・中医学 |

---

## Lenses Applied

### Lens 1: Skills & Interests（Apple フレームワーク）

**問い:** Apple の独自フレームワークを活かして何が作れるか？

| # | アイデア | フレームワーク | 問題解決 |
|---|---------|--------------|---------|
| 1 | **LymphaticFlow** — セルフリンパマッサージガイド | HealthKit（セッション記録）+ Core Animation（ガイドアニメーション）+ UserNotifications | リンパ浮腫・免疫サポート。日常的なセルフケアの手順を忘れる問題 |
| 2 | **WristGuard** — RSI予防手首エクササイズ | HealthKit + CoreMotion（手首動作検出）+ BackgroundTasks | デスクワーカーの手首痛・腱鞘炎予防 |
| 3 | **TinnitusSoothe** — 耳鳴り音響療法 | AVFoundation（音響合成）+ HealthKit（症状記録）| 耳鳴りの苦痛を音マスキングで軽減 |
| 4 | **HRVCoach** — 心拍変動リカバリーガイド | HealthKit（HRVデータ）+ Charts（トレンド可視化）| 疲労・過剰トレーニングの予防 |
| 5 | **AcuPoint** — ツボ圧迫療法ガイド | Core Animation（ボディダイアグラム）+ UserNotifications（タイマー）| 頭痛・疲れ目のセルフ対処 |

---

### Lens 2: Problem-First（日常の不便と苦しみ）

**問い:** 身体的・精神的な苦しみで「まだ良い解決策がない」ものは？

検索クエリ:
- `"iOS app idea 2026 underserved niche health wellness"` (Source: DuckDuckGo)
- `"reddit what app do you wish existed 2026 health"` (Source: DuckDuckGo)

| # | アイデア | 問題の源泉 | 解決策 |
|---|---------|-----------|-------|
| 1 | **NeckRelief** — 首・肩こり特化エクササイズ | デスクワーカーの前傾姿勢による慢性首痛。NeckFit: 7 reviews、Ctrl+Neck: 4 reviews = ほぼ空白 | 段階的な頸椎デコンプレッション + 毎日のリマインダー |
| 2 | **LymphDrain** — リンパ浮腫セルフマッサージ（Lens 2版） | むくみ・免疫低下の悩み。専用アプリが皆無 | 部位別ガイド付きセルフマッサージ手順 |
| 3 | **VertiFix** — 良性頭位めまい（BPPV）エプレー法ガイド | 突然のめまいで医師を呼べない状況でセルフ対処できない | エプレー法・BBQ回転法のステップバイステップガイド |
| 4 | **TriggerPoint** — 筋膜トリガーポイント自己治療 | 肩甲骨・腰・ふくらはぎの筋肉の凝りをほぐせない | 部位別トリガーポイントマップ + ローラー使用ガイド |
| 5 | **SomaticRelease** — ソマティックエクササイズ（身体緊張解放） | 慢性的な身体緊張・トラウマ保持。専用アプリが希少 | TRE（外傷解放エクササイズ）+ ボディスキャン動作ガイド |

---

### Lens 3: Technology-First（最新フレームワーク活用）

**問い:** Apple が最近リリースしたフレームワークで、インディーアプリが少ないものは？

検索クエリ:
- `"HealthKit sleep CoreMotion indie app opportunity 2026"` (Source: DuckDuckGo)
- `"iOS 17 18 new framework underused indie developer 2026"` (Source: DuckDuckGo)

| # | アイデア | フレームワーク機会 | インディー潜在力 |
|---|---------|-----------------|---------------|
| 1 | **CircadianTracker** — 日光曝露・概日リズム管理 | HealthKit TimeInDaylight（iOS 17）。専用インディーアプリ少 | 日光不足によるうつ・睡眠障害対策 ※sleep-ritualとの重複リスクあり |
| 2 | **LymphGuide** — リンパ経路の3Dビジュアルガイド | SceneKit / RealityKit（ライトウェイト3D体図）| 身体解剖の可視化でセルフケア効果を向上 |
| 3 | **FaceYoga** — 顔筋エクササイズ（ARKit顔追跡） | ARKit（顔ランドマーク追跡）—AI不要の静的マッピング | シワ・フェイスライン改善。AI禁止のため純粋顔追跡のみ |
| 4 | **NoiseSensible** — 環境騒音・聴覚過敏トラッカー | CoreAudio + SoundAnalysis | HSP・ASD向けの騒音エクスポージャー管理 |
| 5 | **WristRSI** — 手首角度・タイピング負荷トラッカー | CoreMotion（傾きセンサー）+ HealthKit | RSI予防のためのリアルタイム手首位置フィードバック |

---

### Lens 4: Market Gap（App Storeデータ）

**問い:** App Storeで競合が弱いカテゴリはどこか？

iTunes Search API 実行結果（2026-03-08）:

| カテゴリ | 上位アプリ | レビュー数 | 競合密度 |
|---------|-----------|----------|---------|
| lymphatic massage | Lymphia: Lymphatic Exercises | **2 reviews** | **超低 ✅** |
| neck pain exercises | NeckFit, Ctrl+Neck | **4-7 reviews** | **超低 ✅** |
| vagus nerve | NEUROFIT™ | 651 reviews | 低 ✅ |
| acupressure points | Tsubook | 45 reviews | 低 ✅ |
| somatic exercises | Somatic Exercises app | 297 reviews | 低 ✅ |
| posture corrector | Bend: Stretching | 162,339 reviews | 高 ❌ |
| hydration tracker | Waterllama | 148,182 reviews | 高 ❌ |
| intermittent fasting | Zero | 445,167 reviews | 高 ❌ |

**★1-2 レビュー分析（NEUROFIT™, id=1630278170）:**

> "The app worked great for 5 days then it quit reading anything from my phone... Support only told me to follow the steps again" ★1

> "I don't like the all or nothing values... After doing one exercise the app extols that I have shifted from one extreme to another - which was entirely inaccurate" ★2

> "Yup, I subscribed to the app and ZERO features/content unlocked... now I have a 3 day trial to basically nothing" ★1

**★1-2 レビュー分析（Kylee Lymphedema, id=1621768150）:**

> "The Bluetooth connection never worked" ★2（ハードウェア依存の問題）

> "The app refuses to identify correct body part, even though I entered correct information" ★1（ユーザビリティ問題）

**洞察:** 既存のリンパ系アプリはBluetoothデバイス依存または医療用途特化。一般消費者向けセルフリンパマッサージガイドは完全空白。

| # | アイデア（Lens 4） | 根拠 |
|---|-----------------|------|
| 1 | **LymphaticDrain** — 一般消費者向けセルフリンパマッサージ | Lymphia: 2 reviews。デバイス不要の純ガイドアプリが皆無 |
| 2 | **NeckCervical** — 頸椎特化デコンプレッションガイド | NeckFit: 7 reviews、専用アプリ皆無 |
| 3 | **VagusSimple** — シンプル迷走神経活性化ルーティン | NEUROFITのユーザーが「シンプルさ」を求めるレビュー多数 |
| 4 | **AcupressureMap** — 症状別ツボマップ | Tsubook: 45 reviews、専門的すぎる |
| 5 | **WristEase** — デスクワーカー手首リリースルーティン | 専用アプリ皆無。Airrosti等は一般PT向け |

---

### Lens 5: Trend-Based（TikTok + WebSearch）

**問い:** TikTokで実際にバズっているヘルス系トピックは？

WebSearch クエリ:
- `"TikTok wellness trend 2026"` → Source: DuckDuckGo
- `"trending health topics social media 2026"` → Source: DuckDuckGo

**Apify TikTok Hashtag Scraper 実行結果（2026-03-08）:**

Run ID: 1O5ifI6T5EAz2i7iY (hashtags: somaticexercises, nervoussystemreset, lymphaticdrainage)
Run ID: ngnvmQLOYlRMBkyJY (hashtags: vagusnerve, jawexercises, wristpain)

| ハッシュタグ | 総ビュー数 | 判定 |
|------------|---------|------|
| #lymphaticdrainage | **5,500,000,000** (55億) | ✅ トレンド確認済み（最大級）|
| #vagusnerve | **525,700,000** (5.25億) | ✅ トレンド確認済み |
| #nervoussystemreset | **235,100,000** (2.35億) | ✅ トレンド確認済み |
| #wristpain | **1,000,000,000** (10億) | ✅ トレンド確認済み |
| #jawexercises | **21,200,000** (2120万) | ✅ トレンド確認済み |
| #somaticexercises | **5,000,000** (500万) | ⚠️ 中程度 |

Source: Apify clockworks/tiktok-hashtag-scraper — 実定量データ

**TikTokトレンドからのアイデア5個:**

| # | アイデア | ハッシュタグ根拠 | ビュー数 |
|---|---------|---------------|---------|
| 1 | **LymphaFlow** — セルフリンパドレナージュルーティンコーチ | #lymphaticdrainage | 5.5B |
| 2 | **WristFlow** — 手首痛軽減エクササイズ & 予防タイマー | #wristpain | 1.0B |
| 3 | **VagusActivate** — 迷走神経活性化シンプルルーティン | #vagusnerve | 525M ※呼吸法除外カテゴリに隣接 |
| 4 | **JawSculpt** — 顎筋・エラのエクササイズタイマー | #jawexercises | 21.2M |
| 5 | **SomaticFlow** — ソマティック身体解放エクササイズ | #somaticexercises | 5.0M |

---

## Feasibility Filtering

各アイデアを S/P/M/C/T（各1-10）でスコアリング。いずれか1つでも4以下なら除外。

| アイデア | S | P | M | C | T | 結果 |
|---------|---|---|---|---|---|------|
| LymphaticFlow / LymphaFlow | 9 | 7 | 8 | 10 | 9 | **PASS** |
| NeckRelief / NeckCervical | 9 | 6 | 8 | 10 | 9 | **PASS** |
| WristGuard / WristEase | 9 | 7 | 7 | 8 | 9 | **PASS** |
| TinnitusSoothe | 8 | 8 | 7 | 7 | 8 | **PASS** |
| AcuPoint / AcupressureMap | 8 | 6 | 7 | 9 | 8 | **PASS** |
| JawSculpt | 8 | 6 | 7 | 6 | 7 | **PASS** |
| SomaticFlow | 7 | 6 | 7 | 8 | 7 | **PASS** |
| VertiFix | 7 | 6 | 7 | 8 | 7 | **PASS** |
| VagusActivate | 8 | 7 | 7 | 7 | 8 | **FAIL** — 呼吸法・ストレス管理除外カテゴリに隣接（Step 0） |
| CircadianTracker | 7 | 8 | 6 | 7 | 7 | **FAIL** — sleep-ritualとの重複（Step 0） |
| SomaticRelease | 7 | 6 | 6 | 8 | 7 | **FAIL** — breathwork/meditation除外カテゴリに隣接（Step 0）|
| FaceYoga | 7 | 6 | 7 | 7 | 6 | **FAIL** — Mimika: 1,208 reviews、ARKit不使用だと差別化困難 |
| NoiseSensible | 6 | 7 | 6 | 8 | 7 | **FAIL** — 市場が小さすぎる（HSP/ASD特化）|
| HRVCoach | 7 | 9 | 6 | 7 | 7 | **FAIL** — M=6（HRVはApple Watch必須→ユーザー制限大） |
| TriggerPoint | 8 | 5 | 6 | 7 | 7 | **FAIL** — P=5（フォームローラー等の物理器具前提） |

---

## Shortlist (Top 5)

計算式: `overall_score = (S×1.5 + P×1.0 + M×1.0 + C×1.0 + T×1.5) / 6.0`

### Rank 1: LymphaFlow

| Field | Value |
|-------|-------|
| one_liner | TikTok55億回再生の#lymphaticdrainage トレンドに特化した、デバイス不要のセルフリンパマッサージガイドアプリ |
| lens | Lens 1 + Lens 4 + Lens 5（複数レンズで最高スコア） |
| platform | iOS 17+ |
| problem_statement | リンパドレナージュはむくみ・免疫改善・術後リカバリーに有効として急速に普及しているが、一般消費者向けのデジタルガイドアプリが事実上存在しない（Lymphia: 2 reviews）。既存アプリはBluetoothデバイス依存か医療専門家向けで、普通の人が毎日実践できるセルフマッサージのガイドがない。TikTokで5.5B回再生されているにもかかわらず、「アプリで学べる」解決策が欠如。 |
| target_user | 25-45歳女性、むくみ・疲労感に悩む在宅勤務者・術後患者・美容意識の高い層。TikTokでリンパマッサージ動画を見て実践したいが、正確な手順を覚えられない。 |
| feasibility | S:9 P:7 M:8 C:10 T:9 |
| overall_score | **(9×1.5 + 7 + 8 + 10 + 9×1.5) / 6.0 = (13.5+7+8+10+13.5)/6 = 52/6 = 8.67** |
| monetization_model | Freemium + Subscription ($4.99/月, $29.99/年)。無料: 顔・首ルーティン3種。有料: 全身12部位 + 目的別プログラム（むくみ解消、免疫、術後）+ 進捗ログ |
| competition_notes | Lymphia: Lymphatic Exercises — 5 ★, 2 reviews（事実上空白）。Kylee Lymphedema Assistant — 914 reviews だがBluetoothデバイス専用。一般消費者向け純ガイドアプリは存在しない |
| mvp_scope | ①顔・首・鎖骨エリアのリンパドレナージュルーティン（静的アニメーション）②部位別タイマー付きステップガイド ③毎日のセッション記録 + ストリーク ④Morning/Evening の2プログラム ⑤PaywallView（全身12部位解放） |
| next_step | US-002 で product-plan.md を作成 |

---

### Rank 2: NeckRelief

| Field | Value |
|-------|-------|
| one_liner | デスクワーカーの慢性首痛・ストレートネックに特化した頸椎デコンプレッションエクササイズアプリ |
| lens | Lens 2 + Lens 4 |
| platform | iOS 17+ |
| problem_statement | テレワーク普及でストレートネック・慢性首痛の患者数が急増しているにもかかわらず、首特化エクササイズアプリが存在しない（NeckFit: 7 reviews、Ctrl+Neck: 4 reviews）。stretch-flowは全般的なデスクストレッチだが、首の頸椎デコンプレッション・神経根除圧に特化したプログラムは空白。 |
| target_user | 30-45歳デスクワーカー、慢性的な首こり・頭痛持ち。整形外科でストレートネックと診断された人。 |
| feasibility | S:9 P:6 M:8 C:10 T:9 |
| overall_score | **(9×1.5 + 6 + 8 + 10 + 9×1.5) / 6.0 = (13.5+6+8+10+13.5)/6 = 51/6 = 8.50** |
| monetization_model | Freemium + Subscription ($4.99/月, $29.99/年)。無料: 3種類の基本ストレッチ。有料: 7段階プログレッシブプログラム + 姿勢チェックリマインダー |
| competition_notes | NeckFit: 7 reviews。Ctrl+Neck: 4 reviews。Wakeout（一般デスク向け）: 8,259 reviews だが首特化なし |
| mvp_scope | ①頸椎前弯改善エクササイズ5種 ②上下左右の可動域改善ルーティン ③毎日通知リマインダー ④2週間プログレッシブプログラム ⑤痛みレベル記録 |
| next_step | US-002 で product-plan.md を作成 |

---

### Rank 3: WristGuard

| Field | Value |
|-------|-------|
| one_liner | TikTok10億再生の#wristpainトレンドに応える、デスクワーカーのRSI（反復性ストレス損傷）予防エクササイズタイマーアプリ |
| lens | Lens 1 + Lens 3 + Lens 5 |
| platform | iOS 17+ |
| problem_statement | タイピング・スマホ操作による手首のRSI（腱鞘炎・手根管症候群）は急増しているが、専用予防アプリが存在しない。一般PTアプリ（Prehab: 1,622 reviews）はRSIに特化しておらず、手首特化はほぼ空白。 |
| target_user | 25-40歳エンジニア・クリエイター・デスクワーカー。長時間タイピングで手首痛を自覚している人。 |
| feasibility | S:9 P:7 M:7 C:8 T:9 |
| overall_score | **(9×1.5 + 7 + 7 + 8 + 9×1.5) / 6.0 = (13.5+7+7+8+13.5)/6 = 49/6 = 8.17** |
| monetization_model | Freemium + Subscription ($4.99/月, $29.99/年)。無料: 5分ウォームアップルーティン。有料: 部位別ルーティン + 作業休憩タイマー統合 |
| competition_notes | 専用アプリなし。Prehab: 1,622 reviews（一般物理療法）。Moova: 1,662 reviews（一般活動休憩） |
| mvp_scope | ①ウォームアップ + クールダウン手首ルーティン ②作業時間カウンター（X分おきにアラート） ③手首ストレッチ10種ガイド ④ROMセルフ評価 ⑤痛みログ |
| next_step | US-002 で product-plan.md を作成 |

---

### Rank 4: TinnitusSoothe

| Field | Value |
|-------|-------|
| one_liner | 耳鳴り（キーン音）を音響マスキングとリラクゼーションで和らげる、ハードウェア不要のセルフケアアプリ |
| lens | Lens 1 + Lens 3 |
| platform | iOS 17+ |
| problem_statement | 耳鳴りは成人の15%が経験する慢性症状だが、既存アプリは高価なBluetoothイヤホン（ReSound: 17,713 reviews、ハードウェア連動）か機能が限定的（Tinnitus Aid: 1,012 reviews）。純粋なマスキング音 + セルフTRT（Tinnitus Retraining Therapy）を提供するシンプルアプリの余地あり。 |
| target_user | 40-65歳、加齢性難聴または騒音暴露による耳鳴りに悩む人。補聴器不要の自力対処を求める層。 |
| feasibility | S:8 P:8 M:7 C:7 T:8 |
| overall_score | **(8×1.5 + 8 + 7 + 7 + 8×1.5) / 6.0 = (12+8+7+7+12)/6 = 46/6 = 7.67** |
| monetization_model | Freemium + Subscription ($4.99/月, $29.99/年)。無料: ホワイトノイズ3種。有料: 12種音響 + 周波数カスタマイズ + CBTベースのメモ機能 |
| competition_notes | ReSound Tinnitus Relief: 17,713 reviews（ハードウェア専用）。Oto: 831 reviews（CBT特化）。純音響マスキング特化アプリは中程度競合 |
| mvp_scope | ①ホワイトノイズ・自然音・ノッチ音 8種 ②就寝タイマー ③周波数マッチング（耳鳴り音に近い周波数を特定）④毎日の症状記録 ⑤TRTベースの段階的脱感作プログラム |
| next_step | US-002 で product-plan.md を作成 |

---

### Rank 5: AcuPoint

| Field | Value |
|-------|-------|
| one_liner | 頭痛・疲れ目・肩こりを即時解消するアクレスタライン（ツボ）圧迫ガイドアプリ |
| lens | Lens 1 + Lens 4 |
| platform | iOS 17+ |
| problem_statement | アクレスタライン（ツボ押し）は頭痛・肩こり・疲労への即時セルフケアとして高い需要があるが、Tsubook（45 reviews）、Visual Acupuncture 3D（143 reviews）など既存アプリは専門的すぎるか更新が古い。一般消費者が「今すぐ頭痛を楽にしたい」と検索したときに使える直感的アプリが空白。 |
| target_user | 25-50歳、職場での頭痛・疲れ目・肩こりをすぐに解消したい人。市販薬に頼りたくない自然療法志向の人。 |
| feasibility | S:8 P:6 M:7 C:9 T:8 |
| overall_score | **(8×1.5 + 6 + 7 + 9 + 8×1.5) / 6.0 = (12+6+7+9+12)/6 = 46/6 = 7.67** |
| monetization_model | Freemium + Subscription ($4.99/月, $29.99/年)。無料: 頭痛・疲れ目の緊急ポイント5点。有料: 全身50ポイント + 症状別プログラム + 効果記録 |
| competition_notes | Tsubook: 45 reviews。Visual Acupuncture 3D: 143 reviews（古い）。Muscle Trigger Points: 542 reviews（筋肉特化、違うカテゴリ）|
| mvp_scope | ①ボディマップ（頭/首/手/足）②ポイントタップ → 位置 + 圧迫方法アニメーション ③症状別クイックアクセス ④タイマー（30秒圧迫ガイド）⑤使用履歴 |
| next_step | US-002 で product-plan.md を作成 |

---

## Ideas Filtered Out

| アイデア | 除外理由 |
|---------|---------|
| VagusActivate | Step 0 除外カテゴリ隣接（breatheai, calmcortisol と同じ迷走神経/ストレス管理） |
| CircadianTracker | Step 0 除外カテゴリ隣接（sleep-ritualと概日リズム領域が重複） |
| SomaticRelease | Step 0 除外カテゴリ隣接（dailydhammaと瞑想/ボディスキャン重複） |
| FaceYoga | T=6: AI禁止によりARKit活用が限定的。差別化困難（Mimika: 1,208 reviews）|
| NoiseSensible | M=6: 市場が過小（HSP/ASD特化のニッチすぎる）|
| HRVCoach | M=6: Apple Watch必須でユーザー基盤が限定的 |
| TriggerPoint | P=5: フォームローラー等の物理器具前提で差別化困難 |

---

## Recommendation

**選定アプリ:** **LymphaFlow**（Rank 1, overall_score: 8.67）

**理由:**
1. **市場空白が最大** — Lymphia（唯一の直接競合）がわずか2 reviews。事実上ブルーオーシャン。
2. **TikTokトレンド最大** — #lymphaticdrainage 5.5B（55億）ビューはテスト対象6ハッシュタグ中最大（Source: Apify TikTok Hashtag Scraper, 2026-03-08実行）。
3. **実装シンプル** — AI/外部API不要。静的アニメーションガイド + タイマー + HealthKit記録のみ（Rule 21完全準拠）。
4. **明確な課金価値** — 全身12部位・目的別プログラムのアンロックが自然なペイウォール。
5. **除外カテゴリ非抵触** — 呼吸法・瞑想・睡眠・ストレス管理のいずれとも異なる身体的マッサージカテゴリ。

**ソース:**
- Apify TikTok Hashtag Scraper 実行結果（Run ID: 1O5ifI6T5EAz2i7iY, Dataset: gFAPlF5H90njDhnr5）
- iTunes Search API: `itunes.apple.com/search?term=lymphatic+massage+exercises` (2026-03-08)
- Kylee Lymphedema ★1-2レビュー: `itunes.apple.com/us/rss/customerreviews/id=1621768150`
- NEUROFIT ★1-2レビュー: `itunes.apple.com/us/rss/customerreviews/id=1630278170`
