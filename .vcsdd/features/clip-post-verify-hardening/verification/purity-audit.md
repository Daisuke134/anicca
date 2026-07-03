# Purity Audit — clip-post-verify-hardening (Phase 5)

## Declared Boundaries

Per `specs/verification-architecture.md`'s "Purity boundary map" section, the 5 pure functions and
their impure callers are:

| Function | Declared purity | Declared location |
|---|---|---|
| `_reads_stable(latest, previous)` | PURE (set equality) | `reel_verify.py` |
| `stabilize_reads(read_fn, ...)` | impure DRIVER (calls injected `read_fn`, does `time.sleep`), delegates comparison to `_reads_stable` | `reel_verify.py` |
| `diff_new_href(before_hrefs, after_hrefs)` | PURE | `reel_verify.py` |
| `classify_outcome(candidate, reconfirm_hrefs, before_count)` | PURE | `reel_verify.py` |
| `select_confirmed_href(candidate_hrefs, candidate_page_texts, expected_token)` | PURE (given already-fetched page texts) | `reel_verify.py` |

Declared consumers: `post_reel.py` (imports `reel_verify` via a hardcoded absolute
`sys.path.insert`, matching its existing `cdp.py` import pattern) and the self-heal driver
`self_heal.py` (imports `reel_verify` as a plain same-directory import, since it lives alongside
`reel_verify.py`). No duplicate/drifting reimplementation permitted anywhere else.

## Observed Boundaries (verified against the real, current code)

- `_reads_stable` (reel_verify.py): `return set(latest) == set(previous)` — genuinely pure, no I/O,
  no mutation of inputs, deterministic.
- `stabilize_reads` (reel_verify.py): calls the injected `read_fn()` and `time.sleep(settle_s)` —
  genuinely impure (I/O + real time), but ALL comparison logic is delegated to `_reads_stable`
  (`if len(reads) >= 2 and _reads_stable(reads[-1], reads[-2])`) — matches the declared "impure
  driver delegating comparison to a pure helper" pattern exactly.
- `diff_new_href` (reel_verify.py): pure set-difference-style scan over two lists, no I/O, no
  mutation — genuinely pure.
- `classify_outcome` (reel_verify.py): pure dict construction from 3 scalar/list inputs, no I/O —
  genuinely pure. (Note: the CALLER, `post_reel.py`, prepends `"https://www.instagram.com"` to
  `res["post_url"]` AFTER calling `classify_outcome` — this URL-formatting step is correctly left
  OUTSIDE the pure function, matching PROP-003's own test fixtures which pass/expect bare
  tokens/hrefs like `"X"`, not full URLs.)
- `select_confirmed_href` (reel_verify.py): pure substring-containment scan over an
  already-provided `candidate_page_texts` dict — the actual browser navigation + page-text
  fetching happens in the CALLER (`self_heal.py`'s `run_self_heal`, via the injected
  `read_page_text` callback), never inside this function — matches the declared boundary exactly.
- **Import verified, no duplication**: `post_reel.py:25-26`
  (`sys.path.insert(0, os.path.expanduser("~/anicca/skills/earn/clip")); import reel_verify`) and
  `self_heal.py:16-17` (`sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import
  reel_verify`) both import the SAME single module file — confirmed via `python3 -c` import-path
  resolution during implementation (both resolve to
  `/Users/anicca/anicca/skills/earn/clip/reel_verify.py`). Grepped both `post_reel.py` and
  `self_heal.py` for any inline reimplementation of `_reads_stable`/`stabilize_reads`/
  `diff_new_href`/`classify_outcome`/`select_confirmed_href` logic outside the shared module: zero
  hits — no drift.
- **`count_posts.py`'s `count_confirmed_posts(lines)`** (not in the original purity boundary map,
  added for REQ-009): takes an already-read list of strings, does no I/O, no mutation — genuinely
  pure. `monitor.sh` (the impure caller) does the file read (`open(sys.argv[1]).readlines()`)
  and passes the resulting list in, matching the same impure-driver/pure-function split pattern
  used throughout this feature.
- **`self_heal.py`'s `run_self_heal(...)`** (the top-level self-heal orchestrator, not itself
  declared pure/impure in the original map since it's new plumbing, not one of the 5 named
  functions): correctly impure (file moves, subprocess calls, `os.utime`), but delegates ALL
  decision logic to the pure `reel_verify` functions (`stabilize_reads`, `select_confirmed_href`)
  — no inline reimplementation of stabilize/select logic found.

## Summary

All 5 originally-declared pure functions are genuinely pure as implemented, with zero duplicate or
drifting reimplementations anywhere in the codebase (verified via direct import-path resolution
and grep for inline reimplementation). The one new pure function this feature adds beyond the
original map (`count_posts.count_confirmed_posts`) correctly follows the same pure/impure split
convention. No purity-boundary violation was found during this audit.
