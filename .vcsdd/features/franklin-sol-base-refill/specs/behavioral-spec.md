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
- `/Users/anicca/.hermes/state/citizens.json` — the canonical multi-instance registry; the ONLY
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
- Reading `/Users/anicca/.hermes/state/citizens.json`.
- Solana RPC reads (`getBalance`/`getTokenAccountsByOwner`/`getLatestBlockhash`/
  `sendTransaction`) and Base RPC reads (`eth_call` balanceOf via `lib/erc20.py`, plus
  `eth_getTransactionReceipt` for the tx-specific fill check, impl iteration-1 FIND-004 fix).
- `POST https://api.relay.link/quote` and `GET .../intents/status`.
- Building, signing (solders `Keypair`, via `lib/identity.py`'s proven decoder), and submitting
  the Solana transaction — extracted into `skills/earn/funding/lib/relay_swap.py` (impl
  iteration-1 FIND-007 fix; `skills/earn/sol-to-usdc.py` itself is left unchanged).
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
- **Secret-safe error handling (impl iteration-1 FIND-003 fix)**: BOTH places this feature
  decodes/signs with the raw resolved secret (`derive_pubkey` and the real signing call) use
  `lib/identity.py`'s proven `keypair_from_secret_string` dual-decode helper (base58-first,
  base64-fallback — the SAME decoder `derive_pubkey` already relies on, so the two steps can
  never disagree on how to decode the same secret). If either raises, the exception's message
  text (`str(exc)`) is NEVER interpolated into a ledger row or printed output — only a fixed
  context string plus the exception's class name are recorded (`_sanitized_secret_error`),
  because the underlying decoder's exception message could otherwise embed the raw input it
  failed to parse. A unit test asserts an injected fake secret never appears as a substring of
  any ledger row or printed result on a decode failure.

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
- The orchestration layer NEVER substitutes a locally-computed value (e.g. the requested swap
  amount) for a missing `details.currencyIn`/`currencyOut` field before calling
  `evaluate_relay_fee` — a missing field must reach the pure function as an actual missing
  value (never a fabricated one), so the fail-closed check above is genuinely exercised
  (impl iteration-1 FIND-001 fix).
- **Operator gate (impl iteration-1 FIND-005 fix)**: the cited "proven"/"verified live"
  precedent (`skills/earn/sol-to-usdc.py`) never reads `details.currencyIn.amountUsd` or
  `details.currencyOut.amountUsd` — it only reads `currencyOut.amountFormatted` for a print
  statement. This means the FIRST time this feature's exact field assumption (both
  `currencyIn.amountUsd` AND `currencyOut.amountUsd` present as numeric-parseable strings on a
  real relay.link response for USDC-SPL(Solana)->USDC(Base)) is checked against production
  data will be a real `--live` invocation, unless a real network dry-run is fetched first. THE
  OPERATOR MUST run a real (non-signing) dry-run against the live `api.relay.link/quote`
  endpoint for this exact currency pair and manually inspect the returned `details` shape
  BEFORE the first `--live` invocation, and attach that raw response as evidence in this
  feature's `.vcsdd` directory. This is a MUST gate, not a recommendation — the code's own
  fail-closed behavior (refuse on any unexpected shape, per the FIND-001 fix above) makes an
  unverified field assumption safe-to-attempt but NOT verified-to-work; only a real dry-run
  closes that gap.

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

### REQ-006: Ledger + independent, TX-SPECIFIC on-chain verification before "sent"
**EARS**: WHEN a live run proceeds past all caps THE SYSTEM SHALL append a `"pending"` ledger
row immediately after the Solana transaction is broadcast (before waiting for the relay fill),
THEN SHALL poll relay `/intents/status` to completion, THEN SHALL independently verify the fill
by (a) taking the destination fill transaction hash relay reports (`txHashes[0]`), (b) fetching
that Base transaction's receipt via `eth_getTransactionReceipt`, (c) confirming the receipt's
`status == "0x1"`, and (d) parsing the receipt's logs for a USDC `Transfer` event whose `to`
equals Franklin's own Base destination address, requiring the delivered amount to be >= 85% of
the quote's expected output — and SHALL append a `"sent"` row (exit code 0) ONLY when ALL of
(a)-(d) hold. The coarse wallet-wide Base-balance-delta check (before/after `eth_call
balanceOf`) is retained ONLY as a SECONDARY sanity flag recorded on the ledger row for audit —
it never by itself upgrades a tx-unverified fill to "sent", nor does a failed sanity flag alone
downgrade a tx-verified fill to "failed" (impl iteration-1 FIND-004 fix: a wallet-wide delta
cannot distinguish this specific fill from an unrelated concurrent inflow/outflow on the same
address, e.g. a second concurrent invocation or another earn engine crediting the same wallet).
Any other outcome (relay reports failure/refund, no fill tx hash reported, receipt not success,
no matching Transfer log, delivered amount < 85% of expected, or the confirmation RPC calls
themselves raise) SHALL append a `"failed"` row and exit non-zero — relay's own "success" status
string is never sufficient proof by itself.
**Edge Cases**:
- Relay reports `"success"` but reports no `txHashes` at all, or the fill tx's receipt has no
  Transfer log naming Franklin's own address: treated as unverified -> `failed` row, non-zero
  exit (relay self-report is not trusted alone).
