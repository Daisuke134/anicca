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
- `is_valid_evm_address(candidate)` — REQ-GAS-002 (gas-ETH mode addition, 2026-07-11).
- `evaluate_native_delivery(balance_before_wei, balance_after_wei, expected_wei,
  min_delivered_pct)` — REQ-GAS-004 (gas-ETH mode addition, 2026-07-11).

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
- `eth_get_balance` (added to `lib/erc20.py`, gas-ETH mode, 2026-07-11) — raw wei native-balance
  read via `eth_getBalance`, used before/after broadcast for REQ-GAS-004's independent
  verification.

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

**impl iter2 fixes FIND-002..006** (2026-07-11, addressing `reviews/impl/iteration-2/output/`
verdict FAIL / 6 findings; FIND-001-of-iteration-2, the live relay.link dry-run evidence gate,
is intentionally NOT part of this pass — it is routed to a follow-up pass that runs the real
dry-run and attaches its response as evidence):
- FIND-002 (high, secret safety, module-wide gap): iteration-1's FIND-003 sanitization
  (`_sanitized_secret_error`) was applied only to this feature's own two decode call sites.
  Moved the pattern into `lib/identity.py` as the shared `sanitized_secret_error(context, exc)`
  helper; `verify_solana_secret_file`'s decode-failure `reason` now goes through it too (never
  `str(exc)`, only the path plus the exception's class name), closing the third leak path
  reachable via `bridge.py:104`/`send_to_franklin.py:89,98` into the SAME
  `funding-ledger.jsonl`. `franklin_sol_base_refill.py` now imports the shared helper instead
  of defining its own copy. New regression test injects a fake secret through
  `verify_solana_secret_file`'s real failing path and asserts its absence from `reason`.
- FIND-003 (medium): `deps["append_ledger"]` (called from `fail()` on every refusal path plus
  five more sites) and `deps["is_killed"]()` are now wrapped fail-closed: an `append_ledger`
  failure reports on stderr and exits non-zero (never an uncaught bare traceback with zero
  audit trail); an `is_killed` failure is treated as killed=True. Two new tests cover both.
- FIND-004 (low): guarded the non-dict-truthy `quote` case at `(quote or {}).get("details")`
  itself (a relay.link rate-limit/error response could plausibly return a top-level JSON
  array) — refuses cleanly with a `skipped` ledger row instead of an uncaught `AttributeError`
  one level above `_extract_quote_usd`'s own existing guard. New test covers a list-shaped
  `relay_quote` return.
- FIND-005 (low): renamed `lib/relay_swap.py`'s `build_sign_submit_solana_tx` parameter from
  `secret_b58` to `secret_str`, matching the dual-decode (base58-or-base64) reality FIND-003-
  of-iteration-1 already established; the sole caller (`franklin_sol_base_refill.py`) passes it
  positionally, no call-site change needed.
- FIND-006 (low): this Changelog entry plus the accompanying `state.json` update are
  themselves the fix — `state.json` now records both impl-review iterations' FAIL verdicts and
  this fix cycle instead of stopping at phase `2c`.

## Gas-ETH Mode (`--gas-eth`, added 2026-07-11)

**Root cause this mode fixes** (verified live 2026-07-11): the x402 facilitator's own signer
wallet (`0x1F5b17f41524B02a4ee4d99D4158c86C942e43f3`) holds 0 Base ETH. In x402 EIP-3009
gasless settlement the FACILITATOR pays destination gas, so it must hold native Base ETH.
Franklin's own Base wallet (`0x3EcC...`) also holds ~0 Base ETH (0.0000088), so it cannot do a
normal on-chain DEX swap to acquire gas (no gas to pay for the swap itself). relay.link's
cross-chain intent path sidesteps this: the relay solver delivers the destination-chain output
and pays destination gas itself, so NO gas is needed on the source (Solana) side. Franklin still
holds Solana USDC, so relaying THAT to native Base ETH is the clean path.

Copy-not-reinvent source for this mode's currency id (verified live 2026-07-11 via
`firecrawl scrape`, both endpoints checked):
- https://docs.relay.link/references/api/get-quote (the exact deprecated `/quote` endpoint this
  codebase's `RELAY_API` constant already targets) — its own documented example request/response
  uses `"originCurrency": "0x0000000000000000000000000000000000000000"` /
  `"destinationCurrency": "0x0000000000000000000000000000000000000000"` to swap Base ETH (chain
  8453) for Optimism ETH (chain 10) — confirming the all-zero address is relay.link's sentinel
  for "this chain's native currency", not a USDC-specific quirk.
