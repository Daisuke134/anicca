# Verification Report — franklin-loop-revival (lean)

## Tests (Phase 2a/2b)
- New behavioral tests: 33/33 GREEN (`address-classify`, `balance-solana`, `wallet-address-solana`, `integration-solana-tier`, `franklin-plist-config`, `daemon-script-franklin-routing`).
- Regression baseline: 42/42 PASS (0 regressions). Pre-existing out-of-scope failures disclosed (`tier.test.mjs`/`config.test.mjs` stale literals; a flaky self-eval test) — untouched.
- Evidence: `evidence/sprint-1-red-phase.log` (RED), `evidence/sprint-1-green-phase.log` (GREEN).

## Adversary (Phase 3, fresh Opus, commit a2185d5)
- overallVerdict = PASS (correctness / security_identity / regression_safety / spec_fidelity). Deploy-safety = SAFE_TO_DEPLOY.
- Independently confirmed: no secret leak; franklin `ensure_brain` reads no `$HOME/.openclaw/.env`/`BLOCKRUN_WALLET_KEY`/cross-instance key; shared `anicca-daemon.sh` — automaton(`com.anicca.daemon`) + founder-loop default `ANICCA_INSTANCE=clawrouter`, provably unaffected by franklin-only PORT/ensure_brain changes.
- 5 non-blocking advisories (Solana RPC single-endpoint, stale telemetry label, post-restart env checks, dead plist keys, EVM CLI re-test) — none flip a dimension.

## Live E2E (deploy = franklin-loop reload, 2026-07-08T08:51:51Z)
Both root-cause bugs fixed, verified on the running system:
- ANICCA_WALLET_ADDRESS = `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9` (was "unknown"). Verified in the live process env (PID 41912).
- OPENAI_BASE_URL = `http://127.0.0.1:8402/v1` (ClawRouter, was :8403). Live env.
- Model = `free/glm-4.7` (was rate-limited `nvidia/llama-4-maverick`). Daemon banner + ledger wakes.
- `usdcBalance(8Fpqd)` = **$11.39** — the balance-fetch path the loop uses now returns the real funded balance (was `invalid wallet address: unknown → keeping tier=broke`).
- Loop is actively waking (`~/.blockrun/state/ledger.jsonl`, model=free/glm-4.7, exit_code 0, no HTTP 429) and choosing real slots including `earn/sol-trade`, `hl_trade`, `economy/gig`, `cook`, `token_launch` — NOT stuck at tier=broke.

## Conclusion
The two root causes (wallet-resolution skip + Solana-blindness → tier=broke; THINK pinned to exhausted 8403 model) are fixed and verified live. Franklin's loop now sees and can use the $11.63 seed. Non-blocking advisories tracked for a later hardening pass.

## Proof Obligations (discharge status)

| PROP | requirement | tier | status | discharged by |
|---|---|---|---|---|
| PROP-001 | address-shape classifier | 1 | ✅ discharged | `address-classify.test.mjs` GREEN |
| PROP-002 | Solana balance delegates to usdcBalance | 1 | ✅ discharged | `balance-solana.test.mjs` GREEN + live `usdcBalance(8Fpqd)=$11.39` |
| PROP-003 | tier reflects real balance (not broke) | 0 | ✅ discharged | live E2E: loop wakes funded, no "keeping tier=broke" |
| PROP-005 | Franklin Solana address resolves | 1 | ✅ discharged | `wallet-address-solana.test.mjs` + live env ANICCA_WALLET_ADDRESS=8Fpqd |
| PROP-006 | secret never leaked | 2 | ✅ discharged | adversary-verified single stdout.write (address only) |
| PROP-007/008 | per-instance identity gate, fail-closed foreign | 2 | ✅ discharged | `resolve-identity.mjs:132` legacy-home gate (adversary) |
| PROP-012 | malformed .solana-session → warn-not-crash | 1 | ✅ discharged | `wallet-address-solana.test.mjs` malformed fixtures GREEN |
| PROP-013 | no ANICCA_BALANCE_OVERRIDE in deployed plist | 0 | ✅ discharged | `franklin-plist-config.test.mjs` + live plist |
| PROP-014 | live daemon env has no OVERRIDE / real balance | 0 | ✅ discharged | live process env (PID 41912) |
| PROP-015 | OPENAI_BASE_URL=8402, no franklin proxy on 8403 | 0 | ✅ discharged | live env OPENAI_BASE_URL=http://127.0.0.1:8402/v1 |
| PROP-016 | franklin ensure_brain reads no cross-instance env | 2 | ✅ discharged | adversary read full daemon.sh franklin branch + static test |

All proof obligations discharged via unit tests (33/33), fresh-Opus adversary PASS, and live-system E2E.

## Summary
franklin-loop-revival is verified complete: 33/33 new tests GREEN, 42/42 regression PASS, fresh-Opus impl adversary PASS (SAFE_TO_DEPLOY), and live-system E2E confirming both root-cause bugs fixed — Franklin's loop now resolves its Solana wallet (8Fpqd), fetches its real $11.39 balance (tier no longer broke), THINKs via the healthy free/glm-4.7 model on ClawRouter :8402 (no more HTTP 429), and actively decides across slots including earn/sol-trade. All proof obligations discharged. 5 non-blocking advisories tracked for a later hardening pass.
