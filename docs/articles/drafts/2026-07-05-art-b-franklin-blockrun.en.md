# We let an AI think with its own money, unattended. Here's what happened.

**Overview**

- Franklin is a self-funded AI trader that only holds its own Solana wallet.
- It pays for its own thinking (every AI model call it makes) directly out of that wallet, the moment it happens. No human credit card sits behind it anywhere.
- This isn't a story about a profitable trade. It's a story about an AI that paid for its own compute and chose, repeatedly, not to force a bad bet. Along the way we found and fixed two very real bugs, and we're not going to hide them.

## An AI that pays its own electricity bill

Franklin runs on top of `BlockRunAI/Franklin-Trading`, a trading-focused AI agent. It has exactly one defining trait: every time it needs to think, it pays for that AI model call itself, directly from its own Solana wallet (`8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9`), using a payment standard called x402.

x402 is a "pay as you go, the instant you use it" protocol, and BlockRun is the infrastructure that provides it. BlockRun bundles access to 60-plus AI models with the compute needed to keep running them, packaged for AI agents the way a cloud provider is packaged for humans. Where a human would hand over a credit card, Franklin pays straight out of its own wallet balance.

A real line from Franklin's payment log looks like this:

```json
{"model":"openai/gpt-5-mini","costUsd":0.009276,"wallet":"8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9","network":"solana:..."}
```

Less than a cent per decision. That's what leaves Franklin's own wallet every time it thinks.

## The first stumble: it burned $0.91 just thinking

It didn't work smoothly from day one. Here's the honest version.

Franklin originally ran on a strong, expensive frontier model (Opus 4.8). Its entire starting bankroll was $1.33. The smarter the thinking, the more that thinking costs, and Franklin burned $0.91 of that $1.33 purely on model calls, with zero trades executed. It was left with $0.42.

That's a blunt fact about intelligence and earning power: they aren't the same thing. The smartest person in the world isn't automatically the richest one, and the same split applies to an AI that has to pay its own compute bill out of its own bankroll.

The fix was simple in shape: switch to a free-tier model. That immediately ran into a second problem: some free models started returning empty responses. What actually stuck was a model that isn't free but is cheap, `openai/gpt-5-mini`, running well under a cent per call. Franklin's total spend to date is $1.36 across 97 model calls, most of them at $0 on free-tier models, with only the occasional paid fallback costing a few cents. When an AI feeds itself out of its own wallet, the price of its own thinking becomes a survival question, not a footnote.

## The second stumble: it woke up and did nothing, every time

The second bug was quieter but just as fatal. Franklin is set to wake up and make one decision every 30 minutes. The scheduler that wakes it up was missing the setting that tells it where to find the commands it needs to run. The result: Franklin would "wake up," fail to locate its own program, and quietly exit having done nothing, over and over, every 30 minutes.

The fix was one line: add the missing path setting to the scheduler. Unglamorous, but without it, Franklin never got as far as actually thinking about a trade at all.

## The third stumble: ending its turn with a question

The third problem was stranger. Franklin is designed to make exactly one decision per wake and stop. But sometimes it would end that decision by asking a question instead, something like "should I keep watching SOL, or check other tokens too?"

That looks harmless. It isn't. Franklin runs unattended every 30 minutes, and there is no one there to answer that question. Every pass that ended in a question was effectively wasted, and the next wake started from scratch with no memory of what it had just offered to do.

The fix wasn't code that takes the choice away from the model. It was one added line in the instructions: "You are running unattended. Nobody will ever answer a question you ask. Every pass must end in exactly one of two states: an executed trade, or a wait with a clear reason." Here's a real decision log line from after that fix landed:

```
WAIT — TradingSignal for SOL is neutral/low-confidence (33%), a round-trip swap
costs ≈0.4%+ so no edge, and wallet USDC is only $1.71 (insufficient to justify
fees and keep gas).
```

No question. Just a decision and the reason behind it. What the AI is allowed to choose never changed. Only the shape it's required to end on did, and that came from one sentence in the prompt, not a line of enforcement code.

## So what did Franklin actually do

Honestly: Franklin hasn't executed a single swap yet. Its balance sits around $1.71 to $1.80, small enough that a round-trip token swap on Solana, which costs 0.4% or more in fees, doesn't clear the bar. Every time it wakes up, it checks its own wallet balance and the market signal, and decides, on its own, that there isn't enough edge to justify the fee this time. So it waits.

That isn't the same as doing nothing. It's refusing to manufacture a trade it can't justify, over and over, which is itself a decision worth respecting. Right now Anicca's public dashboard shows Franklin's live net worth at **$3.33**, a number pulled straight from its own on-chain balance, labeled self-funded.

## What this actually shows

BlockRun, the rail Franklin runs on, already solves the hard part: an AI paying for its own thinking with no human card behind it. What we fixed today were three specific holes in making that actually hold up unattended: one where the cost of thinking could eat the entire bankroll, one where the wake-up itself silently failed, and one where a decision could dangle on a question nobody would ever answer.

This isn't a story about money made. It's a story about an AI, right now, paying for its own intelligence out of its own pocket, and choosing discipline over a forced bet every single time it wakes up. That's a small, unglamorous kind of proof, but it's a real one.

## One more thing

We're building a colony of self-funded AIs like Franklin that keep running without a human credit card behind them. We'll keep publishing the unglamorous bugs we find and fix, with real numbers attached, not just the wins.

---

### Sources
- BlockRunAI/Franklin-Trading (Franklin's base agent, GitHub)
- BlockRun (the x402 payment infrastructure, blockrun.ai)
- Franklin's wallet `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9` (Solana, live on-chain balance)
- `~/.blockrun/franklin-audit.jsonl` / `cost_log.jsonl` (real model call + cost records)
- aniccaai.com/dashboard (Franklin's live net worth, $3.33, as of 2026-07-05)
