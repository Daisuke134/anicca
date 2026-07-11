# Behavioral Spec — franklin-sol-base-refill

Feature: operator-invoked, one-shot CLI that bridges Franklin's own USDC (Solana SPL) to
Franklin's own USDC (Base) via relay.link — the last funding step before the colony's first
on-chain loan (Franklin1 lender needs > $5.50 Base USDC; Franklin holds $13.02 on Solana,
$0.02 on Base at spec time).

Copy-not-reinvent sources (verified live 2026-07-11):
- `skills/earn/sol-to-usdc.py` — proven relay.link quote -> build+sign Solana tx from returned
  instructions (solders) -> submit -> poll `/intents/status` until Base fill. This feature
  adapts that pattern from native-SOL input to USDC-SPL input, and from the automaton's wallet
  to Franklin's own wallet.
- `skills/earn/funding/lib/{ledger,caps,identity,kill_switch,erc20,solana_rpc}.py` — the
  money-safety-reviewed funding harness (`MONEY-SAFETY-VERDICT.md`, 2026-07-08, PASS with
  Finding A already fixed in `bridge.py`/`send_to_franklin.py`'s pending-row-before-wait
  pattern). This feature reuses these modules unchanged and appends to the SAME
  `skills/earn/state/funding-ledger.jsonl` with `step="franklin_sol_base_refill"`.
- `skills/self/spawn-funding-swap/lib/resolve-swap-identity.mjs` — the ANICCA_HOME-gated,
  fail-closed "resolve THIS instance's own signer, never a shared-env fallback" pattern this
  feature mirrors for both legs (Solana source, Base destination).
- `skills/earn/lib/resolve-identity.mjs` (`node resolve-identity.mjs solana` CLI entrypoint) —
  the canonical, already-existing per-instance Solana secret resolver; reused via subprocess,
  never re-derived.
- `/Users/operator/.hermes/state/citizens.json` — the canonical multi-instance registry; the ONLY
  source of a citizen's own Base EVM address (never a hardcoded constant).

## Purity Boundary Analysis

**Pure core** (deterministic, no I/O, no side effects — unit-testable in isolation):
- `select_refill_amount(balance_usd, reserve_usd, per_invocation_cap_usd, requested_usd)` —
  REQ-003.
- `evaluate_relay_fee(in_usd, out_usd, max_fee_pct)` — REQ-004.
- `assert_own_citizen_row(citizens, derived_solana_pubkey)` — REQ-002.
- `has_unresolved_pending(ledger_rows, step)` — REQ-005.
- `build_refill_plan(...)` — pure assembly of the JSON plan object logged before any signing.

**Effectful shell** (I/O, network, signing — exercised only behind mocks in tests, never in
CI/unit tests):
- Subprocess call to `resolve-identity.mjs solana` (reads local wallet files).
- Reading `/Users/operator/.hermes/state/citizens.json`.
- Solana RPC reads (`getBalance`/`getTokenAccountsByOwner`/`getLatestBlockhash`/
  `sendTransaction`) and Base RPC read (`eth_call` balanceOf) via `lib/erc20.py`.
- `POST https://api.relay.link/quote` and `GET .../intents/status`.
- Building, signing (solders `Keypair`), and submitting the Solana transaction.
- Appending rows to `skills/earn/state/funding-ledger.jsonl`.

## Requirements

### REQ-001: Fail-closed own-instance identity resolution
**EARS**: WHEN the CLI is invoked THE SYSTEM SHALL resolve the signing secret exclusively via
the ANICCA_HOME-gated `resolve-identity.mjs solana` resolver, and SHALL refuse to proceed
(no quote, no balance read beyond identity checks, exit non-zero) if `ANICCA_HOME` is unset,
empty, or the resolver returns no secret.
**Edge Cases**:
- `ANICCA_HOME` unset: refuse with a reason string that names the missing gate, never fall
  back to `$HOME/.anicca` or any other instance's default home.
- Resolver returns a malformed/undecodable secret: refuse (fail closed), never treat as "no
  balance."
