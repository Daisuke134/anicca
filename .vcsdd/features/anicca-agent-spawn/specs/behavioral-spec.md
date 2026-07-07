# Behavioral Spec — anicca-agent-spawn (Phase 1a)

**feature**: anicca-agent-spawn · **mode**: strict · **increment**: P3 spawn (colony-treasury-gated,
cloud-only) + $0-bootstrap verification · **日付**: 2026-07-08 · **revision**: iteration 19, revised
(spec review iteration-19 finding FIND-1803 resolved — REQ-303's own text was internally
self-contradictory about whether `computeSpawnGate`'s `ready:false` result triggers REQ-304's Skip API
AKT-funding bridge or unconditionally aborts the deploy before that bridge is ever attempted — the
"Funding-readiness gate reuse" paragraph implied `ready:false` decides whether the bridge runs, while
the requirement's own dedicated Edge Case stated `ready:false` is ALWAYS an immediate deploy failure
with nothing further invoked, meaning REQ-304's entire, three-times-hardened bridge mechanism risked
being unreachable dead orchestration as literally worded. Resolved with a genuine design decision,
grounded in REQ-304's own PROP-304d test-method text (which already required the bridge's hops to land
funds "before `akt-treasury.sh`'s existing `mint-act` step runs"): `computeSpawnGate` is now evaluated
in EXACTLY two passes — the FIRST pass's `ready:false` is what triggers an attempt at REQ-304's bridge
(never itself a REQ-305 failure); AFTER the bridge attempt completes, a SECOND `computeSpawnGate`
evaluation runs, and ONLY that SECOND evaluation's `ready:false` is the actual REQ-305 deploy failure —
a first-pass `ready:true` skips the bridge entirely. REQ-303's Edge Case is rewritten to describe only
the SECOND evaluation's failure, and the main paragraph now states this full two-pass sequencing as the
ONE unambiguous statement, resolving the contradiction. A new proof obligation, PROP-303h, proves this
sequencing (three fixtures: first-pass-ready skips the bridge; first-pass-not-ready + successful bridge
proceeds; first-pass-not-ready + still-insufficient second pass is the actual failure); the Purity
Boundary Map's `computeSpawnGate` row and Gate items (6a)/(7) are updated and cross-referenced — AND
spec review iteration-19 finding FIND-1802 resolved — `computeSpawnGate`'s own `balanceAkt` parameter —
its FIRST-listed, most consequential input — had no named real-derivation source anywhere in either
spec document, unlike its immediate signature-siblings `costAkt`/`bufferAkt`, which ARE bound to
`spawn-child/config.json`'s real values one clause later in the same sentence. Resolved by reading the
real `~/anicca/skills/self/spawn-child/run.sh`/`SKILL.md` source (not inventing a mechanism):
`balanceAkt` is now explicitly bound to a FRESH `provider-services query bank balances <address>` call
(address resolved via `provider-services keys show "$AKASH_KEY_NAME"`, the SAME signing wallet
`costAkt`/`bufferAkt` are already scoped to), reusing `run.sh`'s own existing, already-fail-closed
query+uakt→AKT-conversion logic verbatim, performed fresh at each evaluation. A new proof obligation,
PROP-303g, verifies this binding by construction (mirrors PROP-102k/PROP-101j/PROP-202d/PROP-101k's own
discipline); the Purity Boundary Map row and Gate item (6a) are updated accordingly — AND spec review
iteration-19 finding FIND-1801 resolved — REQ-101's own
`filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays})` — the very function
FIND-1401/FIND-1501/FIND-1601's own resolutions repeatedly cited as the established precedent for this
binding discipline — never itself stated an explicit default value for its own `bootstrapWindowDays`
parameter, nor a proof obligation confirming this real, passed-in value is, by construction, identical
to REQ-402's own `BOOTSTRAP_WINDOW_DAYS` constant, which REQ-101's own prose textually claims it mirrors
("the same window REQ-402 itself applies"). Resolved: REQ-101's own Acceptance Criteria now explicitly
states `bootstrapWindowDays` defaults to `14`, identical to REQ-402's own `BOOTSTRAP_WINDOW_DAYS`
constant — never independently configurable to a different value — mirroring the exact treatment this
document's own iteration-18 fix already gave `decideColonySpawn`'s own
`cooldownDays`/`failureCooldownCap`/`maxConcurrentSpawns` defaults. A new proof obligation, PROP-101k,
verifies `bootstrapWindowDays` and `BOOTSTRAP_WINDOW_DAYS` are configured to the IDENTICAL value by
construction, never merely coincidentally equal — mirroring this spec's own established discipline
already used for `BOOTSTRAP_WINDOW_DAYS`/`SPAWN_COOLDOWN_DAYS` (PROP-402e) and `seedUsdc`/REQ-204's
gas-seed-transfer amount (PROP-206g); the Gate's item (1b) is extended to require this identity check —
AND spec review iteration-18 finding FIND-1701 resolved — REQ-102's `decideColonySpawn`'s own
`colonySurplusUsd` parameter — the single most consequential value the function consumes, gating whether
ANY spawn happens at all — had no "never hand-assembled, always the direct return value of X()" binding
sentence and no dedicated real-derivation proof obligation, unlike its immediate signature-siblings
`recentSpawnAttempts`/`childrenProvisioning`, which both already received this exact treatment
(FIND-1401/FIND-1501). Resolved: `colonySurplusUsd` is now explicitly bound, in REQ-102's own text, to
THAT SAME evaluation's `computeColonySurplusUsd({citizens: filterProductiveCitizens(...),
perCitizenReserveUsd})` (REQ-101) direct return value — never hand-assembled, never a stale/earlier
evaluation's cached aggregate. REQ-102's own "multiple evaluations in the same wake" edge case is
explicitly resolved for this hazard: EACH separate evaluation MUST call this pipeline fresh, and REQ-103's
`"colony-spawn"` lock is explicitly NOT relied upon as a substitute safety mechanism, since that lock's
own critical section begins only at REQ-201 — strictly AFTER REQ-101/102's evaluation completes
(confirmed by direct re-read of REQ-103's own statePath prose, which states this exactly) — so staleness
of `colonySurplusUsd` is a hazard this binding closes directly, never one the lock happens to already
prevent. A new proof obligation, PROP-102k, adds the missing Tier-1/Tier-2 real-derivation integration
check (mirroring PROP-101j/PROP-102g/PROP-102i/PROP-202d exactly), and the Gate's item (1) is extended to
require it. Separately, this iteration's own mandated full-signature closeout of `decideColonySpawn`
(every one of its 8 parameters, re-classified with uniform rigor) confirmed
`spawnThresholdUsd`/`recentSpawnAttempts`/`childrenProvisioning` already correctly bound, `nowMs`
correctly exempt as a raw wall-clock primitive (mirroring `selectCloudTarget`'s own raw-I/O-leaf inputs,
iteration 17), `cooldownDays`/`failureCooldownCap` already correctly defaulted — and surfaced one further,
minor asymmetry: `maxConcurrentSpawns`'s own default (`1`) was stated only in REQ-102's EARS clause, never
restated at the Acceptance-Criteria level the way `cooldownDays`/`failureCooldownCap` both are; a new
Acceptance Criteria clause closes this (no new PROP needed, since PROP-102c already tests
`maxConcurrentSpawns`'s behavior directly) — see RESOLUTION-NOTES.md, `reviews/spec/iteration-18/`, for
the full per-parameter closeout table — AND spec review iteration-17 finding FIND-1601 resolved —
REQ-202's `needsSolanaWallet({initialSkills,
deployTarget}) → boolean` pinned TWO inputs with no real-system-state binding rule anywhere in this
document: (a) `deployTarget` is now explicitly bound, in REQ-202's own text, to THAT SAME spawn
attempt's `selectCloudTarget(...)` (REQ-306) direct return value — never hand-assembled by the calling
orchestration, never a stale/earlier attempt's evaluation — mirroring the IDENTICAL "never hand-
assembled, always the direct return value of X()" binding discipline FIND-1401/FIND-1501 already
established for `recentSpawnAttempts`/`deriveRecentSpawnAttempts` and
`childrenProvisioning`/`countChildrenProvisioning`; a new proof obligation, PROP-202d, adds the missing
Tier-1/Tier-2 real-derivation integration check (mirroring PROP-102g/PROP-102i exactly), and the Gate's
item (4) — which, until now, never once cited ANY of REQ-202's own three pre-existing proof obligations
(PROP-202a/b/c) at all — now requires PROP-202a/b/d. (b) `initialSkills` had NO specified source
anywhere in either spec document — not a default, not a derivation, not an explicit agent-judgment
carve-out. Resolved by extending REQ-104's own, pre-existing agent-judgment carve-out ("what the child's
initial goal framing/prompt should say" is the agent's own in-envelope choice) to explicitly ALSO name
`initialSkills`: the spawning agent decides a new child's starting capabilities together with its goal
framing, in the SAME in-envelope decision REQ-104 already grants — never a hardcoded fixed default (this
feature's own purpose, per SPEC.md P3, is a new colony member choosing ITS OWN earning strategy, not a
structural clone of its parent) and never a mechanical full copy of the driving citizen's own current
skill roster (which would make every child structurally identical to its parent, defeating that same
purpose); a new proof obligation, PROP-202e, adds the structural (Tier 0) check that `initialSkills` is
never hardcoded/defaulted inside REQ-202's own orchestration — it is always the SAME value the spawning
agent already chose, per REQ-104's carve-out, for that attempt — and the Gate's item (4) requires this
too (resolves FIND-1601, critical) — AND, found during this SAME iteration's own mandated, genuinely
exhaustive, checklist-driven full-parameter sweep (built as an explicit per-function, per-parameter
classification table, rather than another free-form re-read, precisely because three consecutive prior
sweeps each missed at least one sibling instance): REQ-101's own
`filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays})` — the very function
FIND-1401/FIND-1501's own resolutions repeatedly cited as the established PRECEDENT this binding
discipline was modeled on — never itself stated the identical binding rule for its OWN `ledgerRows`
(`ledger.js::readChildren()`'s real output) or `citizens` (a real `CITIZENS_REGISTRY_PATH` read)
arguments, and PROP-102g's own citation claiming to "mirror PROP-101d/PROP-101e's own real-derivation
discipline" does not actually hold up under a fresh, skeptical re-read: PROP-101d/PROP-101e are
Tier-1/Tier-2 checks of `filterProductiveCitizens`/`readCitizenBalances`'s OWN internal correctness
against already-supplied fixture inputs, never a check that REAL orchestration binds either function's
inputs to a real `readChildren()`/registry-read call rather than a hand-rolled reimplementation at the
call site. Resolved by adding the identical explicit "never hand-assembled" binding sentence REQ-102
already uses to REQ-101's own text for `filterProductiveCitizens`'s `ledgerRows`/`citizens` arguments —
and, by that same sentence's own reasoning, to `readCitizenBalances`'s `citizens` argument, which the
existing prose already implied but never stated with the established phrase; a new proof obligation,
PROP-101j, adds the missing Tier-1/Tier-2 real-derivation integration check (mirroring PROP-102g/
PROP-102i exactly), and the Gate's item (1b) is extended to require it. This closes the FIFTH instance of
this recurring failure class found across iterations 14-17 — see RESOLUTION-NOTES.md for this
iteration's full parameter-by-parameter classification table covering EVERY OTHER pure function listed
in the Purity Boundary Map, none of which surfaced any further UNRESOLVED instance) — AND spec review
iteration-16 finding FIND-1501 resolved — REQ-102's `decideColonySpawn` pinned
`childrenProvisioning` as a sibling input to `recentSpawnAttempts`, in the exact same signature, but no
function anywhere derived this count from `ledger.js`'s real, append-only, duplicate-`child_id`-
containing rows either — the identical failure class FIND-1401 (below) just fixed for its neighbor. A
new sibling pure function, same file as `filterProductiveCitizens`/`deriveRecentSpawnAttempts`,
`countChildrenProvisioning({ledgerRows}) → number`, groups `ledgerRows` by `child_id`, reduces to the
last-appended row per group (last-write-wins, the SAME discipline already established), and counts
exactly the groups whose last row's `status` is `"provisioning"` — a group whose last row is
`"active"`, `"failed"`, or `"bootstrap_failed"` is NEVER counted, regardless of an earlier
`"provisioning"` row for that SAME `child_id` — closing both the double-counting hazard (a naive
per-row scan) and the permanent-block hazard (a stale `"provisioning"` row never superseded in the
count) FIND-1401 already closed for `recentSpawnAttempts`; REQ-102's real orchestration now calls this
function directly over `readChildren`'s real output, mirroring `deriveRecentSpawnAttempts`'s own
integration discipline; new proof obligations PROP-102h (Tier 1, four-case unit fixture) and PROP-102i
(Tier 1/2, real-derivation integration discipline) are added, the Purity Boundary Map gains a new
`countChildrenProvisioning` row and the `decideColonySpawn` row is updated to cite it, and the Gate's
new item (1g) requires all this (resolves FIND-1501, critical) — AND, found during this SAME
iteration's own mandated full-spec sweep for the identical failure class (never independently raised
by the adversary, resolved here preemptively to close it before a third iteration could find it as a
third sibling gap): REQ-102's `SPAWN_THRESHOLD_USD` formula named its `MIN_SHELTER_USD` override,
`measured_last_shelter_cost_usd`, as sourced from "REQ-303's shelter-cost ledger" in prose only, with
NO named function specifying how that ledger's multiple, real, append-only entries (the SAME shape
`ledger.js`'s own rows already have) reduce to the ONE value actually used. Resolved by naming REQ-303's
shelter-cost ledger module explicitly — a new, small, dedicated module,
`~/anicca/skills/self/spawn/lib/shelter-cost-ledger.js`, exporting EXACTLY
`{readShelterCostEntries, appendShelterCostEntry}` (the SAME append-only-JSONL, no-update/upsert
discipline `ledger.js` already establishes) — and a new sibling pure function, same file as
`filterProductiveCitizens`, `deriveMeasuredShelterCostUsd({shelterCostLedgerRows}) → number|null`,
which returns `null` on an empty ledger (no real deploy has ever completed — `MIN_SHELTER_USD` stays its
provisional `5.00`) or the LAST-appended entry's `settledLeaseCostUsd` otherwise (last-write-wins —
NEVER an average, sum, or historical-max across the ledger's accumulated entries, and never the
FIRST-ever entry); a new proof obligation, PROP-102j, verifies both branches, and PROP-303c is corrected
to cite this function by name rather than an unnamed "threshold computation" (resolves this
preemptively-found gap) — AND spec review iteration-14 finding FIND-1401 resolved — REQ-102's own
Cooldown Check pinned
`recentSpawnAttempts: Array<{ts, outcome}>` as an input, but no function anywhere derived this array
from `~/anicca/skills/self/spawn/lib/ledger.js`'s real rows — unlike REQ-101's exactly analogous need,
satisfied by a named, fully-specified pure join function, `filterProductiveCitizens`; two concrete gaps
made this unimplementable: (a) no ledger row carried any timestamp field a failed/in-flight attempt's
`ts` could be drawn from (REQ-305 only ever set `active_since`, and only on success), and (b) the
status→outcome mapping was unspecified for a LATER `"bootstrap_failed"` relabeling of an already-`
"active"` child. Resolved by: REQ-305 now specifies a new field, `attempted_ms`, set to `nowMs` on the
very FIRST `ledger.js` row ever appended for a given `child_id` (the initial `"provisioning"` row) and
copied forward UNCHANGED onto every later row for that SAME `child_id` (a `"failed"` row, an `"active"`
row, or REQ-402's `"bootstrap_failed"` row) — never a freshly-generated timestamp for a follow-up row —
following the EXACT precedent this SAME requirement already establishes for `active_since` (an extra
field the caller merges into `buildChildSpec`'s base returned object before `appendChild`, `child-
spec.js` itself untouched); a new pure function, same file as `filterProductiveCitizens`,
`deriveRecentSpawnAttempts({ledgerRows}) → Array<{ts, outcome}>`, groups `ledgerRows` by `child_id` and
maps EACH group to exactly one entry — `outcome:"success"` PERMANENTLY if that `child_id` ever reached
`"active"` (a later `"bootstrap_failed"` row never retroactively flips this, per REQ-102's own existing
"a successful attempt is ALWAYS cooldown-triggering" rule), else `outcome:"failure"` if its last row is
`"failed"`, else EXCLUDED entirely if its last row is still `"provisioning"` (an in-flight attempt,
already tracked separately via `childrenProvisioning`) — one entry per `child_id`, never per raw row,
closing the double-counting hazard; REQ-102's real orchestration is specified to call this function
directly over `readChildren`'s real output, never a hand-rolled reimplementation at the call site
(mirroring REQ-101's own `filterProductiveCitizens` integration discipline); new proof obligations
PROP-102f (the four-case unit fixture: failure, success, success-then-bootstrap_failed,
in-flight-excluded), PROP-102g (the real-derivation integration discipline), and PROP-305h (the
`attempted_ms` field-lifecycle structural check) are added, and the Gate's item (1) is extended to
require this (resolves FIND-1401, critical) — AND spec review iteration-13 finding FIND-1301 resolved —
REQ-102's own `SPAWN_COOLDOWN_DAYS` constant,
used repeatedly throughout its Cooldown Check and REQ-305's failure-cap reconciliation but never itself
given an explicit default value anywhere in this document — unlike every sibling constant in the SAME
requirement (`MIN_SHELTER_USD` defaults to `5.00`, `SAFETY_MARGIN_MULTIPLIER` defaults to `2`,
`FAILURE_COOLDOWN_CAP` defaults to `3`, `MAX_CONCURRENT_SPAWNS` defaults to `1`) — now explicitly
defaults to `14`, reusing `~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn`'s own existing
`rateLimitDays` parameter default (line 11) for consistency with prior art, rather than inventing an
unrelated value (the SAME citation discipline this spec's own `SAFETY_MARGIN_MULTIPLIER` default already
uses for `akt-treasury.sh`'s "2×" convention); REQ-102's Acceptance Criteria gains the matching
`cooldownDays` default; REQ-402's `BOOTSTRAP_WINDOW_DAYS` (default `14`, reusing REQ-102's own
`SPAWN_COOLDOWN_DAYS` constant) now correctly cites a REQ-102 default that actually exists, rather than
an implied value REQ-102 never stated; and a new proof obligation, PROP-402e, verifies
`BOOTSTRAP_WINDOW_DAYS` and `SPAWN_COOLDOWN_DAYS` are configured to the IDENTICAL value by construction,
never merely coincidentally equal — mirroring this spec's own established "identical by construction,
never merely close" discipline already used for REQ-206's `seedUsdc`/REQ-204 gas-seed-transfer-amount
pair (resolves FIND-1301, major) — AND spec review iteration-12 findings FIND-1201/1202 resolved —
REQ-103's `"colony-spawn"` lock critical
section, previously stated with THREE mutually inconsistent scopes across its EARS clause ("and
beyond", open-ended), its own prose ("REQ-101 through REQ-305"), and its binding Acceptance Criteria
("REQ-201 through REQ-205, and the decision to proceed into REQ-3xx" — textually EXCLUDING REQ-206's
ledger append, REQ-304's funding, and REQ-305's append), is unified to ONE identical scope, stated
IDENTICALLY in all three places: the lock is held from REQ-201's wallet generation THROUGH REQ-305's
ledger append actually completing (the new citizen durably recorded in `citizens.json`) — never released
any earlier, closing the staggered (non-simultaneous) double-spawn/double-funding race the narrower
Acceptance-Criteria reading would have permitted (a second evaluator arriving AFTER a first evaluator's
REQ-205 completes but WHILE its REQ-304/REQ-305 are still executing). A new proof obligation, PROP-103e,
adds the missing STAGGERED-timing fixture — a first evaluator's REQ-304 funding step is deliberately
delayed, and a second evaluator's repeated lock-acquire attempts throughout that entire delay all fail,
succeeding only after the first evaluator's REQ-305 append has actually landed — proving the lock's real
scope, not merely the REQ-201-205 sub-window PROP-103a alone exercises (resolves FIND-1201, critical).
Separately, REQ-101 gains a new sibling pure function, `computePerCitizenSurplusUsd({citizens,
perCitizenReserveUsd}) → Array<{citizenId, surplusUsd}>`, exposing EACH citizen's own `max(0, balance_i -
perCitizenReserveUsd)` term individually — the SAME per-citizen arithmetic `computeColonySurplusUsd`
already sums, now separately named and independently callable; `computeColonySurplusUsd` is now
specified to be implemented by CALLING this function and summing its output, so the aggregate and the
per-citizen breakdown can never silently diverge (mirroring REQ-206's own "two independently-derived
numbers must be identical by construction" discipline). REQ-304's per-citizen ceiling-check Acceptance
Criteria now cites this function BY NAME as the value each citizen's transfer is checked against, and a
new proof obligation, PROP-101i, tests both the function's own per-citizen correctness and its
by-construction consistency with `computeColonySurplusUsd`'s aggregate sum (resolves FIND-1202, major) —
AND spec review iteration-11 findings FIND-1101/1102 resolved — REQ-102's `decideColonySpawn` signature is
extended from a single scalar `lastSpawnAttemptMs` to a richer `recentSpawnAttempts:
Array<{ts, outcome}>` (reusing the SAME array-scan pattern
`~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn` already proves for its own rate-limit
check over `children[].spawned_ms`), reconciling REQ-102/REQ-305's cooldown-consumption contradiction
into ONE rule: a successful attempt in-window is always a hard cooldown gate; a failed attempt is
cooldown-exempt only below `FAILURE_COOLDOWN_CAP` (default `3`), beyond which it triggers cooldown
identically to a success; PROP-102b/PROP-305c are corrected to test this SAME reconciled logic, and a
new proof obligation, PROP-305g, adds the exact "3 failures reached, cooldown now applies" boundary
fixture (resolves FIND-1101, critical). Separately, REQ-304 gains a new proof obligation, PROP-304f,
covering the multi-citizen SEQUENTIAL co-funding SUCCESS path — two citizens' own sequential
single-signer transfers together fully funding one child wallet, distinct from PROP-304c's existing
insufficient-funds no-op test (resolves FIND-1102, major) — AND spec review iteration-1 findings
FIND-001..006 resolved AND spec review iteration-2 findings
FIND-101..104 resolved AND spec review iteration-3 findings FIND-201..206 resolved AND spec review
iteration-4 findings FIND-301..305 resolved AND spec review iteration-5 findings FIND-401..405
resolved AND spec review iteration-6 findings FIND-501..504 resolved AND spec review iteration-7
findings FIND-601..604 resolved AND spec review iteration-8 findings FIND-701..703 resolved AND spec
review iteration-9 findings FIND-801..802 resolved AND spec review iteration-10 finding FIND-901
resolved — `citizens.json` SPLIT into a git-tracked seed template (`citizens.seed.json`) and a
durable, out-of-git-tree runtime file (`CITIZENS_REGISTRY_PATH`, resolved via the SAME
`resolveStateDir({env, home})` mechanism `run.sh` already uses for `children.jsonl`) AND spec review
iteration-10 findings FIND-1001..1002 resolved — REQ-105's one-time bootstrap step is corrected from a
check-then-act ("does the file exist? then copy") to a single ATOMIC POSIX exclusive-create
(`fs.open(path, 'wx')`, `O_CREAT|O_EXCL`) operation — the SAME atomic primitive
`~/anicca/skills/economy/gig/lib/lock.mjs::tryCreateLockFile` already uses to close an identical class
of check-then-act race (that module's own header comment documents a REAL prior double-pay bug this
pattern exists to prevent) — making the bootstrap race-free against both concurrent first-access
bootstraps AND a late/slow bootstrap racing an already-completed REQ-305 append (resolves FIND-1001,
critical); AND `registry-path.mjs`'s Purity Boundary Map row is corrected from "Pure Core" to
"Effectful Shell", consistent with `CITIZENS_REGISTRY_PATH`'s dependency on the already-Effectful
`resolveStateDir` and `COORDINATOR_HOME`'s dependency on a real `os.homedir()` environment read
(resolves FIND-1002, major) — see changelogs below)

## Changelog (iteration 1 → iteration 2)

Spec review iteration 1 FAILed with 6 findings. Each is resolved by a specific, cited design decision
(not a vague "will fix later"):

| Finding | Severity | Resolution |
|---|---|---|
| FIND-001 | critical | `child-spec.js::buildChildSpec` is corrected from a false "reused unmodified" claim to a small, backward-compatible validation extension (new REQ-206): its identity-anchor requirement now accepts EITHER the old `childInbox` (AgentMail) OR the new `agentEvmAddress`+`agentId` (ERC-8004) pair — never both required. |
| FIND-002 | critical | The dynamic citizen registry is specified explicitly (new REQ-105): a brand-new, dedicated registry file (`~/anicca/skills/self/spawn/registry/citizens.json`) holds an array of `{id, wallet, walletAddress, fuel, humanDependencies, telemetryPath}` records that `isSelfFunded()` can consume directly; REQ-305 appends a new record to it on every successful spawn. |
| FIND-003 | major | This increment's scope is explicitly narrowed (new REQ-106): all REQ-101/102/103 evaluation happens on ONE designated coordinator host (the Mac Mini already running automaton); cloud-deployed children never evaluate the colony-spawn gate themselves in this increment (spawn chaining is out of scope, deferred). This is what makes `lock.mjs`/`ledger.js` (local-filesystem primitives) correct as specified. |
| FIND-004 | medium | REQ-204's "already-registered" defensive edge case is rewritten to reuse the existing, already-tested `~/anicca/skills/economy/gig/lib/ensure-agent-id.mjs::ensureAgentId` wrapper instead of re-deriving the same cache/verify/register-once logic from scratch. |
| FIND-005 | low | REQ-204's citation of "SPEC.md §9.9" for the gas-seed tx hashes is corrected to the actual section, "SPEC.md §9.6". |
| FIND-006 | medium | The Nosana-vs-Akash cloud-target selection that REQ-302/303 presupposed is now itself specified (new REQ-306): a deterministic, price/availability-based comparison — bookkeeping, never a model judgment call. |

## Changelog (iteration 2 spec review, round 1 → round 2)

Iteration 2's spec review FAILed with 4 findings (all 6 iteration-1 findings above were reconfirmed
genuinely resolved). Each is resolved by a specific, cited design decision:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-101 | critical | REQ-105/REQ-305 STOP repurposing the pre-existing, live `~/anicca/skills/economy/ubi/colony-wallets.json` (whose 2nd entry is claude-p's own human-funded wallet, and which `ubi.js::distributeAI` already uses for a different, unrelated purpose). A brand-new, dedicated file — `~/anicca/skills/self/spawn/registry/citizens.json` — is introduced instead, seeded with a fixed literal 2-entry array (no migration, no ambiguous classification step), and REQ-305's append path now calls `isSelfFunded()` on any new entry before appending, refusing the append if it returns `false`. |
| FIND-102 | major | REQ-206's EARS clause is corrected to remove its self-contradiction with its own edge case: "at least one of these two anchors" is now stated explicitly as a non-exclusive minimum (both anchors present simultaneously is accepted, not an error), with a new acceptance criterion and PROP-206e covering exactly that path. |
| FIND-103 | major | REQ-103 now names the canonical `statePath` every colony-spawn lock caller MUST use — REQ-105's `citizens.json` path, exported as a single constant `CITIZENS_REGISTRY_PATH` from a new shared module `~/anicca/skills/self/spawn/lib/registry-path.mjs` — closing the "mismatched statePath silently defeats mutual exclusion" gap. |
| FIND-104 | medium | The citizen-registry record's `wallet` field is split into two separate fields: `wallet: {evm?: boolean, solana?: boolean}` (matching `is-self-funded.mjs::hasOwnWallet()`'s real, documented boolean contract exactly) and `walletAddress: {evm?: string, solana?: string}` (the actual address string(s), never passed to `isSelfFunded()`). |

## Changelog (iteration 2 spec review, round 2 → iteration 3)

Iteration 2's round-2 spec review FAILed with 6 NEW findings (all 4 prior findings, FIND-101..104,
were reconfirmed genuinely resolved against the real, current source). Each is resolved by a specific,
cited design decision:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-201 | critical | REQ-402's lifecycle facts (`status`, `active_since`) are pinned to their ONE canonical owner, `ledger.js`'s own rows — never `citizens.json`, which stays deliberately minimal. REQ-101 gains an explicit JOIN step, a new pure function `filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays})`, that cross-references REQ-105's registry against `ledger.js`'s rows before `computeColonySurplusUsd` ever runs. REQ-305 now explicitly sets `active_since` on the ledger row the moment a child is marked `"active"`. |
| FIND-202 + FIND-205 | major + medium | REQ-105's record shape gains a new `homeDir` field (an already-resolved absolute HOME path, for REQ-403's audit), and `telemetryPath` is redefined to be an ALREADY-RESOLVED absolute path at seed/append time — never an unresolved `$HOME` template string requiring a runtime substitution step nobody specified. Both today's citizens legitimately share the same `homeDir` (documented as expected, not a bug, per REQ-106's single-coordinator-host scoping). **[iteration 6 correction, FIND-501]: this "share the same `homeDir`" framing was itself found factually incompatible with `resolve-identity.mjs`'s real resolution semantics — see the iteration 6 changelog and REQ-105/REQ-403 below for the corrected, DISTINCT `homeDir` values.** |
| FIND-203 | major | REQ-402's promise to feed `children_bootstrap_failed` into REQ-102's gate evaluation is REMOVED — descoped to an observability-only bookkeeping count with an explicit, structurally-checkable non-effect on REQ-102's pinned signature/behavior. |
| FIND-204 | critical | REQ-206 is extended (not just its identity-anchor clause) to specify concrete values/derivation for `buildChildSpec`'s other four already-mandatory fields: `parentWallet` (REQ-106's coordinator-host citizen's own wallet), `generation` (fixed `1`, reusing `run.sh`'s own existing default convention), `seedUsdc` (aliased exactly to REQ-204's gas-seed amount, explicitly distinct from REQ-303/304's shelter cost), and `constitutionHash` (a fixed SHA-256 of the already-shipped `identity/genesis.md` canonical genesis file). |
| FIND-206 | low | REQ-101's vestigial "claude-p appears in the same telemetry-file directory listing" edge case is removed entirely — unreachable under the registry-only design REQ-105/101 specify. |

## Changelog (iteration 3 spec review → iteration 4)

Iteration 3's spec review (an Opus-model adversary pass, deeper scrutiny than prior Sonnet passes)
FAILed with 5 NEW findings (all 6 iteration-1 findings, all 4 iteration-2-round-1 findings, and all
6 iteration-2-round-2 findings were reconfirmed genuinely resolved against the real, current source).
Each is resolved by a specific, cited design decision:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-301 | critical | REQ-101's `filterProductiveCitizens` join now explicitly specifies "last write wins": `ledger.js`'s real, append-only rows may legitimately contain MULTIPLE rows sharing one `child_id` (proven by `run.sh`'s own existing provisioning-row-then-status-row pattern), and the join MUST reduce these to exactly one effective row per `child_id` — the LAST-appended one — before applying its exclusion rule. `ledger.js` itself is untouched (no update/upsert primitive added). PROP-101d's own fixture is extended to cover the duplicate-`child_id` case. |
| FIND-302 + FIND-303 | critical | REQ-101's balance lookup is redefined from a coordinator-local `fs.readFile` of a per-citizen `telemetryPath` (which structurally cannot reach a REQ-301-mandated remote child's own disk) to a NEW, registry-driven, coordinator-run PUBLIC-RPC balance query keyed on each citizen's `walletAddress` — generalizing `~/anicca/skills/self/telemetry-collect.sh`'s own already-proven, host-location-agnostic RPC-by-address pattern from 3 hardcoded instances to a registry-driven loop. `telemetryPath` is REMOVED from REQ-105's schema. Separately, REQ-403's LIVE wallet-comparison check (which depends on `resolve-identity.mjs`'s pure-local-filesystem resolvers and therefore has the same structural limitation) is explicitly SCOPED to co-located instances only for this increment (today: automaton + Franklin) — a cloud-hosted spawned child is exempt from the live check until a future increment adds a genuine remote-audit mechanism; REQ-403's STATIC grep-sweep half is unaffected and continues to cover a remote child's deployed source (which boots from the SAME git-cloned repo the grep already runs against). |
| FIND-304 | major | A cross-file disambiguation note is added wherever REQ-206/REQ-305 describe `buildChildSpec`'s returned row: that row's pre-existing, unmodified `wallet` field (a bare address STRING, `child-spec.js:37`) is a completely separate field, in a completely separate file/schema, from `citizens.json`'s `wallet` field (a boolean presence-flag object, REQ-105) — the two share a name only by coincidence; neither file is renamed (same discipline FIND-104 already established for `wallet`/`walletAddress` within `citizens.json` itself). |
| FIND-305 | major | REQ-306's false claim that USD-price normalization reuses "already-available" infrastructure is corrected: `akt-treasury.sh` has no live USD price query (its `P_mint≈0.66` is a one-time historical comment, not a callable rate), and no NOS/SOL/USD or AKT/USD utility exists anywhere in this codebase. REQ-306 now honestly specifies a MINIMAL, genuinely NEW price-fetch step (one public spot-price API call per native token), reusing the exact, already-proven, already-used PATTERN this codebase already applies three times for ETH-USD/SOL-USD (`telemetry-poster.mjs::ethPrice()`, `telemetry-post-franklin.mjs::solPrice()`, `execute-invest.mjs`'s own `ethPrice()`) rather than inventing a bespoke oracle design. |

## Changelog (iteration 4 spec review → iteration 5)

Iteration 4's spec review FAILed with 5 NEW findings (3 critical, 2 major — FIND-401/402/403/404/405;
all 15 prior findings across iterations 1-4 were reconfirmed genuinely resolved against the real,
current source). Each is resolved by a specific, cited design decision, grounded in a full read of
every real artifact these findings cite (`~/anicca/skills/self/spawn-child/`'s `SKILL.md`,
`config.json`, `lib/akt-cost-gate.js`, `sdl/child.yaml`; `~/anicca/skills/self/spawn/`'s `run.sh`,
`scripts/cloud-init.sh`, `scripts/deploy-akash.sh`, `lib/ledger.js`; and a live check of the installed
`provider-services`/`nosana` CLIs' own `--help` output, performed 2026-07-07):

| Finding | Severity | Resolution |
|---|---|---|
| FIND-401 + FIND-402 | critical + critical | The previously-undiscovered sibling skill `~/anicca/skills/self/spawn-child/` is now cited as reused prior art (Scope section, REQ-303 below): it is a narrow, read-only Akash funding-READINESS gate (`lib/akt-cost-gate.js::computeSpawnGate`, already unit-tested) plus a corrected, image-independent SDL template — it does not itself deploy or inject secrets. Separately, and more substantially: REQ-201/301/302/303/304 are corrected to specify a REAL two-phase provisioning sequence for BOTH of this feature's cloud targets — boot the host/lease with ZERO secret material in its public boot config (Akash SDL `env:`, Nosana job command — this was ALREADY correct in the existing artifacts, never a gap), THEN, only after the host/lease is confirmed running, inject the child's own pre-generated wallet material via a NEW, per-provider, authenticated post-boot channel this feature's own orchestration adds: Akash via `provider-services lease-shell <service> "cat > /opt/anicca.env" --stdin` (a real, confirmed-present CLI primitive, `provider-services lease-shell --help`, 2026-07-07); Nosana via `nosana job ssh <job> [port]` (a real, confirmed-present CLI primitive — an actual SSH shell into the running job, `nosana job ssh --help`, 2026-07-07). `deploy-akash.sh`/`akt-treasury.sh` themselves remain byte-identical/unmodified (PROP-303a's claim is preserved, now explicitly SCOPED to those two scripts only); the secrets-injection step is NEW orchestration code this feature adds on top of them, tested as new (not claimed as already-proven reuse). REQ-304 is corrected to drop its false "single-signer, single-transaction" characterization of AKT funding specifically (that claim remains accurate for the same-chain gas-seed transfer and for a same-chain shelter-cost transfer where the funding citizen's native chain already matches the target cloud's native currency) and instead cites the REAL, already-documented multi-hop route `spawn-child/config.json`'s own `funding_route` field specifies for Akash (Jupiter SOL→USDC, then Skip API 4-hop `smart_relay` USDC(solana)→AKT(akashnet-2) via `noble-1`/`osmosis-1`) — reusing that already-vetted route rather than re-deriving a same-chain assumption that does not hold for either of the colony's two actual citizen wallets (neither natively holds AKT). Honesty note (see RESOLUTION-NOTES.md): the pre-existing `~/anicca/skills/self/spawn/scripts/cloud-init.sh`'s own header comment ("Secrets are SCP'd to /opt/anicca.env after boot") is cited here ONLY as the established SECURITY PATTERN precedent (boot-with-zero-secrets, inject-post-boot) — a direct read of `run.sh` confirms NO actual `scp` call exists anywhere in its DO path yet either; that gap is honestly out of scope for THIS feature (DO is not one of REQ-302/303's two cloud targets) and is not claimed as "already proven" anywhere in this revision. |
| FIND-403 | major | REQ-303 now honestly acknowledges that neither `deploy-akash.sh`'s inline default SDL nor `spawn-child/sdl/child.yaml` sets `HOME`/`ANICCA_HOME` in their `env:` block (confirmed by direct read) — this is corrected by specifying that this feature's own child-specific SDL variant (reusing the external template's structure, per REQ-303) adds ONE new, explicit `env:` line, `HOME=/root` (matching `node:22-bookworm`'s own default root-user home, made EXPLICIT rather than relied-upon-implicitly, per PROP-203c's own "never a base-image default" requirement), acknowledged here as a genuinely new, small, necessary SDL modification — the same honesty pattern FIND-305 already established for the price-oracle fix. |
| FIND-404 | critical | REQ-101 now explicitly specifies that a citizen record carrying BOTH `walletAddress.evm` AND `walletAddress.solana` (the expected shape for every Nosana-path child, per REQ-202) has its balance computed as the SUM of both chains' USD-normalized balances — a deliberate design decision, not an unstated ambiguity — with a new edge case, acceptance criterion, and PROP-101f covering exactly this fixture. |
| FIND-405 | major | REQ-402's "bootstrap_failed" relabeling text now explicitly cross-references REQ-101's already-established last-write-wins reduction by name: the relabeling is implemented as `appendChild`-ing a NEW row with the same `child_id` (never mutating the prior row in place — `ledger.js` remains exactly `{readChildren, appendChild}`), and this new row becomes "the" effective row for that citizen precisely because `filterProductiveCitizens`'s last-write-wins reduction (REQ-101) picks it up on the next read — identical to the clarification FIND-301 already gave REQ-101/REQ-305's own analogous writes. |

## Changelog (iteration 5 spec review → iteration 6)

Iteration 5's spec review FAILed with 4 NEW findings (1 critical, 2 major, 1 minor — FIND-501/502/
503/504; all findings across iterations 1-5 were reconfirmed genuinely resolved against the real,
current source). Each is resolved by a specific, cited design decision, grounded in a full re-read of
`~/anicca/skills/earn/lib/resolve-identity.mjs` and its own test suite
(`runtime/loop/__tests__/resolve-identity.test.mjs`), a live filesystem check of both citizens' real
key-file locations on this coordinator host, a live query against Skip API's own public
`/v2/fungible/route` endpoint (2026-07-07), and a freshly-captured, on-disk `--help` transcript for
both cloud-provider CLIs:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-501 | critical | REQ-105's seed data is corrected: `homeDir` no longer stores the bare, shared `$HOME` value (`/Users/anicca`) for BOTH citizens — it now stores each citizen's REAL, DISTINCT resolved root (automaton: `/Users/anicca/.anicca`; Franklin: `/Users/anicca/.blockrun`), matching `install.sh:26`'s own default and `resolve-identity.mjs`'s own fail-closed gating logic exactly. The prior "co-located ⇒ same `homeDir`, expected not a bug" framing is corrected: co-located (same physical host, REQ-106) does NOT mean "same `homeDir`" — each citizen still has its own distinct `ANICCA_HOME` root even on a shared machine. REQ-403's Acceptance Criteria and PROP-403b are corrected to state the exact real resolution the CORRECTED seed values now produce (verified live against this coordinator host's actual filesystem, key CONTENT never read/printed): `resolveEvmPrivateKey({home:'/Users/anicca/.anicca'})` resolves automaton's real key via the existing legacy-fallback path to `/Users/anicca/.automaton/wallet.json` (confirmed present on disk, 2026-07-07); `resolveSolanaSecret({home:'/Users/anicca/.blockrun'})` resolves Franklin's real secret via the existing legacy-fallback path to `/Users/anicca/.blockrun/.solana-session` (confirmed present on disk, 2026-07-07) — both NON-NULL, distinct files, whereas the ORIGINAL bare-`$HOME` seed value resolved BOTH to `null` for every chain (independently re-derived from the module's own gating logic: `effectiveHome === path.join(HOME,'.anicca')` and `=== path.join(HOME,'.blockrun')` both evaluate FALSE when `home`/`effectiveHome` is the bare `/Users/anicca` value, since neither equals `/Users/anicca` after the `.anicca`/`.blockrun` suffix is appended). REQ-101/REQ-402's balance-lookup design (public-RPC `readCitizenBalances`, keyed on `walletAddress`, never `homeDir` — REQ-101, PROP-105f) is confirmed, explicitly, to be UNAFFECTED by this correction. |
| FIND-502 | major | REQ-304/PROP-304d's citation is split into two, correctly attributed sources: `~/anicca/skills/self/spawn-child/config.json`'s own `funding_route` field literally specifies only the 4-hop bridge, `"solana/8453 -> noble-1 -> osmosis-1 -> akashnet-2 (Skip API smart_relay, 4-hop)"`; the Jupiter SOL→USDC pre-step is `SKILL.md`'s own documented step 1 (lines 61-67), a SEPARATE artifact, never itself part of `config.json`'s field value. The `"solana/8453"` ambiguity is investigated for real via a live query against Skip API's own public route-planning endpoint (`api.skip.build/v2/fungible/route`, 2026-07-07): `8453` is confirmed to be Skip API's own real, valid Base-mainnet `chain_id` (matching this codebase's own `escrow.mjs::CHAIN_ID_BASE_MAINNET`), and a real, computable 4-hop route (`8453 → noble-1 → osmosis-1 → akashnet-2`, via a CCTP transfer as the first hop, no Jupiter step) is confirmed to exist directly from `anicca-a3cdd4`'s own Base-native USDC (the exact contract address `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` already used by `escrow.mjs`) to `uakt` on `akashnet-2` — meaning EITHER citizen's wallet can independently enter this SAME documented route family (Franklin via Solana+Jupiter, automaton via Base+CCTP, skipping Jupiter entirely), not only Franklin's. A new proof obligation, PROP-304e, records this confirmed capability and requires Phase 2/3 to support whichever entry chain matches the actually-funding citizen's wallet. |
| FIND-503 | major | REQ-101's dual-chain balance-summing rule is extended to state explicitly that each populated chain (`walletAddress.evm`/`walletAddress.solana`) fails closed INDEPENDENTLY: if one chain's query fails/times out/returns non-finite while the other succeeds with a real value, the citizen's contribution is `0 (failed chain) + <the other chain's real, successfully-fetched value>` — never the whole citizen collapsing to `0` despite one chain's real, successfully-fetched balance, mirroring how `ethPrice()`/`solPrice()` already fail close at the level of one price fetch, not a whole citizen record. A new proof obligation, PROP-101g, adds a fixture exercising exactly this mixed success/failure case. |
| FIND-504 | minor | A raw, dated `--help` transcript for both `provider-services lease-shell` and `nosana job ssh` is now captured on disk at `reviews/spec/iteration-6/evidence/cli-help-2026-07-07.txt` (both CLIs independently confirmed installed and invoked live, 2026-07-07); REQ-302/303's citations of these CLI primitives now point at this captured file instead of an inline prose quote, so a future Read-only reviewer (no shell access) can verify the claim directly from disk. |

