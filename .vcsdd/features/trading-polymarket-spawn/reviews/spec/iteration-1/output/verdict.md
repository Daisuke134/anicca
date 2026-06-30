# VCSDD Phase-1c Spec-Review Verdict — trading-polymarket-spawn (iteration 1)

- **feature**: trading-polymarket-spawn
- **mode**: lean
- **iteration**: 1
- **reviewType**: spec (Phase 1c gate)
- **overallVerdict**: **FAIL**
- **timestamp**: 2026-07-01

Fresh-context, disk-only review. The spec makes multiple load-bearing claims about the live
`~/anicca` runtime that are FALSE when checked against the actual source, and the two most
safety-critical guarantees (child self-pays from its own seed; realized-PnL-only earn recording)
are not achievable with the inherited runtime/skeleton as written.

## Per-dimension verdicts

| Dimension | Verdict | Findings |
|-----------|---------|----------|
| Spec Fidelity | **FAIL** | FIND-002, FIND-011 |
| Edge Case Coverage | **FAIL** | FIND-006, FIND-007 |
| Implementation Correctness | **FAIL** | FIND-001, FIND-004, FIND-005, FIND-008, FIND-010, FIND-012 |
| Structural Integrity | **FAIL** | FIND-013 |
| Verification Readiness | **FAIL** | FIND-003, FIND-009 |

overallVerdict = FAIL (any dimension FAIL ⇒ FAIL). 13 findings: 4 critical, 3 high, 6 medium.

---

## CRITICAL

### FIND-001 — Wallet path is `$HOME/.automaton/wallet.json`, NOT `$ANICCA_HOME`; child self-pay + isolation are impossible
- dimension: implementation_correctness · category: purity_boundary / security_surface · severity: critical
- The whole spec assumes "each instance's own `~/.automaton/wallet.json` under its `ANICCA_HOME`"
  (REQ-R1 spec.md:402, REQ-R2 spec.md:410, REQ-S5 spec.md:329). The real runtime resolves the EVM
  wallet from `process.env.HOME`, never `ANICCA_HOME`:
  - `runtime/compute-proxy/proxy.mjs:9` — `const walletPath = (process.env.HOME || "") + "/.automaton/wallet.json";`
  - `skills/earn/execute-yield.mjs:54` — `fs.readFileSync(process.env.HOME + "/.automaton/wallet.json", ...)`
  - `skills/earn/hl-trade/hl.py:44` — `open(os.path.expanduser("~/.automaton/wallet.json"))`
  - `runtime/anicca-daemon.sh:54` — `node -e 'require(process.env.HOME+"/.automaton/wallet.json")'`
