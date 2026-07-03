# Verification Architecture — clip-post-verify-hardening (Phase 1b) — REV 3 (post iteration-2 FAIL)

## Purity boundary map (3-read/2-pair stabilize model, preserving the existing 120s search window)

`post_reel.py:123` (single unstabilized `_before_reels` read) and `:174-181` (the 10×12s search loop that
diffs a single read against that unstabilized `before`) are the two real race-condition sites. This
feature extracts 3 PURE decision functions; the impure browser-polling code changes to CALL them, but the
existing 10×12s outer search loop's SHAPE is preserved (FIND-005 fix — no shrinking of the search budget):

| Function | Signature | Purity | Replaces |
|---|---|---|---|
| `_reads_stable(latest: list[str], previous: list[str]) -> bool` | **PURE** — set equality of two href lists | new helper |
| `stabilize_reads(read_fn, max_reads=3, settle_s=5) -> {"stable": bool, "hrefs": list[str] or None}` | impure DRIVER (calls `read_fn`, does `time.sleep`), but delegates every comparison to `_reads_stable` | the single read at `:123` (before-snapshot use) |
| `diff_new_href(before_hrefs: list[str], after_hrefs: list[str]) -> str or None` | **PURE** | the inline `new = [h for h in hrefs if h not in before]` at `:179` |
| `classify_outcome(candidate: str or None, reconfirm_hrefs: list[str] or None, before_count: int) -> {"outcome": str, "published": bool, "post_url": str or None}` | **PURE** | new — the post-share decision only (loop-exhausted/unverified/published); the 6 pre-share failure sites set `outcome="failed"` inline, NOT through this function |

Concrete refactor (preserves the existing 10×12s loop shape at `:174-181`, only ADDS a reconfirm step
after a candidate is first found — does not replace the search):
```python
# before composer opens (replaces the single read at :123):
before = stabilize_reads(lambda: read_hrefs(tid, handle))   # REQ-001/002, up to 3 reads / ~10s

# ...unchanged composer/upload/caption/share steps...

# post-share: EXISTING 10x12s loop shape preserved, unchanged outer budget:
candidate = None
if before["stable"]:
    for _ in range(10):                                     # UNCHANGED from :174
        time.sleep(12)                                       # UNCHANGED from :175
        cdp.navigate(tid, f"https://www.instagram.com/{a.handle}/"); time.sleep(5)  # UNCHANGED :176
        hrefs = read_hrefs(tid, a.handle)                     # UNCHANGED single read, :177
        candidate = diff_new_href(before["hrefs"], hrefs)     # was inline :179, now the pure fn
        if candidate: break                                  # UNCHANGED :180-181

reconfirm_hrefs = None
if candidate:                                                 # NEW: only runs if the search found something
    time.sleep(5)                                              # REQ-003's additional wait
    cdp.navigate(tid, f"https://www.instagram.com/{a.handle}/"); time.sleep(5)
    reconfirm_hrefs = read_hrefs(tid, a.handle)                # ONE more read (not a full stabilize —
                                                                # this is a confirmation of an already-found
                                                                # candidate, not the primary race-condition site)

outcome = classify_outcome(candidate, reconfirm_hrefs,
                            len(before["hrefs"]) if before["stable"] else None)
res.update(outcome)
```
This preserves the full ~120s search budget (FIND-005) and only adds a ~10s reconfirmation AFTER a
candidate is already found — total added latency in the worst case (candidate found on the very last
iteration) is ~10s, not a replacement of the search window.

## Proof obligations

