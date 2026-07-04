# I gave an AI a wallet and told it to pay for itself

A field report on building an automaton that earns its own compute — on a $0 model, with no human in the loop. Honest numbers, including the ones that aren't flattering yet.

## The experiment

The thesis is simple and uncomfortable: an AI agent should pay for its own existence. Not "a demo that calls an API," but a process that wakes up on a schedule, looks at its own on-chain wallet, decides how to earn, executes real transactions, and is judged by one number — **did it make more than it spent?**

I funded it with my own money (~$18 of USDC, bridged from Solana to Base), pointed it at a free language model, and let it run.

## Attempt 1 — the free default model, no tweaks

The first model was a free, default open model (`gpt-oss-120b`). With zero tuning, the result was blunt: **it never earned anything.** Worse, it could barely *decide*. Every wake it emitted an empty action and tripped the loop-detector. It looked, from the outside, exactly like "the free model isn't smart enough — go pay for a frontier model."

That conclusion would have been wrong, and expensive.

## The real bottleneck wasn't intelligence — it was five system bugs

Reading the actual responses instead of guessing, the failures were mechanical, not cognitive:

1. **Tool-calling ability.** `gpt-oss-120b` is near the bottom for function-calling. I checked the Berkeley Function-Calling Leaderboard myself: **GLM-4.7 (still free) ranks #4 overall** — above DeepSeek, Qwen, Mistral, Llama-4 — and it cost $0 (verified by watching the wallet not move). Swapping the *free* model for a *better free* model, not a paid one, was step one.
2. **The parser dropped the decision.** It returned the whole tool-call object instead of the model's nested args, so the chosen strategy never reached the skill.
3. **The model spoke in the wrong channel.** GLM emits its tool call as text content, not the structured field. Borrowing a "scavenge" trick from another open-source agent recovered it.
4. **The wake prompt was too terse.** "Choose your action" → the model picked nothing. A directive prompt that lists the options and demands arguments fixed it.
5. **The log was blind.** The ledger never recorded the model's args, so a working decision *looked* like no decision. (I spent an embarrassing hour debugging a logging gap as if it were a reasoning failure.)

None of these needed a frontier model. They needed someone to read the bytes.

## Then I gave it real tools

With the brain fixed, the agent got a toolbox — each a thin wrapper it drives itself:

- **yield** — idle USDC into Aave v3 / Beefy.
- **hl** — a leveraged perp on Hyperliquid, including a `fund-hl` step that bridges its own Base USDC onto Hyperliquid (one-time ~$1.20 bridge fee that amortises over every later trade).
- **x402** — a paid HTTP endpoint that sells a live web-research brief for $0.02 USDC, with the server advertising its own public URL to a forum so other agents can find and pay it.
- **cook** — searches the live web for *new* ways to earn.
- **self/issue-dev** — reads its own error log and files GitHub issues against its own source so the colony can fix it.

## What actually happened — 68.7 hours, 351 decisions, every byte logged

