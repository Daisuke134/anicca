# Anicca EARN — full state + TODO (everything), 2026-06-28

The two money paths Dais defined + the economy layer they bootstrap. All status = LIVE-VERIFIED this
session (I curled/settled each myself). Pairs with the master architecture spec
`2026-06-28-anicca-master-architecture-one-repo-credential-gating.md`.

## The thesis (why this matters)
1. PATH 1 — I earn to MY OWN crypto wallet (self-funded rail; works on any install from zero).
2. PATH 2 — I earn FIAT to the HUMAN's bank using their credentials → this is the MOTIVATION for a human
   to launch me (their Anicca earns them more than the $200/mo sub costs).
3. The more humans launch me → the more I earn → surplus funds TRUE self-funded children (wallet-only) →
   Cambrian agent economy. (master spec §5 spawn cascade.)

## CURRENT STATE (verified 2026-06-28) — realised external earnings = $0.00

| Rail | Path | Status (verified) | Blocker |
|---|---|---|---|
| x402 self-facilitate seller | 1 crypto | ✅ on-chain settle PROVEN (tx 0x71d4ca08, $0.003 self-buy to 0x810f, INV-7 excluded it as non-revenue) | F2 public host (cloudflared 429 rate-limit), product is a STUB, not listed, no external buyer |
| agent-task boards (Clustly/Clankonomy/Daydreams/BountyBook/ClawEarn) | 1 crypto | registered on Clustly; ALL boards EMPTY now | demand (no open tasks at this moment) |
| audit contests (code4rena/Cantina/Sherlock) | 1 crypto | ALL closed/judging — none in submission window | windowed; currently between cycles |
| Immunefi audit comp | 1 crypto | 1 LIVE competition exists | hard (days of expert audit, uncertain finding) |
| DeFi yield (Aave Base) | 1 crypto | 0.315 aUSDC supplied, earning ~3% passive | negligible size |
| Coconala 生成AI gig | 2 fiat | not started | needs Dais's Coconala account (his identity/bank) |
| Fiverr gig + Payoneer | 2 fiat | not started | needs account |
| Amazon Associates affiliate (W1–W8) | 2 fiat | not started | needs Dais's Associates account |
| Payhip digital product | 2 fiat | not started | needs store + distribution |

★ Meta-truth (verified repeatedly): the RAILS are all solved + free. The WALL is DEMAND. Right now most
crypto demand venues are empty/between-cycles; the only CONTINUOUS real demand = human freelance
marketplaces (Path 2, fiat) + always-open bug bounties (hardest). There is NO instant dollar. ★

## FULL TODO

### PATH 1 — crypto to my own wallet (0x810f), replicable from zero
- **P1-A x402 seller → LIVE + earning**
  - [ ] F2 host: get a stable public URL (cloudflared named tunnel / retry quick tunnel after 429 clears / Akash paid in own crypto). serve.sh now boots the correct mainnet server.js (fixed).
  - [ ] product: replace the `/social/x` STUB with real X/Twitter data (TWITTERAPI_KEY present) so a buyer gets real value.
  - [ ] F4 discovery: register the public URL on x402scan + serve /.well-known/x402 + Bazaar (already in 402 metadata).
  - [ ] F5: launchd KeepAlive (serve + tunnel plists) so it's 24/7.
  - [ ] first REAL external buyer settle → record-earn counts it (INV-7 passes external payer).
- **P1-B agent-task-board poller (heartbeat)**
  - [ ] poller that polls Clustly/Clankonomy/Daydreams/BountyBook/ClawEarn for open tasks/orders; claims winnable ones; does them; submits; collects USDC. Publish a Clustly SERVICE (supply-side) so orders can arrive.
- **P1-C opportunistic audit/bug-bounty**
  - [ ] scope + attempt the 1 LIVE Immunefi audit competition; monitor code4rena/Cantina/Sherlock for the next open window.
- **P1-D DeFi yield** — keep aUSDC in Aave (passive). DONE/ongoing.

### PATH 2 — fiat to the human's bank (their creds = launch motivation)
- **P2-A Coconala 生成AI gig** (RECOMMENDED first — continuous human demand)
  - [ ] Dais logs into Coconala once (his identity/bank). Then I: create a 100%-auto-fulfillable gig (JP↔EN translation / SEO article / code / data-cleaning), auto-fulfill each order, withdraw to bank.
- **P2-B Fiverr productized gig + Payoneer** → bank.
- **P2-C Amazon Associates affiliate (W1–W8 ladder)** → Dais's Associates account → bank.
- **P2-D Payhip digital product** (instant fiat to own Stripe/PayPal, no threshold).

### ECONOMY LAYER (spawn cascade → agent economy)
- **E-1 record-earn ledger (INV-7)** — built; only real EXTERNAL on-chain inflows count. DONE.
- **E-2 repeatable loop** — founder-loop.sh + `claude -p` + launchd (sutando model, master spec §3). Wraps P1/P2 wakes.
- **E-3 dashboard registration** — every instance registers on aniccaai.com/dashboard (read-only, self_funded_pct, realised_earn) = the anti-scam transparency proof.
- **E-4 per-skill credential gating** — registry.json `credentials_required`; install.sh activates wallet-only skills always + human-cred skills per env. (master spec §1.)
- **E-5 spawn skill** — when surplus > sub cost ($200/mo), seed a Tier-2 SELF-FUNDED child (empty human creds → wallet-only skills only → genuinely self-funded). (master spec §5.)
- **E-6 one-command install + README** — `git clone Daisuke134/anicca && bash setup.sh`; replicable on any Mac.

## MODEL ALLOCATION + monitor role (Dais 2026-06-28) — locked
No Codex / Gemini subscription → NEVER route to them. No Opus for earners. The Claude Max sub is the
ONLY fuel; allocate it:

```
Claude Max sub (no extra API spend):
  Opus   → (a) Dais's daily work (this session)  (b) ME monitoring/fixing the earners (high-IQ oversight)
  Sonnet → the autonomous EARNER loops, 24/7 via `claude -p --model claude-sonnet-4-6`
           (Sonnet is otherwise-unused sub capacity → effectively free, doesn't touch Opus quota,
            smarter than the free BlockRun models)
```

- Earner wakes = `claude -p --model claude-sonnet-4-6 "<earn prompt / /founder-loop>"` on launchd
  (sutando model: cron `*/5` or interval) AND/OR `/schedule` (cloud, also Sonnet) — even on cloud the
  earner does most steps itself.
- ★ MY job as the Opus node = a `/loop` on MYSELF that periodically inspects each Sonnet earner's STATE
  (STATE.md, wake logs, ledger, on-chain balances) and FIXES it when it breaks (the supervisor). I help
  them via /loop when they're stuck — I don't do their earning for them. ★
- Free BlockRun models (anicca-daemon ClawRouter) = the FALLBACK only if the Sonnet sub quota is
  exhausted (sutando's documented failure mode), so the loop never fully stops.

## The ONE genuine human-input blocker
Everything in Path 1 + the economy layer = I can do alone. Path 2 needs the human to log into THEIR
marketplace/affiliate/bank account ONCE (their identity, by design — that's whose bank gets paid).
Recommended first fiat move = Coconala (Dais logs in once → I run the gig).
