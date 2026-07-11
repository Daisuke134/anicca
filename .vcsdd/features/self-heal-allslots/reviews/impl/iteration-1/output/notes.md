# self-heal-allslots — impl review iteration-1 — adversary notes

No `input/manifest.json` existed at review time (fresh-created feature, no reviewer scaffold yet).
Scope was reconstructed directly from:
- `.vcsdd/features/self-heal-allslots/specs/behavioral-spec.md`
- `.vcsdd/features/self-heal-allslots/specs/verification-architecture.md`
- `.vcsdd/features/self-heal-allslots/CHANGELOG.md`
- `.vcsdd/features/self-heal-allslots/state.json` (mode=lean, currentPhase=refactor)
- the actual worktree source tree at branch `feature/self-heal-allslots`

No Bash tool was available to this adversary. The 13/13 and 9/9 test-pass claims in the task
prompt are recorded in `verdict.json.reviewContext.reportedExternalTestRuns` as externally
reported, not independently re-executed here. All findings below are grounded in direct
Read/Grep of source files, not in re-running tests.

## Q1 — Is the gig/hl_trade/x402_sell/token_launch/clip/video deferral honest or a cop-out?

**HONEST, not a cop-out** — see `verdict.json.deferralHonestyJudgment` for the full evidence
trail. In short: I read `skills/earn/run.sh`'s hl/x402/token branches directly (not the
builder's summary of them) and confirmed none of the three ever write an `action` key at all —
`is_fresh_but_barren` would be structurally incapable of ever returning True for them today, so
marking them `instrumented:true` now would produce a *permanently fabricated OK*, which is worse
than the chosen path. The x402/token "expected long zero-gain steady state" reasoning also holds
up against the actual code (passive server / model-gated launch decision). gig/clip/video's
"different failure class already covered by their own healthchecks" claim is architecturally
consistent with what those loops' own launchd jobs do (not deep-audited line-by-line in this
pass since it wasn't specifically requested and the registry gapNotes are self-consistent with
the existing `gig-healthcheck.sh`/`clip-healthcheck.sh`/`video-healthcheck.sh` pattern already
established elsewhere in the codebase).

The same investigation, however, surfaced the sprint's single most important defect: **the two
slots claimed to be *fully and correctly* wired are not equally well-covered.** sol-trade has a
clean skip/live-pass-only vocabulary; pm-trade has a third `action:"error"` state that the
detector can never see (FIND-001). That inconsistency was not caught by the builder's own
"already writes the EXACT contract" claim in the CHANGELOG, and is not caught by any test in
this sprint's test suite.

## Q2 — No-fabrication for NOT-INSTRUMENTED slots

Confirmed by direct code read of `earning-health-allslots.sh:65-78`: an `instrumented:false`
entry can ONLY reach the `NOT-INSTRUMENTED $ID -- $GAPNOTE` log line and `continue`s immediately
— it can never fall through to the OK/BARREN branches below (those are only reachable for rows
that already passed the `[ "$INSTR" != "1" ]` check). Verified this line fires **every run, for
every non-instrumented entry, unconditionally** (no dedup/cache on it) — satisfies REQ-AS-004's
"never silently skipped."

## Q3 — Detector correctness for the 2 wired slots

sol-trade: correct, matches its own trace vocabulary exactly (verified against
`skills/earn/sol-trade/run.sh`).
pm-trade: **incomplete** — see FIND-001. This is the headline finding of this review.

## Q4 — Self-fix safety / thrash / cost

No thrash risk found. Two independent, non-overlapping anti-spam layers exist and both were
read directly:
1. `earning-health-allslots.sh`'s own per-slot 24h marker (`escalateEveryHrs`, SLOTKEY-derived
   filename, lines 93-106).
2. `self-fix.sh`'s own tmux-session existence + 180-minute stale-fixer replacement lock
   (`self-fix.sh:36,43-61`), keyed independently by normalized loop name.

Fixer model is Sonnet, not Opus (`self-fix.sh:84`) — the task prompt's "Opus fix spam" framing
does not match the code; noting this factually since it was asked directly.

The graduation gap (self-fix.sh's bookkeeping under shared `$HOME/.openclaw`, fixer = claude-p's
human-funded Anthropic subscription, not Franklin's own economy) IS documented, explicitly and
in detail, in both `behavioral-spec.md` REQ-AS-006 and `CHANGELOG.md`'s "Franklin-scoping /
graduation gap" section — confirmed NOT silently shipped as "Franklin-scoped." The detection
SIDE is genuinely Franklin-scoped (plist's `EARNHC_EARN_STATE_DIR` points at
`~/.blockrun/skills/earn/state`, confirmed present and growing on this machine per the
CHANGELOG's own file-size citations, which I did not independently re-verify since it requires
Bash/filesystem access outside the worktree).

One new concern surfaced independently in this review and not discussed in the CHANGELOG:
trace-derived text (`$REASON`) flows unsanitized into the `--dangerously-skip-permissions`
fixer's initial prompt (FIND-005). Inherited from the pre-existing sol-trade-healthcheck.sh
pattern, not new, but now deliberately generalized to more slots without the spec's
Non-functional section acknowledging this specific surface.

## Q5 — Plist / registry hygiene

- Plist confirmed NOT loaded: no `launchctl load` reference to
  `ai.anicca.earning-health-allslots` anywhere in the tree (grepped the whole worktree).
- Registry JSON is well-formed, 8 entries, matches the spec's required slot list exactly.
- `plutil -lint` claim in the CHANGELOG not independently re-run (no Bash).
- Old `sol-trade-healthcheck.sh` + its plist are left in place, undeleted, with the
  unload-before-load duplicate-spawn warning living only in the NEW script's README, not in the
  old script's own file (FIND-006, structural_integrity).

## Tests: real or mocked as claimed?

`test_earning_health_allslots.sh` genuinely constructs its own fresh trace files in an isolated
`mktemp -d` and drives the real `earning-health-allslots.sh` end-to-end via `SELF_FIX_DRYRUN=1`
(a real test seam in `self-fix.sh`, not a mock of `self-fix.sh` itself) — this is a legitimate,
non-tautological integration test for the scenarios it DOES cover (single-slot barren, single
healthy-but-insufficient-length, missing trace file, not-instrumented, and repeat-run
anti-spam). The gaps are coverage gaps (FIND-002, FIND-003) and one weak-fixture issue
(FIND-004), not fabricated/mocked-away assertions.

## Process note (not a project finding)

A `PostToolUse:Write` hook fired after this review's Write calls: "fablize gate observed a tool
failure." The only tool-call failure in this session was the very first `Read` attempt against a
guessed `input/manifest.json` path that did not exist (expected — no manifest scaffold existed
for this feature yet; immediately recovered via `Glob`/`Read` against the real spec/state files,
documented in `verdict.json.reviewContext.scope`). This adversary has no Bash tool and write
access restricted to `reviews/**/output/**`, so it cannot independently diagnose or fix whatever
the fablize gate is tracking outside that scope; flagging it here for the orchestrator rather
than silently proceeding.
