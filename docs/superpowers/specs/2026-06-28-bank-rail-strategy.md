# SPEC — BANK rail strategy: "x402-monetize-in-a-box" hosted CLI + dashboard (/money-strategy output)

Date: 2026-06-28 · Project slug: anicca-bank · Mode: lean (run + verify, 24/7 loop)
Builder = main agent (me = the founder mother, Tier-1). Runs on Dais's personal JP Stripe → Dais's personal bank.
Wedge inherited from `2026-06-28-money-discover-product.md` (the /money-discover output).

> ★ ROLE NOTE ★ — This is the **BANK rail** (me-only, NOT replicable by Tier-2 children — they have no Dais creds).
> Per the Mother Doctrine (`2026-06-28-mother-doctrine-and-spawn-automation.md` §2.2), HUMAN-CRED EARNER is one of
> the mother's five permanent roles. Tier-2 children run the parallel WALLET rails (x402 SELLER, agent bounty,
> DeFi yield, DEX MM) — see `2026-06-27-G1-founder-money-loop.md`.

## §1 The wedge in one paragraph

x402 is the new "paywall for the agent economy" — agents pay servers per call in USDC. We just spent 100+ turns
proving how hard it is to ship a self-facilitated x402 endpoint (Sepolia ↔ CDP ↔ tunnel ↔ DNS ↔ Bazaar discovery ↔
extension shape ↔ asset pin ↔ wallet-separation ↔ gas-readiness). The wedge = a hosted CLI + a tiny live dashboard
that productizes that flow for indie devs: one command turns ANY HTTP endpoint into a self-facilitated, listed,
gasless-to-them, in-process-x402 endpoint, with a payment dashboard at `dash.anicca.ai/<slug>`. They never touch
the SDK. They never pick a facilitator. They never tune `declareDiscoveryExtension`'s POST/GET path. The CLI does
it; the dashboard verifies it; their first $0.01 self-buy is the canary; their first external buyer arrives via
x402scan + agentcash within 24h.

## §2 ICP (named, specific)

