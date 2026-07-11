# Purity Boundary Audit — franklin-alwaysact-skill-router (VCSDD Phase 5)

Compares `specs/verification-architecture.md`'s "Purity Boundary Map" (Phase 1b, iteration-4-corrected)
against the real implementation, worktree `/Users/operator/anicca/.worktrees/alwaysact-impl`, HEAD
`39a9c217`.

## Declared Boundaries

**Pure Core** (declared): a new module `runtime/loop/always-act-router.mjs` — `isEarnActionSlot`,
`assembleAlwaysActMenu`, `buildAlwaysActToolDefinitions`, `isMarketRiskFree`, `noRealizedAction`,
`isRejectableSleepOrOffMenu`, `nextRerouteState`, `buildMustActReinforcement`,
`buildAlwaysActLedgerFields`, `isPostGoLiveRegression`, `buildGoLiveRecord`, `shouldRecordGoLive` — "no
I/O, every input pre-loaded and passed in, every classifier injected." Plus one additively-modified
pre-existing pure function: `prompt.mjs::getToolDefinitions(slots, opts)` gains an optional
`{omitSleep}` parameter, "a pure, deterministic string/object transform," and `buildAlwaysActToolDefinitions`
is declared a thin, non-duplicating wrapper reusing it.

**Effectful Shell** (declared, extended not replaced): `runtime/loop/index.mjs` (identity-gate
subprocess calls, the reprompt/reroute retry loop, the widened classify call-site, the REQ-513 dispatch
guard, all ledger appends); `runtime/loop/go-live.mjs` (new, the one-time operational append);
`runtime/loop/brain.mjs::thinkProxy`/`thinkClaudeP` (additively modified `tools:`/prompt-text lines,
conditional on `ctx.alwaysActEngaged`); `runtime/loop/context.mjs::assembleContext` (additively modified,
new `alwaysActEngaged`/`alwaysActMenu` fields, still itself I/O-free per its own pre-existing contract).
REQ-507's explicit no-judgment contract: "every branch reads only registry bookkeeping fields... or the
harness's own attempt-state counter, never the model's args or free-text output."

## Observed Boundaries

### `always-act-router.mjs` — zero I/O, verified by direct read + grep this session

```
$ grep -n "^import" always-act-router.mjs
22:import { isEarnSlot } from './earn-slot.mjs';
23:import { getToolDefinitions } from './prompt.mjs';
```
Exactly 2 imports, both to other declared-pure modules (`earn-slot.mjs`, `prompt.mjs`) — **zero**
`node:fs`/`node:http`/`node:child_process`/`node:path`/any I/O-capable import. ✅ matches declared.

```
$ grep -n "RegExp\|\.match(\|\.test(" always-act-router.mjs
(zero matches)
```
No regex/pattern-matching over model output anywhere in the file. ✅ matches CRIT-009's own
passThreshold text verbatim (re-derived independently this session, not merely copied from the
contract).

Every one of the 12 exported functions was read in full this session (236 lines total). Each takes its
inputs as plain-value parameters and returns a plain value/object — no function opens a file, spawns a
process, reads `process.env`, or calls `Date.now()`/`Math.random()` internally
(`buildGoLiveRecord`/`isPostGoLiveRegression` take `ts`/pre-gathered `ledgerTail` as caller-supplied
arguments, never self-derived). ✅ matches declared.

### No judgment hardcoding — REQ-507's contract, verified by reading every branch

Every conditional in `always-act-router.mjs` branches on one of: (a) a registry BOOKKEEPING field
(`slots[name].status`, `riskTagOf(slot)`, `alwaysAvailableOf`), (b) the doctrine-named fixed set
(`DOCTRINE_EARN_ACTIONS`, a hardcoded `Set` of 2 slot NAMES — bookkeeping, not the model's free-text
`args` content), (c) set-membership of a `slot` NAME against an offered-slots array
(`isRejectableSleepOrOffMenu`), or (d) the harness's own numeric `attemptsUsed` counter
(`nextRerouteState`). The one place `args` (the model's chosen parameters) appears at all is
`buildAlwaysActLedgerFields`'s pass-through (`args && typeof args === 'object' ? args : {}`, a type
GUARD, not a content branch) and `buildMustActReinforcement`'s template-string interpolation of the
MENU (not `args`). **No branch anywhere reads `args`' CONTENT to decide behavior** — confirmed by the
`grep -n "args\." always-act-router.mjs` re-check this session, whose single hit is inside a template
literal (`` `... and your real args. Pick one now...` ``), not code. The model chooses freely among the
offered slots and its own `args`; the router only constrains the STRUCTURE (which slot names are
legal this attempt) and NEVER inspects/ranks/filters by what the model decided to DO with a slot. ✅
matches REQ-507/PROP-507b's own contract, independently re-derived (not merely quoting the contract's
own claim).

### Effectful shell — `index.mjs`'s real dispatch, verified by direct read

- `resolveAlwaysActGate`/`checkAlwaysActIdentity` (`index.mjs:247-288`): genuinely impure —
  `process.env.HOME`/`process.env.ALWAYS_ACT_ENABLED` reads, `execFileAsync` subprocess spawns
  (`deriveSolanaAddress`), a real `setTimeout` pacing floor. Correctly classified Effectful Shell. ✅
