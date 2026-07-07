# Resolution Notes — spec review iteration-19 (FIND-1801, FIND-1802, FIND-1803)

**Feature**: anicca-agent-spawn · **Result**: all three iteration-19 findings resolved;
`behavioral-spec.md` and `verification-architecture.md` bumped to **revision: iteration 19**.

(This file originally covered only FIND-1801, resolved first. A parallel review process
independently re-ran the iteration-19 spec review and surfaced two additional, critical findings —
FIND-1802 and FIND-1803 — committed to `reviews/spec/iteration-19/output/` after the FIND-1801 fix was
already underway. All three are resolved together in this same pass, in the same **iteration 19**
revision bump, per the scope-extension instruction received mid-task.)

---

## FIND-1801 (major) — `filterProductiveCitizens`'s `bootstrapWindowDays` gains an explicit default + a by-construction identity binding against REQ-402's `BOOTSTRAP_WINDOW_DAYS`

**Problem**: `filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays})` — the same
function whose `ledgerRows`/`citizens` arguments were already hardened in iterations 17/18 (FIND-1601) —
had a fourth parameter, `bootstrapWindowDays`, with neither an explicit stated default anywhere in this
document, nor a proof obligation confirming its real, passed-in value is, by construction, identical to
REQ-402's own `BOOTSTRAP_WINDOW_DAYS` constant (default `14`), which REQ-101's own prose textually claims
it mirrors ("the same window REQ-402 itself applies"). This left an implementer free to hardcode a
diverging value (a stale config default, a typo'd literal) for REQ-101's own real-time safeguard window
without any test ever catching the divergence — structurally the same "two independently-configurable,
same-meaning cross-requirement values could silently drift apart" hazard this document had already closed
twice elsewhere (PROP-402e for `BOOTSTRAP_WINDOW_DAYS`/`SPAWN_COOLDOWN_DAYS`, PROP-206g for
`seedUsdc`/REQ-204's gas-seed-transfer amount) but never itself applied to this specific pair.

**Resolution** — mirrors PROP-402e's exact treatment:

1. `behavioral-spec.md`'s REQ-101 Acceptance Criteria gains a new bullet (after the FIND-1601 real-
   derivation bullet): `bootstrapWindowDays` defaults to `14`, identical to REQ-402's own
   `BOOTSTRAP_WINDOW_DAYS` constant — never independently configurable to a different value —
   mirroring the exact treatment the iteration-18 fix already gave `decideColonySpawn`'s own
   `cooldownDays`/`failureCooldownCap`/`maxConcurrentSpawns` defaults.
2. A new proof obligation, **PROP-101k** (`verification-architecture.md`'s Proof Obligations table,
   immediately after PROP-101j), requires, BY CONSTRUCTION: Tier 0 — a structural read confirming the
   real value passed as `bootstrapWindowDays` into `filterProductiveCitizens` is derived FROM (re-exports,
   aliases, or is assigned directly from) REQ-402's own `BOOTSTRAP_WINDOW_DAYS` constant, never a second,
   independently-declared literal that merely happens to also read `14` today; Tier 1 — a unit test
   asserting `bootstrapWindowDays === BOOTSTRAP_WINDOW_DAYS` at runtime, PLUS a mutation fixture that
   changes `BOOTSTRAP_WINDOW_DAYS`'s configured value and asserts the value fed to
   `filterProductiveCitizens` changes identically alongside it — never remaining pinned to a stale
   independent literal. This is PROP-402e's own mutation-fixture design, applied here to this constant's
   OTHER consumer.
3. The Purity Boundary Map's `filterProductiveCitizens` row is extended with a new sentence citing
   PROP-101k for this default/identity binding.
4. The Gate's item (1b) is extended with a new clause requiring the adversary to confirm, by a
   control-flow read, that `bootstrapWindowDays` is read as/derived from REQ-402's
   `BOOTSTRAP_WINDOW_DAYS`, and that a fixture mutating `BOOTSTRAP_WINDOW_DAYS` changes the fed-in value
   identically alongside it (PROP-101k) — cross-referenced to item (10)'s own PROP-402e identity-check
   discipline for the same constant's other consumer.

**New PROP ID chosen**: `PROP-101k` (next unused ID in the `PROP-101*` family — `a` through `j` were
already in use).

---

## FIND-1802 (critical) — `computeSpawnGate`'s `balanceAkt` gains a real-derivation binding

**Problem**: `computeSpawnGate({balanceAkt, costAkt, bufferAkt})` (REQ-303, reused unmodified from
`~/anicca/skills/self/spawn-child/lib/akt-cost-gate.js`) had `costAkt`/`bufferAkt` bound to
`spawn-child/config.json`'s real values, but `balanceAkt` — its own FIRST-listed, most consequential
parameter, the live quantity actually being tested for sufficiency — had NO stated derivation
anywhere in either spec document: no named query function, no "never hand-assembled, always the
direct return value of X()" binding sentence. The SEVENTH confirmed instance of this session's
recurring pinned-input-derivation failure class (after FIND-1101/1401/1501/1601/1701/1801), this time
extending into REQ群C (REQ-303) rather than the REQ-101/102/202 cluster the prior six instances were
found in.

**Investigation — reading the REAL source before citing a mechanism** (per the dispatch's own
instruction not to invent one): read `~/anicca/skills/self/spawn-child/lib/akt-cost-gate.js` (the pure
gate function itself — confirms it takes `balanceAkt` as a bare argument, no query logic inside, by
design: "Pure Akash self-spawn READINESS gate (no I/O)"), `~/anicca/skills/self/spawn-child/run.sh`
(the REAL caller), and `~/anicca/skills/self/spawn-child/SKILL.md`. `run.sh`'s actual, on-disk logic
(lines resolving `ADDR`/`UAKT`/`BAL_AKT`):
```
ADDR="$("$PS" keys show "$AKASH_KEY" -a ...)"
UAKT="$("$PS" query bank balances "$ADDR" -o json ... | "$JQ" -r '.balances[]? | select(.denom=="uakt") | .amount' ...)"
BAL_AKT="$("$NODE" -e '...Number(process.argv[1]||0)/1e6...' "$UAKT")"
```
confirms the REAL mechanism: a fresh, read-only `provider-services query bank balances <address>` call
(address resolved via `provider-services keys show "$AKASH_KEY_NAME"` — the SAME signing wallet
`costAkt`/`bufferAkt` are already scoped to), parsing the `uakt`-denominated amount via
`jq -r '.balances[]? | select(.denom=="uakt") | .amount'`, converted to AKT by dividing by `1e6`. This
is the exact mechanism now cited — not invented.

**Resolution**:

1. `behavioral-spec.md`'s REQ-303 gains a new paragraph, "Deriving `balanceAkt` from real system
   state," stating this binding explicitly and citing `run.sh`'s real query+conversion logic verbatim,
   and REQ-303's Acceptance Criteria bullet for `computeSpawnGate` is rewritten to include this binding.
2. A new proof obligation, **PROP-303g** (`verification-architecture.md`'s Proof Obligations table,
   immediately after PROP-303f), requires Tier 1 (source-grep/control-flow read confirming the real
   orchestration passes a fresh `provider-services query bank balances` result, converted uakt→AKT, as
   `balanceAkt`) + Tier 2 (integration test independently re-querying the same wallet and asserting a
   match, plus a mutation fixture across a real/simulated AKT top-up between two evaluations) — mirrors
   PROP-102k/PROP-101j/PROP-202d/PROP-101k's own real-derivation discipline.
3. The Purity Boundary Map's `computeSpawnGate` row is extended with a new sentence citing PROP-303g.
4. PROP-303d (the pre-existing obligation for this call site) is corrected: it previously conflated
   "a `ready:false` result is treated as a REQ-305 deploy failure" with its own actual scope
   (arithmetic/config-binding correctness only) — this conflation is what FIND-1803 (below) also flags
   from a different angle, and is corrected here to explicitly hand off the sequencing question to
   PROP-303h.
5. Gate item (6a) is extended with a new clause requiring confirmation of this binding.

**New PROP ID chosen**: `PROP-303g` (next unused ID in the `PROP-303*` family — `a` through `f` were
already in use).

---

## FIND-1803 (critical, different defect class) — `computeSpawnGate`'s `ready:false` vs. REQ-304's bridge: resolving the internal contradiction

**Problem**: REQ-303's own text was internally self-contradictory about whether `computeSpawnGate`'s
`ready:false` result triggers an attempt at REQ-304's Skip API AKT-funding bridge, or unconditionally
aborts the deploy before that bridge is ever attempted. The "Funding-readiness gate reuse" paragraph's
closing clause ("the gate merely decides whether that bridge needs to run at all") implied a
causal/triggering relationship; the SAME requirement's own dedicated Edge Case stated, unconditionally,
that `ready:false` is "identically to the mint-cancels edge case ... a deploy failure under REQ-305 ...
never invoked ... no dseq fabricated" — describing NOTHING about the bridge being attempted first. As
literally worded, an implementer following the more specific, unconditional EARS-styled Edge Case would
never wire REQ-304's entire, three-times-hardened (FIND-402/502/602) bridge mechanism into any reachable
code path at all — every AKT-shortfall Akash deploy would simply fail forever.

**Design decision — grounded in the spec's own existing text, not invented from scratch**: I read
REQ-303 and REQ-304 in full before deciding. The load-bearing clue is PROP-304d's own pre-existing test
method, which already stated the bridge's hops must land funds "**before** `akt-treasury.sh`'s existing
`mint-act` step runs" — i.e., the spec already assumed a sequencing where the bridge runs, then
`akt-treasury.sh`'s mint step runs, consistent with a "bridge first, mint after" ordering rather than
"gate fails once, deploy aborts." I adopted the team's proposed **bridge-first, two-pass** reading, and
verified it is internally consistent with REQ-304's own entry/exit conditions (PROP-304d/e describe the
bridge's own mechanics assuming it IS invoked — they neither require nor forbid a specific trigger
condition, so this reading does not conflict with them):

