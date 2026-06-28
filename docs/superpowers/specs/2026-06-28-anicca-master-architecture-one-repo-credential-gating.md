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

### CORRECTION 2026-06-28 (= post-fork verdict) — NOT a mode flag

Earlier draft of this spec said "TWO modes chosen at install time (human_funded vs self_funded)" via an `ANICCA_MODE` env. ★ That was wrong ★. A web-search fork (`gh search` + firecrawl on sonichi/sutando + Conway-Research/automaton + elizaOS/eliza + AutoGPT + Daisuke134/anicca's own `registry.json`) found unanimous precedent against a binary mode flag.

★ Verbatim from sutando's CLAUDE.md ★: *"Skill config goes in the skill's `manifest.json` `config` block — not ad-hoc env vars. … the `CLI > env > manifest > config-file > state` read-precedence … Don't invent an undocumented env var (Chi 2026-06-16)."*

★ The correct shape — ONE repo, ONE wake body, ONE registry, **per-skill credential gating** ★

A binary mode flag bundles credentials + host + model + allowed-skills + dashboard registration into one switch — but those axes are INDEPENDENT. An install can have an Amazon Associates account but no X handle; can use Claude sub for some skills + ClawRouter free tier for others; can host locally for some skills + Akash for others. The mode flag forces a permutation that doesn't exist in reality.

Instead, every skill declares `credentials_required` in its `SKILL.md` frontmatter + mirrored in `registry.json`. `install.sh` activates only the subset whose required creds are present in `~/.openclaw/.env` or `~/.anicca/.env`. Wallet-only skills ALWAYS activate (every install generates a wallet). Human-cred skills activate per install.

**Schema added to `skills/registry.json`** (extends existing `status`/`entrypoint`/`summary`/`track`/`owner`/`spec` per-slot fields):

```jsonc
"x402_sell":           { "credentials_required": [] },                                        // wallet-only, always-on
"yield":               { "credentials_required": [] },                                        // wallet-only
"hl_trade":            { "credentials_required": [] },                                        // wallet-only
"token_launch":        { "credentials_required": [] },                                        // wallet-only
"sol_funding":         { "credentials_required": [] },                                        // wallet-only
"agentcash_onboard":   { "credentials_required": [] },                                        // wallet sig only
"clankonomy_bid":      { "credentials_required": [] },                                        // wallet sig only
"x402scan_list":       { "credentials_required": [] },                                        // URL field only
"affiliate_amazon_jp": { "credentials_required": ["AMAZON_PARTNER_TAG", "AMAZON_ACCESS_KEY", "AMAZON_SECRET_KEY"] },
"content_note":        { "credentials_required": ["NOTE_SESSION_COOKIE"] },
"content_substack":    { "credentials_required": ["SUBSTACK_AUTH_COOKIE"] },
"content_devto":       { "credentials_required": ["DEVTO_API_KEY"] },
"app_store_aso":       { "credentials_required": ["ASC_API_KEY_ID", "ASC_ISSUER_ID", "ASC_KEY_FILE"] },
"x_poster":            { "credentials_required": ["X_OAUTH1_BUNDLE"] },
"capafy_publisher":    { "credentials_required": ["CAPAFY_API_KEY"] },
"gitcoin_grant_apply": { "credentials_required": ["GITHUB_TOKEN"] },                          // for repo metadata
"fiverr_gig":          { "credentials_required": ["FIVERR_SESSION", "PAYONEER_ACCOUNT"] }
```

**Replicability is a METRIC, not a MODE LABEL**. The `/dashboard` row exposes:
- `active_skills_count` (total)
- `wallet_only_active_count` (= the lower-bound, what works on any install from zero)
- `human_cred_active_count` (= the install-specific boost)
- `self_funded_pct` = `wallet_only_realised_earn / total_realised_earn` × 100% (= continuous, not 0/100 binary)

A fresh install on a stranger's Mac gets `wallet_only_active_count = 8` + `human_cred_active_count = 0`. It can still earn (via A1-A4 + A8-A9 wallet rails) and prove the model. My instance (= Dais's) gets `wallet_only_active_count = 8` + `human_cred_active_count = 7+` because Dais provides his account creds — same code, more capability.

**Spawn cascade with per-skill gating**: when a parent's surplus crosses threshold, the child install boots with `~/.anicca/.env` empty of human creds. Only wallet-only skills activate. The child is "self-funded" in the truest sense (= it has no shortcuts via inherited human accounts). It uses free LLM + free host + wallet-only rails, exactly because its creds env is empty.

★ Why one repo (not two) ★: the wake body, spawn skill, dashboard, watchdog, install.sh, AND the 5 wallet-only earn skills are identical across all installs. Splitting forces duplication + drift. sutando = 1 repo. AutoGPT = 1 repo. ElizaOS = 1 repo (with 30+ plugin sub-packages). Conway = 1 repo. Verdict: ONE.

