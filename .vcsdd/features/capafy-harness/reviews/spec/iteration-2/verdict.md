# Spec Review Verdict — capafy-harness (Phase 1c) — iteration 2

**Reviewer**: fresh-context adversary (no Builder context, no iteration-1 adversary context), disk-only review.
**Reviewed**: `.vcsdd/features/capafy-harness/specs/{behavioral-spec.md,verification-architecture.md}` REV 2
(REQ-CAP-101..112, PROP-CAP-001..016) against `docs/superpowers/specs/2026-07-09-capafy-harness-design.md`
and the live `~/anicca/skills/self/{cadence-evidence.py, cadence-contracts.json, verify-loops.sh,
verify-loops-audit.sh, cadence-deadline-check.sh}` + `~/.openclaw/skills/capafy-autopublish/{publish_finish.sh,
reconcile_ledger.py, build_config.py, state/published.jsonl}` implementation.

## Overall verdict: **FAIL** (1 NEW BLOCKING finding: C-3)

C-1, C-2, and T-1 from iteration-1 are all genuinely, verifiably fixed. But independently reading the full
escalation call chain (not just the two files iteration-1 named) surfaced a **third script with the exact
same disease as C-2** — `cadence-deadline-check.sh`, the script that actually invokes `self-fix.sh` for
Cadence Contract loops — which REQ-CAP-112 never touches, and which the spec's own prose *incorrectly*
asserts needs no wiring. As written, this REV would ship a regression: capafy's only current escalation path
(legacy `stale_hrs`) gets deleted, and no replacement escalation path is actually wired for it.

---

## A. Resolution of C-1 / C-2 / T-1 — verified against live code

### C-1 (RESOLVED)
Read `cadence-evidence.py` directly (`grep -n "raise ValueError\|^def "`): `gather_evidence()` starts at
line 270, ends its per-loop if-chain with `raise ValueError(...)` at line **296**; `evidence_by_date_for_streak()`
starts at line 299, ends with the same raise at line **353** — confirmed TWO independent per-loop dispatch
chains exist exactly as REQ-CAP-102's Ground Truth claims. REQ-CAP-102 (behavioral-spec.md:191-202) now
explicitly requires a matching `if loop == "capafy":` branch in BOTH `gather_evidence()` AND
`evidence_by_date_for_streak()`, reusing the same `_capafy_row_exists_event_dates()` helper in each — I
directly compared this against the live `gig` branch in both functions (`:274-275`, `:313-318`) and confirmed
the mirror structure requested is structurally identical (byte-for-byte shape, only names differ), matching
the requirement's own claim. PROP-CAP-015 (verification-architecture.md:59) exercises `status_for_loop("capafy")`
end-to-end for both a populated and a missing `published.jsonl` fixture, asserting no raise — I confirmed
`_read_jsonl_rows()` (`cadence-evidence.py:77-90`) already returns `[]` gracefully for a missing file, so
PROP-CAP-015(c)'s "no crash on missing file" claim is achievable exactly as described. **C-1 is closed.**

Minor non-blocking note: behavioral-spec.md's Ground Truth section (line 92) cites the two raise lines as
`:293, :353`; live line numbers are actually `296, 353` (gather_evidence's raise is 3 lines later than cited
— evidence_by_date_for_streak's `:353` citation IS exact). This 3-line drift was already present verbatim in
iteration-1's own citation and does not change any conclusion (the two-independent-chains claim, the mirror
requirement, and PROP-CAP-015 are all still correct) — flagging only because REV2's Ground Truth header claims
"re-verified 2026-07-09, exact line numbers." Not blocking.

### C-2 (RESOLVED)
Read `verify-loops-audit.sh` and `verify-loops.sh` directly:
- `verify-loops-audit.sh:35`: `CADENCE_LOOPS="clip affiliate video gig bounty pm-earner founder-loop"` —
  confirmed capafy is currently absent, matching the spec's Ground Truth claim exactly.
- `verify-loops-audit.sh:19`: `[ "$(stale_hrs "$CAP")" -ge 30 ] && bash "$SELF/self-fix.sh" capafy "audit: no
  new capafy skill published in >30h..."` — confirmed present, matching REQ-CAP-112(c)'s deletion target
  exactly (same line, same text).
- `verify-loops-audit.sh:30-32`: comment reads `"capafy/reddit/lm (above) keep stale_hrs()/self-fix unchanged
  (REQ-LV-104, out of this feature's scope)"` — confirmed present, matching REQ-CAP-112(d)'s target text
  exactly.
- `verify-loops.sh:46-52`: confirmed `cadence_line` echo lines exist for clip/affiliate/video/gig/bounty/
  pm-earner/founder-loop, and capafy is genuinely absent from this block — matching REQ-CAP-112(b)'s target.