- Resolver subprocess exits non-zero or times out: treated identically to "no secret resolved."
**Acceptance Criteria**:
- No subprocess for `resolve-identity.mjs` is spawned at all when `ANICCA_HOME` is unset.
- The secret itself is never written to stdout/stderr/logs/ledger by this feature's own code
  (only the derived PUBLIC key ever appears in plan/ledger rows).

### REQ-002: Own-citizen destination binding (never hardcoded, never cross-instance)
**EARS**: WHEN a Solana secret is resolved THE SYSTEM SHALL derive its public key, look up the
citizens.json row whose `walletAddress.solana` equals that derived public key, and SHALL use
ONLY that row's `walletAddress.evm` as the Base destination address.
**Edge Cases**:
- No citizens row matches the derived Solana public key: refuse (fail closed) — this is the
  "never a cross-instance destination" rail; a mismatch means the resolved key is not the
  citizen we think it is, or the registry is stale.
- Multiple rows match (registry corruption): refuse — ambiguous destination is treated as
  unresolved, never "pick the first."
- citizens.json missing/unreadable/malformed JSON: refuse.
**Acceptance Criteria**:
- The Base destination address used in the relay quote/transfer is byte-for-byte the matched
  row's `walletAddress.evm` — never a literal/env-overridable constant.
- A unit test constructs a citizens fixture where the derived pubkey does NOT match any row and
  asserts refusal with no relay quote issued.

### REQ-003: Amount caps — per-invocation ceiling + live-balance reserve
**EARS**: WHEN computing the refill amount THE SYSTEM SHALL cap it at $6.50 per invocation AND
SHALL ensure the source Solana USDC balance after the swap remains >= $5.00, computed from a
freshly-read live balance (never a cached/assumed figure); WHEN either bound cannot be
satisfied THE SYSTEM SHALL refuse with amount_usd <= 0 and take no further action.
**Edge Cases**:
- Live balance <= $5.00 (reserve already exhausted or would be): refuse, amount_usd = 0.
- Live balance between $5.00 and $11.50: amount = balance - $5.00 (below the $6.50 cap).
- Live balance >= $11.50: amount = $6.50 (the per-invocation cap binds).
- An explicit `--amount-usd` request above what caps allow: clip to the smaller bound, never
  raise it.
- An explicit `--amount-usd` request of 0 or negative: refuse (reject non-positive amounts).
**Acceptance Criteria**:
- `select_refill_amount` is a pure function with no default-mutation of its inputs, tested at
  each boundary above (>=6 cases: exact reserve, exact cap, below-both, above-both, explicit
  override below/above the derived ceiling).

### REQ-004: Relay quote economic-sanity cap
**EARS**: WHEN a relay.link quote is returned THE SYSTEM SHALL compute
`fee_pct = (in_usd - out_usd) / in_usd * 100` and SHALL refuse to sign/broadcast (still
recording the quote in a `"skipped"` ledger row) if `fee_pct > 8`.
**Edge Cases**:
- `in_usd == 0` (malformed quote): fail closed (fee_pct treated as unevaluable -> refuse).
- `out_usd > in_usd` (should not happen, but a quote glitch could report it): fee_pct <= 0,
  always passes the cap (never itself a refusal reason).
- Missing `details.currencyIn`/`currencyOut` fields entirely: refuse (cannot verify economics).
**Acceptance Criteria**:
- `evaluate_relay_fee` is a pure function; unit tests cover exactly-8%, just-under, just-over,
  and the malformed-quote refusal.

### REQ-005: Single in-flight guard (ledger-idiom lock)
**EARS**: WHEN the CLI starts a live run THE SYSTEM SHALL read
`skills/earn/state/funding-ledger.jsonl`, and IF a row with
`step == "franklin_sol_base_refill"` and `status == "pending"` exists with no later row of the
SAME step whose `tx_hash`/`signature` reaches a terminal status (`sent`/`failed`) for that same
identifier, THE SYSTEM SHALL refuse to start a new live run (dry-run/quote-only mode is still
permitted for observability).
**Edge Cases**:
- Two pending rows for different tx hashes, neither terminal: refuse (any unresolved pending
  blocks a new live run).
