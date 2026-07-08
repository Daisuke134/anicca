# Spec Review Verdict — claude-p-ceo-loop (Phase 1c, iteration 6)

Reviewer: fresh-context adversary (no Builder context, no prior-iteration adversary context — zero memory
of authoring iterations 1-5). All claims below verified by directly reading the artifacts on disk: the two
spec files as they currently stand in full (`behavioral-spec.md`, 767 lines; `verification-architecture.md`,
126 lines), the iteration-5 verdict (`reviews/spec/iteration-5/verdict.md`), and fresh re-reads/greps of the
cited ground-truth files and — critically, going beyond what iterations 1-5 checked — a fresh filesystem
audit of every roster loop's actual scripts, not just the previously-named `cadence-contracts.json`/
`founder-loop.sh`.

## Overall verdict: **FAIL** (1 new blocking finding, B12 — a Reality-grounding failure, not a recurrence of
the registry-merge defect class. B9/B10 are genuinely, structurally resolved. B11 is resolved at the level
iteration-5 asked for, but the fix's own premise does not hold on disk.)

## Per-dimension verdicts

| # | Dimension | Verdict |
|---|---|---|
| 1 | Completeness | **FAIL** (B12) |
| 2 | Testability | PASS (all specified tests are executable as written; see caveat under B12) |
| 3 | Consistency | PASS (no internal spec-text contradiction found; B9/B10/B11 wording is now internally coherent) |
| 4 | Reality-grounding | **FAIL** (B12 — new, this iteration) |
| 5 | 安全境界 (safety boundary) | **FAIL** (B12 — blast-radius consequence) |

---

## Part A — Disposition of B9/B10/B11 (the three findings this iteration was built to fix)

### B9 (registry_updates inner-merge order undefined): **RESOLVED, structurally, not just by patch**

The accumulator (`registry_updates`) is completely gone. Grepped both spec files for
`registry_updates|queueする|へqueue|merge_allocation|merge_loop_registry_updates`: every remaining hit is
historical narrative describing what iteration-4/5 *used to do* and why it was replaced ("旧", "B9修正で
廃止した", "iteration-4版は…だったが") — none is a live requirement. The live design (behavioral-spec.md
lines 111-163, 368-412, 542-673; verification-architecture.md lines 11-24) has each of the three
side-effecting steps return a fully independent local value with no shared mutable state:

- ③-c (REQ-CEO-025) → `budget_snapshot_by_loop: dict[str, dict]`
- ⑥ (REQ-CEO-053) → `rollback_restore: dict[str, dict] | None`
- ⑧-c (REQ-CEO-040) → `allocation_decisions: dict[str, dict]`

