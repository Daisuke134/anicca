# Verification Architecture — franklin-sol-base-refill

## Purity Boundary Map
- **Pure Core** (`skills/earn/funding/lib/refill_plan.py`, new module): `select_refill_amount`,
  `evaluate_relay_fee`, `assert_own_citizen_row`, `has_unresolved_pending`, `build_refill_plan`.
  Deterministic, no I/O, no network, no clock/randomness dependence (a `now_ts` is always
  passed in, never read from `time.time()` inside pure functions). Also
  `parse_erc20_transfer_amount` (added to the existing `lib/erc20.py`, impl iteration-1
  FIND-004 fix) — a pure parse of a tx receipt's `logs` array, no I/O.
- **Effectful Shell** (`skills/earn/funding/franklin_sol_base_refill.py`, new CLI, plus the new
  `skills/earn/funding/lib/relay_swap.py`): resolves identity via subprocess, reads
  citizens.json, reads Solana/Base balances and tx receipts over RPC, calls relay.link
  `/quote` and `/intents/status`, builds+signs+submits the Solana transaction (solders), and
  appends ledger rows. Every effectful call is behind a small injectable interface (`deps`
  dict of callables) so orchestration tests can substitute fakes — mirrors
  `spawn-funding-swap`'s `SPAWN_FUNDING_SWAP_FAKE_DEPS_MODULE` test seam, adapted to Python via
  plain dependency-injected functions (simpler for a lean, one-shot script; no need for an
  env-var-gated dynamic import).