1. **First pass**: `computeSpawnGate` runs on the wallet's balance as-is. `ready:true` → proceed
   straight to `akt-treasury.sh`'s mint step, bridge never invoked. `ready:false` → this is what
   triggers an attempt at REQ-304's bridge; the first pass's `ready:false` is NEVER itself a REQ-305
   failure.
2. **Second pass**: after the bridge attempt completes (success or failure), `computeSpawnGate` is
   RE-EVALUATED with a freshly re-queried `balanceAkt` (per FIND-1802's own binding rule — the same
   query, run again, so a successful bridge's new funds are honestly reflected). ONLY this second
   evaluation's result is final: `ready:true` → proceed to the mint step; `ready:false` → THIS is the
   actual REQ-305 deploy failure (identical treatment to the pre-existing "mint cancels" edge case).

**Resolution**:

1. `behavioral-spec.md`'s REQ-303 "Funding-readiness gate reuse" section gains a new, explicit
   "`computeSpawnGate`'s exact two-pass sequencing relative to REQ-304's bridge" paragraph stating this
   as the ONE unambiguous rule (superseding the prior implicit clause).
2. The Edge Case describing `computeSpawnGate`'s `ready:false` is rewritten to scope it explicitly to
   the SECOND, post-bridge evaluation, with an explicit note distinguishing it from the first
   evaluation's `ready:false` (which is never itself a failure).
3. REQ-303's Acceptance Criteria bullet for `computeSpawnGate` is rewritten to state the exactly-two-
   calls, only-the-second-`ready:false`-is-a-failure rule.
4. A new proof obligation, **PROP-303h** (`verification-architecture.md`, immediately after PROP-303g),
   requires Tier 1 (control-flow read confirming exactly two `computeSpawnGate` call sites, the second
   reachable only along the first's `ready:false` branch, positioned after the bridge step and before
   the mint step) + Tier 2 (three fixtures: first-pass-ready skips the bridge; first-pass-not-ready +
   successful bridge proceeds; first-pass-not-ready + still-not-ready second pass is the actual
   failure).
5. PROP-303d is corrected to no longer conflate its own scope (arithmetic/config-binding) with the
   sequencing question, explicitly deferring to PROP-303h.
6. The Purity Boundary Map's `computeSpawnGate` row is extended with a new sentence citing PROP-303h.
7. Gate item (6a) is extended with the sequencing confirmation requirement, cross-referencing item (7);
   Gate item (7) is extended with the funding-side half of the same requirement (confirming the bridge
   is genuinely reachable orchestration, not dead code), cross-referencing item (6a) back.

**New PROP ID chosen**: `PROP-303h` (next unused ID in the `PROP-303*` family after PROP-303g).

---

## Revision bump

Both `behavioral-spec.md` and `verification-architecture.md`'s header changelogs are bumped from
**revision: iteration 18** to **revision: iteration 19** (confirmed on-disk prior value was
`iteration 18` in both files before any of this pass's edits). The changelog paragraph is a single
iteration-19 entry covering all three findings, newest-first within the entry
(FIND-1803 → FIND-1802 → FIND-1801), prepended before the existing "AND spec review iteration-18
finding FIND-1701 resolved — ..." chain — the established convention in both files (newest fix first,
older fixes preserved verbatim after "AND spec review iteration-N finding ... resolved —").

**Revision bumped to**: `iteration 19`.

---

## Files changed

- `specs/behavioral-spec.md`:
  - Header (`**revision**:` line): bumped `iteration 18` → `iteration 19`; changelog paragraph now
    covers FIND-1803, FIND-1802, and FIND-1801 (newest first) in one iteration-19 entry.
  - REQ-101 Acceptance Criteria: new bullet for `bootstrapWindowDays`'s default + identity binding
    (FIND-1801).
  - REQ-303 "Funding-readiness gate reuse" section: new "Deriving `balanceAkt` from real system state"
    paragraph (FIND-1802); new "exact two-pass sequencing" paragraph (FIND-1803).
  - REQ-303 Edge Cases: the `computeSpawnGate ready:false` edge case rewritten to scope it to the
    second, post-bridge evaluation only (FIND-1803).
  - REQ-303 Acceptance Criteria: the `computeSpawnGate` bullet rewritten to state the two-call,
    only-second-failure rule (FIND-1802 + FIND-1803).
- `specs/verification-architecture.md`:
  - Header (`**revision**:` line): bumped `iteration 18` → `iteration 19`; same combined changelog.
  - Proof Obligations table: new rows `PROP-101k` (after PROP-101j), `PROP-303g` and `PROP-303h` (after
    PROP-303f); `PROP-303d` corrected to defer the sequencing question to PROP-303h.
  - Purity Boundary Map: `filterProductiveCitizens` row extended (PROP-101k); `computeSpawnGate` row
    extended (PROP-303g, PROP-303h).
  - `## Gate`: item (1b) extended (PROP-101k); item (6a) extended (PROP-303g, PROP-303h); item (7)
    extended and cross-referenced with item (6a) (PROP-303h).
- `reviews/spec/iteration-19/RESOLUTION-NOTES.md`: this file, rewritten to cover all three findings
  (originally drafted for FIND-1801 alone before the scope was extended mid-task).

No other findings from iteration-19's verdict remain open (FIND-1801, FIND-1802, FIND-1803 were the
complete set of three). `state.json` and the next iteration's review directory/manifest are
intentionally left untouched by this resolution — that is the orchestrator's/next dispatch's
responsibility.
