# Verification Architecture — franklin-sol-base-refill

## Purity Boundary Map
- **Pure Core** (`skills/earn/funding/lib/refill_plan.py`, new module): `select_refill_amount`,
  `evaluate_relay_fee`, `assert_own_citizen_row`, `has_unresolved_pending`, `build_refill_plan`.
  Deterministic, no I/O, no network, no clock/randomness dependence (a `now_ts` is always
  passed in, never read from `time.time()` inside pure functions).
- **Effectful Shell** (`skills/earn/funding/franklin_sol_base_refill.py`, new CLI): resolves
  identity via subprocess, reads citizens.json, reads Solana/Base balances over RPC, calls
  relay.link `/quote` and `/intents/status`, builds+signs+submits the Solana transaction
  (solders), and appends ledger rows. Every effectful call is behind a small injectable
  interface (`deps` dict of callables) so orchestration tests can substitute fakes — mirrors
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
  `lib/{caps,identity,ledger,erc20,solana_rpc,kill_switch}.py` modules (no changes to those
  files in this feature — reused as-is).

## Reused, Not Re-Verified
`lib/caps.py`, `lib/identity.py`, `lib/ledger.py`, `lib/kill_switch.py`, `lib/erc20.py`,
`lib/solana_rpc.py`, `lib/solana_cli.py` are unchanged by this feature and already carry a
PASS money-safety adversary verdict (`skills/earn/funding/MONEY-SAFETY-VERDICT.md`,
2026-07-08) plus their own passing test suites (`tests/test_caps.py`, `tests/test_identity.py`,
`tests/test_ledger.py`). This feature's own test suite (`tests/test_refill_plan.py`,
`tests/test_franklin_sol_base_refill.py`) covers only the NEW code
(`lib/refill_plan.py` + `franklin_sol_base_refill.py`) and must not duplicate or weaken those
existing suites — running the FULL `skills/earn/funding/tests/` directory after this feature's
changes is the regression check (all existing tests must remain green, unchanged pass count).
