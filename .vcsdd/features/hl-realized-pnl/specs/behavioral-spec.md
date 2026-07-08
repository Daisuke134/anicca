---
feature: hl-realized-pnl
mode: strict
language: python
phase: 1a
created: 2026-07-09
---

# Behavioral Specification — hl-realized-pnl

## 1. Purpose

Fix the Hyperliquid (`skills/earn/hl-trade/`) realized-P&L recording pipeline so that
`skills/earn/state/earn-ledger.jsonl` reflects Hyperliquid's OWN settled fill records
(`userFills`: `closedPnl`, `fee`) instead of a pre-close `unrealizedPnl` snapshot, so that
auto-closes (take-profit / stop-loss / liquidation) are captured even when the model issues
no explicit `close` that wake, and so that `skills/_shared/lib/ledger.mjs`'s `isProfitable`
(GATE-0) can recognize a verified Hyperliquid close the same way it already recognizes a
verified EVM or Solana settlement.

## 2. Audit findings this spec fixes (evidence, non-normative — context only)

1. `hl.py:61` uses `constants.MAINNET_API_URL` — Hyperliquid trading on this wallet is REAL
   mainnet, not paper/testnet. The old wallet `0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21` carries
   146 real fills with real `closedPnl`/`fee`/`tid`/`hash` — usable as live E2E evidence
   (§Done, verification-architecture.md). Verified by a live, read-only query against this exact
   address in this session: `evidence/audit-userfills-0xa3cdd4-raw.json` (raw response, 146
   fills) and `evidence/audit-userfills-summary.md` (computed sums + raw field-presence check).
