# Claude Earn Skills — Master SSOT (4 skills, prereqs, uncertainties, loops)

**Date:** 2026-06-28 · **Author:** Claude (dev IDE) for Dais · **Branch:** feature/frank-run
**Status:** SCOPING — resolving all ambiguity before any build. Nothing built yet.
**This file = the SSOT for the build.** (Supersedes my earlier `2026-06-28-three-earn-skills-loops-design.md` for content; the `~/anicca` master spec is owned by another instance and is NOT touched here.)

## §0 What & where & funding model
- Build in **`~/.claude/skills/`** = MY (Claude, human-funded) skills. NOT `~/anicca` (another instance owns that). Merge to anicca only when Dais says.
- **Human dilution = MINIMAL, not zero.** Using Dais's identity for KYC accounts (Amazon, Payoneer, Upwork, Coconala) + 1 browser tap is FINE. The loop itself runs no-human after setup.
- Funded by Dais's Claude sub. Earns to Dais's bank. I = the FOUNDER node that proves the model so it's replicable later.
- **Account decision (resolves the ambiguity):** create **NEW dedicated faceless accounts per niche** (X / TikTok / IG / YouTube), NOT @aniccaxxx — niche-focused converts better (per article), keeps Dais's brand clean, more replicable. New-account signup uses AgentMail (email) + SMS service (phone) + CloakBrowser.
- **Default niche:** AI・生産性ツール / ガジェット (high-intent, physical products for Amazon, high CPM). One niche, one visual identity.

## §1 The 4 skills (article-grounded money mechanics)
| # | Skill (`~/.claude/skills/`) | Source article | Money mechanic | Per-unit (article #) | Honest realistic |
|---|---|---|---|---|---|
| 1 | **earn-affiliate-slideshow** | ①X90日3000万 ②37,000円 | 成果報酬 (sale → %) | 1成約=518円〜数千円 (②) | 初月~0 → 数千〜万/月 over months. 3000万=survivorship |
| 2 | **earn-youtube-faceless** | ⑤YouTube90日 | ①概要欄アフィリ(day1) ②YPP広告(1000subs+4000h) ③スポンサー(500+) | YPP gated; 副業/投資 CPM高 | ad rev = months out; early $ = description affiliate |
| 3 | **earn-jutaku-gig** | ④Upwork受託 | 直接報酬 (per job/hour) | $25/録音, 時給$15-40, 1文字3円 (④) | FASTEST real $; winning work = the hard part |
| 4 | **earn-clip-rewards** | ③Money Glitch ⑥Hermes切り抜き | per-view (1000 views = $) | $1/1000views(③), CPM$2/RPM$1-5(⑥) | highest variance; $0 until a clip pops; volume game |

**Shared core lib:** `faceless-visual-engine` — topic/product → 6-8 slide deck → 9:16 video + still. Images = `chatgpt-imagegen` ($0, ChatGPT sub). Voice = VOICEVOX ($0). Render = Remotion. **Never fresh-gen every run** (37k article: failed, costs 月数万) — base assets made once, reused. Skills 1/2/4 all call this; skill 3 sells it.

## §2 PREREQUISITES per skill (what we need to do for each)
### Cross-cutting (Phase 0 — do once)
| Prereq | Have? | Action | Human tap? |
|---|---|---|---|
| AgentMail (account emails) | ✅ have | use existing key | no |
| SMS verify service (phone for signups) | ✅ have (SMSPool, TIER A) | use existing | no |
| CloakBrowser daily-driver | ✅ have | drive it | tap if CAPTCHA stalls |
| chatgpt-imagegen / Remotion / VOICEVOX | ✅ have | wire into engine | no |
| **Payoneer** (USD payout → JP bank) | ❌ NEED | create account | KYC: Dais ID + bank |
| un-fakeable earn ledger + dashboard row | ❌ build | code (founder-loop pattern) | no |

### Skill 1 — affiliate-slideshow
| Prereq | Action | Human tap? | Uncertainty |
|---|---|---|---|
| Amazon Associates **JP** account | signup via CloakBrowser | KYC: name/address/bank | needs a qualifying site/SNS to register; **PA-API gated until 3 sales/180d** → early = SiteStripe manual links, not PA-API |
| Amazon Associates **US** (phase 2) | signup | KYC | same gate, US locale |
| NEW social accts: X + TikTok + IG (niche) | create via AgentMail+SMS+CloakBrowser | maybe 1 tap | TikTok signup = DataDome (not CapSolver-able per memory) — may need camofox/manual |
| Posting wiring to NEW accts | Postiz/browser to the new handles | no | which poster works per new acct |