- `runAlwaysActWake` (`index.mjs:666-860`): the retry-loop orchestrator — calls the impure `think()`,
  `runSkillWithKillRef`, `classifyEarnResult`, and 4 distinct `safeAppend(LEDGER_PATH, ...)` write sites
  (lines 674/704/720/814/818/828/856/913 across the function and its `writeAlwaysActEscalation` helper) —
  but every BRANCH DECISION inside it (whether to retry/reroute/escalate) is made by calling the pure
  `nextRerouteState`/`isRejectableSleepOrOffMenu`/`noRealizedAction`/`isMarketRiskFree` and reading their
  plain return values — the loop never re-implements their logic inline. Confirmed by reading the full
  function body this session (lines 666-860): every `if` that decides retry-vs-escalate calls
  `nextRerouteState({attemptsUsed, maxAttempts: 1})` and reads `.exhausted`/`.attemptsUsedNext`, never
  re-deriving that decision from `currentOfferedSlots` identity inline (the exact FIND-301 class of bug
  the spec's own iteration-4 fix eliminated — re-verified NOT reintroduced: `attemptsUsed` is the only
  variable read at every branch point, `currentOfferedSlots` is read only inside the
  `isRejectableSleepOrOffMenu(slot, currentOfferedSlots)` call itself, for validity, never for branch
  selection). ✅ matches declared "impure orchestrator calls pure core, never duplicates its logic."
- `prompt.mjs::getToolDefinitions` (lines 137-179, read in full this session): the new `opts.omitSleep`
  parameter only conditionally skips one `defs.push(SLEEP_TOOL)` line — no I/O added, no existing
  call site's behavior changed when `opts` is omitted (confirmed: `if (!omitSleep) defs.push(SLEEP_TOOL)`,
  `omitSleep` defaults `false` via `opts.omitSleep === true`). ✅ stays pure, matches declared.
- `context.mjs::assembleContext` (read in full, 60 lines): the 2 new fields
  (`alwaysActEngaged: alwaysActEngaged === true`, `alwaysActMenu: Array.isArray(...) ? ... : []`) are
  pure type-coercions of caller-supplied arguments — no new I/O introduced to this already-pure module.
  ✅ matches declared "unmodified from Phase 2c" (an even stronger guarantee than the spec required,
  since Phase 2c's own diff already landed this additive change before Phase 3).
- `brain.mjs::thinkProxy`/`thinkClaudeP` (`brain.mjs:63-100`, read in full): `tools:` line and the
  prompt-text sleep-mention line both branch on `ctx.alwaysActEngaged` — a plain boolean read off the
  already-assembled `ctx` object, not a new I/O read; `PROP-504b`'s own wire-seam test (re-run this
  session, 3/3 green) proves this conditional actually governs the REAL outbound HTTP body, not merely
  a standalone pure helper's return value. ✅ matches declared.
- `go-live.mjs::recordGoLive` (read in full, 60 lines): impure (reads the real ledger tail via
  `readLedgerLines`, appends via `appendLedgerLine`) but delegates ALL decision logic to the pure
  `shouldRecordGoLive`/`buildGoLiveRecord` — confirmed by direct read, the function body is exactly
  "read tail → ask pure predicate → build pure record → append," no inline re-derivation. ✅ matches
  declared. Confirmed this session (again) that `index.mjs` never imports this module (`grep -n
  "go-live.mjs\|recordGoLive" index.mjs` → zero matches) — the go-live action is genuinely isolated from
  every wake's own control flow, exactly as declared ("index.mjs never imports or calls this module").

### Ledger-record structural purity (`ledger-record.mjs`, unmodified by this feature)

`formatRecord = (fields) => JSON.stringify(fields) + '\n'` — confirmed still a single-line pure
function, unmodified by this feature's diff, and reused unchanged by every new ledger-write call site
this feature adds (`router_reroute_skip`, `router_no_realized_action`, `router_menu_empty`,
`always_act_not_engaged`, `always_act_go_live`) — no new, parallel record-formatting primitive was
introduced. ✅ matches the codebase's existing "no new writer" convention this feature's own comments
repeatedly cite.

## Mismatches found

**None.** Every item in the declared Purity Boundary Map was independently re-derived this session
(fresh reads + greps, not merely re-quoting Phase 1b's own claims) and matches. No hidden side effect
was found inside any function classified Pure Core; no impure function re-implements pure-core decision
logic inline; no verifier-hostile coupling (e.g. a pure function reaching into module-level mutable
state) was found — `always-act-router.mjs` has zero module-level `let`/mutable state at all (only the
one `const DOCTRINE_EARN_ACTIONS = new Set([...])`, itself immutable after definition and never mutated
by any exported function — confirmed by reading the full file, no `.add(`/`.delete(` call anywhere).

## Follow-up before Phase 6

None required for the purity boundary itself. One adjacent, non-purity observation carried over from
`security-report.md` §4 (`go-live.mjs`'s idempotency TOCTOU race under genuinely concurrent invocation)
is a money-observability robustness gap, not a purity violation — `recordGoLive`'s pure/impure split is
itself correct regardless of that race (the race is in the ORCHESTRATION of two impure calls racing each
other, not in any function crossing the pure/impure boundary incorrectly). Not blocking.

## Summary

The implemented core/shell split matches the declared Purity Boundary Map with **zero deviations**:
`always-act-router.mjs` is verified I/O-free (2 pure imports only, no `fs`/`http`/`child_process`, no
mutable module state) and judgment-free (every branch reads registry bookkeeping, a fixed doctrine set,
slot-name membership, or the harness's own `attemptsUsed` counter — never the model's `args` content;
the model retains 100% of the judgment over WHICH offered slot to pick and WHAT args to pass, the router
only constrains the offered STRUCTURE). Every Effectful Shell function extended by this feature
(`index.mjs`'s gate/retry-loop/dispatch-guard, `go-live.mjs`, `brain.mjs`, `context.mjs`) delegates its
actual decision logic to the pure core rather than re-implementing it inline, confirmed by direct read
of every touched function's full body this session. No purity or judgment-hardcoding violation found.