2. `hl.py:130-139` (`cmd_close`) captures `unrealizedPnl` BEFORE calling `market_close` and
   reports that number as `closed_pnl_usd` — this is not the fill's actual realized result and
   is almost always wrong. Per `evidence/audit-userfills-summary.md` (live query, this session):
   summing all 146 fills' real `closedPnl` (`0.27274`) minus real `fee` (`0.396474`) gives an
   actual realized net of `−0.123734` — versus the ≈ `−$0.0006` `unrealizedPnl`-derived number
   the OLD code would have reported for a single close of that magnitude, roughly two orders of
   magnitude off. The evidence file also confirms `fee` and `tid` ARE present on every one of
   the 146 real fill objects returned by the live API (resolves F-5's SDK-docstring concern —
   the installed SDK's docstring is stale/incomplete, not the live API).
3. `run.sh:213` hard-codes `cost_usdc:0` (fees are dropped) and never sets `external`, so a
   Hyperliquid close can never satisfy `isProfitable`'s GATE-0 regardless of its true P&L.
4. Exchange-side auto-close (take-profit / stop-loss / liquidation) is never reconciled today —
   it happens with no `hl.py close` invocation, so the ledger never sees it at all.
5. `resolve-identity.mjs`/`run.sh`'s per-instance identity gate is already correct and is
   REUSED, not reimplemented, by this feature (Group D below).

## 3. Out of scope

- Trading strategy: which coin, side, size, leverage, stop-loss/take-profit, or when to open a
  position. `hl.py`'s `open` command and `SKILL.md`'s baseline strategy are untouched.
- The anti-churn cooldown gate in `run.sh` (`_hl_since` / `HL_COOLDOWN_MIN`) — untouched.
- `fund-hl.mjs` (self-funding relay) — untouched.
- Porting the new Hyperliquid disjunct into
  `skills/earn/self-improve/lib/ledger_reader.py::is_profitable` (documented follow-up, REQ-C4).
- Pagination/chunking of `user_fills_by_time` beyond what the live audited wallet's 146 fills
  require (see NFR-1) — not assumed without live evidence.
- Any AI-usage/AI-generation disclosure text — none is added anywhere by this feature.

## 4. Requirements (EARS)

### Group A — Remove the false pre-close P&L number

- **REQ-A1**: `hl.py`'s `close` subcommand SHALL NOT compute or report a `closed_pnl_usd`
  field derived from the position's `unrealizedPnl` captured before calling
  `Exchange.market_close`. This field SHALL be removed from `cmd_close`'s JSON output
  entirely — it SHALL NOT be replaced by a relabeled or re-scaled version of the same number.
- **REQ-A2**: THE realized P&L for any Hyperliquid position close — whether an explicit
  `hl.py close` invocation OR an exchange-side auto-close (take-profit, stop-loss, or
  liquidation) — SHALL be derived EXCLUSIVELY from Hyperliquid's own `userFills` fill records
  (`closedPnl`, `fee`) for this instance's own address, obtained via a live call to the
  Hyperliquid Info API. It SHALL NEVER be derived from a pre-close or post-close
  `unrealizedPnl`/`accountValue` snapshot.

### Group B — Reconcile engine (fill-based, idempotent, crash-safe)

- **REQ-B1**: THE SYSTEM SHALL provide a PURE function
  `compute_realized_pnl(closed_pnl: float, fee: float) -> {earn_usdc, cost_usdc, net_usdc}`
  such that:
  - IF `closed_pnl > 0` THEN `earn_usdc = closed_pnl` AND `cost_usdc = fee`.
  - IF `closed_pnl <= 0` THEN `earn_usdc = 0` AND `cost_usdc = fee + (-closed_pnl)`.
  - `net_usdc = earn_usdc - cost_usdc` SHALL always equal `closed_pnl - fee` exactly (the fee
    is charged in both the win and loss case; only the win/loss split of the P&L itself
    changes which bucket absorbs it).
- **REQ-B2**: THE SYSTEM SHALL provide a PURE function that, given a list of raw Hyperliquid
  fill objects and a `since_time_ms` cursor, returns ONLY the fills that (a) have
  `time >= since_time_ms` (INCLUSIVE — matches REQ-B8's inclusive query boundary; a
  strictly-greater-than filter here would silently re-exclude a tied-timestamp sibling fill
  that REQ-B8 correctly re-fetched, defeating REQ-B8's entire purpose), AND (b) have a
  numeric, non-zero `closedPnl` — sorted ascending by `time`. A fill with `closedPnl == 0`
  (an opening/increasing fill, or an exact-breakeven close) is excluded by construction: it is
  a non-event for realized-P&L bookkeeping (it can never satisfy GATE-0's `net_usdc > 0` gate
  either way, and recording endless `$0.00` lines is deliberately avoided, not an oversight).
  A candidate at exactly `time == since_time_ms` that was already recorded in a prior pass is
  NOT filtered out here — it reaches REQ-B4.1's tid-dedup step, which is the ONLY mechanism
  that skips already-recorded fills (never the time boundary).
- **REQ-B3**: WHEN a candidate fill (from REQ-B2) has a non-numeric or missing `closedPnl` or
  `fee` field, OR a missing or non-integer `tid` field, THE SYSTEM SHALL classify it as
  UNPROCESSABLE and MUST NOT invent a value (never default to `0`, never fabricate a `tid`,
  never silently coerce via a lossy cast). `tid` is included here because REQ-B4.1's
  idempotency dedup and REQ-C1's ledger schema both require a real, stable integer `tid` —
  live evidence (`evidence/audit-userfills-summary.md`) confirms `tid` is present as a Python
  `int` on all 146 fills of the audited wallet, so this branch is expected to be rare/never-hit
  in practice, but the reconciler MUST NOT silently treat a missing `tid` as recordable.
- **REQ-B4**: THE reconciler SHALL process the fills selected by REQ-B2 in ascending time
  order. For each fill, in order:
  1. IF a prior ledger line already carries this fill's `tid` in its `fill_tid` field, THE
     reconciler SHALL skip recording it (idempotent no-op), treat it as handled for
     checkpoint-advancement purposes (REQ-B5), and continue to the next fill.
  2. ELSE IF the fill is UNPROCESSABLE (REQ-B3), THE reconciler SHALL STOP processing this
     batch immediately — no fill after this one is recorded this pass.
  3. ELSE, THE reconciler SHALL compute `{earn_usdc, cost_usdc, net_usdc}` via REQ-B1 and
     attempt to record ONE ledger line (schema: Group C) through the shared `record.mjs`
     entrypoint (REQ-D1). IF this recording attempt fails (non-zero exit, exception, or
     unparseable output), THE reconciler SHALL STOP processing this batch immediately,
     exactly as in step 2.
- **REQ-B5**: AFTER processing a batch (REQ-B4), THE reconciler SHALL advance its persisted
  checkpoint to the `time` of the LAST fill it successfully recorded or confirmed-as-
  already-recorded (duplicate) in that batch, in strict time order. The checkpoint SHALL
  NEVER advance past a fill that triggered a STOP (REQ-B4.2 or REQ-B4.3), and SHALL NOT
  advance at all if the very first eligible fill triggered a STOP. IF zero eligible fills
  existed this pass, THE checkpoint SHALL remain UNCHANGED. Because REQ-B8's re-query
  boundary is INCLUSIVE, a subsequent pass WILL re-fetch the fill that set the checkpoint
  (and any sibling fill sharing its exact `time`) — this is EXPECTED, not a bug: REQ-B4.1's
  tid-dedup recognizes the already-recorded one as a duplicate (no re-record, checkpoint may
  re-advance to the same value) while any genuinely unrecorded sibling at that same `time` is
  recorded normally. The checkpoint's role is a monotonic lower bound for query efficiency,
  never the sole correctness mechanism for avoiding duplicates.
- **REQ-B6**: THE checkpoint SHALL be persisted at a fixed path colocated with `hl.py`
  (`skills/earn/hl-trade/.last-fill-ts`), written LAST — after every ledger-append attempt in
  the batch has resolved — and written atomically (temp file + rename/replace), so a crash
  mid-batch can never leave a corrupt or partially-written checkpoint file.
- **REQ-B7**: IF the checkpoint file is missing, empty, or unparseable, THE reconciler SHALL
  treat `since_time_ms` as `0` (fetch this address's entire fill history on the first pass)
  rather than crashing or skipping reconciliation.
- **REQ-B8**: THE reconciler SHALL query fills via
  `Info.user_fills_by_time(address, since_time_ms, now_ms, aggregate_by_time=False)` — the
  boundary is INCLUSIVE of `since_time_ms` (NOT `since_time_ms + 1`), because a single
  Hyperliquid close can produce MULTIPLE fills sharing the exact same millisecond `time`
  (EDGE-9), and any of those tied fills could be the one that set the checkpoint while a
  SIBLING fill at that identical `time` was never recorded (REQ-B4.2/B4.3 STOP). Re-fetching
  the checkpoint's own timestamp is safe and REQUIRED: REQ-B4.1's tid-based idempotency check
  — never the query boundary — is what prevents an already-recorded fill from being recorded
  twice. `aggregate_by_time=False` (the SDK default) is REQUIRED so partial fills are never
  merged, preserving the per-fill `tid` granularity Group C / EDGE-9 depend on. `Info.user_fills`
  (the unbounded, all-time variant) SHALL NEVER be used by the reconciler.
  **Invariant (money-safety, non-negotiable)**: for any fill `F` with `F.time == checkpoint`
  that was NOT recorded in the pass that set the checkpoint to that value, the very next pass
  MUST include `F` among its query results. A design that can permanently exclude such an `F`
  from every future query (e.g. a strictly-greater-than boundary) is a silent-drop defect,
  not an optimization — reject it outright regardless of how it is phrased.
- **REQ-B9**: A live Hyperliquid API error or timeout during REQ-B8's fetch SHALL cause the
  reconciler to skip this pass entirely (record nothing, checkpoint unchanged) and return
  control to its caller without raising an uncaught exception. The next wake's reconcile
  retries the same window.
- **REQ-B10**: BEFORE reading the checkpoint (REQ-B7) or the ledger's `already_recorded_tids`
  (REQ-B4.1), THE reconciler SHALL acquire an exclusive, non-blocking file lock
  (`fcntl.flock(fd, LOCK_EX | LOCK_NB)`) on a lock file colocated with the checkpoint
  (`skills/earn/hl-trade/.last-fill-ts.lock`). IF the lock cannot be acquired immediately
  (another `reconcile` invocation for this same instance is already in flight), THE reconciler
  SHALL record nothing, leave the checkpoint file completely untouched, and return a
  `{"status": "locked", "recorded": 0}`-shaped result without raising — exactly as if it were
  never invoked this wake. THE lock SHALL be held for the ENTIRE read-check-record-write
  sequence (REQ-B4 through REQ-B6) and released only after the checkpoint write (REQ-B6)
  completes or the pass STOPs/errors. This closes the check-then-act race that would otherwise
  let two concurrent invocations both read the same `already_recorded_tids` set and both
  attempt to record the same fill.

### Group C — External / GATE-0 classification and ledger schema

- **REQ-C1**: EVERY ledger line recorded by the reconciler (REQ-B4.3) SHALL carry:
  `source: "hl-trade"`, `chain: "hyperliquid"`, `fill_tid: <the fill's tid, integer>`,
  `confirmed: true`, `external: true`, `earn_usdc`, `cost_usdc` (REQ-B1), `wallet` (this
  instance's own resolved address, REQ-D2), `task` (a human-readable string naming the coin
  and `tid`), `wake`.

  Rationale (recorded here, not left implicit, so the fresh-context adversary can evaluate
  it): a Hyperliquid fill's `closedPnl` is realized and cash-settled by the exchange's own
  clearinghouse against a counterparty on the order book at the moment the fill is written
  into `userFills` — there is no separate broadcast/confirmation step the way an EVM tx can
  still revert or a Solana signature can still land unconfirmed. The live `userFills` API
  response for this instance's own address IS the receipt. This is why a Hyperliquid
  close-fill qualifies as `external: true` (real, counterparty-settled revenue) even though a
  same-wallet Jupiter swap (`sol-trade`) deliberately does NOT (a same-wallet asset rotation
  proves nothing about a counterparty). This holds for wins AND losses — a loss is still a
  real, externally-realized outcome, not internal bookkeeping noise, and is recorded exactly
  the same way (REQ-B1's win/loss split only changes the `earn_usdc`/`cost_usdc` bucketing,
  never whether the line is recorded or whether `external` is set).

  **Policy sign-off (this IS a GATE-0 policy decision, not an implicit side effect of a
  recording-bug fix)**: this classification is approved by the policy owner (Dais)'s explicit
  directive of 2026-07-09 — goal: "fix HL realized-P&L recording — set `external: true` only
  if the close is real cash-settled." §2's independent audit, cross-checked by the fresh-context
  spec-review adversary (F-6, iteration 1: confirmed `hl.py:61` uses `constants.MAINNET_API_URL`
  — real mainnet, not paper/testnet) and by this feature's own live evidence
  (`evidence/audit-userfills-summary.md` — 146 real fills, real `closedPnl`/`fee`/`tid`/`hash`
  fields on the live API response), establishes that an HL perp close is a real, cash-settled
  clearinghouse transaction, satisfying the same "someone/something outside our own
  bookkeeping settled this" bar GATE-0 already applies to EVM tx confirmation and Solana
  signature confirmation. **Wash-trading / self-dealing defense**: GATE-0's pre-existing
  `net_usdc > 0` gate (REQ-C3, unchanged) still independently requires a net profit — a line
  is transcribed here exactly as the exchange settled it, win or loss, with no judgment about
  WHY the trade happened. This feature places no order, modifies no order, and cancels no
  order (REQ-D3) — it can only ever transcribe fills that Hyperliquid's own matching engine
  already settled against whatever counterparty was on the opposite side of the order book.
  Any colony-internal self-dealing concern (one instance's HL wallet trading against another
  instance's HL wallet) is a property of Hyperliquid's PUBLIC order book, identical to any two
  unrelated third-party traders crossing there, and is out of scope for a feature that adds no
  trading logic and reads settled history only.

- **REQ-C2**: `skills/_shared/lib/ledger.mjs`'s `deriveLine` SHALL pass through a new optional
  field `fill_tid` unchanged when present on the input object — mirroring the existing
  `tx`/`sig` conditional-passthrough pattern exactly (`if (o.fill_tid != null) line.fill_tid
  = o.fill_tid;`). No other existing `deriveLine` behavior changes.
- **REQ-C3**: `skills/_shared/lib/ledger.mjs`'s `isProfitable` SHALL recognize a
  Hyperliquid-shaped line as chain-correctly-confirmed IFF `line.chain === "hyperliquid" AND
  line.fill_tid` is present (not null/undefined) `AND line.confirmed === true` — added as a
  THIRD disjunct alongside the existing EVM (`tx` present AND `status === "0x1"`) and Solana
  (`sig` present AND `confirmed === true`) checks. The existing `net_usdc > 0` gate, the
  non-swap-source gate, and the `external === true` gate continue to apply UNCHANGED and are
  NOT bypassed for Hyperliquid lines — a well-formed Hyperliquid receipt with `net_usdc <= 0`
  or `external !== true` SHALL still classify as NOT profitable.
- **REQ-C4** (documented follow-up — NOT implemented by this feature):
  `skills/earn/self-improve/lib/ledger_reader.py`'s `is_profitable` is a hand-maintained
  Python mirror of `ledger.mjs::isProfitable` (per its own module docstring, which already
  commits to keeping the two in sync). REQ-C3's new disjunct SHALL be noted in a code comment
  there pointing at this feature (`hl-realized-pnl`), but porting the actual Python-side
  check is deferred to a separate feature. This spec's Done criteria do NOT require
  `ledger_reader.py` to recognize Hyperliquid lines as profitable.

### Group D — Identity / money-safety

- **REQ-D1**: THE reconciler SHALL record ledger lines EXCLUSIVELY by invoking the existing
  `skills/earn/lib/record.mjs` `record()` entrypoint — the SAME entrypoint `run.sh`'s
  `record_line()` and `sol-trade`'s `record-swap.mjs` already use. It SHALL NEVER call
  `appendLedger` directly and SHALL NEVER reimplement `assertOwnIdentityOnly` or
  `checkHalt`. This guarantees the malice-guard (own-identity-only) and the P1
  cumulative-net HALT gate apply to every Hyperliquid realized-P&L line exactly as they do
  to every other earn line.
- **REQ-D2**: THE reconciler SHALL resolve the Hyperliquid account address and signing
  identity through the SAME resolution path `hl.py` already uses (`_clients()`/`_key()`,
  itself gated on `resolve-identity.mjs`'s `ANICCA_HOME`-scoped, fail-closed lookup) — no
  new key-loading code path, no hardcoded key, no shared-`$HOME` fallback for a
  non-owner instance.
- **REQ-D3**: THE reconciler SHALL NOT place, modify, or cancel any order, and SHALL NOT
  call `Exchange.market_close`, `Exchange.order`, or `Exchange.update_leverage` anywhere in
  its own code path — it is READ-ONLY against the Hyperliquid exchange (querying fills)
  plus a ledger WRITE (via REQ-D1). Trading decisions (open/close/size/side) remain
  entirely outside this feature's scope.
- **REQ-D4**: A ledger line recorded by this feature SHALL NEVER cause a write to, or be
  influenced by the contents of, any OTHER instance's `earn-ledger.jsonl` or checkpoint
  file — both are read/written exclusively at paths already scoped to THIS instance's own
  checkout (`skills/earn/hl-trade/.last-fill-ts` and `skills/earn/state/earn-ledger.jsonl`,
  both colocated with the caller's own `hl-trade` directory, mirroring the existing
  per-instance-checkout convention already relied on by `.last-trade-ts`).

### Group E — Non-functional / invariants / non-regression

- **REQ-E1**: Lines recorded for `open` / `hl-cooldown` / `hl-observe` / `hl-fund-skipped`
  (the existing non-close narrate paths in `run.sh`'s `STRATEGY=hl` branch) SHALL remain
  UNCHANGED by this feature and SHALL NEVER carry `external: true`.
- **REQ-E2**: This feature SHALL NEVER rewrite, truncate, or reorder an existing line in
  `earn-ledger.jsonl` — every write is an append via `record.mjs` (REQ-D1), which itself
  only ever appends.
- **REQ-E3**: `run.sh`'s `STRATEGY=hl` branch SHALL invoke the reconciler (via a new
  `hl.py reconcile` subcommand) on EVERY wake that reaches the `STRATEGY=hl` branch at all,
  before evaluating the anti-churn cooldown gate and before branching on `ACTION=close` /
  new-position `open` — this is what makes exchange-side auto-close (take-profit / stop-loss
  / liquidation) fills get recorded even though the model issued no explicit `close` that
  wake. This does NOT override `run.sh`'s pre-existing P1 HALT guard (`earn-guard.mjs`,
  `run.sh:85`): if that guard already exits the wake before the `STRATEGY=hl` branch is ever
  reached, the reconciler is correctly never invoked that wake — the guard takes precedence
  for money-safety, and skipping a reconcile pass this way causes no data loss (REQ-B9's
  "next wake retries the same window" guarantee covers this exactly the same as an API
  timeout would).
- **REQ-E4**: `hl.py`'s `close` subcommand keeps performing `Exchange.market_close`
  unchanged (REQ-A1 only removes the false `closed_pnl_usd` field from its JSON output) —
  the close action itself, its risk parameters, and the anti-churn cooldown in `run.sh` are
  OUT OF SCOPE for this feature.
- **REQ-E5**: No proof obligation, code comment, ledger field, or log line introduced by
  this feature SHALL contain the words "dry", "fake", "mock", or "simulated" describing a
  recorded ledger line's own realized numbers. Pure-function UNIT TESTS may use fixture
  data (not live API calls), but MUST be clearly scoped as tests, never as the production
  reconcile path itself.

## 5. Edge cases

| EDGE | Trigger | Expected |
|---|---|---|
| E1 | First-ever run, checkpoint file missing | `since_time_ms = 0` (REQ-B7); full lifetime `userFills` history fetched once |
| E2 | Zero eligible fills since checkpoint | report `{recorded: 0}`; checkpoint file UNCHANGED (REQ-B5) |
| E3 | Fill `closedPnl == 0` exactly | excluded from candidates (REQ-B2); no ledger line; not an error |
| E4 | Fill `tid` already present in a prior ledger line (crash-retry replay) | skipped as duplicate (REQ-B4.1); counted as handled; checkpoint MAY advance past it |
| E5 | Fill with non-numeric/missing `closedPnl` or `fee` | UNPROCESSABLE (REQ-B3) → batch STOPS at this fill (REQ-B4.2); checkpoint does not advance past it; retried next pass |
| E6 | `record.mjs` invocation fails for a fill (identity-guard reject, crash, unparseable output) | batch STOPS at this fill (REQ-B4.3); checkpoint does not advance past it; retried next pass |
| E7 | Checkpoint file corrupted/unreadable | treated as E1 (`since_time_ms = 0`); never crashes (REQ-B7) |
| E8 | Hyperliquid API call raises or times out | whole pass skipped; nothing recorded; checkpoint unchanged (REQ-B9) |
| E9 | A single close produces MULTIPLE partial fills (crossing several resting orders) | EACH fill with `closedPnl != 0` is its OWN ledger line, keyed by its own `tid` (REQ-B4/C1) — never merged into one line |
| E10 | Account has zero USDC / zero fills ever (e.g. the current wallet `0xb9dd3b...`, unfunded) | reconcile reports `{recorded: 0}` every pass; no error — this is the normal empty-history case, not a defect |
| E11 | Tied-timestamp partial STOP (money-safety, confirmed live-data-real — evidence/audit-userfills-summary.md found 1 such tie in the audited wallet's own history): candidates sorted ascending `[X(t=500,tid=1), Y(t=500,tid=2), Z(t=600,tid=3)]`; `X` records successfully; `Y`'s `record_line` call fails (REQ-B4.3) → batch STOPS; checkpoint advances to `X`'s time = 500 (REQ-B5) | The NEXT pass queries `user_fills_by_time(address, 500, now, ...)` (REQ-B8, inclusive) — `X` (tid=1) is re-fetched but skipped as a duplicate (REQ-B4.1), and `Y` (tid=2) IS re-fetched and recorded normally this time. `Y`'s realized P&L/fee is NEVER permanently lost — this is the exact scenario REQ-B8's inclusive boundary exists to make safe (see F-1, spec review iteration 1) |

## 6. Non-functional

- **NFR-1**: A reconcile pass over the audited historical wallet (`0xa3cdd4...`, 146 real
  fills) SHALL NOT silently drop fills due to an unhandled API page/count limit. This spec
  does NOT assume a specific fill-count limit that hasn't been empirically verified —
  whether pagination/chunking is needed is discovered and, if needed, handled during Phase 5
  hardening's live E2E (verification-architecture.md §Done), not guessed here.
- **NFR-2**: No new external Python dependency — reuses the already-vendored
  `hyperliquid-python-sdk` / `eth_account` already imported by `hl.py`.
- **NFR-3**: The reconcile pass adds no persistent process (no server, no daemon) — it runs
  to completion and exits, invoked once per `earn/run.sh` wake.
- **NFR-4**: `already_recorded_tids` (REQ-B4.1's dedup set) is built by a full linear scan of
  `earn-ledger.jsonl` on every reconcile pass. This is ACCEPTABLE at the current ledger scale
  (append-only, never pruned per REQ-E2) and is explicitly NOT optimized by this feature —
  indexing or incremental-scan optimization is deferred as a future improvement if ledger size
  ever makes the full scan a measurable cost; this spec does not guess at that threshold.

## 7. Follow-up (explicitly out of scope for this feature)

- `skills/earn/self-improve/lib/ledger_reader.py::is_profitable` Python port of the new
  Hyperliquid disjunct (REQ-C4).
- Pagination/chunking of `user_fills_by_time` beyond what the 146-fill audited wallet
  requires (NFR-1).
- Any change to `open` / anti-churn / baseline-strategy logic in `hl.py` / `SKILL.md`.
