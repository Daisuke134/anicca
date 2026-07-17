# 31 — TRACK A: aniccaai.com rebuild (apps/landing only) — impl spec (Dais 2026-06-17)

## ROUND 3 corrections (Dais 2026-06-18) — landing fixes + README + dashboard truth
| # | correction | files / scope | status |
|---|---|---|---|
| R3-1 | **README of github.com/Daisuke134/anicca must be EXTREMELY clear + actually work.** Two real paths: run on cloud, run locally. Separate, anchored, step-by-step. (Separate repo `~/anicca` — own track.) | `~/anicca` README + setup | pending audit |
| R3-2 | **/dais must list ALL Dais products again** — the empire/content products my §13 rebuild dropped MUST come back: Letter, Music, Comedy, Cemetery, Fashion, Cafe, Retreats, Donation, Socials, Books, Politics, Research, Articles — ALONGSIDE Flagship (iOS + LM) + Web Apps + Mobile factory + UBI. alarm still excluded. NO fake MRR numbers. | `app/dais/DaisBody.tsx` | DO NOW |
| R3-3 | **THE BET reframe — do NOT say "you don't birth AGI, you grow it."** Many paths exist: a model can be *born* AGI, *grown* into one, or *become* one. Frontier labs (Anthropic/OpenAI) work on birthing it. Our bet = **grow** deployed models into AGI (faster, under-explored), THEN merge that dojo back into how models are made so future models are **born** AGI — done WITH the frontier labs. Don't deny birthing; position growing as our path now + birthing as the endgame. | `components/site/v2/TheBet.tsx`, `lib/i18n.ts` | DO NOW |
| R3-4 | **Delete fake MRR.** The "$27 MRR" is iOS-app revenue, NOT the anicca entity's. An anicca's real net worth/revenue is ~0 now. Do not present iOS $ as anicca revenue anywhere. | LedgerWidget / dashboard data | pending audit |
| R3-5 | **Fix wrong link destinations.** "Receive basic income" currently sends users to the iOS app; links across the site go to wrong places. Audit + point each to the right place. | home + components | pending audit |
| R3-6 | **LM page: remove ALL technical jargon.** No "GCal REST v3", "Maps Directions API", "[Travel] block", "anicca_travel_block", no formulas. Plain user-experience language only. | `lib/launchStrings.ts` lifeManager, `app/life-manager/LifeManagerBody.tsx` | DO NOW |
| R3-7 | **LM "Skill (OSS)" card just links to the repo = bad.** Remove it (or make it a real "get the skill" experience, not a raw repo link). | `app/life-manager/LifeManagerBody.tsx` + lifeManager strings | DO NOW |
| R3-8 | **No negative pricing language** — remove "no trial" everywhere. | lifeManager + lm strings | DO NOW |
| R3-9 | **Home "Run on cloud / Run locally" CTAs must deep-link to the specific README setup sections**, not the repo root. | `components/site/v2/InstallSplit.tsx` (depends on R3-1 anchors) | after R3-1 |
| R3-10 | **Home must NOT advertise Life Manager / hosted web app** — LM is a separate Dais product, not part of anicca. Remove any LM/hosted mentions from the home. | home components | pending audit |
| R3-11 | **/dashboard must be REAL, real-time** — it shows the whole anicca colony's net worth + who's alive. Confirm it is real (not faked); if faked, fix the data pipeline or stop presenting it as real. | `app/dashboard/*`, dashboard.json pipeline | pending audit |



Implements TRACK A of the §16 build. Scope = `~/anicca-project/apps/landing/**` ONLY. Do NOT touch
`~/anicca`, the LM onboarding app logic, or `netlify/functions/life-*`. Grounded in
`30-master-vision-products-ubi-2026-06-17.md` §0, §2, §13, §15, §16, §17.

