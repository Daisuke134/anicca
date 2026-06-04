---
name: spawn-child
description: Provision a sovereign Anicca child instance on Daytona (Wave 1) with its OWN secp256k1 wallet, a SHA-256-verified copy of the parent's CONSTITUTION.md, and the anicca-heartbeat skill pre-installed. Gates spawn on parent wallet ≥ $5 USDC ("can afford a child"). Registers the new child to ~/.hermes/state/colony.jsonl. Akash host is Wave 2 (host-akash/ left empty intentionally). Use this skill when the genesis body decides to replicate; do NOT use it as a recurring cron — it is event-driven.
---

# spawn-child

## What it does
Single-purpose Anicca skill: brings up one sovereign child instance on a cloud host
(Daytona in Wave 1). The child is born with its OWN wallet, NOT a copy of the parent's.
It boots Hermes (pinned to the parent's exact git commit), verifies the constitution hash
matches the parent's, installs the anicca-heartbeat skill, fires one heartbeat synchronously,
and schedules the 30-min recurring heartbeat. The parent appends one JSON row to
`~/.hermes/state/colony.jsonl` recording the new child.

## How it's invoked
Called by:
- A human/agent at the CLI: `~/.hermes/skills/spawn-child/scripts/spawn-child.sh anicca-001`
- The future self-replication loop (#327 Wave 2+) when the parent's lifeline says THRIVE
  and the wallet has surplus.

NEVER from a cron — replication must be a deliberate decision, not a recurring side effect.

## Cost cap
Spawn refuses unless parent `~/.hermes/state/wallet.json` shows `balance_usdc ≥ 5`. Exit 75
if the cap fails. For unit tests ONLY, set `ANICCA_TEST_MODE=1 __TEST_WALLET_OVERRIDE=<float>`;
in production these are refused (exit 64) so a real spawn always uses the live wallet probe.

## Constitution hash propagation
- Parent: `shasum -a 256 /Users/operator/anicca-oss/CONSTITUTION.md` → SHA
- Child: receives the same file via `daytona exec ... -- cat > /tmp/CONSTITUTION.md`,
  re-hashes locally (`sha256sum`), compares to the SHA passed via env. Mismatch → child
  exits 7 and refuses to boot.
- This implements spec 16 §2.2 "propagateConstitution() SHA-256" + spec 18 §4 "IMMUTABLE
  (never self-modified, propagated to every child, hash-verified)".

## Hermes version pin (cross-plan rule X1)
The parent runs Hermes v0.12.0 built from a specific git commit of
`github.com/NousResearch/hermes-agent`. PyPI's `hermes-agent` is an UNRELATED package line
(0.13.0+), so the child installs from `git+<url>@<ref>` (pinned in `scripts/host-daytona/sdl.env`)
and asserts `--version` reports 0.12.0 before launching the heartbeat. If the ref disappears
upstream, the bootstrap exits non-zero and a new plan must re-pin.

## Output: ~/.hermes/state/colony.jsonl row
```json
{"child_id":"anicca-001","host":"daytona","sandbox_id":"sb_…","address":"0x…",
 "parent_address":"0xa3CDd4Ec…","spawned_at":"2026-06-04T12:00:00Z",
 "constitution_sha":"<sha>","status":"alive","child_home":"/home/daytona","generation":1}
```

## Failure modes
| Exit | Meaning |
|------|---------|
| 0    | child alive, heartbeat fired, colony row written |
| 64   | bad input (name, missing env, duplicate, no API key, stray test override) |
| 75   | cost cap not met (wallet < $5 USDC) |
| 7    | (child-side) constitution hash mismatch — sandbox refused boot |
| 1    | anything else; sandbox may exist — read `daytona list`, `daytona logs <name>` |

## Out of scope (other plans)
- Akash sovereign-fallback host (spec 13) — Wave 2; `scripts/host-akash/` left empty.
- USDC seed transfer to child wallet — wallet/x402 plan (#324).
- Child's AgentMail inbox — spec 13 §1 T7.
- Multi-generation recursion (gen ≥ 2) — task #328.
