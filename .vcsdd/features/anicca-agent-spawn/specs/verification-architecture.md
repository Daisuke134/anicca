# Verification Architecture — anicca-agent-spawn (Phase 1b)

**feature**: anicca-agent-spawn · **mode**: strict · **increment**: same as `behavioral-spec.md`
(P3 colony-treasury-gated cloud spawn + $0-bootstrap verification) · **日付**: 2026-07-07 ·
**revision**: iteration 1 (first draft)

## Purity Boundary Map (file/function level)

| Layer | Location | Purity | Notes |
|---|---|---|---|
| **Pure Core (existing, reused unmodified)** | `~/anicca/skills/_shared/lib/is-self-funded.mjs::isSelfFunded`/`selfFundedReasons` | PURE | Already implemented, already unit-tested (`__tests__/is-self-funded.test.js`). REQ-101 calls this as-is to decide which citizens' balances even enter the aggregation; no new judgment logic. |
| **Pure Core (new)** | new module, e.g. `~/anicca/skills/self/spawn/lib/treasury-gate.mjs::computeColonySurplusUsd({citizens, perCitizenReserveUsd}) → number` | PURE (new) | Sum of `max(0, balance_i - reserve)` over `isSelfFunded()`-passing citizens only; zero I/O once given already-fetched balances. REQ-101's acceptance criteria. |
| **Pure Core (new, extends existing pattern)** | new module, same file, `decideColonySpawn({colonySurplusUsd, spawnThresholdUsd, lastSpawnAttemptMs, nowMs, cooldownDays, childrenProvisioning, maxConcurrentSpawns}) → {eligible, reason}` | PURE (new) | Directly analogous in shape/discipline to the existing `~/anicca/skills/self/spawn/lib/spawn-decision.js::decideSpawn` (same `{eligible, reason}` return, same "no I/O" contract, same ordered-checks style) but colony-aggregate-scoped rather than single-parent-scoped. REQ-102/103/104's acceptance criteria are enforced here. |
| **Pure Core (existing, reused unmodified)** | `~/anicca/skills/self/spawn/lib/child-spec.js::nextChildId`/`buildChildSpec` | PURE (existing) | Already implemented, already unit-tested (`__tests__/child-spec.test.js`); reused unmodified for REQ-201-205's child ledger row, including its existing distinct-wallet assertion (`buildChildSpec` already throws on `childWallet === parentWallet` — REQ-201 generalizes the CALLER's pre-check to "distinct from ALL citizens," but the constructor's own single-parent check is untouched). |
| **Pure Core (existing, reused unmodified)** | `~/anicca/skills/economy/gig/lib/lock.mjs::isLockStale(nowMs, mtimeMs, staleMs)` | PURE (existing, adversary-hardened) | Already extracted and Tier-1-tested as part of `anicca-agent-economy`'s own REQ-101 (concurrency-hardening sprint). REQ-103 reuses this predicate — and the `acquire()`/`release()`/atomic-`fs.rename`-reclaim machinery built on it — under a NEW lock key (`"colony-spawn"`), not new lock logic. |
| **Effectful Shell** | new module, e.g. `~/anicca/skills/self/spawn/lib/colony-balances.mjs::readCitizenBalances()` | EFFECTFUL | Reads each known citizen's `state/telemetry.json` — same file/pattern `~/anicca/skills/economy/ubi/run.sh` already reads (`$HOME/.automaton/state/telemetry.json`, `$HOME/.blockrun/state/telemetry.json`). Feeds REQ-101's pure aggregator; itself performs no aggregation logic. |
| **Effectful Shell** | `~/anicca/skills/self/spawn/scripts/gen-wallet.sh` | EFFECTFUL (existing, reused unmodified) | `openssl`+`python3` subprocess, real entropy. REQ-201. |
| **Effectful Shell (new)** | new script, e.g. `~/anicca/skills/self/spawn/scripts/gen-solana-wallet.sh` | EFFECTFUL (new) | Ed25519/Solana-shaped analog of `gen-wallet.sh`; real entropy, same 600-perm/never-logged discipline. REQ-202. |
| **Effectful Shell** | env injection at process-launch boundary (cloud-init/SDL/job-definition for whichever of REQ-302/303 is used) | EFFECTFUL | Setting `HOME`/`ANICCA_HOME` at spawn time; the isolation PROPERTY it produces is what REQ-203 specifies. |
| **Effectful Shell (existing, reused unmodified)** | `~/anicca/skills/earn/lib/resolve-identity.mjs::resolveEvmPrivateKey`/`resolveSolanaSecret` | EFFECTFUL (existing, already fail-closed) | Already implements the exact HOME-gated, fail-closed-on-foreign-spawn resolution REQ-203/403 depend on; reused unmodified. |
| **Effectful Shell (existing, reused unmodified)** | `~/anicca/skills/economy/gig/lib/identity.mjs::registerIdentity`/`verifyIdentity` | EFFECTFUL (existing, live-verified 2026-07-07) | Real on-chain ERC-8004 `register()`/`ownerOf` calls against the already-live mainnet (`0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`, Base 8453) or testnet (`0xdc527768082c489e0ee228d24d3cfa290214f387`, Base-Sepolia 84532) registry. REQ-204. |
| **Effectful Shell (new, template reused)** | new file-write step producing `<child_home>/.blockrun/mcp.json` (or `.anicca/mcp.json`) | EFFECTFUL (new) | Copies the exact shape of the already-live `~/.blockrun/mcp.json`. REQ-205. |
| **Effectful Shell (new)** | new wrapper around the `nosana` CLI (`nosana job post ...`) | EFFECTFUL (new) | Real subprocess + real Solana-settled market transaction. REQ-302. Confirmed-current CLI per the re-verification table in behavioral-spec.md. |
| **Effectful Shell (existing, reused unmodified)** | `~/anicca/skills/self/spawn/scripts/deploy-akash.sh`, `~/anicca/skills/self/spawn/scripts/akt-treasury.sh` | EFFECTFUL (existing, already implemented against real sandbox-2 chain per those scripts' own inline evidence citations) | REQ-303 reuses both unmodified, substituting only `CHILD_ID`/SDL content. |
| **Effectful Shell (new)** | new funding-transfer step (single-signer, citizen-wallet → child-wallet or facilitator) | EFFECTFUL (new) | Real on-chain transfer, gated on REQ-102's already-certified amount and REQ-304's single-signer-only constraint. |
| **Effectful Shell (existing, reused unmodified)** | `~/anicca/skills/self/spawn/lib/ledger.js::appendChild`/`readChildren` | EFFECTFUL (existing) | Append-only JSONL; already implemented. REQ-305. |
| **Effectful Shell (new)** | new independent RPC balance-read step (before/after comparison) for REQ-401 | EFFECTFUL (new) | Mirrors the exact `eth_call balanceOf` method SPEC.md §9.9 already used to confirm Franklin#1's final balance independently of the parties' own self-report. |
| **Effectful Shell + static analysis (new)** | new audit script combining (a) `grep -r` over skill scripts/cron config for all 3 path forms and (b) live invocation of `resolve-identity.mjs`'s exported resolvers per running instance | EFFECTFUL + STATIC (new) | REQ-403. The grep half is Tier 0 (no runtime execution of the AUDITED code, though the audit script itself runs); the live-comparison half is Tier 2/3 (requires N ≥ 2 real running instances). |
| **Not code — design constraint** | REQ-104 (bookkeeping-only design constraint on REQ-101/102/103) | N/A | Directly analogous to `anicca-agent-economy`'s REQ-203; verified by Phase 3 structural code read (grep for LLM calls/prompt strings/scoring fields in the gate's own source), never a runtime assertion. |
| **Not code — design constraint** | REQ-301 (local-spawn-forbidden structural constraint) | N/A | Verified by reading the deploy code path's artifact list post-attempt, not by running a probe against a hypothetical violation. |
| **Not code — reused-but-superseded prior art** | `~/anicca/skills/self/spawn/{SKILL.md,scripts/cloud-init.sh,scripts/seed-child.py,scripts/sign-telemetry.py,scripts/usdc-balance.py}` (2026-06-16 DigitalOcean + AgentMail single-lineage design) | N/A | Architecturally superseded by SPEC.md §1.3's Franklin/ERC-8004 pivot (predates it). NOT reused by any REQ in this spec (DO droplets + AgentMail inboxes + `automaton.service` systemd units belong to a different, non-cloud-crypto-native provisioning model). Listed here only so Phase 2/3 do not mistake this directory's OLD `run.sh`/`SKILL.md` narrative for this feature's actual target behavior — the REUSED primitives are exactly (and only) `gen-wallet.sh`, `deploy-akash.sh`, `akt-treasury.sh`, `lib/spawn-decision.js`, `lib/child-spec.js`, `lib/ledger.js`, all individually cited above. |

