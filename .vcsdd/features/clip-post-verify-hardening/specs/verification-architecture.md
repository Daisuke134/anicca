# Verification Architecture — clip-post-verify-hardening (Phase 1b) — REV 10 (post iteration-9 FAIL)

## Purity boundary map (3-read/2-pair stabilize model, preserving the existing 120s search window)

`post_reel.py:123` (single unstabilized `_before_reels` read) and `:174-181` (the 10×12s search loop that
diffs a single read against that unstabilized `before`) are the two real race-condition sites. This
feature extracts 3 PURE decision functions; the impure browser-polling code changes to CALL them, but the
existing 10×12s outer search loop's SHAPE is preserved (FIND-005 fix — no shrinking of the search budget):

★ FIXED after iteration-5 FIND-010: all 4 functions below live in ONE NEW shared module,
`~/anicca/skills/earn/clip/reel_verify.py` — both `post_reel.py` (via `sys.path.insert(0,
os.path.dirname(__file__))`-style import, matching its existing `cdp.py` import pattern) and the NEW
self-heal driver script (REQ-008) import from this single file. No duplicate/drifting implementation.

| Function | Signature | Purity | Replaces |
|---|---|---|---|
| `_reads_stable(latest: list[str], previous: list[str]) -> bool` | **PURE** — set equality of two href lists | new helper, `reel_verify.py` |
| `stabilize_reads(read_fn, max_reads=3, settle_s=5) -> {"stable": bool, "hrefs": list[str] or None}` | impure DRIVER (calls `read_fn`, does `time.sleep`), but delegates every comparison to `_reads_stable` | the single read at `:123` (before-snapshot use), `reel_verify.py` |
| `diff_new_href(before_hrefs: list[str], after_hrefs: list[str]) -> str or None` | **PURE** | the inline `new = [h for h in hrefs if h not in before]` at `:179`, `reel_verify.py` |
| `classify_outcome(candidate: str or None, reconfirm_hrefs: list[str] or None, before_count: int) -> {"outcome": str, "published": bool, "post_url": str or None}` | **PURE** | new — the post-share decision only (loop-exhausted/unverified/published); the 6 pre-share failure sites set `outcome="failed"` inline, NOT through this function, `reel_verify.py` |
| `select_confirmed_href(candidate_hrefs: list[str], candidate_captions: dict[str,str], expected_caption: str) -> str or None` | **PURE** — added after iteration-8 FIND-018/019: given the already-fetched candidate hrefs AND their already-fetched live captions (both obtained by IMPURE code), returns the ONE href whose caption exactly matches `expected_caption`, or `None` if zero or more-than-one match | new — self-heal's content-based confirmation (REQ-008 step 6), `reel_verify.py`. The actual browser navigation + caption-reading per candidate href is impure (done by the self-heal driver before calling this), consistent with the purity-boundary pattern already used for `stabilize_reads`. |

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
| PROP-005 | REQ-005/006/007 (run.sh 3-way routing, USING `$CLIP_QUEUE`/`$CLIP_POSTED`/`$CLIP_PENDING_VERIFY` — instance-isolated per FIND-007, tested to the SAME rigor as the existing 4 paths per FIND-014) | 2 (integration, concrete stub shape) | true | stub prints, in turn: `{"reached":"PUBLISHED","published":true,"outcome":"published","post_url":"https://www.instagram.com/aiclipsvault/reel/FAKE1/"}`, `{"reached":"shared-unconfirmed","published":false,"outcome":"unverified","post_url":null}`, `{"reached":"no-share-btn","published":false,"outcome":"failed","post_url":null,"error":"no share button"}`. Assert: case 1 → `$CLIP_POSTED` + ledger `status:"posted"`; case 2 → `$CLIP_PENDING_VERIFY` + ledger `status:"unverified"`,`post_url:null`; case 3 → stays in `$CLIP_QUEUE`, no new ledger line. ★ FIXED after FIND-014: instance-isolation is NOT a new weaker 2-way spot check — EXTEND the EXISTING `tests/test_n_instance_distinctness.sh` (already committed, already does full N-way pairwise distinctness across `["", "myclaude", "clawrouter", "clawrouter-2"]`) to ALSO resolve and assert-distinct `$CLIP_PENDING_VERIFY` for each of those same 4 instance names, exactly like the existing 4 paths — same test file, one more path checked, no separate weaker test. ★ |
| PROP-006 | REQ-008 (self-heal wiring: ONE clip per wake, LEAST-RECENTLY-ATTEMPTED round-robin via CLIP FILE mtime touch, SET+CAPTION sidecar populated via the NOW-PLUMBED `before_hrefs` (FIND-021) + `$CAP` file, CONTENT-VERIFIED confirmation via `select_confirmed_href` using a 40-char whitespace-normalized SUBSTRING match (FIND-022, not full-string equality — robust to IG's own truncation display), shared `reel_verify.py` module, no-placeholder missing-sidecar handling — FIXED after iteration-4 FIND-005/006 + iteration-5 FIND-008/009/010 + iteration-6 FIND-011/012 + iteration-7 FIND-015/016/017 + iteration-8 FIND-018/019/020 + iteration-9 FIND-021/022/023) | 2 (integration) | true | (a) core case: stub `post_reel.py --verify-only` returning a DIFFERENT `reels` list on call 1 vs 2 (unstable) and IDENTICAL on call 2 vs 3 — assert the self-heal driver calls it multiple times and only trusts the result once 2 consecutive calls match; seed `$CLIP_PENDING_VERIFY` with a fake clip + REAL sidecar `<clip>.before-hrefs.json` = `{"before_hrefs":["/aiclipsvault/reel/A/","/aiclipsvault/reel/B/"],"caption":"Money hits different at 3am 💰 #money #ai"}` — ★ FIND-021 regression: also directly assert that when `run.sh` (not just self-heal) first writes THIS sidecar on an `outcome=="unverified"` result, the `before_hrefs` value came from `post_reel.py`'s JSON `res["before_hrefs"]` field (stub `post_reel.py` to return that field, assert `run.sh` copies it verbatim into the sidecar) and `"caption"` came from reading `$CAP`'s file content directly (not from `post_reel.py`'s output) ★; stub 3 identical `--verify-only` calls returning `[...,"/aiclipsvault/reel/NEW/"]` (1 candidate) AND stub the candidate page's `document.body.innerText` for `/NEW/` to CONTAIN the full 40-char normalized prefix (`"Money hits different at 3am 💰 #money #a"`) embedded within a longer realistic page-text blob (proving substring containment, not equality, is what's checked) → `select_confirmed_href` matches → moves to `$CLIP_POSTED` + ledger `"post_url":".../NEW/"` + sidecar deleted; no-new-href case → stays put, clip file mtime touched. ★ FIND-022 truncation regression ★: separately stub `/NEW/`'s innerText to contain the caption prefix followed immediately by IG's literal `"…more"` truncation marker (simulating a real truncated render) → assert the substring-prefix check STILL matches (proving the 40-char/substring design tolerates truncation, unlike a full-equality check which iteration-9 found would false-negative here). (b) **★ THE FIND-018/019 REGRESSION TEST — an unrelated post must NEVER be misattributed ★**: seed the SAME sidecar as (a), stub `--verify-only` returning `[...,"/aiclipsvault/reel/OTHERCLIP/"]` but stub `/OTHERCLIP/`'s innerText to contain a COMPLETELY DIFFERENT caption (`"Someone else's clip #different"`) with NO overlap with the 40-char match_key → assert `select_confirmed_href` returns `None`, clip STAYS in `$CLIP_PENDING_VERIFY`, sidecar NOT deleted. (c) **missing/corrupt sidecar (FIND-008/020, no-placeholder redesign)**: seed a clip in `$CLIP_PENDING_VERIFY` with NO sidecar file → assert self-heal treats it as permanently inconclusive, does NOT create a placeholder sidecar, does NOT delete the clip, does NOT crash, and the CLIP FILE's (not sidecar's) mtime is touched; separately seed a sidecar containing invalid JSON → same assertion. (d) **round-robin fairness via clip-file mtime**: seed 2 pending clips, clip1 (older CLIP FILE mtime) permanently unresolvable (caption never matches) and clip2 (newer clip-file mtime) resolvable (caption matches cleanly). Run self-heal for 2 CONSECUTIVE simulated wakes: wake 1 → clip1 attempted, stays stuck, ITS CLIP FILE'S mtime touched; wake 2 → clip2 now attempted and resolves; clip1 remains safely stuck, never blocking clip2. |
| PROP-010 | `select_confirmed_href`'s own contract (FIXED after iteration-9 FIND-023, which correctly found the 0-match and 1-match cases were tested but the 2+-match case was not, risking a naive `next(match, None)`-style implementation silently picking the wrong href) | 1 (unit) | true | `select_confirmed_href(["/A/","/B/"], {"/A/": "the money hook #ai", "/B/": "the money hook #ai"}, "the money hook #ai")` (BOTH candidates' fetched captions happen to match `expected_caption`) → assert returns `None`, NOT an arbitrary pick of `/A/` or `/B/` — this is the exact branch a naive `next()`-based implementation would get wrong. Combined with the existing 0-match (FIND-018/019 test) and 1-match (core case) tests, this gives full 3-way branch coverage (0 / exactly-1 / 2+) for this pure function, matching its declared purity in the boundary table and closing the Tier-1 test-legend omission FIND-023 also flagged. |
| PROP-009 | REQ-008 gating (self-heal never blocks new-content posting, AND self-heal genuinely executed — FIXED after iteration-5 FIND-009 + iteration-6 FIND-013, which correctly found the original test couldn't distinguish "ran and made no progress" from "never invoked at all") | 2 (integration) | true | seed `$CLIP_PENDING_VERIFY` with a clip whose self-heal check is inconclusive (stub never stabilizes) AND seed `$CLIP_QUEUE` with a fresh, postable clip in the SAME wake — assert BOTH (a) the stub `--verify-only` subprocess was actually invoked at least once (a concrete call-count/call-log assertion, not merely inferred from the outcome — this is what FIND-013 required) AND (b) the wake's new-content posting path (REQ-005-style) still runs and succeeds even though self-heal made no progress |
| PROP-007 | REQ-009 (monitor: URL-deduplicated count with null-guard on BOTH old and new format lines, verified against a FROZEN fixture) | 1 (unit, frozen fixture file, NOT the live ledger path) | true | copy the exact 4 lines quoted in behavioral-spec.md's Ground Truth section into a version-controlled fixture file `tests/fixtures/ledger-2026-07-03-snapshot.jsonl` (already created, committed) — feed monitor's counting function THIS FROZEN FILE, never `~/.openclaw/state/clip-earn-ledger.jsonl` directly (iteration-3's FIND-001 caught exactly this: the live file already grew to 5 lines mid-review, now 5+ and still growing). Assert count == **2** against the frozen fixture. Separately test: (a) 1 `status:"posted"` line + 1 `status:"unverified"` line with DIFFERENT non-null urls → count == 1; (b) **NEW regression test for FIND-005/006**: 1 `status:"posted"` line with `post_url:null` (the exact malformed shape a count-only self-heal bug WOULD have produced, now guarded against by REQ-009 step 1's null-guard) + 1 `status:"posted"` line with a real URL → count == **1**, not 2 (the null-`post_url` line must be excluded, never counted as a distinct "post"). |
| PROP-008 | Live E2E (real post, real independent verify) | 3 (E2E, no-mock) | true | Phase 3+ (main agent only — adversary has no browser): actually post the real queued clip via the refactored `post_reel.py`; independently re-verify via a SEPARATE fresh browser navigation (new tab, not reusing the poster's own `tid`) that the account's post count increased by exactly 1 and the new URL is reachable with video content; re-run `monitor.sh` against the LIVE ledger (not the frozen fixture) and sanity-check its count is plausible (this is a live spot-check, not a pinned-value assertion, since the live ledger keeps growing) |

## Verification tiers legend
- Tier 1: pure-function unit tests (`_reads_stable`, `stabilize_reads`, `diff_new_href`,
  `classify_outcome`, `select_confirmed_href` (FIND-023: was declared pure but omitted from this legend),
  the monitor counting function), deterministic fixtures (including the REAL ledger file as a fixture for
  PROP-007), no browser/network, no real `time.sleep`.
- Tier 2: integration tests using a stub poster/verify-only script with the EXACT JSON shapes specified
  in PROP-005/006 (no real IG network calls — tests `run.sh`'s and the self-heal script's routing logic).
- Tier 3: real, live, no-mock E2E (HARD RULE 0.24) — executed by the main agent after adversary PASS.

## Gate
Phase 3 (adversarial review) confirms PROP-001..007 and PROP-009 PASS via fresh-context, disk-only review,
INCLUDING a full control-flow read (not grep) of all 6 pre-share failure sites plus the post-share branch
to confirm PROP-004(b)'s no-bypass claim, AND confirms the refactored code preserves the existing 10×12s
search loop shape (no silent shrinkage — iteration-2's FIND-005, must not regress), AND confirms
`$CLIP_PENDING_VERIFY` is genuinely sourced from `_instance_paths.sh` (not a hardcoded literal path —
iteration-5's FIND-007), AND confirms the 4 pure functions genuinely live in one shared `reel_verify.py`
module imported by both `post_reel.py` and the self-heal driver (iteration-5's FIND-010, no duplicate
implementation). PROP-008 (live E2E) is executed by the main agent, not the adversary, per the two-gate
design (HARD RULE 0.37: adversary judges disk logic, main agent runs the live browser check).
