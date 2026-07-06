# P1 Adversary Verdict — anicca-agent-economy

Fresh-context adversary, disk-only, zero builder context. Commit reviewed: `88e87ed`
(worktree `/Users/anicca/anicca/.worktrees/agent-economy`, branch `feature/agent-economy`).
Nothing modified, nothing pushed. All commands below were actually executed in this session
(real stdout/exit codes, not inferred).

## Overall (round 1): FAIL (no-fail-open fails; everything else passes) — SUPERSEDED, see ROUND 2 below: PASS

| Dimension | Verdict |
|---|---|
| halt-correctness | **PASS** |
| no-fail-open | **FAIL** |
| wiring-triggers | **PASS** (with one caveat, same root cause as the FAIL above) |
| no-strategy-touch | **PASS** |
| test-integrity | **PASS** |

---

## 1. halt-correctness — PASS

Live E2E, not just the unit tests re-run:

- Seeded a real `-4` cumulative loss for a freshly-generated wallet
  (`0x2c2e6b194e0cf4656fc226bea96a7c7bd20c9aae`), then ran the REAL `skills/earn/run.sh`
  (`EARN_MODE=discover`) against it (using `PKVAR=MYSECRETKEYNAME` to dodge
  `$HOME/.openclaw/.env`'s own `BLOCKRUN_WALLET_KEY=` line silently clobbering the test key —
  note below). Result: `HALT: cumulative-net-below-reserve ... skipping wake`, exit 0,
  **ledger line count unchanged (1→1)** — the pass that would go negative truly did not append.
- Same wallet seeded `+4` instead: `OK: ... byAgent={"halt":false,...,"cumulativeNet":4}`,
  wake proceeded, line count 1→2 (discover line appended). Both directions of the spec's exact
  ask ("a pass that would go negative actually stops") are proven live.
- `node --test __tests__/earn-guard.test.js` in `skills/_shared/lib`: 17/17 pass, including the
  spec-quoted scenario ("a pass that pushes cumulative net negative -> HALT").

## 2. no-fail-open — FAIL (one high-severity, live-reproduced finding; three latent)

### FINDING A (HIGH, live-reproduced) — wallet-resolution failure silently defeats the new gate
`skills/earn/run.sh`'s new guard clause (this diff) is:
```bash
if [ -n "$WLOW" ] && ! node ".../earn-guard.mjs" check "$WLOW" "" "$LEDGER"; then
  echo "... HALT ..."; exit 0
fi
```
`[ -n "$WLOW" ]` is a **precondition**, not part of the check. If wallet resolution fails for any
reason (missing/unreadable signing key, `eth_account`/python transient failure — plausible, this
exact class of identity failure is what caused the cross-instance leak in #27 per this same file's
own comments), `$WLOW` is empty, the whole `&&` short-circuits false, and **the guard silently does
not run at all** — the wake proceeds ungated. Reproduced live:

```
$ env -u BLOCKRUN_WALLET_KEY PKVAR=NONEXISTENT_KEY_VAR EARN_LEDGER=$LEDGER7 EARN_MODE=discover bash run.sh
recorded net=0 tx=- status=-
[earn] discover wake=... -> NARRATE
run.sh exit: 0
$ cat $LEDGER7
{"ts":...,"wallet":"unknown","source":"x402","task":"discover", ...}
```
Worse: the line written in this state is bucketed under the **literal string wallet:"unknown"**
(run.sh's own `${WLOW:-unknown}` default). Any real loss recorded while identity is broken lands in
that "unknown" bucket **permanently invisible to every future real-wallet-scoped check**, because
once identity resolves again, all queries use the real address, never the literal "unknown":

```
$ node ledger.mjs-appendLedger  # seed a -9999 loss under wallet:"unknown", source hl-trade
$ node earn-guard.mjs check 0xa3cdd4ec6b94f01826aaf90a6d5538a2aa8c4c21 hl-trade $LEDGER7
OK: bySkill={"cumulativeNet":0} byAgent={"cumulativeNet":0}   # the -9999 is invisible, forever
```
This is precisely the moment a fail-closed design most needs to trip — "can't verify identity" —
and it is the one case this diff does not gate. Fix direction: treat empty/unresolved `$WLOW` as
itself a HALT condition (fail-closed), not a bypass of the check.

### FINDING B (MEDIUM, live-reproduced, not yet reachable via current wired call sites)
`evaluateHalt(lines, {source, wallet: undefined})` — when `wallet` is omitted/undefined but
`source` is given — computes `bySkill` as a **cross-wallet aggregate** (matchesScope's
`scope.wallet != null` guard is skipped for `undefined`, so it silently matches every wallet) and
sets `byAgent = null` (skipped entirely, since `wallet != null` is false for undefined). Reproduced:
one agent's `-100` masked by a different agent's `+200` → `bySkill.cumulativeNet: 100, halt:false`.
Live end-to-end via `record.mjs` with a JSON payload that simply omits the `"wallet"` key
(an allowed source, `hl-trade`): the `-1000` line it writes is **invisible** to any later caller
that queries with a real wallet string (`cumulativeNet:0, halt:false`) — exactly the "unknown"
mechanism in Finding A, minus even the "unknown" fallback. Not reachable through `run.sh` /
`redeem.py` today (both always populate a wallet string), but `record.mjs` is documented as "the
CANONICAL earn-ledger writer... every earn skill's pass boundary" (spec explicitly wants
`hl-trade`/`sol-trade`/`x402-sell` to adopt this pattern next) — nothing in `record.mjs` or
`earn-guard.mjs` requires/asserts a non-empty wallet before trusting the scope math.

