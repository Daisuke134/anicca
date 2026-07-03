# Behavioral Spec — clip-post-verify-hardening (Phase 1a) — REV 15 (post iteration-14 FAIL)

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
- **REQ-004 (outcome field — every code path, including the 6 pre-share failure sites, the
  before-unstable abort, and the exception fallback)**: `post_reel.py`'s output JSON SHALL include a NEW
  key `outcome` with EXACTLY one of 3 literal string values, PRESENT ON EVERY POSSIBLE RETURN PATH with
  no gap:
  - `"failed"` — set at EACH of the 6 pre-share early-return sites (`:95,108,127,134,141,163` per the
    Ground Truth section above) immediately before their existing `print(...); return`; ALSO set at a
    NEW 8th site — immediately after the before-snapshot (REQ-001) if it comes back `stable=False`, THE
    SYSTEM SHALL ABORT BEFORE OPENING THE COMPOSER (no share risk possible if the composer is never
    opened) — this closes iteration-3's FIND-003, where an earlier draft let the composer/share flow
    proceed unconditionally even on an unstable before-read, risking a genuine post being misclassified
    as `"failed"` and duplicate-retried; ALSO set (via `res.setdefault("outcome","failed")` in the
    existing top-level `finally:` block, `:187-190`) as a last-resort fallback so an uncaught exception
    ANYWHERE in the flow (iteration-3 FIND-002's "7th path") still yields a JSON with `outcome` present,
    never absent; ALSO set when the post-share search loop (REQ-003) exhausts all 10 iterations with no
    candidate href ever found at all.
  - `"unverified"` — set when the search loop DID find a candidate href, but REQ-003's reconfirmation
    step failed (candidate missing on reconfirm, OR count didn't increase by exactly 1).
  - `"published"` — set when the search loop found a candidate AND REQ-003's reconfirmation passed.
  The post-share branch's mapping (loop-exhausted / unverified / published) SHALL be produced by a single
  pure function `classify_outcome(...)` — no code path may set `outcome="published"` other than through
  it (Phase 3 adversary check, see PROP-004/verification gate below). All `"failed"` sites (6 pre-share +
  the before-unstable abort) set `outcome="failed"` directly inline; the exception-fallback uses
  `setdefault` so it never clobbers an outcome a normal path already set. The existing `published`(bool)
  and `post_url`(str|None) keys remain unchanged and are set consistently with `outcome`
  (`outcome=="published"` implies `published==True` and `post_url` is the confirmed URL; both other
  outcomes imply `published==False`).
  ★ FIXED after iteration-9 FIND-021 (a real data-plumbing gap: `before["hrefs"]` was computed inside
  `post_reel.py` but never returned to its caller, so `run.sh` had no source for REQ-006's sidecar
  write) ★: WHENEVER `outcome=="unverified"`, `post_reel.py`'s output JSON SHALL ALSO include
  `res["before_hrefs"] = before["hrefs"]` (the exact stabilized list from REQ-001, already computed and
  in scope at that point in the function — no extra browser work, just also assigning it into `res`
  before printing). `run.sh` reads `d.get("before_hrefs")` from this JSON for REQ-006's sidecar write.
  ★ CORRECTION (iteration-12 FIND-031: stale leftover text from the pre-token, hook-matching design
  scrubbed here) ★ — the sidecar does NOT contain a `"caption"` field at all (superseded by REQ-010's
  token design). `run.sh` does not need `post_reel.py` to return the caption either: `run.sh` already
  GENERATED the token itself (REQ-010, before the post attempt) and already has that exact token value in
  hand at sidecar-write time — it simply persists the SAME token string it already generated, not
  anything read back from `post_reel.py` or `$CAP`. See REQ-010 and REQ-008 step 6 for the sidecar's
  actual (and only) shape: `{"before_hrefs": [...], "token": "..."}`.
- **REQ-005**: WHEN `run.sh` observes `outcome=="published"`, THE SYSTEM SHALL append a ledger line with
  `"status":"posted"` (in addition to keeping the existing line shape) and move the clip file to `posted/`
  — unchanged from current behavior except for the added `status` field.
- **REQ-006 (instance-isolated pending-verify dir — FIXED after iteration-5 FIND-007)**: WHEN `run.sh`
  observes `outcome=="unverified"`, THE SYSTEM SHALL append a ledger line with `"status":"unverified"` and
  `"post_url": null` (even if a candidate URL string exists internally — it is NOT confirmed) and move the
  clip file to `$CLIP_PENDING_VERIFY` — a NEW per-`ANICCA_INSTANCE` path added to the EXISTING
  `_instance_paths.sh` (the same file that already defines `CLIP_QUEUE`/`CLIP_POSTED`/`CLIP_ACCTS`/
  `CLIP_LEDGER`, all suffixed `-${ANICCA_INSTANCE}` when set — see `feature/clip-loop-dual-instance-earn`,
  already shipped). `CLIP_PENDING_VERIFY="${HOME}/clips/pending-verify${_SFX}"`, following the exact same
  pattern as the other four. ★ FIXED after iteration-12 FIND-032 (unspecified whether the paired caption
  file moves too) ★: BOTH `$CLIP` (the `.mp4`) AND `$CAP` (its paired `.txt` caption — the SAME original,
  never-mutated file per REQ-010) move to `$CLIP_PENDING_VERIFY` together, exactly mirroring the existing
  `run.sh:94-95` pattern (`mv "$CLIP" "$POSTED/"; mv "$CAP" "$POSTED/"`) — self-heal and any future manual
  inspection need the original caption alongside the video, and this is zero new logic, just the same
  two-file move applied to a different destination directory. NOT back to `$CLIP_QUEUE` (duplicate-post
  risk) and NOT to `$CLIP_POSTED` (false-confirmation risk). This closes the cross-instance collision risk
  iteration-5 correctly
  identified: without instance-suffixing, a self-funded (ClawRouter) instance and the human-funded
  (claude-p) instance sharing one unsuffixed `pending-verify/` dir would corrupt each other's self-heal
  state — the exact class of bug `clip-loop-dual-instance-earn` was built to prevent, now reintroduced by
  this feature's new directory if left unsuffixed.
- **REQ-007**: WHEN `run.sh` observes `outcome=="failed"`, THE SYSTEM SHALL leave the clip file in
  `queue/` (current behavior preserved, no ledger line added) so the loop naturally retries it on a later
  wake.
- **REQ-010 (unique per-ATTEMPT tracking token, RANDOM not clip_id-derived — REDESIGNED after iteration-11
  FIND-028/029, which correctly proved clip_id is NOT a safe uniqueness source: `producer.sh`'s clip_id is
  derived purely from the source video URL with zero history/dedup check against already-processed URLs,
  and its default no-`--url` picker selects the single most recent video from a fixed channel — on any day
  that channel hasn't published something new, or on any manual retry with the same `--url`, `producer.sh`
  deterministically re-derives the IDENTICAL clip_id, which would have produced the IDENTICAL token under
  REV 11's design — reopening the exact misattribution risk REQ-010 exists to close, just via clip_id
  reuse instead of hook-text reuse)**: ★ CLARIFIED after iteration-12 FIND-036 (prior wording ambiguously
  implied self-heal might itself generate a token; the sentence below is scoped to remove that reading
  entirely) ★ — token generation happens at EXACTLY ONE place: WHEN `run.sh` is about to attempt POSTING a
  clip via the direct live-share path (i.e., the ONE call site that invokes `post_reel.py` WITHOUT
  `--verify-only`). THE SYSTEM SHALL generate a FRESH, RANDOM tracking token for THAT ATTEMPT — e.g. `"#c" + <10 random hex
  characters>` (via `python3 -c "import secrets;print(secrets.token_hex(5))"` or equivalent) — NOT derived
  from the clip's filename/ID/source-URL in any way, so two attempts of the identical source video (whether
  a same-day channel-repeat or a manual retry) always get DIFFERENT tokens, structurally eliminating
  FIND-028's collision path regardless of `producer.sh`'s own dedup behavior (which remains unfixed and
  out of scope — this feature does not need `producer.sh` to be collision-free, only the TOKEN to be).
  ★ Self-heal NEVER generates, derives, or regenerates a token, under any circumstance ★: self-heal
  (REQ-008) only ever READS the one token already persisted into the sidecar by THIS post-attempt-time
  generation step, at the moment `run.sh` first wrote `$CLIP_PENDING_VERIFY`'s sidecar (REQ-008 step 6).
  Self-heal's own `--verify-only` calls (REQ-008 step 4) never invoke this token-generation logic at all —
  `--verify-only` is a read-only reconciliation check, not a posting attempt, so there is no new attempt
  for it to generate a token for.
  ★ Concrete file-plumbing mechanism (FIXED after FIND-029, which correctly found `post_reel.py`'s
  `--caption-file` only accepts a file PATH via `open()`, never inline string content, and using `$CAP`
  in-place would risk corrupting the original file across retries/moves) ★: `run.sh` SHALL write the
  ORIGINAL `$CAP` content plus a trailing `"\n<token>"` line into a NEW TEMPORARY file via `mktemp` under
  the existing disk-hygiene convention (HARD RULE 0.26), and pass THAT TEMP FILE's path as `--caption-file`
  to `post_reel.py`. `$CAP` itself is NEVER mutated, NEVER read-modified-written in place — it is only ever
  READ (to build the temp file's content) — so its existing move-on-success (`$CLIP_POSTED`) /
  reuse-on-retry (`queue/`) behavior is completely unaffected. This tracking token, not any
  derived-from-content value, is what REQ-008 step 6's content match checks for.
  ★ Concrete cleanup mechanism (FIXED after iteration-12 FIND-034, which correctly found no concrete
  cleanup construct was ever specified) ★: `run.sh` SHALL register the temp file's removal via
  `trap 'rm -f "$TMPCAP"' EXIT` immediately after `mktemp` creates it and BEFORE invoking `post_reel.py` —
  this fires on every normal exit path (success/failed/unverified) AND on any ordinary signal `run.sh`'s
  own shell receives, requiring zero outcome-specific cleanup code. Explicitly accepted residual risk: a
  SIGKILL (`kill -9`) delivered to `run.sh` between `mktemp` and the trap firing cannot be caught by any
  shell trap (POSIX-fundamental, not a gap in this design) and would leak one temp file under
  `${TMPDIR:-/tmp}`. This is LOW severity and explicitly out of scope for this feature: a leaked temp
  caption file is inert (never read by anything after the attempt ends, never confused with `$CAP`, never
  causes a misattributed post) — unlike a misattributed post, which is the actual failure mode this whole
  feature exists to eliminate. Ordinary disk hygiene (HARD RULE 0.26) sweeps stray temp files
  independently of this feature.
- **REQ-008 (self-heal, REUSING the existing mechanism — WIRING CLARIFIED after iteration-3 FIND-004,
  further hardened after iteration-5 FIND-008/009/010)**: WHEN a wake begins and `$CLIP_PENDING_VERIFY`
  (REQ-006) is non-empty, THE SYSTEM SHALL run a self-heal driver — a NEW shared module
  `~/anicca/skills/earn/clip/reel_verify.py` (FIXED after FIND-010: this is the ONE file that defines
  `_reads_stable`/`stabilize_reads`/`diff_new_href`/`classify_outcome`; `post_reel.py` imports it via
  `sys.path.insert` the same way it already imports `~/.claude/skills/ig-account-create/scripts/cdp.py`
  today; the new self-heal driver script imports the SAME module — one implementation, zero drift risk)
  — that does the following, gated as specified below (FIXED after FIND-009):
  1. **Gating (FIND-009)**: Self-heal runs ONCE per wake, BEFORE producing/posting any new content, but
     does NOT block that wake's normal new-content posting pipeline regardless of its own outcome —
     self-heal and new-content posting are independent steps in the same wake; a still-unresolved
     `pending-verify/` clip is retried on the NEXT wake, indefinitely, without stalling new posts.
  2. **ONE clip per wake, LEAST-RECENTLY-ATTEMPTED by the CLIP FILE'S OWN mtime — ROUND-ROBIN (SIMPLIFIED
     after iteration-6 FIND-011/012; FIXED after iteration-7 FIND-015/016/017 for starvation; ORDERING
     SIGNAL MOVED from the sidecar's mtime to the CLIP FILE's mtime after iteration-8 FIND-020, so
     round-robin fairness no longer depends on whether a sidecar exists at all)**: IF `$CLIP_PENDING_VERIFY`
     contains more than one clip, THE SYSTEM SHALL process ONLY the clip file (not its sidecar) with the
     OLDEST (least-recent) mtime this wake, and SHALL NOT attempt any other pending clip in the same wake.
     THE CLIP FILE'S MTIME SHALL BE TOUCHED (`os.utime()`, no content change) EVERY TIME that clip is
     attempted and remains unresolved at the end of this step — whether unresolved because "no new href
     yet", "no caption match" (step 6), or a missing/permanently-inconclusive sidecar (step 3). This makes
     "oldest mtime" mean "least recently attempted" — a self-balancing round-robin — and, because it keys
     off the CLIP FILE (which always exists for every pending clip) rather than the sidecar (which may be
     missing per step 3), fairness holds even for a clip whose sidecar was lost. A clip that gets attempted
     and stays stuck immediately becomes the MOST recently touched, so a DIFFERENT clip is attempted next
     wake — no single stuck clip can ever block others. ★ Residual, explicitly accepted limitation: a clip
     whose own confirmation is permanently unresolved (lost sidecar, or genuinely never actually published)
     may itself never resolve — SAFE (never guesses, never duplicate-posts) but not OPTIMAL — while
     round-robin guarantees this never prevents OTHER pending clips from making progress. ★
  3. **Missing/corrupt sidecar (FIND-008, REDESIGNED after FIND-018/019/020)**: IF the selected clip's
     sidecar file is MISSING, unreadable, or fails to parse, THE SYSTEM SHALL treat that clip as
     **permanently inconclusive** — no placeholder is ever written (FIND-020: there is no sound content to
     put in a placeholder; a placeholder "diffed against current state" would trivially never show
     anything new, which is a silently different failure mode than the honest "we lost the ability to
     verify this clip" state). Round-robin fairness for THIS case does NOT depend on the sidecar at all
     (see the ordering-signal change in step 2 below), so a permanently-missing sidecar cannot starve
     other clips either way.
  4. Invokes `post_reel.py --verify-only --handle <handle>` as a subprocess UP TO 3 TIMES, waiting 5
     seconds between invocations — REQ-001's stabilize model applied EXTERNALLY, at the CALLER level
     (via the shared `reel_verify.py`'s `stabilize_reads`), across separate `--verify-only` subprocess
     calls (each individual call's own internal read at `post_reel.py:112-113` is untouched).
  5. Stops calling once 2 consecutive `reels` arrays match (stable), or after 3 calls if they never
     match (inconclusive — leave the clip in `$CLIP_PENDING_VERIFY`, try again next wake).
  6. **THE SIDECAR RECORDS A SET AND THE CLIP'S UNIQUE TRACKING TOKEN (REQ-010), AND CONFIRMATION REQUIRES
     A TOKEN MATCH, NOT A COUNT (REDESIGNED after iteration-8 FIND-018/019, hardened again after
     iteration-10 FIND-024/025: hook/caption-PROSE matching was found unsound for THIS project specifically
     — HARD RULE 0.18 "clone-don't-template" means the same proven hook text is deliberately reused
     verbatim across different clips, so a text-based match can genuinely collide between two real,
     different clips. REQ-010's unique-token approach removes this ambiguity entirely: the token is
     mechanically generated per-clip, never reused, and is what gates confirmation — not the hook/caption
     prose)**: when `run.sh` first moves a clip to `$CLIP_PENDING_VERIFY` (REQ-006), it SHALL write a
     sidecar file `$CLIP_PENDING_VERIFY/<clipname>.before-hrefs.json` containing
     `{"before_hrefs": [...stabilized before["hrefs"]...], "token": "#c<10-hex-random>"}` (REQ-010's exact
     RANDOM tracking token generated for THIS ATTEMPT — already computed when the temp caption file was
     built, just persist it verbatim, never re-derive/regenerate it). For the ONE clip being processed
     this wake (step 2), THE SELF-HEAL DRIVER SHALL compute
     `new_hrefs = stabilized_reels_set - set(sidecar["before_hrefs"])` (a real set difference). THEN, FOR
     EACH href IN `new_hrefs` (whatever the count — 0, 1, or more), navigate to that reel's URL and read
     `document.body.innerText` on the permalink page (the same broad text-scan style `post_reel.py` already
     uses elsewhere, e.g. the account-guard check at `:105` — no rigid caption-specific selector). A
     candidate href IS CONSIDERED A MATCH if `sidecar["token"]` (the EXACT literal string, e.g.
     `"#c3d9a1e5f70"`) appears anywhere in that page's `innerText` — a plain substring containment check
     on a short, mechanically-unique alphanumeric token (not prose, not a hook, no whitespace-normalization
     or truncation-tolerance logic needed: the token is short enough that IG's "…more" truncation of a
     LONG caption is irrelevant — the token is placed via REQ-010 immediately after a newline near the end
     of the caption, alongside the existing hashtag block, which IG does render even when truncating the
     preceding prose, per the same visibility as any other hashtag in the caption). IF EXACTLY ONE href's
     page contains the token, THE SYSTEM SHALL treat it as now-confirmed: move BOTH the clip file AND its
     paired `.txt` caption file (which travelled together into `$CLIP_PENDING_VERIFY` per REQ-006's
     FIND-032 fix) to `$CLIP_POSTED`, delete the sidecar file, and append the delayed `"status":"posted"` ledger line WITH
     `"post_url"` SET TO THAT MATCHED URL (never `null` — a `status:"posted"` ledger line MUST always
     carry a real, non-null, CONTENT-VERIFIED `post_url`, per REQ-009's step-1 guard below). IF ZERO hrefs
     match (none of the new posts are this clip's own — genuinely still unpublished, OR the new href(s)
     belong to other clips) OR MORE THAN ONE href matches (an extremely unlikely caption collision — do
     NOT guess), leave the clip in `$CLIP_PENDING_VERIFY` for the next wake (never silently drop it, never
     duplicate-post it, never fabricate a `post_url`). ★ This closes FIND-018/FIND-025 structurally: an
     unrelated post landing in the gap has ITS OWN, mechanically DIFFERENT token (REQ-010 guarantees
     tokens are never reused across clips, unlike hook prose, which per HARD RULE 0.18 IS reused
     verbatim), so it will correctly FAIL the token match and never be misattributed — regardless of how
     many wakes have passed, how many unrelated posts accumulated, or how many clips share identical hook
     text. There is no meaningful residual token-collision risk (unlike the withdrawn caption-prose
     approach): tokens are derived 1:1 from each clip's own unique source-URL-based ID. ★
     Documented known limitation for the genuinely-never-published case: if new content keeps landing via
     the independent new-content pipeline on EVERY subsequent wake and this clip's own post never actually
     lands, this clip may sit in `$CLIP_PENDING_VERIFY` indefinitely (SAFE — never guesses, never
     duplicate-posts). Given real posting cadence is roughly
     hourly at most and self-heal isn't time-critical, this is an acceptable, explicitly-documented
     limitation rather than a defect requiring more disambiguation machinery. ★
- **REQ-009 (monitor honesty — REV 4, adds the null-guard iteration-4 FIND-005 found missing)**:
  `monitor.sh`'s posts-recorded count SHALL be computed as follows:
  1. Collect `status=="posted"` lines (new-format, this feature onward) that have a non-null non-empty
     `post_url` → their `post_url` values. (★ Null-guard ADDED here per iteration-4 FIND-005: REQ-008(3)
     above now guarantees every `status:"posted"` line it writes carries a real URL, so this guard should
     never actually trigger in practice — it exists as defense-in-depth against any future code path that
     might otherwise write a `status:"posted"` line with `post_url:null` and silently inflate the count,
     which is structurally the exact failure mode this entire feature exists to eliminate.)
  2. Collect OLD-format lines (no `status` field) that have a non-null non-empty `post_url` AND do NOT
     have `"false_positive_corrected": true` → their `post_url` values.
  3. Union both sets of `post_url` values into ONE set and DEDUPLICATE by exact URL string equality.
  4. The reported count is `len()` of that deduplicated set — **NOT a raw line count**.
  This is the concrete fix for the real incident: the ledger's line 2 and line 3 share the IDENTICAL
  `post_url` (`DaLKV2xP8Ij`) — line 2 is the true original post, line 3 is the false-positive duplicate
  of it. A line-count rule (REV 1/REV 2, both wrong) counts both = inflates by 1. URL-based
  deduplication correctly collapses them to 1, giving the true count of 2 for that 4-line snapshot
  (line 1's `DaK4tlmvomQ` + line 2/3's shared `DaLKV2xP8Ij` = 2 distinct URLs, matching the real
  Instagram profile's tracked post count at that point in time; a 3rd, `DaK36VYPYuE`, predates ledger
  tracking entirely per D-57 and is not expected to appear in the ledger — out of scope, unchanged).
  ★ IMPORTANT (iteration-3 FIND-001): the live ledger file is MUTABLE and grows every time a real clip
  posts (already grew to 5 lines — a genuine new post `DaVbOajvKqO` landed — mid-review of this very
  spec). The regression TEST for this algorithm (PROP-007) MUST use a FROZEN, version-controlled copy of
  the exact 4-line snapshot quoted above, at `~/anicca/skills/earn/clip/tests/fixtures/ledger-2026-07-03-snapshot.jsonl`
  — ★ path CORRECTED after iteration-14 FIND-040: this is the REAL target codebase (`anicca` repo, where
  `monitor.sh` itself lives), NOT the `.vcsdd/features/.../tests/fixtures/` copy under this spec's own
  `anicca-project` staging tree, which is a separate git repository and not where the implementation or
  its tests actually run ★ — not a live reference to `~/.openclaw/state/clip-earn-ledger.jsonl` — a test
  that reads the live path will keep drifting and eventually fail for reasons unrelated to the algorithm's
  correctness. ★
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
