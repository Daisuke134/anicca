# profiles/orch/inventory.md

| Field | Value |
|---|---|
| Name | `orch` |
| Role | front door of the instance — classifies inbound, drops Kanban tasks, synthesizes specialist outputs |
| Primary model | Kimi K2.6 Thinking via OpenRouter (`moonshotai/kimi-k2-thinking`) |
| Fallback chain | Qwen3.7 Max → DeepSeek v4-pro → Claude Opus 4.8 (spike only) → GPT-5.5 (spike only) — all via OpenRouter |
| Judge model | Claude Haiku 4.5 via OpenRouter (auxiliary, parses goal-done JSON) |
| Spec authority | `specs/07-HERMES-PIVOT.md` § 2.2 + § 2.3 + § 7 |

---

## § 1. Scope

### What `orch` CAN do

| Capability | Mechanism |
|---|---|
| Classify inbound into 8 categories | LLM call with category enum |
| Drop tasks into Kanban (`category`, `profile_hint`, `payload`, `ttl=600s`) | `kanban_db.create_task()` |
| Synthesize multi-specialist results back to caller | LLM call with `result_payload` aggregation |
| Run the 60s heartbeat loop (calls `anicca-heartbeat-core`) | `hermes daemon` tick |
| Spawn / kill direct children (via `anicca-spawn-controller`) | Daytona API |
| Halt the instance gracefully (drain Kanban, exit clean) | shutdown signal handler |
| Report status to operator via `/goal "status"` | reads Kanban + wallet + Constitution hash |

### What `orch` CANNOT do

| Anti-capability | Why |
|---|---|
| Sign wallet transactions directly | belongs to `earn-x402` / `earn-autohedge` / `ubi` (separation of concerns) |
| Modify Constitution.md | `constitution` profile owns hash verification; no profile can mutate the file |
| Run an x402 endpoint | `earn-x402` owns the HTTP listener |
| Generate creative content / write blog posts | `cook-loop` profile owns SHIP step |
| Send USDC out | `ubi` profile owns money-out routing |
| Repair broken skills | `fixer` profile owns self-heal |
| Talk to OpenRouter billing | `anicca-fuel-broker` skill (separate) |

---

## § 2. Tools (≤10 in scope per Shann pattern)

| Tool | Source | Use |
|---|---|---|
| `kanban_create_task` | Hermes core (`kanban_db.py`) | drop work for specialists |
| `kanban_query` | Hermes core | inspect status |
| `goal_classify` | L2 skill `anicca-orch-classifier` | LLM-based category routing |
| `goal_synthesize` | L2 skill `anicca-orch-synthesizer` | LLM-based result aggregation |
| `wallet_balance_read` | viem `PublicClient` | balance check for spawn gate |
| `constitution_hash_read` | `shasum -a 256` shell call | hash sanity for own ticks |
| `colony_ledger_read` | reads `~/.hermes/colony.json` | colony size check |
| `heartbeat_tick` | L2 skill `anicca-heartbeat-core` | 60s loop |
| `spawn_request` | L2 skill `anicca-spawn-controller` | provision new child |
| `halt_instance` | shutdown signal | emergency stop |

---

## § 3. Dependencies (which profiles `orch` routes to)

```
                       
  orch                  
   ├──► earn-x402        (when category=earn AND payload has x402_url)
   ├──► earn-autohedge   (when category=earn AND payload has swap_path)
   ├──► earn-bounty      (when category=earn AND payload has bounty_url)
   ├──► earn-bittensor   (when category=earn AND payload has subnet_id)
   ├──► earn-farcaster   (when category=earn AND payload has cast_hash)
   ├──► cook-loop        (when category=cook)
   ├──► ubi              (when category=ubi)
   ├──► fixer            (when category=heal OR retried task fails 3×)
   └──► constitution     (when category=constitution OR hash mismatch detected)
                       
```

---

## § 4. Success metric (how to know it's working)

| Metric | Target | Source |
|---|---|---|
| Inbound goals classified | ≥ 99% within 2s | `daemon.log` grep `category=` |
| Kanban tasks reach `done` (not `failed`) | ≥ 95% per 24h | `sqlite3 ~/.hermes/kanban.db "SELECT COUNT(*)/COUNT(*)..."` |
| Heartbeat tick on time | < 60s drift | `~/.hermes/logs/heartbeat.log` |
| Multi-specialist synthesis correctness | manual spot-check weekly | sample `result_payload` |
| Self-heal escalations | < 5 / day | count `fixer` profile claims in Kanban |
| Constitution hash check | 100% pass | `~/.hermes/logs/constitution-audit.log` |

If any metric drops, escalate to `fixer` profile and read `runbook.md`.

---

## § 5. State files this profile owns

| Path | Purpose |
|---|---|
| `~/.hermes/profiles/<instance>-orch/config.toml` | model + Kanban + heartbeat config |
| `~/.hermes/profiles/<instance>-orch/wallet.json` | smart wallet address (NOT privkey — that's CDP HSM) |
| `~/.hermes/profiles/<instance>-orch/soul.md` | personality (see `soul.md` in this dir) |
| `~/.hermes/profiles/<instance>-orch/sessions.db` | FTS5 session search |
| `~/.hermes/kanban.db` | shared Kanban (read/write) |
| `~/.hermes/colony.json` | colony ledger (read for spawn gate) |

---

## § 6. Cross-references

| Concept | Authority |
|---|---|
| /goal lifecycle | `specs/07-HERMES-PIVOT.md` § 2.3 |
| Kanban schema | `control-room/orchestrator-and-fleet-skills.md` § 3 |
| Heartbeat tick | `specs/07-HERMES-PIVOT.md` § 7 |
| Routing categories | `control-room/orchestrator-and-fleet-skills.md` § 2 |
| Spawn gate | `specs/00-MASTER.md` § 7.3 |

---

**END OF profiles/orch/inventory.md.**