### FINDING C (MEDIUM, design gap, no live case-mismatch found in the current wiring)
`matchesScope` does exact case-sensitive string equality on `wallet`/`source`, with zero
normalization inside the one shared module meant to be the uniform choke point for "every earn
skill". Confirmed directly: a `0xABCDEF` ledger line queried with scope `0xabcdef` is silently
excluded (`cumulativeNet:0` instead of the real `-100`). Audited every current wallet-writing site
in `skills/earn` (run.sh's `WLOW`, `redeem.py`'s `DEPOSIT_WALLET.lower()`) — both are disciplined to
lowercase today, so this is **not currently triggered**, but it is enforced by caller convention,
not by the guard itself, in a codebase whose own history (#27) is exactly "wallet-identity string
mismatch caused a cross-instance leak."

### FINDING D (LOW/inherited, not part of this diff but breaks the module's own stated promise)
`earn-guard.mjs`'s doc comment says: "it is never safe to just skip the bad line and sum the rest
(that would hide a real loss)." That promise is enforced for bad *fields* inside an
otherwise-valid-JSON line (`isTrustworthy`), but not for a bad *line* — `ledger.mjs::readLedger`
(untouched, pre-existing) silently drops any line that fails `JSON.parse` (e.g. truncated by a
crash mid-`appendFile`) before `earn-guard.mjs` ever sees it. Reproduced: appended a genuine `+100`
line, then a truncated line representing an intended `-500` loss (`{"...,"net_` cut off) —
`earn-guard.mjs check` reports `OK: cumulativeNet=100`, exit 0, no `malformed-ledger-data` signal
at all. This is a gap in a shared dependency this feature builds its entire fail-closed invariant
on top of, not a bug newly introduced by this diff — flagging because P1's own money-safety
argument depends on it being closed somewhere.

### Not a finding (checked, ruled out)
`net_usdc` values that don't match `earn_usdc - cost_usdc` are trusted verbatim
(`isTrustworthy` never recomputes), but `deriveLine` (the sole writer in every currently-wired
path) always derives `net_usdc` itself — not reachable today, no live repro attempted beyond direct
function calls since no real writer can produce this shape.

### Methodology note (not a finding, but disclose it)
Live E2E of `run.sh` on this machine must use `PKVAR=<unused-name>` rather than relying on the
default `BLOCKRUN_WALLET_KEY` — `$HOME/.openclaw/.env` already defines that variable, and run.sh's
pre-existing (not part of this diff) env-sourcing loop unconditionally `export`s it, silently
overriding any caller-supplied test key of the same name. First attempt at the halt-correctness E2E
was invalidated by this and had to be redone; documenting so the next reviewer doesn't lose time to
the same trap.

## 3. wiring-triggers — PASS (same root cause as Finding A noted, not re-scored here)

- `earn/run.sh` top clause: proven above (halt-correctness section) — real HALT, real skipped
  append, real exit 0.
- `polymarket-trade/redeem.py → KILL → polymarket-trade/run.sh`'s **pre-existing, untouched**
  kill-switch: verified the path computation is identical
  (`os.path.dirname(os.path.abspath(__file__))` in both files, same directory) and verified live on
  an **isolated copy** of the whole `polymarket-trade/` dir (never touched the real worktree):
  `touch KILL` → ran the copied `run.sh` → exit 0, trace shows exactly
  `{"action":"skip","reason":"kill-switch"}`, nothing else executed.
- `record.mjs` stdout contract: captured stdout/stderr separately on a HALT-triggering call —
  stdout is byte-for-byte `NARRATE\n` (verified with `od -c`), the `P1-GUARD HALT: ...` line is
  stderr-only. `run.sh`'s `[ "$OUT" = "PROFITABLE" ]` exact-match callers are unaffected.

## 4. no-strategy-touch — PASS

`git diff main --stat` for this commit's P1-relevant wiring touches exactly
`skills/earn/lib/record.mjs`, `skills/earn/run.sh` (+9 lines, one guard clause), and
`skills/earn/polymarket-trade/redeem.py` (+38 lines, all accounting/kill-switch), plus new
`skills/_shared/lib/earn-guard.mjs` + tests and `earn/SKILL.md`/`README.md` doc updates. Zero
changes to `pick.py`, `place_order.py`, `market_maker.py`, `bundle_arb.py`, `hl.py`,
`execute-swap.py`, `execute-yield.mjs`, `execute-0xwork.py`, or any other file that makes a
market/side/amount/timing decision.

## 5. test-integrity — PASS (with a minor documentation-accuracy note)

Re-ran every relevant suite directly (not trusted from the commit message):
- `skills/_shared/lib/__tests__/*.test.js`: **84/84 pass** (matches the commit's claim exactly).
- `skills/earn/__tests__/*.js`: **5/5 pass** (matches).
- `skills/earn/lib/__tests__/*.js *.mjs`: **78/78 pass** across 9 files (oxwork, swap, cost-basis,
  deposit-guard, deposit-wiring, evolve, genome, record-solana, revenue) — the commit claims
  "earn/lib/__tests__ 60"; actual count on disk is 78 (or 18 if the `.mjs` files are excluded from
  the glob, which is an easy mistake — `*.js` does not match `*.mjs`). Every test in every file
  passes; this is a stale/imprecise count in the commit message, not a hidden failure.
- `skills/earn/polymarket-trade/test_redeem.py`: **15/15 pass** (matches).
- Net: 0 failures found anywhere. The commit's headline claim ("Full suite... green") is TRUE; its
  itemized per-directory breakdown (164 total) is not exactly reproducible with a straightforward
  glob (my recount: 84+5+78+15=182) — worth a quick fix to whatever counting method produced 164,
  but does not change the PASS/FAIL status of any test.

---

## Required before P1 can re-submit as PASS

Fix Finding A (empty/unresolved `$WLOW` must HALT, not bypass the gate) at minimum — it is a live,
reproduced fail-open in the exact top-of-wake clause this diff added, and it is the single highest-
risk moment (identity resolution broken) for a money-safety gate to go dark. Findings B/C are worth
closing in the same pass since they're the same root cause (unscoped/mismatched wallet identity)
and the fix is cheap (assert non-empty wallet in `evaluateHalt`/`checkHalt`'s CLI before computing
scopes; normalize wallet/source case inside `matchesScope`). Finding D should at least be filed
against `ledger.mjs` even if not fixed in this phase.

---

## ROUND 2 RE-VERIFICATION (commit `edc059b`, same worktree/branch) — 2026-07-06

Fresh re-verification, disk-only, nothing modified/pushed. All four findings independently
re-attacked with my ORIGINAL round-1 repro inputs (not re-reading the builder's own tests and
declaring victory) plus the real `earn/run.sh` E2E.

### Per-finding verdict

| Finding | Verdict |
|---|---|
| FIND-A (empty-wallet bypasses the gate) | **CLOSED** |
| FIND-B (cross-wallet aggregate / false-solvent on empty scope) | **CLOSED** |
| FIND-C (case-sensitive wallet match drops a real loss) | **CLOSED** |
| FIND-D (corrupt ledger line silently dropped) | **CLOSED** |
| New fail-open introduced by the fix | **NONE FOUND** |

### FIND-A — CLOSED

`earn/run.sh`'s guard clause is now unconditional (`if ! node earn-guard.mjs check "$WLOW" "" "$LEDGER"; then HALT; fi` — no more `[ -n "$WLOW" ] &&`). Live E2E, real script, no test mocks:
```
$ env -u BLOCKRUN_WALLET_KEY PKVAR=NONEXISTENT_KEY_VAR_2 EARN_LEDGER=$LEDGER_A EARN_MODE=discover bash earn/run.sh
HALT: missing-wallet bySkill=null byAgent=null
[earn] P1 GUARD: cumulative net breach or unresolved wallet (wallet='') — HALT (fail-closed), skipping wake.
exit: 0
$ ls $LEDGER_A  # does NOT exist — stronger than the old "unknown"-bucketed write
```
This is a strictly better outcome than what I asked for: not only does the gate now fire, no ledger
file is created at all (the guard runs before any `record_line` call is reachable, so the old
`${WLOW:-unknown}` fallback in the discover/execute JSON branches is now dead code for this path —
harmless, confirmed by reading run.sh's control flow: guard clause is at line 78, before the mode
branches that would ever construct that JSON).

**Regression check (real wallet, guard must still behave as before):** re-ran both original
halt-correctness E2E scenarios against a resolvable wallet — real `-4` loss still HALTs
(`cumulative-net-below-reserve`, byAgent computed, 0 lines added) and real `+4` profit still
proceeds (line count 1→2). Unaffected.

### FIND-B — CLOSED

`evaluateHalt` now asserts `isValidWallet(wallet)` (non-empty string after trim) BEFORE computing
any scope, returning `{halt:true, reason:"missing-wallet", bySkill:null, byAgent:null}` otherwise.
Re-ran my exact original repro (one agent -100, a different agent +200, source given/wallet
omitted):
```
evaluateHalt(lines, { source: 'hl-trade' })
=> {"halt":true,"reason":"missing-wallet","bySkill":null,"byAgent":null}
```
No more cross-wallet masking (previously: `{"halt":false,...,"cumulativeNet":100}`, hiding the -100).
The empty-string-wallet variant (`wallet:""`, previously a false "matches nothing → solvent" pass)
is also fixed — 31/31 tests including `FIND-B: evaluateHalt with wallet='' ...` pass, and I
independently confirmed the CLI maps an empty wallet arg to exit 1 (not exit 2 usage, not exit 0),
live, via the FIND-A run above (`check "" "" ...` → HALT).

### FIND-C — CLOSED

`matchesScope` now lowercases both sides of the wallet comparison (`normalizeWallet`, `source`
deliberately stays strict since it's a fixed code-constant identifier, not an address). Re-ran my
exact original repro:
```
evaluateScope([{wallet:'0xABCDEF', source:'s', earn_usdc:0, cost_usdc:100, net_usdc:-100}],
              {wallet:'0xabcdef', source:'s'})
=> {"halt":true,"reason":"cumulative-net-below-reserve","cumulativeNet":-100}
```
Previously this returned `{"halt":false,"cumulativeNet":0}` — the mixed-case loss was invisible.
Now it is found and correctly halts.

### FIND-D — CLOSED

`earn-guard.mjs` now has its own `readLedgerStrict` (separate from `ledger.mjs`'s `readLedger`,
which is explicitly left unchanged for its other callers) that tracks whether any non-blank line
failed `JSON.parse` and fail-closed HALTs with reason `unparseable-ledger-line` regardless of scope
match. Re-ran my exact original repro (healthy `+100` line, then a truncated line cut off mid-write):
```
$ node earn-guard.mjs check 0xcafe hl-trade $CORRUPT2
HALT: unparseable-ledger-line bySkill=null byAgent=null
exit: 1
```
Previously this returned `OK: cumulativeNet=100` (the corruption silently vanished). Now it halts.
Regression-checked: blank lines between real lines are still correctly treated as normal (not
corruption) — verified via the builder's own `FIND-D regression: blank lines...` test, and it's
consistent with `readLedgerStrict`'s explicit `if (l.trim().length === 0) continue;`.

### New fail-open hunt on the fix diff itself

Deliberately re-attacked the new code with edge cases beyond the four findings:
- `isValidWallet` rejects non-string wallets (null/undefined/number/object) and whitespace-only
  strings — all correctly HALT `missing-wallet`, not just the empty-string case.
- `hasSource` now also treats an explicit empty-string `source` as "no source" (`source !== ""`),
  which is STRICTER than the pre-fix code (old code would have computed a near-always-empty
  `bySkill` scope for `source:""` and silently reported it solvent by finding zero matching lines —
  not independently exploitable before either, since the CLI already normalized `""` to `undefined`,
  but the direct-caller path is now hardened too). This is a strict improvement, not a new gap.
- `byAgent` is now unconditionally computed once wallet is valid (previously gated on
  `wallet != null`, an equivalent-but-less-defensive check) — no scenario found where this produces
  a wrong result.
- Checked whether `readLedgerStrict`'s "any corruption anywhere in the file halts every wallet's
  check regardless of scope" (intentional, per the builder's own comment and unit test) creates an
  operational concern: `earn/run.sh` defaults ALL wallets/sources to ONE shared
  `state/earn-ledger.jsonl` file, so one corrupted line from any agent now halts every OTHER
  agent sharing that file too, until a human/agent manually removes the bad line. This is a
  deliberate, maximally-conservative fail-closed tradeoff (documented, tested), not a fail-open —
  flagging as an operational note for whoever owns ledger hygiene, not a blocking finding.
- No non-string/odd `source` value (e.g. a number) is passed by any current real caller (run.sh's
  CLI arg, redeem.py's literal `"polymarket-redeem"`, record.mjs's `line.source` from `deriveLine`),
  so the `source`-side of `matchesScope` staying strict-string-equality is not currently reachable
  as a gap; noted only as a symmetry observation, not a finding.

### Test-integrity re-verification

Re-ran every suite myself, real execution:
- `skills/_shared/lib/__tests__/*.test.js`: **98/98 pass** (was 84 before this fix; +14 new
  FIND-A/B/C/D tests in `earn-guard.test.js`, matches the commit's stated recount exactly).
- `skills/earn/__tests__/*.js`: **5/5 pass** (unchanged).
- `skills/earn/lib/__tests__/*.js + *.mjs`: **78/78 pass** (unchanged).
- `skills/earn/polymarket-trade/test_redeem.py`: **15/15 pass** (unchanged, as the commit claims).
- **Total: 98+5+78+15 = 196/196, 0 failures.** The corrected recount (196, was 164) is accurate —
  independently reproduced, not taken on faith.

### Overall no-fail-open verdict: PASS

All four round-1 findings are closed with live, adversarial re-repro (not just re-reading the new
unit tests). No new fail-open found in the fix diff itself. One operational note (shared-ledger
blast radius on corruption) is worth surfacing to whoever owns ledger hygiene but does not block
P1. **P1 overall verdict flips to PASS** (all five original dimensions: halt-correctness PASS,
no-fail-open PASS, wiring-triggers PASS, no-strategy-touch PASS — re-confirmed unaffected by this
diff since it touches no strategy file — test-integrity PASS).
