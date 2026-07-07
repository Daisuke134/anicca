# Resolution Notes — spec review iteration-12 (FAIL, 2 findings) → iteration-13 candidate

**Findings resolved**: FIND-1101 (critical), FIND-1102 (major)
**Files edited**: `specs/behavioral-spec.md`, `specs/verification-architecture.md`
**Not touched** (per instructions): `state.json`, reviews manifest/verdict files; no commit/push performed.

---

## FIND-1101 (critical) — REQ-102/REQ-305 cooldown-consumption contradiction

**Root cause confirmed by re-reading `~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn`
in full** (lines 6-32 of that file, the ONLY function in it): its rate-limit check is a genuine
array-scan over prior children, `children.some((c) => typeof c.spawned_ms === "number" &&
Number.isFinite(c.spawned_ms) && c.spawned_ms >= windowStart)` — never a single scalar "last attempt"
timestamp. REQ-102's own pinned `decideColonySpawn` signature, by contrast, took a bare scalar
`lastSpawnAttemptMs`, which structurally cannot express "how many of the recent attempts were
failures" — exactly what REQ-305's own failure-cap-of-3 rule needs to be computed. This produced a
genuine, unresolvable contradiction: REQ-102's own EARS clause said a failed attempt restarts the
cooldown "success OR failure," while REQ-305 said a failed attempt is EXEMPT from the cooldown up to
3 recent failures — both bound to the SAME `decideColonySpawn` function, with PROP-102b and PROP-305c
each requiring a DIFFERENT, incompatible behavior from it.

**Fix**: extend `decideColonySpawn`'s signature from the scalar `lastSpawnAttemptMs` to
`recentSpawnAttempts: Array<{ts: number, outcome: "success"|"failure"}>`, reusing the SAME array-scan
discipline `decideSpawn` already proves out, generalized from "an array of successes only" to "an
array of attempts, each carrying its own `outcome`." The ONE reconciled rule now stated identically by
both REQ-102 and REQ-305: a SUCCESSFUL attempt within `SPAWN_COOLDOWN_DAYS` is ALWAYS a hard cooldown
gate, regardless of failures in the same window; a FAILED attempt is cooldown-EXEMPT strictly below
`FAILURE_COOLDOWN_CAP` (default `3`, the same cap REQ-305 already specified) and becomes
cooldown-TRIGGERING, identically to a success, once the cap is reached.

### Edits made — `specs/behavioral-spec.md`

1. **Header revision line** (line 4) and its extended parenthetical (lines 4-16, new): bumped
   `iteration 11` → `iteration 12` and prepended a paragraph describing both FIND-1101's and
   FIND-1102's resolutions before the existing "AND spec review iteration-1 findings..." chain, so the
   document's own revision history stays self-describing and in the same style as every prior
   iteration's header.

2. **New changelog section**, `## Changelog (iteration 11 spec review → iteration 12)` — inserted at
   **line 213** (heading), with the Finding/Severity/Resolution table at **lines 220-223** (FIND-1101
   at line 222, FIND-1102 at line 223), immediately after the iteration-10→11 changelog's FIND-1002 row
   and before "## Scope of this increment (read first)" (now at line 225). Documents both findings in
   the same table format every prior iteration uses, grounded in the fresh re-read of
   `spawn-decision.js::decideSpawn`.

3. **REQ-102's EARS clause** (originally lines 494-500, now **lines 519-546**): replaced the single
   clause "at least `SPAWN_COOLDOWN_DAYS`... have elapsed since the colony's last spawn attempt
   (success OR failure — see REQ-305)" with a new named **"Cooldown Check, reconciled with REQ-305"**
   subsection (lines 525-546) that: (a) defines `recentSpawnAttempts` and explicitly cites
   `spawn-decision.js::decideSpawn`'s own array-scan pattern as the prior art being reused/generalized;
   (b) states the two-branch reconciled rule (success → unconditional hard gate; failure → exempt below
   `FAILURE_COOLDOWN_CAP`, gating once the cap is reached); (c) closes with an explicit one-sentence
   statement that this is "the ONE reconciled rule both REQ-102 and REQ-305 describe... never two
   different behaviors."

