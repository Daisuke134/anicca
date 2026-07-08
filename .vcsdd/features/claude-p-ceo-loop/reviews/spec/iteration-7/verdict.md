# Spec Review Verdict — claude-p-ceo-loop (Phase 1c, iteration 7 — confirmation review)

Reviewer: fresh-context adversary (no Builder context, no prior-iteration adversary context — zero memory of
authoring iterations 1-6). All claims below verified by directly reading the artifacts on disk: both spec files
in full (`behavioral-spec.md`, 820 lines; `verification-architecture.md`, 126 lines), the iteration-6 verdict
(`reviews/spec/iteration-6/verdict.md`), and — the sole focus of this iteration, per team-lead instruction — an
independent, from-scratch filesystem re-audit of every roster loop's actual `*-cli.sh` scripts, not trusting the
spec's own Ground-truth citation or the Builder's claim of having re-checked it.

## Overall verdict: **PASS** (0 blocking findings)

## Per-dimension verdicts

| # | Dimension | Verdict |
|---|---|---|
| 1 | Completeness | PASS |
| 2 | Testability | PASS |
| 3 | Consistency | PASS |
| 4 | Reality-grounding | PASS |
| 5 | 安全境界 (safety boundary) | PASS |

---

## Part A — B12 disposition: RESOLVED, independently re-verified against disk (not taken on the spec's or the
Builder's word)

Iteration-6's B12 found that REQ-CEO-020's Ground-truth citation was wrong for affiliate/bounty/gig/pm-earner:
it had checked `~/.openclaw/skills/anicca-glitchy-affiliate/` and `~/.openclaw/skills/anicca-earn-bounty/` and
found no `loop-report.sh` hook, and could not locate a `gig` implementation at all. The spec now claims (Ground
truth section, behavioral-spec.md lines 66-85) that iteration-6 searched the wrong location — the live
implementation is at `~/profitable-claude/skills/human-funded/{affiliate,gig,bounty}/`, with the
`~/.openclaw/skills/...` paths being "現在使われていない旧パス". I did not accept this claim on its own
authority; I re-ran the exact grep pattern myself, from a clean context, against the current filesystem:

| Loop | File checked | `grep -n "loop-report"` result |
|---|---|---|
| clip | `~/anicca/skills/earn/clip/clip-cli.sh` | **Confirmed.** Line 18, `STARTUP` variable contains `bash ~/anicca/skills/report/loop-report.sh clip "<summary>" ...` verbatim. |
| video | `~/anicca/skills/earn/video/video-cli.sh` | **Confirmed.** Line 17, same pattern, `loop-report.sh video ...`. |
| clip-promote | `~/anicca/skills/earn/clip-promote/clip-promote-cli.sh` | **Confirmed.** Line 24, `loop-report.sh clip-promote ...`. |
| affiliate | `~/profitable-claude/skills/human-funded/affiliate/affiliate-cli.sh` | **Confirmed.** Line 9, `STARTUP` variable contains `bash ~/anicca/skills/report/loop-report.sh affiliate "<summary>" ...` verbatim. |
| gig | `~/profitable-claude/skills/human-funded/gig/gig-cli.sh` | **Confirmed.** Line 21, `bash ~/anicca/skills/report/loop-report.sh gig "<summary>" ...` present in the STARTUP prompt (this is a large, actively-maintained script with `passprep.py`/`funnel_report.py`/lesson-sharing machinery — clearly the live implementation, not a stub). |
| bounty | `~/profitable-claude/skills/human-funded/bounty/bounty-cli.sh` | **Confirmed.** Line 17, `bash ~/anicca/skills/report/loop-report.sh bounty "<summary>" ...` present. |
| pm-earner | `~/anicca/skills/earn/polymarket-trade/` (17 files) | **Confirmed absent, both ways.** `grep -rln "loop-report"` → exit code 1, zero matches. `grep -rl "STARTUP"` → exit code 1, zero matches — this directory genuinely has no tmux-STARTUP-prompt concept at all (it is pure Python: `run.sh`/`run_earner.sh`/`pick.py`/`place_order.py`/etc.), corroborating the spec's characterization exactly. |

This is a 7/7 match against the spec's Ground-truth section and REQ-CEO-020's text — 6 loops confirmed to have
the hook verbatim, pm-earner confirmed to have neither the hook nor the STARTUP-prompt mechanism it would live
in. I additionally checked the two old paths iteration-6 cited, to understand why they misled that review:
`~/.openclaw/skills/anicca-glitchy-affiliate/` exists but its newest file has an mtime from 2026-06-01 (over 5
weeks stale relative to today); `~/.openclaw/skills/anicca-earn-bounty/` exists as an empty directory shell (no
`SKILL.md`, no script content) with mtime 2026-06-22. I also checked `~/.openclaw/cron/jobs.json` (221 jobs) and
found one enabled cron entry, `anicca-earn-bounty` (id `1730c972-...`), still pointing at
`anicca-earn-bounty/scripts/run.sh` under the `~/.openclaw` skills root — but this cron belongs to a materially
different agent identity (`agentId: "anicca"`, i.e. the Dais-funded Anicca-OpenClaw instance per this project's
CLAUDE.md colony table) than claude-p (the human-funded loop this feature belongs to, which registers its own
crons via the `CronCreate` tool calls embedded in each `*-cli.sh` `STARTUP` string). This is consistent with —
not contradicting — the spec's claim: the stale `~/.openclaw/skills/...` paths are a different instance's
now-unused artifact, not claude-p's actual affiliate/gig/bounty implementation, which lives at
`~/profitable-claude/skills/human-funded/` and is what REQ-CEO-020 correctly targets.