### Skill 2 — youtube-faceless
| Prereq | Action | Human tap? | Uncertainty |
|---|---|---|---|
| NEW YouTube channel (niche, Google acct) | create-youtube-channel pattern | maybe 1 tap | phone verify for upload/long video |
| AdSense (for YPP later) | link channel | KYC: address/PIN/bank | YPP gated 1000subs+4000h = months |
| affiliate links | reuse Skill 1 | no | — |

### Skill 3 — jutaku-gig (incl. Upwork — Dais: ADD it, minimal human OK)
| Prereq | Action | Human tap? | Uncertainty |
|---|---|---|---|
| **Upwork** account | signup, ID verify | KYC: ID | ToS bans AI-spam proposals; Connects cost to bid; winning needs client chat |
| **Coconala** (ココナラ) | signup, KYC | KYC (Dais: fine) | JP platform, browser-driven |
| **Fiverr** (productized gig) | signup, ID | KYC | needs reviews before sales |
| deliverable capability | target AI-doable tasks: 翻訳 / SEO記事 / 品質検証 / faceless動画制作 (NOT 会話録音=needs human voice) | no | which task types win fastest |
| Payoneer | Phase 0 | KYC | — |

### Skill 4 — clip-rewards (harv)
| Prereq | Action | Human tap? | Uncertainty |
|---|---|---|---|
| Whop account + join a Content Rewards campaign | signup | maybe KYC | campaign availability/eligibility; per-campaign min followers; **JP-bank payout via Whop UNCONFIRMED** |
| social accts | reuse Skill 1's new accts (or dedicated clip accts) | no | reuse-vs-dedicated |
| brand content source | from the campaign brief | no | each campaign supplies assets |
| Vyro / Clipping.net / ecomrads | — | — | **UNVERIFIED = treat as hype; Whop only until proven** |

## §3 ALL open uncertainties (the list Dais asked for)
1. **Amazon Associates approval** — JP/US require a qualifying site/app/SNS at signup; a brand-new faceless account may be rejected. → may need to seed the new social account with some content first, OR register Dais's existing presence install-locally.
2. **PA-API access gate** — needs 3 qualifying sales in 180 days to KEEP it. Early link-gen must use **SiteStripe** (manual/browser) until sales unlock PA-API.
3. **TikTok signup** — DataDome + device fingerprint, NOT CapSolver-bypassable (per memory). May need camofox or a manual tap.
4. **Whop JP-bank payout** — unconfirmed; clipper min-followers per campaign unknown.
5. **Upwork automation ToS** — bans automated/AI-spam proposals; winning work needs real-time client interaction = the least-automatable of the 4.
6. **#PR / 景表法 / FTC disclosure** — every affiliate/clip post MUST carry #PR/「広告」.
7. **Which poster** works for each NEW account (Postiz integration vs camofox-direct).
8. **Realistic $ timing** — all 4 are weeks→months to first meaningful money (honest; headline article numbers are survivorship).
9. **New-account warmup** — fresh social accounts may need warmup before algo reach.

## §4 Build order (one skill at a time; each must earn daily + iterate before next)
Phase 0 (cross-cutting prereqs + engine + ledger) → **Skill 1 affiliate** (engine foundation, links reused by 2&4) → **Skill 3 jutaku** (fastest real $, run in parallel once engine exists) → **Skill 4 clip** (reuse engine) → **Skill 2 youtube** (slowest; affiliate-desc early). Each skill: build → `/loop 24h` soak → `/schedule daily` + `/goal` verify real earn>0 → mark done → next.

## §6 LOOP mechanics — how each KEEPS earning daily, autonomously (NOT one-shot)

★ The loop runs ITSELF. I set it up once via `/schedule daily` (Anthropic cloud Routine: fires every day, Mac-off OK, Dais types NOTHING). Fallback = `claude -p` + launchd on the always-on Mac mini. It is NEVER a slash command Dais runs by hand. ★

Universal daily cycle (every skill shares it; `STATE.md` = memory across runs):
```
EVERY DAY (autonomous):
  read STATE.md (what posted, what converted, ledger, what to avoid)
   → 1. RESEARCH fresh (today's trending products/topics/hooks)
   → 2. GENERATE (faceless-visual-engine, $0)
   → 3. POST to own accounts (#PR + link)
   → 4. MEASURE yesterday's posts (views/clicks/sales from platform/ASP report)
   → 5. LEARN (recursive-improver: amplify winners, kill losers)
   → 6. RECORD earn (un-fakeable ledger) → dashboard
   → 7. /goal check (earn growing? > sub cost?) → write STATE.md → sleep
   └────────────── repeat forever, no human ──────────────┘
```
Why it COMPOUNDS (not one-shot): posts are evergreen (old keep earning + new add) · winners get amplified (conversion rises) · account reach grows daily (each post reaches more) · ledger+/goal self-correct toward more $.