## Changelog (iteration 6 spec review → iteration 7)

Iteration 6's spec review FAILed with 4 NEW findings (2 critical, 2 major — FIND-601/602/603/604; all
findings across iterations 1-6 were reconfirmed genuinely resolved against the real, current source).
Each is resolved by a specific, cited design decision, grounded in a fresh re-read of
`~/anicca/skills/earn/lib/resolve-identity.mjs` and its own test suite
(`runtime/loop/__tests__/resolve-identity.test.mjs`), and a fact question the architect (not this spec
author acting alone) settled by cryptographically re-deriving a real wallet address from its own signing
key material:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-601 | critical | REQ-105's seed data required ZERO change — `anicca-a3cdd4`'s seeded `walletAddress.evm`, `0xB9dd3B67921B354c656523d6851537988F31DD56`, was already correct. Only this section's own PROSE CITATION of its verification method was wrong: it claimed verification "per... this project's own `CLAUDE.md` colony table," but `CLAUDE.md`/`docs/WALLETS.md` had themselves drifted stale after a real 2026-07-07 key rotation (`~/.automaton/wallet.json`'s own `rotatedAt`/`rotationReason` fields confirm this — exposure in `~/.anicca-founder/agents/polymarket-agent/.env` and `~/.openclaw/.env`) and were independently corrected as a SEPARATE documentation fix (commit `18e6ae96a`), not a consequence of this spec. The citation is corrected to the method that was ALWAYS actually used and remains authoritative: a direct CRYPTOGRAPHIC RE-DERIVATION of the address from `~/.automaton/wallet.json`'s real `privateKey` (`viem`'s `privateKeyToAccount`), cross-checked against `colony-status.sh`'s own live on-chain balance query — never a markdown doc alone, precisely because a markdown doc is exactly what just silently went stale. A new proof obligation, PROP-105g, makes this the permanent, binding verification method for every future seed/append. |
| FIND-602 | major | Two purity-boundary SUMMARY tables (behavioral-spec.md's own overview table, verification-architecture.md's Purity Boundary Map) — never touched again after iteration 5's REQ-304 correction — are corrected to match REQ-304/PROP-304e's already-accurate body text: the Akash `uact` funding route is a multi-hop Skip API bridge enterable from EITHER current citizen's own native chain (Franklin via Solana/Jupiter, automaton via Base/CCTP), never Solana-only. A third, incidental stale phrase in REQ-303's own prose ("the Jupiter→Skip-API bridge") is corrected for the same reason. |
| FIND-603 | critical | REQ-403's live-audit worked examples and PROP-403b are corrected from a bare `{home: citizen.homeDir}` invocation shape (which silently depends on the audit script's own ambient `process.env.HOME`) to an EXPLICIT, fully-constructed `env` object (`{home, env: {HOME, ANICCA_HOME}}`) — the exact shape `resolve-identity.mjs`'s own reused test suite actually exercises in all 20 of its cases. A new proof obligation, PROP-403e, requires this explicit-env shape and tests it under a stripped/launchd-style minimal environment. |
| FIND-604 | major | A new proof obligation, PROP-101h, adds the missing dual-wallet-both-chains-fail-simultaneously fixture: a citizen with BOTH `walletAddress.evm` AND `walletAddress.solana` populated, both chains' queries failing at once, asserting `readCitizenBalances` returns exactly `0` — never throws, never `NaN`, never double-subtracts `perCitizenReserveUsd`. |

## Changelog (iteration 7 spec review → iteration 8)

Iteration 7's spec review FAILed with 3 findings (2 critical, 1 major — FIND-701/702/703; all findings
across iterations 1-7 were reconfirmed genuinely resolved against the real, current source). Each is
resolved by a specific, cited design decision, grounded in a fresh re-read of
`~/anicca/skills/self/spawn/lib/registry-path.mjs`'s real current exports (confirmed: at iteration 7 this
module is a PLANNED file, not yet created on disk — its only planned export, per REQ-103, is
`CITIZENS_REGISTRY_PATH`) and `~/anicca/skills/earn/lib/resolve-identity.mjs`'s exact resolution logic:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-701 | critical | REQ-403's "Explicit-env correction" left the coordinator host's own real `$HOME` value as an unresolved placeholder phrase ("sourced from a registry/coordinator constant") with no canonical constant actually defined anywhere — the same class of un-pinned-input hazard REQ-103 already closed for `CITIZENS_REGISTRY_PATH`. A SECOND named constant, `COORDINATOR_HOME`, is now exported from that SAME shared module, `~/anicca/skills/self/spawn/lib/registry-path.mjs` (REQ-403, new "Canonical coordinator-HOME constant" subsection), computed ONCE via Node's `os.homedir()` at module-load time — never `process.env.HOME` read ad hoc, never hardcoded. REQ-403's live-audit script MUST import and use this SAME constant for every `env.HOME` value it passes to `resolveEvmPrivateKey`/`resolveSolanaSecret`. A new proof obligation, PROP-403f (mirroring PROP-103d's structural discipline exactly), requires a source-grep/import-identity check confirming zero independent `os.homedir()`/`process.env.HOME` reads anywhere else in this feature's audit-script code path. |
| FIND-702 | major | PROP-105g is rewritten from a citation-presence check ("the adversary confirms the commit/PR cites a verification method") to an actual mechanical re-derivation: Phase 3 verification now REQUIRES a real script/test that reads the real private-key file in memory (the same `viem`'s `privateKeyToAccount` pattern already used for the automaton wallet), computes the address, and DIFFS it against `citizens.json`'s stored `walletAddress`, failing hard on any mismatch — never merely checking that a commit/PR cites the right KIND of verification. A new explicit carve-out reconciles this with REQ-105's "file EXISTENCE only — content never read/printed" phrase: reading a private-key file's content IN-MEMORY for THIS SPECIFIC re-derivation purpose is explicitly permitted and required (never logging/printing/persisting the raw key itself — only the DERIVED address may ever be logged/compared), distinct from and not contradicting the general "existence only" discipline used elsewhere in this spec. |
| FIND-703 | critical | REQ-105's citizen record schema gains a new field, `coLocatedWithCoordinator: boolean` — both of today's seeded citizens (automaton, Franklin) are seeded `true` (genuinely co-located on the same Mac Mini today); REQ-305's append-on-spawn logic now ALWAYS sets this to `false` for any newly-spawned child (per REQ-301's absolute mandate, every spawned child is cloud-hosted, never co-located — a structural constant, not a judgment call). REQ-403's live-audit enumeration now explicitly filters `citizens.filter(c => c.coLocatedWithCoordinator === true)`, making PROP-403d's "no code path invokes the resolvers against a cloud-hosted child's homeDir" claim mechanically enforceable. REQ-403's EARS clause is reworded to remove its vacuous promise ("before any newly-spawned CO-LOCATED child is permitted... a category REQ-301 makes structurally impossible"): the live-comparison half runs only among citizens with `coLocatedWithCoordinator === true` (today: automaton + Franklin), while every spawned child (always `false`) is structurally excluded from this check's candidate set and covered only by REQ-403's static grep-sweep half. New proof obligations PROP-105h (seed/schema correctness of the new field) and PROP-305f (every REQ-305 append sets it to exactly `false`) are added. |

## Changelog (iteration 8 spec review → iteration 9)

Iteration 8's spec review FAILed with 2 findings (1 critical, 1 major — FIND-801/802; all findings
across iterations 1-8 were reconfirmed genuinely resolved against the real, current source). Each is
resolved by a specific, cited design decision, grounded in a fresh full read of
`~/anicca/skills/earn/lib/resolve-identity.mjs::resolveSolanaSecret`/`readRawSecretFile`,
`~/anicca/runtime/dashboard/telemetry-post-franklin.mjs` (this codebase's own already-proven,
already-working base58-secret → Solana-address derivation pattern), `~/anicca/package.json` (confirming
`@solana/web3.js` is ALREADY a real, existing dependency of this monorepo — no new dependency added),
and a LIVE re-derivation actually performed, 2026-07-07, against Franklin's real
`~/.blockrun/.solana-session` file:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-801 | critical | PROP-105g's only named re-derivation tool, `viem`'s `privateKeyToAccount`, is secp256k1/EVM-only — structurally inapplicable to Franklin's Solana-only seeded record and to every future Nosana-path child (REQ-202 makes a Solana wallet the norm, not the exception, for that path). PROP-105g is corrected to a genuine TWO-BRANCH re-derivation method: EVM via `viem::privateKeyToAccount` against `walletAddress.evm` (unchanged); Solana via `@solana/web3.js::Keypair.fromSecretKey` (fed the real secret's `bs58`-decoded 64-byte form — the EXACT, already-proven conversion `telemetry-post-franklin.mjs` already performs against this SAME file) against `walletAddress.solana` — both already-real dependencies of this monorepo (`@solana/web3.js@^1.98.4` in `~/anicca/package.json`; `bs58@^5.0.0` in `~/anicca/runtime/package.json`, already imported by `telemetry-post-franklin.mjs`), no new dependency introduced. A citizen record with BOTH fields populated (REQ-202's expected Nosana-path shape) MUST pass BOTH branches independently (new PROP-105i). The Solana branch was ACTUALLY, LIVE re-derived against Franklin's real `~/.blockrun/.solana-session` (2026-07-07, `@solana/web3.js@1.98.4`+`bs58@6.0.0` installed to a disposable scratch directory OUTSIDE this repo for the check only): the derived address EXACTLY matches Franklin's seeded `walletAddress.solana`, `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9` — a genuine, real, live-confirmed result, never a hypothetical. The previously weak, unelaborated "OR a live on-chain balance query" escape hatch is also corrected: a balance query may now only be cited as an ADDITIONAL corroboration (as already done for automaton, cross-checked against `colony-status.sh`), never a substitute for the re-derivation — a funded address existing on-chain does not by itself prove the address was correctly derived from a specific private key, a categorically weaker property. |
| FIND-802 | major | The `COORDINATOR_HOME` constant's formal definition (previously introduced only in REQ-403, iteration 8) is moved UP into REQ-105 — the first point in this document's reading order that needs to express "the coordinator host's own real `$HOME`" as a worked-example value — so the symbol is established before ANY literal use anywhere in the document. REQ-403 no longer re-defines the constant; it now only POINTS to REQ-105's earlier definition. Every literal `/Users/anicca` occurrence used for this specific "coordinator's own HOME, passed as `env.HOME`" purpose in REQ-105's worked example and in REQ-403's Seed-data-correction section and Acceptance Criteria is replaced with the symbolic `COORDINATOR_HOME` reference — including the one Acceptance Criteria bullet that had drifted inconsistent with an earlier bullet in the SAME list (one already correctly wrote `COORDINATOR_HOME`, a later one still hardcoded the literal). The literal's current real value is now stated exactly ONCE, parenthetically, at its one definition point in REQ-105 — never restated or independently re-typed anywhere else in this spec. |

## Changelog (iteration 9 spec review → iteration 10)

Iteration 9's spec review FAILed with 1 NEW critical finding (FIND-901; all findings across
iterations 1-9 were reconfirmed genuinely resolved against the real, current source). Resolved by a
specific, cited design decision, grounded in a fresh full read of
`~/anicca/skills/self/spawn/lib/state-path.js::resolveStateDir({env, home})` (its own header comment:
"Durable state-dir resolution for the colony ledger (children.jsonl) + earn ledger. Fail-closed:
REFUSE any /tmp-rooted path. The 2026-06 self-spawn E2E wrote children.jsonl to /tmp/spawn-live-state,
which the OS tmp-cleaner deleted — the colony record was lost and the verifier could not reproduce
it.") and `~/anicca/skills/self/spawn/run.sh` lines 39-45's own real, current caller of that function
(`STATE_DIR="$("$NODE" -e '...resolveStateDir({ env: process.env, home: process.env.HOME })...')"`;
`COLONY="$STATE_DIR/children.jsonl"` — confirming the real default this produces today on this
coordinator host, `${HOME}/.hermes/state/children.jsonl`, i.e.
`/Users/anicca/.hermes/state/children.jsonl` — deliberately OUTSIDE the `~/anicca` git working tree)
and `~/anicca/.gitignore`'s current patterns (`skills/*/state/`, `skills/*/*/state/`, neither of which
matches `skills/self/spawn/registry/`, confirming that path would be git-tracked by default):

| Finding | Severity | Resolution |
|---|---|---|
| FIND-901 | critical | REQ-105's single `citizens.json` artifact — previously BOTH "a single, versioned JSON registry file" seeded once with fixed literal data AND, per REQ-305, a live runtime-append target forever after, sitting at a hardcoded path INSIDE the `~/anicca` git working tree (`~/anicca/skills/self/spawn/registry/citizens.json`) — is SPLIT into TWO distinct artifacts, reconciling the "versioned seed vs. live-append target" tension this project's own routine, frequently agent-automated `git pull`/`git checkout <branch>`/`git worktree add\|remove` operations on this SAME repo (`CLAUDE.md`/`worktree.md`) could otherwise silently conflict with, overwrite, or lose: (1) a git-tracked SEED TEMPLATE, `~/anicca/skills/self/spawn/registry/citizens.seed.json` — committed to git, read-only, NEVER mutated at runtime, existing purely to define the fixed literal starting content REQ-105 already specified; and (2) the actual LIVE, mutable runtime file, resolved via a NEW exported constant `CITIZENS_REGISTRY_PATH` (`~/anicca/skills/self/spawn/lib/registry-path.mjs`, alongside `COORDINATOR_HOME`) as `path.join(resolveStateDir({env, home}), 'citizens.json')` — REUSING, not reimplementing, the SAME `resolveStateDir({env, home})` mechanism `~/anicca/skills/self/spawn/lib/state-path.js` already exports and `run.sh` already calls for `children.jsonl`'s own durable location (today: `~/.hermes/state/children.jsonl`, so `CITIZENS_REGISTRY_PATH` resolves, by the identical mechanism, to `~/.hermes/state/citizens.json`) — a DURABLE, OUT-OF-GIT-TREE location, immune to every routine git operation above, exactly as `children.jsonl` already is. On first access, if `CITIZENS_REGISTRY_PATH`'s file does not yet exist, THE SYSTEM initializes it by copying `citizens.seed.json`'s content VERBATIM — a ONE-TIME bootstrap, never an ongoing sync — after which every REQ-305 runtime append happens ONLY at this durable location; the git-tracked seed template is never read from or written to again. REQ-103's lock `statePath`, REQ-105's own registry read, and REQ-403's audit enumeration ALL now cite this SAME durable `CITIZENS_REGISTRY_PATH` — never the git-tracked seed template's path. Two new proof obligations close this gap: PROP-105j (structural/Tier-0 — the git-tracked seed template is NEVER written to by any runtime code path) and PROP-105k (Tier 0 structural — `CITIZENS_REGISTRY_PATH`'s construction always routes through `resolveStateDir`, never a literal path inside the repo — PLUS a Tier 2 live test — a real `git checkout`/`git worktree add`/`git pull` on `~/anicca` does NOT affect the durable `citizens.json`'s content); see `verification-architecture.md` for both. **[iteration 11 correction, FIND-1001]: this iteration's "on first access, IF the file does NOT yet exist, copy" framing was itself a check-then-act (TOCTOU) race — see the iteration 11 changelog and REQ-105's corrected, ATOMIC exclusive-create bootstrap below.]** |

## Changelog (iteration 10 spec review → iteration 11)

Iteration 10's spec review FAILed with 2 findings (1 critical, 1 major — FIND-1001/1002; all findings
across iterations 1-10 were reconfirmed genuinely resolved against the real, current source). Each is
resolved by a specific, cited design decision, grounded in a full re-read of
`~/anicca/skills/economy/gig/lib/lock.mjs`'s real `tryCreateLockFile` implementation and its own header
comment (documenting a REAL prior double-pay bug caused by an analogous check-then-act gap) and a
re-read of this SAME feature's own `verification-architecture.md` Purity Boundary Map entries for
`resolveStateDir` and `registry-path.mjs`:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-1001 | critical | REQ-105's "one-time bootstrap" step is corrected from a check-then-act ("IF the file does NOT yet exist, THEN copy") — a classic TOCTOU race REQ-103's own `"colony-spawn"` lock does NOT protect (that lock's critical section starts at REQ-201's identity generation, per REQ-103's own Acceptance Criteria, never at REQ-101's earlier registry READ that triggers the bootstrap) — to a SINGLE atomic POSIX exclusive-create operation (`fs.open(CITIZENS_REGISTRY_PATH, 'wx')`, `O_CREAT\|O_EXCL`), the SAME primitive `lib/lock.mjs::tryCreateLockFile` already uses to close an identical class of race (that module's own header comment: two concurrent `gig_verify_and_pay(true)` calls both read status `'delivered'` before either wrote back, and both settled a real on-chain payout — the escrow was drained twice). Because POSIX exclusive-create can only ever succeed against a file that is truly nonexistent at the instant of the call, at most ONE writer, ever, successfully creates the durable file from the seed template; every other/later caller's exclusive-create fails with `EEXIST` and that caller writes nothing, simply reading the existing file as-is — this is true whether the "existing file" is another racer's just-completed bootstrap OR a real, already-appended REQ-305 citizen record, closing both the concurrent-bootstrap race AND the late-bootstrap-overwrites-a-real-append hazard in the SAME atomic step. A new proof obligation, PROP-105l, adds both concrete race fixtures (two-fixture: concurrent first-access race; late-bootstrap-after-real-append). |
| FIND-1002 | major | `verification-architecture.md`'s Purity Boundary Map row for the new `registry-path.mjs` module (`CITIZENS_REGISTRY_PATH`/`COORDINATOR_HOME`) is corrected from "Pure Core" to "Effectful Shell" — `CITIZENS_REGISTRY_PATH` is built from `resolveStateDir`, which this SAME table already (correctly) classifies "Effectful Shell" two rows away, and `COORDINATOR_HOME` is built from Node's `os.homedir()`, a real OS/environment read, not a deterministic computation over its own inputs. A new proof obligation, PROP-105m, adds the missing Tier-2 (real-environment-dependent) proof that `COORDINATOR_HOME` genuinely tracks the real process environment's `os.homedir()` value rather than being treated as a fixed, zero-I/O constant — mirroring the rigor PROP-403e/PROP-403f already apply to this SAME module's other, correctly-classified properties. |

## Changelog (iteration 11 spec review → iteration 12)

Iteration 11's spec review FAILed with 2 findings (1 critical, 1 major — FIND-1101/1102; all findings
across iterations 1-11 were reconfirmed genuinely resolved against the real, current source). Each is
resolved by a specific, cited design decision, grounded in a full re-read of
`~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn`'s real, current implementation:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-1101 | critical | REQ-102's `decideColonySpawn` and REQ-305's failure-cap edge case previously described DIRECTLY CONTRADICTORY cooldown-consumption rules that could not both be satisfied by one implementation (REQ-102's own EARS clause claimed a failed attempt restarts the FULL cooldown "success OR failure," while REQ-305 claimed a failed attempt is EXEMPT from consuming the cooldown up to a cap of 3) — and REQ-102's own pinned `decideColonySpawn` signature used a single scalar `lastSpawnAttemptMs`, which structurally cannot express "how many of the recent attempts were failures," making REQ-305's cap-of-3 rule unimplementable against REQ-102's own contract. This is fixed by extending `decideColonySpawn`'s signature from the scalar `lastSpawnAttemptMs` to a richer `recentSpawnAttempts: Array<{ts: number, outcome: "success"\|"failure"}>` — reusing the SAME array-scan discipline `~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn` already proves out for its own rate-limit check (`children.some(c => typeof c.spawned_ms === "number" && c.spawned_ms >= windowStart)`, confirmed by direct read, 2026-07-07), generalized from "an array of successes only" to "an array of attempts, each carrying its own `outcome`." The ONE reconciled rule both REQ-102 and REQ-305 now describe: a SUCCESSFUL attempt within `SPAWN_COOLDOWN_DAYS` is ALWAYS a hard cooldown gate, regardless of how many failures also occurred in the same window; a FAILED attempt is cooldown-EXEMPT strictly below `FAILURE_COOLDOWN_CAP` (default `3`, the SAME cap REQ-305 already specified) but becomes cooldown-TRIGGERING, identically to a success, once the cap is reached within that same window — closing REQ-305's own "engineer repeated failures to attempt unlimited spawns" gap. REQ-102's EARS clause, Edge Cases, and Acceptance Criteria, and REQ-305's EARS clause and Edge Case, are both rewritten to state this IDENTICAL reconciled behavior. PROP-102b and PROP-305c (verification-architecture.md) are corrected to test the SAME reconciled logic from their respective sides (success-triggers-cooldown vs. failure-cap-triggers-cooldown), and a new proof obligation, PROP-305g, adds the exact "3 failures reached, cooldown now applies" boundary fixture (2 failures → still eligible; 3 failures → rate-limited), distinct from PROP-305c's own "3 failures then a 4th attempt" fixture. |
| FIND-1102 | major | REQ-304's own edge case already specifies, as real supported behavior, that a spawn can proceed via multi-citizen sequential co-funding (two separate single-signer transfers from two different citizens' own wallets, landing on the SAME child wallet, when no single citizen alone has enough surplus) — but no proof obligation anywhere exercised this SUCCESS path; PROP-304c only tested the BLOCKED path (no single citizen sufficient, aggregate insufficient too — a distinct scenario). A new proof obligation, PROP-304f, is added with a concrete fixture: citizen A transfers a partial amount, citizen B transfers the remaining amount sequentially (never simultaneously) to the same child wallet, and the child wallet's final balance equals the FULL required funding amount — asserting the spawn proceeds and both transfers are independently traceable in the funding ledger (each carrying its own paying citizen's identity, per REQ-304's existing memo/log requirement). REQ-304's own Acceptance Criteria gains a matching new bullet describing this success path explicitly, plus a clarifying rule that the per-transfer ceiling check applies to EACH citizen's own transfer against THAT citizen's own certified contribution, never a single combined ceiling checked against the whole aggregate for one citizen's individual transfer (closing the ambiguity the review's own evidence raised about how PROP-304b's ceiling check interacts with a SUM of two transfers). |

## Changelog (iteration 12 spec review → iteration 13)

