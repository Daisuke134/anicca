# Spec Review Verdict — capafy-harness (Phase 1c) — iteration 1

**Reviewer**: fresh-context adversary (no Builder context), disk-only review.
**Reviewed**: `.vcsdd/features/capafy-harness/specs/{behavioral-spec.md,verification-architecture.md}` (REQ-CAP-101..111, PROP-CAP-001..014) against `docs/superpowers/specs/2026-07-09-capafy-harness-design.md`, `docs/superpowers/specs/2026-07-08-claude-p-loop-verification-evidence-design.md`, and the live `~/.openclaw/skills/capafy-autopublish/` + `~/anicca/skills/self/{capafy-loop/,cadence-contracts.json,cadence-evidence.py}` implementation.

## Overall verdict: **FAIL** (3 BLOCKING findings, all Completeness/Testability)

Reality-grounding, Agent-vs-code boundary, and the Dais AI-disclosure constraint are all clean. The spec's ground-truth claims about the *existing* code are unusually well-verified (see below). But the spec has two concrete, disk-provable holes in what it wires up, both of which would make REQ-CAP-101/102 — the "①cadence contract" deliverable, i.e. the #1 item in the design's To-be table — silently non-functional even if implemented exactly as written and even if every proof obligation in verification-architecture.md passes.

---

## 1. Completeness — **FAIL** (2 BLOCKING)

### FINDING C-1 (BLOCKING): REQ-CAP-102 wires only half of `cadence-evidence.py`'s per-loop dispatch
`cadence-evidence.py`'s actual public entrypoint is `status_for_loop()` (`cadence-evidence.py:356-369`), which calls **two** separate per-loop if-chains:
- `gather_evidence()` (`:270-295`) — REQ-CAP-102 correctly specifies adding `if loop == "capafy": ...` here.
- `evidence_by_date_for_streak()` (`:299-353`) — a **second, independent** per-loop if-chain, used to compute the `streak` the design doc explicitly calls the "health の KPI" (`2026-07-08-...-design.md` line 71: "streak が health の KPI"). REQ-CAP-102 never mentions this function.

Both chains end in `raise ValueError(f"no evidence source wired for loop: {loop!r}")` (`:293`, `:353`) if the loop isn't handled. Every existing loop (gig, bounty, founder-loop, pm-earner) has a matching branch in BOTH functions — REQ-CAP-102 as written would give capafy a branch in only one, so `status_for_loop("capafy")` will raise mid-call.

This isn't just a theoretical asymmetry — I traced the actual callers: `verify-loops.sh:42` and `verify-loops-audit.sh:38` both invoke `python3 cadence-evidence.py status <loop>`. `verify-loops.sh`'s `cadence_line()` wrapper (`:40-45`) swallows the resulting stderr/non-zero exit into a hardcoded `"❌missed (streak=0) [evidence-gather error]"` fallback — so capafy would **permanently** read as `❌missed (streak=0) [evidence-gather error]` regardless of whether it actually published today, forever, silently. No proof obligation exercises `status_for_loop("capafy")` end-to-end (PROP-CAP-002 only unit-tests `_capafy_activity_event_dates` and the `gather_evidence("capafy",...)` dispatch shape in isolation), so this would pass every specced test and still be broken in production.

**Fix**: REQ-CAP-102 must also add a matching `if loop == "capafy":` branch to `evidence_by_date_for_streak()` (mirror the existing `gig` block at `:311-317`, reusing `_capafy_row_exists_event_dates()`), and a proof obligation must assert `status_for_loop("capafy")` returns a real `scorecard` string without raising.

### FINDING C-2 (BLOCKING): the new cadence contract is never wired into the actual healthcheck/escalation scripts that consume `cadence-contracts.json`
Neither `verify-loops.sh` nor `verify-loops-audit.sh` appears in the design doc's file scope (`2026-07-09-capafy-harness-design.md` line 25: `~/.openclaw/skills/capafy-autopublish/... + ~/anicca/skills/self/{capafy-loop/, cadence-contracts.json, cadence-evidence.py の capafy 分岐}`), and no REQ-CAP-10x touches them. I read both scripts directly:

- `verify-loops-audit.sh:33`: `CADENCE_LOOPS="clip affiliate video gig bounty pm-earner founder-loop"` — **capafy is not in this list.**
- `verify-loops-audit.sh:16` and `verify-loops.sh:19-22`: capafy is instead handled by the **legacy** `stale_hrs()`/`liveurl()` 30h-artifact-staleness block (`[ "$(stale_hrs "$CAP")" -ge 30 ] && ... self-fix.sh capafy "audit: no new capafy skill published in >30h..."`), with an explicit comment at `verify-loops-audit.sh:29-31`: *"capafy/reddit/lm (above) keep stale_hrs()/self-fix unchanged (REQ-LV-104, out of this feature's scope)"* — i.e. a **prior, sibling spec** (`2026-07-08-claude-p-loop-verification-evidence-design.md`, whose own §Cadence Contract explicitly says "既存 OUT_STALE_HRS（30h）方式はこの cadence contract 判定に置き換える") deliberately deferred capafy's cadence-contract migration, and **this feature is the obvious follow-up that should close it — but doesn't.**

