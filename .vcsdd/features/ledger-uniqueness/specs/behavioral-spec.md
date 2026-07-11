# Behavioral Spec — ledger-uniqueness

## Problem (evidence-grounded, verified by Read/Grep in this session)

Root-cause #2 of "稼いでるか分からない": the earn-ledger data that self-improve/reporting
consumers treat as "this instance's realized earnings" is **contaminated with other
instances' rows**, and no shared reader filters them out before summing/gating on them.

### Evidence trail (real files, real content, read this session)

1. `skills/self/founder-loop/record-earn.mjs` (prod root literal
   `/Users/operator/.anicca-founder`) writes to
   `<FOUNDER_DIR>/state/earn-ledger.jsonl` — an EVM/Base-RPC-verified, external-inflow-only
   ledger, ONE writer only, wallet pinned to `0x810f6d61f7606deee2657d3083e150a222bc29c5`
   (INV-1). This ledger is **not** contaminated (verified: prod root is env-independent,
   wallet is asserted against a pinned constant before any write).
2. `skills/earn/lib/record.mjs`, `skills/earn/lib/evolve.mjs`,
   `skills/earn/sol-trade/lib/sol-evolve.mjs`, `skills/earn/hl-trade/hl.py`, `skills/earn/run.sh`,
   `skills/economy/gig/run.sh`, `skills/cook/run.sh`, `skills/self/issue-dev/run.sh` all
   independently compute (each via its own `__dirname`/`$HERE`-relative resolution, no
   shared helper) the SAME logical path: `<instance-tree>/skills/earn/state/earn-ledger.jsonl`
   — the general, multi-strategy ledger (x402, sol-trade, hl-trade, gig, cook, …), written by
   many engines under many wallets (Base EVM, Solana, Hyperliquid).
