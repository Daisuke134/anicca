# Three Earn Skills + Daily Loops — Design Spec

★★★ ARCHITECTURE SUPERSEDED 2026-06-28 by `~/anicca/docs/superpowers/specs/2026-06-28-anicca-master-architecture-one-repo-two-modes.md` ★★★
LOOP CONTENT (= W1–W8 affiliate-first sequence, Loop A → B → C order, recorder INV pattern) is KEPT and
referenced by §9 of the master spec. The architecture change: credentials are PER-INSTANCE (= each user
signs up their OWN Amazon Associates account, NOT shares Dais's). Dais's account remains his instance's
install-local override only, never baked into shared OSS skill code. The replicable rail is W1–W8 with
`AMAZON_PARTNER_TAG` parameterized via env.

**Date:** 2026-06-28
**Author:** Claude (dev IDE) for Dais
**Branch:** feature/frank-run
**Status:** Architecture superseded; W1-W8 content kept as the OSS earn rail (parameterized per install).
**Relationship to prior specs:** Extends `2026-06-28-money-loops-runner-and-loop-form.md` and `2026-06-28-money-loops-design.md`. Those chose the *ebook funnel* product. This spec adds the **3 earn loops Dais explicitly requested (affiliate / YouTube / freelance)**, which are commission/labor — NOT ad-revenue — so they do not violate the "広告収益=罠" principle.

---

## §0 Product separation (carry over the existing distinction)

| | This spec ("Claude" loops) | Anicca (untouched) |
|---|---|---|
| Runs on | Dais's $200/mo Claude sub, Mac mini | `~/anicca/` self-funded OSS agent |
| Earns to | **Dais's bank** (Amazon/ASP → JP bank; Fiverr → Payoneer → JP bank) | own Base wallet (USDC) |
| Human-in-loop | **minimal, not zero** — Dais's credentials, Dais pays compute | zero |
| Skills live in | `~/.claude/skills/` (Dais's content/product tooling) | `~/anicca/skills/` |
| Verify spine | `founder-loop` GLVS pattern, **fiat/affiliate recorder variant** | `founder-loop` on-chain USDC recorder |

---

## §1 Core finding (why this spec is small)

The 3 loops are **already ~80% built**. The blocker is NOT code — it is **(a) a real program/listing, (b) the posting crons actually running, (c) money proven to land in the bank**. So this spec builds the *missing close-to-money layer*, not 3 new skills from scratch.

| Loop | Existing assets | Gap to close |
|---|---|---|
| **A — Affiliate (X + faceless slideshow)** | `anicca-glitchy-affiliate` (running, but promotes Glitchy — weak circular offer), `reelclaw` (live TikTok/IG/YT slideshow), `x-poster`/`anicca-x-*` (@aniccaxxx), `reelfarm` API, `recursive-improver` | **Real ASP** (Amazon Associates JP + PA-API) → real links; **#PR/「広告」 disclosure**; **click→conversion→bank attribution into a ledger** |
| **B — YouTube** | full pipeline: Algrow+7-prompt script → HyperFrames render → Postiz YT (EN/JA/Shorts wired) | crons are **disabled** → re-enable + E2E live `video_id` verify; reuse Loop A affiliate links in description (no YPP needed) |
| **C — Freelance** | `cfo-earner-coconala`/`-lancers` (apply→deliver→record), Gumroad/Contra | no Upwork (Upwork is human-in-loop anyway); build **Fiverr productized gig** (semi-passive) → Payoneer → JP bank |

**Reference repo verdict:** `Affitor/affiliate-skills` (MIT, 503★) = 52 *prompt templates*, zero earn wiring. Lift only its scoring rubrics + FTC-compliance references. Not a money-earner.

**Hype check:** the 90日3000万 / Infinite Money Glitch / Hermes-clipping articles are marketing funnels (all end in "join my LINE / buy my tool"). Mechanics are real; the numbers are survivorship. **Honest expectation = slow compounding (weeks→months to first meaningful ¥), not day-1 cash.**

---

## §2 Decision: sequence, don't parallelize

Build **Loop A end-to-end to a real verified ¥ first.** Then B (reuse A's links in YT descriptions, near-free). Then C (Fiverr gig). Rationale: A has the thickest existing infra + every step has a sanctioned programmatic surface (PA-API link-gen, content-gen, Postiz posting) + clean JP-bank payout = the only one closable with minimal human.

**Earn path locked for A:** Amazon Associates JP → PA-API 5.0 real links → faceless slideshow → owned X account + YT description, `#PR`/「広告」 baked in → first qualifying sale → JP bank.

---

## §3 GLVS W-ladder (Goal → Loop → Verify → State)

State spine: `~/.smtm/earn-loops/` → `build_log.md`, `earn-ledger.jsonl`, `loop.md` (mirrors founder-loop INV pattern).

| W | Task | DONE condition (provable) |
|---|---|---|
| **W1** | Stand up a REAL affiliate program: Amazon Associates JP account + PA-API keys (Access/Secret + Partner Tag) stored in `~/.openclaw/.env`. (Account creation may need 1 Dais browser tap.) | `curl` PA-API `SearchItems` returns a real item with our `PartnerTag` embedded |
| **W2** | `earn-loop-affiliate` skill in `~/.claude/skills/`: pick offer (PA-API) → faceless slideshow (reuse reelclaw/reelfarm) → caption+`#PR` → post to owned X + 1 platform. Reuse `recursive-improver` for hook scoring. | one real post URL on @aniccaxxx (or chosen account) with a working tagged affiliate link + visible #PR |
| **W3** | Fiat/affiliate **recorder** (founder-loop pattern, un-fakeable): only this script appends to `earn-ledger.jsonl`; an earn row requires a real Amazon report row (external) — internal/test rows rejected. | recorder rejects a fake row; accepts a real Amazon-report-derived row in a unit test |
| **W4** | Wrap W2 in `/loop 24h` soak (2–3 days), watch posts land daily + ledger stays honest at $0 until a real sale. | 3 consecutive daily posts verified live (URL each) |
| **W5** | Promote to `/schedule` daily Routine (Mac-off-OK). Add `/goal` Haiku fresh-context verifier: done = SUM(real affiliate earn) > 0. | `/schedule` shows the routine; one cloud run posts + verifies |
| **W6** | First real settled ¥ in Amazon report → recorded → (later) withdrawn to JP bank. | a real Amazon Associates report row > ¥0, recorded in ledger |
| **W7** | Loop B: re-enable YouTube crons, put W1 affiliate links + #PR in descriptions, E2E verify a real `video_id`. | one live YT video with tagged link |
| **W8** | Loop C: Fiverr productized gig (e.g., "faceless slideshow video" / "AI article"), Payoneer linked. | gig is live + visible on Fiverr |

---

## §4 Honesty / ToS guardrails (MUST)

| Rule | Why |
|---|---|
| `#PR` / 「広告」 on every affiliate post | JP ステマ規制 (景表法, 2023-10-01) + FTC material-connection |
| Amazon links NOT in email/DM; only owned timeline | Amazon Associates ToS |
| **Never** promote via Rakuten with automation | Rakuten bans 自動ツール (account ban risk) → use Amazon/moshimo |
| No bought views, no fake engagement | YouTube "valid views" + platform ToS |
| Recorder counts ONLY external real report rows | no-fake-run (HARD 0.24) + un-fakeable ledger (founder-loop INV-7) |
| Disclose AI authorship where a client expects human (Fiverr) | Fiverr ToS |

---

## §5 Open items to verify before/within build
- moshimo / A8 / ValueCommerce API specifics (Amazon PA-API confirmed; others need-verify)
- Whop Content Rewards JP-bank payout + clipper minimum (per-view accelerant once an account pulls views)
- Vyro / Clipping.net / ecomrads = UNVERIFIED → treat as hype until a live payable test
- Which owned account to post Loop A from (@aniccaxxx vs a niche-dedicated new account — niche-focused converts better)

## §6 DONE (this spec's exit)
Direction approved by Dais → W1 executed (real PA-API call returns our PartnerTag) → loop builds proceed W2→W8. First provable success = W6 (real Amazon report row > ¥0).