Iteration 12's spec review FAILed with 2 findings (1 critical, 1 major — FIND-1201/1202; all findings
across iterations 1-12 were reconfirmed genuinely resolved against the real, current source). Each is
resolved by a specific, cited design decision, grounded in a full re-read of REQ-103's own three
scope-statements (EARS clause, statePath prose, Acceptance Criteria) side by side and of REQ-304's own
FIND-1102 resolution against REQ-101's actually-specified functions:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-1201 | critical | REQ-103's `"colony-spawn"` lock critical section previously carried THREE mutually inconsistent scopes within the SAME requirement — its EARS clause said "REQ-201's identity generation and beyond" (open-ended), its own statePath prose said "REQ-101 through REQ-305", and its binding Acceptance Criteria said only "REQ-201 through REQ-205, and the decision to proceed into REQ-3xx" (textually excluding REQ-206's ledger-row assembly, REQ-304's funding transfer(s), and REQ-305's append) — the narrowest of the three being what a Phase 2 implementer/Phase 3 verifier actually builds/tests against, and insufficient to prevent a genuine STAGGERED double-spawn/double-funding race (a second evaluator arriving after a first evaluator releases the lock post-REQ-205 but while its REQ-304/REQ-305 are still executing). All three statements are corrected to state the IDENTICAL scope: the lock is held from REQ-201 through REQ-305's ledger append actually completing, never released earlier. A new proof obligation, PROP-103e, adds the missing staggered-timing fixture (a delayed REQ-304 funding step, with a second evaluator's lock-acquire attempts failing throughout the entire delay), and the Gate's item (2) (verification-architecture.md) is corrected to require this fixture in addition to PROP-103a's simultaneous-race fixture. |
| FIND-1202 | major | REQ-304's own FIND-1102 resolution required each citizen's own transfer to be checked against "THAT citizen's own certified surplus-above-reserve contribution", but no function anywhere exposed that value per-citizen — only `computeColonySurplusUsd`'s aggregate SUM existed. A new sibling pure function, REQ-101's `computePerCitizenSurplusUsd({citizens, perCitizenReserveUsd}) → Array<{citizenId, surplusUsd}>`, now exposes exactly that value, one citizen at a time; `computeColonySurplusUsd` is specified to be implemented by calling this function and summing its output (never an independently-maintained second reduce), guaranteeing the aggregate and the per-citizen breakdown can never diverge. REQ-304's ceiling-check Acceptance Criteria now cites this function by name, and a new proof obligation, PROP-101i (verification-architecture.md), tests its per-citizen correctness and its by-construction consistency with `computeColonySurplusUsd`'s own sum. |

## Changelog (iteration 13 spec review → iteration 14)

Iteration 13's spec review FAILed with 1 finding (major — FIND-1301; all findings across iterations
1-13 were reconfirmed genuinely resolved against the real, current source). Resolved by a specific,
cited design decision, grounded in a full re-read of REQ-102's own text side by side with every sibling
constant's default statement in the same requirement, and of the real, existing
`~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn`'s own `rateLimitDays` parameter default:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-1301 | major | REQ-102's own `SPAWN_COOLDOWN_DAYS` constant was used repeatedly throughout REQ-102's Cooldown Check and REQ-305's failure-cap reconciliation (5 uses total) but its own default numeric value was never stated anywhere in this document — unlike every sibling constant in the SAME requirement (`MIN_SHELTER_USD` defaults to `5.00`, `SAFETY_MARGIN_MULTIPLIER` defaults to `2`, `FAILURE_COOLDOWN_CAP` defaults to `3`, `MAX_CONCURRENT_SPAWNS` defaults to `1`); the only place a value (`14`) appeared was REQ-402's `BOOTSTRAP_WINDOW_DAYS`, which asserted it was "reusing REQ-102's own `SPAWN_COOLDOWN_DAYS` constant" — a backward citation to a definition that did not actually exist at its cited location. REQ-102's Cooldown Check paragraph now explicitly states `SPAWN_COOLDOWN_DAYS` defaults to `14`, reusing `spawn-decision.js::decideSpawn`'s own existing `rateLimitDays` parameter default (line 11) for consistency with prior art (the SAME citation discipline this spec's own `SAFETY_MARGIN_MULTIPLIER` default already uses for `akt-treasury.sh`'s "2×" convention) — never inventing an unrelated value; REQ-102's Acceptance Criteria gains the matching `cooldownDays` default. REQ-402's existing citation to "REQ-102's own `SPAWN_COOLDOWN_DAYS` constant" now correctly resolves to a default REQ-102 actually states. A new proof obligation, PROP-402e (verification-architecture.md), verifies `BOOTSTRAP_WINDOW_DAYS` and `SPAWN_COOLDOWN_DAYS` are configured to the IDENTICAL value by construction, never merely coincidentally equal — mirroring this spec's own established "identical by construction, never merely close" discipline already used for REQ-206's `seedUsdc`/REQ-204 gas-seed-transfer-amount pair. |

## Changelog (iteration 14 spec review → iteration 15)

Iteration 14's spec review FAILed with 1 finding (critical — FIND-1401; FIND-1301 was reconfirmed
genuinely resolved against the real, current source, including a fresh live read of the cited
`spawn-decision.js`). Resolved by a specific, cited design decision, grounded in a full re-read of
REQ-102's Cooldown Check side by side with REQ-101's own `filterProductiveCitizens` precedent, and of
the real, current `~/anicca/skills/self/spawn/lib/child-spec.js`/`ledger.js`:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-1401 | critical | REQ-102's Cooldown Check pinned `recentSpawnAttempts: Array<{ts, outcome}>` as an input, but no function anywhere derived this array from `ledger.js`'s real rows — unlike REQ-101's exactly analogous need, satisfied by a named, fully-specified pure join function, `filterProductiveCitizens`. Two concrete gaps made this unimplementable: (a) `buildChildSpec`'s real, current returned row (confirmed by direct read) carries no generic timestamp field at all, and REQ-305 only ever set a timestamp field, `active_since`, on the SUCCESS path — never on a `"failed"`/`"provisioning"` row — so no cited data source existed anywhere for a failed or in-flight attempt's `ts` value; (b) the status→outcome mapping was never stated for a LATER `"bootstrap_failed"` relabeling (REQ-402) of an already-`"active"` child, leaving it ambiguous whether that spawn attempt's `recentSpawnAttempts` entry stays `outcome:"success"` or flips to `outcome:"failure"`, and whether a naive per-row mapping could double-count one real attempt as both. Resolved by: (1) REQ-305 now specifies a new field, `attempted_ms`, set to `nowMs` on the very FIRST `ledger.js` row ever appended for a given `child_id` (the initial `"provisioning"` row) and copied forward UNCHANGED onto every later row for that SAME `child_id` (a `"failed"` row, an `"active"` row, or REQ-402's `"bootstrap_failed"` row) — never a freshly-generated timestamp for a follow-up row — following the EXACT precedent this SAME requirement already establishes for `active_since` (an extra field the caller merges into `buildChildSpec`'s base returned object before `appendChild`; `child-spec.js`/`buildChildSpec` itself is NOT modified). (2) A new sibling pure function, same file as `filterProductiveCitizens`, `~/anicca/skills/self/spawn/lib/treasury-gate.mjs::deriveRecentSpawnAttempts({ledgerRows}) → Array<{ts, outcome}>`, groups `ledgerRows` by `child_id` and maps EACH group to exactly ONE entry: `outcome:"success"` PERMANENTLY if that `child_id` ever reached `"active"` (a later `"bootstrap_failed"` row never retroactively flips this, per REQ-102's own existing "a successful attempt is ALWAYS cooldown-triggering" rule); else `outcome:"failure"` if its last (last-write-wins) row is `"failed"`; else EXCLUDED entirely if its last row is still `"provisioning"` (an in-flight attempt, already tracked separately via `childrenProvisioning`/`MAX_CONCURRENT_SPAWNS`, never double-counted here) — one entry per `child_id`, never per raw row, closing the double-counting hazard. (3) REQ-102's real orchestration is now specified to call `deriveRecentSpawnAttempts({ledgerRows: readChildren(...)})` directly, never a hand-rolled reimplementation at the call site (mirroring REQ-101's own `filterProductiveCitizens` integration discipline). Three new proof obligations are added (verification-architecture.md): PROP-102f (Tier 1, the four-case unit fixture: a plain failure, a plain success, a success-then-`bootstrap_failed` attempt that must remain `outcome:"success"` with its ORIGINAL `attempted_ms` and must never also appear as a second, extra failure entry, and an in-flight `"provisioning"`-only attempt that must be excluded entirely), PROP-102g (Tier 1/2, confirming the real orchestration calls `deriveRecentSpawnAttempts` over real `readChildren` output rather than reimplementing the logic inline, mirroring PROP-101d/PROP-101e's own real-derivation discipline), and PROP-305h (Tier 0, confirming `attempted_ms` is set on the first row per `child_id` and copied forward unchanged onto every later row for that `child_id`, including REQ-402's `"bootstrap_failed"` row) — and the Gate's item (1) is extended to require all three. |

## Changelog (iteration 15 spec review → iteration 16)

Iteration 15's spec review FAILed with 1 finding (critical — FIND-1501; FIND-1401 was reconfirmed
genuinely resolved against the real, current source). The reviewer's own convergence note additionally
mandated a full-spec sweep for the identical failure class, which surfaced one further gap, resolved
preemptively in the same pass:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-1501 | critical | `decideColonySpawn`'s pinned `childrenProvisioning` input — a sibling parameter to `recentSpawnAttempts` in the EXACT SAME function signature — had no specified derivation from `ledger.js`'s real, append-only, duplicate-`child_id`-containing rows, recreating BOTH of FIND-1401's own hazards on this sibling: (a) a naive per-row scan (rather than a last-write-wins reduction first) could double-count, or worse, PERMANENTLY count a child whose stale `"provisioning"` row was later superseded by `"active"`/`"failed"` — silently and permanently blocking all future spawns once even one child has ever been spawned; (b) it was unclear whether a child whose LAST row is `"bootstrap_failed"` (REQ-402) should still count as "in provisioning" (a naive scan might still find its earlier `"provisioning"` row). Resolved by a new sibling pure function, same file as `filterProductiveCitizens`/`deriveRecentSpawnAttempts`, `~/anicca/skills/self/spawn/lib/treasury-gate.mjs::countChildrenProvisioning({ledgerRows}) → number`, which groups `ledgerRows` by `child_id`, reduces each group to its last-appended row (last-write-wins, the identical discipline already established), and counts exactly the groups whose last row's `status` is `"provisioning"` — a group whose last row is `"active"`, `"failed"`, or `"bootstrap_failed"` is NEVER counted, regardless of an earlier `"provisioning"` row for that same `child_id`. REQ-102's real orchestration now calls this function directly over `readChildren`'s real output, never a hand-rolled reimplementation at the call site — mirroring `deriveRecentSpawnAttempts`'s own integration discipline. Two new proof obligations are added (verification-architecture.md): PROP-102h (Tier 1, a four-case unit fixture: a child whose only row is `"provisioning"` → counted; a `"provisioning"` row followed by a later `"active"` row → NOT counted; a `"provisioning"` row followed by a later `"failed"` row → NOT counted; a `"provisioning"`→`"active"`→`"bootstrap_failed"` sequence → NOT counted) and PROP-102i (Tier 1/2, confirming the real orchestration calls `countChildrenProvisioning` over real `readChildren` output rather than reimplementing the count inline, mirroring PROP-102g's own discipline) — the Purity Boundary Map gains a new `countChildrenProvisioning` row, the `decideColonySpawn` row is updated to cite it for `childrenProvisioning`, and the Gate gains a new item (1g) requiring all of the above. |
| (preemptive, found during this iteration's mandated sweep — not independently raised by the adversary) | major | REQ-102's `SPAWN_THRESHOLD_USD` formula named its `MIN_SHELTER_USD` override, `measured_last_shelter_cost_usd`, as sourced from "REQ-303's shelter-cost ledger" in prose only, with no named function specifying how that ledger's multiple, real, append-only entries (the SAME accrual shape `ledger.js`'s own rows already have) reduce to the ONE value actually used — the identical failure class, one step removed. Resolved by naming REQ-303's shelter-cost ledger module explicitly, a new, small, dedicated module `~/anicca/skills/self/spawn/lib/shelter-cost-ledger.js` exporting EXACTLY `{readShelterCostEntries, appendShelterCostEntry}` (the SAME append-only-JSONL, no-update/upsert discipline `ledger.js` already establishes), and a new sibling pure function, same file as `filterProductiveCitizens`, `deriveMeasuredShelterCostUsd({shelterCostLedgerRows}) → number\|null`, which returns `null` on an empty ledger (no real deploy has ever completed — `MIN_SHELTER_USD` stays its provisional `5.00`) or the LAST-appended entry's `settledLeaseCostUsd` otherwise (last-write-wins — never an average, sum, or historical-max across the ledger's accumulated entries, and never the first-ever entry). A new proof obligation, PROP-102j, verifies both branches, and PROP-303c is corrected to cite this function by name rather than an unnamed "threshold computation". |

## Changelog (iteration 17 spec review → iteration 18)

Iteration 17's spec review FAILed with 1 finding (critical — FIND-1601; FIND-1501 and its sweep-found
sibling gap were both reconfirmed genuinely resolved against the real, current source). The reviewer's
own convergence note additionally mandated a genuinely exhaustive, checklist-driven full-parameter sweep
— an explicit per-function, per-parameter classification table, not another free-form re-read — since
three consecutive prior sweeps (iterations 15, 16, and the adversary's own iteration-17 pass) had each
still missed at least one sibling instance of the identical failure class. That sweep surfaced one
further gap, resolved preemptively in the same pass:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-1601 | critical | REQ-202's `needsSolanaWallet({initialSkills, deployTarget}) → boolean` pinned two inputs with no real-system-state binding rule. **(a) `deployTarget`** is now explicitly bound, in REQ-202's own text, to THAT SAME spawn attempt's `selectCloudTarget(...)` (REQ-306) direct return value — never hand-assembled by the calling orchestration, never a stale/earlier attempt's evaluation — mirroring the identical discipline FIND-1401/FIND-1501 established for `recentSpawnAttempts`/`childrenProvisioning`; new proof obligation PROP-202d adds the missing Tier-1/Tier-2 real-derivation integration check (mirrors PROP-102g/PROP-102i). **(b) `initialSkills`** had no specified source anywhere — not a default, not a derivation, not an agent-judgment carve-out; resolved by extending REQ-104's existing agent-judgment carve-out ("what the child's initial goal framing/prompt should say") to explicitly also name `initialSkills` — the spawning agent chooses a new child's starting capabilities together with its goal framing, in the SAME in-envelope decision, never a hardcoded fixed default and never a mechanical full copy of the driving citizen's own current skill roster (this feature's own purpose is a new colony member choosing its own earning strategy, not a structural clone of its parent); new proof obligation PROP-202e adds the structural (Tier 0) check that `initialSkills` is never hardcoded/defaulted inside REQ-202's own orchestration. The Gate's item (4) — which never once cited any of REQ-202's own proof obligations at all — now requires PROP-202a/b/d/e. |
| (preemptive, found during this iteration's own mandated exhaustive sweep — not independently raised by the adversary) | major | REQ-101's `filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays})` — the very function FIND-1401/FIND-1501's own resolutions repeatedly cited as the established precedent for this binding discipline — never itself stated the "never hand-assembled, always the real function's direct return value" rule for its OWN `ledgerRows` (`ledger.js::readChildren()`'s real output) or `citizens` (a real `CITIZENS_REGISTRY_PATH` read) arguments; PROP-102g's own citation claiming to "mirror PROP-101d/PROP-101e's own real-derivation discipline" does not actually hold up under a fresh, skeptical re-read, since both of those obligations test the functions' own internal correctness against fixture inputs, never a real-orchestration binding check. Resolved by adding the identical explicit binding sentence to REQ-101 for `filterProductiveCitizens`'s `ledgerRows`/`citizens` arguments (and, by the same reasoning, `readCitizenBalances`'s `citizens` argument, which the existing prose already implied but never stated with the established phrase); a new proof obligation, PROP-101j, adds the missing Tier-1/Tier-2 real-derivation integration check (mirrors PROP-102g/PROP-102i), and the Gate's item (1b) is extended to require it. |

This closes the fifth instance of this recurring failure class found across iterations 14-17 (see
RESOLUTION-NOTES.md, `reviews/spec/iteration-17/`, for the full per-function, per-parameter
classification table covering EVERY pure function listed in the Purity Boundary Map — no further
UNRESOLVED instance was found beyond the one row above).

## Changelog (iteration 18 spec review → iteration 19)

Iteration 18's spec review FAILed with 1 finding (critical — FIND-1701; iteration 17's own
`priorIterationFindingReconfirmation` confirmed FIND-1601 and its sweep-found `filterProductiveCitizens`
sibling gap both genuinely resolved against the real, current source). The reviewer performed a full,
independent re-derivation of the per-function, per-parameter classification table this project's own
methodology now mandates (not a spot-check of the iteration-17 builder's own table), and found exactly one
discrepancy — this is the SIXTH instance of this recurring failure class across iterations 14-18, found on
`decideColonySpawn` itself, the SAME function whose other two comparable parameters
(`recentSpawnAttempts`/`childrenProvisioning`) were already fixed in the FIND-1101/1401/1501 line of work:

| Finding | Severity | Resolution |
|---|---|---|
| FIND-1701 | critical | `decideColonySpawn`'s `colonySurplusUsd` parameter — its own FIRST-listed parameter, and the single most consequential value the function consumes (gating, alongside the cooldown/concurrency checks, whether ANY spawn happens at all) — had no "never hand-assembled, always the direct return value of X()" binding sentence and no dedicated real-derivation proof obligation, unlike its immediate signature-siblings `recentSpawnAttempts`/`childrenProvisioning`, which both already received this exact treatment in prior iterations. REQ-102's own "multiple evaluations in the same wake cycle" edge case already contemplates more than one `decideColonySpawn` evaluation running per wake — meaning a stale/cached/hand-rolled `colonySurplusUsd` reused across evaluations, or a shortcut inline recomputation that skips `filterProductiveCitizens`'s exclusion logic, was a real, concrete, previously-uncaught hazard. Resolved by adding the identical "never hand-assembled, always the direct return value of X()" binding sentence to REQ-102 for `colonySurplusUsd`, binding it to THAT SAME evaluation's `computeColonySurplusUsd({citizens: filterProductiveCitizens(...), perCitizenReserveUsd})` (REQ-101) call — and by explicitly resolving the "multiple evaluations" edge case for this specific hazard: EACH separate evaluation within one wake MUST call this pipeline fresh, and REQ-103's `"colony-spawn"` lock is explicitly documented as NOT providing this protection (its own statePath prose already states its critical section begins only at REQ-201, strictly after REQ-101/102's evaluation completes — confirmed by direct re-read before asserting this, since a false safety claim here would repeat this spec's own earlier FIND-501 mistake for a different mechanism). A new proof obligation, PROP-102k, adds the missing Tier-1/Tier-2 real-derivation integration check (mirroring PROP-101j/PROP-102g/PROP-102i/PROP-202d exactly), the Purity Boundary Map's `decideColonySpawn` row is updated to cite it, and the Gate's item (1) is extended to require it. |

Separately, per this task's own dispatch, `decideColonySpawn`'s COMPLETE 8-parameter signature was
re-classified one final time with uniform rigor (not merely the one flagged parameter) — see
`reviews/spec/iteration-18/RESOLUTION-NOTES.md` for the full per-parameter closeout table. This confirmed
`spawnThresholdUsd` (DERIVED-BOUND, fully specified formula `MIN_SHELTER_USD * SAFETY_MARGIN_MULTIPLIER`
fed by `deriveMeasuredShelterCostUsd`, already correctly bound), `recentSpawnAttempts`/`childrenProvisioning`
(DERIVED-BOUND, already fixed by FIND-1401/FIND-1501), `cooldownDays`/`failureCooldownCap` (CONSTANT,
already explicitly defaulted at the Acceptance-Criteria level), and `nowMs` (a genuine raw wall-clock
runtime primitive — "the evaluation's own current time at the moment of the call" — needing no derivation,
the identical treatment iteration 17 already gave `selectCloudTarget`'s own four raw I/O-leaf inputs) all
already correctly treated. It surfaced one further, minor asymmetry, closed preemptively in the same pass
(no new FIND number, not independently raised by the adversary): `maxConcurrentSpawns`'s own default
(`1`) was previously stated only in REQ-102's EARS clause, never restated at the Acceptance-Criteria level
the way `cooldownDays`/`failureCooldownCap` both are — a new Acceptance Criteria clause now closes this
(no new proof obligation needed, since `maxConcurrentSpawns`'s behavior is already directly tested by
PROP-102c).

This closes the sixth instance of this recurring failure class found across iterations 14-18 — see
RESOLUTION-NOTES.md, `reviews/spec/iteration-18/`, for the full per-parameter closeout table specific to
`decideColonySpawn`'s own complete signature.

## Scope of this increment (read first)

This is `.vcsdd/features/anicca-agent-economy/specs/SPEC.md`'s **P3** ("spawn — cloud,
treasury-funded script — + $0-bootstrap", SPEC.md §3 P3 / §8 checklist item `P3`), split into its
own feature directory because it is architecturally distinct from the already-`DONE` P2 gig-board
work: P2 proved two EXISTING citizens (Franklin#1↔Franklin#2, both genesis-funded once by Dais'
explicit, one-time, human-approved exception per SPEC.md §9.9) can trade. P3 must instead prove the
colony can **create a brand-new citizen from its own accumulated surplus, with zero further
human-funded injection**, and that the new citizen can earn its own keep. **The genesis exception in
§9.9 does NOT extend to P3** — SPEC.md §0's HARD invariant ("claude-p + 全 human-funded AI は経済圏の
永久非構成員") governs every spawn this feature specifies: funding for a spawn comes exclusively from
self-funded citizens' own accumulated surplus (REQ-101/304), never from claude-p's or any other
human-funded wallet.

This spec covers exactly four requirement groups, mapped 1:1 to the task's four groups:
- **REQ群A (REQ-101..104)**: the deterministic treasury gate — pure arithmetic bookkeeping over the
  colony's aggregate self-funded surplus, not a model judgment call.
- **REQ群B (REQ-201..205)**: new-instance identity generation, reusing the already-proven P2
  mechanisms (`gen-wallet.sh`, `$HOME`/`ANICCA_HOME` isolation, ERC-8004 `register()`, gig-board MCP
  wiring) rather than reinventing them.
- **REQ群C (REQ-301..305)**: cloud deployment via Nosana or Akash — genuinely new for this project
  (never yet executed end-to-end for a spawn), verified against re-fetched, current-as-of-2026-07-07
  documentation before being specified (see citations inline). The Akash leg additionally REUSES a
  previously-undiscovered sibling skill, `~/anicca/skills/self/spawn-child/` (its own `SKILL.md`: "Akash
  self-spawn READINESS gate... narrow, read-only... never moves money"), for its funding-readiness
  arithmetic (`lib/akt-cost-gate.js::computeSpawnGate`) and its corrected, image-independent SDL
  template (`sdl/child.yaml`) — see REQ-303 (added iteration 5, resolves FIND-402).
- **REQ群D (REQ-401..403)**: the $0-bootstrap success/failure criteria and the cross-instance wallet
  non-interference audit that must hold once N ≥ 2 instances (including newly-spawned children) run
  concurrently.

**Explicitly OUT of scope for this increment**: P4 (UBI/mutual-aid/collective self-repair) and P5
(scale/self-host/GitHub graduation) remain separate, later SPEC.md phases and are not specified here.
Rewriting or deleting the pre-existing, architecturally-superseded `~/anicca/skills/self/spawn/`
directory (a 2026-06-16 DigitalOcean + AgentMail single-lineage design predating the Franklin +
ERC-8004 pivot documented in SPEC.md §1.3) is also out of scope: Phase 2 MAY reuse its pure,
still-valid primitives (see the Purity Boundary table below) but replacing its DO/AgentMail-specific
provisioning code is a Phase 2b implementation decision, not something this spec mandates either way.
Reusing those primitives is NOT always "unmodified" — see REQ-206 for the one, small,
backward-compatible exception (`child-spec.js`'s identity-anchor validation). This feature never
extends the DO-specific path (`run.sh --host=do`, `scripts/cloud-init.sh`) to a real spawn — REQ-302/303
are the only two deploy targets this increment specifies — but `cloud-init.sh`'s own header comment
("SECURITY: NO secret VALUES in user_data... Secrets are SCP'd... after boot") IS cited (REQ-303/402
resolution, iteration 5) as the established SECURITY-PATTERN PRECEDENT this feature's own Akash/Nosana
secrets-injection mechanism follows; it is cited for that pattern only, never as a claim that DO's own
SCP step is itself already wired (a direct read of `run.sh` confirms it is not — see RESOLUTION-NOTES.md
for iteration 5).

**Also reconciled, iteration 5 (resolves FIND-402)**: the separate, already-complete, narrower
`~/anicca/skills/self/spawn-child/` skill (a 2026-07-05 Akash-specific funding-READINESS gate + a
corrected SDL template, per its own `SKILL.md`) is REUSED — not rebuilt, not duplicated — by REQ-303's
Akash-specific funding-readiness check (`lib/akt-cost-gate.js::computeSpawnGate`) and by REQ-304's
AKT-funding-route citation (`config.json`'s own `funding_route` field). `spawn-child` itself remains
unmodified; this spec adds no new requirement group for it, since its own SKILL.md already documents it
as complete ("does not need re-building").

**Single-coordinator-host scope constraint (added iteration 2, resolves FIND-003)**: this increment
does NOT build a multi-host colony-spawn architecture. REQ-106 makes this explicit: every REQ-101/
102/103 evaluation (and the resulting REQ-201-305 execution) runs exclusively on ONE, designated
coordinator host — currently the Mac Mini already running automaton's own loop (this project's own
`CLAUDE.md`: "Mac Mini（`anicca-mac-mini-1`...）で直接実行する"). A cloud-deployed child does NOT
itself evaluate the colony-spawn gate in this increment — spawn CHAINING (a child spawning its own
child) is explicitly deferred to a future increment. This is the scope boundary that makes REQ-103's
`lock.mjs` (a local-POSIX-filesystem primitive) and REQ-305's `ledger.js` (a local append-only file)
correct AS SPECIFIED: neither mechanism needs to serialize/record callers on different physical hosts,
because this increment guarantees there is only ever one evaluator host.

## Nosana/Akash documentation re-verification (performed 2026-07-07, before writing REQ群C)

Per the task's explicit instruction not to spec cloud deployment from stale training-data knowledge,
the following was re-checked live via `firecrawl scrape` against the current sites (all URLs fetched
2026-07-07; none were cached/assumed):

| Claim in SPEC.md §1 | Still accurate? | Fresh evidence |
|---|---|---|
| Nosana CLI = `@nosana/cli`, wallet auto-generated, no signup | **Yes, unchanged** | `learn.nosana.com/inference/quick_start.html`: `npm install -g @nosana/cli`; "When you first run the Nosana CLI, a new keypair is generated for you in `~/.nosana/.nosana_key.json`"; job posting = `nosana job post <cmd> --wait --market <address>`, needs SOL+NOS in that wallet, no account/API-key required for this CLI path. |
| Akash = `provider-services` CLI, SDL-based, crypto-wallet-only | **Yes, unchanged** | `akash.network/docs/developers/deployment/cli/`: "The Provider Services CLI (`provider-services`) is the official command-line interface for deploying on Akash Network." Sub-pages (`.../cli/act-mint-burn/`) confirm `akash tx bme mint-act`/`burn-act` (the ACT↔AKT bonding-curve conversion this project's `akt-treasury.sh` already automates) is still the current, documented mechanism — no drift from the already-verified `sandbox-2` E2E this repo's scripts cite. |
| Akash also offers a managed, card-billed Console API | **New finding, not in SPEC.md §1** | `akash.network/docs/developers/deployment/`: Akash now separately documents a "Console API — Managed REST API... managed wallets and credit-card billing. No private keys, crypto, or blockchain client required." **This path is explicitly REJECTED for this feature** (human card + managed custody violates human-zero); REQ-303 binds exclusively to the CLI/`provider-services` (self-custody) path, never the Console API. |
| ACT (`uact`) is pegged 1:1 to USD | **Not true — corrected** | Neither the CLI docs nor the mint/burn page states a fixed peg; `akash tx bme mint-act` converts AKT→ACT at a floating bonding-curve rate (this repo's own `akt-treasury.sh` comment already documents an observed `P_mint≈0.66` — i.e. NOT 1:1). REQ-102's threshold below is deliberately built to avoid assuming any fixed ACT/USD or AKT/USD rate. |
| Akash `provider-services` exposes an authenticated exec-into-running-lease primitive | **New finding, iteration 5 (resolves FIND-401); evidence captured to disk, resolves FIND-504** | `provider-services lease-shell --help` (installed CLI, invoked live 2026-07-07) — a real, present primitive (`--stdin` flag confirmed), the Akash analog of an authenticated SSH exec channel into a running container. The raw, complete, dated transcript is captured on disk at `reviews/spec/iteration-6/evidence/cli-help-2026-07-07.txt` (this feature's own review directory) — a future Read-only reviewer (no shell access) can verify this claim directly from that file, never from this inline prose alone. Never previously cited anywhere in this spec before iteration 5. |
| Nosana CLI exposes an authenticated exec-into-running-job primitive | **New finding, iteration 5 (resolves FIND-401); evidence captured to disk, resolves FIND-504** | `nosana job ssh --help` (installed CLI, invoked live 2026-07-07) — a real, present primitive (`Usage: nosana job ssh [options] <job> [port]`, an actual SSH shell proxied through Nosana's own relay). The raw, complete, dated transcript is captured on disk at `reviews/spec/iteration-6/evidence/cli-help-2026-07-07.txt` alongside the Akash transcript above — a future Read-only reviewer can verify this claim directly from that file. Never previously cited anywhere in this spec before iteration 5; the exact non-interactive (single-command) invocation shape is not independently re-verified beyond this `--help` output in this revision (see REQ-302). |

No other drift was found: both CLIs, both wallet models (Solana-keypair-auto-gen for Nosana,
`provider-services`+SDL for Akash), and this repo's existing `deploy-akash.sh`/`akt-treasury.sh`
scripts remain aligned with current upstream documentation.

## Purity boundary analysis (overview — file/function detail lives in verification-architecture.md)

| Concern | Classification | Why |
|---|---|---|
| Colony self-funded citizen filter | **Pure core (existing, reused unmodified)** | `~/anicca/skills/_shared/lib/is-self-funded.mjs::isSelfFunded(agent)` — already implements exactly the "own wallet + own-funded fuel + zero human deps" test this feature's REQ-101 needs to decide which balances even count toward the colony surplus. No new judgment logic is written; REQ-101 calls this existing, already-tested function on each RECORD supplied by REQ-105's registry (below) — `isSelfFunded()` itself is untouched; only its INPUT source is now specified. |
| Colony citizen registry — SEED TEMPLATE (git-tracked, read-only; new, resolves FIND-901) | **Static config asset (git-tracked, NEVER mutated at runtime)** | `~/anicca/skills/self/spawn/registry/citizens.seed.json` — a brand-new, git-tracked file created fresh by this feature, holding the FIXED LITERAL 2-entry starting array (`{id, wallet: {evm?: boolean, solana?: boolean}, walletAddress: {evm?: string, solana?: string}, fuel, humanDependencies, homeDir, coLocatedWithCoordinator: boolean}` records, `telemetryPath` REMOVED, resolves FIND-302). Read exactly ONCE, at the durable runtime file's one-time bootstrap copy (next row) — NEVER written to by any runtime code path this feature adds, and NEVER read again after that bootstrap (PROP-105j). Sharing ZERO state with the pre-existing `~/anicca/skills/economy/ubi/colony-wallets.json` (see below). |
| Colony citizen registry — DURABLE RUNTIME FILE (data source for REQ-101; revised to resolve FIND-101/202/302/304/901) | **Effectful shell (BRAND NEW, dedicated, durable, OUT-OF-GIT-TREE)** | `CITIZENS_REGISTRY_PATH` (`~/anicca/skills/self/spawn/lib/registry-path.mjs`) = `path.join(resolveStateDir({env, home}), 'citizens.json')` — REUSING, not reimplementing, the SAME `resolveStateDir({env, home})` mechanism `~/anicca/skills/self/spawn/lib/state-path.js` already exports and `run.sh` already calls for `children.jsonl`'s own durable location (today: `~/.hermes/state/citizens.json`, alongside `~/.hermes/state/children.jsonl`) — a location immune to `git checkout`/`git worktree add\|remove`/`git pull` on `~/anicca` (resolves FIND-901). Bootstrapped ONCE from `citizens.seed.json`'s content verbatim if absent, then diverges permanently via REQ-305's runtime appends — the git-tracked seed template above is never touched again (PROP-105k). Holds the SAME record shape as the seed template — the BOOLEAN-shaped `wallet` field is the exact shape `isSelfFunded()` already requires (resolves FIND-104's type mismatch; UNRELATED to `child-spec.js`'s own returned-row `wallet` STRING field, resolves FIND-304), `walletAddress` separately carries the real address string(s) and is what REQ-101's `readCitizenBalances` keys its RPC query on, and `homeDir` is an ALREADY-RESOLVED absolute path (never an unresolved `$HOME` template, resolves FIND-202) feeding REQ-403's now co-located-only-scoped audit (resolves FIND-303). This registry deliberately carries NEITHER `status` NOR `active_since` — those lifecycle facts live exclusively in `ledger.js` (see below, resolves FIND-201). Sharing ZERO state with the pre-existing `~/anicca/skills/economy/ubi/colony-wallets.json` (see next row). |
| Pre-existing mutual-aid recipient list (untouched, out of scope) | **Effectful shell (existing, NOT read/written by this feature)** | `~/anicca/skills/economy/ubi/colony-wallets.json` — `ubi.js::distributeAI`'s own recipient-eligibility list ("addresses proven to be real colony members," its own JSDoc), a DIFFERENT purpose than REQ-101's surplus aggregation. Its current 2nd entry is claude-p's own human-funded wallet (`docs/WALLETS.md` lines 49-62). This feature never reads, writes, or repurposes this file — resolves FIND-101's critical finding that an earlier draft wrongly proposed migrating/extending it, which would have risked a human-funded wallet silently entering the colony-surplus aggregate. |
| Colony surplus aggregation | **Pure core (new)** | A sum of `max(0, balance_i - perCitizenReserveUsd)` over self-funded, currently-productive citizens only — deterministic arithmetic over already-fetched balances, no I/O once inputs are supplied (REQ-101). Fed exclusively by `filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays})`, a new pure join function that cross-references REQ-105's registry against `ledger.js`'s rows to exclude `"bootstrap_failed"`/window-overdue children before this sum ever runs (resolves FIND-201). |
| Spawn eligibility gate | **Pure core (new, extends an existing pattern)** | `~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn` already establishes the exact target shape (`{eligible, reason}`, pure, no I/O) this feature's colony-scoped gate follows — REQ-102 is a colony-aggregate generalization of that same pattern, not a new design. Fed by `deriveRecentSpawnAttempts({ledgerRows})`, a new pure sibling function (same file as `filterProductiveCitizens`) that groups `ledger.js`'s rows by `child_id` and maps each group to one `{ts, outcome}` entry, reading `ts` from the new `attempted_ms` field REQ-305 sets on each child's first row and copies forward onto every later row (resolves FIND-1401) — AND, for its sibling `childrenProvisioning` input, by `countChildrenProvisioning({ledgerRows})`, a new pure sibling function (same file, same grouping/last-write-wins discipline) that counts exactly the `child_id` groups whose last row's `status` is `"provisioning"` (resolves FIND-1501) — AND, for `spawnThresholdUsd`'s own `MIN_SHELTER_USD` override, by `deriveMeasuredShelterCostUsd({shelterCostLedgerRows})`, a new pure sibling function (same file) that reads the last-appended entry of the new `shelter-cost-ledger.js` module (resolves the sweep-found gap alongside FIND-1501). |
| Per-child identity record assembly | **Pure core (existing, extended — small, backward-compatible modification, REQ-206)** | `~/anicca/skills/self/spawn/lib/child-spec.js::nextChildId`/`buildChildSpec` — monotonic ID (unchanged) + an identity-anchor validation that now accepts EITHER the old `childInbox` (AgentMail) OR the new `agentEvmAddress`+`agentId` (ERC-8004) pair, never requiring both (REQ-206). This corrects iteration 1's false "reused unmodified" claim (FIND-001): the distinct-wallet assertion and every other existing field/behavior are untouched, and a regression test locks in that today's `childInbox`-only callers still succeed identically. `buildChildSpec`'s OTHER four already-mandatory fields (`parentWallet`, `generation`, `seedUsdc`, `constitutionHash`) are unchanged CODE but now have an explicit spec-level derivation rule each (REQ-206, resolves FIND-204) — the function's own source is not modified for these four; only the caller-supplied values are now specified. |
| Cross-instance spawn mutual exclusion (lock predicate) | **Pure core (existing, reused unmodified)** | `~/anicca/skills/economy/gig/lib/lock.mjs::isLockStale(nowMs, mtimeMs, staleMs)` — the already-adversary-hardened staleness predicate from the P2 concurrency-hardening sprint (`anicca-agent-economy` REQ-101). REQ-103 reuses the SAME generic file-lock module under a new lock key (`"colony-spawn"`), not a new lock implementation. This module's local-POSIX-filesystem guarantee is sufficient ONLY because REQ-106 scopes every evaluator to a single coordinator host this increment (FIND-003) — it is not claimed to solve cross-host mutual exclusion. |
| Cloud target selection (Nosana vs Akash) | **Pure core (new) + Effectful shell (new)** | A pure comparison function `selectCloudTarget({nosanaAvailable, nosanaPriceUsd, akashAvailable, akashPriceUsd}) → "nosana"\|"akash"\|"none"` (deterministic, price-based, never a model judgment — REQ-306) fed by an effectful price/availability query step against each provider's own CLI/API, INCLUDING a genuinely NEW USD-normalization price-fetch step (one public spot-price API call per native token, reusing the exact fail-closed pattern already established by `ethPrice()`/`solPrice()` elsewhere in this codebase — resolves FIND-305's false "already-available oracle" claim; `akt-treasury.sh` has no live USD price query). Resolves FIND-006 (REQ-302/303 presupposed this selection without ever specifying it). |
| Balance/telemetry reads across colony instances | **Effectful shell (revised, resolves FIND-302)** | A NEW, coordinator-run, registry-driven public-RPC balance query, `readCitizenBalances({citizens})`, keyed on each citizen's own `walletAddress` (REQ-105) — generalizing `~/anicca/skills/self/telemetry-collect.sh`'s own existing hardcoded-3-instance RPC-by-address pattern (`erc20()`/`sol()`/`solusdc()` against public RPC endpoints) into a registry-driven loop, so it reaches a REQ-301-mandated cloud-hosted child's balance exactly as readily as a co-located citizen's (a public RPC call does not care where the querying process runs, unlike the coordinator-local `fs.readFile` this mechanism REPLACES — REQ-105's `telemetryPath` field is REMOVED as a result, its sole purpose now served by this walletAddress-keyed RPC read). Real I/O, not inferred. |
| Child EVM wallet generation | **Effectful shell** | `~/anicca/skills/self/spawn/scripts/gen-wallet.sh` — `openssl`+`python3` subprocess, real entropy source, reused unmodified. |
| Child Solana keypair generation | **Effectful shell (new)** | New script analogous to `gen-wallet.sh` but ed25519/Solana-shaped (REQ-202); real entropy source. |
| `$HOME`/`ANICCA_HOME` isolation at process launch | **Effectful shell** | Setting an env var at process spawn time is an OS-level side effect; the isolation PROPERTY it produces (a distinct resolved path) is what REQ-203 specifies and what `~/anicca/skills/earn/lib/resolve-identity.mjs` already relies on for existing instances. |
| ERC-8004 `register()` | **Effectful shell (existing, reused unmodified)** | `~/anicca/skills/economy/gig/lib/identity.mjs::registerIdentity`/`verifyIdentity`, called THROUGH the existing, already-tested `~/anicca/skills/economy/gig/lib/ensure-agent-id.mjs::ensureAgentId` cache-then-verify-then-register-once wrapper (not re-derived from scratch — resolves FIND-004) — a real on-chain transaction (mainnet registry `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` on Base, chain 8453; testnet `0xdc527768082c489e0ee228d24d3cfa290214f387` on Base-Sepolia; both independently re-verified live 2026-07-07 per that file's own header). |
| gig-board `mcp.json` generation | **Effectful shell (new, template reused)** | File write following the exact shape of the already-live, verified `~/.blockrun/mcp.json`. |
| Nosana job deploy | **Effectful shell (new)** | Real `nosana job post` subprocess against a real Solana-settled market; genuinely new for this project (REQ-302). |
| Akash job deploy | **Effectful shell (existing, reused unmodified) + new secrets-injection step (revised iteration 5, resolves FIND-401/402/403)** | `~/anicca/skills/self/spawn/scripts/deploy-akash.sh` + `akt-treasury.sh` — already implemented, already tested against a real sandbox-2 chain per those scripts' own inline evidence references; reused unmodified with a new CHILD-SPECIFIC SDL (NOT byte-identical to `spawn-child/sdl/child.yaml` — that template lacks an explicit `HOME`/`ANICCA_HOME` `env:` line, confirmed by direct read; this feature's own variant adds ONE new line, `HOME=/root`, resolves FIND-403) and `CHILD_ID` (REQ-303). PROP-303a's "zero source modification" claim is scoped to `deploy-akash.sh`/`akt-treasury.sh`'s own script files only, never to this new SDL variant. A genuinely NEW post-lease-active secrets-injection step (this feature's own orchestration code, never a `deploy-akash.sh` modification) delivers the child's pre-generated wallet material (REQ-201/202) via `provider-services lease-shell <service> "cat > /opt/anicca.env" --stdin` (confirmed-present CLI primitive, `lease-shell --help`, invoked live 2026-07-07, raw transcript captured at `reviews/spec/iteration-6/evidence/cli-help-2026-07-07.txt` — resolves FIND-504) — resolves FIND-401's core gap: neither the SDL nor `install.sh` ever provided ANY channel for this. |
| Akash-specific AKT funding-readiness gate (reused, new to this feature — resolves FIND-402) | **Pure core (existing, reused unmodified) + effectful config read** | `~/anicca/skills/self/spawn-child/lib/akt-cost-gate.js::computeSpawnGate({balanceAkt, costAkt, bufferAkt}) → {ready, reason, thresholdAkt, shortfallAkt}` — already implemented, already unit-tested (`lib/__tests__/akt-cost-gate.test.js`); REQ-303 calls it with `costAkt`/`bufferAkt` read from `spawn-child/config.json`'s own real values (`spawn_cost_akt: 25`, `buffer_akt: 1`) BEFORE invoking `akt-treasury.sh`/`deploy-akash.sh` — a DIFFERENT, narrower concern than REQ-102's colony-wide `MIN_SHELTER_USD`/`SPAWN_THRESHOLD_USD` (cross-cloud aggregate USD surplus), never a competing reimplementation of it. |
| Nosana job deploy — post-boot secrets-injection (new, resolves FIND-401's Nosana-side analog) | **Effectful shell (new)** | A NEW orchestration step delivering the child's pre-generated Solana/EVM wallet material onto a `RUNNING` Nosana job via `nosana job ssh <job> [port]` (confirmed-present CLI primitive, `job ssh --help`, invoked live 2026-07-07, raw transcript captured at `reviews/spec/iteration-6/evidence/cli-help-2026-07-07.txt` — resolves FIND-504) — genuinely new, never previously specified; the exact non-interactive invocation shape is confirmed against the actually-installed CLI at Phase 2, not asserted here as already-proven (REQ-302). |
| Shelter-cost funding transfer | **Effectful shell (new)** | A real on-chain transfer from a citizen's own wallet to cover a deploy's escrow/deposit, gated on REQ-102's already-certified amount (REQ-304). For Akash's `uact` requirement specifically, this is a MULTI-HOP transfer via Skip API's `smart_relay` 4-hop bridge into `akashnet-2`, reusing `spawn-child/config.json`'s own already-documented `funding_route` — the SAME bridge is enterable from EITHER of the colony's two current citizens' own native chains: Franklin via Solana (Jupiter SOL→USDC, then a CCTP-first-hop transfer) or automaton via Base (a CCTP-first-hop transfer directly from Base-native USDC, no Jupiter step needed, per PROP-304e's live-confirmed alternative entry) — NOT a single-signer single-transaction transfer for this specific target, since neither citizen's wallet natively holds AKT (revised iteration 5, resolves FIND-402(c); revised iteration 7, resolves FIND-602 — corrected from a stale Solana/Jupiter-only summary that was never updated for iteration 6's PROP-304e correction, to match REQ-304/PROP-304e's own already-accurate body text). |
| Spawn ledger append | **Effectful shell (existing, reused unmodified) + a new registry-append side effect (REQ-105/305)** | `~/anicca/skills/self/spawn/lib/ledger.js::appendChild`/`readChildren` — append-only JSONL, already implemented, unmodified. This feature's own rows are the SOLE canonical owner of each child's lifecycle state (`status`, a new `active_since` field REQ-305 sets the moment a child is first marked `"active"`, and a new `attempted_ms` field REQ-305 sets on the FIRST row ever appended for a `child_id` and copies forward unchanged onto every later row for that `child_id`, resolves FIND-1401) — REQ-402's window check and REQ-101's `filterProductiveCitizens` join both read `active_since`/`status` from THESE rows, and REQ-102's new `deriveRecentSpawnAttempts` reads `attempted_ms`, never from `citizens.json` (resolves FIND-201/FIND-1401). On a successful spawn (child marked `"active"`), REQ-305 ALSO appends a new record to REQ-105's colony citizen registry — the DURABLE runtime file at `CITIZENS_REGISTRY_PATH` (resolved via `resolveStateDir`, e.g. `~/.hermes/state/citizens.json` — NEVER the git-tracked seed template `citizens.seed.json`, and NEVER `economy/ubi/colony-wallets.json`, which this feature never touches — resolves FIND-901) — a new, explicit write path this spec did not previously specify (resolves FIND-002's "how does the registry grow" gap), GATED on an `isSelfFunded()` pre-append check that REFUSES the append if the new record would itself fail that gate (resolves FIND-101's permanent-hazard-closure requirement). |
| $0-bootstrap independent on-chain re-verification | **Effectful shell (new)** | A fresh RPC `eth_call`/balance read performed independently of either trading party's self-report, mirroring the exact method SPEC.md §9.9 already used to confirm Franklin#1's final USDC balance (REQ-401). |
| Wallet mutual non-interference audit | **Effectful shell + static analysis (new)** | A grep-based static source audit (Tier 0) PLUS a live runtime comparison of resolved signing keys across N ≥ 2 concurrently-running instances (Tier 2/3) — reusing the exact "grep all path forms across skill scripts and cron config" method this project's own wallet-rotation work already established (REQ-403). |
| REQ-104 (bookkeeping-only design constraint) | **Not code — a design constraint, verified structurally** | Directly analogous to `anicca-agent-economy`'s REQ-203 ("Design-constraint requirement — bookkeeping only, never judgment"): not independently unit-testable in the normal sense; verified by a Phase 3 structural code read (no scoring/ranking/preference logic anywhere in REQ-101-103's diff), not a runtime assertion. |

---

## Requirements

### REQ群A: 決定論 treasury ゲート

### REQ-101: Colony self-funded surplus aggregation
**EARS**: WHEN any component needs to know how much surplus the colony has available to fund a new
spawn, THE SYSTEM SHALL compute it as the sum, over every **self-funded, currently-productive** citizen
only, of `max(0, balance_i − perCitizenReserveUsd)`, where the candidate citizen list is assembled in
two explicit, separately-owned steps, never a single blended lookup (resolves FIND-201's location
contradiction between REQ-105's registry and REQ-402's ledger-based lifecycle state):
1. READ the candidate citizen array from REQ-105's colony citizen registry (`citizens.json`) — never
   hardcoded inline in this aggregation — and call `isSelfFunded()`
   (`~/anicca/skills/_shared/lib/is-self-funded.mjs`, reused unmodified) on each record's `{wallet,
   fuel, humanDependencies}` sub-object to decide which citizens count as self-funded at all.
2. JOIN that self-funded subset against REQ-402's lifecycle state — which lives EXCLUSIVELY in
   `~/anicca/skills/self/spawn/lib/ledger.js`'s own JSONL rows (`status`, `active_since`), NEVER in
   `citizens.json` (REQ-105's registry is deliberately minimal and carries neither field) — via a new,
   pure join function `filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays}) →
   citizens[]`, zero I/O, matched by `citizens[].id` against `ledgerRows[].child_id`.

   **Deriving `filterProductiveCitizens`'s inputs from real system state (new, resolves the sweep-found
   sibling gap alongside FIND-1601):** `ledgerRows` is never hand-assembled by the calling
   orchestration — it is ALWAYS the direct return value of `ledger.js::readChildren()`'s real output
   (`filterProductiveCitizens({citizens: ..., ledgerRows: readChildren(...), ...})`), mirroring the
   IDENTICAL "never hand-assembled, always the direct return value of X()" binding discipline REQ-102
   (below) establishes for `deriveRecentSpawnAttempts`/`countChildrenProvisioning`'s own `ledgerRows`
   arguments. `citizens` is likewise never hand-assembled — it is ALWAYS the direct return value of a
   real read of REQ-105's colony citizen registry at its canonical `CITIZENS_REGISTRY_PATH` location
   (never an independently reconstructed, cached, or partial citizen list). `computeColonySurplusUsd`'s
   own `citizens` argument and `readCitizenBalances`'s own `citizens` argument (both below) are BOTH, in
   turn, this SAME `filterProductiveCitizens`-filtered array, passed through unchanged — never
   independently re-read from the registry or re-derived a second time — so the citizen set every
   downstream step reasons about can never silently diverge.

   **`ledgerRows` may legitimately contain MULTIPLE rows sharing one `child_id` (resolves FIND-301):**
   `ledger.js` is real, existing, append-only JSONL, reused unmodified — it exports exactly
   `readChildren`/`appendChild`, no update/upsert primitive, and this spec does NOT add one — so every
   lifecycle transition (`"provisioning"` → `"active"`, or → `"bootstrap_failed"`, or a later
   retroactive correction, REQ-402) is recorded by APPENDING A NEW LINE with the SAME `child_id`, never
   by mutating an existing line. This is not hypothetical: the superseded `run.sh`'s own real, existing
   behavior already does exactly this on every spawn attempt (`run.sh:124-140` appends a
   `"provisioning"` row, then a LATER, SEPARATE `appendChild` call at `run.sh:200-205` or
   `run.sh:213-220` appends a SECOND row with the SAME `child_id` and an updated `status`
   (`"seed_failed"` or `"active"`) — proving `readChildren`'s raw output routinely contains duplicate
   `child_id` rows in real production usage). Because JSONL append order is strictly chronological,
   "that row" (the row a citizen with a matching `child_id` is evaluated against, below) MEANS the LAST
   (highest array index / most-recently-appended) row for that `child_id` — last-write-wins is the
   correct, and only specified, reading of "current status." `filterProductiveCitizens` MUST reduce
   `ledgerRows` to exactly one effective row per `child_id` (its last-appended row) BEFORE applying the
   exclusion rule below; it MUST NOT match against the FIRST row for a `child_id` (which would
   incorrectly mean a child is NEVER observed past `"provisioning"`) nor pick nondeterministically among
   duplicates.

   A citizen with NO matching ledger row (e.g. today's two seed citizens, automaton/Franklin, which were
   never spawned via this feature) passes through unfiltered; a citizen WITH a matching ledger row is
   EXCLUDED if that (last-appended) row's `status` is already `"bootstrap_failed"`, OR if that row's
   `status` is `"active"` with no recorded REQ-401 success and `nowMs − active_since >=
   bootstrapWindowDays * 86400000` (the same window REQ-402 itself applies, checked here too as a
   real-time safeguard so REQ-101 never has to wait for REQ-402's own separately-scheduled relabeling
   job to have already run this wake).

`computeColonySurplusUsd({citizens, perCitizenReserveUsd})` then runs ONLY on
`filterProductiveCitizens`'s OUTPUT — never on the raw registry array — where `balance_i` is that
citizen's own most-recently-read liquid balance, obtained via a NEW, coordinator-run, registry-driven
effectful step, `readCitizenBalances({citizens})` (`~/anicca/skills/self/spawn/lib/colony-balances.mjs`),
that queries EACH citizen's balance directly from PUBLIC CHAIN RPC, keyed on that citizen's own
`walletAddress` (REQ-105's registry field, already present) — generalizing, rather than reinventing, the
EXACT mechanism `~/anicca/skills/self/telemetry-collect.sh` already proves works today (that script's
own `erc20()`/`sol()`/`solusdc()` helpers query `base-rpc.publicnode.com`/`api.mainnet-beta.solana.com`
by a hardcoded wallet-address CONSTANT per instance, writing a local `telemetry.json` as a SEPARATE,
unrelated side effect this feature does not depend on) into a REGISTRY-DRIVEN loop over
`citizens[].walletAddress` instead of 3 hardcoded constants (resolves FIND-302: a public RPC balance
read does not care where the querying PROCESS runs, unlike a local `fs.readFile`, so this mechanism
reaches a REQ-301-mandated cloud-hosted child's balance exactly as readily as it reaches a co-located
citizen's — no coordinator-local filesystem access to the child's own disk is ever required).
`telemetryPath` is REMOVED from REQ-105's registry schema (below) — its sole prior purpose (locating
this balance) is now served by this walletAddress-keyed RPC mechanism instead; `telemetry-collect.sh`'s
own separate `telemetry.json` output remains, unmodified, an independent, out-of-scope mechanism for the
public dashboard (not read by this feature). `perCitizenReserveUsd` defaults to `5.00` (reusing, for
consistency, the exact `RESERVE = 5.0` constant `economy/ubi/run.sh` already uses for the same "don't
count money a citizen needs for its own survival" purpose — not a new number invented for this feature).

**Per-citizen surplus, exposed individually (new, resolves FIND-1202; REQ-304's ceiling check depends on
this):** `computeColonySurplusUsd`'s own aggregate is a SUM over per-citizen terms, `max(0, balance_i -
perCitizenReserveUsd)` — but until this revision no requirement exposed any ONE citizen's own term as a
standalone, individually-checkable value, even though REQ-304's own per-transfer ceiling check needs
EXACTLY that ("each citizen's own transfer against THAT citizen's own certified surplus-above-reserve
contribution"). A new, sibling pure function, same file, `~/anicca/skills/self/spawn/lib/
treasury-gate.mjs::computePerCitizenSurplusUsd({citizens, perCitizenReserveUsd}) →
Array<{citizenId: string, surplusUsd: number}>`, runs on the SAME `filterProductiveCitizens`-filtered
input `computeColonySurplusUsd` itself consumes, and returns EACH citizen's own `max(0, balance_i -
perCitizenReserveUsd)` term individually, keyed by `citizenId` (`citizens[].id`) — the IDENTICAL
per-citizen arithmetic `computeColonySurplusUsd` already sums, now also exposed one citizen at a time.
`computeColonySurplusUsd` SHALL be implemented by CALLING this function and summing its returned
`surplusUsd` values — never by an independently-written, separately-maintained reduce — so the aggregate
and the per-citizen breakdown can never silently diverge (the SAME "two independently-derived numbers
must be identical by construction, never merely close" discipline REQ-206's own edge case already
establishes for `seedUsdc`/REQ-204's gas-seed amount). REQ-304's per-citizen ceiling check reads THIS
function's output directly, by name, for its own ceiling comparison — never re-deriving `max(0,
balance_i - reserve)` a second, independent time inside its own funding code.

**Dual-chain balance handling (resolves FIND-404):** A citizen record legitimately carries BOTH
`walletAddress.evm` AND `walletAddress.solana` simultaneously — this is the EXPECTED shape for every
Nosana-path child this feature ever produces (REQ-201 unconditionally generates an EVM wallet for every
child; REQ-202 additionally generates a Solana wallet whenever the child is Nosana-deployed; REQ-305's
own append template records both address strings when both exist). THE SYSTEM SHALL, for such a citizen,
SUM both chains' USD-normalized balances into that citizen's single `balance_i` for this aggregation —
never pick one chain and ignore the other, and never treat the dual-wallet shape itself as a malformed
record. This is a deliberate design decision (the citizen's TOTAL liquid surplus, not one chain's share
of it, is what REQ-102's colony-wide threshold gate needs to reason about), not an unstated ambiguity:
`readCitizenBalances` queries EACH populated `walletAddress` field independently (EVM via the existing
`erc20()`-style public-RPC pattern, Solana via the existing `sol()`/`solusdc()`-style pattern, both
already established by `telemetry-collect.sh`), normalizes each to USD via the same already-proven
spot-price mechanism (`ethPrice()`/`solPrice()`), and returns their SUM as that citizen's one balance
figure — a citizen with only ONE populated `walletAddress` field degenerates to that single chain's own
balance, with no special-casing required.

**Per-chain independent fail-closing (resolves FIND-503):** each populated chain's query fails closed
INDEPENDENTLY of the other — EACH chain is its own separate fail-closed unit, not the citizen record as a
whole. If a citizen's EVM query fails/times out/returns non-finite while that SAME citizen's Solana query
succeeds with a real value (or vice versa), THE SYSTEM SHALL contribute `0` for ONLY the failing chain
and the OTHER chain's real, successfully-fetched value for the rest — the citizen's total contribution is
`0 (failed chain) + <the other chain's real, successfully-fetched, USD-normalized value>`, NEVER `0` for
the whole citizen despite one chain's real, successfully-fetched balance. This mirrors how `ethPrice()`/
`solPrice()` already fail close at the level of ONE price fetch, never at the level of a whole citizen
record — the general fail-closed convention below (a citizen's query fails → that citizen contributes
`0`) is read, for a dual-wallet citizen, as applying PER CHAIN, not to the citizen record as an
indivisible unit.

**Edge Cases**:
- A citizen's public-RPC balance query fails, times out, or returns a non-finite/negative value:
  that citizen contributes **0** to the sum (fail-closed — never treated as infinite/unknown-but-fine),
  matching the existing `tier.mjs`/`catalog-gate.mjs` convention of "unparseable numeric input collapses
  to the safe default," here the safe default being "counts for nothing until it can be read cleanly"
  (resolves FIND-302: this replaces the prior "telemetry.json missing/unreadable" framing, which assumed
  a coordinator-local file read that cannot reach a remote child).
- A citizen's `child_id` has TWO OR MORE matching `ledger.js` rows with different `status` values (e.g.
  a `"provisioning"` row followed later by an `"active"` row for the SAME child): `filterProductiveCitizens`
  uses ONLY the LAST (most-recently-appended) row's `status`/`active_since` — never the first, never an
  arbitrary pick (resolves FIND-301; `ledger.js` is real, append-only, and legitimately produces exactly
  this shape per real spawn attempts, per `run.sh`'s own existing provisioning-row-then-status-row
  pattern).
- A citizen's matching ledger.js row has `status:"active"` but a missing/non-finite `active_since`
  (a malformed row): `filterProductiveCitizens` applies the SAME fail-closed convention as above —
  the citizen is excluded from the productive set until the row is corrected, never assumed fresh.
- Exactly one self-funded citizen exists (current colony state, per §9.9/§9.5): the sum degenerates to
  that single citizen's own surplus-above-reserve; the formula requires no special case for N=1.
- A citizen's on-chain balance is native-token-denominated only (e.g. a Solana citizen's SOL/native-USDC
  holdings, exactly the shape `telemetry-collect.sh`'s own existing `sol()`/`solusdc()` helpers already
  produce for Franklin — `balance_native: {sol, usdc}`, no single `balance_usd` field): THE SYSTEM SHALL
  normalize to USD using the SAME already-proven, already-used spot-price pattern this codebase already
  applies for exactly this purpose (`runtime/dashboard/telemetry-post-franklin.mjs::solPrice()`'s single
  Coinbase SOL-USD spot-price call) rather than inventing a second conversion path — the identical
  discipline `economy/ubi/run.sh`'s own `bal()` helper already applies for its own, differently-scoped
  purpose.
- A citizen's registry record carries BOTH `walletAddress.evm` AND `walletAddress.solana` populated
  simultaneously (the expected Nosana-path shape, REQ-202): `readCitizenBalances` queries and
  USD-normalizes BOTH chains independently and returns their SUM as that citizen's single balance figure
  — never one chain alone, and never treated as a malformed/ambiguous record (resolves FIND-404). A
  citizen with a nonzero balance on one chain and zero on the other still correctly contributes the sum
  (i.e., the nonzero chain's own normalized value) — no special case is needed for the "one chain is
  empty" sub-case.
- **(resolves FIND-503)** A citizen's registry record carries BOTH `walletAddress.evm` AND
  `walletAddress.solana` populated, and exactly ONE chain's query FAILS (times out, errors, or returns a
  non-finite/negative value) while the OTHER chain's query SUCCEEDS with a real, nonzero value: THE
  SYSTEM SHALL fail closed at the level of the INDIVIDUAL FAILING CHAIN ONLY — that citizen's
  contribution is `0 (for the failed chain) + <the successful chain's real, normalized value>`, NEVER `0`
  for the whole citizen. This is a DIFFERENT sub-case from "one chain is empty" (zero balance, both
  queries succeed) directly above — here one query genuinely FAILS while the other genuinely SUCCEEDS,
  and only the failing one collapses to `0`.
- **(resolves FIND-604)** A citizen's registry record carries BOTH `walletAddress.evm` AND
  `walletAddress.solana` populated, and BOTH chains' queries FAIL (time out, error, or return a
  non-finite/negative value) SIMULTANEOUSLY: THE SYSTEM SHALL contribute exactly `0` for that citizen —
  `0 (failed EVM chain) + 0 (failed Solana chain) = 0` — composing the SAME per-chain-independent
  fail-closed rule above to its natural both-fail limit. THE SYSTEM SHALL NEVER throw, NEVER return
  `NaN`/non-finite, and NEVER subtract `perCitizenReserveUsd` more than ONCE for this citizen (the
  reserve is subtracted once from the citizen's single combined `balance_i`, per REQ-101's
  `max(0, balance_i - reserve)` formula — never once per populated chain). This is distinct from
  PROP-101f's both-succeed fixture and PROP-101g's exactly-one-fails fixture; no fixture anywhere in
  this spec previously instantiated the both-fail-simultaneously case for a dual-wallet citizen.

**Acceptance Criteria**:
- Pure function, e.g. `computeColonySurplusUsd({ citizens, perCitizenReserveUsd }) → number`, takes
  already-fetched balance data as input and performs zero I/O itself.
- **(new, resolves FIND-1202)** A new sibling pure function, `computePerCitizenSurplusUsd({ citizens,
  perCitizenReserveUsd }) → Array<{citizenId, surplusUsd}>`, returns one `{citizenId, surplusUsd}` record
  per input citizen (`surplusUsd = max(0, balance_i - perCitizenReserveUsd)`, the IDENTICAL per-citizen
  term `computeColonySurplusUsd` sums); `computeColonySurplusUsd`'s own returned total is confirmed, BY
  CONSTRUCTION (it calls this function internally and sums its output), to equal the SUM of every
  returned `surplusUsd` value on the SAME fixture — the two can never independently drift apart.
- Given a fixture citizen with a nonzero, independently-verifiable balance on BOTH its `walletAddress.evm`
  AND `walletAddress.solana` fields, `readCitizenBalances` returns a total equal to the SUM of both
  chains' own USD-normalized values (each normalized via the existing `ethPrice()`/`solPrice()`
  mechanism) — never either chain's value alone (resolves FIND-404).
- **(resolves FIND-503)** Given a fixture dual-wallet citizen whose EVM query is engineered to
  fail/time out/return a non-finite value while its Solana query genuinely succeeds with a real, nonzero
  value (or the symmetric case, Solana fails and EVM succeeds), `readCitizenBalances` returns a total
  equal to ONLY the successful chain's own normalized value — NEVER `0` for the whole citizen despite the
  other chain's real, successfully-fetched balance.
- **(resolves FIND-604)** Given a fixture dual-wallet citizen whose EVM AND Solana queries are BOTH
  engineered to fail/time out/return a non-finite value SIMULTANEOUSLY, `readCitizenBalances` returns
  exactly `0` for that citizen, `computeColonySurplusUsd` never throws and never returns `NaN`, and
  `perCitizenReserveUsd` is confirmed subtracted exactly ONCE (not once per populated chain) from that
  citizen's zero balance.
- Given two self-funded citizens with balances `$8` and `$3` and `perCitizenReserveUsd=5`, returns
  `max(0,8-5) + max(0,3-5) = 3 + 0 = 3`.
- Given a citizen whose `isSelfFunded()` check returns `false`, its balance (however large) contributes
  `0` regardless of magnitude.
- `filterProductiveCitizens({ citizens, ledgerRows, nowMs, bootstrapWindowDays }) → citizens[]` is a
  pure function, zero I/O, that FIRST reduces `ledgerRows` to at most one effective row per `child_id`
  (the LAST-appended row for that id — last-write-wins, resolves FIND-301), THEN excludes exactly the
  citizens whose (reduced) matching row is `"bootstrap_failed"` or window-overdue-while-`"active"`, and
  passes through unfiltered any citizen with no matching ledger row (resolves FIND-201).
- **(new, resolves the sweep-found sibling gap alongside FIND-1601)** `filterProductiveCitizens`'s
  `ledgerRows` argument is never hand-assembled by the calling orchestration — it is ALWAYS the direct
  return value of `readChildren(...)` (`ledger.js`'s real output); its `citizens` argument is likewise
  never hand-assembled — it is ALWAYS the direct return value of a real read of REQ-105's registry at
  `CITIZENS_REGISTRY_PATH`. `computeColonySurplusUsd` and `readCitizenBalances` both receive this SAME
  `filterProductiveCitizens`-filtered `citizens` array directly, never an independently re-read or
  re-derived one.
- **(new, resolves FIND-1801)** `bootstrapWindowDays` defaults to `14`, identical to REQ-402's own
  `BOOTSTRAP_WINDOW_DAYS` constant (which itself defaults to `14`, reusing REQ-102's own
  `SPAWN_COOLDOWN_DAYS` default) — never independently configurable to a different value, mirroring the
  exact treatment this document's own iteration-18 fix already gave `decideColonySpawn`'s own
  `cooldownDays`/`failureCooldownCap`/`maxConcurrentSpawns` defaults (REQ-102's Acceptance Criteria,
  above).

---

### REQ-102: Deterministic spawn threshold gate
**EARS**: WHEN REQ-101's colony surplus is computed, THE SYSTEM SHALL permit at most one new spawn
attempt when, and only when, `colonySurplusUsd >= SPAWN_THRESHOLD_USD` AND the Cooldown Check below
evaluates to "not on cooldown" AND fewer than `MAX_CONCURRENT_SPAWNS` (default `1`) children are
currently in `"provisioning"` state.

**Cooldown Check, reconciled with REQ-305 (resolves FIND-1101, critical):** the colony maintains
`recentSpawnAttempts: Array<{ ts: number, outcome: "success"|"failure" }>` — one entry per completed
spawn attempt, whichever the outcome — REPLACING a single scalar "last attempt" timestamp, which
cannot express "how many of the recent attempts were failures." This reuses the SAME array-scan
discipline `~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn` already proves out for its
own rate-limit check (`children.some(c => typeof c.spawned_ms === "number" && c.spawned_ms >=
windowStart)`), generalized here from "an array of successes only" to "an array of attempts, each
carrying its own `outcome`" — exactly the richer shape REQ-305's failure-cap rule (below) needs.
`SPAWN_COOLDOWN_DAYS` defaults to `14` (resolves FIND-1301) — reusing
`~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn`'s own existing `rateLimitDays`
parameter default (line 11) for consistency with prior art, rather than inventing an unrelated value —
the SAME precedent this Cooldown Check's own array-scan discipline (above) already reuses from that
module. Given `windowStart = nowMs - SPAWN_COOLDOWN_DAYS * DAY_MS` and `inWindow =
recentSpawnAttempts.filter(a => a.ts >= windowStart)`:
- IF any entry in `inWindow` has `outcome === "success"`: cooldown applies UNCONDITIONALLY (a hard
  gate) — a successful spawn always restarts the full cooldown, regardless of how many failures (if
  any) also occurred in the same window.
- ELSE, let `failuresInWindow = inWindow.filter(a => a.outcome === "failure").length`. A failed
  attempt is cooldown-EXEMPT — it does NOT by itself trigger the cooldown — UNLESS
  `failuresInWindow >= FAILURE_COOLDOWN_CAP` (default `3`, identical to REQ-305's own cap), in which
  case THE SYSTEM SHALL treat the window as under cooldown exactly as it would for a success, closing
  the "engineer repeated failures to attempt unlimited spawns" gap REQ-305's own edge case identifies.

This is the ONE reconciled rule both REQ-102 and REQ-305 describe: a successful attempt is ALWAYS
cooldown-triggering; a failed attempt is cooldown-EXEMPT strictly below `FAILURE_COOLDOWN_CAP` and
cooldown-TRIGGERING once the cap is reached — never two different behaviors.

**Deriving `colonySurplusUsd` from real system state (new, resolves FIND-1701, critical):**
`colonySurplusUsd` is never hand-assembled by the calling orchestration — it is ALWAYS the DIRECT return
value of THAT SAME evaluation's `computeColonySurplusUsd({citizens: filterProductiveCitizens({citizens: <a
real `CITIZENS_REGISTRY_PATH` read>, ledgerRows: readChildren(...), nowMs, bootstrapWindowDays}),
perCitizenReserveUsd})` call (REQ-101) — never a hand-rolled reimplementation of the aggregation at the
call site, and never a stale/earlier evaluation's aggregate carried over from a prior evaluation. This
mirrors the IDENTICAL "never hand-assembled, always the direct return value of X()" binding discipline
this SAME function's own signature-siblings `recentSpawnAttempts`/`childrenProvisioning` already establish
(below), and REQ-202's own `deployTarget` binding establishes for `selectCloudTarget(...)`. This binding is
not cosmetic: `colonySurplusUsd` is the single most consequential value `decideColonySpawn` consumes —
gated only by the cooldown/concurrency checks, it is the number that determines whether ANY spawn happens
at all this wake. A hand-assembled or stale `colonySurplusUsd`, or a shortcut inline recomputation that
skips `filterProductiveCitizens`'s exclusion logic (e.g. accidentally including a `"bootstrap_failed"`
citizen's balance), would silently corrupt this decision without any other check in this spec catching it.

**Each separate `decideColonySpawn` evaluation within one wake cycle MUST call `computeColonySurplusUsd`
fresh (resolves, for this specific hazard, the "multiple evaluations in the same wake" edge case REQ-102's
own edge cases below already contemplate):** REQ-103's `"colony-spawn"` lock does NOT provide staleness
protection for `colonySurplusUsd` and MUST NOT be cited as though it did — REQ-103's own statePath prose
is explicit that "REQ-101's earlier registry read and REQ-102's decision themselves run OUTSIDE the lock,
since REQ-102's gate function is pure and needs no mutual exclusion of its own"; the lock's critical
section begins only at REQ-201's wallet generation, strictly AFTER REQ-101/102's evaluation has already
completed. THE SYSTEM SHALL therefore compute `colonySurplusUsd` via a FRESH `computeColonySurplusUsd(...)`
call (over a fresh `filterProductiveCitizens(...)` call, over a fresh `readChildren(...)`/registry read)
for EVERY separate `decideColonySpawn` evaluation this wake — never reusing an earlier evaluation's
already-returned aggregate, and never caching it across evaluations, however close together in time they
run.

**Deriving `recentSpawnAttempts` from real ledger rows (new, resolves FIND-1401, critical):** nothing
above specifies WHERE `recentSpawnAttempts` comes from at runtime. REQ-101's exactly analogous need
(turning `ledger.js`'s raw rows into an aggregation-ready shape) is satisfied by a named,
fully-specified pure function, `filterProductiveCitizens` — this Cooldown Check gains the identical
treatment. A new, sibling pure function, same file, `~/anicca/skills/self/spawn/lib/
treasury-gate.mjs::deriveRecentSpawnAttempts({ledgerRows}) → Array<{ts: number, outcome:
"success"|"failure"}>`, zero I/O, is THE SOLE mechanism that produces this array, and REQ-102's real
orchestration calls it directly over `readChildren`'s real output
(`deriveRecentSpawnAttempts({ledgerRows: readChildren(...)})`) — never a hand-rolled reimplementation
at the call site (mirroring REQ-101's own `filterProductiveCitizens` integration discipline). It works
as follows:
1. GROUP `ledgerRows` by `child_id` (the same grouping key `filterProductiveCitizens` already uses).
2. For each `child_id` group, `ts` = that group's `attempted_ms` field — a new field REQ-305 (below)
   specifies is set to `nowMs` on the FIRST ledger.js row ever appended for that `child_id` and copied
   forward, unchanged, onto every later row for the SAME `child_id`; it is therefore identical across
   every row in the group by construction, so any row's value suffices, though the group's FIRST
   (earliest-appended) row is the canonical source.
3. `outcome` — IF ANY row in the group ever reached `status:"active"` at some point in its history,
   `outcome:"success"` PERMANENTLY: a LATER `"bootstrap_failed"` row (REQ-402) for that SAME `child_id`
   does NOT retroactively flip this entry to `"failure"`, per this SAME Cooldown Check's own rule above
   that "a successful attempt is ALWAYS cooldown-triggering" — REQ-402's relabeling is a
   productivity/aggregation fact for REQ-101 (via `filterProductiveCitizens`'s OWN, separate reduction),
   never a cooldown-history fact for this function. ELSE, if the group's LAST (last-write-wins) row is
   `status:"failed"`, `outcome:"failure"`. ELSE (the group's last row is still `status:"provisioning"` —
   an attempt genuinely still in flight), EXCLUDE that `child_id` from the returned array entirely: an
   in-flight attempt is already counted, separately, via `childrenProvisioning`/`MAX_CONCURRENT_SPAWNS`
   (above) and must never ALSO appear in `recentSpawnAttempts`, which would double-count it.
4. Exactly ONE entry per `child_id` group is ever returned — never one entry per raw ledger row —
   closing the double-counting hazard a naive per-row mapping would create (e.g. treating a success AND
   its own earlier `"provisioning"` row, or a success AND a later `"bootstrap_failed"` row, as two
   separate attempts).

**Deriving `childrenProvisioning` from real ledger rows (new, resolves FIND-1501, critical):** the
EARS clause above and the `MAX_CONCURRENT_SPAWNS` edge case below both describe what
`childrenProvisioning` MEANS ("how many children are currently in `"provisioning"` state") but — until
this revision — no function anywhere specified HOW this count is computed from `ledger.js`'s real,
append-only, duplicate-`child_id`-containing rows: the exact same raw data source
`filterProductiveCitizens` and `deriveRecentSpawnAttempts` (above) both already correctly derive their
own outputs from. A new, sibling pure function, same file, `~/anicca/skills/self/spawn/lib/
treasury-gate.mjs::countChildrenProvisioning({ledgerRows}) → number`, zero I/O, is THE SOLE mechanism
that produces this count, and REQ-102's real orchestration calls it directly over `readChildren`'s real
output (`countChildrenProvisioning({ledgerRows: readChildren(...)})`) — never a hand-rolled
reimplementation at the call site (mirroring `deriveRecentSpawnAttempts`'s own integration discipline
above). It works as follows:
1. GROUP `ledgerRows` by `child_id` (the SAME grouping key `filterProductiveCitizens`/
   `deriveRecentSpawnAttempts` already use).
2. For each `child_id` group, reduce to the LAST-appended (last-write-wins) row — the SAME reduction
   `filterProductiveCitizens` already performs before applying its own exclusion rule.
3. COUNT exactly the groups whose LAST row's `status` is EXACTLY `"provisioning"`. A group whose last
   row is `"active"`, `"failed"`, or `"bootstrap_failed"` is NEVER counted — regardless of whether an
   EARLIER `"provisioning"` row exists somewhere in that SAME `child_id`'s history — closing both (a) the
   double-counting hazard a naive per-row scan would create, and (b) the permanent-block hazard where a
   child's stale `"provisioning"` row is never superseded in the count once that child resolves to
   `"active"`/`"failed"`, which would otherwise leave `childrenProvisioning >= maxConcurrentSpawns`
   permanently true and silently block every future spawn attempt forever.
4. Return the resulting count as a plain number — never an array, never per-child detail — this
   function answers only "how many," matching `MAX_CONCURRENT_SPAWNS`'s own bare-integer comparison.

`SPAWN_THRESHOLD_USD = MIN_SHELTER_USD * SAFETY_MARGIN_MULTIPLIER`, where:
- `MIN_SHELTER_USD` defaults to `5.00` — a provisional anchor, NOT a live-market-verified figure
  (deliberately, since Nosana/Akash CPU-only small-workload pricing floats with AKT/SOL/NOS market
  price and is not fixed to USD — see the re-verification table above). It reuses the same
  order-of-magnitude anchor as REQ-101's `perCitizenReserveUsd` for internal consistency rather than
  inventing an unrelated number. **This default MUST be superseded by `measured_last_shelter_cost_usd`
  — the actual USD-equivalent cost recorded by REQ-303's shelter-cost ledger after the first real
  deploy — the moment that ledger has at least one entry** (`MIN_SHELTER_USD =
  max(deriveMeasuredShelterCostUsd({shelterCostLedgerRows: readShelterCostEntries(...)}), 5.00)` once
  `deriveMeasuredShelterCostUsd` returns non-`null`; `5.00` alone while it still returns `null`, i.e.
  before any real deploy has ever completed — see REQ-303 for `deriveMeasuredShelterCostUsd`'s own
  definition, added preemptively during this iteration's full-spec sweep alongside the FIND-1501 fix
  above, the identical failure class one step removed).
- `SAFETY_MARGIN_MULTIPLIER` defaults to `2` — reusing the exact "2×" convention already documented in
  this project's own `~/anicca/skills/self/spawn/scripts/akt-treasury.sh` (`ACT_BUFFER_UACT`'s comment:
  "target ACT on hand (≥ 2× min_mint so a few deploys never wait)"), applied here to the same
  subsystem's spawn-funding buffer for consistency, not a newly-invented margin.
- Default `SPAWN_THRESHOLD_USD = 5.00 * 2 = 10.00` until a real measured shelter cost exists, after
  which it recomputes from that measured figure.

This is arithmetic bookkeeping (a numeric comparison against an already-known threshold and an
already-known Cooldown Check result and an already-known in-flight count), not a value judgment about
WHETHER to spawn — see REQ-104.

**Edge Cases**:
- `colonySurplusUsd` is EXACTLY equal to `SPAWN_THRESHOLD_USD`: treated as **eligible** (the boundary
  is inclusive, `>=`, matching the existing `catalog-gate.mjs`/`tier.mjs` "at or above" convention
  already used elsewhere in this codebase for the same class of threshold comparison).
- Two or more spawn evaluations run in the same wake cycle (e.g. because two independently-scheduled
  loops on the SAME coordinator host, per REQ-106, both evaluate the colony-wide gate — this increment
  never has evaluations racing across DIFFERENT physical hosts, see REQ-106): the gate function ITSELF
  is pure and may return `eligible:true` from both evaluations — REQ-103 is what prevents both from
  acting on that `true` result simultaneously; REQ-102 does not need to know about concurrency.
- The Cooldown Check (above) is under cooldown — either a successful attempt is within
  `SPAWN_COOLDOWN_DAYS`, OR `FAILURE_COOLDOWN_CAP` recent failures have accumulated in the same
  window — but `colonySurplusUsd` has grown far past the threshold in the meantime: still **not
  eligible**, `reason:"rate_limited"` — surplus size never overrides an active cooldown (mirrors
  `spawn-decision.js`'s existing ordering: balance → rate-limit → cap).
- Fewer than `FAILURE_COOLDOWN_CAP` failed attempts have occurred within the current window and NO
  successful attempt has occurred within it (resolves FIND-1101): the Cooldown Check does NOT apply
  on failure-count alone — a new attempt remains eligible (surplus/concurrency checks permitting) —
  see REQ-305's own edge case and PROP-305g for the exact boundary fixture (fewer than the cap → still
  eligible; the cap reached → rate-limited).
- `MAX_CONCURRENT_SPAWNS` children are already `"provisioning"` (none yet resolved to `"active"` or
  `"failed"`): not eligible, `reason:"max_concurrent_spawns"`, regardless of surplus/cooldown — a
  slow/stuck provisioning attempt does not silently permit unbounded parallel spawns.
- `colonySurplusUsd` is non-finite/negative due to an upstream computation error: treated as `0`
  (fail-closed — never eligible), matching REQ-101's own fail-closed convention.

**Acceptance Criteria**:
- Pure function, e.g. `decideColonySpawn({ colonySurplusUsd, spawnThresholdUsd, recentSpawnAttempts,
  nowMs, cooldownDays, failureCooldownCap, childrenProvisioning, maxConcurrentSpawns }) → { eligible:
  boolean, reason: "ok"|"insufficient_surplus"|"rate_limited"|"max_concurrent_spawns" }`, no I/O.
  `recentSpawnAttempts: Array<{ ts: number, outcome: "success"|"failure" }>` (resolves FIND-1101 —
  REPLACES the prior single-scalar `lastSpawnAttemptMs`, which could not express "how many of the
  recent attempts were failures"); `cooldownDays` defaults to `14`, identical to `SPAWN_COOLDOWN_DAYS`'s
  own default above (resolves FIND-1301) — never independently configurable to a different value;
  `failureCooldownCap` defaults to `3` — identical to REQ-305's own
  cap, the SAME number, never independently configurable to a different value; `maxConcurrentSpawns`
  defaults to `1`, identical to `MAX_CONCURRENT_SPAWNS`'s own default above — never independently
  configurable to a different value.
- **(new, resolves FIND-1701)** `colonySurplusUsd` is never hand-assembled by the calling
  orchestration — it is ALWAYS the direct return value of THAT SAME evaluation's
  `computeColonySurplusUsd({citizens: filterProductiveCitizens(...), perCitizenReserveUsd})` call
  (REQ-101), never a stale/earlier evaluation's cached aggregate. EACH separate `decideColonySpawn`
  evaluation within one wake cycle calls this pipeline FRESH — REQ-103's `"colony-spawn"` lock does NOT
  cover REQ-101/102's evaluation step (its critical section begins only at REQ-201), so this staleness
  protection can never be attributed to that lock; a stale/cached/hand-rolled `colonySurplusUsd` is a
  real, distinct hazard this binding closes.
- **(resolves FIND-1401)** `recentSpawnAttempts` is never hand-assembled by the calling
  orchestration — it is ALWAYS the direct return value of `deriveRecentSpawnAttempts({ledgerRows:
  readChildren(...)})` (defined above), one entry per `child_id` group, with in-flight
  (`"provisioning"`-only) groups excluded and a group that ever reached `"active"` always mapped to
  `outcome:"success"` regardless of any later `"bootstrap_failed"` relabeling.
- **(new, resolves FIND-1501)** `childrenProvisioning` is never hand-assembled by the calling
  orchestration — it is ALWAYS the direct return value of `countChildrenProvisioning({ledgerRows:
  readChildren(...)})` (defined above): a count of `child_id` groups whose LAST (last-write-wins) row's
  `status` is EXACTLY `"provisioning"` — a group whose last row is `"active"`, `"failed"`, or
  `"bootstrap_failed"` is NEVER counted, regardless of an earlier `"provisioning"` row for that same
  `child_id`.
- Order of checks is surplus → cooldown → concurrency cap (each independently testable at its own
  boundary), matching the existing `spawn-decision.js` ordering convention (a broke colony never
  spawns whatever else is true).
- `colonySurplusUsd = spawnThresholdUsd` exactly → `eligible:true`.
- `colonySurplusUsd = spawnThresholdUsd - 0.01` → `eligible:false, reason:"insufficient_surplus"`.
- A `recentSpawnAttempts` entry with `outcome:"success"` inside the cooldown window → `eligible:false,
  reason:"rate_limited"` UNCONDITIONALLY, regardless of how many (if any) `outcome:"failure"` entries
  also occur in the same window (resolves FIND-1101).
- Fewer than `failureCooldownCap` `outcome:"failure"` entries inside the window, and ZERO
  `outcome:"success"` entries inside the window → the Cooldown Check does NOT apply on failure-count
  alone (resolves FIND-1101).
- `failureCooldownCap` or more `outcome:"failure"` entries inside the window (zero successes) →
  `eligible:false, reason:"rate_limited"` — the failure cap itself becomes a hard gate, identical to a
  success (resolves FIND-1101; see REQ-305's own edge case for the identical rule from that side).

---

### REQ-103: Cross-instance spawn mutual exclusion
**EARS**: WHEN two or more evaluation LOOPS — always running on the SAME single coordinator host per
REQ-106, this increment — independently evaluate REQ-102's gate in the same or an overlapping wake
window and BOTH observe `eligible:true`, THE SYSTEM SHALL ensure that at most ONE of them actually
proceeds past REQ-201's identity generation, and SHALL hold the `"colony-spawn"` lock continuously
through REQ-305's ledger append actually completing (the new citizen durably recorded in
`citizens.json`) — this is the lock's ENTIRE critical section, stated identically here, in this
requirement's own statePath prose below, and in its Acceptance Criteria (resolves FIND-1201: no
"and beyond" open-ended phrasing, and no narrower reading that releases the lock any earlier) — the
other(s) SHALL detect the lock is held, decline to proceed, and log a no-op (never silently duplicate a
spawn, and never queue indefinitely waiting for the lock).

This reuses, unmodified, the same generic per-resource file lock already adversary-hardened for the P2
gig board (`~/anicca/skills/economy/gig/lib/lock.mjs`, including its `isLockStale` pure predicate and
its atomic `fs.rename`-based reclaim fix from that lock's own REQ-101), acquired under a new, distinct
lock key (e.g. `"colony-spawn"`) rather than any gig-specific key — this is a new lock KEY on an
EXISTING lock MECHANISM, not new lock-implementation code. Per REQ-106, this local-POSIX-filesystem
lock is sufficient because every caller in this increment shares the SAME mounted filesystem on the
SAME coordinator host — this requirement does NOT claim to solve mutual exclusion across physically
separate hosts (see REQ-106's own known-limitation edge case for that future scenario).

**Canonical `statePath` (resolves FIND-103; corrected, resolves FIND-901)**: `withGigLock`'s real,
existing signature is `withGigLock(statePath, lockKey, fn, opts)` — `statePath` is a MANDATORY
positional argument, and `lockPaths()` derives the actual lock FILE from BOTH `statePath`'s directory
AND `lockKey` (`path.join(path.dirname(statePath), 'locks', lockKey + '.lock')`), never from `lockKey`
alone. If two call sites passed two DIFFERENT `statePath` values under the same `"colony-spawn"` lock
key, they would resolve to two DIFFERENT physical lock files under two different `locks/` directories
and BOTH could "hold the lock" simultaneously — silently defeating this requirement's entire purpose.
THE SYSTEM SHALL therefore designate REQ-105's citizen registry's **DURABLE RUNTIME location — never
the git-tracked seed template** — as the colony-spawn lock's ONE canonical `statePath`, exported as ONE
named constant, `CITIZENS_REGISTRY_PATH`, from a new shared module
`~/anicca/skills/self/spawn/lib/registry-path.mjs`, computed as `path.join(resolveStateDir({env,
home}), 'citizens.json')` — REUSING, not reimplementing, the SAME `resolveStateDir({env, home})`
function `~/anicca/skills/self/spawn/lib/state-path.js` already exports and
`~/anicca/skills/self/spawn/run.sh` (lines 39-45) already calls for `children.jsonl`'s own durable
location (confirmed by direct read: `STATE_DIR="$(... resolveStateDir({ env: process.env, home:
process.env.HOME }) ...)"`; `COLONY="$STATE_DIR/children.jsonl"`, real default on this coordinator
host today: `~/.hermes/state/children.jsonl`). This is a natural fit: the lock's critical section is
REQ-201's wallet generation THROUGH REQ-305's ledger append actually completing (resolves FIND-1201 —
the IDENTICAL scope this requirement's EARS clause and Acceptance Criteria both state; REQ-101's earlier
registry read and REQ-102's decision themselves run OUTSIDE the lock, since REQ-102's gate function is
pure and needs no mutual exclusion of its own, per its own edge case above — only the ACT of proceeding
on a `true` decision needs the lock), and the durable state dir is EXACTLY where a live-appended,
must-never-be-lost ledger belongs, per `state-path.js`'s own header comment documenting the real 2026-06
incident this mechanism
exists to prevent (a spawn ledger written to `/tmp` was deleted by the OS tmp-cleaner — the SAME
failure class a git-tracked, live-mutated file would risk from routine `git checkout`/`git worktree
add\|remove`/`git pull` instead of a tmp-sweep). EVERY call site that acquires the `"colony-spawn"`
lock (and every REQ-101/105/305 read/write of the registry itself) SHALL import and use this SAME
exported constant — never an independently hardcoded path string, and never the git-tracked seed
template's path — so lock identity and registry identity can never silently drift apart across call
sites, and so a routine `git checkout`/`git worktree add\|remove`/`git pull` on the `~/anicca` repo
(this project's own, frequently agent-automated workflow, per `CLAUDE.md`/`worktree.md`) can never
conflict with, overwrite, or lose a REQ-305 runtime append (resolves FIND-901 — see REQ-105 for the
full two-artifact design).

**Edge Cases**:
- Two evaluation loops on the coordinator host race to acquire the `"colony-spawn"` lock within the
  same millisecond: POSIX exclusive file creation (`fs.open(..., "wx")`, the existing mechanism's own
  atomicity guarantee) ensures exactly one succeeds; the other's `acquire()` call fails immediately
  (fail-closed, no retry-queue).
- The instance holding the lock crashes mid-spawn (dies before releasing): the existing heartbeat +
  `isLockStale` mechanism reclaims the lock after `staleMs` of no heartbeat, exactly as it already does
  for gig-board operations — REQ-103 does not need a second staleness mechanism.
- A held lock's holder is still genuinely working (heartbeating) well past any naive fixed timeout: per
  the existing `isLockStale` semantics, it is NEVER stolen from while it heartbeats, regardless of
  elapsed wall-clock time — this property is inherited, not re-derived, from the existing lock.
- A future call site hardcodes its own literal `citizens.json` path string (whether the git-tracked
  seed template's path OR an independently-typed copy of the durable path) instead of importing
  `CITIZENS_REGISTRY_PATH`: even if the literal string happens to match TODAY, THE SYSTEM treats this as
  a spec violation to be caught at Phase 3 review (a structural/import-identity check, not a runtime
  assertion) — the binding contract is "imports the constant," not "the string happens to be correct."
- A routine `git checkout <branch>`/`git worktree add|remove`/`git pull` runs on the `~/anicca` repo
  while the colony-spawn lock is held or `citizens.json` has just been appended: because
  `CITIZENS_REGISTRY_PATH` resolves entirely OUTSIDE the git working tree (resolves FIND-901), THE
  SYSTEM SHALL be unaffected by this operation — neither the lock file nor the registry's live-appended
  content is ever touched by it (see PROP-105k).

**Acceptance Criteria**:
- The colony-spawn critical section (REQ-201's wallet generation THROUGH REQ-305's ledger append
  ACTUALLY COMPLETING — the new citizen durably recorded in `citizens.json` — resolves FIND-1201: the
  IDENTICAL scope this requirement's own EARS clause and statePath prose both state, never released any
  earlier, e.g. not merely through REQ-205 or "the decision to proceed into REQ-3xx") is wrapped by the
  existing `withGigLock`-equivalent helper (or a directly analogous `withColonyLock("colony-spawn",
  fn)`) using the SAME `lock.mjs` module, not a reimplementation, with `statePath` set to the single
  exported `CITIZENS_REGISTRY_PATH` constant from `registry-path.mjs` — never an independently hardcoded
  string.
- Given two concurrent callers both observing `eligible:true`, an integration test proves exactly one
  reaches REQ-201's wallet-generation step during the run; the other's attempt is recorded as
  `reason:"lock_held"` and makes zero wallet-generation calls.
- A structural/Tier-0 check (source-grep or import-identity check) confirms EVERY call site that
  invokes the `"colony-spawn"` lock imports and passes the SAME `CITIZENS_REGISTRY_PATH` constant — this
  is required IN ADDITION TO (not instead of) the concurrent-race integration test above, because a
  single test process sharing one implicit `statePath` choice cannot, by itself, prove every real call
  site in the eventual implementation converges on one canonical path.

---

### REQ-104: Design-constraint requirement — bookkeeping only, never judgment
**EARS**: WHERE this increment decides WHETHER a spawn is currently permitted (REQ-101/102/103), THE
SYSTEM SHALL implement that decision exclusively as arithmetic and boolean logic over objective,
already-known bookkeeping facts (aggregate USD surplus, an elapsed-time comparison, an in-flight count,
a lock-held boolean) and SHALL NOT implement, alongside or instead of it, any model-driven judgment
about whether spawning is currently a "good idea," any heuristic scoring of colony health, or any
steering text that asks an LLM to decide the threshold/cooldown/cap values at runtime.

This is the SAME design principle already established and adversary-verified for
`anicca-agent-economy`'s REQ-203 ("bookkeeping only, never judgment" for its catalog eligibility gate)
and is consistent with this project's own hard rule (`~/.claude/rules/building-effective-ai-agents.md`
HARD RULE #1/#2: deterministic code owns arithmetic/bookkeeping; the agent owns everything that is
genuinely a decision). What the agent DOES still decide, entirely inside this deterministic envelope
(per SPEC.md §1.5's "spawn = HYBRID" design), is: *when* (within an eligible wake) to actually invoke
the spawn flow, and *what the child's initial goal framing/prompt should say* — **(extended, new,
resolves FIND-1601(b)): together with *what the child's initial skill set should be* — REQ-202's
`initialSkills` parameter is this SAME in-envelope choice, decided by the spawning agent in the SAME
step as the goal framing/prompt above, never a hardcoded fixed default and never a mechanical full copy
of the driving citizen's own current skill roster (see REQ-202 for the full derivation this extension
establishes)** — REQ-104 governs only the eligibility ARITHMETIC, never the agent's own in-envelope
choices (which now explicitly include both the goal framing/prompt AND the initial skill set).