REQ-CAP-112 (behavioral-spec.md:331-356) requires all four sub-fixes (a)-(d) exactly matching what I found on
disk, and PROP-CAP-016 (verification-architecture.md:71) tests all four plus a byte-identical-diff guard on
every other loop's block (including reddit/lm, which remain deliberately deferred). The design doc's file-scope
line (`2026-07-09-...-design.md:25`) was also updated to include `verify-loops.sh, verify-loops-audit.sh`
explicitly, with an inline note citing iteration-1 FINDING C-2. **The two specific gaps iteration-1 found are
closed as specified** — see Finding C-3 below for a THIRD gap in the same escalation chain that iteration-1
did not surface and this REV does not close.

### T-1 (RESOLVED)
PROP-CAP-009 (verification-architecture.md:65) is rewritten to the same honest Tier-2
grep/text-content-assertion framing as PROP-CAP-008, with an explicit note that no stub-execution/file-write
assertion is claimed and that the real behavioral proof is deferred to the Tier-3 main-agent E2E check. I
confirmed no deterministic function exists anywhere in the purity-boundary table (verification-architecture.md
lines 17-27) that mechanically maps an agent-reach return value to a `strategy.json` write — the table's
`apply_category_boost`/`funnel_metrics.py` entries are for the METRICS half (REQ-CAP-108), not the search half
(REQ-CAP-107), so PROP-CAP-009's rewritten scope is honest and consistent with the rest of the document.
**T-1 is closed.** The non-blocking `apply_category_boost` location note is also resolved: it is now pinned to
`funnel_metrics.py`'s `boost-category`/`record-zero-signal` CLI subcommands (verification-architecture.md:26-27),
with no remaining "or STARTUP-driven inline write" ambiguity.

---

## B. NEW findings from this iteration's independent read

### FINDING C-3 (BLOCKING, Completeness): REQ-CAP-112 wires 2 of 3 scripts that own capafy's escalation — `cadence-deadline-check.sh` is the ONE that actually calls `self-fix.sh`, and it is never touched

I traced the full call chain for how a Cadence Contract loop's `met=False` actually turns into a `self-fix.sh`
invocation, independent of what REQ-CAP-112 claims. There are exactly three places a cadence-contract loop
name can appear in this codebase's scripts, not two:

1. `verify-loops.sh:46-52`'s `cadence_line()` echoes — **purely informational** (prints a scorecard string to
   stdout/log). No `self-fix.sh` call anywhere in this file for cadence-contract loops (confirmed via
   `grep -n self-fix.sh verify-loops.sh` — zero matches).
2. `verify-loops-audit.sh:37-41`'s `for L in $CADENCE_LOOPS` loop — also **purely informational**: it only
   builds a `CADENCE_SCORECARD` string that gets appended to a `loop-report.sh audit ... no-op 0` call
   (`verify-loops-audit.sh:69`). Confirmed via direct read: no `self-fix.sh` invocation exists inside this
   for-loop or anywhere else in the file tied to `$L`/`CADENCE_LOOPS`.
3. `cadence-deadline-check.sh:23,32-44` — **this is the only place `self-fix.sh` is actually invoked for a
   Cadence Contract loop** (`cadence-deadline-check.sh:42`: `bash "$SELF/self-fix.sh" "$L" "cadence audit:
   $L's Cadence Contract was NOT met by 21:00 JST today..."`), gated by its OWN, SEPARATE hardcoded variable
   at line 23: `CADENCE_LOOPS="clip affiliate video gig bounty pm-earner founder-loop"` — **not derived from
   `cadence-contracts.json`'s keys, not read from `verify-loops-audit.sh`'s `CADENCE_LOOPS`, a completely
   independent hardcoded string that also lacks `capafy`.**

