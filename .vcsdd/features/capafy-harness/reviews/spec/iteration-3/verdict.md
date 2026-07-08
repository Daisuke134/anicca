# Spec Review Verdict — capafy-harness (Phase 1c) — iteration 3

**Reviewer**: fresh-context adversary (no Builder context, no prior-iteration adversary context), disk-only review.
**Reviewed**: `.vcsdd/features/capafy-harness/specs/{behavioral-spec.md,verification-architecture.md}` REV 3
(REQ-CAP-101..112, PROP-CAP-001..016) against `docs/superpowers/specs/2026-07-09-capafy-harness-design.md`
and the live `~/anicca/skills/self/{cadence-evidence.py, cadence-contracts.json, verify-loops.sh,
verify-loops-audit.sh, cadence-deadline-check.sh, tests/test_cadence_deadline_check.sh}` +
`~/.openclaw/skills/capafy-autopublish/{scripts/publish_finish.sh, scripts/reconcile_ledger.py}` +
`~/Library/LaunchAgents/ai.anicca.{cadence-deadline-check,verify-loops-audit}.plist` implementation.

## Overall verdict: **PASS** (0 BLOCKING findings, 1 non-blocking note for Phase 2)

---

## A. FINDING C-3 resolution — verified by independent full-chain trace, not by trusting the spec's own claim