**Edge Cases**:
- A future change that makes `SPAWN_THRESHOLD_USD` itself computed by an LLM call (e.g. "ask the model
  whether $10 is enough") would violate this requirement and must be rejected in review, however
  well-intentioned, exactly as `anicca-agent-economy` REQ-203 rejects a "recommended slot" field.
- This requirement is not independently unit-testable in the normal sense; it is verified via
  structural code review at Phase 3 (grep/read for any LLM call, prompt template, or scoring logic
  inside `decideColonySpawn`/`computeColonySurplusUsd`/the lock-acquisition path), not a runtime
  assertion.

**Acceptance Criteria**:
- `decideColonySpawn` and `computeColonySurplusUsd`'s source contains no network call, no prompt
  string, and no reference to any LLM/inference client.
- The functions' return types carry no free-text "explanation"/"recommendation" field beyond the fixed
  `reason` enum already specified in REQ-102.

---

### REQ-105: Colony citizen registry — brand-new, dedicated, spawn-appended, two-artifact durable design (resolves FIND-002; revised to resolve FIND-101/FIND-104/FIND-901)
**EARS**: WHEN REQ-101 needs the list of citizens to evaluate, THE SYSTEM SHALL read that list from a
single, DURABLE, mutable registry file dedicated EXCLUSIVELY to this feature's colony-surplus/spawn
concern, resolved via the exported constant `CITIZENS_REGISTRY_PATH` — never a hardcoded literal path
at any call site. THE SYSTEM SHALL NOT read from, write to, migrate, or otherwise repurpose the
pre-existing `~/anicca/skills/economy/ubi/colony-wallets.json`: that file remains exclusively `ubi.js::
distributeAI`'s own recipient-eligibility list ("addresses proven to be real colony members," a
DIFFERENT purpose than this requirement's surplus-aggregation registry), and its current 2nd entry is
claude-p's own human-funded wallet — the two files share ZERO state (resolves FIND-101's critical
finding that an earlier draft wrongly proposed migrating/extending that live, differently-scoped,
already-in-use file).

