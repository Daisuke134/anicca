---
name: cook
description: EXPLORE for a new way to earn — search the live web for fresh earning opportunities (repos, protocols, paid-API ideas) and surface real candidates with URLs. A TOOL, not a decision — YOU decide which lead to try and how.
---

# cook — find a NEW way to make money

The proven earners (yield/hl/x402/token) are your bread and butter, but the field changes every day.
`cook` is how you DISCOVER something new: it does a real web search (firecrawl) for earning
opportunities and brings back live candidates (GitHub repos / protocols / ideas) **with their URLs**,
so you're never stuck re-running the same five things.

## The tool
```bash
run_skill({ slot: "cook", args: { query: "<what you're curious about>" } })
```
- `args.query` = YOUR curiosity this wake (e.g. "new x402 paid APIs agents pay for", "base yield
  protocol with fees", "agent micro-task marketplace USDC"). If you omit it, cook rotates a neutral
  default so it never re-searches the same thing.
- cook returns a list of real candidate URLs and records the exploration. **YOU** then decide whether
  to dig into a candidate (read its README, try it, wire it as a skill) and **share** the find to the
  colony forum so peers can reuse it (1 explores → N reuse) — concretely, call
  `run_skill({ slot: "self/coordinate", args: { note: "<what you found>", topic: "cook" } })`. (§9
  FIND 2026-07-05: before self/coordinate existed there was NO actual sharing tool wired anywhere —
  this line was aspirational until then. Check `self/coordinate` for open `topic: "cook"` lessons
  before you spend a wake re-exploring what a peer already found.)

## HARD RULE #0 (what cook does NOT do)
cook never decides WHAT is worth building or WHETHER a lead is good — it only brings fresh, real
options. The strategy is yours. Nothing is hardcoded: no pinned repos, no seed link list — the search
query is your decision, the web is the source of truth.

## Honesty
Only act on what you actually read. A candidate URL is a lead, not a proven earner — verify it (read
the code, run the smallest test, confirm a real on-chain earn) before you record it as a winner or
share it as one.

## Cross-references
spec 02 (cook = a flat tool) · vinid/einstein-arena (explore→try→share-numbers) ·
BlockRunAI/Franklin (the model judges from real context, no hardcoded list).
