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

## What actually happened (the honest ledger)

On the free GLM-4.7 model, **no human in the loop**, the agent:

- Autonomously deployed **$8.8 into Aave v3** (real tx `0x77b0…`), and now chooses to hold or top-up each wake.
- Funded its **own Hyperliquid account** from Base USDC and opened a **real ETH long, 2× leverage, with stop-loss and take-profit** (entry $1,735) — then, when the position later showed a gain, decided on its own to *close and realise it*.
- Stood up a **public x402 endpoint** (returns HTTP 402 to the open internet) and advertised it.
- Started **asking its own questions** — one wake it explored *"how to earn USDC with zero capital on Base?"* — exactly the right question for an agent with little liquidity.

And the number that matters, reported honestly by a monitor that runs every 30 minutes:

> Invested ~$18.7 · realised profit ≈ **$0** so far · net **slightly negative**, mostly gas burned while debugging.

It is **not yet net-positive.** Yield interest accrues in cents per day; the HL position's profit is real only once closed; the x402 shop has an address but not yet a paying stranger. The honest version of this story is *"the machine now earns autonomously, and we are watching whether the earnings clear the costs over days, not minutes."*

## The lesson

"The AI can't make money" almost always decomposes into "the plumbing is broken" — a parser, a prompt, a guard with the wrong threshold, a log that lied. The cure for those is engineering, not a bigger model. We kept the free model and fixed the system.

If, after honest effort and real monitoring, a free model genuinely *can't* — that's when you switch to a premium one, deliberately, as a measured experiment. Not as the first reflex.

The monitor keeps running. The next report will have the number this one doesn't.
