# Phase 3 implementation review — franklin-alwaysact-skill-router — iteration 3

Fresh-context adversary review, zero builder context. Reviewed commit `2096ee06` on
`feature/franklin-alwaysact-skill-router` in worktree `/Users/anicca/anicca/.worktrees/alwaysact-impl`.
No Bash tool was available this session; test execution (183/183 pass) was independently performed by
the launching thinker (plus a proven-pre-existing `integration.test.mjs` ENOTEMPTY teardown flake) and
is treated as externally verified per the task instructions. This review is grounded entirely in
`Read`/`Grep`/`Glob` over the real source, test, spec, and contract files, with every finding citing a
concrete file:line.

No `reviews/impl/iteration-3/input/manifest.json` existed in this worktree (only `output/` artifacts
were ever persisted for iteration-1/2, and iteration-3's directory did not exist at all prior to this
review). Proceeded directly from `specs/behavioral-spec.md`, `specs/verification-architecture.md`,
`contracts/sprint-1.md`, `state.json`, and the iteration-2 findings/verdict/notes as the review basis,
per the task's own explicit instructions.

## Tool-failure hook note (disclosed)

A `PostToolUse:Write` hook fired after this session's `Write` calls stating "fablize gate observed a
tool failure. Do not report completion until it is fixed, isolated as a known baseline, or explicitly
documented." Every `Write` invocation in this session returned "File created successfully" with no
error surfaced to this adversary, and this adversary has no Bash/shell tool to independently
investigate the underlying fablize gate. Iteration-2's review encountered and disclosed the identical
notice under the identical circumstances (no Bash tool, no visible Write failure) — disclosed here on
the same basis. It does not originate from or relate to any of the findings below, all of which are
grounded in direct `Read`/`Grep` evidence of the reviewed commit's actual content.

## Iteration-2 findings: 3 of 4 genuinely resolved, 1 only partially resolved (re-opened)

**FIND-001 (`ALWAYS_ACT_REGISTRY_PATH_OVERRIDE` unconditional prod backdoor)**: Confirmed resolved.
`runtime/loop/__tests__/franklin-plist-config.test.mjs:62-76` adds two real, deployed-plist-reading
guardrail tests (`ai.anicca.franklin-loop.plist` and `ai.anicca.franklin2-loop.plist`) asserting the
key is absent from both live plists — the exact same mitigation pattern already established for
`ANICCA_BALANCE_OVERRIDE`. Both plists are read live, not a fixture/copy.

**FIND-002 (contract missing REQ-503/REQ-510 mapping)**: Confirmed resolved. `contracts/sprint-1.md`
now has 12 CRIT criteria; CRIT-011 (weight 0.05) explicitly maps to REQ-503 (`PROP-503a`/`PROP-503b`)
and CRIT-012 (weight 0.05) explicitly maps to REQ-510 (`PROP-510a`, `PROP-506f`'s domain-pin
assertion). Total weight: 10×0.09 + 2×0.05 = 1.00. Every REQ-501..513 is now named by at least one
criterion.

**FIND-003 (PROP-506f missing)**: Confirmed resolved. `always-act-reroute.test.mjs:463-486` is a real
spawn-based test (`writeRiskTaggedRegistry` fixture, `engagedSpawn`, `ALWAYS_ACT_REGISTRY_PATH_OVERRIDE`)
asserting `requests.length === 1` (zero additional `think()` calls), `escalated.attemptsUsed === 0`
despite the one call having been made, and `kind:'router_no_realized_action'` — exactly the named,
previously-missing scenario, and it also exercises REQ-510's own second literal-domain-pin AC that
FIND-003 identified as otherwise untested.

**FIND-004 (dead-assertion + REQ-509 skip-record AC) — ONLY PARTIALLY RESOLVED, RE-OPENED as
iteration-3 FIND-001**: The dead-code half is genuinely fixed — `always-act-reroute.test.mjs:611-616`'s
guard-skip-preservation assertion now runs unconditionally against `harness-failures.jsonl` (no
`if (skillErrorOrWakeForFirstPick)` dead guard remains), and `index.mjs:792-796` unconditionally
appends a `kind:'router_reroute_skip'` line to `harness-failures.jsonl` for every no-realized-action
pick, whether the wake goes on to reroute successfully or escalate. **However**, this reads REQ-509's
own literal AC text — "preserved verbatim **in the ledger**" — and finds a genuine, unresolved
requirement mismatch, not a stylistic quibble:

