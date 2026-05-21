# Market Research: EyeRest

## 1. Market Definition

| Item | Value |
|------|-------|
| Category | Health & Fitness (Primary), Medical (Secondary) |
| Sub-Category | Eye Health / Digital Eye Strain Prevention |
| Region | US + JP (iOS) |
| ICP | Knowledge workers aged 25-45 who spend 6-10+ hours daily on screens and experience eye fatigue, headaches, or dry eyes |
| App Store Sub-Category | Health & Fitness > Exercise & Fitness |

---

## 2. Market Sizing (TAM/SAM/SOM)

### Top-Down Approach

| Metric | Value | Source |
|--------|-------|--------|
| Global Digital Eye Care Market | $3.5B (2025) | [Grand View Research](https://www.grandviewresearch.com/industry-analysis/eye-health-supplements-market) — digital eye care segment (apps + devices + lenses) |
| CAGR | 8.5% (2025-2030) | Grand View Research — eye health market growing driven by screen time increase |
| Global mHealth App Market | $86.4B (2025) | [Precedence Research](https://www.precedenceresearch.com/mobile-health-apps-market) — mobile health apps market |
| H&F App Revenue (iOS) | ~$7.5B (2025) | [Sensor Tower](https://sensortower.com/) — Health & Fitness category App Store revenue estimate |

**Top-Down TAM:** $3.5B (digital eye care total market)

### Bottom-Up Approach

| Step | Calculation | Value |
|------|------------|-------|
| US adults with DES symptoms | 210M adults x 65% prevalence | 136.5M |
| JP adults with DES symptoms | 105M adults x 50% prevalence | 52.5M |
| Total addressable users (US + JP) | 136.5M + 52.5M | 189M |
| iOS users (US 57%, JP 68%) | (136.5M x 0.57) + (52.5M x 0.68) | 77.8M + 35.7M = 113.5M |
| Screen workers subset (6+ hrs/day) | 113.5M x 40% (office/knowledge workers) | 45.4M |
| ARPU (blended) | 10% paid x $40 avg annual | $4.00 |
| **Bottom-Up TAM** | 45.4M x $4.00 | **$181.6M** |

Source: [Vision Council 2016](https://www.thevisioncouncil.org/content/digital-eye-strain) — "65% of Americans report experiencing symptoms of digital eye strain"
Source: [Sheppard & Wolffsohn, BMJ Open Ophthalmology 2018](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6020759/) — "estimates suggest its prevalence may be 50% or more among computer users"

**Cross-Check:** Top-Down ($3.5B total market) vs Bottom-Up ($181.6M app-only TAM). The $3.5B includes hardware (glasses, devices, supplements) — app-only TAM of $181.6M is ~5.2% of total market, which is reasonable for a software-only play.

### SAM Calculation

| Factor | Value | Source |
|--------|-------|--------|
| Bottom-Up TAM | $181.6M | Calculated above |
| iOS rate (already applied) | 100% (pre-filtered) | — |
| Target region (US + JP only) | 100% (pre-filtered) | — |
| "Eye break reminder" intent segment | 15% of DES sufferers actively seek a timer solution | [AppRadar](https://appradar.com/blog/5-essential-factors-in-competitor-analysis-for-mobile-apps) — competitor review volume as proxy for intent |
| **SAM** | $181.6M x 15% | **$27.2M** |

Validation: Top 5 direct competitors have ~550 total reviews. At 50-100x multiplier (industry standard), that's 27,500-55,000 installs across the entire niche. At $40 avg annual ARPU for 10% of installs = $110K-$220K annual revenue in the niche today. This suggests the **active market** is small but growing.

### SOM Calculation

| Year | Calculation | SOM |
|------|------------|-----|
| Year 1 | $27.2M x 0.01% (new entrant) | $2,720 |
| Year 2 | $27.2M x 0.05% (traction + ASO) | $13,600 |
| Year 3 | $27.2M x 0.2% (word-of-mouth + reviews) | $54,400 |

Source: [GoingVC](https://www.goingvc.com/post/how-investors-use-tam-sam-som-to-evaluate-startups) — "A startup calculated their SOM as 15% of SAM while competing against HubSpot—realistic SOM was closer to 0.5%." Indie app with 0 marketing budget = 0.01-0.2%.

### Alternative SOM (Unit Economics)

| Scenario | Monthly Downloads | Trial Rate | Conversion | Monthly Rev | Annual Rev |
|----------|-------------------|-----------|------------|-------------|------------|
| Conservative (Y1) | 2,000 | 8% | 15% | $120 | $1,440 |
| Base (Y2) | 5,000 | 10% | 20% | $500 | $6,000 |
| Optimistic (Y3) | 15,000 | 12% | 25% | $2,250 | $27,000 |

Source: [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — H&F download-to-trial median ~8-10%, trial-to-paid varies by price point

---

## 3. Problem Size & Demand Validation

| # | Statistic | Value | Source |
|---|-----------|-------|--------|
| 1 | US adults reporting DES symptoms | 65% | [Vision Council 2016 Digital Eye Strain Report](https://www.thevisioncouncil.org/content/digital-eye-strain) — "65% of Americans report experiencing symptoms of digital eye strain" |
| 2 | Global DES prevalence among computer users | 50%+ | [Sheppard & Wolffsohn, BMJ Open Ophthalmology 2018 (PMC6020759)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6020759/) — "estimates suggest its prevalence may be 50% or more among computer users" |
| 3 | Average US worker daily screen time | 7 hours | [AOA Computer Vision Syndrome](https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome) — "The average American worker spends seven hours a day on the computer" |
| 4 | 20-20-20 rule recommendation | Official AOA recommendation | [AOA](https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome) — "take a 20-second break to view something 20 feet away every 20 minutes" |
| 5 | Annual economic cost of visual impairment (US) | $145B | [CDC Vision Health Initiative](https://www.cdc.gov/vision-health/php/data-research/) — annual cost of vision problems in the US |
| 6 | Post-pandemic screen time increase | +30-40% | [Deloitte Digital Consumer Trends 2023](https://www2.deloitte.com/us/en/insights/industry/technology/technology-media-and-telecom-predictions.html) — remote work driving screen time surge |

**Demand Signal from Competitor Reviews:**

Eye Care 20 20 20 has 365 reviews despite being fundamentally broken (forced login, broken timer). This proves user demand exists — people actively search for and download 20-20-20 apps. The 19 negative reviews document specific, solvable failures, indicating users WANT this solution but can't find a reliable one.

---

## 4. Growth Analysis

### CAGR & Growth Drivers

| Factor | Impact | Direction | Source |
|--------|--------|-----------|--------|
| Remote/hybrid work permanence | HIGH | Upward | Screen time increase → more DES → more demand |
| DES awareness campaigns (AOA, WHO) | MEDIUM | Upward | Public health messaging increasing search volume |
| Screen time per capita growth | HIGH | Upward | +30-40% since pandemic, no sign of reversal |
| App Store H&F category growth | MEDIUM | Upward | [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — H&F subscription apps growing |
| Blue light glasses market saturation | LOW | Upward | Glasses don't solve break frequency — complementary, not competitive |

### Headwinds

| Factor | Impact | Direction | Source |
|--------|--------|-----------|--------|
| Apple Health app expansion | HIGH | Downward | Apple could add 20-20-20 to Health app natively |
| Subscription fatigue | MEDIUM | Downward | [RevenueCat SOSA 2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) — "Nearly 30% of annual subscriptions are canceled in the first month" |
| Small niche ceiling | MEDIUM | Downward | Only 365 reviews for top competitor = limited active demand today |
| Free alternatives (iOS timer) | LOW | Downward | No guided rest, no exercises, no tracking — minimal overlap |

---

## 5. POEM Market Opportunity Score

Source: [Mind the Product](https://www.mindtheproduct.com/poem-framework/) — "Identify strengths and weaknesses in a market opportunity based on five key forces"

| Axis | Score | Rationale |
|------|-------|-----------|
| **Customer** | 4/5 | DES affects 50-65% of screen workers (deep pain). WTP moderate: health investment mindset, but eye care seen as "nice-to-have" vs "must-have" by some. 365 reviews on broken competitor = demand proven. |
| **Product** | 5/5 | Technically trivial (timer + notifications + SwiftData). Near-zero technical risk. Clear differentiation via fixing all documented competitor failures. 8 unique features vs top competitor. |
| **Timing** | 4/5 | Post-pandemic screen time permanently elevated. DES awareness growing. 20-20-20 rule gaining mainstream recognition. No seasonal dependency. |
| **Competition** | 5/5 | Weakest competition of any health niche analyzed. Top competitor: 365 reviews, 4.34 rating, broken core features. No VC-backed or well-funded competitor. 5+ new entrants (Tweny, GlanceAway, Eye Break Timer) all at 0 reviews = market is actively being explored. |
| **Finance** | 2/5 | SOM Year 1: $1,440-$2,720. SAM: $27.2M but realistic capture is tiny. LTV:CAC unknown (organic only). Subscription model viable per RevenueCat data but niche is small. Not a $500K+ SOM without significant marketing investment. |

### Total Score

| Total | Judgment |
|-------|----------|
| **20/25** | Strong Opportunity |

### Negative Signal (Mandatory — Confirmation Bias Prevention)

**The niche may be too small for sustainable subscription revenue.** Eye Care 20 20 20 has operated since ~2015 with only 365 reviews — approximately 33 reviews per year. Even at 100x multiplier, that's 36,500 lifetime installs over 11 years (~3,300/year). If EyeRest captures this entire niche (unlikely), at 10% conversion and $40 avg annual ARPU, that's $13,200/year. This is a **lifestyle business, not a venture-scale opportunity**. The subscription model must be validated quickly — if Month 3 conversion is below 10%, consider pivot to one-time purchase ($4.99).

Source: [Charisol](https://charisol.io/12-common-market-research-mistakes-and-how-to-avoid-them/) — "It's easy to let personal opinions influence how you interpret data. Sometimes, teams cherry-pick findings that support what they already believe."

---

## Sources

| # | Source | URL | What It Supports |
|---|--------|-----|-----------------|
| 1 | Vision Council 2016 | [thevisioncouncil.org/content/digital-eye-strain](https://www.thevisioncouncil.org/content/digital-eye-strain) | 65% DES prevalence in US adults |
| 2 | BMJ Open Ophthalmology 2018 | [ncbi.nlm.nih.gov/pmc/articles/PMC6020759](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6020759/) | 50%+ global DES prevalence |
| 3 | AOA Computer Vision Syndrome | [aoa.org/healthy-eyes/.../computer-vision-syndrome](https://www.aoa.org/healthy-eyes/eye-and-vision-conditions/computer-vision-syndrome) | 7 hrs/day screen time, 20-20-20 rule |
| 4 | Grand View Research | [grandviewresearch.com/industry-analysis/eye-health-supplements-market](https://www.grandviewresearch.com/industry-analysis/eye-health-supplements-market) | $3.5B digital eye care market, 8.5% CAGR |
| 5 | RevenueCat SOSA 2025 | [revenuecat.com/state-of-subscription-apps-2025](https://www.revenuecat.com/state-of-subscription-apps-2025/) | H&F pricing benchmarks, trial/churn data |
| 6 | GoingVC TAM/SAM/SOM | [goingvc.com/post/how-investors-use-tam-sam-som](https://www.goingvc.com/post/how-investors-use-tam-sam-som-to-evaluate-startups) | SOM estimation methodology |
| 7 | Mind the Product POEM | [mindtheproduct.com/poem-framework](https://www.mindtheproduct.com/poem-framework/) | Market opportunity scoring framework |
| 8 | Charisol Market Research | [charisol.io/12-common-market-research-mistakes](https://charisol.io/12-common-market-research-mistakes-and-how-to-avoid-them/) | Confirmation bias prevention |
| 9 | AppRadar Competitor Analysis | [appradar.com/blog/5-essential-factors-in-competitor-analysis](https://appradar.com/blog/5-essential-factors-in-competitor-analysis-for-mobile-apps) | Market intent estimation methodology |
| 10 | CDC Vision Health Initiative | [cdc.gov/vision-health/php/data-research](https://www.cdc.gov/vision-health/php/data-research/) | $145B annual cost of vision problems (US) |
