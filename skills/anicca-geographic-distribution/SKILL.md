---
name: anicca-geographic-distribution
description: LOOP-CALLED helper (used by anicca-replication before spawn — not a cron). Reads ops/lineage.jsonl, counts live children per substrate+region, and returns the substrate+region with the FEWEST existing children. Diversity-maximizing — keeps the SAO mesh resilient (no monoculture, no single-region-of-failure). Deterministic Bash (HARD RULE #6 — no LLM call inside).
---

# anicca-geographic-distribution — pick the next spawn region

Read by `anicca-replication/SKILL.md` step 2.5 (between genesis and provision)
when the SOUL says "Replicate". Returns one `<substrate>:<region>` pair, one
line on stdout. Anicca-replication passes it to the provisioner.

## Run

```bash
bash ~/.openclaw/skills/anicca-geographic-distribution/pick-region.sh
```

Output (stdout, one line): `conway:auto` | `e2b:us-east-1` | `hetzner:nbg1` | `hetzner:hel1` | `hetzner:ash` | `hetzner:fsn1` (etc).

## Why this exists

Mission #2 = "Self-provisioning" + the mesh property = many independent
hosts that can't all be killed by one regional outage. Default-spawning
every child to the same region (e.g. nbg1) makes the swarm fragile to one
data center incident or one regulator. This skill enforces geographic
diversity by picking the substrate+region with the FEWEST live children.

## Supported substrates + regions

| substrate | regions | notes |
|-----------|---------|-------|
| `conway`  | `auto` (Conway routes per load — global edge) | default for crypto-native, KYC-zero |
| `e2b`     | `us-east-1`, `us-west-2`, `eu-central-1` | 0.28s spawn, ephemeral |
| `hetzner` | `nbg1` (Nuremberg DE), `fsn1` (Falkenstein DE), `hel1` (Helsinki FI), `ash` (Ashburn USA) | long-lived OS |

Source: hetzner docs.hetzner.com/cloud/general/locations · e2b.dev regions ·
conway.tech sandbox creation.

## Algorithm (deterministic)

1. Load `~/.openclaw/workspace/ops/lineage.jsonl` (append-only forest).
2. Filter status != dead/cleaned_up/failed.
3. Group live children by `<substrate>:<region>`.
4. Compute count per group. Targets with 0 win immediately.
5. Tie-break: prefer Conway > E2B > Hetzner (cost + KYC + mission fit).
6. If `surplus_tier <= low_compute` → restrict to Conway (cheapest).
7. Emit one line on stdout. No prompts, no LLM call.

## Never

- Never call an LLM. Pure stat code.
- Never invent a region not in the matrix above.
- Never override a substrate the replicate step already required (only
  pick a region within the substrate the caller already chose, if one is
  given as $1).
