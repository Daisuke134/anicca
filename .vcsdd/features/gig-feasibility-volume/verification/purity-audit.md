# Purity Boundary Audit

## Feature: gig-feasibility-volume | Phase 5 (lean) | Date: 2026-07-08

## Declared Boundaries

Per `specs/verification-architecture.md` §1:

**Pure core (Tier 1, no I/O)**:
- `funnel.py::summarize_gig_funnel(rows)` (existing, unmodified)
- `funnel.py::dedupe_latest_status(rows, key_field="requestId")` (existing, widened with a
  `key_field` param for listing dedupe reuse)
- `funnel.py::summarize_gig_funnel_by_category(rows)` (new)
- `funnel.py::count_live_listings(listing_rows)` (new)
- `passprep.py`'s `listings_due` boolean-decision sub-logic, factored to take `(listing_rows, now,
  listing_weekly_target)`
- `passprep.py`'s skip-floor logic (existing, unmodified)
- `self-improve/gig/evaluator.py`'s new per-category scoring function (`evaluate_by_category`)
- `funnel_report.py`'s `listings_live` count logic (factored into `funnel.count_live_listings`)
- `passprep.py`'s `cold_start` computation, factored to take `(earnings_rows, SETTLED_set)`
- `cadence-evidence.py`'s tolerant gig timestamp parser (`_gig_ts_to_jst_date`)
- `cadence-evidence.py`'s `_gig_activity_event_dates(applied_rows, listings_rows)`

**Effectful shell (Tier 0, I/O / browser / time)**:
- `passprep.py`'s file reads/writes (`strategy.json`, `strategy.default.json`, `listings.jsonl`,
  `earnings.jsonl`) — atomic-write pattern (`tempfile.mkstemp` + `os.replace`)
- `funnel_report.py`'s file reads/writes (`applied.jsonl`, `listings.jsonl` read, `gig-funnel.jsonl`
  append)
- `gig-cli.sh` STARTUP prompt: listing creation/maintenance on Coconala (CDP daily-driver),
  B2-APPLY submission, B3-LEARN capture, B4-IMPROVE web search + strategy.json diff, B1/B2
  individualized message generation — all genuinely effectful + judgment-laden, explicitly NOT
  unit-testable by design
- `weekly_compare.py::beats_previous_week` (existing, unmodified, out of scope)
- `cadence-contracts.json`'s `gig.source` field + `cadence-evidence.py`'s env-seam path functions
  (`_gig_applied_path`, `_gig_listings_path`)

## Observed Boundaries

Verified this session via `Read` + targeted `grep` on the exact line ranges of each declared-pure
function body (not merely the surrounding file), isolating each pure function from its neighboring
effectful helpers:

| Function | grep for `open(`/`requests.`/`subprocess`/`urllib`/`os.system` inside its body | Result |
|---|---|---|
| `funnel.py` (whole file: `summarize_gig_funnel`, `dedupe_latest_status`, `summarize_gig_funnel_by_category`, `count_live_listings`) | 0 hits, and 0 `import` statements beyond none needed | **CLEAN — genuinely pure**, matches declaration |
| `cadence-evidence.py::_gig_ts_to_jst_date` (lines 41–67) | 0 hits | **CLEAN** |
| `cadence-evidence.py::_gig_activity_event_dates` (lines 147–177) | 0 hits | **CLEAN** |
| `cadence-evidence.py::_read_jsonl_rows` (lines 77–90, the declared effectful shell) | 1 hit (`open(path)`) | **Correctly impure**, exactly where the architecture doc says the file read belongs |
| `passprep.py::compute_listings_due` (lines 88–100) | 0 hits | **CLEAN** |
| `passprep.py::compute_cold_start` (lines 103–117) | 0 hits | **CLEAN** |
| `self-improve/gig/evaluator.py`'s new per-category function | imports checked: only `os`, `sys`, `ledger_metrics.{evaluate_stage1_generic,load_ledger_rows}` — no browser/http/subprocess import anywhere in the file | **CLEAN**, also satisfies PROP-017's stricter "no post/apply/dispatch import" requirement |

**Judgment/determinism boundary** (per `~/.claude/rules/building-effective-ai-agents.md`, binding on
this spec per its §1): re-confirmed via grep this session that zero `re.compile`/regex-literal
judgment exists anywhere in the scope-locked file set — feasibility (`ai_doable`/`ai_infeasible`),
category matching, skip/apply decisions, proposal wording, and search-finding interpretation all
remain natural-language prose in `strategy.json`/`strategy.default.json` fields read and interpreted
by the agent inside `gig-cli.sh`'s STARTUP prompt, never hardcoded classifier logic. This matches
both the behavioral-spec's §1 boundary statement and PROP-001's acceptance criterion.

**Cross-repo mirroring, not import**: `cadence-evidence.py` (repo `~/anicca/`) intentionally carries a
literal local copy of `funnel.py`'s (repo `~/profitable-claude/`) `_WON_STATUSES`/`_PAID_STATUSES`
vocabulary rather than a cross-repo import — verified this is documented in both files' docstrings/
comments as an intentional, acknowledged duplication (not an accidental purity/DRY violation), since
the two repos are genuinely separate deployables with no shared Python package boundary between them.

## Drift / gaps found

No core/shell drift found — every function inspected matches its declared purity classification
exactly, with one caveat surfaced during PROP-030's adversarial probing (cross-referenced from
`verification-report.md`'s GAP-1): the pure functions are pure (no I/O), but they are not fully
defensive against malformed *shape* (non-dict rows) reaching them from their effectful-shell callers.
This is a **robustness** gap inside an otherwise-correctly-pure function, not a purity-boundary
violation — the function still performs zero I/O and remains referentially transparent for all
dict-shaped inputs; it simply raises on a small class of malformed inputs instead of degrading
gracefully. Recorded here because the failure mode's practical impact (a crash reaching all the way to
an unguarded CLI entrypoint with no top-level try/except) is a purity-adjacent hardening concern: the
effectful shell around `cadence-evidence.py`'s gig branch (`status_for_loop()`/`_main()`) does not
provide the same "effectful shell absorbs and neutralizes pure-function exceptions" contract that
`passprep.py`'s `main()` provides for its own pure sub-functions (verified directly — see
verification-report.md GAP-1 for the side-by-side proof).

## Summary

- Every function verification-architecture.md declares "pure" is confirmed genuinely I/O-free by
  direct line-range inspection this session (not merely trusted from the architecture doc).
- Every function declared "effectful shell" is confirmed to contain the I/O, exactly at the declared
  boundary — no I/O leaked into a declared-pure function, no declared-effectful function is secretly
  pure-with-hidden-side-effects.
- No regex/keyword judgment hardcoding found; the judgment/determinism boundary from
  `~/.claude/rules/building-effective-ai-agents.md` is intact.
- **Required follow-up before this feature's hardening is considered fully closed** (non-blocking for
  the literal PROP set, but recommended): harden the effectful-shell boundary around
  `cadence-evidence.py`'s `status_for_loop()`/`_main()` so a malformed ledger row degrades gracefully
  (matching `passprep.py`'s own crash-safety pattern) instead of propagating an uncaught exception —
  see GAP-1 in `verification-report.md`.