- https://docs.relay.link/references/api/get-quote-v2 — identical request/response shape,
  confirming the same sentinel and the same `details.currencyIn`/`currencyOut` object shape
  (`amount` [raw base units, string], `amountFormatted`, `amountUsd`, `minimumAmount`) this
  feature's existing `_extract_quote_usd` already parses `amountUsd` from; this mode adds
  `_extract_quote_raw_units` to read the sibling `amount` field, since a native-ETH quote's
  wei-denominated expected output cannot be derived from its USD figure (ETH's market price is
  not ~1:1 like USDC's).
- https://docs.relay.link/features/gas-top-up — the "Gas Top-Up" feature is a DIFFERENT thing
  (adds a small amount of native gas ALONGSIDE a non-native bridged token, and explicitly cannot
  be combined with bridging TO the native token itself); this mode does not use that feature at
  all, it does a plain USDC-in/native-ETH-out swap via the same `/quote` -> sign -> submit ->
  poll flow this feature's USDC mode already implements.

### REQ-GAS-001: Same fail-closed identity resolution as REQ-001 (source leg only)
**EARS**: WHEN the CLI is invoked with `--gas-eth` THE SYSTEM SHALL resolve the SAME
Franklin-own Solana signing secret via the identical ANICCA_HOME-gated resolver REQ-001
describes (no separate resolution path), used only to sign/read-balance on the SOURCE (Solana)
side.
**Edge Cases**: identical to REQ-001 (unset ANICCA_HOME, malformed secret, resolver failure).
**Acceptance Criteria**: identical to REQ-001's acceptance criteria; `derive_pubkey` and the
real signing call both go through `lib/identity.py`'s `keypair_from_secret_string`/
`sanitized_secret_error`, unchanged from REQ-001.

### REQ-GAS-002: Explicit `--recipient` required — no default, no citizens.json lookup
**EARS**: WHEN `--gas-eth` is invoked THE SYSTEM SHALL require an explicit `--recipient` Base
EVM address argument and SHALL refuse (no quote, no identity-independent action beyond the
kill-switch check) if it is missing or not a syntactically valid EVM address (`0x` + 40 hex
chars). THE SYSTEM SHALL NEVER derive the destination from `citizens.json` or any other
default/hardcoded address in this mode — unlike REQ-002's own-citizen binding, gas-ETH mode's
destination is an arbitrary caller-named address (e.g. the x402 facilitator's own signer
wallet, which is NOT a citizen of this colony).
**Edge Cases**:
- `--recipient` omitted entirely (`None`): refuse before resolving any identity or making any
  network call.
- `--recipient` present but malformed (wrong length, missing `0x`, non-hex characters): refuse.
- This check applies identically in dry-run and `--live` — REQ-GAS-002 is not a live-only gate.
**Acceptance Criteria**:
- `is_valid_evm_address` is a pure function (deterministic parse of a fixed hex-address format,
  not a judgment call); unit tests cover valid/None/empty/wrong-prefix/wrong-length/non-hex/
  non-string-type cases.
- `is_valid_evm_address` returns the NORMALIZED (`.strip()`-ped, lower-cased) address string on
  success, never a bare bool — the caller MUST bind `recipient` to that returned value
  immediately and use ONLY the normalized value for every downstream operation (the relay quote
  payload's `recipient` field, `build_sign_submit`, and every ledger row's destination address),
  never the original raw `--recipient` argv string. A regression test proves a whitespace-padded
  (or differently-cased) but otherwise well-formed `--recipient` reaches the relay payload AND
  every ledger row in the SAME normalized form (impl iteration-3 FIND-003 fix — closes a
  validate-vs-use mismatch where the pre-fix `is_valid_evm_address` validated a stripped LOCAL
  copy but returned only a bool, leaving every caller still using the original, unstripped
  string).
- An orchestration test asserts zero `relay_quote`/`build_sign_submit` calls when `--recipient`
  is missing or malformed.
- **Accepted residual (impl iteration-3 FIND-005)**: `is_valid_evm_address` performs syntactic
  validation ONLY (`0x` + 40 hex chars) — it does NOT perform EIP-55 checksum verification, so a
  single mistyped/transposed character in an otherwise well-formed `--recipient` passes silently,
  with no typo-detection signal (checksum-aware wallets reject a wrong-case address specifically
  to catch this class of error). This is a DELIBERATELY ACCEPTED residual, not an oversight: the
  destination is operator-supplied, fully validated (syntactically) and logged (every ledger row
  records the normalized `to` address) for a shared-infra gas-funding recipient that has no
  citizens.json/allowlist binding by design (REQ-GAS-002's whole premise is an arbitrary
  caller-named address). The only remaining defense against a mistyped address is the operator
  reading the printed dry-run plan before choosing to pass `--live`.

### REQ-GAS-003: Amount caps — smaller, separate literals from USDC mode
**EARS**: WHEN computing the gas-ETH refill amount THE SYSTEM SHALL cap it at $3.00 per
invocation AND SHALL ensure the source Solana USDC balance after the swap remains >= $3.00,
computed from a freshly-read live balance; WHEN a relay quote's fee exceeds 12% of the amount
being swapped THE SYSTEM SHALL refuse to sign/broadcast (still recording a `"skipped"` ledger
row). These caps are deliberately smaller (amount) and wider (fee%) than USDC mode's
$6.50/$5.00/8% — gas top-ups are small by design, and relay's fee% runs structurally higher on
small transfers (fixed solver/gas overhead is a bigger fraction of a small amount) — but they
are NEVER derived from or shared with USDC mode's `PER_INVOCATION_USD_CAP`/`RESERVE_USD`/
`MAX_FEE_PCT` constants; each mode's caps are independently enforced.
**Edge Cases**: identical boundary structure to REQ-003/REQ-004, evaluated against the gas-mode
literals (`GAS_PER_INVOCATION_USD_CAP`, `GAS_RESERVE_USD`, `GAS_MAX_FEE_PCT`).
**Acceptance Criteria**:
- `select_refill_amount`/`evaluate_relay_fee` (the SAME pure functions REQ-003/REQ-004 use,
  already generic over `reserve_usd`/`per_invocation_cap_usd`/`max_fee_pct`) are reused
  unchanged, called with the gas-mode literals — no new pure cap function was written.
- A unit test proves a 10% fee is refused under USDC mode's default 8% cap but allowed under gas
  mode's 12% cap, confirming the two modes' caps never accidentally share state.

### REQ-GAS-004: Single in-flight guard + independent native-ETH balance-delta verification
**EARS**: WHEN a live gas-ETH run starts THE SYSTEM SHALL read the SAME
`skills/earn/state/funding-ledger.jsonl` and refuse if a row with `step ==
"franklin_gas_eth_refill"` has an unresolved `"pending"` status (same `has_unresolved_pending`
logic as REQ-005, evaluated against the gas-mode step — a pending USDC-mode row never blocks a
gas-mode run and vice versa). WHEN a live run proceeds past all caps THE SYSTEM SHALL append a
`"pending"` row immediately after the Solana transaction is broadcast (before waiting for the
relay fill, identical ordering guarantee to REQ-006), THEN SHALL poll relay `/intents/status` to
completion, THEN SHALL independently verify delivery by (a) taking the destination fill
transaction hash relay reports, (b) fetching that Base transaction's receipt via
`eth_getTransactionReceipt` and confirming `status == "0x1"`, and (c) reading the recipient's
Base NATIVE ETH balance via `eth_getBalance` both immediately before broadcasting and after the
poll completes, requiring the delta to be >= 85% of the quote's expected raw wei output (parsed
from `details.currencyOut.amount`, NOT `amountUsd`) — and SHALL append a `"sent"` row (exit code
0) ONLY when ALL of (a)-(c) hold. Unlike REQ-006's USDC leg, a plain native-currency transfer
emits NO ERC-20 `Transfer` event log at all, so THERE IS NO tx-specific Transfer-log check
available for native ETH — the `eth_getBalance` delta itself IS the tx-specific evidence here,
not a secondary sanity-only signal (the balance-delta-is-secondary-only design of REQ-006/
FIND-004 does not apply in this mode, precisely because the finer-grained signal it exists to
supplement does not exist for native transfers).
**Edge Cases**:
- Relay reports `"success"` but the fill tx's receipt is not `status == "0x1"`: unverified ->
  `"failed"` row, non-zero exit.