## Verification tiers (this feature's convention, consistent with `anicca-agent-economy`'s
`specs/verification-architecture.md`)

- **Tier 0**: structural/existence checks — no runtime execution of the AUDITED code required (a
  ledger row's `status` field is always one of the three allowed values; a design-constraint
  requirement's source contains no LLM call/prompt string; the static grep sweep for cross-instance
  path references).
- **Tier 1**: pure-function unit tests — deterministic fixtures, no filesystem/network/real
  wall-clock sleep, fast (milliseconds). REQ-101's aggregation, REQ-102's gate, REQ-103's reused
  `isLockStale` predicate (already Tier-1-proved upstream; this feature's own Tier-1 obligation is
  only proving the NEW `"colony-spawn"` lock KEY is wired to it correctly, not re-proving the
  predicate itself), REQ-201/202's conditional-generation logic, REQ-402's window-boundary
  relabeling logic.
- **Tier 2**: integration tests — real module wiring (real `fs`, small injected timing constants,
  concurrent `Promise.all`/multi-process calls against the real lock/identity/resolve-identity
  modules) plus fresh-context adversary review of the disk artifacts (no live chain/cloud spend
  required for this tier). REQ-103's concurrent-attempt race, REQ-203's cross-instance
  `resolve-identity.mjs` non-leak test, REQ-305's failure-injection-at-each-step test, REQ-403's
  static-grep-plus-fixture-collision test.