I re-derived the escalation call chain from scratch (not from iteration-2's verdict) to avoid inheriting a
stale conclusion.

**1. Is `cadence-deadline-check.sh:23`'s `CADENCE_LOOPS` the fix target, and does REQ-CAP-112(e) require it?**
Confirmed. Read the live file directly: line 23 is `CADENCE_LOOPS="clip affiliate video gig bounty
pm-earner founder-loop"` — capafy genuinely absent today. Line 42 is the ONLY `self-fix.sh` invocation in
this file, gated by a per-loop `met==False` check (`:38`) and a once-per-JST-day marker file (`:39-41`),
iterating `$L` from that same `CADENCE_LOOPS` (`:32`). REQ-CAP-112(e) (behavioral-spec.md:361-377) requires
adding `capafy` to this exact string with the same order-preserving-append convention as (a), and explicitly
retracts REV-2's disproven "needs no new wiring" claim. This is byte-for-byte the correct fix location.

**2. Is `cadence-deadline-check.sh` genuinely the ONLY place `self-fix.sh` is invoked for a Cadence Contract
loop — no 4th script?** I did not trust iteration-2's "exactly three places" claim and re-ran the search
myself, independently and more broadly than either prior iteration:
- `grep -rn "self-fix\.sh" ~/anicca/skills/self/` (all `.sh`/`.py`, not just the three named files) — the
  only invocation tied to a per-loop dispatch driven by `$CADENCE_LOOPS`/cadence-contract semantics is
  `cadence-deadline-check.sh:42`. The other hits are: `verify-loops-audit.sh:19` (capafy's legacy
  `stale_hrs`, REQ-CAP-112(c)'s deletion target) and `:22` (reddit's separate, deliberately-deferred legacy
  block, untouched — correctly out of scope); `healthcheck-lib.sh:64` and `healthcheck-runtime-loop.sh:61`
  (a DIFFERENT mechanism entirely — stuck-tmux-pane detection, generic per any loop name, unrelated to "did
  today's cadence happen"; out of this feature's scope, matches the design's As-is table calling this
  SELF-HEAL part "✅稼働中" and unrelated to the cadence-contract escalation this feature adds); and
  `capafy-loop-cli.sh`'s own STARTUP prompt text, which is the AGENT's own judgment-driven self-fix call
  inside its interactive session (not a machine-triggered escalation chain member).
- Grepped for any OTHER hardcoded `CADENCE_LOOPS`-style list anywhere in `~/anicca/skills/`,
  `~/.openclaw/skills/`, and `~/anicca-project/` — found exactly two outside this feature's own spec/design
  docs: `verify-loops-audit.sh` and `cadence-deadline-check.sh`. No third hardcoded escalation-loop list
  exists anywhere in the live, non-spec codebase.
- Checked for duplicate installed copies of these scripts elsewhere on disk (`~/.anicca/`, `~/.blockrun/`,
  `~/.anicca-founder/`, a stale worktree `~/anicca/.worktrees/launchd-daemons/`) — these DO exist as
  installed-framework copies (per this codebase's own multi-instance `install.sh` convention), which raised
  the question of whether a 4th, independently-scheduled escalation path could be running from one of them.
  I checked this directly against the ACTUAL running launchd jobs, not the presence of files on disk:
  `launchctl list | grep -E "cadence|verify-loops"` shows `ai.anicca.cadence-deadline-check` and
  `ai.anicca.verify-loops-audit` loaded, and their plists' `ProgramArguments`
  (`~/Library/LaunchAgents/ai.anicca.{cadence-deadline-check,verify-loops-audit}.plist`) point EXCLUSIVELY
  at `/Users/anicca/anicca/skills/self/{cadence-deadline-check.sh,verify-loops-audit.sh}` — the exact path
  this feature's design doc scopes to. The other installed copies are not loaded by any launchd job found;
  they are dormant/other-instance bodies, not a live 4th escalation path for THIS production capafy loop.

Net: the exhaustive re-search confirms REQ-CAP-112(e) closes the escalation chain completely — there is no
remaining hole. The "3 scripts own capafy's escalation, 2 informational + 1 that actually fires" claim
iteration-2 established and REV-3 encodes is verified correct and complete, not merely plausible.

**3. Was the "配線不要" (no wiring needed) misclaim genuinely retracted?** Yes. REQ-CAP-112's preamble
(behavioral-spec.md:340-342) and item (e)'s own text (:361-366) explicitly state the prior claim "is
DISPROVEN and RETRACTED." The design doc's scope line (`2026-07-09-...-design.md:25`) was updated with an
inline note citing iteration-2 FINDING C-3 and adding `cadence-deadline-check.sh` to the touched-files list.
No trace of the old claim remains in either spec file (grepped for "needs no new wiring" — zero hits in the
current REV 3 files; it only appears, correctly, as a quoted-and-retracted citation inside REQ-CAP-112's own
explanation of why (e) exists).

**4. Are PROP-CAP-016(d)/(e) verifiable and load-bearing?** Yes, and I checked this against the REAL existing
test harness for this file, not just the spec's prose. `~/anicca/skills/self/tests/test_cadence_deadline_check.sh`
already exists (from the prior sibling feature) and proves the exact seams PROP-CAP-016(e) needs are real,
not hypothetical: `VERIFY_LOOPS_SELF_DIR` (fake `SELF` dir with a stub `cadence-evidence.py` and a stub
`self-fix.sh` that logs its calls) and `CADENCE_DEADLINE_NOW_HOUR_JST` (deterministic hour override) are both
genuine, already-proven test seams (`test_cadence_deadline_check.sh:37,43,49`). PROP-CAP-016(e)'s call-log
assertion ("self-fix.sh IS invoked with capafy as its first argument") is directly achievable with this exact
harness. PROP-CAP-016(d)'s `grep 'CADENCE_LOOPS=' cadence-deadline-check.sh` assertion is a trivial, already
line-23-targeted check. Both are genuinely satisfiable as written — this is NOT a repeat of iteration-2's
finding that a proof obligation was structurally unsatisfiable.

**C-3 is genuinely resolved. No new instance of the same disease was found.**

---

## B. Non-blocking note (Phase 2 attention, not a spec defect)

`test_cadence_deadline_check.sh:46` currently hardcodes `[ "$CALLS_1" = 7 ]` ("escalated exactly 7 — one per
Cadence Contract loop") for its 21:00-JST run, because today's `CADENCE_LOOPS` has 7 entries. Once
REQ-CAP-112(e) adds `capafy` as an 8th entry, this stub-`cadence-evidence.py`-based test (which reports
`met=false` for whatever loop name it's called with, including capafy) will genuinely escalate 8 times, and
this pre-existing assertion will fail unless updated to 8. This is not a behavioral-spec gap — no REQ or PROP
needs to change to fix it, it's a one-line, non-judgment test-count bump any competent implementer discovers
immediately on running the existing test suite after REQ-CAP-112(e) lands — but flagging it explicitly so
Phase 2 doesn't get surprised by an "existing test broke" red herring. Not blocking Phase 1c→Phase 2
transition (unlike C-1/C-2/C-3, this affects zero production behavior — only a test file's expected count).

---

## C. Spot-check: iteration-1/iteration-2 findings (C-1, C-2, T-1) not regressed

- **C-1** (`gather_evidence()` + `evidence_by_date_for_streak()` both need a capafy branch): REQ-CAP-102
  unchanged from REV 2's confirmed-resolved wording (behavioral-spec.md:184-211 still requires both
  branches, still cites the exact `gig` mirror shape). Re-read `cadence-evidence.py` directly: the two
  `raise ValueError(f"no evidence source wired for loop: {loop!r}")` sites are still at lines 296 and 353
  (unchanged since iteration-2's citation), no capafy branch present yet in either function — correct
  pre-implementation state, no drift.
- **C-2** (`verify-loops.sh`/`verify-loops-audit.sh` scorecard wiring): REQ-CAP-112(a)-(d) unchanged from
  REV 2's confirmed-resolved wording. Re-read both scripts directly: `verify-loops-audit.sh:35`'s
  `CADENCE_LOOPS` still lacks capafy, `:19`'s legacy `stale_hrs` escalation line still present (both awaiting
  Phase 2 implementation, as expected) — matches the spec's Ground Truth claims exactly, no drift.
- **T-1** (PROP-CAP-009's honest Tier-2 framing): unchanged from REV 2, still mirrors PROP-CAP-008's framing,
  no stub-execution claim. No regression.
- `reconcile_ledger.py:91` still computes the UTC day (unfixed, awaiting REQ-CAP-103) — matches Ground Truth.
- `publish_finish.sh`'s ledger heredoc still lacks `category` extraction — matches Ground Truth, awaiting
  REQ-CAP-104.

All three prior findings remain genuinely resolved at the spec level, and the live code remains in the exact
pre-implementation state the spec describes (no stale citations, no silent drift since iteration-2).

---

## D. Final dimension verdicts

| Dimension | Verdict | Blocking findings |
|---|---|---|
| Completeness | **PASS** | 0 (1 non-blocking note, §B) |
| Testability | PASS | 0 — PROP-CAP-016(d)/(e) confirmed achievable against the REAL existing test harness (`test_cadence_deadline_check.sh`), not merely plausible in prose |
| Consistency | PASS | 0 — REQ-CAP-112(e) internally consistent with (a)-(d) and with PROP-CAP-016; design doc's file-scope line matches the spec's touched-file set exactly (all three scripts) |
| Reality-grounding | PASS | 0 — every Ground Truth claim independently re-verified against live disk state (code, launchd plists, test harness); the "3 scripts, 1 that actually fires" claim re-derived from scratch, not trusted from iteration-2's verdict; confirmed via `launchctl list` + plist `ProgramArguments` that no dormant duplicate-instance copy (`~/.anicca`, `~/.blockrun`, `~/.anicca-founder`) is a live 4th escalation path |
| Agent-vs-code boundary | PASS | 0 — no new judgment introduced by REV 3's diff (a data-list append + a retracted-claim correction); all changes remain in the BUILD AGENTS RIGHT exemption already established in iteration-1 |
| Dais 制約 (AI-disclosure) | PASS | 0 — REQ-CAP-111 unchanged since iteration-1, still a pure prohibition; no requirement anywhere adds/requires AI-disclosure language |

**Total BLOCKING findings: 0.** C-1, C-2, C-3, and T-1 are all genuinely resolved, confirmed independently
against live disk state (code, test harness, and running launchd configuration), not merely against the
spec's own prose. This spec **PASSES** Phase 1c and may proceed to `vcsdd-tdd`.
