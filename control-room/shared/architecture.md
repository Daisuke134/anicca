# shared/architecture.md — multi-profile-per-instance × colony

> Why does each Anicca instance host **10 specialist profiles** inside a single
> Hermes daemon, rather than one monolithic agent or one container per role?
> And why does the colony scale by spawning **whole Daytona sandboxes**, each
> containing its own 10-profile set, rather than scaling specialists
> independently?

This file answers both. It is derived from `specs/07-HERMES-PIVOT.md` §§ 1, 2,
3 and `specs/05-SERVER-NATIVE-DEPLOY.md` §§ 1, 2.

---

## § 1. The Shann Holmberg control-room pattern (origin)

Shann Holmberg's empirical lesson from running multi-agent systems in
production:

> "A single agent with 30 tools will hallucinate tool selection. A swarm
> of 30 agents with one tool each will lose the thread. The sweet spot is
> ~10 specialists, each with a tight scope, coordinated by a router
> ('control room') that sees all of them."

Anicca v3.2 adopts this exactly:

| Anti-pattern Shann observed | Anicca avoids it by |
|---|---|
| single agent, 50+ tools, confused tool calls | 10 profiles, each profile has ≤10 tools in scope |
| swarm of 30 micro-agents, no coordinator | `orch` profile is the single front door |
| container-per-role overhead (Kubernetes-style) | all 10 profiles share **one Hermes daemon process** (same Kanban DB, same wallet, same Constitution hash) |
| state drift between agents | shared SQLite + shared FTS5 session search per instance |

---

## § 2. Why one Hermes daemon (not 10 daemons)

| Concern | One daemon (chosen) | 10 daemons (rejected) |
|---|---|---|
| Wallet consistency | one CDP smart wallet per instance, all profiles see same balance | 10 sub-wallets, race conditions on spend, KYC re-derivation cost |
| Constitution propagation | hash check runs once per tick for the whole instance | 10× hash check overhead, 10× drift surface |
| Kanban routing | single SQLite DB, ACID `claim_task()` already supports per-profile claims | 10 DBs, cross-DB transactions impossible, lock contention |
| Memory cost | ~512 MB / instance | ~5 GB / instance (= 10× FastAPI + 10× SQLite + 10× Python interp) |
| Spawn cost (Daytona) | 0.5 vCPU / 512 MB / 5 GB disk = fits in cheapest tier | 5 vCPU / 5 GB RAM = 10× cost, breaks the $5/mo-per-child economics in spec 01 § 2 |
| Operator mental model | "1 sandbox = 1 Anicca instance with 10 jobs" | "1 sandbox = 10 disjoint agents pretending to be Anicca" |

The deciding factor: **AgentKit's CDP wallet is per-account, not per-process**.
One CDP signup → N smart wallets (one per instance). Within an instance, all
profiles must share that wallet to avoid signing-key fragmentation.