- The recipient's native-ETH balance does not increase at all (delta <= 0): unverified -> the
  quote's expected amount could never have been below the 85% floor in this case either,
  `"failed"` row.
- The balance increases but by less than 85% of the quote's expected wei output (a short/partial
  fill): `"failed"` row, never silently accepted.
- relay quote response is missing/malformed `details.currencyOut.amount` (the raw-wei field):
  refuse BEFORE signing/broadcasting (there is no expected value to verify delivery against) —
  a `"skipped"` row, not `"failed"` (nothing was ever broadcast).
- relay quote response has `details.currencyOut.amount` PRESENT but non-positive (`"0"` or a
  negative value — a relay quirk/bug): refuse BEFORE signing/broadcasting, exactly like the
  missing-field case above — a non-positive `expected_wei` is not a valid quantity to verify
  delivery against, and `evaluate_native_delivery` itself also fails closed on this input (never
  a silent `min_required = 0` bypass of the 85% floor that would let ANY positive delta, however
  tiny, verify as "delivered") (impl iteration-3 FIND-002 fix).
- The receipt-fetch/balance-read RPC calls themselves raise after broadcast: the `"pending"` row
  already written is the audit trail; the run reports "needs manual reconciliation" (identical
  pattern to REQ-006's own edge case), never fabricating a `"sent"` row.
- Relay reports `"refund"`: `"failed"` row with that reason, non-zero exit.
**Acceptance Criteria**:
- `evaluate_native_delivery` is a pure function (no I/O) taking already-read before/after wei
  balances and the quote's expected wei output; unit tests cover full delivery, exactly-85%,
  just-under-85%, zero-delta, negative-delta (an unrelated concurrent outflow), zero/negative
  `expected_wei` (refused, never a bypass — impl iteration-3 FIND-002), and non-int/bool
  fail-closed inputs.
- `_extract_quote_raw_units` (the extraction feeding `expected_wei`) FAILS CLOSED — returns
  `None`, never a fabricated/coerced fallback — when `details.currencyOut.amount` is missing,
  `null`, or non-numeric; unit-equivalent orchestration tests cover all three shapes (impl
  iteration-3 FIND-001 fix, mirroring `_extract_quote_usd`'s existing missing/null/wrong-type
  coverage for the USDC mode).
- No test in this mode's suite performs real network I/O — orchestration tests inject fake
  relay/RPC clients (same convention as REQ-006's acceptance criteria).
- An orchestration test asserts the `"pending"` row is written strictly before the
  `poll_relay_status` call (same call-order-spy technique as REQ-006).
- **Operator gate (impl iteration-3 FIND-001 fix, mirroring REQ-004's own MUST gate)**: before
  this feature's own `_extract_quote_raw_units` field assumption (`details.currencyOut.amount`,
  raw wei, for the actual Solana-USDC → Base-native-ETH pair) had ever been checked against a
  real relay.link response, the only verification on record was relay.link's own STATIC
  documentation example for a DIFFERENT pair (Base-ETH↔Optimism-ETH) — the identical class of
  gap REQ-004's own MUST gate exists to close for the USDC mode's `amountUsd` fields (impl
  iteration-1 FIND-005). THE OPERATOR MUST run a real (non-signing) dry-run against the live
  `api.relay.link/quote` endpoint for this exact pair BEFORE the first `--gas-eth --live`
  invocation, and attach that raw response as evidence in this feature's `.vcsdd` directory. This
  gate has been CLOSED: a real non-signing `--gas-eth --dry-run` invocation was run 2026-07-11
  and its raw relay.link response — confirming `details.currencyOut.amount` (raw wei,
  `expected_wei=1654875211425918`) AND `currencyIn`/`currencyOut.amountUsd` both actually present
  and parseable for the real pair, not just relay's docs example — is attached at
  `.vcsdd/features/franklin-sol-base-refill/evidence/live-dryrun-gas-eth-2026-07-11.md`. This is
  a MUST gate, not a recommendation — the code's own fail-closed behavior (refuse on any
  unexpected shape) makes an unverified field assumption safe-to-attempt but NOT verified-to-
  work; only a real dry-run against the exact pair in use closes that gap, and it has now been
  closed.

### REQ-GAS-005: Dry-run-by-default, operator-invoked one-shot only (same as REQ-007)
**EARS**: identical to REQ-007, but for `--gas-eth`: WITHOUT `--live`, THE SYSTEM SHALL perform
identity resolution, recipient validation, cap evaluation, and a relay quote, THEN print the
plan and append a `"dry"` ledger row (`step == "franklin_gas_eth_refill"`), WITHOUT signing or
broadcasting; ONLY `--live` permits signing/broadcast. `--gas-eth` is NOT wired into any cron
job, loop, or wake path — operator/agent invoked, one shot per run, same as the USDC mode.
**Acceptance Criteria**: identical structure to REQ-007's; `grep -rl franklin_sol_base_refill`
across `~/.openclaw/cron/` and this repo's own loop/wake wiring still returns nothing beyond
this feature's own files (the CLI entrypoint file is unchanged, `--gas-eth` is just a new flag
on the same never-cron-wired script).

