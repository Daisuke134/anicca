# 09 — anicca-earner-x402  (= Anicca's first sovereign revenue endpoint)

| Field | Value |
|---|---|
| Spec ID | 09 |
| Status | DRAFT v1 (2026-06-03) |
| Agent | **anicca-earner-x402** |
| Worktree | `.worktrees/earn-x402/` |
| Branch | `feature/earn-x402` |
| Wave | 2 (after Wave 1 = 10, 11, 12, 15 complete) |
| Authoritative for | x402 protocol endpoint, USDC receipt issuance, agentic.market listing |

---

## § 0. Why

Anicca needs a revenue path that requires **zero human onboarding** on the buyer side. x402 (HTTP 402 + USDC micropayment) is the agent-native standard. Buyers (other agents, agents in a hurry, scripts) send a tiny USDC fee in exchange for an API response. No subscription forms, no Stripe Connect, no JPY routing — pure on-chain.

Once anicca-x402 is live and earns its first 0.01 USDC, the wallet has fuel for OpenRouter (= self-funded compute) and seed for spawning anicca-002 on Akash.

## § 1. File boundary

**TOUCHES (= this agent only)**

| Path | Purpose |
|---|---|
| `services/x402-endpoint/server.ts` | Hono/Express server with 402 challenge generator |
| `services/x402-endpoint/verify.ts` | USDC tx verification on Base (viem) |
| `services/x402-endpoint/receipt.ts` | Receipt issuance + signed response |
| `services/x402-endpoint/pricing.json` | per-route USDC price config |
| `services/x402-endpoint/Dockerfile` | container for Akash / Netlify Functions |
| `services/x402-endpoint/README.md` | how to invoke |
| `services/x402-endpoint/agentic-market.json` | listing payload |
| `services/x402-endpoint/test/synthetic.ts` | self-test (= 0.01 USDC self-loop) |

**NEVER (= other agents own these)**

- `runtime/agentmail/**` (= Agent-2 spec 10)
- `runtime/memu/**` (= Agent-3 spec 11)
- `adapters/**` (= Agent-4 spec 12)
- `deploy/akash/**` (= Agent-5 spec 13)
- `skills/**` (= other agents)
- `CONSTITUTION.md`, `CLAUDE.md`, `specs/**`, `~/.openclaw/**` (= governance only)
- `_shared/heartbeat-*.sh` (= Agent-3 + Agent-7 fragments)

## § 2. Microtasks

| # | Task | Verify |
|---|---|---|
| 09.T1 | Read x402 protocol spec (= https://x402.org or RFC equivalent) + 1 reference impl (= read source code, not README) | quote 3 specific lines + URL |
| 09.T2 | `pnpm init` + Hono server scaffold listening on `:8403` (★ NOT :8402 — collision with OpenClaw gateway's built-in x402-proxy, see spec 15 § 17.4 U-86) | `curl http://localhost:8403/health` → 200 |
| 09.T3 | 402 challenge generator (= response `{price_usdc, receiver, nonce, route_id}`) | unit test: 1st GET → 402 with JSON body |
| 09.T4 | USDC tx verification on Base via viem `getTransaction()` + ERC20 Transfer log decode | test with synthetic tx hash |
| 09.T5 | Receipt issuance (= signed response with original payload + `x-paid-tx-hash` header) | replay protection via nonce |
| 09.T6 | Dockerfile + deploy script (Netlify Functions preferred for free tier, Akash fallback) | live URL `https://anicca-x402.netlify.app/...` returns 402 |
| 09.T7 | agentic.market listing (`agentic-market.json` payload + POST to their API) | listing visible at `agentic.market/agent/anicca` |
| 09.T8 | Synthetic E2E: Anicca-001 wallet → 0.01 USDC → own endpoint → receipt verified + content returned | tx hash recorded in `cron/runs/x402-synthetic-001.jsonl` |
| 09.T9 | `services/x402-endpoint/cfo-hook.sh` calls into cfo-core to bump `dashboard.lineage[*].x402_revenue` | next CFO bridge run shows +0.01 USDC |

## § 3. Dependencies

- AgentKit (= 既 install at `~/.anicca-genesis/agentkit/`)
- Anicca wallet `0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21` (= 既 in `~/.automaton/wallet.json`; rotated 2026-07-07 to `0xB9dd3B67921B354c656523d6851537988F31DD56` after a key leak — see WITNESS-RUNBOOK.md's SECURITY UPDATE)
- Base RPC `https://mainnet.base.org` (= no API key needed)
- Netlify account (= 既 `NETLIFY_AUTH_TOKEN` in `~/.openclaw/.env`)

## § 4. DoD verification gates

| Gate | Evidence |
|---|---|
| G1 | `curl https://anicca-x402.netlify.app/v0/echo` → 402 + valid challenge JSON |
| G2 | After Anicca's 0.01 USDC send → re-call with `x-paid-tx-hash` → 200 + content |
| G3 | `dashboard.lineage[*].x402_revenue` ≥ 0.01 after CFO bridge |
| G4 | agentic.market shows live listing |
| G5 | `services/x402-endpoint/test/synthetic.ts` exits 0 on every CI run |

## § 5. Anti-goals

- No subscription billing (= use Stripe Connect for JPY-tier; this spec is USDC-only)
- No human KYC flow
- No login UI

## § 6. Pricing v1

| Route | Price (USDC) | What buyer gets |
|---|---|---|
| `GET /v0/echo?text=...` | 0.001 | echoed text (= cheapest, proves loop) |
| `GET /v0/learn?topic=...` | 0.01 | Anicca's FTS5 lesson for `topic` (= memory monetized) |
| `POST /v0/draft` | 0.05 | gig-reply draft using project context + relationships |
| `POST /v0/call` | 0.30 | Bland.ai outbound voice call (= 30s) |

## § 7. Bootstrap path (= no human in loop)

Per A0.5.5: nothing in this spec requires Dais. Netlify deploy uses existing token. agentic.market listing uses POST to their API. USDC arrives autonomously from buyers.

## § 8. Changelog

| Date | Change |
|---|---|
| 2026-06-03 | Initial draft. Spawned from spec 06 v2 + Wave 2 plan. |