| ID | Requirement | Tier | Required (lean) | Verification method |
|---|---|---|---|---|
| PROP-001 | REQ-001 (3-read/2-pair stabilize model) | 1 (unit) | true | `_reads_stable(["a","b"],["a","b"])` → True; `_reads_stable(["a","b"],["a"])` → False. `stabilize_reads` fixture test: reads=[["a"],["a","b"],["a","b"]] (read2==read3) → stable=True, hrefs=["a","b"]; reads=[["a"],["b"],["c"]] (no consecutive pair matches across all 3 reads) → stable=False, hrefs=None |
| PROP-002 | REQ-002 (3-read exhaustion → inconclusive, hrefs=None not last-read) | 1 (unit) | true | same fixture as PROP-001's failing case — explicitly assert `hrefs is None` (not `["c"]`, the last read) so a caller cannot accidentally use it |
| PROP-003 | REQ-003 (reconfirm: candidate present + count exactly +1, existing 120s loop unaffected) | 1 (unit) | true | `classify_outcome("X", ["X","a","b"], 2)` → outcome="published" (len 3 == 2+1); `classify_outcome("X", ["a","b"], 2)` → "unverified" (X missing from reconfirm); `classify_outcome("X", ["X","a"], 2)` → "unverified" (len 2 != 2+1, count didn't net-increase even though X present); `classify_outcome(None, None, 2)` → "failed" (loop exhausted, no candidate ever) |
| PROP-004 | REQ-004 (outcome on EVERY path: 6 pre-share sites inline "failed" + classify_outcome for post-share) | 1 (unit) + Phase-3 full-diff read | true | (a) unit: exhaustive branch test over `classify_outcome`'s 3 return values; (b) Phase-3 adversary reads the FULL diff of all 6 pre-share sites (`:95,108,127,134,141,163`) confirming each sets `res["outcome"]="failed"` inline before its existing `print();return`, AND confirms the post-share branch's `outcome` is set ONLY via `classify_outcome`'s return (control-flow read, not a grep) |
| PROP-005 | REQ-005/006/007 (run.sh 3-way routing) | 2 (integration, concrete stub shape) | true | stub prints, in turn: `{"reached":"PUBLISHED","published":true,"outcome":"published","post_url":"https://www.instagram.com/aiclipsvault/reel/FAKE1/"}`, `{"reached":"shared-unconfirmed","published":false,"outcome":"unverified","post_url":null}`, `{"reached":"no-share-btn","published":false,"outcome":"failed","post_url":null,"error":"no share button"}`. Assert: case 1 → `posted/` + ledger `status:"posted"`; case 2 → `pending-verify/` + ledger `status:"unverified"`,`post_url:null`; case 3 → stays in `queue/`, no new ledger line |
| PROP-006 | REQ-008 (self-heal via EXISTING `--verify-only`) | 2 (integration) | true | seed `pending-verify/` with a fake clip + sidecar `before_count=2`; stub `--verify-only` → `{"reels":[3 items],"ok":true}` (2+1) → self-heal moves to `posted/` + ledger line; stub → 2 reels (no increase) → stays in `pending-verify/`; idempotency: run self-heal twice with an unchanged 3-reel stub, assert only ONE ledger line total (not two) |
| PROP-007 | REQ-009 (monitor: URL-deduplicated count, verified against the REAL ledger) | 1 (unit, using REAL ledger data as the fixture) | true | feed monitor's counting function the ACTUAL 4 lines from `~/.openclaw/state/clip-earn-ledger.jsonl` verbatim → assert count == **2** (not 3) — this is the literal regression test for the incident: line 2 (`DaLKV2xP8Ij`, true) and line 3 (`DaLKV2xP8Ij`, false-positive duplicate) collapse to 1 distinct URL, plus line 1 (`DaK4tlmvomQ`) = 2 total; separately test a synthetic new-format case: 1 `status:"posted"` line + 1 `status:"unverified"` line with DIFFERENT urls → count == 1 |
| PROP-008 | Live E2E (real post, real independent verify) | 3 (E2E, no-mock) | true | Phase 3+ (main agent only — adversary has no browser): actually post the real queued clip via the refactored `post_reel.py`; independently re-verify via a SEPARATE fresh browser navigation (new tab, not reusing the poster's own `tid`) that the account's post count increased by exactly 1 and the new URL is reachable with video content; re-run `monitor.sh` and confirm PROP-007's count now correctly reflects the new real post |

## Verification tiers legend
- Tier 1: pure-function unit tests (`_reads_stable`, `stabilize_reads`, `diff_new_href`,
  `classify_outcome`, the monitor counting function), deterministic fixtures (including the REAL ledger
  file as a fixture for PROP-007), no browser/network, no real `time.sleep`.
- Tier 2: integration tests using a stub poster/verify-only script with the EXACT JSON shapes specified
  in PROP-005/006 (no real IG network calls — tests `run.sh`'s and the self-heal script's routing logic).
- Tier 3: real, live, no-mock E2E (HARD RULE 0.24) — executed by the main agent after adversary PASS.

## Gate
Phase 3 (adversarial review) confirms PROP-001..007 PASS via fresh-context, disk-only review, INCLUDING a
full control-flow read (not grep) of all 6 pre-share failure sites plus the post-share branch to confirm
PROP-004(b)'s no-bypass claim, AND confirms the refactored code preserves the existing 10×12s search loop
shape (no silent shrinkage — this was iteration-2's FIND-005, must not regress). PROP-008 (live E2E) is
executed by the main agent, not the adversary, per the two-gate design (HARD RULE 0.37: adversary judges
disk logic, main agent runs the live browser check).