## Non-Functional Requirements
- No test in this feature's suite performs real network I/O or moves real funds — all
  relay/RPC interactions are mocked/injected (matches REQ-006's acceptance criterion).
- The signing secret is never logged, printed, or written to the ledger in any form.
- All caps (REQ-003 $6.50/REQ-003 $5.00 reserve/REQ-004 8%; REQ-GAS-003 $3.00/$3.00/12%) are
  literals in the new module, not reachable via CLI flag or env var override — mirrors
  `driver.mjs`'s "fixed literals, never process.env-overridable" precedent for money-critical
  constants.

## Changelog (gas-ETH mode)

**gas-ETH mode** (2026-07-11): added `--gas-eth`/`--recipient` (REQ-GAS-001..005) to
`franklin_sol_base_refill.py`, reusing the SAME Solana-USDC source leg, relay-quote/poll/sign/
submit flow, single-in-flight-guard idiom, and pending-row-before-wait pattern the USDC mode
already implements — only the destination currency (native ETH via relay.link's documented
`0x000...000` sentinel, not USDC) and the independent delivery-verification method
(`eth_getBalance` delta, since native transfers have no ERC-20 Transfer log to parse) differ.
New pure functions in `lib/refill_plan.py`: `is_valid_evm_address` (REQ-GAS-002),
`evaluate_native_delivery` (REQ-GAS-004); new gas-mode literals `GAS_STEP`,
`GAS_PER_INVOCATION_USD_CAP`, `GAS_RESERVE_USD`, `GAS_MAX_FEE_PCT`, `GAS_FILL_MIN_DELIVERED_PCT`,
`NATIVE_ETH_BASE`. New effectful read in `lib/erc20.py`: `eth_get_balance` (raw wei balance via
`eth_getBalance`). New orchestration function `run_gas_refill` in `franklin_sol_base_refill.py`,
tested in the new `tests/test_franklin_gas_eth_refill.py` (kept separate from the already-large
`tests/test_franklin_sol_base_refill.py`, many-small-files convention). `lib/caps.py`,
`lib/identity.py`, `lib/ledger.py`, `lib/kill_switch.py`, `lib/solana_rpc.py`,
`lib/relay_swap.py`, and every existing USDC-mode function (`run_refill`, `assert_own_citizen_row`,
`select_refill_amount`, `evaluate_relay_fee`, `has_unresolved_pending`, `build_refill_plan`,
`parse_erc20_transfer_amount`, `eth_get_transaction_receipt`) are UNCHANGED by this pass — gas
mode is purely additive.

**gas-eth impl iter1 fixes FIND-001..005** (2026-07-11, addressing
`reviews/impl/iteration-3/output/` verdict FAIL / 5 findings — the `--gas-eth` mode's OWN first
fresh-context adversary review pass):
- FIND-001 (critical, spec_fidelity + verification_readiness): REQ-GAS-004 previously had no
  MUST live-evidence gate equivalent to REQ-004's — `_extract_quote_raw_units`'s field
  assumption (`details.currencyOut.amount`) had only ever been checked against relay.link's
  static docs example for a DIFFERENT pair, never a real response for the actual
  Solana-USDC→Base-native-ETH pair. Closed: a real non-signing `--gas-eth --dry-run` was run
  2026-07-11 (`expected_wei=1654875211425918` actually resolved from the live response), evidence
  attached at `.vcsdd/features/franklin-sol-base-refill/evidence/live-dryrun-gas-eth-2026-07-11.md`,
  and REQ-GAS-004's acceptance criteria now carry the same explicit MUST gate REQ-004 has. Code
  side: `_extract_quote_raw_units` already failed closed (returned `None`, no fallback) on
  missing/null/non-numeric `amount` — this pass adds the missing test coverage for the null and
  non-numeric cases (`test_gas_quote_currency_out_amount_wei_null_refuses_before_signing`,
  `test_gas_quote_currency_out_amount_wei_non_numeric_refuses_before_signing`,
  `test_gas_quote_currency_out_wrong_type_refuses`) that exercised only the missing-key case
  before.
- FIND-002 (critical, edge_case_coverage + implementation_correctness): `evaluate_native_delivery`
  silently disabled its own 85%-floor check whenever `expected_wei <= 0` (`min_required` was
  hard-coded to `0` in that branch), so ANY positive balance delta — even 1 wei — verified as
  `True`. Fixed: `expected_wei <= 0` is now its own fail-closed refusal, checked immediately after
  the existing non-int/bool type guards, before `min_required` is ever computed. `run_gas_refill`'s
  pre-signing guard (previously only `expected_wei is None`) now also refuses on
  `expected_wei <= 0`, symmetric with the `None` case — never relying on
  `evaluate_native_delivery` alone to be the sole guard against a degenerate quote reaching a real
  broadcast. New tests: `test_evaluate_native_delivery_zero_expected_wei_refused`,
  `test_evaluate_native_delivery_negative_expected_wei_refused`,
  `test_evaluate_native_delivery_zero_expected_wei_refused_even_with_large_delta`,
  `test_gas_quote_currency_out_amount_wei_zero_refuses_before_signing`.
- FIND-003 (medium, implementation_correctness, security_surface): `is_valid_evm_address`
  validated a `.strip()`-ped LOCAL copy of its argument but returned only a bool — every
  downstream use (relay payload, `build_sign_submit`, every ledger row) kept using the ORIGINAL,
  unstripped/mixed-case `recipient` string, so a whitespace-padded (or differently-cased)
  address would pass validation yet reach production unnormalized. Fixed: `is_valid_evm_address`
  now returns the NORMALIZED (stripped, lower-cased) address string on success (`None` on
  failure); `run_gas_refill` rebinds `recipient` to that return value immediately after
  validation, so every downstream use — relay quote payload, `build_sign_submit`, every ledger
  row's `to` address — sees the identical normalized string. New tests:
  `test_is_valid_evm_address_strips_and_lowercases_whitespace_padded_address`,
  `test_gas_whitespace_padded_recipient_normalized_in_relay_payload_and_ledger`,
  `test_gas_dry_run_also_normalizes_recipient_in_ledger_row`; existing
  `is_valid_evm_address`/`evaluate_native_delivery` bool-return assertions in
  `tests/test_refill_plan.py` updated to match the new `Optional[str]` return contract.
- FIND-004 (medium, structural_integrity, non-blocking): the fail-closed ledger-append helper
  existed in two independently-maintained, byte-for-byte-identical copies (`run_refill`'s inline
  closure and the module-level `_safe_append_ledger_factory` built for `run_gas_refill`), a
  drift risk for money-safety-critical logic. Fixed: `run_refill` now calls
  `_safe_append_ledger_factory(deps)` too (mechanical, behavior-preserving — no other change to
  `run_refill`'s logic), removing the duplicate.
- FIND-005 (low, spec_fidelity, accepted residual): `is_valid_evm_address` performs syntactic
  validation only, no EIP-55 checksum — documented as a deliberately accepted residual in
  REQ-GAS-002's acceptance criteria (this pass), since the destination is operator-supplied,
  validated, and logged for a shared-infra gas-funding recipient with no allowlist binding by
  design. No code change.

All 5 findings fixed/documented; funding suite: 177/177 pass (was 167/167 before this pass — 10
new regression tests, 0 removed, 0 regressions). NOT run with `--live` in this pass — the real
$3 `--gas-eth --live` invocation remains a separate, explicit operator action after this fix
commit merges and clears its own fresh-context re-review.
