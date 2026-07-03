# Verification Architecture — clip-post-verify-hardening (Phase 1b) — REV 4 (post iteration-3 FAIL)

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
after a candidate is first found — does not replace the search). ★ FIXED after iteration-3 FIND-003: ★
the composer/upload/share flow is now GATED on `before["stable"]` — if the before-snapshot never
stabilizes, THE SYSTEM ABORTS BEFORE OPENING THE COMPOSER (treated as an 8th "failed" site, alongside the
existing 6 pre-share sites), so the share button is never clicked and no genuine post can ever occur
un-classified/duplicated:
```python
# before composer opens (replaces the single read at :123):
before = stabilize_reads(lambda: read_hrefs(tid, handle))   # REQ-001/002, up to 3 reads / ~10s
if not before["stable"]:
    res["outcome"] = "failed"; res["error"] = "before-snapshot did not stabilize"
    print(json.dumps(res, ensure_ascii=False)); return   # ABORT before composer — no share risk

# ...unchanged composer/upload/caption/share steps (only reached when before IS stable)...

# post-share: EXISTING 10x12s loop shape preserved, unchanged outer budget.
# (No `if before["stable"]` guard needed here anymore — we already aborted above when unstable,
#  so reaching this point GUARANTEES before["stable"] is True.)
candidate = None
for _ in range(10):                                         # UNCHANGED from :174
    time.sleep(12)                                           # UNCHANGED from :175
    cdp.navigate(tid, f"https://www.instagram.com/{a.handle}/"); time.sleep(5)  # UNCHANGED :176
    hrefs = read_hrefs(tid, a.handle)                         # UNCHANGED single read, :177
    candidate = diff_new_href(before["hrefs"], hrefs)         # was inline :179, now the pure fn
    if candidate: break                                      # UNCHANGED :180-181

reconfirm_hrefs = None
if candidate:                                                 # NEW: only runs if the search found something
    time.sleep(5)                                              # REQ-003's additional wait
    cdp.navigate(tid, f"https://www.instagram.com/{a.handle}/"); time.sleep(5)
    reconfirm_hrefs = read_hrefs(tid, a.handle)                # ONE more read (not a full stabilize —
                                                                # this is a confirmation of an already-found
                                                                # candidate, not the primary race-condition site)

outcome = classify_outcome(candidate, reconfirm_hrefs, len(before["hrefs"]))
res.update(outcome)
```

