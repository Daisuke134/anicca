# Resolution Notes — spec review iteration-16 (FIND-1501 + mandated full-spec sweep)

**Feature**: anicca-agent-spawn · **Result**: finding resolved, plus one additional sibling gap found
and resolved during the mandated sweep; `behavioral-spec.md` and `verification-architecture.md` bumped
to **revision: iteration 16**.

---

## FIND-1501 (critical) — `childrenProvisioning` gains a real, cited derivation from `ledger.js`'s rows

**Problem**: `decideColonySpawn`'s pinned `childrenProvisioning` input — a SIBLING parameter to
`recentSpawnAttempts` in the EXACT SAME function signature (`behavioral-spec.md:758-760`) — had no
specified derivation from `ledger.js`'s real, append-only, duplicate-`child_id`-containing rows: the
identical failure class FIND-1401 (iteration 15) had just fixed for its neighbor, left unaddressed for
this sibling. Two concrete hazards, both confirmed against the real, current source (`ledger.js`,
`run.sh`'s own provisioning-row-then-status-row pattern already cited at `behavioral-spec.md:472-475`):

1. A naive per-row scan (rather than a last-write-wins reduction first) could double-count, or worse,
   PERMANENTLY count a child whose stale `"provisioning"` row was later superseded by
   `"active"`/`"failed"` — silently and permanently blocking all future spawns forever once even one
   child has ever spawned (`childrenProvisioning >= maxConcurrentSpawns` staying true forever).
2. It was unclear whether a child whose LAST row is `"bootstrap_failed"` (REQ-402) should still count as
   "in provisioning" (a naive scan might still find its earlier `"provisioning"` row and wrongly count
   it), mirroring FIND-1401's own bootstrap_failed ambiguity for its sibling.

**Resolution**: A new sibling pure function, same file as `filterProductiveCitizens`/
`deriveRecentSpawnAttempts`, `~/anicca/skills/self/spawn/lib/treasury-gate.mjs::
countChildrenProvisioning({ledgerRows}) → number`, groups `ledgerRows` by `child_id`, reduces each group
to its last-appended row (last-write-wins — the SAME discipline already established), and counts
EXACTLY the groups whose last row's `status` is EXACTLY `"provisioning"` — a group whose last row is
`"active"`, `"failed"`, or `"bootstrap_failed"` is NEVER counted, regardless of whether an earlier
`"provisioning"` row exists for that same `child_id`. REQ-102's real orchestration now calls this
function directly over `readChildren`'s real output, never a hand-rolled reimplementation at the call
site, mirroring `deriveRecentSpawnAttempts`'s own integration discipline. Two new proof obligations:
PROP-102h (Tier 1, the four-case unit fixture: only-`"provisioning"` row → counted;
`"provisioning"`→`"active"` → NOT counted; `"provisioning"`→`"failed"` → NOT counted;
`"provisioning"`→`"active"`→`"bootstrap_failed"` → NOT counted) and PROP-102i (Tier 1/2, the
real-derivation integration discipline, mirroring PROP-102g).

### `specs/behavioral-spec.md` edits

| Location | Change |
|---|---|
| Revision header (top of file) | Bumped `iteration 15` → `iteration 16`; new lead paragraph describing the FIND-1501 fix AND the sweep-found gap (below), prior iteration-14→15 (FIND-1401) content preserved as a subordinate `— AND spec review iteration-14 finding FIND-1401 resolved —` clause, following the exact chaining pattern every prior revision bump uses. |
| New `## Changelog (iteration 15 spec review → iteration 16)` section (inserted immediately after the existing `## Changelog (iteration 14 spec review → iteration 15)` section, before `## Scope of this increment (read first)`) | Added, with a `\| Finding \| Severity \| Resolution \|` table containing one row for FIND-1501 and one row for the preemptively-resolved sweep-found gap (no FIND-15xx number assigned to the latter per the dispatch's own instruction, since it was not independently raised by the adversary this round). |
| REQ-102's Cooldown Check, new paragraph **"Deriving `childrenProvisioning` from real ledger rows (new, resolves FIND-1501, critical)"** inserted immediately after the existing "Deriving `recentSpawnAttempts`..." paragraph (step 4), before the `SPAWN_THRESHOLD_USD = ...` bullet block | Fully defines `countChildrenProvisioning({ledgerRows})`'s 4-step derivation rule (group by `child_id` → reduce to last-appended row → count exactly the `"provisioning"`-last groups → return a plain number). |
| REQ-102's `SPAWN_THRESHOLD_USD`/`MIN_SHELTER_USD` bullet | Updated to name `deriveMeasuredShelterCostUsd`/`readShelterCostEntries` explicitly instead of the bare, unnamed `measured_last_shelter_cost_usd` phrase (part of the sweep-found gap fix, below). |
| REQ-102 Acceptance Criteria, new bullet inserted immediately after the FIND-1401 `recentSpawnAttempts` bullet | "**(new, resolves FIND-1501)** `childrenProvisioning` is never hand-assembled by the calling orchestration — it is ALWAYS the direct return value of `countChildrenProvisioning({ledgerRows: readChildren(...)})` ..." |
| Purity boundary analysis overview table (`## Purity boundary analysis`), "Spawn eligibility gate" row | Extended to cite the new `countChildrenProvisioning` function for `childrenProvisioning` (resolves FIND-1501) AND the new `deriveMeasuredShelterCostUsd` function for `spawnThresholdUsd`'s `MIN_SHELTER_USD` override (sweep-found gap). |

### `specs/verification-architecture.md` edits

| Location | Change |
|---|---|
| Revision header (top of file) | Bumped `iteration 15` → `iteration 16`; new lead paragraph condensing the FIND-1501 fix and the sweep-found gap fix (mirroring this file's own established condensed-summary convention), prior FIND-1401 content preserved as a subordinate `— AND spec review iteration-14 finding FIND-1401 resolved —` clause. |
| Purity Boundary Map — new row **`countChildrenProvisioning`** (inserted directly after the `deriveRecentSpawnAttempts` row, before the `decideColonySpawn` row) | Added: `~/anicca/skills/self/spawn/lib/treasury-gate.mjs::countChildrenProvisioning({ledgerRows}) → number`, PURE (new), full derivation-rule description, resolves FIND-1501. |
| Purity Boundary Map — `decideColonySpawn` row | Classification note extended to `"input derivation corrected, resolves FIND-1401/FIND-1501"`; new sentence added stating `childrenProvisioning` is never hand-assembled, always the direct return of `countChildrenProvisioning`; also notes `spawnThresholdUsd` is computed upstream via `MIN_SHELTER_USD`/`deriveMeasuredShelterCostUsd`. |
| Tier 1 narrative list | Extended the REQ-102 mention to cite the new `countChildrenProvisioning` four-case fixture (PROP-102h, resolves FIND-1501) and the new `deriveMeasuredShelterCostUsd` fixture (PROP-102j). |
| Tier 2 narrative list | New clause citing PROP-102i (real orchestration wiring for `childrenProvisioning`, mirroring PROP-102g's discipline). |
| Proof Obligations table — new rows **PROP-102h**, **PROP-102i** (inserted directly after PROP-102g, before PROP-103a) | Added per the design above. |
| Gate — item (1) | Extended with a new clause covering `deriveMeasuredShelterCostUsd`'s null/last-entry derivation (PROP-102j) — part of the sweep-found gap fix. |
| Gate — new sub-item **(1g)** (inserted directly after (1f), before item (2)) | Requires the adversary to confirm `countChildrenProvisioning` is the sole mechanism producing `childrenProvisioning` (PROP-102i) and to independently re-derive the four-case count rule (PROP-102h, resolves FIND-1501). |

---

## Additional gap found during the mandated full-spec sweep (preemptive fix, no independent FIND-15xx number)

Per the dispatch's own instruction ("sweep EVERY OTHER pinned input across EVERY pure function in this
ENTIRE spec... for the SAME failure class"), every parameter of every pure function in the Purity
Boundary Map was checked against the checklist: is there a named derivation function from real,
persisted state, or is the parameter a genuinely constant/config value needing only a default? All
parameters of `filterProductiveCitizens`, `readCitizenBalances`, `computeColonySurplusUsd`,
`computePerCitizenSurplusUsd`, `deriveRecentSpawnAttempts`, `countChildrenProvisioning` (new),
`selectCloudTarget`, and `needsSolanaWallet` were confirmed either already correctly derived (with a
named function) or genuinely constant/call-time-context values needing no further derivation.

**One additional gap of the identical class was found**, on `decideColonySpawn`'s own `spawnThresholdUsd`
parameter: REQ-102's `SPAWN_THRESHOLD_USD = MIN_SHELTER_USD * SAFETY_MARGIN_MULTIPLIER` formula states
`MIN_SHELTER_USD` "MUST be superseded by `measured_last_shelter_cost_usd` — the actual USD-equivalent
cost recorded by REQ-303's shelter-cost ledger after the first real deploy" — but no function anywhere
named HOW multiple, real, append-only entries in that ledger (REQ-303's own text: "record the actual
`AKASH_DEPOSIT` escrowed and, once observable, the real settled lease cost, into a persistent
shelter-cost ledger") reduce to the ONE value actually used. This is the identical failure class as
FIND-1501/FIND-1401, one step removed: a pinned input to `decideColonySpawn` sourced from real,
persisted, potentially-multi-entry state, with no named reduction rule.

**Resolution**: The shelter-cost ledger is now a named, dedicated module,
`~/anicca/skills/self/spawn/lib/shelter-cost-ledger.js`, exporting EXACTLY
`{readShelterCostEntries, appendShelterCostEntry}` — the SAME append-only-JSONL, no-update/upsert
discipline `ledger.js` already establishes (one entry per real deploy attempt,
`{ts: number, settledLeaseCostUsd: number}`, appended once the settled cost first becomes observable).
A new sibling pure function, same file as `filterProductiveCitizens`,
`deriveMeasuredShelterCostUsd({shelterCostLedgerRows}) → number|null`, returns `null` on an empty ledger
(no real deploy has ever completed — `MIN_SHELTER_USD` stays its provisional `5.00`) or the
LAST-appended entry's `settledLeaseCostUsd` otherwise (last-write-wins — never an average, sum, or
historical-max across the ledger's accumulated entries, and never the first-ever entry). A new proof
obligation, PROP-102j (Tier 1, three fixtures: empty → `null`; single entry → that entry's value; three
entries with different values → only the last is used), is added, and the pre-existing PROP-303c
(previously a vague "a subsequent `decideColonySpawn`-adjacent threshold computation reads
`measured_last_shelter_cost_usd`") is corrected to cite `deriveMeasuredShelterCostUsd`/
`readShelterCostEntries` by name.

### Additional `specs/behavioral-spec.md` edits

| Location | Change |
|---|---|
| REQ-303, new paragraph **"Naming the shelter-cost ledger and its derivation function"** inserted immediately after the existing shelter-cost-ledger sentence | Names `shelter-cost-ledger.js`'s exact export shape and `deriveMeasuredShelterCostUsd`'s full derivation rule. |
| REQ-303 Acceptance Criteria, the "real `AKASH_DEPOSIT` amount... appended to a shelter-cost ledger" bullet | Rewritten to cite `appendShelterCostEntry`/`deriveMeasuredShelterCostUsd`/`readShelterCostEntries` by name, and to state the last-write-wins reduction explicitly. |

### Additional `specs/verification-architecture.md` edits

| Location | Change |
|---|---|
| Purity Boundary Map — new row **`deriveMeasuredShelterCostUsd`** (inserted directly after `countChildrenProvisioning`, before `decideColonySpawn`) | Pure Core (new), full null/last-entry derivation-rule description. |
| Purity Boundary Map — new row **`shelter-cost-ledger.js::readShelterCostEntries`/`::appendShelterCostEntry`** (inserted directly after the `deriveMeasuredShelterCostUsd` row) | Effectful Shell (new), mirrors `ledger.js`'s own row shape/discipline. |
| Proof Obligations table — new row **PROP-102j** (inserted directly after PROP-102i, before PROP-103a) | Added per the design above. |
| Proof Obligations table — **PROP-303c** (existing row) | Corrected to name `deriveMeasuredShelterCostUsd`/`readShelterCostEntries`/`appendShelterCostEntry` explicitly. |
| Tier 2 narrative list, REQ-303's shelter-cost-ledger mention | Corrected to name the functions explicitly rather than an unnamed threshold computation. |
| Gate — item (1) | Extended (see above) with the `deriveMeasuredShelterCostUsd` null/last-entry clause (PROP-102j). |

---

## Note on revision numbering

Confirmed by direct read of both spec files' revision headers at the start of this task: the on-disk
revision was **iteration 15** (produced by the prior task's resolution of FIND-1401, per
`reviews/spec/iteration-15/RESOLUTION-NOTES.md`'s own numbering note). This task's dispatch was for
`reviews/spec/iteration-16/`'s `verdict.json`, which reviewed that revision-15 spec and raised FIND-1501
plus the mandated full-spec sweep instruction. Following the SAME convention the iteration-15 note
already established (review round directory `iteration-N` reviews the spec at revision `N-1` and, once
resolved, the spec is bumped to revision `N`), this task resolves `reviews/spec/iteration-16/`'s finding
against a spec that was at revision 15, so the spec is bumped to revision **16** — consistent with the
task list's own next item, "P3 spawn spec iteration-17待ち", i.e. the NEXT review round (directory
`iteration-17`) will review this now-produced revision 16. No `state.json`/review-manifest files were
touched by this task per its own instructions, so the orchestrator can advance `state.json` and create
the `iteration-17` review directory separately.

---

## Verification of internal consistency (post-edit)

- Grep-confirmed `PROP-102h`, `PROP-102i`, and `PROP-102j` each appear exactly once as a table-row
  definition in `verification-architecture.md`'s Proof Obligations table (no ID collisions with any
  existing `PROP-102*`/`PROP-103*` row), correctly ordered between PROP-102g and PROP-103a.
- `countChildrenProvisioning` referenced consistently across both spec files (8 occurrences in
  `behavioral-spec.md`, 10 in `verification-architecture.md`), all pointing at the SAME file location
  (`~/anicca/skills/self/spawn/lib/treasury-gate.mjs`) as its siblings `filterProductiveCitizens`/
  `deriveRecentSpawnAttempts`.
- `deriveMeasuredShelterCostUsd` referenced consistently (9 occurrences in each file), and
  `shelter-cost-ledger.js` referenced consistently (5 occurrences in `behavioral-spec.md`, 3 in
  `verification-architecture.md`) — no divergent spelling or competing definition introduced.
- Gate item (1g) confirmed present exactly once, inserted between (1f) and (2); Gate item (1) confirmed
  extended with the `deriveMeasuredShelterCostUsd` clause.
- Confirmed the fix does NOT modify `ledger.js`'s own `{readChildren, appendChild}` shape (verified by
  direct read of the real, current `~/anicca/skills/self/spawn/lib/ledger.js` at the start of this task)
  or `child-spec.js`'s own source (verified by direct read of the real, current
  `~/anicca/skills/self/spawn/lib/child-spec.js`) — this is purely an additive extension (two new
  sibling pure functions in `treasury-gate.mjs`, plus one new small effectful module,
  `shelter-cost-ledger.js`, mirroring `ledger.js`'s own existing shape).
- No edits were made to `state.json`, review manifest/verdict files, or the `iteration-17` review
  directory — those remain the orchestrator's responsibility per this task's own instructions. No
  commit/push was performed.
