# Phase 3 implementation review — franklin-alwaysact-skill-router — iteration 4 (scoped closing review)

Fresh-context adversary review, zero builder context. Reviewed commit `39a9c217` on
`feature/franklin-alwaysact-skill-router` in worktree `/Users/operator/anicca/.worktrees/alwaysact-impl`
(recreated from the branch ref after an external deletion; confirmed readable — every file cited below
was successfully `Read`/`Grep`'d from this worktree, so the "unreachable" fallback in the task
instructions did not apply). No Bash tool was available this session; test execution (183/183 pass) was
independently performed by the launching thinker and is treated as externally verified per the task's
own explicit instructions. This review is grounded entirely in `Read`/`Grep`/`Glob` over the real source,
test, spec, and contract files, with every claim below citing a concrete file:line.

## Tool-failure hook note (disclosed, same as iteration-2/3's precedent)

A `PostToolUse:Write` hook fired after this session's `Write` call to `verdict.json`, stating "fablize
gate observed a tool failure. Do not report completion until it is fixed, isolated as a known baseline,
or explicitly documented." The `Write` invocation itself returned "File created successfully" with no
error surfaced to this adversary, and this adversary has no Bash/shell tool to independently investigate
the underlying fablize gate. Iteration-2 and iteration-3's reviews both encountered and disclosed the
identical notice under identical circumstances (no Bash tool, no visible Write failure) — disclosed here
on the same basis, isolated as a recurring, session-external condition unrelated to any content of this
review. It does not originate from, or relate to, any finding/evidence below, all of which are grounded
in direct `Read`/`Grep` evidence of the reviewed commit's actual content.

## Scope of this iteration (per task instructions)

1. Verify iteration-3 FIND-001 (REQ-509 skip record targeting the wrong file) is genuinely resolved.
2. Regression-scan the fix diff for weakened assertions across the 8 retargeted tests, and confirm the
   3 test-race fixes are test-infrastructure-only (never a product-code change), and that the product's
   `skill_missing` handling the race exposed is itself spec-conformant.
3. Spot-check transition-matrix Rows 5/6/7/9/12 for correct expected-line-set assertions given the extra
   ledger line.
4. Full 5-dimension verdict.

## 1. REQ-509 FIND-001 resolution — CONFIRMED GENUINE, not a reinterpretation

`specs/behavioral-spec.md:493-495`'s literal AC text ("the guard-blocked slot's own skip record is
preserved verbatim in the ledger") is unchanged since iteration-3. Re-confirmed the spec's consistent use
of "the ledger"/"a ledger line" as a proper noun for `state/ledger.jsonl` (REQ-510 EARS clause line 498,
REQ-512 lines 581/585, line 777), distinct from REQ-508's explicit `harness-failures.jsonl` naming
(line 467).

Read `runAlwaysActWake` in full (`index.mjs:666-860`). The no-realized-action branch
(`index.mjs:779-814`) now:
- Builds `skipRecordStr` via `formatRecord({..., kind:'router_reroute_skip', ..., skip_reason:
  skillResult.output || ''})` — no `.slice()`/`.replace(/\s+/g,' ')` truncation/collapse, unlike the
  wake's own terminal `result` field (`index.mjs:852`, which IS capped at 900 chars and whitespace-
  collapsed). Only the same `redactPrivateKeyPatterns` pass (a 64-hex private-key regex substitution,
  `env-filter.mjs:46-49` — confirmed it leaves 40-hex wallet addresses and all other content byte-for-
  byte untouched) every other ledger line already receives is applied. This satisfies "verbatim" under
  the spec's own established convention (REQ-510's edge case explicitly permits the SAME redaction pass,
  "no new redaction pass, no bypass") — consistent secret redaction is not a verbatim violation.
- Writes via `await safeAppend(LEDGER_PATH, redactPrivateKeyPatterns(skipRecordStr))` — the SAME
  `formatRecord`/`safeAppend`/`LEDGER_PATH` machinery every other `ledger.jsonl` line in this file uses.