Confirmed via `grep -n self-fix.sh` across all three files: `cadence-deadline-check.sh:42` is the ONLY
`self-fix.sh` call tied to a cadence-contract `$L` variable anywhere in this codebase; the only OTHER
`self-fix.sh` calls are `verify-loops-audit.sh:19` (capafy's legacy `stale_hrs` line, which REQ-CAP-112(c)
deletes) and `verify-loops-audit.sh:22` (reddit's separate legacy block, untouched).

The spec's own text makes an affirmatively incorrect claim about this exact script. REQ-CAP-112's closing
paragraph (behavioral-spec.md:350-354) states: *"The Cadence Contract's OWN daily 21:00 JST escalation already
exists and needs no new wiring: `cadence-deadline-check.sh` (`verify-loops-audit.sh:49`) already fires for
every loop present in `cadence-contracts.json`, so adding the `capafy` key (REQ-CAP-101) is sufficient for
THAT path."* I read `cadence-deadline-check.sh` directly — this is false. The script does not read
`cadence-contracts.json`'s keys dynamically at all; it has its own literal, independently-hardcoded
`CADENCE_LOOPS` string (line 23) that requires the SAME kind of explicit-append maintenance as
`verify-loops-audit.sh`'s list did before REQ-CAP-112(a). Adding `"capafy"` to `cadence-contracts.json`
(REQ-CAP-101) has zero effect on which loops `cadence-deadline-check.sh` iterates.

**Net effect if this spec ships exactly as written**: REQ-CAP-101 (contract entry) + fixed REQ-CAP-102 (both
dispatch chains) + REQ-CAP-112(a)/(b) (scorecard visibility in the two audit/report scripts) are all
implemented correctly, `status_for_loop("capafy")` returns real data, and capafy's scorecard becomes VISIBLE
in the 6h report — but REQ-CAP-112(c) DELETES capafy's only current self-fix trigger (legacy `stale_hrs`,
`verify-loops-audit.sh:19`), and NOTHING replaces it, because `cadence-deadline-check.sh`'s `CADENCE_LOOPS`
(the only script that ever calls `self-fix.sh` for a cadence-contract loop) never gains `capafy`. This is
**worse than the current production state**, not merely incomplete: today, a stale capafy pipeline gets a
self-fix escalation within ~30h (via the legacy check); after this feature ships as specified, a stale capafy
pipeline gets NO self-fix escalation at all, ever, ONLY a passive scorecard line in a report nobody is forced
to act on. This directly contradicts the design doc's stated goal #1 ("cadence contract 化: 「今日 publish or
実 progress したか」未達→self-fix") — the "→self-fix" half is not achieved, and is actively regressed.

This also makes **PROP-CAP-016(d) unsatisfiable as currently specified**: it asserts *"run
`verify-loops-audit.sh` end-to-end against a fixture where `published.jsonl` is stale... assert `self-fix.sh`
is invoked for capafy via the Cadence Contract's OWN `cadence-deadline-check.sh` path... and NOT via any
`stale_hrs`-triggered call."* Implemented exactly as REQ-CAP-112 specifies, this assertion would FAIL every
time — `cadence-deadline-check.sh` would never invoke `self-fix.sh` for `capafy` because `capafy` is not in
its `CADENCE_LOOPS`, and the `stale_hrs`-triggered call no longer exists either (deleted by (c)). The proof
obligation would need a real code change to `cadence-deadline-check.sh` to even be executable as written, let
alone pass.

**Fix**: extend REQ-CAP-112 with a new sub-item (e), or add REQ-CAP-113, requiring `cadence-deadline-check.sh:23`'s
`CADENCE_LOOPS` to also gain `capafy` (same order-preserving-append convention as REQ-CAP-112(a)), and correct
the now-disproven claim in REQ-CAP-112's closing paragraph that this script "needs no new wiring." Add this
file to the design doc's file-scope line (`2026-07-09-...-design.md:25`, currently lists only
`verify-loops.sh, verify-loops-audit.sh`). PROP-CAP-016(d) should then be verifiable as literally written
(self-fix invoked via `cadence-deadline-check.sh`, keyed off its own now-updated `CADENCE_LOOPS`) — add a
companion diff-based assertion (same style as PROP-CAP-016(e)) that every OTHER loop in
`cadence-deadline-check.sh`'s `CADENCE_LOOPS` is unchanged/order-preserved.

---

## C. Final dimension verdicts

| Dimension | Verdict | Blocking findings |
|---|---|---|
| Completeness | **FAIL** | C-3 (NEW) |
| Testability | PASS | — (T-1 resolved; PROP-CAP-016(d)'s unsatisfiability is a symptom of C-3, not a separate testability defect — fixing C-3 fixes it) |
| Consistency | PASS | — (REQ-CAP-112's four sub-items are internally consistent with each other and with PROP-CAP-016; the inconsistency is between REQ-CAP-112's closing claim and the actual `cadence-deadline-check.sh` source, captured as C-3 under Completeness/Reality-grounding) |
| Reality-grounding | **FAIL** (1 finding folded into C-3's evidence) | The "needs no new wiring" claim about `cadence-deadline-check.sh` is independently disk-verified false; separately, the raise-line citation `:293` vs actual `296` in gather_evidence is a minor, non-blocking drift inherited from iteration-1's own citation, not a new error introduced by REV2 |
| Agent-vs-code boundary | PASS | — no new judgment-in-code introduced by REV2's diffs; all changes are either data-list appends or already-approved patterns from iteration-1 |
| Dais 制約 (AI-disclosure) | PASS | — REQ-CAP-111 unchanged from iteration-1, still a pure prohibition, no disclosure-adding requirement introduced |

**Total BLOCKING findings: 1 (C-3).** C-1, C-2, and T-1 are genuinely resolved and need no further changes.
Per `dev-workflow.md`'s rule ("blocking 1件でも次フェーズ進行禁止"), this spec must not proceed to
`vcsdd-tdd` until C-3 is addressed (a REQ-CAP-112 extension or new REQ-CAP-113 wiring
`cadence-deadline-check.sh`'s `CADENCE_LOOPS`, plus correcting the disproven "needs no new wiring" claim) and
this review is re-run as iteration 3.
