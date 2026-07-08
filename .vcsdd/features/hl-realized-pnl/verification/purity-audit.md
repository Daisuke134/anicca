# Purity Boundary Audit — hl-realized-pnl (Phase 5)

Cross-checks `specs/verification-architecture.md`'s "Purity boundary map" against the actual
worktree implementation (`/Users/anicca/anicca/.worktrees/hl-realized-pnl`, branch
`feature/hl-realized-pnl`, clean working tree). Read-only audit — no production code touched.

## Declared Boundaries

From `verification-architecture.md`:

| Component | Declared |
|---|---|
| `fills.select_close_fills` | PURE |
| `fills.is_unprocessable` | PURE |
| `fills.compute_realized_pnl` | PURE |
| `reconcile.plan_batch` | PURE |
| `reconcile.acquire_lock` | IMPURE (fcntl.flock) |
| `reconcile.read_checkpoint` | IMPURE (file read) |
| `reconcile.write_checkpoint` | IMPURE (atomic file write, called LAST) |
| `reconcile.fetch_fills` (conceptual — realized as the inline `info.user_fills_by_time` call inside `reconcile()`) | IMPURE (live HTTP) |
| `reconcile.already_recorded_tids` | IMPURE, read-only |
| `reconcile.record_line` | IMPURE — the ONLY ledger-mutating call, via subprocess to `record.mjs` |
| `reconcile.reconcile` | IMPURE (composition root) |
| `hl.py::cmd_reconcile` | IMPURE (CLI glue) |
| `hl.py::cmd_close` | IMPURE, unchanged shape minus `closed_pnl_usd` |
| `ledger.mjs::deriveLine` | PURE |
| `ledger.mjs::isProfitable` | PURE |

## Observed Boundaries

Read directly from the worktree source (`skills/earn/hl-trade/lib/fills.py`,
`skills/earn/hl-trade/lib/reconcile.py`, `skills/earn/hl-trade/hl.py`,
`skills/_shared/lib/ledger.mjs`):

- **`fills.compute_realized_pnl`** (fills.py:10-21): only `float()` conversions and arithmetic on
  its two scalar args. No I/O, no global/module state read or written, no clock. **Matches
  declared PURE.**
