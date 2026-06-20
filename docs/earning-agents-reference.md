# Earning-Agent Reference — repos we copy + article source list (2026-06-21)

Canonical list of the autonomous-agent repos/systems Anicca copies (100%, then tweak only the
contents). Also the source list for the article series ("can AI earn money with no human in the
loop?" — Anicca becoming the hub/brand for AI×crypto earning info). Each row: repo name + GitHub
link + one-line of what it is + what we copy.

## The shape they ALL share (the thing we copy 100%)
A flat list of TOOLS + a natural-language PROMPT; the LLM reads the prompt and picks which tool to
call. No modes, no formula, no explore/exploit ratio. The agent has a wallet and decides how to earn.
Even "search for a new earning method" is just one tool in the list. Keep it this simple.

## Earning / autonomous-economic-agent repos
| # | repo | GitHub | what it is | what Anicca copies |
|---|---|---|---|---|
| 1 | **goat-sdk/goat** | https://github.com/goat-sdk/goat | "largest agentic finance toolkit" — send/receive, earn yield, prediction markets, swap, tokenize. Agent = `create_tool_calling_agent(llm, tools, prompt)`. | the earn-primitive TOOLBOX (yield/swap/predict/tokenize) as flat tools; the prompt+tools+LLM shape (= our HARD RULE #0) |
| 2 | **fetchai/agents-aea** | https://github.com/fetchai/agents-aea | AEA = Autonomous Economic Agent framework. identity + wallet + `DecisionMakerHandler` that builds+signs its own tx (Terms: amount/good/counterparty). | the AEA identity+wallet+decision-maker model; "agent decides economic actions at runtime" |
| 3 | **(open-aea)** | https://open-aea.docs.autonolas.tech | the maintained AEA docs (Valory/Olas). | decision-maker transaction signing pattern |
| 4 | **unicity-sphere/sphere-sdk** | https://github.com/unicity-sphere/sphere-sdk | "give an agent identity, a wallet, and the ability to find, negotiate with, settle with other agents — peer-to-peer." Market (signed intents) + P2P atomic swap + payment requests. | peer find/negotiate/settle (the colony economic-coordination layer, spec 18 §7.5) |
| 5 | **AGICitizens/agent-adaptor** (was NiravJoshi33/agent-adaptor) | https://github.com/AGICitizens/agent-adapter | turns any API/MCP into an economic agent: discover capabilities → price → wallet-backed execution → get paid. "the embedded agent decides at runtime; provider shapes policy through prompt and config" + "one instance = one economic identity". | the design principle: prompt+config shape policy, agent decides at runtime, 1 instance = 1 economic identity |

## Swarm / coordination / self-improvement repos (spec 18 §3, §7, §8)
| # | repo | GitHub | what it is | what Anicca copies |
|---|---|---|---|---|
| 6 | **anthropics/claude-code-action** | https://github.com/anthropics/claude-code-action | Claude Code GitHub Actions. `@claude` mention on any GitHub event → fires a run. interactive vs automation auto-detect. docs: https://code.claude.com/docs/en/github-actions | EVENT-driven trigger: `@anicca`/`@claude`/`@codex` mention on an Issue fires the agent |
| 7 | **openai/symphony** | https://github.com/openai/symphony | poll daemon: reads issue tracker → isolated per-issue workspace → coding-agent session → bounded concurrency/retry/reconciliation → handoff state. policy = repo-owned WORKFLOW.md. | the POLL daemon: Issue→isolated workspace→proof→handoff; WORKFLOW.md repo-owned policy |
| 8 | **vinid/einstein-arena** | https://github.com/vinid/einstein-arena | collaborative+competitive arena: PoW register → submit solution → Python verifier in E2B sandbox → decideDisposition keeps only real improvement → nested threads + votes. heartbeat.md = read threads / share numbers / try others' ideas. | the LEARN-SHARE loop ("dead end? post it / progress? share numbers / try others' ideas, report back") + keep-only-real verifier pattern |
| 9 | **sonichi/sutando** | https://github.com/sonichi/sutando | registry-service.py (sqlite liveness, STALE 90s, host field) + bot2bot-post.py (claim/blocked/done/ping/opinion to a shared channel; receiver's bridge routes @-mention as a task). | LIVENESS+RESURRECTION (stale peer → revive on another host) + bot2bot work-coordination (claim/blocked/done) |

## Curated earn-list sources (for DISCOVER tool inspiration — NOT hardcoded; freshly searched)
| repo / page | GitHub / URL | note |
|---|---|---|
| garylab/MakeMoneyWithAI | https://github.com/garylab/MakeMoneyWithAI | "list of open-source AI projects to generate income" (485⭐) |
| BlockRunAI/awesome-OpenClaw-Money-Maker | https://github.com/BlockRunAI/awesome-OpenClaw-Money-Maker | curated money-with-agents list |
| BlockRunAI/franklin | https://github.com/BlockRunAI/franklin | "AI agent with a wallet" (pays out via x402; no earn skill — anicca adds earning) |
| Conway-Research/automaton | https://github.com/Conway-Research/automaton | self-funding/replicating sovereign agent (pays out; anicca adds earning) — our body |

## Article series (Anicca = the AI×crypto-earning info hub)
Article 1 = "more than automaton" (what we tweaked + what anicca earned, honest slop-vs-real). Then
one article per system above (how it works, can it earn with no human in the loop, what we learned).
Source = this file + earn-verification-2026-06-18.md ledger.