- A pending row followed by a terminal row for the SAME tx hash: not blocking (the prior run
  finished, one way or another).
- Empty/missing ledger file: never blocking (first run).
**Acceptance Criteria**:
- `has_unresolved_pending` is a pure function over a list of ledger row dicts; unit tests cover
  no-rows, resolved-pending, and unresolved-pending cases.

### REQ-006: Ledger + independent on-chain verification before "sent"
**EARS**: WHEN a live run proceeds past all caps THE SYSTEM SHALL append a `"pending"` ledger
row immediately after the Solana transaction is broadcast (before waiting for the relay fill),
THEN SHALL poll relay `/intents/status` to completion, THEN SHALL independently verify the fill
by reading Franklin's Base USDC balance via `eth_call` (same `balanceOf` pattern as
`lib/erc20.py`) before and after, and SHALL append a `"sent"` row (exit code 0) ONLY when the
post-run Base balance increased by an amount consistent with the quote's expected output
(within a tolerance); any other outcome (relay reports failure/refund, balance did not
increase, or the confirmation RPC call itself raises) SHALL append a `"failed"` row and exit
non-zero — relay's own "success" status string is never sufficient proof by itself.
**Edge Cases**:
- Relay reports `"success"` but the Base balance delta is ~0: treated as unverified -> `failed`
  row, non-zero exit (relay self-report is not trusted alone).
- The balance-delta RPC call itself raises (transient network failure) after broadcast: the
  `pending` row already written is the audit trail; no `sent` row is fabricated, and the run
  reports "needs manual reconciliation" (mirrors `bridge.py`/`send_to_franklin.py`'s existing
  try/except-around-confirmation pattern) rather than crashing with no ledger evidence at all.
- Relay reports `"refund"`: `failed` row with that reason, non-zero exit.
**Acceptance Criteria**:
- No test path ever calls the real `api.relay.link` or a real RPC endpoint — orchestration
  tests inject fake relay/RPC clients and assert on the resulting ledger rows and exit
  behavior.
- The `pending` row is written before the code awaits the relay status poll (ordering is
  asserted directly in an orchestration test via a call-order spy).

### REQ-007: Dry-run-by-default, operator-invoked one-shot only
**EARS**: WHEN the CLI is invoked WITHOUT the `--live` flag THE SYSTEM SHALL perform identity
resolution, citizens-row binding, cap evaluation, and a relay quote, THEN SHALL print the
resulting plan and append a `"dry"` ledger row, WITHOUT signing or broadcasting anything; ONLY
`--live` SHALL permit signing/broadcast. THE SYSTEM SHALL NOT be referenced from any cron
job, loop, or wake path — it is invoked directly by an operator/agent, one shot per run.
**Edge Cases**:
- Both `--live` and no explicit mode given: default is dry-run (never live-by-default).
- `--dry-run` passed alongside `--live`: `--dry-run` wins (never silently go live when a
  dry-run flag is present).
**Acceptance Criteria**:
- `grep -rl franklin_sol_base_refill` (or the script's filename) across `~/.openclaw/cron/`
  and this repo's own loop/wake wiring returns nothing beyond this feature's own files/docs.
- A test asserts that omitting `--live` never reaches the signing/broadcast code path (spied
  and asserted as zero calls).

## Non-Functional Requirements
- No test in this feature's suite performs real network I/O or moves real funds — all
  relay/RPC interactions are mocked/injected (matches REQ-006's acceptance criterion).
- The signing secret is never logged, printed, or written to the ledger in any form.
- All caps (REQ-003 $6.50/REQ-003 $5.00 reserve/REQ-004 8%) are literals in the new module,
  not reachable via CLI flag or env var override — mirrors `driver.mjs`'s "fixed literals,
  never process.env-overridable" precedent for money-critical constants.