- Contains NO `appendHarnessFailure` call. Grepped every `appendHarnessFailure` call site in
  `index.mjs`: line 613 (`runOneWake`'s own unrelated non-always-act path), line 767 (gated on
  `classifyLayer(kind) !== 'clean'`, which is FALSE for `kind:'wake'` — never fires for this
  no-realized-action case, since `kind` is only reassigned away from `'wake'` by `skillResult.notFound`/
  `timedOut`/non-zero exit, none of which apply to a guard-block that exits 0 with no earn-ledger line),
  line 878 (`wake_error` handler, unrelated), line 914 (`writeAlwaysActEscalation`'s own REQ-508
  TERMINAL-escalation write, a semantically different, correct call site). The harness-failures.jsonl
  write for THIS branch was genuinely removed, not merely duplicated.

This is a **literal, non-reinterpretive fix**: the code now conforms to REQ-509's AC exactly as already
written in `behavioral-spec.md` — no spec-text change was needed (unlike iteration-3's harness-failures.jsonl
deviation, which required either a code fix or an undisclosed spec reinterpretation; this iteration took
the code-fix path, closing the gap cleanly).

`contracts/sprint-1.md`'s CRIT-006 (lines 33-37) was correspondingly rewritten: its description now
accurately documents the current ledger.jsonl-targeting implementation, and its `passThreshold` contains
an explicit, falsifiable regression guard: "FAIL if ... PROP-509b's preserved-record assertion targets
harness-failures.jsonl instead of ledger.jsonl" and requires confirming harness-failures.jsonl carries NO
`router_reroute_skip` record. This closes iteration-3's "contract-level rationale amends REQ-509's AC by
fiat" concern — the contract is now a truthful description of literal spec conformance, not an inference
substituting for it.

`always-act-reroute.test.mjs:637-688` (PROP-509b) now asserts unconditionally (no dead-code `if` guard,
confirmed by reading the full test body) against `ledger.jsonl`, plus a NEW negative-control assertion
(lines 680-687: `harness-failures.jsonl` must carry NO `router_reroute_skip` record) — proving both
halves of the AC (record exists + wrong file does not carry it), not a one-sided check.

**Verdict: iteration-3 FIND-001 is genuinely, fully resolved. No new finding raised.**

## 2. Regression scan of the 8 retargeted tests + 3 race fixes

Read every retargeted test in full (`always-act-reroute.test.mjs` Rows 5/6/6b/7/9/12, PROP-506f,
PROP-506c×2, PROP-509b). For each, traced the code's actual write sequence and confirmed the test's
`waitForLines(path, N, ...)` count and `.find()` assertions match exactly:

| Test | Ledger lines expected | Why | Confirmed |
|---|---|---|---|
| Row 5 | 2 | skip (sol-trade) + terminal wake (gig) | ✓ |
| Row 6 | 2 | skip (sol-trade) + escalation | ✓ |
| Row 6b | 2 | skip (sol-trade) + escalation | ✓ |
| Row 7 | 3 | skip (sol-trade) + skip (gig, reroute ALSO no-ops) + escalation | ✓ |
| Row 9 | 2 | skip (gig, reprompt-attempt no-op) + escalation | ✓ |
| Row 12 | 2 | skip (clip, reprompt-attempt no-op) + escalation | ✓ |
| PROP-506f | 2 | skip (sol-trade) + escalation (empty risk-free set) | ✓ |
| PROP-506c (gig) | 2 | skip (gig) + terminal wake (clip) | ✓ |
| PROP-506c (lending) | 2 | skip (lending) + terminal wake (clip) | ✓ |
| PROP-509b | 2 | skip (sol-trade, guard-blocked) + terminal wake (gig) | ✓ |

No assertion was weakened — every count is a real, code-traced number (not a loosened `>=` or removed
check), and several tests (Rows 5/6/6b/7/9/12, PROP-506f, PROP-509b) now assert BOTH the skip record's
existence AND its `slot`/`skip_reason` content via `.find((l) => l.kind === 'router_reroute_skip' &&
l.slot === '...')`, which is strictly MORE assertion surface than iteration-3's harness-failures.jsonl
version had (per iteration-3's own FIND-001 evidence, that version's assertion ran unconditionally against
`harness-failures.jsonl` with equivalent content checks — this iteration is a like-for-like or stronger
replacement, not a weakening).

Rows 8/10/11 (rejected-slot/no-tool-call reprompt paths — REQ-505/513's Case A/B, never REQ-506's Case C
no-realized-action branch) correctly remain at `waitForLines(1)` with no spurious extra line — confirming
the skip record is written ONLY on the no-realized-action reroute branch, never on ordinary reject/reprompt
branches. This is the correct differentiation and rules out an over-broad implementation that would write
a skip record on every rejected pick.

