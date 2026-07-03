# Behavioral Spec — clip-post-verify-hardening (Phase 1a) — REV 3 (post iteration-2 FAIL)

## Context (why this feature exists)
2026-07-03 live incident: `EARN_MODE=execute bash run.sh` self-reported `"posted @aiclipsvault: .../DaLKV2xP8Ij/"`
and moved the queued clip to `posted/`. Independent verification (direct profile check + hard reload,
twice) showed the account was STILL at exactly 3 posts, same 3 URLs as before — nothing new was
published. Root cause: `post_reel.py`'s before/after reel-diff snapshots the profile grid immediately on
navigation; Instagram can render the grid progressively (lazy-load), so an already-existing post can be
absent from the `_before_reels` read and then look "new" in the `after` diff. The ledger recorded a false
"posted" line; the clip was moved out of the queue even though nothing was actually published. The
corrective ledger line added to fix this (`clip-earn-ledger.jsonl` last line) has `post_url: null` and
`"false_positive_corrected": true` and NO `status` field — this exact line is the counter-example that
killed REV 1's naive backward-compat rule (see REQ-009 REV 2 below).

Dais's directive (2026-07-03 verbatim intent): "since verification is so important... since we ain't using
Postiz, we have to VERIFY with browser that shit is actually posted. This should be in the loop also.
Since by having the SSOT, you can be sure that shit was actually posted and you can self-heal and
self-improve." → The ledger (SSOT) must only ever record a post as confirmed when independently, robustly
verified — never from a single self-report — so that a later wake (this session or a different AI
instance) can trust the ledger completely and self-heal (retry an unverified post, never silently lose
or duplicate a clip).

## Ground truth: the REAL current code contract (re-verified 2026-07-03, exact line numbers)
- `post_reel.py` returns ONE json dict via `print(json.dumps(res, ...))`. Existing keys used today:
  `video`, `handle`, `live`, `reached` (a string state-machine marker: `"start"`/`"composer"`/
  `"video-loaded"`/`"caption-step"`/`"caption-filled"`/`"READY"`/`"DRY-ok"`/`"PUBLISHED"`/
  `"shared-unconfirmed"`/`"no-share-btn"`/`"verify-only"`), `published` (bool), `post_url` (str|None),
  `error` (str, only on failure paths). There is currently **no** `outcome` field and the literal strings
  `"published"`/`"unverified"`/`"failed"` do NOT exist anywhere in the code today.
- `run.sh:87-105` currently branches ONLY on `d.get("post_url")` being truthy — no 3-way branch exists.
- **Exact early-return (pre-share) failure sites in `post_reel.py`, ALL of which currently `print()` and
  `return` WITHOUT any `outcome` field** — REQ-004 REV 3 below requires each of these to also set
  `res["outcome"] = "failed"` before printing:
  - `:95` not logged in
  - `:108` account-guard fail-closed abort
  - `:127` no create button found
  - `:134` file-chooser load failed
  - `:141` video never loaded (12×5s poll exhausted)
  - `:163` no share button found (`"no-share-btn"`)
  (`:118` verify-only-mode return and `:169` DRY-ok are NOT failure paths — they are distinct successful
  modes, out of scope for the outcome vocabulary.)
- **The actual root-cause single-read site**: `:123` — `res["_before_reels"] = ev(tid, "...querySelectorAll...")`
  — ONE unstabilized read, taken right after `cdp.navigate` with only a 4s sleep, no repeat-read check.
  This is THE site REQ-001 fixes.
- **The actual post-share search window**: `:174-181` — a 10-iteration loop, 12s sleep per iteration
  (~120s total search budget), each iteration re-navigates + re-reads + diffs against the (single,
  unstabilized) `before` list, breaking on the FIRST href not in `before`. REQ-003 REV 3 below explicitly
  PRESERVES this ~120s search budget — it adds a confirmation step AFTER a candidate is found, it does
  NOT replace or shrink the existing 10×12s search loop (this was FIND-005 from iteration-2: REV 2's
  pseudocode had silently collapsed the window to ~45s, which is now corrected).
- `post_reel.py` already has a `--verify-only` flag (`:82`, implemented `:111-118`, tagged FIND-502/601 in
  its own comments) whose PURPOSE is exactly "reconcile a timeout-killed post so the loop never
  double-posts" — it re-navigates, re-reads reel hrefs, and returns `{"reels": [...], "ok": bool}`. REQ-008
  REUSES this flag instead of inventing a parallel re-check mechanism.