Net effect: even with REQ-CAP-101 (contract entry) and a fixed REQ-CAP-102 (both dispatch functions wired, per C-1) fully implemented, `cadence-contracts.json`'s new `"capafy"` entry is **never read by anything that runs in production**. The self-fix escalation for capafy keeps firing off the old 30h-artifact-staleness check exclusively — the design's stated goal #1 ("cadence contract 化: 「今日 publish or 実 progress したか」未達→self-fix") is not achieved by this spec as written, regardless of implementation quality.

**Fix**: add a REQ (e.g. REQ-CAP-112) requiring: (a) `verify-loops-audit.sh`'s `CADENCE_LOOPS` gains `capafy`, (b) `verify-loops.sh` gains a `cadence_line capafy` echo line matching the other 7, (c) the legacy `stale_hrs("$CAP")`/`liveurl` self-fix block for capafy is removed or demoted to non-escalating (since the cadence-contract path now owns the escalation, matching the "REPLACES" language already used for the other 7 loops at `verify-loops-audit.sh:28`). Expand the design doc's file-scope line to include these two files. A proof obligation must assert `capafy` appears in `CADENCE_LOOPS` and the old `stale_hrs`-driven self-fix call for capafy is gone/inert.

---

## 2. Testability — **FAIL** (1 BLOCKING, 1 non-blocking note)

### FINDING T-1 (BLOCKING): PROP-CAP-009(b)/(c)/(d) specify a test method that has no corresponding code surface
REQ-CAP-107 (search-half) is defined purely as *"add a NEW instruction block to `capafy-loop-cli.sh`'s STARTUP prompt"* — a natural-language string executed by an interactive LLM session, exactly like REQ-CAP-106. The verification-architecture's own purity-boundary table lists no pure/impure function for the search-half at all (only `agent-reach` invocation, described as agent-judgment, impure). PROP-CAP-008 (REQ-CAP-106, the sibling prompt-text requirement) correctly scopes itself to *"Tier 2 (text-content assertion on the STARTUP string, since this is a prompt-string change not executable code)"*.

PROP-CAP-009 does not follow that same honest scoping — items (b)/(c)/(d) claim *"a stubbed `agent-reach` call returning a fixture 'finding' → assert the resulting `strategy.json` gets a NEW `recent_bp_notes` entry"* etc. There is no deterministic function anywhere in this spec (or the existing codebase) that takes an agent-reach return value and mechanically writes `strategy.json`/`lessons.jsonl` — that write is the AGENT's own judgment call inside the interactive prompt, not a script. "Stub agent-reach, assert the file changed" is not achievable without literally running the LLM session, which is not what a Tier-2 stub test means anywhere else in this spec.

**Fix**: rewrite PROP-CAP-009 to match PROP-CAP-008's framing (grep/text-content assertion that the instruction is present + unconditional, plus reliance on the Tier-3 main-agent E2E check already named in the Verification tiers legend) — or, if a real Tier-2 stub test is actually wanted, add an explicit deterministic wrapper function (e.g. a small `search_half.py` with a stubbable `run_search()`/`record_finding()` pair) to the purity-boundary table first, so PROP-CAP-009 has something concrete to target.

### Note (non-blocking): `apply_category_boost`'s location is left as "`funnel_metrics.py` **or** STARTUP-driven inline write (NEW)" in the verification-architecture table — an unresolved "or" that Phase 2 (TDD) will need pinned down before writing PROP-CAP-010/011's tests. Not blocking for lean mode, but should be resolved before `vcsdd-tdd` starts so the RED-phase tests target a real file/function.

---

## 3. Consistency — **PASS** (with cross-reference to C-1/C-2)
- `cadence-contracts.json`'s proposed capafy entry shape (`kind: row-exists`, `cadence: 1/day`, `boundary_tz: Asia/Tokyo`) matches the existing clip/affiliate/video/gig convention exactly (`unit: listing` instead of `reel` is an appropriate, non-breaking deviation).
- No internal contradiction found between REQ-CAP-101..111.
- The design doc's To-be table (BASE/VERIFY/SELF-HEAL/SELF-IMPROVE/REPORT) is fully mapped onto REQ-CAP-101‑110 with no unmapped To-be item.
- The one real cross-spec inconsistency is C-2 above: this spec is the obvious follow-up to `2026-07-08-claude-p-loop-verification-evidence-design.md`'s explicit `REQ-LV-104` deferral of capafy's cadence migration, but doesn't actually close it.