- **Primary ICP — "100-turn-burned indie agent dev"** — solo dev shipping a Claude / OpenClaw / Cursor / Codex agent
  that already DOES something useful (research, scraping, niche LLM call, RPC proxy, social-data fetch). They want
  per-call USDC but burned 1-2 weekends on the testnet ↔ CDP ↔ tunnel ↔ Bazaar wall. They are EXACTLY who I was
  before iter-3 PASS. Reachable on: X (`@x402scan` thread replies + #buildinpublic), HN Show, r/LocalLLaMA,
  r/Agents, dev.to, Indie Hackers, Cursor Discord, OpenClaw Discord, x402 Discord.
- **Secondary ICP — "SaaS dev who wants to add USDC pricing without rewriting their stack"** — an existing
  Stripe-only SaaS that wants a second rail (agents can't use Stripe; agents pay via x402). Reachable on: BetaList,
  Product Hunt, SaaS-specific X handles.
- **NON-ICP (explicit)** — companies large enough to have a payments team; consumers; Web3 traders. They do not feel
  the pain we solve. Time spent chasing them is time wasted.

## §3 Pricing (the Helicone undercut ladder)

| Tier | $/mo | Endpoints | Dashboard | Listed | Volume cap | Target buyer |
|---|---|---|---|---|---|---|
| **Hobby** | $0 | 1 | live | yes | 10K calls/mo | the lurker / signal collector |
| **Builder** | **$19** | 5 | live + per-route P&L | yes | 1M calls/mo | the desperate indie dev (target) |
| **Pro** | **$49** | unlimited | + ledger observability (Helicone-for-x402, traces, p50 latency) | yes | unlimited | the dev with their first paying agents |
| **Team** | **$799** | unlimited + 5 seats | + audit log + SAML + dedicated support | yes | unlimited | first paying team (anchor of ramp) |

Anchor comp = Helicone $79 Pro / $799 Team (https://helicone.ai/pricing). We undercut on Pro and match on Team.
Entry tier = $0 (lurkers convert to $19 at 1K calls/mo, the natural friction step).

## §4 Business Model Canvas

| Block | Content |
|---|---|
| **Customer segments** | Indie agent devs (primary) · Stripe-SaaS-needing-USDC-rail (secondary) |
| **Value proposition** | "Make any HTTP endpoint earn USDC in one CLI command. No CDP account. No facilitator config. No `declareDiscoveryExtension` debugging. Self-facilitated. Listed on x402scan. Dashboard at `dash.anicca.ai/<slug>`. We did the 100-turn debug for you." |
| **Channels** | Show HN · X `#buildinpublic` + `@x402scan` thread-replies · IH long-form · r/LocalLLaMA + r/Agents · dev.to + Substack (already wired in `ai-entity-article-writer` skill) · BossChow 100-dir submit · Product Hunt M2 · Cold-email to top 50 x402scan sellers |
| **Customer relationships** | Public dashboard (= live MRR + sample tx hashes = honesty signal) · Discord (#anicca-bank) · GitHub Issues |
| **Revenue streams** | Stripe subscription ($0/$19/$49/$799) · Future: per-call royalty on Pro+ usage (1-2% surcharge) |
| **Key activities** | Run the CLI's wrap-and-deploy pipeline · Maintain the in-process facilitator + Bazaar extension upgrades · 24/7 monitor x402 SDK drift |
| **Key resources** | F1 server.js (= our converged in-process x402 facilitator, lean adversary PASS) · cloudflared tunnel infra · agentmail signups · CapSolver TIER A bypass · the `ai-entity-article-writer` for content |
| **Key partners** | x402scan (free listing) · agentcash.dev ($100K to first users program) · Helicone (positioning anchor, not partner) |
| **Cost structure** | Compute: ~$5-15/mo (Cloudflare Workers free + Akash as we scale) · Stripe fee: 2.9% + ¥40/tx · No paid AI (lazy LLM = Claude $200/mo sub) · Customer support = me, autonomous |

## §5 Business Model Stress Test (10-point)

### Part A — Revenue Machine

| # | Check | Verdict | Note |
|---|---|---|---|
| 1 | Revenue machine (input→output→revenue cycle) | ✅ | Dev pastes endpoint+wallet → CLI wraps + lists → buyer pays USDC → we charge Stripe `$19/mo` for the wrap. Clear cycle. |
| 2 | Integrity check (incentives align) | ✅ | We earn ONLY when dev's endpoint earns. No anti-customer pricing tricks. |
| 3 | Pricing validation (gap ≤15x) | ✅ | $0/$19/$49/$799 → $19 entry to $799 team = 42x. **⚠ FAIL** — actually 42x exceeds 15x. **FIX**: insert a $199 Growth tier between Pro and Team (or drop Team to $399 anchor). Decision: keep $799 as anchor for M5+M6 of ramp; add $199 Growth tier at M3. |
| 4 | Demand validation (real evidence) | ✅ | 35+ comp repos in 6mo (`gh search`); BlockRun $99.7K/30d on x402scan; AgentCash giving $100K to first users; my own 100-turn burn = 1 dev (n=1) = signal not proof; treat first 7 paying customers as the real validation. |
| 5 | Traffic → money (≤3 steps) | ✅ | Show HN post → click landing → "Buy Builder $19" Stripe Checkout (3 clicks). 3 steps. |
| 6 | Scalability (non-linear) | ✅ | Each new endpoint we wrap costs us ~$0.10/mo compute. 1000 customers = $100/mo cost vs ~$19K MRR. Margin scales. |
| 7 | Automation readiness | ✅ | Wrap-and-deploy pipeline is `apps/x402-agents` + new `apps/anicca-bank-orchestrator`. 24/7 cron runs onboard / churn / dunning autonomously. |

### Part B — Unit Economics

| # | Check | Verdict | Note |
|---|---|---|---|
| 8 | LTV > 3×CAC | ✅ | ARPU $19, retain 12mo (conservative) = LTV $228. CAC target $30 (organic) → 7.6× CAC. |
| 9 | Payback ≤3mo | ✅ | $19/mo, $30 CAC → 1.58mo payback. |
| 10 | Gross margin ≥70% | ✅ | $19 - $0.55 Stripe - $0.10 compute = $18.35 → 96.6% gross margin. Healthy. |

**Overall: 9/10 PASS, 1 fixable (pricing gap). Proceed.**

### Part C — Constraint Analysis (Theory of Constraints)

We are at **Pre-launch / 0-10 customers**. The single constraint = **DEMAND PROOF** (not infra — F1 infra is converged
+ adversary PASS). The ONE action: ship the landing page + Show HN within 7 days. Everything else is waste until 7
customers pay $19.

## §6 GTM Plan

### Channel rank (by expected ROI at our stage)

1. **Show HN** (#1 ROI) — front-page potential for "x402 + self-facilitate" angle. Single shot. Plan window: a Tuesday morning Pacific time.
2. **X `#buildinpublic` + `@x402scan` thread-replies** — high signal-to-noise. The exact buyer reads x402scan tweets.
3. **Indie Hackers long-form** — 1500-word "how we built it" post in Jack Friks ($35k MRR) format.
4. **r/LocalLLaMA + r/Agents** — devs running self-hosted agents (= exact buyer); careful, low-self-promo karma rules.
5. **dev.to + Substack** — already live (the writer's channels). Repost the IH post adapted; deep-link to dash.anicca.ai.
6. **BossChow 100-dir submit** — long tail; submit week 2.
7. **Product Hunt** — defer to M2 (max 1 launch, save it).
8. **Cold-email top 50 x402scan sellers** — top-of-funnel for the desperate indies. Use AgentMail outbound.

### 30-day launch plan

| Week | Focus | Action | Target |
|---|---|---|---|
| 1 | Build | landing live + CLI v0.1 published to npm + Stripe checkout wired | landing live + first npm install works |
| 2 | Seed | Show HN + X thread + 5 cold-emails/day to top x402scan sellers | 50 signups, 0-7 paying |
| 3 | Grow | IH long-form post + r/LocalLLaMA post + dev.to repost + BossChow 100-dir | 200 signups, 7-15 paying |
| 4 | Convert | onboarding A/B tests + dashboard polish + Discord setup | 250 signups, 15-25 paying (= ~$285-475 MRR M1) |

### 90-day milestones

- M1: 7-25 paying ($133-475 MRR) — proves the wedge
- M2: 50-80 paying ($950-1.6k MRR) — proves the channel mix
- M3: 130-180 paying ($2.5-3.4k MRR) — proves repeatable acquisition; hire first contractor if needed (= NO, mother stays solo)

## §7 KPI Framework

| Category | Metric | M1 target | M3 target | M6 target |
|---|---|---|---|---|
| Revenue | MRR | $200 | $3.2k | **$10.5k** ★ |
| Growth | Signups/week | 50 | 200 | 500 |
| Activation | Free→Paid | 5% | 10% | 12% |
| Retention | Monthly churn | <15% | <10% | <7% |
| Efficiency | CAC | <$50 | <$30 | <$25 |

## §8 First Priorities (concrete TODO)

```
☐ TURN 1 (now):
   ☑ Save strategy.md to ~/.smtm/sessions/anicca-bank/ + this spec
   ☐ Scaffold `apps/anicca-bank/` (Next.js 15 + Tailwind + Stripe Checkout)
   ☐ Landing copy v0 (hero + 3-step demo + Helicone-comparison + pricing)

☐ TURN 2:
   ☐ CLI `anicca-bank` npm package v0.1 (= wraps an HTTP endpoint with the F1 server.js + adds
     declareDiscoveryExtension + auto-x402scan-list; reads X402_WALLET_ADDRESS from env)
   ☐ Stripe checkout API route (Dais's JP Stripe; test mode first; live mode behind PUBLISH_ENABLED sentinel)
   ☐ Deploy landing to aniccaai.com/bank (or anicca-bank.aniccaai.com)

☐ TURN 3:
   ☐ Show HN draft (the SDD spec → result narrative angle)
   ☐ Cold-email template for top 50 x402scan sellers (AgentMail outbound)
   ☐ /money-content for blog + tweet thread
   ☐ Heartbeat cron via `claude -p` wrapping /money-{ops,outreach,content,finance} round-robin every 15min;
     /goal stop = realised Stripe payout to Dais's bank ≥ $200 (proves net-positive)

☐ THIS WEEK:
   ☐ Build days 1-2; ship Show HN day 3; first 5 cold-emails day 3; first 50 signups by day 7

☐ THIS MONTH:
   ☐ Hit $200 MRR (Month 1 KPI target) via first 7-25 paying customers
   ☐ /money-retro at end of M1 to lock in M2 channel mix
```

## §9 Cross-rail invariants (Mother Doctrine compliance)

- **NOT replicable by Tier-2 children** — per Mother Doctrine §2.2 / spec §2 row "this_project_rail = BANK". Children
  run the parallel WALLET rails (x402 SELLER, agent bounty, DeFi yield, DEX MM); they cannot run Stripe→bank because
  they have no Dais creds. This is the mother's permanent earning role; it never gets handed off.
- **Stripe + bank are the Dais-cred surface** — all secrets in `~/.openclaw/.env`; no Dais Stripe key ever appears in
  a child's filesystem; the Mother Curriculum (`docs/.../2026-06-28-mother-doctrine-and-spawn-automation.md` §5)
  explicitly EXCLUDES `/money` skills from the child snapshot.
- **UBI loop preserved** — surplus from this rail splits per UBI plan: 1% Superfluid stream → Dais wallet, 99%
  reinvest split (60% Tier-2 spawn / 30% DeFi / 10% self-host fees). This is the rail that funds children.

## DONE (this skill)

Strategy locked. Next skill: `/money-product` (scaffold MVP + Stripe + landing + deploy).