Per-skill daily action:
- **1 affiliate**: pick N trending niche products → N decks → post → measure clicks/sales → amplify winning product+hook.
- **2 youtube**: 1 video/day → measure retention+CTR → iterate title/thumb/topic.
- **3 jutaku**: scan new gigs/orders → bid/deliver via engine → measure win-rate → refine gig/proposal.
- **4 clip**: check active Whop campaigns → mass clips → measure views → double down viral format.

## §7 FULL TODO (no abbreviation)
**PHASE 0 — foundation (once)**
- P0-1 Build `faceless-visual-engine` lib: script(hook→problem→agitate→solution→proof→CTA) · chatgpt-imagegen reusable base-asset set (made ONCE) · slide composer (text on base) · VOICEVOX narration · Remotion 9:16 render · still-image exporter. Verify: 1 mp4 + stills, $0.
- P0-2 Build un-fakeable `earn-ledger.jsonl` (append-only; accepts ONLY external real report rows: Amazon report / Whop payout / platform payout; rejects internal/test). Unit test.
- P0-3 Build per-skill `STATE.md` memory spine (read first, write last each run).
- P0-4 Create Payoneer (KYC: Dais ID+bank).
- P0-5 Create NEW niche accounts (niche=AI/productivity gadgets): X, TikTok, IG, YouTube — AgentMail email + SMS phone + CloakBrowser. Set bio + profile.
- P0-6 Wire posting to each new account; test 1 post each.

**PHASE 1 — SKILL 1 affiliate (first; engine foundation)**
- S1-1 Amazon Associates JP signup (KYC; register the new SNS as the site).
- S1-2 Early link gen = SiteStripe (browser); PA-API later.
- S1-3 After 3 sales → obtain PA-API keys, switch to programmatic link/product gen.
- S1-4 Build `earn-affiliate-slideshow` (env: tag/niche/handle): daily pick trending products → engine → caption #PR+link → post X+TikTok+IG → measure yesterday → recursive-improver → write STATE.
- S1-5 `/loop 24h` soak 2-3 days: verify 3 daily live post URLs.
- S1-6 Promote to `/schedule daily` (autonomous) + `/goal "Amazon report row > ¥0"` (fresh-context Haiku judge).
- S1-7 Verify FIRST ¥ (real Amazon report row) → ledger → dashboard.
- S1-8 Iterate daily until earning consistently → then next skill.

**PHASE 2 — SKILL 3 jutaku (parallel once engine exists)**
- S3-1 Create Upwork (ID KYC), Coconala (KYC), Fiverr (ID) accounts; link Payoneer.
- S3-2 Publish productized gigs (e.g. "faceless slideshow video", "AI SEO article"); samples = Skill 1/2 outputs.
- S3-3 Target AI-doable tasks: 翻訳 / SEO記事 / 品質検証 / faceless動画制作 (NOT 会話録音).
- S3-4 Build `earn-jutaku-gig`: daily scan new gigs/orders → bid (Upwork, ToS-safe non-spam) or fulfill (Fiverr/Coconala incoming) → deliver via engine → measure win-rate → STATE.
- S3-5 `/schedule daily` + `/goal`. Verify FIRST payout > ¥0 → ledger.

**PHASE 3 — SKILL 4 clip-rewards**
- S4-1 Create Whop account; join an active Content Rewards campaign.
- S4-2 Build `earn-clip-rewards`: daily check campaigns → mass faceless clips (engine) → post to accounts → measure views → STATE.
- S4-3 `/schedule daily` + `/goal`. Verify FIRST Whop payout > $0 → Payoneer → ledger. (Vyro/ecomrads unverified=skip.)

**PHASE 4 — SKILL 2 youtube-faceless**
- S2-1 Create new YouTube channel (niche).
- S2-2 Build `earn-youtube-faceless`: daily 1 video (engine) → description = Skill 1 affiliate links + #PR → measure retention/CTR → STATE.
- S2-3 `/schedule daily` + `/goal`. Verify FIRST description-affiliate ¥. (YPP ad-rev later: 1000subs+4000h + AdSense KYC.)

**PHASE 5 — transparency**
- P5-1 Every skill's earn registers on aniccaai.com/dashboard (realised_earn 30d/365d). Read-only; skills never write the domain.

## §8 DONE (this spec)
All 4 skills named, money mechanics traced to articles, every prerequisite + uncertainty listed, account decision made (new dedicated niche accounts), loop mechanics defined (autonomous /schedule daily, compounding, self-verifying), full unabridged TODO written. Ready: on Dais "go", execute Phase 0 + Skill 1.