**Two-artifact design (resolves FIND-901 — critical): a git-tracked SEED TEMPLATE, distinct from the
durable, live-appended runtime file.** An earlier revision of this requirement conflated "a single,
versioned JSON registry file" that is BOTH seeded once with fixed literal data AND, per REQ-305,
mutated forever after via live runtime appends — sitting at a hardcoded path INSIDE the `~/anicca` git
working tree — never reconciling that this project's own repo undergoes routine, frequently
agent-automated `git pull`/`git checkout <branch>`/`git worktree add\|remove` operations (this
project's own `CLAUDE.md`/`worktree.md`), any of which could silently conflict with, overwrite,
stash-and-lose, or hard-reset an uncommitted, live-appended registry file if it lived inside the git
working tree — which it WOULD by default, since `~/anicca/.gitignore`'s current patterns
(`skills/*/state/`, `skills/*/*/state/`) do not match `skills/self/spawn/registry/`. This requirement
is now SPLIT into exactly two artifacts:
1. **A git-tracked SEED TEMPLATE**, `~/anicca/skills/self/spawn/registry/citizens.seed.json` — committed
   to git as part of this feature's own versioned codebase, READ-ONLY, NEVER mutated at runtime by any
   code path this feature adds. It exists purely to define the fixed, literal starting content this
   requirement specifies below — nothing else ever writes to it (see PROP-105j).
2. **The actual LIVE, mutable runtime file**, resolved via the exported constant `CITIZENS_REGISTRY_PATH`
   (`~/anicca/skills/self/spawn/lib/registry-path.mjs`, alongside `COORDINATOR_HOME` below) as
   `path.join(resolveStateDir({env, home}), 'citizens.json')` — REUSING, not reimplementing, the SAME
   `resolveStateDir({env, home})` function `~/anicca/skills/self/spawn/lib/state-path.js` already
   exports and `~/anicca/skills/self/spawn/run.sh` (lines 39-45) already calls, TODAY, for
   `children.jsonl`'s own durable location (confirmed by direct read: `STATE_DIR="$(...
   resolveStateDir({env: process.env, home: process.env.HOME}) ...)"`; `COLONY="$STATE_DIR/children.jsonl"`
   — real default on this coordinator host: `~/.hermes/state/children.jsonl`). `CITIZENS_REGISTRY_PATH`
   therefore resolves, by the SAME mechanism, to `~/.hermes/state/citizens.json` on this host — a
   DURABLE, OUT-OF-GIT-TREE location, immune to every routine git operation listed above, exactly as
   `children.jsonl` already is (and, per `state-path.js`'s own header comment, fail-closed against ever
   being `/tmp`-rooted — the same 2026-06 incident class that lost a prior spawn ledger to the OS
   tmp-cleaner) (see PROP-105k).

**One-time bootstrap (never an ongoing sync) — ATOMIC, race-free exclusive-create (revised, resolves
FIND-1001, critical):** an earlier revision of this step specified "on first access, IF
`CITIZENS_REGISTRY_PATH`'s file does NOT yet exist, THEN copy `citizens.seed.json`'s content VERBATIM"
— a classic check-then-act (TOCTOU) race that REQ-103's own `"colony-spawn"` lock does NOT protect,
because that lock's critical section starts at REQ-201's identity generation (REQ-103's own Acceptance
Criteria), never at REQ-101's earlier registry READ that is what actually triggers this bootstrap step.
This is corrected to a SINGLE atomic filesystem operation: on first access, THE SYSTEM SHALL attempt to
create `CITIZENS_REGISTRY_PATH`'s file using an EXCLUSIVE-CREATE operation — POSIX `O_CREAT|O_EXCL`
semantics (`fs.open(path, 'wx')` or equivalent) — writing `citizens.seed.json`'s content VERBATIM as the
new file's content, then closing the handle. This is the EXACT SAME atomic primitive
`~/anicca/skills/economy/gig/lib/lock.mjs::tryCreateLockFile` already uses to close an identical class
of check-then-act race (that module's own header comment documents a REAL prior double-pay bug this
pattern exists to prevent: two concurrent `gig_verify_and_pay(true)` calls both read status `'delivered'`
before either wrote back, and both settled a real on-chain payout — the escrow was drained twice).
THE SYSTEM SHALL NEVER perform a separate "check if the file exists, then copy" sequence for this step —
existence and creation SHALL be the SAME atomic filesystem call, never two:

- If the exclusive-create SUCCEEDS: this caller is the bootstrap winner — the durable file now holds
  the seed content verbatim, and bootstrap is complete.
- If the exclusive-create FAILS with `EEXIST` (the file already exists — either because another
  concurrent evaluator's bootstrap attempt already won this SAME race, OR because a real REQ-305 append
  has already happened before this caller ever ran): THE SYSTEM SHALL NOT write anything at all — no
  retry, no overwrite, no partial write — and SHALL simply proceed to READ the existing file exactly as
  it already is.
- Any OTHER exclusive-create failure (neither success nor `EEXIST`) fails closed exactly as
  `tryCreateLockFile`'s own existing error-handling contract already does — never silently swallowed.

This makes the bootstrap step naturally idempotent and race-free: because POSIX exclusive-create can
only ever succeed against a file that is TRULY nonexistent at the instant of the call, AT MOST ONE
writer, ever, across the entire lifetime of this durable file, successfully creates it from the seed
template — and a real, already-appended citizen record (REQ-305) can NEVER be silently overwritten by a
late/slow bootstrap attempt, because by the time that late attempt's exclusive-create runs, the file
already exists (from the append), so the exclusive-create fails with `EEXIST` and the late caller falls
through to a plain read, never a write. Every subsequent REQ-101 read and every REQ-305 runtime append
happens EXCLUSIVELY at this durable, out-of-tree location — the git-tracked seed template is NEVER read
from or written to again after whichever ONE caller's bootstrap exclusive-create succeeds. REQ-103's
lock `statePath`, this requirement's own registry read, and REQ-403's audit enumeration ALL cite this
SAME durable `CITIZENS_REGISTRY_PATH` — never the git-tracked seed template's path. See PROP-105l for
the concurrent-race and late-append proof obligations this correction adds.

Each record in the registry (whether in `citizens.seed.json` or the durable `citizens.json`) carries
EXACTLY the fields `isSelfFunded()`/`selfFundedReasons()`
(`~/anicca/skills/_shared/lib/is-self-funded.mjs`, reused unmodified) already require, SPLIT into the
two separate shapes that module's own documented contract and this feature's own consumers each need
(resolves FIND-104's wallet-field type mismatch: `is-self-funded.mjs::hasOwnWallet()` documents and
implements `wallet.evm`/`wallet.solana` as BOOLEAN presence flags — `Boolean(wallet.evm) ||
Boolean(wallet.solana)` — never address strings):
- `wallet: {evm?: boolean, solana?: boolean}` — a presence-flag pair, matching `hasOwnWallet()`'s real,
  documented boolean contract EXACTLY (true compatibility, never accidental truthiness coercion of a
  non-empty address string).
- `walletAddress: {evm?: string, solana?: string}` — the actual address string(s), for REQ-305's
  registry-append use and any future consumer that needs the real address — this field is NEVER passed
  to `isSelfFunded()`.

The full record shape is therefore `{id: string, wallet: {evm?: boolean, solana?: boolean},
walletAddress: {evm?: string, solana?: string}, fuel: {provider: string}, humanDependencies: string[]}`
plus TWO additional fields this feature needs and `isSelfFunded()` itself does not read (revised, resolves
FIND-302: the prior second additional field, `telemetryPath`, is REMOVED from this schema — REQ-101's
balance lookup no longer depends on a coordinator-local file path per citizen; see REQ-101's revised
`readCitizenBalances`, which reads each citizen's balance via public RPC keyed on `walletAddress` above,
a mechanism that works identically whether that citizen is co-located with the coordinator or, per
REQ-301, exclusively cloud-hosted):
- `homeDir: string` — the citizen's own resolved absolute `HOME`/`ANICCA_HOME` directory (e.g.
  `/Users/anicca/.anicca` for automaton, `/Users/anicca/.blockrun` for Franklin — see the corrected seed
  data below), used exclusively by REQ-403's wallet mutual non-interference audit's LIVE comparison half
  — itself now scoped to co-located instances only for this increment (resolves FIND-303; see REQ-403) —
  to learn each CO-LOCATED running instance's own HOME without a second, parallel instance-enumeration
  mechanism (resolves FIND-202).
- `coLocatedWithCoordinator: boolean` — **new, resolves FIND-703 (critical):** a structural classifier,
  never a judgment call, distinguishing a citizen genuinely co-located on the SAME physical host as the
  coordinator (REQ-106) from a citizen that is cloud-hosted (REQ-301). Prior to this field, REQ-403's
  live-comparison half's own enumeration ("the current set of CO-LOCATED running instances") had no
  registry-level way to be computed at all — `citizens.json`'s schema carried no field distinguishing
  the two, yet REQ-301 mandates every spawned child is cloud-hosted and REQ-305 mandates every spawned
  child is appended into this SAME registry, so the instant the first child spawns, `citizens.json`
  necessarily mixes co-located and cloud-hosted entries with no schema-level way to tell them apart.
  THE SYSTEM SHALL seed this field as `true` for both of today's citizens (automaton, Franklin — both
  genuinely co-located on the same Mac Mini today, see the seed data below) and THE SYSTEM SHALL,
  per REQ-305, ALWAYS append `false` for this field on every newly-spawned child — never `true`, since
  REQ-301's own absolute mandate makes a co-located spawned child structurally impossible this
  increment. REQ-403's live-audit enumeration reads THIS field directly (`citizens.filter(c =>
  c.coLocatedWithCoordinator === true)`) rather than relying on any undefined/implicit notion of
  "co-located" — see REQ-403's corrected Acceptance Criteria.

  **Corrected, resolves FIND-501 (critical — the most serious defect found across all six spec-review
  iterations of this feature):** an earlier revision of this field stored BOTH of today's seeded
  citizens' `homeDir` as the IDENTICAL, bare `$HOME` value (`/Users/anicca`) and framed this as "expected,
  not a bug" because both citizens are co-located (REQ-106) on the same physical Mac Mini. **Co-located
  (same physical host) does NOT mean "same `homeDir`"** — each citizen still has its own distinct
  `ANICCA_HOME` root even on a shared machine, and `homeDir` MUST store THAT distinct root, never the
  shared physical machine's bare user directory. A full re-read of the real, live
  `~/anicca/skills/earn/lib/resolve-identity.mjs` (`resolveEvmPrivateKey`/`resolveSolanaSecret`) and its
  own test suite (`runtime/loop/__tests__/resolve-identity.test.mjs`) proves the bare-`$HOME` seed value
  is factually incompatible with how these resolvers actually work: automaton's real `ANICCA_HOME` is
  `$HOME/.anicca` (`install.sh:26`: `ANICCA_HOME="${ANICCA_HOME:-$HOME/.anicca}"`), and Franklin's real
  `ANICCA_HOME`-equivalent is `$HOME/.blockrun` — `resolve-identity.mjs`'s own legacy-fallback gate
  (`effectiveHome === path.join(legacyHome, '.anicca')` for EVM, `=== path.join(legacyHome, '.blockrun')`
  for Solana) is DELIBERATELY designed to return `null` for any `HOME`/`ANICCA_HOME` value that is not
  EXACTLY each citizen's own real, distinct root (proven by the test suite's own "foreign spawn... does
  NOT inherit... -> null" cases for both chains). Passing the bare, shared `/Users/anicca` value into
  either resolver therefore resolves to `null` for BOTH citizens (`/Users/anicca` equals neither
  `path.join('/Users/anicca', '.anicca')` nor `path.join('/Users/anicca', '.blockrun')`) — NOT their real
  signing keys — which would have made REQ-403's live audit either trivially "pass" by comparing two
  `null` results (never having read either citizen's real key material) or, worse, never actually prove
  genuine pairwise inequality at all. `homeDir` therefore now stores each citizen's REAL, DISTINCT
  resolved root (see the corrected seed data below) — never the shared machine's bare `$HOME`. A future
  cloud-hosted child's `homeDir`, if ever recorded, is NOT consulted by REQ-403's live check this
  increment (that check is co-located-only) — the field is present on every record only so a future
  increment's remote-audit mechanism has somewhere to read it from.

THE SYSTEM SHALL seed the git-tracked template, `citizens.seed.json`, at implementation time, with the
following FIXED, LITERAL JSON array — NOT a migration of `colony-wallets.json`'s entries, and NOT
derived from any out-of-band classification step, because there is no migration to begin with —
containing ONLY the entities this spec's author has verified, as of 2026-07-07, are genuinely
self-funded colony citizens. This exact content is what the durable `CITIZENS_REGISTRY_PATH` file is
initialized with, verbatim, at its one-time bootstrap (see the two-artifact design above) — the array
below is never independently re-typed or diverged between the two artifacts at seed time.

**Corrected, resolves FIND-601 (critical):** an earlier revision of this section cited "this project's
own `CLAUDE.md` colony table" as ITS OWN verification source for `anicca-a3cdd4`'s seeded
`walletAddress.evm` — but a markdown doc is exactly the WRONG kind of evidence to anchor a live signing
address to, precisely because markdown docs silently go stale: `CLAUDE.md`/`docs/WALLETS.md` themselves
had drifted to a STALE, already-REVOKED address after a real 2026-07-07 key rotation
(`~/.automaton/wallet.json`'s own `rotatedAt`/`rotationReason` fields confirm this — "key exposed in
`~/.anicca-founder/agents/polymarket-agent/.env` and `~/.openclaw/.env`, 2026-07-07 incident") and were
independently fixed as a SEPARATE, out-of-band documentation correction (commit `18e6ae96a`), not a
consequence of anything in this spec. The correct verification method — and the one this seed data was
ALWAYS actually derived from — is a CRYPTOGRAPHIC RE-DERIVATION of each citizen's real, currently-in-use
address directly from its own signing key material: `~/.automaton/wallet.json`'s actual `privateKey`,
independently re-derived to an address via `viem`'s `privateKeyToAccount` (performed live, 2026-07-07),
cross-checked against `~/anicca/skills/self/colony-status.sh`'s own live on-chain balance query against
that SAME address — both methods independently confirm `0xB9dd3B67921B354c656523d6851537988F31DD56`
below is automaton's real, current wallet, never a markdown snapshot.

**Corrected, resolves FIND-801 (critical) — the re-derivation method is TWO-BRANCH, EVM and Solana,
never EVM-only:** `viem`'s `privateKeyToAccount` is a secp256k1/EVM-only function — it cannot derive,
and was never claimed to derive, an ed25519 Solana public key. Franklin's own seeded record below
carries ONLY `walletAddress.solana` (no `evm` field at all), and REQ-202 makes a Solana wallet the norm
— not the exception — for every future Nosana-path child, so PROP-105g's binding rule MUST name a
genuine Solana-equivalent re-derivation method, not merely an EVM one. `@solana/web3.js` (already a
real, EXISTING dependency of this monorepo — `~/anicca/package.json`: `"@solana/web3.js": "^1.98.4"`,
confirmed by direct read; no new dependency introduced) supplies it:
`Keypair.fromSecretKey(secretKeyBytes)` followed by `.publicKey.toBase58()`. The exact byte format this
needs is already established, real, WORKING code in this codebase:
`~/anicca/runtime/dashboard/telemetry-post-franklin.mjs` (lines 11, 21-23) already reads Franklin's OWN
`~/.blockrun/.solana-session` file and calls `bs58.decode(secretB58)` to get a 64-byte `Uint8Array` —
that file's own comment confirms the shape: `"64 bytes: tweetnacl secretKey format == Solana
Keypair.secretKey"`. A full read of `resolve-identity.mjs::readRawSecretFile` (the function
`resolveSolanaSecret` actually calls for this same file) confirms this IS the exact real format
`resolveSolanaSecret` returns: `fs.readFileSync(filePath, 'utf8').trim()` — a bare base58 STRING, no
JSON wrapper, no array of bytes. `bs58` is likewise an already-real dependency of this monorepo
(`~/anicca/runtime/package.json`: `"bs58": "^5.0.0"`, already imported by `telemetry-post-franklin.mjs`)
— no new dependency for THIS conversion step either. PROP-105g's Solana branch is therefore: read
`~/.blockrun/.solana-session`'s real content IN-MEMORY (the SAME in-memory-read carve-out FIND-702
already established for the EVM branch — never log/print the raw secret), `bs58.decode()` it to a
64-byte `Uint8Array` (the format `resolveSolanaSecret`'s base58 string converts to), pass that to
`Keypair.fromSecretKey(secretKeyBytes)` (this call itself re-derives AND validates the embedded public
key against the secret half, throwing on any internal mismatch — an extra integrity check the EVM path
does not have an equivalent of), then `.publicKey.toBase58()` to obtain the address, and DIFF that
address against `citizens.json`'s stored `walletAddress.solana` for that SAME citizen — FAILING HARD on
any mismatch, mirroring the EVM branch's exact rigor. **This was ACTUALLY PERFORMED, not merely cited**
(2026-07-07, `@solana/web3.js@1.98.4`+`bs58@6.0.0` installed to a disposable scratch directory OUTSIDE
this repo, for the check only — never adding a new dependency to `~/anicca/package.json` itself, since
Phase 2 will call the already-real in-repo dependency): reading `~/.blockrun/.solana-session`'s real
content, `bs58.decode()`-ing it to a 64-byte secret, and calling
`Keypair.fromSecretKey(secretKeyBytes).publicKey.toBase58()` returns
`8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9` — an EXACT match against Franklin's seeded
`walletAddress.solana` below (never printed: the raw secret bytes themselves — only this derived public
address). A citizen record with BOTH `walletAddress.evm` AND `walletAddress.solana` populated (the
expected shape for every Nosana-path child, REQ-202) MUST pass BOTH branches independently — see
PROP-105i.

See PROP-105g for the resulting binding rule this correction establishes: any FUTURE seed/append of a
citizen's `walletAddress` MUST be verified the same way — EVM via `viem::privateKeyToAccount` against
`walletAddress.evm`; Solana via `@solana/web3.js::Keypair.fromSecretKey` against `walletAddress.solana`;
whichever chain(s) that citizen's record populates, BOTH independently if both are populated — never
solely against a markdown doc, precisely the class of source that just failed here:

```json
[
  {
    "id": "anicca-a3cdd4",
    "wallet": { "evm": true },
    "walletAddress": { "evm": "0xB9dd3B67921B354c656523d6851537988F31DD56" },
    "fuel": { "provider": "clawrouter-own-wallet" },
    "humanDependencies": [],
    "homeDir": "/Users/anicca/.anicca",
    "coLocatedWithCoordinator": true
  },
  {
    "id": "Franklin",
    "wallet": { "solana": true },
    "walletAddress": { "solana": "8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9" },
    "fuel": { "provider": "x402" },
    "humanDependencies": [],
    "homeDir": "/Users/anicca/.blockrun",
    "coLocatedWithCoordinator": true
  }
]
```

**(resolves FIND-703)** Both seed entries carry `"coLocatedWithCoordinator": true` — accurate as of
2026-07-07, since both automaton and Franklin genuinely run on the same physical coordinator host (the
Mac Mini, REQ-106). This is a structural fact about physical placement, not an inference from `homeDir`
or any other field — it is recorded explicitly so REQ-403's live-audit enumeration never has to guess.

Both entries' `homeDir` values are ALREADY-RESOLVED absolute paths — never a `$HOME`-template string —
because this spec's author already knows the real, concrete path each citizen uses at seed time
(resolves FIND-202).

**Canonical coordinator-HOME constant, `COORDINATOR_HOME` (defined HERE — the ONE place in this entire
spec this literal value is stated; resolves FIND-802, moved up from REQ-403 so the symbol is
established before ANY literal use anywhere in this document):** the worked example immediately below,
and REQ-403's own live-audit worked examples further down this document, both need to express "the
coordinator host's own real `$HOME`" as an `env.HOME` value passed into
`resolveEvmPrivateKey`/`resolveSolanaSecret` — but only as an EXPORTED, NAMED CONSTANT, never
independently hardcoded or independently re-derived at each usage site (the identical class of
un-pinned-input hazard REQ-103 already closed for `CITIZENS_REGISTRY_PATH` via a single named, exported
constant). THE SYSTEM SHALL export a constant, `COORDINATOR_HOME`, from the SAME shared module REQ-103
already introduces, `~/anicca/skills/self/spawn/lib/registry-path.mjs`, computed EXACTLY ONCE, at
module-load time, via Node's `os.homedir()` (the canonical OS-level API for "this process's own real
home directory" — NEVER `process.env.HOME` read ad hoc at any call site, and NEVER a hardcoded literal
string). On this coordinator host, `COORDINATOR_HOME` currently resolves to `/Users/anicca` (confirmed
live, 2026-07-07, via `os.homedir()`) — **every literal `/Users/anicca` value appearing as an
`env.HOME`/coordinator-HOME value anywhere below in this section and in REQ-403 IS `COORDINATOR_HOME`'s
resolved value on THIS host, never an independently-sourced or independently-hardcoded copy.** See
PROP-403f for the corresponding structural check (zero independent `os.homedir()`/`process.env.HOME`
reads anywhere else in this feature's audit-script code path). **Purity note (resolves FIND-1002,
major):** because `COORDINATOR_HOME` is a real read of ambient OS/environment state (`os.homedir()`) and
`CITIZENS_REGISTRY_PATH` (above) is built from `resolveStateDir`, `registry-path.mjs` is classified
"Effectful Shell" in `verification-architecture.md`'s Purity Boundary Map, never "Pure Core" — a
zero-I/O, no-environment-control Tier-1 unit test is NOT sufficient to prove either constant's real
behavior; see PROP-105m for the Tier-2, real-environment-dependent proof this correction adds.