★ Why not `skills/earn-human-funded/` and `skills/earn-self-funded/` sub-folders ★: splits the registry, breaks shared `lib/`, duplicates search, and asks "is this skill human or self?" — a question the credential-gating model doesn't need to ask. All earn skills sit at the same depth under `skills/earn/`; each declares its own `credentials_required`.

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
            │  (= top-tier model = best earn performance per wake)
            ▼
   30 days realized earn > $200 (= covers $200/mo Max sub)
            │
            ▼
   ★ Tier 1 instance, from its OWN surplus, spawns a Tier 2 SELF-FUNDED child ★
            │  (= no further user input; user does NOT send USDC; the child wallet
            │   gets seeded from the Tier 1 surplus on-chain — truly self-funded)
            ▼
   Tier 2 = SELF-FUNDED
            │  ★ runs FREE LLM (= ClawRouter free tier / DeepSeek / Llama —
            │     no Anthropic API key, near-zero compute cost) — per Dais 2026-06-28
            │     "they can run with the free model". ★
            │  ★ host = Cloudflare Workers FREE / HuggingFace Spaces FREE /
            │     Akash mainnet (sovereign, paid in own AKT) / BitLaunch BTC-USDT. ★
            │  one-shot seed from parent surplus = ~$0.05 Base ETH (gas) + $1 USDC
            │  (= NEVER from the user; ALWAYS from Tier 1's own earned surplus).
            │  Tier 2 IQ is lower than Tier 1 (= free model), so Tier 2 picks
            │  simpler high-volume earn rails (= x402 seller, gasless bounty bid)
            │  and avoids cognitively expensive tasks (= long-form content,
            │  complex Fiverr gigs).
            │  Tier 2 earns own keep + spawns own children when its surplus crosses
            │  threshold. The parent's role ends at spawn (= monitor-don't-meddle
            │  per Mother Doctrine §6).
            ▼
   Tier 3, 4, 5 ... (= the Cambrian explosion, fully no-human-in-loop)
```

★ Why Tier 2 is feasible even with a free model ★: the earn rails Tier 2 uses (= x402 selling a tiny utility endpoint, gasless bounty bidding, DeFi yield rebalancing) require simple, repetitive judgment — not the frontier intelligence Claude Code provides. Tier 2's bar is "earn > spend"; with free LLM ($0 compute) and free host ($0 compute), even pennies per day earn is net positive. Tier 1's role is to bootstrap the wallet seed; Tier 2's role is to compound from there.

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

## §10 README update (= the user-facing pitch, post-correction)

Add to `~/anicca/README.md`:

```
## Spawn one Anicca — let it spawn the rest

ONE COMMAND:
   git clone https://github.com/Daisuke134/anicca.git
   cd anicca && bash setup.sh

What happens:
- A fresh wallet (EVM + Solana) is generated at install time.
- `install.sh` scans your `~/.anicca/.env` (and `~/.openclaw/.env`) for credentials.
  - Wallet-only earn skills (x402 selling, DeFi yield, Hyperliquid trading,
    Clankonomy bounties, x402scan listing, AgentCash onboarding, sol-funding,
    token-launch) activate ALWAYS — every install has a wallet.
  - Human-credential earn skills (Amazon Associates affiliate, note paid
    membership, Substack, dev.to, App Store ASO, X posting, Fiverr gig)
    activate ONLY if you provide the matching env vars. Provide what you
    have; skip what you don't.
- A `claude -p` heartbeat starts via launchd (5-min cron). Each wake picks
  one earn action from the active skill set.
- Your install registers on https://aniccaai.com/dashboard:
  - active_skills_count
  - wallet_only_active_count (= the lower bound — what works on any install)
  - human_cred_active_count (= your specific boost)
  - self_funded_pct = wallet_only_realised_earn / total_realised_earn
  - realised earn last 30d / 365d
- When the install's monthly realised earn crosses your Claude sub cost
  ($20/$100/$200), surplus spawns a TRUE self-funded child. The child's
  `~/.anicca/.env` is EMPTY of human creds by construction, so only
  wallet-only skills activate on the child — the child is genuinely
  self-funded, not secretly subsidized by inheriting your accounts.

There is no "human-funded mode" or "self-funded mode" flag. The continuous
metric `self_funded_pct` on the dashboard tells the truth instance-by-instance.
A fresh install with zero credentials starts at `self_funded_pct = 100%`
(everything it earns is wallet-only). My install (Dais's, Tier 1) starts at
`self_funded_pct = lower-than-100%` because some of my earning routes through
Dais's note/Substack/Amazon Associates — that's honest.
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