- **Tier 3**: live, no-mock E2E — real transactions/leases against the live (or, for a first-pass
  dry run, testnet/sandbox) chain and cloud provider, executed the same way the P2 gig-board
  adversary and SPEC.md §9.9's witness already did (real tx hashes, real cloud lease/job IDs,
  independent re-verification), per this project's HARD RULE 0.24 (on-chain-verified only, no
  paper/simulated claims). REQ-204's real `register()` call, REQ-302's real Nosana job, REQ-303's
  real Akash lease, REQ-304's real funding transfer, REQ-401's real, independently-re-verified gig
  settlement, REQ-403's live pairwise-key-inequality check across N ≥ 2 real running instances.
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
| PROP-101c | REQ-101 | Missing/unreadable/non-finite/negative `telemetry.json` data for a citizen contributes `0` (fail-closed), never throws | 1 | true | unit test: malformed/missing fixture files → function returns a finite number, never throws, never counts the bad entry as positive surplus |
| PROP-102a | REQ-102 | `colonySurplusUsd === spawnThresholdUsd` exactly → `eligible:true` (inclusive boundary) | 1 | true | unit test at the exact boundary value and at `boundary - 0.01` |
| PROP-102b | REQ-102 | Cooldown gate overrides surplus size — surplus far above threshold does NOT bypass an unexpired cooldown | 1 | true | unit test: huge surplus, `lastSpawnAttemptMs` inside the cooldown window → `eligible:false, reason:"rate_limited"` |
| PROP-102c | REQ-102 | `childrenProvisioning >= maxConcurrentSpawns` blocks eligibility regardless of surplus/cooldown | 1 | true | unit test: surplus and cooldown both satisfied, `childrenProvisioning=maxConcurrentSpawns` → `eligible:false, reason:"max_concurrent_spawns"` |
| PROP-102d | REQ-102 | Non-finite/negative `colonySurplusUsd` input is treated as `0` (never eligible) | 1 | true | unit test mirroring the existing `tier.mjs`/`catalog-gate.mjs` NaN/Infinity/negative fixture convention |
| PROP-102e | REQ-102 | Check ordering is surplus → cooldown → concurrency cap (matches `spawn-decision.js`'s existing ordering discipline) | 1 | true | unit test: a fixture failing ALL THREE checks asserts the returned `reason` is the SURPLUS failure, not cooldown or cap (proves evaluation order, not just final boolean) |
| PROP-103a | REQ-103 | Given two concurrent callers both observing `eligible:true`, exactly one reaches REQ-201's wallet-generation step | 2 | true | integration test: two `Promise.all`-raced calls into `withColonyLock("colony-spawn", fn)`, assert exactly one invocation of the (mocked) wallet-generation step, the other returns `reason:"lock_held"` with zero wallet-generation calls |
| PROP-103b | REQ-103 | A crashed holder's lock (no heartbeat for ≥ `staleMs`) is reclaimable by exactly one subsequent caller | 1/2 | true | reuses the exact Tier-1 `isLockStale` fixture tests already proved upstream (`anicca-agent-economy` REQ-101/PROP-101b) plus a Tier-2 test creating a real backdated `"colony-spawn"` lock file and asserting exactly one of two concurrent reclaim attempts succeeds |
| PROP-103c | REQ-103 | A live, heartbeating holder is never stolen from, however long its critical section legitimately runs | 1 | true | reuses the exact Tier-1 fixture proof already established upstream for `isLockStale` (no new proof needed — REQ-103's own obligation is only that the NEW `"colony-spawn"` key is wired through the same, already-proved mechanism) |
| PROP-104a | REQ-104 | `decideColonySpawn`/`computeColonySurplusUsd`'s source contains no network call, no prompt/LLM-client reference, and no scoring/ranking/free-text-recommendation field on its return value | 0 | true | Phase 3 structural grep/read of the diff; fails if any such reference is found, exactly as `anicca-agent-economy`'s PROP-203a/b already established for its own gate |
| PROP-201a | REQ-201 | A `gen-wallet.sh` output whose address derives from the documented sha256-fallback path (no real keccak available) is detected and rejected, never used | 1/2 | true | unit/integration test: inject an environment where the keccak dependency is unavailable, assert the caller aborts rather than proceeding with the fallback address |
| PROP-201b | REQ-201 | The generated child EVM address is verified distinct from every currently-known citizen's own address before proceeding | 1 | true | unit test: fixture citizen-address list including the freshly-generated address (forced collision case) → assert abort/regenerate, never silent proceed |
| PROP-201c | REQ-201 | Private key material is captured only into a 600-perm file under the child's own isolated `$HOME`, never into a shared log | 0/2 | true | Tier 0: structural read of the calling code confirms stdout is redirected directly to a file path, never piped through any logging wrapper; Tier 2: a real invocation's `gen-wallet.sh` output file has mode `0600` and lives under the child's own home |
| PROP-202a | REQ-202 | `needsSolanaWallet({initialSkills, deployTarget})` returns `true` exactly when a Solana-settled skill OR Nosana deploy target is present, `false` otherwise | 1 | true | unit test, exhaustive branch coverage of the three trigger conditions (Solana skill / Nosana target / neither) |
| PROP-202b | REQ-202 | When `needsSolanaWallet` is `false`, no Solana key-generation subprocess is invoked at all | 2 | true | integration test: spy/mock the Solana keygen call, assert zero invocations on an EVM-only + Akash-only fixture |
| PROP-202c | REQ-202 | Generated Solana address is verified distinct from every existing citizen's own Solana address | 1 | true | unit test mirroring PROP-201b for the Solana keyspace |
| PROP-203a | REQ-203 | The child's proposed `HOME`/`ANICCA_HOME` is checked for equality/containment against every existing citizen's own value BEFORE any REQ-201/202 key generation runs | 1 | true | unit test asserting the distinctness check function is called, and key-generation is NOT called, when a forced collision fixture is supplied |
| PROP-203b | REQ-203 | Two processes with two different injected `HOME` values, run against the SAME `resolve-identity.mjs` module, each resolve ONLY their own wallet file | 2 | true | integration test extending the existing `resolve-identity.mjs` test suite's own FIND-001-class regression pattern to a THIRD, freshly-generated home directory fixture |
| PROP-203c | REQ-203 | Every process-launch boundary used by REQ-302/303 explicitly sets `HOME`/`ANICCA_HOME` in its own artifact (SDL `env:`, job-definition `env`, cloud-init `Environment=`) — never relies on a base-image default | 0 | true | structural read of the actual SDL/job-definition/cloud-init artifact used for a real deploy, confirming the explicit env line is present |
| PROP-204a | REQ-204 | A real `register()` call against the live registry (mainnet or testnet, per `GIG_CHAIN`) succeeds, returns a real `agentId` and tx hash, using `identity.mjs` unmodified | 3 | true | live E2E: a fresh child key calls `registerIdentity`, independently re-verify the tx receipt + `ownerOf(agentId)` via a separate RPC call (not just trusting the returned value) |
| PROP-204b | REQ-204 | The one-time gas seed funding a child's `register()` call is sized to cover exactly one `register()` + one gig-board interaction, never an open-ended top-up | 0/2 | true | structural read of the funding-amount constant/formula; integration test confirms the transferred amount matches the documented sizing formula, not an arbitrary/larger figure |
| PROP-204c | REQ-204 | A wallet that already holds an agentId (defensive case) is not re-registered; the existing agentId is reused and the anomaly logged | 1/2 | true | unit test: mock `verifyIdentity`/`ownerOf` returning an existing owner match → assert `register()` is never called a second time |
| PROP-205a | REQ-205 | The written `mcp.json` matches the exact key shape of the existing, live `~/.blockrun/mcp.json` | 0 | true | structural JSON-shape diff against the existing live file's schema |
| PROP-205b | REQ-205 | `GIG_STATE_PATH`'s resolved absolute path is verified distinct from every other currently-known citizen's own `GIG_STATE_PATH` at write time | 1 | true | unit test: fixture citizen path list including a forced collision → assert write is blocked/regenerated, not silently duplicated |
| PROP-301a | REQ-301 | After a spawn attempt completes (success or failure), the initiating host retains no child-specific persistent runtime artifact (no lingering process, no child-specific systemd/launchd unit, no child wallet file left outside the child's own relocated home) | 0 | true | structural review of the deploy code path's post-attempt cleanup; Phase 3 adversary spot-checks a real attempt's initiating host afterward |
| PROP-302a | REQ-302 | The Nosana deploy step never reads/writes the invoking host's own default `~/.nosana/` directory when acting on behalf of a child | 1/2 | true | unit/integration test asserting the CLI invocation's key-path argument/env points at the child's own isolated file, and that no file appears under the invoking host's own `~/.nosana/` as a side effect |
| PROP-302b | REQ-302 | A real `nosana job post ... --wait` invocation for a child yields a job ID that independently resolves (via a separate query, not just the posting call's own stdout) to `RUNNING`/`COMPLETED` | 3 | true | live E2E against Nosana (devnet/cheapest mainnet market as a first pass, mainnet-class market for final completion per the Tier-3 policy above); independently re-query `https://explore.nosana.com/jobs/<id>` (or current CLI equivalent) |
| PROP-303a | REQ-303 | `deploy-akash.sh`/`akt-treasury.sh` are invoked with zero source modification (only `CHILD_ID`/SDL substitution) | 0 | true | structural diff: the scripts on disk are byte-identical to their pre-existing versions; only the SDL template/CHILD_ID argument passed in differs |
| PROP-303b | REQ-303 | A real Akash deploy for a child yields an active lease and a successfully sent manifest, independently re-queryable | 3 | true | live E2E against Akash (sandbox-2 as a first pass per this repo's own established practice, mainnet for final completion); independently re-run `provider-services query market lease list`/`query deployment` to confirm state, not just trusting the script's own stdout |
| PROP-303c | REQ-303 | The real `AKASH_DEPOSIT` and settled lease cost are appended to a shelter-cost ledger that REQ-102 reads on its next evaluation | 1/2 | true | integration test: after a real/fixture deploy, confirm the ledger file gains an entry, and a subsequent `decideColonySpawn`-adjacent threshold computation reads `measured_last_shelter_cost_usd` from it rather than the `$5.00` default |
| PROP-304a | REQ-304 | No code path in this feature ever reads a human-funded wallet's private key or balance as a funding source | 0 | true | structural grep across all new funding-transfer code for any reference to a human-funded wallet path/env var (e.g. claude-p's known wallet identifiers) — must find none |
| PROP-304b | REQ-304 | A funding transfer's amount never exceeds the amount REQ-102 certified as available for that specific spawn attempt | 1/2 | true | unit/integration test: attempt to fund an amount greater than the certified surplus → assert rejection, not a silent overdraw |
| PROP-304c | REQ-304 | When no single citizen individually holds enough (even though the aggregate clears REQ-102's threshold), the spawn does not proceed this wake and no child ledger row is created | 1 | true | unit test: fixture with aggregate surplus above threshold but each individual citizen's own surplus below the deploy cost → assert no child record created, a funding-shortfall no-op is logged |
| PROP-305a | REQ-305 | Every ledger write path sets `status` to exactly one of `{"provisioning","active","failed"}` — never omits it, never writes `"active"` before REQ-204+REQ-205 complete | 0 | true | structural review of every code path that calls `appendChild`/updates a child row |
| PROP-305b | REQ-305 | Injecting a failure at each of REQ-201/202/203/204/205/302/303 in turn produces a ledger row correctly identifying the failing step, and REQ-101's next aggregation excludes that child | 2 | true | integration test, one fixture per injected failure point |
| PROP-305c | REQ-305 | Failed attempts within a single cooldown window are capped (default `3`); beyond the cap, further attempts within that window are rate-limited exactly as a successful spawn would be | 1 | true | unit test: 3 injected failures within one window, a 4th attempt within the same window → `eligible:false, reason:"rate_limited"` even though no successful spawn has occurred |
| PROP-401a | REQ-401 | A claimed $0-bootstrap success is corroborated by an independent RPC balance read (before/after), not accepted from either trading party's own self-report | 3 | true | live E2E: a fresh, independent `eth_call`/balance query taken before and after the child's own gig settlement, performed by a process that is neither trading party |
| PROP-401b | REQ-401 | The ledger entry recording success contains gig ID, tx hash, balance delta, and timestamp sufficient for a fresh adversary to re-derive the claim | 0 | true | structural check of the ledger row schema on a real success case |
| PROP-402a | REQ-402 | A child exceeding `BOOTSTRAP_WINDOW_DAYS` without a recorded REQ-401 success is relabeled `"bootstrap_failed"`, and no others are | 1 | true | unit test: fixture set of children with varying `active_since` timestamps and success flags, assert exactly the correct subset is relabeled |
| PROP-402b | REQ-402 | A late (post-window) success retroactively corrects the label back from `"bootstrap_failed"` | 1/2 | true | unit test: a child already labeled `"bootstrap_failed"` that subsequently produces a REQ-401-qualifying success → assert label correction on the next evaluation |
| PROP-402c | REQ-402 | A `"bootstrap_failed"` child's balance is excluded from REQ-101's productive-surplus aggregation even if nonzero | 1 | true | unit test: fixture `"bootstrap_failed"` citizen with nonzero balance → assert `computeColonySurplusUsd` excludes it |
| PROP-403a | REQ-403 | The static grep sweep (all 3 path forms, across skill scripts + cron/job configs) reports zero cross-instance path references in the current, real codebase | 0 | true | run the actual grep sweep against the real repo at Phase 3, not a fixture — must report zero findings for it to be considered proved on the CURRENT tree |
| PROP-403b | REQ-403 | With N ≥ 2 real running instances (including at least one newly-spawned child), pairwise comparison of `resolveEvmPrivateKey`/`resolveSolanaSecret` outputs shows no equal keys, and no instance's resolved key-FILE PATH lies inside another instance's own home directory | 2/3 | true | live check: invoke the resolvers once per real running instance's own environment, assert pairwise inequality; Tier 3 once an actual spawned child exists to include in the comparison |
| PROP-403c | REQ-403 | A deliberately-injected fixture where two fake instances share a `HOME` is correctly flagged as a collision by the audit (negative-test / audit-is-not-vacuous check) | 1/2 | true | unit/integration test: two fixture "instances" with an identical `HOME` value → assert the audit reports a collision, proving the check would actually catch a real one |

## Verification Strategy

- **Tier 0** (no runtime execution of the audited code): REQ-104's structural no-LLM/no-scoring
  check (PROP-104a); REQ-201's private-key-handling structural check (PROP-201c, structural half);
  REQ-203's explicit-env-injection structural check (PROP-203c); REQ-204's gas-seed-sizing
  structural check (PROP-204b, structural half); REQ-205's `mcp.json` shape check (PROP-205a);
  REQ-301's post-attempt-artifact structural check (PROP-301a); REQ-303's unmodified-script-reuse
  structural check (PROP-303a); REQ-304's no-human-funded-source structural check (PROP-304a);
  REQ-305's ledger-status-completeness structural check (PROP-305a); REQ-401's ledger-schema
  structural check (PROP-401b); REQ-403's static grep sweep against the real current tree
  (PROP-403a).
- **Tier 1** (pure-function unit tests): REQ-101's aggregation (PROP-101a/b/c); REQ-102's gate
  (PROP-102a-e); REQ-103's reused `isLockStale` wiring (PROP-103b/c, reusing the already-proved
  upstream fixtures); REQ-201/202's collision/conditional-generation checks (PROP-201b, PROP-202a/c);
  REQ-203's pre-generation distinctness check (PROP-203a); REQ-204's defensive
  already-registered check (PROP-204c, unit half); REQ-205's state-path-uniqueness check
  (PROP-205b); REQ-302's own-home-isolation check (PROP-302a, unit half); REQ-304's
  amount-ceiling and individual-insufficiency checks (PROP-304b/c); REQ-305's cooldown-cap check
  (PROP-305c); REQ-402's window-boundary relabeling and exclusion checks (PROP-402a/c); REQ-403's
  negative-test collision-detection check (PROP-403c, unit half).
- **Tier 2** (integration, real module wiring + fresh-context adversary disk review, no live
  chain/cloud spend required): REQ-103's concurrent-attempt race (PROP-103a) and crashed-holder
  reclaim (PROP-103b, integration half); REQ-201's real 600-perm/own-home file check (PROP-201c,
  integration half); REQ-202's zero-invocation-when-unneeded check (PROP-202b); REQ-203's
  cross-instance `resolve-identity.mjs` non-leak test (PROP-203b); REQ-204's gas-seed-amount
  integration check (PROP-204b, integration half) and already-registered defensive check
  (PROP-204c, integration half); REQ-302's own-home-isolation integration check (PROP-302a,
  integration half); REQ-303's shelter-cost-ledger feedback check (PROP-303c); REQ-305's
  failure-injection-at-each-step test (PROP-305b); REQ-402's late-success retroactive-correction
  test (PROP-402b); REQ-403's live pairwise-key check once ≥ 2 real instances exist but before a
  fresh spawn (PROP-403b, integration half), and negative-test collision-detection integration
  half (PROP-403c).
- **Tier 3** (live, no-mock E2E against real/testnet-first chain and cloud state, HARD RULE 0.24):
  REQ-204's real `register()` call (PROP-204a); REQ-302's real Nosana job deploy (PROP-302b);
  REQ-303's real Akash lease deploy (PROP-303b); REQ-401's independently-re-verified real gig
  settlement by the spawned child itself (PROP-401a); REQ-403's live pairwise-key check extended to
  include an actual newly-spawned child (PROP-403b, Tier-3 half). **Per the Tier-3 policy stated
  above, a testnet/sandbox-first pass is an acceptable precursor, but this increment's completion
  requires at least one real mainnet-class result for REQ-204, REQ-302 or REQ-303 (whichever cloud
  path is actually used for the completing spawn), and REQ-401 — mirroring SPEC.md §9.9's own
  correction that only a mainnet-class settlement counts as the actual witness.**

## Gate

Phase 3 (adversarial review) must confirm, via fresh-context, disk-only review plus (for the Tier-3
items) live re-execution performed by the adversary itself:

(1) REQ-101/102's arithmetic is read end-to-end confirming: the self-funded filter (`isSelfFunded`)
gates the aggregation exactly as REQ-101 specifies with no human-funded wallet leaking in
(PROP-101b), the threshold comparison is inclusive at the boundary (PROP-102a), the cooldown check
is never bypassed by surplus size (PROP-102b), and the check ORDER matches REQ-102's specified
surplus→cooldown→cap sequence (PROP-102e) — a control-flow read, not merely an outcome check;

(2) REQ-103's mutual exclusion is proven under a deliberately-induced concurrent race (two
simultaneous `eligible:true` evaluations), confirming exactly one proceeds and the other logs
`reason:"lock_held"` with zero wallet-generation side effects (PROP-103a), AND that the
`"colony-spawn"` lock key is genuinely wired through the EXISTING, already-hardened `lock.mjs`
module rather than a fresh reimplementation (control-flow read, not a grep for the word "lock");

(3) REQ-104's design constraint holds — no LLM/prompt/scoring code exists anywhere in
`computeColonySurplusUsd`/`decideColonySpawn`'s diff (PROP-104a), matching the identical
`anicca-agent-economy` REQ-203 precedent this feature explicitly follows;

(4) REQ-201-205's identity-generation chain is read end-to-end confirming: the sha256-fallback
address is detected and rejected rather than silently used (PROP-201a), every generated
key/address is checked for distinctness against ALL existing citizens (not just one parent)
before use (PROP-201b/PROP-202c), the `$HOME`/`ANICCA_HOME` distinctness check runs BEFORE any
key generation (PROP-203a), the cross-instance `resolve-identity.mjs` non-leak property holds for
a genuinely new third home directory (PROP-203b), `identity.mjs`/`gen-wallet.sh`/`deploy-akash.sh`/
`akt-treasury.sh` are reused with zero source modification (PROP-201/303's structural checks), and
the written `mcp.json` + `GIG_STATE_PATH` are structurally distinct from every existing citizen's own
config (PROP-205a/b);

(5) REQ-301's local-spawn-forbidden constraint holds — a real or simulated spawn attempt leaves no
persistent child-specific artifact on the initiating host (PROP-301a);

(6) REQ-302/303's cloud deploy paths are each proven live at least once (testnet/sandbox first pass
acceptable, but the increment's completion requires one real mainnet-class result per the Tier-3
policy) with independent re-verification of the resulting job/lease state via a SEPARATE query than
the deploying script's own stdout (PROP-302b/PROP-303b), and that neither path ever touches the
invoking host's own default key-storage directory when acting on a child's behalf (PROP-302a);

(7) REQ-304's funding-source constraint is confirmed structurally (no human-funded wallet reference
anywhere in the funding code, PROP-304a) AND behaviorally (a funding attempt exceeding the
REQ-102-certified amount is rejected, PROP-304b; an aggregate-sufficient-but-no-individual-sufficient
scenario correctly produces a no-op with no child record, PROP-304c);