## 4. Reality-grounding — **PASS** (strong)
I independently re-verified all four Ground Truth claims from disk, not from the spec's assertions:
- **(a)** `publish_finish.sh:129` — confirmed byte-exact: `"date":__import__("datetime").date.today().isoformat()`. Local-day, no TZ conversion needed/possible. Confirmed.
- **(b)** `reconcile_ledger.py:91` — confirmed byte-exact: `datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")`. This is a real UTC-day computation; for a reconcile run in the JST 00:00–08:59 window it writes yesterday's UTC date, a genuine off-by-one. REQ-CAP-103's fix (swap to `zoneinfo.ZoneInfo("Asia/Tokyo")`) is correct and matches every other contract's `boundary_tz` convention.
- **(c)** `publish_finish.sh`'s ledger-append heredoc (actual write at `:126-131`, spec cites `:121-133` — close enough, same block) writes only `{agent_id, skill, title, status, date}`; confirmed via direct read — no `category` key anywhere in that write path. Confirmed via `cat state/published.jsonl`: rows written by this pipeline (e.g. `agent_id 8875030146`, `3947077924`) indeed lack `category`; only older hand-published rows carry it. REQ-CAP-104's fix reuses `build_config.py:28`'s exact regex (`re.search(r"category:\s*([^\(·\n]+)", L)`), confirmed byte-identical by direct read of `build_config.py:28-29` including the identical `"ライティング"` default.
- **(d)** No `views`/`impressions`/`clicks` field exists. I verified this independently (stronger than the spec's live-call claim) via the vendored, checked-in official API docs: `vendor/capafy-publisher/api-docs/00_overview.md:187-201` (`GET /agent/agents` list-item schema: `agentId, name, desc, agentType, agentStatus, developerVerified, latestAgentVersionId, updatedAt, sales, rating, ratingCount, reviewCount, recentSales` — no views) and `:401-422` (`GET /agent/agent/{agentId}/stats`: `sales, revenue, rating, reviewCount, daily[].orders, daily[].revenue` — no views). REQ-CAP-108's scoping to `sales`/`recentSales`/`rating`/`reviewCount` (+ `loop.sh`'s existing `CAP_MO`/`CAP_3D` aggregate reads, confirmed at `loop.sh:24-34`/`:36-43` exactly as cited) is honest and correct — and I'll note the per-agent `/stats` endpoint's `revenue`/`daily[].revenue` fields are a *more* precise signal than `publish-list`'s bare `sales` int that REQ-CAP-108 doesn't use; not a defect (lean-mode honest minimal scope), but worth flagging to Builder as a cheap future upgrade.
- `loop-report.sh`'s `lr_valid_evidence`/`--valid-evidence` gate (cited by PROP-CAP-007) confirmed to exist at `loop-report.sh:28-59`.
- `capafy-loop-cli.sh`'s current STARTUP STEP4 text (cited verbatim in Ground Truth) confirmed byte-for-byte identical to the live file's line 8.
- `DAILY_LOOP.md`'s step 7 (cited as calling only `git add -A && commit && push` + Telegram, no `loop-report.sh`) confirmed identical to the live file's lines 52-53.

No fabricated symbols, no incorrect line-number claims that change the conclusion, no stale/incorrect reads found anywhere in the Ground Truth section.

## 5. Agent-vs-code boundary — **PASS**
- Judgment (what to publish next, what to search for, what diff/finding to apply, which category to double-down on) is consistently assigned to "THE AGENT SHALL..." language, not hardcoded into scripts.
- The three new regex/TZ-arithmetic pieces (REQ-CAP-102's date-format validation, REQ-CAP-103's JST conversion, REQ-CAP-104's category extraction) are all genuine fixed-machine-format parsing of already-proven patterns (byte-identical reuse of `build_config.py:28`'s regex; a date-format regex `^\d{4}-\d{2}-\d{2}$`; a TZ conversion), squarely inside the BUILD AGENTS RIGHT exemption ("regex... for genuine parsing of a fixed machine format... is not judgment") — not a new judgment call.
- REQ-CAP-108's "≥1 signal → raise priority" rule is explicitly framed as prompt guidance to the agent ("THE AGENT SHALL... raise"), reusing an established precedent already in production for gig's B4 metrics-half, not a new hardcoded threshold invented for this feature.
- No regex/if-else is used anywhere to classify or route a judgment call (e.g. nothing decides "is this a good listing" or "which category to enter" deterministically).

## 6. Dais 制約 (AI-disclosure) — **PASS**
Grepped the full spec: the only AI-disclosure-related text is REQ-CAP-111, which is purely a *prohibition* ("SHALL NEVER introduce AI-usage-disclosure... language"), matching the Dais constraint exactly. No requirement anywhere instructs the agent or any script to add, require, or check for an AI-usage disclosure/label. Clean.

---

## Summary

| Dimension | Verdict | Blocking findings |
|---|---|---|
| Completeness | FAIL | C-1, C-2 |
| Testability | FAIL | T-1 |
| Consistency | PASS | (cross-ref C-2) |
| Reality-grounding | PASS | — |
| Agent-vs-code boundary | PASS | — |
| Dais 制約 | PASS | — |

**Total BLOCKING findings: 3** (C-1, C-2, T-1). Per this repo's `dev-workflow.md` rule ("blocking 1件でも次フェーズ進行禁止"), this spec must not proceed to `vcsdd-tdd` until C-1, C-2, and T-1 are addressed in the behavioral-spec/verification-architecture and this review is re-run.

C-2 is the highest-priority fix: without it, the entire feature could be built exactly to spec, pass every proof obligation, and still not change capafy's actual health-check behavior in production, because the file that owns escalation (`verify-loops-audit.sh`) never looks at the new contract entry.
