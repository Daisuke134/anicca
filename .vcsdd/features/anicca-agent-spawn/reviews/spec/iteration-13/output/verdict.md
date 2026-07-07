# Spec Review Verdict — anicca-agent-spawn — iteration 13

**Overall verdict: FAIL**

This is a fresh-context, zero-prior-history adversary pass. I read `specs/behavioral-spec.md` (2339
lines) and `specs/verification-architecture.md` (729 lines) end-to-end, cross-checked every load-bearing
citation I could verify against the real source files (`spawn-decision.js`, `resolve-identity.mjs`,
`is-self-funded.mjs`, `ledger.js`, `child-spec.js`, `state-path.js`, `lock.mjs`, `akt-cost-gate.js`,
`spawn-child/config.json`, `spawn-child/SKILL.md`, `run.sh`), and re-verified iteration-12's two prior
findings against the current spec text.

## Prior findings re-verified

- **FIND-1101 (critical, cooldown contradiction): GENUINELY RESOLVED.** REQ-102 and REQ-305 now state
  the identical reconciled cooldown rule verbatim (behavioral-spec.md:525-546, 1854-1859, 1912-1927),
  with explicit two-way cross-references. `decideColonySpawn`'s new `recentSpawnAttempts` signature
  genuinely mirrors `spawn-decision.js::decideSpawn`'s real array-scan pattern (confirmed by direct
  read of the current source). PROP-305g's exact 2-vs-3-failures boundary fixture exists as claimed.
  I grepped both spec files exhaustively for every remaining cooldown/`FAILURE_COOLDOWN_CAP`/
  `recentSpawnAttempts` mention and found no residual contradiction.
- **FIND-1102 (major, missing co-funding success proof): GENUINELY RESOLVED.** PROP-304f
  (verification-architecture.md:305) exercises a genuinely different code path than PROP-304c
  (verification-architecture.md:302) — PROP-304c is the blocked/no-op path (zero transfers, zero
  ledger row); PROP-304f is the success path (two real sequential transfers, an exact final balance,
  a created child ledger row, both transfers independently traceable). This is not a cosmetic variant.

## New findings (this iteration)

### FIND-1201 (critical) — REQ-103's lock critical-section scope is self-contradictory, and the
binding (Acceptance Criteria) reading is too narrow to prevent a real double-spawn/double-funding race

REQ-103 states three different scopes for the `"colony-spawn"` lock's critical section within the
*same requirement*:

| Where | Scope stated |
|---|---|
| EARS clause (behavioral-spec.md:617-624) | "...proceeds to REQ-201's identity generation **and beyond**" — open-ended |
| Prose justifying the lock's `statePath` (behavioral-spec.md:650-652) | "the critical section this lock protects IS... **(REQ-101 through REQ-305)**" — the whole spawn attempt |
| Acceptance Criteria (behavioral-spec.md:688) | "**REQ-201 through REQ-205**, and the decision to proceed into REQ-3xx" — textually excludes REQ-206 (buildChildSpec/first ledger append), REQ-304 (funding), and REQ-305 (final append); reads as releasing the lock at the decision point, before REQ-3xx executes |

The Acceptance Criteria is the binding, testable contract a Phase 2 implementer and Phase 3 verifier
actually build/test against — and it is narrower than what REQ-102 explicitly relies on the lock to
guarantee ("REQ-103 is what prevents both from acting on that true result simultaneously; REQ-102
does not need to know about concurrency", behavioral-spec.md:571-575). Under the narrow reading, a
concrete race is possible: Evaluator A acquires the lock, runs REQ-201-205, releases the lock at "the
decision to proceed" (before REQ-206's initial provisioning ledger append and before any REQ-3xx
execution). A's own `recentSpawnAttempts` entry is only recorded on *completion* (behavioral-spec.md:
526-527), so it is invisible to a second evaluator's cooldown check while A is still mid-flight — and
if the ledger's `childrenProvisioning` count is still 0 (because the provisioning row hasn't been
appended yet, since REQ-206 sits textually outside "REQ-201 through REQ-205"), a second,
later-woken evaluator can also observe `eligible:true`, acquire the now-free lock, and independently
proceed through its own REQ-3xx/REQ-304 funding — a genuine double-spend of the colony's certified
surplus and two children spawned when `MAX_CONCURRENT_SPAWNS` (default 1) is supposed to cap it at one.
Akash's own bid-polling loop ("30 attempts, existing default sleep", REQ-303's edge case,
behavioral-spec.md:1699-1701) confirms this window is real wall-clock minutes, not an instant.

Proof obligations do not close this gap either: PROP-103a (verification-architecture.md:247) and Gate
item (2) (verification-architecture.md:563-571) both test only *simultaneous* `eligible:true`
evaluations, never the *staggered* scenario the narrow Acceptance Criteria would actually permit. A
Phase 3 adversary following these proof obligations verbatim would PASS an implementation that has
exactly this double-spend race.

Routed to Phase 1a: REQ-103's Acceptance Criteria must state one unambiguous critical-section boundary
(consistent with its own EARS clause and prose, and sufficient to protect `MAX_CONCURRENT_SPAWNS`'s
own precondition), and a new proof obligation must test the staggered-timing case, not merely the
simultaneous one.

### FIND-1202 (major) — REQ-304's per-citizen ceiling check has no specified computation source

REQ-304's own Acceptance Criteria (behavioral-spec.md:1836-1839, added to resolve FIND-1102) requires
checking each citizen's transfer "against THAT citizen's own certified surplus-above-reserve
contribution" — but no function anywhere in this spec (not `computeColonySurplusUsd`, not
`filterProductiveCitizens`, not any other named export) is specified to expose that per-citizen value;
`computeColonySurplusUsd({citizens, perCitizenReserveUsd}) → number` returns only the aggregate sum.
This is inconsistent with how rigorously every other cross-requirement data dependency in this spec is
pinned to an exact named function/constant (`CITIZENS_REGISTRY_PATH`, `COORDINATOR_HOME`,
`filterProductiveCitizens`, `selectCloudTarget`, etc.). Left as-is, a Phase 2 implementer must either
invent an unspecified new return shape or independently re-derive `max(0, balance_i - reserve)` a
second time inside REQ-304's own code — precisely the "two independently-derived numbers that must be
identical by construction" hazard this spec explicitly rejects elsewhere (REQ-206's own
`seedUsdc`/gas-seed-amount edge case).

## Full-spec skeptical pass

I read every REQ (101-106, 201-206, 301-306, 401-403) and every changelog entry end-to-end, and
cross-checked line-number/content citations against real source files where feasible (not merely
trusting prior iterations' citations). All citations I checked — `run.sh:124-140/200-205/213-220`,
`spawn-decision.js`'s array-scan, `resolve-identity.mjs`'s legacy-fallback gate and `COORDINATOR_HOME`
interaction, `is-self-funded.mjs`'s boolean/set contracts, `lock.mjs::tryCreateLockFile`'s exact shape,
`ledger.js`'s exact export surface, `child-spec.js::buildChildSpec`'s required-field/throw behavior,
`state-path.js::resolveStateDir`'s fail-closed logic, `spawn-child/config.json` and `SKILL.md`'s
verbatim content — matched the spec's claims exactly. I found no further citation-accuracy defects.
The two findings above are genuine design/proof-obligation gaps, not citation errors.