(8) REQ-305's no-partial-spawn guarantee is proven by injecting a failure at EACH step in the chain
in turn and confirming the resulting ledger row correctly identifies the failing step and is
excluded from REQ-101's next aggregation (PROP-305b), and that the failed-attempt cooldown-cap
closes the "engineer repeated failures to bypass cooldown" gap (PROP-305c);

(9) REQ-401's $0-bootstrap success criterion is proven with a REAL, independently-re-verified
on-chain settlement performed autonomously by the spawned child itself — the adversary must not
accept either trading party's own self-report, and must perform its own fresh balance read
(PROP-401a);

(10) REQ-402's bootstrap-timeout bookkeeping is proven at the boundary (exactly the children past
the window are relabeled, no others — PROP-402a) and its non-punitive, retroactive-correction
property is proven for a late success (PROP-402b), and its exclusion from REQ-101's aggregation
while `"bootstrap_failed"` (PROP-402c);

(11) REQ-403's wallet mutual non-interference audit is run BY THE ADVERSARY ITSELF against the
real, current tree (zero cross-instance path references, PROP-403a) and, once ≥ 2 real instances
exist (including, ideally, an actual spawned child), against real running processes (pairwise key
inequality, PROP-403b) — and the audit's own negative-test collision-detection is confirmed
non-vacuous (PROP-403c) before its "zero findings" result on the real tree is trusted.

Any single BLOCKING finding under (1)-(11) fails this Gate; Phase 4 (implementation) may not be
marked complete until all findings are resolved and a fresh adversary pass confirms PASS, per this
project's strict-mode VCSDD discipline (no postponement).