- A spawned child (REQ-S2 writes `$CHILD_HOME/.automaton/wallet.json`, spec.md:273) shares the same
  `$HOME` as the parent (same host, only `ANICCA_HOME` differs). Therefore the child's compute-proxy,
  yield, and trade code all read the PARENT's `$HOME/.automaton/wallet.json`. The child's seeded wallet
  is never used; the parent's wallet pays for and signs the child's trades. This is the exact
  "spawn loop spending parent funds unsafely" failure mode, plus a wallet-collision/isolation break
  (REQ-R2's own acceptance criterion). The spec does not require modifying proxy/daemon/execute-yield
  to honor `ANICCA_HOME`, so as written it is infeasible and money-unsafe.

### FIND-002 — INV-7 earn gate (skeleton REQ-G2) cannot verify Polymarket/Kalshi/Hyperliquid settlements; on-chain settlement is explicitly OUT OF SCOPE
- dimension: spec_fidelity · category: requirement_mismatch / verification_tool_mismatch · severity: critical
- REQ-T8 (spec.md:202-219) records earn via the skeleton's REQ-G2 three-check gate. But the inherited
  skeleton spec scopes that gate to off-chain JSON payout processors and EXPLICITLY defers on-chain
  settlement: earn-shared-skeleton/specs/behavioral-spec.md:578-589 — "NO MVP slot settles directly
  via `eth_getLogs` or Solana RPC. On-chain raw-unit settlements (wei_uint256, lamport_uint64) are
  declared OUT OF SCOPE … will be added by a future feature." The allowlist (`payout-endpoint-allowlist.json`)
  enumerates Coconala/Stripe/Whop/Algora/Amazon only (skeleton:537-581) — there is NO Polymarket,
  Kalshi, or Hyperliquid entry, and units are `jpy_int`/`usdc_float_6dp`, not on-chain settlement.
- REQ-T8's receipt is `settlement_tx_hash_or_venue_payout_id` (spec.md:206) — precisely the on-chain
  case the skeleton cannot verify. Consequently either (a) every pm-trade earn row fails the gate and
  no earnings are ever recorded (E2E-1, verification-architecture.md:175, can never pass), or (b) the
  gate is bypassed = an INV-7 faked-earn path. The spec neither adds the venue allowlist entries nor
  extends the unit/comparison enums, so the INV-7 guarantee it leans on does not exist for this slot.

### FIND-003 — `riskGate` is declared pure with no network, but its conditions require `current_balance`, which is neither in its signature nor in `risk_state`
- dimension: verification_readiness · category: purity_boundary · severity: critical
- verification-architecture.md:18 fixes the signature `riskGate(risk_state, position_usdc, config)` and
  spec.md:129-130 mandates "pure … No file read, no network call inside `riskGate`." Yet REQ-T4's table
  (spec.md:113, 115) evaluates `(risk_state.peak_balance − current_balance) ≥ …` and
  `current_balance − position_usdc < gas_reserve_usdc`, and row 5 needs `edge ≤ 0`. Neither
  `current_balance` nor `edge` is a parameter, and the documented `risk_state` fields
  (Tracked Quantities, spec.md:44) contain `session_start_balance, peak_balance, daily_loss_usdc,
  drawdown_usdc, open_positions, paper_mode, paper_pass_count, last_daily_reset_ts` — no
  `current_balance`, no `edge`. `current_balance` is the live wallet balance (an RPC read). The function
  as specified cannot compute its own predicates while staying pure. PROP-T6/T8/T9/T11 are therefore
  unverifiable as written — the contract is internally contradictory.

### FIND-004 — Child brain bootstrap shares the parent's `:8402` ClawRouter on the parent's wallet; "child self-pays its own inference" is unachievable
- dimension: implementation_correctness · category: security_surface / faked-feasibility · severity: critical
- REQ-S5 (spec.md:329) claims the child "self-pays its own inference from `child_wallet_base` via x402"
  and binds compute on `parent_port + 1`. The real `anicca-daemon.sh` ensure_brain (lines 47-61):
  (a) only starts a brain when `:$PORT` is NOT already answering (line 58 `curl -sf …/v1/models`);
  on a shared host the parent's ClawRouter already answers on 8402, so the child starts none;
  (b) derives the brain key from `$HOME/.openclaw/.env::BLOCKRUN_WALLET_KEY` then `$HOME/.automaton/wallet.json`
  (lines 53-54, `process.env.HOME`), i.e. the parent/OpenClaw wallet — never `$CHILD_HOME`;
  (c) the in-code comment states ClawRouter "is :8402-only (no port split)" (line 51), contradicting the
  spec's `parent_port + 1` plan. Net: a spawned child's inference is paid by the parent's (or OpenClaw's)
  wallet, draining parent funds, and the "self-funded child" claim is false. No REQ modifies the daemon
  to isolate the child brain/wallet.

---

## HIGH

### FIND-005 — REQ-R5 misnames the runtime: `yield-keeper.mjs` does not compute/deploy; `execute-yield.mjs` does. The change target and its test are wrong, and the isolation fails OPEN
- dimension: implementation_correctness · category: requirement_mismatch / verification_tool_mismatch · severity: high
- spec.md:435 asserts "`runtime/yield-keeper.mjs` deterministically deploys ALL idle USDC above
  COMPUTE_RESERVE_USDC." False: `yield-keeper.mjs` only `spawn`s `execute-yield.mjs` on a 6h interval and
  passes `COMPUTE_RESERVE_USDC` (yield-keeper.mjs:32-52). The surplus math `surplus = liquid - RESERVE`
  and the actual deposit live in `execute-yield.mjs:103-152`. `RESERVE` is read ONCE at module load
  (yield-keeper.mjs:25; execute-yield.mjs:43), so a per-pass `reserved.json` cannot be honored without
  restructuring the tick to re-read it. PROP-R5 (verification-architecture.md:88) says "stub
  execute-yield, assert deposit amount cap" — but stubbing execute-yield removes the very code that caps
  the deposit, so the property is untestable as described; the acceptance "yield-keeper deploys at most
  $35" (spec.md:451) attributes deployment to the wrong module.
