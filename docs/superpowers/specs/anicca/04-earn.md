# 04 — Earn (ANICCA does it, not Claude)
Goal: Anicca's loop calls earn skills and ACTUALLY earns USDC, no human/no Claude. Curated (not 100):
  main (agent-native, no capital): nookplot (mine/bounties — ★wire ClawRouter as the `openai` provider so the solver works; today it 400s "provider must be one of …"★), virtuals.io, x402 sell own work (research/code/content), media gen via ClawRouter.
  advanced opt-in (capital+risk): AutoHedge/Freqtrade (exchange keys), OpenAlice (human-approval).
Files: skills/earn/nookplot.mjs, skills/earn/x402-sell.mjs, skills/earn/content.mjs, state/earn-ledger.jsonl.
Acceptance: Anicca's loop runs an earn skill end-to-end and the ledger shows a positive USDC/credit delta with the tx/receipt. MUST be run by the agent, verified by Claude — not run by Claude.
