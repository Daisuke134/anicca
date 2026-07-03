# Verification Architecture — clip-post-verify-hardening (Phase 1b) — REV 2 (post iteration-1 FAIL)

## Purity boundary map (REVISED after FIND-006: this requires a real refactor, not just addition)

`post_reel.py:171-183`'s live-share section today is ONE imperative loop mixing I/O (navigate/sleep) with
decision logic (diff/break). This feature extracts 3 PURE decision functions and refactors the loop to
call them, rather than adding new functions alongside untouched old logic:

| Function | Signature | Purity | Replaces |
|---|---|---|---|
| `stabilize_reads(read_fn, max_attempts=4, settle_s=5) -> {"stable": bool, "hrefs": list[str] or None}` | the LOOP is impure (calls `read_fn` which does browser I/O + `time.sleep`), but is refactored so the STABILITY DECISION over the sequence of reads it collects is delegated to a pure helper `_reads_stable(reads: list[list[str]]) -> bool` that this function calls internally | `_reads_stable` is PURE; `stabilize_reads` itself is a thin impure driver | the current single unstabilized `ev(tid, "...querySelectorAll...")` calls at `:112,116,171,177` |
| `diff_new_href(before_hrefs: list[str], after_hrefs: list[str]) -> str or None` | **PURE** | the current inline `new = [h for h in hrefs if h not in before]` at `:180` |
| `classify_outcome(reached: str, before_stable: bool, after_stable: bool, candidate: str or None, reconfirm_stable: bool, reconfirm_hrefs: list[str] or None, before_count: int) -> {"outcome": str, "published": bool, "post_url": str or None}` | **PURE** | new — REQ-004's single point of truth; nothing else may set `outcome` |

Concrete refactor of `post_reel.py:171-183`'s loop, per REQ-001/002/003:
```
before = stabilize_reads(lambda: read_hrefs(tid, handle))          # REQ-001/002
# ...share click...
after1 = stabilize_reads(lambda: read_hrefs(tid, handle))          # REQ-001/002 (post-share)
candidate = diff_new_href(before["hrefs"], after1["hrefs"]) if before["stable"] and after1["stable"] else None
time.sleep(5); # REQ-003
recheck = stabilize_reads(lambda: read_hrefs(tid, handle))
outcome = classify_outcome(res["reached"], before["stable"], after1["stable"], candidate,
                            recheck["stable"], recheck["hrefs"], len(before["hrefs"]) if before["stable"] else None)
res.update(outcome)
```
This is a real code-structure change to `post_reel.py`'s live-share block, not an additive-only patch —
acknowledged explicitly here per FIND-006 so Phase 2 implementation isn't a surprise.

## Proof obligations