3. **Live contamination, confirmed by direct read of the deployed file**
   `/Users/operator/.anicca-founder/skills/earn/state/earn-ledger.jsonl` (577 lines):
   - 155 lines carry `"wallet":"0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21"` — automaton's
     pre-rotation (leaked) wallet, NOT this instance's (`0x810f6d61f7606deee2657d3083e150a222bc29c5`).
   - Additional lines carry `"wallet":"0xb9dd3b67921b354c656523d6851537988f31dd56"`
     (automaton's post-rotation wallet) and the literal string `"wallet":"unknown"`.
   - 114 lines carry no `wallet` key at all (non-EVM/narrate rows — Solana/Hyperliquid/cook
     engines never stamp an EVM wallet).
   - This is exactly the SHARED-wallet blacklist `record-earn.mjs:39` already defines
     (`SHARED = ["0xa3cdd4...", "0xb9dd3b67...", "0x9b1ee988..."]`) — proof that the SAME
     contamination class record-earn.mjs already defends against on its OWN ledger is present,
     unfiltered, in the general `skills/earn/state/earn-ledger.jsonl` that self-improve/
     evolve/weekly-report consumers read.
4. **No existing reader filters by wallet.** Verified by reading
   `skills/_shared/lib/ledger.mjs` (`isProfitable`/`readLedger`) and
   `skills/earn/self-improve/lib/ledger_reader.py` (`is_profitable`/`is_confirmed`/
   `realized_summary`) in full: neither checks the `wallet` field. `realized_summary()` — the
   self-improve harness's own OBSERVE step, which gates genome evolution/promotion — sums
   `net_usdc` over every `is_profitable` row in the resolved ledger, including any
   contaminated 0xa3cdd4/0xb9dd3b67 rows that happen to satisfy `is_profitable` (chain-correct
   receipt + net>0 + external:true). This is the concrete "which number is real" gap.
5. **Two intentionally-separate canonical ledgers already exist for two different purposes**
   (this is NOT itself a bug — see Design Decision below):
   - `<ANICCA_HOME>/state/earn-ledger.jsonl` — founder-loop's GATE-0 ledger. ONE writer
     (record-earn.mjs), RPC-verified inflow only, wallet-pinned. Purpose: "did the founder
     wallet receive real external USDC" — the literal GLVS done-check for `founder-loop.sh`.
   - `<ANICCA_HOME>/skills/earn/state/earn-ledger.jsonl` — the general multi-strategy ledger.
     MANY writers (every earn engine), multiple chains/wallets. Purpose: per-strategy
     attribution, genome evolution fitness (`evolve.mjs`/`sol-evolve.mjs`), self-improve
     OBSERVE (`ledger_reader.py::realized_summary`), weekly reporting.
6. Two files hardcode `~/anicca` (the OSS dev-repo checkout) rather than resolving relative to
   `ANICCA_HOME`: `skills/earn/polymarket-trade/redeem.py:89` (`LEDGER_PATH`) and
   `skills/self/cadence-evidence.py:376` (`_pm_earner_ledger_path`). Read in full: these are
   BY DESIGN for the PM-earner role (claude-p), whose own runtime body genuinely IS the
   `~/anicca` checkout per the colony SSOT (no separate `ANICCA_HOME` directory exists for
   claude-p) — not a bug to "fix" by relocating them. They are named here only so a reviewer
   does not mistake them for the same class of bug; REQ-005 documents this explicitly so the
   "which path is canonical" question has one written answer instead of being re-litigated
   every time someone reads the earn-ledger fan-out.
7. `skills/self/self-improve/weekly_report.py::LEDGER_PATH_FOR_LOOP` deliberately has NO entry
   for `pm`/`pm-earner` (confirmed via `skills/self/founder-loop/ceo/run_pass.py:176-184`
   comment: "no real earn-ledger source has been declared for this loop yet... honestly
   empty rather than inventing a new per-loop file convention"). That gap is an existing,
   already-documented, deliberate deferral from a prior feature and is explicitly OUT OF SCOPE
   for `ledger-uniqueness` (do not add a `pm` entry here — see Non-Goals).

### Design Decision — which path is "the" canonical general earn ledger

`<ANICCA_HOME>/skills/earn/state/earn-ledger.jsonl` (i.e. `<instance-tree>/skills/earn/state/`,
resolved relative to `ANICCA_HOME` when set, else relative to the running module's own
location) is the canonical general earn ledger. Justification (least-destructive, no
reinvention — BP=answer):
- It is the path SIX already-live, already-tested writers/readers agree on TODAY
  (`record.mjs`, `evolve.mjs`, `sol-evolve.mjs`, `hl.py`, `earn/run.sh`, `economy/gig/run.sh`
  fallback), each independently computed but landing on the identical logical location.
- A prior feature (`self-improve-real-ledger`, already shipped, tests green) already codified
  this EXACT convention formally for the Python side:
  `skills/earn/self-improve/lib/ledger_reader.py::resolve_ledger_path()` resolves
  `ANICCA_HOME/skills/earn/state/earn-ledger.jsonl` when `ANICCA_HOME` is set, else a
  module-`__file__`-relative fallback to the same logical path (REQ-RL1, tested by
  `tests/test_ledger_resolution.py`, 26/26 passing before this feature touches anything).
- Choosing a DIFFERENT canonical path (e.g. unifying onto
  `<ANICCA_HOME>/state/earn-ledger.jsonl`, founder-loop's path) would require rewriting six
  live, money-critical writers with existing HARD-invariant test suites
  (`test-record-earn.sh`, `evolve.test.mjs`, `sol-evolve.test.mjs`, `test_reconcile.py`) —
  exactly the destructive, out-of-scope rewrite this feature must NOT do.

The JS side has no equivalent shared resolver function (each of the 6 writers duplicates
`path.join(__dirname, "..", "state", "earn-ledger.jsonl")` inline) — REQ-001 closes that gap
by adding ONE pure resolver to the already-designated shared module
(`skills/_shared/lib/ledger.mjs`, named as "the one shared interface" in
`ledger_reader.py`'s own module docstring), mirroring the Python contract exactly so both
languages agree by construction, not by convention alone.

## Purity Boundary Analysis

- **Pure core (this feature's entire surface)**: path resolution given `{home, env}` inputs;
  wallet-based row filtering given `(rows, ownWallet)` inputs. No I/O, no network, no wallet
  generation, no ledger writes. Fully deterministic, referentially transparent, unit-testable
  with in-memory fixtures.
- **Effectful shell (untouched by this feature)**: `appendLedger`/`readLedger` (existing file
  I/O in `ledger.mjs`), `record-earn.mjs`'s RPC calls, `redeem.py`'s on-chain redeem, every
  `run.sh` wrapper. This feature adds READ-ONLY pure functions on top of the existing
  `readLedger`/`read_ledger` outputs; it introduces no new I/O primitive.

## Requirements

### REQ-001: Canonical earn-ledger path resolver (JS)
**EARS**: WHEN a JS caller needs "this instance's own general earn-ledger path" THE SYSTEM
SHALL provide one pure function, `resolveEarnLedgerPath({ home, env } = {})`, exported from
`skills/_shared/lib/ledger.mjs`, that returns `{ path, resolved, resolutionSource }` using the
SAME two-branch priority `ledger_reader.py::resolve_ledger_path()` already uses:
1. If `home` (or `env.ANICCA_HOME` when `home` is omitted, or `process.env.ANICCA_HOME` when
   `env` is also omitted) is a non-empty string: return
   `path.join(<that value>, "skills", "earn", "state", "earn-ledger.jsonl")`,
   `resolved: true`, `resolutionSource: "anicca_home_env"`.
2. Else: return `path.join(<this module's own __dirname-climbed earn/state dir>,
   "earn-ledger.jsonl")` computed relative to `ledger.mjs`'s own `import.meta.url`
   (`_shared/lib` → climb to the sibling `earn/state/` tree, mirroring the Python module's
   `lib → self-improve → earn` climb, adjusted for this file's own location one level up at
   `_shared/lib`), `resolved: true`, `resolutionSource: "file_relative_default"`.
This function MUST NOT read/write any file — it only computes a string.
**Edge Cases**:
- `home: ""` (empty string) → treated as absent, falls through to branch 2 (an empty string is
  never a valid ANICCA_HOME).
- `env` provided without `ANICCA_HOME` key and no explicit `home` → branch 2.
- Two different `home` values in two separate calls in the same process → two different,
  independent paths (never cached, never a frozen module-level constant used by this
  function's own return value — mirrors REQ-RL3's "resolves fresh, per call").
**Acceptance Criteria**:
- `resolveEarnLedgerPath({ home: "/tmp/instX" }).path === "/tmp/instX/skills/earn/state/earn-ledger.jsonl"`.
- `resolveEarnLedgerPath({ env: {} }).resolutionSource === "file_relative_default"` and the
  returned path ends with `earn/state/earn-ledger.jsonl`.
- Two instances (`home: A`, `home: B`, `A !== B`) never resolve to the same path.

### REQ-002: Wallet-based row filter (JS)
**EARS**: WHEN a JS caller has a list of parsed ledger rows (the output of
`readLedger`) and wants only rows attributable to THIS instance's own wallet(s) THE SYSTEM
SHALL provide one pure function, `filterOwnWalletRows(rows, ownWallets)`, exported from
`skills/_shared/lib/ledger.mjs`, where `ownWallets` is a string or array of strings (this
instance's own wallet address(es), any case), that returns a NEW array (never mutates `rows`
or any row object) containing:
- every row whose `wallet` field is absent (`undefined`/`null`/key not present) — non-EVM
  engines (Solana, Hyperliquid) and narrate-only rows never carry an EVM wallet and are never
  cross-instance-attributable by this check, so they always pass through;
- every row whose `wallet` field, lower-cased, exactly equals one of `ownWallets` (also
  lower-cased before comparison);
and EXCLUDES every row whose `wallet` field is a non-empty string that does not match (this
covers both the three pinned SHARED wallets from `record-earn.mjs:39` and any future/unknown
foreign wallet — the filter is allow-list based on `ownWallets`, not a blacklist of known-bad
values, so it fails closed against wallets not yet known to be compromised).
**Edge Cases**:
- `rows` is `[]` → returns `[]`.
- `ownWallets` is `[]` or `""` or `undefined` → every row WITH a non-empty `wallet` field is
  excluded (fail-closed: "no known own wallet" means nothing can be proven "own"); rows with
  no `wallet` field still pass through.
- `wallet` field present but empty string `""` → treated as "no proof of ownership", excluded
  unless `ownWallets` itself contains `""` (never true in practice; documented, not specially
  cased).
- Case mismatch (`"0x810F..."` vs `"0x810f..."`) → still matches (case-insensitive compare).
- `rows` contains a non-object/`null` entry → skipped (defensive; mirrors `readLedger`'s own
  `.filter(Boolean)` contract, never throws).
**Acceptance Criteria**:
- Given the 3 pinned SHARED wallets as **foreign** rows plus one row for `ownWallets`, only
  the matching row (+ any wallet-less rows) survive.
- Calling with `ownWallets` omitted excludes every walleted row and keeps every walletless row.
- Original `rows` array/object identity is unchanged after the call (immutability check).

### REQ-003: Wallet-based row filter (Python, opt-in, non-breaking)
**EARS**: WHEN a Python caller of `ledger_reader.py` wants realized-earnings figures scoped to
THIS instance's own wallet THE SYSTEM SHALL provide a pure function
`filter_own_wallet_rows(rows, own_wallets)` mirroring REQ-002's exact semantics (case-
insensitive allow-list match; walletless rows always pass; empty/absent `own_wallets` excludes
every walleted row) AND SHALL extend `realized_summary()` and `confirmed_net_series()` with a
NEW optional keyword parameter `own_wallets=None` that, when provided, applies
`filter_own_wallet_rows` to the rows read from the ledger BEFORE any `is_profitable`/
`is_confirmed` classification; when `own_wallets` is omitted (`None`, the default), behavior
is BYTE-IDENTICAL to the current implementation (no filtering) so every existing caller and
every existing passing test (`test_ledger_reader.py`, `test_ledger_resolution.py`,
`test_realized_gate.py`) is unaffected.
**Edge Cases**:
- `own_wallets=None` (default) → identical output to pre-feature `realized_summary`/
  `confirmed_net_series` (regression-safety requirement, not merely a nice-to-have).
- `own_wallets=[]` → every walleted row excluded (same fail-closed edge as REQ-002), summary
  degrades to only walletless (Solana/HL/narrate) rows' totals.
- A ledger containing BOTH the instance's own wallet AND a foreign (SHARED-list) wallet row
  with a larger `net_usdc` → `realized_net_usd` with `own_wallets` set MUST be strictly less
  than or equal to the unfiltered total, and MUST equal the sum of only the own-wallet +
  walletless profitable rows.
**Acceptance Criteria**:
- `realized_summary(path, own_wallets=["0x810f..."])` on a ledger containing one own-wallet
  profitable row (net 5) and one foreign-wallet profitable row (net 100) returns
  `realized_net_usd == 5.0`, `profitable_row_count == 1`.
- `realized_summary(path)` (no `own_wallets`) on the SAME ledger returns the pre-feature value
  (`105.0`, `profitable_row_count == 2`) — proves non-regression.

### REQ-004: Non-destructive, read-only, append-only-preserving
**EARS**: THE SYSTEM SHALL implement REQ-001/002/003 as pure, read-only functions that never
open a file for writing, never call `appendLedger`/`fs.writeFile`/`fs.unlink`/any Python file-
write API, and never mutate an input array/object in place.
**Edge Cases**: none beyond REQ-001-003's own (this is a structural constraint, verified by
code review / grep for write APIs in the new functions, not a runtime edge case).
**Acceptance Criteria**:
- `grep -n "writeFile\|appendFile\|fs.rm\|fs.unlink" ` on the new function bodies returns
  nothing.
- A test asserts the real production contaminated ledger file's byte content (mtime + size)
  is unchanged after calling `filterOwnWalletRows`/`filter_own_wallet_rows` on rows read from
  a COPY of it (money-safe: the real file is only ever opened for reading in a throwaway test
  fixture copy under `tmp_path`, never the live `.anicca-founder` path itself — no test in this
  feature touches `/Users/operator/.anicca-founder/**` or any real wallet/RPC).

### REQ-005: Two-ledger design documented (no path unification)
**EARS**: THE SYSTEM SHALL document, in this spec (Design Decision section above) and in a
short doc-comment addition to `skills/_shared/lib/ledger.mjs`'s existing file-header comment,
that `<ANICCA_HOME>/state/earn-ledger.jsonl` (founder-loop GATE-0) and
`<ANICCA_HOME>/skills/earn/state/earn-ledger.jsonl` (general multi-strategy, this feature's
`resolveEarnLedgerPath` target) are two DELIBERATELY separate files for two different
purposes, so a future reader does not attempt to "fix" the split by merging them.
**Edge Cases**: N/A (documentation requirement).
**Acceptance Criteria**: the doc-comment addition is present in `ledger.mjs` and references
both paths and both purposes by name.

## Non-Goals (explicitly out of scope for this feature)

- Rewriting `record.mjs`/`evolve.mjs`/`sol-evolve.mjs`/`hl.py`/`earn/run.sh` to CALL the new
  `resolveEarnLedgerPath` (they keep their own working `__dirname`-relative constants
  unchanged — REQ-001 only adds the shared function for NEW/future callers to converge on,
  it does not migrate existing callers in this lean sprint).
- Relocating `redeem.py`/`cadence-evidence.py`'s hardcoded `~/anicca` paths (by-design for
  claude-p's PM-earner role; see Evidence #6).
- Adding a `pm`/`pm-earner` entry to `weekly_report.py::LEDGER_PATH_FOR_LOOP` (an existing,
  already-documented, deliberate deferral from a prior feature; see Evidence #7).
- Quarantining/moving the 155 already-contaminated lines out of the live
  `.anicca-founder/skills/earn/state/earn-ledger.jsonl` file (a live production file; this
  feature ships the FILTER capability so future reads can exclude them — actually invoking
  that filter against the live file, or physically moving lines, is a follow-up operational
  action outside a lean VCSDD sprint's blast radius, and is money-adjacent enough to require
  its own explicit sign-off).
- Wiring `own_wallets=` into any live call site (`run_evolve.sh`, `weekly_report.py`, CEO
  `run_pass.py`) — this feature ships the capability (REQ-003) opt-in and backward-compatible;
  wiring it into a specific caller is a separate, reviewable follow-up.

## Non-Functional Requirements

- **Performance**: both new functions are O(n) over the row list with no I/O; no bound is
  needed beyond "does not re-read the file" (the file read stays in the caller, unchanged).
- **Security/money-safety**: no test in this feature touches a real wallet, real RPC endpoint,
  or writes to any path under `/Users/operator/.anicca-founder/`, `/Users/operator/.blockrun/`, or
  any other live instance home. All fixtures live under `tmp_path`/`os.tmpdir()`.