**The 3 race fixes** (`always-act-reroute.test.mjs:259-273` Row 5, `:537-551` PROP-506c-gig, `:642-656`
PROP-509b): each captures `wakeId` from the FIRST `think()` request's body (regex `/Wake
([A-Z0-9]+):/.exec(body.messages?.[1]?.content)`) inside the mock brain server's response callback, then
`await waitForCondition(() => wakeId !== null, ...)` before calling `writeMockEarnSkill(home, ..., {
realizeForWakeId: wakeId })` — moving the fixture write earlier (before the 2nd `think()` call resolves)
rather than after `requests.length >= 2`, which the comments correctly identify as a genuine race (the
child may already be resolving the skill path before the test-side write lands). Confirmed via
`always-act-harness.mjs:63-92` that `writeMockEarnSkill`/`writeMockGuardBlockedSkill` are pure
shell-fixture generators — the fix is confined to test bodies + this helper file, never touching
`runtime/loop/index.mjs` or `always-act-router.mjs`. **Test-infrastructure-only, confirmed.**

**The product's `skill_missing` handling** (`index.mjs:751`: `if (skillResult.notFound) kind =
'skill_missing'`, evaluated BEFORE the `kind === 'wake' && ...` reroute-trigger check at line 779) is
unchanged by this fix and independently confirmed spec-conformant against REQ-506's own edge case
(`behavioral-spec.md:406-409`: "This reroute is NEVER triggered by a slot execution that itself
errors/times out"). A `skill_missing`/`skill_timeout`/`skill_error` outcome can never reach the
no-realized-action reroute/skip-record branch, by construction (kind is reassigned away from `'wake'`
first). No defect found here.

## 3. Structural collision check (harness-health.mjs + go-live.mjs consumers)

Read `harness-health.mjs` in full. `CLEAN_KINDS = {wake,narrate,shutdown}` and `SLOT_HEALTH_KINDS =
{wake,skill_missing,skill_timeout,skill_error}` (lines 24,27) — `'router_reroute_skip'` is a member of
NEITHER set. `classifyLayer()` (lines 40-48) maps any unrecognized kind to the fail-safe `'unknown'`
layer (never throws), and `computeSlotHealth`'s filter (line 62: `SLOT_HEALTH_KINDS.has(r.kind)`) silently
excludes the new kind from per-slot failure-rate/streak tracking. Zero structural collision, confirmed by
full-file read (not merely the two kind-set declarations).

Read `always-act-router.mjs`'s `isPostGoLiveRegression` (lines 235-256), REQ-512's own consumer-facing
regression detector: any ledger kind OTHER than `'always_act_go_live'`/`'always_act_not_engaged'` resets
its consecutive-not-engaged run counter (line 251-253, "any other kind after go-live is a
successfully-engaged wake"). A `router_reroute_skip` line correctly falls into this reset case — it only
ever appears on a wake that DID engage and DID execute a skill — so its presence neither creates a false
"not yet enabled" signal nor suppresses a genuine regression signal. Semantically correct, no collision.

Also spot-checked `skills/self/earning-health.py` (a DIFFERENT detector, operating on `trace.jsonl`'s own
`action`/`reason` fields, not `ledger.jsonl`'s `kind` field) — structurally unrelated to this feature's
diff, confirmed no interaction.

## 4. Verdict summary

All 5 dimensions PASS, 0 blocking findings. See `findings/` — none filed this iteration; every prior
concern traced to ground truth and confirmed resolved without introducing a new defect.

## Non-blocking process observation (disclosed, not filed as a finding)

`state.json`'s `phaseHistory` has no entries for Phase 3 impl-review iterations 1-4, and `currentPhase`
is still recorded as `"2c"` despite `reviews/impl/iteration-{1,2,3}/` all existing with real, dated
verdicts. This adversary did NOT modify `state.json` (outside this review's write scope) and does not
treat this as a spec/test/impl defect in the reviewed commit — it is a bookkeeping/process-tracking gap
for the launching thinker to reconcile (mirroring the reconciliation note already present at
`state.json`'s own `phaseHistory[7]` for a prior, similar gap in the spec-review iterations) before
calling `vcsdd-converge`.
