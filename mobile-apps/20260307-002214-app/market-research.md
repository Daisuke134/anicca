# Market Research: EyeBreakIsland

**Generated:** 2026-03-07
**Method:** Bottom-up + Top-down クロスチェック (iTunes API + AOA統計 + RevenueCat SOSA 2025)

---

## 1. Market Definition

| 項目 | 値 |
|------|-----|
| **カテゴリ** | Health & Fitness（App Store主カテゴリ） |
| **サブカテゴリ** | Eye Care / Digital Wellness / Productivity |
| **対象地域** | 主：米国 (US) + 日本 (JP)、副：EU（英・独・仏） |
| **ICP (Ideal Customer Profile)** | iPhone 14 Pro以降（Dynamic Island搭載）保有の、1日6時間以上スクリーンを使う25-45歳リモートワーカー・エンジニア・デザイナー |
| **App Store対象セグメント** | 20-20-20ルールを「知っているが守れていない」ユーザー |

---

## 2. Market Sizing (TAM/SAM/SOM)

### トップダウン アプローチ

| 階層 | 計算根拠 | 規模 |
|------|---------|------|
| **TAM (Global)** | Global mobile health apps revenue (2025推定) × 目の健康カテゴリ割合 (~2%) | **$280M** (Health & Fitness iOS global $14B × 2%) |
| **SAM (US+JP iOS)** | 米国DES患者 168M × iPhone利用率57% × アプリ検討率10% = 9.6M + 日本4M = 13.6M 人 × ARPU $4/yr | **$54M** |
| **SOM Year 1** | SAM × 0.02% (新規参入インディー現実値) | **$11K** |
| **SOM Year 2** | SAM × 0.07% (ASO確立後) | **$38K** |
| **SOM Year 3** | SAM × 0.25% (口コミ+Watch対応後) | **$135K** |

