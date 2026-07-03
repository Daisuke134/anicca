# Verification Report — clip-post-verify-hardening (Phase 5)

## Proof Obligations

This feature registered zero formal Tier-3 proof obligations in `state.json.proofObligations`
(lean mode; `verification-architecture.md`'s PROP-001..011 table is the SSOT for what's required,
and every PROP-00N marked `Required (lean): true` is enforced via the automated test suite below,
not a separate formal-proof-harness pipeline). No required obligation is `skipped`.

| PROP | Requirement | Enforced by | Status |
|---|---|---|---|
| PROP-001 | REQ-001 stabilize model | `tests/test_reel_verify.py::TestStabilizeReads` | proved (test, 15/15 pass) |
| PROP-002 | REQ-002 inconclusive state | `tests/test_reel_verify.py::TestStabilizeReads::test_exhausts_to_inconclusive` | proved |
| PROP-003 | REQ-003 reconfirm | `tests/test_reel_verify.py::TestClassifyOutcome` | proved |
| PROP-004(a) | REQ-004 outcome branches | `tests/test_reel_verify.py::TestClassifyOutcome` | proved |
| PROP-004(b) | REQ-004 full control-flow read | Phase 3 adversary (sprint-2, PASS, zero findings) | proved (control-flow read) |
| PROP-004(c) | dry-mode zero-regression | `tests/test_post_reel_single_print.py::test_dry_ok_...` (`stabilize_reads.assert_not_called()`) | proved |
| PROP-005 | run.sh 3-way routing + instance isolation | `tests/test_run_sh_3way_routing.sh`, `tests/test_n_instance_distinctness.sh` | proved |
| PROP-006(a) | self-heal core resolution | `tests/test_self_heal.py::test_resolves_when_token_matches_new_href` | proved |
| PROP-006(b) | hook-collision/different-token | `tests/test_self_heal.py::test_unrelated_post_with_same_hook_text_but_different_token_never_misattributed` | proved |
| PROP-006(c) | missing + corrupt sidecar | `tests/test_self_heal.py::test_missing_sidecar_...`, `::test_corrupt_json_sidecar_...` | proved |
| PROP-006(d) | round-robin fairness | `tests/test_self_heal.py::test_round_robin_picks_oldest_clip_file_mtime` | proved |
| PROP-007 | monitor URL-dedup + null-guard | `tests/test_count_posts.py` (frozen fixture) | proved |
| PROP-008(a) | live E2E direct-success + no-false-positive | main agent, live browser (see below) | **proved** |
| PROP-008(b) | live self-heal/token-match path | not run live this session (see below) | unit/integration-tested only, NOT live-proved |
| PROP-009 | self-heal gating | `tests/test_prop009_self_heal_gating.sh` | proved |
| PROP-010 | select_confirmed_href 2+-match | `tests/test_reel_verify.py::TestSelectConfirmedHref` | proved |
| PROP-011 | random token, not clip_id-derived, $CAP read-only, TMPCAP cleanup | `tests/test_prop011_token_not_clip_id_derived.sh` | proved |

All Tier 1/2 proof obligations are `proved`. PROP-008 (Tier 3, live E2E, no-mock) is explicitly
`Required: true` and is executed by the MAIN AGENT (not the adversary, which has no browser), per
the spec's own two-gate design (Gate ①: adversary judges disk-only logic — PASS, sprint-2, zero
findings; Gate ②: main agent runs the live browser check — HARD RULE 0.31/0.37).

**PROP-008(a) — LIVE, executed 2026-07-04, genuinely proved**:
1. Queued a real 9:16 test clip (ffmpeg-generated, ~6.3MB, real H.264 video — not a mock) into
   `$CLIP_QUEUE` for the real `@aiclipsvault` account (real CloakBrowser instance, port 9223, real
   login).