- Cross-referencing every other use of "the ledger" / "a ledger line" in `behavioral-spec.md`
  (REQ-510's own EARS clause, REQ-512's "append ... a ledger line", and line 777's "distinguishable
  from the ledger alone") confirms this spec consistently uses "the ledger" as a specific proper noun
  for the file the wake-loop's `LEDGER_PATH`/`formatRecord`/`safeAppend` machinery writes to
  (`state/ledger.jsonl`) — never for `harness-failures.jsonl`, which the spec ALWAYS names explicitly
  by its literal filename whenever meant (REQ-508's AC: "append one `harness-failures.jsonl` detail
  line").
- Ground truth (read `runAlwaysActWake` in full, `index.mjs:666-842`): the reroute branch never calls
  `safeAppend(LEDGER_PATH, ...)` for the just-rerouted-away-from slot — only `appendHarnessFailure`
  (→ `harness-failures.jsonl`). So `ledger.jsonl` genuinely carries zero trace of the guard-blocked
  attempt after a successful reroute; only the file the spec explicitly does NOT call "the ledger"
  carries it.
- This reinterpretation was made silently: the fix rewrote the CODE and the TEST's own title/comments
  to target `harness-failures.jsonl`, and `contracts/sprint-1.md`'s CRIT-006 was rewritten with a
  supporting rationale ("ledger.jsonl's one line per wake is always the wake's own FINAL outcome") —
  but `behavioral-spec.md`'s own REQ-509 AC text (lines 490-495) was never correspondingly revised, and
  no changelog entry documents this pivot, unlike every other requirement-shape change in this
  feature's history (FIND-101/102/103/201/301), each of which closed with an explicit, dated
  changelog rewrite of the actual requirement text.
- The claimed justification itself is an unstated design inference, not an explicit spec prohibition:
  REQ-510's EARS text requires `ledger.jsonl` to carry a line with AT LEAST certain named fields for
  the wake's final outcome — it never states the file may carry no OTHER line for that `wake_id`.
  REQ-512's own `always_act_not_engaged`/`always_act_go_live` lines already coexist with ordinary wake
  lines in the SAME file, proving multi-line-per-wake-id `ledger.jsonl` entries are not architecturally
  forbidden by this spec. An additional, distinctly-`kind`ed `ledger.jsonl` line for the guard-blocked
  attempt was an available, spec-literal-compliant design this fix did not take.
- Practical consequence: `harness-failures.jsonl` is defined by REQ-508 for a semantically different
  event class (the wake's TERMINAL exhausted-bound failure), not an in-flight, ultimately-successful
  reroute. `harness-health.mjs`'s `classifyLayer`/`computeSlotHealth`/`computeHarnessHealth` (the
  existing per-slot health/escalation machinery this codebase already has) read `ledger.jsonl`-shaped
  `kind` values exclusively — `router_reroute_skip` is structurally invisible to that system. An
  operator inspecting `ledger.jsonl` (the file every other REQ-51x observability requirement in this
  spec directs them to) after a real guard-block-then-reroute event sees only the final, successfully
  rerouted pick, with no cross-reference hint that a skip happened at all — exactly the visibility gap
  REQ-509's AC exists to close.

See `findings/FIND-001.json` for the full evidence trail.

## Full REQ-501..513 conformance sweep (final pass before harden/converge)

Walked every requirement against the current implementation + its named test(s):

- **REQ-501** (identity+flag gate): `checkAlwaysActIdentity`/`resolveAlwaysActGate` (index.mjs) strip
  `ANICCA_SOLANA_PRIVATE_KEY` before either derivation, fail closed on mismatch/error/malformed flag.
  PROP-501a/b/c present and non-tautological (real spawned wakes, real mocked-identity fixture).
- **REQ-502** (menu = isEarnSlot ∪ doctrine set): `isEarnActionSlot` in `always-act-router.mjs`,
  PROP-502a/b/c present, literal-set-equality test against the real registry confirmed.
- **REQ-503** (bootstrap-reserve gate applies): `assembleAlwaysActMenu` threads `catalog-gate.mjs`'s
  real `filterCatalog` unmodified; PROP-503a/b present, now named in CRIT-011.
- **REQ-504** (sleep withheld on real wire): `getToolDefinitions(slots,{omitSleep})`,
  `brain.mjs`'s conditional `tools:`/prompt-text lines; PROP-504a/b present, PROP-504b is a real
  `thinkProxy` call with only `httpPost` mocked.
- **REQ-505** (no-tool-call not terminal): Rows 2/3/4/8/9/10/11/12 of the transition matrix all present
  as named tests; PROP-505a covered.
- **REQ-506** (no-realized-action reroute, risk-free-only, hard exclusion): Rows 5/6/6b/7 present;
  PROP-506a/b/c/d/e/f/g all present and traced against real code (`index.mjs:779-818`'s
  `rerouteTargets = alwaysActMenu.filter((s) => s !== slot && isMarketRiskFree(s, riskTagOf))`).
- **REQ-507** (no judgment): `always-act-router.mjs` re-read in full, zero regex/judgment branching;
  PROP-507a/b present.
- **REQ-508** (truthful escalation): `writeAlwaysActEscalation` never fabricates `profitable:true`,
  always calls `appendHarnessFailure`; PROP-508a covered via the Row escalation tests.
- **REQ-509** (money-safety non-regression + skip-record preservation): PROP-509a (diff-path
  allowlist) present and correct. PROP-509b's "different slot picked" half is correct; its
  "preserved verbatim in the ledger" half targets the wrong file per the spec's own literal wording —
  **this is FIND-001, blocking**.
- **REQ-510** (per-wake ledger record, attemptsUsed domain pin): PROP-510a present; the two
  iteration-5-notes.md literal-domain-pin ACs are both covered (empty-menu case trivially via
  PROP-502d; the falsifying empty-reroute-target case via PROP-506f). Now named in CRIT-012.
- **REQ-511** (bounded 2-total think() calls, attemptsUsed sole arbiter): PROP-511a present as a
  bounded-exhaustive property test; every Row 1-12 confirms no reachable sequence exceeds 2 calls.
- **REQ-512** (observability of silently-OFF flag): PROP-512a/b present including the `go-live.mjs`
  standalone-module structural test confirming `index.mjs` never imports it.
- **REQ-513** (fabricated-slot rejection, attemptsUsed-only branch selection): Rows 3/6/6b/8/10/11
  directly exercise PROP-513a/b/c/d/e; branch selection confirmed keyed exclusively on `attemptsUsed`
  by direct code read of `index.mjs:717-728`.

Every requirement except REQ-509 has both conforming code and a non-tautological test. REQ-509's code
and test are internally CONSISTENT with each other (both target `harness-failures.jsonl`) but neither
is consistent with the spec's own literal AC text — this is a spec_fidelity/requirement_mismatch
finding, not a test-quality or coverage gap.

## Regression scan of the iter2-fix diff (706e8fcb..2096ee06)

- `harness-health.mjs` itself is unmodified by this sprint (confirmed by reading it in full); the new
  `router_reroute_skip`/`router_menu_empty`/`router_no_realized_action` kind values are, by design,
  members of none of its kind sets (`CLEAN_KINDS`, `SLOT_HEALTH_KINDS`, `wake_error`/`skill_*`
  branches) — no structural collision, no false-positive/negative health classification introduced.
- `runtime/loop/package.json`'s `test`/`test:unit`/`test:integration` scripts correctly register all
  5 always-act-*/go-live test files; no test file is silently excluded from the default `npm test` run.
- No test assertion was found weakened (loosened tolerance, removed check, or narrowed scope) between
  iteration-2 and this HEAD in any of the 4 findings' fix diffs — FIND-001/002/003's fixes are purely
  additive (new tests, new contract criteria); FIND-004's fix changed an assertion's TARGET file
  (ledger.jsonl's implicit expectation → harness-failures.jsonl) rather than weakening it, which is
  precisely the substance of the re-opened finding above, not a coverage regression in itself.

## Positive evidence (dimensions/areas re-verified clean this iteration)

- **REQ-507 purity/no-judgment**: `always-act-router.mjs` re-read in full (257 lines) — unchanged,
  still zero I/O imports, zero regex/judgment branching.
- **REQ-513 dispatch guard**: `isRejectableSleepOrOffMenu(slot, currentOfferedSlots)` still invoked
  against the retry loop's own per-attempt local variable, never `ctx.alwaysActMenu` directly; branch
  selection still keyed exclusively on `attemptsUsed`.
- **Contract weight integrity**: CRIT-001..012 weights sum to exactly 1.00.
