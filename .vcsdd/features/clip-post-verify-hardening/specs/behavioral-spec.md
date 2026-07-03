# Behavioral Spec — clip-post-verify-hardening (Phase 1a) — REV 2 (post iteration-1 FAIL)

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

## Ground truth: the REAL current code contract (read 2026-07-03, cited by file:line)
- `post_reel.py` returns ONE json dict via `print(json.dumps(res, ...))`. Existing keys used today:
  `video`, `handle`, `live`, `reached` (a string state-machine marker: "start"/"composer"/"video-loaded"/
  "caption-step"/"caption-filled"/"READY"/"PUBLISHED"/"shared-unconfirmed"/"no-share-btn"/etc),
  `published` (bool), `post_url` (str|None), `error` (str, only on failure paths). There is currently
  **no** `outcome` field and the literal strings "published"/"unverified"/"failed" (REQ-004 REV1's
  vocabulary) do NOT exist anywhere in the code today — REV 2 below defines exactly how this feature adds
  them without breaking the existing `reached`/`published`/`post_url` fields other tooling may still read.
- `run.sh:87-105` currently branches ONLY on `d.get("post_url")` being truthy — no 3-way branch exists.
- `post_reel.py` already has a `--verify-only` flag (`:82`, implemented `:111-118`, tagged FIND-502/601 in
  its own comments) whose PURPOSE is exactly "reconcile a timeout-killed post so the loop never
  double-posts" — it re-navigates, re-reads reel hrefs, and returns `{"reels": [...], "ok": bool}`. REQ-008
  REV 2 below REUSES this flag instead of inventing a parallel re-check mechanism.
- `post_reel.py:171-183`'s live-share section is ONE imperative loop: click share → loop 10x
  {sleep 12s → navigate → re-read hrefs → compute `new = [h for h in hrefs if h not in before]` → break on
  first match}. There are no separately-callable functions today — REV 2 explicitly scopes the refactor
  needed to extract testable pure logic (see Verification Architecture REV 2, PROP-006).

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

- **REQ-001**: WHEN reading the profile's reel-href list to establish a "before" or "after" snapshot,
  THE SYSTEM SHALL poll the read EXACTLY twice with a 5-second settle delay between reads (firm value,
  not an example), and SHALL treat the snapshot as stable only when both reads return the identical
  ordered list of hrefs.
- **REQ-002**: IF two consecutive reads never match within 4 poll attempts (firm value: attempts 1v2,
  2v3, 3v4 — i.e. at most 5 total reads), THEN THE SYSTEM SHALL treat the snapshot as **inconclusive**
  (a distinct third state, not merely "the last read") and the caller MUST branch on an explicit
  `stable: bool` flag before ever using the returned href list as ground truth.
- **REQ-003**: WHEN a post-share poll finds a candidate new href (present in a stabilized `after` read,
  absent from a stabilized `before` read), THE SYSTEM SHALL perform a SECOND independent confirmation:
  wait 5 seconds, re-navigate to the profile fresh, re-run the REQ-001 stabilize procedure, and confirm
  BOTH (a) the candidate href is present in the re-confirmed stable list AND (b) `len(reconfirmed_hrefs)
  == len(stable_before_hrefs) + 1`.
- **REQ-004**: `post_reel.py`'s output JSON SHALL include a NEW key `outcome` with EXACTLY one of the
  3 literal string values `"published"` (REQ-003's double-confirmation passed), `"unverified"` (share was
  clicked and reached the post-share polling phase, but REQ-001/002/003's stabilize-then-reconfirm chain
  did not pass within its bounded attempts), or `"failed"` (the share button was never reached, i.e. the
  existing `reached` field never advanced to `"READY"`/past the composer steps). The existing `published`
  (bool) and `post_url` (str|None) keys remain unchanged and are set consistently with `outcome`
  (`outcome=="published"` implies `published==True` and `post_url` is the confirmed URL; both other
  outcomes imply `published==False`). This mapping SHALL be produced by a single pure function
  `classify_outcome(...)` — no code path may set `outcome="published"` other than through it (Phase 3
  adversary check, see PROP-004/verification gate below).
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
- **REQ-009 (monitor honesty — REVISED after FIND-001)**: `monitor.sh`'s posts-recorded count SHALL count
  a ledger line as "posted" IF AND ONLY IF: `status == "posted"` (new-format lines from this feature
  onward), OR (for OLD lines predating this feature, backward compat) the line has NO `status` field AND
  a non-null non-empty `post_url` AND does NOT have `"false_positive_corrected": true`. This exact
  compound condition was chosen because the REAL ledger already contains a counter-example line
  (`false_positive_corrected: true`, `post_url: null`, no `status`) that a naive "absent status = posted"
  rule would have miscounted — REV 1 of this requirement was wrong and is superseded by this version.

## Non-functional constraints
- No dry runs (HARD RULE 0.24): Phase 3+ E2E evidence for this feature must be a REAL live post attempt
  with REAL browser-based independent verification — not a mocked/simulated reel-list. This is executed
  by the main agent AFTER Phase 3 adversary PASS (adversary cannot run a live browser — see verification
  architecture gate).
- Backward compatibility is precisely REQ-009's compound rule above, not a looser "absent status" rule.
