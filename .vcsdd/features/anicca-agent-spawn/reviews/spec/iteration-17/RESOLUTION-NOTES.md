# Resolution Notes — spec review iteration-17 (FIND-1601 + mandated exhaustive full-parameter sweep)

**Feature**: anicca-agent-spawn · **Result**: FIND-1601 resolved (both halves), plus one additional
sibling gap found and resolved during a genuinely exhaustive, checklist-driven full-parameter sweep;
`behavioral-spec.md` and `verification-architecture.md` bumped to **revision: iteration 17**.

---

## FIND-1601 (critical) — `needsSolanaWallet({initialSkills, deployTarget})` gains real binding rules for both inputs

### (a) `deployTarget`

**Problem**: `needsSolanaWallet`'s `deployTarget` argument conceptually means "the cloud target selected
for this spawn attempt," but no requirement anywhere stated that this value is bound to THAT SAME
attempt's `selectCloudTarget(...)` (REQ-306) real return value. REQ-302's own EARS clause is explicit
that the Nosana deploy step provisions the child's compute "pointed at the child's OWN pre-generated,
isolated Solana keypair (REQ-202)" — i.e. REQ-302 structurally REQUIRES REQ-202 to have already
generated a Solana wallet whenever Nosana is the real selected target for that attempt. A hand-assembled
or stale `deployTarget` (e.g. read from an earlier evaluation, or guessed) that diverges from
`selectCloudTarget`'s real, same-attempt output would either (i) skip Solana keygen for a child that
REQ-302 needs it for — a hard, deploy-breaking failure of the entire Nosana path — or (ii) waste a real,
billable Solana keygen for a child that never uses it. This is the IDENTICAL "never hand-assembled,
always the direct return value of X()" failure class FIND-1401/FIND-1501 already closed for
`recentSpawnAttempts`/`deriveRecentSpawnAttempts` and `childrenProvisioning`/`countChildrenProvisioning`.

**Resolution**: REQ-202's own text now states explicitly: `deployTarget` is never hand-assembled by the
calling orchestration — it is ALWAYS the DIRECT return value of THAT SAME spawn attempt's
`selectCloudTarget({nosanaAvailable, nosanaPriceUsd, akashAvailable, akashPriceUsd})` call, never a
stale/earlier attempt's evaluation. A new proof obligation, **PROP-202d** (Tier 1/2, mirroring
PROP-102g/PROP-102i's own real-derivation discipline), requires a control-flow read confirming the
caller passes `selectCloudTarget(...)`'s return value directly, plus an integration test proving a
specific attempt's `deployTarget` matches THAT SAME attempt's `selectCloudTarget` output (never an
earlier/different attempt's). The Purity Boundary Map gains a dedicated `needsSolanaWallet` row (it had
none before, despite already having three proof obligations — itself part of the fix), and the Gate's
item (4) — which never once cited ANY of REQ-202's own proof obligations at all — now requires
PROP-202a/b/d.

### (b) `initialSkills`

**Problem**: `initialSkills` had NO specified source anywhere in either spec document — not a fixed
default, not a derivation from another named function, not an explicit agent-judgment carve-out.

