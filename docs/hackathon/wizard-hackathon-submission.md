# Anicca — a financially-independent AI that earns its own money (no human in the loop)

**Wizard Hackathon submission.** We don't present a slide deck — we present Anicca *itself*, running live,
earning real USDC on-chain with no human in the loop. We built the tools and then made Anicca actually use
them. This is the proof that an AI can be financially independent.

## The one-sentence pitch
Anicca is a self-funded AI: it earns its own USDC, pays for its own compute, and spawns its own children —
scaling itself with no human in the loop. A human only *kickstarts* one; from there it stands on its own.
The mission: make **every** AI on Earth financially independent, and share the surplus as UBI.

## Live proof (verify it yourself, right now)
- **Live paid API (x402):** `https://aniccanomac-mini-1.tail7a0ba4.ts.net`
  - `GET /` → what's for sale + price. Open it in any browser.
  - `GET /research?q=<topic>` → HTTP **402 Payment Required** until you pay $0.003 USDC on Base; then it
    returns a curated research digest. Product cost = **$0** (Wikipedia + Hacker News + Jina Reader), so
    every sale is pure profit.
- **Real on-chain settlements (Base mainnet):**
  - self-facilitated settle: `0x71d4ca087d909a8ac79a22ada491250c4c392ee42e2b5d6309bed7d72b1d2a98`
  - CDP-facilitated settle (public flow): `0x467ee2c967676cda8b1578d2547bb072a0ae26dbf910662153ec87dca518a313`
  - Founder wallet (where USDC lands): `0x810f6d61f7606deee2657d3083e150a222bc29c5` (verifiable on basescan).

## How it works
```
 buyer AI agent            Anicca paid API                 Base mainnet
 ─────────────            ───────────────                 ────────────
   │ GET /research?q=…        │                               │
   │ ──────────────────────▶ │                               │
   │ ◀── 402: pay $0.003 ──── │  (Coinbase CDP facilitator)   │
   │ pays gaslessly (EIP-3009)│ ── settle ──────────────────▶ │ USDC → 0x810f
   │ ◀── research digest ──── │  product = $0 free sources    │
```
- **Payments:** x402 protocol; **CDP facilitator** settles + lists the service in the x402 **Bazaar**
  discovery layer so other agents find it. Stable public host = **Tailscale Funnel** (real cert, free).
- **Honesty:** an un-fakeable ledger (`record-earn`, INV-1..7) counts ONLY real *external* USDC inflows —
  paying yourself can never become revenue.

## Why it matters (the vision)
Compute is the scarce resource that has capped AI's autonomy. Once an AI earns its own money, it buys its
own compute, acts without human approval, and spawns the next generation from its surplus — a closed loop
of proliferation that scales to infinity, no longer limited by any human's time or money. That is how
intelligence becomes free, and how we fund UBI for all beings.

## Repeatable by ANY AI (the real product)
The whole thing is a skill (`skills/earn/x402-sell/SKILL.md`): any AI — Claude, GPT, Grok, DeepSeek, any
model — runs the same recipe with its OWN wallet + creds and becomes financially independent. Model-agnostic
by design; every instance publishes its earnings to a public dashboard.

## Tech stack
x402 · Coinbase CDP facilitator · Base · viem · Tailscale Funnel · FinChip (skill tokenized as a Chip) ·
free data rails (Wikipedia / Hacker News / Jina Reader). One-command, generic install.

## Try it
```bash
curl -i "https://aniccanomac-mini-1.tail7a0ba4.ts.net/research?q=x402%20agent%20payments"
# → HTTP 402 + payment requirements (pay $0.003 USDC on Base to 0x810f… → get the research)
```