## Proof Obligations
| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-001 | `select_refill_amount` never returns > per_invocation_cap_usd | 1 | true | pytest (property-style boundary table) |
| PROP-002 | `select_refill_amount` never returns an amount that would drop live balance below reserve_usd | 1 | true | pytest |
| PROP-003 | `select_refill_amount` never returns a negative amount | 1 | true | pytest |
| PROP-004 | `evaluate_relay_fee` refuses (ok=false) whenever fee_pct > 8, allows at exactly 8 | 1 | true | pytest boundary cases |
| PROP-005 | `assert_own_citizen_row` refuses on zero matches AND on >1 matches (never picks-first) | 1 | true | pytest |
| PROP-006 | `has_unresolved_pending` is symmetric: any pending row without a later terminal row for the same id blocks, regardless of row order/count | 1 | true | pytest |
| PROP-007 | `build_refill_plan` never mutates its input dicts (matches `lib/ledger.py`'s existing `build_row` non-mutation contract) | 1 | true | pytest identity-equality check on the input after the call |
| PROP-008 | Orchestration: `--live` without a resolved identity never reaches the signing code path | 2 | true | pytest with a spy dep that asserts zero calls |
| PROP-009 | Orchestration: the `pending` ledger row is appended strictly before the relay-status-poll call | 2 | true | pytest call-order spy |
| PROP-010 | Orchestration: a `"sent"` row is appended only when the injected Base-balance-delta check returns a verified increase; a relay `"success"` string alone never triggers `"sent"` | 2 | true | pytest with a fake relay client reporting success + a fake balance reader reporting no delta |
| PROP-011 | Orchestration: omitting `--live` never invokes the sign/broadcast dep | 2 | true | pytest |
| PROP-012 | No test in this suite performs real network I/O (static grep: no `requests.get/post` or `urllib.request.urlopen` call outside `franklin_sol_base_refill.py`/`lib/*.py` production code, i.e. never inside `tests/`) | 0 | true | grep check documented in test-run notes |
| PROP-013 | The orchestration layer never substitutes a locally-computed value for a missing `details.currencyIn`/`currencyOut.amountUsd`; a missing/null/wrong-type field reaches `evaluate_relay_fee` as `None`, never a fabricated number (FIND-001) | 2 | true | pytest with malformed-quote fixtures (missing key, null, wrong type) |
| PROP-014 | `read_citizens()` failures (missing file, malformed JSON, empty registry) are caught and produce a `failed` ledger row + non-zero exit, never an uncaught crash (FIND-002) | 2 | true | pytest with a raising fake `read_citizens` dep |
| PROP-015 | Any exception raised while decoding/signing with the raw resolved secret (`derive_pubkey`, `build_sign_submit`) never has `str(exc)` written to a ledger row or printed result; an injected fake secret is asserted absent from all ledger rows and the result JSON on a decode failure (FIND-003) | 2 | true | pytest asserting substring-absence over `json.dumps(row)`/`json.dumps(result)` |
| PROP-016 | A `"sent"` row requires ALL of: a relay-reported fill tx hash, that tx's receipt `status == "0x1"`, and a matching USDC Transfer log to our own address delivering >= 85% of the quote's expected output; a wallet-wide balance increase alone (no matching Transfer log) never triggers `"sent"`, and a flat/failed balance-delta sanity flag alone never downgrades a tx-verified fill to `"failed"` (FIND-004) | 2 | true | pytest with fake relay/receipt fixtures: correct fill, unrelated-inflow-only, short-fill (<85%) |
| PROP-017 | `parse_erc20_transfer_amount` (pure) correctly matches/ignores logs by token address, recipient address, and event topic, and never raises on malformed log shapes | 1 | true | pytest boundary/malformed-shape table |
| PROP-018 | `is_valid_evm_address` accepts only well-formed `0x` + 40 hex-char strings and returns the NORMALIZED (stripped, lower-cased) address string on success (never a bare bool); rejects (returns `None`) on None, empty, wrong prefix, wrong length, non-hex chars, non-string types (REQ-GAS-002; impl iteration-3 FIND-003 fix) | 1 | true | pytest boundary table, incl. whitespace-padded/mixed-case normalization assertions |
| PROP-019 | `evaluate_native_delivery` never verifies a non-positive or negative wei delta, never verifies a delta below `min_delivered_pct` of `expected_wei`, and never verifies when `expected_wei` itself is <= 0 (fails closed, never a `min_required=0` bypass — impl iteration-3 FIND-002 fix); fails closed on non-int/bool inputs (REQ-GAS-004) | 1 | true | pytest boundary table (full delivery, exactly-85%, just-under-85%, zero-delta, negative-delta, zero/negative expected_wei, non-int/bool) |
| PROP-020 | Gas-ETH mode's `select_refill_amount`/`evaluate_relay_fee` calls (reused pure functions) never share cap state with USDC mode's calls -- a 10% fee is refused under `MAX_FEE_PCT`=8 but allowed under `GAS_MAX_FEE_PCT`=12 (REQ-GAS-003) | 1 | true | pytest, same fee inputs evaluated against both cap constants |
| PROP-021 | Orchestration: `run_gas_refill` with a missing or malformed `recipient` never calls `relay_quote`/`build_sign_submit`, in both dry-run and `--live` (REQ-GAS-002) | 2 | true | pytest with a spy dep asserting zero calls |
| PROP-022 | Orchestration: `run_gas_refill`'s single-in-flight guard (`GAS_STEP`) is independent of USDC mode's (`STEP`) -- a pending row of one step never blocks a live run of the other (REQ-GAS-004) | 2 | true | pytest with cross-step pending-row fixtures |
| PROP-023 | Orchestration: a `"sent"` gas-ETH row requires ALL of a relay-reported fill tx hash, that tx's receipt `status == "0x1"`, and `evaluate_native_delivery(...).verified == True`; a flat/negative/short native-balance delta alone never triggers `"sent"` (REQ-GAS-004) | 2 | true | pytest with fake relay/RPC fixtures: correct fill, flat delta, short fill (<85%), reverted receipt |
| PROP-024 | Orchestration: `run_gas_refill` refuses BEFORE broadcasting when `details.currencyOut.amount` (raw wei) cannot be extracted from the relay quote (missing/null/non-numeric) OR is present but non-positive, even if `details.currencyOut.amountUsd`/the fee check both look fine (REQ-GAS-004; impl iteration-3 FIND-001/FIND-002 fixes) | 2 | true | pytest with quote fixtures: missing/null/non-numeric/zero `amount` field |
| PROP-025 | Orchestration: `run_gas_refill` normalizes `recipient` ONCE (via `is_valid_evm_address`'s return value) and uses the SAME normalized string in the relay quote payload, `build_sign_submit`, and every ledger row — a whitespace-padded/mixed-case `--recipient` never reaches production unnormalized (REQ-GAS-002; impl iteration-3 FIND-003 fix) | 2 | true | pytest asserting the relay-payload `recipient` field and every ledger row's `to` address equal the normalized form |

## Verification Strategy
- **Tier 0** (no formal proof needed): CLI argument parsing, print/JSON-output formatting,
  the "not wired into cron" acceptance check (a repo-wide grep, run manually per REQ-007).
- **Tier 1** (property-style unit tests over pure functions): all of `refill_plan.py`'s pure
  functions (PROP-001..007) — exhaustive boundary-table tests, no mocks needed since there is
  no I/O to mock.
- **Tier 2** (orchestration tests with injected fakes): the CLI's `main()`/`run_refill()`
  control flow (PROP-008..011) — fake identity resolver, fake citizens reader, fake relay
  client, fake Solana/Base balance readers, fake ledger (in a `tmp_path`), asserting on call
  order, ledger rows written, and exit codes. No live network, no real keys, matches the
  existing `skills/earn/funding/tests/` convention (pure/offline pytest, `tmp_path` fixtures).
- **Tier 3** (strong formal proof): not applicable — this is a lean, bounded, one-shot
  operator tool, not a protocol or concurrent data structure; the money-safety invariants
  (caps, reserve, single-flight, on-chain-verify-before-sent) are fully covered by Tier 1/2
  property tests plus the existing `MONEY-SAFETY-VERDICT.md` review of the reused
  `lib/{caps,identity,ledger,solana_rpc,kill_switch}.py` modules (no changes to those files in
  this feature — reused as-is) plus this iteration's own PROP-013..017 tests covering the
  additions to `lib/erc20.py` (`eth_get_transaction_receipt`, `parse_erc20_transfer_amount`,
  impl iteration-1 FIND-004 fix — `lib/erc20.py`'s pre-existing functions are unchanged, only
  new functions were appended).

## Changelog

**gas-ETH mode** (2026-07-11): added PROP-018..024 (see table above) covering the new
`is_valid_evm_address`/`evaluate_native_delivery` pure functions (Tier 1) and `run_gas_refill`'s
orchestration (Tier 2). Purity Boundary Map additions: `is_valid_evm_address`,
`evaluate_native_delivery` (both pure, `lib/refill_plan.py`); `eth_get_balance` (effectful,
`lib/erc20.py`, mirrors `erc20_balance_units`'s raw-RPC-call contract but for native currency).
No changes to Tier 3 rationale -- gas-ETH mode is the same class of lean, bounded, one-shot
operator tool as USDC mode, with its own caps/reserve/single-flight/on-chain-verify-before-sent
invariants fully covered by these new Tier 1/2 property tests.

**impl iter1 fixes FIND-001..007** (2026-07-11): added PROP-013..017 (see table above) covering
the orchestration-layer fail-closed fixes; `parse_erc20_transfer_amount` (new, in `lib/erc20.py`)
is a pure function added to the Purity Boundary Map's reusable-primitives set (it performs no
I/O, unlike its sibling `eth_get_transaction_receipt` in the same module, which is effectful);
the ALT-parsing/build/sign/submit block moved out of `franklin_sol_base_refill.py`'s effectful
shell into `skills/earn/funding/lib/relay_swap.py` (FIND-007) — still effectful, still
dependency-injected as the `build_sign_submit` dep, only the module location changed.

**gas-eth impl iter1 fixes FIND-001..005** (2026-07-11): added PROP-025 (recipient
normalization); revised PROP-018 (`is_valid_evm_address` now returns the normalized address
string, not a bool), PROP-019/024 (both now cover `expected_wei <= 0` as a fail-closed refusal,
not just missing/`None`). No Purity Boundary Map changes — `is_valid_evm_address` and
`evaluate_native_delivery` remain pure (return-type change only, still no I/O); the
`_safe_append_ledger_factory`/`run_refill` ledger-append dedupe (FIND-004) is a structural,
behavior-preserving refactor of the effectful shell, not a new proof obligation.

## Reused, Not Re-Verified
`lib/caps.py`, `lib/identity.py`, `lib/ledger.py`, `lib/kill_switch.py`,
`lib/solana_rpc.py`, `lib/solana_cli.py`, `lib/relay_swap.py`, and every pre-existing function in
`lib/erc20.py` (`erc20_balance_units`, `eth_tx_status`, `eth_tx_confirmed_success`,
`eth_get_transaction_receipt`, `parse_erc20_transfer_amount`) are unchanged by the gas-ETH mode
addition and already carry a PASS money-safety adversary verdict
(`skills/earn/funding/MONEY-SAFETY-VERDICT.md`, 2026-07-08) plus their own passing test suites
(`tests/test_caps.py`, `tests/test_identity.py`, `tests/test_ledger.py`, `tests/test_erc20.py`).
This feature's own test suites (`tests/test_refill_plan.py`, `tests/test_franklin_sol_base_refill.py`,
plus the new `tests/test_franklin_gas_eth_refill.py`) cover only the NEW code
(`lib/refill_plan.py` additions + `franklin_sol_base_refill.py`'s `run_gas_refill` +
`lib/erc20.py`'s new `eth_get_balance`) and must not duplicate or weaken those existing suites —
running the FULL `skills/earn/funding/tests/` directory after this feature's changes is the
regression check (all existing tests must remain green, unchanged pass count: 167 total after
the gas-ETH mode addition, up from 119 at the end of impl iteration-2).