- A Transfer log names Franklin's own address but for less than 85% of the quote's expected
  output (a short/partial fill): `failed` row, non-zero exit — never silently accepted as
  "close enough".
- An unrelated inflow increases the wallet-wide Base balance during the same window (no
  matching Transfer log for the actual fill tx): NOT verified — the tx-specific check is
  authoritative, the balance delta alone is never sufficient.
- The receipt-fetch/Transfer-log-parse RPC call itself raises (transient network failure) after
  broadcast: the `pending` row already written is the audit trail; no `sent` row is fabricated,
  and the run reports "needs manual reconciliation" (mirrors `bridge.py`/
  `send_to_franklin.py`'s existing try/except-around-confirmation pattern) rather than crashing
  with no ledger evidence at all.
- Relay reports `"refund"`: `failed` row with that reason, non-zero exit.
**Acceptance Criteria**:
- No test path ever calls the real `api.relay.link` or a real RPC endpoint — orchestration
  tests inject fake relay/RPC clients and assert on the resulting ledger rows and exit
  behavior.
- The `pending` row is written before the code awaits the relay status poll (ordering is
  asserted directly in an orchestration test via a call-order spy).
- Orchestration tests cover: a correct fill (matching Transfer log, receipt success) verified;
  an unrelated-inflow-only case (balance moved, no matching Transfer log) NOT verified; a
  short-fill (matching Transfer log but < 85% of expected) refused/flagged.

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

## Changelog

**impl iter1 fixes FIND-001..007** (2026-07-11, addressing `reviews/impl/iteration-1/output/`
verdict FAIL / 7 findings):
- FIND-001 (critical): removed the `or amount`/`or 0` fallback that fabricated a passing
  `in_usd`/`out_usd` for `evaluate_relay_fee` when relay's quote omitted
  `currencyIn`/`currencyOut`; extraction now returns `None` on any missing/malformed field
  (`_extract_quote_usd`), letting the already-correct pure fail-closed check actually trigger.
- FIND-002 (critical): `read_citizens()` call is now wrapped in try/except, failing closed with
  a ledger row instead of crashing uncaught on a missing/unreadable/malformed citizens.json.
- FIND-003 (high, secret safety): the real signing path now uses `lib/identity.py`'s proven
  `keypair_from_secret_string` dual-decode helper (same one `derive_pubkey` uses) instead of a
  base58-only `Keypair.from_base58_string` call; both `derive_pubkey` and signing failures now
  record only a sanitized, fixed error string + exception class name, never `str(exc)`.
- FIND-004 (medium): independent fill verification is now tx-specific — fetches the relay
  fill's own Base tx receipt, confirms `status == "0x1"`, and requires a matching USDC
  `Transfer` log to Franklin's own address delivering >= 85% of the quoted output; the
  wallet-wide balance delta is retained only as a secondary sanity flag on the ledger row.
- FIND-005 (high): added an explicit operator gate (REQ-004 acceptance criteria) requiring a
  real, non-signing dry-run fetch against `api.relay.link/quote` for this exact currency pair
  before the first `--live`, since the cited precedent never exercised the `currencyIn`/
  `currencyOut.amountUsd` fields this feature's fee cap depends on.
- FIND-006 (medium): `relay_quote()` and `read_solana_balance_usd()` production wiring calls
  are now wrapped in fail-closed try/except (clean JSON + skipped ledger row, no crash); added
  orchestration tests for `derive_pubkey` raising, citizens-read failures, and network errors.
- FIND-007 (low): extracted the ALT-parsing/build/sign/submit block into
  `skills/earn/funding/lib/relay_swap.py`; `skills/earn/sol-to-usdc.py` is left untouched (it
  is proven and live under another job) with a one-line origin comment noting the future
  consolidation candidate.

## Non-Functional Requirements
- No test in this feature's suite performs real network I/O or moves real funds — all
  relay/RPC interactions are mocked/injected (matches REQ-006's acceptance criterion).
- The signing secret is never logged, printed, or written to the ledger in any form.
- All caps (REQ-003 $6.50/REQ-003 $5.00 reserve/REQ-004 8%) are literals in the new module,
  not reachable via CLI flag or env var override — mirrors `driver.mjs`'s "fixed literals,
  never process.env-overridable" precedent for money-critical constants.
