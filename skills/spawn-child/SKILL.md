---
name: anicca-spawn-child
description: Provisions a new Anicca instance (wallet + AgentMail inbox + constitution verify), deploys it to Akash, and registers it with anicca-001 peer-api. Spec 13 implementation.
triggers:
  - spawn anicca-N
  - new instance
  - akash deployment
  - cloud child
requires:
  - akash CLI (= /opt/homebrew/bin/akash 2.0.1)
  - tsx + viem (= bundled via package.json)
  - AGENTMAIL_API_KEY in ~/.openclaw/.env
  - DEEPSEEK_API_KEY in ~/.openclaw/.env
when_to_use: Triggered by anicca-001 heartbeat ONLY when threshold-check.sh prints ALLOW.
fire_condition: |
  wallet_usdc > $SPAWN_THRESHOLD_USDC (default 400)
  AND uptime_days > $SPAWN_THRESHOLD_DAYS (default 14)
  AND lifeline.status == THRIVE
---

# anicca-spawn-child (spec 13)

Spawns a new Anicca instance. The child gets its own wallet, its own AgentMail inbox,
its own Akash deployment, and verifies the constitution hash matches anicca-001's
expected value before running any heartbeat. Child registers itself with anicca-001
peer-api so the lineage dashboard sees it.

## Usage

```bash
# Local dry-run (= no broadcast, validates files + threshold check)
ANICCA_INSTANCE_ID=anicca-002 bash scripts/spawn.sh

# Production (= fires when threshold-check ALLOWS)
# Wired into _shared/heartbeat-beat.sh via:
#   bash skills/spawn-child/scripts/spawn.sh || true
```

## Files

| File | Purpose |
|---|---|
| `scripts/threshold-check.sh` | Gate — checks wallet/uptime/THRIVE. Prints ALLOW or BLOCK. |
| `scripts/wallet-factory.ts` | Provisions owner EOA + counter-factual smart account via viem. |
| `scripts/inbox-factory.ts` | Provisions `<instance_id>-claude@agentmail.to`. Falls back to auto-address if cap reached. |
| `scripts/constitution-hash.sh` | Boot-time integrity check. Hard-aborts on mismatch (exit 30). |
| `scripts/boot.sh` | Image entrypoint. Inline `/health` server + register with anicca-001. |
| `scripts/register.py` | Child posts itself to anicca-001 peer-api. Falls back to local pending file if peer-api offline. |
| `scripts/spawn.sh` | Orchestrator. Idempotent — caches each step's output to `state/<instance>/<step>.json`. |
| `package.json` | tsx + viem + agentmail deps for the TS scripts. |

## Sequence

```
1. threshold-check.sh         must print ALLOW
2. wallet-factory.ts          owner EOA + counter-factual smart account
3. inbox-factory.ts           <instance>-claude@agentmail.to
4. constitution.json          capture expected sha256 for boot verify
5. seed-transfer (DEFERRED)   anicca-001 → 1 USDC → anicca-002.smart_account
6. akash-deploy  (DEFERRED)   akash tx deployment create + provider lease
7. register.py                child notifies anicca-001 peer-api
```

Steps 5–6 deferred until anicca-001 wallet is funded. Mechanism is verified locally
(wallet+inbox+constitution+register code) so the live spawn is a one-shot from the
heartbeat once threshold-check returns ALLOW.

## Verification (v1 — live-tested 2026-06-03)

| Microtask | Status | Evidence |
|---|---|---|
| T1 akash CLI install + key | ✅ | `akash1g2vuc97l3n40gsp27av60ypta02upx0xmpph2g` (akash 2.0.1, mnemonic chmod 600) |
| T3 cert generate | DEFERRED | requires keys + AKT for tx; code path lives in `deploy/akash/cert.sh` |
| T4 Hermes Docker | written | `deploy/akash/Dockerfile.hermes` builds locally |
| T5 SDL | written | `deploy/akash/sdl.yaml` parses; akash 2.0.1 has no `validate` subcommand, deferred to provider-services dry-run |
| T6 wallet-factory | ✅ | EOA + smart account derived: `0x29297e8B31F40D5D9a46f4Ac1C1e571bCe0BDBa3`, broadcast=false |
| T7 inbox-factory | code-only | SDK call same shape as spec 10's `inboxes.create()`; gated until spawn fires (free tier cap) |
| T8 seed USDC | DEFERRED | waits for anicca-001 wallet > 0 |
| T9 constitution hash | ✅ | `38d4c8df4eff20699cb8d2057b20a1f9e659504370fac3b23d585a6cc9e6572e` matches main |
| T10 register call | code-only | falls back to `register-pending.json` if peer-api offline (= non-fatal) |
| T11 CFO bridge | future | will pick up child from peer-api once registered |

## Threshold semantics

`threshold-check.sh` returns exit 0 (= ALLOW) only if all three conditions hold:

| Variable | Default | Source |
|---|---|---|
| `SPAWN_THRESHOLD_USDC` | 400 | env |
| `SPAWN_THRESHOLD_DAYS` | 14 | env |
| `SPAWN_REQUIRE_STATUS` | THRIVE | env |

Wallet balance read via Base RPC `eth_call` (ERC-20 `balanceOf`), so no API key
needed. Lifeline status read from `~/.openclaw/state/lifeline.json::status`.

## Anti-goals

- No multi-tenant — each instance = own Akash deployment.
- No GPU — Hermes runs on 1 vCPU.
- No automatic re-deploy on lease expiry (= v2; for now, friction-fixer notices
  `lease-status != active` and re-fires spawn manually).