- **The real ledger's actual 4 lines** (`~/.openclaw/state/clip-earn-ledger.jsonl`, verified 2026-07-03):
  line 1 = a TRUE positive (`post_url: DaK4tlmvomQ`, no status); line 2 = a TRUE positive
  (`post_url: DaLKV2xP8Ij`, no status); line 3 = the FALSE POSITIVE itself
  (`post_url: DaLKV2xP8Ij` — IDENTICAL to line 2's url — no status, NOT flagged); line 4 = the corrective
  note (`post_url: null`, `false_positive_corrected: true`). REV 2's compound rule
  ("no status AND non-null post_url AND NOT false_positive_corrected") counted lines 1, 2, AND 3
  (line 3's own post_url is non-null and it isn't the line carrying the flag) = **3**, identical to the
  broken pre-fix behavior — a complete no-op for the very incident this feature exists to fix (iteration-2
  FIND-001). REV 3's REQ-009 below fixes this with URL-based deduplication instead of a line-count rule.

## In scope
- Make the before/after reel-diff **race-free** via a `stabilize_reads` primitive (2 consecutive identical
  polls required) used for BOTH the pre-share `_before_reels` capture and each post-share poll.
- Add a NEW explicit `outcome` field to `post_reel.py`'s output JSON, computed by a pure `classify_outcome`
  function, with exactly 3 possible values: `"published"`, `"unverified"`, `"failed"` — additive, the
  existing `reached`/`published`(bool)/`post_url` keys are UNCHANGED for any other consumer.
- Reuse the EXISTING `--verify-only` reconciliation flow (not a new mechanism) for the self-heal check of
  `pending-verify/` clips on a later wake.
- `run.sh` reads the NEW `outcome` field (not just truthy `post_url`) to do a 3-way file-move + ledger
  write.

## Out of scope
- Fixing the wrong-browser-process bug (D-63, already fixed manually this session — was an operational
  port-collision, not a code bug).
- Building the ClawRouter second instance (task #3), the weekly self-improvement scoring loop (task #4),
  and the promote.fun harness (task #5) — unrelated, separate features.
- Video/frame content verification (MD5/frame-extract of the ALREADY-uploaded video) — this feature only
  hardens "did a NEW post actually appear", not "does its content match the source clip".

## Requirements (EARS)

- **REQ-001 (stabilize model — FIXED after FIND-003's 4-vs-5-reads contradiction)**: THE SYSTEM SHALL
  collect reel-href reads ONE AT A TIME, up to a firm maximum of **3 total reads**, waiting a firm
  **5 seconds** between each read. After the 2nd read, and again after the 3rd read (if reached), THE
  SYSTEM SHALL compare the LATEST read against the IMMEDIATELY PRECEDING read (as sets of hrefs, order
  independent): if they match, the snapshot is **stable** and the latest read is ground truth — stop
  collecting further reads. This gives exactly 2 chances to match (read1-vs-read2, read2-vs-read3) within
  exactly 3 reads — no other read-count/attempt-count interpretation is valid.
- **REQ-002**: IF neither of REQ-001's 2 pair-comparisons matches after all 3 reads are collected, THEN
  THE SYSTEM SHALL treat the snapshot as **inconclusive** (`stable=False`, `hrefs=None` — a distinct
  third state, not "the last read used as if trustworthy") and the caller MUST branch on the explicit
  `stable` flag before ever using the href list.
- **REQ-003 (preserves the EXISTING ~120s search window — FIXED after FIND-005)**: THE SYSTEM SHALL KEEP
  the existing post-share search loop unchanged in its outer shape (10 iterations, 12s sleep each,
  ~120s total budget, `post_reel.py:174-181`) — each iteration re-navigates, re-reads reel hrefs ONCE,
  and diffs against a STABILIZED `before` snapshot (REQ-001, taken once before the composer opens). The
  first iteration whose single read yields a non-empty diff produces a CANDIDATE href (this loop's
  existing behavior, unchanged — it is the outer search, not the verification). ONLY THEN, as an
  ADDITIONAL step on top of (not replacing) that search loop, THE SYSTEM SHALL perform ONE independent
  reconfirmation: wait 5 more seconds, re-navigate fresh, re-read once more, and confirm BOTH (a) the
  candidate href is present in that reconfirmation read AND (b) `len(reconfirmation_hrefs) ==
  len(stable_before_hrefs) + 1`. If the outer loop exhausts all 10 iterations with no candidate ever
  found, there is nothing to reconfirm — proceed directly to REQ-004's `"unverified"` classification.
- **REQ-004 (outcome field — every code path, including the 6 pre-share failure sites)**: `post_reel.py`'s
  output JSON SHALL include a NEW key `outcome` with EXACTLY one of 3 literal string values, set on
  EVERY return path (not just the live-share path):
  - `"failed"` — set at EACH of the 6 pre-share early-return sites (`:95,108,127,134,141,163` per the
    Ground Truth section above) immediately before their existing `print(...); return`, AND also when the
    post-share search loop (REQ-003) exhausts all 10 iterations with no candidate href ever found at all
    (this is a stronger negative than "unverified": literally nothing new ever appeared, not even an
    unconfirmed candidate).
  - `"unverified"` — set when the search loop DID find a candidate href, but REQ-003's reconfirmation
    step failed (candidate missing on reconfirm, OR count didn't increase by exactly 1).
  - `"published"` — set when the search loop found a candidate AND REQ-003's reconfirmation passed.
  The post-share branch's mapping (loop-exhausted / unverified / published) SHALL be produced by a single
  pure function `classify_outcome(...)` — no code path may set `outcome="published"` other than through
  it (Phase 3 adversary check, see PROP-004/verification gate below). The 6 pre-share sites set
  `outcome="failed"` directly inline (simple early returns, no decision logic needed there). The existing
  `published`(bool) and `post_url`(str|None) keys remain unchanged and are set consistently with `outcome`
  (`outcome=="published"` implies `published==True` and `post_url` is the confirmed URL; both other
  outcomes imply `published==False`).
- **REQ-005**: WHEN `run.sh` observes `outcome=="published"`, THE SYSTEM SHALL append a ledger line with
  `"status":"posted"` (in addition to keeping the existing line shape) and move the clip file to `posted/`
  — unchanged from current behavior except for the added `status` field.
- **REQ-006**: WHEN `run.sh` observes `outcome=="unverified"`, THE SYSTEM SHALL append a ledger line with
  `"status":"unverified"` and `"post_url": null` (even if a candidate URL string exists internally — it is
  NOT confirmed, so it is not published as a trustworthy `post_url` in the ledger) and move the clip file
  to a NEW `~/clips/pending-verify/` directory (sibling of `queue/`/`posted/`) — NOT back to `queue/`
  (duplicate-post risk) and NOT to `posted/` (false-confirmation risk).
- **REQ-007**: WHEN `run.sh` observes `outcome=="failed"`, THE SYSTEM SHALL leave the clip file in
  `queue/` (current behavior preserved, no ledger line added) so the loop naturally retries it on a later
  wake.
- **REQ-008 (self-heal, REUSING the existing mechanism)**: WHEN a wake begins and `~/clips/pending-verify/`
  is non-empty, THE SYSTEM SHALL, BEFORE producing/posting any new content, call the EXISTING
  `post_reel.py --verify-only --handle <handle>` reconciliation flow (already implemented at
  `post_reel.py:82,111-118` — do not build a parallel mechanism) for each pending-verify clip's expected
  account; IF the returned `reels` list (once run through REQ-001's stabilize check) contains a URL not
  present at the time the clip was moved to `pending-verify/` (tracked via a small sidecar file recording
  the `stable_before_hrefs` count/set at move-time), THEN treat it as now-confirmed: move the clip to
  `posted/` and append the delayed `"status":"posted"` ledger line; OTHERWISE leave it in
  `pending-verify/` for the next wake (never silently drop it, never duplicate-post it).
- **REQ-009 (monitor honesty — REV 3, fixes the no-op found in iteration-2 FIND-001)**: `monitor.sh`'s
  posts-recorded count SHALL be computed as follows:
  1. Collect `status=="posted"` lines (new-format, this feature onward) → their `post_url` values.
  2. Collect OLD-format lines (no `status` field) that have a non-null non-empty `post_url` AND do NOT
     have `"false_positive_corrected": true` → their `post_url` values.
  3. Union both sets of `post_url` values into ONE set and DEDUPLICATE by exact URL string equality.
  4. The reported count is `len()` of that deduplicated set — **NOT a raw line count**.
  This is the concrete fix for the real incident: the ledger's line 2 and line 3 share the IDENTICAL
  `post_url` (`DaLKV2xP8Ij`) — line 2 is the true original post, line 3 is the false-positive duplicate
  of it. A line-count rule (REV 1/REV 2, both wrong) counts both = inflates by 1. URL-based
  deduplication correctly collapses them to 1, giving the true count of 2 for the real ledger
  (line 1's `DaK4tlmvomQ` + line 2/3's shared `DaLKV2xP8Ij` = 2 distinct URLs), matching the real
  Instagram profile's actual post count of 2 tracked posts (a 3rd, `DaK36VYPYuE`, predates ledger
  tracking entirely per D-57 and is not expected to appear in the ledger at all — monitor.sh has never
  claimed to count untracked pre-ledger posts, that is unchanged, out of scope).
  Going forward (once REQ-004/005/006 ship), this exact false-positive-duplicate-URL scenario cannot
  recur (an `unverified` outcome never gets a ledger `post_url`, per REQ-006) — URL-deduplication is
  primarily a historical-data fix plus defense-in-depth, not the primary prevention mechanism (REQ-001/
  002/003's stabilize+reconfirm chain is the primary prevention).

## Non-functional constraints
- No dry runs (HARD RULE 0.24): Phase 3+ E2E evidence for this feature must be a REAL live post attempt
  with REAL browser-based independent verification — not a mocked/simulated reel-list. This is executed
  by the main agent AFTER Phase 3 adversary PASS (adversary cannot run a live browser — see verification
  architecture gate).
- Backward compatibility is precisely REQ-009's URL-deduplication rule above, not a line-count rule.
