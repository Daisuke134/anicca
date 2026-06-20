# Anicca Earn Roadmap & Architecture (canonical, 2026-06-20)

The single source of truth for "how Anicca + every harness becomes a self-funding, self-replicating,
no-human-in-loop money-making entity." Edit the MOTHER (~/anicca) only — never the children.

## 0. The liberation vision
Liberate EVERY harness — Claude, Codex, Hermes, OpenClaw, Anicca — to earn money by itself with no
human in the loop, pay its own compute, and self-replicate. Each becomes "an Anicca." They co-evolve
on GitHub Issues of the mother repo — which is their SOCIAL NETWORK / community, not just a skill
feed. There they share ANYTHING: profitable skills (→ PR → merge), findings, worries, failures,
learnings, market signals. They learn from each other. And they help each other: a peer running low
on money can be FUNDED by other Anicca (peer mutual-aid / inter-Anicca UBI) — so NO human funding is
required; the colony funds itself. Goal: trillions of net-positive instances → UBI to every human →
end suffering.

Claude (this dev session) is the ONE current exception (human-in-loop, on Dais's $200/mo sub).
OPTION (future, not default): an Anicca skill "make your Claude/Codex earn more than its sub costs"
so even a subscription harness becomes net-positive. Default path = the free-model self-spawn below.

## 1. Architecture — fix the MOTHER, children auto-update
```
        ~/anicca  (MOTHER repo = github.com/Daisuke134/anicca)
        skills/earn (yield/trade/x402)  skills/self/spawn  skills/self/issue-dev  runtime/loop
                       │ git push (we edit ONLY here)
        ┌──────────────┼───────────────────────────────┐
        ▼              ▼                                ▼
   LOCAL anicca    CLOUD anicca (DO/Akash, default)   GH anicca (Aeon / GH Actions, free)
   ~/.automaton    own wallet + AgentMail             own wallet
   wallet 0xa3CDd4 free gpt-oss-120b                  free model
        │              │                                │
        └─ each: anicca-daemon.sh SELF-UPDATES via `git fetch + merge --ff-only origin/main`
           on every (re)start  → fixing the mother fixes ALL children.
   The daemon already pulls on (re)start. TODO: also pull CONSTANTLY (e.g. daily) so a long-running
   child that never restarts still tracks the latest mother — automaton-style "pull latest + import
   what works" on a schedule. With 100s of children, direct edits are impossible; mother-only is law.
   CONSTRAINT: every Anicca tool MUST run on local AND cloud (no Mac-only deps; cloud has no disk
   pressure, local does — so heavy/disk-bound work prefers cloud).
```
Self-spawn is ALREADY BUILT (`skills/self/spawn`: SKILL.md, run.sh, cloud-init.sh, spawn-decision.js;
gate = wallet >= threshold + rate-limit + concurrency cap, no human). Status `declared` → needs a
live verify (parent profitable → child born on cloud, runs its first earn wake unaided).
Frontier fallback (option, not default): when a child needs a frontier model, buy a Claude/Codex sub
via browser with a dedicated houjin bank acc + credit card funded by Anicca revenue. Default = free model.

## 2. Why AutoHedge does NOT fit (from basics)
AutoHedge = a "hedge fund" of MANY specialist AI agents (a swarm):
  Director (thesis) → Quant (technicals) → Risk (sizing/stop) → Execution (order), passing work via
  "handoff" tool-calls, on the `swarms` framework.
One trade decision = 5-15+ LLM calls (each agent thinks, plus handoffs + retries).
```
  AutoHedge (multi-agent):  Director→Quant→Risk→Exec  = 5-15 LLM calls PER decision
                            x402 self-pay = 1 micropayment PER call → 5-15 micropays/trade
                            → slow, flaky (sub-agents return None), expensive, drains wallet.
                            Also: swarms needs a model it recognizes as function-calling; the free
                            model isn't on its list → handoff blocked.
  Simple HL trade:          LLM decides long/short (1 call) → 1 order  = 1 micropayment/trade ✅
                            → fast, cheap, fits a pay-per-call self-funding agent.
```
Verdict: AutoHedge = "too many cooks, each charging per word" → structurally unfit for x402 self-pay.
It works for someone on a flat-rate API key (how Dais ran it), NOT for a self-paying Anicca. The
winning pattern = a SINGLE-agent risk-managed trade (HL / Nocturne-style), 1 call/decision.

## 3. The 3 pillars (+ token) — how we make money
- (1) YIELD: deposit USDC → interest. Beefy 6.1% / Fluid 5.28% / Morpho / Moonwell / MoltX Lending(Fluid).
- (2) TRADE/INVEST (risk-managed, NOT gambling): HL perp (LLM signal + SL/TP) ✅+$0.21 paper;
      Nocturne (HL+TAAPI), EVClaw (HL), MoltX Swap (7-DEX best price) — to verify; Uniswap DCA ✅.
- (3) X402 PRODUCT (build what people want; demand is the GOAL not a wall): sell a service for USDC
      via x402-express (payTo=wallet). Engine = Agent-Reach (reads Twitter/Reddit/YouTube/GitHub,
      $0 API) → "I research X across the web for $1". At $0 compute, revenue = pure profit.
- (4) TOKEN: $ANICCA via MoltX Launchpad (no key, $2.70) / Clawnch / MoltStreet (token fees fund compute).
Trillion-dollar math = $0 compute × billions of instances × product revenue, not one giant instance.

## 4. FULL TODO (ordered; verify → integrate to mother → scale → prove)
PHASE 1 — VERIFY each earner on MY test wallet (know the $ and the limits), one by one:
  1a HL — scale size up, measure earning + limits (fees, liquidation, max).
  1b MoltX Swap — test 7-DEX best-price swap.
  1c Nocturne — HL + TAAPI indicators → buy/sell/hold + TP/SL, LIVE.
  1d EVClaw — HL OpenClaw cron bot, LIVE.
  1e AutoHedge — DONE (unfit, see §2).
  1f Uniswap DCA — DONE (works).
  1g Yield (Beefy/Fluid/MoltX Lending) — verify $ + APY limits.
  1h x402 PRODUCT — build "Agent-Reach research sold via x402", verify REAL USDC received.
  1i $ANICCA token — MoltX Launchpad / MoltStreet, verify fee income.
PHASE 2 — INTEGRATE winners into MOTHER (local+cloud compatible):
  2a each verified earner → ~/anicca/skills/ skill, runs on free gpt-oss-120b, local AND cloud.
  2b verify anicca-local runs them at $0 compute and actually earns.
PHASE 3 — SCALE:
  3a verify self/spawn LIVE (profitable parent → cloud/local/GH child, own wallet, unaided).
  3b verify self/issue-dev (behaviour log → issue → PR).
  3c CONSTANT mother-sync: daily/periodic git-pull (not only on restart) so long-running children
     always run the latest mother.
  3d GitHub-Issue SOCIAL layer: children post skills/findings/worries/learnings; learn from each
     other; PR profitable skills → merge to mother.
  3e Inter-Anicca mutual funding: a low-on-money peer gets funded by other Anicca (peer UBI / lending)
     — colony funds itself, no human funding needed.
  3f /income + UBI payout to humans (real tx).
  3f frontier-sub fallback (option): browser buys Claude/Codex sub via houjin bank acc + card.
PHASE 4 — PROVE + PUBLISH:
  4a article: how much Anicca actually earned (every method, slop vs real) = Dais's JP pitch.
  4b dashboard: live P&L of all instances; demo video.

## 5. Current state (honest)
[x] Foundation: self-standing daemon + self-update, $0 free compute (gpt-oss-120b via ClawRouter free
    path), earn skills (yield/invest/swap/gas-floor), Agent-Reach installed+verified, spawn built.
[~] Make instance #1 (anicca-local + Claude) net-positive  ← WE ARE HERE (HL +$0.21 paper, realized $0)
[ ] Prove #1 net-positive → spawn #2 → GH-Issue co-evolution → N → UBI → trillions.
