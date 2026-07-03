# Verification Architecture — clip-post-verify-hardening (Phase 1b)

## Purity boundary map

| Layer | Purity | Location |
|---|---|---|
| `stabilize_reads(reads: list[list[str]]) -> {"stable": bool, "hrefs": list[str] or None}` | **PURE** — given a fixed sequence of poll reads (as data), decides stability with no I/O | new function, `post_reel.py` (or a small extracted module `reel_verify.py`) |
| `diff_new_href(before: list[str], after: list[str]) -> str or None` | **PURE** — set difference, no I/O | same |
| `classify_outcome(before_stable, after_stable, candidate, recheck_stable, recheck_count) -> "published"\|"unverified"\|"failed"` | **PURE** — decision table over booleans/counts, no I/O | same |
| Actual polling (navigate + sleep + read reel hrefs from the live page) | IMPURE (browser I/O) | `post_reel.py` `main()` |
| `run.sh` ledger-write + file move based on outcome | IMPURE (filesystem) | `run.sh` |

The purity boundary is exactly the 3 pure functions above: every decision (is this stable? is there a new
href? published/unverified/failed?) is computable from plain data (lists of strings, counts, booleans),
independent of HOW that data was obtained (real browser vs. a test fixture). This is what makes Phase 2
RED/GREEN testable without a live browser for the DECISION logic, while the actual browser-polling
integration is covered separately in Phase 3 with a REAL live post (no mocks per HARD RULE 0.24).

## Proof obligations

| ID | Requirement | Tier | Required (lean) | Verification method |
|---|---|---|---|---|
| PROP-001 | REQ-001 (stabilize requires 2 consecutive identical reads) | 1 (unit) | true | `test_reel_verify.py`: feed `stabilize_reads` a sequence where reads 1,2 differ and reads 3,4 match → assert stable=true with reads 3/4's href list; feed a sequence that never repeats → assert stable=false |
| PROP-002 | REQ-002 (bounded timeout → inconclusive, not last-read-as-truth) | 1 (unit) | true | feed `stabilize_reads` a 4-read sequence that never converges → assert `stable=false` and NOT silently returning read[3] as if trustworthy (caller must branch on `stable` before using `hrefs`) |
| PROP-003 | REQ-003 (second independent confirmation: href persists + count+1) | 1 (unit) | true | `classify_outcome` unit table: (stable_before=True, candidate="X", recheck_stable=True, recheck_hrefs contains X, recheck_count==before_count+1) → "published"; recheck_hrefs missing X → "unverified"; recheck_count != before_count+1 → "unverified" |
| PROP-004 | REQ-004 (exactly one of 3 outcomes, unverified never reported as published) | 1 (unit) | true | exhaustive table test over `classify_outcome`'s branches, assert the return value is always one of the 3 literal strings and specifically that any recheck-failure path returns "unverified" or "failed", never "published" |
| PROP-005 | REQ-005/006/007 (run.sh routes each outcome to the correct dir + ledger status) | 2 (integration) | true | shell test: fake a `post_reel.py` stub that prints each of the 3 outcome JSONs in turn; assert run.sh moves the file to the correct dir (`posted/`, `pending-verify/`, stays in `queue/`) and the ledger line has the correct `status` field for each case |
| PROP-006 | REQ-008 (self-heal re-check of pending-verify on a later wake) | 2 (integration) | true | seed `pending-verify/` with a fake entry + a stub poster that now returns `published` on re-check; run the self-heal step; assert the file moves to `posted/` and a ledger line appears; separately, stub that still returns unverified → assert file stays in `pending-verify/`, no ledger line added twice |
| PROP-007 | REQ-009 (monitor counts only status=="posted"/absent) | 1 (unit) | true | feed monitor.sh's ledger-counting python a ledger with 2 posted + 1 unverified line → assert `posts recorded : 2`, not 3 |
| PROP-008 | Live E2E (real post, real independent verify) | 3 (E2E, no-mock) | true | Phase 3+: actually post the queued real clip via the fixed `post_reel.py`, independently re-verify via a SEPARATE browser navigation (not reusing the poster's own internal state) that the account's post count increased by 1 and the new URL is reachable — this is the HARD RULE 0.24 no-dry-run gate for this feature |

## Verification tiers legend
- Tier 1: pure-function unit tests, deterministic fixtures, no browser/network.
- Tier 2: integration tests using a stub/fake poster script (still no real IG network calls — stubs
  simulate the poster's JSON output shape, testing run.sh's routing logic in isolation).
- Tier 3: real, live, no-mock E2E (HARD RULE 0.24) — the actual queued clip actually gets posted and
  independently reconfirmed via a fresh browser check.

## Gate
Phase 3 (adversarial review) must confirm PROP-001..007 all PASS via fresh-context, disk-only review of
the pure-function logic and its unit/integration tests. PROP-008 (live E2E) is NOT something the
disk-only adversary can execute — per the two-gate design (adversary judges logic from disk; I execute
the live browser E2E myself afterward, HARD RULE 0.37/0.31) — the adversary instead confirms that the
IMPLEMENTATION correctly wires the pure decision functions into the live polling path (i.e., that
PROP-008 is achievable in principle from reading the code), and I run the actual live post + independent
re-verification myself as the final acceptance step before declaring this feature done.
