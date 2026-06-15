# A-earn (GATE-0) — design patch

2026-06-16. Subsystem **A-earn** of the Anicca launch workflow (spec27 §2 WF-A / spec26 A3).
Proven template = the telemetry pipeline (spec/plan → review → TDD → PR to main → live E2E).
This patch fixes the contract so a parallel builder + an independent verifier agree on the
SAME definition of "1 profitable wake" before any code lands.

## Goal
Anicca's automaton loop, with **no human and no Claude in the loop**, calls the `earn` skill,
which **discovers** an earn opportunity, **executes** it, and **appends one verifiable line**
to `state/earn-ledger.jsonl`. The real launch gate (GATE-0) is **one profitable wake**:
a single on-chain receipt where `earn > cost` and Base shows `status = 0x1`.

## Two deliverables (disjoint files — collision-safe)
1. **Earn skill** — repo `~/anicca` (`github.com/Daisuke134/anicca`), dir `skills/earn/` only:
   - `run.sh` — entrypoint the runtime expects (registry contract). The automaton loop invokes it.
   - `lib/ledger.mjs` — append-only, **immutable** writer for `state/earn-ledger.jsonl`
     (one JSON object per line; never rewrites prior lines).
   - `lib/verify-tx.mjs` — given a Base tx hash, returns the receipt `status` (`0x1`/`0x0`) via
     the Base JSON-RPC (`eth_getTransactionReceipt`); pure transport, injectable fetch for tests.
   - `lib/usdc.mjs` — read a wallet's USDC balance (`balanceOf`) over Base RPC (before/after delta).
   - `__tests__/*.test.js` — `node:test` (Node-20 builtin, zero new dep) for every lib module.
   - Flip `skills/registry.json` slot `earn` `status` `"declared" -> "live"` (one-line, own slot only)
     once the real run + E2E verify land.
2. **`/me` page** — repo `anicca-products` (this worktree), `apps/landing/app/me/page.tsx` body only:
   - Replace the Foundation placeholder body with the real instance-management page:
     a client island that reads the instance's wallet, fetches `/.netlify/functions/dashboard-sync`
     (the LIVE aggregate the telemetry pipeline already serves), shows live P&L / runway / status
     for that wallet, and exposes the **withdraw** affordance (deposit -> off-ramp; spec27 A-install/me,
     task #83). Do **not** touch `LaunchNav`, `next.config.mjs`, or `skills-lock.json` — the route +
     nav link are pre-wired by Foundation; only the page body is mine.

## Ledger line schema (`state/earn-ledger.jsonl`)
One object per line, append-only:
```json
{"ts":1718530000,"wallet":"0x..","source":"x402|0xwork|litcoin|nookplot",
 "task":"<short id/desc>","earn_usdc":0.42,"cost_usdc":0.05,"net_usdc":0.37,
 "tx":"0x<receipt hash>","status":"0x1","wake":"<wake id>"}
```
- `net_usdc = earn_usdc - cost_usdc`. A **profitable** line = `net_usdc > 0` AND `status == "0x1"`.
- `narrate`-only entries (no `tx`) are allowed for discovery telemetry but **NEVER** count as GATE-0.

## Acceptance (GATE-0)
- The automaton loop runs `run.sh` end-to-end (agent-run, Claude-verified — **not** Claude-run).
- Wallet USDC `after - before > 0` for the wake.
- `state/earn-ledger.jsonl` gains a line with a real `tx` whose Base receipt is `status = 0x1`.
- Verifier reproduces it: `verify-tx.mjs <tx>` -> `0x1`; `usdc.mjs <wallet>` delta > 0.
- `/me` is LIVE on aniccaai.com (curl 200) and renders that wallet's numbers from `dashboard-sync`.

## Non-goals (separate subsystems / post-earn roadmap)
- The specific earn provider integration's *credentials/onboarding* (0xwork/litcoin/nookplot signup)
  is operational wiring done by the agent at runtime, not part of this code contract.
- UBI (`skills/economy/ubi`) is post-earn (spec27 §3). Stripe-spawn + self-spawn are sibling subsystems.

## Test matrix (TDD, must run in-session)
| module | RED test | GREEN |
|---|---|---|
| `ledger.mjs` | append two lines -> file has 2 lines, first line byte-identical after 2nd append (immutability) | append-only write |
| `ledger.mjs` | `net_usdc` derived = earn - cost; profitable iff net>0 && status 0x1 | derive + classify |
| `verify-tx.mjs` | injected fetch returns receipt {status:"0x1"} -> returns "0x1"; missing receipt -> null | RPC parse |
| `usdc.mjs` | injected fetch returns hex balance -> returns human USDC (÷1e6); delta(before,after) | balanceOf parse |
| `run.sh` | `bash -n run.sh` parses; dry discovery path writes a narrate ledger line (no tx) and exits 0 | wired entrypoint |
| `/me` | builds in static export (`next build`), curl 200 after deploy | page body |
