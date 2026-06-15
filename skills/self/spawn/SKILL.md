---
name: self/spawn
description: Self-replication — a profitable parent Anicca births a child instance on DO/Akash with its OWN wallet + OWN AgentMail inbox; the child runs its first earn wake without parent instruction. Gate is deterministic (wallet >= threshold + rate-limit + concurrency cap); no human in the loop.
metadata:
  track: A
  spec: 26 A4 / 27 A-self-spawn
  entrypoint: run.sh
  parallel_safe: true
  requires:
    bins: [bash, jq, node, curl, openssl]
    env_optional: [DIGITALOCEAN_TOKEN, AGENTMAIL_API_KEY, ANICCA_WALLET_JSON]
---

# self/spawn

## Why
spec27 A-self-spawn: a profitable Anicca should birth a child so the colony compounds. The child is
**pure Anicca lineage** (no Dais keys) — its own wallet, its own inbox, its own earn wake. This is the
`live/die` primitive that makes takeoff possible.

## Gate (deterministic — `lib/spawn-decision.js`, node:test-covered)
```
eligible = balance_usdc >= minBalance (20)          # own survival first
        && no child spawned in the last 14 days     # rate-limit
        && children < maxChildren (1)               # parent caps concurrency
otherwise -> dormant (silent), exit 0, reason in {low_balance, rate_limited, max_children}
```
Order is balance -> rate-limit -> cap (a broke parent never spawns, whatever else is true).

## Flow (real run, when eligible)
```
1. read parent balance (state/wallet.json) + colony (state/children.jsonl)
2. decideSpawn(...)  -> eligible?  (pure, tested)
3. nextChildId(...)  -> anicca-cNNN  (monotonic, gap-safe, tested)
4. scripts/gen-wallet.sh         -> child secp256k1 wallet (600-perm temp; DISTINCT from parent, asserted)
5. POST AgentMail /v0/inboxes    -> child's own inbox (AGENTMAIL_API_KEY)
6. append PROVISIONAL row to state/children.jsonl  (never lose track)
7. provision droplet (DO API) or lease (akash)     -> PROVIDER_ID
8. print CHILD_ID / CHILD_WALLET / CHILD_INBOX / PROVIDER_ID
```
Seed: transfer $1 USDC parent->child so the child can pay its first wake (the child wakes on its own).

## Usage
```bash
bash run.sh --dry-run        # gate-only: prints decision JSON, touches NOTHING. exit 0.
bash run.sh                  # real run (host=do by default; --host=akash for sovereign)
ANICCA_SPAWN_HOST=akash bash run.sh
```

## NO FAKE RUN (HARD 0.24)
`--dry-run` performs ZERO side effects and says so. A real run reports success **only** after a real
provider id + a child wallet **distinct** from the parent exist; any failed step exits non-zero and
leaves an honest `provisioning`/`failed` ledger row (never a fabricated success).

## NO HUMAN IN LOOP (HARD 0.20)
Never asks "spawn OK?" or "where to host?" — the gate decides and the provider auto-bids. The child's
identity ("Daughter of Anicca <hash>") and the $1 seed are fixed, not confirmed.

## Verify (spec27 A-self-spawn)
- `node --test lib/__tests__/*.test.js` -> all pass.
- `bash run.sh --dry-run` below threshold -> `eligible:false` + reason, no ledger written.
- (runtime, post-fund) real run -> child droplet active + `CHILD_WALLET != parent` on basescan +
  the child appears on aniccaai.com/dashboard (it POSTs telemetry from its own report skill).

## Collision
This skill edits ONLY `skills/self/spawn/**`. It does NOT touch `skills/registry.json`, `install.sh`,
or any landing file. Flipping this slot's registry `status` to `"live"` is a separate one-line change
Foundation makes once runtime E2E lands.