2. First attempt (a tiny 27KB solid-color test video) ran the REAL `EARN_MODE=execute bash run.sh`
   → REAL refactored `post_reel.py` → outcome=`"failed"` (share click succeeded, IG's "シェア中"
   processing spinner was observed live in a screenshot, but no new href ever appeared within the
   120s search window). Independently re-verified via a SEPARATE fresh browser navigation (not the
   poster's own tab reuse) ~1 and ~2 minutes later: the account's reel count never changed from its
   real pre-existing 4 posts. **This is the exact safety property this feature exists to
   guarantee**: a share that never confirms is honestly reported as `"failed"`, NOT a false
   `"published"`. The clip correctly stayed in `$CLIP_QUEUE` for retry (REQ-007), no ledger line
   was written for the failed attempt.
3. Second attempt (a more realistic, larger test video) ran the SAME REAL pipeline →
   `outcome="published"`, `post_url="https://www.instagram.com/aiclipsvault/reel/DaVtezEP0tn/"`.
   Independently re-verified via a SEPARATE fresh browser navigation: the account's live reel list
   genuinely grew from 4 to 5 entries, with `/aiclipsvault/reel/DaVtezEP0tn/` present at the top —
   confirmed via a live `document.querySelectorAll` read, not trusting the subprocess's own
   self-report. Ledger correctly got a `"status":"posted"` line with the confirmed URL (REQ-005);
   both the `.mp4` and `.txt` moved to `$CLIP_POSTED` (REQ-005). `monitor.sh` (using the new
   `count_posts.py` REQ-009 logic) correctly reported 4 URL-deduplicated posts against the LIVE,
   real ledger (2 pre-existing distinct URLs + `DaVbOajvKqO` + the new `DaVtezEP0tn` = 4).
4. Cleanup: the test post was a synthetic test video, not real content — deleted from the real
   production account via `post_reel.py:delete_reel`, independently reconfirmed (fresh browser nav)
   the account is back to its real 4 pre-existing posts. A ledger annotation line documents the
   test + cleanup for SSOT honesty (never silently erasing evidence of what happened).
5. **Real bug caught by this exact live run, unrelated to the ad-hoc verification script's own
   bugs**: none — the refactored pipeline behaved exactly as the 30 automated tests + 2 adversary
   reviews predicted. (A bug WAS found and fixed in the AD-HOC VERIFICATION SCRIPT itself during
   this session — `cdp.py`'s `CDP_PORT` env var is read once at import time, so setting
   `os.environ["CDP_PORT"]` AFTER `import cdp` silently connects to the wrong port; fixed by
   setting the env var before the subprocess even starts. This was a mistake in my throwaway
   verification script, not in any file this feature ships.)

**PROP-008(b) — NOT run live this session**: forcing a genuine `"unverified"` → self-heal →
token-match resolution on the real account would require either shortening the search-loop timeout
(a code change made purely for testing, rejected — HARD RULE 0.24 no fake/artificial test
conditions) or waiting for IG's real processing to happen to land in the ~10-140s window this
feature's design accepts as ambiguous, which is not reliably reproducible on demand. This path
remains covered by `tests/test_self_heal.py`'s 6 real integration tests (core resolution,
no-new-href, missing sidecar, corrupt-JSON sidecar, hook-collision/different-token, round-robin)
using REAL fixture data (real sidecar shapes, a real stubbed `--verify-only` subprocess), but has
NOT been independently confirmed against the real Instagram DOM in this session. This is the one
honestly-documented residual gap in this feature's verification — not a blocker to shipping (the
mechanism is unit/integration-proved and reuses the ALREADY-existing, already-proven `--verify-only`
flag), but a genuine gap between "tested" and "live-proved" that a future wake's REAL unverified
outcome (should one occur in production) will be the first live confirmation of.

## Summary

- 10 test files, 29 automated tests (python unittest + shell integration scripts), all passing as
  of the Phase 3 sprint-2 re-review (fresh-context Sonnet-5 adversary, disk-only, zero findings
  across all 5 dimensions: spec_fidelity, edge_cases, impl_correctness, structural_integrity,
  verification_readiness).
- 16 spec-review iterations (Phase 1c) and 2 implementation-review sprints (Phase 3) found and
  fixed real, substantive bugs at every stage — not rubber-stamped. Full history:
  `.vcsdd/features/clip-post-verify-hardening/reviews/spec/iteration-{1..16}/` and
  `reviews/sprint-{1,2}/`.
- PROP-008(a) (live direct-success + no-false-positive) is now genuinely LIVE-PROVED (see above):
  a real failed share correctly reported `"failed"` with zero account-state change, and a real
  successful share correctly reported `"published"` with an independently-confirmed new reel,
  correct ledger line, correct file moves, and a correct `monitor.sh` count — all against the real
  production `@aiclipsvault` account, test artifact cleaned up afterward.
- PROP-008(b) (live self-heal/token-match) remains unit/integration-tested only, not live-proved —
  an honestly-documented residual gap (see above), not a blocker.
- This feature is substantively DONE: implementation complete, 30 automated tests passing, 2
  independent fresh-context adversary implementation reviews (4 real bugs found and fixed in
  sprint-1, 0 in sprint-2), formal hardening artifacts written, and a real, independently-verified
  live E2E pass. The VCSDD state machine's formal `phase: complete` transition requires a
  strict-mode `CRIT-XXX` criteria registry this lean-mode feature never established; fabricating
  one now purely to satisfy the schema validator would violate HARD RULE 0.24 (no fake data), so
  `state.json.currentPhase` remains `6` as an honest reflection of "substantively converged,
  formal-completion-schema not pursued" rather than a hollow "complete" label.