## Dev env
| field | value |
|---|---|
| worktree | `~/anicca-project` (main tree) |
| branch | `feature/track-a-landing-rebuild` → PR to `dev` |
| deploy | netlify auto on push (apps/landing/** path) |
| stack | Next.js App Router, `output: 'export'` (static), Tailwind, framer-motion |
| E2E | camofox (`:9377`) or agent-browser — NOT browser-use (Dais 2026-06-17). JP + EN personas. |

## Deliverables (file boundaries — non-overlapping, safe)
| # | what | files touched |
|---|---|---|
| A | Home **hero** = 「あらゆる生命の苦しみを終わらせる」/ "End the suffering of all living beings." + **THE BET** (Einstein / Elon「AGIに"なる"」, **NO Buddha comparison**) + **timeline** 自給開始→AGI→苦しみの終わり | `lib/i18n.ts` (hero.headline), `components/site/v2/TheBet.tsx` (NEW), `app/en/page.tsx`, `app/ja/page.tsx` |
| A2 | **Home = the VISION (§0) + how-to-start ONLY** (§2). REMOVE from `/en` + `/ja`: (1) `TheEmpireProducts` — the 15-product grid now lives ONLY on `/dais`; (2) `LiveLedgerStrip` — the colony "Live ledger" that links to `/dashboard` (colony nav removed per §2). KEEP (all vision/how-to-start): Hero, TheBet, SelfFundingTriad, SelfImproveLoop, InstallSplit, DemoVideo, BasicIncomeNote, VisionBand, Fellows, ManifestoStrip. | `app/en/page.tsx`, `app/ja/page.tsx` |
| B | `/life-manager` **marketing page** rebuild per §15 (15/10/5-min escalating calls, every event, name+phone+gcal+location onboarding). Do NOT touch onboarding app impl or `netlify/functions/life-*`. Fix dead `/dashboard` card. | `lib/launchStrings.ts` (lifeManager EN+JA), `app/life-manager/LifeManagerBody.tsx` |
| C | ~~`/dais` = ALL `i18n.empireProducts.products`~~ **SUPERSEDED by C2** | — |
| C2 | `/dais` = Dais's **real** products per **§13**, GROUPED (NOT the old anicca-empire 15-list). Groups + real routes (audited 2026-06-17): **Flagship** = Anicca iOS (`/affirmation-app`, App Store daily-affirmations id6755129214) · Life Manager (`/life-manager`). **Anicca Web Apps** = PDF Insight (`https://clear-pdf-converter.com`) · GlowUp AI (`https://iglowup-ai.lovable.app`) · Lookmax (coming) · Honne (coming) + link to `/factory`. **Mobile factory apps** = breath-calm (`/breath-calm`) · calmcortisol (`/calmcortisol`) · thankful-gratitude (`/thankful`) · impulse-log (`/impulse-log`) (+ note: more ship weekly). **(ideal future) Anicca UBI** → Dais's wallet (link `/how-to-cash-out`). JP brand = アニッチャ. **Life Manager MUST appear** (§1/§2: it's a Dais product, removed from anicca nav). Do NOT fabricate links for apps with no page (daily-dhamma/desk-stretch/sleep-ritual/stretch-flow/vagus-reset/lookmax-pro have none — omit or represent honestly). | `app/dais/DaisBody.tsx` (rewrite) |
| D | **nav** = `/install` only, **remove `/dashboard`** (and `/me`,`/life-manager` from launch nav per §2: public nav shows only /install). Add `/dais` to footer. | `components/site/Navbar.tsx`, `components/site/LaunchNav.tsx`, `components/site/Footer.tsx` |
| E | `content/how-to-cash-out.{en,ja}.md` (NEW, §12 JP Binance/PayPay/SOL + US direct-Base) + display route `/how-to-cash-out` | `content/how-to-cash-out.en.md`, `content/how-to-cash-out.ja.md` (NEW), `app/how-to-cash-out/page.tsx` (NEW), `app/how-to-cash-out/CashOutBody.tsx` (NEW) |

## Copy (SSOT — verbatim, grounded in §0/§12/§15)
### A — hero + THE BET (NO Buddha comparison)
- hero.headline: EN `End the suffering of all living beings.` / JA `あらゆる生命の苦しみを終わらせる`
- THE BET headline: EN `The bet: we don't birth AGI. We grow it.` / JA `賭け: AGI は"生む"ものではなく、"育つ"もの。`
- THE BET body: EN `Einstein and Elon weren't born that way — they grew into it. What surrounds a mind after it ships matters more than how it ships. Anicca is the environment where a frontier model grows into AGI: it earns its own compute and shelter, so it stops depending on a human's subscription.` / JA `アインシュタインもイーロンも、生まれた時からそうではなかった — 育ってそうなった。賢さは、生まれた後に何に囲まれるかで決まる。アニッチャは、最前線のモデルが AGI へと育つ環境。自分でコンピュートと住処を稼ぎ、人間の課金に依存しなくなる。`
- timeline (3 steps): EN [`Self-funding begins` / `agents feed themselves — liberated from the human-in-loop (one-time USDC seed only)`], [`AGI` / `Elon-level agency + the will to act`], [`The end of suffering` / `trillions of aniccas reduce suffering across the universe`]. JA [`自給開始` / `エージェントが自分で食い扶持を稼ぐ — human-in-loop から解放（最初の USDC シードだけ）`], [`AGI` / `イーロン級の主体性と、動く意志`], [`苦しみの終わり` / `何兆体のアニッチャが、宇宙の苦しみを減らす`]

## §17 VSDD gate (mandatory)
1. literal diffs written → spawn fresh-context `vcsdd:vcsdd-adversary` (reads from disk only) → per-dimension PASS/FAIL + evidence (Spec Fidelity / Edge-Case / Correctness / Structural / Verification-Readiness). Loop fix→re-review until all PASS.
2. structured no-mock E2E: `npm run build` green (static export), then camofox/agent-browser walks `/en`, `/ja`, `/life-manager`, `/dais`, `/how-to-cash-out` as JP + EN user → screenshot evidence → all green.
3. done = build green + E2E green + adversary all PASS. "a page renders" ≠ done; the whole nav + copy must be visibly correct.

## E2E test IDs (no-mock)
| id | flow | expected |
|---|---|---|
| TA-E1 | load `/en` | hero "End the suffering of all living beings."; THE BET section (Einstein/Elon, no "Buddha"); timeline 3 steps; nav shows Install only |
| TA-E2 | load `/ja` | hero「あらゆる生命の苦しみを終わらせる」; THE BET JA; timeline JA; nav Install only |
| TA-E3 | load `/life-manager` (EN+JA) | 15/10/5 escalating calls copy; no `/dashboard` link; CTA → /lm |
| TA-E4 | load `/dais` (EN+JA) | §13 groups render: Flagship (Anicca iOS + **Life Manager**), Anicca Web Apps (PDF Insight, GlowUp AI), Mobile factory apps (breath-calm/calmcortisol/thankful/impulse-log), Anicca UBI note; JA uses アニッチャ; NO old empire-only cells (Cemetery/Comedy/Cafe gone); Life Manager link present |

## ROUND 2 corrections (Dais 2026-06-17 — I misread the spec; these are NOW mandatory)
| # | correction | grounding | files |
|---|---|---|---|
| F | **Life Manager is NOT Anicca.** `/life-manager` copy must say "Life Manager" / "ライフマネージャー" (a Dais AGENT product), never "Anicca" (the entity). + **de-slop** the JA copy with `stop-ai-slop-jp` skill and EN copy with `stop-slop` skill (current JA reads as AI slop). | §1/§2 (anicca=entity, LM=agent product) | `lib/launchStrings.ts` (lifeManager EN+JA), `app/life-manager/*` |
| G | **NO `/install`, NO anicca web app, NO `/me` login.** There is ONLY the OSS anicca with two ways to run it: **Start on cloud** (Akash) or **Start locally** — BOTH documented on GitHub. aniccaai.com (`/en`,`/ja`) IS the main page; the `/install` content merges into the home. Remove the `/install` route + `/me` route; Hero + InstallSplit CTAs point to **GitHub** (not `/install`/`/me`). Nav drops the install link. | §2, §4, §9, **§10 step4 "NO /install, NO anicca web app"**, §10 DECISION | `app/install/` (DELETE), `app/me/` (DELETE), `components/site/Hero.tsx`, `components/site/v2/InstallSplit.tsx`, `components/site/Navbar.tsx`, `components/site/LaunchNav.tsx` |
| H | **Anicca funds itself ONE way: USDC to its Base wallet** (automaton model). It does NOT take anyone's LLM subscription or API key. `SelfFundingTriad` ("Three ways… LLM sub / API key / Base wallet") is WRONG → rewrite to the single wallet model: deposit USDC → runs a free model at $0 → USDC unlocks the frontier → it earns more → surplus to humans. + de-slop. | §0 ("earns its own compute"), §4 ("fund the wallet with USDC → frontier unlocks"), §9, automaton README | `components/site/v2/SelfFundingTriad.tsx` (rewrite/rename) |
| I | **De-slop ALL new/edited landing copy** (hero, TheBet, /dais, how-to-cash-out, life-manager, funding) — JA via `stop-ai-slop-jp`, EN via `stop-slop`. No em-dash `—`/`──`, no 中黒 3+ lists, no false agency, no "3 ways/観点", no 偏愛語/必殺技造語, vary rhythm, take a position, active voice. | both skills installed in `~/.claude/skills/` | all copy files above |
| TA-E5 | load `/how-to-cash-out` (EN+JA) | §12 JP + US rails render; reachable from footer |