REQ-CEO-044's `build_next_registry(existing_registry, budget_snapshot_by_loop, rollback_restore,
allocation_decisions)` is specified as literal, unambiguous pseudocode (line 390-396), not prose — a single
dict-comprehension-style expression per loop, with an explicit per-field priority: `"budget"` always comes
from `budget_snapshot_by_loop` (independent of rollback), `"allocation"` prefers `rollback_restore` over
`allocation_decisions` over `existing_registry`, `"consecutive_bad_weeks"` comes from `allocation_decisions`
over `existing_registry`. Because each of the three inputs is an independently-computed, non-overlapping-key
dict (rollback_restore only ever carries `"allocation"` per REQ-CEO-052's snapshot shape; allocation_decisions
only ever carries `"allocation"`/`"consecutive_bad_weeks"`; budget_snapshot_by_loop only ever carries budget
fields), there is no "which write wins" question left to answer — the fields simply don't collide, and where
they conceptually could (rollback firing + budget update in the same pass, for the same loop), the formula
computes `"budget"` and `"allocation"` from two different named arguments in the same expression, not from a
shared mutable dict written by two different steps at different times. This is exactly the fix iteration-5
asked for ("state explicitly... never a top-level dict replace").

I independently re-derived the collision scenario iteration-5 raised (rollback_restore and budget_snapshot
present for the same loop in the same pass) against REQ-CEO-044's formula by hand: `"budget"` resolves via
`budget_snapshot_by_loop.get(loop, ...)`, entirely unaffected by whether `rollback_restore` is `None` or not
— it survives. **PROP-CEO-024** (verification-architecture.md line 103) tests precisely this: the same
fixture is run once with `rollback_restore=None` (allocation from `allocation_decisions`) and once with
`rollback_restore={"clip":{"allocation":{"x":99}}}` (non-None), asserting the `"budget"` key is unchanged in
both runs while `"allocation"` switches from `allocation_decisions`'s value to `rollback_restore`'s value —
directly exercising the priority-and-non-collision property, not merely write-count. **PROP-CEO-021**'s B9-
反証 (verification-architecture.md line 100) also now asserts *content* (both `"allocation"` and `"budget"`
present and correct for the same loop in the rollback-pass write), not just that a single atomic write
occurred — the exact strengthening iteration-5 demanded of PROP-CEO-021. B9 is resolved.

### B10 (INV-CEO-1 enumeration not exhaustive — `weekly_realized_profit_usd` missing): **RESOLVED**

INV-CEO-1's enumeration (behavioral-spec.md lines 130-135) now lists four items, the fourth being
`ceo-escalations.jsonl`'s `weekly_realized_profit_usd` field (REQ-CEO-060, B10新規追加) — with REQ-CEO-060's
own text (lines 681-687) stating this field must be `realized_profit_usd(entries, fx_config)`'s output, the
same value already computed at ③-a. PROP-CEO-015 (verification-architecture.md line 94) directly tests this
with a JPY fixture. I independently re-ran the exhaustive grep iteration-5's own critique demanded (not
trusting the enumeration's self-claim): every `_usd`/`_usdc`-suffixed identifier across both spec files (full
list captured via `grep -noE`) reduces to: (a) the four INV-CEO-1-covered items, (b) the `realized_profit_usd`/
`convert_to_usd` function names themselves (the converters, not values needing conversion), (c) `jpy_usd_rate`
(a config rate, input to conversion, not an output needing it), (d) spend-side fields (`weekly_spend_usd`,
`monthly_spend_by_loop`'s implicit USD unit, `company_weekly_spend_usd`, `capital_cap_usd`) which are sourced
from `usd_estimate` (REQ-CEO-020) — a fundamentally different, already-USD-native data path with no
native-currency (JPY) source to convert from, structurally outside INV-CEO-1's concern (native-earn-currency
conflation) — and (e) `earned_usdc`/`company_realized_profit_summary` (REQ-CEO-080), which the spec itself
explicitly states is out of scope with reasoning ("この値はINV-CEO-1の列挙対象外…既に安全な`company_score`
を下流でそのまま使うだけの reporting stepであるため", line 741-744), mirroring the same "属さない理由を明記"
discipline INV-CEO-2 uses. No further unenumerated native-currency-to-`_usd` gap was found. B10 is resolved.

### B11 (REQ-CEO-020 caller/cadence undefined): **resolved at the textual/logical level iteration-5 asked for
— but its own premise fails a fresh disk check (see B12 below, which supersedes this as the operative finding)**

REQ-CEO-020 (lines 265-280) now states unambiguously: PER-LOOP-PASS, not part of REQ-CEO-058's ①-⑫, caller
is each roster loop itself via its existing `loop-report.sh <loop> ...` pass-end hook, integration is a 1-line
addition to that hook. INV-CEO-2 (lines 136-147) now lists exactly two named exceptions (REQ-CEO-020,
REQ-CEO-070) with stated reasons, closing the "unqualified 全てのREQ" gap iteration-5 found. The "In scope"
section (lines 95-100) was extended to name this integration point explicitly. This textual fix is complete
and internally consistent — but see B12: the premise "each roster loop **already has** this hook" does not
hold for 4 of the 7 roster loops when checked against the actual files on disk.

---

## Part B — New finding (B12), found by going one level deeper than any prior iteration checked: verifying
the Ground-truth claim underlying B11's fix against the actual loop scripts, not just against
`cadence-contracts.json`/`founder-loop.sh`

### B12 (new, blocking, Reality-grounding + Completeness + 安全境界) — REQ-CEO-020's "既存フック" premise is
false for **affiliate, bounty, gig, and pm-earner** — 4 of the roster's 7 loops — contradicting the spec's own
Ground-truth citation

REQ-CEO-020's text (line 273-274) makes a specific, falsifiable claim: "各loopは既に自分のpass終了時に
`loop-report.sh <loop> ...`を呼ぶ既存フックを持つ（Ground truth参照: **gig/affiliate/bountyの**tmux STARTUP
promptがpass末尾でこれを既に呼んでいる）". I checked every roster loop's actual files:

| Loop | Where I looked | Result |
|---|---|---|
| clip | `~/anicca/skills/earn/clip/clip-cli.sh` | **Confirmed.** The `STARTUP` variable (the literal tmux-session prompt) contains `bash ~/anicca/skills/report/loop-report.sh clip "<summary>" ...` verbatim. |
| video | `~/anicca/skills/earn/video/video-cli.sh` | **Confirmed.** Same pattern, `loop-report.sh video ...` present in `STARTUP`. |
| clip-promote | `~/anicca/skills/earn/clip-promote/clip-promote-cli.sh` | **Confirmed.** Same pattern, `loop-report.sh clip-promote ...` present. |
| **affiliate** | `~/.openclaw/skills/anicca-glitchy-affiliate/` (SKILL.md, 174 lines; scripts: `generate-slides.sh`/`pick-hook.sh`/`pick-offer.sh`/`post-to-youtube.sh`; `prompts/hooks.json`) | **Not found.** `grep -rn "report"` across the entire skill directory returns zero hits. No `STARTUP` variable, no `loop-report.sh` call anywhere. |
| **bounty** | `~/.openclaw/skills/anicca-earn-bounty/` (the dir the cron job `anicca-earn-bounty` actually invokes via `anicca-earn-bounty/scripts/run.sh`) | **Not found — worse than "no hook": the directory contains no `SKILL.md` and no `scripts/` contents at all**, only `state/` and `work/`. The `run.sh` the cron payload references does not exist as a persistent file I could locate. |
| **gig** | Searched `~/anicca/skills/self/`, `~/anicca/skills/earn/`, `~/.openclaw/skills/` for any `gig`-named skill directory or `*-cli.sh`/`STARTUP` pattern; also checked `~/gig/` (a separate top-level dir with `deliverables/`, `proposals_pass133/`, `replies/`) | **Not found anywhere.** No script or prompt implementing this loop was located at all under any of the three canonical skill roots. `cadence-contracts.json`'s own `"gig"` entry points evidence at `~/gig/gig-funnel.jsonl`, a file/path I could not confirm exists either. |
| **pm-earner** | `~/anicca/skills/earn/polymarket-trade/` (17 files incl. `run.sh`, `run_earner.sh`, `SKILL.md`) | **Not found.** `grep -rln "loop-report"` across the entire directory returns zero hits; the one "report" hit found (`verify_positions.py`) is an unrelated internal "daily mail-evidence report" docstring, not a `loop-report.sh` call. |

A tree-wide, unbiased cross-check corroborates this: `grep -rl "STARTUP" ~/anicca/skills | xargs grep -l
"loop-report"` across the *entire* `~/anicca/skills` tree returns exactly six files — `clip-cli.sh`,
`video-cli.sh`, `clip-promote-cli.sh`, `capafy-loop-cli.sh`, `reddit-loop-cli.sh`, `life-manager-loop-cli.sh`,
plus `verify-loops-audit.sh` (an audit tool, not a loop itself). The last three loops in that list
(capafy/reddit/life-manager) are **not even in the CEO roster** — they aren't in `cadence-contracts.json`.
Of the roster's 7 loops, only clip/video/clip-promote have this pattern anywhere on disk.

**Why this is blocking, not a minor documentation nit**: REQ-CEO-020's entire integration plan, and the "In
scope" boundary's framing of it ("既存の`loop-report.sh`呼び出しパターンへ**1行追加するのみ**"), is
predicated on an existing call site to append one line to. For affiliate, bounty, gig, and pm-earner, there is
no such call site — implementing REQ-CEO-020 as specified for these four loops would require *authoring a new
reporting integration from scratch inside four separate, currently-running production earn loops whose
scripts have never been reviewed by this VCSDD pipeline* — not a bounded 1-line edit. This has three
compounding consequences:

1. **Completeness**: the spec's "In scope" section does not actually describe what would need to be built for
   4 of 7 loops (no proposed script/prompt edit, no description of *where* in affiliate's four `.sh` files or
   in bounty's non-existent `run.sh` the call would go), because it incorrectly assumes the work is already
   "1行追記".
2. **Reality-grounding**: the Ground-truth citation itself ("gig/affiliate/bountyのtmux STARTUP promptが…
   既に呼んでいる") is factually wrong for all three loops it names, verified fresh against the live
   filesystem this session — the same standard of fresh verification iterations 1-5 applied to
   `cadence-contracts.json`/`founder-loop.sh`, now applied one level deeper.
3. **安全境界 (safety boundary)**: if this is fixed by actually implementing the missing hooks, the feature's
   blast radius silently expands from "founder-loop.sh (1 line) + CEO's own new files" to "6 other live,
   currently-scheduled production earn loops, each requiring new judgment about where/how to insert a cost-
   reporting call into their existing STARTUP/cron flow" — a materially larger and riskier change surface than
   what this spec's "In scope"/"Out of scope" boundary claims to gate, and one this review process has not
   yet seen designed or reviewed for the 4 affected loops.

This also means REQ-CEO-014/010's dependency chain — which iteration-5's own B11 finding already flagged as
at risk of `ceo-cost-events.jsonl` staying empty — is **not just hypothetically at risk but empirically
guaranteed to be structurally incomplete for the majority of the roster** under the current spec: even a
perfect implementation of REQ-CEO-020 exactly as worded produces cost data for clip/video/clip-promote only,
so `weekly_spend_by_loop()`/`monthly_spend_by_loop()` return `0`/`{}` for affiliate/bounty/gig/pm-earner
permanently, silently defeating `BudgetPacer` (REQ-CEO-014) and the reward denominator (REQ-CEO-010) for 4 of
7 loops — the exact "silently defeating the entire budget-pacing mechanism" failure iteration-5 warned about,
now confirmed rather than merely possible.

**Required fix**: Either (a) scope this feature down to record verified cost events for clip/video/
clip-promote only for now, explicitly stating in "Out of scope" that affiliate/bounty/gig/pm-earner cost
tracking is deferred pending those loops' own scripts being confirmed/built (and stating what REQ-CEO-014/010
do with permanently-missing spend data for those loops — do they get `weekly_spend_usd=0` and thus a `reward`
computed on a possibly-misleading spend-free basis? this needs an explicit fallback rule if the scope is
narrowed), or (b) extend "In scope" to include the actual, concrete integration point for each of the 4
loops — which first requires confirming or building the reporting mechanism for gig (which currently appears
to have no locatable implementation at all) and bounty (whose skill directory has no script content on disk),
and specifying the exact insertion point for affiliate's `generate-slides.sh`/`pick-hook.sh`/`pick-offer.sh`/
`post-to-youtube.sh` (none of which currently has a `loop-report.sh` call to extend) and pm-earner's
`run.sh`/`run_earner.sh`. Either way, the Ground-truth section's specific claim about gig/affiliate/bounty
must be corrected or withdrawn before REQ-CEO-020 can be trusted as accurately scoped.

### Steps re-traced, no new defect found beyond B12

Independently re-verified `cadence-contracts.json` (8 keys, `_comment` is `str`, other 7 are `dict` — matches
REQ-CEO-001/PROP-CEO-001 exactly) and `founder-loop.sh` (73 lines, `exit "$RC"` remains the literal last line
— matches REQ-CEO-070/PROP-CEO-022 exactly). The cooldown/rollback state machine (①②④⑤⑥⑦⑨⑩⑪, independent of
the now-removed accumulator) was re-traced against the current text and remains internally consistent with
iteration-4/5's already-confirmed arithmetic — no new B6-class defect. No further `_usd`/`_usdc` or
side-effecting-REQ enumeration gap was found beyond B10/B11's now-fixed items.

---

## Reality-grounding summary (re-verified fresh against live sources this session)

- `~/anicca/skills/self/cadence-contracts.json` — re-loaded with `json.load`: 8 keys, types match spec
  exactly. PASS.
- `~/anicca/skills/self/founder-loop/founder-loop.sh` — 73 lines, `exit "$RC"` is the literal last line.
  PASS.
- `~/anicca/skills/earn/{clip,video,clip-promote}/*-cli.sh` — each contains a `STARTUP` variable with a
  literal `loop-report.sh <loop> ...` call. PASS (these 3 loops only).
- `~/.openclaw/skills/anicca-glitchy-affiliate/`, `~/.openclaw/skills/anicca-earn-bounty/`, any `gig`-named
  skill directory, `~/anicca/skills/earn/polymarket-trade/` — **FAIL**: none contains a `loop-report.sh`
  call site; bounty's directory has no script content at all; no `gig` implementation was locatable under
  any of the three canonical skill roots this session. This directly contradicts REQ-CEO-020's Ground-truth
  citation. **This is the basis for B12 and the only reason the overall verdict is FAIL this iteration.**

---

## 収束傾向 (convergence trend)

Genuine, durable, structural progress on the subsystem that produced 5 consecutive iterations of defects
(B3→B4→B6→B7/B8→B9/B10/B11): B9 and B10 are resolved by construction, not by patch, and independently
re-derived by hand rather than taken on the spec's own word — the `registry_updates` accumulator that was
itself the site of iteration-5's most severe finding no longer exists, and the currency-invariant enumeration
survives a fresh, from-scratch grep this iteration performed independently of the prior one. **This specific
subsystem (registry write assembly + currency routing) has now converged** — I could not find a defect in it
despite deliberately trying the same "grep every occurrence, don't trust the enumeration's self-claim"
technique iteration-5 used to find B10/B11 in the first place.

The overall verdict is still FAIL, but for a **different reason than iterations 1-5**: not a new gap in the
same registry/currency mechanism, but a Reality-grounding failure one layer removed — the B11 fix (correctly
resolving *how* REQ-CEO-020 should be worded, who calls it, when) rests on a factual claim about the existing
codebase that iterations 1-5 never checked against the actual loop scripts (they checked
`cadence-contracts.json` and `founder-loop.sh`, which are correct, but not the other 6 loops' own scripts,
which this iteration did check and found wanting for 4 of them). This is not evidence the spec's design
approach is "本質的に複雑すぎる" (the team-lead's explicit alternative hypothesis) — the design (per-loop local
returns → single named-argument assembly function) is sound and has now survived independent scrutiny. It is
evidence that this spec's Ground-truth section made an unverified extrapolation ("gig/affiliate/bountyの…
既に呼んでいる", generalized from what is only actually true of clip/video/clip-promote) that nobody
fact-checked against the filesystem before this iteration. This is a fixable, bounded gap (narrow the scope,
or do the legwork to confirm/build the 4 missing hooks) — not a sign to abandon or re-architect the
registry-merge design, which should be preserved unchanged into iteration 7.

## What must happen before re-review

1. Fix B12 (blocking, highest priority): correct or withdraw the Ground-truth claim about gig/affiliate/
   bounty already having a `loop-report.sh` pass-end hook. Choose and specify one of the two paths above (narrow
   scope to clip/video/clip-promote for cost tracking now, with an explicit fallback rule for the other 4
   loops' permanently-zero spend data in REQ-CEO-014/010; or extend "In scope" with concrete, per-loop
   integration points after confirming/building each of the 4 missing hooks — including first locating or
   building the `gig` loop's implementation and bounty's `run.sh`, which do not currently exist as locatable
   files).
2. Do not re-touch REQ-CEO-044/build_next_registry or the INV-CEO-1 enumeration — both are resolved and
   independently re-verified this iteration; further edits to them risk reopening a closed, converged
   subsystem without cause.
3. Before claiming B12 resolved, re-run the same disk check this verdict performed (`grep -rl "STARTUP" | xargs
   grep -l "loop-report"` across each of the 4 affected loops' actual directories, plus confirming `gig`'s
   implementation location) rather than accepting a textual claim of resolution.