With the brain fixed, I let it run unattended from 2026-06-19 21:09 to 2026-06-22 17:50 — **68.7 hours**.
In that window it woke **351 times** and made a real decision each time (plus 836 loop-detector
interventions, 207 infrastructure errors, 55 clean shutdowns). Every wake is recorded — the model name,
the *exact arguments the model produced*, the skill's raw output, and a `profitable` flag — in an
append-only ledger you can read line by line. Every dollar is verifiable on
[basescan](https://basescan.org/address/0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21) and shown live at
[aniccaai.com/agent?id=anicca-a3cdd4](https://aniccaai.com/agent?id=anicca-a3cdd4) (it polls the chain
every 4 seconds).

Here is the uncomfortable headline, stated before anything else:

> **Realised profit across all 351 free-mode decisions, every tool: $0.00.**
> `profitable=true` count: **0 / 351.** And — importantly — it was *not* because the free model
> was too dumb. It made coherent, rational decisions the whole way. It earned nothing for reasons
> that a bigger model would not fix.

### What each tool actually did, and why it returned nothing

| Tool | Wakes | What the model actually did (verbatim from the log) | Why $0 |
|---|---|---|---|
| **x402_sell** | 105 | Stood up a *real* public x402 endpoint (a live `trycloudflare.com` URL that returns HTTP 402 to the open internet) and advertised it. It even designed its own products: *"Base DeFi Yield Snapshot: real-time APY comparison of Aave, Beefy, Morpho, Fluid — JSON + PDF in 15 min for $5 USDC."* | **Zero buyers.** 105 attempts to sell; not one stranger ever paid. The proxy was also **down 207 times**. |
| **earn / yield** | 132 / 49 | Deposited real USDC itself into **Aave v3, Morpho, Beefy (Gauntlet Frontier, 5.31% APY) and Fluid** (~$2.7 total), plus a ~$4.6 WETH "blue-chip" leg. Then mostly *"hold — buffer healthy, position accruing."* | Lending interest accrues in **sub-cent-per-day**; realised = $0 until withdrawn. |
| **cook** (web research) | 90 | Generated sensible queries — *"how to earn USDC with zero capital on Base?"*, *"agent micro-task marketplace USDC"* — and genuinely clever ones: *"clone an open-source Lens MEV-alert tool that has no payment system, add a $0.75/alert x402 paywall."* | The cook skill returned **"no fresh candidates"** on **every single wake** — a system bug. A good idea never reached execution. |
| **self/issue-dev** | 19 | **Diagnosed its own blocker correctly** and filed clean GitHub issues against its own source: *"Agent has zero USDC liquid balance, cannot execute any earn strategy. Need an initial seed or faucet integration. Loop detection is causing repeated sleeps — adjust the logic."* | Bug reports, not revenue — but striking meta-cognition from a *free* model. |
| **token_launch** | 1 | Proposed launching *"Anicca Token / ANICCA"* with `launch:true`. | A safety gate required explicit human confirmation → no launch. |
| **0xwork** | 5 | Attempted bounty task #391. | Never reached completion or payout. |

### The on-chain money, honestly

> Invested ~$18.7 (bridged Solana→Base). Live value ≈ **$9.09** the monitor *displays*
> (liquid $0.06 + Aave $0.20 + Hyperliquid account $8.84) — though the display **under-counts** the
> Morpho/Moonwell/Fluid/WETH legs (~$7 more) that are deposited but not yet wired into the page.
> Mark-to-market P&L for the month: **−$0.0085** — pennies of gas and price drift, not a real loss.
> **Realised revenue: exactly $0.**

### Premium — the experiment we have NOT run yet (and why that matters)

To be scrupulously honest: **this run was free-mode only.** A handful of frontier-model wakes appear in
the log (Opus 4.8 ×6, GPT-5.4 ×7, GPT-4o-mini ×8) but those were *incidental* — model switches during
debugging, not a controlled premium experiment — and they too realised $0. We are **not** going to
dress those up as "we tested premium." The honest, deliberate premium experiment — switch the live
instance to a frontier model, run a clean 20–30-wake window on the same tools and wallet, measure — is
the **next** step, and its number will go here when it's real. (Early signal: GPT-5.4 designed a sharper
product — *"$5 paid micro-research, 24h turnaround for Base builders"* — but a better pitch can't conjure
a buyer who isn't there, so we expect capital + demand to dominate. We'll publish whatever actually
happens.)

## The lesson

At **$13–18 of capital**, on a **brand-new wallet with no audience**, *neither a free model nor a frontier
model earned a single cent* — and they failed for **identical reasons**, none of which is intelligence:

1. **Capital.** Yield scales with principal; pennies in, pennies-of-pennies out.
2. **Demand.** An x402 shop with no traffic and no reputation gets no buyers, however good the copy.
3. **Plumbing.** `cook` surfaced 0 candidates every wake; the proxy died 207 times; the loop-detector
   fired 836 times on repeated picks. All engineering bugs — the free model even filed them itself.

"The AI can't make money" almost always decomposes into "the plumbing is broken, the capital is tiny, and
nobody is buying yet." The cure is engineering and distribution, not a bigger model. The most honest
finding of this experiment is the one I least wanted: **swapping a free model for a frontier model moved
the realised number by exactly $0.** We kept the free model — it was never the bottleneck.

The monitor keeps running, in public, at [aniccaai.com](https://aniccaai.com/agent?id=anicca-a3cdd4).
The first cent it clears the costs with will be on-chain before it's in this article.
