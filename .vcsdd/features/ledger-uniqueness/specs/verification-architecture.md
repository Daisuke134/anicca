# Verification Architecture — ledger-uniqueness

## Purity Boundary Map

- **Pure Core** (100% of this feature's new code):
  - `skills/_shared/lib/ledger.mjs::resolveEarnLedgerPath({ home, env })` — string computation
    only, no I/O.
  - `skills/_shared/lib/ledger.mjs::filterOwnWalletRows(rows, ownWallets)` — array filter, no
    I/O, no mutation.
  - `skills/earn/self-improve/lib/ledger_reader.py::filter_own_wallet_rows(rows, own_wallets)`
    — Python mirror, no I/O.
  - `ledger_reader.py::realized_summary`/`confirmed_net_series`'s new `own_wallets=None`
    parameter — the added branch is pure (delegates to `filter_own_wallet_rows`); the existing
    `read_ledger` I/O call is UNCHANGED (already effectful, already tested, not modified).
- **Effectful Shell** (untouched, out of scope): `readLedger`/`appendLedger` (`ledger.mjs`),
  `read_ledger`/`resolve_ledger_path`'s own `os.environ` read (`ledger_reader.py`, already
  shipped/tested by a prior feature), `record-earn.mjs`'s RPC calls, every `run.sh` writer.

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-LU-001 | `resolveEarnLedgerPath({home})` returns `<home>/skills/earn/state/earn-ledger.jsonl` for any non-empty string home | 1 | true | node:test (property: fast-check string generator) |
| PROP-LU-002 | `resolveEarnLedgerPath` branch-2 (no home) path always ends with `earn/state/earn-ledger.jsonl` and is derived from `import.meta.url`, never a literal absolute string | 0 | true | node:test |
| PROP-LU-003 | Two distinct non-empty `home` values always resolve to two distinct paths (injectivity on non-empty input) | 1 | true | node:test property (fast-check, two distinct non-empty strings) |
| PROP-LU-004 | `filterOwnWalletRows`: every row with no `wallet` key is preserved, order-stable, for any input array | 1 | true | node:test property (fast-check arbitrary row arrays) |
| PROP-LU-005 | `filterOwnWalletRows`: every surviving walleted row's `wallet.toLowerCase()` is in `ownWallets.map(toLowerCase)` | 1 | true | node:test property |
| PROP-LU-006 | `filterOwnWalletRows` never mutates its input `rows` array or any row object (reference/deep-equality check pre/post) | 1 | true | node:test |
| PROP-LU-007 | `filter_own_wallet_rows` (Python) mirrors PROP-LU-004/005 exactly | 1 | true | pytest (hypothesis, this repo already vendors `hypothesis` — see `.hypothesis/` cache in self-improve) |
| PROP-LU-008 | `realized_summary(own_wallets=None)` is byte-identical (same dict) to pre-feature behavior on a fixed multi-row fixture (regression) | 0 | true | pytest (golden-value fixture) |
| PROP-LU-009 | `realized_summary(own_wallets=[X])` on a mixed own/foreign ledger returns `realized_net_usd` == sum of only own+walletless profitable rows, strictly ≤ unfiltered total | 2 | true | pytest (hand-built fixture, exact arithmetic) |
| PROP-LU-010 | Neither new JS nor Python function ever calls a write/delete file API (static check) | 0 | true | grep-based static assertion test |
| PROP-LU-011 | Full existing `ledger.test.js` + `ledger.test.mjs` + `test_ledger_reader.py` + `test_ledger_resolution.py` + `test_realized_gate.py` suites remain 100% green after this feature's changes (regression baseline) | 0 | true | node --test / pytest |

## Verification Strategy

- **Tier 0** (no formal proof needed, structural/regression checks suffice): doc-comment
  presence (REQ-005), no-write-API static grep (PROP-LU-010), full regression baseline
  (PROP-LU-011), branch-2 shape check (PROP-LU-002).
- **Tier 1** (property tests / fuzzing): the path-resolution injectivity and wallet-filter
  allow-list properties (PROP-LU-001/003/004/005/006/007) — these are exactly the kind of
  "for all inputs" claims a Hypothesis/fast-check property test is the right-sized tool for
  (both libraries are already vendored in this repo: `fast-check` in root `package.json`
  devDependencies, `hypothesis` already used under `skills/earn/self-improve/.hypothesis/`).
- **Tier 2** (lightweight formal / hand-proven arithmetic): PROP-LU-009's exact-sum claim is
  verified with a hand-built fixture where the expected `realized_net_usd` is computed by hand
  and asserted exactly (no floating-point tolerance needed at 1-2 rows of clean decimal USDC
  amounts) — a lightweight but exact proof obligation, not a full formal-methods tool
  (Kani/TLA+ would be disproportionate for a pure filter+sum over a finite fixture).
- **Tier 3** (strong formal proof): none required — no cryptography, no consensus, no
  concurrency in this feature's pure-function surface.

## Regression Gate

Before this feature is marked GREEN, the following pre-existing suites MUST show identical
pass counts to their pre-feature baseline (captured this session):
- `node --test skills/_shared/lib/__tests__/ledger.test.js skills/_shared/lib/__tests__/ledger.test.mjs` → baseline 21/21 pass.
- `cd skills/earn/self-improve && python3 -m pytest tests/test_ledger_reader.py tests/test_ledger_resolution.py -q` → baseline 26/26 pass.
- `cd skills/earn/self-improve && python3 -m pytest tests/test_realized_gate.py -q` → captured as part of RED-phase evidence (must stay green through GREEN/refactor).