**The 7th path (iteration-3 FIND-002)**: `post_reel.py:187-190`'s top-level `except Exception as e: ...
finally: print(...)` wraps the entire flow. Fix: change the `finally` block to
`res.setdefault("outcome", "failed"); print(json.dumps(res, ensure_ascii=False))` — this guarantees
`outcome` is ALWAYS present in the printed JSON (defaults to `"failed"` only if nothing upstream already
set it, e.g. an exception fired mid-flow before any of the above code paths ran), without clobbering an
`outcome` that a normal code path already set correctly.
This preserves the full ~120s search budget (FIND-005) and only adds a ~10s reconfirmation AFTER a
candidate is already found — total added latency in the worst case (candidate found on the very last
iteration) is ~10s, not a replacement of the search window.

## Proof obligations

| ID | Requirement | Tier | Required (lean) | Verification method |
|---|---|---|---|---|
| PROP-001 | REQ-001 (3-read/2-pair stabilize model) | 1 (unit) | true | `_reads_stable(["a","b"],["a","b"])` → True; `_reads_stable(["a","b"],["a"])` → False. `stabilize_reads` fixture test: reads=[["a"],["a","b"],["a","b"]] (read2==read3) → stable=True, hrefs=["a","b"]; reads=[["a"],["b"],["c"]] (no consecutive pair matches across all 3 reads) → stable=False, hrefs=None |
| PROP-002 | REQ-002 (3-read exhaustion → inconclusive, hrefs=None not last-read) | 1 (unit) | true | same fixture as PROP-001's failing case — explicitly assert `hrefs is None` (not `["c"]`, the last read) so a caller cannot accidentally use it |
| PROP-003 | REQ-003 (reconfirm: candidate present + count exactly +1, existing 120s loop unaffected) | 1 (unit) | true | `classify_outcome("X", ["X","a","b"], 2)` → outcome="published" (len 3 == 2+1); `classify_outcome("X", ["a","b"], 2)` → "unverified" (X missing from reconfirm); `classify_outcome("X", ["X","a"], 2)` → "unverified" (len 2 != 2+1, count didn't net-increase even though X present); `classify_outcome(None, None, 2)` → "failed" (loop exhausted, no candidate ever) |
| PROP-004 | REQ-004 (outcome on EVERY path: 6 pre-share sites + before-unstable-abort + exception fallback, all inline "failed"; classify_outcome ONLY for the actual post-share branch) | 1 (unit) + Phase-3 full-diff read | true | (a) unit: exhaustive branch test over `classify_outcome`'s 3 return values; (b) Phase-3 adversary reads the FULL diff of all 6 pre-share sites (`:95,108,127,134,141,163`) PLUS the new before-unstable-abort site PLUS the `except/finally` fallback (see REQ-004b/REQ-010 below), confirming each sets `res["outcome"]="failed"` (or, for the fallback, `res.setdefault("outcome","failed")`) and that the post-share branch's `outcome` is set ONLY via `classify_outcome`'s return (control-flow read, not a grep) |
| PROP-005 | REQ-005/006/007 (run.sh 3-way routing) | 2 (integration, concrete stub shape) | true | stub prints, in turn: `{"reached":"PUBLISHED","published":true,"outcome":"published","post_url":"https://www.instagram.com/aiclipsvault/reel/FAKE1/"}`, `{"reached":"shared-unconfirmed","published":false,"outcome":"unverified","post_url":null}`, `{"reached":"no-share-btn","published":false,"outcome":"failed","post_url":null,"error":"no share button"}`. Assert: case 1 → `posted/` + ledger `status:"posted"`; case 2 → `pending-verify/` + ledger `status:"unverified"`,`post_url:null`; case 3 → stays in `queue/`, no new ledger line |
| PROP-006 | REQ-008 (self-heal wiring: caller-side stabilize over multiple `--verify-only` invocations, `--verify-only` itself UNCHANGED) | 2 (integration) | true | stub `post_reel.py --verify-only` as a subprocess that returns a DIFFERENT `reels` list on its 1st call vs. its 2nd call (simulating an unstable read) and an IDENTICAL list on its 2nd vs 3rd call — assert the self-heal driver calls it multiple times (up to 3, per REQ-001's model) and only treats the reels list as ground truth once 2 consecutive calls match; separately, seed `pending-verify/` with a fake clip + sidecar `before_count=2`, stub 3 identical calls returning 3 reels (2+1) → self-heal moves to `posted/` + ledger line; stub returns 2 reels (no increase) → stays in `pending-verify/`; idempotency: run self-heal twice with an unchanged stub, assert only ONE ledger line total |
| PROP-007 | REQ-009 (monitor: URL-deduplicated count, verified against a FROZEN fixture) | 1 (unit, frozen fixture file, NOT the live ledger path) | true | copy the exact 4 lines quoted in behavioral-spec.md's Ground Truth section into a version-controlled fixture file `tests/fixtures/ledger-2026-07-03-snapshot.jsonl` (already created, committed alongside this spec) — feed monitor's counting function THIS FROZEN FILE, never `~/.openclaw/state/clip-earn-ledger.jsonl` directly (that path is live/mutable and will keep drifting as the loop posts more real clips — iteration-3's FIND-001 caught exactly this: the live file already grew to 5 lines mid-review). Assert count == **2** against the frozen fixture. Separately test a synthetic new-format case: 1 `status:"posted"` line + 1 `status:"unverified"` line with DIFFERENT urls → count == 1. (The live ledger's CURRENT real count, whatever it is at Phase 3/E2E time, is checked separately by PROP-008 as a live sanity check, not as this Tier-1 unit test's fixture.) |
| PROP-008 | Live E2E (real post, real independent verify) | 3 (E2E, no-mock) | true | Phase 3+ (main agent only — adversary has no browser): actually post the real queued clip via the refactored `post_reel.py`; independently re-verify via a SEPARATE fresh browser navigation (new tab, not reusing the poster's own `tid`) that the account's post count increased by exactly 1 and the new URL is reachable with video content; re-run `monitor.sh` against the LIVE ledger (not the frozen fixture) and sanity-check its count is plausible (this is a live spot-check, not a pinned-value assertion, since the live ledger keeps growing) |

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
