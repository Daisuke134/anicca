# Verification Architecture — anicca-agent-spawn (Phase 1b)

**feature**: anicca-agent-spawn · **mode**: strict · **increment**: same as `behavioral-spec.md`
(P3 colony-treasury-gated cloud spawn + $0-bootstrap verification) · **日付**: 2026-07-08 ·
**revision**: iteration 18, revised (spec review iteration-18 finding FIND-1701 resolved —
`decideColonySpawn`'s own `colonySurplusUsd` parameter — the single most consequential value the function
consumes, gating whether ANY spawn happens at all — had no "never hand-assembled, always the direct
return value of X()" binding sentence and no dedicated real-derivation proof obligation, unlike its
immediate signature-siblings `recentSpawnAttempts`/`childrenProvisioning`, which both already received
this exact treatment; `colonySurplusUsd` is now bound to THAT SAME evaluation's
`computeColonySurplusUsd({citizens: filterProductiveCitizens(...), perCitizenReserveUsd})` (REQ-101)
direct return value, REQ-102's own "multiple evaluations in the same wake" edge case is explicitly
resolved for this hazard (each evaluation calls this pipeline fresh; REQ-103's `"colony-spawn"` lock is
explicitly NOT relied upon, since that lock's own critical section begins only at REQ-201), a new proof
obligation PROP-102k adds the missing Tier-1/Tier-2 real-derivation integration check (mirrors
PROP-101j/PROP-102g/PROP-102i/PROP-202d), the Purity Boundary Map's `decideColonySpawn` row is updated
to cite it, and the Gate's item (1) is extended to require it — this iteration's own mandated
full-signature closeout of `decideColonySpawn`'s complete 8-parameter signature additionally confirmed
`spawnThresholdUsd`/`recentSpawnAttempts`/`childrenProvisioning`/`cooldownDays`/`failureCooldownCap`/
`nowMs` already correctly treated and closed one further minor asymmetry for `maxConcurrentSpawns`'s own
default (see `behavioral-spec.md`'s own iteration-18 changelog and
`reviews/spec/iteration-18/RESOLUTION-NOTES.md` for the full per-parameter table) — AND spec review
iteration-17 finding FIND-1601 resolved — REQ-202's
`needsSolanaWallet({initialSkills, deployTarget})` pinned two inputs with no real-system-state binding
rule: (a) `deployTarget` is now bound to THAT SAME spawn attempt's `selectCloudTarget(...)` (REQ-306)
direct return value, mirroring the identical discipline already established for
`recentSpawnAttempts`/`childrenProvisioning`; new proof obligation PROP-202d adds the missing
real-derivation integration check (mirrors PROP-102g/PROP-102i), and the Gate's item (4) — which never
cited any of REQ-202's own proof obligations at all — now requires PROP-202a/b/d/e. (b) `initialSkills`
had no specified source anywhere; resolved by extending REQ-104's existing agent-judgment carve-out to
explicitly name `initialSkills` too — the spawning agent chooses a new child's starting capabilities
together with its goal framing, never a hardcoded default or a mechanical copy of the parent's own
roster; new proof obligation PROP-202e adds the structural (Tier 0) check that `initialSkills` is never
hardcoded/defaulted in REQ-202's own orchestration (resolves FIND-1601, critical) — AND, found during
this SAME iteration's own mandated, genuinely exhaustive, checklist-driven full-parameter sweep: REQ-101's
own `filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays})` — the very function
FIND-1401/FIND-1501's own resolutions repeatedly cited as the established precedent for this binding
discipline — never itself stated the identical "never hand-assembled, always the real function's direct
return value" rule for its OWN `ledgerRows` (`ledger.js::readChildren()`'s real output) or `citizens` (a
real `CITIZENS_REGISTRY_PATH` read) arguments; PROP-102g's own citation claiming to "mirror
PROP-101d/PROP-101e's own real-derivation discipline" does not actually hold up, since both of those
obligations test the functions' own internal correctness against fixture inputs, never a real-orchestration
binding check. Resolved by adding the identical explicit binding sentence to REQ-101 for
`filterProductiveCitizens`'s `ledgerRows`/`citizens` arguments (and, by the same reasoning,
`readCitizenBalances`'s `citizens` argument); a new proof obligation, PROP-101j, adds the missing
Tier-1/Tier-2 real-derivation integration check (mirrors PROP-102g/PROP-102i), and the Gate's item (1b) is
extended to require it. This closes the fifth instance of this recurring failure class found across
iterations 14-17 — see `behavioral-spec.md`'s own iteration-17 changelog and
`reviews/spec/iteration-17/RESOLUTION-NOTES.md` for the full per-function, per-parameter classification
table — AND spec review iteration-16 finding FIND-1501 resolved —
REQ-102's `decideColonySpawn` pinned `childrenProvisioning` as a sibling input to `recentSpawnAttempts`,
in the exact same signature, but no function anywhere derived this count from `ledger.js`'s real rows
either — a new sibling pure function, same file, `countChildrenProvisioning({ledgerRows}) → number`,
now derives it: groups `ledgerRows` by `child_id`, reduces to the last-appended row per group
(last-write-wins, the SAME discipline `deriveRecentSpawnAttempts` already uses), and counts exactly the
groups whose last row's `status` is `"provisioning"` — a group whose last row is `"active"`,
`"failed"`, or `"bootstrap_failed"` is NEVER counted, closing both the double-counting hazard and the
permanent-spawn-block hazard (a stale `"provisioning"` row never superseded in the count) FIND-1401
already closed for its neighbor; new proof obligations PROP-102h (Tier 1, four-case unit fixture) and
PROP-102i (Tier 1/2, real-derivation integration discipline) are added, the Purity Boundary Map gains a
new `countChildrenProvisioning` row and the `decideColonySpawn` row is updated to cite it, and the Gate
gains a new item (1g) (resolves FIND-1501, critical) — AND, found during this same iteration's own
mandated full-spec sweep for the identical failure class (preemptive, not independently raised by the
adversary): `SPAWN_THRESHOLD_USD`'s `MIN_SHELTER_USD` override, `measured_last_shelter_cost_usd`, was
sourced from "REQ-303's shelter-cost ledger" in prose only, with no named function specifying how that
ledger's multiple, real, append-only entries reduce to the one value used; resolved by naming the
ledger module explicitly, `shelter-cost-ledger.js` (`{readShelterCostEntries, appendShelterCostEntry}`,
the SAME append-only discipline as `ledger.js`), and a new pure function, same file as
`filterProductiveCitizens`, `deriveMeasuredShelterCostUsd({shelterCostLedgerRows}) → number|null`,
returning `null` on an empty ledger or the LAST-appended entry's `settledLeaseCostUsd` otherwise
(last-write-wins, never an average/max/first-entry read); new proof obligation PROP-102j is added and
PROP-303c is corrected to cite this function by name — AND spec review iteration-14 finding FIND-1401
resolved —
REQ-102's Cooldown Check pinned `recentSpawnAttempts: Array<{ts, outcome}>` as an input, but no
function anywhere derived this array from `ledger.js`'s real rows — unlike REQ-101's exactly analogous
need, satisfied by the named, fully-specified `filterProductiveCitizens`; a new sibling pure function,
same file, `deriveRecentSpawnAttempts({ledgerRows}) → Array<{ts, outcome}>`, now derives it, reading
`ts` from a new `attempted_ms` field REQ-305 sets on the FIRST ledger.js row ever appended for a
`child_id` and copies forward unchanged onto every later row for that SAME `child_id` (including
REQ-402's `"bootstrap_failed"` row), and mapping `outcome` per `child_id` group (never per raw row) so
a `child_id` that ever reached `"active"` is PERMANENTLY `outcome:"success"` regardless of a later
`"bootstrap_failed"` relabeling, closing the double-counting hazard the prior spec left unresolved; new
proof obligations PROP-102f (Tier 1, four-case unit fixture), PROP-102g (Tier 1/2, real-derivation
integration discipline), and PROP-305h (Tier 0, `attempted_ms` field-lifecycle structural check) are
added, the Purity Boundary Map gains a new `deriveRecentSpawnAttempts` row and the `ledger.js`/
`decideColonySpawn` rows are updated to cite `attempted_ms`, and the Gate's item (1) is extended to
require all three (resolves FIND-1401, critical) — AND spec review iteration-13 finding FIND-1301
resolved — REQ-102's own `SPAWN_COOLDOWN_DAYS` constant, used repeatedly throughout REQ-102's Cooldown Check and
REQ-305's failure-cap reconciliation but never itself given an explicit default value anywhere in
`behavioral-spec.md` — unlike every sibling constant in the SAME requirement — now explicitly defaults
to `14` there, reusing `~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn`'s own existing
`rateLimitDays` parameter default (line 11) for consistency with prior art; REQ-402's
`BOOTSTRAP_WINDOW_DAYS` now correctly cites a REQ-102 default that actually exists rather than an
implied one; a new proof obligation, PROP-402e, verifies `BOOTSTRAP_WINDOW_DAYS` and
`SPAWN_COOLDOWN_DAYS` are configured to the IDENTICAL value by construction, never merely coincidentally
equal — mirroring this spec's own established "identical by construction, never merely close"
discipline already used for REQ-206's `seedUsdc`/REQ-204 gas-seed-transfer-amount pair (PROP-206g); the
Gate's item (10) is extended to require this identity check (resolves FIND-1301, major) — AND spec
review iteration-12 findings FIND-1201/1202 resolved —
REQ-103's `"colony-spawn"` lock critical section, previously stated with THREE mutually inconsistent
scopes across its EARS clause ("and beyond", open-ended), its own statePath prose ("REQ-101 through
REQ-305"), and its binding Acceptance Criteria ("REQ-201 through REQ-205, and the decision to proceed
into REQ-3xx" — textually EXCLUDING REQ-206's ledger append, REQ-304's funding, and REQ-305's append),
is unified to ONE identical scope stated the SAME way in all three places: the lock is held from
REQ-201's wallet generation THROUGH REQ-305's ledger append actually completing (the new citizen
durably recorded), never released earlier — closing a genuine STAGGERED (non-simultaneous)
double-spawn/double-funding race the narrower Acceptance-Criteria reading would otherwise have
permitted; a new proof obligation, PROP-103e, adds the missing staggered-timing fixture (a first
evaluator's REQ-304 funding step is deliberately delayed, and a second evaluator's repeated lock-acquire
attempts throughout that entire delay all fail, succeeding only after the first evaluator's REQ-305
append has landed), and the Gate's item (2) is corrected to require it alongside PROP-103a's existing
simultaneous-race fixture (resolves FIND-1201, critical). Separately, REQ-101 gains a new sibling pure
function, `computePerCitizenSurplusUsd({citizens, perCitizenReserveUsd}) → Array<{citizenId,
surplusUsd}>`, exposing EACH citizen's own `max(0, balance_i - perCitizenReserveUsd)` term individually
— `computeColonySurplusUsd` is now specified to be implemented by calling this function and summing its
output, guaranteeing the aggregate and the per-citizen breakdown can never diverge; REQ-304's
per-citizen ceiling-check Acceptance Criteria and PROP-304f's companion fixture now cite this function
by name, and a new proof obligation, PROP-101i, tests its own per-citizen correctness and its
by-construction consistency with `computeColonySurplusUsd`'s aggregate sum (resolves FIND-1202, major)
— AND spec review iteration-11 findings FIND-1101/1102 resolved —
REQ-102's `decideColonySpawn` signature is extended from a single scalar `lastSpawnAttemptMs` to a
richer `recentSpawnAttempts: Array<{ts, outcome}>` (reusing the SAME array-scan pattern
`~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn` already proves for its own rate-limit
check over `children[].spawned_ms`), reconciling REQ-102/REQ-305's cooldown-consumption contradiction
into ONE rule: a successful attempt in-window is always a hard cooldown gate; a failed attempt is
cooldown-exempt only below `FAILURE_COOLDOWN_CAP` (default `3`), beyond which it triggers cooldown
identically to a success; the Purity Boundary Map's `decideColonySpawn` row, PROP-102b, and PROP-305c
are corrected to reflect/test this SAME reconciled logic, and a new proof obligation, PROP-305g, adds
the exact "3 failures reached, cooldown now applies" boundary fixture (resolves FIND-1101, critical).
Separately, REQ-304 gains a new proof obligation, PROP-304f, covering the multi-citizen SEQUENTIAL
co-funding SUCCESS path (two citizens' own sequential single-signer transfers together fully funding
one child wallet, distinct from PROP-304c's existing insufficient-funds no-op test) (resolves
FIND-1102, major) — AND spec review iteration-10 findings FIND-1001/1002 resolved — REQ-105's
one-time bootstrap step is corrected from a check-then-act existence-check-then-copy to a
SINGLE atomic POSIX exclusive-create (`fs.open(CITIZENS_REGISTRY_PATH, 'wx')`, `O_CREAT|O_EXCL`)
operation, the SAME atomic primitive `~/anicca/skills/economy/gig/lib/lock.mjs::tryCreateLockFile`
already uses to close an identical class of check-then-act race (that module's own header comment
documents a REAL prior double-pay bug this pattern exists to prevent); a new proof obligation,
PROP-105l, adds both a concurrent-first-access-race fixture and a late-bootstrap-after-real-append
fixture (resolves FIND-1001, critical). Separately, the Purity Boundary Map row for the new
`registry-path.mjs` module (`CITIZENS_REGISTRY_PATH`/`COORDINATOR_HOME`) is corrected from "Pure Core"
to "Effectful Shell" — `CITIZENS_REGISTRY_PATH` is built from `resolveStateDir`, already classified
"Effectful Shell" two rows away in this SAME table, and `COORDINATOR_HOME` is built from a real
`os.homedir()` environment read, not a deterministic computation over its own inputs; a new proof
obligation, PROP-105m, adds the missing Tier-2 (real-environment-dependent) proof that `COORDINATOR_HOME`
genuinely tracks the real process environment rather than being treated as a fixed, zero-I/O constant
(resolves FIND-1002, major) — AND spec review iteration-10 finding FIND-901 resolved — the single
`citizens.json` artifact is SPLIT into a git-tracked SEED TEMPLATE, `citizens.seed.json` (read-only,
never mutated at runtime), and a DURABLE, out-of-git-tree runtime file resolved via
`CITIZENS_REGISTRY_PATH` = `path.join(resolveStateDir({env, home}), 'citizens.json')` — REUSING the
SAME `resolveStateDir({env, home})` mechanism (`~/anicca/skills/self/spawn/lib/state-path.js`)
`~/anicca/skills/self/spawn/run.sh` already uses for `children.jsonl`'s own durable location — closing
the "versioned seed vs. live-append target inside the git working tree" hazard; two new proof
obligations, PROP-105j (seed template never written to by runtime code, Tier 0) and PROP-105k
(`CITIZENS_REGISTRY_PATH` always routes through `resolveStateDir`, Tier 0, PLUS a live test proving a
real `git checkout`/`git worktree add`/`git pull` on `~/anicca` does not affect the durable
`citizens.json`, Tier 2), are added — see `behavioral-spec.md`'s own iteration-10 changelog for the
full design AND spec review iteration-9 findings FIND-801..802 resolved —
PROP-105g corrected to a genuine TWO-BRANCH re-derivation method, EVM via `viem::privateKeyToAccount`
against `walletAddress.evm` AND Solana via `@solana/web3.js::Keypair.fromSecretKey` against
`walletAddress.solana` (both already-real monorepo dependencies, no new dependency added), with a new
PROP-105i covering the dual-populated-citizen conjunctive-pass case, and Franklin's Solana address
LIVE re-derived and confirmed to match `citizens.json`'s seeded value; `COORDINATOR_HOME`'s definition
already correctly used throughout this file — see `behavioral-spec.md`'s own iteration-9 changelog for
FIND-802's fix, which was scoped to that file's prose reading-order, this file having already been
internally consistent — AND spec review iteration-1 findings FIND-001..006 resolved AND
spec review iteration-2 findings FIND-101..104 resolved AND spec review iteration-3 findings
FIND-201..206 resolved AND spec review iteration-4 findings FIND-301..305 resolved AND spec review
iteration-5 findings FIND-401..405 resolved AND spec review iteration-6 findings FIND-501..504
resolved AND spec review iteration-7 findings FIND-601..604 resolved (PROP-105g's walletAddress-
verification-method rule, the two stale Akash-funding-route summary tables corrected, PROP-403e's
explicit-`env` invocation rule, and PROP-101h's dual-wallet-both-fail fixture) AND spec review
iteration-8 findings FIND-701..703 resolved (a new `COORDINATOR_HOME` constant exported from
`registry-path.mjs` alongside `CITIZENS_REGISTRY_PATH`, plus PROP-403f's import-identity structural
check; PROP-105g rewritten from a citation-presence check to an actual mechanical re-derivation, plus
an explicit in-memory-read carve-out reconciling it with REQ-105's "existence only" secrets discipline;
a new `coLocatedWithCoordinator` registry field, PROP-105h/PROP-305f, and PROP-403b/PROP-403d's
enumeration now keyed on that real field instead of an implicit notion), mirrors
`behavioral-spec.md`'s own changelogs: REQ-105/
106/206/306 added, REQ-101/103/204/305 amended, then REQ-103/105/206/305 further amended for
FIND-101/102/103/104 — new registry path `citizens.json`, canonical `CITIZENS_REGISTRY_PATH` constant,
`wallet`/`walletAddress` field split, and REQ-206's "at least one, not XOR" clarification — then
REQ-101's new `filterProductiveCitizens` join, REQ-105's new `homeDir` field + already-resolved
`telemetryPath`, REQ-402's descoped `children_bootstrap_failed` observability-only count, and REQ-206's
extension to `parentWallet`/`generation`/`seedUsdc`/`constitutionHash` for FIND-201..206 — then, for
FIND-301..305: `filterProductiveCitizens`'s last-write-wins duplicate-`child_id` rule, `telemetryPath`
REMOVED from REQ-105's schema in favor of a new registry-driven public-RPC `readCitizenBalances`
mechanism, REQ-403's live-comparison half scoped to co-located instances only this increment, a
cross-file `wallet`-field disambiguation note, and REQ-306's price-normalization claim corrected to a
genuinely new, pattern-reused price-fetch step — then, for FIND-401..405: REQ-303's new post-lease
secrets-injection step (`provider-services lease-shell`) + reused `spawn-child/lib/akt-cost-gate.js`
funding-readiness gate + new child-specific SDL `HOME=/root` line, REQ-302's new post-boot
secrets-injection step (`nosana job ssh`), REQ-304's AKT funding-route correction (multi-hop
Jupiter+Skip-API bridge, reusing `spawn-child/config.json`'s documented route), REQ-101's dual
evm+solana balance-summing rule, and REQ-402's explicit cross-reference to REQ-101's last-write-wins
`appendChild` reduction — then, for FIND-501..504: REQ-105's `homeDir` seed values corrected to each
citizen's REAL, DISTINCT `ANICCA_HOME` root (never the shared bare `$HOME`), PROP-403b corrected to cite
the exact real resolved paths this now produces, REQ-304/PROP-304d's citation split into `config.json`
(the 4-hop bridge field) vs `SKILL.md` (the Jupiter pre-step) plus a new PROP-304e recording a
live-confirmed Base-native (`8453`) alternative entry into the same Skip API route, REQ-101/PROP-101g's
new per-chain-independent fail-closing fixture, and REQ-302/303's CLI-primitive citations pointed at a
newly-captured on-disk evidence transcript rather than inline prose)

## Purity Boundary Map (file/function level)

| Layer | Location | Purity | Notes |
|---|---|---|---|
| **Pure Core (existing, reused unmodified)** | `~/anicca/skills/_shared/lib/is-self-funded.mjs::isSelfFunded`/`selfFundedReasons` | PURE | Already implemented, already unit-tested (`__tests__/is-self-funded.test.js`). REQ-101 calls this as-is, on each record's `{wallet, fuel, humanDependencies}` sub-object supplied by REQ-105's registry, to decide which citizens' balances even enter the aggregation; no new judgment logic. `wallet.evm`/`wallet.solana` are consumed here strictly in their documented BOOLEAN shape — `walletAddress` (the real address string(s), REQ-105/REQ-104 below) is a SEPARATE field never passed to this function (resolves FIND-104's type-mismatch finding). |
| **Static config asset (git-tracked, NEVER mutated at runtime; new, resolves FIND-901)** | `~/anicca/skills/self/spawn/registry/citizens.seed.json` | EFFECTFUL (read-only, git-tracked) | A brand-new, git-tracked seed template holding the FIXED LITERAL 2-entry starting array (`{id, wallet: {evm?: boolean, solana?: boolean}, walletAddress: {evm?: string, solana?: string}, fuel: {provider}, humanDependencies: [], homeDir, coLocatedWithCoordinator: boolean}` records, `telemetryPath` REMOVED, resolves FIND-302). Read exactly ONCE — at the durable runtime file's one-time bootstrap copy (next row) — and NEVER written to by any runtime code path this feature adds, and NEVER read again after that bootstrap (PROP-105j). Committed to git as part of this feature's own versioned codebase. |
| **Effectful Shell (BRAND NEW, dedicated, durable, OUT-OF-GIT-TREE — REQ-105, revised to resolve FIND-101/202/302/703/901)** | `CITIZENS_REGISTRY_PATH` (`~/anicca/skills/self/spawn/lib/registry-path.mjs`) = `path.join(resolveStateDir({env, home}), 'citizens.json')` | EFFECTFUL (new) | REUSES, not reimplements, the SAME `resolveStateDir({env, home})` function (`~/anicca/skills/self/spawn/lib/state-path.js`, see its own dedicated row below) `run.sh` already calls for `children.jsonl`'s own durable location (today: `~/.hermes/state/citizens.json`, alongside `~/.hermes/state/children.jsonl`) — a location OUTSIDE the `~/anicca` git working tree, immune to `git checkout`/`git worktree add\|remove`/`git pull` (resolves FIND-901). **Corrected, resolves FIND-1001 (critical):** bootstrapped via a SINGLE atomic POSIX exclusive-create (`fs.open(CITIZENS_REGISTRY_PATH, 'wx')`, `O_CREAT\|O_EXCL`) — never a check-then-act "does the file exist? then copy" pair — writing `citizens.seed.json`'s content verbatim ONLY if the exclusive-create succeeds; if it fails with `EEXIST` (another racer's bootstrap already won, OR a real REQ-305 append already happened), NOTHING is written and the caller simply reads the existing content, which can therefore never be overwritten by a late bootstrap attempt (PROP-105l) — then diverges permanently via REQ-305's runtime appends — the git-tracked seed template above is never touched again (PROP-105k). Holds the SAME record shape as the seed template — the BOOLEAN-shaped `wallet` sub-object is the EXACT shape `isSelfFunded()` already requires (resolves FIND-104; note this `wallet` is UNRELATED to `child-spec.js`'s own returned-row `wallet` STRING field, see the `child-spec.js` row below, resolves FIND-304), `walletAddress` separately carries the real address string(s) and is what `readCitizenBalances` keys its RPC query on, and `homeDir` is an already-resolved absolute path (never an unresolved `$HOME` template — resolves FIND-202) — **corrected, resolves FIND-501 (critical): each seeded entry's `homeDir` is that citizen's own REAL, DISTINCT `ANICCA_HOME` root (automaton `/Users/anicca/.anicca`, Franklin `/Users/anicca/.blockrun`), never the shared physical machine's bare `$HOME` an earlier revision wrongly used for both — co-located (REQ-106, same physical host) does NOT mean "same `homeDir`"** — feeding REQ-403's now co-located-only-scoped audit (resolves FIND-303). **New, resolves FIND-703 (critical): `coLocatedWithCoordinator` is a structural classifier (never a judgment call), seeded `true` for both of today's citizens (both genuinely co-located on the Mac Mini today) and ALWAYS appended `false` by REQ-305 for any newly-spawned child (per REQ-301's absolute mandate that a spawned child is never co-located) — REQ-403's live-audit enumeration filters on this exact field (`citizens.filter(c => c.coLocatedWithCoordinator === true)`) rather than an undefined/implicit "co-located" notion.** This registry deliberately carries NEITHER `status` NOR `active_since` — those lifecycle facts live exclusively in `ledger.js` (see below, resolves FIND-201). Resolves FIND-002 (the previously-undefined dynamic citizen registry). Sharing ZERO state with `~/anicca/skills/economy/ubi/colony-wallets.json` (next row) — resolves FIND-101's critical finding that an earlier draft wrongly proposed repurposing that live, differently-scoped file. |
| **Effectful Shell (existing, reused unmodified — new to this feature, resolves FIND-901)** | `~/anicca/skills/self/spawn/lib/state-path.js::resolveStateDir({env, home})` | EFFECTFUL (existing, reused unmodified) | Already implemented, already the mechanism `~/anicca/skills/self/spawn/run.sh` (lines 39-45) uses TODAY for `children.jsonl`'s durable location (confirmed by direct read). Its own header comment documents the real 2026-06 incident it exists to prevent: a spawn ledger written to `/tmp` was deleted by the OS tmp-cleaner. Fail-closed: throws if the resolved dir is `/tmp`- or `/private/tmp`-rooted. REQ-103/105's `CITIZENS_REGISTRY_PATH` (row above) calls this SAME function unmodified — no new state-directory-resolution logic is written for this feature. |
| **Effectful Shell (existing, UNTOUCHED, out of scope)** | `~/anicca/skills/economy/ubi/colony-wallets.json` | EFFECTFUL (existing, not read/written by this feature) | `ubi.js::distributeAI`'s own recipient-eligibility list ("addresses proven to be real colony members," its own JSDoc) — a DIFFERENT purpose than REQ-101's surplus aggregation. Its current 2nd entry is claude-p's own human-funded wallet (`docs/WALLETS.md` lines 49-62). This feature never reads, writes, or repurposes this file; listed here ONLY to make explicit (per FIND-101) that it is a separate, unmodified concern sharing zero state with `citizens.json` above. |
| **Pure Core (new — extended, resolves FIND-1202)** | new module, e.g. `~/anicca/skills/self/spawn/lib/treasury-gate.mjs::computeColonySurplusUsd({citizens, perCitizenReserveUsd}) → number`, PLUS a new sibling in the SAME file, `::computePerCitizenSurplusUsd({citizens, perCitizenReserveUsd}) → Array<{citizenId, surplusUsd}>` | PURE (new) | `computeColonySurplusUsd`: sum of `max(0, balance_i - reserve)` over `isSelfFunded()`-passing citizens only; zero I/O once given already-fetched balances; runs ONLY on `filterProductiveCitizens`'s output (next row), never on the raw registry array. **New, resolves FIND-1202 (major):** `computePerCitizenSurplusUsd` exposes that SAME per-citizen term individually, one `{citizenId, surplusUsd}` record per citizen; `computeColonySurplusUsd` is implemented by CALLING this function and summing its `surplusUsd` values, never an independently-written reduce, so the two can never silently diverge (PROP-101i). REQ-304's per-citizen ceiling check reads this function's output directly, by name. REQ-101's acceptance criteria. |
| **Pure Core (new)** | new module, same file, `~/anicca/skills/self/spawn/lib/treasury-gate.mjs::filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays}) → citizens[]` | PURE (new) | Resolves FIND-201: a new join function, zero I/O, that cross-references REQ-105's registry (`citizens`) against `ledger.js`'s own rows (`ledgerRows`, matched by `id`===`child_id`) and excludes any citizen whose matching row is `"bootstrap_failed"` or window-overdue-while-`"active"`; a citizen with no matching row (e.g. today's two non-spawned seed citizens) passes through unfiltered. Resolves FIND-301: `ledgerRows` may contain MULTIPLE rows sharing one `child_id` (real, existing `ledger.js` behavior, proven by `run.sh`'s own provisioning-row-then-status-row pattern) — this function FIRST reduces to exactly one effective row per `child_id` (the LAST-appended row — last-write-wins) BEFORE applying its exclusion rule. This is the ONLY place `status`/`active_since` cross REQ-101's aggregation boundary — `citizens.json` itself never carries either field. **New, resolves the sweep-found sibling gap alongside FIND-1601:** `ledgerRows` is never hand-assembled by the calling orchestration — it is ALWAYS `ledger.js::readChildren(...)`'s real output; `citizens` is likewise never hand-assembled — it is ALWAYS a real read of `CITIZENS_REGISTRY_PATH`'s content, never an independently reconstructed or cached list; `computeColonySurplusUsd`/`readCitizenBalances` both receive this SAME filtered array unchanged (PROP-101j). REQ-101/REQ-402's acceptance criteria. |
| **Pure Core (new, resolves FIND-1401, critical)** | new module, same file, `~/anicca/skills/self/spawn/lib/treasury-gate.mjs::deriveRecentSpawnAttempts({ledgerRows}) → Array<{ts: number, outcome: "success"|"failure"}>` | PURE (new) | Resolves FIND-1401: REQ-102's Cooldown Check pinned `recentSpawnAttempts` as an input but no function anywhere derived it from `ledger.js`'s real rows — the exactly analogous gap `filterProductiveCitizens` (row above) already closes for REQ-101. This function GROUPS `ledgerRows` by `child_id` (the SAME grouping key `filterProductiveCitizens` uses) and returns exactly ONE entry per group — never one per raw row, closing a double-counting hazard. `ts` is read from the group's `attempted_ms` field (identical across every row in the group by construction, set by REQ-305, see the `ledger.js` row below). `outcome` is `"success"` PERMANENTLY if the group ever reached `status:"active"` — a LATER `"bootstrap_failed"` row (REQ-402) never retroactively flips this, per REQ-102's own "a successful attempt is ALWAYS cooldown-triggering" rule; else `"failure"` if the group's LAST (last-write-wins) row is `"failed"`; else the group is EXCLUDED entirely if its last row is still `"provisioning"` (an in-flight attempt, already counted via `childrenProvisioning`/`MAX_CONCURRENT_SPAWNS`, never double-counted here). REQ-102's real orchestration calls this function directly over `readChildren`'s real output, never a hand-rolled reimplementation at the call site. REQ-102's acceptance criteria. |
| **Pure Core (new, resolves FIND-1501, critical)** | new module, same file, `~/anicca/skills/self/spawn/lib/treasury-gate.mjs::countChildrenProvisioning({ledgerRows}) → number` | PURE (new) | Resolves FIND-1501: REQ-102's `decideColonySpawn` pinned `childrenProvisioning` as a SIBLING input to `recentSpawnAttempts` (same signature) but no function anywhere derived it from `ledger.js`'s real rows either — the identical gap `deriveRecentSpawnAttempts` (row above) already closes for its neighbor. This function GROUPS `ledgerRows` by `child_id` (the SAME grouping key `filterProductiveCitizens`/`deriveRecentSpawnAttempts` use), reduces EACH group to its LAST-appended row (last-write-wins), and COUNTS exactly the groups whose last row's `status` is EXACTLY `"provisioning"` — a group whose last row is `"active"`, `"failed"`, or `"bootstrap_failed"` is NEVER counted, regardless of an earlier `"provisioning"` row for that SAME `child_id` — closing both the double-counting hazard (a naive per-row scan) and the permanent-block hazard (a stale `"provisioning"` row never superseded in the count, which would otherwise leave `childrenProvisioning >= maxConcurrentSpawns` permanently true and silently block every future spawn forever). REQ-102's real orchestration calls this function directly over `readChildren`'s real output, never a hand-rolled reimplementation at the call site, mirroring `deriveRecentSpawnAttempts`'s own integration discipline. REQ-102's acceptance criteria. |
| **Pure Core (new, resolves the sweep-found sibling gap alongside FIND-1501)** | new module, same file, `~/anicca/skills/self/spawn/lib/treasury-gate.mjs::deriveMeasuredShelterCostUsd({shelterCostLedgerRows}) → number\|null` | PURE (new) | Resolves the gap found during this iteration's mandated full-spec sweep: REQ-102's `SPAWN_THRESHOLD_USD` formula named its `MIN_SHELTER_USD` override, `measured_last_shelter_cost_usd`, as sourced from "REQ-303's shelter-cost ledger" in prose only, with no named function specifying how that ledger's multiple, real, append-only entries reduce to the ONE value used — the identical failure class one step removed. This function returns `null` on an empty `shelterCostLedgerRows` (no real deploy has ever completed — `MIN_SHELTER_USD` stays its provisional `5.00` default), else reduces to the LAST-appended entry (last-write-wins, the SAME discipline `filterProductiveCitizens`/`deriveRecentSpawnAttempts`/`countChildrenProvisioning` already apply to `ledger.js`'s own rows) and returns that entry's `settledLeaseCostUsd` — NEVER an average, sum, or historical-max across every accumulated entry, and never the first-ever entry. REQ-102/REQ-303's acceptance criteria. |
| **Effectful Shell (new, resolves the sweep-found sibling gap alongside FIND-1501)** | new module `~/anicca/skills/self/spawn/lib/shelter-cost-ledger.js::readShelterCostEntries`/`::appendShelterCostEntry` | EFFECTFUL (new) | The persistent shelter-cost ledger REQ-303 writes to and REQ-102's `deriveMeasuredShelterCostUsd` (row above) reads from — append-only JSONL, exporting EXACTLY `{readShelterCostEntries, appendShelterCostEntry}`, the SAME no-update/upsert discipline `~/anicca/skills/self/spawn/lib/ledger.js` already establishes for children (this module gains no mutation primitive either). One entry per real deploy attempt, `{ts: number, settledLeaseCostUsd: number}`, appended once the settled lease cost first becomes observable (REQ-303). |
| **Pure Core (new, extends existing pattern — corrected, resolves FIND-1101; input derivation corrected, resolves FIND-1401/FIND-1501)** | new module, same file, `decideColonySpawn({colonySurplusUsd, spawnThresholdUsd, recentSpawnAttempts, nowMs, cooldownDays, failureCooldownCap, childrenProvisioning, maxConcurrentSpawns}) → {eligible, reason}` | PURE (new) | Directly analogous in shape/discipline to the existing `~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn` (same `{eligible, reason}` return, same "no I/O" contract, same ordered-checks style, and now the SAME array-scan discipline over `recentSpawnAttempts` that `decideSpawn` already proves out over `children[].spawned_ms`) but colony-aggregate-scoped rather than single-parent-scoped. **Corrected, resolves FIND-1101 (critical): this row previously pinned a single scalar `lastSpawnAttemptMs`, which cannot express "how many of the recent attempts were failures" — REQ-305's own failure-cap rule needs exactly that count. The signature now carries `recentSpawnAttempts: Array<{ts: number, outcome: "success"|"failure"}>`, reconciling REQ-102/REQ-305's cooldown-consumption contradiction into ONE rule: a success in-window is always a hard cooldown gate; a failure is cooldown-exempt only below `failureCooldownCap` (default `3`), beyond which it triggers cooldown identically to a success.** **Corrected, resolves FIND-1401 (critical): `recentSpawnAttempts` is NEVER hand-assembled by the calling orchestration — it is always the direct return value of the new `deriveRecentSpawnAttempts` (row above), called over `readChildren`'s real output.** **Corrected, resolves FIND-1501 (critical): `childrenProvisioning` is likewise NEVER hand-assembled by the calling orchestration — it is always the direct return value of the new `countChildrenProvisioning` (row above), called over `readChildren`'s real output — never a naive per-row `"provisioning"` count that would double-count or permanently over-count a since-resolved child.** **Corrected, resolves FIND-1701 (critical): `colonySurplusUsd` — this row's own FIRST-listed parameter, and the single most consequential value the function consumes — is likewise NEVER hand-assembled by the calling orchestration; it is ALWAYS the direct return value of THAT SAME evaluation's `computeColonySurplusUsd({citizens: filterProductiveCitizens(...), perCitizenReserveUsd})` (REQ-101) call, never a stale/earlier evaluation's cached aggregate and never a shortcut inline recomputation that skips `filterProductiveCitizens`'s exclusion logic. REQ-103's `"colony-spawn"` lock does NOT provide staleness protection here and MUST NOT be cited as though it did — that lock's own critical section begins only at REQ-201's wallet generation, strictly AFTER REQ-101/102's evaluation already completes (REQ-103's own statePath prose confirms this) — so EACH separate `decideColonySpawn` evaluation within one wake MUST call this pipeline fresh, never reuse an earlier evaluation's aggregate.** `spawnThresholdUsd` is itself computed upstream of this function's own call from `MIN_SHELTER_USD * SAFETY_MARGIN_MULTIPLIER`, `MIN_SHELTER_USD` in turn reading `deriveMeasuredShelterCostUsd` (row above) once non-`null` (resolves the sweep-found sibling gap alongside FIND-1501). `nowMs` is a raw wall-clock runtime primitive — the evaluation's own current time at the moment of the call — needing no further derivation, the identical treatment `selectCloudTarget`'s own four raw I/O-leaf inputs already receive (row below); `maxConcurrentSpawns` defaults to `1`, stated at both the EARS-clause and Acceptance-Criteria level (resolves the sweep-found asymmetry alongside FIND-1701). REQ-102/103/104's acceptance criteria are enforced here. |
| **Pure Core (existing, extended — small, backward-compatible modification, REQ-206)** | `~/anicca/skills/self/spawn/lib/child-spec.js::nextChildId`/`buildChildSpec` | PURE (existing, extended) | `nextChildId` fully unchanged. `buildChildSpec`'s identity-anchor validation is extended (REQ-206) to accept EITHER `childInbox` (old AgentMail path, backward-compatible, unchanged behavior) OR the new `agentEvmAddress`+`agentId` pair (ERC-8004, this feature's actual path) — never both required. This CORRECTS iteration 1's false "reused unmodified" claim (FIND-001: today's code unconditionally throws on missing `childInbox`, and this feature never produces an AgentMail inbox). The distinct-wallet assertion (`childWallet === parentWallet` throw) and every other existing field/behavior are untouched; REQ-201 generalizes the CALLER's pre-check to "distinct from ALL citizens," not this constructor. The function's OTHER four already-mandatory fields (`parentWallet`, `generation`, `seedUsdc`, `constitutionHash`) receive NO code change at all — REQ-206 now specifies an explicit spec-level derivation rule for each (coordinator-host wallet / fixed `1` / aliased to REQ-204's gas seed / fixed hash of `identity/genesis.md`, respectively), resolving FIND-204 without touching this file a second time. **Disambiguation (resolves FIND-304):** this function's own, pre-existing, unmodified returned row carries a field literally named `wallet` (`child-spec.js:37`: `wallet: childWallet`, a bare address STRING, confirmed by `child-spec.test.js:36`) — a COMPLETELY SEPARATE field, in a COMPLETELY SEPARATE file/schema, from `citizens.json`'s `wallet` field (a boolean presence-flag object, REQ-105's durable-runtime-file row above); the two share a name only by coincidence and this spec does not rename either. |
| **Pure Core (existing, reused unmodified)** | `~/anicca/skills/economy/gig/lib/lock.mjs::isLockStale(nowMs, mtimeMs, staleMs)` | PURE (existing, adversary-hardened) | Already extracted and Tier-1-tested as part of `anicca-agent-economy`'s own REQ-101 (concurrency-hardening sprint). REQ-103 reuses this predicate — and the `acquire()`/`release()`/atomic-`fs.rename`-reclaim machinery built on it — under a NEW lock key (`"colony-spawn"`), not new lock logic. `withGigLock(statePath, lockKey, fn, opts)`'s lock-file identity depends on BOTH `statePath` AND `lockKey`; REQ-103 (revised to resolve FIND-103/FIND-901) therefore designates REQ-105's citizen registry's DURABLE runtime location — never the git-tracked seed template — as the ONE canonical `statePath`, exported as `CITIZENS_REGISTRY_PATH` from a new `~/anicca/skills/self/spawn/lib/registry-path.mjs` module that every call site must import. Its local-POSIX-filesystem guarantee is sufficient ONLY because REQ-106 scopes every REQ-102/103 evaluator to a SINGLE coordinator host this increment (resolves FIND-003) — this module is never claimed to solve cross-host mutual exclusion. |
| **Effectful Shell (new — corrected, resolves FIND-1002, major)** | new module `~/anicca/skills/self/spawn/lib/registry-path.mjs::CITIZENS_REGISTRY_PATH`, `::COORDINATOR_HOME` | EFFECTFUL (new, two constants) | **Corrected, resolves FIND-1002 (major): this row was previously mislabeled "Pure Core" — corrected here.** `CITIZENS_REGISTRY_PATH` is built from `resolveStateDir` (the row above this one — already, and correctly, classified "Effectful Shell" in this SAME table), and `COORDINATOR_HOME` is built from Node's `os.homedir()`, a real OS/environment read, not a deterministic computation over its own inputs — a module built entirely from two Effectful primitives cannot itself be Pure Core. Labeling it "Pure Core" would have invited Phase 3 to treat both constants as testable with a zero-I/O, no-environment-control Tier-1 unit test; both instead require the same real-filesystem/real-environment Tier-2 rigor `resolveStateDir` and `os.homedir()` themselves need, consistent with how PROP-403e/PROP-403f already correctly treat this SAME module's other properties. See PROP-105m (new) for the Tier-2 proof that `COORDINATOR_HOME` genuinely tracks a real, controllable `os.homedir()`/environment value rather than being assumed pure. Resolves FIND-103: `CITIZENS_REGISTRY_PATH` is the single, canonical absolute path to the DURABLE `citizens.json`, computed as `path.join(resolveStateDir({env, home}), 'citizens.json')` (resolves FIND-901 — see the dedicated `resolveStateDir` row above; NEVER a literal path inside the `~/anicca` git working tree), exported as ONE named constant so both REQ-103's lock `statePath` and REQ-101/105/305's own registry reads/writes converge on the identical value — never independently hardcoded per call site. **New, resolves FIND-701 (critical): this SAME module ALSO exports `COORDINATOR_HOME`, the coordinator host's own real `$HOME`, computed EXACTLY ONCE at module-load time via Node's `os.homedir()` (never `process.env.HOME` read ad hoc, never a hardcoded literal) — REQ-403's live-audit script imports and uses this SAME constant for every `env.HOME` value it passes to `resolveEvmPrivateKey`/`resolveSolanaSecret`, closing the identical un-pinned-input hazard class `CITIZENS_REGISTRY_PATH` already closed for the lock `statePath` (PROP-403f).** |
| **Pure Core (new)** | new module, e.g. `~/anicca/skills/self/spawn/lib/cloud-target.mjs::selectCloudTarget({nosanaAvailable, nosanaPriceUsd, akashAvailable, akashPriceUsd}) → "nosana"\|"akash"\|"none"` | PURE (new) | Deterministic, price/availability-based comparison — bookkeeping, never a model judgment. Resolves FIND-006 (REQ-302/303 presupposed a selection step that was never itself specified). REQ-306's acceptance criteria are enforced here. |
| **Pure Core (new — row added, resolves FIND-1601)** | new module, same file as `gen-solana-wallet.sh`'s caller, e.g. `~/anicca/skills/self/spawn/lib/child-spec.js`-adjacent `needsSolanaWallet({initialSkills, deployTarget}) → boolean` | PURE (new) | Deterministic conditional (a Solana-settled skill present in `initialSkills` OR `deployTarget === "nosana"`) — bookkeeping over already-given inputs, never a model judgment (REQ-202). **Corrected, resolves FIND-1601 (critical): this row was previously MISSING from this table entirely, despite the function already having three proof obligations (PROP-202a/b/c) — added here.** `deployTarget` is never hand-assembled — it is ALWAYS THAT SAME spawn attempt's `selectCloudTarget(...)` (row above) direct return value, mirroring `decideColonySpawn`'s own `recentSpawnAttempts`/`childrenProvisioning` binding discipline; `initialSkills` is never hardcoded/defaulted — it is ALWAYS the SAME value the spawning agent already chose per REQ-104's agent-judgment carve-out (extended to cover this choice). New proof obligations PROP-202d (deployTarget real-derivation) and PROP-202e (initialSkills structural non-hardcoding check) are added. REQ-202's acceptance criteria are enforced here. |
| **Effectful Shell (revised, resolves FIND-302)** | new module, e.g. `~/anicca/skills/self/spawn/lib/colony-balances.mjs::readCitizenBalances({citizens})` | EFFECTFUL | Queries EACH citizen's balance directly from PUBLIC CHAIN RPC, keyed on that citizen's own `walletAddress` (REQ-105's registry field) — a registry-driven GENERALIZATION of `~/anicca/skills/self/telemetry-collect.sh`'s own existing, already-proven hardcoded-3-instance pattern (that script's `erc20()`/`sol()`/`solusdc()` helpers query `base-rpc.publicnode.com`/`api.mainnet-beta.solana.com` by a hardcoded wallet-address constant per instance) into a loop over `citizens[].walletAddress`. Because a public RPC read does not depend on the querying process's own filesystem, this mechanism reaches a REQ-301-mandated cloud-hosted child's balance exactly as readily as a co-located citizen's — unlike the coordinator-local `fs.readFile`-of-`telemetryPath` mechanism this REPLACES (that field is removed from REQ-105's schema, see the `citizens.json` row above). Native-token balances are normalized to USD via the SAME already-proven spot-price pattern reused for REQ-306 (resolves FIND-305 — see below): a single public spot-price API call, fail-closed to `0` on error, mirroring `runtime/dashboard/telemetry-post-franklin.mjs::solPrice()`. When a citizen record carries BOTH `walletAddress.evm` AND `walletAddress.solana` populated (the expected Nosana-path shape, REQ-202), this function queries and normalizes BOTH chains independently and returns their SUM as that citizen's one balance figure — a deliberate design decision, resolves FIND-404 (never "pick one chain," never treated as a malformed record). Feeds REQ-101's pure aggregator; itself performs no aggregation logic. |
| **Effectful Shell** | `~/anicca/skills/self/spawn/scripts/gen-wallet.sh` | EFFECTFUL (existing, reused unmodified) | `openssl`+`python3` subprocess, real entropy. REQ-201. |
| **Effectful Shell (new)** | new script, e.g. `~/anicca/skills/self/spawn/scripts/gen-solana-wallet.sh` | EFFECTFUL (new) | Ed25519/Solana-shaped analog of `gen-wallet.sh`; real entropy, same 600-perm/never-logged discipline. REQ-202. |
| **Effectful Shell** | env injection at process-launch boundary (cloud-init/SDL/job-definition for whichever of REQ-302/303 is used) | EFFECTFUL | Setting `HOME`/`ANICCA_HOME` at spawn time; the isolation PROPERTY it produces is what REQ-203 specifies. |
| **Effectful Shell (existing, reused unmodified)** | `~/anicca/skills/earn/lib/resolve-identity.mjs::resolveEvmPrivateKey`/`resolveSolanaSecret` | EFFECTFUL (existing, already fail-closed) | Already implements the exact HOME-gated, fail-closed-on-foreign-spawn resolution REQ-203/403 depend on; reused unmodified. This is a PURE LOCAL-FILESYSTEM primitive (`fs.readFileSync`, no network path — confirmed by direct read) — REQ-403's live-comparison half therefore invokes it ONLY once per instance whose registry record has `coLocatedWithCoordinator === true` (resolves FIND-703 — never an undefined/implicit "co-located" notion), using that instance's `homeDir` value read directly from REQ-105's registry (resolves FIND-202), scoped to that filtered set only for this increment (resolves FIND-303: a cloud-hosted child's key material lives on a physically separate filesystem this coordinator-local primitive cannot reach, and is never transmitted over the network for comparison; every spawned child's `coLocatedWithCoordinator` is structurally `false` by REQ-305, so it is never a member of this set). **Corrected, resolves FIND-501:** with REQ-105's now-corrected, DISTINCT `homeDir` seed values, a real invocation against each citizen's own `homeDir` resolves REAL, non-null key material via this module's own existing legacy-fallback branch (`/Users/anicca/.automaton/wallet.json` for automaton, `/Users/anicca/.blockrun/.solana-session` for Franklin — both confirmed present on disk, 2026-07-07, content never read/printed) — the prior bare-`$HOME` seed value would have resolved `null` for both citizens on every chain, per this module's own fail-closed gate, never proving genuine pairwise key inequality at all. |
| **Effectful Shell (existing, reused unmodified)** | `~/anicca/skills/economy/gig/lib/identity.mjs::registerIdentity`/`verifyIdentity`, invoked THROUGH `~/anicca/skills/economy/gig/lib/ensure-agent-id.mjs::ensureAgentId` | EFFECTFUL (existing, live-verified 2026-07-07) | REQ-204 calls `ensureAgentId` (the existing cache-then-verify-then-register-once wrapper, already ANICCA_HOME-gated and already unit-tested), NOT `registerIdentity` directly — resolves FIND-004 (REQ-204's "already-registered" defensive check reuses this existing primitive rather than re-deriving the same logic). Real on-chain ERC-8004 `register()`/`ownerOf` calls against the already-live mainnet (`0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`, Base 8453) or testnet (`0xdc527768082c489e0ee228d24d3cfa290214f387`, Base-Sepolia 84532) registry. |
| **Effectful Shell (new, template reused)** | new file-write step producing `<child_home>/.blockrun/mcp.json` (or `.anicca/mcp.json`) | EFFECTFUL (new) | Copies the exact shape of the already-live `~/.blockrun/mcp.json`. REQ-205. |
| **Effectful Shell (new)** | new wrapper around the `nosana` CLI (`nosana job post ...`) and its own market price-query for REQ-306's selection input | EFFECTFUL (new) | Real subprocess + real Solana-settled market transaction. REQ-302/306. Confirmed-current CLI per the re-verification table in behavioral-spec.md. |
| **Effectful Shell (existing, reused unmodified)** | `~/anicca/skills/self/spawn/scripts/deploy-akash.sh`, `~/anicca/skills/self/spawn/scripts/akt-treasury.sh`, and a `provider-services`-equivalent bid-price query for REQ-306's selection input | EFFECTFUL (existing, already implemented against real sandbox-2 chain per those scripts' own inline evidence citations) | REQ-303 reuses both unmodified, substituting only `CHILD_ID`/SDL content. REQ-306's Akash-side price query (native `uact`/`uakt` amounts) is new. |
| **Pure Core (existing, reused unmodified) + effectful config read (revised iteration 5, resolves FIND-402)** | `~/anicca/skills/self/spawn-child/lib/akt-cost-gate.js::computeSpawnGate({balanceAkt, costAkt, bufferAkt}) → {ready, reason, thresholdAkt, shortfallAkt}` + `~/anicca/skills/self/spawn-child/config.json` | PURE (the gate function) + EFFECTFUL (reading `config.json`'s `spawn_cost_akt`/`buffer_akt`) | A previously-undiscovered sibling skill, now cited (Scope section). Already implemented, already unit-tested (`lib/__tests__/akt-cost-gate.test.js`); REQ-303 calls it, with `costAkt`/`bufferAkt` read from `config.json`'s own real values (`spawn_cost_akt: 25`, `buffer_akt: 1`), as the Akash-specific funding-READINESS check — a DIFFERENT, narrower concern than REQ-102's colony-wide `MIN_SHELTER_USD`/`SPAWN_THRESHOLD_USD` (cross-cloud aggregate surplus), never a competing reimplementation of it. `spawn-child`'s own `sdl/child.yaml`/`run.sh`/`SKILL.md` remain that skill's own files, unmodified — REQ-303 reuses only this ONE function + these TWO config values, never rewrites or duplicates `spawn-child` itself. |
| **Effectful Shell (new, small — resolves FIND-403)** | new child-specific SDL variant (structurally identical to `spawn-child/sdl/child.yaml` plus one new `env:` line, `HOME=/root`) | EFFECTFUL (new) | Direct reads confirm neither `deploy-akash.sh`'s inline default SDL nor `spawn-child/sdl/child.yaml` sets `HOME`/`ANICCA_HOME`, relying instead on `node:22-bookworm`'s own implicit default (`/root`) — exactly what PROP-203c prohibits relying on implicitly. This is a genuinely NEW, small SDL modification (the same honesty pattern FIND-305 already established for the price-oracle fix) — PROP-303a's "zero source modification" claim is corrected to apply only to `deploy-akash.sh`/`akt-treasury.sh`'s own script files, never to this new SDL variant. |
| **Effectful Shell (new — resolves FIND-401)** | new post-lease/post-job secrets-injection step: Akash via `provider-services lease-shell <service> "cat > /opt/anicca.env" --stdin`; Nosana via `nosana job ssh <job> [port]` | EFFECTFUL (new) | Neither existing artifact (`deploy-akash.sh`'s SDL, a Nosana job command) provides ANY channel to deliver the child's own pre-generated wallet material (REQ-201/202) onto the booted lease/job — both CLIs' own `--help` output, invoked live 2026-07-07 and captured verbatim to disk at `reviews/spec/iteration-6/evidence/cli-help-2026-07-07.txt` (resolves FIND-504), confirm the real primitive exists (`lease-shell --stdin`; `job ssh`), but neither is currently wired into any existing script (`deploy-akash.sh` never calls `lease-shell`; no Nosana orchestration exists yet in this codebase at all) — this is genuinely NEW orchestration code this feature adds, tested as new, never claimed as pre-proven reuse. `deploy-akash.sh`/`akt-treasury.sh` themselves remain byte-identical (PROP-303a, scope corrected). Honesty note: `~/anicca/skills/self/spawn/scripts/cloud-init.sh`'s own header comment documents an analogous DO-specific "SCP after boot" security pattern as PRECEDENT for this design, but a direct read of `run.sh` (the DO-path caller) confirms NO actual `scp` invocation exists in that (separate, out-of-scope) path either — that gap belongs to a different, non-REQ-302/303 cloud target this feature does not touch. |
| **Effectful Shell (new, resolves FIND-305)** | new minimal price-fetch step: one public spot-price API call for AKT-USD, and (only if Nosana's configured market is NOS-denominated) one analogous new call for NOS-USD, feeding REQ-306's `selectCloudTarget` | EFFECTFUL (new) | Corrects the prior FALSE claim that this normalization reuses "already-available" infrastructure: `akt-treasury.sh` (read in full) has no live USD price query — only native-unit balance comparisons — and no NOS/SOL/USD or AKT/USD utility exists anywhere in this codebase (repo-wide grep confirmed). This step is genuinely NEW, but follows the exact, already-proven, already-used PATTERN this codebase already applies 3× for ETH-USD/SOL-USD (`telemetry-poster.mjs::ethPrice()`, `telemetry-post-franklin.mjs::solPrice()`, `execute-invest.mjs`'s own `ethPrice()`: one `fetch()` to a public spot-price API, fail-closed to `0` on error) — if Nosana's market is SOL-denominated, the EXISTING `solPrice()` is reused as-is, unmodified. |
| **Effectful Shell (new)** | new funding-transfer step: single-signer, single-transaction (citizen-wallet → child-wallet or facilitator) for SAME-CHAIN transfers; a multi-hop Skip-API `smart_relay` bridge into `akashnet-2`, reusing `spawn-child/config.json`'s own documented `funding_route`, for Akash's `uact` requirement specifically — enterable from EITHER current citizen's own native chain (Franklin via Solana/Jupiter, automaton via Base/CCTP, per PROP-304e's live-confirmed Base-native entry) (revised iteration 5, resolves FIND-402; revised iteration 7, resolves FIND-602 — corrected from a stale Solana/Jupiter-only summary that was never updated for iteration 6's PROP-304e correction) | EFFECTFUL (new) | Real on-chain transfer(s), gated on REQ-102's already-certified amount and REQ-304's single-signer-only constraint (per hop). REQ-304's "single-signer, single-transaction" characterization applies only where the funding citizen's own native chain already matches the target's native currency (e.g. Franklin's SOL/USDC directly funding a Nosana deploy) — NOT to Akash's `uact` requirement, which genuinely needs the multi-hop bridge, though EITHER citizen's wallet can independently enter that SAME bridge (Franklin via Solana+Jupiter, automaton via Base+CCTP skipping Jupiter entirely) depending on whose surplus is actually being spent, per PROP-304e — never hardcode a Solana-only entry. |
| **Effectful Shell (existing, reused unmodified) + new registry-append side effect** | `~/anicca/skills/self/spawn/lib/ledger.js::appendChild`/`readChildren` | EFFECTFUL (existing) | Append-only JSONL; already implemented, unmodified — NO update/upsert primitive is added (resolves FIND-301's own constraint: `filterProductiveCitizens`, not this module, absorbs the duplicate-`child_id` last-write-wins reduction). This feature's own rows are the SOLE canonical owner of each child's `status`, a new `active_since` field REQ-305 sets the moment a child is first marked `"active"`, and a new `attempted_ms` field (resolves FIND-1401) REQ-305 sets to `nowMs` on the FIRST row ever appended for a `child_id` and copies forward, unchanged, onto every later row for that SAME `child_id` (a `"failed"` row, an `"active"` row, or REQ-402's `"bootstrap_failed"` row — never a freshly-generated timestamp on a follow-up row) — REQ-402's window check and REQ-101's `filterProductiveCitizens` join both read `active_since`/`status` from THESE rows, and REQ-102's new `deriveRecentSpawnAttempts` (above) reads `attempted_ms` from them, never from `citizens.json` (resolves FIND-201/FIND-1401). REQ-402's `"bootstrap_failed"` relabeling is likewise implemented as `appendChild`-ing a NEW row for the same `child_id` (never a mutation) — this new row becomes "the" effective row exactly because `filterProductiveCitizens`'s own last-write-wins reduction (above) picks it up on the next read, and it copies forward the SAME `attempted_ms` value from that child's first row — REQ-402 introduces no second, competing reduction rule (revised iteration 5, resolves FIND-405, the identical clarification pattern FIND-301 already established for REQ-101/REQ-305's own writes). Each row's own `wallet` field (a STRING, from `buildChildSpec`, see the `child-spec.js` row above) is UNRELATED to `citizens.json`'s boolean `wallet` field appended below (resolves FIND-304). REQ-305. `child-spec.js`/`buildChildSpec` itself is NOT modified for `attempted_ms` — it is an extra field the effectful caller merges into `buildChildSpec`'s base returned object before calling `appendChild`, the EXACT precedent already established for `active_since`. On success (child marked `"active"`), REQ-305 ALSO appends a new record to REQ-105's colony citizen registry — the DURABLE runtime file at `CITIZENS_REGISTRY_PATH` (resolved via `resolveStateDir`; NEVER the git-tracked seed template `citizens.seed.json`, and NEVER `colony-wallets.json`, resolves FIND-901) — a new, explicit write path (resolves FIND-002's "how does the registry grow" gap), GATED on an `isSelfFunded()` pre-append check that REFUSES the append if it would fail (resolves FIND-101). The appended record splits `wallet` (booleans) from `walletAddress` (strings), resolving FIND-104, and carries an already-resolved `homeDir` value (resolving FIND-202) — NO `telemetryPath` field (removed, resolves FIND-302). |
| **Effectful Shell (new)** | new independent RPC balance-read step (before/after comparison) for REQ-401 | EFFECTFUL (new) | Mirrors the exact `eth_call balanceOf` method SPEC.md §9.9 already used to confirm Franklin#1's final balance independently of the parties' own self-report. |
| **Effectful Shell + static analysis (new)** | new audit script combining (a) `grep -r` over skill scripts/cron config for all 3 path forms (covers the WHOLE fleet, including a cloud-hosted child, since it boots from the same git-cloned repo — resolves FIND-303) and (b) live invocation of `resolve-identity.mjs`'s exported resolvers per instance enumerated via `citizens.filter(c => c.coLocatedWithCoordinator === true)` (resolves FIND-703), reading REQ-105's registry and its `homeDir` field (resolves FIND-202) and passing `env: {HOME: COORDINATOR_HOME, ANICCA_HOME: citizen.homeDir}` (resolves FIND-603/FIND-701 — `COORDINATOR_HOME` imported from `registry-path.mjs`, never independently read/hardcoded) | EFFECTFUL + STATIC (new) | REQ-403. The grep half (a) is Tier 0 (no runtime execution of the AUDITED code, though the audit script itself runs) and covers every instance this increment produces. The live-comparison half (b) is Tier 2 and, for THIS increment, is SCOPED to exactly the `coLocatedWithCoordinator===true` set (resolves FIND-303/FIND-703) — a cloud-hosted child is structurally excluded from (b)'s candidate set (its own registry record's `coLocatedWithCoordinator` is `false`, by REQ-305) until a future increment adds a remote-audit mechanism; it remains covered by (a). |
| **Not code — design constraint** | REQ-104 (bookkeeping-only design constraint on REQ-101/102/103) | N/A | Directly analogous to `anicca-agent-economy`'s REQ-203; verified by Phase 3 structural code read (grep for LLM calls/prompt strings/scoring fields in the gate's own source), never a runtime assertion. |
| **Not code — design constraint** | REQ-106 (single-coordinator-host scope constraint on REQ-101/102/103, this increment only) | N/A | Resolves FIND-003. Verified by a Phase 3 structural code read confirming `lock.mjs`/`ledger.js` are invoked from exactly one designated coordinator-host entry point, and that this spec's own scope section states spawn chaining is out of scope — never by proving multi-host correctness (explicitly not required this increment). |
| **Not code — design constraint** | REQ-301 (local-spawn-forbidden structural constraint) | N/A | Verified by reading the deploy code path's artifact list post-attempt, not by running a probe against a hypothetical violation. |
| **Not code — reused-but-superseded prior art** | `~/anicca/skills/self/spawn/{SKILL.md,scripts/cloud-init.sh,scripts/seed-child.py,scripts/sign-telemetry.py,scripts/usdc-balance.py}` (2026-06-16 DigitalOcean + AgentMail single-lineage design) | N/A | Architecturally superseded by SPEC.md §1.3's Franklin/ERC-8004 pivot (predates it). NOT reused by any REQ in this spec (DO droplets + AgentMail inboxes + `automaton.service` systemd units belong to a different, non-cloud-crypto-native provisioning model). Listed here only so Phase 2/3 do not mistake this directory's OLD `run.sh`/`SKILL.md` narrative for this feature's actual target behavior — the REUSED primitives are exactly (and only) `gen-wallet.sh`, `deploy-akash.sh`, `akt-treasury.sh`, `lib/spawn-decision.js`, `lib/child-spec.js`, `lib/ledger.js`, all individually cited above. |

## Verification tiers (this feature's convention, consistent with `anicca-agent-economy`'s
`specs/verification-architecture.md`)

- **Tier 0**: structural/existence checks — no runtime execution of the AUDITED code required (a
  ledger row's `status` field is always one of the three allowed values; a design-constraint
  requirement's source contains no LLM call/prompt string; the static grep sweep for cross-instance
  path references (now confirmed to cover a cloud-hosted child's deployed source too, since it boots
  from the same git-cloned repo — resolves FIND-303); REQ-106's single-coordinator-host entry-point
  check; REQ-103's structural import-identity check that every colony-spawn lock call site uses the
  SAME exported `CITIZENS_REGISTRY_PATH` constant, resolving FIND-103; REQ-105's structural check that
  its literal seed array contains only the two verified self-funded entries; REQ-105's structural
  check that `homeDir` is never an unresolved `$HOME` template, resolving FIND-202 (`telemetryPath` is
  removed from this schema entirely, resolving FIND-302 — there is nothing left to check for it);
  REQ-105's walletAddress-verification-method check, STRUCTURAL HALF ONLY (PROP-105g, resolves
  FIND-601/FIND-702 — confirms a real re-derivation script/test exists in the diff COVERING BOTH the EVM
  and Solana branches (corrected, resolves FIND-801 — `viem::privateKeyToAccount` alone is insufficient,
  Franklin's Solana-only record and every future Nosana-path child need the `@solana/web3.js`
  equivalent) and is wired to run at Phase 3; the actual re-derivation EXECUTION itself is Tier 2, see
  below — never merely a citation check); REQ-105's dual-branch-conjunctive structural check (PROP-105i,
  structural half, resolves FIND-801 — confirms the re-derivation script never short-circuits after only
  one chain when a citizen record has both populated); REQ-105's `coLocatedWithCoordinator`-schema
  structural check (PROP-105h, resolves FIND-703 —
  the seed array's `coLocatedWithCoordinator` values are both `true`, and the field is boolean-typed on
  every entry); REQ-305's structural check that every append sets `coLocatedWithCoordinator` to EXACTLY
  `false` (PROP-305f, structural half, resolves FIND-703); REQ-403's explicit-env-invocation structural
  check (PROP-403e, structural half, resolves FIND-603) AND its `COORDINATOR_HOME`-import-identity
  structural check, mirroring PROP-103d exactly (PROP-403f, resolves FIND-701 — confirms every call site
  supplying `env.HOME` imports the SAME `COORDINATOR_HOME` constant from `registry-path.mjs`, with zero
  independent `os.homedir()`/`process.env.HOME` reads anywhere else in the audit-script code path) AND
  its enumeration-keyed-on-`coLocatedWithCoordinator` structural check (PROP-403d, resolves FIND-703 —
  the live-comparison candidate set is now a real, checkable filter, `citizens.filter(c =>
  c.coLocatedWithCoordinator === true)`, never an implicit/undefined notion);
  `ledger.js`'s structural check that it remains exactly `{readChildren, appendChild}` — no
  update/upsert primitive added, resolving FIND-301's own constraint; a structural read confirming
  `child-spec.js`'s returned-row `wallet` (string) and `citizens.json`'s `wallet` (boolean object) are
  never cross-assigned anywhere in the diff, resolving FIND-304; REQ-402's structural check that
  `children_bootstrap_failed` has zero effect on REQ-102's pinned signature, resolving FIND-203;
  REQ-305's structural check (PROP-305h, resolves FIND-1401) that `attempted_ms` is set on the FIRST
  `ledger.js` row appended for a given `child_id` and copied forward unchanged onto every later row for
  that SAME `child_id`, including REQ-402's `"bootstrap_failed"` row, never a freshly-generated
  timestamp on a follow-up row;
  REQ-201/301's structural check that generated private-key material never appears in any boot-time
  artifact, resolving FIND-401 (PROP-201d); REQ-303's structural checks that `deploy-akash.sh`/
  `akt-treasury.sh` remain byte-identical while the new child-specific SDL variant and secrets-injection
  step are correctly scoped OUT of that "unmodified" claim (PROP-303a, resolving FIND-401/403), that the
  ACTUAL rendered SDL contains an explicit `HOME=/root` line (PROP-303f, resolving FIND-403), and that
  the Akash-readiness check imports `spawn-child/lib/akt-cost-gate.js::computeSpawnGate` rather than a
  competing threshold (PROP-303d, structural half, resolving FIND-402)).
- **Tier 1**: pure-function unit tests — deterministic fixtures, no filesystem/network/real
  wall-clock sleep, fast (milliseconds). REQ-101's aggregation AND its new `filterProductiveCitizens`
  join, INCLUDING its last-write-wins reduction of multiple rows sharing one `child_id` (resolves
  FIND-201/FIND-301) AND its dual-chain (evm+solana) balance-summing rule (PROP-101f, resolves
  FIND-404) AND its new per-citizen surplus exposure/consistency check (PROP-101i, resolves
  FIND-1202), REQ-102's gate AND its new `deriveRecentSpawnAttempts` join, grouping `ledger.js`'s rows
  by `child_id` and covering all four cases — a plain failure, a plain success, a success-then-
  `"bootstrap_failed"` attempt that must remain `outcome:"success"` with its ORIGINAL `attempted_ms`
  and must never also appear as a second, extra failure entry, and an in-flight `"provisioning"`-only
  attempt that must be excluded entirely (PROP-102f, resolves FIND-1401), REQ-103's reused `isLockStale` predicate (already
  Tier-1-proved upstream; this feature's own Tier-1 obligation is only proving the NEW
  `"colony-spawn"` lock KEY is wired to it correctly, not re-proving the predicate itself), REQ-105's
  registry-record-shape/malformed-record fixtures AND its direct seed-data-passes-`isSelfFunded()`
  assertion (resolves FIND-101's "compare against today's known-good identities" critique — this is
  now a straightforward literal-fixture assertion, not an out-of-band-knowledge-dependent comparison)
  AND its `homeDir`-is-never-passed-to-`isSelfFunded()` check (resolves FIND-202), REQ-201/202's
  conditional-generation logic, REQ-206's identity-anchor validation (both accepted paths, both
  rejection paths, AND the "both anchors present is accepted, not an XOR" path — PROP-206e, resolves
  FIND-102) AND its `parentWallet`/`generation`/`seedUsdc`/`constitutionHash` derivation-rule fixtures
  (PROP-206f/g, resolves FIND-204), REQ-305's isSelfFunded-refusal-before-append check (unit half,
  resolves FIND-101), REQ-306's `selectCloudTarget` comparison (price/availability/tie-breaker
  branches) AND its new AKT-USD/NOS-USD price-fetch step's fail-closed behavior (resolves FIND-305),
  REQ-402's window-boundary relabeling logic (now read from `ledger.js` rows, resolving FIND-201).
- **Tier 2**: integration tests — real module wiring (real `fs`, small injected timing constants,
  concurrent `Promise.all`/multi-process calls against the real lock/identity/resolve-identity
  modules) plus fresh-context adversary review of the disk artifacts (no live chain/cloud spend
  required for this tier). REQ-102's real orchestration calling `deriveRecentSpawnAttempts({ledgerRows:
  readChildren(...)})` directly over a real `ledger.js` file, rather than reimplementing the join
  inline at the call site (PROP-102g, resolves FIND-1401 — mirroring PROP-101d/PROP-101e's own
  real-derivation discipline for `filterProductiveCitizens`/`readCitizenBalances`), REQ-102's real
  orchestration calling `countChildrenProvisioning({ledgerRows: readChildren(...)})` directly over that
  SAME real `ledger.js` file, rather than reimplementing the count inline (PROP-102i, resolves
  FIND-1501, mirroring PROP-102g's own discipline), REQ-101's real orchestration calling
  `filterProductiveCitizens({citizens: <real registry read>, ledgerRows: readChildren(...), ...})`
  directly, rather than hand-assembling either argument at the call site, with `computeColonySurplusUsd`/
  `readCitizenBalances` confirmed to receive that SAME filtered array unchanged (PROP-101j, new, resolves
  the sweep-found sibling gap alongside FIND-1601 — this is the genuine real-derivation discipline
  PROP-102g's own citation had claimed, but did not actually establish, for this function), REQ-202's real
  orchestration calling `needsSolanaWallet({initialSkills, deployTarget: selectCloudTarget(...)})` with
  `deployTarget` bound directly to THAT SAME attempt's real `selectCloudTarget(...)` return value, never a
  stale/earlier attempt's evaluation (PROP-202d, new, resolves FIND-1601, critical), REQ-102's real
  orchestration calling `computeColonySurplusUsd({citizens: filterProductiveCitizens(...),
  perCitizenReserveUsd})` directly and passing its return value as `colonySurplusUsd`, with a SEPARATE
  such call made for EACH separate `decideColonySpawn` evaluation within one wake, never a cached/stale
  aggregate reused across evaluations (PROP-102k, new, resolves FIND-1701, critical), REQ-101's
  `readCitizenBalances` registry-driven public-RPC query, proven
  against both a co-located citizen's and a simulated remote citizen's `walletAddress` alike (resolves
  FIND-302), REQ-103's concurrent-attempt race (PROP-103a) AND its staggered-timing/lock-held-through-
  REQ-304-REQ-305 race (PROP-103e, resolves FIND-1201, critical), REQ-105's
  walletAddress-verification-method check,
  ACTUAL RE-DERIVATION HALF, TWO-BRANCH (PROP-105g, resolves FIND-702/FIND-801 — EVM: a real script/test
  reads the real private-key file in memory, computes the address via `privateKeyToAccount`, and diffs
  it against `citizens.json`'s stored `walletAddress.evm`; Solana: a real script/test reads the real
  secret file in memory, `bs58.decode()`s it, computes the address via
  `Keypair.fromSecretKey(...).publicKey.toBase58()`, and diffs it against `walletAddress.solana` —
  both failing hard on any mismatch, this is the runtime re-performance the Tier-0 structural half above
  only confirms is wired up) AND its dual-populated-citizen conjunctive-pass check (PROP-105i, resolves
  FIND-801), REQ-203's cross-instance
  `resolve-identity.mjs` non-leak test, REQ-204's `ensureAgentId` already-registered defensive test,
  REQ-206's real full-seven-field `buildChildSpec` call (PROP-206f, resolves FIND-204), REQ-305's
  failure-injection-at-each-step test, registry-append-on-success test (now also asserting
  `active_since` is set, `homeDir` is pre-resolved, and `coLocatedWithCoordinator` is exactly `false`
  (PROP-305f, integration half, resolves FIND-703) — no `telemetryPath` field exists to assert on,
  resolving FIND-201/202/302), and isSelfFunded-refusal-before-append check (integration half, resolves
  FIND-101), REQ-403's static-grep-plus-fixture-collision test AND its live pairwise-key-inequality
  check across N ≥ 2 real running instances whose registry record has `coLocatedWithCoordinator === true`
  (scoped, resolves FIND-303/FIND-703 — this increment's live check does not extend to a spawned child,
  whose own record is always `coLocatedWithCoordinator: false`).
- **Tier 3**: live, no-mock E2E — real transactions/leases against the live (or, for a first-pass
  dry run, testnet/sandbox) chain and cloud provider, executed the same way the P2 gig-board
  adversary and SPEC.md §9.9's witness already did (real tx hashes, real cloud lease/job IDs,
  independent re-verification), per this project's HARD RULE 0.24 (on-chain-verified only, no
  paper/simulated claims). REQ-204's real `register()` call, REQ-302's real Nosana job, REQ-303's
  real Akash lease, REQ-304's real funding transfer, REQ-401's real, independently-re-verified gig
  settlement. REQ-403's live pairwise-key check does NOT extend to Tier 3 this increment (resolves
  FIND-303/FIND-703: it is Tier-2, scoped to exactly the `coLocatedWithCoordinator===true` set — no
  cloud-hosted child is ever a member of that set, so it is never included in it
  this increment).
  **A first Tier-3 pass on Base-Sepolia/Akash sandbox-2/Nosana devnet-equivalent (whichever each
  provider documents as its low-stakes environment) is an acceptable precursor to a mainnet Tier-3
  pass, matching this project's own established practice (e.g. the P2 gig board's testnet-first,
  mainnet-second sequencing) — but the increment's OWN completion still requires at least one real
  mainnet-class Tier-3 result for REQ-204/302or303/401, not testnet alone, mirroring SPEC.md §9.9's
  own "gig #3 was the first to actually complete on Base mainnet" correction.**

## Proof Obligations

| ID | REQ | Description | Tier | Required | Tool / Method |
|---|---|---|---|---|---|
| PROP-101a | REQ-101 | `computeColonySurplusUsd` sums `max(0, balance_i - reserve)` correctly over a mixed fixture (some above reserve, some below, some self-funded, some not) | 1 | true | unit test, fixed fixture, assert exact numeric output |
| PROP-101b | REQ-101 | A citizen failing `isSelfFunded()` contributes `0` regardless of its raw balance magnitude | 1 | true | unit test: fixture citizen with `balance=1000` but `isSelfFunded()→false` → assert total unaffected by that balance |
| PROP-101c | REQ-101 | A failed/timed-out/non-finite/negative public-RPC balance query for a citizen contributes `0` (fail-closed), never throws | 1/2 | true | unit test: mocked `readCitizenBalances` fixture returning an error/non-finite value for one citizen → function returns a finite number, never throws, never counts the bad entry as positive surplus (resolves FIND-302: replaces the prior "telemetry.json missing" framing, which assumed a coordinator-local file read) |
| PROP-101d | REQ-101 | `filterProductiveCitizens({citizens, ledgerRows, nowMs, bootstrapWindowDays})` excludes exactly the citizens whose matching ledger.js row is `"bootstrap_failed"` or window-overdue-while-`"active"`, passes through unfiltered any citizen with NO matching ledger row, correctly reduces MULTIPLE rows sharing one `child_id` to the LAST-appended row before applying that exclusion (last-write-wins, resolves FIND-301), and performs zero I/O | 1 | true | unit test, fixed fixture: a citizen with a `"bootstrap_failed"` row, a citizen with an overdue `"active"` row (no REQ-401 success, `now - active_since >= bootstrapWindowDays`), a citizen with a healthy `"active"` row, a citizen with NO matching row, AND a citizen with TWO rows for the SAME `child_id` — an earlier `"provisioning"` row followed by a later `"active"`-and-healthy row (or, in a second fixture variant, a later `"bootstrap_failed"` row) — → assert the function returns exactly `{healthy citizen(s), no-row citizen}` using each duplicate-id citizen's LAST row only (never its first), and that `computeColonySurplusUsd` is never called on the excluded ones (resolves FIND-201/FIND-301; this fixture is an extension of the SAME test, not a new PROP ID, since it exercises the identical function under a broader input shape) |
| PROP-101e | REQ-101 | `readCitizenBalances({citizens})` queries each citizen's balance via public RPC keyed on the registry's `walletAddress` field, and this mechanism succeeds identically whether that citizen is co-located with the coordinator or, per REQ-301, exclusively cloud-hosted (no dependency on any coordinator-local file belonging to the citizen) | 2 | true | integration test: invoke `readCitizenBalances` against (a) a real co-located citizen's known `walletAddress` and (b) a fixture/simulated remote citizen's `walletAddress` with no corresponding local file on the test host at all → assert both resolve a balance via RPC alone, proving no local-file dependency exists (resolves FIND-302) |
| PROP-101f | REQ-101 | A citizen record carrying BOTH `walletAddress.evm` AND `walletAddress.solana` populated has `readCitizenBalances` sum both chains' independently-normalized USD balances into one total — never pick one chain, never treat the dual-wallet shape as malformed | 1/2 | true | unit/integration test: fixture citizen with a nonzero, independently-verifiable balance on BOTH chains → assert the returned total equals the SUM of both chains' own `ethPrice()`/`solPrice()`-normalized values, never either value alone (resolves FIND-404) |
| PROP-101g | REQ-101 | A dual-wallet citizen's balance queries fail closed INDEPENDENTLY per chain — if exactly ONE chain's query fails/times out/returns non-finite while the OTHER chain's query genuinely SUCCEEDS with a real, nonzero value, the returned total equals ONLY the successful chain's own normalized value, NEVER `0` for the whole citizen (resolves FIND-503; distinct from PROP-101f's both-succeed fixture and PROP-101c's whole-citizen-failure fixture) | 1/2 | true | unit/integration test: fixture dual-wallet citizen with its EVM query engineered to fail/time out/return a non-finite value while its Solana query genuinely succeeds with a real, independently-verifiable nonzero value (and the symmetric case, Solana fails/EVM succeeds) → assert the returned total equals ONLY the successful chain's own `ethPrice()`/`solPrice()`-normalized value, never `0` |
| PROP-101h | REQ-101 | A dual-wallet citizen (`walletAddress.evm` AND `walletAddress.solana` both populated) whose BOTH chains' queries fail/time out/return non-finite SIMULTANEOUSLY contributes exactly `0` to the aggregation — never throws, never `NaN`, never double-subtracts `perCitizenReserveUsd` for that one citizen (resolves FIND-604; distinct from PROP-101f's both-succeed fixture and PROP-101g's exactly-one-fails fixture — no fixture in this table previously instantiated the both-fail-simultaneously case for a dual-wallet citizen) | 1/2 | true | unit/integration test: fixture dual-wallet citizen with BOTH its EVM and Solana queries engineered to fail/time out/return non-finite simultaneously → assert `readCitizenBalances` returns exactly `0` for that citizen (`0` (EVM) + `0` (Solana) = `0`), `computeColonySurplusUsd` never throws/returns `NaN`, and `perCitizenReserveUsd` is subtracted exactly ONCE (not once per populated chain) from that citizen's (zero) `balance_i`, per REQ-101's own `max(0, balance_i - reserve)` formula operating on the citizen's single combined balance, never per-chain |
| PROP-101i | REQ-101 | `computePerCitizenSurplusUsd({citizens, perCitizenReserveUsd})` returns exactly one `{citizenId, surplusUsd}` record per input citizen, each `surplusUsd` equal to `max(0, balance_i - perCitizenReserveUsd)` for that SAME citizen, and `computeColonySurplusUsd`'s own returned aggregate on the IDENTICAL fixture equals the SUM of every returned `surplusUsd` value — proving the two are consistent BY CONSTRUCTION (`computeColonySurplusUsd` literally calls this function and sums it), never two independently-maintained numbers that could silently drift apart (new, resolves FIND-1202, major) | 0/1 | true | Tier 0 (structural): read `computeColonySurplusUsd`'s source confirming it calls `computePerCitizenSurplusUsd` and sums its output, rather than an independently-written reduce. Tier 1: unit test, fixture set of citizens with mixed above/below-reserve balances → assert `computePerCitizenSurplusUsd`'s per-citizen output matches `max(0, balance_i - reserve)` for EACH citizen individually, AND assert `computeColonySurplusUsd`'s own returned total on the SAME fixture equals the sum of every `surplusUsd` this function returns |
| PROP-101j | REQ-101 | REQ-101's real orchestration derives `filterProductiveCitizens`'s `ledgerRows` argument by calling it with `ledger.js::readChildren(...)`'s direct real output, and its `citizens` argument with a real read of `CITIZENS_REGISTRY_PATH`'s content — never a hand-rolled reimplementation/re-assembly of either at the call site; `computeColonySurplusUsd`/`readCitizenBalances` both receive this SAME filtered array directly, never an independently re-read or re-derived one (new, resolves the sweep-found sibling gap alongside FIND-1601 — mirrors PROP-102g/PROP-102i's own real-derivation discipline, which PROP-102g's own citation had claimed, but did not actually establish, for `filterProductiveCitizens`/`readCitizenBalances`) | 1/2 | true | Tier 1: source-grep/control-flow read confirming REQ-101's caller passes `readChildren(...)`'s return value directly as `ledgerRows` and a real registry read's content directly as `citizens`, with no intervening re-derivation/re-mapping code, and that `computeColonySurplusUsd`/`readCitizenBalances` receive the SAME `filterProductiveCitizens`-filtered array, never an independent second read. Tier 2: integration test — write a real, mixed set of rows to a real `ledger.js` file and a real citizen registry to `CITIZENS_REGISTRY_PATH`, call `readChildren`/the registry read for real, and assert `filterProductiveCitizens`'s behavior over that REAL data matches PROP-101d's fixture-level expectations exactly |
| PROP-102a | REQ-102 | `colonySurplusUsd === spawnThresholdUsd` exactly → `eligible:true` (inclusive boundary) | 1 | true | unit test at the exact boundary value and at `boundary - 0.01` |
| PROP-102b | REQ-102 | Cooldown gate overrides surplus size — surplus far above threshold does NOT bypass an unexpired cooldown, for EITHER cooldown trigger (a success in-window, OR the failure-cap reached in-window) — corrected, resolves FIND-1101 | 1 | true | unit test: huge surplus, `recentSpawnAttempts` containing ONE `outcome:"success"` entry inside the cooldown window → `eligible:false, reason:"rate_limited"` UNCONDITIONALLY; a SECOND fixture, huge surplus, `recentSpawnAttempts` containing `failureCooldownCap` (3) `outcome:"failure"` entries (zero successes) inside the window → `eligible:false, reason:"rate_limited"` identically — proving PROP-102b and PROP-305c/PROP-305g exercise the SAME reconciled `decideColonySpawn` logic from each side, never two different behaviors (resolves FIND-1101 — replaces the prior single-scalar `lastSpawnAttemptMs` fixture, which could not express the failure-cap case at all) |
| PROP-102c | REQ-102 | `childrenProvisioning >= maxConcurrentSpawns` blocks eligibility regardless of surplus/cooldown | 1 | true | unit test: surplus and cooldown both satisfied, `childrenProvisioning=maxConcurrentSpawns` → `eligible:false, reason:"max_concurrent_spawns"` |
| PROP-102d | REQ-102 | Non-finite/negative `colonySurplusUsd` input is treated as `0` (never eligible) | 1 | true | unit test mirroring the existing `tier.mjs`/`catalog-gate.mjs` NaN/Infinity/negative fixture convention |
| PROP-102e | REQ-102 | Check ordering is surplus → cooldown → concurrency cap (matches `spawn-decision.js`'s existing ordering discipline) | 1 | true | unit test: a fixture failing ALL THREE checks asserts the returned `reason` is the SURPLUS failure, not cooldown or cap (proves evaluation order, not just final boolean) |
| PROP-102f | REQ-102 | `deriveRecentSpawnAttempts({ledgerRows})` correctly maps `ledger.js` rows, grouped by `child_id`, to exactly one `{ts, outcome}` entry per group across all four real-world cases (new, resolves FIND-1401, critical) | 1 | true | unit test, four fixtures against the SAME function: (a) a `child_id` whose only/last row is `"failed"` → one entry, `outcome:"failure"`, `ts` equal to that row's `attempted_ms`; (b) a `child_id` whose last row is `"active"` (no bootstrap failure) → one entry, `outcome:"success"`, `ts` equal to the FIRST row's `attempted_ms`; (c) a `child_id` with an `"active"` row FOLLOWED by a LATER `"bootstrap_failed"` row for the SAME `child_id` → still exactly ONE entry, `outcome:"success"` (never flipped to `"failure"`, and never a SECOND, additional entry for the same attempt), `ts` unchanged from the original `attempted_ms`; (d) a `child_id` whose only row is still `"provisioning"` (genuinely in flight) → EXCLUDED entirely from the returned array (zero entries for that `child_id`) — together these four fixtures prove the exact double-counting/retroactive-flip hazard FIND-1401 raised cannot occur |
| PROP-102g | REQ-102 | REQ-102's real orchestration derives `recentSpawnAttempts` by calling `deriveRecentSpawnAttempts({ledgerRows: readChildren(...)})` directly over `ledger.js`'s real output — never a hand-rolled reimplementation of the join logic at the call site (new, resolves FIND-1401, critical — mirrors PROP-101d/PROP-101e's own real-derivation discipline for `filterProductiveCitizens`/`readCitizenBalances`) | 1/2 | true | Tier 1: source-grep/control-flow read confirming `decideColonySpawn`'s caller passes `deriveRecentSpawnAttempts`'s return value directly as `recentSpawnAttempts`, with no intervening re-derivation/re-mapping code. Tier 2: integration test — append a real mixed set of rows (a failure, a success, a success-then-`bootstrap_failed`, an in-flight `"provisioning"`) to a real `ledger.js` file, call `readChildren` for real, and assert `deriveRecentSpawnAttempts`'s output over that REAL data matches PROP-102f's fixture-level expectations exactly |
| PROP-102h | REQ-102 | `countChildrenProvisioning({ledgerRows})` correctly counts `ledger.js` rows, grouped by `child_id`, reduced to the last-appended row per group, whose `status` is EXACTLY `"provisioning"` (new, resolves FIND-1501, critical) | 1 | true | unit test, four fixtures against the SAME function: (a) a `child_id` whose only row is `"provisioning"` → count includes it; (b) a `child_id` whose `"provisioning"` row is followed by a LATER `"active"` row → NOT counted; (c) a `child_id` whose `"provisioning"` row is followed by a LATER `"failed"` row → NOT counted; (d) a `child_id` with a `"provisioning"`→`"active"`→`"bootstrap_failed"` sequence → NOT counted (mirrors PROP-102f's own case (c) for its sibling function) — together these four fixtures prove the exact double-counting/permanent-block hazard FIND-1501 raised cannot occur |
| PROP-102i | REQ-102 | REQ-102's real orchestration derives `childrenProvisioning` by calling `countChildrenProvisioning({ledgerRows: readChildren(...)})` directly over `ledger.js`'s real output — never a hand-rolled reimplementation of the count at the call site (new, resolves FIND-1501, critical — mirrors PROP-102g's own real-derivation discipline for `recentSpawnAttempts`) | 1/2 | true | Tier 1: source-grep/control-flow read confirming `decideColonySpawn`'s caller passes `countChildrenProvisioning`'s return value directly as `childrenProvisioning`, with no intervening re-derivation/re-counting code. Tier 2: integration test — append a real mixed set of rows (a lone `"provisioning"` row, a `"provisioning"`-then-`"active"` pair, a `"provisioning"`-then-`"failed"` pair) to a real `ledger.js` file, call `readChildren` for real, and assert `countChildrenProvisioning`'s output over that REAL data matches PROP-102h's fixture-level expectations exactly |
| PROP-102j | REQ-102 | `deriveMeasuredShelterCostUsd({shelterCostLedgerRows})` returns `null` on an empty ledger (so `MIN_SHELTER_USD` stays its provisional `5.00` default) and, once one or more entries exist, returns ONLY the LAST-appended entry's `settledLeaseCostUsd` — never an average, sum, or historical-max across every accumulated entry, and never the first-ever entry (new, resolves the sweep-found sibling gap alongside FIND-1501) | 1 | true | unit test, three fixtures: (a) empty `shelterCostLedgerRows` → `null`; (b) a single entry → that entry's `settledLeaseCostUsd`; (c) THREE entries appended over time with DIFFERENT `settledLeaseCostUsd` values → assert the function returns ONLY the LAST (most-recently-appended) entry's value, never an average/max/first-entry value across the three |
| PROP-102k | REQ-102 | REQ-102's real orchestration derives `colonySurplusUsd` by calling `computeColonySurplusUsd({citizens: filterProductiveCitizens({citizens: <a real `CITIZENS_REGISTRY_PATH` read>, ledgerRows: readChildren(...), nowMs, bootstrapWindowDays}), perCitizenReserveUsd})` directly — never a hand-rolled reimplementation/re-assembly of the aggregation at the call site, and never a stale/earlier evaluation's cached aggregate reused across multiple `decideColonySpawn` evaluations within the SAME wake (new, resolves FIND-1701, critical — mirrors PROP-101j/PROP-102g/PROP-102i/PROP-202d's own real-derivation discipline) | 1/2 | true | Tier 1: source-grep/control-flow read confirming `decideColonySpawn`'s caller passes `computeColonySurplusUsd(...)`'s return value directly as `colonySurplusUsd`, with no intervening re-derivation/re-assembly/caching code, and confirming a SEPARATE call to this SAME pipeline is made for EACH separate `decideColonySpawn` evaluation within one wake — never one cached aggregate shared across multiple evaluations. Tier 2: integration test — write a real, mixed set of rows to a real `ledger.js` file and a real citizen registry to `CITIZENS_REGISTRY_PATH`, call the real `readChildren`/registry read → `filterProductiveCitizens` → `computeColonySurplusUsd` pipeline, and assert `decideColonySpawn`'s real call site receives EXACTLY that value for that evaluation; a second fixture that mutates the underlying registry/ledger data BETWEEN two evaluations within the same simulated wake confirms the SECOND evaluation's `colonySurplusUsd` reflects the freshly-recomputed value, never the FIRST evaluation's earlier aggregate |
| PROP-103a | REQ-103 | Given two concurrent callers both observing `eligible:true`, exactly one reaches REQ-201's wallet-generation step, AND both callers acquire the lock via the SAME `statePath` (the exported `CITIZENS_REGISTRY_PATH` constant) | 2 | true | integration test: two `Promise.all`-raced calls into `withColonyLock(CITIZENS_REGISTRY_PATH, "colony-spawn", fn)`, assert exactly one invocation of the (mocked) wallet-generation step, the other returns `reason:"lock_held"` with zero wallet-generation calls — this proves interlock WITHIN one test process; PROP-103d (below) is required IN ADDITION to prove every real call site converges on the same `statePath` (resolves FIND-103: a single test process sharing one implicit `statePath` choice cannot, by itself, prove that) |
| PROP-103b | REQ-103 | A crashed holder's lock (no heartbeat for ≥ `staleMs`) is reclaimable by exactly one subsequent caller | 1/2 | true | reuses the exact Tier-1 `isLockStale` fixture tests already proved upstream (`anicca-agent-economy` REQ-101/PROP-101b) plus a Tier-2 test creating a real backdated `"colony-spawn"` lock file and asserting exactly one of two concurrent reclaim attempts succeeds |
| PROP-103c | REQ-103 | A live, heartbeating holder is never stolen from, however long its critical section legitimately runs | 1 | true | reuses the exact Tier-1 fixture proof already established upstream for `isLockStale` (no new proof needed — REQ-103's own obligation is only that the NEW `"colony-spawn"` key is wired through the same, already-proved mechanism) |
| PROP-103d | REQ-103 | EVERY call site in the implementation that acquires the `"colony-spawn"` lock imports and passes the SAME exported `CITIZENS_REGISTRY_PATH` constant from `registry-path.mjs` — never an independently hardcoded path string | 0 | true | structural/Tier-0 check: source-grep or import-identity check across the diff confirming a single import site for `CITIZENS_REGISTRY_PATH` and zero literal `citizens.json` path strings hardcoded elsewhere (resolves FIND-103) |
| PROP-103e | REQ-103 | The colony-spawn lock remains HELD across its ENTIRE critical section — REQ-201's wallet generation THROUGH REQ-304's funding call THROUGH REQ-305's ledger append actually completing — never released any earlier (e.g. not merely through REQ-205 or "the decision to proceed"); proven under a STAGGERED (non-simultaneous) race, not merely PROP-103a's simultaneous one: a second evaluator's lock-acquire attempts, issued repeatedly WHILE a first evaluator's REQ-304 funding call is still in flight (i.e. AFTER the first evaluator's REQ-201-205 have already completed), ALL fail — succeeding only after the first evaluator's REQ-305 append has actually landed and the lock is released (new, resolves FIND-1201, critical) | 2 | true | integration test: the first caller's fixture funding-transfer step (REQ-304) is instrumented with a controllable, artificially delayed resolution (e.g. a `Promise` the test itself resolves on command); WHILE that delay is pending — i.e., strictly AFTER the first caller's REQ-201-205 wallet-generation/identity steps have already completed, and strictly BEFORE its REQ-304 funding call and REQ-305 append have run — a second caller repeatedly attempts to acquire the SAME `"colony-spawn"` lock (same `CITIZENS_REGISTRY_PATH` `statePath`) at multiple points across that delay window → assert EVERY one of those attempts fails with `reason:"lock_held"` and makes zero REQ-201 wallet-generation calls; only once the first caller's REQ-305 append completes (releasing the lock) does the second caller's NEXT attempt succeed — proving the lock's real scope covers REQ-304/REQ-305, not merely REQ-201-205, closing the staggered-evaluator double-spend/double-funding race FIND-1201 identified |
| PROP-104a | REQ-104 | `decideColonySpawn`/`computeColonySurplusUsd`'s source contains no network call, no prompt/LLM-client reference, and no scoring/ranking/free-text-recommendation field on its return value | 0 | true | Phase 3 structural grep/read of the diff; fails if any such reference is found, exactly as `anicca-agent-economy`'s PROP-203a/b already established for its own gate |
| PROP-105a | REQ-105 | The seed template, `citizens.seed.json`, parses as an array of `{id, wallet: {evm?: boolean, solana?: boolean}, walletAddress: {evm?: string, solana?: string}, fuel, humanDependencies, homeDir, coLocatedWithCoordinator: boolean}` objects (no `telemetryPath` field — removed, resolves FIND-302), and `isSelfFunded()` (unmodified) accepts any one record's `{wallet, fuel, humanDependencies}` sub-object (never `walletAddress`, never `coLocatedWithCoordinator`) without throwing | 0/1 | true | Tier 0: structural JSON-shape check of `citizens.seed.json`, including that `coLocatedWithCoordinator` is present and boolean-typed on every entry (resolves FIND-703); Tier 1: unit test calling `isSelfFunded()` on each seeded record's boolean `wallet` sub-object only |
| PROP-105b | REQ-105 | A single malformed/incomplete registry record is excluded from REQ-101's aggregation without aborting aggregation for every OTHER valid citizen | 1 | true | unit test: fixture registry with one malformed record among 2 valid ones → assert aggregation returns the sum of only the 2 valid citizens, never throws |
| PROP-105c | REQ-105 | `citizens.seed.json`'s content, when each entry's `{wallet, fuel, humanDependencies}` sub-object is passed through the existing, unmodified `isSelfFunded()`, returns `true` for EVERY seeded entry | 1 | true | unit test: direct assertion against the literal seed fixture (both entries) — a straightforward assertion against literal fixture data, NOT an out-of-band-knowledge-dependent comparison (resolves FIND-101's critique that the prior "compare against today's known-good identities" proof method presupposed a ground truth the bare pre-existing file could never supply) |
| PROP-105d | REQ-105 | Neither `citizens.seed.json` at bootstrap NOR the durable `citizens.json` at any later append (see PROP-305e) EVER contains an entry whose `{wallet, fuel, humanDependencies}` sub-object makes `isSelfFunded()` return `false` | 0/1 | true | Tier 0: structural check that the literal seed array in `citizens.seed.json` contains only the two verified self-funded entries and excludes claude-p/any human-funded wallet; Tier 1: unit test iterating the seed array asserting `isSelfFunded()===true` for all entries (resolves FIND-101's permanent-hazard-closure requirement) |
| PROP-105e | REQ-105 | Every entry's `homeDir` is an ALREADY-RESOLVED absolute path — its value never contains the literal substring `$HOME` or `$ANICCA_HOME` anywhere in `citizens.seed.json` or the durable `citizens.json`, at seed time or at any later append (no `telemetryPath` field exists to check — removed, resolves FIND-302) | 0 | true | structural/Tier-0 check: grep `citizens.seed.json` (and, at Phase 3, the durable `citizens.json`'s any real appended rows) for the literal substrings `$HOME`/`$ANICCA_HOME` — must find none (resolves FIND-202); also grep confirms zero occurrences of the key `telemetryPath` anywhere in either file (resolves FIND-302) |
| PROP-105f | REQ-105 | `homeDir` is present and non-empty on every seeded/appended entry, and is consumed ONLY by REQ-403's audit — never passed to `isSelfFunded()` | 1 | true | unit test: fixture record's `homeDir` field is asserted present and is NOT among the keys `isSelfFunded()` reads (resolves FIND-202) |
| PROP-105g | REQ-105 | Every seeded (and later appended, REQ-305) entry's `walletAddress` value is verified, at the time it is written, against that citizen's ACTUAL signing key material via an ACTUAL, MECHANICALLY-PERFORMED cryptographic re-derivation — **TWO-BRANCH, corrected resolves FIND-801 (critical): EVM** (`viem`'s `privateKeyToAccount` against the real private-key file, read in memory, diffed against `walletAddress.evm`) **and Solana** (`@solana/web3.js`'s `Keypair.fromSecretKey` against the real secret file's `bs58`-decoded 64-byte form, read in memory, diffed against `walletAddress.solana`) — whichever chain(s) that citizen's record populates; a citizen with BOTH populated (REQ-202's expected Nosana-path shape) MUST pass BOTH branches independently (see PROP-105i) — NEVER solely against a static markdown documentation snapshot (`CLAUDE.md`/`docs/WALLETS.md`), which this iteration's own review proved can silently drift stale after a real key rotation without this spec's own seed data (already correct) being affected (resolves FIND-601), and NEVER merely a check that a commit/PR message CITES the right kind of verification method without the computation ever actually having been run (resolves FIND-702 — a citation-presence check is a materially weaker, non-equivalent substitute for this row's own binding rule and is explicitly rejected). A live on-chain balance query is NEVER an acceptable substitute for either branch — it does not prove derivation-correctness (resolves FIND-801's critique of this obligation's prior unelaborated "OR a live balance query" escape hatch), though it MAY be cited as additional corroboration | 0/2 | true | **Rewritten, resolves FIND-702 — this is an ACTUAL mechanical re-performance, never a citation check; corrected TWO-BRANCH, resolves FIND-801:** Tier 0 (structural): confirms a real re-derivation script/test exists in this feature's diff, covering BOTH the EVM and Solana branches (whichever a given citizen's record populates), and is wired to run at Phase 3 for every seeded/appended `walletAddress`. Tier 2 (the binding check), EVM branch: a real script/test reads the real private-key file's content IN-MEMORY (e.g. `~/.automaton/wallet.json`'s real `privateKey`), computes the resulting address via `privateKeyToAccount` (the same pattern already used this session for the automaton wallet), and DIFFS the result against `citizens.json`'s stored `walletAddress.evm` for that SAME citizen — FAILING HARD (non-zero exit / test failure) on any mismatch. Tier 2, Solana branch (new, resolves FIND-801): a real script/test reads the real secret file's content IN-MEMORY (e.g. `~/.blockrun/.solana-session`'s real base58-encoded 64-byte secret, per `resolve-identity.mjs::readRawSecretFile`'s own confirmed real return shape — a bare base58 string, no JSON wrapper), `bs58.decode()`s it to a 64-byte `Uint8Array` (the EXACT, already-proven conversion `~/anicca/runtime/dashboard/telemetry-post-franklin.mjs` already performs against this SAME file — `bs58` already a real dependency, `~/anicca/runtime/package.json`: `"bs58": "^5.0.0"`), computes the resulting address via `Keypair.fromSecretKey(secretKeyBytes).publicKey.toBase58()` (`@solana/web3.js` already a real dependency, `~/anicca/package.json`: `"@solana/web3.js": "^1.98.4"` — no new dependency introduced for either conversion), and DIFFS the result against `citizens.json`'s stored `walletAddress.solana` for that SAME citizen — FAILING HARD on any mismatch, identical rigor to the EVM branch. **Carve-out (resolves FIND-702's secrets-handling reconciliation, extended to the Solana branch):** reading either branch's key-material file content IN-MEMORY, for THIS ONE specific re-derivation purpose, is explicitly PERMITTED and REQUIRED — narrower than, and not in conflict with, REQ-105's general "file EXISTENCE only — content never read/printed" discipline used elsewhere in this spec for checks that do not need to read secret content (e.g. REQ-403's live filesystem-existence check, which never needs this); the ONLY discipline retained here is that the raw private key/secret itself is NEVER logged, printed, or persisted anywhere — only the DERIVED PUBLIC ADDRESS may ever be logged/compared/asserted on. Today's two seed entries are confirmed to satisfy this: automaton's `0xB9dd3B...` independently re-derived via `privateKeyToAccount` against `~/.automaton/wallet.json`'s real `privateKey`, cross-checked against `colony-status.sh`'s own live balance query, 2026-07-07 — ACTUALLY PERFORMED, not merely cited; Franklin's `8FpqdcCHqjqkVXR58eVJa53neXbJf9emXhvHhgeUPCV9` independently re-derived via `bs58.decode()` + `Keypair.fromSecretKey().publicKey.toBase58()` against `~/.blockrun/.solana-session`'s real secret, 2026-07-07 — likewise ACTUALLY PERFORMED (in a disposable scratch install of `@solana/web3.js`/`bs58` outside this repo, for the check only) and an EXACT match against the seeded value, resolving FIND-801 |
| PROP-105h | REQ-105 | Every seeded entry's `coLocatedWithCoordinator` field is present, boolean-typed, and `true` for BOTH of today's seeded entries (automaton, Franklin — both genuinely co-located on the same Mac Mini today, REQ-106); no seed entry ever has this field `false` or missing (resolves FIND-703) | 0/1 | true | Tier 0: structural JSON-shape check of the seed file confirming `coLocatedWithCoordinator === true` for both literal entries; Tier 1: unit test asserting the seeded array's `coLocatedWithCoordinator` values equal `[true, true]` |
| PROP-105i | REQ-105 | A citizen record with BOTH `walletAddress.evm` AND `walletAddress.solana` populated (REQ-202's expected shape for every Nosana-path child) has EACH populated chain independently re-derived and diffed via PROP-105g's two branches — passing ONLY if BOTH branches independently match; a mismatch on EITHER chain alone fails the whole check hard, never averaged/OR'd/skipped across chains, and neither branch's pass/fail result is ever inferred from the other (new, resolves FIND-801) | 0/2 | true | Tier 0 (structural): confirms the re-derivation script/test invokes BOTH branches (never short-circuiting after the first populated field) whenever a citizen record has both `walletAddress.evm` and `walletAddress.solana` populated. Tier 2 (the binding check): fixture/integration test with a dual-populated citizen record where (a) both branches match → overall PASS, (b) the EVM branch mismatches while the Solana branch matches → overall FAIL (never silently passing on the Solana match alone), and (c) the Solana branch mismatches while the EVM branch matches → overall FAIL (the symmetric case) — asserting the check is conjunctive (`AND`), never disjunctive (`OR`), across the two chains |
| PROP-105j | REQ-105 | The git-tracked seed template, `citizens.seed.json`, is NEVER written to by any runtime code path this feature adds — it is read exactly once (at `CITIZENS_REGISTRY_PATH`'s one-time bootstrap copy) and never mutated thereafter (new, resolves FIND-901 — critical) | 0 | true | structural/Tier-0 check: source-grep across this feature's ENTIRE diff for any write call (`fs.writeFile`/`fs.writeFileSync`/`fs.appendFile`/equivalent) whose target path resolves to `citizens.seed.json` — must find ZERO such call sites; the ONE documented read call site (the bootstrap-copy step) is confirmed to be a READ, never paired with a write back to the same path |
| PROP-105k | REQ-105 | `CITIZENS_REGISTRY_PATH` resolves, via `resolveStateDir({env, home})` (`~/anicca/skills/self/spawn/lib/state-path.js`, reused unmodified — the SAME function `run.sh` already calls for `children.jsonl`), to a location structurally OUTSIDE the `~/anicca` git working tree; consequently, a real `git checkout <branch>`/`git worktree add\|remove`/`git pull` on `~/anicca` does NOT affect the durable `citizens.json`'s content (new, resolves FIND-901 — critical) | 0/2 | true | Tier 0 (structural): read `registry-path.mjs`'s source confirming `CITIZENS_REGISTRY_PATH`'s construction is `path.join(resolveStateDir({env, home}), 'citizens.json')` — never a literal path string beginning with (or resolving inside) the `~/anicca` repo root, and never independently duplicating `resolveStateDir`'s logic. Tier 2 (the binding check, LIVE, no mock): (1) write a distinctive fixture record to the durable file at the real `CITIZENS_REGISTRY_PATH`; (2) run a real `git checkout` to a different branch (or back), a real `git worktree add`/`git worktree remove` cycle, and a real `git pull` (or `git fetch && git merge`, whichever is safe in the test environment) on the REAL `~/anicca` repo; (3) re-read the durable file and assert the fixture record is BYTE-IDENTICAL to what was written in step (1); (4) separately assert a `git status`/`git diff` on `~/anicca` taken immediately after a REQ-305 durable-file append shows ZERO changes to the working tree (the append touched no git-tracked path at all) |
| PROP-105l | REQ-105 | The `CITIZENS_REGISTRY_PATH` bootstrap step is a SINGLE atomic POSIX exclusive-create (`fs.open(path, 'wx')`, `O_CREAT\|O_EXCL`) — never a check-then-act "exists? then copy" pair; consequently (a) of two concurrent first-access callers, exactly ONE succeeds and the other fails `EEXIST` and reads-only (never overwrites, never double-writes), and (b) a late/slow bootstrap attempt racing a real, already-completed REQ-305 append also fails `EEXIST` and reads-only, NEVER overwriting the already-appended citizen record (new, resolves FIND-1001 — critical) | 0/2 | true | Tier 0 (structural): read the bootstrap implementation's source confirming it performs exactly ONE `fs.open(CITIZENS_REGISTRY_PATH, 'wx')`-equivalent call (or catches its `EEXIST` and falls through to a read) — NO separate `fs.existsSync`/`fs.stat` check precedes a separate write call anywhere in this code path, mirroring `lib/lock.mjs::tryCreateLockFile`'s own exact shape. Tier 2 (the binding check, LIVE, no mock), TWO fixtures: (1) concurrent-race fixture — two simulated first-access callers (`Promise.all`-raced, or two separate `node` subprocesses against the SAME real, not-yet-existing `CITIZENS_REGISTRY_PATH`) both attempt the bootstrap exclusive-create at the same time → assert exactly ONE observes success (the seed content is written verbatim, byte-identical to `citizens.seed.json`) and the OTHER observes `EEXIST` and performs zero writes, instead reading back the winner's content; (2) late-bootstrap-after-real-append fixture — perform a real REQ-305 append to the durable file BEFORE invoking a simulated late bootstrap attempt's exclusive-create call → assert the exclusive-create fails `EEXIST` (the file already exists, now containing the real appended record, not merely the seed content), the late caller performs zero writes, and a re-read of the durable file shows the appended record byte-identical/untouched |
| PROP-105m | REQ-105 | `COORDINATOR_HOME` genuinely tracks the real process environment's `os.homedir()` value at module-load time — it is NOT a hardcoded literal, NOT an independent `process.env.HOME` read, and NOT assumable-pure/zero-I/O — consistent with `registry-path.mjs`'s corrected "Effectful Shell" classification (resolves FIND-1002 — major; corrects the prior "Pure Core" mislabeling that invited a zero-I/O, no-environment-control Tier-1 test for this module) | 0/2 | true | Tier 0 (structural): read `registry-path.mjs`'s source confirming `COORDINATOR_HOME`'s implementation is a direct `os.homedir()` call at module-load time — never a hardcoded literal string, and never `process.env.HOME` read as a substitute. Tier 2 (the binding check, LIVE, no mock): (1) in the SAME test process, independently call `os.homedir()` directly and assert it equals the imported `COORDINATOR_HOME` constant (proves no drift/caching bug); (2) load/invoke `registry-path.mjs` in a real child process launched with a DIFFERENT real `HOME` environment value (a disposable fixture directory, distinct from the coordinator's own real home) and assert THAT process's own `COORDINATOR_HOME` equals `os.homedir()`'s value FOR THAT PROCESS — never the original coordinator host's value — proving `COORDINATOR_HOME` is genuinely environment-coupled (Effectful), never a fixed constant baked in at build time |
| PROP-106a | REQ-106 | `lock.mjs`'s acquire/release path and `ledger.js`'s read/write path are invoked from exactly one designated coordinator-host code entry point, with no code path invoking them from a cloud-deployed child's own runtime | 0 | true | structural read of the implementation's call graph; Phase 3 adversary confirms no child-side code path reaches `lock.mjs`/`ledger.js` |
| PROP-106b | REQ-106 | This spec's own scope section explicitly states spawn chaining is out of scope | 0 | true | structural read of `behavioral-spec.md`'s scope section; a fresh adversary reviewing REQ-103/REQ-305 is not required to (and must not) prove multi-host correctness |
| PROP-201a | REQ-201 | A `gen-wallet.sh` output whose address derives from the documented sha256-fallback path (no real keccak available) is detected and rejected, never used | 1/2 | true | unit/integration test: inject an environment where the keccak dependency is unavailable, assert the caller aborts rather than proceeding with the fallback address |
| PROP-201b | REQ-201 | The generated child EVM address is verified distinct from every currently-known citizen's own address before proceeding | 1 | true | unit test: fixture citizen-address list including the freshly-generated address (forced collision case) → assert abort/regenerate, never silent proceed |
| PROP-201c | REQ-201 | Private key material is captured only into a 600-perm file under the child's own isolated `$HOME`, never into a shared log | 0/2 | true | Tier 0: structural read of the calling code confirms stdout is redirected directly to a file path, never piped through any logging wrapper; Tier 2: a real invocation's `gen-wallet.sh` output file has mode `0600` and lives under the child's own home |
| PROP-201d | REQ-201/301 | The generated private key material is NEVER written into any boot-time artifact (SDL `env:` line, Nosana job command string, cloud-init `user_data` field, or any artifact `provider-services sdl-to-manifest`/a job-definition dump would expose publicly) at any point between generation and its delivery via REQ-303's `lease-shell`/REQ-302's `job ssh` post-boot injection step | 0 | true | structural read: grep the rendered SDL/job-definition artifact actually submitted for a real deploy for any private-key-shaped string — must find none; confirms the two-phase "boot secretless, inject after" sequence is actually followed, not merely asserted (resolves FIND-401) |
| PROP-202a | REQ-202 | `needsSolanaWallet({initialSkills, deployTarget})` returns `true` exactly when a Solana-settled skill OR Nosana deploy target is present, `false` otherwise | 1 | true | unit test, exhaustive branch coverage of the three trigger conditions (Solana skill / Nosana target / neither) |
| PROP-202b | REQ-202 | When `needsSolanaWallet` is `false`, no Solana key-generation subprocess is invoked at all | 2 | true | integration test: spy/mock the Solana keygen call, assert zero invocations on an EVM-only + Akash-only fixture |
| PROP-202c | REQ-202 | Generated Solana address is verified distinct from every existing citizen's own Solana address | 1 | true | unit test mirroring PROP-201b for the Solana keyspace |
| PROP-202d | REQ-202 | REQ-202's real orchestration derives `needsSolanaWallet`'s `deployTarget` argument by passing THAT SAME spawn attempt's `selectCloudTarget({nosanaAvailable, nosanaPriceUsd, akashAvailable, akashPriceUsd})` (REQ-306) return value directly — never hand-assembled, never a stale/earlier attempt's evaluation reused (new, resolves FIND-1601, critical — mirrors PROP-102g/PROP-102i's own real-derivation discipline) | 1/2 | true | Tier 1: source-grep/control-flow read confirming the caller passes `selectCloudTarget(...)`'s return value directly as `deployTarget`, with no intervening re-derivation, hardcoding, or stale-value reuse. Tier 2: integration test — invoke `selectCloudTarget` for a real/fixture spawn attempt and assert `needsSolanaWallet`'s `deployTarget` argument for THAT SAME attempt equals that exact return value; a second fixture with a DIFFERENT, earlier attempt's stale `selectCloudTarget` evaluation confirms the current attempt's `deployTarget` is never drawn from it |
| PROP-202e | REQ-202 | `needsSolanaWallet`'s `initialSkills` argument is never hardcoded or independently invented inside REQ-202's own orchestration — it is ALWAYS the SAME initial-skill-set value the spawning agent already chose for this child, per REQ-104's own agent-judgment carve-out (extended to explicitly cover this choice), identical to the value used to construct the child's own initial goal framing/prompt (new, resolves FIND-1601, critical) | 0 | true | structural/Tier-0 check: source-grep/read of REQ-202's implementation confirming `initialSkills` is passed through from the SAME upstream value the spawning agent's own goal-framing/prompt construction step uses for this child — never a literal/hardcoded skill-list constant, and never independently re-derived a second time inside REQ-202's own code path |
| PROP-203a | REQ-203 | The child's proposed `HOME`/`ANICCA_HOME` is checked for equality/containment against every existing citizen's own value BEFORE any REQ-201/202 key generation runs | 1 | true | unit test asserting the distinctness check function is called, and key-generation is NOT called, when a forced collision fixture is supplied |
| PROP-203b | REQ-203 | Two processes with two different injected `HOME` values, run against the SAME `resolve-identity.mjs` module, each resolve ONLY their own wallet file | 2 | true | integration test extending the existing `resolve-identity.mjs` test suite's own FIND-001-class regression pattern to a THIRD, freshly-generated home directory fixture |
| PROP-203c | REQ-203 | Every process-launch boundary used by REQ-302/303 explicitly sets `HOME`/`ANICCA_HOME` in its own artifact (SDL `env:`, job-definition `env`, cloud-init `Environment=`) — never relies on a base-image default | 0 | true | structural read of the ACTUAL rendered SDL/job-definition/cloud-init artifact used for a real deploy, confirming the explicit env line is present — for Akash, this means the child-specific SDL variant's new `HOME=/root` line (PROP-303f), NOT the original `spawn-child/sdl/child.yaml`/`deploy-akash.sh` inline-default templates, which a direct read confirms lack this line entirely (resolves FIND-403; this criterion was previously unverifiable against any real artifact this spec cited) |
| PROP-204a | REQ-204 | A real `register()` call against the live registry (mainnet or testnet, per `GIG_CHAIN`), invoked via `ensureAgentId`, succeeds, returns a real `agentId` and tx hash, using `ensure-agent-id.mjs`/`identity.mjs` unmodified | 3 | true | live E2E: a fresh child key calls `ensureAgentId`, independently re-verify the tx receipt + `ownerOf(agentId)` via a separate RPC call (not just trusting the returned value) |
| PROP-204b | REQ-204 | The one-time gas seed funding a child's `register()` call is sized to cover exactly one `register()` + one gig-board interaction, never an open-ended top-up | 0/2 | true | structural read of the funding-amount constant/formula; integration test confirms the transferred amount matches the documented sizing formula, not an arbitrary/larger figure |
| PROP-204c | REQ-204 | A wallet that already holds an agentId (defensive case) is not re-registered; the existing agentId is reused, via `ensureAgentId`'s own existing cache-hit/`verifyIdentity` re-check path, no second, parallel defensive check implemented for this feature | 1/2 | true | unit test reusing `ensure-agent-id.mjs`'s own existing `registerFn`/`verifyFn` injection pattern: inject a `verifyFn` that reports an existing, matching cached agentId → assert `registerFn` (`register()`) is never called a second time |
| PROP-205a | REQ-205 | The written `mcp.json` matches the exact key shape of the existing, live `~/.blockrun/mcp.json` | 0 | true | structural JSON-shape diff against the existing live file's schema |
| PROP-205b | REQ-205 | `GIG_STATE_PATH`'s resolved absolute path is verified distinct from every other currently-known citizen's own `GIG_STATE_PATH` at write time | 1 | true | unit test: fixture citizen path list including a forced collision → assert write is blocked/regenerated, not silently duplicated |
| PROP-206a | REQ-206 | A regression fixture identical to today's `child-spec.test.js` "assembles a complete, distinct-wallet spec" case (non-empty `childInbox`, no `agentEvmAddress`/`agentId`) passes UNCHANGED after the modification | 1 | true | unit test: exact existing fixture, assert identical output shape/values to today's |
| PROP-206b | REQ-206 | A fixture supplying `agentEvmAddress`+`agentId` and omitting `childInbox` succeeds; the returned row carries `agent_evm_address`/`agent_id` | 1 | true | unit test: new fixture, assert success and returned field presence |
| PROP-206c | REQ-206 | A fixture supplying NEITHER anchor throws; a fixture supplying only HALF of the ERC-8004 pair also throws | 1 | true | unit test: two fixtures (neither anchor; `agentEvmAddress` only) → assert both throw `missing identity anchor` |
| PROP-206d | REQ-206 | A structural diff of `child-spec.js` confirms the change is limited to required-field validation and the returned row's field list; `nextChildId` and the distinct-wallet assertion are byte-identical to today's | 0 | true | structural diff of the file against its pre-modification version |
| PROP-206e | REQ-206 | A fixture supplying BOTH a non-empty `childInbox` AND a complete `agentEvmAddress`+`agentId` pair simultaneously succeeds without throwing, and the returned row carries all three fields together | 1 | true | unit test: both-anchors-present fixture → assert success (never rejected as an XOR violation) — resolves FIND-102's EARS/edge-case self-contradiction |
| PROP-206f | REQ-206 | A real `buildChildSpec` call from REQ-305's spawn flow supplies concrete values for all SEVEN required fields — `parentWallet` (REQ-106's coordinator-host citizen's own wallet, distinct from `childWallet`), `generation` (exactly `1`), `seedUsdc`, `constitutionHash`, plus the ERC-8004 identity anchor pair — and succeeds, with every field correctly present in the returned row | 1/2 | true | fixture/integration test: populate all seven fields per REQ-206's derivation rules and assert success + correct field presence — not just the two identity-anchor-focused fixtures (PROP-206a/b) (resolves FIND-204) |
| PROP-206g | REQ-206 | `seedUsdc` passed into `buildChildSpec` is identical to the amount REQ-204 actually transferred as the gas seed for that same spawn attempt (never an independently-computed number), and `generation` is exactly `1` for every REQ-305 call in this increment | 1/2 | true | unit test: assert `seedUsdc === <REQ-204 gas-seed fixture amount>` and `generation === 1`; structural/Tier-0 check confirms no code path in this feature's diff passes any other `generation` value (resolves FIND-204) |
| PROP-206h | REQ-206 | A structural read/diff confirms `child-spec.js`'s returned row field `wallet` (a string) is never read as if it were, or assigned into, `citizens.json`'s `wallet` field (a boolean object) anywhere in this feature's implementation — the two are cross-referenced only via `walletAddress`/`child_id`, never via a shared `wallet` value | 0 | true | structural/Tier-0 check: source-grep/read across the diff confirming no code path assigns `ledger.js` row's `.wallet` into a `citizens.json` record's `.wallet` (or vice versa) (resolves FIND-304) |
| PROP-301a | REQ-301 | After a spawn attempt completes (success or failure), the initiating host retains no child-specific persistent runtime artifact (no lingering process, no child-specific systemd/launchd unit, no child wallet file left outside the child's own relocated home) | 0 | true | structural review of the deploy code path's post-attempt cleanup; Phase 3 adversary spot-checks a real attempt's initiating host afterward |
| PROP-302a | REQ-302 | The Nosana deploy step never reads/writes the invoking host's own default `~/.nosana/` directory when acting on behalf of a child | 1/2 | true | unit/integration test asserting the CLI invocation's key-path argument/env points at the child's own isolated file, and that no file appears under the invoking host's own `~/.nosana/` as a side effect |
| PROP-302b | REQ-302 | A real `nosana job post ... --wait` invocation for a child yields a job ID that independently resolves (via a separate query, not just the posting call's own stdout) to `RUNNING`/`COMPLETED` | 3 | true | live E2E against Nosana (devnet/cheapest mainnet market as a first pass, mainnet-class market for final completion per the Tier-3 policy above); independently re-query `https://explore.nosana.com/jobs/<id>` (or current CLI equivalent) |
| PROP-302c | REQ-302 | After a Nosana job reaches `RUNNING`, a `nosana job ssh`-based post-boot secrets-injection step delivers the child's own pre-generated wallet material into the running job's container — a genuinely NEW step, never claimed as pre-proven reuse | 2/3 | true | integration/E2E test: post-`RUNNING` invocation of `nosana job ssh <job> [port]` (confirmed-present CLI primitive, `job ssh --help`, invoked live 2026-07-07, raw transcript at `reviews/spec/iteration-6/evidence/cli-help-2026-07-07.txt`, resolves FIND-504) delivers a `.env`-shaped payload; assert the file/content lands inside the job's own container, never inferred from the job-posting call's own stdout alone (resolves FIND-401's Nosana-side analog); the exact non-interactive invocation shape is confirmed against the actually-installed CLI version at this test's own execution, not asserted from this spec's text alone |
| PROP-303a | REQ-303 | `deploy-akash.sh`/`akt-treasury.sh` are invoked with zero source modification (only `CHILD_ID`/SDL substitution) — this claim is SCOPED to those two script files only, never to the new child-specific SDL variant (PROP-303f) or the new secrets-injection step (PROP-303e), both of which are new code (resolves FIND-401/403's scope correction) | 0 | true | structural diff: the two script files on disk are byte-identical to their pre-existing versions; only the SDL template/CHILD_ID argument passed in differs |
| PROP-303b | REQ-303 | A real Akash deploy for a child yields an active lease and a successfully sent manifest, independently re-queryable | 3 | true | live E2E against Akash (sandbox-2 as a first pass per this repo's own established practice, mainnet for final completion); independently re-run `provider-services query market lease list`/`query deployment` to confirm state, not just trusting the script's own stdout |
| PROP-303c | REQ-303 | The real `AKASH_DEPOSIT` and settled lease cost are appended, via `shelter-cost-ledger.js::appendShelterCostEntry`, to the shelter-cost ledger that REQ-102's `deriveMeasuredShelterCostUsd({shelterCostLedgerRows: readShelterCostEntries(...)})` reads on its next evaluation (corrected, resolves the sweep-found sibling gap alongside FIND-1501 — previously cited an unnamed "threshold computation") | 1/2 | true | integration test: after a real/fixture deploy, confirm `readShelterCostEntries` gains a new entry, and a subsequent call to `deriveMeasuredShelterCostUsd({shelterCostLedgerRows: readShelterCostEntries(...)})` returns that entry's `settledLeaseCostUsd` (never `null`, never the `$5.00` default) — mirrors PROP-102g/PROP-102i's own real-derivation discipline |
| PROP-303d | REQ-303 | `computeSpawnGate({balanceAkt, costAkt: config.spawn_cost_akt, bufferAkt: config.buffer_akt})` (`~/anicca/skills/self/spawn-child/lib/akt-cost-gate.js`, reused unmodified) is called before every Akash deploy attempt, with `costAkt`/`bufferAkt` read from `spawn-child/config.json`'s own real values, and a `ready:false` result is treated as a REQ-305 deploy failure (never a fabricated `dseq`) | 0/1 | true | Tier 0: structural read confirms REQ-303's Akash-readiness check imports and calls this exact existing function rather than defining a competing threshold; Tier 1: reuses `akt-cost-gate.js`'s own existing unit tests (`lib/__tests__/akt-cost-gate.test.js`) as already-sufficient proof of the arithmetic itself (resolves FIND-402) |
| PROP-303e | REQ-303 | After `deploy-akash.sh`'s manifest-send succeeds, a NEW `provider-services lease-shell <service> "cat > /opt/anicca.env" --stdin` step (this feature's own orchestration code, never a `deploy-akash.sh` modification) delivers the child's pre-generated wallet material onto the leased container | 2/3 | true | integration/E2E test: post-manifest-send invocation of `lease-shell` (confirmed-present CLI primitive, `provider-services lease-shell --help`, invoked live 2026-07-07, raw transcript at `reviews/spec/iteration-6/evidence/cli-help-2026-07-07.txt`, resolves FIND-504) with `--stdin`; assert `/opt/anicca.env` exists on the leased container with the expected content, and that this step's failure (post-lease-active) is recorded as a REQ-305 deploy failure, never a silently-secretless `"active"` child (resolves FIND-401) |
| PROP-303f | REQ-303 | The child-specific SDL variant actually rendered/submitted for a real deploy contains an explicit `HOME=/root` `env:` line — corrects PROP-203c, which the ORIGINAL `spawn-child/sdl/child.yaml`/`deploy-akash.sh` inline default SDL do NOT satisfy (confirmed by direct read) | 0 | true | structural read of the ACTUAL post-`envsubst` SDL artifact used for a real deploy (not the unmodified template file) confirming the explicit `HOME=/root` line is present (resolves FIND-403) |
| PROP-304a | REQ-304 | No code path in this feature ever reads a human-funded wallet's private key or balance as a funding source | 0 | true | structural grep across all new funding-transfer code for any reference to a human-funded wallet path/env var (e.g. claude-p's known wallet identifiers) — must find none |
| PROP-304b | REQ-304 | A funding transfer's amount never exceeds the amount REQ-102 certified as available for that specific spawn attempt | 1/2 | true | unit/integration test: attempt to fund an amount greater than the certified surplus → assert rejection, not a silent overdraw |
| PROP-304c | REQ-304 | When no single citizen individually holds enough (even though the aggregate clears REQ-102's threshold), the spawn does not proceed this wake and no child ledger row is created | 1 | true | unit test: fixture with aggregate surplus above threshold but each individual citizen's own surplus below the deploy cost → assert no child record created, a funding-shortfall no-op is logged |
| PROP-304d | REQ-304 | Funding an Akash deploy's AKT/`uact` requirement reuses the REAL, already-documented multi-hop route — `~/anicca/skills/self/spawn-child/config.json`'s own `funding_route` field literally specifies the 4-hop bridge itself (`"solana/8453 -> noble-1 -> osmosis-1 -> akashnet-2 (Skip API smart_relay, 4-hop)"`); `SKILL.md`'s own separate documented sequence (lines 61-67) specifies the Solana-side Jupiter SOL→USDC pre-step that feeds it — rather than a same-chain single-transfer assumption, since neither current citizen's wallet natively holds AKT (citation split, corrected, resolves FIND-502) | 0/2 | true | structural read confirming the Akash-funding code path invokes this documented multi-hop sequence (not a single-transfer helper) and cites `config.json`'s field for the bridge and `SKILL.md`'s prose for the Jupiter pre-step as two separate sources, never merged; integration test (sandbox-2/testnet-first, per Tier-3 policy) confirms each hop lands the expected asset on the expected chain before `akt-treasury.sh`'s existing `mint-act` step runs (resolves FIND-402) |
| PROP-304e | REQ-304 | `config.json`'s `funding_route` field's first-hop label, `"solana/8453"`, names TWO real, independently valid Skip API entry points into the SAME `noble-1`→`osmosis-1`→`akashnet-2` back-half — `"solana"` (Franklin's path, via Jupiter SOL→USDC then a CCTP bridge transfer) and `"8453"`/Base mainnet (automaton's path, via a CCTP bridge transfer directly from Base-native USDC, no Jupiter step needed) — never a stray/internally-conflated label; the actually-funding citizen's own wallet chain determines which entry is used | 0 | true | resolved by a live query against Skip API's own public endpoints (2026-07-07, not a guess): `GET api.skip.build/v2/info/chains?include_evm=true&include_svm=true` confirms `{"chain_name":"Base","chain_id":"8453","chain_type":"evm"}` and `{"chain_name":"Solana","chain_id":"solana","chain_type":"svm"}` are both real, distinct, registered chains; `POST api.skip.build/v2/fungible/route` sourcing from Base USDC (`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, the same address `escrow.mjs::USDC_BASE_MAINNET` already uses) to `uakt` on `akashnet-2` returns a real, computable route (`chain_ids: ["8453","noble-1","osmosis-1","akashnet-2"]`, first hop `cctp_transfer`); Phase 2 implementation MUST support whichever entry chain (`"solana"` or `"8453"`) matches the actually-funding citizen's own wallet, never hardcoding a Solana-only entry (resolves FIND-502) |
| PROP-304f | REQ-304 | Multi-citizen SEQUENTIAL co-funding SUCCESS path (new, resolves FIND-1102): when no single citizen individually holds enough but two citizens' surpluses TOGETHER cover the deploy cost, two SEPARATE single-signer transfers (citizen A's own partial amount, then citizen B's own remaining amount, sequential — never simultaneous, no pooled/joint transaction) land the FULL required amount on the child wallet, and the spawn proceeds — distinct from PROP-304c's blocked/no-op path, which never exercises a successful multi-citizen fund-up | 1/2 | true | unit/integration test: fixture with citizen A surplus-above-reserve `$6`, citizen B surplus-above-reserve `$5`, deploy cost `$10` (neither alone sufficient, aggregate sufficient, matching REQ-102's already-certified amount) → citizen A transfers `$6`, citizen B transfers the remaining `$4` sequentially to the SAME child wallet → assert the final child-wallet balance equals exactly `$10` (the full deploy cost), assert the spawn proceeds (a child ledger row is created, never blocked as a no-op), and assert BOTH transfers are independently recorded/traceable in the funding ledger (each carrying its own paying citizen's identity per REQ-304's memo/log requirement) — never a single combined/anonymous transfer entry; a companion fixture confirms each individual transfer amount is checked against ONLY that citizen's own certified contribution — read directly, by name, from REQ-101's `computePerCitizenSurplusUsd({citizens, perCitizenReserveUsd})` output for that citizen's `citizenId` (resolves FIND-1202: the ceiling check binds to this exact, individually-exposed function, never a re-derived/re-summed aggregate value) — never the whole aggregate amount (resolves FIND-1102) |
| PROP-305a | REQ-305 | Every ledger write path sets `status` to exactly one of `{"provisioning","active","failed"}` — never omits it, never writes `"active"` before REQ-204+REQ-205 complete | 0 | true | structural review of every code path that calls `appendChild`/updates a child row |
| PROP-305b | REQ-305 | Injecting a failure at each of REQ-201/202/203/204/205/302/303 in turn produces a ledger row correctly identifying the failing step, and REQ-101's next aggregation excludes that child | 2 | true | integration test, one fixture per injected failure point |
| PROP-305c | REQ-305 | Failed attempts within a single cooldown window are capped (`FAILURE_COOLDOWN_CAP`, default `3`) — the IDENTICAL reconciled rule REQ-102's own Cooldown Check applies (corrected, resolves FIND-1101: this is no longer a competing behavior from PROP-102b's — it is the SAME `decideColonySpawn` logic exercised from the failure-count side); beyond the cap, further attempts within that window are rate-limited exactly as a successful spawn would be | 1 | true | unit test: `recentSpawnAttempts` containing exactly 3 `outcome:"failure"` entries within one window (zero `outcome:"success"` entries), then a 4th evaluation within the same window → `eligible:false, reason:"rate_limited"` even though no successful spawn has occurred — see PROP-305g for the adjacent below-cap boundary fixture |
| PROP-305d | REQ-305 | Marking a child `"active"` appends a new, correctly-shaped record (with `wallet` booleans and `walletAddress` strings correctly split, per REQ-105/FIND-104) to REQ-105's registry (`citizens.json`); a FAILED attempt appends NO registry record | 2 | true | integration test: assert a successful fixture spawn gains a registry record matching REQ-105's schema, and a failed fixture spawn leaves the registry unchanged |
| PROP-305e | REQ-305 | The append-on-spawn path calls the existing, unmodified `isSelfFunded()` on the new record's `{wallet, fuel, humanDependencies}` sub-object BEFORE appending, and REFUSES the append (zero write to `citizens.json`, a distinct logged failure) if it returns `false` | 1/2 | true | unit test (fixture record engineered to fail `isSelfFunded()`, e.g. all-`false` wallet flags → assert zero append) plus integration test (real `citizens.json` file, real `isSelfFunded()` call, confirm no new line is written) — resolves FIND-101's permanent-hazard-closure requirement |
| PROP-305f | REQ-305 | Every REQ-305 append sets the new record's `coLocatedWithCoordinator` field to EXACTLY `false` — never `true`, never omitted, never a computed/inferred value — because REQ-301's own absolute mandate makes a co-located spawned child structurally impossible this increment (resolves FIND-703) | 0/2 | true | Tier 0: structural/source-grep check confirming no code path in this feature's diff ever appends `coLocatedWithCoordinator: true` (or any value other than the literal `false`) for a REQ-305-triggered append; Tier 2: integration test — a real fixture append writes a record whose `coLocatedWithCoordinator` field is asserted `=== false` |
| PROP-305g | REQ-305 | The EXACT `FAILURE_COOLDOWN_CAP` boundary (new, resolves FIND-1101): STRICTLY FEWER than `FAILURE_COOLDOWN_CAP` failed attempts in the window (zero successes) does NOT trigger cooldown; the MOMENT the cap is reached, cooldown applies — proving the cap is exactly `3`, never `2` or unbounded, and never a different number than the one PROP-102b/PROP-305c already exercise | 1 | true | unit test, two fixtures against the SAME `decideColonySpawn`: (a) `recentSpawnAttempts` with exactly 2 `outcome:"failure"` entries in the window (zero successes), surplus/concurrency otherwise satisfied → `eligible:true` (cooldown does not yet apply); (b) the SAME fixture plus one more `outcome:"failure"` entry in the same window (now exactly 3) → `eligible:false, reason:"rate_limited"` — the two fixtures together pin the exact boundary, distinct from PROP-305c's own "3 failures, then a 4th attempt" fixture |
| PROP-305h | REQ-305 | `attempted_ms` field-lifecycle: it is set to `nowMs` on the FIRST `ledger.js` row ever appended for a given `child_id`, and every SUBSEQUENT row appended for that SAME `child_id` (a `"failed"` row, an `"active"` row, or REQ-402's `"bootstrap_failed"` row) carries the IDENTICAL `attempted_ms` value copied forward — never a freshly-generated timestamp on a follow-up row (new, resolves FIND-1401, critical) | 0 | true | structural/Tier-0 check: source-grep/read of every code path that calls `appendChild` for a `child_id` already present in `ledgerRows` confirms it reads that `child_id`'s existing (first-row) `attempted_ms` value and copies it verbatim onto the new row, never calling `Date.now()`/generating a new timestamp for a non-first row; a fixture on real `ledger.js` data (`"provisioning"` → `"active"` → `"bootstrap_failed"`, three rows for one `child_id`) asserts all three rows carry the IDENTICAL `attempted_ms` value |
| PROP-306a | REQ-306 | `selectCloudTarget` returns `"nosana"` when `nosanaPriceUsd < akashPriceUsd` and both available, `"akash"` for the reverse | 1 | true | unit test, both price-ordering branches |
| PROP-306b | REQ-306 | Equal normalized prices, both available → `"nosana"` (documented, deterministic tie-breaker, never randomized) | 1 | true | unit test: identical `nosanaPriceUsd`/`akashPriceUsd` fixture → assert `"nosana"` returned every run |
| PROP-306c | REQ-306 | Exactly one provider unavailable → that provider is never selected, the other is selected regardless of price; both unavailable → `"none"` | 1 | true | unit test: 3 fixtures (`nosanaAvailable=false`, `akashAvailable=false`, both `false`) |
| PROP-306d | REQ-306 | `selectCloudTarget` itself performs zero I/O — the effectful price/availability queries are a separate, effectful step | 0 | true | structural read confirming the pure comparison function accepts only already-fetched primitives as arguments |
| PROP-306e | REQ-306 | The new AKT-USD (and, if applicable, NOS-USD) price-fetch step fails closed to `0` (never throws, never silently treated as "provider unavailable" when it is actually a price error) when its public spot-price API call errors or returns a non-finite value, mirroring the exact fail-closed pattern already used by `ethPrice()`/`solPrice()` in this codebase | 1/2 | true | unit test: mocked fetch failure/non-finite response → price-fetch function returns `0`, never throws (resolves FIND-305) |
| PROP-401a | REQ-401 | A claimed $0-bootstrap success is corroborated by an independent RPC balance read (before/after), not accepted from either trading party's own self-report | 3 | true | live E2E: a fresh, independent `eth_call`/balance query taken before and after the child's own gig settlement, performed by a process that is neither trading party |
| PROP-401b | REQ-401 | The ledger entry recording success contains gig ID, tx hash, balance delta, and timestamp sufficient for a fresh adversary to re-derive the claim | 0 | true | structural check of the ledger row schema on a real success case |
| PROP-402a | REQ-402 | A child exceeding `BOOTSTRAP_WINDOW_DAYS` without a recorded REQ-401 success is relabeled `"bootstrap_failed"` (via `appendChild`-ing a NEW row for that `child_id`, never mutating the prior row — resolves FIND-405, reusing REQ-101's own last-write-wins reduction), and no others are | 1 | true | unit test: fixture set of children with varying `active_since` timestamps and success flags, assert exactly the correct subset is relabeled, and that the relabeling asserted is a NEW appended row (not an in-place mutation of `ledger.js`'s existing rows) |
| PROP-402b | REQ-402 | A late (post-window) success retroactively corrects the label back from `"bootstrap_failed"` | 1/2 | true | unit test: a child already labeled `"bootstrap_failed"` that subsequently produces a REQ-401-qualifying success → assert label correction on the next evaluation |
| PROP-402c | REQ-402 | A `"bootstrap_failed"` child's balance is excluded from REQ-101's productive-surplus aggregation even if nonzero — the citizen record comes from REQ-105's registry, but the `"bootstrap_failed"` FLAG itself is read from its matching `ledger.js` row via `filterProductiveCitizens` (REQ-101), never from a second, competing copy in `citizens.json` (resolves FIND-201) | 1 | true | unit test: fixture citizen (a REQ-105 registry record) whose matching ledger.js row is `"bootstrap_failed"`, with nonzero registry-recorded balance → assert `filterProductiveCitizens` excludes it before `computeColonySurplusUsd` ever runs |
| PROP-402d | REQ-402 | `children_bootstrap_failed` is recorded for observability only and has ZERO effect on REQ-102's `decideColonySpawn` signature or behavior (resolves FIND-203: no dangling REQ-402→REQ-102 data flow) | 0 | true | structural/Tier-0 check: `decideColonySpawn`'s pinned signature (REQ-102's own Acceptance Criteria) contains no `childrenBootstrapFailed`/`children_bootstrap_failed` parameter anywhere in the diff, and a fixture run with a nonzero bootstrap-failure count produces an IDENTICAL `decideColonySpawn` result to the same fixture with a zero count |
| PROP-402e | REQ-402 | `BOOTSTRAP_WINDOW_DAYS`'s configured value is the IDENTICAL value to `SPAWN_COOLDOWN_DAYS`'s configured value (REQ-102) — never merely coincidentally equal, and never two independently-configurable literals that could silently drift apart (new, resolves FIND-1301, major) — mirroring this spec's own established discipline that two cross-requirement-dependent values MUST be identical by construction, the SAME rule REQ-206's own `seedUsdc`/REQ-204 gas-seed-transfer-amount identity check already applies ("the two MUST be the identical value by construction, never merely close") | 0/1 | true | Tier 0 (structural): read the configuration source confirming `BOOTSTRAP_WINDOW_DAYS` is derived FROM (re-exports, aliases, or is assigned directly from) the SAME `SPAWN_COOLDOWN_DAYS` constant/config value REQ-102 defines — never a second, independently-declared literal that merely happens to also read `14` today. Tier 1: unit test asserting `BOOTSTRAP_WINDOW_DAYS === SPAWN_COOLDOWN_DAYS` at runtime, plus a mutation fixture — change `SPAWN_COOLDOWN_DAYS`'s configured value and assert `BOOTSTRAP_WINDOW_DAYS` changes identically alongside it, never remaining pinned to a stale independent literal — proving the identity holds by construction, not by today's coincidental numeric match |
| PROP-403a | REQ-403 | The static grep sweep (all 3 path forms, across skill scripts + cron/job configs) reports zero cross-instance path references in the current, real codebase | 0 | true | run the actual grep sweep against the real repo at Phase 3, not a fixture — must report zero findings for it to be considered proved on the CURRENT tree |
| PROP-403b | REQ-403 | With N ≥ 2 real running instances whose registry record has `coLocatedWithCoordinator === true` (enumerated from REQ-105's registry via that exact field, resolves FIND-703 — today: automaton + Franklin), pairwise comparison of `resolveEvmPrivateKey`/`resolveSolanaSecret` outputs, invoked against each citizen's own CORRECTED, DISTINCT `homeDir` (resolves FIND-501 — never the bare, shared `$HOME` an earlier revision wrongly seeded) AND against an EXPLICITLY-CONSTRUCTED `env` object using the canonical `COORDINATOR_HOME` constant (resolves FIND-603/FIND-701 — never a bare `{home: X}` call relying on ambient `process.env.HOME`, never an independently-hardcoded or independently-`os.homedir()`-read HOME value), shows no equal keys, and no instance's resolved key-FILE PATH lies inside another instance's own home directory | 2 | true | live check: invoke the resolvers once per instance in `citizens.filter(c => c.coLocatedWithCoordinator === true)` (resolves FIND-703), using that instance's own `homeDir` value (read directly from REQ-105's registry, resolves FIND-202), ALWAYS passing an explicit `env: {HOME: COORDINATOR_HOME, ANICCA_HOME: citizen.homeDir}` object — `COORDINATOR_HOME` imported from `registry-path.mjs` (resolves FIND-701, see PROP-403f), never independently sourced — assert pairwise inequality. **Corrected, resolves FIND-501:** with the corrected seed values, `resolveEvmPrivateKey({home: '/Users/anicca/.anicca', env: {HOME: COORDINATOR_HOME, ANICCA_HOME: '/Users/anicca/.anicca'}})` (automaton; `COORDINATOR_HOME` resolves to `/Users/anicca` on this host, confirmed live via `os.homedir()`, 2026-07-07) resolves via `resolve-identity.mjs`'s own existing legacy-fallback branch to `/Users/anicca/.automaton/wallet.json` — CONFIRMED PRESENT on disk, 2026-07-07, content never read/printed — and `resolveSolanaSecret({home: '/Users/anicca/.blockrun', env: {HOME: COORDINATOR_HOME, ANICCA_HOME: '/Users/anicca/.blockrun'}})` (Franklin) resolves via the symmetric legacy-fallback branch to `/Users/anicca/.blockrun/.solana-session` — CONFIRMED PRESENT on disk, 2026-07-07 — BOTH non-null, proving this check actually reads real key material; the PRIOR bare-`$HOME` seed value resolved `null` for both citizens on every chain (independently re-derived from the module's own gate: `effectiveHome === path.join(legacyHome,'.anicca')`/`.blockrun` both evaluate FALSE for the bare `/Users/anicca` value), which would have made this obligation vacuous. **Corrected, resolves FIND-603/FIND-701:** the invocation shape ITSELF is now always the explicit-`env` form above using the canonical `COORDINATOR_HOME` constant, never the bare `{home: X}` shape a prior revision used (which silently depended on the AUDIT SCRIPT's own ambient `process.env.HOME`), and never an independently-hardcoded/independently-`os.homedir()`-read HOME value (which would have reintroduced the identical ambient-coupling hazard one layer up). Corrected (resolves FIND-303/FIND-703): this obligation does NOT extend to Tier 3 and does NOT require "at least one newly-spawned child" this increment — `resolve-identity.mjs`'s resolvers are a pure local-filesystem primitive that structurally cannot reach a REQ-301-mandated remote child's own disk, and this feature never transmits a child's private key over the network for comparison; a cloud-hosted child (`coLocatedWithCoordinator: false`, by REQ-305) is structurally excluded from this obligation's candidate set until a future increment adds a genuine remote-audit mechanism (PROP-403d) |
| PROP-403c | REQ-403 | A deliberately-injected fixture where two fake instances (both `coLocatedWithCoordinator: true`) share a `HOME` is correctly flagged as a collision by the audit (negative-test / audit-is-not-vacuous check) | 1/2 | true | unit/integration test: two fixture "instances" with an identical `HOME` value → assert the audit reports a collision, proving the check would actually catch a real one |
| PROP-403d | REQ-403 | REQ-403's live pairwise-key-comparison check is invoked only for instances whose registry record has `coLocatedWithCoordinator === true` (resolves FIND-703 — a real, checkable registry field, never an implicit/undefined enumeration); no code path in this feature's diff invokes `resolveEvmPrivateKey`/`resolveSolanaSecret` against a record with `coLocatedWithCoordinator === false` (structurally, every cloud-hosted spawned child's `homeDir`), and this exemption is documented in the spec as a known limitation of this increment, not silently assumed | 0 | true | structural/Tier-0 check: read the audit script's enumeration source and confirm its live-comparison input list is constructed via `citizens.filter(c => c.coLocatedWithCoordinator === true)` — never any other predicate — so it structurally can never include a `coLocatedWithCoordinator: false` record (resolves FIND-703, replaces the pre-FIND-703 check which had no real field to key on), while the static grep-sweep half (step (1)) is confirmed to run against the whole fleet (resolves FIND-303) |
| PROP-403e | REQ-403 | The live-audit invocation ALWAYS passes an EXPLICIT, fully-constructed `env` object to `resolveEvmPrivateKey`/`resolveSolanaSecret` (`{HOME: COORDINATOR_HOME, ANICCA_HOME: citizen.homeDir}`) — NEVER a bare `{home: X}` call that silently depends on the invoking process's own ambient `process.env.HOME` happening to be correct (resolves FIND-603: `resolve-identity.mjs`'s real legacy-fallback gate reads a SECOND, separate `env.HOME`/ambient `process.env.HOME` input the prior spec text never modeled, and the module's own reused test suite never exercises the bare `{home: X}`-only shape — every one of its 20 cases passes an explicit `env.HOME` alongside `home`/`ANICCA_HOME`) | 0/2 | true | Tier 0: structural read of the audit script's source confirms every `resolveEvmPrivateKey`/`resolveSolanaSecret` call site passes an explicit `env` object literal (never a bare `{home: X}` call, never an implicit fallthrough to `process.env`); Tier 2: integration test simulating a stripped/launchd-style minimal `process.env` (e.g. `{PATH: '/usr/bin:/bin'}`, deliberately omitting `HOME`) as the AMBIENT environment the audit script itself runs under, then asserting the audit still correctly resolves both citizens' real, non-null key material — proving the explicit-`env` invocation makes the result independent of the audit script's own ambient environment |
| PROP-403f | REQ-403 | EVERY call site in the implementation's REQ-403 live-audit script that supplies an `env.HOME` value to `resolveEvmPrivateKey`/`resolveSolanaSecret` imports and passes the SAME exported `COORDINATOR_HOME` constant from `registry-path.mjs` — never an independently hardcoded literal string, and never an independent `os.homedir()`/`process.env.HOME` read at the call site (resolves FIND-701 — mirrors PROP-103d's structural discipline exactly for the analogous coordinator-HOME hazard) | 0 | true | structural/Tier-0 check: source-grep or import-identity check across the diff confirming a single import site for `COORDINATOR_HOME` in this feature's audit-script code path, and ZERO occurrences of `os.homedir()`/`process.env.HOME` anywhere else in that same code path (resolves FIND-701) |

## Verification Strategy

- **Tier 0** (no runtime execution of the audited code): REQ-104's structural no-LLM/no-scoring
  check (PROP-104a); REQ-105's registry-shape structural check (PROP-105a, structural half, now
  `telemetryPath`-free AND `coLocatedWithCoordinator`-typed, resolves FIND-302/FIND-703), seed-purity
  structural check (PROP-105d, structural half), already-resolved-path structural check (PROP-105e,
  resolves FIND-202, and confirms zero `telemetryPath` occurrences, resolves FIND-302), STRUCTURAL half
  of its walletAddress-verification-method check (PROP-105g, resolves FIND-601/FIND-702/FIND-801 —
  confirms a real re-derivation script/test exists COVERING BOTH the EVM and Solana branches and is
  wired to Phase 3; the binding re-derivation itself is Tier 2, below) AND its dual-branch-conjunctive
  structural check (PROP-105i, structural half, resolves FIND-801), and its `coLocatedWithCoordinator`
  seed-schema check (PROP-105h, structural half,
  resolves FIND-703); its seed-template-never-written structural check (PROP-105j, resolves FIND-901
  — critical) AND the structural half of its durable-out-of-git-tree-path check (PROP-105k, structural
  half, resolves FIND-901 — confirms `CITIZENS_REGISTRY_PATH`'s construction always routes through
  `resolveStateDir`, never a literal in-tree path; the binding live-git-operation test is Tier 2,
  below); its atomic-exclusive-create bootstrap structural check (PROP-105l, structural half, resolves
  FIND-1001 — critical — confirms the bootstrap step is a single `fs.open(..., 'wx')`-equivalent call,
  never a separate exists-check-then-write pair; the binding concurrent-race/late-append fixtures are
  Tier 2, below) AND `registry-path.mjs`'s corrected "Effectful Shell" classification's structural check
  (PROP-105m, structural half, resolves FIND-1002 — confirms `COORDINATOR_HOME` is implemented as a
  direct `os.homedir()` call, never a hardcoded literal or `process.env.HOME` substitute; the binding
  real-environment-dependent test is Tier 2, below); REQ-106's single-coordinator-host entry-point
  check and scope-statement check (PROP-106a/b); REQ-103's canonical-`statePath` import-identity
  check (PROP-103d, resolves FIND-103); a structural check that `ledger.js` remains exactly
  `{readChildren, appendChild}` (no update/upsert primitive added, resolves FIND-301); REQ-201's
  private-key-handling structural check (PROP-201c, structural half); REQ-202's `initialSkills`
  never-hardcoded structural check (PROP-202e, new, resolves FIND-1601, critical — confirms
  `initialSkills` is passed through from the SAME upstream agent-chosen value used for the child's own
  goal-framing/prompt, never a literal/hardcoded skill-list constant); REQ-203's
  explicit-env-injection structural check (PROP-203c); REQ-204's gas-seed-sizing structural check
  (PROP-204b, structural half); REQ-205's `mcp.json` shape check (PROP-205a); REQ-206's
  structural-diff-limited-to-anchor-validation check (PROP-206d), fixed-`generation`-value
  structural check (PROP-206g, structural half, resolves FIND-204), and the
  `wallet`-field-cross-assignment structural check (PROP-206h, resolves FIND-304); REQ-301's
  post-attempt-artifact structural check (PROP-301a); REQ-303's unmodified-script-reuse structural
  check (PROP-303a); REQ-304's no-human-funded-source structural check (PROP-304a) AND its
  Base-native-entry Skip API route confirmation (PROP-304e, resolves FIND-502); REQ-305's
  ledger-status-completeness structural check (PROP-305a) AND its
  `coLocatedWithCoordinator`-always-`false`-on-append structural half (PROP-305f, resolves FIND-703);
  REQ-306's zero-I/O pure-function check
  (PROP-306d); REQ-401's ledger-schema structural check (PROP-401b); REQ-402's no-effect-on-REQ-102
  structural check (PROP-402d, resolves FIND-203) AND its `BOOTSTRAP_WINDOW_DAYS`/`SPAWN_COOLDOWN_DAYS`
  identity structural half (PROP-402e, structural half, new, resolves FIND-1301); REQ-403's static grep sweep against the real
  current tree, now confirmed to cover a cloud-hosted child's deployed source too (PROP-403a,
  resolves FIND-303), its `coLocatedWithCoordinator===true`-enumeration structural check (PROP-403d,
  resolves FIND-303/FIND-703 — now a real, checkable field-filter, not an implicit notion), its
  explicit-env-invocation structural half (PROP-403e, resolves FIND-603), and its
  `COORDINATOR_HOME`-import-identity structural check (PROP-403f, resolves FIND-701 — mirrors PROP-103d
  exactly).
- **Tier 1** (pure-function unit tests): REQ-101's aggregation (PROP-101a/b/c, PROP-101c now
  covering a public-RPC query failure rather than a local file read, resolves FIND-302) AND its new
  `filterProductiveCitizens` join, INCLUDING its last-write-wins duplicate-`child_id` reduction
  (PROP-101d, resolves FIND-201/FIND-301) AND its per-chain-independent fail-closing fixture for a
  dual-wallet citizen with exactly one chain failing (PROP-101g, resolves FIND-503) AND its
  dual-wallet-both-chains-fail-simultaneously fixture (PROP-101h, resolves FIND-604); REQ-102's gate
  (PROP-102a-e, PROP-102b corrected to test the reconciled success-vs-failure-cap cooldown rule,
  resolves FIND-1101) AND its new `countChildrenProvisioning` four-case fixture (PROP-102h, resolves
  FIND-1501) AND its new `deriveMeasuredShelterCostUsd` empty/single/multi-entry-last-write-wins
  fixture (PROP-102j, resolves the sweep-found sibling gap alongside FIND-1501); REQ-103's reused
  `isLockStale` wiring (PROP-103b/c, reusing the already-proved upstream fixtures); REQ-105's
  malformed-record-exclusion check (PROP-105b), direct seed-data-passes-`isSelfFunded()` assertion
  (PROP-105c, resolves FIND-101), seed-purity unit check (PROP-105d, unit half),
  `homeDir`-never-passed-to-`isSelfFunded()` check (PROP-105f, resolves FIND-202), and
  `coLocatedWithCoordinator`-seed-values-both-`true` unit check (PROP-105h, unit half, resolves
  FIND-703); REQ-201/202's
  collision/conditional-generation checks (PROP-201b, PROP-202a/c); REQ-203's pre-generation
  distinctness check (PROP-203a); REQ-204's defensive already-registered check (PROP-204c, unit
  half); REQ-205's state-path-uniqueness check (PROP-205b); REQ-206's identity-anchor validation
  (PROP-206a/b/c — both accepted paths and both rejection paths — AND PROP-206e, the
  both-anchors-present accepted path, resolves FIND-102) AND its `seedUsdc`-aliasing/
  `generation`-fixed-at-`1` fixture (PROP-206g, unit half, resolves FIND-204); REQ-302's
  own-home-isolation check (PROP-302a, unit half); REQ-304's amount-ceiling and
  individual-insufficiency checks (PROP-304b/c) AND its multi-citizen co-funding SUCCESS-path check
  (PROP-304f, unit half, resolves FIND-1102, distinct from PROP-304c's blocked/no-op path — its
  per-citizen ceiling half now reading REQ-101's PROP-101i-proved `computePerCitizenSurplusUsd`,
  resolves FIND-1202); REQ-305's
  cooldown-cap check (PROP-305c, corrected resolves FIND-1101) AND its exact-boundary check (PROP-305g,
  new, resolves FIND-1101) and
  isSelfFunded-refusal-before-append check (PROP-305e, unit half, resolves FIND-101); REQ-306's
  price-ordering, tie-breaker, and availability-branch checks (PROP-306a/b/c) AND its new
  price-fetch fail-closed check (PROP-306e, unit half, resolves FIND-305); REQ-303's Akash-readiness-gate
  reuse check (PROP-303d, unit half — reuses `spawn-child/lib/akt-cost-gate.js`'s own already-existing
  unit tests as already-sufficient arithmetic proof, resolves FIND-402); REQ-402's
  window-boundary relabeling and exclusion checks (PROP-402a/c, now read from `ledger.js` rows via a
  NEW `appendChild` row rather than a mutation, resolving FIND-201/FIND-405) AND its
  `BOOTSTRAP_WINDOW_DAYS`/`SPAWN_COOLDOWN_DAYS` identity unit check (PROP-402e, unit half, new, resolves
  FIND-1301); REQ-403's negative-test
  collision-detection check (PROP-403c, unit half).
- **Tier 2** (integration, real module wiring + fresh-context adversary disk review, no live
  chain/cloud spend required): REQ-101's real orchestration binding of `filterProductiveCitizens`'s
  `ledgerRows`/`citizens` arguments to `readChildren(...)`'s real output and a real
  `CITIZENS_REGISTRY_PATH` read, respectively, never hand-assembled at the call site, with
  `computeColonySurplusUsd`/`readCitizenBalances` confirmed to receive that SAME filtered array
  unchanged (PROP-101j, new, resolves the sweep-found sibling gap alongside FIND-1601); REQ-102's real
  orchestration binding of `colonySurplusUsd` to THAT SAME evaluation's real `computeColonySurplusUsd({
  citizens: filterProductiveCitizens(...), perCitizenReserveUsd})` return value, never hand-assembled and
  never a stale/earlier evaluation's cached aggregate reused across multiple evaluations within one wake
  (PROP-102k, new, resolves FIND-1701, critical); REQ-101's
  registry-driven, host-location-agnostic
  `readCitizenBalances` check (PROP-101e, resolves FIND-302) AND its dual-chain summing check
  (PROP-101f, integration half, resolves FIND-404) AND its per-chain-independent fail-closing check
  (PROP-101g, integration half, resolves FIND-503) AND its dual-wallet-both-fail integration check
  (PROP-101h, integration half, resolves FIND-604); REQ-105's walletAddress-verification-method check,
  BINDING RE-DERIVATION half, TWO-BRANCH (PROP-105g, integration half, resolves FIND-702/FIND-801 —
  the EVM branch: an actual real script/test that reads the real private-key file in memory, computes
  the address via `privateKeyToAccount`, and diffs it against `citizens.json`'s stored
  `walletAddress.evm`, failing hard on mismatch; the Solana branch, corrected resolves FIND-801: an
  actual real script/test that reads the real secret file in memory, `bs58.decode()`s it to a 64-byte
  secret, computes the address via `Keypair.fromSecretKey(...).publicKey.toBase58()`, and diffs it
  against `citizens.json`'s stored `walletAddress.solana`, failing hard on mismatch — LIVE-CONFIRMED,
  2026-07-07, against Franklin's real `~/.blockrun/.solana-session`, exact match) AND its
  dual-populated-citizen conjunctive-pass check (PROP-105i, integration half, resolves FIND-801 — both
  branches must independently match; either branch's mismatch fails the whole check) AND its
  durable-out-of-git-tree live check (PROP-105k, live half, resolves FIND-901 — critical: write a
  fixture record to the real `CITIZENS_REGISTRY_PATH`, perform a real `git checkout`/`git worktree add`/
  `git pull` on `~/anicca`, re-read the durable file and confirm the fixture record is byte-identical,
  and confirm a `git status`/`git diff` immediately after a real REQ-305 append shows zero working-tree
  changes) AND its atomic-exclusive-create bootstrap live check (PROP-105l, live half, resolves
  FIND-1001 — critical: the concurrent-race fixture — two simulated first-access callers race the
  bootstrap exclusive-create, exactly one succeeds and the other fails `EEXIST` and reads-only — and the
  late-bootstrap-after-real-append fixture — a real REQ-305 append completes before a simulated late
  bootstrap attempt's exclusive-create call, which fails `EEXIST` and leaves the already-appended record
  byte-identical/untouched) AND its `COORDINATOR_HOME` real-environment-coupling live check (PROP-105m,
  live half, resolves FIND-1002 — a real child process launched with a different real `HOME` value
  resolves its OWN `COORDINATOR_HOME` to ITS OWN `os.homedir()` output, never the original coordinator
  host's cached value, proving genuine Effectful environment-coupling rather than an assumed-pure
  constant); REQ-302's
  post-boot Nosana secrets-injection check
  (PROP-302c, integration half, resolves FIND-401's Nosana-side analog); REQ-303's post-lease-active
  Akash secrets-injection check (PROP-303e, integration half, resolves FIND-401); REQ-103's concurrent-attempt race
  (PROP-103a) and crashed-holder reclaim (PROP-103b, integration half); REQ-201's real
  600-perm/own-home file check (PROP-201c, integration half); REQ-202's zero-invocation-when-unneeded
  check (PROP-202b) AND its `deployTarget` real-derivation binding check — confirming a real/fixture
  `selectCloudTarget(...)` call's return value is passed directly into `needsSolanaWallet`'s
  `deployTarget` for that SAME attempt, never a stale/earlier evaluation (PROP-202d, new, resolves
  FIND-1601, critical); REQ-203's cross-instance `resolve-identity.mjs` non-leak test (PROP-203b);
  REQ-204's gas-seed-amount integration check (PROP-204b, integration half) and already-registered
  defensive check (PROP-204c, integration half); REQ-206's real full-seven-field `buildChildSpec`
  call (PROP-206f, resolves FIND-204); REQ-302's own-home-isolation integration check (PROP-302a,
  integration half); REQ-303's shelter-cost-ledger feedback check, now naming
  `deriveMeasuredShelterCostUsd`/`readShelterCostEntries` directly rather than an unnamed threshold
  computation (PROP-303c, corrected, resolves the sweep-found sibling gap alongside FIND-1501); REQ-304's multi-citizen
  sequential co-funding SUCCESS-path integration check (PROP-304f, integration half, resolves
  FIND-1102, distinct from PROP-304c's blocked/no-op path — its per-citizen ceiling half reading
  REQ-101's PROP-101i-proved `computePerCitizenSurplusUsd`, resolves FIND-1202); REQ-305's
  failure-injection-at-each-step test (PROP-305b), registry-append-on-success test (PROP-305d, now
  also asserting `active_since` is set on the ledger row and `homeDir` is pre-resolved on the
  registry row — no `telemetryPath` field to assert on, resolving FIND-201/202/302),
  isSelfFunded-refusal-before-append check (PROP-305e, integration half), and
  `coLocatedWithCoordinator`-always-`false`-on-append integration half (PROP-305f, resolves FIND-703);
  REQ-306's price-fetch
  fail-closed check (PROP-306e, integration half); REQ-402's late-success retroactive-correction test
  (PROP-402b); REQ-403's live pairwise-key check across real instances whose registry record has
  `coLocatedWithCoordinator === true` only, scoped this
  increment and now proven against each citizen's own corrected, distinct `homeDir` and the canonical
  `COORDINATOR_HOME` constant (PROP-403b,
  resolves FIND-303/FIND-501/FIND-701/FIND-703), and negative-test collision-detection integration half (PROP-403c);
  AND its stripped/launchd-style-environment integration half proving the explicit-`env` invocation is
  environment-independent (PROP-403e, integration half, resolves FIND-603).
- **Tier 3** (live, no-mock E2E against real/testnet-first chain and cloud state, HARD RULE 0.24):
  REQ-204's real `register()` call (PROP-204a); REQ-302's real Nosana job deploy (PROP-302b) AND its
  real post-boot secrets-injection delivery (PROP-302c, E2E half, resolves FIND-401); REQ-303's real
  Akash lease deploy (PROP-303b) AND its real post-lease-active secrets-injection delivery (PROP-303e,
  E2E half, resolves FIND-401); REQ-304's real multi-hop AKT funding-route execution (PROP-304d, E2E
  half, resolves FIND-402); REQ-401's independently-re-verified real gig
  settlement by the spawned child itself (PROP-401a). **REQ-403's live pairwise-key check does NOT
  extend to Tier 3 this increment** (resolves FIND-303/FIND-703: PROP-403b is Tier-2, scoped to exactly
  the `coLocatedWithCoordinator===true` set, by
  design — no cloud-hosted child is ever a member of that set, so it is never included in it this
  increment; see PROP-403d). **Per the
  Tier-3 policy stated above, a testnet/sandbox-first pass is an acceptable precursor, but this
  increment's completion requires at least one real mainnet-class result for REQ-204, REQ-302 or
  REQ-303 (whichever cloud path is actually used for the completing spawn), and REQ-401 —
  mirroring SPEC.md §9.9's own correction that only a mainnet-class settlement counts as the actual
  witness.**

## Gate

Phase 3 (adversarial review) must confirm, via fresh-context, disk-only review plus (for the Tier-3
items) live re-execution performed by the adversary itself:

(1) REQ-101/102's arithmetic is read end-to-end confirming: the self-funded filter (`isSelfFunded`)
gates the aggregation exactly as REQ-101 specifies with no human-funded wallet leaking in
(PROP-101b), the threshold comparison is inclusive at the boundary (PROP-102a), the cooldown check
is never bypassed by surplus size for EITHER cooldown trigger — a success in-window, or the
`FAILURE_COOLDOWN_CAP` reached in-window (PROP-102b, corrected, resolves FIND-1101 — the adversary
confirms `decideColonySpawn`'s `recentSpawnAttempts` array-scan implements the SAME reconciled rule
REQ-102's own EARS clause and REQ-305's failure-cap edge case both now describe, never two competing
behaviors), and the check ORDER matches REQ-102's specified surplus→cooldown→cap sequence (PROP-102e)
— a control-flow read, not merely an outcome check; AND — resolves the sweep-found sibling gap
alongside FIND-1501 — that `spawnThresholdUsd`'s own `MIN_SHELTER_USD` override is read via the new
`deriveMeasuredShelterCostUsd({shelterCostLedgerRows: readShelterCostEntries(...)})`, returning `null`
(hence the `5.00` default) on an empty shelter-cost ledger and, once entries exist, ONLY the
LAST-appended entry's `settledLeaseCostUsd` — never an average/max/first-entry read across the
ledger's accumulated history (PROP-102j); AND — resolves FIND-1701, critical — that `colonySurplusUsd`
itself (this function's own FIRST-listed parameter, and the single most consequential value it consumes)
is confirmed, by a control-flow read, to be the DIRECT return value of THAT SAME evaluation's real
`computeColonySurplusUsd({citizens: filterProductiveCitizens(...), perCitizenReserveUsd})` call, never a
hand-assembled or stale/earlier-evaluation's cached aggregate, AND that a SEPARATE such call is made for
EACH separate `decideColonySpawn` evaluation within one wake — the adversary explicitly confirms REQ-103's
`"colony-spawn"` lock is NOT relied upon (nor cited) as a substitute safety mechanism for this binding,
since that lock's own critical section begins only at REQ-201, strictly AFTER this evaluation step
already completes (PROP-102k);

(1a) REQ-105's colony citizen registry is read end-to-end confirming: the brand-new, dedicated
`citizens.json` (NOT `colony-wallets.json`, which this feature never touches — resolves FIND-101)
parses in the `{id, wallet: {evm?: boolean, solana?: boolean}, walletAddress: {evm?: string,
solana?: string}, fuel, humanDependencies, homeDir, coLocatedWithCoordinator: boolean}` shape — NO
`telemetryPath` field (removed, resolves FIND-302) — (PROP-105a, resolves FIND-104's
wallet/walletAddress split, FIND-202's `homeDir` addition, and FIND-703's `coLocatedWithCoordinator`
addition) and its fixed literal seed data passes `isSelfFunded()` directly for every entry
(PROP-105c — a straightforward fixture assertion, not an out-of-band comparison), that the seed set
contains ZERO entries that would fail `isSelfFunded()` and specifically excludes claude-p/any
human-funded wallet (PROP-105d), that `homeDir` is always an already-resolved absolute path, never
an unresolved `$HOME` template, and `telemetryPath` occurs zero times anywhere in the file (PROP-105e,
resolves FIND-202/FIND-302), that each entry's `homeDir` is that citizen's own REAL, DISTINCT
`ANICCA_HOME` root — automaton `/Users/anicca/.anicca`, Franklin `/Users/anicca/.blockrun` — never the
shared physical machine's bare `$HOME` an earlier revision wrongly seeded for both (resolves FIND-501:
the adversary independently confirms, against the real `resolve-identity.mjs` source, that these
corrected values resolve real, non-null key material, whereas the prior bare-`$HOME` value would have
resolved `null` for both citizens on every chain), that BOTH seeded entries carry
`coLocatedWithCoordinator: true` (PROP-105h, resolves FIND-703 — an accurate structural fact, not an
inference), a single malformed record never aborts aggregation
for other valid citizens (PROP-105b), that every seeded entry's `walletAddress` is INDEPENDENTLY
RE-DERIVED — never merely CITED, and never accepted via a live balance query alone — from real signing
key material, via the CORRECT chain-specific tool (PROP-105g, corrected TWO-BRANCH resolves FIND-801:
EVM entries via `viem::privateKeyToAccount` against `walletAddress.evm`; Solana entries via
`@solana/web3.js::Keypair.fromSecretKey` against `walletAddress.solana` — `viem` alone is EVM-only and
cannot cover Franklin's Solana-only record or any future Nosana-path child's Solana wallet, REQ-202)
— resolves FIND-601/FIND-702/FIND-801: the adversary must confirm an ACTUAL re-derivation script/test
was run for EVERY populated chain on a record (both, conjunctively, if both are populated — PROP-105i),
reading the real private-key/secret file in memory and diffing the computed address against the stored
`walletAddress.evm`/`walletAddress.solana` respectively, failing hard on mismatch — a commit/PR message
merely claiming the right kind of verification method, without the computation ever having been run,
does NOT satisfy this obligation; a live balance query alone likewise does NOT satisfy it (it does not
prove derivation-correctness) and may only ever be cited as additional corroboration, and
REQ-101/REQ-403 both read their citizen list from this SAME
registry — no second, undocumented citizen-enumeration mechanism exists anywhere in the diff;

(1b) REQ-101's new `filterProductiveCitizens` join is read end-to-end confirming it is the ONLY place
`status`/`active_since` cross the aggregation boundary — cross-referencing REQ-105's registry against
`ledger.js`'s own rows (matched by `id`===`child_id`), FIRST reducing any citizen with MULTIPLE
matching rows to its LAST-appended row (last-write-wins, resolves FIND-301 — `ledger.js` itself
remains exactly `{readChildren, appendChild}`, no update/upsert primitive added), THEN excluding
exactly the citizens whose (reduced) matching row is `"bootstrap_failed"` or
window-overdue-while-`"active"`, and passing through unfiltered any citizen with no matching row
(PROP-101d) — before `computeColonySurplusUsd` ever runs (resolves FIND-201's location contradiction
between REQ-105's registry and REQ-402's ledger-based lifecycle state), and that `citizens.json`
itself is confirmed, by a structural read, to carry NEITHER field — AND (new, resolves the sweep-found
sibling gap alongside FIND-1601) a control-flow read confirms `filterProductiveCitizens`'s own
`ledgerRows` argument is the DIRECT return value of a real `readChildren(...)` call and its `citizens`
argument is the DIRECT return value of a real `CITIZENS_REGISTRY_PATH` read — never hand-assembled or
independently reconstructed at the call site — and that `computeColonySurplusUsd`/`readCitizenBalances`
both receive this SAME filtered array unchanged, never a second, independent read (PROP-101j);

(1c) REQ-101's balance-lookup mechanism (`readCitizenBalances`) is read end-to-end confirming it is a
registry-driven, coordinator-run, PUBLIC-RPC query keyed on each citizen's `walletAddress` — a
generalization of `telemetry-collect.sh`'s own existing, already-proven hardcoded-3-instance
RPC-by-address pattern — and NOT a coordinator-local `fs.readFile` of any per-citizen path (PROP-101e,
resolves FIND-302); the adversary confirms this mechanism has no structural dependency on the
querying citizen being co-located with the coordinator, since a REQ-301-mandated cloud-hosted child
has no other way for its balance to reach REQ-101's aggregation;

(1d) REQ-101's dual-chain balance handling is confirmed for a citizen record carrying BOTH
`walletAddress.evm` AND `walletAddress.solana` populated (the expected Nosana-path shape, REQ-202):
`readCitizenBalances` sums both chains' independently-normalized USD balances into one total (PROP-101f)
— the adversary confirms this is a deliberate, documented design decision, never an unstated ambiguity
that an implementer could instead resolve as "pick one chain" or "treat as malformed" (resolves
FIND-404); AND that each chain fails closed INDEPENDENTLY — a mixed-fixture where exactly one chain's
query fails while the other genuinely succeeds with a real value produces a total equal to ONLY the
successful chain's value, never `0` for the whole citizen (PROP-101g, resolves FIND-503); AND that BOTH
chains failing simultaneously for one dual-wallet citizen produces exactly `0` for that citizen — never
a throw, `NaN`, or a double-subtracted reserve (PROP-101h, resolves FIND-604);

(1e) REQ-101's new `computePerCitizenSurplusUsd({citizens, perCitizenReserveUsd})` is confirmed to
return EACH citizen's own `max(0, balance_i - perCitizenReserveUsd)` term individually, and
`computeColonySurplusUsd`'s own source is read confirming it is implemented by CALLING this function
and summing its output — never an independently-written second reduce — so the aggregate and the
per-citizen breakdown are consistent BY CONSTRUCTION, never merely by two numbers happening to agree on
today's fixtures (PROP-101i, resolves FIND-1202, major); this is the exact function REQ-304's
per-citizen ceiling check (see item (7) below) binds to by name;

(1f) REQ-102's new `deriveRecentSpawnAttempts({ledgerRows})` is confirmed to be the SOLE mechanism that
produces `recentSpawnAttempts` — a control-flow read confirms `decideColonySpawn`'s caller passes this
function's return value directly, never a hand-rolled reimplementation of the join at the call site
(PROP-102g); the adversary independently re-derives, against real/fixture `ledger.js` rows, that a
`child_id` group is mapped to exactly ONE `{ts, outcome}` entry across all four real cases — a plain
failure, a plain success, a success-THEN-`"bootstrap_failed"` attempt that remains `outcome:"success"`
with its ORIGINAL `attempted_ms` and is never ALSO counted as a second, extra failure entry, and an
in-flight `"provisioning"`-only attempt that is excluded entirely (PROP-102f, resolves FIND-1401,
critical) — AND confirms `attempted_ms` itself is set once, on the FIRST `ledger.js` row for a
`child_id`, and copied forward unchanged onto every later row for that SAME `child_id`, including
REQ-402's `"bootstrap_failed"` row, never a freshly-generated timestamp on a follow-up row (PROP-305h);

(1g) REQ-102's new `countChildrenProvisioning({ledgerRows})` is confirmed to be the SOLE mechanism that
produces `childrenProvisioning` — a control-flow read confirms `decideColonySpawn`'s caller passes this
function's return value directly, never a hand-rolled reimplementation of the count at the call site
(PROP-102i); the adversary independently re-derives, against real/fixture `ledger.js` rows, that a
`child_id` group is counted if and only if its LAST (last-write-wins) row's `status` is EXACTLY
`"provisioning"` — a group whose last row is `"active"`, `"failed"`, or `"bootstrap_failed"` is NEVER
counted, even when an EARLIER `"provisioning"` row exists for that same `child_id` (PROP-102h, resolves
FIND-1501, critical) — closing the identical double-counting/permanent-spawn-block hazard item (1f)
above already closed for `recentSpawnAttempts`;

(2) REQ-103's mutual exclusion is proven under a deliberately-induced concurrent race (two
simultaneous `eligible:true` evaluations), confirming exactly one proceeds and the other logs
`reason:"lock_held"` with zero wallet-generation side effects (PROP-103a), AND that the
`"colony-spawn"` lock key is genuinely wired through the EXISTING, already-hardened `lock.mjs`
module rather than a fresh reimplementation (control-flow read, not a grep for the word "lock"), AND
that EVERY call site acquiring this lock imports and passes the SAME exported
`CITIZENS_REGISTRY_PATH` constant as its `statePath` argument, never an independently hardcoded path
string (PROP-103d, resolves FIND-103 — a source-grep/import-identity check the race test above
cannot by itself provide), AND — resolves FIND-1201, critical — that the lock remains HELD across its
ENTIRE critical section (REQ-201 through REQ-304's funding call through REQ-305's ledger append
actually completing), never released any earlier, proven under a STAGGERED (non-simultaneous) race
where a first evaluator's REQ-304 funding call is deliberately delayed and a second evaluator's
repeated lock-acquire attempts throughout that entire delay window all fail, succeeding only after the
first evaluator's REQ-305 append has landed (PROP-103e) — this is confirmed IN ADDITION to PROP-103a's
simultaneous-race fixture, since a simultaneous race alone cannot prove the lock is not released early
somewhere between REQ-206 and REQ-305;

(2a) REQ-106's single-coordinator-host scope constraint is confirmed structurally: `lock.mjs`'s and
`ledger.js`'s acquire/read/write paths are invoked from exactly one designated coordinator-host code
entry point with no path reachable from a cloud-deployed child's own runtime (PROP-106a), and this
spec's own scope section states spawn chaining is out of scope (PROP-106b) — the adversary does
NOT need to (and must not be asked to) prove cross-host correctness for this increment, since
REQ-106 makes that topology explicitly out of scope;

(3) REQ-104's design constraint holds — no LLM/prompt/scoring code exists anywhere in
`computeColonySurplusUsd`/`decideColonySpawn`'s diff (PROP-104a), matching the identical
`anicca-agent-economy` REQ-203 precedent this feature explicitly follows;

(4) REQ-201-205's identity-generation chain is read end-to-end confirming: the sha256-fallback
address is detected and rejected rather than silently used (PROP-201a), every generated
key/address is checked for distinctness against ALL existing citizens (not just one parent)
before use (PROP-201b/PROP-202c), the `$HOME`/`ANICCA_HOME` distinctness check runs BEFORE any
key generation (PROP-203a), the cross-instance `resolve-identity.mjs` non-leak property holds for
a genuinely new third home directory (PROP-203b), `gen-wallet.sh`/`deploy-akash.sh`/
`akt-treasury.sh` are reused with zero source modification (PROP-201/303's structural checks),
REQ-204's identity registration is invoked via the existing `ensureAgentId` wrapper rather than a
freshly-derived defensive check (PROP-204c), and the written `mcp.json` + `GIG_STATE_PATH` are
structurally distinct from every existing citizen's own config (PROP-205a/b) — AND (new, resolves
FIND-1601 — this item previously never cited ANY of REQ-202's own proof obligations at all) REQ-202's
`needsSolanaWallet` conditional is confirmed correct across all three trigger branches (PROP-202a) and
never invokes Solana keygen when unneeded (PROP-202b), with a control-flow read confirming its
`deployTarget` argument is the DIRECT return value of THAT SAME spawn attempt's real `selectCloudTarget(...)`
call, never hand-assembled or a stale/earlier attempt's evaluation (PROP-202d), and its `initialSkills`
argument confirmed to be the SAME value the spawning agent already chose per REQ-104's own
agent-judgment carve-out, never hardcoded/defaulted inside REQ-202's own orchestration (PROP-202e);

(4a) REQ-206's `buildChildSpec` identity-anchor extension is confirmed backward-compatible: the
existing `childInbox`-only regression fixture passes unchanged (PROP-206a), the new
`agentEvmAddress`+`agentId`-only path succeeds and is what this feature's own children actually use
(PROP-206b), both "missing anchor" rejection paths still throw (PROP-206c), BOTH anchors present
simultaneously is ACCEPTED, not rejected as an XOR violation (PROP-206e, resolves FIND-102's
EARS/edge-case self-contradiction), and a structural diff confirms the change touched ONLY the
required-field validation and returned-row field list — never `nextChildId` or the distinct-wallet
assertion (PROP-206d) — this is the control-flow read that replaces iteration 1's now-corrected
false "reused unmodified" claim (FIND-001); AND a real, full-seven-field `buildChildSpec` call
supplies concrete, spec-derived values for `parentWallet`/`generation`/`seedUsdc`/`constitutionHash`
(PROP-206f), with `seedUsdc` verified identical to REQ-204's actual gas-seed transfer amount and
`generation` verified fixed at `1` (PROP-206g) — resolves FIND-204; AND a structural read confirms
`buildChildSpec`'s returned-row `wallet` field (a string) is never cross-assigned with, or conflated
against, `citizens.json`'s differently-shaped `wallet` field (a boolean object, REQ-105) anywhere in
the implementation (PROP-206h, resolves FIND-304's cross-file naming collision);

(5) REQ-301's local-spawn-forbidden constraint holds — a real or simulated spawn attempt leaves no
persistent child-specific artifact on the initiating host (PROP-301a);

(6) REQ-302/303's cloud deploy paths are each proven live at least once (testnet/sandbox first pass
acceptable, but the increment's completion requires one real mainnet-class result per the Tier-3
policy) with independent re-verification of the resulting job/lease state via a SEPARATE query than
the deploying script's own stdout (PROP-302b/PROP-303b), and that neither path ever touches the
invoking host's own default key-storage directory when acting on a child's behalf (PROP-302a);

(6a) REQ-303's Akash-specific corrections (resolves FIND-401/402/403) are confirmed: the Akash-readiness
check calls the existing, unmodified `spawn-child/lib/akt-cost-gate.js::computeSpawnGate` (with
`spawn_cost_akt`/`buffer_akt` read from `spawn-child/config.json`) rather than a competing threshold
(PROP-303d); the ACTUAL rendered SDL used for a real deploy contains an explicit `HOME=/root` line —
the ORIGINAL `spawn-child/sdl/child.yaml`/`deploy-akash.sh` inline-default templates are confirmed,
by direct read, to lack it (PROP-303f); a NEW post-lease-active `provider-services lease-shell ...
--stdin` step delivers the child's own pre-generated wallet material onto the leased container, with
`deploy-akash.sh`/`akt-treasury.sh`'s own source confirmed byte-identical throughout — PROP-303a's
scope is correctly limited to those two script files, never the new SDL variant or injection step
(PROP-303e); and REQ-302's Nosana path has the identical post-boot secrets-injection property via
`nosana job ssh` (PROP-302c) — the adversary must confirm no code path claims the ORIGINAL,
pre-existing SDL/job artifacts already carried this capability (they do not);

(7) REQ-304's funding-source constraint is confirmed structurally (no human-funded wallet reference
anywhere in the funding code, PROP-304a) AND behaviorally (a funding attempt exceeding the
REQ-102-certified amount is rejected, PROP-304b; an aggregate-sufficient-but-no-individual-sufficient
scenario correctly produces a no-op with no child record, PROP-304c) AND, for Akash's AKT requirement
specifically, that the REAL multi-hop route (`config.json`'s own `funding_route` field for the 4-hop
Skip API bridge itself, `SKILL.md`'s own separate documented sequence for the Solana-side Jupiter
SOL→USDC pre-step that feeds it — cited as TWO separate sources, never merged, resolves FIND-502's
over-attribution finding), followed by `akt-treasury.sh`'s existing mint step, is followed rather than
an unsupported same-chain single-transfer assumption — since neither current citizen's wallet natively
holds AKT (PROP-304d, resolves FIND-402); AND that the implementation correctly supports BOTH of this
route's real, Skip-API-confirmed entry points (`"solana"` for a Solana-native funder, `"8453"`/Base for
a Base-native funder — PROP-304e, resolves FIND-502) rather than hardcoding a Solana-only entry when
automaton's own Base-native surplus is the one actually funding a given spawn; AND that the
multi-citizen SEQUENTIAL co-funding SUCCESS path — two citizens' own sequential single-signer
transfers, neither alone sufficient, together landing the FULL required amount on the child wallet,
with BOTH transfers independently traceable in the funding ledger — is proven to actually SUCCEED, not
merely that the insufficient-funds case is blocked (PROP-304f, resolves FIND-1102, distinct from
PROP-304c) — AND that each individual transfer's ceiling check reads its own citizen's value from
REQ-101's `computePerCitizenSurplusUsd` output BY NAME, never a re-derived or re-summed aggregate value
(PROP-101i, resolves FIND-1202);

(8) REQ-305's no-partial-spawn guarantee is proven by injecting a failure at EACH step in the chain
in turn and confirming the resulting ledger row correctly identifies the failing step and is
excluded from REQ-101's next aggregation (PROP-305b), that the failed-attempt cooldown-cap closes
the "engineer repeated failures to bypass cooldown" gap (PROP-305c, corrected, resolves FIND-1101 —
confirmed to be the IDENTICAL reconciled rule REQ-102's own PROP-102b tests from the success side,
never two different behaviors) — proven at the EXACT boundary, fewer than the cap → still eligible,
the cap reached → rate-limited (PROP-305g, resolves FIND-1101) — that a SUCCESSFUL spawn (and
only a successful one) appends a new record to REQ-105's registry (PROP-305d), that the
append path itself calls `isSelfFunded()` on the new record BEFORE appending and refuses the append
(zero write) if it returns `false` (PROP-305e, resolves FIND-101's permanent-hazard-closure
requirement), AND that every REQ-305 append sets the new record's `coLocatedWithCoordinator` field to
EXACTLY `false` — never `true`, never a computed value — since REQ-301's own absolute mandate makes a
co-located spawned child structurally impossible this increment (PROP-305f, resolves FIND-703);

(8a) REQ-306's cloud-target selection is confirmed deterministic and bookkeeping-only: the
price-ordering and tie-breaker branches are read end-to-end confirming no model/LLM call anywhere in
`selectCloudTarget`'s diff (PROP-306a/b/d), and the availability-fallback branches are proven for
both single-provider-unavailable cases and the both-unavailable `"none"` case (PROP-306c) — this
resolves FIND-006's previously-unspecified selection step; AND the USD-normalization price-fetch step
feeding it is confirmed to be a genuinely NEW, minimal mechanism (one public spot-price API call per
native token, reusing the exact fail-closed pattern already established by `ethPrice()`/`solPrice()`
in this codebase) rather than the previously-claimed, nonexistent "already-available" `akt-treasury.sh`
oracle, and that it fails closed to `0` on any query error (PROP-306e) — this resolves FIND-305's
false-reuse claim;

(9) REQ-401's $0-bootstrap success criterion is proven with a REAL, independently-re-verified
on-chain settlement performed autonomously by the spawned child itself — the adversary must not
accept either trading party's own self-report, and must perform its own fresh balance read
(PROP-401a);

(10) REQ-402's bootstrap-timeout bookkeeping is proven at the boundary (exactly the children past
the window are relabeled, no others, reading `active_since`/`status` from `ledger.js`'s own rows —
PROP-402a) — the adversary confirms this relabeling is implemented as `appendChild`-ing a NEW row for
the same `child_id` (never an in-place mutation, since `ledger.js` remains exactly `{readChildren,
appendChild}`), and that this new row is correctly picked up as "the" effective row only because
REQ-101's own `filterProductiveCitizens` last-write-wins reduction reads it that way — a explicit
cross-reference, not an independently-assumed second reduction rule (resolves FIND-405) — and its
non-punitive, retroactive-correction property is proven for a late success
(PROP-402b), and its exclusion from REQ-101's aggregation while `"bootstrap_failed"` is confirmed to
run EXCLUSIVELY through `filterProductiveCitizens` (PROP-402c, resolves FIND-201), and that the
`children_bootstrap_failed` observability count has ZERO effect on REQ-102's pinned
`decideColonySpawn` signature or behavior (PROP-402d, resolves FIND-203's dangling data-flow claim);
AND — resolves FIND-1301, major — that `BOOTSTRAP_WINDOW_DAYS`'s configured value is read as, or
derived directly from, REQ-102's own `SPAWN_COOLDOWN_DAYS` constant (now `14` by that requirement's own
stated default) rather than an independently-declared literal that merely happens to also read `14`
today, and that a fixture changing `SPAWN_COOLDOWN_DAYS`'s configured value changes
`BOOTSTRAP_WINDOW_DAYS` identically alongside it (PROP-402e) — mirroring the SAME "identical by
construction, never merely close" discipline REQ-206's own `seedUsdc`/gas-seed-transfer-amount identity
check (item (4a) above) already establishes for a different cross-requirement value pair;

(11) REQ-403's wallet mutual non-interference audit is run BY THE ADVERSARY ITSELF against the
real, current tree: the STATIC grep-sweep half covers zero cross-instance path references across the
WHOLE fleet, including a cloud-hosted child's deployed source since it boots from the same
git-cloned repo (PROP-403a, resolves FIND-303), and, once ≥ 2 real instances whose registry record has
`coLocatedWithCoordinator === true` exist (enumerated from REQ-105's registry via that exact field —
resolves FIND-703, never an implicit/undefined "co-located" notion — and via its CORRECTED, DISTINCT
`homeDir` field — resolves FIND-202
and FIND-501, NEVER the bare, shared `$HOME` an earlier revision wrongly seeded), the LIVE-comparison
half is run against exactly that filtered set only (pairwise key inequality, PROP-403b) — **the
adversary must confirm each citizen's corrected `homeDir` actually resolves that citizen's REAL,
non-null key material via `resolve-identity.mjs`'s own existing legacy-fallback branch (never `null`,
which the prior bare-`$HOME` seed value would have produced for both citizens on every chain — resolves
FIND-501), that this live half's enumeration is genuinely keyed on `citizens.filter(c =>
c.coLocatedWithCoordinator === true)` — a real, checkable structural filter, not an implicit notion
(resolves FIND-703) — and that it does NOT
require, or attempt to include, a cloud-hosted spawned child, which is structurally excluded because its
own registry record's `coLocatedWithCoordinator` is `false` (PROP-403d, resolves FIND-303/FIND-703:
`resolve-identity.mjs`'s resolvers are a pure local-filesystem primitive that cannot reach a remote
child's disk, and this feature never transmits a child's private key over the network)** — **the
adversary additionally confirms every one of those live-comparison invocations passes an EXPLICIT,
fully-constructed `env` object (`{HOME: COORDINATOR_HOME, ANICCA_HOME}`), never a bare `{home: X}` call relying on the
audit script's own ambient `process.env.HOME` (PROP-403e, resolves FIND-603), including under a
deliberately-stripped/launchd-style minimal `process.env` fixture** — **the adversary further confirms
that EVERY call site supplying this `env.HOME` value imports and uses the SAME `COORDINATOR_HOME`
constant exported from `registry-path.mjs` (the identical module REQ-103's `CITIZENS_REGISTRY_PATH`
already lives in), computed via `os.homedir()` at module-load time, with ZERO independent
`os.homedir()`/`process.env.HOME` reads or hardcoded literals anywhere else in the audit-script code
path (PROP-403f, resolves FIND-701 — mirrors PROP-103d's structural discipline exactly)** — and the
audit's own negative-test collision-detection is confirmed non-vacuous (PROP-403c) before its "zero
findings" result on the real tree is trusted.

Any single BLOCKING finding under (1)-(11) (including sub-items 1a/1b/1c/1d/2a/4a/6a/8a) fails this
Gate; Phase 4 (implementation) may not be marked complete until all findings are resolved and a fresh
adversary pass confirms PASS, per this project's strict-mode VCSDD discipline (no postponement).