- Money-safety: REQ-R5 itself admits the staleness path "defaults to the prior … behaviour" (spec.md:447).
  That is fail-OPEN — if the trading slot crashes/stops refreshing `reserved.json`, within one 6h tick
  `execute-yield` sweeps the trading bankroll into Beefy/Fluid, contradicting the requirement's own title
  ("trading stake must NOT be swept", spec.md:433).

### FIND-006 — Spawn double-seed TOCTOU: the "initiated" row is not an atomic lock; two concurrent passes can both transfer seed
- dimension: edge_case_coverage · category: security_surface · severity: high
- `spawnEligible` is pure over a passed-in `recent_spawns` snapshot (spec.md:247-256; PROP-S5). The only
  concurrency guard is "no row with status ∈ {initiated,…}" (REQ-S1 cond 3, spec.md:256) written AFTER
  the check (REQ-S2(e), spec.md:275). NFR-6 (spec.md:464) explicitly allows the spawn slot to run "from
  the earn pass OR as a standalone ReAct loop pick" — two passes can interleave: both read the log
  (no "initiated" yet), both pass eligibility, both append "initiated", both reach REQ-S4 and transfer
  `spawn_seed_usdc` on Base. Append-only logs (spec.md:428) provide no compare-and-swap. PROP-S13 /
  INT-T16 ("only first proceeds", verification-architecture.md:83,163) are not satisfiable without an
  OS-level lock or atomic claim, which the spec does not define. Result: parent funds double-spent.

### FIND-007 — Geoblock reroute to Kalshi requires human KYC (J8 violation) and "jurisdiction" is a hand-set flag with no real detection
- dimension: edge_case_coverage · category: security_surface / spec_gap · severity: high
- REQ-T10 (spec.md:233) reroutes a US-blocked Polymarket stake to "the next-preferred venue … (e.g.
  Kalshi, Hyperliquid)". Kalshi is a US-regulated exchange requiring SSN/identity KYC; the spec's own
  EDGE-T6 (spec.md:477) acknowledges "venue_rejected: kyc_required". A no-human-in-the-loop instance
  cannot complete Kalshi KYC, so the reroute either dead-ends (real trading impossible for US instances)
  or implies a human KYC step — a direct REQ-J8/REQ-S7.5 NO-HUMAN violation. Separately, the "geoblock"
  is only a static `menu.json` flag `jurisdiction_ok_for_real` (spec.md:231-241) — there is no IP/geo
  detection. Enforcement for real stakes is only as correct as a manually-set boolean; the spec never
  specifies who provisions `menu.json` nor that it is created fail-closed.

---

## MEDIUM