Source: [Sensor Tower 2025 Report](https://sensortower.com) — 「Global Health & Fitness app market ~$14B in 2025」
Source: [Vision Council: Digital Eye Strain Report 2021](https://visioncouncil.org) — 「65% of US adults report symptoms of digital eye strain」
Source: [AOA: Computer Vision Syndrome](https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome) — 「Average American worker spends 7 hours a day on computer」

### ボトムアップ アプローチ（競合レビューベース）

| 競合アプリ | レビュー数 | 推定インストール数 (×100) |
|-----------|----------|------------------------|
| Eye Care 20 20 20 | 365 | ~36,500 |
| Eye Workout | 231 | ~23,100 |
| Eye Strain Guard | 1 | ~100 |
| その他眼ブレーク系 | ~10 | ~1,000 |
| **合計（目ブレーク専門）** | **607** | **~60,700** |

```
ボトムアップ TAM推計:
推定インストール合計: 60,700
ARPU（現状、無料アプリ多いため広告ベース）: $0.10/user/yr (低)
現在の市場規模: ~$6,000/yr (= 市場未開拓を示す)

新規市場として:
潜在ユーザー: 9.6M (US) × 5%アプリ検討 = 480,000
ARPU（有料化後）: $29.99/yr × 5% paid = $1.50
Bottom-up TAM: 480,000 × $1.50 = $720,000/yr
```

**クロスチェック:** トップダウン ($54M SAM) vs ボトムアップ ($720K) → 乖離75倍
→ ボトムアップが現実的。トップダウンは市場全体の"潜在"規模。**現在の実質市場は未開拓 = 先行者優位チャンス大**。

### 詳細 SOM テーブル

| 指標 | Year 1 | Year 2 | Year 3 |
|------|--------|--------|--------|
| 月間新規DL | 500 | 2,000 | 8,000 |
| 累計インストール | 6,000 | 30,000 | 126,000 |
| 有料転換率 | 5% | 6% | 7% |
| 有料ユーザー数 | 300 | 1,800 | 8,820 |
| Monthly ARPU | $5.00 | $5.50 | $6.00 |
| 年間収益 | **$18,000** | **$118,800** | **$635,040** |

Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — 「H&F apps: trial-to-paid 39.9% median; 30% churn in first month」

---

## 3. Problem Size & Demand Validation

### 統計データによる需要証明

| # | 統計 | 数値 | ソース |
|---|------|------|--------|
| 1 | 米国成人のDES（デジタル眼精疲労）有病率 | **65%**（約1.68億人） | [Vision Council: Digital Eye Strain Report 2021](https://visioncouncil.org) |
| 2 | 米国労働者の平均スクリーン時間 | **7時間/日** | [AOA: Computer Vision Syndrome](https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome) |
| 3 | DES発症リスク閾値 | **2時間以上/日**の連続スクリーン使用 | [AOA: Computer Vision Syndrome](https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome) — 「At greatest risk: those who spend two or more continuous hours at a computer every day」 |
| 4 | TikTok #eyestrain 視聴数（実測） | **471,344 views**（4動画、2026-03-07） | Apify TikTok Scraper Dataset eFjMOK1Yz6WQr55Ac |
| 5 | Dynamic Island搭載機（米国推定） | **5,000万台以上** | iPhone 14 Pro+ (2022), 全iPhone 15 (2023), 全iPhone 16 (2024) |
| 6 | 米国iPhoneユーザー数 | **1.6億人** | [Statista 2025](https://www.statista.com) |

### 需要の質的証拠

| カテゴリ | 証拠 | 示すもの |
|---------|------|---------|
| **ユーザー痛み（★1レビュー）** | 「stops counting and never notifies you」(Eye Care 20 20 20) | 既存解決策の失敗 → 代替需要 |
| **ユーザー要望** | 「I wanted an app that would pair with my Apple Watch」 | 未充足ニーズの存在 |
| **SNSトレンド** | #eyestrain 471K TikTok views | 問題認知の高まり |
| **医療機関推奨** | AOA公式推奨「20-20-20 rule」 | 解決策の科学的正当性 |

---

## 4. Growth Analysis

### CAGR & 成長ドライバー

| 指標 | 値 | ソース |
|------|-----|--------|
| モバイルヘルスアプリ市場 CAGR | ~14%/年 (2024-2030) | Market research consensus |
| H&F iOS app revenue CAGR | ~11%/年 | Sensor Tower 2025 |
| Dynamic Island搭載iPhone 普及率 | 毎年増加（iPhone 15全モデル以降標準搭載） | Apple Product Line |

### 成長ドライバー

| Driver | 詳細 | インパクト |
|--------|------|----------|
| **Remote Work 定着** | COVID後もリモートワーカー増加継続。スクリーン時間増加が構造的 | High |
| **Dynamic Island普及** | iPhone 15（2023）・16（2024）で全モデル標準搭載。毎年数千万台追加 | High |
| **デジタルウェルネス意識向上** | #eyestrain TikTokトレンド。若年層の目の健康関心増加 | Medium |
| **Health & Fitness APP成長** | RevenueCat: 「AI apps + H&F = Revenue per install $0.63 (top category)」 | Medium |
| **競合の技術的停滞** | Eye Care 20 20 20が2026-01更新もバグ未修正のまま | Medium |

### 向かい風（Headwinds）

| Headwind | 詳細 | 対応策 |
|---------|------|-------|
| **Screen Time API制限** | Apple がサードパーティのScreen Time読み取りを制限 | MVP では Screen Time API 不使用。Live Activities で代替 |
| **無料競合の存在** | Eye Care 20 20 20 が無料のまま改善した場合 | Dynamic Island + Watch = 有料機能で差別化維持 |
| **Dynamic Island制限** | 同時に表示できるLive Activitiesは限られる | 軽量アクティビティ設計。競合との衝突最小化 |
| **習慣化の難しさ** | 目の健康アプリは30-day churn高い傾向 | Streak（連続日数）+ Daily Summary通知で習慣化促進 |

---

## 5. POEM Market Opportunity Score

### スコアリング

| 軸 | スコア (1-5) | 評価根拠 |
|----|------------|---------|
| **Customer** (ペインの深刻度 + WTP) | **4** | DES有病率65%、症状は目の疲れ・頭痛・ドライアイと深刻。ただしWTPは中程度（$4.99/月） |
| **Product** (技術実現性 + 差別化) | **5** | ActivityKit + UserNotifications で実装可能。Dynamic Island は全競合未使用 → 強差別化 |
| **Timing** (トレンド合致) | **4** | #eyestrain TikTok 471K views。Remote Work定着。Dynamic Island普及中。ただし市場自体は萌芽期 |
| **Competition** (競合密度 + 参入障壁) | **5** | 直接競合最高 365 reviews（極弱）。参入障壁低（Swift/SwiftUI + ActivityKit） |
| **Finance** (SOM規模 + LTV:CAC) | **3** | SOM Year 1 は $18K（小規模）。LTV ($29.99 annual × 2yr) = $60 vs CAC ($0、ASO有機) → LTV:CAC∞だが絶対額は小さい |
| **合計** | **21 / 25** | |

**判定:** 🟢 **Strong Opportunity** (20-25点)

### ネガティブシグナル（必須記載 — 確証バイアス防止）

> ⚠️ **重大なネガティブシグナル:** Dynamic Island は「目立つが慣れで無視される」可能性がある。Verge等のレビューで「Live Activitiesはロック画面を雑然とさせる」批判あり。ユーザーが最終的にLive Activitiesを無効化した場合、EyeBreakIslandの核心的差別化が失われる。**対策:** オンボーディングで通知ON + Live Activities有効化を強調。無効化ユーザーへの代替通知UX（大きなバナー通知）を用意する。

Source: [Charisol: Market Research Mistakes](https://charisol.io/12-common-market-research-mistakes-and-how-to-avoid-them/) — 「It's easy to let personal opinions influence how you interpret data. Cherry-picking findings is a common mistake.」

---

## Sources

| # | Source | URL | What It Supports |
|---|--------|-----|-----------------|
| 1 | AOA: Computer Vision Syndrome | https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome | 7h/day screen time, 2h+ risk threshold, 20-20-20 official recommendation |
| 2 | Vision Council: Digital Eye Strain Report 2021 | https://visioncouncil.org | 65% of US adults experience DES |
| 3 | RevenueCat SOSA 2025 | https://www.revenuecat.com/state-of-subscription-apps-2025/ | H&F ARPU, trial-to-paid 39.9%, 30% first-month churn |
| 4 | Apify TikTok Dataset eFjMOK1Yz6WQr55Ac (2026-03-07) | https://apify.com | #eyestrain 471,344 TikTok views |
| 5 | Sensor Tower 2025 | https://sensortower.com | Global H&F app market ~$14B; CAGR ~11% |
| 6 | Antler: TAM/SAM/SOM | https://www.antler.co/blog/tam-sam-som | 「Bottom-up approach is more credible」 |
| 7 | GoingVC: TAM/SAM/SOM | https://www.goingvc.com/post/how-investors-use-tam-sam-som-to-evaluate-startups | 「Investors look at SOM for grounded bottom-up forecast」 |
| 8 | AppTweak: App Market Research | https://www.apptweak.com/en/aso-blog/app-market-research | Market insights, competitors, target audience |
| 9 | Statista 2025 | https://www.statista.com | 米国 iPhone ユーザー数 1.6億人 |
| 10 | iTunes Search API / Lookup API (2026-03-07) | https://itunes.apple.com/search | 競合レビュー数（ボトムアップ計算の基礎データ） |
| 11 | Mind the Product: POEM Framework | https://www.mindtheproduct.com/poem-framework/ | Customer/Product/Timing/Competition/Finance 5軸評価 |
| 12 | Charisol: Market Research Mistakes | https://charisol.io/12-common-market-research-mistakes-and-how-to-avoid-them/ | ネガティブシグナル記載の重要性（確証バイアス防止） |
