# VCSDD Phase-1c Spec-Review Verdict — trading-polymarket-spawn (iteration 5, FINAL GATE, TRADING-ONLY)

- **feature**: trading-polymarket-spawn
- **mode**: lean
- **iteration**: 5
- **reviewType**: spec (Phase 1c gate → Phase 2)
- **scope**: TRADING ONLY (Group T + Group R); Group S (spawn) deferred to `spawn-child-earn`
- **reviewing**: the 4 surgical fixes (commit b88c221) for iter-4 FIND-024/025/026/027
- **overallVerdict**: **PASS**
- **timestamp**: 2026-07-01

Fresh-context, disk-only re-review against the REAL `~/anicca` runtime. All four iteration-4 open
findings are closed by the surgical edits, no regressions were introduced to the eight earlier-resolved
trading fixes, and spawn stays fully carved out into `out-of-scope.jsonl`. The trading spec is now
internally consistent and implementation-ready. One LOW, explicitly NON-blocking precision observation
remains (FIND-028) — it does not gate Phase 2.

## Per-dimension verdicts

| Dimension | Verdict | Findings |
|-----------|---------|----------|
| Spec Fidelity | **PASS** | (FIND-024 + FIND-026 closed) |
| Edge Case Coverage | **PASS** | (EDGE-T1..T7 + EDGE-R1/R2 + boundary fixtures RG-07/08, KF-03/04/05 + fail-closed defaults intact) |
| Implementation Correctness | **PASS** | FIND-028 (low, non-blocking) |
| Structural Integrity | **PASS** | (FIND-025 closed) |
| Verification Readiness | **PASS** | (FIND-024 closed) |

## Iteration-4 findings — disposition (verified on disk)

| Finding | Sev | Status | Evidence on disk |
|---------|-----|--------|------------------|
| **FIND-024** — `filled_size` consumed by settlement gate but never written by REQ-T7(c) | high | **RESOLVED** | REQ-T7(c) write-list now is `{order_id, venue, market_id, side, size_usdc, entry_price, filled_size, ts}` (behavioral-spec.md:187) with an explicit clause: `filled_size` and `entry_price` (avg execution) "MUST be read back from the venue fill response… a position row missing `filled_size` is invalid and the slot SHALL re-query the fill before persisting." This now matches the schema (behavioral-spec.md:45), the settlement predicate REQ-T8(b) cond-2 (behavioral-spec.md:209: `shares_held = filled_size/entry_price`), and PROP-T26 (verification-architecture.md:74: `amount = round(filled_size/entry_price * 1e6) ±1`). The predicate's sole input is now produced on the write side — loop closed. |
| **FIND-025** — REQ-R4 dangled a contract over deferred `spawn-log.jsonl`/`tithe-log.jsonl` | low | **RESOLVED** | REQ-R4 (behavioral-spec.md:289) now reads "(FIND-025: spawn-log/tithe-log removed — spawn is deferred… no in-scope requirement creates them.)". Grep confirms zero surviving live `spawn-log`/`tithe-log` contracts in either spec; the only remaining `tithe` token is the descriptive phrase "including sibling tithes" in the REJECT list at behavioral-spec.md:208 (correctly characterizes a transfer the allowlist must reject — not an artifact this feature produces). |
| **FIND-026** — `settlement_amount`/`entry_cost` undefined in Tracked Quantities | low | **RESOLVED** | Tracked Quantities (behavioral-spec.md:45) now binds both: `entry_cost = filled_size` (USDC actually spent = cost basis) and `settlement_amount = the verified gross_payout_usdc from settle-verify.py (0 on a losing outcome)`. REQ-T8(a)'s `realized_pnl_usdc = settlement_amount − entry_cost` (behavioral-spec.md:205) now rests on canonical, bound quantities consistent with the settlement gate; PROP-T22/T23 inherit bound inputs. (Loss case checks out: `settlement_amount=0 − filled_size = −filled_size`, i.e. the full stake lost — correct for a binary CTF loser.) |
| **FIND-027** — `entry_price` defined as order-book MID; `shares_held` mis-reconstructed | medium | **RESOLVED** | `entry_price` (behavioral-spec.md:45) is redefined as "the **average execution (fill) price** = VWAP of the actual fills for this order… read back from the venue fill response — NOT the order-book mid (FIND-027…)". Because VWAP ≡ filled_size / shares, `shares_held = filled_size / entry_price` now reconstructs the exact CTF share count, so `gross_payout_usdc = shares_held × $1.00` reconstructs the on-chain redemption amount; PROP-T26's deterministic stub is now satisfiable by a real fill. Note: `market_p` remains the order-book mid (REQ-T3:92, REQ-T5:142) — correctly distinct from `entry_price`, used only for edge/Kelly; no collision. |