### FIND-008 — `market_p` defined two different ways (mid vs ask); Kelly sizing and edge use inconsistent prices
- dimension: implementation_correctness · category: requirement_mismatch · severity: medium
- REQ-T3 (spec.md:92) defines `market_p` as "current market implied probability from CLOB order book
  mid." REQ-T5 (spec.md:142) says "`market_p` is the current ask (buy price from CLOB)." `edge = model_p −
  market_p` and the Kelly denominator `1 − market_p` therefore use different quantities depending on which
  REQ you read, producing an inconsistent (and bias-prone) position size. The pure-function fixtures
  (KF-01.., verification-architecture.md:108) cannot be authoritative until `market_p` has one definition.

### FIND-009 — Paper→real transition depends on an "adversary PASS evidence file at the expected path" that is never defined
- dimension: verification_readiness · category: spec_gap · severity: medium
- REQ-T6 (spec.md:166-179) gates the `paper_mode:true→false` transition on an adversary PASS file, and
  PROP-T20 / INT-T4 (verification-architecture.md:65,151) test "file absent → paper stays." But no
  requirement specifies the path, filename, schema, or which adversary verdict (nightly REQ-E1 reviews
  the slot generally, not "a completed paper-log batch"). The single most important real-money gate is
  thus not concretely implementable or unambiguously checkable.

### FIND-010 — Risk caps gate ENTRY only; no forced close on breach, and perp trades carry no stop-loss (weaker than existing hl.py)
- dimension: implementation_correctness · category: security_surface · severity: medium
- `riskGate` HALT (REQ-T4, spec.md:108-119) only prevents NEW orders; nothing closes existing positions
  when daily-loss/drawdown caps trip. For Hyperliquid (a listed venue, spec.md:186) REQ-T7 exposes only
  `buy/sell/positions/close` with no stop-loss/take-profit, whereas the existing `hl.py` mandates SL+TP
  on every open (skills/earn/hl-trade/hl.py:106-112; SKILL.md:42 "ALWAYS a stop-loss"). A leveraged perp
  opened by pm-trade can therefore blow straight past the drawdown cap with no exit — the "kill switch"
  is toothless against an open position.

### FIND-011 — REQ-R2/REQ-S2 falsely attribute EVM `wallet.json` creation to `ensure-solana-wallet.mjs`; an ed25519 key is not a valid Base key
- dimension: spec_fidelity · category: requirement_mismatch · severity: medium
- REQ-R2 (spec.md:410) states `wallet.json` "is created by `ensure-solana-wallet.mjs`." That script only
  writes `solana.json` with an ed25519 keypair (ensure-solana-wallet.mjs:12, 43-54). No runtime code
  creates the EVM `wallet.json` (proxy/daemon/execute-yield/hl.py only READ it). REQ-S2(c) wants a fresh
  Base/EVM key, but a Solana ed25519 key is secp256k1-incompatible and cannot be reused as a Base key.
  The provisioning of the parent's own `wallet.json` is out-of-band/unspecified, so the spec misstates
  the runtime and leaves child EVM keygen unanchored.

### FIND-012 — `pm.py` Python deps are never installed; child install (REQ-S3) provisions none → slot inert
- dimension: implementation_correctness · category: spec_gap · severity: medium
- NFR-1 (spec.md:459) lists `requests`, `eth-account`, and the Polymarket/Kalshi SDK. `install.sh` does
  no `pip install` (install.sh:42-58 only checks for `python3`'s presence; the existing `hl.py:33-35`
  already fails closed when its SDK is absent). REQ-S3 (spec.md:291) runs `install.sh` on the child but
  never provisions Python deps, so a freshly spawned child's `earn/pm-trade` pass cannot import `pm.py`'s
  dependencies — making E2E-2 "child completes ≥1 earn pass" (verification-architecture.md:176)
  unreachable. No requirement covers dependency installation.

### FIND-013 — `pm.py` as a single 4-action adapter over three incompatible venue APIs duplicates the existing `hl.py` Hyperliquid integration
- dimension: structural_integrity · category: structural · severity: medium
- REQ-T7 (spec.md:182-201) makes one `pm.py` "thin REST adapter" speak Polymarket CLOB + Kalshi REST +
  Hyperliquid REST behind four actions. Hyperliquid already has a working, SL/TP-enforcing adapter at
  `skills/earn/hl-trade/hl.py`. Folding a second Hyperliquid path into `pm.py` duplicates that logic and
  under-abstracts three structurally different venue protocols (order books vs perps vs Kalshi contracts)
  into one undifferentiated tool. The spec should reuse `hl.py` for the perps venue and keep venue
  adapters separate; as written it invites drift between two Hyperliquid code paths.

---

## Money-safety / hunt summary

| Hunt target | Result |
|-------------|--------|
| (a) real stake lost/swept/double-spent; paper→real gated; kill-switch dimensionally correct | FAIL — FIND-005 (sweep, fail-open), FIND-006 (double-seed), FIND-009 (gate path undefined), FIND-010 (entry-only kill-switch, no perp SL) |
| (b) hidden human-in-the-loop | FAIL — FIND-007 (Kalshi KYC) |
| (c) faked-earn / INV-7 violation | FAIL — FIND-002 (G2 gate cannot verify on-chain venue settlement) |
| (d) spawn loop spending parent funds unsafely | FAIL — FIND-001, FIND-004, FIND-006 |
| (e) geoblock enforced for real stakes | FAIL — FIND-007 (flag only, no detection) |
| (f) false claims about the runtime | FAIL — FIND-001, FIND-004, FIND-005, FIND-011 |
