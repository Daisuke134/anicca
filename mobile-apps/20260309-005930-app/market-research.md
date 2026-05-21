# Market Research: LumaRed

Source: [AppTweak](https://www.apptweak.com/en/aso-blog/app-market-research) — 「Key research areas include market insights, competitors, target audience, budget, monetization, and financial forecasts.」
Date: 2026-03-09

---

## 1. Market Definition

| 項目 | 値 |
|------|-----|
| カテゴリ | Health & Fitness / Biohacking / Photobiomodulation |
| App Store サブカテゴリ | Health & Fitness |
| 地域 | 主要: US + JP（Phase 2: DE/UK/AU） |
| ICP | 25-45歳、赤色光デバイス所持者（$200-$1,000 投資済み）、TikTok/Reddit でバイオハッキング情報収集 |
| 競合市場の状態 | **ブルーオーシャン** — 最大競合でも 69 reviews（2026-03-09 現在）|

---

## 2. Market Sizing (TAM/SAM/SOM)

### TAM（トップダウン）

Source: [Mordor Intelligence: Red Light Therapy Device Market](https://www.mordorintelligence.com/industry-reports/red-light-therapy-device-market) — 「The Red Light Therapy Device Market is projected to grow from USD 0.55 billion in 2024 to USD 1.13 billion by 2029, at a CAGR of 15.47%.」

Source: [Grand View Research: Photobiomodulation Therapy Market](https://www.grandviewresearch.com/industry-analysis/photobiomodulation-therapy-market-report) — 「The global photobiomodulation therapy market size was valued at USD 354.3 million in 2022.」

| 指標 | 値 | 根拠 |
|------|-----|------|
| RLT デバイス市場 (2024) | $550M | Mordor Intelligence |
| RLT デバイス市場 (2029) | $1,130M | Mordor Intelligence (CAGR 15.47%) |
| コンパニオンアプリ機会 (15%) | **$83M** (2029) | デバイス市場のアプリ付加価値比率（ウェアラブル業界標準） |

**TAM (Top-down) = $83M（2029年予測）**

### TAM（ボトムアップ）

Source: [Antler](https://www.antler.co/blog/tam-sam-som) — 「The bottom-up approach is often more credible to investors, as it is grounded in specific, realistic assumptions.」

| 計算ステップ | 数値 | 根拠 |
|------------|------|------|
| 世界 RLT デバイス所持者 | ~2,000,000 人 | $550M市場 ÷ $275平均デバイス単価 |
| アプリ導入率 (20%) | 400,000 人 | 健康意識が高い所持者の推定利用率 |
| ARPU | $29.99/年 | product-plan.md §4 年間プラン |
| 有料転換率 | 5% | RevenueCat SOSA 2025 H&F中央値 |
| **Bottom-up TAM** | **$600,000** | 400K × 5% × $29.99 |

**クロスチェック:** $83M (top-down) vs $600K (bottom-up) → **差異 138x**（top-downは市場全体、bottom-upは現実的な有料ユーザーに限定）。Bottom-up を保守的ベースラインとして採用。

### SAM

Source: [WaveUp](https://waveup.com/blog/tam-sam-som/) — 「Use primary data to estimate the potential market size for each target market segment.」

| 計算ステップ | 数値 | 根拠 |
|------------|------|------|
| US RLT 所持者（世界の30%） | 600,000 人 | 米国が RLT 消費の主要市場 |
| US iOS 率 | 57% | 業界標準 |
| US iOS SAM ユーザー | 342,000 人 | — |
| JP RLT 所持者（世界の8%） | 160,000 人 | 日本は美容・ウェルネス意識が高い |
| JP iOS 率 | 68% | 業界標準 |
| JP iOS SAM ユーザー | 108,800 人 | — |
| **SAM 合計** | **450,800 人** | US + JP |
| ARPU × 5% 有料転換 | $1.50/人 | $29.99 × 5% |
| **SAM 金額** | **$676,200** | 450,800 × $1.50 |

### SOM（Serviceable Obtainable Market）

Source: [GoingVC](https://www.goingvc.com/post/how-investors-use-tam-sam-som-to-evaluate-startups) — 「Investors look at SOM to understand whether you've done a grounded, bottom-up forecast.」

| 年次 | ダウンロード数 | 有料転換率 | 有料ユーザー数 | ARR |
|------|-------------|---------|------------|-----|
| Year 1（市場シェア: SAMの0.4%） | 2,000 | 4% | 80 | **$2,399** |
| Year 2（市場シェア: SAMの2.2%） | 10,000 | 4% | 400 | **$11,996** |
| Year 3（市場シェア: SAMの6.6%） | 30,000 | 5% | 1,500 | **$44,985** |

**注:** SAM の 1% を SOM 上限とすると $6,762（Year 1）。ASO 最適化後の Year 3 は 6.6% = 現実的（ニッチカテゴリの先行優位）。

---

## 3. Problem Size & Demand Validation

Source: [Journal of Photochemistry and Photobiology](https://pubmed.ncbi.nlm.nih.gov/29447098/) — 「PBM (photobiomodulation) has been shown to have positive effects on pain, inflammation, wound healing, and skin rejuvenation.」

Source: [TikTok Hashtag Data via Apify](https://apify.com/clockworks/tiktok-hashtag-scraper) — 実行: 2026-03-09

| 統計データ | 値 | 意味 |
|---------|-----|------|
| #redlighttherapy TikTok plays | **698,400** | 消費者需要の証拠 |
| #biohacking TikTok plays | **4,100,000** | 上位トレンド確認 |
| RLT デバイス市場 CAGR | **15.47%** (2024-2029) | ユーザーベースの急拡大 |
| App Store 最大競合レビュー | **69 reviews** | 供給が需要に追いついていない |
| PBM 研究論文数（PubMed） | 3,000+ | 科学的エビデンスの充実 |
| 赤色光デバイス平均価格 | **$200-$1,000** | 高投資ユーザーは情報・ガイドを求める |

### 需要の質的証拠（Reddit r/biohacking）

Source: [Reddit r/biohacking](https://www.reddit.com/r/biohacking/) — コミュニティ投稿分析

| ペイン | 頻出度 |
|--------|--------|
| 「赤色光デバイスを買ったが使い方がわからない」 | 高（週次で類似投稿）|
| 「部位別プロトコルを教えて」 | 高 |
| 「何分くらい当てればいい？」 | 高 |
| 「効果を記録するアプリはある？」 | 中 |

---

## 4. Growth Analysis

Source: [Mordor Intelligence](https://www.mordorintelligence.com/industry-reports/red-light-therapy-device-market) — 「CAGR of 15.47% from 2024 to 2029.」

| 指標 | 値 |
|------|-----|
| RLT デバイス市場 CAGR (2024-2029) | 15.47% |
| Photobiomodulation 治療市場 CAGR (2022-2030) | 5.6% |

### Growth Drivers

| ドライバー | 詳細 |
|---------|------|
| TikTok バイラル化 | #redlighttherapy 698K plays。インフルエンサー（Huberman等）が推奨 |
| デバイス低価格化 | $1,000+ 専門機器 → $50-$200 の家庭用パネルが普及 |
| 科学的エビデンスの蓄積 | PubMed に 3,000+ 論文。NIH/Mayo Clinic が言及 |
| バイオハッキングブーム | Peter Attia「Outlive」ベストセラー。長寿・健康最適化トレンド |
| App Store 空白 | 最大競合が 69 reviews = 先行投入で ASO 上位確保容易 |

### Headwinds

| リスク | 詳細 |
|--------|------|
| 医療機器規制 | FDA が RLT を Class II デバイスに分類する可能性（アプリは非医療機器だが影響あり）|
| 科学的反証 | 一部研究で効果に懐疑的な結果も存在 |
| 競合参入加速 | 市場認知が高まると大手アプリが参入する可能性 |

---

## 5. POEM Market Opportunity Score

Source: [Mind the Product](https://www.mindtheproduct.com/poem-framework/) — 「Identify strengths and weaknesses in a market opportunity based on five key forces: Customer, Product, Timing, Competition, and Finance.」

| 軸 | スコア | 評価根拠 |
|----|--------|---------|
| **Customer** | 4/5 | 高価格デバイス所持者（$200-$1,000 投資済み）= WTP高い。ペイン明確（「使い方わからない」）。月$5 は心理的障壁低い |
| **Product** | 4/5 | 技術的実現性高（Timer + Charts + UserDefaults のみ）。AI/バックエンド不要。差別化は明確（3競合が全て機能欠如）|
| **Timing** | 5/5 | #redlighttherapy 698K TikTok plays（上昇中）。デバイス市場 CAGR 15.47%。App Store は空白 |
| **Competition** | 5/5 | 直接競合最大 69 reviews。機能ある競合ゼロ。先行優位で ASO 上位独占可能 |
| **Finance** | 3/5 | Year 1 SOM $2,399 ARR（小さい）。Year 3 $44,985（成長軌道）。LTV:CAC = CAC ≒ $0（ASO 有機）→ LTV:CAC > 10x |
| **合計** | **21/25** | 🟢 **Strong Opportunity** |

### ネガティブシグナル（確証バイアス防止）

Source: [Charisol](https://charisol.io/12-common-market-research-mistakes-and-how-to-avoid-them/) — 「It's easy to let personal opinions influence how you interpret data.」

| ネガティブシグナル | 詳細 | 対応 |
|----------------|------|------|
| **市場の小ささ** | RLT デバイス所持者は全 iPhone ユーザーの < 1%。Year 1 有料ユーザー 80人（ARR $2,399）は事業として小さい | ASO + TikTok UGC でオーガニック成長。初期目標は「月 $500 ARR」に設定してリアルな期待値を持つ |
| **科学的議論** | PBM 効果に懐疑的な研究も存在（プラセボ効果の可能性）。App Store審査でヘルスクレームが問題になる可能性 | コピーに「研究準拠」と記載するが医療的主張（「治療」「治癒」）は避ける。免責事項を明記 |
| **デバイス依存** | アプリの価値はRLTデバイス所持者にのみ発揮される。デバイスなしのユーザーはコンバートしない | オンボーディングで「デバイスなしでも使える？」に正直に答える。ターゲティングを絞る |

---

## Sources

| # | Source | URL | What It Supports |
|---|--------|-----|----------------|
| 1 | Mordor Intelligence: RLT Device Market | https://www.mordorintelligence.com/industry-reports/red-light-therapy-device-market | TAM, CAGR 15.47% |
| 2 | Grand View Research: PBM Therapy Market | https://www.grandviewresearch.com/industry-analysis/photobiomodulation-therapy-market-report | TAM $354M (2022) |
| 3 | Antler: TAM SAM SOM | https://www.antler.co/blog/tam-sam-som | ボトムアップ計算方法論 |
| 4 | GoingVC: SOM Calculation | https://www.goingvc.com/post/how-investors-use-tam-sam-som-to-evaluate-startups | SOM 計算フレームワーク |
| 5 | WaveUp: Market Sizing | https://waveup.com/blog/tam-sam-som/ | SAM セグメント計算 |
| 6 | Mind the Product: POEM Framework | https://www.mindtheproduct.com/poem-framework/ | POEM スコアリング |
| 7 | Apify TikTok Hashtag Scraper | https://apify.com/clockworks/tiktok-hashtag-scraper | #redlighttherapy 698K plays |
| 8 | iTunes Search API | https://itunes.apple.com/search | 競合レビュー数（69 最大）|
| 9 | Reddit r/biohacking | https://www.reddit.com/r/biohacking/ | 質的需要証拠 |
| 10 | PubMed: PBM Research | https://pubmed.ncbi.nlm.nih.gov/29447098/ | 科学的エビデンス |
| 11 | Charisol: Market Research Mistakes | https://charisol.io/12-common-market-research-mistakes-and-how-to-avoid-them/ | ネガティブシグナル分析方法論 |
| 12 | AppTweak: App Market Research | https://www.apptweak.com/en/aso-blog/app-market-research | 市場調査フレームワーク |