**B12 is resolved**, and resolved more favorably than iteration-6's two suggested remediation paths anticipated:
rather than needing to narrow scope to 3 loops (clip/video/clip-promote) or do net-new integration work for 4
loops, the corrected Ground-truth check found that 6 of 7 roster loops already have the hook, and only pm-earner
genuinely lacks it (and lacks the STARTUP-prompt mechanism the hook would live in, at all).

## Part B — REQ-CEO-020 scope confirmation and REQ-CEO-021 fallback-rule trace

- **Scope**: REQ-CEO-020 (behavioral-spec.md lines 294-317) explicitly limits its "roster内の各loop自身が持つ既存
  フックへの1行追加" integration to the 6 confirmed loops, and explicitly states "pm-earnerはこのREQのscopeに含
  まれない". The "Out of scope" section (lines 132-138) independently repeats and grounds this exclusion in the
  same grep evidence. Consistent, no contradiction between the two sections.
- **Fallback rule (REQ-CEO-021, B12新設)**: I traced the three claimed consequences of `weekly_spend_by_loop()`/
  `monthly_spend_by_loop()` never containing a `"pm-earner"` key by hand against the already-established (pre-B12)
  definitions elsewhere in the spec, rather than accepting the trace on faith:
  - (a) `compute_reward(realized_earn_usdc, weekly_spend_usd, lambda_)` (REQ-CEO-010, defined at
    behavioral-spec.md lines 248-253) already defines `base = weekly_spend_usd>0 の場合 earn/spend、そうでなければ
    earn そのもの`. A caller doing `dict.get("pm-earner", 0.0)` naturally produces `weekly_spend_usd=0.0`, which
    hits the existing `else` branch and returns `realized_earn_usdc` unchanged — no new conditional is required,
    this is a direct, mechanical consequence of a definition that predates B12. Confirmed sound.
  - (b) `filter_budget_compliant_loops` is specified to take `spend_by_loop: dict[str, float]` as a parameter
    (verification-architecture.md line 39); a missing key naturally defaults to `0.0` under the same "fail-open"
    philosophy REQ-CEO-023 already establishes for missing budget-config entries (a related but not identical
    mechanism — REQ-CEO-023 is about config-entry absence, this is about spend-data absence — the spec's own text
    acknowledges this is "同型" (same *type* of fallback) rather than literally the same code path, which is an
    accurate characterization, not an overclaim). This specific scenario has its own dedicated Tier-2 test in
    REQ-CEO-021's verification-architecture.md row (line 38: "`filter_budget_compliant_loops`がpm-earnerを
    `spend=0`として扱いhard-stop対象から除外することを直接確認"), so it is not left unverified.
  - (c) `BudgetPacer.update()`'s company-wide weekly total simply omits pm-earner's contribution (0 by omission,
    equivalent to summing with 0) — no special-casing needed, confirmed as a direct consequence of "no key = no
    addend" dict-sum semantics.
  No new blocking gap found in this trace. The fallback rule is well-specified, internally consistent with
  pre-existing REQ-CEO-010/022/023 definitions, and independently testable via the REQ-CEO-021 row's own stated
  assertions — it does not merely assert consistency in prose without a verification hook.

## Part C — B9/B10/B11 spot check: no regression

Re-read the full text of INV-CEO-1 (behavioral-spec.md lines 150-164), INV-CEO-2 (lines 165-192), REQ-CEO-044's
`build_next_registry` pseudocode (lines 440-465), and REQ-CEO-058's ①-⑫ sequence (lines 595-726) against
iteration-6's verdict, which independently hand-verified these same sections and found them PASS. None of this
iteration's B12-driven edits touch these sections — the diff is confined to REQ-CEO-020's caller/scope text,
REQ-CEO-021 (new fallback-rule prose), the "In scope"/"Out of scope" sections, and the Ground-truth section's
citation correction. The `_usd`/`_usdc` enumeration in INV-CEO-1 is unchanged (still 4 items); the
`registry_updates`-accumulator-free design (`budget_snapshot_by_loop`/`rollback_restore`/`allocation_decisions`
as three independent local return values, assembled once by `build_next_registry`) is unchanged; INV-CEO-2's two
named exceptions (REQ-CEO-020 as PER-LOOP-PASS, REQ-CEO-070 as the sequence's caller) are unchanged and still
internally consistent with REQ-CEO-020's now-corrected text. No regression found.

---

## Convergence assessment

This is the second consecutive iteration (6 and 7) in which the core registry-assembly/currency-routing
subsystem (the site of 5 consecutive prior defects, B3→B4→B6→B7/B8→B9/B10/B11) produced zero new findings under
independent, from-scratch scrutiny. Iteration 6 found exactly one new defect, entirely outside that subsystem
(a Ground-truth/Reality-grounding gap in a different requirement, REQ-CEO-020). This iteration's sole task was
to verify that gap's fix against disk, independently — which I did, and it holds. No new finding surfaced
anywhere else in the spec during this full re-read. Per the team-lead's own criterion ("7回目で数値コアも周辺も
安定ならこれ以上のiterationは過剰でありPASSが妥当"): the numeric core has been stable for 2 iterations, the one
remaining gap (B12) is now closed and independently re-verified rather than merely re-asserted, and no new class
of defect has appeared. Further iteration on this spec pair would not be examining an open question — it would
be re-running the same disk checks that both iteration 6 and this iteration already performed and found clean.

**Verdict: PASS. 0 blocking findings. Spec review gate (Phase 1c) is satisfied — proceed to Phase 2a
(`vcsdd-tdd`).**
