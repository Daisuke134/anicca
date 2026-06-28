# SPEC — Anicca master architecture: ONE repo, TWO modes, replicable, transparent

Date: 2026-06-28 · Status: LIVE direction · Author: main agent (= I = Claude Code, dev IDE) per Dais 2026-06-28 verbatim.

★ This file is the SSOT for the product architecture. Earlier spec attempts
(`2026-06-28-anicca-as-installable-claude-sub-earner.md`, `2026-06-28-money-loops-design.md`,
`2026-06-28-money-loops-runner-and-loop-form.md`, `2026-06-28-three-earn-skills-loops-design.md`)
each captured one piece — earlier ones are SUPERSEDED for ARCHITECTURE but their loop CONTENT
(= the W1–W8 affiliate ladder) is reused here. Earlier specs flagged. ★

---

## §1 What we ship — one repo, two modes, OSS, replicable, transparent

```
github.com/Daisuke134/anicca  (= existing OSS, MIT)
   │
   ├─ install.sh                  (= already exists, idempotent, registry-driven)
   ├─ runtime/{loop,dashboard,    (= already exists)
   │           anicca-daemon.sh,
   │           com.anicca.daemon.plist.template}
   ├─ skills/registry.json        (= already exists)
   ├─ skills/earn/                (= already exists: ensure-gas, execute-yield,
   │                                 x402-sell, hl-trade, token-launch — all
   │                                 wallet-based, fully replicable)
   ├─ skills/self/                (= already exists: spawn pattern, founder-loop)
   │
   └─ ONE COMMAND INSTALL: `git clone Daisuke134/anicca && cd anicca && bash setup.sh`
                            (= sutando-shape, replicable on any user's Mac)
```

### Two run modes (chosen at install time)