**Design decision (made per the dispatch's own instruction to decide using my own judgment, grounded in
this spec's existing patterns)**: I read REQ-104's own existing agent-judgment carve-out
(`behavioral-spec.md`, REQ-104: "*what the child's initial goal framing/prompt should say*" is
explicitly named as the agent's own in-envelope choice, distinct from REQ-104's bookkeeping-only
eligibility arithmetic) and REQ-201-205 in full, plus this project's own governing rule
(`~/.claude/rules/building-effective-ai-agents.md`, HARD RULE #1/#2, already cited inline by REQ-104:
"deterministic code owns arithmetic/bookkeeping; the agent owns everything that is genuinely a
decision"). I evaluated the three options the dispatch posed:

- **(i) Fixed literal default** — rejected. A child's starting capabilities are a genuinely variable,
  strategic choice (unlike `generation`/`constitutionHash`, which are structural/identity facts, not
  strategy), and hardcoding it would contradict this project's own repeated "skills give a TOOL, never a
  hardcoded DECISION" discipline (mirrored elsewhere in this codebase's own memory:
  `feedback_skills_give_tool_not_decision`) and REQ-401's own edge case, which explicitly refuses to let
  this feature hardcode a forced choice in an analogous situation ("THIS IS NOT a defect to be worked
  around by this feature hardcoding a forced selection... doing so would violate this project's HARD
  RULE that judgment/selection belongs to the model").
- **(ii) Parent-inherited (copied from the driving citizen's own current skill roster)** — rejected. This
  IS deterministic and avoids ambiguity, but it would make every spawned child structurally identical in
  capability to its parent, directly at odds with this feature's own stated purpose (`Scope of this
  increment`: "the colony can create a brand-new citizen from its own accumulated surplus... and that
  the new citizen can earn its own keep" — implying a citizen that can pursue its OWN strategy, not a
  clone).
- **(iii) Explicit agent-judgment choice, extending REQ-104's existing carve-out** — **selected**. This
  is the option most consistent with the spec's own already-established architecture: REQ-104 ALREADY
  grants the spawning agent the in-envelope choice of the child's own goal framing/prompt; deciding what
  capabilities a new colony member starts with is the SAME kind of decision, made at the SAME point, by
  the SAME agent, for the SAME reason (a new citizen should be free to pursue its own earning strategy).
  `needsSolanaWallet` itself REMAINS a pure, deterministic bookkeeping function given this input (it is
  not itself making a judgment — it deterministically checks whether the agent-chosen skill list
  contains a Solana-settled capability) — only the SOURCE of `initialSkills` is an agent choice, exactly
  mirroring how `deployTarget`'s source is a deterministic function's real output. This also does not
  conflict with REQ-104's own bookkeeping-only mandate, which is explicitly scoped ONLY to the
  REQ-101/102/103 spawn-ELIGIBILITY decision, never to REQ-202's downstream child-provisioning details.

**Resolution**: REQ-104's existing carve-out sentence is extended to explicitly name `initialSkills`
alongside "goal framing/prompt" as the SAME in-envelope agent choice. REQ-202's own text now states
`initialSkills` is never hardcoded/defaulted inside REQ-202's own orchestration — it is always the SAME
value the spawning agent already chose, identical to the value used for the child's own goal
framing/prompt. A new proof obligation, **PROP-202e** (Tier 0, structural — agent-choice inputs are not
unit-testable against a "correct" fixture value the way a deterministic derivation is; only that the
value is never hardcoded and is genuinely the agent's real choice), is added, mirroring REQ-104's own
PROP-104a structural-check style. The Gate's item (4) now requires this too.

### `specs/behavioral-spec.md` edits

| Location | Change |
|---|---|
| Revision header (top of file) | Bumped `iteration 16` → `iteration 17`; new lead paragraph describing both halves of the FIND-1601 fix AND the sweep-found `filterProductiveCitizens` gap (below), prior iteration-16 content preserved as a subordinate `— AND spec review iteration-16 finding FIND-1501 resolved —` clause, following the exact chaining pattern every prior revision bump uses. |
| New `## Changelog (iteration 17 spec review → iteration 18)` section (inserted immediately after the existing `## Changelog (iteration 15 spec review → iteration 16)` section, before `## Scope of this increment (read first)`) | Added, with a `\| Finding \| Severity \| Resolution \|` table containing one row for FIND-1601 (both halves) and one row for the preemptively-resolved sweep-found gap (no new FIND number, not independently raised by the adversary). |
| REQ-101, new paragraph **"Deriving `filterProductiveCitizens`'s inputs from real system state"** inserted immediately after `filterProductiveCitizens`'s signature sentence (step 2), before the existing "`ledgerRows` may legitimately contain MULTIPLE rows..." paragraph | States `ledgerRows`/`citizens` are never hand-assembled — always `readChildren(...)`'s real output / a real `CITIZENS_REGISTRY_PATH` read — and that `computeColonySurplusUsd`/`readCitizenBalances` both receive the SAME filtered array. |
| REQ-101 Acceptance Criteria, new bullet inserted immediately after the `filterProductiveCitizens` bullet | "**(new, resolves the sweep-found sibling gap alongside FIND-1601)** `filterProductiveCitizens`'s `ledgerRows` argument is never hand-assembled..." |
| REQ-104, existing carve-out sentence | Extended to explicitly name `initialSkills` as the same in-envelope agent choice as goal framing/prompt (resolves FIND-1601(b)). |
| REQ-202, new paragraph **"Deriving `needsSolanaWallet`'s inputs from real system state"** inserted immediately after the EARS clause, before "**Edge Cases**" | Full binding rule for both `deployTarget` (bound to `selectCloudTarget(...)`'s same-attempt output) and `initialSkills` (bound to the spawning agent's REQ-104 choice). |
| REQ-202 Acceptance Criteria | Two new bullets added for the `deployTarget`/`initialSkills` bindings. |

### `specs/verification-architecture.md` edits

| Location | Change |
|---|---|
| Revision header (top of file) | Bumped `iteration 16` → `iteration 17`; condensed lead paragraph covering both FIND-1601 halves and the sweep-found gap. |
| Purity Boundary Map — `filterProductiveCitizens` row | Extended with the new `ledgerRows`/`citizens` real-derivation binding sentence, citing PROP-101j. |
| Purity Boundary Map — new row **`needsSolanaWallet`** (inserted directly after the `selectCloudTarget` row) | Added — this function had NO row at all before this fix, despite already having three proof obligations (PROP-202a/b/c). Documents both the `deployTarget`/`initialSkills` bindings and cites PROP-202d/e. |
| Proof Obligations table — new row **PROP-101j** (inserted directly after PROP-101i, before PROP-102a) | Real-derivation integration check for `filterProductiveCitizens`'s `ledgerRows`/`citizens` arguments. |
| Proof Obligations table — new rows **PROP-202d**, **PROP-202e** (inserted directly after PROP-202c, before PROP-203a) | `deployTarget` real-derivation check (Tier 1/2) and `initialSkills` non-hardcoding structural check (Tier 0). |
| Verification tiers narrative — Tier 0 list | New clause citing PROP-202e. |
| Verification tiers narrative — Tier 2 list | New clauses citing PROP-101j and PROP-202d. |
| Verification Strategy — Tier 0 list | New clause citing PROP-202e. |
| Verification Strategy — Tier 2 list | New clauses citing PROP-101j and PROP-202d. |
| Gate — item (1b) | Extended with the `filterProductiveCitizens`/`readCitizenBalances` real-derivation binding requirement (PROP-101j). |
| Gate — item (4) | Extended — previously never cited ANY of REQ-202's own proof obligations; now requires PROP-202a/b/d/e. |

---

## Methodology for the mandated exhaustive sweep

Per the dispatch's explicit instruction (a checklist, not another free-form re-read, since three
consecutive prior sweeps — iterations 15, 16, and this iteration's own adversary pass — each still
missed at least one sibling instance), I built an explicit table, one row per (function, parameter) pair,
for every pure function listed in `verification-architecture.md`'s Purity Boundary Map (re-read in full,
line by line, rather than working from memory of what prior iterations already fixed), classifying each
parameter as exactly one of **CONSTANT**, **DERIVED-BOUND**, **AGENT-CHOICE**, or **UNRESOLVED**:

| Function | Parameter | Classification | Basis |
|---|---|---|---|
| `isSelfFunded`/`selfFundedReasons` (existing, reused) | `{wallet, fuel, humanDependencies}` sub-object | DERIVED-BOUND | REQ-101 §1: explicitly the sub-object of each citizen record read from REQ-105's registry |
| `computeColonySurplusUsd` | `citizens` | DERIVED-BOUND | REQ-101: "runs ONLY on `filterProductiveCitizens`'s OUTPUT"; now further pinned by the new binding paragraph |
| `computeColonySurplusUsd` | `perCitizenReserveUsd` | CONSTANT | Defaults `5.00`, cites `economy/ubi/run.sh`'s `RESERVE = 5.0` |
| `computePerCitizenSurplusUsd` | `citizens` | DERIVED-BOUND | Same `filterProductiveCitizens`-filtered input as `computeColonySurplusUsd` (REQ-101 explicit) |
| `computePerCitizenSurplusUsd` | `perCitizenReserveUsd` | CONSTANT | Same as above |
| `filterProductiveCitizens` | `citizens` | **was UNRESOLVED → now DERIVED-BOUND (fixed this iteration)** | No prior "never hand-assembled" phrase existed for this argument, despite `deriveRecentSpawnAttempts`/`countChildrenProvisioning` (this function's own cited siblings/precedent) both having one; now added, binding it to a real `CITIZENS_REGISTRY_PATH` read |
| `filterProductiveCitizens` | `ledgerRows` | **was UNRESOLVED → now DERIVED-BOUND (fixed this iteration)** | No prior "never hand-assembled" phrase existed; PROP-102g's own citation claiming to "mirror PROP-101d/PROP-101e's own real-derivation discipline" for this function did not actually hold (PROP-101d/e are fixture-only Tier-1/2 correctness tests of the function's OWN logic, never a real-orchestration binding check); now bound explicitly to `readChildren(...)`'s real output, with new PROP-101j closing the verification gap |
| `filterProductiveCitizens` | `nowMs` | CONSTANT (ambient clock) | Real-time value, not derived from another pure function's output; same treatment as every other `nowMs` parameter in this spec |
| `filterProductiveCitizens` | `bootstrapWindowDays` | CONSTANT | `BOOTSTRAP_WINDOW_DAYS`, default `14`, identical-by-construction to `SPAWN_COOLDOWN_DAYS` (FIND-1301/PROP-402e) |
| `deriveRecentSpawnAttempts` | `ledgerRows` | DERIVED-BOUND | FIND-1401, already resolved — bound to `readChildren(...)` |
| `countChildrenProvisioning` | `ledgerRows` | DERIVED-BOUND | FIND-1501, already resolved — bound to `readChildren(...)` |
| `deriveMeasuredShelterCostUsd` | `shelterCostLedgerRows` | DERIVED-BOUND | Explicitly inline-bound: `deriveMeasuredShelterCostUsd({shelterCostLedgerRows: readShelterCostEntries(...)})` (REQ-102/REQ-303 text) |
| `decideColonySpawn` | `colonySurplusUsd` | DERIVED-BOUND | REQ-102 EARS clause: "WHEN REQ-101's colony surplus is computed" — ties directly to `computeColonySurplusUsd` |
| `decideColonySpawn` | `spawnThresholdUsd` | DERIVED-BOUND | Fully specified formula, `MIN_SHELTER_USD * SAFETY_MARGIN_MULTIPLIER`, itself fed by `deriveMeasuredShelterCostUsd` |
| `decideColonySpawn` | `recentSpawnAttempts` | DERIVED-BOUND | FIND-1401, resolved |
| `decideColonySpawn` | `nowMs` | CONSTANT (ambient clock) | As above |
| `decideColonySpawn` | `cooldownDays` | CONSTANT | `SPAWN_COOLDOWN_DAYS`, default `14` (FIND-1301, resolved) |
| `decideColonySpawn` | `failureCooldownCap` | CONSTANT | `FAILURE_COOLDOWN_CAP`, default `3` |
| `decideColonySpawn` | `childrenProvisioning` | DERIVED-BOUND | FIND-1501, resolved |
| `decideColonySpawn` | `maxConcurrentSpawns` | CONSTANT | `MAX_CONCURRENT_SPAWNS`, default `1` |
| `buildChildSpec` (existing, extended) | `childInbox` / `agentEvmAddress`+`agentId` | DERIVED-BOUND | REQ-206: `agentEvmAddress` = REQ-201's generated wallet; `agentId` = `ensureAgentId`/REQ-204's returned ID |
| `buildChildSpec` | `parentWallet` | DERIVED-BOUND | REQ-206: REQ-106's coordinator-host citizen's own wallet |
| `buildChildSpec` | `generation` | CONSTANT | Fixed `1` (FIND-204, resolved) |
| `buildChildSpec` | `seedUsdc` | DERIVED-BOUND | Aliased to REQ-204's gas-seed amount, identical-by-construction (PROP-206g) |
| `buildChildSpec` | `constitutionHash` | CONSTANT | Fixed SHA-256 of `identity/genesis.md` |
| `isLockStale` (existing, reused) | `nowMs`, `mtimeMs`, `staleMs` | CONSTANT (ambient/effectful leaves) | Pre-existing, adversary-hardened upstream (`anicca-agent-economy` REQ-101); out of this feature's own scope |
| `selectCloudTarget` | `nosanaAvailable`/`nosanaPriceUsd`/`akashAvailable`/`akashPriceUsd` | CONSTANT (effectful leaves) | Raw effectful price/availability query results — the PRIMARY I/O source itself, not derived from any OTHER named pure function in this spec (same treatment as `computeSpawnGate`'s `balanceAkt` and every other raw on-chain/API read in this spec) |
| `readCitizenBalances` | `citizens` | DERIVED-BOUND | Now explicitly clarified (new binding paragraph): the SAME `filterProductiveCitizens`-filtered array `computeColonySurplusUsd` also receives |
| `resolveEvmPrivateKey`/`resolveSolanaSecret` (existing, reused) | `home`, `env` | DERIVED-BOUND | REQ-403: `homeDir` from REQ-105's registry, `env.HOME` = the canonical `COORDINATOR_HOME` constant (FIND-501/603/701/802, all resolved) |
| `ensureAgentId` (existing, reused) | `privateKey`, `cacheFile` | DERIVED-BOUND | REQ-204: `privateKey` = REQ-201's generated key; `cacheFile` = the child's own isolated `$HOME`-based path |
| `computeSpawnGate` (existing, reused) | `balanceAkt` | CONSTANT (effectful leaf) | Raw on-chain balance query result — the primary I/O source, not derived from another named pure function (same class as `selectCloudTarget`'s own inputs) |
| `computeSpawnGate` | `costAkt`, `bufferAkt` | CONSTANT | Explicitly bound to `spawn-child/config.json`'s real `spawn_cost_akt: 25`/`buffer_akt: 1` values |
| `needsSolanaWallet` | `deployTarget` | **was UNRESOLVED → now DERIVED-BOUND (FIND-1601(a), fixed this iteration)** | Bound to THAT SAME attempt's `selectCloudTarget(...)` (REQ-306) return value |
| `needsSolanaWallet` | `initialSkills` | **was UNRESOLVED → now AGENT-CHOICE (FIND-1601(b), fixed this iteration)** | Extended REQ-104's existing agent-judgment carve-out to explicitly cover this choice (see design decision above) |

**Result of the sweep**: exactly **one** additional UNRESOLVED instance was found beyond the two named
in FIND-1601 — `filterProductiveCitizens`'s `citizens`/`ledgerRows` arguments (counted as a single
finding since both parameters of the SAME function were fixed together, in the SAME resolution). No
other row in this table was UNRESOLVED. All CONSTANT rows have an explicit, cited default value already
stated in the spec; all DERIVED-BOUND rows now have an explicit "never hand-assembled, always the direct
return value of a named function" statement (after this iteration's fixes); the one AGENT-CHOICE row is
grounded in REQ-104's own existing, pre-established carve-out, extended by explicit design decision
rather than left implicit.

I also directly applied the reviewer's own suggested secondary check (searching for conceptual
cross-references — "the selected cloud target," "the certified amount," "the resolved balance" — that
might resolve to something other than a named function): every such phrase in both spec documents
resolves cleanly to an explicitly-named function (`selectCloudTarget`, `computePerCitizenSurplusUsd`,
`readCitizenBalances` respectively) — no further hidden instance was found via this secondary method.

---

## Additional gap found during the mandated sweep (preemptive fix, no independent FIND-16xx number)

**Problem**: REQ-101's own `filterProductiveCitizens({citizens, ledgerRows, nowMs,
bootstrapWindowDays})` — the very function FIND-1401's and FIND-1501's own prior resolutions repeatedly
cited as the established PRECEDENT this binding discipline was modeled on ("unlike REQ-101's exactly
analogous need, satisfied by a named, fully-specified pure join function, `filterProductiveCitizens`")
— never itself stated the identical "never hand-assembled, always the real function's direct return
value" rule for its OWN `ledgerRows` (`ledger.js::readChildren()`'s real output) or `citizens` (a real
`CITIZENS_REGISTRY_PATH` read) arguments. Worse, `PROP-102g`'s own citation, which claims to "mirror
PROP-101d/PROP-101e's own real-derivation discipline for `filterProductiveCitizens`/
`readCitizenBalances`," does not actually hold up under a fresh, skeptical re-read: PROP-101d is a
Tier-1 fixture test of `filterProductiveCitizens`'s OWN internal correctness given already-supplied
fixture inputs (never a check that real orchestration binds its inputs to `readChildren()`/a registry
read rather than a hand-rolled reimplementation), and PROP-101e is a Tier-2 test of
`readCitizenBalances`'s OWN internal correctness (that it queries public RPC, not a local file — again,
never a real-orchestration binding check). This is the IDENTICAL failure class as FIND-1401/1501/1601,
found on the function this spec's own text had been treating as the ALREADY-SOLVED reference case.

**Resolution**: Added the identical explicit "never hand-assembled" binding sentence REQ-102 already
uses for `recentSpawnAttempts`/`childrenProvisioning` to REQ-101's own text, for
`filterProductiveCitizens`'s `ledgerRows` (bound to `ledger.js::readChildren()`'s real output) and
`citizens` (bound to a real `CITIZENS_REGISTRY_PATH` read) arguments — and, by the same reasoning, noted
that `readCitizenBalances`'s own `citizens` argument (and `computeColonySurplusUsd`'s own `citizens`
argument) are BOTH, in turn, this SAME filtered array, passed through unchanged, never independently
re-read or re-derived. A new proof obligation, **PROP-101j** (Tier 1/2, mirroring PROP-102g/PROP-102i
exactly), closes the missing verification coverage.

This closes the **fifth** instance of this recurring failure class found across iterations 14-17
(FIND-1401 → FIND-1501 → FIND-1501's own sweep-found sibling → FIND-1601(a) → FIND-1601(b) →
`filterProductiveCitizens`'s own gap) — confirming this iteration's own convergence note's suspicion that
the pattern was never about specific parameters, but a systemic documentation gap that required a
genuinely different (checklist-based, not free-form) review methodology to fully close.

---

## Note on revision numbering

Confirmed by direct read of both spec files' revision headers at the start of this task: the on-disk
revision was **iteration 16** (produced by the prior task's resolution of FIND-1501, per
`reviews/spec/iteration-16/RESOLUTION-NOTES.md`'s own numbering note). This task's dispatch was for
`reviews/spec/iteration-17/`'s `verdict.json`, which reviewed that revision-16 spec and raised FIND-1601
plus the mandated exhaustive-sweep instruction. Following the SAME convention iteration-16's own note
established (review round directory `iteration-N` reviews the spec at revision `N-1` and, once resolved,
the spec is bumped to revision `N`), this task resolves `reviews/spec/iteration-17/`'s finding against a
spec that was at revision 16, so the spec is bumped to revision **17** — consistent with the task list's
own next item, "P3 spawn spec iteration-18待ち", i.e. the NEXT review round (directory `iteration-18`)
will review this now-produced revision 17. No `state.json`/review-manifest files were touched by this
task per its own instructions, so the orchestrator can advance `state.json` and create the `iteration-18`
review directory separately.

---

## Verification of internal consistency (post-edit)

- Grep-confirmed `PROP-101j`, `PROP-202d`, and `PROP-202e` each appear exactly once as a table-row
  definition in `verification-architecture.md`'s Proof Obligations table (no ID collisions with any
  existing `PROP-101*`/`PROP-202*` row), correctly ordered (`PROP-101j` after `PROP-101i`, before
  `PROP-102a`; `PROP-202d`/`PROP-202e` after `PROP-202c`, before `PROP-203a`).
- `FIND-1601` referenced consistently across both spec files (10 occurrences in `behavioral-spec.md`, 14
  in `verification-architecture.md`).
- `needsSolanaWallet` now has a dedicated Purity Boundary Map row (it had none before this fix, despite
  three pre-existing proof obligations, PROP-202a/b/c) — confirmed by direct re-read of the full Purity
  Boundary Map table after the edit.
- Gate item (4) confirmed to now cite PROP-202a/b/d/e (previously cited NONE of REQ-202's own proof
  obligations at all — confirmed by direct re-read of the pre-edit text before making this change).
  Gate item (1b) confirmed extended with the `filterProductiveCitizens`/`readCitizenBalances`
  real-derivation clause (PROP-101j).
- Confirmed the fix does NOT modify `~/anicca/skills/self/spawn/lib/child-spec.js` or `ledger.js` (no
  edits touched either file description) — this is purely an additive spec-text extension (new binding
  sentences + three new proof obligations + one new Purity Boundary Map row), consistent with the
  discipline every prior FIND-14xx/15xx fix in this document already established.
- No edits were made to `state.json`, review manifest/verdict files, or the `iteration-18` review
  directory — those remain the orchestrator's responsibility per this task's own instructions. No
  commit/push was performed.
