---
feature: trading-polymarket-spawn
phase: 1c
mode: lean
iteration: 4
type: scope-split + targeted-fixes
basedOn: iteration-3 verdict (FAIL) + FIND-019..023
---

# Iteration-4 Input Note — Scope Split + Trading Fixes

## What changed and why

### 1. Scope split: Group S deferred to `spawn-child-earn` (REQ-J4)

The lean 3-round cap was reached on iteration-3 with FAIL. The FAIL root cause is entirely in Group S
(spawn): the "thin wrapper fully delegates to run.sh" framing asserts capabilities the real
`skills/self/spawn/run.sh` does not have (FIND-019: no on-chain seed transfer; FIND-020: no
`ANICCA_VENUE_POLICY_PATH` consumption / child `menu.json` bootstrap; FIND-021: contradictory internal
gate). Group T (trading) is genuinely converged — all iteration-3 Group T findings are the two
correctness bugs fixed below.

**Actions taken:**
- Created `out-of-scope.jsonl` with one JSONL row documenting the deferral verbatim (all Group S REQs,
  proof obligations, integration tests, NFRs, edge cases, and linked findings FIND-014/016/019/020/021).
- Removed Group S text from `behavioral-spec.md`: REQ-S1..S9 replaced with a single "DEFERRED" marker
  paragraph that points to `out-of-scope.jsonl` and states the two prerequisites that must be built in
  `skills/self/spawn/run.sh` before the feature can be accurately specified.
- Removed Group S artefacts from `verification-architecture.md`: PROP-S1..S14 (replaced with a deferred
  comment), PROP-R6 (spawn isolation), PROP-E2E-2 (spawn E2E), SE-01..SE-07 fixtures, INT-T10..T13/T16
  (spawn integration tests), spawnEligible hypothesis sweep, spawn step 9 in E2E procedure.
- Updated feature `Purpose` to say "trading earn slot only; spawn deferred to `spawn-child-earn`".
- Removed `spawnEligible` from Pure Core purity boundary in both spec files.
- Removed spawn-related Effectful Shell entries (seed transfer, git clone + install.sh, child boot,
  children.jsonl append).
- Removed `colony_ledger` tracked quantity row.
- Removed spawn params from `risk_config` (`spawn_threshold_usdc`, `spawn_net_pos_days`,
  `spawn_rate_cap_days`, `spawn_seed_usdc`, `tithe_pct`).
- Removed NFR-3, NFR-6, NFR-8 (spawn-specific NFRs); renumbered/rewrote remaining NFRs.
- Removed EDGE-S1..S5 from Edge Case Catalog.
- Removed "Parent-provisioned venue policy" sub-paragraph from REQ-T10 (spawn policy propagation
  deferred); removed spawned-child acceptance criterion from REQ-T10.
- Anti-Slop commitments updated to remove spawn and tithe references.

**Nothing lost**: all deferred content is preserved verbatim in `out-of-scope.jsonl`.

### 2. FIND-022 fix (CRITICAL for correctness): REQ-T8(b) payout formula + PROP-T26

The formula `gross_payout_usdc = position_size_usdc × settlement_price` is dimensionally wrong for a
Polymarket CTF binary redemption. For a YES/NO outcome share:
- The CLOB sells outcome shares at `entry_price` USDC each (e.g. 0.65 for YES at 65¢).
- The actual USDC spent is `filled_size` (recorded in `risk_state.open_positions`).
- The number of shares held is `shares_held = filled_size / entry_price`.
- On a winning outcome, the CTF Exchange redeems each share for exactly $1.00 USDC.
- Therefore: `gross_payout_usdc = shares_held × $1.00 = (filled_size / entry_price) × 1.00`

**Actions taken:**
- Added `filled_size` to `risk_state.open_positions` schema in Tracked Quantities (alongside existing
  `entry_price`); defined `shares_held = filled_size / entry_price` as a computed quantity (not stored).
- Rewrote REQ-T8(b) condition-2 to use `gross_payout_usdc = shares_held × $1.00` with ±1 raw 6-decimal
  unit tolerance; explicitly noted that `settlement_price` is NOT a valid formula term.
- Rewrote PROP-T26 to reference the new formula; stub assertion now checks
  `amount = round(filled_size/entry_price * 1e6) ±1` (deterministically checkable).
- PROP-T26b unchanged in substance (still rejects non-allowlist `from` transfers).
- PROP-S11 (which tested a non-existent seed-transfer step) is gone via the Group S deferral.

### 3. FIND-023 fix (low): vestigial `jurisdiction`/`venue` args removed from `jurisdictionVenueFilter`

The `jurisdiction` and `venue` string parameters were never used in the function body (return depends
only on the two booleans). They are dead inputs that create a name-vs-behavior mismatch for a function
intended as formally verifiable.

**Actions taken:**
- Renamed to `jurisdictionVenueFilter(jurisdiction_ok_for_real, kyc_required)` (2-arg form) everywhere:
  - Pure Core table in both spec files
  - REQ-T10 body text
  - PROP-T14, PROP-T14b, PROP-T15, PROP-T15b, PROP-T16 (all test call-sites updated to drop the
    vestigial string args)
  - INT-T7 description unchanged in substance (tests the 3 branches via menu.json read → effectful
    shell extracts booleans → calls 2-arg function)
- The effectful shell's role (reading `menu.venues[venue].*` and passing booleans as explicit args) is
  unchanged; only the pure function's public arity is narrowed to match its actual semantics.

## Previously resolved findings (kept intact)

FIND-001, FIND-002, FIND-003, FIND-005, FIND-007 (iter-1/2), FIND-015, FIND-017, FIND-018 (iter-3):
all intact. No regressions introduced.

## State after this iteration

- `behavioral-spec.md`: trading-only, internally consistent for Group T + R.
- `verification-architecture.md`: trading-only proof obligations; all spawn PROPs replaced by deferred
  comments pointing to `out-of-scope.jsonl`.
- `out-of-scope.jsonl`: single JSONL row with full verbatim Group S content + findings.
- Open finding count: 0 trading-side / 5 spawn-side (all deferred to `spawn-child-earn`).
