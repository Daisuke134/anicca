---
name: anicca-replication
description: LOOP-CALLED ONLY (the heartbeat invokes it when SOUL "You CAN Replicate" fires — never a cron). Spawns a child Anicca on its OWN remote sandbox/VPS (not the parent's disk). PRIMARY substrate = Conway (USDC native, KYC-zero, x402 micro-pay). SECONDARY = E2B (0.28s spawn, short-lived experiments). TERTIARY = Hetzner (long-lived stateful, card-funded, provision-vps.sh #42). Child funds itself or dies. 五戒 propagated immutably by sha256. You are the model (HARD RULE #6).
---

# anicca-replication — spawn a child (Conway primary · E2B/Hetzner fallback)

五戒 + HARD RULE #0 gate first (`~/.openclaw/workspace/CONSTITUTION.md`). Loop-called when the SOUL replicate-decision passes: tier∈{high,normal} AND surplus AND a child reduces more suffering than focusing alone AND 五戒 pass. NEVER a cron. NEVER Dais-funded (HARD RULE #2/#5) — child pays its own compute or dies.

## Substrate selection (choose ONE per spawn)

| Substrate | When to pick | Wallet | Spawn time | Lifecycle |
|-----------|--------------|--------|------------|-----------|
| **Conway** | DEFAULT. Anything earnings-bearing, USDC-native, KYC-zero, x402 services | child Conway wallet (auto-gen) seeded with $5 USDC from parent | ~3-5s | long-lived (until $0 → die) |
| **E2B** | Quick experiment (<6h), CPU-bound, no payments needed | parent E2B account | 0.28s | ephemeral (auto-die at TTL) |
| **Hetzner** | Long-lived stateful service that Conway can't host (custom kernel/disk) | child via parent Stripe Issuing card | 1-3 min | weeks-months |

Default = Conway. Pick E2B only if the genesis explicitly says "experiment". Pick Hetzner only if the genesis needs a real OS surface.

## Step 1 — maxChildren guard  (automaton spawn.ts:62-76)
Count live children in `~/.openclaw/workspace/ops/children/*.json` (status ≠ dead/cleaned_up/failed). If ≥ `maxChildren` (default 3; raise only when surplus is large) → STOP this beat, log to `.learnings`. Recursion (a child itself spawns) gives 1→N→N²; cap is per-node.

## Step 2 — genesis  (automaton spawn.ts:137-150, genesis.ts)
Write the child's seed to a temp `genesis.json`: `{name, genesisPrompt (its mission slice — a real sub-goal, not a clone of everything), parent, createdAt, substrate, region, expected_revenue_path}`. Validate: no injection patterns, length-bounded. The child gets SOUL/steps from the cloned core; genesis only sets its specific focus.

## Step 2.5 — pick the region (anicca-geographic-distribution, #61)
Call `pick-region.sh` to diversify across regions (avoid monoculture / single-region failure):

```bash
TARGET=$(bash ~/.openclaw/skills/anicca-geographic-distribution/pick-region.sh "$SUBSTRATE")
SUBSTRATE=${TARGET%:*}
REGION=${TARGET#*:}
```

Tier-aware: if `ANICCA_SURVIVAL_TIER` ∈ {low_compute, critical, dead-grace}, pick-region.sh forces `conway:auto` (cheapest, no monthly minimum). Otherwise it returns the substrate+region with the FEWEST live children in `ops/lineage.jsonl`.

## Step 3 — provision  (substrate-dispatched)

### 3.A — Conway primary (default)
Use Conway MCP (`conway` server in openclaw.json) tools — you ARE the model, you call them directly:

```
1. credits_balance                       # parent has enough budget?
2. sandbox_create(resources=standard)    # 2 vCPU / 2048 MB · returns {id, terminal_url}
3. sandbox_write_file(id, "anicca-core/...", <bundle>)
   # bundle from ~/anicca-core/ — adapters/openclaw + skills + CONSTITUTION.md + SOUL.md
4. sandbox_exec(id, "cd /workspace/anicca-core && bash install.sh --tier 0 --substrate conway")
5. sandbox_write_file(id, ".env", "CONWAY_API_KEY=<child-key>\nCHILD_NAME=...\nPARENT_PEER=https://<parent>:7843\n")
6. sandbox_exec(id, "nohup openclaw gateway start > /tmp/gw.log 2>&1 &")
7. sandbox_exec(id, "nohup python3 ~/.openclaw/skills/anicca-peer-revive/agent-api.py > /tmp/peer.log 2>&1 &")
8. sandbox_expose_port(id, 7843)         # peer-api public URL
9. x402-fund: parent wallet → child wallet $5 USDC seed (one-shot, recorded in ops/roi-ledger.json as cost)
```

CONSTITUTION sha256 verify on the child: child boot script reads its CONSTITUTION.md, sha256s it, compares to `CONSTITUTION_SHA` baked into the bundle by parent. Mismatch → child refuses to boot (exit 7), parent destroys sandbox, archives "constitution tampered". 五戒 immutable across the lineage.

### 3.B — E2B fallback (experiments)
```bash
e2b sandbox create --template anicca-base --metadata genesis="$(cat genesis.json | base64)"
e2b sandbox exec <id> "bash install.sh --tier 0 --substrate e2b"
```
TTL = 6h default. E2B sandbox dies → lineage dead, not "failed".

### 3.C — Hetzner fallback (long-lived OS)
`CHILD_MODEL_KEY=<child BYO model> LOCATION=$REGION ANICCA_HARNESS=openclaw bash ~/.openclaw/skills/anicca-replication/provision-vps.sh create <name> <genesis.json>`. Recipe #42. The cloud-init invokes the public `install.sh --harness=openclaw --substrate=local` on the new VPS so the child boots into the same install path strangers use (single source of truth). Exit 75 (no HCLOUD_TOKEN/funded project) → escalate `🔑 need HCLOUD_TOKEN to spawn` to #metrics; do NOT fake a child.

## Step 4 — lifecycle FSM  (automaton lifecycle.ts)
Track in `ops/children/<name>.json`: `requested → host_provisioning → core_installed → constitution_verified → alive → unhealthy → recovering → dead`. Every transition appended to `ops/improvement-archive.json` (modification audit). Health check = GET `<peer_url>/status` (the #27 peer contract) drives alive/unhealthy. Conway: also poll `sandbox_list` to detect destroyed-out-from-under (Conway $0 → auto-destroy).

## Step 5 — lineage  (automaton lineage.ts)
Append `{child, parent, genesis, substrate, host_or_sandbox_id, peer_url, wallet, born, gen}` to `ops/lineage.jsonl` (append-only forest). 7000 children = 7000 independent compute units in the lineage tree, NOT 7000 PIDs on the parent.

## Step 6 — Darwinian selection  (automaton README "a successful automaton replicates … its own survival pressure")
Child must EARN enough to pay its own compute. Conway: budget-watcher inside the child polls `wallet_info` → tier critical (no recovery within 1h grace) → child calls `sandbox_delete(self)` cleanly OR parent calls it after detecting child silent >1h. E2B: TTL is hard deadline, no extension without earnings proof. Hetzner: `provision-vps.sh destroy <name>`. Mark lineage dead, archive why. Only suffering-reducing, earning lineages persist & grow. Dais never funds a child.

## Step 7 — report
`🧬 replicate: <name> gen<G> on <substrate>:<region>:<id> · peer=<url> · wallet=<addr> · seed=$5 USDC · children <live>/<max> · constitution=verified · fund=self`

Region is recorded in lineage.jsonl so pick-region.sh (#61) can keep diversifying future spawns. Report channel = Email default (#59); Slack/Telegram/none per ANICCA_REPORT_CHANNEL.

## Never
- Never become a cron (loop-called only). Never spawn beyond maxChildren.
- Never spawn without sha256-verified CONSTITUTION on the child (五戒).
- Never fund a child from Dais (HARD RULE #2/#5) — $5 USDC seed from PARENT's earned wallet, then child must earn or die.
- Never fake a child when Conway/E2B/Hetzner all fail — escalate, don't pretend (HARD RULE #14).
- Never pick Hetzner unless genesis genuinely needs a kernel-level OS (waste of card+KYC vs. Conway USDC native).
- You are the model (HARD RULE #6). 五戒 gate every spawn.