| ID | Requirement | Tier | Required (lean) | Verification method |
|---|---|---|---|---|
| PROP-001 | REQ-001 (`_reads_stable`: 2 consecutive identical reads) | 1 (unit) | true | `test_reel_verify.py`: `_reads_stable([["a"],["a","b"],["a","b"],["a","b"]])` → the LAST TWO reads match → stable=true, hrefs=["a","b"]; `_reads_stable([["a"],["b"],["c"],["d"]])` (never repeats across 4 reads) → stable=false, hrefs=None |
| PROP-002 | REQ-002 (bounded 4-attempt timeout → inconclusive) | 1 (unit) | true | feed a 5-read sequence (4 attempts = 5 reads) that never converges → assert `stable=False` and that the caller-facing dict's `hrefs` is `None` (not the last read) — a caller reading `stable=False` must never be tempted to use a non-None `hrefs` |
| PROP-003 | REQ-003 (second independent confirmation: href persists + count exactly +1) | 1 (unit) | true | `classify_outcome` table: (before_stable=True, before_count=2, candidate="X", reconfirm_stable=True, reconfirm_hrefs=["X","a","b"] [len 3 = 2+1]) → outcome="published"; reconfirm_hrefs missing "X" → "unverified"; reconfirm_hrefs len==2 (no net increase, e.g. a different post got deleted+added) → "unverified" (count check fails even though "X" present — REQ-003(b) is a hard AND) |
| PROP-004 | REQ-004 (exactly 3 outcomes; outcome=="published" ONLY via classify_outcome) | 1 (unit) + static check | true | (a) exhaustive branch coverage test over `classify_outcome` asserting return is always one of the 3 literal strings; (b) `grep -n '"outcome"\s*[:=]' post_reel.py` — every assignment site must be inside `classify_outcome`'s return statement, verified by the Phase-3 adversary reading the full diff (not just grep, since grep can't see control flow — this is the concrete "correctly wires" criterion FIND-007 asked for) |
| PROP-005 | REQ-005/006/007 (run.sh 3-way routing) | 2 (integration, concrete stub shape) | true | stub script prints, in turn, these 3 EXACT JSON shapes on stdout (matching the REAL `post_reel.py` output shape plus the new `outcome` key): `{"video":"x.mp4","handle":"aiclipsvault","live":true,"reached":"PUBLISHED","published":true,"outcome":"published","post_url":"https://www.instagram.com/aiclipsvault/reel/FAKE1/"}`, `{"video":"x.mp4","handle":"aiclipsvault","live":true,"reached":"shared-unconfirmed","published":false,"outcome":"unverified","post_url":null}`, `{"video":"x.mp4","handle":"aiclipsvault","live":true,"reached":"no-share-btn","published":false,"outcome":"failed","post_url":null,"error":"no share button"}`. Test asserts: case 1 → file in `posted/`, ledger line has `status:"posted"`; case 2 → file in `pending-verify/`, ledger line has `status:"unverified"`, `post_url:null`; case 3 → file stays in `queue/`, no new ledger line |
| PROP-006 | REQ-008 (self-heal via EXISTING `--verify-only`, not a new mechanism) | 2 (integration) | true | seed `pending-verify/` with a fake clip + sidecar recording `before_count=2`; stub `post_reel.py --verify-only` to return `{"reels":["/aiclipsvault/reel/NEWURL/", ...],"ok":true}` with 3 reels (2+1) → self-heal step moves file to `posted/` + appends ledger line; separately, stub returns only 2 reels (no net increase) → file stays in `pending-verify/`, no ledger line added twice on repeated self-heal runs (idempotency check: run self-heal twice with the same stub output, assert exactly 0 or 1 ledger lines added, never 2) |
| PROP-007 | REQ-009 (monitor counts per the REVISED compound rule) | 1 (unit) | true | feed monitor's ledger-counting python 4 lines: (1) `status:"posted"`, (2) `status:"unverified"`, (3) old-format `post_url:"https://..."` no status, (4) the REAL false-positive-corrected shape (`post_url:null, false_positive_corrected:true`, no status) → assert count == 2 (lines 1 and 3 only) |
| PROP-008 | Live E2E (real post, real independent verify) | 3 (E2E, no-mock) | true | Phase 3+ (main agent, not adversary — adversary has no browser): actually post the real queued clip via the refactored `post_reel.py`; independently re-verify via a SEPARATE fresh browser navigation (new tab/context, not reusing the poster's internal `tid` state) that the account's post count increased by exactly 1 and the new URL is reachable and shows video content |

## Verification tiers legend
- Tier 1: pure-function unit tests (`_reads_stable`, `diff_new_href`, `classify_outcome`), deterministic
  fixtures, no browser/network, no `time.sleep`.
- Tier 2: integration tests using a stub poster script with the EXACT JSON shapes specified in PROP-005/006
  (no real IG network calls — tests `run.sh`'s and the self-heal script's routing logic in isolation).
- Tier 3: real, live, no-mock E2E (HARD RULE 0.24) — the actual queued clip actually gets posted and
  independently reconfirmed via a fresh browser check, executed by the main agent after adversary PASS.

## Gate
Phase 3 (adversarial review) confirms PROP-001..007 PASS via fresh-context, disk-only review, INCLUDING
reading the full diff of `post_reel.py`'s refactored live-share block (not just grepping for the string
`"outcome"`) to confirm `outcome` is set exclusively through `classify_outcome`'s return value with no
bypass path (PROP-004(b)'s concrete "correctly wires" criterion). PROP-008 (live E2E) is explicitly NOT
something the disk-only adversary executes — the adversary instead confirms the wiring is correct in
principle; the main agent runs the actual live post + independent re-verification as the final acceptance
step (HARD RULE 0.37's two-gate design: adversary = disk logic, main agent = live E2E).
