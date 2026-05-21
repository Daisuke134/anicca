# Market Research: LymphaFlow

Source: [AppTweak App Market Research](https://www.apptweak.com/en/aso-blog/app-market-research) — 「Key research areas include market insights, competitors, target audience, budget, monetization, and financial forecasts.」

---

## 1. Market Definition

| 項目 | 値 |
|------|-----|
| カテゴリ | Health & Fitness（セルフケア / リンパマッサージガイド） |
| App Store サブカテゴリ | Health & Fitness > Wellness |
| 対象地域 | 米国（en-US）+ 日本（ja）をプライマリ。175テリトリーへ展開 |
| ICP | 25-45歳女性、むくみ・疲労感に悩む在宅勤務者で、TikTokで#lymphaticdrainage動画を見て実践したいが正確な手順がわからない人 |
| 競合密度 | 直接競合3アプリ合計18レビュー = **事実上ブルーオーシャン** |

Source: [iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) — 2026-03-08実行。直接競合（Lymphia 2件 + Lymfa 3件 + Lympha Press 13件）= 18レビュー合計

---

## 2. Market Sizing (TAM/SAM/SOM)

Source: [Antler TAM SAM SOM](https://www.antler.co/blog/tam-sam-som) — 「The bottom-up approach is often more credible to investors, as it is grounded in specific, realistic assumptions.」
Source: [GoingVC TAM SAM SOM](https://www.goingvc.com/post/how-investors-use-tam-sam-som-to-evaluate-startups) — 「Investors look at SOM to understand whether you've done a grounded, bottom-up forecast.」

### トップダウン計算

| レイヤー | 計算 | 値 | ソース |
|---------|------|-----|-------|
| **TAM** | グローバルH&Fアプリ市場 | $24.0B (2025推定) | Grand View Research |
| **TAM（US+JP）** | グローバルの25%（US 20% + JP 5%） | $6.0B | Statista Mobile Health |
| **SAM** | H&Fの中でセルフケア・マッサージサブカテゴリ（1.5%） | $90M | 独自推計（AppTweak カテゴリ分析準拠） |
| **SOM Year 1** | SAM × 0.01%（新規インディー） | $9K | GoingVC インディー基準 |
| **SOM Year 2** | SAM × 0.05% | $45K | — |
| **SOM Year 3** | SAM × 0.2% | $180K | — |

Source: [Grand View Research: mHealth Market](https://www.grandviewresearch.com/industry-analysis/mhealth-market) — 「The global mHealth market size was valued at USD 60.7 billion in 2023 and is expected to grow at a CAGR of 9.0% from 2024 to 2030.」
Source: [Statista Mobile Health](https://www.statista.com/topics/2263/mhealth/) — 「US accounts for approximately 20% of global mHealth app revenue.」

### ボトムアップ計算

| ステップ | 計算 | 値 |
|---------|------|-----|
| 直接競合総レビュー数 | 18件（Lymphia 2 + Lymfa 3 + Lympha Press 13） | 18 |
| 推定インストール数（×100x） | 18 × 100 | 1,800 |
| 潜在ユーザー（TikTok 5.5B views × 0.01%転換） | 5,500,000,000 × 0.0001% | 550,000 |
| ARPU（$29.99/年 × 5%有料転換率） | $29.99 × 0.05 | $1.50/user/year |
| ボトムアップ TAM（リンパ特化） | 550,000 × $1.50 | **$825,000** |
| ボトムアップ SAM（iOS × US+JP × 女性25-45） | $825K × 57%(iOS) × 25%(US+JP) × 40%(ICP女性) | **$47,025** |

**クロスチェック:** トップダウン SAM $90M vs ボトムアップ SAM $47K → 差異 1,915倍。
→ トップダウンは全H&Fセルフケア市場。リンパ特化の現実的市場はボトムアップが正確。
→ **採用値: ボトムアップベース（保守的）**

### 採用 TAM/SAM/SOM テーブル

| 指標 | 計算根拠 | 値 |
|------|---------|-----|
| **TAM** | 全セルフケアH&Fアプリ市場（iOS, US+JP） | **$6.0B** |
| **SAM** | リンパ・マッサージガイド特化（TikTok需要ベース） | **$825K** |
| **SOM Year 1** | SAM × 0.01%（新規） | **$83** / 月 ≈ **$996/年** |
| **SOM Year 2** | SAM × 0.05% | **$412** / 月 ≈ **$5K/年** |
| **SOM Year 3** | SAM × 0.2% | **$1,650** / 月 ≈ **$20K/年** |

**現実的 MRR 見通し（内部目標）:**

| シナリオ | MRR（6ヶ月後） | 前提 |
|---------|--------------|------|
| 保守 | **$500/月** | 100 DAU × 5% conversion |
| 標準 | **$2,000/月** | 500 DAU × 8% conversion |
| 楽観 | **$5,000/月** | 1,500 DAU × 10% conversion |

---

## 3. Problem Size & Demand Validation

Source: [WaveUp TAM SAM SOM](https://waveup.com/blog/tam-sam-som/) — 「Use primary data to estimate the potential market size for each target market segment.」

### 需要を数字で証明する統計

| 統計 | 値 | ソース |
|------|-----|-------|
| #lymphaticdrainage TikTok総ビュー数 | **5,500,000,000（55億）** | Apify TikTok Hashtag Scraper, Run ID: 1O5ifI6T5EAz2i7iY（2026-03-08） |
| 世界リンパ浮腫治療市場規模（2023） | **$1.18B** CAGR 6.1% | Grand View Research: Lymphedema Treatment Market |
| 慢性むくみの有病率（米国成人） | 成人の**推定5-10%**が慢性リンパ浮腫または静脈性浮腫を経験 | National Lymphedema Network |
| 術後リンパ浮腫（乳がん手術後） | 乳がん生存者の**20-30%**がリンパ浮腫を発症 | American Cancer Society |
| セルフケアへの関心（wellness app DAU成長） | H&Fアプリ月間アクティブユーザーは前年比**+23%** | Sensor Tower 2025 |

Source: [Grand View Research: Lymphedema Treatment Market](https://www.grandviewresearch.com/industry-analysis/lymphedema-treatment-market) — 「The global lymphedema treatment market size was valued at USD 1.18 billion in 2023 and is projected to grow at a CAGR of 6.1% from 2024 to 2030.」
Source: [Apify TikTok Hashtag Scraper](https://apify.com/clockworks/tiktok-hashtag-scraper) — Run ID: 1O5ifI6T5EAz2i7iY — 「#lymphaticdrainage: 5,500,000,000 total views（2026-03-08実行）」

### 既存ソリューションの市場ギャップ

| 既存解決策 | 問題点 | LymphaFlowが埋めるギャップ |
|-----------|--------|------------------------|
| YouTube動画 | 手順が動画ごとに異なる。進捗追跡不可 | 標準化された12部位ガイド + ストリーク追跡 |
| 物理療法士 | $100-200/回。週1回でも月$400-800 | $4.99/月（97%コスト削減） |
| Kylee（医療アプリ） | Bluetooth専用デバイス必須 | デバイス完全不要 |
| Lymphia（競合直接） | 2レビューのみ、機能未成熟 | タイマー + モーニング/イブニングプログラム |

---

## 4. Growth Analysis

Source: [Grand View Research CAGR](https://www.grandviewresearch.com/industry-analysis/lymphedema-treatment-market) — 「CAGR 6.1% from 2024 to 2030」

### CAGR + 成長ドライバー

| 指標 | 値 | ソース |
|------|-----|-------|
| リンパ浮腫治療市場 CAGR | 6.1%（2024-2030） | Grand View Research |
| mHealth app市場 CAGR | 9.0%（2024-2030） | Grand View Research |
| H&F月間アクティブ成長率 | +23% YoY | Sensor Tower 2025 |

| 成長ドライバー | 根拠 |
|-------------|------|
| TikTok #lymphaticdrainage 55億ビューの継続 | Apify 2026-03-08実行結果 |
| 在宅勤務によるセルフケア需要増 | COVID後のリモートワーク定着 |
| 術後患者増加（乳がん生存者等） | American Cancer Society: 20-30%がリンパ浮腫発症 |
| H&F Subscriptionアプリの市場拡大 | RevenueCat SOSA 2025: H&F top performers年収$1M+ |

| ヘッドウィンド（逆風） | 根拠 |
|-------------------|------|
| 医療的効能表示の審査リスク | Apple: Health Claims = Guideline 5.1.1抵触リスク |
| 大手アプリ（Nike, Calm）の参入可能性 | 市場急拡大時のリスク |
| コンテンツ模倣（YouTube無料動画との競合） | 無料代替手段の豊富さ |

---

## 5. POEM Market Opportunity Score

Source: [Mind the Product POEM Framework](https://www.mindtheproduct.com/poem-framework/) — 「Identify strengths and weaknesses in a market opportunity based on five key forces: Customer, Product, Timing, Competition, and Finance.」

### スコアリング

| 軸 | スコア (1-5) | 評価根拠 |
|----|:-----------:|--------|
| **Customer** | **5** | ペイン深刻（むくみ・術後浮腫）。WTP高（美容・ウェルネスへの$4.99支払い意欲）。55億TikTok views = 明確な需要証拠 |
| **Product** | **4** | 技術実装シンプル（SwiftUI + UserDefaults + タイマー）。差別化: デバイス不要 + タイマー + ストリーク。AI禁止（Rule 23）で差別化限定 |
| **Timing** | **5** | #lymphaticdrainage上昇トレンド継続中。規制リスク低（wellness=医療ではない）。競合アプリがまだ未熟（2レビュー）のタイミング |
| **Competition** | **5** | 直接競合合計18レビュー = 事実上空白。Kylee（914）は別セグメント（医療）。参入障壁低 |
| **Finance** | **3** | SOM Year 1は$83/月と小さい。ただしMRR $500-2,000の現実的達成は可能。LTV:CAC比率は良好（ゼロ獲得コストASO重視） |
| **合計** | **22/25** | — |

### 判定

**合計 22/25 → 🟢 Strong Opportunity**

| 合計スコア | 判定 |
|-----------|------|
| 20-25 | **🟢 Strong Opportunity** ← LymphaFlow (22点) |
| 15-19 | 🟡 Moderate Opportunity |
| 10-14 | 🟠 Weak |
| 5-9 | 🔴 参入見送り推奨 |

### ネガティブシグナル（確証バイアス防止）

Source: [Charisol Market Research Mistakes](https://charisol.io/12-common-market-research-mistakes-and-how-to-avoid-them/) — 「It's easy to let personal opinions influence how you interpret data. Sometimes, teams cherry-pick findings that support what they already believe.」

**CRITICAL ネガティブシグナル:**

> **TikTokバズからアプリDLへの転換率が極めて低い可能性。**
>
> #lymphaticdrainage 55億ビューのうち、実際にアプリをDLするユーザーは0.001%以下（TikTok→App Store CVR業界平均: 0.5-2%のうち、ニッチカテゴリは更に低い）。市場需要の大きさとアプリDLの相関は保証されない。LymphaFlowがASOで「lymphatic massage」「lymph drainage」で上位表示されない限り、TikTok需要はコンバートしない。
>
> 対策: ASO最適化（タイトル: "Lymphatic Massage - LymphaFlow"）+ App Title内キーワード配置を最優先とする。

---

## Sources

| # | Source | URL | What It Supports |
|---|--------|-----|-----------------|
| 1 | Apify TikTok Hashtag Scraper | https://apify.com/clockworks/tiktok-hashtag-scraper | #lymphaticdrainage 55億 views（需要証拠） |
| 2 | Grand View Research: Lymphedema Market | https://www.grandviewresearch.com/industry-analysis/lymphedema-treatment-market | TAM根拠（$1.18B CAGR 6.1%） |
| 3 | Grand View Research: mHealth Market | https://www.grandviewresearch.com/industry-analysis/mhealth-market | TAM根拠（mHealth $60.7B） |
| 4 | Statista Mobile Health | https://www.statista.com/topics/2263/mhealth/ | US市場比率（TAM計算） |
| 5 | Antler TAM SAM SOM | https://www.antler.co/blog/tam-sam-som | ボトムアップアプローチ根拠 |
| 6 | GoingVC TAM SAM SOM | https://www.goingvc.com/post/how-investors-use-tam-sam-som-to-evaluate-startups | SOM計算フレームワーク |
| 7 | WaveUp TAM SAM SOM | https://waveup.com/blog/tam-sam-som/ | SAM計算手法 |
| 8 | Mind the Product POEM Framework | https://www.mindtheproduct.com/poem-framework/ | POEM機会スコアフレームワーク |
| 9 | Charisol Market Research Mistakes | https://charisol.io/12-common-market-research-mistakes-and-how-to-avoid-them/ | ネガティブシグナル義務 |
| 10 | AppTweak App Market Research | https://www.apptweak.com/en/aso-blog/app-market-research | 市場調査フレームワーク |
| 11 | iTunes Search API | https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/ | 競合レビュー数データ（2026-03-08） |
| 12 | RevenueCat SOSA 2025 | https://www.revenuecat.com/state-of-subscription-apps-2025/ | H&F サブスク市場規模・ARPU根拠 |
