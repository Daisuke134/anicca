# Behavioral Spec — clip-post-verify-hardening (Phase 1a)

## Context (why this feature exists)
2026-07-03 live incident: `EARN_MODE=execute bash run.sh` self-reported `"posted @aiclipsvault: .../DaLKV2xP8Ij/"`
and moved the queued clip to `posted/`. Independent verification (direct profile check + hard reload,
twice) showed the account was STILL at exactly 3 posts, same 3 URLs as before — nothing new was
published. Root cause: `post_reel.py`'s before/after reel-diff snapshots the profile grid immediately on
navigation; Instagram can render the grid progressively (lazy-load), so an already-existing post can be
absent from the `_before_reels` read and then look "new" in the `after` diff. The ledger recorded a false
"posted" line; the clip was moved out of the queue even though nothing was actually published.

Dais's directive (2026-07-03 verbatim intent): "since verification is so important... since we ain't using
Postiz, we have to VERIFY with browser that shit is actually posted. This should be in the loop also.
Since by having the SSOT, you can be sure that shit was actually posted and you can self-heal and
self-improve." → The ledger (SSOT) must only ever record `posted:true` when independently, robustly
confirmed — never from a single self-report — so that a later wake (this session or a different AI
instance) can trust the ledger completely and self-heal (retry an unverified post, never silently lose
or duplicate a clip).

## In scope
- Make the before/after reel-diff **race-free**: a "stabilize" primitive that polls the reel-href list
  until it stops changing (or a max-timeout), used for BOTH the before-snapshot and the after-check.
- Make a post's "published" status **independently re-confirmed**, not trusted from a single diff: after
  the initial diff finds a candidate new URL, do a SECOND independent check (fresh navigation, wait,
  re-read) that the URL persists AND the total post count is `before_count + 1` (not just "any diff").
- Introduce a third, honest ledger status besides posted/not-posted: **`unverified`** — when the
  post attempt reached "shared" but verification could not conclusively confirm success within the
  timeout. An `unverified` clip is NOT moved to `posted/`, and is NOT left silently in `queue/` either
  (which would cause a duplicate-post retry) — it moves to a distinct `pending-verify/` bucket that a
  later wake re-checks (self-heal) before ever producing new content.
- `run.sh` must only write a ledger "posted" line when `post_reel.py` itself returns a status that has
  passed BOTH the initial diff and the second independent re-confirmation — `run.sh` does not do its own
  separate ad-hoc verification; the poster is the single source of truth for "is this actually live".

## Out of scope
- Fixing the wrong-browser-process bug (D-63, already fixed manually this session — not a code bug, was
  an operational port-collision).
- Building the ClawRouter second instance (task #3), the weekly self-improvement scoring loop (task #4),
  and the promote.fun harness (task #5) — unrelated, separate features.
- Video/frame content verification (MD5/frame-extract of the ALREADY-uploaded video) — this feature only
  hardens "did a NEW post actually appear", not "does its content match the source clip" (a plausible
  follow-on, not required here).

## Requirements (EARS)

- **REQ-001**: WHEN reading the profile's reel-href list to establish a "before" or "after" snapshot,
  THE SYSTEM SHALL poll the read at least twice with a settle delay between reads, and SHALL treat the
  snapshot as stable only when two consecutive reads return the IDENTICAL ordered list (or the SAME set,
  at minimum the same length and same href set) — not a single unstabilized read.
- **REQ-002**: IF the reel-href list does not stabilize within a bounded timeout (e.g. 4 poll attempts),
  THEN THE SYSTEM SHALL treat the snapshot as **inconclusive** rather than silently using the last-read
  (possibly incomplete) list as ground truth.
- **REQ-003**: WHEN a post-share diff finds a candidate new href (present in `after`, absent from a
  STABLE `before`), THE SYSTEM SHALL perform a SECOND independent confirmation: re-navigate to the
  profile fresh, wait, re-read the stabilized reel list, and confirm (a) the candidate href is still
  present AND (b) the stabilized post count equals `stable_before_count + 1`.
- **REQ-004**: THE SYSTEM SHALL report exactly one of three outcomes for a live post attempt:
  `published` (REQ-003's double-confirmation passed), `unverified` (share was attempted, a plausible
  candidate may exist, but double-confirmation did not pass within timeout), or `failed` (no candidate
  href ever appeared, e.g. share button never reachable). `unverified` is NEVER reported as `published`.
- **REQ-005**: WHEN `run.sh` receives a `published` result, THE SYSTEM SHALL append a `posted` ledger
  line (unchanged from current behavior) and move the clip file to `posted/`.
- **REQ-006**: WHEN `run.sh` receives an `unverified` result, THE SYSTEM SHALL append an `unverified`
  ledger line (distinct `status` field, NOT counted as `posted` by any summary/monitor logic) and move
  the clip file to a NEW `pending-verify/` directory (sibling of `queue/`/`posted/`) — NOT back to
  `queue/` (which would risk a future wake re-posting duplicate content while the original share may
  still be processing) and NOT to `posted/` (which would falsely count it as confirmed).
- **REQ-007**: WHEN `run.sh` receives a `failed` result, THE SYSTEM SHALL leave the clip file in `queue/`
  (current behavior preserved) so the loop naturally retries it on a later wake.
- **REQ-008 (self-heal)**: WHEN a wake begins and `pending-verify/` is non-empty, THE SYSTEM SHALL,
  BEFORE producing/posting any new content, re-run the double-confirmation check (REQ-003) against each
  pending-verify clip's expected account; if it now confirms `published`, move it to `posted/` and append
  the (delayed) `posted` ledger line; if it still can't confirm after a reasonable additional wait,
  leave it in `pending-verify/` for the next wake (never silently drop it, never duplicate-post it).
- **REQ-009 (monitor honesty)**: `monitor.sh`'s posts-recorded count SHALL count only ledger lines with
  `status == "posted"` (or absent `status` for backward-compat with pre-existing lines) — `unverified`
  lines SHALL NOT inflate the reported post count.

## Non-functional constraints
- No dry runs (HARD RULE 0.24): Phase 3 E2E evidence for this feature must be a REAL live post attempt
  with REAL browser-based independent verification — not a mocked/simulated reel-list.
- Backward compatibility: existing ledger lines (no `status` field) must not break `monitor.sh` or any
  downstream consumer — treat missing `status` as `"posted"` for lines that have a non-null `post_url`.