## Earlier-resolved trading fixes — re-confirmed intact (no regression)

| # | Concern | Status | Evidence |
|---|---------|--------|----------|
| FIND-001/002/003/005 | earn-slot wiring / tier / registry plumbing | INTACT | `isEarnSlot('earn/pm-trade')` true via `slot.startsWith('earn/')` (earn-slot.mjs:11); `earnSkillRelPath('earn/pm-trade')` → `"earn/pm-trade/run.sh"` (earn-slot.mjs:32); REQ-T1/PROP-T24/T25/PROP-R1 consistent. |
| FIND-007 | single-level earn slot (one slash only) | INTACT | earn-slot.mjs:29 "Single-level only (FIND-007)"; REQ-T1 declares only `earn/pm-trade`. |
| FIND-015 | settle-verify accepted any inbound USDC ≥ entry_cost | INTACT | REQ-T8(b) 3-condition predicate (behavioral-spec.md:207-211); PROP-T26b (verification-architecture.md:75) rejects non-allowlist `from` even when amount ≥ entry_cost. |
| FIND-017 | `kyc_required` not in filter signature | INTACT | `jurisdictionVenueFilter(jurisdiction_ok_for_real, kyc_required)` 2-arg (behavioral-spec.md:36; verification-architecture.md:21); PROP-T14b/T15b prove veto + absent-key fail-closed default; INT-T7 tests all three branches. |
| FIND-022 | settlement formula dimensionally wrong | INTACT + fully wired | `gross_payout_usdc = shares_held × $1.00`, `shares_held = filled_size/entry_price` (behavioral-spec.md:209); `settlement_price` term gone (only explanatory removal notes remain at behavioral-spec.md:209 + verification-architecture.md:173). FIND-024/027 (the previously-incomplete wiring) now closed. |
| FIND-023 | vestigial `jurisdiction`/`venue` string args | INTACT | 2-arg form consistent across Pure Core, REQ-T10 body (behavioral-spec.md:240), and PROP-T14/T14b/T15/T15b/T16. |

## Runtime claims spot-checked and TRUE

- `hl.py` exposes `open`/`close` with `--sl/--tp/--lev` (hl.py:142-144) and reads `~/.automaton/wallet.json` (hl.py:44) → REQ-T7(a)/(b) routing to `hl.py` for Hyperliquid with SL/TP is grounded.
- `earn-slot.mjs` predicates back REQ-T1/PROP-T24/T25 exactly (earn-slot.mjs:11,32).
- `out-of-scope.jsonl` preserves REQ-S1..S9, PROP-S1..S14, INT-T10..T13/T16, NFR-3/6/8, EDGE-S1..S5, and FIND-014/016/019/020/021 verbatim → spawn deferral is lossless and structurally clean.

## Remaining finding (LOW — does NOT block Phase 2)

| # | Dim | Sev | One-line | Blocks Phase 2? |
|---|-----|-----|----------|-----------------|
| FIND-028 | implementation_correctness / verification_readiness | low | The settlement gate recomputes `shares_held = filled_size/entry_price` from a stored float VWAP rather than persisting the exact share count from the fill receipt. With full-precision `entry_price` this reconstructs within the ±1 raw-unit tolerance; it is only fragile if a venue reports a rounded average price alongside an exact share size. A robustness nicety (store `shares_held` directly), not a correctness defect. | **NO** |

## Phase-2 gate decision

All critical/high/medium iteration-4 findings (FIND-024 high, FIND-027 medium, FIND-025 low, FIND-026
low) are RESOLVED. Zero open critical/high/medium findings. The single residual (FIND-028) is LOW and
explicitly non-blocking. **This spec PASSES the Phase-1c gate and is cleared for Phase 2 implementation.**

## convergenceSignals

- findingCount: 1 (FIND-028, low, non-blocking)
- iteration-4 findings resolved: FIND-024, FIND-025, FIND-026, FIND-027 (4/4)
- earlier trading fixes re-confirmed: FIND-001/002/003/005/007/015/017/022/023 (all intact)
- spawn carve-out: complete — no dangling spawn/tithe contract; `out-of-scope.jsonl` lossless
- allClaimsVerifiedAgainstRuntime: true (hl.py, earn-slot.mjs, proxy/wallet path)
- duplicateFindings: []
- blocksPhase2: false