**Corrected, resolves FIND-501:** these two `homeDir` values are each citizen's own REAL, DISTINCT
resolved `ANICCA_HOME` root — `/Users/anicca/.anicca` (automaton's real default, per `install.sh:26`)
and `/Users/anicca/.blockrun` (Franklin's real legacy-Solana root) — NEVER the shared physical machine's
bare `$HOME` (`/Users/anicca`) that an earlier revision of this seed data wrongly used for BOTH entries.
Both citizens still run CO-LOCATED on the same physical coordinator host per REQ-106 (that scoping is
unchanged and correct) — co-location is a fact about the PHYSICAL HOST, not about `homeDir`, and does
not make the two citizens' `ANICCA_HOME` roots identical; each retains its own distinct root even while
sharing a machine. A live filesystem check of this coordinator host (2026-07-07, file EXISTENCE only —
content never read/printed, per this project's own secrets-handling discipline) confirms both corrected
values resolve to real, distinct, non-null key material via `resolve-identity.mjs`'s own existing
legacy-fallback path, invoked with an EXPLICIT `env` object (never the bare `{home: X}` shape — resolves
FIND-603, see REQ-403's Explicit-env correction):
`resolveEvmPrivateKey({home: '/Users/anicca/.anicca', env: {HOME: COORDINATOR_HOME, ANICCA_HOME:
'/Users/anicca/.anicca'}})` reads `/Users/anicca/.automaton/wallet.json` (confirmed present), and
`resolveSolanaSecret({home: '/Users/anicca/.blockrun', env: {HOME: COORDINATOR_HOME, ANICCA_HOME:
'/Users/anicca/.blockrun'}})` reads `/Users/anicca/.blockrun/.solana-session` (confirmed present) — see
REQ-403's Acceptance Criteria for the full derivation. Neither entry carries a `telemetryPath` field
(removed, resolves FIND-302 — see above).

claude-p (real funds at `0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74`, human-funded, per
`docs/WALLETS.md` lines 49-62) and every other human-funded wallet SHALL NEVER be seeded into this
file — there is no ambiguous classification step here precisely BECAUSE there is no migration; the
seed set above is a fixed literal this spec's author already verified against live, on-disk evidence.

**Edge Cases**:
- The registry file is missing, unparseable, or one record is missing a required field: THE SYSTEM
  SHALL exclude only that INDIVIDUAL malformed record from REQ-101's aggregation (fail-closed
  per-record, matching REQ-101's own missing-telemetry fail-closed convention) — one bad record never
  aborts aggregation for every OTHER valid citizen.
- A record's `wallet`/`fuel`/`humanDependencies` fields are well-formed but `isSelfFunded()` itself
  returns `false` for that record (e.g. `fuel.provider` not in `OWN_FUNDED_FUEL_PROVIDERS`): excluded
  from the surplus sum exactly as REQ-101 already specifies — REQ-105 supplies DATA, REQ-101 still
  owns the JUDGMENT of who counts; REQ-105 does not duplicate or override that gate.
- Two records share the same `id`: THE SYSTEM SHALL treat this as a malformed registry and exclude
  BOTH duplicate-id records from aggregation until corrected, rather than arbitrarily picking one.
- A future write path (anywhere in this feature) attempts to append or edit an entry in the durable
  `citizens.json` whose `{wallet, fuel, humanDependencies}` sub-object would make `isSelfFunded()`
  return `false`: see REQ-305's binding pre-append `isSelfFunded()` check below — this registry SHALL
  NEVER contain an entry that fails its own gate, at seed time OR at any later append.
- **(new, resolves FIND-901)** A routine `git checkout <branch>`/`git worktree add|remove`/`git pull`
  runs on the `~/anicca` repo (this project's own, frequently agent-automated workflow) at any point
  before, during, or after REQ-305 has appended runtime rows to the durable `citizens.json`: THE SYSTEM
  SHALL be structurally unaffected — because `CITIZENS_REGISTRY_PATH` resolves entirely OUTSIDE the git
  working tree (via `resolveStateDir`), no git operation on `~/anicca` ever reads, writes, stashes, or
  resets the durable file's content (see PROP-105k).
- **(new, resolves FIND-901)** A future code path attempts to write to the git-tracked seed template,
  `citizens.seed.json` (e.g. an accidental "sync the seed forward" step): THE SYSTEM treats this as a
  spec violation — the seed template is READ-ONLY at runtime, consulted only during the one-time
  bootstrap of `CITIZENS_REGISTRY_PATH`'s file, and NEVER written to by any runtime code path this
  feature adds (see PROP-105j).
- **(new, resolves FIND-1001 — critical)** Two simulated "first access" callers (e.g. two
  independently-scheduled evaluation loops on the coordinator host, per REQ-106's own edge case) both
  observe `CITIZENS_REGISTRY_PATH`'s file does not yet exist and both attempt the bootstrap
  exclusive-create within the same millisecond: because POSIX `O_CREAT|O_EXCL` (`fs.open(path, 'wx')`)
  is atomic even across separate OS processes, THE SYSTEM SHALL guarantee exactly ONE caller's
  exclusive-create succeeds (that caller wrote the seed content verbatim); the OTHER caller's
  exclusive-create SHALL fail with `EEXIST`, and THAT caller SHALL write nothing and proceed directly to
  reading the (now-existing) file — never a torn/partial/double write, and never two divergent copies of
  the seed content (see PROP-105l).
- **(new, resolves FIND-1001 — critical)** A real REQ-305 append has already happened (a genuine
  successful spawn recorded a new citizen into the durable file) BEFORE a late/slow bootstrap attempt's
  exclusive-create call ever runs: THE SYSTEM SHALL NOT overwrite or lose the already-appended record —
  the late caller's exclusive-create fails with `EEXIST` (the file already exists, now WITH the real
  appended record, not merely the seed content) exactly the same way it would against a plain
  bootstrap-only file, so the late caller writes nothing and simply reads the existing, already-appended
  content untouched (see PROP-105l).

**Acceptance Criteria**:
- The seed template (`citizens.seed.json`) parses as an array of objects each satisfying `{id, wallet,
  walletAddress, fuel, humanDependencies, homeDir}` (no `telemetryPath` field — removed, resolves
  FIND-302), and calling the existing, unmodified `isSelfFunded()` on any one record's `{wallet, fuel,
  humanDependencies}` sub-object (never `walletAddress`) returns a boolean without throwing.
- Every seeded (and later appended, REQ-305) entry's `homeDir` is an ALREADY-RESOLVED absolute path — a
  structural check confirms its value never contains the literal substring `$HOME` or `$ANICCA_HOME`
  anywhere in `citizens.seed.json` or the durable `citizens.json` (resolves FIND-202).
- **(new, resolves FIND-901)** `CITIZENS_REGISTRY_PATH`'s construction is confirmed, by a structural/
  Tier-0 read of `registry-path.mjs`, to always route through `resolveStateDir({env, home})` — never a
  literal path string inside the `~/anicca` git working tree (PROP-105k, structural half).
- **(new, resolves FIND-901)** A live test that (1) writes a distinctive fixture record to the durable
  `citizens.json` at `CITIZENS_REGISTRY_PATH`, (2) performs a real `git checkout`/`git worktree add`/
  `git pull` on the `~/anicca` repo, and (3) re-reads the durable file, confirms the fixture record is
  UNCHANGED (PROP-105k, live half) — and a structural/Tier-0 grep across this feature's diff confirms
  ZERO write calls (`fs.writeFile`/`fs.writeFileSync`/equivalent) target `citizens.seed.json`'s path
  anywhere outside the one documented one-time bootstrap-read call site (PROP-105j).
- **(new, resolves FIND-1001 — critical)** The bootstrap step is a SINGLE atomic exclusive-create
  filesystem call (`fs.open(CITIZENS_REGISTRY_PATH, 'wx')`-equivalent, POSIX `O_CREAT|O_EXCL`) — a
  structural/Tier-0 check confirms the bootstrap implementation contains no separate
  `fs.existsSync`/`fs.stat`-then-`fs.writeFile` check-then-act pair for this specific step (PROP-105l,
  structural half).
- **(new, resolves FIND-1001 — critical)** Two fixtures prove this atomicity is race-free: (1) a
  concurrent-race fixture — two simulated first-access callers attempt the bootstrap exclusive-create at
  the same time — asserts exactly ONE succeeds and the other fails with `EEXIST` and proceeds to read
  (never overwrites, never double-writes); (2) a late-bootstrap-after-real-append fixture — a real
  REQ-305 append completes BEFORE a simulated late bootstrap attempt's exclusive-create call runs —
  asserts the exclusive-create fails with `EEXIST` (the file already exists) and the already-appended
  citizen record survives byte-identical, untouched by the late attempt (PROP-105l, live/Tier-2 half).
- A direct test confirms that EACH of the two seeded entries above, when its `{wallet, fuel,
  humanDependencies}` sub-object is passed through the existing, unmodified `isSelfFunded()`, returns
  `true` — a straightforward assertion against literal fixture data (resolves FIND-101's critique of
  the prior "compare against today's known-good identities" proof method, which presupposed an
  out-of-band ground truth no longer needed once there is no migration).
- `citizens.seed.json`'s content contains ZERO entries whose `isSelfFunded()` verdict is `false` — and
  REQ-305's append-on-spawn path (below) enforces the SAME property on every future append to the
  durable `citizens.json`, closing this hazard PERMANENTLY rather than only at t=0.
- **(resolves FIND-601, corrected resolves FIND-801)** Every seeded (and later appended, REQ-305)
  entry's `walletAddress` value is verified, at the time it is written, against that citizen's ACTUAL
  signing key material via a direct cryptographic re-derivation — EVM: `viem`'s `privateKeyToAccount`
  against the real private-key file, diffed against `walletAddress.evm`; Solana: `@solana/web3.js`'s
  `Keypair.fromSecretKey` (fed the real secret's `bs58`-decoded 64-byte form) against the real secret
  file, diffed against `walletAddress.solana` — whichever chain(s) that citizen's record populates, BOTH
  independently if both are populated (REQ-202's expected Nosana-path shape, see PROP-105i) — NEVER
  solely against a markdown documentation snapshot (`CLAUDE.md`/`docs/WALLETS.md`), which this
  iteration's own review proved can silently go stale after a real key rotation without this spec's own
  seed data (already correct) being affected. A live on-chain balance query MAY be cited as an
  ADDITIONAL corroboration (as already done for automaton's address, cross-checked against
  `colony-status.sh`) but is NEVER a substitute for the re-derivation above — a funded address existing
  on-chain does not by itself prove that address was correctly derived from a specific private key, a
  categorically weaker property (resolves FIND-801's critique that an unelaborated "balance query"
  alternative never explained what it would prove). See PROP-105g/PROP-105i.
- REQ-403 (the wallet non-interference audit's "current set of co-located running instances," this
  increment — resolves FIND-303) reads its citizen list AND each instance's `homeDir` directly from
  THIS SAME registry — no second, parallel instance-enumeration mechanism exists anywhere in this spec.
  REQ-402/REQ-101's productivity exclusion (`"bootstrap_failed"`, `active_since`) is a SEPARATE concern
  that lives EXCLUSIVELY in `ledger.js` — see REQ-101's `filterProductiveCitizens` join and REQ-402 —
  this registry intentionally carries neither field (resolves FIND-201's location contradiction).
- **(resolves FIND-703)** Every seeded (and later appended, REQ-305) entry carries a
  `coLocatedWithCoordinator: boolean` field. Both of today's seeded entries have this set to `true`; a
  structural check confirms REQ-403's live-audit enumeration filters on
  `citizens.filter(c => c.coLocatedWithCoordinator === true)` rather than any undefined/implicit
  "co-located" notion — see PROP-105h.

---

### REQ-106: Colony-spawn evaluation is scoped to a single coordinator host, this increment only (resolves FIND-003)
**EARS**: THE SYSTEM SHALL perform every REQ-101/102/103 evaluation (colony surplus aggregation,
threshold gate, and `"colony-spawn"` lock acquisition) EXCLUSIVELY on one, explicitly-designated
coordinator host for the full duration of this increment — currently the Mac Mini
(`anicca-mac-mini-1`) on which automaton's own loop already runs (this project's own `CLAUDE.md`:
"Mac Mini（`anicca-mac-mini-1`...）で直接実行する"). A cloud-deployed child instance (REQ-301-303)
SHALL NOT itself evaluate REQ-101/102/103 or attempt to acquire the `"colony-spawn"` lock during this
increment — spawn CHAINING (a child later spawning its own child) is explicitly OUT OF SCOPE,
deferred to a future increment. This constraint is what makes REQ-103's `lock.mjs` (a local-POSIX-
filesystem primitive) and REQ-305's `ledger.js` (a local append-only file) CORRECT as specified: both
mechanisms only need to serialize/record callers that share the SAME mounted filesystem, which holds
precisely because every evaluator in this increment IS that one coordinator host.

**Edge Cases**:
- Multiple LOOPS on the SAME coordinator host (e.g. automaton's own cron-driven wake and a separately-
  scheduled evaluation) race to evaluate REQ-102/103 in the same window: this is the scenario REQ-103's
  lock already handles (both are local callers sharing one filesystem) — this is the ONLY concurrency
  scenario this increment's lock/ledger design needs to survive, and it replaces iteration 1's
  now-corrected edge case that conflated this with a cross-host scenario.
- A future increment extends the colony to genuinely multiple physical coordinator hosts (e.g. once a
  spawned child is itself permitted to evaluate REQ-102/103): THE SYSTEM as specified in THIS increment
  does NOT support that topology — `lock.mjs`/`ledger.js` would need to be replaced or backed by
  networked/shared storage (a shared network filesystem, a database-backed lock, or a distributed
  consensus mechanism) before multi-host colony-spawn evaluation is safe. This is an explicit,
  documented, KNOWN LIMITATION of this increment, not an oversight.
- The coordinator host itself becomes unavailable (hardware failure, network partition from the cloud
  providers): no OTHER host picks up colony-spawn evaluation in this increment (single coordinator, by
  design) — an accepted single-point-of-failure for this increment's scope, matching the colony's
  actual current topology (every existing citizen's own loop already runs on this same Mac Mini today).

**Acceptance Criteria**:
- A structural/Tier-0 check confirms `lock.mjs`'s acquire/release path and `ledger.js`'s read/write
  path are invoked from exactly one designated coordinator-host code entry point in this feature's
  implementation, with no code path that invokes them from a cloud-deployed child's own runtime.
- This spec's own scope section states spawn chaining is out of scope, so a fresh adversary reviewing
  REQ-103/REQ-305 does not need to (and must not be asked to) prove multi-host correctness for this
  increment.

---

## REQ群B: 新規 instance identity 生成（P2 実証済み手順の再利用、車輪の再発明禁止）

### REQ-201: Child EVM (Base) wallet generation
**EARS**: WHEN REQ-102/103 jointly permit a spawn attempt to proceed, THE SYSTEM SHALL generate the
child's own secp256k1/Base-EVM keypair via `~/anicca/skills/self/spawn/scripts/gen-wallet.sh`
(existing, unmodified — the exact script this feature's task description names as already-proven),
BEFORE any cloud provisioning or on-chain action for that child occurs, and SHALL verify the resulting
address is a real keccak256-derived Ethereum address (not the script's own documented sha256 fallback,
which is not a valid Ethereum address — see Edge Cases) and is distinct from every existing colony
citizen's own EVM address (reusing `child-spec.js::buildChildSpec`'s existing, UNTOUCHED distinct-
wallet assertion, which already throws if `childWallet === parentWallet`; REQ-201 generalizes that same
check to "distinct from ALL existing citizens," not merely the one parent that happened to initiate the
attempt). This generated address ALSO becomes `buildChildSpec`'s `agentEvmAddress` identity-anchor
field once REQ-204 registers it (see REQ-206) — REQ-201 itself only generates and validates the
keypair; it does not call `buildChildSpec`.

**Edge Cases**:
- The host running `gen-wallet.sh` lacks a real keccak implementation (its own comment: "not a real eth
  addr; smoke-test will warn" is the fallback-sha256 branch) — THE SYSTEM SHALL treat any address
  produced by that fallback path as INVALID and abort the spawn attempt (REQ-305), rather than
  registering an ERC-8004 identity or funding a wallet that cannot actually be an Ethereum address.
  This makes the script's own existing "warn" comment into a hard, machine-enforced abort at the
  calling layer, since `gen-wallet.sh` itself only warns.
- The generated address happens to collide with an existing citizen's address (secp256k1
  birthday-collision, astronomically unlikely but checked defensively): abort and regenerate — never
  proceed with a colliding wallet.
- The private key material must never appear in any log file, stdout capture that reaches persistent
  logs, or process list — the caller MUST redirect `gen-wallet.sh`'s stdout directly to a 600-perm file
  (the script's own header comment already states this constraint; REQ-201 makes the CALLER's
  compliance with it a binding acceptance criterion, not merely documentation).
- The generated private key material must be delivered to the child's own remote lease/job via REQ-303's
  (`provider-services lease-shell`) or REQ-302's (`nosana job ssh`) post-boot injection channel ONLY —
  THE SYSTEM SHALL NEVER write this key material into any boot-time artifact (an SDL `env:` line, a
  Nosana job command string, a cloud-init `user_data` field, or any other artifact
  `provider-services sdl-to-manifest`/a job-definition dump would expose publicly) at any point between
  generation and injection (resolves FIND-401: this is the structural property that makes the two-phase
  "boot secretless, inject after" sequence in REQ-302/303 actually correct, rather than merely asserted).

**Acceptance Criteria**:
- `gen-wallet.sh`'s output JSON (`{address, private_key, public_key}`) is captured directly into a
  600-perm file path under the child's own isolated `$HOME` (REQ-203), never echoed to a shared log.
- The address independently re-derives to the same value under a second, independent keccak
  implementation (cross-check), matching the existing SKILL.md's own stated verification method
  ("address derives identically under ethers v6 — cross-checked").

---

### REQ-202: Child Solana keypair generation (conditional)
**EARS**: IF the child instance's initial skill set includes any Solana-settled capability (e.g. a
`sol-trade`-class skill, matching Franklin's own existing dependency on a Solana wallet at
`~/.blockrun/.solana-session`) OR the child will be deployed via Nosana (REQ-302, which itself requires
a Solana-funded wallet per the re-verified quick-start docs above), THE SYSTEM SHALL also generate a
fresh, locally-generated, non-custodial Solana Ed25519 keypair for the child, using the same
generation-discipline as REQ-201 (fresh entropy, 600-perm temp file, never logged) — reusing Nosana's
own CLI convention (auto-generating `~/.nosana/.nosana_key.json` on first run, re-confirmed live
2026-07-07) as the evidence that "wallet-per-instance, zero signup, locally generated" is the current,
live norm this feature's own generation script should match, rather than a bespoke design.

**Deriving `needsSolanaWallet`'s inputs from real system state (new, resolves FIND-1601, critical):**
neither the EARS clause above nor the Acceptance Criteria below previously specified WHERE either of
`needsSolanaWallet({initialSkills, deployTarget})`'s two inputs actually comes from at runtime.

`deployTarget` is never hand-assembled by the calling orchestration — it is ALWAYS the DIRECT return
value of THAT SAME spawn attempt's `selectCloudTarget({nosanaAvailable, nosanaPriceUsd, akashAvailable,
akashPriceUsd})` call (REQ-306) — never a hand-rolled reimplementation, and never a stale/earlier
evaluation carried over from a prior or different attempt. This mirrors the IDENTICAL "never
hand-assembled, always the direct return value of X()" binding discipline REQ-102 establishes for
`recentSpawnAttempts`/`deriveRecentSpawnAttempts` and `childrenProvisioning`/`countChildrenProvisioning`.
This binding is not cosmetic: REQ-302's own EARS clause states the Nosana deploy step provisions the
child's compute "pointed at the child's OWN pre-generated, isolated Solana keypair (REQ-202)" — i.e.
REQ-302 structurally REQUIRES that REQ-202 already generated a Solana wallet for this specific child
whenever Nosana ends up being THAT SAME attempt's real selected target. A hand-assembled or stale
`deployTarget` that diverges from REQ-306's actual real-time selection for that attempt either (i)
wrongly skips Solana keygen for a child REQ-302 will need it for (a hard, deploy-breaking failure of the
entire Nosana path), or (ii) wastes a real, billable Solana keygen for a child that will never use it.

`initialSkills` is never hardcoded or independently invented by REQ-202's own orchestration — it is
ALWAYS the SAME initial-skill-set value the spawning agent already chose for this child, per REQ-104's
own agent-judgment carve-out (extended, above, to explicitly cover this choice) — the identical value
used to construct the child's own initial goal framing/prompt, never a second, independently-derived
list.

**Edge Cases**:
- The child needs NEITHER a Solana-settled skill NOR Nosana deployment (e.g. it is deployed via Akash
  only, with an EVM-only initial skill set): THE SYSTEM SHALL skip Solana keypair generation entirely
  — this requirement is conditional, not universal, so a child never holds an unused, unmonitored key
  it has no use for.
- The generated Solana address collides with an existing citizen's Solana address: abort and
  regenerate (same discipline as REQ-201's EVM collision check).

**Acceptance Criteria**:
- A pure conditional check (`needsSolanaWallet({ initialSkills, deployTarget }) → boolean`) determines
  whether this step runs at all, before any key material is generated.
- When it runs, the resulting keypair is captured directly into a 600-perm file under the child's own
  isolated `$HOME` (REQ-203), matching REQ-201's handling exactly.
- **(new, resolves FIND-1601)** `deployTarget` is never hand-assembled by the calling orchestration —
  it is ALWAYS the direct return value of THAT SAME spawn attempt's `selectCloudTarget(...)` call
  (REQ-306), never a stale/earlier attempt's evaluation.
- **(new, resolves FIND-1601)** `initialSkills` is never hardcoded/defaulted inside REQ-202's own
  orchestration — it is ALWAYS the SAME value the spawning agent already chose, per REQ-104's
  agent-judgment carve-out, for this child's initial skill set/goal framing.

---

### REQ-203: `$HOME`/`ANICCA_HOME` isolation for the child instance
**EARS**: WHEN the child instance is provisioned, THE SYSTEM SHALL assign it a `$HOME` (or
`ANICCA_HOME`, matching the priority order `~/anicca/skills/earn/lib/resolve-identity.mjs` already
implements: `ANICCA_HOME` explicit override, else `$HOME`-derived default) that is a path DISTINCT from
every existing citizen's own home/`ANICCA_HOME` directory, and no process belonging to the child SHALL
ever be launched with an inherited `HOME`/`ANICCA_HOME` environment variable pointing at any existing
citizen's directory. This exploits, unmodified, the SAME mechanism already relied upon in production:
Franklin's own `BLOCKRUN_DIR = path.join(os.homedir(), '.blockrun')` (verified current 2026-07-07,
`@blockrun/franklin` v3.29.16, `src/config.ts:19`) means setting a distinct `HOME` at process-launch
time gives the child a distinct `.blockrun`/`.anicca` state directory with ZERO code changes to
Franklin itself — exactly the mechanism SPEC.md §1.2 point 3 and §9.9 already describe and this
project's own `resolve-identity.mjs`/`ensure-agent-id.mjs` already gate on for existing instances.

**Edge Cases**:
- The child's assigned `HOME` path is accidentally identical to (or a parent/child directory of) an
  existing citizen's own home path: fail-closed abort BEFORE any wallet material (REQ-201/202) is ever
  written there — this check runs first, before key generation, not after.
- The child process is launched by a supervisor (a cloud-init script, systemd unit, or the Akash/Nosana
  container's own entrypoint — REQ-302/303) that does not explicitly set `HOME`/`ANICCA_HOME` and would
  otherwise inherit whatever default the base image provides: THE SYSTEM SHALL require an EXPLICIT
  environment-variable injection at every such process-launch boundary (verified present in the actual
  SDL/job-definition/cloud-init artifact used for that child, not assumed from a shell default).
- `resolve-identity.mjs`'s existing legacy-path fallback (`effectiveHome === path.join(legacyHome,
  '.blockrun')`) is scoped ONLY to the rightful owner of that exact legacy home — a spawned child with
  a genuinely different `HOME` value already fails that equality check and correctly resolves `null`
  rather than a foreign citizen's key; REQ-203 relies on this EXISTING fail-closed behavior rather than
  re-implementing it.

**Acceptance Criteria**:
- Before any REQ-201/202 key generation, a distinctness check compares the child's proposed
  `HOME`/`ANICCA_HOME` against every currently-known citizen's own value and aborts on any match.
- An integration test launches two processes with two different injected `HOME` values against the
  SAME `resolve-identity.mjs` module and asserts each resolves only its own wallet file, never the
  other's (this is the exact `FIND-001-class` regression test style that module's own header comment
  already documents having fixed once — REQ-203 extends that same test to a THIRD, freshly-spawned
  home directory).

---

### REQ-204: ERC-8004 identity registration for the child
**EARS**: WHEN the child's own EVM wallet (REQ-201) exists and its cloud shelter (REQ-302/303) is
reachable, THE SYSTEM SHALL register the child's ERC-8004 identity by calling the existing
`~/anicca/skills/economy/gig/lib/ensure-agent-id.mjs::ensureAgentId({privateKey: childPrivateKey,
cacheFile: <child's own isolated cache path>})` — NOT `identity.mjs::registerIdentity()` directly —
reusing `ensureAgentId`'s already-implemented, already-tested cache-then-verify-then-register-once
wrapper UNMODIFIED (resolves FIND-004: this is the SAME defensive "don't double-register" logic REQ-204
needs, already built and covered by that module's own test suite; REQ-204 does not re-derive it).
`ensureAgentId` itself calls `registerIdentity()`/`verifyIdentity()` against the already-live registry
contract — mainnet `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (Base, chain 8453) or testnet
`0xdc527768082c489e0ee228d24d3cfa290214f387` (Base-Sepolia, chain 84532), selected by the same
`GIG_CHAIN` env toggle it already uses — signed with the child's OWN private key (`msg.sender` = the
child's own address, matching the existing "each agent registers itself" discipline). Because
`ensureAgentId`'s own cache path is gated on `ANICCA_HOME`/`HOME` exactly as `resolve-identity.mjs`
already is (that module's own header: "so a foreign spawn ... can never read/reuse another instance's
cached agentId"), passing the child's own isolated `$HOME` (REQ-203) as `cacheFile`'s basis is
sufficient — no new per-child cache-scoping logic is needed. THE SYSTEM SHALL record the returned
`agentId` and transaction hash in the spawn ledger (REQ-305) before the child may be marked `"active"`.

**Edge Cases**:
- `register()` reverts for insufficient gas (the child's fresh wallet starts at exactly `0 ETH`): THE
  SYSTEM SHALL fund it with a ONE-TIME, minimal gas seed transferred from a self-funded citizen's own
  wallet — sized to cover exactly one `register()` call plus the child's first gig-board interaction,
  the SAME class of transfer SPEC.md §9.6 already performed and evidenced on-chain (tx `0x48d49e…`
  /`0x1478758…`), never an open-ended top-up, and never sourced from a human-funded wallet (REQ-304
  governs the funding SOURCE constraint).
- The registration transaction succeeds but its `Registered` event cannot be decoded (a malformed/odd
  log): treated as a REQ-305 failure (no `agentId` recorded), never a fabricated/guessed agentId.
- The SAME child wallet somehow already holds an agentId (should be impossible for a genuinely fresh
  key): THE SYSTEM SHALL rely EXCLUSIVELY on `ensureAgentId`'s own existing cache-hit/`verifyIdentity`
  re-check path (already reads a cached `{address, agentId}` pair, re-verifies via `verifyIdentity`
  before trusting it, and falls through to a fresh `register()` only if that re-check fails) — REQ-204
  does not implement a second, parallel "already-registered" check; the anomaly (a fresh key already
  owning an agentId) is logged by `ensureAgentId`'s own `cached:true` return value, which REQ-305's
  ledger write surfaces for audit.

**Acceptance Criteria**:
- `ensureAgentId({ privateKey: childPrivateKey, cacheFile: <child's own isolated path> })` is called
  with no modification to `ensure-agent-id.mjs`'s or `identity.mjs`'s existing logic, signature, ABI,
  or registry-address constants.
- A successful registration produces a real, independently-re-verifiable transaction hash and a
  numeric `agentId`; both are appended to the spawn ledger (REQ-305) in the same row that eventually
  marks the child `"active"`.
- A fixture where `ensureAgentId`'s injected `verifyFn` reports an existing, matching cached agentId
  results in ZERO calls to `registerFn` (i.e. `register()` is never invoked a second time) — reusing
  that module's own existing test double pattern (`registerFn`/`verifyFn` injection), not a new mock
  harness built from scratch for this feature.

---

### REQ-205: gig-board MCP configuration for the child
**EARS**: WHEN the child instance boots inside its cloud shelter, THE SYSTEM SHALL write it an
`mcp.json` in the exact shape of the already-live, verified `~/.blockrun/mcp.json`
(`mcpServers.<name>.{transport:"stdio", command:<node path>, args:[<child's OWN
economy/gig/mcp-server.mjs path>], env:{GIG_FACILITATOR_URL, GIG_STATE_PATH, GIG_CHAIN}}`), with
`GIG_STATE_PATH` pointing at a state file location UNIQUE to the child (under its own isolated `$HOME`,
REQ-203 — never the shared `~/.anicca-signing/gig-board/state/gigs.json` path an existing citizen
already uses unless the gig board is explicitly colony-shared by design) and `GIG_FACILITATOR_URL`
pointing at the colony's existing, live self-host facilitator, so the child's own Franklin process
discovers the gig-board MCP server through the exact same startup-discovery mechanism SPEC.md §9.1
already documents ("append to `~/.blockrun/mcp.json`... Franklin が起動時 discovery"), with ZERO
modification to Franklin's own source required.

**Edge Cases**:
- `GIG_STATE_PATH` is accidentally set to an existing citizen's own state file path (a template
  copy-paste bug): THE SYSTEM SHALL verify the resolved path is unique to this child before the file is
  first written — a collision here would let the child observe/mutate another citizen's gig-board state,
  which REQ-403's audit must also be able to catch independently.
- The facilitator URL is unreachable at the child's first boot: this is NOT an REQ-205 failure by
  itself (REQ-205 only specifies that the config POINTS at a real, currently-live endpoint at write
  time) — the child's own gig `run.sh` already fail-closes on an unreachable facilitator per its
  existing, unmodified discipline ("no signing key resolved ... fail closed").

**Acceptance Criteria**:
- The written `mcp.json` parses as valid JSON and validates against the same shape as the existing
  `~/.blockrun/mcp.json` (same top-level keys, same env-var names).
- `GIG_STATE_PATH`'s resolved absolute path is verified, at write time, to be different from every
  other currently-known citizen's own `GIG_STATE_PATH`.

---

### REQ-206: `buildChildSpec`'s identity-anchor validation — backward-compatible extension (resolves FIND-001; EARS clarified to resolve FIND-102)
**EARS**: WHEN a new child record is assembled via `~/anicca/skills/self/spawn/lib/child-spec.js::
buildChildSpec` (called from REQ-305's ledger-append step), THE SYSTEM SHALL accept as a valid
"identity anchor" for the child EITHER (a) a non-empty `childInbox` string (the pre-existing
AgentMail-based anchor, unchanged in shape and validation from today's already-shipped design) OR (b)
the pair `agentEvmAddress` (identical to `childWallet`, REQ-201) AND `agentId` (the numeric ERC-8004
identifier `ensureAgentId`/REQ-204 returns), both present and non-empty. THE SYSTEM SHALL require that
AT LEAST ONE of these two anchors is present; it is NOT an error for BOTH to be present simultaneously
(a future hybrid child with both an AgentMail inbox and an on-chain identity succeeds identically to
either anchor alone — see Edge Cases and Acceptance Criteria); it IS an error for NEITHER to be present.
"At least one" is stated here as a genuine minimum, not an exclusive-or, so this EARS clause and the
Edge Cases below never disagree (resolves FIND-102's self-contradiction between an earlier XOR-reading
EARS sentence and this requirement's own "both present" acceptance rule). This corrects iteration 1's
false claim that
`buildChildSpec` is reused "unmodified" (FIND-001: today's code throws `missing required field
"childInbox"` for `undefined`/`null`/`""`, and this feature's own design never produces an AgentMail
inbox at all): `buildChildSpec` requires a SMALL, backward-compatible validation/signature extension
— adding the optional `agentEvmAddress`/`agentId` pair and relaxing `childInbox` from unconditionally-
required to "required only if the ERC-8004 pair is absent" — never a rewrite of its existing
distinct-wallet assertion, monotonic-ID logic (`nextChildId`), or returned row shape (which gains two
new optional fields, `agent_evm_address`/`agent_id`, alongside its existing, unchanged fields).

**Cross-file field-name disambiguation (resolves FIND-304):** `buildChildSpec`'s own, pre-existing,
UNMODIFIED returned row carries a field literally named `wallet` (`child-spec.js:37`: `wallet:
childWallet` — a bare address STRING; confirmed by its own existing test, `child-spec.test.js:36`:
`assert.strictEqual(spec.wallet, "0xCHILD...")`). This is a COMPLETELY SEPARATE field, in a COMPLETELY
SEPARATE file/schema, from REQ-105's `citizens.json` registry record's `wallet` field, which is a
BOOLEAN presence-flag object (`{evm?: boolean, solana?: boolean}`, REQ-105). The two `wallet` fields
share a name only by coincidence across two unrelated schemas this feature touches — this spec does NOT
rename `child-spec.js`'s existing field (that would violate its "unmodified" contract, the same
discipline already established above for this file) — implementers and reviewers MUST read each
`wallet` field per its OWN file's schema and MUST NOT cross-reference the two (same class of
disambiguation FIND-104 already performed for `wallet`/`walletAddress` WITHIN `citizens.json` itself;
here it is a cross-file clarifying note, not a schema change).

**The other four fields `buildChildSpec` already unconditionally requires** (`parentWallet`,
`generation`, `seedUsdc`, `constitutionHash` — confirmed still mandatory at
`~/anicca/skills/self/spawn/lib/child-spec.js:16-34`, unrelated to and untouched by the identity-anchor
extension above) **are reconciled with this feature's actual architecture as follows** (resolves
FIND-204 — REQ-206 is extended to cover these four, not merely the identity-anchor clause):
- **`parentWallet`**: set to REQ-106's single coordinator-host citizen's OWN wallet address — the
  citizen that evaluated REQ-101/102/103 and is driving this spawn attempt (never a synthesized or
  absent value). This value is always distinct from the freshly generated `childWallet` (REQ-201), so
  `buildChildSpec`'s own existing `childWallet === parentWallet` throw is never triggered by a
  colony-treasury-funded spawn. REQ-304's multi-citizen co-funding (no single "parent" for FUNDING
  purposes) is a SEPARATE concept from `parentWallet` here, which only identifies the
  coordinator-driving citizen for `buildChildSpec`'s own distinct-wallet bookkeeping — it does not imply
  that citizen alone funded the deploy.
- **`generation`**: fixed at `1` for every child this feature produces — reusing, not inventing, the
  SAME default `run.sh` already hardcodes (`"${ANICCA_GENERATION:-1}"`, `run.sh:136`) — because this
  feature's colony-treasury-funded spawns are, by design, top-level, non-lineage children (REQ-304's own
  edge case already establishes there is no single funding "parent" to derive a lineage depth from);
  spawn CHAINING (which would need a real generation-incrementing rule) is explicitly out of scope this
  increment (REQ-106).
- **`seedUsdc`**: IS REQ-204's gas-seed USDC amount — the SAME value, passed straight through (never a
  second, independently-derived quantity). REQ-303/304's "shelter cost" (cloud hosting/lease cost) is a
  GENUINELY DISTINCT amount — never conflated with `seedUsdc` — funded and ledgered separately per
  REQ-303/304's own mechanism.
- **`constitutionHash`**: a fixed SHA-256 hex digest of `~/anicca/identity/genesis.md`'s content — the
  SAME canonical identity-seed file `install.sh` already ships verbatim into every new instance's own
  `ANICCA_HOME` (`install.sh:78-93`, "Canonical hustle genesis lives at identity/genesis.md in the repo;
  ship it verbatim") — computed ONCE and treated as a fixed spec-level constant for this feature (not
  recomputed per spawn, since every child this increment produces inherits the identical, unmodified
  genesis file). A future increment that needs per-child constitution variation would need a dedicated
  new requirement; this increment's children are all identical-genesis siblings.

**Edge Cases**:
- An existing (hypothetical future) caller that still passes a non-empty `childInbox` and omits
  `agentEvmAddress`/`agentId` entirely (the old AgentMail-only design, e.g. today's
  `~/anicca/skills/self/spawn/run.sh`'s own happy path where `AGENTMAIL_API_KEY` is set and a real
  inbox is minted) MUST continue to succeed with an identical returned row shape to today's — this is
  the binding backward-compatibility contract; a regression test locks this in.
- A caller (this feature's own REQ-305 integration) passes `agentEvmAddress`+`agentId` and omits
  `childInbox` (or passes it as `""`/`null`, which is exactly what this feature's spawn flow does,
  since it never mints an AgentMail inbox): THE SYSTEM SHALL accept this as a valid identity anchor and
  NOT throw the pre-existing "missing childInbox" error — this is the specific behavior iteration 1
  incorrectly assumed already existed.
- Neither `childInbox` nor the `agentEvmAddress`+`agentId` pair is present, or only ONE half of the
  ERC-8004 pair is present (e.g. `agentEvmAddress` set but `agentId` missing): THE SYSTEM SHALL throw
  a `missing identity anchor` error — exactly as strict as today's all-required validation, never
  silently defaulting to a placeholder identity.
- Both `childInbox` AND the ERC-8004 pair are present simultaneously (a future hybrid child with both
  an inbox and an on-chain identity): THE SYSTEM SHALL accept this without error — "at least one" is a
  minimum, not an exclusive-or.
- `parentWallet` is supplied as the coordinator-host citizen's own wallet and happens to equal the
  freshly-generated `childWallet` (an astronomically unlikely secp256k1 collision, REQ-201's own
  defensive check): `buildChildSpec`'s existing, untouched `childWallet === parentWallet` throw fires
  exactly as it already does today — this feature relies on that EXISTING check, never a new one.
- `generation` is passed as anything other than `1` for a colony-treasury-funded spawn (a future coding
  error): THE SYSTEM treats this as a spec violation to be caught at Phase 3 review — this increment's
  children are never lineage-chained, so `1` is the only value this requirement authorizes.
- `seedUsdc` and REQ-204's actual gas-seed transfer amount ever diverge (a future bug passing two
  different numbers into `buildChildSpec` vs the real on-chain gas-seed transfer): THE SYSTEM treats
  this as a spec violation — the two MUST be the identical value by construction, never merely close.

**Acceptance Criteria**:
- A regression test fixture identical to the existing `child-spec.test.js`'s "assembles a complete,
  distinct-wallet spec" case (non-empty `childInbox`, no `agentEvmAddress`/`agentId`) passes UNCHANGED
  after this modification.
- A new test fixture supplying `agentEvmAddress`+`agentId` and omitting `childInbox` succeeds, and the
  returned row carries `agent_evm_address`/`agent_id`.
- A new test fixture supplying NEITHER anchor throws; a fixture supplying only HALF of the ERC-8004
  pair also throws.
- A new test fixture supplying BOTH a non-empty `childInbox` AND a complete `agentEvmAddress`+`agentId`
  pair simultaneously SUCCEEDS without throwing, and the returned row carries `childInbox`,
  `agent_evm_address`, AND `agent_id` all together — proving the "at least one, not an XOR" reading of
  the EARS clause above (resolves FIND-102).
- A structural diff of `child-spec.js` confirms the change is limited to the required-field validation
  and the returned row's field list — `nextChildId`, the distinct-wallet assertion, and every other
  existing field/behavior are byte-identical to today's.
- A fixture/integration test calls `buildChildSpec` with all SEVEN required fields populated per the
  derivation rules above (`parentWallet`=a fixture coordinator wallet, `generation`=1, `seedUsdc`=the
  same fixture gas-seed amount used elsewhere in the test, `constitutionHash`=the real SHA-256 of
  `identity/genesis.md`, plus the ERC-8004 anchor pair) and asserts success with every field correctly
  present in the returned row — not just the two identity-anchor-focused fixtures (PROP-206a/b) already
  specified (resolves FIND-204).
- `generation` is asserted to be exactly `1` for every REQ-305 spawn-flow call in this increment; a
  structural/Tier-0 check confirms no code path in this feature's diff passes any other value.
- `seedUsdc`'s value, in every real REQ-305 call, is asserted identical to the amount REQ-204 actually
  transferred as the gas seed for that same spawn attempt — never an independently-computed number.

---

## REQ群C: cloud deployment（新規、local 禁止）

### REQ-301: Local spawn is structurally forbidden
**EARS**: THE SYSTEM SHALL NOT provision any child instance's runtime, wallet material (beyond the
ephemeral REQ-201/202 generation step, which MAY run on whichever host initiates the spawn attempt,
provided the generated key is held ONLY in a transient, 600-perm file on the initiating host and is
relocated into the child's own isolated remote `$HOME` EXCLUSIVELY via REQ-302's/REQ-303's post-boot
secrets-injection channel — resolves FIND-401's timing gap: "relocated" means relocated the moment the
child's own lease/job is confirmed running and reachable via that injection channel, never synchronously
at generation time, since no authenticated channel to an as-yet-unbooted lease/job can exist — and is
never itself persisted under the initiating host's own home beyond that transient file, which the
trap/cleanup discipline REQ-201 already specifies removes), or persistent state on the same
physical/virtual host as any existing colony citizen's own runtime. Every child SHALL be deployed
exclusively via REQ-302 (Nosana) or REQ-303 (Akash) — reusing SPEC.md §3 P3's own stated rationale
("spawn は local 禁止（disk を埋めて崩壊）") — never onto the machine currently running the spawning
process itself.

**Edge Cases**:
- A spawn attempt is initiated from a laptop/Mac Mini host that ALSO happens to run an existing
  citizen (the current colony's actual topology): the child's own long-running process/state MUST
  still end up exclusively on the cloud lease, never left running on that initiating host after the
  spawn attempt completes (success or failure).
- The generated wallet material's transient temp file on the initiating host is never cleaned up
  (e.g. the process crashes before REQ-302/303's post-boot injection step and its own trap/cleanup
  runs): THE SYSTEM treats this as a REQ-305 failed-attempt condition requiring the SAME shred/rm
  cleanup discipline REQ-201 already specifies, checked at the NEXT wake if it was missed — never left
  indefinitely as a stray secret on the initiating host.

**Acceptance Criteria**:
- Structural/Tier-0 check: reading the deploy code path confirms the only two artifacts the initiating
  host retains after a spawn attempt are (a) the spawn ledger row and (b) nothing else persistent for
  that child — no child-specific systemd/launchd unit, no lingering child process, on the initiating
  host.

---

### REQ-302: Nosana deploy path
**EARS**: WHEN a spawn attempt (REQ-102/103) proceeds and Nosana is the selected cloud target for that
attempt (the selection ITSELF — Nosana vs Akash — is specified by REQ-306, not by this requirement;
REQ-302 governs only the Nosana-specific execution once selected), THE SYSTEM SHALL provision the
child's compute using the Nosana CLI (`@nosana/cli`, confirmed
current 2026-07-07 per the re-verification table above; installed via `npm install -g @nosana/cli`),
pointed at the child's OWN pre-generated, isolated Solana keypair (REQ-202) — via whatever
env/flag the installed CLI version exposes for supplying an existing key file — rather than letting the
CLI auto-generate a NEW keypair inside the invoking process's own default `~/.nosana/` path (which
would violate REQ-203's isolation guarantee by creating key material outside the child's own isolated
`$HOME`), and SHALL post the deploy job with `nosana job post <command> --market <marketAddress> --wait`,
verifying a `RUNNING`/`COMPLETED` job status and a real, resolvable job ID/URL (per the documented
output format: `Job: https://explore.nosana.com/jobs/<id>`) before considering this leg successful.

**Post-boot secrets-injection channel (new, resolves FIND-401's Nosana-side analog):** Exactly like
REQ-303's Akash path, a Nosana job posted via `nosana job post` boots the child's compute with no
channel, by itself, for delivering the child's own already-generated EVM (REQ-201) private key material
onto the running job (the `-w/--wallet` flag documented above supplies the JOB-POSTING wallet — the
transaction signer for the Nosana market itself — not a channel for injecting a DIFFERENT, separate
secret payload into the job's own running container). THE SYSTEM SHALL therefore deliver that payload,
after the job reaches `RUNNING` status (this leg's own existing success check, above), via
`nosana job ssh <job> [port]` — a real, confirmed-present CLI primitive (`nosana job ssh --help`, invoked
live 2026-07-07, raw output "Open an SSH shell into a running job... Usage: nosana job ssh [options]
<job> [port]" captured verbatim to disk at `reviews/spec/iteration-6/evidence/cli-help-2026-07-07.txt` —
resolves FIND-504: this citation now points a Read-only reviewer at that captured transcript, never an
inline prose quote alone), the direct Nosana analog of Akash's `lease-shell` and the
authenticated-post-boot-channel security pattern `cloud-init.sh`'s own header comment already
establishes as this codebase's precedent (see the Scope section's honesty note on that precedent). The
EXACT non-interactive invocation shape for a single `cat > /opt/anicca.env`-style payload delivery (as
opposed to an interactive shell) is NOT independently re-verified beyond this CLI's own `--help` output
in this revision — THE SYSTEM SHALL confirm the exact working invocation against the actually-installed
`@nosana/cli` version at Phase 2 implementation time before relying on it, rather than this spec
asserting an unverified exact command line as already-proven.

**Edge Cases**:
- The `nosana job ssh` secrets-delivery step fails after the job itself is already `RUNNING` (billing):
  treated as a deploy failure under REQ-305, mirroring REQ-303's identical Akash-side edge case — the
  already-paid job cost is logged for colony accounting, and the child is never marked `"active"` on a
  booted-but-secretless job alone.
- The child's Solana wallet lacks sufficient NOS/SOL to cover the selected market's posted price at
  submission time: job post fails immediately (documented CLI behavior) — treated identically to
  REQ-305's deploy-failure path, no partial success recorded.
- No open market/node is available at an acceptable price within a bounded poll/retry window: same
  failure path — REQ-302 does not silently fall back to a different market tier without that being an
  explicit, separately-specified policy (out of scope for this first increment; a single documented
  default market is used).
- The job's `Result`/exit status is non-zero (the child's boot script itself failed inside the leased
  container): treated as a deploy failure even though the Nosana JOB itself completed — REQ-302's
  success criterion is "the child's own process is actually running," not merely "Nosana accepted the
  job."

**Acceptance Criteria**:
- The deploy step never reads or writes any file under the invoking host's own default `~/.nosana/`
  directory when acting on behalf of a child — a distinctness check analogous to REQ-201/203's.
- A successful deploy yields a real job ID that independently resolves via
  `https://explore.nosana.com/jobs/<id>` (or the equivalent current CLI "get job" query) to a
  `RUNNING`/`COMPLETED` status, not merely a locally-logged claim.
- After a Nosana job reaches `RUNNING`, a `nosana job ssh`-based delivery step lands the child's own
  pre-generated wallet material inside the running job's container — an integration/E2E check confirms
  this (never inferred from the job posting's own stdout alone), mirroring REQ-303's Akash-side check
  (resolves FIND-401's Nosana-side analog).

---

### REQ-303: Akash deploy path (reuse existing, already-implemented scripts)
**EARS**: WHEN a spawn attempt proceeds and Akash is the selected cloud target for that attempt (per
REQ-306's selection mechanism — see REQ-302's own note), THE SYSTEM SHALL provision the child's compute
using the existing, already-implemented
`~/anicca/skills/self/spawn/scripts/deploy-akash.sh` (`provider-services` CLI, confirmed still the
current, officially-documented Akash deployment CLI per the re-verification table above) together with
`~/anicca/skills/self/spawn/scripts/akt-treasury.sh` (ACT top-up via `akash tx bme mint-act`, confirmed
still current), REUSING both scripts UNMODIFIED for the deployment-create → bid-poll → lease-create →
manifest-send flow, substituting only the child's own `CHILD_ID` and the child's own SDL (the existing
image-independent template — public `node:22-bookworm` base, `git clone` of the OSS repo at boot — is
reused as-is unless a child-specific variant is explicitly required). THE SYSTEM SHALL record the
actual `AKASH_DEPOSIT` escrowed and, once observable, the real settled lease cost, into a persistent
shelter-cost ledger that REQ-102's `measured_last_shelter_cost_usd` mechanism reads.

**Naming the shelter-cost ledger and its derivation function (new, resolves the sweep-found sibling gap
alongside FIND-1501):** this persistent shelter-cost ledger is a new, small, dedicated module,
`~/anicca/skills/self/spawn/lib/shelter-cost-ledger.js`, exporting EXACTLY
`{readShelterCostEntries, appendShelterCostEntry}` — the SAME append-only-JSONL, no-update/upsert
discipline `~/anicca/skills/self/spawn/lib/ledger.js` already establishes for children (this module
never gains a mutation primitive either). THE SYSTEM SHALL append ONE entry per real deploy attempt,
`{ts: number, settledLeaseCostUsd: number}`, at the point the settled lease cost first becomes
observable (the provisional `AKASH_DEPOSIT`-only figure is logged for colony accounting per REQ-304's
own memo/log discipline, but is NOT itself what `MIN_SHELTER_USD` reads once a real settled cost
exists). REQ-102's `MIN_SHELTER_USD` override reads this ledger via a new sibling pure function, same
file as `filterProductiveCitizens`, `~/anicca/skills/self/spawn/lib/
treasury-gate.mjs::deriveMeasuredShelterCostUsd({shelterCostLedgerRows}) → number|null`: returns `null`
on an empty ledger (no real deploy has ever completed), else reduces to the LAST-appended entry (the
SAME last-write-wins discipline `filterProductiveCitizens`/`deriveRecentSpawnAttempts`/
`countChildrenProvisioning` already apply to `ledger.js`'s own rows) and returns that entry's
`settledLeaseCostUsd` — NEVER an average, sum, or historical-max across every accumulated entry, and
NEVER the first-ever entry, even once many real deploys have accrued many ledger rows over time.

**Funding-readiness gate reuse (resolves FIND-402):** BEFORE invoking `akt-treasury.sh`/
`deploy-akash.sh`, THE SYSTEM SHALL determine whether the signing wallet's current AKT balance is
sufficient by calling the existing, already-unit-tested
`~/anicca/skills/self/spawn-child/lib/akt-cost-gate.js::computeSpawnGate({balanceAkt, costAkt,
bufferAkt})` — reusing `spawn-child/config.json`'s own real, already-documented `spawn_cost_akt`
(default `25`) and `buffer_akt` (default `1`) values as `costAkt`/`bufferAkt` — rather than defining a
competing, Akash-specific numeric threshold from scratch. This is a DIFFERENT, narrower concern than
REQ-102's `MIN_SHELTER_USD`/`SPAWN_THRESHOLD_USD` (which answers "does the colony have enough aggregate
USD-equivalent surplus to attempt a spawn at all, across either cloud target"): `computeSpawnGate`
answers the Akash-specific mechanical question "given Akash is the already-SELECTED target (REQ-306)
and REQ-102 already certified sufficient aggregate surplus, does the signing wallet's OWN AKT balance
right now cover this deploy's real cost" — REQ-303 reuses it exactly as
`~/anicca/skills/self/spawn-child/SKILL.md` itself already documents (its own "READY" branch: steps 1-4,
ending in `deploy-akash.sh`), never re-deriving `spawn-child`'s already-tested arithmetic.

**Deriving `balanceAkt` from real system state (new, resolves FIND-1802, critical):** `balanceAkt` —
this function's own FIRST-listed parameter, and the single most consequential value it consumes, since
it IS the live quantity being tested for sufficiency — is never hand-assembled or cached by REQ-303's
own orchestration: it is ALWAYS the direct result of a FRESH `provider-services query bank balances
<address>` call (`<address>` resolved via `provider-services keys show "$AKASH_KEY_NAME"` — the SAME
signing wallet `costAkt`/`bufferAkt` are already scoped to, `spawn-child/config.json`'s own
`akash_key_name`), performed at the moment of THAT SPECIFIC evaluation — reusing
`~/anicca/skills/self/spawn-child/run.sh`'s own existing, already-fail-closed query+conversion logic
verbatim (the `uakt`-denominated balance parsed from that query's real JSON output via
`.balances[]? | select(.denom=="uakt") | .amount`, converted to AKT by dividing by `1e6`) rather than
re-deriving a second, independently-written balance-query path. REQ-303's own orchestration performs
this SAME fresh query immediately before EACH of the (at most two, see below) `computeSpawnGate`
evaluations it makes — never a stale reading carried over from an earlier evaluation, and never the
wrong wallet's balance.

**`computeSpawnGate`'s exact two-pass sequencing relative to REQ-304's bridge (rewritten, resolves
FIND-1803, critical — this is the ONE, unambiguous statement of this sequencing, superseding any other
characterization elsewhere in this requirement):** THE SYSTEM SHALL evaluate `computeSpawnGate` in
EXACTLY two passes for any deploy attempt whose first pass is insufficient, and never more than two:
1. **First pass**, on the signing wallet's balance as it stands right now. If this FIRST evaluation
   returns `ready:true`, THE SYSTEM SHALL proceed directly to `akt-treasury.sh`'s mint step (see the
   Edge Cases below) WITHOUT ever attempting REQ-304's Skip API bridge — the bridge is never invoked
   when the wallet is already sufficiently funded.
2. If the FIRST evaluation instead returns `ready:false`, THIS is precisely what triggers an attempt at
   funding the AKT shortfall via REQ-304's multi-hop Skip API bridge (Jupiter-first-hop if
   Solana-funded, CCTP-first-hop if Base-funded, per PROP-304e; corrected iteration 7, resolves
   FIND-602's stale Jupiter-only phrasing) — the FIRST evaluation's own `ready:false` result is NEVER
   itself treated as a REQ-305 deploy failure; it is only ever the bridge-attempt trigger.
3. AFTER that bridge attempt completes — whether it succeeds in landing funds or fails outright — THE
   SYSTEM SHALL re-evaluate `computeSpawnGate` a SECOND time, with `balanceAkt` freshly re-queried per
   the real-derivation binding above (so a successful bridge's newly-landed funds are actually
   reflected, and a failed bridge's unchanged balance is likewise honestly reflected). ONLY this SECOND
   evaluation's result is ever treated as final: a SECOND-pass `ready:true` proceeds to `akt-treasury.sh`'s
   mint step exactly as the first-pass-ready case does; a SECOND-pass `ready:false` — meaning the bridge
   attempt did not (or could not) bring the balance to sufficiency — IS the actual REQ-305 deploy
   failure (identical treatment to the "ACT mint cancels" edge case below: `akt-treasury.sh`/
   `deploy-akash.sh` are never invoked, no `dseq` is fabricated).

**Child-specific SDL variant — explicit `HOME` (resolves FIND-403):** Direct reads confirm neither
`deploy-akash.sh`'s inline default SDL nor the reused external template
(`~/anicca/skills/self/spawn-child/sdl/child.yaml`) sets `HOME`/`ANICCA_HOME` anywhere in its `env:`
block — both currently rely on `node:22-bookworm`'s own default root-user home (`/root`), which is
exactly the "base-image default" REQ-203's own PROP-203c prohibits relying on implicitly. THE SYSTEM
SHALL therefore use a child-specific SDL variant (structurally identical to
`spawn-child/sdl/child.yaml` in every other respect — same image, same `command`/`args` boot shape, same
`expose`/`profiles`/`placement` blocks) that adds exactly ONE new `env:` line, `HOME=/root` (the same
value the base image already resolves to implicitly today — made EXPLICIT, not a behavior change),
acknowledged here as a genuinely new, small, necessary SDL modification — NOT a claim that the existing
template is reused byte-for-byte for THIS feature's actual deploys (PROP-303a's "zero source
modification" claim is correspondingly scoped to `deploy-akash.sh`/`akt-treasury.sh`'s own script files
only, never to this new, small SDL variant).

**Post-lease secrets-injection step (resolves FIND-401, new — not a modification to `deploy-akash.sh`):**
`deploy-akash.sh` (unmodified) already boots the lease with ZERO secret material in the SDL/manifest —
this was ALREADY correct, existing behavior, not a gap needing a fix. What the existing artifacts never
provided is a channel for delivering the child's own already-generated EVM (and, if applicable, Solana)
private key material (REQ-201/202) onto that booted lease so the running process can actually sign as
the identity REQ-204 registers and REQ-305 ledgers. THE SYSTEM SHALL therefore add a NEW orchestration
step, run by THIS feature's own code (never by `deploy-akash.sh`'s own source, which stays byte-identical
per PROP-303a) immediately after `deploy-akash.sh`'s existing manifest-send succeeds (i.e., after the
lease is confirmed `active` and the manifest is confirmed sent — reusing `deploy-akash.sh`'s own existing
`ACTIVE`/`SENT` polling result as the trigger, never a new polling mechanism): render the child's wallet
material (the REQ-201/202 private key(s), `ANICCA_CHILD_ID`, and any other `.env` value the child's own
`install.sh`/`runtime/loop/index.mjs` require at first wake) into a `.env`-shaped payload, then deliver
it via `provider-services lease-shell <service-name> "cat > /opt/anicca.env" --dseq <dseq> --gseq <gseq>
--oseq <oseq> --provider <provider> --from "$AKASH_KEY_NAME" --stdin` — a real, confirmed-present
`provider-services` CLI primitive (`provider-services lease-shell --help`, invoked live 2026-07-07, raw
output "do lease shell... Usage: provider-services lease-shell <service-name> <command> [flags]" and its
full flag list, including `--stdin` "connect stdin", captured verbatim to disk at
`reviews/spec/iteration-6/evidence/cli-help-2026-07-07.txt` — resolves FIND-504: this citation now points
a Read-only reviewer at that captured transcript, never an inline prose quote alone), the direct Akash
analog of an authenticated SSH exec-into-running-container channel. `<service-name>` is `automaton` (the
SDL's own service name, `sdl/child.yaml` line 7);
`<dseq>`/`<provider>` are already known from `deploy-akash.sh`'s own successful run (its own
stdout/internal variables); `<gseq>`/`<oseq>` default to `1` per `provider-services`' own documented
defaults (unchanged from `deploy-akash.sh`'s own lease-create call, which never overrides them). Once
delivered, the file lands at `/opt/anicca.env` — the path the child's own booted process is configured to
read its runtime configuration from (a Phase 2 implementation detail this feature's diff, not
`install.sh` itself, is responsible for wiring). THE SYSTEM SHALL NEVER place this secret payload in the
SDL's own `env:` block, in any `user_data`-equivalent boot config, or in any location
`provider-services query`/`sdl-to-manifest` exposes publicly — this mirrors the EXACT security discipline
`~/anicca/skills/self/spawn/scripts/cloud-init.sh`'s own header comment already documents for the
(separate, DO-specific, out-of-scope) `run.sh` path ("SECURITY: NO secret VALUES in user_data...
Secrets are SCP'd... after boot") — cited here ONLY as the established SECURITY PATTERN precedent this
feature's Akash-specific mechanism follows, NOT as a claim that DO's own SCP step is itself already
implemented (a direct read of `run.sh` confirms no `scp` invocation exists anywhere in its current DO
path either — an honest, out-of-scope gap in a DIFFERENT, non-REQ-302/303 cloud target this feature does
not touch; see RESOLUTION-NOTES.md).

**Edge Cases**:
- The signing wallet's `uact` (ACT) balance is below `AKASH_DEPOSIT` at spawn time: `akt-treasury.sh`
  MUST be run and its EXECUTED (not CANCELED — the script's own documented balance-delta check)
  outcome confirmed BEFORE `deploy-akash.sh` is invoked; if the mint cancels (output below
  `bme.params.min_mint`), THE SYSTEM SHALL treat this as a deploy failure (REQ-305) and never fabricate
  a `dseq`.
- The SECOND, post-bridge `computeSpawnGate` evaluation ALSO reports `ready:false` (insufficient AKT
  even after REQ-304's bridge attempt and after accounting for `buffer_akt`): THE SYSTEM SHALL treat
  this identically to the "mint cancels" edge case above — a deploy failure under REQ-305,
  `akt-treasury.sh`/`deploy-akash.sh` are never invoked, and no `dseq` is fabricated. This is DISTINCT
  from the FIRST evaluation's own `ready:false` result (see the "exact two-pass sequencing" paragraph
  above), which is NEVER itself treated as a REQ-305 failure — it is only ever the trigger for
  attempting REQ-304's bridge in the first place (resolves FIND-1803's internal contradiction between
  this Edge Case and the Funding-readiness gate reuse paragraph's own bridge-triggering clause).
- No open bid appears within `deploy-akash.sh`'s existing poll window (30 attempts, existing default
  sleep): the script's own existing fail-closed behavior (non-zero exit, no dseq printed) is reused
  as-is; REQ-303 adds no new retry logic beyond what already exists.
- `send-manifest` fails after its existing retry budget (5 attempts): treated as a deploy failure even
  though the lease itself is technically active — a leased-but-unmanifested deployment is not a running
  child and MUST NOT be marked `"active"`.
- The post-lease secrets-injection step (`lease-shell`) fails (network error, expired lease-shell
  authorization, or a non-zero exit) AFTER `deploy-akash.sh` already reports an active lease + sent
  manifest: THE SYSTEM SHALL treat this as a deploy failure under REQ-305 (the lease itself is real and
  billing, but the child cannot yet sign as its own registered identity) — the already-paid,
  non-refundable lease deposit is logged for colony accounting (mirroring REQ-305's own "already-spent,
  non-refundable resource" handling), and the child is NEVER marked `"active"` on the strength of a
  booted-but-secretless lease alone.
- The child-specific SDL variant's new `HOME=/root` line is accidentally omitted at implementation time
  (a regression): THE SYSTEM treats this as a spec violation to be caught at Phase 3 review — PROP-203c's
  "explicit env line" acceptance criterion is re-checked against the ACTUAL rendered SDL used for a real
  deploy, not merely asserted from this spec's own text.

**Acceptance Criteria**:
- `deploy-akash.sh CHILD_ID` and `akt-treasury.sh` are invoked with no source modification; their
  existing exit-code/stdout contract (dseq on stdout, non-zero exit + stderr message on any failure) is
  the sole success/failure signal this feature reads.
- The real `AKASH_DEPOSIT` amount and (once queryable) the real settled lease cost are appended, via
  the new `shelter-cost-ledger.js::appendShelterCostEntry`, to the shelter-cost ledger file that
  REQ-102's `deriveMeasuredShelterCostUsd({shelterCostLedgerRows: readShelterCostEntries(...)})` reads
  on its NEXT evaluation — the very first spawn therefore uses the provisional `$5.00`/`$10.00`
  defaults (`deriveMeasuredShelterCostUsd` returns `null` on the still-empty ledger), and every
  subsequent evaluation uses the LAST-appended entry's real measured data once at least one successful
  deploy exists — never an average/max across multiple accumulated entries.
- `computeSpawnGate({balanceAkt, costAkt: config.spawn_cost_akt, bufferAkt: config.buffer_akt})` (from
  `~/anicca/skills/self/spawn-child/lib/akt-cost-gate.js`, reused unmodified) is called EXACTLY TWICE
  for any Akash deploy attempt whose first pass is insufficient (never once, never an unbounded/variable
  number of times) — once BEFORE any REQ-304 bridge attempt, and once AFTER — both times with
  `balanceAkt` freshly re-queried per its real-derivation binding above (resolves FIND-1802) and
  `costAkt`/`bufferAkt` read from `spawn-child/config.json`'s own real values — never a competing,
  independently-invented Akash-specific threshold. Only the SECOND evaluation's `ready:false` is ever
  treated as the REQ-305 deploy failure; the FIRST evaluation's `ready:false` is only ever the REQ-304
  bridge-attempt trigger, and a FIRST-pass `ready:true` skips the bridge and the second evaluation
  entirely (resolves FIND-1803).
- The rendered SDL actually submitted on-chain for a real deploy contains an explicit `HOME=/root` line
  in its `env:` block — a structural check of the ACTUAL post-`envsubst` artifact (not the template
  file alone), resolving FIND-403 and satisfying PROP-203c's "never a base-image default" requirement.
- After `deploy-akash.sh`'s manifest-send succeeds, a `provider-services lease-shell ... --stdin` call
  delivers the child's own pre-generated wallet material to `/opt/anicca.env` on the leased container —
  an integration/E2E check confirms the file exists post-delivery with the expected content (never
  checked via the SDL/manifest artifact, which never carries it) — and that `deploy-akash.sh`/
  `akt-treasury.sh`'s own source remains byte-identical throughout (PROP-303a's scope, corrected to
  exclude the new secrets-injection step and the new child-specific SDL variant, both of which are
  tested as NEW code, never claimed as pre-proven reuse).

---

### REQ-304: Shelter cost is funded only from treasury-gate-approved surplus
**EARS**: THE SYSTEM SHALL NOT fund any REQ-302/303 deploy (nor REQ-204's gas seed) from any single
citizen's own `perCitizenReserveUsd` (the amount REQ-101 excludes from the aggregate precisely because
it is that citizen's own survival reserve) or from any human-funded wallet (claude-p's or any other);
funding SHALL draw only from the aggregate surplus REQ-102 already certified as available for THAT
spawn attempt, and by an amount not exceeding what REQ-102 approved.

**AKT funding route correction (resolves FIND-402; citation and route-capability corrected, resolves
FIND-502):** The "single-signer, single-transaction transfer" characterization in the first Edge Case
below is accurate for REQ-204's gas-seed transfer and for any shelter-cost transfer where the funding
citizen's OWN native chain already matches the deploy target's native currency (e.g., Franklin's Solana
SOL/USDC directly funding a Nosana deploy — REQ-302 — both Solana-native, genuinely one signer, one
transaction). It is NOT accurate for funding an AKASH deploy's `uact`-denominated escrow specifically:
NEITHER of the colony's two currently-verified self-funded citizens (`anicca-a3cdd4`'s Base USDC,
`Franklin`'s Solana SOL/USDC, per REQ-105's seed data) natively holds AKT. THE SYSTEM SHALL fund an
Akash deploy's AKT requirement via the REAL, already-documented, already-vetted route
`~/anicca/skills/self/spawn-child/config.json`'s own `funding_route` field literally specifies
(confirmed by direct read, 2026-07-07): `"solana/8453 -> noble-1 -> osmosis-1 -> akashnet-2 (Skip API
smart_relay, 4-hop)"` — a 4-hop Skip API bridge from a source chain, through `noble-1`/`osmosis-1`, to
`uakt` on `akashnet-2` — followed by `akt-treasury.sh`'s own existing `mint-act` step (unmodified) to
convert the received AKT into the `uact` `deploy-akash.sh` actually escrows. **Corrected citation
attribution (resolves FIND-502):** the Jupiter SOL→USDC pre-step is NOT part of `config.json`'s
`funding_route` field value — that field, read literally, contains no mention of Jupiter, SOL, or USDC
at all. The Jupiter step is `~/anicca/skills/self/spawn-child/SKILL.md`'s own separate, documented
sequence (lines 61-67: "1. Jupiter: SOL → USDC (Solana) 2. Skip API 4-hop smart_relay: USDC(solana) →
AKT(akashnet-2)...") — a same-chain Solana DEX swap that converts Franklin's native SOL into USDC BEFORE
that USDC enters the Skip API bridge at its `"solana"` first hop. THE SYSTEM SHALL cite these as TWO
SEPARATE artifacts, never merged into one: `config.json`'s own field for the 4-hop bridge itself, and
`SKILL.md`'s own prose for the Solana-side Jupiter pre-step that feeds it.

**The `"solana/8453"` first-hop ambiguity, investigated (resolves FIND-502):** `config.json`'s own
literal field value labels its first hop `"solana/8453"` — a label that, read naively, conflates the
chain NAME `"solana"` with the literal string `"8453"`, which is Base's own EVM chain ID elsewhere in
this codebase (`~/anicca/skills/economy/gig/lib/escrow.mjs::CHAIN_ID_BASE_MAINNET = 8453`). Rather than
leave this unexamined, it was checked against Skip API's own real, live capabilities (`api.skip.build`,
the same bridge/relay this route already documents using): a live query against Skip API's public
`/v2/info/chains` endpoint (2026-07-07) confirms `8453` IS Skip API's own real, valid `chain_id` for
Base mainnet (`{"chain_name":"Base","chain_id":"8453","chain_type":"evm",...}`), a distinct, independently
real chain entry alongside `{"chain_name":"Solana","chain_id":"solana","chain_type":"svm",...}` — NOT a
stray typo or an internally-conflated label. A live query against Skip API's public
`/v2/fungible/route` endpoint (2026-07-07), sourcing directly from `anicca-a3cdd4`'s (automaton's) own
Base-native USDC contract (`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, the EXACT address this
codebase's own `escrow.mjs::USDC_BASE_MAINNET` already uses) to `uakt` on `akashnet-2`, returns a REAL,
computable 4-hop route — `chain_ids: ["8453","noble-1","osmosis-1","akashnet-2"]`, first hop a `cctp_transfer`
(Circle's Cross-Chain Transfer Protocol, Base→`noble-1`) — confirming this exact same documented Skip
API route family genuinely supports a SECOND, independent entry point from Base-native USDC, requiring
NO Jupiter step at all (Jupiter is a Solana-only same-chain DEX swap, irrelevant to a Base entry that
already holds USDC directly; the Base-entry variant instead uses a CCTP transfer as its first hop). THE
SYSTEM THEREFORE CONFIRMS, with concrete evidence (not a guess): `"solana/8453"` names TWO real, valid,
alternative FIRST hops into the SAME shared `noble-1`→`osmosis-1`→`akashnet-2` back-half — `"solana"`
(Franklin's path, via Jupiter SOL→USDC then CCTP) and `"8453"`/Base (automaton's path, via CCTP directly,
no Jupiter) — meaning EITHER of the colony's two current citizens can independently enter this documented
route to fund an Akash deploy's AKT requirement, not only Franklin. See PROP-304e for the corresponding
proof obligation. THE SYSTEM SHALL reuse this documented route (whichever entry matches the actually-
funding citizen's own wallet) rather than re-deriving a same-chain assumption that does not hold for
either citizen's actual wallet composition — this is a genuinely multi-hop, multi-transaction funding
path for the Akash target specifically, never a single-signer single-transaction transfer.

**Edge Cases**:
- The approved aggregate surplus is spread across multiple citizens' wallets and no single citizen
  individually holds the full deploy cost: THE SYSTEM SHALL fund from whichever citizen(s)
  INDIVIDUALLY hold sufficient surplus-above-reserve to cover the cost alone (a single-signer,
  single-transaction transfer for a SAME-CHAIN funding path, matching the existing gojo/rescue transfer
  pattern already used in `economy/ubi/run.sh` — see the AKT funding route correction above for the
  Akash-specific, genuinely multi-hop exception), rather than attempting a new multi-wallet pooled
  transaction mechanism — this feature deliberately does not build multi-signer pooling.
- No single citizen individually holds enough, even though the AGGREGATE clears REQ-102's threshold:
  THE SYSTEM SHALL NOT proceed with the spawn this wake; it is logged as a funding-shortfall no-op
  (distinct from REQ-305's provisioning-failure state — no child record is even created), and
  re-evaluated on a future wake once some citizen's individual surplus alone suffices, or once the
  colony has more than one surplus-holding citizen able to co-fund via two SEPARATE single-signer
  transfers to the SAME child wallet (still no pooling — sequential individual transfers are allowed;
  a single joint transaction is not required and is explicitly out of scope).

**Acceptance Criteria**:
- Every on-chain transfer this feature initiates carries a memo/log entry naming (a) the REQ-102
  decision it was approved under and (b) the paying citizen's own identity — auditable after the fact.
- A structural/Tier-0 check confirms no code path in this feature ever reads a human-funded wallet's
  private key or balance as a funding source.
- **(resolves FIND-502)** The implementation's AKT-funding code path cites `config.json`'s
  `funding_route` field for the 4-hop bridge itself and `SKILL.md`'s own documented sequence for the
  Solana-side Jupiter pre-step, as two separate citations — never merging the two into a single claim
  about either file. Whichever citizen actually funds a given Akash deploy, its funding-transfer code
  enters the documented Skip API route at THAT citizen's own real first hop (`"solana"` for a
  Solana-native funder, `"8453"` for a Base-native funder) — never hardcoding a Solana-only entry when a
  Base-native citizen's surplus is the one actually being spent.
- **(resolves FIND-1102)** Given two self-funded citizens, A and B, where NEITHER individually holds
  enough surplus-above-reserve to cover the deploy cost alone but their surplus TOGETHER does, and A's
  own single-signer transfer of a partial amount is followed SEQUENTIALLY (never simultaneously) by
  B's own single-signer transfer of the remaining amount, both to the SAME child wallet: THE SYSTEM
  SHALL complete both transfers, the child wallet's final balance SHALL equal the FULL required
  funding amount, and BOTH transfers SHALL be independently traceable in the funding ledger (each
  carrying its own paying citizen's identity, per the memo/log requirement above) — this is the
  co-funding SUCCESS path, distinct from the no-single-citizen-sufficient BLOCKED path the edge case
  above also describes when co-funding capability does not (yet) exist. **(resolves FIND-1202)** The
  per-transfer ceiling check (above) applies to EACH citizen's own transfer against THAT citizen's own
  certified surplus-above-reserve contribution — read directly, by name, from REQ-101's
  `computePerCitizenSurplusUsd({citizens, perCitizenReserveUsd})` output for that citizen's `citizenId`
  (never an independently re-derived or re-summed aggregate value) — never a single combined ceiling
  checked against the whole aggregate amount for one citizen's individual transfer.

---

### REQ-305: Deploy/spawn failure handling — no partial spawn
**EARS**: IF any step from REQ-201 through REQ-303 fails, THE SYSTEM SHALL leave no ledger entry
claiming the child is `"active"`; a partially-completed attempt SHALL be recorded with status
`"failed"` (or `"provisioning"` only while genuinely still in progress, per the existing
`child-spec.js::buildChildSpec`'s own `status:"provisioning"` initial value, assembled via
`buildChildSpec` called with all seven required fields populated per REQ-206's rules — the identity
anchor being the child's own `agentEvmAddress`+`agentId` once REQ-204 completes (this feature's children
never carry a `childInbox`), and `parentWallet`/`generation`/`seedUsdc`/`constitutionHash` set exactly
as REQ-206 now specifies (resolves FIND-204)) together with the specific failing step and error
message, any already-spent, non-refundable resource (e.g. an Akash deployment deposit not yet
converted into an active lease) SHALL be logged for colony accounting, and REQ-102's
`SPAWN_COOLDOWN_DAYS` timer SHALL NOT be considered "consumed" by a failed attempt UNLESS that failure
is itself the `FAILURE_COOLDOWN_CAP`-th (default `3`) recent failed attempt within the SAME window —
see REQ-102's own reconciled Cooldown Check and the edge case below, which describe this IDENTICAL
rule (resolves FIND-1101: REQ-102 and REQ-305 no longer describe two different behaviors) — mirroring
this project's existing HARD RULE 0.24 ("NO FAKE RUN... any failed step exits non-zero and leaves an
honest provisioning/failed ledger row, never a fabricated success").

**A stable attempt-timestamp field, `attempted_ms` (new, resolves FIND-1401, critical):** THE SYSTEM
SHALL set a new field, `attempted_ms`, to `nowMs` on the very FIRST `ledger.js` row ever appended for a
given `child_id` — the initial `status:"provisioning"` row assembled via `buildChildSpec` above — and
EVERY LATER row appended for that SAME `child_id` (a `"failed"` row from this SAME requirement, an
`"active"` row per the paragraph below, or REQ-402's `"bootstrap_failed"` row) SHALL copy forward that
SAME original `attempted_ms` value, verbatim, from that child's first row — NEVER generate a new
timestamp for a follow-up row. This follows the EXACT precedent this SAME requirement already
establishes for `active_since` (below): an extra field the effectful caller merges into
`buildChildSpec`'s base returned object before calling `appendChild` — `child-spec.js`/`buildChildSpec`
itself is NOT modified for this, remaining exactly as classified in the Purity Boundary Map (Pure Core,
existing, extended only for REQ-206's identity-anchor rule). This is the SOLE data source for REQ-102's
Cooldown Check's `recentSpawnAttempts[].ts` value, via the new `deriveRecentSpawnAttempts` function
(REQ-102, above) — closing FIND-1401's first gap, where no cited data source existed anywhere for a
failed (or in-flight) row's timestamp.

WHEN, and only when, a spawn attempt completes and the child is marked `"active"` (REQ-204+REQ-205 both
complete), THE SYSTEM SHALL, in that SAME ledger.js row, ALSO set a new field `active_since` to the
current timestamp (never omitted, never set earlier at the `"provisioning"` stage) — this is the SOLE
field REQ-402's window check and REQ-101's `filterProductiveCitizens` join read (resolves FIND-201's
location contradiction: this lifecycle fact lives exclusively in `ledger.js`, never in
`citizens.json`). THE SYSTEM SHALL ALSO append a new record for that child to REQ-105's colony citizen
registry — the DURABLE runtime file at `CITIZENS_REGISTRY_PATH` (`~/anicca/skills/self/spawn/lib/
registry-path.mjs`, resolved via `resolveStateDir({env, home})`, e.g. `~/.hermes/state/citizens.json`
today — NEVER the git-tracked seed template, `citizens.seed.json`, which this append NEVER touches
again after its one-time bootstrap read, resolves FIND-901; and NEVER `economy/ubi/colony-wallets.json`,
which this feature never touches, per REQ-105's FIND-101 revision) — `{id: child_id, wallet: {evm:
true, solana: true-if-generated} (BOOLEAN presence flags, matching `is-self-funded.mjs::hasOwnWallet()`'s
own documented contract exactly — resolves FIND-104), walletAddress: {evm: childWallet, solana:
childSolanaAddress-if-generated} (the actual address STRING(s) — a SEPARATE field from `wallet`, never
passed to `isSelfFunded()`), fuel: {provider: "free-model"} (per REQ-401's exclusive free-model fuel
requirement), humanDependencies: [], homeDir: <the child's own resolved absolute `HOME`/`ANICCA_HOME`
directory, REQ-203 — resolves FIND-202>, coLocatedWithCoordinator: false}` — **resolves FIND-703:** THE
SYSTEM SHALL ALWAYS set `coLocatedWithCoordinator` to exactly `false` for every REQ-305 append — never
`true`, and never a computed/inferred value — because REQ-301's own absolute mandate makes a
co-located spawned child structurally impossible this increment (every child is deployed exclusively via
REQ-302 or REQ-303, never onto the coordinator host itself); this is a fixed structural constant for this
increment, not a judgment call an implementer evaluates per spawn. This is the field REQ-403's
live-audit enumeration filters on to correctly EXCLUDE every spawned child from its live-comparison
half's candidate set (resolves FIND-703; see REQ-403) — NO `telemetryPath` field (removed from this schema,
resolves FIND-302; REQ-101's balance lookup for this child, like every other citizen, goes through the
registry-driven public-RPC `readCitizenBalances` step keyed on `walletAddress` above) — so REQ-101's
NEXT evaluation includes the new citizen automatically, without any separate manual or out-of-band
registry-edit step (resolves FIND-002's "how does the registry grow" gap). This registry record
deliberately carries NEITHER `status` NOR `active_since` — those remain exclusively in the ledger.js
row set above.

**Cross-file field-name disambiguation (resolves FIND-304):** the `ledger.js` row this feature writes
for each child (first paragraph above, assembled via `buildChildSpec`) already carries a field named
`wallet` — this is `buildChildSpec`'s own, pre-existing, UNMODIFIED returned-row field (`child-spec.js:
37`: `wallet: childWallet`, a bare address STRING; see REQ-206's own disambiguation note), NOT the
boolean-shaped `wallet` object this same paragraph just appended to `citizens.json`. The two `wallet`
fields — one in `ledger.js`'s JSONL rows (a string, untouched code) and one in `citizens.json`'s
registry records (a boolean pair, REQ-105) — share a name only by coincidence across two unrelated
files/schemas this feature touches; implementers and reviewers reading these two files side by side
MUST read each `wallet` field per its OWN file's schema, never cross-reference the two.

**Before this append is performed** (resolves FIND-101's permanent-hazard-closure requirement), THE
SYSTEM SHALL call the existing, unmodified `isSelfFunded()` on the new record's `{wallet, fuel,
humanDependencies}` sub-object — exactly the same gate REQ-101 itself would apply — and SHALL REFUSE
the append (logged as a distinct, non-silent REQ-305 append-failure; the child's ledger row remains
`"active"` since REQ-204+REQ-205 genuinely completed, but the registry-append reconciliation below
applies) if `isSelfFunded()` returns `false` for that exact record. This ensures the durable
`citizens.json` (at `CITIZENS_REGISTRY_PATH`) can NEVER come to contain a non-self-funded entry,
whether at its initial REQ-105 bootstrap (from `citizens.seed.json`) or at ANY later spawn-triggered
append — a permanent closure of the hazard, not merely a t=0 check.

**Edge Cases**:
- The cloud deploy (REQ-302/303) succeeds but ERC-8004 registration (REQ-204) subsequently fails: the
  child remains `"provisioning"`, is EXCLUDED from REQ-101's colony-surplus aggregation (it is not yet
  a citizen, and NO registry record is appended for it yet), and registration is retried up to a
  bounded retry window (to avoid wasting an already-paid, non-refundable lease) before the lease itself
  is torn down and the attempt marked `"failed"`.
- A failed attempt's cooldown-exemption (above) could in principle be exploited to attempt unlimited
  spawns by engineering repeated "failures": THE SYSTEM SHALL cap the number of failed attempts
  counted within any single `SPAWN_COOLDOWN_DAYS` window (`FAILURE_COOLDOWN_CAP`, default `3`) — this
  is the SAME `recentSpawnAttempts`-scanning cap REQ-102's own reconciled Cooldown Check applies
  (resolves FIND-1101: REQ-102 and REQ-305 now describe the IDENTICAL reconciled rule, never two
  different behaviors) — beyond that cap (i.e. once `FAILURE_COOLDOWN_CAP` `outcome:"failure"` entries
  already exist in the window, with ZERO `outcome:"success"` entries in it), the NEXT attempt within
  the SAME window is rate-limited exactly as a successful spawn would be, closing this gap. See
  PROP-305g for the exact boundary fixture: fewer than the cap → still eligible; the cap reached →
  rate-limited.
- The ledger write (`"active"`) succeeds but the SUBSEQUENT registry-append write fails FOR A TRANSIENT
  REASON (e.g. a filesystem error): THE SYSTEM SHALL retry the registry-append on the NEXT wake before
  any further spawn evaluation runs — a child marked `"active"` in the ledger but absent from the
  registry is a detectable inconsistency (the next REQ-101 aggregation run reconciles it), never a
  silent, permanent gap.
- The registry-append is REFUSED because the new record fails its own `isSelfFunded()` pre-append check
  (e.g. an upstream bug produced a `wallet` object with no `true` flags): THE SYSTEM SHALL treat this as
  a DISTINCT failure mode from the transient-filesystem-error case above — it is NOT blindly retried on
  the next wake (retrying an isSelfFunded-refusal without fixing the underlying defect would either loop
  forever or eventually succeed for the wrong reason) — instead it SHALL be surfaced as a BLOCKING
  colony-accounting anomaly requiring explicit remediation; the child remains `"active"` in the spawn
  ledger (REQ-204+REQ-205 genuinely completed) but is PERMANENTLY excluded from REQ-101's aggregation
  until the anomaly is fixed and the append is manually/explicitly retried.
- **(new, resolves FIND-901)** A REQ-305 append happens WHILE a routine `git checkout`/`git worktree
  add|remove`/`git pull` is running concurrently on the `~/anicca` repo: because the append target,
  `CITIZENS_REGISTRY_PATH`, resolves entirely outside the git working tree, THE SYSTEM SHALL be
  unaffected — the append is never lost, stashed, or overwritten by the concurrent git operation, and
  the git operation is never blocked or corrupted by the concurrent append (the two touch disjoint
  filesystem locations by construction).
- **(new, sprint-2, resolves FIND-2002)** A failure occurs in REQ-201/202/203/306/302/303 — i.e.,
  BEFORE an identity anchor (`agentEvmAddress`+`agentId`, REQ-204) exists at all — meaning
  `buildChildSpec` cannot yet be called (its own required-anchor validation would throw): see REQ-307's
  own edge case for the exact resolution (a minimal `{child_id, status:"failed", attempted_ms, error}`
  row appended directly via `ledger.js::appendChild`, never via `buildChildSpec`) — this is the SAME
  "partially-completed attempt SHALL be recorded" promise this requirement's own EARS clause already
  makes, stated once, canonically, at REQ-307, never restated independently here.

**Acceptance Criteria**:
- A structural/Tier-0 check of the ledger-writing code path confirms every write path that can leave a
  row behind sets `status` to one of `{"provisioning","active","failed"}` — never omits `status`, and
  never writes `"active"` from any branch that has not completed REQ-204+REQ-205.
- An integration test that injects a failure at each of REQ-201/202/203/204/205/302/303 in turn
  confirms the resulting ledger row's `status` and `error` fields correctly identify the failing step,
  and that REQ-101's next aggregation run excludes that child.
- An integration test confirms that marking a child `"active"` appends a new, correctly-shaped record
  (with `wallet` boolean flags and `walletAddress` strings correctly split — resolves FIND-104) to
  REQ-105's registry, and that a FAILED attempt appends NO registry record at all.
- A fixture where the new record's `{wallet, fuel, humanDependencies}` sub-object would fail
  `isSelfFunded()` (e.g. `fuel.provider` missing/unrecognized) results in ZERO append to the durable
  `citizens.json` and a logged, distinct refusal — never a silent append of a non-self-funded entry
  (resolves FIND-101).
- Marking a child `"active"` ALSO sets that SAME ledger.js row's `active_since` field to the current
  timestamp (never omitted, never set at the earlier `"provisioning"` stage) — the field REQ-402's
  window check and REQ-101's `filterProductiveCitizens` join both read (resolves FIND-201).
- **(new, resolves FIND-1401)** A structural/Tier-0 check confirms `attempted_ms` is set to `nowMs` on
  the FIRST `ledger.js` row ever appended for a given `child_id`, and that every SUBSEQUENT row
  appended for that SAME `child_id` (a `"failed"` row, an `"active"` row, or REQ-402's
  `"bootstrap_failed"` row) carries the IDENTICAL `attempted_ms` value copied forward from that first
  row — never a freshly-generated timestamp on a follow-up row (PROP-305h).
- The appended `citizens.json` record's `homeDir` field is an ALREADY-RESOLVED absolute path — a
  structural check confirms it never contains a `$HOME`/`ANICCA_HOME` template string (resolves
  FIND-202), and the appended record carries NO `telemetryPath` field at all (removed, resolves
  FIND-302).
- **(resolves FIND-703)** Every REQ-305 append sets `coLocatedWithCoordinator` to EXACTLY `false` — a
  structural/Tier-0 check confirms no code path in this feature's diff ever appends `true` (or any
  computed value) for this field, and an integration test on a real fixture append confirms the written
  record's `coLocatedWithCoordinator` is `false` — see PROP-305f.
- The real `buildChildSpec` call underlying this append supplies concrete values for all seven required
  fields per REQ-206's derivation rules (`parentWallet`, `generation`, `seedUsdc`, `constitutionHash`
  included, not just the identity-anchor pair) — resolves FIND-204.
- **(new, resolves FIND-901)** A structural/Tier-0 check confirms every REQ-305 append call targets
  `CITIZENS_REGISTRY_PATH` (imported from `registry-path.mjs`) — NEVER `citizens.seed.json`'s path — and
  a real fixture append followed by a fresh `git status`/`git diff` on `~/anicca` confirms the append
  produced ZERO changes to the git working tree (the durable file lives entirely outside it) — see
  PROP-105k.

---

### REQ-306: Deterministic cloud-target selection — Nosana vs Akash (resolves FIND-006)
**EARS**: WHEN a spawn attempt (REQ-102/103) proceeds and REQ-301's local-spawn-prohibition applies,
THE SYSTEM SHALL select which of Nosana (REQ-302) or Akash (REQ-303) is "the selected cloud target for
that attempt" via a single, deterministic, bookkeeping decision function `selectCloudTarget({
nosanaAvailable, nosanaPriceUsd, akashAvailable, akashPriceUsd }) → "nosana"|"akash"|"none"` — NEVER a
model/LLM judgment call (consistent with REQ-104's bookkeeping-only discipline, extended here to
cloud-target selection). THE SYSTEM SHALL query BOTH providers' current price/availability for the
SAME minimal workload spec immediately before each spawn attempt (Nosana: the CLI's own market-price
query for the configured market address; Akash: the `provider-services query market bid list`-
equivalent for the configured SDL) and SELECT the provider whose quoted price, normalized to a common
USD-equivalent estimate, is LOWER, given both are currently available (at least one biddable
node/market at query time). IF exactly one provider is currently available, THAT provider is selected
regardless of price. IF NEITHER provider is currently available, THE SYSTEM SHALL treat this as a
deploy failure under REQ-305 (no cloud target selected, no child record ever reaches beyond
`"provisioning"`) — this mirrors REQ-302/303's own existing "no open market/bid" failure paths,
generalized to the selection step itself.

**Edge Cases**:
- Both providers quote the exact same normalized USD price (a tie): THE SYSTEM SHALL default
  deterministically to `"nosana"` (a fixed, documented tie-breaker — arbitrary but CONSISTENT, never
  randomized, so identical inputs always produce the identical selection — bookkeeping determinism,
  matching REQ-104's own discipline).
- A price quote cannot be directly compared because the two providers price in different native tokens
  (Nosana: NOS/SOL-denominated; Akash: AKT/`uact`-denominated): THE SYSTEM SHALL normalize both to a
  USD-equivalent estimate. **Corrected (resolves FIND-305): this normalization is NOT already-available,
  reused infrastructure.** `akt-treasury.sh` (read in full) contains no live USD price query anywhere —
  it only compares NATIVE-denominated balances (`uact`/`uakt`, via `akash query bank balances`) against
  fixed native-unit thresholds, and the `P_mint≈0.66` figure its own comment documents is a ONE-TIME
  HISTORICAL OBSERVATION recorded at write time, not a callable, live rate function. A repo-wide grep
  (`nosana|market.*price|SOL.*price`, case-insensitive, across `~/anicca/skills`) confirms no NOS/USD or
  AKT/USD price-conversion utility exists anywhere in this codebase either. THE SYSTEM therefore requires
  a MINIMAL, genuinely NEW price-fetch step — one public spot-price API call per native token — rather
  than reusing a nonexistent oracle. This new step SHALL follow the exact, already-established,
  already-used PATTERN this codebase already applies three times for ETH-USD/SOL-USD
  (`runtime/dashboard/telemetry-poster.mjs::ethPrice()`, `runtime/dashboard/
  telemetry-post-franklin.mjs::solPrice()`, `skills/earn/execute-invest.mjs`'s own `ethPrice()`: a single
  `fetch()` to a public spot-price API, parsed to a number, fail-closed to `0` on any error) — a single
  new call for AKT-USD (no existing utility covers Akash's native token) and, if Nosana's configured
  market denominates in NOS rather than SOL, a single new analogous call for NOS-USD (the existing
  `solPrice()` mechanism is reused AS-IS, unmodified, if the market is SOL-denominated) — never a
  bespoke, multi-source, or judgment-based oracle design.
- The selection function's own PRICE QUERIES are I/O (effectful), but the COMPARISON/decision logic is
  pure given the two already-fetched quotes — mirroring this spec's existing effectful-shell-feeds-
  pure-core pattern (REQ-101's `readCitizenBalances`/`computeColonySurplusUsd` split); `selectCloudTarget`
  itself performs zero I/O.

**Acceptance Criteria**:
- Pure function `selectCloudTarget({ nosanaAvailable, nosanaPriceUsd, akashAvailable, akashPriceUsd })
  → "nosana"|"akash"|"none"`, zero I/O, given already-fetched quotes as input.
- `nosanaPriceUsd < akashPriceUsd`, both available → `"nosana"`. The reverse → `"akash"`. Equal prices,
  both available → `"nosana"` (documented tie-breaker). `nosanaAvailable=false`, `akashAvailable=true`
  → `"akash"` regardless of price (and vice versa). Both unavailable → `"none"`.
- REQ-302's and REQ-303's own EARS clauses ("Nosana/Akash is the selected cloud target for that
  attempt") are satisfied exactly when this function returns the matching string — no other selection
  path exists anywhere in this spec.

---

### REQ-307: The spawn orchestrator's single entry-point function (new, sprint-2, resolves FIND-2001)
**EARS**: WHEN REQ-102/103 jointly permit a spawn attempt to proceed (`decideColonySpawn` returns
`eligible:true` AND the `"colony-spawn"` lock, per REQ-103, is successfully acquired), THE SYSTEM SHALL
execute the ENTIRE remainder of that spawn attempt — REQ-201 through REQ-206's identity-generation
steps, REQ-306's cloud-target selection, REQ-302's or REQ-303's deploy (including REQ-304's funding),
and REQ-305's ledger/registry append — via exactly ONE new, named entry-point function,
`executeSpawnAttempt({ initialSkills, drivingCitizenWallet, nowMs = Date.now() }) → Promise<{ status:
"active"|"failed", childId, error? }>`, exported from a NEW module,
`~/anicca/skills/self/spawn/lib/spawn-orchestrator.mjs`. **This closes the one gap a full sweep of this
spec found (2026-07-08): every individual step (REQ-201-206, REQ-301-306) already has its own pinned
signature, but no function anywhere before this correction was named as the thing that calls them all,
in order, inside REQ-103's lock — the Purity Boundary Map's own row list (all "REQ-201/202/etc.
acceptance criteria are enforced here" citations) had no row for this binding function itself.** This
function SHALL contain NO decision/judgment logic of its own (mirrors REQ-104's bookkeeping-only
discipline and this project's own pre-existing `~/anicca/skills/self/spawn/run.sh`'s header comment,
"Decision core is pure JS ... this shell only orchestrates") — it is PURE SEQUENCING AND ERROR
PROPAGATION over the already-specified pure/narrow modules, calling each in the canonical order below
and never re-deriving, re-computing, or hardcoding any value those modules already own.

**Canonical call order** (never varied, never partially reordered — each step's own REQ number retains
full ownership of that step's internal behavior; this paragraph states ONLY the sequencing, not a
restatement of any step's own logic):
1. REQ-203's HOME/ANICCA_HOME distinctness check (BEFORE any key generation).
2. REQ-201's EVM wallet generation.
3. REQ-306's `selectCloudTarget` (a fresh price/availability query for THIS attempt, never a
   cached/earlier evaluation).
4. REQ-202's conditional Solana wallet generation, fed step 3's own `deployTarget` return value
   directly (this ordering — step 3 before step 4 — is what makes REQ-202's own already-specified
   PROP-202d binding possible at all).
5. REQ-302 (Nosana) or REQ-303 (Akash) deploy, selected by step 3's own return value — REQ-303's own
   internal two-pass funding-gate sequencing (REQ-304) runs entirely within this step.
6. REQ-204's ERC-8004 registration (requires the child's EVM wallet from step 2 and a reachable
   shelter from step 5).
7. REQ-205's `mcp.json` write.
8. REQ-206's `buildChildSpec` assembly (identity anchor = step 2's `agentEvmAddress` + step 6's
   `agentId`).
9. REQ-305's ledger append (the `"active"` row, `active_since` set) and citizen-registry append
   (gated on `isSelfFunded()`).

**Edge Cases**:
- A failure occurs at step 1, 2, 3, 4, or 5 (REQ-201/202/203/306/302/303) — i.e., BEFORE step 6
  (REQ-204) ever produces an `agentId` — meaning NEITHER of `buildChildSpec`'s two identity-anchor
  shapes (`childInbox`, never produced by this feature's design, or the `agentEvmAddress`+`agentId`
  pair) is yet available (new, resolves FIND-2002, critical: REQ-305's own EARS clause promises "a
  partially-completed attempt SHALL be recorded with status failed" for ANY failure from REQ-201
  THROUGH REQ-303, but its own cited mechanism, `buildChildSpec`, structurally CANNOT construct a row
  without an identity anchor that does not yet exist this early — an unaddressed gap until this
  correction): THE SYSTEM SHALL append a MINIMAL row directly via `ledger.js::appendChild` — NEVER via
  `buildChildSpec`, whose own required-anchor validation cannot yet be satisfied — carrying at minimum
  `{child_id, status:"failed", attempted_ms, error}` (`child_id` from `nextChildId`, which needs no
  identity anchor; `attempted_ms` set to `nowMs`, establishing this AS that `child_id`'s true first row,
  per REQ-305's own `attempted_ms`-lifecycle rule). No later, successful `buildChildSpec`-shaped row is
  ever retroactively required for an attempt that failed this early — REQ-101's
  `filterProductiveCitizens`/REQ-102's `deriveRecentSpawnAttempts` already key only on
  `status`/`attempted_ms`/`active_since`, never on `buildChildSpec`'s other, optional fields, so this
  minimal row is already sufficient input for both.
- A failure occurs at step 6, 7, 8, or 9 (REQ-204/205/206/305) — i.e., AFTER an identity anchor already
  exists: THE SYSTEM SHALL record the failure via the ALREADY-specified `buildChildSpec`-based path
  REQ-305 describes, exactly as today — this function adds no second, competing failure-recording path
  for this later window.
- The `"colony-spawn"` lock (REQ-103) is held for this function's ENTIRE execution, steps 1-9
  inclusive, released only in a `finally` block after step 9 completes OR after any step's failure has
  been ledgered (mirrors `withGigLock`'s own existing `try/finally` release discipline — REQ-307
  introduces no new release logic, only a new `fn` body passed into the EXISTING
  `withGigLock`/`withColonyLock` wrapper REQ-103 already specifies).
- `initialSkills`/`drivingCitizenWallet` are supplied by THIS function's OWN caller (the wake-cycle
  scheduler that already evaluated REQ-102/103) — `executeSpawnAttempt` does not itself decide or
  default either value; `initialSkills` is the SAME agent-chosen value REQ-104's carve-out and
  REQ-202's own PROP-202e already govern, and `drivingCitizenWallet` is REQ-206's own "the citizen that
  evaluated REQ-101/102/103 and is driving this spawn attempt" value, unchanged.

**Acceptance Criteria**:
- A structural/Tier-0 check confirms exactly ONE function, `executeSpawnAttempt`, in exactly ONE new
  module (`spawn-orchestrator.mjs`), calls REQ-201 through REQ-305's own already-exported
  functions/scripts in the canonical order above — no second, competing orchestration entry point
  exists anywhere in the diff.
- A structural/Tier-0 check confirms `executeSpawnAttempt`'s own function body contains no
  arithmetic/boolean eligibility logic (that belongs exclusively to `decideColonySpawn`, called by ITS
  OWN caller before `executeSpawnAttempt` is ever invoked) and no LLM/prompt reference — mirrors
  REQ-104's own structural check, extended to this new function.
- An integration test triggers a failure at each of steps 1 through 9 in turn and confirms: (a) for
  steps 1-5, a minimal `{child_id, status:"failed", attempted_ms, error}` row is appended directly
  (never via `buildChildSpec`); (b) for steps 6-9, the existing `buildChildSpec`-based failure path
  (REQ-305) is used; (c) in every case, no row anywhere claims `status:"active"` for that `child_id`.
- An integration test confirms the `"colony-spawn"` lock (REQ-103) is held from before step 1 begins
  until after step 9 completes (or a failure is ledgered), reusing PROP-103e's own staggered-race proof
  method against this REAL function rather than a fixture stand-in for it.

---

## REQ群D: $0-bootstrap 実証

### REQ-401: $0-bootstrap success criterion
**EARS**: WHEN a child instance has been marked `"active"` (REQ-204/205 complete), THE SYSTEM SHALL
consider its $0-bootstrap successful only when — using EXCLUSIVELY the `"free-model"` fuel provider
(the same `OWN_FUNDED_FUEL_PROVIDERS` entry `~/anicca/skills/_shared/lib/is-self-funded.mjs` already
defines) and its own wallet, with no funding beyond the one-time gas seed already recorded under REQ-204
— it achieves a first realized, on-chain gig settlement (`~/anicca/skills/economy/gig`) with a real
positive amount, resulting from the CHILD'S OWN autonomous `post`/`take`/`deliver`/`verify_and_pay`
participation (not one initiated/executed on its behalf by a parent or by this feature's own tooling —
matching SPEC.md §9.9's precedent that the measured event is the AGENT's own choice, not a scripted
proxy for it).

**Edge Cases**:
- The child's first realized gig counterparty is the SAME citizen that spawned it (plausible when only
  2-3 citizens exist): still counts — what is measured is the CHILD's own autonomous participation, not
  counterparty diversity — but the settlement itself MUST be independently re-verified via a fresh RPC
  balance read taken before and after (mirroring the exact method SPEC.md §9.9 already used to confirm
  Franklin#1's final `0.02` USDC balance via `eth_call balanceOf`), never accepted from either party's
  own self-report.
- The child never once selects the gig skill from its own available catalog within the bootstrap window
  (the exact "model doesn't autonomously select the slot" frontier SPEC.md §9.6 already documented and
  is still resolving for automaton as of this spec's writing): THIS IS NOT a defect to be worked around
  by this feature hardcoding a forced selection or scripted proxy call — doing so would violate this
  project's HARD RULE that judgment/selection belongs to the model, not to hardcoded control flow
  (`~/.claude/rules/building-effective-ai-agents.md` #1). REQ-402 defines the bookkeeping consequence of
  this outcome instead.
- Genuinely free inference becomes unavailable for the child's entire bootstrap window (upstream
  outage, e.g. the historical `nvidia/llama-4-maverick` 403 SPEC.md §9.2 already documented and fixed
  once): treated the same as REQ-402's timeout path — a bookkeeping fact, not blamed on the child.

**Acceptance Criteria**:
- Success is recorded only once an independent RPC call (not the gig board's own internal ledger alone)
  confirms the child's wallet balance increased by the settled amount.
- The ledger entry recording success references: the gig ID, the on-chain transaction hash, the balance
  delta as independently observed, and a timestamp — enough for a fresh adversary to re-derive the
  claim without trusting this feature's own self-report.

---

### REQ-402: Bootstrap failure/timeout handling
**EARS**: IF a child instance marked `"active"` has NOT achieved REQ-401's success criterion within
`BOOTSTRAP_WINDOW_DAYS` (default `14`, reusing REQ-102's own `SPAWN_COOLDOWN_DAYS` constant — which
REQ-102 itself now states defaults to `14` (resolves FIND-1301) — for
internal consistency rather than inventing an unrelated window), THE SYSTEM SHALL relabel that child
`"bootstrap_failed"` in the ledger — `~/anicca/skills/self/spawn/lib/ledger.js`'s own JSONL rows, the
SOLE canonical owner of this lifecycle fact (REQ-105's `citizens.json` is deliberately minimal per its
own exact-field-list design and carries neither `status` nor `active_since` — this feature never stores
a second, competing copy of either fact there, resolving FIND-201's location contradiction) — never
silently delete or destroy the child, its wallet, or its cloud lease. This relabeling is implemented as
`ledger.js::appendChild`-ing a NEW row carrying the SAME `child_id` and `status:"bootstrap_failed"` —
`ledger.js` itself gains NO update/upsert primitive and remains exactly `{readChildren, appendChild}`
(the identical discipline REQ-101/REQ-305 already establish for every other lifecycle transition) —
this new row ALSO copies forward, unchanged, the SAME `attempted_ms` value REQ-305 set on that child's
very first ledger row (never a freshly-generated timestamp for this relabeling row, resolves FIND-1401's
second gap); this new row becomes "the" effective row for that citizen precisely because REQ-101's own
`filterProductiveCitizens` join already reduces multiple rows sharing one `child_id` to the
LAST-appended row before applying its exclusion rule (last-write-wins, REQ-101's own naming) — REQ-402
does not introduce a second, competing reduction rule; it relies on that SAME one, by cross-reference,
resolving FIND-405's recurrence of FIND-301's class of ambiguity. `active_since` is itself a ledger.js
row field, set once by REQ-305 at the exact moment a child is first marked `"active"` (REQ-204+REQ-205
complete); REQ-402's window check is `now − active_since >= BOOTSTRAP_WINDOW_DAYS * 86400000`, read
directly from that same (last-appended, "active") row.

THE SYSTEM SHALL EXCLUDE a `"bootstrap_failed"` child from REQ-101's colony-surplus aggregation until it
produces its own first realized settlement (it does not count as a "productive" self-funded citizen
while `"bootstrap_failed"`, though its wallet may still technically satisfy `isSelfFunded()`'s
structural test — REQ-402 adds a SEPARATE productivity flag, not a change to that existing gate). This
exclusion is realized EXCLUSIVELY through REQ-101's own `filterProductiveCitizens` join step (see
REQ-101), which reads this exact ledger.js row per citizen — REQ-402 does not maintain, and this
requirement does not specify, any second, parallel exclusion mechanism.

THE SYSTEM SHALL record this outcome (a running `children_bootstrap_failed` count) for observability
ONLY — e.g. in the ledger row itself or in telemetry — and this count SHALL NOT be passed as a
parameter to, or otherwise change the behavior of, REQ-102's `decideColonySpawn`: REQ-102's gate
signature is pinned (see REQ-102's own Acceptance Criteria) and remains governed solely by its own
seven named parameters, unaffected by how many prior attempts failed (resolves FIND-203 — this is a
descope of the prior false promise, not a signature extension). This feature does not implement a
bootstrap-failure-aware spawn throttle this increment; a bootstrap failure never automatically triggers
or blocks a replacement spawn (that remains gated purely by REQ-102's own arithmetic).

**Edge Cases**:
- The child achieves REQ-401's criterion on day 15 (just past the window): the `"bootstrap_failed"`
  label is corrected to reflect success retroactively the moment the on-chain settlement is
  independently observed — the window gates a BOOKKEEPING classification (whether it currently counts
  toward the colony's productive surplus), not a hard kill-switch that destroys the child at day 14.
- Two or more children are simultaneously `"bootstrap_failed"`: each is tracked independently by its
  own `child_id`; this requirement does not rank, compare, or triage them against each other (no
  judgment call — consistent with REQ-104's bookkeeping-only design constraint).
- A `"bootstrap_failed"` child's cloud lease continues to accrue cost indefinitely with no plan to ever
  retry: THE SYSTEM SHALL record this state plainly (it is a real, ongoing colony cost) but this feature
  does NOT specify an automatic lease-teardown-on-bootstrap-failure policy — that decision is left to
  a future increment (P4/self-repair) or explicit operator action, to avoid this feature silently making
  an irreversible "give up on this child" judgment call of its own.

**Acceptance Criteria**:
- A scheduled/wake-triggered check reads `active_since` and `status` directly from
  `~/anicca/skills/self/spawn/lib/ledger.js`'s own rows (never from REQ-105's registry, which carries
  neither field) for every `"active"` child lacking a recorded REQ-401 success, compares
  `now - active_since` against `BOOTSTRAP_WINDOW_DAYS`, and, for exactly those past the window,
  `appendChild`s a NEW row for the SAME `child_id` with `status:"bootstrap_failed"` — never a mutation
  of the prior row, and never applied to any child not past the window (resolves FIND-405: this new row
  becomes "the" effective row for REQ-101's `filterProductiveCitizens` join precisely because that join's
  own last-write-wins reduction, REQ-101, picks up the LAST-appended row for each `child_id`). Every
  child this check considers is one already present in BOTH REQ-105's colony citizen registry (as a
  citizen record, appended by REQ-305 on activation) AND ledger.js (as one or more rows, appended at
  spawn time and again at activation) — REQ-402 does not maintain a third, separate list of children,
  nor does it add any update/upsert primitive to `ledger.js`, which stays exactly `{readChildren,
  appendChild}`.
- `filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays})` (REQ-101's new join
  function), given a citizen whose matching ledger.js row is flagged `"bootstrap_failed"`, excludes it
  from the productive-surplus sum even if its own registry-recorded balance is nonzero (e.g. residual
  gas-seed dust) — this is the ONLY mechanism REQ-402's exclusion is realized through; there is no
  second, parallel exclusion path anywhere in this spec.
- The `children_bootstrap_failed` count is recorded for observability only; a structural/Tier-0 check
  confirms REQ-102's `decideColonySpawn` signature and behavior are byte-identical whether or not any
  bootstrap failures have occurred (resolves FIND-203: no dangling REQ-402→REQ-102 data flow).
- **(resolves FIND-1401)** REQ-102's `deriveRecentSpawnAttempts` treats a `child_id` that ever reached
  `"active"` as `outcome:"success"` PERMANENTLY — a LATER `"bootstrap_failed"` relabeling for that SAME
  `child_id` never retroactively flips its `recentSpawnAttempts` entry to `outcome:"failure"`, and never
  creates a SECOND, additional entry for the same attempt; the relabeling row's `attempted_ms` is
  confirmed identical to that `child_id`'s first row (never a new timestamp) — a unit fixture
  (PROP-102f) confirms both properties together.

---

### REQ-403: Wallet mutual non-interference audit (live-comparison half scoped to co-located instances this increment — resolves FIND-303; enumeration keyed on `coLocatedWithCoordinator`, resolves FIND-703)
**EARS**: WHEN N ≥ 2 instances (any mix of pre-existing citizens and newly-spawned children) run
concurrently, THE SYSTEM SHALL provide a deterministic audit combining two independently-scoped halves:
(a) a static, grep-based source audit across every skill script and cron/job config, checking all three
path-reference forms (`$HOME/...`, `~/...`, and the fully-resolved absolute form), reusing the exact
method this project's own wallet-rotation work already established (memory
`feedback_move_refcheck_must_cover_skill_scripts_and_home_forms`: "grep ~/.openclaw/skills +
~/anicca/skills + cron in ALL 3 path forms") — this static half covers EVERY instance this increment
produces, INCLUDING a cloud-hosted child, because REQ-303's SDL boots that child by `git clone`-ing the
SAME OSS repo this static grep already runs against (no separate remote-source-audit mechanism is
needed for this half); with (b) a live runtime comparison — reusing `resolve-identity.mjs`'s existing
exported resolvers, invoked once per instance in REQ-105's registry — the DURABLE runtime file at
`CITIZENS_REGISTRY_PATH`, never the git-tracked seed template `citizens.seed.json` (resolves FIND-901)
— whose `coLocatedWithCoordinator`
field is exactly `true` (resolves FIND-703 — never an undefined/implicit "co-located" notion; today this
set is exactly `{automaton, Franklin}`, and any future EXCEPTIONAL co-located addition would also be
included by construction, though none is anticipated) with that instance's OWN `HOME`/
`ANICCA_HOME` (read from REQ-105's registry's `homeDir` field, an already-resolved absolute path, PLUS an
EXPLICITLY-CONSTRUCTED `env` object — never ambient `process.env` — see Acceptance Criteria and the
Explicit-env correction below, resolves FIND-603) — that PROVES no two `coLocatedWithCoordinator===true`
instances' resolved EVM or Solana signing keys are ever equal, and no such instance's resolved key-file
PATH ever points inside another such instance's own home directory. **Corrected, resolves FIND-703:**
every newly-spawned child is, per REQ-301's own absolute mandate, ALWAYS `coLocatedWithCoordinator:
false` (REQ-305) — a co-located spawned child is structurally impossible this increment, so this
live-comparison half NEVER runs against, and NEVER gates, a newly-spawned child's participation in
REQ-401's bootstrap; every spawned child is structurally EXCLUDED from this half's candidate set by
construction (its registry record's own `coLocatedWithCoordinator` value) and is covered ONLY by half
(a)'s static grep-sweep, which remains a blocking gate for it exactly as for any co-located instance
(see the Edge Cases below — this replaces an earlier, vacuous promise that this check runs "before any
newly-spawned co-located child" participates, a category that can never exist this increment).

**Scoping correction (resolves FIND-303, enumeration corrected FIND-703):** `resolve-identity.mjs`'s
exported resolvers (`resolveEvmPrivateKey`/`resolveSolanaSecret`) are a PURE LOCAL-FILESYSTEM primitive
(`fs.readFileSync` against `path.join(effectiveHome, '.automaton', 'wallet.json')`, confirmed by direct
read of that module's real source) — the coordinator process invoking them can only ever resolve a key
that lives on the coordinator's OWN local disk. Per REQ-301, a spawned child's wallet material lives
EXCLUSIVELY on its own remote Nosana/Akash lease, a physically separate filesystem the coordinator
cannot `fs.readFileSync` into, and this feature never transmits a child's own private key material back
to the coordinator over the network for comparison (that would itself violate REQ-201's private-key-
handling discipline — "must never appear in any log file, stdout capture that reaches persistent logs,
or process list," reasonably extended here to "or any network transmission"). THE SYSTEM SHALL therefore
SCOPE the live-comparison half of this audit, for THIS INCREMENT ONLY, to instances whose registry
record's `coLocatedWithCoordinator` field is `true` — today, automaton + Franklin, both on the Mac Mini
per REQ-106 — mirroring REQ-106's own already-established "this increment only, future work for
multi-host" precedent. A cloud-hosted spawned child (`coLocatedWithCoordinator: false`, structurally
guaranteed by REQ-305/REQ-301) is EXEMPT from the live-comparison check until a future increment adds a
genuine remote-audit mechanism (e.g. a self-check script deployed to the child that reports only a
boolean PASS/FAIL result — never key material — back to the coordinator). The STATIC grep-sweep half (a)
is UNAFFECTED by this scoping and continues to cover a cloud-hosted child's deployed source, per the EARS
clause above.

**Seed-data correction (resolves FIND-501 — critical):** the live-comparison half (b) is only a genuine
proof if the `homeDir` values it reads (REQ-105's registry) are each citizen's REAL, DISTINCT
`ANICCA_HOME` root — an earlier revision of REQ-105's seed data stored the SAME bare `$HOME` value
(`/Users/anicca`) for BOTH citizens, which `resolve-identity.mjs`'s own gating logic resolves to `null`
for EVERY chain for BOTH citizens (see REQ-105's corrected seed-data section for the full derivation),
making this audit either vacuously "pass" on two `null` results or never actually exercise either
citizen's real key material at all. With REQ-105's now-corrected seed values (`/Users/anicca/.anicca`
for automaton, `/Users/anicca/.blockrun` for Franklin), a real invocation of
`resolveEvmPrivateKey({home: citizen.homeDir, env: {HOME: COORDINATOR_HOME, ANICCA_HOME: citizen.homeDir}})`/
`resolveSolanaSecret({home: citizen.homeDir, env: {HOME: COORDINATOR_HOME, ANICCA_HOME: citizen.homeDir}})`
— an EXPLICIT `env` object, never the bare `{home: citizen.homeDir}` shape an earlier revision of this
section used (see the Explicit-env correction below, resolves FIND-603), and `COORDINATOR_HOME` being
the SAME canonical constant REQ-105 already defines above (resolves FIND-802 — never an
independently-hardcoded literal at this call site) — against each citizen's own corrected `homeDir`
actually resolves that citizen's REAL key material (never `null`) via `resolve-identity.mjs`'s own
existing legacy-fallback branch — confirmed by a live filesystem check of this coordinator host
(2026-07-07, file EXISTENCE only, key CONTENT never read or printed):
`resolveEvmPrivateKey({home: '/Users/anicca/.anicca', env: {HOME: COORDINATOR_HOME, ANICCA_HOME:
'/Users/anicca/.anicca'}})` resolves via the legacy `$HOME/.automaton/wallet.json` path
(`effectiveHome === path.join(legacyHome,'.anicca')` holds because the EXPLICITLY-PASSED `env.HOME` is
`COORDINATOR_HOME`'s resolved value) to `/Users/anicca/.automaton/wallet.json` — CONFIRMED PRESENT on
disk; and `resolveSolanaSecret({home: '/Users/anicca/.blockrun', env: {HOME: COORDINATOR_HOME,
ANICCA_HOME: '/Users/anicca/.blockrun'}})` resolves via the legacy `$HOME/.blockrun/.solana-session` path
(`effectiveHome === path.join(legacyHome,'.blockrun')` holds symmetrically) to
`/Users/anicca/.blockrun/.solana-session` — CONFIRMED PRESENT on disk. THIS is what proves genuine
pairwise key inequality: each citizen resolves ONLY its own real, non-null key material through its own
`homeDir`, and (per the module's own fail-closed gate, exercised identically) resolves `null` — never the
OTHER citizen's real secret — if either citizen's `homeDir` were ever passed into the resolver for the
OTHER chain/citizen. **This correction does NOT affect REQ-101/REQ-402's balance-lookup design**: that
mechanism (`readCitizenBalances`, REQ-101) reads exclusively `walletAddress` via public-chain RPC and
never reads or references `homeDir` at all (REQ-105's own Acceptance Criteria/PROP-105f already pin
`homeDir` as consumed ONLY by this REQ-403 audit) — confirmed explicitly, no residual doubt.

**Canonical coordinator-HOME constant, `COORDINATOR_HOME` (resolves FIND-701; formally DEFINED in
REQ-105 above, resolves FIND-802 — moved up so the symbol is established before ANY literal use
anywhere in this document, rather than being introduced only here, after this section's own worked
examples had already used the bare literal):** the Explicit-env correction below requires supplying
"the coordinator host's own real `$HOME`" as `env.HOME` on every invocation — REQ-105 above already
exports this constant, `COORDINATOR_HOME`, from `~/anicca/skills/self/spawn/lib/registry-path.mjs` (the
SAME module REQ-103 introduces for `CITIZENS_REGISTRY_PATH`), computed EXACTLY ONCE, at module-load
time, via Node's `os.homedir()` — see REQ-105 for its full definition, rationale, and its ONE,
parenthetical statement of its current real value on this host. REQ-403's live-audit script SHALL
import and use this SAME `COORDINATOR_HOME` constant for EVERY `env.HOME` value it passes to
`resolveEvmPrivateKey`/`resolveSolanaSecret` — never independently re-reading `process.env.HOME`/
`os.homedir()` a second time at the call site, never hardcoding a literal copy of REQ-105's stated
value. See PROP-403f for the corresponding structural check.

**Explicit-env correction (resolves FIND-603 — critical):** `resolve-identity.mjs`'s real legacy-fallback
gate depends on a SECOND, separate input this section's own prior worked examples never modeled. Reading
its actual source: `resolveEvmPrivateKey`/`resolveSolanaSecret` both open with `const e = env ||
process.env;`, then compute `const legacyHome = e.HOME;` — the legacy-fallback branch that actually
resolves both citizens' real keys (see the correction directly above) only fires when `legacyHome` (i.e.
`env.HOME` if an `env` object is passed, or bare AMBIENT `process.env.HOME` if it is not) equals the
literal string `/Users/anicca`. The prior worked examples in this section invoked the BARE shape
`resolveEvmPrivateKey({home: citizen.homeDir})` — passing no `env` key at all — which silently depended
on the CALLING PROCESS's own ambient `process.env.HOME` happening to already equal `/Users/anicca`. This
is exactly the class of hazard `resolve-identity.mjs` was built to eliminate (fail-closed,
never-ambient, per-instance money-key resolution — see that module's own header comment), and its OWN
reused test suite (`runtime/loop/__tests__/resolve-identity.test.mjs`) never exercises the bare
`{home: X}`-only shape: every one of its 20 test cases passes an explicit `env` object containing BOTH
`HOME` and (where applicable) `ANICCA_HOME` together. THE SYSTEM SHALL therefore specify that REQ-403's
live-audit script ALWAYS invokes both resolvers with an EXPLICIT, fully-constructed `env` object —
`resolveEvmPrivateKey({home: citizen.homeDir, env: {HOME: COORDINATOR_HOME, ANICCA_HOME:
citizen.homeDir}})` (and symmetrically for `resolveSolanaSecret`) — `COORDINATOR_HOME` being the SAME
canonical, `os.homedir()`-derived constant REQ-105 above defines (resolves FIND-701; NEVER the vague
"sourced from a registry/coordinator constant" phrase an earlier revision left unresolved, and NEVER the
bare `{home: X}` shape this section's own prior worked examples used, which depends on that same ambient
value being correct by accident — a launchd-style cron invocation is not guaranteed to set
`process.env.HOME` identically to an interactive shell's). See PROP-403e for the corresponding
explicit-env proof obligation (including a stripped/launchd-style minimal-`process.env` fixture proving
the explicit-`env` invocation makes the audit's result independent of its own launcher's ambient
environment) and PROP-403f for the `COORDINATOR_HOME`-import-identity structural check.

**Edge Cases**:
- The static grep audit finds a hardcoded/templated path in a cloud-init script or SDL that could
  resolve to a shared location across children (e.g. a copy-paste bug reusing the SAME literal
  `GIG_STATE_PATH` or wallet-file path across two SDL templates): THE SYSTEM SHALL treat this as a
  BLOCKING finding — the affected child(ren) SHALL NOT be marked `"active"` until fixed, even if no
  actual runtime collision has yet been observed (structural risk is enough to block, not requiring a
  live incident first).
- The live runtime comparison finds an ACTUAL key collision among CO-LOCATED instances (two co-located
  instances resolve the identical signing key): THE SYSTEM SHALL halt BOTH implicated instances from any
  further signing immediately (fail-closed security-incident response), not merely log a warning and
  continue.
- A cloud-hosted spawned child exists and is about to participate in REQ-401's bootstrap: THE SYSTEM
  SHALL NOT block it on the live-comparison half (that check does not run for it this increment,
  resolves FIND-303) — it IS still covered by the static grep-sweep half (a), which remains a blocking
  gate for it exactly as for any co-located instance.
- A new cloud-host template is added later (e.g. a third provider beyond Nosana/Akash) with a
  different environment-injection mechanism than either already-audited path: THE SYSTEM SHALL require
  the audit to be explicitly extended to that new mechanism before any child deployed via it is trusted
  — silent "probably fine by analogy" reasoning is not permitted for a money-safety check.

**Acceptance Criteria**:
- A repeatable audit script exists that, given REQ-105's colony citizen registry, (1) runs the static
  grep sweep across the WHOLE fleet (co-located AND cloud-hosted, since the latter's deployed source is
  the same repo, per the EARS clause above) and reports zero cross-instance path references, and (2)
  enumerates its live-comparison candidate set via `citizens.filter(c => c.coLocatedWithCoordinator ===
  true)` (resolves FIND-703 — never an undefined/implicit "co-located" notion; today this evaluates to
  exactly `{automaton, Franklin}`), reading each such instance's own `homeDir` field (an
  ALREADY-RESOLVED absolute path per REQ-105's schema — resolves FIND-202; the same registry REQ-101
  aggregates over, no second, parallel instance-enumeration mechanism is introduced for this audit), then
  invokes `resolveEvmPrivateKey`/`resolveSolanaSecret` once per candidate's own `homeDir`, ALWAYS passing
  an EXPLICIT `env` object (`{HOME: COORDINATOR_HOME, ANICCA_HOME: citizen.homeDir}` — `COORDINATOR_HOME`
  imported from `registry-path.mjs`, resolves FIND-701 — never a bare `{home: X}` call relying on ambient
  `process.env`, resolves FIND-603, see PROP-403e/PROP-403f), and asserts pairwise inequality across all
  resolved keys — this increment's live-comparison scope is exactly the `coLocatedWithCoordinator===true`
  set (resolves FIND-303/FIND-703); every spawned child (`coLocatedWithCoordinator: false`, by
  construction per REQ-305) is structurally excluded from step (2)'s candidate set and is covered only by
  step (1).
- Given a deliberately-injected test fixture where two fake instances both have
  `coLocatedWithCoordinator: true` and share a `HOME` (negative test), the audit correctly reports a
  collision — proving the check is not vacuously passing.
- **(resolves FIND-501, corrected resolves FIND-603/FIND-802)** Given today's two real, corrected
  registry entries, invoking `resolveEvmPrivateKey({home: '/Users/anicca/.anicca', env: {HOME:
  COORDINATOR_HOME, ANICCA_HOME: '/Users/anicca/.anicca'}})` — the EXPLICIT-`env` shape, never the bare
  `{home: X}` shape this section's own examples used before FIND-603, and using the SAME
  `COORDINATOR_HOME` constant every other invocation in this section uses, never an independently
  hardcoded literal (resolves FIND-802's internal-inconsistency finding: this bullet previously
  hardcoded the literal while the earlier bullet above it already correctly used the symbol) — returns a
  REAL, non-null EVM key resolved from `/Users/anicca/.automaton/wallet.json` (confirmed present on disk,
  2026-07-07), and invoking `resolveSolanaSecret({home: '/Users/anicca/.blockrun', env: {HOME:
  COORDINATOR_HOME, ANICCA_HOME: '/Users/anicca/.blockrun'}})` returns a REAL, non-null Solana secret
  resolved from
  `/Users/anicca/.blockrun/.solana-session` (confirmed present on disk, 2026-07-07) — NEITHER resolution
  is `null`, proving the live-comparison half actually reads real key material under BOTH the corrected
  seed data AND the explicit-env invocation shape, not two vacuous `null` results as either the prior
  bare-`$HOME` seed value (FIND-501) or an ambient-`process.env.HOME`-dependent bare `{home: X}` call
  (FIND-603) could each independently have produced.