- **`fills.select_close_fills`** (fills.py:33-40) and its private helper `_closed_pnl_is_zero`
  (fills.py:24-30): list comprehension + `sorted()` over the input list only; the `since_time_ms`
  bound is a parameter, never `time.time()`/`datetime.now()` read internally. **Matches declared
  PURE** (the purity map explicitly calls out "no clock read (caller supplies since_time_ms)" —
  confirmed, the clock is only read once by `hl.py::cmd_reconcile` at `now_ms = int(time.time() *
  1000)` and passed in, never re-read inside `fills.py`/`reconcile.py`'s pure layer).
- **`fills.is_unprocessable`** (fills.py:43-54): dict lookups + `float()`/`isinstance()` checks
  only. **Matches declared PURE.**
- **`reconcile.plan_batch`** (reconcile.py:36-49): pure loop over `candidates` and a `set`
  membership test against `already_recorded_tids`; calls `is_unprocessable` (itself pure); builds
  and returns a new list/dict, mutates no input argument. **Matches declared PURE.**
- **`reconcile.acquire_lock`** (reconcile.py:52-61): `os.makedirs` + `open()` + `fcntl.flock`.
  **Matches declared IMPURE** — filesystem + kernel lock-table side effects, as specified. Never
  raises past this function (catches `OSError` and returns `None`), matching REQ-B10's "never
  blocks, never raises" contract.
- **`reconcile.read_checkpoint`** (reconcile.py:64-71): `open()` + `.read()`; catches
  `FileNotFoundError`/`ValueError` and returns `0`. **Matches declared IMPURE**, never raises
  (REQ-B7).
- **`reconcile.write_checkpoint`** (reconcile.py:74-87): `tempfile.mkstemp` in the SAME directory
  as `path` + `os.fdopen`/write + `os.replace` (atomic rename). On any exception, unlinks the
  temp file and re-raises. **Matches declared IMPURE**; the atomic-write claim (REQ-B6) is
  structurally correct — `os.replace` on POSIX is atomic within the same filesystem, and
  `mkstemp(dir=d, ...)` guarantees the temp file is on the same filesystem as `path` (same `d`).
  **Call-site check**: in `reconcile()` (reconcile.py:203-207), `write_checkpoint` is called
  exactly once, after the entire `plan["steps"]` loop has resolved (recorded, skipped, or
  stopped) — confirms "called LAST" from the purity map.
- **`reconcile.already_recorded_tids`** (reconcile.py:90-108): `open()` + read + per-line
  `json.loads`; no write. **Matches declared IMPURE, read-only.** One subtlety not mentioned
  verbatim in the purity map: it also unions in `_recorded_tids_cache.get(ledger_path, set())` —
  a **module-level mutable dict** (reconcile.py:34). This makes `already_recorded_tids` not
  purely a function of the ledger file's disk contents; it also depends on in-process history.
  The module docstring for `_recorded_tids_cache` (reconcile.py:32-35, quoted below) explicitly
  justifies this as a same-process bridge for a real-CLI-subprocess deployment where the cache is
  always empty (`skills/earn/run.sh` invokes `hl.py reconcile` as a fresh subprocess every wake —
  confirmed by `grep -n "hl.py reconcile" skills/earn/run.sh:177`, a `subprocess`-per-wake
  invocation, not a long-lived process). **Finding (informational, not a violation)**: this
  function is IMPURE by the file-I/O side alone regardless of the cache, so its overall IMPURE
  classification is unaffected — but the boundary map's own prose ("reads `earn-ledger.jsonl`,
  extracts `fill_tid` values — read-only") does not mention the in-memory cache contribution.
  Recommend a one-line addendum to the boundary map text (non-blocking, doc-only) rather than a
  code change, since production behavior (fresh subprocess per wake) makes the cache inert there.
- **`reconcile.record_line`** (reconcile.py:111-121): `subprocess.run(["node", _RECORD_MJS,
  json.dumps(payload), ledger_path], ...)`. **Matches declared IMPURE** — the only
  ledger-mutating call in this feature's Python code. Confirmed no other `open(..., "w")` /
  `appendLedger`-equivalent call exists anywhere in `reconcile.py` (see PROP-015's static grep,
  re-verified independently below).
- **`reconcile.reconcile`** (reconcile.py:159-210), the composition root: acquires the lock
  first, reads checkpoint, calls `info.user_fills_by_time(...)` (the live-HTTP IMPURE step —
  realized inline rather than as a separately-named `fetch_fills` function; the purity map lists
  `fetch_fills` as a row but the implementation folds it directly into `reconcile()`'s body. This
  is a **naming-only deviation, not a purity violation** — the HTTP call is still isolated to
  exactly one call site, wrapped in its own `try/except` per REQ-B9), then `select_close_fills` /
  `plan_batch` (pure), then the record loop, then `write_checkpoint` last, then releases the
  lock in a `finally` block. **Matches declared IMPURE (composition root)** shape and ordering.
- **`hl.py::cmd_reconcile`** (hl.py:141-158): calls the SAME `_clients()` every other subcommand
  uses (no second key-loading path — re-confirms PROP-016), builds `ledger_path` /
  `checkpoint_path` / `lock_path` from `os.path.dirname(os.path.abspath(__file__))` (never a
  literal absolute path or another instance's home — re-confirms PROP-023), calls
  `reconcile_mod.reconcile(...)`, prints JSON. **Matches declared IMPURE (CLI glue).**
- **`hl.py::cmd_close`** (hl.py:114-127): calls `ex.market_close(args.coin)`, sleeps 2s, reads
  `info.user_state`, prints JSON with no `closed_pnl_usd` key. **Matches declared "IMPURE,
  unchanged shape minus one field."**
- **`ledger.mjs::deriveLine`** (ledger.mjs:11-33): builds and returns a new object from its
  input `o`; the only "clock-like" behavior is `o.ts ?? Math.floor(Date.now() / 1000)` — an
  existing (pre-feature) fallback that is itself impure in the strictest sense, but this is
  **unchanged by this feature** (the purity map's own annotation says "unchanged purity; one new
  conditional field" — confirmed: the only diff this feature adds is the `fill_tid` passthrough
  block, itself a pure conditional). No new impurity introduced.
- **`ledger.mjs::isProfitable`** (ledger.mjs:46-56): pure boolean expression over its input
  object; the new `hlOk` disjunct reads only `line.chain`/`line.fill_tid`/`line.confirmed`. **No
  new impurity introduced**, matches "unchanged purity; one new disjunct."

## Independent re-verification of the two PURE-boundary static claims

```
$ grep -n "appendLedger\|assertOwnIdentityOnly\|checkHalt" skills/earn/hl-trade/lib/reconcile.py
(0 matches)
$ grep -n "record.mjs" skills/earn/hl-trade/lib/reconcile.py
31:_RECORD_MJS = os.path.join(_LIB_DIR, "..", "..", "lib", "record.mjs")
132:        ["node", _RECORD_MJS, json.dumps(payload), ledger_path],
(2 matches, >= 1 required)
```
Confirms PROP-015 (REQ-D1) holds at the source level, independent of the pre-existing
`test_reconcile_py_never_reimplements_ledger_guards_static_grep` unit test.

## Summary

- **0 purity-boundary violations found.** Every PURE-declared function (`fills.py`'s three
  functions, `reconcile.plan_batch`, `ledger.mjs`'s `deriveLine`/`isProfitable`) is genuinely
  free of I/O, clock reads, and subprocess calls in the actual implementation. Every
  IMPURE-declared function performs exactly the side effect the map describes, at exactly the
  call-site discipline the map/spec requires (lock-first, checkpoint-write-last,
  record.mjs-only mutation, no second key path, no order/leverage calls).
- **1 informational finding** (non-blocking, doc-only): `already_recorded_tids`'s in-process
  `_recorded_tids_cache` contribution isn't mentioned in the purity-map's one-line description of
  that function. It does not change the function's IMPURE classification (it's already impure
  via file I/O) and is inert in the real deployment topology (fresh subprocess per wake). No code
  change recommended; a doc addendum to `verification-architecture.md` would close this
  cosmetically if desired.
- **1 naming-only deviation** (non-blocking): the purity map lists `fetch_fills` as a distinct
  row; the implementation inlines the equivalent call directly inside `reconcile()`. The
  IMPURE/HTTP boundary itself is intact (one call site, try/except-wrapped, REQ-B9-compliant) —
  this is a documentation/naming mismatch, not a behavioral one.
