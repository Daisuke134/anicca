# Anicca Homepage — Evidence-Backed Copy Refresh Proposal

**Created 2026-11-05. Status: DRAFT ONLY — NOT MERGED INTO THE ANICCA WEBSITE AND NOT DEPLOYED.**

## Source and reason for updating

Site: https://aniccaai.com/ (redirects to /en). Actual primary source: `Daisuke134/anicca-products` (GitHub main), notably `apps/landing/components/site/ManagerHome.tsx`, `apps/landing/app/en/page.tsx`, `apps/landing/app/ja/page.tsx`, and potentially the reusable `apps/landing/components/site/Hero.tsx`. Site is already much more mature than an old simple voice assistant page; preserve the mission, existing products/URLs, localization, design and the separation of vision from proof.

**Observed stale claim (official current source):**
- Home Evidence: "We are developing the first population and evaluation components", status "IMPLEMENTATION PLANNED".
- Now actual 2026-11-05 research execution includes published real human reward/learning data from Collins WMH, five datasets / 269,603 valid trial choices, participant-disjoint holdout and separate research stress tests, alongside openESM repeated self-reports for rumination-related brooding and stress. No verified causal benefit for actual clients, no general behavior FM weights released.
- English homepage SEO describes the company as "run entirely by AI agents", stronger than the public evidence for fully unstaffed legal/operational functions; consider "AI-led" while retaining ambitious long-term company vision.

## Proposed revised hero (English)

**Headline (retain strong minimalist "Manager."):**

Manager.

**Tagline (retain mission):** One entity, blessing for all.

**Lead copy:**

Understand human behavior. Compare what could happen next. Act within verified permissions, and measure what actually changed.

Manager is Anicca's open research and product effort to connect AI predictions with real-world outcomes across body, mind, and money.

**Call to action:** Explore the vision / See the evidence

## Proposed revised hero (日本語)

**見出し：** マネージャー。

**タグライン：** ひとつの存在、すべてに恩恵を。

**リード文：**

人の行動を理解し、「もし別の行動を選んだら？」という可能性を比較する。許可された範囲で行動し、実際に何が変わったかを確かめる。

Managerは、身体・心・お金の課題をよりよくするためのAniccaのオープンな研究・プロダクト開発です。

## Proposed Evidence section (English)

**Heading:** A transparent ambition. Evidence you can inspect.

**Lead:** We distinguish our long-term ambition from demonstrated results. We have evaluated predictive models on observed human choices, including participant-held-out reward, habit, and memory tasks. An improvement in prediction is not proof of better wellbeing or business results.

**Ledger:**

| Category | Evidence | Status |
|---|---|---|
| Human behavior evaluation | 269,603 observed research-task choices; reproducible held-out reward/habit/memory analysis | RESEARCH CODE VERIFIED |
| What-if and execution | Offline policy/permission/reconciliation tests exist. Real commercial live interventions remain pending | FIELD VALIDATION PENDING |
| Real human & business outcomes | Independent causal reduction in rumination, improvement in wellbeing, and net profit | NOT YET ESTABLISHED |

**Link:** Read the reproducible human behavior evaluation

Destination: `https://github.com/Daisuke134/life-manager/blob/main/docs/research/manager/masterclass/2026-11-04-p04-causal/P07-1_JA.md`

## Proposed Evidence section (日本語)

**見出し：** 大きな構想を、確かめられる進歩に。

**リード文：** 長期の目標と検証済みの成果を分けて公開します。公開された実人間の選択データを使い、報酬・習慣・記憶モデルを比較しました。ただし予測の改善は、人の苦しみや会社の利益を実際に改善したという証明ではありません。

| 項目 | 実績・今後 | 状態 |
|---|---|---|
| 行動予測と評価 | 269,603件の実人間選択試行、未知参加者・別研究でのモデル比較 | 研究コード検証済 |
| What-ifと実行 | 権限・証拠・復旧などのオフライン検証。実事業での介入効果は未確認 | 実地評価待ち |
| 本人と事業への便益 | 反すう減少、生活機能、支払い済み増分利益の独立検証 | 未実証 |

**リンク：** 実人間データを使った研究結果を読む

## Meta description

English: Anicca researches Manager, a proactive AI project connecting human-behavior prediction, permissioned action, and verifiable results. Explore open research, current products, and what remains to be tested.

日本語: Aniccaは、行動予測・権限に基づく実行・独立した結果検証をつなぐAI「Manager」を研究・開発しています。公開研究の成果、提供中のアプリ、未検証の課題をご覧いただけます。

## Release and acceptance conditions

1. Locate the actual Next.js homepage and localized metadata in `Daisuke134/anicca-products`. Preserve live product and CTA routing.
2. Verify exact currently released wording and which features are actually public. The vision should not make unreleased interventions, full zero-human legal operations, or clinical efficacy sound proven.
3. Review the English/Japanese pairs, TypeScript tests and site preview on its canonical Netlify/Next deployment workflow.
4. Use authorized repository updates + PR, review/merge, and fetch actual `https://aniccaai.com/en` and `/ja` independently before claiming copy deployed.
5. **Current status: draft prepared only; repository mutation tool security check blocked the direct website edit. Do not bypass that control or claim a live change.**
