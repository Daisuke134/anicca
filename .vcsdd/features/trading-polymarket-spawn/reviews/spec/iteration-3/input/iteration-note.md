---
feature: trading-polymarket-spawn
reviewType: spec
iteration: 3
basedOn: iteration-2 verdict (FAIL, commit 0ada823)
fixedFindings: [FIND-014, FIND-015, FIND-016, FIND-017, FIND-018]
timestamp: 2026-07-01
---

# Iteration-3 Fix Note — trading-polymarket-spawn

## Summary of changes vs iteration-2 round-2 spec

All 5 open findings from iteration-2 are addressed. The 12 previously-resolved findings are untouched.

---

## FIND-014 + FIND-018 (CRITICAL + MEDIUM): Reinvented spawn subsystem + infeasible port-split

**Root cause**: REQ-S5 invented a same-host CHILD_PORT ClawRouter port-split that `anicca-daemon.sh:50-55` explicitly disavows (":8402-only, no port split"). Group S duplicated logic from the existing, live-E2E-proven `skills/self/spawn/run.sh`.

**Fix applied**:
- Added a Group S delegation invariant note: `self/spawn-child` is a thin wrapper around `skills/self/spawn/run.sh` (verified E2E 2026-06-16).
- Rewrote REQ-S2 to describe the thin wrapper invocation: `bash $ANICCA_REPO/skills/self/spawn/run.sh` with `ANICCA_SEED_USDC` and `ANICCA_VENUE_POLICY_PATH`. All 7 mechanics (wallet gen via `gen-wallet.sh`, AgentMail inbox, provisional `children.jsonl` row, DO/Akash droplet, seed transfer, telemetry, final row) delegate to the spawn skill.
- Rewrote REQ-S3/S4 to acknowledge delegation (framework install = cloud-init; seed transfer = spawn skill step 5).
- Completely rewrote REQ-S5: removed CHILD_PORT, port scanning, COMPUTE_PROXY_PORT. Documented the correct isolation model: separate droplet where child's clawrouter binds its own `:8402` with no port collision.
- Updated REQ-S1 `spawnEligible` to wrap `decideSpawn` from `lib/spawn-decision.js` (children array from `readChildren`), replacing `spawn_log` rows with `children` array.
- Replaced all `spawn-log.jsonl` references with `children.jsonl` (Tracked Quantities + PROP-S11/12/13/14 + PROP-R6 + edge cases).
- Updated verification-architecture.md Pure Core table: `spawnEligible` module = `skills/self/spawn/lib/spawn-decision.js`; Effectful Shell = `skills/self/spawn/run.sh` (separate isolated host).
- Updated PROP-R6: no CHILD_PORT / COMPUTE_PROXY_PORT; child on separate droplet with HOME=$CHILD_HOME in systemd unit.
- Updated PROP-S14: flock → decideSpawn rate-cap via children array.

---

## FIND-015 (HIGH): settle-verify accepts any inbound USDC — faked earn

**Root cause**: REQ-T8(b) Polymarket `eth_getLogs` filter matched ANY Transfer to our wallet with amount >= entry_cost, not bound to the settlement contract or specific market.

**Fix applied**:
- Tightened REQ-T8(b) Polymarket predicate to require ALL THREE of:
  1. `from` ∈ `POLYMARKET_SETTLEMENT_ADDRS` allowlist (CTF Exchange + NegRiskAdapter contracts on Polygon; configured in `settle_verify_config.json`, not hardcoded)
  2. amount = `gross_payout_usdc` for THIS resolved position (± 1 raw unit rounding only), not just `>= entry_cost`
  3. tx containing the Transfer references THIS market's `condition_id` (via `eth_getTransactionReceipt` + CTF `PositionRedemption`/`PayoutRedemption` log in same tx)
- Added PROP-T26b: `settle-verify.py` REJECTS a Transfer from a non-allowlist address even if amount >= entry_cost (covers sibling tithe, parent top-up, unrelated market payout).
- Updated PROP-T26 to reference all 3 sub-conditions.
- Updated Anti-Slop Commitments row for fake-PnL to reference PROP-T26b.

---

## FIND-016 (MEDIUM): child can never enable real venue (no operator)

**Root cause**: `install.sh` sets all venues `jurisdiction_ok_for_real:false` and the spec never defined who flips the flag for a no-human autonomous child.

**Fix applied**:
- Added parent-provisioned venue policy mechanism to REQ-T10: at spawn time, the PARENT INSTANCE (not a human) derives `parent_venue_policy.json` from its own `menu.json` (entries where BOTH `jurisdiction_ok_for_real:true` AND `kyc_required:false`) and passes it to `run.sh` via `ANICCA_VENUE_POLICY_PATH`. The child's cloud-init bootstrap writes this as the initial `menu.json` BEFORE `install.sh` runs.
- Added this mechanism to REQ-S2 (spawn invocation) and REQ-S3 (cloud-init writes policy before install.sh) and REQ-S5 (venue policy provisioning section).
- Updated PROP-E2E-2 done condition: child uses parent-provisioned Hyperliquid policy (no human operator needed) to complete ≥1 real earn pass + tithe tx.
- The PARENT is the operator for its children (no-human-in-loop per REQ-J8): parent has already confirmed its own real-stake venues programmatically.

---

## FIND-017 (MEDIUM): kyc_required not in jurisdictionVenueFilter signature; unverified guard

**Root cause**: `jurisdictionVenueFilter(jurisdiction, venue, menu)` signature didn't expose `kyc_required` as an explicit parameter; PROP-T14/15/16 only tested `jurisdiction_ok_for_real`.

**Fix applied**:
- Changed `jurisdictionVenueFilter` signature in behavioral-spec.md Purity Boundary and verification-architecture.md Pure Core to: `jurisdictionVenueFilter(jurisdiction, venue, jurisdiction_ok_for_real, kyc_required)` (4 scalar args; effectful shell reads both fields from `menu.venues[venue]` before calling).
- Return semantics: True IFF BOTH `jurisdiction_ok_for_real == true` AND `kyc_required == false`. Missing `kyc_required` key defaults to True (fail-closed) at the effectful shell read step.
- Added PROP-T14b: `jurisdictionVenueFilter("US", "kalshi", True, True)` = False (kyc_required veto fires even when jurisdiction_ok_for_real=True).
- Added PROP-T15b: absent `kyc_required` key → default True → False (fail-closed read in effectful shell).
- Updated PROP-T16 to use new signature (SG + hyperliquid + both clear = True).
- Updated INT-T7 to test all three branches (jurisdiction blocked, kyc_required blocked, both clear = allowed).

---

## Internal consistency check

- All 12 previously-resolved findings (FIND-001 through FIND-013) remain intact: riskGate purity (FIND-003), wallet isolation via HOME (FIND-001), settle-verify direction (FIND-002 base direction intact, now tightened), pm.py/hl.py separation (FIND-013), yield-keeper isolation (FIND-005), spawn TOCTOU (FIND-006, now via decideSpawn rate-cap), Kalshi ban (FIND-007), market_p mid price (FIND-008), adversary-pass.json path (FIND-009), perp SL/TP (FIND-010), wallet.json attribution (FIND-011), pm.py requirements.txt (FIND-012).
- REQ-J8 invariant maintained: no human touch in spawn flow; parent is the policy source for children.
- PROP-E2E-1 (human-funded body real tx) unchanged; PROP-E2E-2 updated to be reachable via parent venue policy (no human needed for spawned child).