See `specs/07-HERMES-PIVOT.md` § 3.4 ("Per-profile wallet inheritance — the
'1 CDP account → N wallets' trick").

---

## § 3. Why 10 profiles (not 5, not 30)

Profiles map 1:1 to the spec 01 + 02 + 03 functional taxonomy:

| Functional layer (spec) | Profiles | Count |
|---|---|---|
| Front door (spec 07 § 2) | `orch` | 1 |
| Money in — 5 spouts (spec 01 § 1) | `earn-x402` / `earn-autohedge` / `earn-bounty` / `earn-bittensor` / `earn-farcaster` | 5 |
| Imitation cook loop (spec 02 § 2) | `cook-loop` | 1 |
| Money out — UBI router (spec 01 § 3) | `ubi` | 1 |
| Self-heal (spec 03 § 2) | `fixer` | 1 |
| Constitution guard (spec 00 § 6) | `constitution` | 1 |
| **TOTAL** | | **10** |

Why not 5 (collapse earn into one): per-spout incident-isolation. If
`autohedge` glitches, the other 4 spouts keep earning. A single `earn`
profile would put all 5 spouts in one prompt context window — a Kimi K2.6
262K window can hold them, but tool-call confusion goes up sharply past ~8
distinct verbs.

Why not 30 (split earn-x402 by endpoint, fixer by error class, etc.):
diminishing returns on Kanban routing efficiency. Shann's observation:
~10 is the sweet spot.

Why not 11 (e.g., separate ACP profile): Virtuals Protocol is DEFERRED in
spec 07 § 3.5 until OSS code lands. When ACP is verified, see
`templates/new-profile.md` for how to add it as profile #11.

---

## § 4. The colony layer (N Daytona sandboxes)

```
                                                                                
   ┌──────────────────────────────────────────────────────────────────────┐    
   │   COLONY (anicca-genesis + spawned children)                          │    
   │                                                                       │    
   │   ┌─ instance: anicca-genesis ──┐                                     │    
   │   │  Daytona sandbox            │                                     │    
   │   │  • 10 profiles              │  ─────► spawn (when wallet > $20)   │    
   │   │  • 1 CDP smart wallet       │                                     │    
   │   │  • Kanban SQLite            │                                     │    
   │   │  • Constitution.sha256      │                                     │    
   │   └─────────────────────────────┘                                     │    
   │              │                                                        │    
   │              ▼ anicca-spawn-controller L2 skill                       │    
   │   ┌─ instance: anicca001 ──────┐  ┌─ instance: anicca002 ──┐  ...    │    
   │   │  Daytona sandbox            │  │  Daytona sandbox        │        │    
   │   │  • 10 profiles (copy)       │  │  • 10 profiles (copy)   │        │    
   │   │  • 1 CDP smart wallet       │  │  • 1 CDP smart wallet   │        │    
   │   │    (derived from same       │  │    (derived from same   │        │    
   │   │     CDP_API_KEY_* trio)     │  │     CDP_API_KEY_* trio) │        │    
   │   │  • Kanban SQLite (its own)  │  │  • Kanban SQLite        │        │    
   │   │  • Constitution.sha256      │  │  • Constitution.sha256  │        │    
   │   │    (== genesis hash)        │  │    (== genesis hash)    │        │    
   │   └─────────────────────────────┘  └─────────────────────────┘        │    
   └──────────────────────────────────────────────────────────────────────┘    
                                                                                
```

Properties:

| Property | Value | Why |
|---|---|---|
| Sandbox isolation | Daytona = AGPL-3.0 self-host, network-isolated | OS-level isolation; one instance's exploit can't reach another's wallet |
| Wallet inheritance | each instance derives its own smart wallet from the **same CDP signup** | spec 07 § 3.4 — KYC-zero for all spawned children |
| Constitution propagation | parent verifies hash before child boots; child verifies hash on every tick | spec 00 § 6.3 — immutable backdrop |
| Kanban isolation | each instance has its own SQLite Kanban DB | no cross-instance race on `claim_task()`; messaging across instances uses x402 / Farcaster, not shared DB |
| Spawn budget | parent only spawns if wallet > $20 + colony size < target | spec 00 § 7.3 + spec 07 § 6 Day 7 |
| Hosting backend | Daytona primary, Akash fallback | spec 07 § 3.6 + spec 05 MODE B |

See `templates/new-instance.md` for the exact provisioning steps.

---

## § 5. Why not container-per-role (rejected design)

A naïve port of the Shann pattern would put each of the 10 profiles in its
own Docker container. Rejected because:

| Cost | Container-per-role | 10-profile-per-daemon (chosen) |
|---|---|---|
| Daytona sandboxes per instance | 10 | 1 |
| Monthly Daytona cost per instance | $50+ | $5 |
| Inter-profile latency | network RTT (~10 ms / hop) | in-process function call (~10 µs) |
| Operator complexity | 10× docker-compose files, 10× restart policies | 1 launchd plist |
| Wallet split / merge | every spend requires cross-container signing dance | one wallet, one signer |

NHOSS economics (spec 01 § 2) require ≤$5/mo per child to break even on the
$0.30/x402 invoice price. Container-per-role makes the math impossible.

---

## § 6. Operational invariants

| Invariant | Enforced by | What breaks if violated |
|---|---|---|
| 10 profiles per instance, no more, no less | `templates/new-profile.md` review gate | Kanban routing breaks; orch can't classify |
| 1 Hermes daemon per Daytona sandbox | launchd `KeepAlive=true` + 1 plist per sandbox | wallet race, Constitution drift |
| 1 CDP smart wallet per instance, N instances per CDP signup | `anicca-wallet-x402` skill on first boot | mixed signing keys, KYC re-derivation |
| Constitution SHA-256 == genesis hash on every tick | `constitution` profile + `anicca-constitution-guard` skill | Pañcasīla violation gate fails open |
| Self-pay 100% via OpenRouter USDC topup | `anicca-fuel-broker` skill + spec 07 § 4 routing matrix | operator CC charged, NHOSS violated |
| Personal companion skills (mr-bot / phone / etc.) NEVER in anicca-oss | spec 07 § 9 + `shared/security.md` | PII leak into public OSS |

---

## § 7. Cross-references

| Concept | Authority |
|---|---|
| L3 Hermes daemon anatomy | `specs/07-HERMES-PIVOT.md` § 2.2 |
| L4 AgentKit wallet bootstrap | `specs/07-HERMES-PIVOT.md` § 3.2 |
| Daytona spawn primary | `specs/07-HERMES-PIVOT.md` § 3.6 + `specs/05-SERVER-NATIVE-DEPLOY.md` § 2 |
| Akash fallback | `specs/05-SERVER-NATIVE-DEPLOY.md` MODE B |
| Mac mini local-seeded genesis | `specs/05-SERVER-NATIVE-DEPLOY.md` MODE C |
| Constitution propagation | `specs/00-MASTER.md` § 6.3 |
| 5 spouts (earn) + UBI (out) | `specs/01-EARN-AND-UBI.md` |
| Imitation cook loop | `specs/02-IMITATE-AND-COOK.md` § 2 |
| Self-eval / fix-the-fix | `specs/03-SELF-AWARE-EVAL.md` |
| Heartbeat (60s) | `specs/07-HERMES-PIVOT.md` § 7 |

---

**END OF shared/architecture.md.**
