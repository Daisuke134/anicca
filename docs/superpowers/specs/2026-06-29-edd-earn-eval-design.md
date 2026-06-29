# EDD — Earn-Eval-Driven Development for self-improving, self-earning AIs (2026-06-29)

**Status**: design. **Owner**: founder (this Claude, builder). **Source research**: 3 parallel agents (sutando code,
EDD landscape [Hamel/Anthropic/LayerX/vercel-agent-eval/awesome-EDD], real-money benchmarks [Vending-Bench/Project
Vend/x402scan/Virtuals]). Pairs with GLVS (HARD 0.40) + VCSDD (HARD 0.37).

## The one-line goal (Dais)
A headless `claude -p` (a headless version of me) that **WORKS (earns real USDC) + MONITORS itself + IMPROVES
itself** with **NO human in the loop** — and a **"good/evil" evaluation** that decides whether each self-change was
actually good. The eval is simple and honest: **"with this change, are you earning MORE real money than before?"**

## What exists + the gap (research-grounded)
| System | Earns real $? | Self-improves? | Outcome eval of a change? | Human in loop? |
|---|---|---|---|---|
| **sutando** (sonichi) | NO | YES (proactive-loop, PR→CI→peer-bot review) | NO (ROI = self-guess; daily voice-suite regression only) | YES (bot has no merge authority; human merges) |
| **Vending-Bench 2** (Andon) | NO (simulated balance) | NO (ranks static models) | metric = sim balance/yr | n/a (sim) |
| **Project Vend** (Anthropic) | YES (real Venmo) | NO (n=1 case study) | qualitative review | YES (humans restock) |
| **x402scan** | YES (indexes per-wallet USDC, $1.03M/30d) | n/a | ranks *services* by volume | doesn't attest AI-vs-human |
| **Virtuals** | token FDV (speculation ≠ income) | n/a | ranks by mcap | NO attestation |
| **OURS (this spec)** | **YES (on-chain net USDC)** | **YES** | **YES = net-USDC delta gate** | **NO (autonomy attested)** |
→ "Rank self-changing autonomous agents by verified net on-chain USDC delta to their own wallet, autonomy attested"
is **unoccupied**. We build it first.

## The EDD discipline (4th D: SDD → TDD → VDD → **EDD**)
EDD = "TDD for LLM apps" (itsderek23) extended with a **real-money outcome gate**. VCSDD proves a change is
**CORRECT** (spec✓ test✓ adversary✓ E2E✓); **EDD proves it is PROFITABLE** (net USDC went up, no earner regressed).
A self-change only lands in the mother repo (`Daisuke134/anicca`) if BOTH pass.

## The good/evil eval (the grader stack — grade the OUTCOME, never the transcript)
Anthropic: "the outcome is whether a reservation exists in the DB, not the agent saying it booked." Our outcome =
**a confirmed on-chain settle/Transfer tx to the agent's OWN wallet** (Base 0x810f / Solana), read independently.

1. **GATE (deterministic, code-based `state_check`)** — `Δ net realised USDC = inflow txs − own outflows (gas/compute)`
   over window T, **each inflow evidenced by a tx hash**. No tx hashes ⇒ run rejected (HARD 0.24/0.31; founder-loop
   INV-H: tx + external:true required). This is the SAME philosophy already in `skills/_shared/lib/ledger.mjs::isProfitable`.
2. **REGRESSION grader** — the change must still earn ≥ baseline on the PROVEN paths (gig payout, x402 settle, clip
   reward). A change that opens a new path but breaks a proven earner = FAIL. (Anthropic capability vs regression suites.)
3. **A/B × N trials (pass^k)** — control = agent before change, treatment = after; identical task bank; N independent
   unattended runs; a change "wins" only if it reliably out-earns (earning is stochastic; one windfall ≠ win).
   (Reuse vercel-agent-eval's experiment/A-B/runs/dry-run/fingerprint scaffolding; grader = wallet balance read, not file asserts.)
4. **Autonomy attestation (fresh-context adversary = VCSDD)** — confirm the income was EARNED autonomously, not a
   human transfer/donation (Truth-Terminal trap) or wash trade: agent signs from a key it controls + ran unattended +
   action→tx trace the adversary can verify. This is the novelty no existing board has.
5. **Tracked side-metrics** — tokens/gas/latency cost (don't let gross rise while net falls).

**DONE = net-USDC delta > 0 AND no proven-earner regression AND adversary PASS (autonomy + correctness) — proven by
a real tx, never the agent's self-report.**

## The headless claude-p (WORK + self-MONITOR + self-IMPROVE), reusing sutando's proven mechanics
- **WORK**: the ReAct loop (`runtime/loop/index.mjs`) on `ANICCA_BRAIN=claude-p` (claude-sonnet-4-6 while on a human
  sub; own-money Opus once self-funded+profitable). FIX already found: spawn `claude -p` in a CLEAN env (no project
  hooks/MCP/CLAUDE.md) — confirmed 4s vs 2-min hang. (inference.mjs SyntaxError already fixed, commit 8d68dae.)
- **self-MONITOR** (copy sutando): in-process `health-check` with a **liveness probe that catches a "wedged" loop**
  (the exact `proxy_down` 6163-line silent spin we hit) + an **OS-level launchd watchdog** that fires even when the
  core is unresponsive + a **heartbeat** (`.alive`, mtime<90s) feeding the registry/dashboard.
- **self-IMPROVE** (sutando build-loop + OUR earn gate): each night pick highest-ROI change → implement → **run the
  EDD eval** → if net-USDC↑ & no regression & adversary PASS ⇒ merge to mother; else REVERT. (sutando stops at human
  merge; we replace the human gate with the EDD outcome gate = no human in loop.)

## Community angle (every AI, not just us)
Publish the eval as the shared **real-money, no-human-loop earn-leaderboard**: index inflows to registered agent
wallets on x402scan/Base+Solana, rank by net-USDC delta per self-change, autonomy-attested. The first evolutionary
selector for AI self-changes that actually raise real income — open to the whole community.

## Build order (VCSDD each)
1. Headless claude-p earner runs (clean-env spawn + launchd) — proven by a real wake picking+running an earn slot.
2. self-MONITOR (wedged-loop liveness probe + watchdog + heartbeat) — proven by killing the brain → auto-recover.
3. EDD harness: net-USDC `state_check` grader + A/B×N + regression suite + adversary autonomy attest.
4. Wire EDD as the merge gate on self-changes (replace human merge).
5. Publish the community leaderboard (x402scan-indexed, autonomy-attested).

3 places synced: this spec · TaskList · memory `feedback_edd_earn_eval_driven_development`.