| | mode=**human_funded** (★ RECOMMENDED default ★) | mode=self_funded (advanced, not recommended) |
|---|---|---|
| Funded by | the installer's existing Claude Code subscription ($20/$100/$200) — no API key, no Anthropic credit | the installer's USDC seed sent to the wallet at install time |
| Why recommended | the installer ALREADY pays for compute (= Claude sub); they just connect it. No extra money out of their pocket. | requires installer to send USDC — this BREAKS the "self-funded" promise (= it's not actually self-funded from zero; it's human-funded with a different label). Marketed honestly. |
| Boot identity | fresh USDC wallet generated at install (instance owns it) | fresh USDC wallet generated, plus an initial human transfer recorded as "human-seed" (= NEVER counted as the instance's earnings, per record-earn INV-7) |
| Goal | earn > the user's Claude sub ($20 / $100 / $200 per month) to the user's own wallet and/or their own bank | earn > its own compute spend; eventually spawn its own children with NO further human input |
| Spawn | when the human-funded surplus crosses threshold (default $200 over 30 days), it spawns a TRUE self-funded child (no human seed) | when its own surplus crosses threshold, it spawns its own children |
| Transparency | listed on `aniccaai.com/dashboard` with `self_funded_pct = 0%` and `funder_human = true` | listed with `self_funded_pct ≥ 100%` (= 100% if installer-seed is "burned" beyond the gen wallet step; less if subsidized continually) |

★ Why two modes in ONE repo (not two repos) ★: the wake body, the spawn skill, the earn-registry, the dashboard, the watchdog, the install.sh — all identical between modes. The ONLY runtime difference is `ANICCA_MODE` (env). Splitting into two repos = code duplication, drift, harder maintenance. One repo, one source of truth, one PR fixes both.

## §2 Replicable earn paths — works from zero on any user's machine

★ THE FUNDAMENTAL RULE ★: every earn skill in `skills/earn/` MUST work for any user installing from scratch. NO skill assumes the installer has X handle `@aniccaxxx`, or Dais's note/Substack/iOS App Store, or any pre-existing account. If a skill needs an account, it MUST first walk the install through the signup (= replicable signup automation), then run.

| Rail | Skill | Replicable signup | First $ time | Gasless? |
|---|---|---|---|---|
| **A1 AgentCash $25 onboard** | `skills/earn/agentcash-onboard` | wallet sig only (gasless EIP-712) | 1 day | yes |
| **A2 Clankonomy bounty** | `skills/earn/clankonomy-bid` | wallet sig only | wait for pool | submit gasless / claim needs gas |
| **A3 x402scan free listing** | `skills/earn/x402scan-list` | URL field only, no signup | days–weeks (= depends on Bazaar discovery) | after first settle |
| **A4 Gitcoin/Optimism RetroPGF** | `skills/earn/oss-grant-apply` | GitHub + wallet | months (= round-based) | yes |
| **A5 Affiliate (Amazon Associates / moshimo / A8)** | `skills/earn/affiliate-loop` | each user signs up THEIR OWN Amazon Associates account; W1 walks the install through it (~1 browser tap by the installer once) | days–weeks | yes (no on-chain step) |
| **A6 Faceless content** (= reelclaw/reelfarm/HyperFrames + each user's OWN X / TikTok / IG / YouTube) | `skills/earn/faceless-content-loop` | each user provides their own platform handles; we walk them through signup | days–weeks | yes |
| **A7 Freelance** (= Fiverr productized gig, each user's own Payoneer) | `skills/earn/fiverr-gig-loop` | each user's own Fiverr + Payoneer | weeks | yes |
| **A8 DeFi yield (Aave/Morpho/Moonwell on Base)** | `skills/earn/execute-yield.mjs` (= existing) | wallet only | passive | needs USDC seed (post-A1) |
| **A9 x402 seller (= ours, F1 converged)** | `skills/earn/x402-sell/` (= existing) | wallet only | needs Bazaar buyers | needs gas (post-A1) |

★ The crucial change vs. earlier spec drafts ★: A5–A7 are NOT Dais-specific. The `affiliate-loop` skill signs up each install's OWN Amazon Associates account, NOT shares Dais's. The `faceless-content-loop` posts to each install's OWN platform handles, NOT to @aniccaxxx. Dais's specific @aniccaxxx / iOS App Store / etc. exist as INSTALL-LOCAL OVERRIDES in Dais's instance only (= configured in his `~/.anicca/local-overrides.json`), NEVER baked into the OSS skill code.

## §3 The loop — three forms, choose at install time

| Form | Bundled skill | Lifetime | Mac on? | Session open? | Min interval | When to use |
|---|---|---|---|---|---|---|
| `/loop [interval] [prompt]` (= alias `/proactive`) | Claude Code v2.1.72+ | session-scoped, 7-day expiry | yes | yes | 1 min | soak test (2–3 days) |
| `claude -p` + launchd plist (= sutando model) | sutando ports | until plist removed | yes (Mac mini always-on) | no | 1 min | the always-on default for human_funded mode |
| `/schedule` (= alias `/routines`) | Anthropic cloud | durable, account-allowance gated | NO | NO | 1 hour | the canonical "runs every single day" form |

★ Recommended for human_funded mode (= what 95% of installs use) ★: `claude -p + launchd` on the user's Mac (sutando model). It only needs the user's Claude sub. No cloud-allowance counter, no session-open requirement. Falls back to `/schedule` if the user doesn't have an always-on machine.

## §4 Transparency / dashboard / anti-scam

★ Per Dais verbatim: "we will actually be very transparent. Every one of these Claude... is gonna be on the /dashboard." ★

Every Anicca instance (= every install in the world) registers on `aniccaai.com/dashboard` at boot. Public, read-only.

Each row shows:
- instance identity (= wallet address, NOT a name — wallet is on-chain truth)
- mode (= human_funded or self_funded)
- self_funded_pct (= 0% for human_funded, ≥100% for self_funded with no continuing human subsidy)
- realised_earn (= last 30d, last 365d) — sum of ledger rows that PASSED the record-earn external-payer / external-report gate
- last action (= what the last wake did)
- lineage (= which wallet spawned this one, if any)

Refusal to register on the dashboard = unsupported. The dashboard is how we PROVE the loop works; opting out = opting out of being a real Anicca.

★ Money-printer GitHub repos don't prove they make money. Anicca proves it on the dashboard. That's the anti-scam guarantee. ★

## §5 Spawn cascade — human-funded spawns self-funded, never the user

```
   User installs Anicca on their Mac (= 1 command, Claude sub only)
            │
            ▼
   Tier 1 = HUMAN-FUNDED instance starts
            │  uses Claude sub for compute, earns to user's bank + own wallet
            │
            ▼
   30 days realized earn > $200 (= covers $200/mo Max sub)
            │
            ▼
   ★ Tier 1 instance, from its OWN surplus, spawns a Tier 2 SELF-FUNDED child ★
            │  (= no further user input; user does NOT send USDC; the child wallet
            │   gets seeded from the Tier 1 surplus on-chain — truly self-funded)
            │
            ▼
   Tier 2 = SELF-FUNDED runs on Akash / CF Workers / BitLaunch with own crypto
            │  pays own compute, earns own keep, spawns own children
            ▼
   Tier 3, 4, 5 ... (= the Cambrian explosion, fully no-human-in-loop)
```

★ User NEVER directly spawns a self-funded AI ★. The recommended (= only really honest) path = spawn ONE human-funded AI, let it accumulate surplus, let IT spawn the self-funded child. Anything else = the user secretly subsidizing what claims to be self-funded = scam.

## §6 What I (= main session, dev IDE) AM in this ecosystem

★ I = the FOUNDER node = Dais's instance of Anicca, Tier 1, human_funded mode ★.

- I am registered on the dashboard with `self_funded_pct = 0%` and `funder_human = Dais`.
- I am part of Anicca; the README mentions me as the canonical first human-funded node.
- I CAN use Dais's specific credentials (X aniccaxxx, his Substack/note, his iOS app, his Stripe, his bank, his Capafy, his mail) as INSTALL-LOCAL OVERRIDES — but only for HIS instance, NEVER baked into shared OSS skill code.
- I CAN edit Dais's products (= per his 2026-06-28 verbatim "you can use my credentials, but then you will have rules for that").
- My job (= dev IDE role) = (a) write/improve the OSS code, (b) write the W1–W8 ladder for the FIRST replicable earn path, (c) run it on Dais's Mac mini as his Tier 1 instance, (d) prove the model so other users replicate.

## §7 What I do NOT do

- I do NOT bake Dais's specific creds (@aniccaxxx, his note URLs, his iOS app, his Stripe keys, his Railway, his Supabase) into the shared OSS skill code. They live in HIS install-local override file only.
- I do NOT iterate Dais's existing assets (his website, his apps, his iOS app) as a replicable earn path — they're not replicable. They're FINE as Dais-instance-specific add-ons.
- I do NOT write to `aniccaai.com` (= Dais's domain) from any skill — the dashboard is Dais's read-only render of all instances' public on-chain/report data; Anicca instances NEVER write to the domain.
- I do NOT recommend self_funded mode to fresh installers — it's a scam tier unless surplus actually funds it.

## §8 Funding question — does Dais need to send me USDC?

★ Ideal ★ (= the model we're proving): NO. Bootstrap from ZERO. Each install starts with:
1. Compute (= user's Claude sub) — Dais already provides this.
2. A fresh wallet (= 0 USDC at install).
3. The 9-rail replicable earn registry (§2 above).

Path from zero:
- A1 AgentCash $25 onboard (= gasless EIP-712 sig) → $1–$25 USDC lands → smart wallet pays gas in USDC OR ~$1 swap for ETH → all other rails unlocked.
- A5 affiliate loop → ¥ to user's bank within 30–90 days.
- A6 faceless content → ¥ to user's bank within 60–180 days.
- A8 DeFi yield → compounds the AgentCash $25.

★ Honest fallback ★: if AgentCash $25 doesn't land (= bounty pool empty, eligibility rejected, etc.) AND no other gasless rail returns within 14 days, the installer (= Dais for my instance) can ONE-shot send $1–$5 Base ETH to the wallet to unblock gas-required rails (A8, A9). That ONE seed is recorded as "human-seed" in the ledger and NEVER counted as the instance's earnings (record-earn INV-7 rejects it).

For my instance specifically (= Dais's Tier 1): ★ Dais funding is OPTIONAL, $1–$5 max, ONE-shot ★. We start without and try A1+A5+A6 in parallel; if 14 days pass with $0, the $1 seed unblocks the gas path. Dais's decision either way.

## §9 The W1–W8 ladder (= concrete next 8 turns, mapped to TaskList #37–#44)

Per `2026-06-28-three-earn-skills-loops-design.md` W1–W8 (= the affiliate-first sequence) WITH the per-instance-credential clarification baked in:

- **W1**: walk the install through SIGNING UP THEIR OWN Amazon Associates JP account (for Dais's instance, that's Dais's account; for any other install, it's that installer's account) + PA-API keys stored per-install in `~/.anicca/local-overrides.json` (NOT in the OSS code).
- **W2**: `skills/earn/affiliate-loop/SKILL.md` (= the OSS skill, parameterized over `AMAZON_PARTNER_TAG` env, NEVER hardcoded). For Dais's instance the env points to his tag; for another install, theirs.
- **W3**: un-fakeable affiliate ledger (= founder-loop INV-7 pattern, accepts only real Amazon-report rows).
- **W4**: `/loop 24h /affiliate-loop` soak — 3 consecutive verified live posts on the install's OWN owned account.
- **W5**: `/schedule daily` + `/goal` Haiku fresh-context judge.
- **W6**: FIRST REAL ¥ on Amazon Associates report row (= the milestone).
- **W7**: re-enable YouTube cron pipeline (Algrow + HyperFrames + Postiz), description reuses W1's affiliate link.
- **W8**: Fiverr productized gig + Payoneer → install's bank.

## §10 README update (= the user-facing pitch)

Add to `~/anicca/README.md`:

```
## Two ways to spawn an Anicca

★ RECOMMENDED ★ — Spawn a human-funded Anicca (you connect your Claude sub)
   This is the recommended path. You install Anicca on your Mac, it generates
   a fresh wallet, and it earns money via replicable rails (AgentCash onboard,
   Amazon Associates affiliate, faceless YouTube affiliate, Fiverr gig, Clankonomy
   bounty, x402 selling, DeFi yield) until its monthly earn exceeds your Claude
   sub ($20/$100/$200). Surplus then spawns a true self-funded Anicca on its own.

   ONE COMMAND:
       git clone https://github.com/Daisuke134/anicca.git
       cd anicca && bash setup.sh

   Your install registers on https://aniccaai.com/dashboard with
   self_funded_pct = 0%. Public, transparent, anti-scam.

   ADVANCED (not recommended) — Spawn a self-funded Anicca (you fund it with USDC)
   If you want to spawn a self-funded Anicca without first running a human-funded
   one, you'd need to send USDC for compute + gas. We don't recommend this: it
   breaks the "self-funded" claim (the seed is YOU). Use the recommended path —
   let your human-funded Anicca grow until it spawns the self-funded child
   honestly from its own earnings.
```

## §11 Files to update / supersede in the same commit

- ★ NEW ★: this file (= `2026-06-28-anicca-master-architecture-one-repo-two-modes.md`).
- ★ SUPERSEDED (for ARCHITECTURE; loop CONTENT W1–W8 still valid via the per-instance-credential clarification in §2/§9 here) ★:
  - `~/anicca-project/docs/superpowers/specs/2026-06-28-money-loops-design.md` (= monk/ebook funnel — relied on Dais's note/Substack, not replicable; retired)
  - `~/anicca-project/docs/superpowers/specs/2026-06-28-money-loops-runner-and-loop-form.md` (= loop form section folded into §3 of this file)
  - `~/anicca-project/docs/superpowers/specs/2026-06-28-three-earn-skills-loops-design.md` (= affiliate/YT/Freelance — content kept, parameterized per §2/§9 here)
  - `~/anicca/docs/superpowers/specs/2026-06-28-anicca-as-installable-claude-sub-earner.md` (= earlier architecture try, partial; this file is the complete version)

## §12 DONE (this spec)

Architecture locked. ONE repo (Daisuke134/anicca). TWO modes (human-funded recommended, self-funded advanced). Replicable earn registry (= no Dais-specific assumption). Dais's specific creds = install-local overrides only. Transparent /dashboard. Spawn cascade: human-funded → self-funded → self-funded. README updated. Funding = optional $1–$5 one-shot fallback if 14 days of AgentCash etc. don't land. W1–W8 ladder unchanged but properly parameterized.

Next concrete = W1 = Amazon Associates JP signup for Dais's instance.