4. **REQ-102 Edge Cases** (lines 567-590): the old single bullet ("`SPAWN_COOLDOWN_DAYS` has NOT
   elapsed since the last attempt... cooldown is a hard gate regardless of how much surplus exists")
   was rewritten (lines 576-580) to reference the reconciled Cooldown Check by name instead of "the
   last attempt," and a NEW bullet (lines 581-585) was added stating the below-cap case explicitly
   ("Fewer than `FAILURE_COOLDOWN_CAP` failed attempts... the Cooldown Check does NOT apply on
   failure-count alone"), cross-referencing REQ-305's edge case and the new PROP-305g.

5. **REQ-102 Acceptance Criteria** (lines 592-613): the pinned function signature (lines 593-599) now
   reads `decideColonySpawn({ colonySurplusUsd, spawnThresholdUsd, recentSpawnAttempts, nowMs,
   cooldownDays, failureCooldownCap, childrenProvisioning, maxConcurrentSpawns })`, with an explicit
   note that `failureCooldownCap` defaults to `3`, "identical to REQ-305's own cap, the SAME number,
   never independently configurable." Three NEW bullets were added (lines 605-613) pinning the exact
   reconciled behavior: a success entry in-window → unconditional `rate_limited`; fewer than
   `failureCooldownCap` failures with zero successes → NOT rate-limited; `failureCooldownCap` or more
   failures with zero successes → `rate_limited`, identical to a success.

6. **REQ-305's EARS clause** (originally line 1777, now **line 1854**): "REQ-102's
   `SPAWN_COOLDOWN_DAYS` timer SHALL NOT be considered 'consumed' by a failed attempt" is now qualified:
   "...UNLESS that failure is itself the `FAILURE_COOLDOWN_CAP`-th (default `3`) recent failed attempt
   within the SAME window — see REQ-102's own reconciled Cooldown Check and the edge case below, which
   describe this IDENTICAL rule (resolves FIND-1101: REQ-102 and REQ-305 no longer describe two
   different behaviors)."

7. **REQ-305's failure-cap Edge Case** (originally lines 1838-1841, now **lines 1918-1927**): rewritten
   to explicitly name `FAILURE_COOLDOWN_CAP` and `recentSpawnAttempts`, state that this is "the SAME
   `recentSpawnAttempts`-scanning cap REQ-102's own reconciled Cooldown Check applies," and closes by
   pointing at the new PROP-305g ("fewer than the cap → still eligible; the cap reached →
   rate-limited") for the exact boundary fixture.

### Edits made — `specs/verification-architecture.md`

1. **Header revision line** (line 5) and its extended parenthetical (lines 5-18, new): bumped
   `iteration 11` → `iteration 12`, prepending a paragraph mirroring `behavioral-spec.md`'s header
   addition, so both spec files' own revision headers stay in sync.

2. **Purity Boundary Map row** for `decideColonySpawn` (**line 100**): the pinned signature was
   corrected from `{colonySurplusUsd, spawnThresholdUsd, lastSpawnAttemptMs, nowMs, cooldownDays,
   childrenProvisioning, maxConcurrentSpawns}` to `{colonySurplusUsd, spawnThresholdUsd,
   recentSpawnAttempts, nowMs, cooldownDays, failureCooldownCap, childrenProvisioning,
   maxConcurrentSpawns}`, with a new "**Corrected, resolves FIND-1101 (critical)**" sentence in the
   Notes column explaining the correction and citing the reconciled rule.

3. **Proof Obligations table**:
   - **PROP-102b** (**line 243**) corrected: description now states the cooldown gate holds "for
     EITHER cooldown trigger (a success in-window, OR the failure-cap reached in-window)"; the test
     column now specifies TWO fixtures against `recentSpawnAttempts` (one `outcome:"success"` entry →
     unconditional `rate_limited`; `failureCooldownCap` `outcome:"failure"` entries with zero
     successes → `rate_limited` identically), explicitly cross-referencing PROP-305c/PROP-305g as
     proving the SAME reconciled logic from the other side.
   - **PROP-305c** (**line 308**) corrected: description now states this is "the IDENTICAL reconciled
     rule REQ-102's own Cooldown Check applies... no longer a competing behavior from PROP-102b's"; the
     test column now uses `recentSpawnAttempts` with exactly 3 `outcome:"failure"` entries (zero
     successes) rather than an undefined "3 injected failures" against a scalar.
   - **New row PROP-305g** (**line 312**, inserted immediately after the existing PROP-305f row):
     Tier 1, Required `true`. Description: "The EXACT `FAILURE_COOLDOWN_CAP` boundary... STRICTLY
     FEWER than `FAILURE_COOLDOWN_CAP` failed attempts... does NOT trigger cooldown; the MOMENT the cap
     is reached, cooldown applies." Test column: two fixtures — (a) exactly 2 failures, zero
     successes → `eligible:true`; (b) the same fixture plus one more failure (now exactly 3) →
     `eligible:false, reason:"rate_limited"` — this is the literal "3 failures reached, cooldown now
     applies" boundary fixture the finding requested, distinct from PROP-305c's own "3 failures, then a
     4th attempt" fixture.

4. **Verification Strategy — Tier 1 list**: two clauses updated — "REQ-102's gate (PROP-102a-e...)" at
   **lines 382-384** now adds "PROP-102b corrected to test the reconciled success-vs-failure-cap
   cooldown rule, resolves FIND-1101"; "REQ-305's cooldown-cap check (PROP-305c)..." at **lines
   397-402** now reads "AND its multi-citizen co-funding SUCCESS-path check (PROP-304f...)... REQ-305's
   cooldown-cap check (PROP-305c, corrected resolves FIND-1101) AND its exact-boundary check
   (PROP-305g, new, resolves FIND-1101)".

5. **Gate section, item (1)** (**lines 490-496**): "the cooldown check is never bypassed by surplus
   size (PROP-102b)" is extended to "...for EITHER cooldown trigger — a success in-window, or the
   `FAILURE_COOLDOWN_CAP` reached in-window (PROP-102b, corrected, resolves FIND-1101 — the adversary
   confirms `decideColonySpawn`'s `recentSpawnAttempts` array-scan implements the SAME reconciled rule
   REQ-102's own EARS clause and REQ-305's failure-cap edge case both now describe, never two competing
   behaviors)".

6. **Gate section, item (8)** (**lines 654-659**): "that the failed-attempt cooldown-cap closes the
   'engineer repeated failures to bypass cooldown' gap (PROP-305c)" is extended with "corrected,
   resolves FIND-1101 — confirmed to be the IDENTICAL reconciled rule REQ-102's own PROP-102b tests
   from the success side, never two different behaviors" and a new clause requiring the adversary
   confirm the EXACT boundary via PROP-305g.

---

## FIND-1102 (major) — REQ-304 multi-citizen co-funding SUCCESS path untested

**Root cause confirmed**: REQ-304's own edge case (originally lines 1743-1749) already specifies, as
real supported behavior, that a spawn CAN proceed via two separate sequential single-signer transfers
from two different citizens when no single citizen alone has enough surplus. Re-reading
`verification-architecture.md`'s Proof Obligations table confirmed PROP-304a/b/c/d/e cover: no
human-funded source (PROP-304a), a per-transfer ceiling (PROP-304b), the BLOCKED path when no single
citizen suffices AND co-funding isn't available (PROP-304c), the Akash multi-hop bridge route
(PROP-304d), and the Base-native Skip-API entry point (PROP-304e) — none of these exercise the
multi-citizen co-funding SUCCESS path at all. A test suite passing every existing PROP-304 obligation
would pass even if multi-citizen co-funding were entirely unimplemented.

### Edits made — `specs/behavioral-spec.md`

1. **REQ-304 Acceptance Criteria** (originally ending at line 1762, now **lines 1828-1839**, new
   bullet added after the existing FIND-502 bullet): states the reconciled co-funding SUCCESS
   criterion explicitly — citizen A's partial transfer followed SEQUENTIALLY by citizen B's remaining
   transfer to the SAME child wallet must both complete, the child wallet's final balance must equal
   the FULL required funding amount, and both transfers must be independently traceable in the funding
   ledger (each carrying its own paying citizen's identity). Also adds one clarifying sentence closing
   an ambiguity the finding's own evidence raised: the per-transfer ceiling check applies to EACH
   citizen's own transfer against THAT citizen's own certified contribution, never a single combined
   ceiling checked against the whole aggregate for one citizen's individual transfer (this was
   necessary to make the new PROP-304f's fixture well-defined and unambiguous).

### Edits made — `specs/verification-architecture.md`

1. **Proof Obligations table** — new row **PROP-304f** (**line 305**, inserted immediately after the
   existing PROP-304e row, before PROP-305a): Tier `1/2`, Required `true`. Description: "Multi-citizen
   SEQUENTIAL co-funding SUCCESS path... distinct from PROP-304c's blocked/no-op path, which never
   exercises a successful multi-citizen fund-up." Test column: concrete fixture — citizen A
   surplus-above-reserve `$6`, citizen B surplus-above-reserve `$5`, deploy cost `$10` (neither alone
   sufficient, aggregate sufficient) → citizen A transfers `$6`, citizen B transfers the remaining `$4`
   sequentially to the SAME child wallet → assert final child-wallet balance equals exactly `$10`,
   assert the spawn proceeds (child ledger row created, never blocked), and assert BOTH transfers are
   independently traceable in the funding ledger — never a single combined/anonymous entry. This is the
   literal fixture the finding requested, and is explicitly distinguished from PROP-304c's own
   insufficient-funds/no-op fixture.

2. **Verification Strategy — Tier 1 list** (**lines 397-401**): "REQ-304's amount-ceiling and
   individual-insufficiency checks (PROP-304b/c)" now adds "AND its multi-citizen co-funding
   SUCCESS-path check (PROP-304f, unit half, resolves FIND-1102, distinct from PROP-304c's blocked/
   no-op path)".

3. **Verification Strategy — Tier 2 list** (**lines 449-451**): a new clause inserted immediately after
   "REQ-303's shelter-cost-ledger feedback check (PROP-303c);" and before the REQ-305 clauses: "REQ-304's
   multi-citizen sequential co-funding SUCCESS-path integration check (PROP-304f, integration half,
   resolves FIND-1102, distinct from PROP-304c's blocked/no-op path)".

4. **Gate section, item (7)** (item spans **lines 633-650**; the new clause is at **lines 645-650**):
   appended after the existing PROP-304e confirmation: "AND that the multi-citizen SEQUENTIAL
   co-funding SUCCESS path... is proven to actually SUCCEED, not merely that the insufficient-funds
   case is blocked (PROP-304f, resolves FIND-1102, distinct from PROP-304c)."

---

## New proof-obligation IDs introduced (PROP-XXX-lettersuffix convention preserved)

| ID | REQ | Tier | Resolves |
|---|---|---|---|
| PROP-304f | REQ-304 | 1/2 | FIND-1102 (major) — multi-citizen sequential co-funding SUCCESS-path fixture (distinct from PROP-304c's blocked/no-op path) |
| PROP-305g | REQ-305 | 1 | FIND-1101 (critical) — exact `FAILURE_COOLDOWN_CAP` boundary fixture (2 failures → still eligible; 3 failures → rate-limited) |

## Corrected (pre-existing) proof obligations

| ID | REQ | Change |
|---|---|---|
| PROP-102b | REQ-102 | Now tests the reconciled rule from BOTH sides (success in-window; failure-cap reached in-window), against `recentSpawnAttempts` instead of the removed `lastSpawnAttemptMs` |
| PROP-305c | REQ-305 | Now explicitly stated as the IDENTICAL rule PROP-102b tests, against `recentSpawnAttempts` instead of an undefined scalar-based "3 injected failures" |

## Markdown table integrity check performed

After editing, both spec files' markdown tables (`| FIND-... |` changelog rows, `| PROP-... |` proof
obligation rows, `| **...** |` Purity Boundary Map rows) were checked for a uniform pipe-split field
count matching their unedited neighbor rows (PROP-304f/PROP-305g both split into 8 fields, matching
PROP-304e/PROP-305f exactly; the corrected PROP-102b/PROP-305c rows retained the same 8-field split as
before editing). All new prose introducing the literal union type `"success"|"failure"` was written
either outside table rows (REQ-102/REQ-305 prose in `behavioral-spec.md`, which is not tabular) or,
inside table rows, was written as two separate literals (`outcome:"success"`, `outcome:"failure"`)
rather than the piped union form, so no table row was accidentally split into a phantom extra column.

## Not changed

- `state.json`, reviews manifest/verdict files — untouched, per instructions.
- No `git add`/`commit`/`push` performed.
- No other findings, requirements, or proof obligations were touched beyond what FIND-1101/FIND-1102
  required — REQ-101, REQ-103, REQ-105, REQ-106, REQ-201 through REQ-306 (aside from the one new
  REQ-304 Acceptance Criteria bullet), and REQ-401 through REQ-403, are otherwise byte-identical to the
  pre-iteration-12 state.
