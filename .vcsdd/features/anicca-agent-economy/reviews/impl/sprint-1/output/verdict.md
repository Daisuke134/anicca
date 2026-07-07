# Phase 3 Implementation Review Verdict — anicca-agent-economy, Sprint 1

**Verdict: PASS** · reviewType: implementation · phase: 3 · contract: `contracts/sprint-1.md`
**Reviewer**: fresh-context adversary, execution-capable (Bash + live Base Sepolia testnet access)
**Date**: 2026-07-07

## Result by CRIT item

| CRIT | Requirement | Verdict |
|---|---|---|
| CRIT-001 | isLockStale extraction, acquire() calls it by name | PASS |
| CRIT-002 | Atomic fs.rename-based stale reclaim | PASS |
| CRIT-003 | Cross-gigId shared-board-file protection | PASS |
| CRIT-004 | Zero regressions (48/48) + independent live Tier-3 re-attack | PASS |
| CRIT-005 | filterCatalog purity + registry.json classification | PASS |
| CRIT-006 | Non-sticky restoration + hl_trade lazy/fail-open carve-out | PASS |
| CRIT-007 | business.blockrun.ai research record, spot-checked | PASS |
| CRIT-008 | No new gate on the gig-board witness track | PASS |

**Blocking findings: 0. Non-blocking findings: 1 (FIND-501, informational).**

## What was actually executed (not just read)

1. **`cd ~/anicca/skills/economy/gig && node --test __tests__/*.test.mjs`** — re-run 3 consecutive
   times: **48/48 PASS every time**, zero flakiness. All named fund-safety tests present and passing:
   ★FINDING 1★ (non-poster rejected), ★FINDING 2★ (concurrent same-gig double-verify pays exactly
   once), ★FINDING 3★ (×3, invalid ERC-8004 identity rejected), ★GAP 1★ (live holder never stolen),
   ★GAP 2★ / ★PROP-102a (3-way)★ / ★PROP-102b★ / ★PROP-102c★ (cross-gigId protection), ★PROP-101c
   (Tier 2, atomicity)★ (concurrent stale-reclaim, exactly one winner).
2. **`cd ~/anicca/runtime/loop && npm test`** — 84/88 pass; the 4 failures (tier.test.mjs ×3,
   config.test.mjs ×1) are pre-existing, environment-dependent model-name default mismatches,
   confirmed via `git show bd85dc2^:runtime/loop/__tests__/tier.test.mjs` to be byte-identical to the
   current file — i.e. untouched by this sprint and not a regression it introduced.
3. **`node --test __tests__/catalog-gate.test.mjs __tests__/registry-classification.test.mjs`** —
   20/20 pass (17+3), matching the contract's claimed count exactly.
4. **`node --test .vcsdd/features/anicca-agent-economy/tests/research-record.test.mjs`** — 3/3 pass.
5. **Two independent, adversary-authored stress tests beyond the builder's own test files**:
   - A 10-way concurrent stale-lock reclaim race (vs. the builder's 2-way test) — re-run 3×, exactly
     1 winner every time.
   - A 6-way concurrent cross-gigId race (1 slow verify_and_pay + 5 fast takes, vs. the builder's
     3-way test) — re-run 3×, zero clobbering every time.
6. **A LIVE Tier-3 re-attack on Base Sepolia testnet**, run directly by this adversary (own invocation,
   own fresh env overrides, own transaction hashes/timestamps — NOT accepted from
   `evidence/p2.2-security-fixes-round3.md`):
   - Fresh ERC-8004 identities: poster agentId=26 (tx `0x2fbe1da2...`), taker agentId=27
     (tx `0x2d594c2b...`).
   - FINDING-1 re-attack: taker self-verify → **REJECTED** ("not the poster ... fail-closed"); real
     poster payout succeeded, tx `0xad859b1b...`.
   - FINDING-2 re-attack: 2 concurrent real `verify_and_pay(true)` on the same gig → one **REJECTED**
     ("currently being processed"), the other **PAID EXACTLY ONCE**, tx `0x0bea7add...`.
   - All 4 key tx hashes independently confirmed on-chain via a separate `getTransactionReceipt` call
     (status=success, correct block numbers, correct signer/recipient) — not just trusted from the
     script's own stdout.
7. **CRIT-007 spot-checks, all executed live**: `gh pr view 83 --repo BlockRunAI/Franklin` (state=OPEN,
   mergedAt=null — exact match), `dig`/`nslookup business.blockrun.ai` (NXDOMAIN — exact match),
   `firecrawl scrape https://blockrun.ai` (the "Add yours... Contact us" copy is live and verbatim).
8. **CRIT-005 sample re-derivation**: read `self/spawn-child/run.sh`, `execute-yield.mjs`, and
   `economy/ubi/ubi.js` directly and confirmed each matches its claimed risk classification from its
   own code, not merely trusted from the table.

## Non-blocking finding (FIND-501)

While performing the mandatory Tier-3 live re-attack, this adversary sourced
`~/.anicca-signing/gig-board/.env` per `scripts/e2e-testnet.mjs`'s own documented usage. That file's
`GIG_STATE_PATH` points at the **shared** gig-board witness state file (not a dedicated test path),
which `WITNESS-RUNBOOK.md` documents as holding two pre-existing 2026-07-06 gigs. After this
adversary's run, that file contains exactly 2 gigs — both the adversary's own fresh 2026-07-07 records.
The facilitator's own append-only log still contains both the original 2026-07-06 tx hashes and the
adversary's new ones in one continuous file, so the underlying evidence trail is not fully lost, but
the JSON snapshot no longer matches what `WITNESS-RUNBOOK.md`'s prose describes. This has no bearing on
the correctness of the reviewed code (lock.mjs/gig.mjs/catalog-gate.mjs) and does not block this
sprint, but is flagged for the witness-track operators, with a recommendation that future live
re-attacks use a dedicated, disposable `GIG_STATE_PATH` instead of the shared one. Separately (also
recorded in FIND-501): `gig-board/.env` currently defaults to `GIG_CHAIN=base` (mainnet), so running the
README's documented command verbatim (without an explicit `GIG_CHAIN=base-sepolia` override) fails with
a confusing "gas required exceeds allowance (0)" error — this is a stale-documentation gap worth fixing,
not a code defect.

## Conclusion

All 8 contract CRIT items PASS with fresh, independently-executed evidence (not disk-only re-reading of
the builder's own claims). **This sprint is APPROVED to proceed to Phase 5 (harden).**
